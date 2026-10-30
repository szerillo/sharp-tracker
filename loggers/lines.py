#!/usr/bin/env python3
"""Generic game-line + prop logger for the registry sports (NFL, NBA, CFB): python3 loggers/lines.py --sport nfl

One snapshot per run of every venue, written as NORMALISED ticks already keyed to the canonical event (ESPN event id), so the
build needs no per-venue parsing:  data/<sport>/ticks/YYYY-MM-DD.jsonl, one row per venue x market x side:
  ts, event_id, market (ml|spread|total|tt_home|tt_away, with 1h_/1q_ prefixes; prop_<STAT>), side (home|away|over|under|draw),
  line, participant (team code or player key), player, venue, feed, american | bid/ask/last/vol, limit, flags, extra (depth, public %).
Schedule: data/<sport>/schedule.json (ESPN scoreboard, cumulative; carries status + scores so results.py can grade from it).
Venues: Pinnacle guest API (limits), Kalshi public (game + 1H/1Q + player props), Action Network (open, consensus with ticket/money %,
NY books; BetMGM excluded), Novig public (book depth, best-bid per outcome). Polymarket is logged by loggers/polymarket.py.
Read-only. Places nothing."""
import urllib.parse, sys, os, json, time, re, datetime as dt, urllib.request, collections, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
from sharp import sports as S
from sharp.norm import player_key, et_date, iso, parse_ts

ARGS = sys.argv[1:]; SPORT = ARGS[ARGS.index('--sport') + 1] if '--sport' in ARGS else 'nfl'; CFG = S.SPORTS[SPORT]
OUT = os.path.join(HERE, '..', 'data', SPORT); TD = os.path.join(OUT, 'ticks'); os.makedirs(TD, exist_ok=True)
SCHED = os.path.join(OUT, 'schedule.json')
NOW = dt.datetime.now(dt.timezone.utc); TS = iso(NOW)
KAPI = "https://api.elections.kalshi.com/trade-api/v2"; PIN = "https://guest.api.arcadia.pinnacle.com/0.1"; NOV = "https://api.novig.com/v3/public"
AN_BOOKS = {'15': 'AN_Consensus', '30': 'AN_Open', '1548': 'DK', '69': 'FD', '1005': 'Caesars', '972': 'BetRivers', '2789': 'Fanatics', '4621': 'theScore'}


T0 = time.time(); BUDGET_S = float(os.environ.get('LINES_BUDGET_S', 420)); STATS = collections.Counter()
FAST = bool(os.environ.get('LINES_FAST'))   # 5-minute logger: game markets only, no props, Novig best-bid from the listing (no book calls)


def over_budget(): return time.time() - T0 > BUDGET_S


def g(u, tries=2, timeout=20):
    """One GET with short retries; gives up fast when the whole run is over budget so a throttling venue cannot stall the job."""
    for i in range(tries):
        if over_budget(): STATS['skipped_budget'] += 1; return {}
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=timeout)); STATS['ok'] += 1; return r
        except urllib.error.HTTPError as e:
            STATS[f'http{e.code}'] += 1
            if e.code == 404: return {}
            if e.code == 429: time.sleep(3 * (i + 1)); continue
            time.sleep(1.0 * (i + 1))
        except Exception as e: STATS[type(e).__name__] += 1; time.sleep(1.0 * (i + 1))
    return {}


