#!/usr/bin/env python3
"""NFL EPA before each game (Sean 11/6: "EPA per play for football"). Source: nflverse play-by-play (github.com/nflverse/nflverse-data).
For every team-game: season-to-date offensive and defensive EPA per play (pass + rush plays), success rate, pass EPA, rush EPA, points
for / against per game, from EARLIER games only. Matched to odds.sqlite NFL games by ET date and team.
Writes data/metrics/nfl_pregame.json. Usage: python3 sharp/metrics_nfl.py <dir with nfl_pbp_YYYY.parquet>"""
import os, sys, json, sqlite3, collections, datetime as dt
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
FIX = {'LA': 'LAR', 'WAS': 'WSH', 'JAC': 'JAX', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'}
ab = lambda x: FIX.get(x, x)


def main():
    src = sys.argv[1]; games = collections.defaultdict(dict)
    for f in sorted(os.listdir(src)):
        if not f.startswith('nfl_pbp_'): continue
        d = pd.read_parquet(os.path.join(src, f), columns=['game_id', 'game_date', 'season', 'season_type', 'posteam', 'defteam', 'home_team', 'away_team', 'epa', 'success', 'pass', 'rush', 'home_score', 'away_score'])
        d = d[(d['pass'] == 1) | (d['rush'] == 1)].dropna(subset=['epa', 'posteam'])
        for (gid, team), x in d.groupby(['game_id', 'posteam']):
            r0 = x.iloc[0]
            games[(gid, ab(team))].update(date=r0['game_date'], season=int(r0['season']), stype=r0['season_type'], opp=ab(r0['defteam']), home=ab(r0['home_team']), away=ab(r0['away_team']),
                                          off_epa=float(x['epa'].mean()), off_sr=float(x['success'].mean()), off_pass=float(x.loc[x['pass'] == 1, 'epa'].mean()) if (x['pass'] == 1).any() else None,
                                          off_rush=float(x.loc[x['rush'] == 1, 'epa'].mean()) if (x['rush'] == 1).any() else None, plays=len(x),
                                          pf=int(r0['home_score'] if ab(team) == ab(r0['home_team']) else r0['away_score']), pa=int(r0['away_score'] if ab(team) == ab(r0['home_team']) else r0['home_score']))
    # defensive numbers are the opponent's offensive ones in the same game
    for (gid, team), v in games.items():
        o = games.get((gid, v['opp'])) or {}
        v.update(def_epa=o.get('off_epa'), def_sr=o.get('off_sr'))
    seq = collections.defaultdict(list)
    for (gid, team), v in sorted(games.items(), key=lambda x: x[1]['date']): seq[(team, v['season'])].append(v)
    pre = {}
    avg = lambda L, k: (sum(x[k] for x in L if x.get(k) is not None) / max(1, sum(1 for x in L if x.get(k) is not None)))
    for (team, s), L in seq.items():
        for i, v in enumerate(L):
            P = [x for x in L[:i] if x['stype'] == 'REG']
            if len(P) < 2: continue
            pre[(team, v['date'])] = dict(n=len(P), off_epa=avg(P, 'off_epa'), def_epa=avg(P, 'def_epa'), off_sr=avg(P, 'off_sr'), def_sr=avg(P, 'def_sr'), off_pass=avg(P, 'off_pass'),
                                          off_rush=avg(P, 'off_rush'), plays=avg(P, 'plays'), pf=avg(P, 'pf'), pa=avg(P, 'pa'))
    import sharp.nfl_replay as NR, sharp.oddsapi_edge as E
    A = NR.abbr_map(); c = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite')); out = {}; miss = 0
    from zoneinfo import ZoneInfo
    ET = ZoneInfo('America/New_York')
    for gid, start, home, away in c.execute("SELECT game_id, start, home, away FROM games WHERE sport='nfl'"):
        d = dt.datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(ET).date().isoformat()
        h, a = A.get(E.norm(home)), A.get(E.norm(away))
        ph, pa = pre.get((h, d)), pre.get((a, d))
        if not ph or not pa: miss += 1; continue
        out[gid] = dict(home={k: round(v, 4) if isinstance(v, float) else v for k, v in ph.items()}, away={k: round(v, 4) if isinstance(v, float) else v for k, v in pa.items()})
    json.dump(out, open(os.path.join(ROOT, 'data', 'metrics', 'nfl_pregame.json'), 'w'), separators=(',', ':'))
    print(f'team-games {len(games)}, pre-game rows {len(pre)}, odds games matched {len(out)}, unmatched {miss}')


if __name__ == '__main__':
    main()
