#!/usr/bin/env python3
"""Curve rules tested on an EARLY snapshot (11/6): derivative files pulled N minutes before the start with that moment's full-game total
and spread (data/oddsapi/derivs/<sport>_early<N>.jsonl.gz or <sport>_curve_t<N>m.jsonl.gz). For each derivative market, the curve price
(sharp/curve_live.curve, leave-one-season-out pool) vs Pinnacle's no-vig at the same line; bets on the side the curve prefers at gaps of
4 / 7 points, graded on period scores at Pinnacle's price and at the best of FD / Caesars / DK. Also the blend test (does the curve add
information to Pinnacle at that moment?). Usage: python3 sharp/curve_early.py nba data/oddsapi/derivs/nba_early360.jsonl.gz"""
import os, sys, json, math, sqlite3, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.curve_live as CL
from sharp.gzlines import lines
from sharp.deriv_curve import season, parse_mk, PER
US = ('fanduel', 'williamhill_us', 'draftkings')


def main():
    sp, path = sys.argv[1], sys.argv[2]
    c = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    LS = json.load(open(os.path.join(ROOT, 'data', 'state', 'linescores.json'))).get(sp, {})
    RES = {r[0]: r[1:] for r in c.execute("SELECT game_id, espn_id, home_score, away_score FROM results")}
    full = CL.pool(sp); bys = {se: [p for p in full[0] if p[0] != se] for se in {p[0] for p in full[0]}}
    H = collections.defaultdict(lambda: [0, 0, 0.0]); CAL = []; n = 0
    for l in lines(path):
        try: d = json.loads(l)
        except Exception: continue
        if d['game_id'] not in RES: continue
        eid, hs, as_ = RES[d['game_id']]; ls = LS.get(str(eid))
        if hs is None or not ls or not ls['h'] or not ls['a']: continue
        B = {b['key']: {m['key']: m['outcomes'] for m in b['markets']} for b in d['bookmakers']}
        pin = B.get('pinnacle') or {}
        T = next((o['point'] for o in pin.get('totals', []) if o['name'] == 'Over'), None)
        S = next((o['point'] for o in pin.get('spreads', []) if o['name'] == d['home']), None)
        if T is None or S is None: continue
        n += 1; se = season(sp, d['start'])
        for mk, outs in pin.items():
            kind, per = parse_mk(mk)
            if kind not in ('total', 'team') or mk in ('totals',): continue
            if kind == 'total' and per not in PER.get(sp, {}): continue
            prd = PER[sp][per] if per else None
            if kind == 'team' and per is not None: continue          # full-game team totals only
            G = {}
            for o in outs:
                if o.get('point') is None or o['name'] not in ('Over', 'Under'): continue
                team = None
                if kind == 'team':
                    team = 'home' if o.get('description') == d['home'] else 'away' if o.get('description') == d['away'] else None
                    if not team: continue
                G.setdefault((team, o['point']), {})[o['name'].lower()] = o['price']
            for (team, ln), pr in G.items():
                if 'over' not in pr or 'under' not in pr: continue
                CL._POOL[sp] = (bys.get(se, full[0]), full[1], full[2]); vals = CL.curve(sp, T, S, 'team' if team else 'total', prd, team); CL._POOL[sp] = full
                if len(vals) < 100: continue
                if team: v = hs if team == 'home' else as_
                else:
                    i0, k = prd
                    if len(ls['h']) < i0 + k or len(ls['a']) < i0 + k: continue
                    v = sum(ls['h'][i0:i0 + k]) + sum(ls['a'][i0:i0 + k])
                q_over = (1 / pr['over']) / (1 / pr['over'] + 1 / pr['under']); pc_over = CL.probs(vals, ln, 'over')
                if v != ln: CAL.append((mk, min(max(q_over, .02), .98), min(max(pc_over, .02), .98), 1 if v > ln else 0))
                for side in ('over', 'under'):
                    q = q_over if side == 'over' else 1 - q_over; pc = CL.probs(vals, ln, side); gap = pc - q
                    if gap < 0.04: continue
                    won = 0.5 if v == ln else 1 if (v > ln) == (side == 'over') else 0
                    band = 'gap 7+' if gap >= 0.07 else 'gap 4-7'
                    for k in (f'{mk} | {band}', f'{mk} | {band} | {side}', f'{mk} | {band} | {se}'):
                        x = H[k]; x[0] += won == 1; x[1] += won == 0; x[2] += (pr[side] - 1) if won == 1 else -1 if won == 0 else 0
                    us = [o['price'] for b in US for o in (B.get(b) or {}).get(mk, []) if o['name'].lower() == side and o.get('point') == ln and (not team or o.get('description') == (d['home'] if team == 'home' else d['away']))]
                    if us:
                        x = H[f'{mk} | {band} | at best of FD/Caesars/DK']; bp = max(us); x[0] += won == 1; x[1] += won == 0; x[2] += (bp - 1) if won == 1 else -1 if won == 0 else 0
    print(f'{sp} {os.path.basename(path)}: {n} games')
    lg = lambda p: math.log(p / (1 - p)); R = dict(games=n, blend={}, bets={})
    for mk in sorted({x[0] for x in CAL}):
        Rw = [x for x in CAL if x[0] == mk]
        if len(Rw) < 300: continue
        X = np.array([[1.0, lg(q), lg(p)] for _, q, p, _ in Rw]); Y = np.array([y for *_, y in Rw], dtype=float); w = np.zeros(3)
        for _ in range(25):
            p_ = 1 / (1 + np.exp(-X @ w)); Hm = X.T @ (X * (p_ * (1 - p_))[:, None]) + 1e-6 * np.eye(3); w += np.linalg.solve(Hm, X.T @ (Y - p_))
        se_ = np.sqrt(np.diag(np.linalg.inv(Hm)))
        R['blend'][mk] = dict(n=len(Rw), w_pin=round(float(w[1]), 2), w_curve=round(float(w[2]), 2), z=round(float(w[2] / se_[2]), 2))
        print(f'   blend {mk:22s} n={len(Rw):5d}  Pinnacle {w[1]:+.2f}  curve {w[2]:+.2f} (z {w[2] / se_[2]:+.2f})')
    for k, (w, l, u) in sorted(H.items()):
        R['bets'][k] = dict(w=w, l=l, roi=round(100 * u / max(1, w + l), 1))
        if w + l >= 40: print(f'   {k:58s} {w}-{l} {100 * u / max(1, w + l):+.1f}%')
    json.dump(R, open(os.path.join(ROOT, 'data', 'research', f'curve_early_{sp}_{os.path.basename(path).split(".")[0]}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