# ----------------------------------------------------------------- schedule (ESPN) ----
def espn_schedule():
    sched = json.load(open(SCHED)) if os.path.exists(SCHED) else {}
    for d in range(-1, CFG['horizon_days'] + 1):
        day = (et_date(NOW) + dt.timedelta(days=d)).strftime('%Y%m%d')
        extra = '&groups=80&limit=400' if SPORT == 'cfb' else ''
        x = g(f"https://site.api.espn.com/apis/site/v2/sports/{CFG['espn']}/scoreboard?dates={day}{extra}")
        if CFG.get('fights'):
            for card in x.get('events', []):
                for c in card.get('competitions', []):
                    teams = {}
                    for t in c['competitors']:
                        ath = t.get('athlete') or {}; nm = ath.get('displayName') or ''; parts = nm.split()
                        teams['home' if t.get('order') == 1 else 'away'] = dict(abbr=S.fighter_code(nm), displayName=nm, shortDisplayName=ath.get('shortName'), name=parts[-1] if parts else nm,
                                                                                 location=' '.join(parts[:-1]), score=None, id=ath.get('id'), winner=t.get('winner'))
                    if len(teams) != 2: continue
                    st = c.get('status', {}).get('type', {})
                    sched[c['id']] = dict(event_id=c['id'], start=c.get('date') or card['date'], away=teams['away']['abbr'], home=teams['home']['abbr'], away_team=teams['away'], home_team=teams['home'],
                                          venue=(c.get('venue') or {}).get('fullName'), card=card.get('name'), card_id=card['id'], weight=(c.get('type') or {}).get('abbreviation'),
                                          status=st.get('name'), completed=st.get('completed'), fetched=TS)
            continue
        for ev in x.get('events', []):
            c = ev['competitions'][0]; teams = {}
            for t in c['competitors']:
                tm = t['team']; teams[t['homeAway']] = dict(abbr=tm.get('abbreviation'), displayName=tm.get('displayName'), shortDisplayName=tm.get('shortDisplayName'),
                                                              name=tm.get('name'), location=tm.get('location'), score=t.get('score'), id=tm.get('id'))
            v = c.get('venue') or {}; st = c.get('status', {}).get('type', {})
            rec = dict(event_id=ev['id'], start=ev['date'], away=teams.get('away', {}).get('abbr'), home=teams.get('home', {}).get('abbr'),
                       away_team=teams.get('away'), home_team=teams.get('home'), venue=v.get('fullName'), indoor=v.get('indoor'),
                       city=(v.get('address') or {}).get('city'), state=(v.get('address') or {}).get('state'), status=st.get('name'), completed=st.get('completed'),
                       week=(ev.get('week') or {}).get('number'), neutral=c.get('neutralSite'), conf=c.get('conferenceCompetition'), fetched=TS, league=CFG.get('league_key'))
            # linescores (for 1H / 1Q grading) when present
            ls = {t['homeAway']: [float(q.get('value') or 0) for q in (t.get('linescores') or [])] for t in c['competitors']}
            if any(ls.values()): rec['linescores'] = ls
            sched[ev['id']] = rec
    json.dump(sched, open(SCHED, 'w'), separators=(',', ':'))
    return sched


class Matcher:
    def fighter_key(self, ev, name):
        """Vendor fighter name -> the ESPN fighter's player_key for this fight (surname match; vendors spell first names differently)."""
        e = self.sched.get(ev) or {}
        code = S.fighter_code(name)
        for side in ('away_team', 'home_team'):
            dn = (e.get(side) or {}).get('displayName')
            if dn and S.fighter_code(dn) == code: return player_key(dn)
        return player_key(name)

    def __init__(self, sched):
        self.sched = sched; self.by = collections.defaultdict(list); self.unmatched = collections.Counter()
        for e in sched.values():
            if not (e.get('away') and e.get('home')): continue
            st = parse_ts(e['start'])
            if st < NOW - dt.timedelta(days=2) or st > NOW + dt.timedelta(days=CFG['horizon_days'] + 1): continue
            for d in (-1, 0, 1): self.by[(et_date(st) + dt.timedelta(days=d), e['away'], e['home'])].append(e)
        self.teams = S.Teams(SPORT, [e for e in sched.values()])

    def match(self, date, away, home, start=None):
        c = self.by.get((date, away, home)) or []
        if not c and CFG.get('fights'): c = self.by.get((date, home, away)) or []     # fight feeds disagree on who is listed first; orient() fixes the sides
        if not c: self.unmatched[f"{date} {away}@{home}"] += 1; return None
        if start is not None and len(c) > 1: c = sorted(c, key=lambda e: abs((parse_ts(e['start']) - start).total_seconds()))
        return c[0]['event_id']


    def orient(self, ev, a, h):
        """(away, home) in the ESPN event's own order, whatever order the feed used."""
        e = self.sched.get(ev)
        return (e['away'], e['home']) if e and {e['away'], e['home']} == {a, h} else (a, h)


# ----------------------------------------------------------------- ticks ----
ROWS = []; UNMATCHED = collections.Counter()


def tick(event_id, market, side, venue, feed, line=None, participant=None, player=None, american=None, bid=None, ask=None, last=None, vol=None,
         limit=None, flags=None, extra=None):
    if not event_id: return
    r = dict(ts=TS, event_id=event_id, market=market, side=side, venue=venue, feed=feed)
    for k, v in (('line', line), ('participant', participant), ('player', player), ('american', american), ('bid', bid), ('ask', ask), ('last', last),
                 ('vol', vol), ('limit', limit), ('flags', flags), ('extra', extra)):
        if v is not None and v != [] and v != {}: r[k] = v
    ROWS.append(r)


