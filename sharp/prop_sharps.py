#!/usr/bin/env python3
"""Polymarket sharps on player props (Sean, 11/2). Props are thinner and slower than game lines; does a proven account matter more there,
and are the prop sharps the same people as the game-line sharps?

Markets: settled two-way prop markets with $2k+ volume (data/polymarket/history/catalog_props.jsonl: NBA points / rebounds / assists,
UFC method / distance, NFL touchdowns / yards, MLB NRFI and player props, soccer goalscorers, WNBA). Split by start time: first two thirds
train, last third test.
Groups (scored on train only):
  GAME-LINE top 200   accounts' game-line CLV before the cut (the live list's method, 30+ fills on 15+ games)
  PROP top 50         accounts' prop CLV before the cut (15+ fills on 8+ markets; props are thin)
  PROP bottom 50      (check)
  ANY $100+ fill      every account's first $100+ fill per market (baseline: is following anyone on props worth anything?)
Follow: first $100+ fill by a member per test market, entry at the two-sided mid 5 minutes later; CLV vs Polymarket's close and ROI.
By sport for NBA and UFC (the two with volume). Writes data/research/prop_sharps.json. Usage: python3 sharp/prop_sharps.py"""
import os, sys, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V
from sharp.sharp_accounts2 import Px
PH = V.PH; LAG = 300


def props():
    out = []
    for l in open(os.path.join(PH, 'catalog_props.jsonl')):
        c = json.loads(l)
        if os.path.exists(os.path.join(PH, 'trades', f"{c['cond']}.jsonl.gz")):
            out.append((c, dt.datetime.fromisoformat(c['start'].replace(' ', 'T').replace('+00', '+00:00')).timestamp()))
    return sorted(out, key=lambda x: x[1])


def stat(R):
    n = len(R)
    if n < 10: return dict(n=n)
    def zz(x):
        m = sum(x) / len(x); s = (sum((v - m) ** 2 for v in x) / max(1, len(x) - 1)) ** .5
        return round(m, 3), round(m / (s / math.sqrt(len(x))), 2) if s else None
    c, cz = zz([r[0] for r in R]); r_, rz = zz([r[1] for r in R])
    return dict(n=n, clv=round(c, 2), clv_z=cz, roi=round(100 * r_, 1), roi_z=rz)


def main():
    PM = props(); cut = PM[int(len(PM) * 2 / 3)][1]
    print(f"[prop_sharps] {len(PM)} prop markets with trades; test from {dt.datetime.fromtimestamp(cut, dt.timezone.utc):%Y-%m-%d}", flush=True)
    G = collections.defaultdict(lambda: [0.0, 0, set()])
    for i, (c, st) in enumerate(V.poly_markets()):                     # game-line scores before the same cut
        if st >= cut: break
        L = V.poly_trades(c, st)
        if len(L) < 5: continue
        cl = Px([x[:4] for x in L]).at(st)
        if cl is None: continue
        for t, py, usd, d, w in L:
            if usd < 100 or not w: continue
            g = G[w]; g[0] += 100 * ((cl if d > 0 else 1 - cl) - (py if d > 0 else 1 - py)); g[1] += 1; g[2].add(c['cond'])
        if i % 5000 == 0: print(f"[prop_sharps] game lines {i}", flush=True)
    gen = sorted([w for w, x in G.items() if x[1] >= 30 and len(x[2]) >= 15], key=lambda w: -G[w][0] / G[w][1]); gen200 = set(gen[:200])
    P = collections.defaultdict(lambda: [0.0, 0, set()]); tests = []
    for c, st in PM:
        L = V.poly_trades(c, st)
        if len(L) < 5: continue
        L4 = [x[:4] for x in L]; X = Px(L4); cl = X.at(st)
        if cl is None: continue
        if st < cut:
            for t, py, usd, d, w in L:
                if usd < 100 or not w: continue
                p = P[w]; p[0] += 100 * ((cl if d > 0 else 1 - cl) - (py if d > 0 else 1 - py)); p[1] += 1; p[2].add(c['cond'])
            continue
        ry = 1 if c['winner'] == c['outcomes'][0] else 0; first = {}
        for t, py, usd, d, w in L:
            if usd >= 100 and w and w not in first: first[w] = (t, d)
        ent = {}
        for w, (t, d) in first.items():
            if t + LAG >= st: continue
            px = X.at(t + LAG)
            if px is None: continue
            price = px if d > 0 else 1 - px
            if 0.05 < price < 0.95: ent[w] = (t, d, price)
        tests.append((c['tag'], c['stat'], ry, cl, ent))
    pr = sorted([w for w, x in P.items() if x[1] >= 15 and len(x[2]) >= 8], key=lambda w: -P[w][0] / P[w][1])
    groups = {'GAME-LINE top 200': gen200, 'PROP top 50': set(pr[:50]), 'PROP top 50 not in game-line top 200': set(pr[:50]) - gen200,
              'PROP bottom 50': set(pr[-50:]) if len(pr) >= 150 else set(), 'ANY $100+ fill': None}
    res = dict(prop_markets=len(PM), test_markets=len(tests), prop_scored=len(pr), overlap_prop50_game200=len(set(pr[:50]) & gen200), cells={})
    for name, grp in groups.items():
        for part in ('all', 'nba', 'ufc'):
            R = []
            for tag, stt, ry, cl, ent in tests:
                if part != 'all' and tag != part: continue
                h = sorted(v for w, v in ent.items() if grp is None or w in grp)
                if not h: continue
                t, d, price = h[0]; won = ry if d > 0 else 1 - ry
                R.append((100 * ((cl if d > 0 else 1 - cl) - price), (1 - price) / price if won else -1.0))
            res['cells'][f'{name} | {part}'] = dict(stat(R), members=None if grp is None else len(grp))
    json.dump(res, open(os.path.join(ROOT, 'data', 'research', 'prop_sharps.json'), 'w'), indent=1)
    print({k: v for k, v in res.items() if k != 'cells'})
    for k, v in res['cells'].items(): print(f"  {k:52} {v}")


if __name__ == '__main__':
    main()
