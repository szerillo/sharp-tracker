#!/usr/bin/env python3
"""NHL expected goals before each game (Sean 11/6). Source: MoneyPuck team game-by-game (moneypuck.com/.../all_teams.csv).
For every team-game: season-to-date rates from EARLIER games only, all situations and 5-on-5: xGF/60, xGA/60, GF/60, GA/60, and the
last-10 versions. Matched to odds.sqlite NHL games by ET date and team. Writes data/metrics/nhl_pregame.json.
Usage: python3 sharp/metrics_nhl.py <all_teams.csv>"""
import os, sys, csv, json, sqlite3, collections, datetime as dt
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); ET = ZoneInfo('America/New_York')
FIX = {'TBL': 'TB', 'LAK': 'LA', 'NJD': 'NJ', 'SJS': 'SJ', 'ARI': 'UTA', 'UTAH': 'UTA', 'WAS': 'WSH', 'MON': 'MTL', 'CLB': 'CBJ', 'NAS': 'NSH'}
ab = lambda x: FIX.get((x or '').replace('.', '').upper(), (x or '').replace('.', '').upper())


def main():
    rows = collections.defaultdict(dict)            # (team, date) -> {situation: row}
    for r in csv.DictReader(open(sys.argv[1])):
        if r['situation'] not in ('all', '5on5') or r.get('playoffGame') == '1': continue
        try: d = dt.datetime.strptime(r['gameDate'], '%Y%m%d').date()
        except Exception: continue
        rows[(ab(r['playerTeam']), d)][r['situation']] = dict(season=r['season'], ice=float(r['iceTime']) / 60, xgf=float(r['xGoalsFor']), xga=float(r['xGoalsAgainst']),
                                                              gf=float(r['goalsFor']), ga=float(r['goalsAgainst']), sf=float(r['shotsOnGoalFor']), sa=float(r['shotsOnGoalAgainst']))
    seq = collections.defaultdict(list)
    for (t, d), v in sorted(rows.items(), key=lambda x: x[0][1]):
        if 'all' in v: seq[(t, v['all']['season'])].append((d, v))
    pre = {}
    def rate(L, sit, k):
        ice = sum(x[1][sit]['ice'] for x in L if sit in x[1]); return 60 * sum(x[1][sit][k] for x in L if sit in x[1]) / ice if ice else None
    for (t, s), L in seq.items():
        for i, (d, v) in enumerate(L):
            P = L[:i]
            if len(P) < 3: continue
            last = P[-10:]
            pre[(t, d)] = dict(n=len(P), xgf=rate(P, 'all', 'xgf'), xga=rate(P, 'all', 'xga'), gf=rate(P, 'all', 'gf'), ga=rate(P, 'all', 'ga'),
                               xgf5=rate(P, '5on5', 'xgf'), xga5=rate(P, '5on5', 'xga'), xgf_l10=rate(last, 'all', 'xgf'), xga_l10=rate(last, 'all', 'xga'),
                               gf_l10=rate(last, 'all', 'gf'), ga_l10=rate(last, 'all', 'ga'))
    c = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite')); out = {}; miss = 0
    for gid, start, ha, aa in c.execute("SELECT g.game_id, g.start, r.home_ab, r.away_ab FROM games g JOIN results r USING(game_id) WHERE g.sport='nhl' AND r.home_score IS NOT NULL"):
        d = dt.datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(ET).date()
        h = next((pre[(ab(ha), dd)] for dd in (d, d - dt.timedelta(days=1)) if (ab(ha), dd) in pre), None)
        a = next((pre[(ab(aa), dd)] for dd in (d, d - dt.timedelta(days=1)) if (ab(aa), dd) in pre), None)
        if not h or not a: miss += 1; continue
        out[gid] = dict(home={k: round(v, 3) if isinstance(v, float) else v for k, v in h.items()}, away={k: round(v, 3) if isinstance(v, float) else v for k, v in a.items()})
    json.dump(out, open(os.path.join(ROOT, 'data', 'metrics', 'nhl_pregame.json'), 'w'), separators=(',', ':'))
    print(f'team-games {len(pre)}, odds games matched {len(out)}, unmatched {miss}')


if __name__ == '__main__':
    main()