def pair(event_id, market, yes_side, no_side, venue, feed, bid, ask, last=None, vol=None, line=None, line_no=None, p_yes=None, p_no=None, player=None, extra=None):
    """Exchange yes/no as two rows (the complement side is the mirror of the book)."""
    flags = []
    if extra and 'ticker' in extra: extra = {**extra, 'yes': yes_side}     # Kalshi: which side the yes contract is, for the trade tape
    if bid is not None and ask is not None and ask - bid > 0.04: flags.append('wide')
    if (bid or 0) <= 0 or (ask or 1) >= 1: flags.append('oneside')
    tick(event_id, market, yes_side, venue, feed, line=line, participant=p_yes, player=player, bid=bid, ask=ask, last=last, vol=vol, flags=flags or None, extra=extra)
    nb = (1 - ask) if ask is not None else None; na = (1 - bid) if bid is not None else None
    tick(event_id, market, no_side, venue, feed, line=line if line_no is None else line_no, participant=p_no, player=player, bid=nb, ask=na,
         last=(1 - last) if last else None, vol=vol, flags=flags or None, extra=extra)


# ----------------------------------------------------------------- Pinnacle ----
def pinnacle(M):
    pm = g(f"{PIN}/leagues/{CFG['pinnacle']}/matchups?brandId=0") or []; pk = g(f"{PIN}/leagues/{CFG['pinnacle']}/markets/straight") or []
    km = collections.defaultdict(list)
    for k in pk: km[k['matchupId']].append(k)
    games = {}; n = 0
    for m in pm:
        if m.get('type') != 'matchup' or len(m.get('participants', [])) != 2: continue
        al = {p.get('alignment'): p['name'] for p in m['participants']}
        a, h = M.teams.code(al.get('away')), M.teams.code(al.get('home'))
        if not (a and h): continue
        st = parse_ts(m['startTime']); ev = M.match(et_date(st), a, h, st)
        if not ev: continue
        pin_home, pin_away = h, a; a, h = M.orient(ev, a, h)
        games[m['id']] = (ev, a, h)
        for k in km[m['id']]:
            per = CFG['pin_period'].get(k.get('period'))
            if per is None or k.get('status') != 'open' or k.get('isAlternate'): continue
            lim = next((l['amount'] for l in k.get('limits') or [] if l['type'] == 'maxRiskStake'), None)
            P = {x['designation']: x for x in k['prices']}; typ = k.get('type')
            if typ == 'moneyline' and 'home' in P and 'away' in P:
                fl = ['threeway'] if 'draw' in P else None
                s_home = 'home' if pin_home == h else 'away'; s_away = 'away' if s_home == 'home' else 'home'   # Pinnacle's alignment vs the ESPN event's
                tick(ev, per + 'ml', s_away, 'Pinnacle', 'pinnacle_guest', participant=pin_away, american=P['away']['price'], limit=lim, flags=fl)
                tick(ev, per + 'ml', s_home, 'Pinnacle', 'pinnacle_guest', participant=pin_home, american=P['home']['price'], limit=lim, flags=fl)
                if 'draw' in P: tick(ev, per + 'ml', 'draw', 'Pinnacle', 'pinnacle_guest', american=P['draw']['price'], limit=lim, flags=fl)
            elif typ == 'spread' and 'home' in P:
                lh = P['home'].get('points')
                tick(ev, per + 'spread', 'home', 'Pinnacle', 'pinnacle_guest', line=lh, participant=h, american=P['home']['price'], limit=lim)
                tick(ev, per + 'spread', 'away', 'Pinnacle', 'pinnacle_guest', line=-lh, participant=a, american=P['away']['price'], limit=lim)
            elif typ in ('total', 'team_total') and 'over' in P:
                mk = per + ('total' if typ == 'total' else 'tt_' + k.get('side', '')); part = None if typ == 'total' else (h if k.get('side') == 'home' else a)
                tick(ev, mk, 'over', 'Pinnacle', 'pinnacle_guest', line=P['over'].get('points'), participant=part, american=P['over']['price'], limit=lim)
                tick(ev, mk, 'under', 'Pinnacle', 'pinnacle_guest', line=P['under'].get('points'), participant=part, american=P['under']['price'], limit=lim)
            n += 1
    # fight props (UFC): yes/no specials -> prop_<STAT> with line 0.5, over = yes. Method of victory per fighter, inside the distance,
    # goes the distance, fight starts round N. Graded from the ESPN finish (results_espn.pull_fight).
    npr = 0
    if CFG.get('fights') and not FAST:
        for m in pm:
            if m.get('type') != 'special' or (m.get('special') or {}).get('category') != 'Fight Props': continue
            par = games.get((m.get('parent') or {}).get('id'))
            if not par: continue
            d = m['special']['description']; key = S.fight_prop(d)
            if not key: continue
            stat, name = key; side_of = {p['id']: p['name'].lower() for p in m['participants']}
            for k in km[m['id']]:
                pr = {side_of.get(x['participantId']): x for x in k['prices']}
                if 'yes' in pr and 'no' in pr:
                    lim = next((l['amount'] for l in k.get('limits') or [] if l['type'] == 'maxRiskStake'), None)
                    pk = M.fighter_key(par[0], name) if name else '_fight'
                    tick(par[0], f'prop_{stat}', 'over', 'Pinnacle', 'pinnacle_guest', line=0.5, participant=pk, player=name or 'Fight', american=pr['yes']['price'], limit=lim)
                    tick(par[0], f'prop_{stat}', 'under', 'Pinnacle', 'pinnacle_guest', line=0.5, participant=pk, player=name or 'Fight', american=pr['no']['price'], limit=lim)
                    npr += 1
        return n, npr
    # player props (specials) hang off the parent matchup
    pmap = S.PIN_PROPS[SPORT]
    for m in ([] if FAST else pm):
        if m.get('type') != 'special' or (m.get('special') or {}).get('category') != 'Player Props': continue
        par = games.get((m.get('parent') or {}).get('id'))
        if not par: continue
        d = m['special']['description']; key = next((k for k in pmap if d.endswith('(' + k + ')') or d.endswith(k)), None)
        if not key: continue
        name = re.sub(r'\s*\(' + re.escape(key) + r'\)\s*$', '', d).replace(key, '').strip(' -'); stat = pmap[key]
        name = re.sub(r'\s+(Total|\(.*\))\s*$', '', name).strip()     # Pinnacle: 'Brock Bowers Total Receiving Yards' -> 'Brock Bowers'
        side = {p['id']: p['name'].lower() for p in m['participants']}
        for k in km[m['id']]:
            pr = {side.get(x['participantId']): x for x in k['prices']}
            if 'over' in pr and 'under' in pr:
                lim = next((l['amount'] for l in k.get('limits') or [] if l['type'] == 'maxRiskStake'), None)
                for s in ('over', 'under'):
                    tick(par[0], f'prop_{stat}', s, 'Pinnacle', 'pinnacle_guest', line=pr[s].get('points'), participant=player_key(name), player=name,
                         american=pr[s]['price'], limit=lim)
                npr += 1
    return n, npr


