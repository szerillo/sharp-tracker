#!/usr/bin/env python3
"""Tennis prices: Pinnacle, Kalshi and Novig, pregame only, matched to one event registry (Sean, 11/1: first-set betting is where he
thinks tennis has an edge).

Events: ESPN tour matches (data/tennis/schedule.json from loggers/tennis_scores.py) are the backbone; Pinnacle matchups add the
Challenger / ITF matches ESPN does not carry. Every vendor match is keyed by the two players' surnames and the date, so the
same match lines up across venues whatever the first-name spelling ("T. Seyboth Wild" / "Thiago Seyboth Wild").
event_id = the ESPN match id when ESPN has it, else "x:<YYYYMMDD>:<surname>-<surname>" (alphabetical). Sides: home = player 1
(ESPN order; alphabetical for x: events), away = player 2. Ticks stop at the match start (ESPN, else Pinnacle).

Markets (same tick format as loggers/lines.py, so the move tape and flow code read them unchanged):
  ml        match winner               Pinnacle (main matchup, period 0), Kalshi *MATCH series, Novig MONEY
  1s_ml     first-set winner           Pinnacle (period 1), Kalshi *SETWINNER set 1, Novig FIRST_SET_MONEYLINE
  spread    games handicap (main)      Pinnacle "(Games)" matchup, Novig SPREAD (main strike)
  total     total games (main)         Pinnacle "(Games)" matchup, Novig TOTAL (main strike)
  1s_spread / 1s_total                 Pinnacle "(Games)" matchup, period 1
Writes data/tennis/ticks/<ET date>.jsonl.gz (20-minute run) or data/tennis/ticks5/ (--fast), data/tennis/events.json (the registry,
in the schedule shape the move tape reads: start, away, home, away_team/home_team displayName, tour, tournament) and
data/kalshi/fast_meta_tennis.json (Kalshi ticker / Novig market -> event, market, side) so the 5-minute trade feed logs tennis fills.
Usage: python3 loggers/tennis_lines.py [--fast]"""
import os, sys, random, re, json, gzip, time, unicodedata, collections, datetime as dt, urllib.request, urllib.parse
import concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
FAST = '--fast' in sys.argv
TD = os.path.join(ROOT, 'data', 'tennis'); OUTD = os.path.join(TD, 'ticks5' if FAST else 'ticks'); os.makedirs(OUTD, exist_ok=True)
EVENTS = os.path.join(TD, 'events.json'); KMETA = os.path.join(ROOT, 'data', 'kalshi', 'fast_meta_tennis.json')
NOW = dt.datetime.now(dt.timezone.utc); TS = NOW.strftime('%Y-%m-%dT%H:%M:%SZ'); ET = __import__('zoneinfo').ZoneInfo('America/New_York')
PIN = "https://guest.api.arcadia.pinnacle.com/0.1"; KAPI = "https://api.elections.kalshi.com/trade-api/v2"; NOVP = "https://api.novig.com/v3/public/catalog"
HORIZON_H = 36
K_MATCH = ['KXATPMATCH', 'KXWTAMATCH', 'KXATPCHALLENGERMATCH', 'KXWTACHALLENGERMATCH', 'KXITFMATCH', 'KXITFWMATCH']
K_SET = ['KXATPSETWINNER', 'KXWTASETWINNER']
NOVIG_TYPES = {'MONEY': 'ml', 'FIRST_SET_MONEYLINE': '1s_ml', 'SPREAD': 'spread', 'TOTAL': 'total'}
STATS = collections.Counter(); T0 = time.time()
ROUND_RE = r'\s+(Round of \d+|\d+(st|nd|rd|th) Qualifying Round|Qualif\w*.*|Quarter\w*.*|Semi\w*.*|Final.*|Round \d+.*|R\d+)$'


def g(u, tries=3, timeout=25):
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=timeout))
        except urllib.error.HTTPError as e:
            if e.code == 404: return {}
            if e.code == 429: STATS['429'] += 1; time.sleep(3 * (i + 1)); continue
            time.sleep(1 + i)
        except Exception: STATS['err'] += 1; time.sleep(1 + i)
    return {}


