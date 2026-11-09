#!/usr/bin/env python3
"""Game lines (spread + total, compact rows) at fixed times before the start for the games in a props snapshot file (Sean, 11/9: the
stale-props test needs the game total 6 hours out and at the close for every game we hold props for). One historical odds call per
distinct asked time (every game on the board at that instant is kept, so a Sunday kickoff window costs one call). Cost: 10 credits per
market per 10 books -> 20 a call (spreads + totals; --markets h2h for fights: 10). Resumable: times already in the output are skipped. Stops at --floor credits left.
Output: data/oddsapi/compact/<--out>.jsonl.gz, same rows as loggers/oddsapi_bulk.py.
Usage: ODDS_API_KEY=... python3 loggers/oddsapi_lines_at.py nfl data/oddsapi/derivs/nfl_props_t360m.jsonl.gz --at 360,10 --out nfl_lines_at --floor 2970000"""
import os, sys, json, gzip, time, datetime as dt, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from oddsapi_bulk import compact
from sharp.gzlines import lines
API = 'https://api.the-odds-api.com/v4'; KEY = os.environ.get('ODDS_API_KEY')
SK = {'nfl': 'americanfootball_nfl', 'nba': 'basketball_nba', 'nhl': 'icehockey_nhl', 'cfb': 'americanfootball_ncaaf', 'mlb': 'baseball_mlb', 'boxing': 'boxing_boxing', 'mma': 'mma_mixed_martial_arts'}
BOOKS = 'pinnacle,draftkings,fanduel,williamhill_us,betonlineag,bovada,lowvig'
arg = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=60) as r:
                return json.load(r), int(r.headers.get('x-requests-last') or 0), int(r.headers.get('x-requests-remaining') or 0)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(5 * (i + 1)); continue
            print(f'[lines_at] {e.code} {e.read()[:200]}'); return None, 0, None
        except Exception: time.sleep(2 + i)
    return None, 0, None


def main():
    if not KEY: print('[lines_at] no ODDS_API_KEY'); return
    sp, src = sys.argv[1], sys.argv[2]; key = SK[sp]
    offs = [int(x) for x in arg('--at', '360,10').split(',')]; floor = int(arg('--floor', '3000000')); mkts = arg('--markets', 'spreads,totals')
    out = os.path.join(ROOT, 'data', 'oddsapi', 'compact', f"{arg('--out', sp + '_lines_at')}.jsonl.gz")
    starts = set()
    for l in lines(src):
        try: d = json.loads(l)
        except Exception: continue
        if d.get('start'): starts.add(d['start'])
    when = set()
    for s in starts:
        st = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
        for o in offs:
            w = st - dt.timedelta(minutes=o); w = w.replace(minute=w.minute - w.minute % 5, second=0, microsecond=0)   # snapshots every 5 minutes
            when.add(w)
    done = set()
    if os.path.exists(out):
        for l in lines(out):
            try: done.add(json.loads(l)['asked'])
            except Exception: pass
    todo = sorted(w for w in when if w.strftime('%Y-%m-%dT%H:%M:%SZ') not in done)
    print(f'[lines_at] {sp}: {len(starts)} start times, {len(when)} asked times, {len(todo)} to pull', flush=True)
    spent = 0; left = None; n = 0
    with gzip.open(out, 'at') as f:
        for w in todo:
            if left is not None and left - 20 < floor: print(f'[lines_at] stopping at the {floor} floor ({left} left)'); break
            a = w.strftime('%Y-%m-%dT%H:%M:%SZ')
            d, used, left_ = get(f'{API}/historical/sports/{key}/odds/?apiKey={KEY}&bookmakers={BOOKS}&markets={mkts}&oddsFormat=decimal&date={a}')
            spent += used; left = left_ if left_ is not None else left
            if not d: continue
            for r in compact(sp, key, d): r['asked'] = a; f.write(json.dumps(r, separators=(',', ':')) + '\n')
            n += 1
            if n % 25 == 0: print(f'[lines_at] {n}/{len(todo)} calls, {spent} credits, {left} left', flush=True); f.flush()
    print(f'[lines_at] {sp}: finished {n} calls, {spent} credits, {left} left')


if __name__ == '__main__': main()
