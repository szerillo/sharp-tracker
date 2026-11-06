#!/usr/bin/env python3
"""Odds API historical derivatives (Sean 11/5: "use the rest of the credits"): per-event pregame snapshot of first-half and team-total
markets, for games already in data/oddsapi/odds.sqlite. Historical period / additional markets exist from 2023-05-03 only.
Cost: 10 credits per market returned per game (one region). Second-half lines are not posted pregame, so 2H cannot be pulled.

Plans (sport: markets):  nfl: spreads_h1,totals_h1,team_totals   nba: totals_h1
Snapshot = start - 10 minutes (the API returns the latest snapshot at or before that time). Raw bookmaker payloads are appended to
data/oddsapi/derivs/<sport>.jsonl.gz, one line per game; reruns skip games already pulled. Stops when credits remaining < --floor.
Usage: ODDS_API_KEY=... python3 loggers/oddsapi_derivs.py nfl nba [--floor 12000] [--newest-first]"""
import os, sys, json, gzip, time, sqlite3, urllib.request, urllib.error, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
DB = os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'); OUTD = os.path.join(ROOT, 'data', 'oddsapi', 'derivs')
API = 'https://api.the-odds-api.com/v4'; KEY = os.environ.get('ODDS_API_KEY')
BOOKS = 'pinnacle,draftkings,fanduel,williamhill_us,betonlineag,lowvig,betrivers,bovada,circasports'
PLAN = {'nfl': 'spreads_h1,totals_h1,team_totals', 'nba': 'totals_h1', 'cfb': 'spreads_h1,totals_h1', 'nhl': 'totals_p1', 'mlb': 'totals_1st_5_innings,spreads_1st_5_innings'}
SINCE = '2023-05-03'


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def get(url):
    for i in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sharp-tracker'}), timeout=60)
            return json.load(r), int(r.headers.get('x-requests-last') or 0), int(r.headers.get('x-requests-remaining') or 0)
        except urllib.error.HTTPError as e:
            if e.code in (404, 422): return None, 0, None
            if e.code == 401: raise SystemExit('[derivs] 401: key rejected or out of credits')
            time.sleep(3 * (i + 1))
        except Exception:
            time.sleep(3 * (i + 1))
    return None, 0, None


def main():
    if not KEY: raise SystemExit('ODDS_API_KEY not set')
    floor = int(arg('--floor', '12000')); sports = [a for a in sys.argv[1:] if a in PLAN]
    os.makedirs(OUTD, exist_ok=True); conn = sqlite3.connect(DB)
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    for sp in sports:
        path = os.path.join(OUTD, f'{sp}.jsonl.gz'); done = set()
        if os.path.exists(path):
            try:
                for l in gzip.open(path, 'rt'): done.add(json.loads(l)['game_id'])
            except (EOFError, OSError): pass
        order = 'DESC' if '--newest-first' in sys.argv else 'ASC'
        G = conn.execute(f"SELECT game_id, key, start, home, away FROM games WHERE sport=? AND start>=? AND start<? ORDER BY start {order}", (sp, SINCE, now)).fetchall()
        todo = [g for g in G if g[0] not in done]
        print(f'[derivs] {sp}: {len(G)} games since {SINCE}, {len(done)} done, {len(todo)} to pull ({PLAN[sp]})', flush=True)
        n = spent = 0; left = None
        with gzip.open(path, 'at') as out:
            for gid, key, start, home, away in todo:
                when = (dt.datetime.fromisoformat(start.replace('Z', '+00:00')) - dt.timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')
                d, cost, rem = get(f"{API}/historical/sports/{key}/events/{gid}/odds?apiKey={KEY}&bookmakers={BOOKS}&markets={PLAN[sp]}&oddsFormat=decimal&date={when}")
                spent += cost; left = rem if rem is not None else left
                e = (d or {}).get('data') or {}
                out.write(json.dumps(dict(game_id=gid, sport=sp, start=start, home=home, away=away, snap=(d or {}).get('timestamp'), asked=when,
                                          markets=PLAN[sp], bookmakers=e.get('bookmakers') or [])) + '\n')
                n += 1
                if n % 100 == 0: out.flush(); print(f'[derivs] {sp}: {n}/{len(todo)} pulled, {spent} credits this run, {left} left', flush=True)
                if left is not None and left < floor: print(f'[derivs] stopping at the {floor} floor ({left} left)', flush=True); return
                time.sleep(0.15)
        print(f'[derivs] {sp}: finished {n} games, {spent} credits, {left} left', flush=True)


if __name__ == '__main__':
    main()
