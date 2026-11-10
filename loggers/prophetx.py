#!/usr/bin/env python3
"""ProphetX (Sean 11/10: "we can also test ProphetX"; third exchange for the offer scan and the maker tests). Keys come only from the
environment (GitHub secrets PROPHETX_KEY and, if set, PROPHETX_SECRET); nothing is printed or stored.
Two ways in, tried in this order:
  1. market-data key: the key alone as the Authorization header on /partner/affiliate/* (docs.prophetx.co, Market Data Integration)
  2. token pair: POST /partner/auth/login {access_key, secret_key} -> a session token, then /partner/mm/* (the trading API's read side)
Usage: python3 loggers/prophetx.py probe      # which way works, and the shape of what comes back (no prices stored)"""
import os, sys, json, time, urllib.request, urllib.parse, urllib.error
BASE = 'https://cash.api.prophetx.co/partner'
KEY = os.environ.get('PROPHETX_KEY') or ''; SEC = os.environ.get('PROPHETX_SECRET') or ''


def call(path, params=None, headers=None, body=None):
    u = BASE + path + ('?' + urllib.parse.urlencode(params, doseq=True) if params else '')
    h = {'User-Agent': 'sharp-tracker', 'Accept': 'application/json'}; h.update(headers or {})
    data = None
    if body is not None: data = json.dumps(body).encode(); h['Content-Type'] = 'application/json'
    try:
        with urllib.request.urlopen(urllib.request.Request(u, data=data, headers=h, method='POST' if body is not None else 'GET'), timeout=40) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try: msg = e.read().decode()[:300]
        except Exception: msg = ''
        return e.code, msg
    except Exception as e: return 0, f'{type(e).__name__}: {e}'


def shape(x, depth=0):
    if isinstance(x, dict): return {k: shape(v, depth + 1) for k, v in list(x.items())[:14]} if depth < 4 else '{...}'
    if isinstance(x, list): return [shape(x[0], depth + 1), f'... {len(x)} items'] if x else []
    return type(x).__name__ if not isinstance(x, (int, float)) or isinstance(x, bool) else x


def login():
    if not (KEY and SEC): return None
    st, d = call('/auth/login', body=dict(access_key=KEY, secret_key=SEC))
    tok = ((d.get('data') or {}).get('access_token') if isinstance(d, dict) else None)
    print(f'login with the key pair: HTTP {st}, token {"received" if tok else "not received"}' + ('' if tok else f' ({str(d)[:200]})'))
    return tok