# ----------------------------------------------------------------- Kalshi ----
def kalshi(M):
    pre = CFG['kalshi']; n = 0; npr = 0; codes = M.teams.codes; fix = {**S.CODE_FIX[SPORT], **(CFG.get('code_fix') or {})}
    def walk(series):
        cur = ''
        while True:
            x = g(f"{KAPI}/markets?series_ticker={series}&status=open&limit=1000" + (f"&cursor={cur}" if cur else ''))
            for m in x.get('markets', []): yield m
            cur = x.get('cursor')
            if not cur or not x.get('markets'): break
    def resolve(evt):
        p = S.kalshi_event(evt)
        if not p: return None
        date, blob = p; sp = S.split_codes(blob, codes, fix)
        if not sp: return None
        a, h = sp
        if CFG.get('kalshi_home_first'): a, h = h, a          # soccer and UFC tickers list the home side first
        ev = M.match(date, a, h)
        if not ev: return None
        a, h = M.orient(ev, a, h)
        return ev, a, h
    for suf, (mkt, per) in (CFG.get('kalshi_game') or S.KALSHI_GAME).items():
        if per and per.strip('_') not in CFG['periods']: continue
        for m in walk(pre + suf):
            evt = m['event_ticker'].split('-', 1)[1]; r = resolve(evt)
            if not r: continue
            ev, a, h = r; tail = m['ticker'].rsplit('-', 1)[1]
            bid, ask, last, vol = float(m.get('yes_bid_dollars') or 0) or None, float(m.get('yes_ask_dollars') or 0) or None, float(m.get('last_price_dollars') or 0) or None, float(m.get('volume_fp') or 0)
            if bid is not None and ask is not None and ask < bid: continue
            strike = m.get('floor_strike')
            kx = {'ticker': m['ticker']}
            if mkt == 'ml':
                if tail == 'TIE': tick(ev, per + 'ml', 'draw', 'Kalshi', 'kalshi_api', bid=bid, ask=ask, last=last, vol=vol, flags=['threeway'], extra={**kx, 'yes': 'draw'}); continue
                t = fix.get(tail, tail)
                if t not in (a, h): continue
                tick(ev, per + 'ml', 'home' if t == h else 'away', 'Kalshi', 'kalshi_api', participant=t, bid=bid, ask=ask, last=last, vol=vol,
                     flags=(['wide'] if bid and ask and ask - bid > 0.04 else None), extra={**kx, 'yes': 'home' if t == h else 'away'})
            elif mkt == 'total':
                if strike is None: continue
                pair(ev, per + 'total', 'over', 'under', 'Kalshi', 'kalshi_api', bid, ask, last, vol, line=float(strike), extra=kx)
            elif mkt == 'spread':
                if strike is None: continue
                t = fix.get(re.sub(r'\d+$', '', tail), re.sub(r'\d+$', '', tail))
                if t not in (a, h): continue
                yes = 'home' if t == h else 'away'; other = a if yes == 'home' else h
                pair(ev, per + 'spread', yes, 'away' if yes == 'home' else 'home', 'Kalshi', 'kalshi_api', bid, ask, last, vol, line=-float(strike), line_no=float(strike), p_yes=t, p_no=other, extra=kx)
            elif mkt == 'tt':
                if strike is None: continue
                t = fix.get(re.sub(r'\d+$', '', tail), re.sub(r'\d+$', '', tail))
                if t not in (a, h): continue
                pair(ev, per + ('tt_home' if t == h else 'tt_away'), 'over', 'under', 'Kalshi', 'kalshi_api', bid, ask, last, vol, line=float(strike), p_yes=t, p_no=t, extra=kx)
            n += 1
    if CFG.get('fights') and not FAST:
        for suf, kind in (('MOV', 'mov'), ('DISTANCE', 'dist'), ('ROUNDS', 'rounds')):
            for m in walk(pre + suf):
                evt = m['event_ticker'].split('-', 1)[1]; r = resolve(evt)
                if not r: continue
                bid, ask, last, vol = float(m.get('yes_bid_dollars') or 0) or None, float(m.get('yes_ask_dollars') or 0) or None, float(m.get('last_price_dollars') or 0) or None, float(m.get('volume_fp') or 0)
                if bid is None and ask is None: continue
                kx = {'ticker': m['ticker']}; tail = m['ticker'].rsplit('-', 1)[1]
                if kind == 'mov':
                    sub = m.get('yes_sub_title') or ''; mm_ = re.match(r'^(.*?)\s+by\s+(Submission|KO/TKO/DQ|Decision)$', sub)
                    if not mm_: continue
                    name = mm_.group(1).strip(); stat = {'Submission': 'MOV_SUB', 'KO/TKO/DQ': 'MOV_KO', 'Decision': 'MOV_DEC'}[mm_.group(2)]
                    pk = M.fighter_key(r[0], name)
                    pair(r[0], f'prop_{stat}', 'over', 'under', 'Kalshi', 'kalshi_api', bid, ask, last, vol, line=0.5, p_yes=pk, p_no=pk, player=name, extra=kx)
                elif kind == 'dist':
                    pair(r[0], 'prop_DIST', 'over', 'under', 'Kalshi', 'kalshi_api', bid, ask, last, vol, line=0.5, p_yes='_fight', p_no='_fight', player='Fight', extra=kx)
                else:   # 'fight ends before round N' = no to 'fight starts round N'
                    if not tail.isdigit(): continue
                    pair(r[0], f'prop_STARTR{tail}', 'under', 'over', 'Kalshi', 'kalshi_api', bid, ask, last, vol, line=0.5, p_yes='_fight', p_no='_fight', player='Fight', extra=kx)
                npr += 1
    for suf, stat in ({} if FAST else S.KALSHI_PROPS[SPORT]).items():
        for m in walk(pre + suf):
            evt = m['event_ticker'].split('-', 1)[1]; r = resolve(evt)
            if not r or m.get('floor_strike') is None: continue
            name = (m.get('yes_sub_title') or m.get('title') or '').split(':')[0].strip()
            if not name: continue
            bid, ask, last, vol = float(m.get('yes_bid_dollars') or 0) or None, float(m.get('yes_ask_dollars') or 0) or None, float(m.get('last_price_dollars') or 0) or None, float(m.get('volume_fp') or 0)
            if bid is None and ask is None: continue
            pair(r[0], f'prop_{stat}', 'over', 'under', 'Kalshi', 'kalshi_api', bid, ask, last, vol, line=float(m['floor_strike']), p_yes=player_key(name), p_no=player_key(name), player=name)
            npr += 1
    return n, npr


