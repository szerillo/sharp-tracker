#!/usr/bin/env python3
"""Tennis first set on the curve, Odds API history (Sean 11/6: "like we did with first set tennis stuff"; list item 5).
The curve: for every match with a Pinnacle closing match price (odds.sqlite, 2022-26, Slams and the big events the Odds API covers) and an
ESPN result (data/tennis/results.jsonl, surname + date): how often a player at a given no-vig match probability wins the first set,
leave-one-season-out, binned by match probability (2.5-point bins), separately for best-of-3 and best-of-5 (men's Slams).
Then every first-set price quoted 10 minutes before (derivs/tennis_full) and 2 hours before (tennis_early120): Pinnacle's no-vig and each
US book's price against the curve.
  1. Blend: does the curve add information to Pinnacle's first-set price?
  2. Bets: a book (or Pinnacle) price 3%+ better than the curve, graded on the ESPN first-set winner, by season / book / side.
Writes data/research/tennis_set1_curve.json. Usage: python3 sharp/tennis_set1_curve.py"""
import os, sys, json, math, sqlite3, collections, datetime as dt
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
from sharp.tennis_firstset import sur
NICE = dict(pinnacle='Pinnacle', draftkings='DK', fanduel='FD', williamhill_us='Caesars', betrivers='BetRivers', betonlineag='BetOnline', lowvig='LowVig', bovada='Bovada', betmgm='BetMGM')