def probe():
    print(f'key set: {bool(KEY)} (length {len(KEY)}); secret set: {bool(SEC)}')
    if not KEY: return
    ok = None
    st, d = call('/affiliate/get_tournaments', dict(has_active_events='true'), {'Authorization': KEY})
    print(f'market-data key on /affiliate/get_tournaments: HTTP {st}' + ('' if st == 200 else f' ({str(d)[:200]})'))
    if st == 200: ok = ('affiliate', {'Authorization': KEY})
    tok = login()
    if tok:
        st2, d2 = call('/mm/get_tournaments', dict(has_active_events='true'), {'Authorization': 'Bearer ' + tok})
        print(f'session token on /mm/get_tournaments: HTTP {st2}' + ('' if st2 == 200 else f' ({str(d2)[:200]})'))
        if st2 == 200 and not ok: ok = ('mm', {'Authorization': 'Bearer ' + tok}); d = d2
    if not ok: print('neither way worked'); return
    kind, H = ok; print('using:', kind)
    T = ((d.get('data') or {}).get('tournaments') or []) if isinstance(d, dict) else []
    print(f'{len(T)} tournaments with active events:', sorted({(t.get("sport") or {}).get("name") or "?" for t in T}))
    print('tournament shape:', json.dumps(shape(T[:1])))
    want = [t for t in T if any(k in (t.get('name') or '') for k in ('NBA', 'NFL', 'NHL', 'NCAA'))][:6]
    print('examples:', [(t.get('id'), t.get('name')) for t in want])
    for t in [t for t in want if t.get('name') in ('NBA', 'NFL', 'NHL')][:1]:
        st, e = call(f'/{kind}/get_sport_events', dict(tournament_id=t['id']), H)
        E = ((e.get('data') or {}).get('sport_events') or []) if isinstance(e, dict) else []
        print(f"{t.get('name')}: HTTP {st}, {len(E)} events; shape {json.dumps(shape(E[:1]))[:700]}")
        if E:
            ev = E[0]; eid = ev.get('event_id')
            for path in (f'/v4/{kind}/get_markets', f'/{kind}/get_markets'):
                st, m = call(path, dict(event_id=eid), H)
                M = m.get('data') if isinstance(m, dict) else None
                n = len(M) if isinstance(M, list) else len((M or {}).get('markets') or []) if isinstance(M, dict) else 0
                print(f"  {path} for {ev.get('name')}: HTTP {st}, {n} markets")
                if st == 200 and n:
                    L = M if isinstance(M, list) else M.get('markets')
                    print('  market types:', sorted({str(x.get('type')) for x in L})[:40])
                    print('  market shape:', json.dumps(shape(L[:1]))[:1500])
                    import collections
                    c = collections.Counter((x.get('type'), x.get('category_name'), x.get('sub_type'), x.get('status')) for x in L)
                    print('  kinds (type, category, sub_type, status):', c.most_common(40))
                    for want_ in ('moneyline', 'spread', 'total'):
                        x = next((x for x in L if x.get('type') == want_ and x.get('category_name') in (None, '', 'Game Lines', 'game', 'Game') or (x.get('type') == want_ and 'game' in str(x.get('category_name')).lower())), None) or next((x for x in L if x.get('type') == want_), None)
                        if x: print('  sample', want_, json.dumps({k: v for k, v in x.items() if k != 'selections'})[:400], '| selections:', json.dumps(x.get('selections'))[:1200])
                    x = next((x for x in L if 'player' in str(x.get('category_name')).lower() or 'prop' in str(x.get('category_name')).lower()), None)
                    if x: print('  sample prop', json.dumps({k: v for k, v in x.items() if k != 'selections'})[:400], '| selections:', json.dumps(x.get('selections'))[:900])
                    print('  event:', json.dumps(ev)[:700])
                    break
        time.sleep(0.5)


# ---------------------------------------------------------------------------------------------------------------------------------
# pull: pregame game lines (moneyline, spread, total) and first-half spreads and totals for the next 48 hours, written as tick rows
# (venue "ProphetX") to data/<sport>/ticks_px/<ET date>.jsonl.gz, a folder of its own so it never collides with the price job's files.
# ask = the best price a taker gets on that side (implied probability), bid = 1 - the other side's ask; extra.qty = size at the best price.
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TOUR = {'NBA': 'nba', 'NFL': 'nfl', 'NHL': 'nhl', 'NCAAF': 'cfb', 'NCAAB': 'cbb', 'NCAA Football': 'cfb', 'NCAA Basketball': 'cbb', 'NCAAM': 'cbb', 'College Football': 'cfb', 'College Basketball': 'cbb'}
SUB = {'moneyline': 'ml', 'spread': 'spread', 'total': 'total', 'first_half_spread': '1h_spread', 'first_half_total': '1h_total'}


# ProphetX prop sub_type (after "player_total_") -> our prop code, as the price job names them (data/<sport>/ticks)
PROP = {(None, 'points'): 'PTS', (None, 'rebounds'): 'REB', (None, 'assists'): 'AST', (None, 'points_rebounds_assists'): 'PRA', (None, 'points_rebounds'): 'PR', (None, 'points_assists'): 'PA',
        (None, 'rebounds_assists'): 'RA', (None, 'steals'): 'STL', (None, 'blocks'): 'BLK', (None, 'three_pointers_made'): '3PM', (None, 'shots_on_goal'): 'SOG', (None, 'shots'): 'SOG', (None, 'goals'): 'GOALS',
        (None, 'receiving_yards'): 'RECYDS', (None, 'receptions'): 'REC', (None, 'rushing_yards'): 'RUSHYDS', (None, 'rushing_attempts'): 'RUSHATT', (None, 'passing_yards'): 'PASSYDS',
        (None, 'passing_touchdowns'): 'PASSTD', (None, 'passing_attempts'): 'PASSATT', (None, 'passing_completions'): 'PASSCOMP', (None, 'interceptions'): 'INT', (None, 'interceptions_thrown'): 'INT',
        (None, 'rushing_receiving_yards'): 'RUSHRECYDS', (None, 'passing_rushing_yards'): 'PASSRUSHYDS'}