# ----------------------------------------------------------------- Action Network ----
def action_network(M):
    n = 0; fix = S.CODE_FIX[SPORT]
    for d in range(0, CFG['horizon_days'] + 1):
        day = (et_date(NOW) + dt.timedelta(days=d)).strftime('%Y%m%d')
        x = g(f"https://api.actionnetwork.com/web/v2/scoreboard/{CFG['an']}?bookIds={','.join(AN_BOOKS)}&date={day}&periods={','.join(CFG['an_period'])}")
        for gm in x.get('games', []):
            tm = {t['id']: M.teams.code(t.get('abbr')) or M.teams.code(t.get('full_name')) for t in gm.get('teams', [])}
            a, h = tm.get(gm['away_team_id']), tm.get(gm['home_team_id'])
            st = parse_ts(gm['start_time'].replace('.000Z', 'Z')); ev = M.match(et_date(st), a, h, st)
            if not ev: continue
            for bid_, per_m in (gm.get('markets') or {}).items():
                venue = AN_BOOKS.get(bid_)
                if not venue: continue
                if venue == 'Fanatics' and CFG.get('threeway'): continue   # AN's Fanatics soccer feed has home and away swapped (verified 10/29: BAR +1800 at home); not logged rather than guessed
                for per, mk in per_m.items():
                    pfx = CFG['an_period'].get(per)
                    if pfx is None: continue
                    for typ, outs in mk.items():
                        for o in outs:
                            if o.get('is_live') or o.get('is_alt_market') or o.get('odds') is None: continue
                            side = 'away' if o.get('team_id') == gm['away_team_id'] else ('home' if o.get('team_id') == gm['home_team_id'] else o.get('side'))
                            bi = o.get('bet_info') or {}
                            extra = {'tickets_pct': (bi.get('tickets') or {}).get('percent'), 'money_pct': (bi.get('money') or {}).get('percent')} if venue == 'AN_Consensus' else None
                            if extra and all(v is None for v in extra.values()): extra = None
                            if typ == 'moneyline':
                                if side not in ('home', 'away', 'draw'): continue
                                tick(ev, pfx + 'ml', side, venue, 'action_network', participant=None if side == 'draw' else (h if side == 'home' else a), american=o['odds'], extra=extra,
                                     flags=['threeway'] if CFG.get('threeway') else None)
                            elif typ == 'total': tick(ev, pfx + 'total', o['side'], venue, 'action_network', line=o.get('value'), american=o['odds'], extra=extra)
                            elif typ == 'spread': tick(ev, pfx + 'spread', side, venue, 'action_network', line=o.get('value'), participant=h if side == 'home' else a, american=o['odds'], extra=extra)
                            elif typ == 'core_bet_type_6_team_score' and side in ('home', 'away'):
                                tick(ev, pfx + 'tt_' + side, o['side'], venue, 'action_network', line=o.get('value'), participant=h if side == 'home' else a, american=o['odds'])
            n += 1
    return n


