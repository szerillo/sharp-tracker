#!/usr/bin/env python3
"""MLB starters and bullpens before each game (Sean 11/6: first five vs full game with pitcher quality). Free MLB Stats API:
schedule (probable = starting pitchers for past games) and each starter's season game log. For every game since 2023-05 in odds.sqlite:
both starters' season-to-date FIP from EARLIER starts (prior season's FIP when fewer than 3 starts), innings per start, and each team's
bullpen runs allowed per 9 innings over innings 6-9 of its earlier games (ESPN linescores). Writes data/metrics/mlb_pregame.json.
Usage: python3 sharp/metrics_mlb.py"""
import os, sys, json, time, sqlite3, collections, urllib.request, datetime as dt, concurrent.futures as cf
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); ET = ZoneInfo('America/New_York')
CACHE = os.path.join(ROOT, 'data', 'metrics', 'mlb_api_cache.json')
API = 'https://statsapi.mlb.com/api/v1'


def get(u):
    for i in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=30))
        except Exception: time.sleep(1.5 * (i + 1))
    return None


def ip(x):
    w, _, f = str(x).partition('.'); return int(w or 0) + int(f or 0) / 3


def main():
    C = json.load(open(CACHE)) if os.path.exists(CACHE) else dict(sched={}, logs={})
    c = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    G = c.execute("SELECT g.game_id, g.start, g.home, g.away, r.espn_id FROM games g JOIN results r USING(game_id) WHERE g.sport='mlb' AND g.start>='2023-03-01' AND r.home_score IS NOT NULL").fetchall()
    dates = sorted({dt.datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(ET).date().isoformat() for _, s, *_ in G})
    need = [d for d in dates if d not in C['sched']]
    print(f'{len(G)} games, {len(dates)} dates, {len(need)} schedules to fetch', flush=True)
    def fs(d):
        x = get(f"{API}/schedule?sportId=1&date={d}&hydrate=probablePitcher")
        out = []
        for day in (x or {}).get('dates', []):
            for g in day['games']:
                h, a = g['teams']['home'], g['teams']['away']
                out.append(dict(pk=g['gamePk'], start=g['gameDate'], home=h['team']['name'], away=a['team']['name'], hp=(h.get('probablePitcher') or {}).get('id'), ap=(a.get('probablePitcher') or {}).get('id')))
        return d, out
    with cf.ThreadPoolExecutor(8) as ex:
        for d, out in ex.map(fs, need): C['sched'][d] = out
    json.dump(C, open(CACHE, 'w'))
    pitchers = {(p, d[:4]) for d, L in C['sched'].items() for g in L for p in (g['hp'], g['ap']) if p}
    pitchers |= {(p, str(int(s) - 1)) for p, s in list(pitchers)}
    need = [k for k in pitchers if f'{k[0]}|{k[1]}' not in C['logs']]
    print(f'{len(pitchers)} pitcher-seasons, {len(need)} game logs to fetch', flush=True)
    def fl(k):
        x = get(f"{API}/people/{k[0]}/stats?stats=gameLog&group=pitching&season={k[1]}")
        S = ((x or {}).get('stats') or [{}])[0].get('splits') or []
        return k, [[s['date'], s['stat'].get('gamesStarted', 0), ip(s['stat'].get('inningsPitched', 0)), s['stat'].get('strikeOuts', 0), s['stat'].get('baseOnBalls', 0),
                    s['stat'].get('hitByPitch', 0), s['stat'].get('homeRuns', 0), s['stat'].get('earnedRuns', 0)] for s in S]
    with cf.ThreadPoolExecutor(8) as ex:
        for i, (k, L) in enumerate(ex.map(fl, need)):
            C['logs'][f'{k[0]}|{k[1]}'] = L
            if i % 300 == 0: print(f'  logs {i}/{len(need)}', flush=True); json.dump(C, open(CACHE, 'w'))
    json.dump(C, open(CACHE, 'w'))
    FIPC = 3.15
    def fip(rows):
        I = sum(r[2] for r in rows)
        if I < 1: return None, 0
        return (13 * sum(r[6] for r in rows) + 3 * (sum(r[4] for r in rows) + sum(r[5] for r in rows)) - 2 * sum(r[3] for r in rows)) / I + FIPC, I
    def starter(p, date):
        if not p: return None
        L = [r for r in C['logs'].get(f'{p}|{date[:4]}', []) if r[0] < date and r[1]]
        f, I = fip(L)
        if len(L) >= 3: return dict(fip=round(f, 2), ip_per=round(I / len(L), 2), starts=len(L), src='season')
        P = [r for r in C['logs'].get(f'{p}|{int(date[:4]) - 1}', []) if r[1]]
        f2, I2 = fip(P)
        if f2 is not None and len(P) >= 5: return dict(fip=round(f2, 2), ip_per=round(I2 / len(P), 2), starts=len(L), src='prior season')
        return None
    # bullpen proxy from ESPN linescores: runs allowed in innings 6-9 per game, earlier games this season
    LS = json.load(open(os.path.join(ROOT, 'data', 'state', 'linescores.json'))).get('mlb', {})
    team_games = collections.defaultdict(list)
    for gid, start, home, away, eid in sorted(G, key=lambda x: x[1]):
        ls = LS.get(str(eid))
        if not ls or len(ls['h']) < 9 or len(ls['a']) < 8: continue
        late_h = sum(x or 0 for x in ls['a'][5:9]); late_a = sum(x or 0 for x in ls['h'][5:9])     # runs the home pen allowed = away runs in 6-9
        team_games[home].append((start, late_h, 4)); team_games[away].append((start, late_a, 3 + (1 if len(ls['h']) >= 9 and ls['h'][8] is not None else 0)))
    def pen(team, start):
        L = [x for x in team_games.get(team, []) if x[0] < start and x[0][:4] == start[:4]]
        if len(L) < 10: return None
        return round(9 * sum(x[1] for x in L) / sum(x[2] for x in L), 2)
    idx = collections.defaultdict(list)
    for d, L in C['sched'].items():
        for g in L: idx[(d, g['home'], g['away'])].append(g)
    out = {}; miss = 0
    for gid, start, home, away, eid in G:
        d = dt.datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(ET).date().isoformat()
        cand = idx.get((d, home, away)) or []
        if not cand: miss += 1; continue
        g = min(cand, key=lambda x: abs((dt.datetime.fromisoformat(x['start'].replace('Z', '+00:00')) - dt.datetime.fromisoformat(start.replace('Z', '+00:00'))).total_seconds()))
        hs, as_ = starter(g['hp'], d), starter(g['ap'], d)
        out[gid] = dict(home_sp=hs, away_sp=as_, home_pen=pen(home, start), away_pen=pen(away, start))
    json.dump(out, open(os.path.join(ROOT, 'data', 'metrics', 'mlb_pregame.json'), 'w'), separators=(',', ':'))
    print(f'games with metrics {len(out)}, both starters rated {sum(1 for v in out.values() if v["home_sp"] and v["away_sp"])}, unmatched {miss}')


if __name__ == '__main__':
    main()