def pkey(name):
    """The price job's player key: lower case, no accents, punctuation to spaces, no Jr / Sr / II / III."""
    import re, unicodedata
    s = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower()
    return ' '.join(w for w in re.sub(r'[^a-z ]', ' ', s).split() if w not in ('jr', 'sr', 'ii', 'iii', 'iv'))


def imp(a): return 100.0 / (a + 100.0) if a > 0 else -a / (-a + 100.0)


def get(path, params, H):
    for i in range(5):
        st, d = call(path, params, H)
        if st == 429 or st == 0 or st >= 500: time.sleep(2 * (i + 1)); continue
        return st, d
    return st, d


def norm(s):
    import re, unicodedata
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower().replace('&', 'and')
    return re.sub(r'[^a-z0-9 ]', '', s).replace(' state', ' st').strip()


def pull():
    import gzip, datetime as dt, collections
    tok = login()
    if not tok: print('no session'); return
    H = {'Authorization': 'Bearer ' + tok}; now = dt.datetime.now(dt.timezone.utc); ts_ = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    st, d = get('/mm/get_tournaments', dict(has_active_events='true'), H)
    T = ((d.get('data') or {}).get('tournaments') or []) if isinstance(d, dict) else []
    print('tournaments:', sorted(t.get('name') for t in T))
    out = collections.defaultdict(list); stats = collections.Counter(); T0 = time.time(); shown_prop = False; unmapped = collections.Counter()
    for t in T:
        sp = TOUR.get(t.get('name'))
        if not sp: continue
        try: sched = json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json')))
        except Exception: continue
        S = [e for e in (sched.values() if isinstance(sched, dict) else sched) if isinstance(e, dict) and e.get('start')]
        # props are kept only at the lines Pinnacle quotes today (the offer scan can price nothing else); the full ladders were 25,000 rows a pull
        PL = set()
        for dd_ in {(now - dt.timedelta(hours=5)).strftime('%Y-%m-%d'), (now - dt.timedelta(hours=10)).strftime('%Y-%m-%d')}:
            fp = os.path.join(ROOT, 'data', sp, 'ticks', f'{dd_}.jsonl.gz')
            if not os.path.exists(fp): continue
            try:
                for l in gzip.open(fp, 'rt'):
                    if '"Pinnacle"' in l and '"prop_' in l:
                        try: x = json.loads(l); PL.add((str(x['event_id']), x['market'], x.get('participant'), x.get('line')))
                        except Exception: pass
            except Exception: pass
        def names(tm, abbr): return {norm(tm.get('displayName')), norm(tm.get('location')), norm(tm.get('shortDisplayName')), norm(abbr)} - {''}
        st, e = get('/mm/get_sport_events', dict(tournament_id=t['id']), H); time.sleep(0.4)
        E = ((e.get('data') or {}).get('sport_events') or []) if isinstance(e, dict) else []
        for ev in E:
            if time.time() - T0 > 420: stats['out of time'] += 1; continue
            try: start = dt.datetime.fromisoformat(ev['scheduled'].replace('Z', '+00:00'))
            except Exception: continue
            if ev.get('status') != 'not_started' or not (dt.timedelta(minutes=5) < start - now < dt.timedelta(hours=48)): continue
            comp = {c.get('side'): c for c in ev.get('competitors') or []}
            if 'home' not in comp or 'away' not in comp: continue
            hn = {norm(comp['home'].get('name')), norm(comp['home'].get('display_name')), norm(comp['home'].get('abbreviation'))}; an = {norm(comp['away'].get('name')), norm(comp['away'].get('display_name')), norm(comp['away'].get('abbreviation'))}
            def hit(px, tm, abbr):
                nm = names(tm, abbr); full = norm(tm.get('displayName'))
                return bool(px & nm) or any(p_ and (full.startswith(p_ + ' ') or p_.startswith(norm(tm.get('location')) + ' ')) for p_ in px if len(p_) > 3)
            M_ = [x for x in S if abs((dt.datetime.fromisoformat((x['start'] if len(x['start']) > 17 else x['start'].replace('Z', ':00Z')).replace('Z', '+00:00')) - start).total_seconds()) <= 6 * 3600
                  and hit(hn, x.get('home_team') or {}, x.get('home')) and hit(an, x.get('away_team') or {}, x.get('away'))]
            if len(M_) != 1: stats[f'{sp} no schedule match'] += 1; continue
            eid = str(M_[0]['event_id']); side_of = {comp['home'].get('id'): 'home', comp['away'].get('id'): 'away'}
            st, m = get('/v4/mm/get_markets', dict(event_id=ev['event_id']), H); time.sleep(0.35)
            L = m.get('data') if isinstance(m, dict) else None
            L = L if isinstance(L, list) else ((L or {}).get('markets') or [])
            if st != 200: stats[f'markets HTTP {st}'] += 1; continue
            stats[f'{sp} games'] += 1
            for mk in L:
                if not shown_prop and str(mk.get('sub_type', '')).startswith('player_total_points'):
                    shown_prop = True; print('prop sample:', json.dumps({k: v for k, v in mk.items() if k not in ('selections', 'market_strikes')})[:500], json.dumps((mk.get('market_strikes') or [mk])[0].get('selections'))[:700])
                st_ = mk.get('sub_type') or ''; our = SUB.get(st_); player = None
                if not our and st_.startswith('player_total_') and mk.get('type') == 'total':
                    # player props (11/10, Sean: "less seeded at ProphetX ... if we can seed stuff"): logged with empty sides too, so the offer
                    # scan can list books nobody has seeded. Player = the market name up to " Total ".
                    code = PROP.get((sp, st_[13:])) or PROP.get((None, st_[13:]))
                    if not code: unmapped[(sp, st_)] += 1; continue
                    our = 'prop_' + code; player = str(mk.get('name') or '').split(' Total ')[0].strip()
                    if not player: continue
                if not our or mk.get('status') != 'active': continue
                for grp_ in (mk.get('market_strikes') or [mk]):
                    sel = grp_.get('selections') or []
                    rows = []
                    for lv in sel:
                        lv = lv or []
                        if not lv: continue
                        live = [x for x in lv if x.get('price') is not None and (x.get('quantity') or 0) > 0]
                        x = live[0] if live else lv[0]
                        if our.endswith('total') or player: side = 'over' if str(x.get('name', '')).lower().startswith('over') else 'under' if str(x.get('name', '')).lower().startswith('under') else None; line = x.get('strike')
                        else: side = side_of.get(x.get('competitor_id')); line = x.get('strike') if our.endswith('spread') else None
                        if side is None: rows = []; break
                        rows.append((side, line, imp(float(x['price'])) if live else None, x))
                    if len(rows) != 2 or rows[0][0] == rows[1][0]: continue
                    if not player and (rows[0][2] is None or rows[1][2] is None): continue        # game lines: both sides quoted
                    if player and (eid, our, pkey(player), rows[0][1]) not in PL: stats['prop strikes off Pinnacle\'s line (not kept)'] += 1; continue
                    for i, (side, line, ask, x) in enumerate(rows):
                        oa = rows[1 - i][2]
                        r_ = dict(ts=ts_, sport=sp, event_id=eid, market=our, side=side, line=line, venue='ProphetX', bid=round(1 - oa, 4) if oa is not None else None, ask=round(ask, 4) if ask is not None else None,
                                  american=x['price'] if ask is not None else None,
                                  extra=dict(px_event=ev['event_id'], market_id=mk.get('id'), outcome_id=x.get('outcome_id'), strike_id=x.get('strike_id'), qty=x.get('quantity') if ask is not None else 0))
                        if player: r_['participant'] = pkey(player); r_['player'] = player
                        out[sp].append(r_); stats['prop rows' if player else 'rows'] += 1
                        if player and ask is None and oa is None: stats['prop sides with an empty book'] += 1
    etd = (now - dt.timedelta(hours=5)).strftime('%Y-%m-%d')
    for sp, R in out.items():
        dd = os.path.join(ROOT, 'data', sp, 'ticks_px'); os.makedirs(dd, exist_ok=True)
        with gzip.open(os.path.join(dd, f'{etd}.jsonl.gz'), 'at') as f:
            for r in R: f.write(json.dumps(r, separators=(',', ':')) + '\n')
    print('[prophetx]', dict(stats), f'{round(time.time() - T0)}s')
    if unmapped: print('[prophetx] prop types not mapped yet:', unmapped.most_common(40))


if __name__ == '__main__':
    if (sys.argv[1:] or ['probe'])[0] == 'pull': pull(); sys.exit(0)
    if (sys.argv[1:] or ['probe'])[0] == 'probe': probe()