def ts(s):
    if isinstance(s, (int, float)): return dt.datetime.fromtimestamp(s / 1000 if s > 1e11 else s, dt.timezone.utc)
    s = s.replace(' ', 'T'); s = s if re.search(r'(Z|[+-]\d\d:?\d\d)$', s) else s + 'Z'
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\((games|sets)\)', '', s); s = re.sub(r'[^a-z\s-]', ' ', s).replace('-', ' ')
    return [t for t in s.split() if t]


def surname(name):
    t = norm(name); return t[-1] if t else ''


def same_player(a, b):
    """Vendor name a vs registry name b: same surname, or (reversed name order, e.g. East Asian names) any shared token of 4+ letters
    that is also one side's surname."""
    ta, tb = norm(a), norm(b)
    if not ta or not tb: return False
    if ta[-1] == tb[-1]:
        fa, fb = ta[:-1], tb[:-1]
        return not fa or not fb or fa[0][0] == fb[0][0]          # first initial agrees when both have one
    return (ta[-1] in tb and len(ta[-1]) >= 4) or (tb[-1] in ta and len(tb[-1]) >= 4)


class Registry:
    def __init__(self):
        self.ev = {}
        old = json.load(open(EVENTS)) if os.path.exists(EVENTS) else {}
        cut = (NOW - dt.timedelta(days=3)).isoformat()
        self.ev = {k: v for k, v in old.items() if (v.get('start') or '9') >= cut[:10]}
        sp = os.path.join(TD, 'schedule.json')
        for k, m in (json.load(open(sp)) if os.path.exists(sp) else {}).items():
            if not m.get('start') or m.get('status') in ('STATUS_FINAL',): continue
            self.ev[k] = dict(event_id=k, start=m['start'], home=surname(m['p1']).upper(), away=surname(m['p2']).upper(),
                              home_team=dict(displayName=m['p1']), away_team=dict(displayName=m['p2']), tour=m.get('tour'), tournament=m.get('tournament'),
                              round=m.get('round'), source='espn')

    def find(self, n1, n2, when):
        """-> (event_id, n1 is home) or (None, None). when: vendor start time (may be rough)."""
        best = None
        for k, e in self.ev.items():
            st = ts(e['start']); dh = abs((st - when).total_seconds()) / 3600 if when else 0
            if dh > 30: continue
            h, a = e['home_team']['displayName'], e['away_team']['displayName']
            if same_player(n1, h) and same_player(n2, a): o = True
            elif same_player(n1, a) and same_player(n2, h): o = False
            else: continue
            if best is None or dh < best[0]: best = (dh, k, o)
        return (best[1], best[2]) if best else (None, None)

    def add(self, n1, n2, when, tour=None, tournament=None):
        """A match ESPN does not carry (Challenger / ITF), from Pinnacle or Novig (exact starts): synthetic id, alphabetical sides."""
        p = sorted([n1, n2], key=lambda n: surname(n))
        k = f"x:{when.astimezone(ET).strftime('%Y%m%d')}:{surname(p[0])}-{surname(p[1])}"
        if k not in self.ev:
            self.ev[k] = dict(event_id=k, start=when.strftime('%Y-%m-%dT%H:%MZ'), home=surname(p[0]).upper(), away=surname(p[1]).upper(),
                              home_team=dict(displayName=p[0]), away_team=dict(displayName=p[1]), tour=tour, tournament=tournament, source='pinnacle')
        return k, n1 == p[0]

    def started(self, k):
        e = self.ev.get(k); return bool(e) and ts(e['start']) <= NOW


ROWS = []


def tick(ev, market, side, venue, feed, R, line=None, american=None, bid=None, ask=None, last=None, vol=None, limit=None, flags=None, extra=None, participant=None):
    if R.started(ev): STATS['live_dropped'] += 1; return
    r = dict(ts=TS, event_id=ev, market=market, side=side, venue=venue, feed=feed)
    for k, v in (('line', line), ('participant', participant), ('american', american), ('bid', bid), ('ask', ask), ('last', last), ('vol', vol),
                 ('limit', limit), ('flags', flags), ('extra', extra)):
        if v is not None and v != [] and v != {}: r[k] = v
    ROWS.append(r)


