#!/usr/bin/env python3
"""td_corr_backtest (Sean 11/28): correlation between side and total results at Pinnacle's close, exactly as pre-registered in
docs/validation/correlation_ml_totals.md (commit f1a56cf9de). Paper research only.
Usage: python3 sharp/research/corr_ml_totals.py [ROOT_WITH_ODDS_DB]  -> data/research/corr_ml_totals.json and a markdown report on stdout."""
import datetime as dt
import json
import math
import os
import sys

HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); sys.path.insert(0, HERE)
from sharp import rule_replay as RR

SPORTS = ['cfb', 'nfl', 'nba', 'nhl', 'cbb']
LO, HI = dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc), dt.datetime(2026, 11, 29, tzinfo=dt.timezone.utc)
BANDS = [('-100 to -200', 0.5, 2 / 3), ('-200 to -400', 2 / 3, 0.8), ('-400+', 0.8, 1.01)]


def phi_stats(pairs):
    """pairs of (a, b) in {0,1}. phi, 95% interval, n, P(a), P(b), joint table."""
    n = len(pairs)
    if n < 30: return dict(n=n)
    a = sum(x for x, _ in pairs) / n; b = sum(y for _, y in pairs) / n; ab = sum(x * y for x, y in pairs) / n
    cov = ab - a * b; den = math.sqrt(a * (1 - a) * b * (1 - b))
    phi = cov / den if den else 0.0
    z = math.atanh(max(min(phi, 0.999999), -0.999999)); se = 1 / math.sqrt(n - 3)
    joint = {'A&B': ab, 'A&notB': a - ab, 'notA&B': b - ab, 'notA&notB': 1 - a - b + ab}
    return dict(n=n, phi=round(phi, 4), lo=round(math.tanh(z - 1.96 * se), 4), hi=round(math.tanh(z + 1.96 * se), 4), pA=round(a, 4), pB=round(b, 4),
                cov=cov, joint={k: round(v, 4) for k, v in joint.items()},
                indep={'A&B': round(a * b, 4), 'A&notB': round(a * (1 - b), 4), 'notA&B': round((1 - a) * b, 4), 'notA&notB': round((1 - a) * (1 - b), 4)},
                lift_B_given_A=round(ab / a - b, 4) if a else None,                       # P(Over | fav wins) - P(Over)
                lift_notB_given_notA=round((1 - a - b + ab) / (1 - a) - (1 - b), 4) if a < 1 else None)   # P(Under | dog wins) - P(Under)


def var_ratio(rows):
    """rows of (pl1, pl2): variance of the 2-bet P/L over the sum of the two variances (1.0 = independent)."""
    n = len(rows)
    if n < 30: return None
    m1 = sum(x for x, _ in rows) / n; m2 = sum(y for _, y in rows) / n
    v1 = sum((x - m1) ** 2 for x, _ in rows) / n; v2 = sum((y - m2) ** 2 for _, y in rows) / n
    vs = sum((x + y - m1 - m2) ** 2 for x, y in rows) / n
    return round(vs / (v1 + v2), 4) if v1 + v2 else None


def games(sport):
    out = []
    for g in RR.load(sport):
        if not (LO <= g['start'] < HI) or not g.get('regular', True): continue
        p, s, t = g['p_close'], g['sp_close'], g['tot_close']
        if None in (p, s, t, g['hs'], g['as_']) or p == 0.5: continue
        home_fav = p > 0.5; pf = p if home_fav else 1 - p
        mf = (g['hs'] - g['as_']) if home_fav else (g['as_'] - g['hs'])          # favorite's margin
        lf = s if home_fav else -s                                                # favorite's closing spread
        sf, sd = (g['hs'], g['as_']) if home_fav else (g['as_'], g['hs'])
        tot = g['hs'] + g['as_']
        out.append(dict(pf=pf, t=t, fav_won=int(mf > 0) if mf != 0 else None, cover=None if mf + lf == 0 else int(mf + lf > 0),
                        over=None if tot == t else int(tot > t),
                        fav_tt=None if sf == (t - lf) / 2 else int(sf > (t - lf) / 2), dog_tt=None if sd == (t + lf) / 2 else int(sd > (t + lf) / 2)))
    return out


def section(G):
    ml = [(g['fav_won'], g['over']) for g in G if g['fav_won'] is not None and g['over'] is not None]
    sp = [(g['cover'], g['over']) for g in G if g['cover'] is not None and g['over'] is not None]
    r = dict(ml=phi_stats(ml), spread=phi_stats(sp))
    fav_pl = lambda g, won: (1 / g['pf'] - 1) if won else -1.0
    dog_pl = lambda g, won: (1 / (1 - g['pf']) - 1) if won else -1.0
    M = [g for g in G if g['fav_won'] is not None and g['over'] is not None]
    S = [g for g in G if g['cover'] is not None and g['over'] is not None]
    r['var_ratio'] = {
        'fav ML + Over': var_ratio([(fav_pl(g, g['fav_won']), 1.0 if g['over'] else -1.0) for g in M]),
        'fav ML + Under': var_ratio([(fav_pl(g, g['fav_won']), -1.0 if g['over'] else 1.0) for g in M]),
        'dog ML + Over': var_ratio([(dog_pl(g, not g['fav_won']), 1.0 if g['over'] else -1.0) for g in M]),
        'dog ML + Under': var_ratio([(dog_pl(g, not g['fav_won']), -1.0 if g['over'] else 1.0) for g in M]),
        'fav spread + Over': var_ratio([(1.0 if g['cover'] else -1.0, 1.0 if g['over'] else -1.0) for g in S]),
        'dog spread + Under': var_ratio([(-1.0 if g['cover'] else 1.0, -1.0 if g['over'] else 1.0) for g in S]),
    }
    return r


def main():
    if len(sys.argv) > 1:
        RR.ROOT = os.path.abspath(sys.argv[1]); RR.DB = os.path.join(RR.ROOT, 'data', 'oddsapi', 'odds.sqlite')
    out = dict(built=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), prereg='f1a56cf9de', sports={})
    for sp in SPORTS:
        G = games(sp)
        ts = sorted(g['t'] for g in G); c1, c2 = ts[len(ts) // 3], ts[2 * len(ts) // 3]
        R = dict(games=len(G), all=section(G), bands={}, thirds={}, thirds_cut=[c1, c2])
        for name, lo, hi in BANDS: R['bands'][name] = section([g for g in G if lo <= g['pf'] < hi])
        for name, f in (('low', lambda t: t < c1), ('mid', lambda t: c1 <= t < c2), ('high', lambda t: t >= c2)):
            R['thirds'][name] = section([g for g in G if f(g['t'])])
        R['control'] = dict(fav_tt=phi_stats([(g['fav_tt'], g['over']) for g in G if g['fav_tt'] is not None and g['over'] is not None]),
                            dog_tt=phi_stats([(g['dog_tt'], g['over']) for g in G if g['dog_tt'] is not None and g['over'] is not None]))
        out['sports'][sp] = R
    os.makedirs(os.path.join(HERE, 'data', 'research'), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, 'data', 'research', 'corr_ml_totals.json'), 'w'), indent=1, default=float)
    print(json.dumps({sp: dict(games=R['games'], ml=R['all']['ml'].get('phi'), spread=R['all']['spread'].get('phi'),
                               ctrl=R['control']['fav_tt'].get('phi')) for sp, R in out['sports'].items()}))


if __name__ == '__main__':
    main()
