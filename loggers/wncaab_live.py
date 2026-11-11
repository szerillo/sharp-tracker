#!/usr/bin/env python3
"""Women's college basketball spreads, live, for two PAPER rules (Kirk for Sean, 11/10; tests in docs/wncaab_mma_2026-11-09.md, rebuilt in
sharp/wncaab_replay.py). Nothing is placed; every row is graded at 0 units.
  wncaab_dog_7_10: the dog is +7 to +10 at the close (median across books)            replay 53-38-1, +11.4%, both seasons positive
  wncaab_move_follow: the median spread moved 1+ point from our first look to the close; take the side it moved toward
                                                                                      replay 76-57-1, +9.6%, 2025-26 negative
The live feed (loggers/lines.py) does not carry this sport, so this pulls The Odds API directly: one call per run, spreads only, eight
US books in one request (1 credit; BetMGM is not requested). Self-throttled to one pull every 18 minutes, and it stops if the account
falls under FLOOR credits. The key is read from ODDS_API_KEY and never printed.
Per pull: a compact snapshot appended to data/wncaab/snaps/<day>.jsonl.gz (the same shape as the history file); a game's first snapshot
is its open (data/wncaab/open.json). A rule fires once per game, on the first pull inside the last FIRE_MIN minutes before the start.
The line is the median home spread across the books (as in the replay); the bet is priced at the best of Sean's books on that number
(DK, FD, Caesars, BetRivers, Fanatics, theScore/ESPN Bet). The best price anywhere is stored too.
Grading: ESPN final scores (womens-college-basketball scoreboard), matched by both team names and a start within 6 hours.
Writes data/state/wncaab_paper.jsonl (one row per fire, `won` filled in when final) and data/state/wncaab_record.json.
Usage: ODDS_API_KEY=... python3 loggers/wncaab_live.py [--grade-only]"""
import os, sys, json, gzip, time, statistics, collections, unicodedata, re, urllib.request, urllib.error, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
D = os.path.join(ROOT, 'data', 'wncaab'); SNAPS = os.path.join(D, 'snaps'); OPEN = os.path.join(D, 'open.json'); STATE = os.path.join(D, 'state.json')
PAPER = os.path.join(ROOT, 'data', 'state', 'wncaab_paper.jsonl'); REC = os.path.join(ROOT, 'data', 'state', 'wncaab_record.json')
API = 'https://api.the-odds-api.com/v4/sports/basketball_wncaab/odds'
BOOKS = 'draftkings,fanduel,williamhill_us,betrivers,fanatics,espnbet,betonlineag,lowvig'      # eight books = one credit
SEAN = {'draftkings': 'DK', 'fanduel': 'FD', 'williamhill_us': 'Caesars', 'betrivers': 'BetRivers', 'fanatics': 'Fanatics', 'espnbet': 'theScore'}
SKIP = ('betmgm',)                                                                                 # never bettable, never in the median
FIRE_MIN, THROTTLE_MIN, FLOOR = 40, 18, 2_950_000
NOW = dt.datetime.now(dt.timezone.utc)


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
def iso(t): return t.strftime('%Y-%m-%dT%H:%M:%SZ')
def norm(s): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower())


def load(p, d):
    try: return json.load(open(p))
    except Exception: return d


def pull():
    key = os.environ.get('ODDS_API_KEY')
    if not key: print('[wncaab] no ODDS_API_KEY; pull skipped'); return None
    st = load(STATE, {})
    if st.get('last_pull') and (NOW - ts(st['last_pull'])).total_seconds() < THROTTLE_MIN * 60: print(f"[wncaab] pulled at {st['last_pull']}; next pull after {THROTTLE_MIN} minutes"); return None
    if st.get('remaining') is not None and st['remaining'] < FLOOR: print(f"[wncaab] Odds API credits {st['remaining']:,} under the {FLOOR:,} floor; pull skipped"); return None
    q = f'{API}?apiKey={key}&bookmakers={BOOKS}&markets=spreads&oddsFormat=decimal&dateFormat=iso'
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers={'User-Agent': 'sharp-tracker'}), timeout=40) as r:
                ev = json.load(r); rem = int(r.headers.get('x-requests-remaining') or 0); used = int(r.headers.get('x-requests-last') or 0); break
        except urllib.error.HTTPError as e: print(f'[wncaab] Odds API HTTP {e.code}'); return None          # never print the URL (it holds the key)
        except Exception: time.sleep(3 * (i + 1))
    else: print('[wncaab] Odds API unreachable'); return None
    json.dump(dict(st, last_pull=iso(NOW), remaining=rem, last_cost=used), open(STATE, 'w'))
    rows = []
    for e in ev:
        books = {}
        for b in e.get('bookmakers') or []:
            if b['key'] in SKIP: continue
            for m in b.get('markets') or []:
                if m.get('key') != 'spreads': continue
                o = {x.get('name'): x for x in m.get('outcomes') or []}
                h, a = o.get(e['home_team']), o.get(e['away_team'])
                if h and a and h.get('point') is not None: books[b['key']] = {'sp': [h['point'], h['price'], a['price']]}
        if books: rows.append(dict(t=iso(NOW), id=e['id'], sport='wncaab', start=e['commence_time'], home=e['home_team'], away=e['away_team'], books=books))
    os.makedirs(SNAPS, exist_ok=True)
    with gzip.open(os.path.join(SNAPS, f'{NOW:%Y-%m-%d}.jsonl.gz'), 'at') as f:
        for r in rows: f.write(json.dumps(r, separators=(',', ':')) + '\n')
    print(f'[wncaab] {len(ev)} games listed, {len(rows)} with spreads; cost {used} credit(s), {rem:,} left')
    return rows


