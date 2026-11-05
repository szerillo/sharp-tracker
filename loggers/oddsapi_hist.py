#!/usr/bin/env python3
"""Historical odds snapshots from The Odds API (Sean, 11/4): openers and closers across books for every system's sport, so each rule can
be tested against the close over whole seasons, not the week of our own tape. Key in the ODDS_API_KEY secret (never in a file).

A snapshot = one sport at one instant, every game on the board, moneyline + spread + total at the books in BOOKS, saved as
data/oddsapi/<sport>/<YYYY-MM-DDTHHMM>.json.gz (the API's own shape). Cost: 10 credits per market per 10 books -> 30 a snapshot.
Monthly budget is 20,000, so pulls are planned, not continuous: pass the sport, the date range and the snapshot hours (UTC), and the
script skips snapshots already on disk and stops at --budget credits. The API returns the last snapshot at or before the asked time.

Usage: ODDS_API_KEY=... python3 loggers/oddsapi_hist.py --sport nba --from 2026-10-21 --to 2026-11-04 --hours 23,0,2 [--budget 3000]
  --hours are UTC hours of day; for a close, use the hour the games start (NBA 7 PM ET = 0 UTC next day: pass 0 and 2 with the day
  shifted, see shift()). --open pulls a 15:00 UTC snapshot the day before each date instead (the morning line).
Sports: nba nhl nfl cfb cbb soccer_epl mma tennis (tennis keys change by event; use --sport-key for those)."""
import os, sys, json, gzip, time, datetime as dt, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'data', 'oddsapi')
API = "https://api.the-odds-api.com/v4"
KEY = os.environ.get('ODDS_API_KEY')
SPORT_KEY = {'nba': 'basketball_nba', 'nhl': 'icehockey_nhl', 'nfl': 'americanfootball_nfl', 'cfb': 'americanfootball_ncaaf', 'cbb': 'basketball_ncaab',
             'soccer_epl': 'soccer_epl', 'mma': 'mma_mixed_martial_arts', 'wnba': 'basketball_wnba', 'mlb': 'baseball_mlb'}
BOOKS = 'pinnacle,draftkings,fanduel,williamhill_us,betmgm,betonlineag,lowvig'
MARKETS = 'h2h,spreads,totals'


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def pull(sport_key, when):
    u = f"{API}/historical/sports/{sport_key}/odds/?apiKey={KEY}&bookmakers={BOOKS}&markets={MARKETS}&oddsFormat=decimal&date={when.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=60) as r:
                used = int(r.headers.get('x-requests-last') or 0); left = int(r.headers.get('x-requests-remaining') or 0)
                return json.load(r), used, left
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(5 * (i + 1)); continue
            print(f"[oddsapi] {e.code} {e.read()[:200]}"); return None, 0, None
        except Exception as e:
            time.sleep(2 + i)
    return None, 0, None


def main():
    if not KEY: print('[oddsapi] no ODDS_API_KEY'); return
    sport = arg('--sport', 'nba'); sk = arg('--sport-key') or SPORT_KEY.get(sport, sport)
    d0 = dt.date.fromisoformat(arg('--from')); d1 = dt.date.fromisoformat(arg('--to', arg('--from')))
    hours = [int(h) for h in arg('--hours', '0').split(',')]
    budget = int(arg('--budget', '3000')); spent = 0; left = None
    od = os.path.join(OUT, sport); os.makedirs(od, exist_ok=True)
    dow = [int(x) for x in arg('--dow').split(',')] if arg('--dow') else None      # 0 = Monday ... 6 = Sunday (ET game day)
    d = d0; n = 0
    while d <= d1:
        if dow is not None and d.weekday() not in dow: d += dt.timedelta(days=1); continue
        for h in hours:
            # hours under 12 UTC belong to the next calendar day (a 7 PM ET tip is 00:00 UTC the day after); --open takes the day before at 15 UTC
            when = dt.datetime.combine(d + dt.timedelta(days=1 if h < 12 else 0), dt.time(h, 0), dt.timezone.utc)
            if '--open' in sys.argv: when = dt.datetime.combine(d - dt.timedelta(days=1), dt.time(15, 0), dt.timezone.utc)
            p = os.path.join(od, when.strftime('%Y-%m-%dT%H%M') + '.json.gz')
            if os.path.exists(p): continue
            if spent + 30 > budget: print(f"[oddsapi] budget {budget} reached ({spent} spent); stop"); return
            data, used, left = pull(sk, when)
            if data is None: continue
            spent += used; n += 1
            with gzip.open(p, 'wt') as fh: json.dump(data, fh, separators=(',', ':'))
            print(f"[oddsapi] {sport} {when:%Y-%m-%d %H:%M}Z: {len(data.get('data') or [])} games, snapshot {data.get('timestamp')}, cost {used}, remaining {left}")
            time.sleep(0.3)
        d += dt.timedelta(days=1)
    print(f"[oddsapi] {n} snapshots, {spent} credits spent, {left} remaining this month")


if __name__ == '__main__':
    main()
