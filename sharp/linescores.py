#!/usr/bin/env python3
"""Period scores from ESPN scoreboards (free) for grading first-half / first-period / team-total bets.
For every game in data/oddsapi/odds.sqlite with an ESPN id since 2023-05-03 in the requested sports, fetch the scoreboard for each game
date (ET) and store per ESPN event: home/away period lines. Writes data/state/linescores.json {sport: {espn_id: {h: [...], a: [...]}}}.
Usage: python3 sharp/linescores.py nfl nba"""
import os, sys, json, time, sqlite3, urllib.request, collections, datetime as dt
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
DB = os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'); OUT = os.path.join(ROOT, 'data', 'state', 'linescores.json')
LG = {'nfl': 'football/nfl', 'nba': 'basketball/nba', 'cfb': 'football/college-football', 'nhl': 'hockey/nhl', 'cbb': 'basketball/mens-college-basketball', 'mlb': 'baseball/mlb', 'wnba': 'basketball/wnba'}
ET = ZoneInfo('America/New_York')


def get(u):
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=30))
        except Exception: time.sleep(2)
    return None


def main():
    S = json.load(open(OUT)) if os.path.exists(OUT) else {}
    conn = sqlite3.connect(DB)
    for sp in [a for a in sys.argv[1:] if a in LG]:
        have = S.setdefault(sp, {})
        rows = conn.execute("SELECT r.espn_id, g.start FROM games g JOIN results r USING(game_id) WHERE g.sport=? AND g.start>='2023-05-03' AND r.espn_id IS NOT NULL", (sp,)).fetchall()
        need = collections.defaultdict(set)
        for eid, start in rows:
            if str(eid) in have: continue
            d = dt.datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(ET).date()
            for x in (d, d + dt.timedelta(days=1)): need[x.strftime('%Y%m%d')].add(str(eid))
        print(f'[linescores] {sp}: {len(rows)} games, {len(have)} have, {len(need)} dates to fetch', flush=True)
        extra = '&groups=80&limit=400' if sp == 'cfb' else '&groups=50&limit=400' if sp == 'cbb' else ''
        for i, day in enumerate(sorted(need)):
            d = get(f"https://site.api.espn.com/apis/site/v2/sports/{LG[sp]}/scoreboard?dates={day}{extra}")
            for e in (d or {}).get('events', []):
                c = (e.get('competitions') or [{}])[0]; L = {}
                for t in c.get('competitors', []):
                    L['h' if t.get('homeAway') == 'home' else 'a'] = [l.get('value') for l in t.get('linescores', [])]
                if L.get('h') and L.get('a'): have[str(e['id'])] = L
            if i % 50 == 0:
                json.dump(S, open(OUT, 'w')); print(f'[linescores] {sp}: {i}/{len(need)} dates, {len(have)} games', flush=True)
            time.sleep(0.1)
        json.dump(S, open(OUT, 'w')); print(f'[linescores] {sp}: done, {len(have)} games', flush=True)


if __name__ == '__main__':
    main()