def main():
    R = collections.defaultdict(list)
    for l in open(os.path.join(ROOT, 'data', 'tennis', 'results.jsonl')):
        r = json.loads(l)
        if not r.get('first_set_complete') or r.get('walkover'): continue
        R[(r['start'][:10], sur(r['p1']))].append(r); R[(r['start'][:10], sur(r['p2']))].append(r)

    def result(start, a, b):
        """first-set winner 'a' / 'b' for players a, b on that date (or the day before / after)"""
        d0 = dt.date.fromisoformat(start[:10])
        for dd in (0, -1, 1):
            k = (d0 + dt.timedelta(days=dd)).isoformat()
            for r in R.get((k, sur(a)), []):
                s1, s2 = sur(r['p1']), sur(r['p2'])
                if {s1, s2} == {sur(a), sur(b)}:
                    w = r['p1'] if r['first_set_winner'] == 'p1' else r['p2']
                    return ('a' if sur(w) == sur(a) else 'b'), (r.get('n_sets_max') or (5 if r['tour'] == 'atp' and 'Singles' in (r.get('draw') or '') and any(x in (r.get('tournament') or '') for x in ('Open', 'Wimbledon', 'Roland', 'Australian')) and r['tournament'] in ('Australian Open', 'Roland Garros', 'French Open', 'Wimbledon', 'US Open') else 3))
        return None, None

    c = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    G = {}
    for gid, key, start, home, away, ct in c.execute("SELECT game_id, key, start, home, away, close_t FROM games WHERE sport='tennis' AND close_t IS NOT NULL"):
        q = c.execute("SELECT ml_home, ml_away FROM quotes WHERE game_id=? AND t=? AND book='pinnacle'", (gid, ct)).fetchone()
        if not q or not q[0] or not q[1]: continue
        ph = (1 / q[0]) / (1 / q[0] + 1 / q[1])
        w, bo = result(start, home, away)
        if w is None: continue
        bo = 5 if ('atp' in key and any(x in key for x in ('aus_open', 'french_open', 'wimbledon', 'us_open'))) else 3
        G[gid] = dict(season=start[:4], ph=ph, home_s1=1 if w == 'a' else 0, bo=bo, key=key, home=home, away=away)
    print('matches with a Pinnacle close and a first-set result:', len(G), flush=True)

    def curve(p, season, bo):
        """first-set win rate for a player at match probability p: matches in other seasons within 2.5 points, same format"""
        xs = [(g['home_s1'] if abs(g['ph'] - p) <= .025 else None) for g in G.values() if g['season'] != season and g['bo'] == bo and abs(g['ph'] - p) <= .025]
        ys = [(1 - g['home_s1']) for g in G.values() if g['season'] != season and g['bo'] == bo and abs((1 - g['ph']) - p) <= .025]
        v = [x for x in xs if x is not None] + ys
        return (sum(v) / len(v), len(v)) if len(v) >= 40 else (None, len(v))

    CACHE = {}
    out = {}
    for tag, fn in (('10 minutes out', 'tennis_full.jsonl.gz'), ('2 hours out', 'tennis_early120.jsonl.gz')):
        path = os.path.join(ROOT, 'data', 'oddsapi', 'derivs', fn)
        if not os.path.exists(path): continue
        CAL = []; H = collections.defaultdict(lambda: [0, 0, 0.0])
        for l in lines(path):
            try: d = json.loads(l)
            except Exception: continue
            g = G.get(d['game_id'])
            if not g: continue
            k = (round(g['ph'] / .01) * .01, g['season'], g['bo'])
            if k not in CACHE: CACHE[k] = curve(k[0], g['season'], g['bo'])
            pc_h, n = CACHE[k]
            if pc_h is None: continue
            B = {b['key']: {o['name']: o['price'] for m in b['markets'] if m['key'] == 'h2h_s1' for o in m['outcomes']} for b in d['bookmakers']}
            P = B.get('pinnacle') or {}
            if d['home'] in P and d['away'] in P:
                q = (1 / P[d['home']]) / (1 / P[d['home']] + 1 / P[d['away']])
                CAL.append((min(max(q, .02), .98), min(max(pc_h, .02), .98), g['home_s1']))
            for bk, prices in B.items():
                if bk == 'betmgm': continue
                for side, nm, pc in (('home', d['home'], pc_h), ('away', d['away'], 1 - pc_h)):
                    pr = prices.get(nm)
                    if not pr: continue
                    ev = pc * pr - 1
                    if ev < 0.03: continue
                    won = g['home_s1'] if side == 'home' else 1 - g['home_s1']
                    fav = (g['ph'] >= .5) == (side == 'home')
                    for kk in ('all', f'book {NICE.get(bk, bk)}', f'season {g["season"]}', f'side {"match favourite" if fav else "match underdog"}', f'edge {"3-6%" if ev < .06 else "6%+"}',
                               f'format best of {g["bo"]}', 'US books (FD/Caesars/DK)' if bk in ('fanduel', 'williamhill_us', 'draftkings') else None):
                        if not kk: continue
                        x = H[kk]; x[0] += won; x[1] += 1 - won; x[2] += (pr - 1) if won else -1
        res = {}
        if len(CAL) > 200:
            lg = lambda p: math.log(p / (1 - p))
            X = np.array([[1, lg(q), lg(p)] for q, p, _ in CAL]); Y = np.array([y for *_, y in CAL], float); w = np.zeros(3)
            for _ in range(30):
                p_ = 1 / (1 + np.exp(-X @ w)); Hm = X.T @ (X * (p_ * (1 - p_))[:, None]) + 1e-6 * np.eye(3); w += np.linalg.solve(Hm, X.T @ (Y - p_))
            se = np.sqrt(np.diag(np.linalg.inv(Hm)))
            res['blend'] = dict(n=len(CAL), w_pin=round(float(w[1]), 2), w_curve=round(float(w[2]), 2), z=round(float(w[2] / se[2]), 2))
            print(f'{tag}: blend n={len(CAL)} Pinnacle {w[1]:+.2f} curve {w[2]:+.2f} (z {w[2] / se[2]:+.2f})')
        res['bets'] = {k: dict(w=a, l=b, roi=round(100 * u / max(1, a + b), 1)) for k, (a, b, u) in H.items()}
        for k, v in sorted(res['bets'].items()):
            if v['w'] + v['l'] >= 30: print(f"   {tag} | {k:34s} {v['w']}-{v['l']} {v['roi']:+.1f}%")
        out[tag] = res
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'tennis_set1_curve.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