# ----------------------------------------------------------------- Novig ----
def novig(M):
    """Signed when NOVIG_* secrets exist (per-key throttle; the public API 429s shared CI addresses), public otherwise.
    Best bid + size for every outcome comes from the markets listing (one call per event); full books (depth within 3c) only for the
    game markets, which is where the depth rule matters."""
    try:
        from sharp import novig_auth as NA; signed = NA.available()
    except Exception: signed = False
    def nv(path, query=''):
        if signed:
            st, r = NA.request('GET', path, query, timeout=30); STATS['novig_signed'] += 1
            if st == 429: time.sleep(2); st, r = NA.request('GET', path, query, timeout=30)
            return r if st == 200 else {}
        return g(f"{NOV}{path}" + (('?' + query) if query else ''))
    evs = [e for e in (nv('/v3/catalog/events', f"league={urllib.parse.quote(CFG['novig'])}&status=OPEN_PREGAME&limit=500") or {}).get('items', [])
           if '@' in e.get('description', '') and 0 < e['startsTs'] / 1000 - NOW.timestamp() < CFG['horizon_days'] * 86400]
    types = set(S.NOVIG_GAME) | (set() if FAST else set(S.NOVIG_PROPS[SPORT])); todo = []
    for e in evs:
        if over_budget(): break
        aw, hm = [s_.strip() for s_ in e['description'].split('@', 1)]; a, h = M.teams.code(aw), M.teams.code(hm)
        st = parse_ts(e['startsTs']); ev = M.match(et_date(st), a, h, st)
        if not ev: continue
        a, h = M.orient(ev, a, h)
        for m in (nv('/v3/catalog/markets', f"event={e['eventId']}&limit=2000") or {}).get('items', []):
            if m.get('marketType') in types and m.get('status') == 'OPEN': todo.append((ev, a, h, m))
    def best_from_listing(m):
        out = {}
        for o in m.get('outcomes', []):
            b = o.get('bid')
            if b and b.get('price') is not None: out[o['name']] = dict(best=float(b['price']), qty_best=int(b.get('qty') or 0), qty_3c=None)
        return out
    def snap(x):
        ev, a, h, m = x
        if FAST or m['marketType'] not in S.NOVIG_GAME or over_budget(): return ev, a, h, m, best_from_listing(m)
        b = (nv(f"/v3/catalog/markets/{m['marketId']}/book", 'depth=10') or {}).get('orders', {})
        if not b: return ev, a, h, m, best_from_listing(m)
        oc = {o['outcomeId']: o['name'] for o in m['outcomes']}; best = {}
        for oid, L in b.items():
            ps = [(float(o['price']), o['qty']) for o in L]
            if not ps: continue
            bp = max(p for p, _ in ps)
            best[oc.get(oid, oid)] = dict(best=bp, qty_best=sum(q for p, q in ps if p == bp), qty_3c=sum(q for p, q in ps if p >= bp - 0.03))
        return ev, a, h, m, best
    with cf.ThreadPoolExecutor(4 if signed else 6) as ex: out = list(ex.map(snap, todo))
    n = 0
    for ev, a, h, m, best in out:
        if not best: continue
        typ = m['marketType']; strike = float(m['strike']) if m.get('strike') not in (None, '') else None
        names = list(best.keys())
        def two(side_of):
            """side_of: name -> side; emits both sides with ask = 1 - other side's bid."""
            nonlocal n
            sides = {side_of(nm): nm for nm in names if side_of(nm)}
            if len(sides) != 2: return
            bids = {s_: best[nm]['best'] for s_, nm in sides.items()}; flags = ['wide'] if 1 - sum(bids.values()) > 0.04 else None
            for s_, nm in sides.items():
                other = [t for t in sides if t != s_][0]; o = best[nm]
                q3 = o['qty_3c'] if o['qty_3c'] is not None else o['qty_best']
                ex_ = dict(qty_best=o['qty_best'], qty_3c=o['qty_3c'], depth3=round(q3 * o['best'] / 100, 2), depth_src='book' if o['qty_3c'] is not None else 'best', market_id=m['marketId'])   # 1c contracts -> dollars
                yield s_, bids[s_], 1 - bids[other], flags, ex_
            n += 1
        if typ in S.NOVIG_GAME:
            mkt, per = S.NOVIG_GAME[typ]
            if mkt in ('ml3', 'draw'):      # soccer: Yes/No market per outcome; Yes bid = price of the outcome, ask = 1 - No bid
                if mkt == 'draw': side = 'draw'; part = None
                else:
                    t = M.teams.code(re.sub(r'\s+MONEYLINE_3_WAY_WIN$', '', m.get('description', '')).strip())
                    if t not in (a, h): continue
                    side = 'home' if t == h else 'away'; part = t
                yes, no = best.get('Yes'), best.get('No')
                if not yes: continue
                q3 = yes['qty_3c'] if yes['qty_3c'] is not None else yes['qty_best']
                tick(ev, per + 'ml', side, 'Novig', 'novig_api', participant=part, bid=yes['best'], ask=(1 - no['best']) if no else None, flags=['threeway'],
                     extra=dict(qty_best=yes['qty_best'], qty_3c=yes['qty_3c'], depth3=round(q3 * yes['best'] / 100, 2), depth_src='book' if yes['qty_3c'] is not None else 'best', market_id=m['marketId']))
                n += 1
            elif mkt == 'ml':
                for s_, bid, ask, flags, ex_ in two(lambda nm: 'home' if M.teams.code(nm) == h else ('away' if M.teams.code(nm) == a else None)):
                    tick(ev, per + 'ml', s_, 'Novig', 'novig_api', participant=h if s_ == 'home' else a, bid=bid, ask=ask, flags=flags, extra=ex_)
            elif mkt == 'spread':
                lines = {}
                def sd(nm):
                    mm = re.match(r'^(.*?)\s+([+-]?\d+\.?\d*)$', nm)
                    if not mm: return None
                    t = M.teams.code(mm.group(1)); s_ = 'home' if t == h else ('away' if t == a else None)
                    if s_: lines[s_] = float(mm.group(2))
                    return s_
                for s_, bid, ask, flags, ex_ in two(sd):
                    tick(ev, per + 'spread', s_, 'Novig', 'novig_api', line=lines.get(s_), participant=h if s_ == 'home' else a, bid=bid, ask=ask, flags=flags, extra=ex_)
            elif mkt in ('total', 'tt'):
                mk = per + 'total'; part = None
                if mkt == 'tt':
                    t = M.teams.code(re.sub(r'\s+t?\d+\.?\d*$', '', m.get('description', '')).split('@')[-1].strip()) or M.teams.code(m.get('description', '').split()[0])
                    if t not in (a, h): continue
                    mk = per + ('tt_home' if t == h else 'tt_away'); part = t
                for s_, bid, ask, flags, ex_ in two(lambda nm: 'over' if nm.lower().startswith('over') else ('under' if nm.lower().startswith('under') else None)):
                    tick(ev, mk, s_, 'Novig', 'novig_api', line=strike, participant=part, bid=bid, ask=ask, flags=flags, extra=ex_)
        else:
            stat = S.NOVIG_PROPS[SPORT][typ]; desc = m.get('description', '')
            mm = re.match(r'^(.*?)\s+[ou]?\d+\.?\d*(\s+[A-Z_]+)?$', desc); name = (mm.group(1) if mm else desc).strip()   # 'Bo Melton 14.5 RECEIVING_YARDS'
            for s_, bid, ask, flags, ex_ in two(lambda nm: 'over' if nm.lower().startswith('over') else ('under' if nm.lower().startswith('under') else None)):
                tick(ev, f'prop_{stat}', s_, 'Novig', 'novig_api', line=strike, participant=player_key(name), player=name, bid=bid, ask=ask, flags=flags, extra=ex_)
    return len(evs), n


