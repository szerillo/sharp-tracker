#!/usr/bin/env python3
"""Historical player props from The Odds API (Sean, 11/4: "grab as much prop stuff as you can"). Per event, one snapshot an hour before
the start (the close), the prop markets below at every book in BOOKS; stored compact as one line per event per market:
{t, id, sport, start, home, away, market, books: {book: [[player, line, over dec, under dec], ...]}} (yes/no markets like anytime TD:
[player, null, yes dec, no dec]). Event ids and start times come from the compact game files (data/oddsapi/compact/<sport>.jsonl.gz),
so run after oddsapi_bulk.py has covered the season. Cost: 10 credits per market per 10 books per event. Resumable per sport.
Usage: ODDS_API_KEY=... python3 loggers/oddsapi_props.py nba|nfl|nhl [--from 2024-10-01] [--budget N]
Output: data/oddsapi/props/<sport>.jsonl.gz"""
import os, sys, json, gzip, time, datetime as dt, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
COMPACT = os.path.join(ROOT, 'data', 'oddsapi', 'compact'); OUT = os.path.join(ROOT, 'data', 'oddsapi', 'props')
API = "https://api.the-odds-api.com/v4"; KEY = os.environ.get('ODDS_API_KEY')
BOOKS = 'pinnacle,draftkings,fanduel,williamhill_us,betmgm,betonlineag,betrivers,bovada,fanatics,espnbet'
MARKETS = {'nba': ('basketball_nba', ['player_points', 'player_rebounds', 'player_assists', 'player_threes', 'player_points_rebounds_assists']),
           'nfl': ('americanfootball_nfl', ['player_pass_yds', 'player_rush_yds', 'player_reception_yds', 'player_receptions', 'player_anytime_td']),
           'nhl': ('icehockey_nhl', ['player_shots_on_goal', 'player_points', 'player_goal_scorer_anytime']),
           'cbb': ('basketball_ncaab', ['player_points', 'player_rebounds', 'player_assists'])}


def get(u):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=60) as r:
                return json.load(r), int(r.headers.get('x-requests-last') or 0), int(r.headers.get('x-requests-remaining') or 0)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(5 * (i + 1)); continue
            if e.code in (404, 422): return None, 0, None
            time.sleep(2 + i)
        except Exception: time.sleep(2 + i)
    return None, 0, None


def main():
    sport = sys.argv[1]; key, markets = MARKETS[sport]
    d0 = sys.argv[sys.argv.index('--from') + 1] if '--from' in sys.argv else '2000-01-01'
    budget = int(sys.argv[sys.argv.index('--budget') + 1]) if '--budget' in sys.argv else 300000
    os.makedirs(OUT, exist_ok=True); donep = os.path.join(OUT, f'_done_{sport}.json')
    done = set(json.load(open(donep))) if os.path.exists(donep) else set()
    events = {}
    with gzip.open(os.path.join(COMPACT, f'{sport}.jsonl.gz'), 'rt') as fh:
        for l in fh:
            r = json.loads(l)
            if r['start'][:10] >= d0: events[r['id']] = r
    print(f"[props {sport}] {len(events)} events on file, {len(done)} done", flush=True)
    spent = 0; n = 0; t0 = time.time(); left = None
    for eid, r in sorted(events.items(), key=lambda kv: kv[1]['start']):
        if eid in done: continue
        if spent + 10 * len(markets) > budget: print(f"[props {sport}] budget reached at {spent}"); break
        when = dt.datetime.fromisoformat(r['start'].replace('Z', '+00:00')) - dt.timedelta(hours=1)
        d, used, left = get(f"{API}/historical/sports/{key}/events/{eid}/odds?apiKey={KEY}&bookmakers={BOOKS}&markets={','.join(markets)}&oddsFormat=decimal&date={when:%Y-%m-%dT%H:%M:%SZ}")
        spent += used; done.add(eid)
        if d and d.get('data'):
            g = d['data']; rows = {}
            for b in g.get('bookmakers') or []:
                for m in b.get('markets') or []:
                    P = {}
                    for o in m.get('outcomes') or []:
                        pl = o.get('description') or o.get('name'); e = P.setdefault(pl, [pl, o.get('point'), None, None])
                        if o['name'] in ('Over', 'Yes'): e[2] = o.get('price')
                        elif o['name'] in ('Under', 'No'): e[3] = o.get('price')
                    if P: rows.setdefault(m['key'], {})[b['key']] = list(P.values())
            with gzip.open(os.path.join(OUT, f'{sport}.jsonl.gz'), 'at') as fh:
                for mk, bk in rows.items(): fh.write(json.dumps(dict(t=d.get('timestamp'), id=eid, sport=sport, start=r['start'], home=r['home'], away=r['away'], market=mk, books=bk), separators=(',', ':')) + '\n')
            n += 1
        if n % 25 == 0 or len(done) % 50 == 0:
            tmp = donep + '.tmp'; json.dump(sorted(done), open(tmp, 'w')); os.replace(tmp, donep)
            print(f"[props {sport}] {r['start'][:10]} | {n} events with props, {spent} credits, {left} left, {time.time() - t0:.0f}s", flush=True)
        time.sleep(0.4)
    tmp = donep + '.tmp'; json.dump(sorted(done), open(tmp, 'w')); os.replace(tmp, donep)
    print(f"[props {sport}] done: {n} events, {spent} credits, {left} left")


if __name__ == '__main__':
    main()