def pinnacle(R):
    pm = g(f"{PIN}/sports/33/matchups?brandId=0") or []; pk = g(f"{PIN}/sports/33/markets/straight?primaryOnly=false") or []
    km = collections.defaultdict(list)
    for k in pk:
        if not k.get('isAlternate') and k.get('status') == 'open': km[k['matchupId']].append(k)
    main = {}; n = 0
    for m in pm:
        if m.get('type') != 'matchup' or len(m.get('participants', [])) != 2: continue
        st = ts(m['startTime'])
        if st <= NOW or st > NOW + dt.timedelta(hours=HORIZON_H): continue
        ps = {p['alignment']: re.sub(r'\s*\((Games|Sets)\)\s*$', '', p['name']) for p in m['participants']}
        lg = (m.get('league') or {}).get('name') or ''
        if 'doubles' in lg.lower() or '/' in ps.get('home', ''): continue
        ev, o = R.find(ps['home'], ps['away'], st)
        if not ev: ev, o = R.add(ps['home'], ps['away'], st, tour=lg.split()[0] if lg else None, tournament=lg)
        if R.ev[ev].get('source') == 'espn' and st < ts(R.ev[ev]['start']): R.ev[ev]['start_pin'] = m['startTime']
        side = {'home': 'home' if o else 'away', 'away': 'away' if o else 'home'}      # Pinnacle alignment -> registry side
        games = '(Games)' in m['participants'][0]['name']
        for k in km[m['id']]:
            per = k.get('period'); typ = k.get('type'); P = {x['designation']: x for x in k['prices']}
            lim = next((l['amount'] for l in k.get('limits') or [] if l['type'] == 'maxRiskStake'), None)
            pre = {0: '', 1: '1s_'}.get(per)
            if pre is None: continue
            if typ == 'moneyline' and not games and 'home' in P and 'away' in P:
                for d in ('home', 'away'): tick(ev, pre + 'ml', side[d], 'Pinnacle', 'pinnacle_guest', R, american=P[d]['price'], limit=lim, participant=ps[d])
                n += 1
            elif typ == 'spread' and games and 'home' in P:
                lh = P['home'].get('points')
                tick(ev, pre + 'spread', side['home'], 'Pinnacle', 'pinnacle_guest', R, line=lh, american=P['home']['price'], limit=lim, participant=ps['home'])
                tick(ev, pre + 'spread', side['away'], 'Pinnacle', 'pinnacle_guest', R, line=-lh, american=P['away']['price'], limit=lim, participant=ps['away'])
                n += 1
            elif typ == 'total' and games and 'over' in P:
                for d in ('over', 'under'): tick(ev, pre + 'total', d, 'Pinnacle', 'pinnacle_guest', R, line=P[d].get('points'), american=P[d]['price'], limit=lim)
                n += 1
    return n


AN_TENNIS = {'1548': 'DK', '1006': 'FD', '1005': 'Caesars', '15': 'AN_Consensus'}   # NY books (11/2, Sean: domestic books price set 1 softer than the exchanges)


def action_network(R):
    """US sportsbooks through Action Network's public scoreboard: match moneyline and set-1 moneyline (DraftKings NY carries ATP set 1;
    FanDuel NY the match only; Caesars NY no tennis at present; consensus for reference). Joined to the registry by player names."""
    n = 0
    for lg in ('atp', 'wta'):
        for d in (0, 1):
            day = (NOW.astimezone(ET) + dt.timedelta(days=d)).strftime('%Y%m%d')
            x = g(f"https://api.actionnetwork.com/web/v2/scoreboard/{lg}?bookIds={','.join(AN_TENNIS)}&periods=event,set1&date={day}") or {}
            for c in x.get('competitions') or []:
                if c.get('status') != 'scheduled': continue
                st = ts(c['start_time'].replace('.000Z', 'Z'))
                if st <= NOW or st > NOW + dt.timedelta(hours=HORIZON_H): continue
                cp = {p['id']: (p.get('player') or {}).get('full_name') for p in c.get('competitors') or []}
                ah = {p['side']: cp[p['id']] for p in c.get('competitors') or []}
                if not ah.get('home') or not ah.get('away'): continue
                ev, o = R.find(ah['home'], ah['away'], st)
                if not ev: continue
                for bid, M in (c.get('markets') or {}).items():
                    v = AN_TENNIS.get(bid)
                    if not v: continue
                    for per, mk in (('event', 'ml'), ('set1', '1s_ml')):
                        for oc in ((M.get(per) or {}).get('moneyline') or []):
                            nm = cp.get(oc.get('competitor_id'))
                            if not nm or oc.get('odds') is None or oc.get('is_live'): continue
                            e = R.ev[ev]; sd = 'home' if same_player(nm, e['home_team']['displayName']) else 'away' if same_player(nm, e['away_team']['displayName']) else None
                            if not sd: continue
                            tick(ev, mk, sd, v, 'action_network', R, american=oc['odds'], participant=nm); n += 1
    return n


