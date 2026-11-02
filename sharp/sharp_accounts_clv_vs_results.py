#!/usr/bin/env python3
"""Sharp accounts: did results track CLV, and does ranking accounts by past ROI work as well as by past CLV? (Sean, 11/2). Writes data/research/sharp_accounts_clv_vs_results.json."""
import os, sys, json, math, collections, datetime as dt
sys.path.insert(0, '/home/claude/sharp-tracker')
import sharp.flow_volume as V, sharp.exchange_backtest as EB
from sharp.sharp_accounts2 import Px
MK = V.poly_markets(); cut = MK[int(len(MK) * 2 / 3)][1]
W = collections.defaultdict(lambda: [0.0, 0, set(), 0.0])     # clv sum, n, games, roi sum (at their own fill price)
F = []
for i, (c, st) in enumerate(MK):
    L = V.poly_trades(c, st)
    if len(L) < 5: continue
    L4 = [x[:4] for x in L]; P = Px(L4); cl = P.at(st); ry = 1 if c['winner'] == c['outcomes'][0] else 0
    if cl is None: continue
    if st < cut:
        for t, py, usd, d, w in L:
            if usd < 100 or not w: continue
            price = py if d > 0 else 1 - py; won = ry if d > 0 else 1 - ry
            x = W[w]; x[0] += 100 * ((cl if d > 0 else 1 - cl) - price); x[1] += 1; x[2].add(c['cond']); x[3] += ((1 - price) / price if won else -1.0)
    else:
        F.append((c['cond'], c['market'], c['tag'], st, ry, cl, [(t, d, w, usd) for t, py, usd, d, w in L if usd >= 100 and w], P))
    if i % 5000 == 0: print(i, len(MK), flush=True)
sc = {w: x for w, x in W.items() if x[1] >= 30 and len(x[2]) >= 15}
by_clv = sorted(sc, key=lambda w: -sc[w][0] / sc[w][1]); by_roi = sorted(sc, key=lambda w: -sc[w][3] / sc[w][1])
def follow(S):
    R = []
    for cond, mk, tag, st, ry, cl, fills, P in F:
        f = next((f for f in fills if f[2] in S), None)
        if not f or f[0] + 300 >= st: continue
        px = P.at(f[0] + 300)
        if px is None: continue
        d = f[1]; price = px if d > 0 else 1 - px
        if not 0.05 < price < 0.95: continue
        q = cl if d > 0 else 1 - cl; won = ry if d > 0 else 1 - ry
        R.append(dict(price=price, close=q, clv=100 * (q - price), won=won, roi=(1 - price) / price if won else -1.0, exp=q / price - 1))
    return R
def s(R):
    n = len(R); roi = sum(r['roi'] for r in R) / n; sd = (sum((r['roi'] - roi) ** 2 for r in R) / (n - 1)) ** 0.5
    return dict(n=n, clv=round(sum(r['clv'] for r in R) / n, 2), roi=round(100 * roi, 1), roi_z=round(roi / (sd / math.sqrt(n)), 2),
                exp_roi_from_close=round(100 * sum(r['exp'] for r in R) / n, 1), win=round(sum(r['won'] for r in R) / n, 3),
                exp_win_from_close=round(sum(r['close'] for r in R) / n, 3), exp_win_at_price=round(sum(r['price'] for r in R) / n, 3))
out = {}
R = follow(set(by_clv[:200])); out['top200 by train CLV: all'] = s(R)
for lo, hi, nm in ((-99, 0, 'CLV < 0'), (0, 2, 'CLV 0-2'), (2, 5, 'CLV 2-5'), (5, 99, 'CLV 5+')):
    B = [r for r in R if lo <= r['clv'] < hi]
    if len(B) > 10: out[f'top200 by CLV, bets with {nm}'] = s(B)
for nm, L_ in (('top200 by train ROI', by_roi[:200]), ('top1000 by train ROI', by_roi[:1000]), ('top1000 by train CLV', by_clv[:1000]), ('bottom200 by train ROI', by_roi[-200:])):
    out[nm] = s(follow(set(L_)))
ov = len(set(by_clv[:200]) & set(by_roi[:200])); out['overlap top200 CLV vs ROI lists'] = ov
# do train CLV and train ROI agree across accounts?
import statistics
xs = [sc[w][0] / sc[w][1] for w in sc]; ys = [100 * sc[w][3] / sc[w][1] for w in sc]
mx, my = statistics.mean(xs), statistics.mean(ys)
out['train corr(account CLV, account ROI)'] = round(sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)), 3)
json.dump(out, open('/home/claude/sharp-tracker/data/research/sharp_accounts_clv_vs_results.json', 'w'), indent=1)
for k, v in out.items(): print(k, v)
