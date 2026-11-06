#!/usr/bin/env python3
"""CBB tempo and efficiency before each game (Sean 11/6: layer team metrics into the derivative edges). Source: Bart Torvik game stats
(barttorvik.com/getgamestats.php?year=Y&csv=1; one row per team-game: offensive / defensive efficiency, four factors, possessions).
For every team-game: the team's season-to-date averages from its EARLIER games only (tempo, adjusted off / def efficiency) and games
played. Matched to odds.sqlite games by ET date and final score. Writes data/metrics/cbb_pregame.json {game_id: {home: {...}, away: {...}}}.
Usage: python3 sharp/metrics_cbb.py <dir with torvik_games_YYYY.csv>"""
import os, sys, csv, json, sqlite3, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
from zoneinfo import ZoneInfo
ET = ZoneInfo('America/New_York')


def main():
    src = sys.argv[1]; G = []
    for f in sorted(os.listdir(src)):
        if not f.startswith('torvik_games_'): continue
        for r in csv.reader(open(os.path.join(src, f))):
            try:
                d = dt.datetime.strptime(r[0], '%m/%d/%y').date(); res = r[6]; a, b = [int(x) for x in res.split(',')[1].strip().split('-')]
                pts_for, pts_against = (a, b) if res.startswith('W') else (b, a)
                G.append(dict(date=d, team=r[2], opp=r[4], venue=r[5], pf=pts_for, pa=pts_against, adjo=float(r[7]), adjd=float(r[8]), oe=float(r[9]), de=float(r[14]), tempo=float(r[23]), season=int(r[22])))
            except Exception: continue
    G.sort(key=lambda x: x['date'])
    hist = collections.defaultdict(list); pre = {}
    for g in G:
        H = hist[(g['team'], g['season'])]
        if H:
            n = len(H); pre[(g['date'], g['team'])] = dict(n=n, tempo=sum(x['tempo'] for x in H) / n, adjo=sum(x['adjo'] for x in H) / n, adjd=sum(x['adjd'] for x in H) / n,
                                                          pf=sum(x['pf'] for x in H) / n, pa=sum(x['pa'] for x in H) / n)
        H.append(g)
    # league tempo by season (for relative tempo)
    lg = collections.defaultdict(list)
    for g in G: lg[g['season']].append(g['tempo'])
    lgm = {s: sum(v) / len(v) for s, v in lg.items()}
    by = collections.defaultdict(list)                  # (date, score pair) -> torvik rows
    for g in G: by[(g['date'], tuple(sorted((g['pf'], g['pa']))))].append(g)
    c = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    out = {}; miss = 0
    for gid, start, hs, as_ in c.execute("SELECT g.game_id, g.start, r.home_score, r.away_score FROM games g JOIN results r USING(game_id) WHERE g.sport='cbb' AND r.home_score IS NOT NULL"):
        d = dt.datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(ET).date()
        cand = []
        for dd in (d, d - dt.timedelta(days=1), d + dt.timedelta(days=1)): cand += by.get((dd, tuple(sorted((int(hs), int(as_))))), [])
        hrow = [g for g in cand if g['pf'] == hs and g['pa'] == as_ and g['venue'] in ('H', 'N')]
        arow = [g for g in cand if g['pf'] == as_ and g['pa'] == hs and g['venue'] in ('A', 'N')]
        if len(hrow) != 1 or len(arow) != 1: miss += 1; continue
        ph, pa = pre.get((hrow[0]['date'], hrow[0]['team'])), pre.get((arow[0]['date'], arow[0]['team']))
        if not ph or not pa: continue
        out[gid] = dict(season=hrow[0]['season'], lg_tempo=round(lgm[hrow[0]['season']], 2), home=dict(team=hrow[0]['team'], **{k: round(v, 2) for k, v in ph.items()}),
                        away=dict(team=arow[0]['team'], **{k: round(v, 2) for k, v in pa.items()}), tempo_game=hrow[0]['tempo'])
    json.dump(out, open(os.path.join(ROOT, 'data', 'metrics', 'cbb_pregame.json'), 'w'), separators=(',', ':'))
    print(f'torvik team-games {len(G)}, odds games matched with pre-game metrics {len(out)}, unmatched {miss}')


if __name__ == '__main__':
    main()