def kalshi(R, meta):
    def walk(series):
        cur = ''
        while True:
            x = g(f"{KAPI}/markets?series_ticker={series}&status=open&limit=1000" + (f"&cursor={cur}" if cur else ''))
            for m in x.get('markets', []): yield m
            cur = x.get('cursor')
            if not cur or not x.get('markets'): break
    n = 0; un = 0
    for series in K_MATCH + K_SET:
        evs = collections.defaultdict(list)
        for m in walk(series): evs[m['event_ticker']].append(m)
        for et, ms in evs.items():
            if series in K_SET and not et.endswith('-1'): continue          # first set only
            if len(ms) != 2: continue
            names = [m.get('yes_sub_title') or '' for m in ms]
            when = ts(ms[0].get('occurrence_datetime') or ms[0].get('expected_expiration_time') or TS)
            ev, o = R.find(names[0], names[1], when)
            if not ev: un += 1; continue                                     # Kalshi times are rough: never create events from Kalshi
            mk = '1s_ml' if series in K_SET else 'ml'
            for m, nm in zip(ms, names):
                sd = 'home' if same_player(nm, R.ev[ev]['home_team']['displayName']) else 'away'
                bid = float(m.get('yes_bid_dollars') or 0) or None; ask = float(m.get('yes_ask_dollars') or 0) or None
                fl = []
                if bid is not None and ask is not None and ask - bid > 0.04: fl.append('wide')
                if not bid or not ask or ask >= 1: fl.append('oneside')
                tick(ev, mk, sd, 'Kalshi', 'kalshi_api', R, bid=bid, ask=ask, last=float(m.get('last_price_dollars') or 0) or None,
                     vol=float(m.get('volume_fp') or m.get('volume') or 0), flags=fl or None, extra=dict(ticker=m['ticker'], yes=sd), participant=nm)
                meta[m['ticker']] = dict(sport='tennis', event_id=ev, market=mk, line=None, yes_side=sd, seen=NOW.date().isoformat(), start=R.ev[ev]['start'])
            n += 1
    STATS['kalshi_unmatched'] = un
    return n