PROP_LADDER = 3   # prop strikes kept per venue x player x stat x side: the ones whose price is nearest 50% (the main line and its neighbours)


def trim(rows):
    """Dedupe (AN's NFL scoreboard returns the whole week for every date) and keep only the prop strikes near the main line."""
    seen = set(); out = []; props = collections.defaultdict(list)
    for r in rows:
        k = (r['event_id'], r['venue'], r['market'], r['side'], r.get('line'), r.get('participant'))
        if k in seen: continue
        seen.add(k)
        if r['market'].startswith('prop_'): props[(r['event_id'], r['venue'], r['market'], r['side'], r.get('participant'))].append(r)
        else: out.append(r)
    for L in props.values():
        def p(r):
            if r.get('ask') is not None: return r['ask']
            if r.get('american') is not None: return 1 / (1 + r['american'] / 100) if r['american'] > 0 else 1 / (1 + 100 / -r['american'])
            return 0.5
        L.sort(key=lambda r: abs(p(r) - 0.5)); out.extend(L[:PROP_LADDER])
    return out


def main():
    import gzip
    counts = collections.Counter(); errs = {}
    leagues = CFG.get('leagues') or {'_': {}}
    for lk, lg in leagues.items():
        if over_budget(): break
        CFG.update(lg); CFG['league_key'] = None if lk == '_' else lk
        sched = espn_schedule(); M = Matcher(sched)
        for name, fn in (('pinnacle', pinnacle), ('kalshi', kalshi), ('action_network', action_network), ('novig', novig)):
            if CFG.get({'pinnacle': 'pinnacle', 'kalshi': 'kalshi', 'action_network': 'an', 'novig': 'novig'}[name]) is None: continue
            t = time.time()
            try:
                c = fn(M); counts[name] += (c if isinstance(c, int) else sum(x for x in c if isinstance(x, int)))
            except Exception as e: errs[f'{name}:{lk}'] = f'{type(e).__name__}: {e}'
            counts[name + '_s'] += round(time.time() - t)
        if M.unmatched: UNMATCHED.update(M.unmatched)
    counts = dict(counts); counts.update(errs); M = type('M', (), {'unmatched': UNMATCHED})()
    rows = trim(ROWS)
    with gzip.open(os.path.join(TD, f"{et_date(NOW).isoformat()}.jsonl.gz"), 'at') as f:
        for r in rows: f.write(json.dumps(r, separators=(',', ':')) + '\n')
    byv = collections.Counter(r['venue'] for r in rows); nev = len({r['event_id'] for r in rows})
    print(f"[lines {SPORT}] {len(rows)} ticks ({len(ROWS)} raw) on {nev} events in {round(time.time() - T0)}s; {dict(byv)}; sources {counts}; http {dict(STATS)}"
          + (f"; unmatched {dict(M.unmatched.most_common(5))}" if M.unmatched else ''))


if __name__ == '__main__':
    main()