def med(books):
    L = {b: v['sp'] for b, v in books.items() if b not in SKIP and v.get('sp')}
    return (statistics.median(x[0] for x in L.values()), L) if L else (None, {})


def fire(rows):
    O = load(OPEN, {}); fired = set()
    if os.path.exists(PAPER):
        for l in open(PAPER):
            try: fired.add(json.loads(l)['key'])
            except Exception: pass
    new = []
    for r in rows:
        m, L = med(r['books'])
        if m is None: continue
        if r['id'] not in O: O[r['id']] = dict(t=r['t'], line=m, n=len(L))
        mins = (ts(r['start']) - NOW).total_seconds() / 60
        if not 0 < mins <= FIRE_MIN or len(L) < 3: continue
        op = O[r['id']]['line']; mv = m - op; bets = []
        if abs(mv) >= 1 and O[r['id']]['t'] < r['t']: bets.append(('wncaab_move_follow', 'home' if mv < 0 else 'away'))
        dog = 'home' if m > 0 else 'away' if m < 0 else None
        if dog and 7 <= abs(m) <= 10: bets.append(('wncaab_dog_7_10', dog))
        for rule, side in bets:
            k = f"{rule}|{r['id']}"
            if k in fired: continue
            at = [(v[1] if side == 'home' else v[2], b) for b, v in L.items() if abs(v[0] - m) < 1e-9]
            mine = [z for z in at if z[1] in SEAN]
            if not mine: continue                                   # none of Sean's books on the median number: not bettable, not logged
            dec, bk = max(mine); anyb = max(at)
            line = m if side == 'home' else -m; team = r['home'] if side == 'home' else r['away']
            new.append(dict(key=k, rule=rule, sport='wncaab', event_id=r['id'], game=f"{r['away']} @ {r['home']}", home=r['home'], away=r['away'], start=r['start'],
                            market='spread', side=side, line=line, open_line=op if side == 'home' else -op, books=len(L), book=SEAN[bk], dec=dec, price=round(1 / dec, 4),
                            best_any=anyb[0], best_any_book=anyb[1], bet=f"{team} {'+' if line > 0 else ''}{line:g}", flagged=r['t']))
            fired.add(k)
    json.dump(O, open(OPEN, 'w'), separators=(',', ':'))
    if new:
        with open(PAPER, 'a') as f:
            for x in new: f.write(json.dumps(x, separators=(',', ':')) + '\n')
    print(f'[wncaab] {len(new)} paper bets logged ({collections.Counter(x["rule"] for x in new)})')


def espn(day):
    u = f'https://site.api.espn.com/apis/site/v2/sports/basketball/womens-college-basketball/scoreboard?dates={day:%Y%m%d}&groups=50&limit=500'
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=30) as r: return json.load(r).get('events') or []
        except Exception: time.sleep(2 + i)
    return []


def grade():
    if not os.path.exists(PAPER): return
    R = [json.loads(l) for l in open(PAPER) if l.strip()]
    todo = [x for x in R if x.get('won') is None and (NOW - ts(x['start'])).total_seconds() > 2.5 * 3600]
    days = sorted({(ts(x['start']) - dt.timedelta(hours=5)).date() for x in todo})          # ESPN's day is US Eastern
    G = []
    for d in days: G += espn(d)
    def names(t): return {norm(t.get(k) or '') for k in ('displayName', 'shortDisplayName', 'name', 'location')} | {norm((t.get('location') or '') + ' ' + (t.get('name') or ''))} - {''}
    def same(a, S): n = norm(a); return any(n == s or (len(s) >= 6 and (s in n or n in s)) for s in S)
    for x in todo:
        for e in G:
            c = (e.get('competitions') or [{}])[0]
            if not (c.get('status') or {}).get('type', {}).get('completed'): continue
            T = {t['homeAway']: t for t in c.get('competitors') or []}
            if 'home' not in T or 'away' not in T or abs((ts(e['date'].replace('Z', ':00Z') if len(e['date']) == 17 else e['date']) - ts(x['start'])).total_seconds()) > 6 * 3600: continue
            if not (same(x['home'], names(T['home']['team'])) and same(x['away'], names(T['away']['team']))): continue
            hs, as_ = float(T['home']['score']), float(T['away']['score'])
            cov = ((hs - as_) if x['side'] == 'home' else (as_ - hs)) + x['line']
            x.update(won=1 if cov > 0 else 0 if cov < 0 else 0.5, home_score=hs, away_score=as_, espn=e['id']); break
    with open(PAPER + '.tmp', 'w') as f:
        for x in R: f.write(json.dumps(x, separators=(',', ':')) + '\n')
    os.replace(PAPER + '.tmp', PAPER)
    S = collections.defaultdict(lambda: dict(bets=0, w=0, l=0, p=0, units=0.0, open=0))
    for x in R:
        for k in ('all', x['rule']):
            s = S[k]; s['bets'] += 1
            if x.get('won') is None: s['open'] += 1
            elif x['won'] == 1: s['w'] += 1; s['units'] += x['dec'] - 1
            elif x['won'] == 0: s['l'] += 1; s['units'] -= 1
            else: s['p'] += 1
    out = {k: dict(v, units=round(v['units'], 2), roi=round(100 * v['units'] / (v['w'] + v['l']), 1) if v['w'] + v['l'] else None) for k, v in S.items()}
    json.dump(dict(updated=iso(NOW), note='paper, flat 1 unit at the logged price; 0 units on the board', rules=out), open(REC, 'w'), indent=0)
    print(f"[wncaab] graded: {out.get('all')}")


def main():
    os.makedirs(D, exist_ok=True)
    if '--grade-only' not in sys.argv:
        rows = pull()
        if rows: fire(rows)
    grade()


if __name__ == '__main__': main()