def novig(R, meta):
    try:
        from sharp import novig_auth as NA; signed = NA.available()
    except Exception: signed = False
    def nv(path, query):
        if signed:
            for i in range(4):          # the 5-minute job shares Novig with four other fast jobs at the same second: back off on 429 / 5xx
                try: st, r = NA.request('GET', '/v3/catalog' + path, query, timeout=30)
                except Exception as e: st, r = type(e).__name__, None
                if st == 200: return r
                STATS[f'novig_http_{st}'] += 1
                if st in (401, 403): break          # 11/6: signed key rejected since 11/4; use the public API
                time.sleep(3 * (i + 1) + random.random() * 2)
            else: return {}
        return g(f"{NOVP}{path}?{query}")
    todo = []
    for lg in ('ATP', 'WTA'):
        for e in (nv('/events', f"league={lg}&status=OPEN_PREGAME&limit=500") or {}).get('items', []):
            if '@' not in e.get('description', ''): continue
            st = ts(e['startsTs'])
            if st <= NOW or st > NOW + dt.timedelta(hours=HORIZON_H): continue
            d = re.sub(ROUND_RE, '', e['description'])
            a, h = [s.strip() for s in d.split('@', 1)]
            ev, o = R.find(h, a, st)
            if not ev: ev, o = R.add(h, a, st, tour=lg, tournament=None); STATS['novig_new_events'] += 1     # Novig start times are exact
            todo.append((ev, e))
            continue
    def mk_list(x):
        ev, e = x
        if time.time() - T0 > 200: return ev, []
        return ev, (nv('/markets', f"event={e['eventId']}&limit=2000") or {}).get('items', [])
    with cf.ThreadPoolExecutor(4 if signed else 3) as ex: out = list(ex.map(mk_list, todo))
    n = 0
    for ev, ms in out:
        E = R.ev[ev]; H, A = E['home_team']['displayName'], E['away_team']['displayName']
        mains = collections.defaultdict(list)
        for m in ms:
            typ = NOVIG_TYPES.get(m.get('marketType'))
            if not typ or m.get('status') != 'OPEN': continue
            bids = {o['name']: float(o['bid']['price']) for o in m.get('outcomes', []) if (o.get('bid') or {}).get('price') is not None}
            if len(bids) != 2: continue
            mains[typ].append((m, bids))
        for typ, L in mains.items():
            m, bids = min(L, key=lambda z: abs(list(z[1].values())[0] - 0.5))   # main strike: nearest even money
            strike = float(m['strike']) if m.get('strike') not in (None, '') else None
            sides = {}
            for nm in bids:
                if typ == 'total': sides[nm] = 'over' if nm.lower().startswith('over') else 'under'
                else:
                    base = re.sub(r'\s+[+-]?\d+\.?\d*$', '', nm)
                    sides[nm] = 'home' if same_player(base, H) else ('away' if same_player(base, A) else None)
            if None in sides.values() or len(set(sides.values())) != 2: STATS['novig_side_miss'] += 1; continue
            flags = ['wide'] if 1 - sum(bids.values()) > 0.04 else None
            outs = {}
            for nm, sd in sides.items():
                other = [x for x in bids if x != nm][0]
                line = None
                if typ == 'spread':
                    mm = re.search(r'([+-]?\d+\.?\d*)$', nm); line = float(mm.group(1)) if mm else None
                elif typ == 'total': line = strike
                oid = next((o['outcomeId'] for o in m['outcomes'] if o['name'] == nm), None); outs[oid] = sd
                tick(ev, typ, sd, 'Novig', 'novig_api', R, line=line, bid=bids[nm], ask=round(1 - bids[other], 4), flags=flags,
                     extra=dict(market_id=m['marketId'], outcome_id=oid))
            meta['nv:' + m['marketId']] = dict(sport='tennis', event_id=ev, market=typ, line=strike if typ == 'total' else None, outcomes=outs,
                                               seen=NOW.date().isoformat(), start=E['start'])
            n += 1
    return n


def main():
    R = Registry(); meta = json.load(open(KMETA)) if os.path.exists(KMETA) else {}
    rep = {}
    for name, fn in (('pinnacle', lambda: pinnacle(R)), ('novig', lambda: novig(R, meta)), ('action_network', lambda: action_network(R)), ('kalshi', lambda: kalshi(R, meta))):   # Kalshi last: it only joins events
        t = time.time()
        try: rep[name] = fn()
        except Exception as e: rep[name] = f'{type(e).__name__}: {e}'
        rep[name + '_s'] = round(time.time() - t)
    day = NOW.astimezone(ET).date().isoformat()
    if ROWS:
        with gzip.open(os.path.join(OUTD, f'{day}.jsonl.gz'), 'at') as f:
            for r in ROWS: f.write(json.dumps(r, separators=(',', ':')) + '\n')
    json.dump(R.ev, open(EVENTS, 'w'), separators=(',', ':'))
    cut = (NOW - dt.timedelta(days=14)).date().isoformat(); meta = {k: v for k, v in meta.items() if v.get('seen', '9') >= cut}
    json.dump(meta, open(KMETA, 'w'), separators=(',', ':'))
    byv = collections.Counter((r['venue'], r['market']) for r in ROWS)
    print(f"[tennis lines{' fast' if FAST else ''}] {len(ROWS)} ticks on {len({r['event_id'] for r in ROWS})} matches; markets {rep}; {dict(byv)}; {dict(STATS)}")


if __name__ == '__main__':
    main()
