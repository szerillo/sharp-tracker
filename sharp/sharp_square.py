#!/usr/bin/env python3
"""Follow the sharps, fade the squares, on Polymarket (Sean, 11/2: "I do think there's signal in bad bettors too ... combine following
the sharps and fading the squares").

Accounts scored on train (markets that started before the round-3 cut, 2026-09-01): per account, pregame fills of $100+ (risk-equivalent):
mean CLV vs Polymarket's two-sided close, and flat ROI at their own fill price; 30+ fills on 15+ games to be scored.
  sharp  = top 200 by train CLV (round 3)
  square = three definitions, each tested: bottom 500 by train ROI / bottom 500 by train CLV / both (train ROI and CLV both negative,
           bottom 500 by ROI among those)
Holdout (Sep 1 on), per market, entry at the two-sided mid 5 minutes after the triggering fill (never the account's own price),
first trigger per market and class, graded on CLV vs Polymarket's close and on the result:
  FOLLOW      a sharp's $100+ fill: bet its side
  FADE        a square's $100+ fill: bet the other side
  BOTH AGREE  a sharp on side X and a square on the other side (whichever comes second triggers)
  CLASH       a sharp and a square on the same side (bet the sharp side; shows whether squares spoil a sharp bet)
Also writes data/research/poly_wallet_scores.json with CLV and ROI per scored account (the live signal reads it).
Usage: python3 sharp/sharp_square.py"""
import os, sys, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V
from sharp.sharp_accounts2 import Px
LAG = 300


def stat(R):
    n = len(R)
    if not n: return None
    roi = [r['roi'] for r in R]; mu = sum(roi) / n; sd = (sum((x - mu) ** 2 for x in roi) / max(1, n - 1)) ** 0.5
    cv = [r['clv'] for r in R]; cm = sum(cv) / n; csd = (sum((x - cm) ** 2 for x in cv) / max(1, n - 1)) ** 0.5
    return dict(n=n, clv=round(cm, 2), clv_z=round(cm / (csd / math.sqrt(n)), 2) if csd else None, roi=round(100 * mu, 1),
                roi_z=round(mu / (sd / math.sqrt(n)), 2) if sd else None, win=round(sum(r['won'] for r in R) / n, 3), price=round(sum(r['price'] for r in R) / n, 3))


def main():
    MK = V.poly_markets(); cut = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc).timestamp()
    W = collections.defaultdict(lambda: [0.0, 0, set(), 0.0]); H = []
    for i, (c, st) in enumerate(MK):
        L = V.poly_trades(c, st)
        if len(L) < 5: continue
        P = Px([x[:4] for x in L]); cl = P.at(st); ry = 1 if c['winner'] == c['outcomes'][0] else 0
        if cl is None: continue
        if st < cut:
            for t, py, usd, d, w in L:
                if usd < 100 or not w: continue
                price = py if d > 0 else 1 - py; won = ry if d > 0 else 1 - ry; x = W[w]
                x[0] += 100 * ((cl if d > 0 else 1 - cl) - price); x[1] += 1; x[2].add(c['cond']); x[3] += (1 - price) / price if won else -1.0
        else:
            H.append((c['tag'], c['market'], st, ry, cl, [(t, d, w) for t, py, usd, d, w in L if usd >= 100 and w], P))
        if i % 5000 == 0: print(f"[sharp_square] {i}/{len(MK)}", flush=True)
    sc = {w: dict(clv=x[0] / x[1], roi=100 * x[3] / x[1], fills=x[1], games=len(x[2])) for w, x in W.items() if x[1] >= 30 and len(x[2]) >= 15}
    by_clv = sorted(sc, key=lambda w: -sc[w]['clv']); by_roi = sorted(sc, key=lambda w: -sc[w]['roi'])
    json.dump(dict(train_cut='2026-09-01', n=len(sc), wallets=[dict(w=w, clv=round(sc[w]['clv'], 2), roi=round(sc[w]['roi'], 1), fills=sc[w]['fills'], games=sc[w]['games'],
                                                               clv_rank=i + 1) for i, w in enumerate(by_clv)]),
              open(os.path.join(ROOT, 'data', 'research', 'poly_wallet_scores.json'), 'w'))
    sharp = set(by_clv[:200])
    neg = [w for w in by_roi if sc[w]['roi'] < 0 and sc[w]['clv'] < 0]
    SQ = {'square = bottom 500 by ROI': set(by_roi[-500:]), 'square = bottom 500 by CLV': set(by_clv[-500:]),
          'square = ROI and CLV both negative (worst 500 by ROI)': set(neg[-500:])}
    sharp_n = len(sharp)
    out = dict(scored=len(sc), sharp=sharp_n, squares={k: len(v) for k, v in SQ.items()}, overlap_sharp_square={k: len(v & sharp) for k, v in SQ.items()}, cells={})
    T = collections.defaultdict(list)
    for tag, mk, st, ry, cl, fills, P in H:
        def add(key, t, d):
            if t + LAG >= st: return
            px = P.at(t + LAG)
            if px is None: return
            price = px if d > 0 else 1 - px
            if not 0.05 < price < 0.95: return
            q = cl if d > 0 else 1 - cl; won = ry if d > 0 else 1 - ry
            T[key].append(dict(clv=100 * (q - price), roi=(1 - price) / price if won else -1.0, won=won, price=price, tag=tag, mk=mk))
        f = next((f for f in fills if f[2] in sharp), None)
        if f: add('FOLLOW sharp', f[0], f[1])
        for name, S in SQ.items():
            g = next((f for f in fills if f[2] in S and f[2] not in sharp), None)
            if g: add(f'FADE {name}', g[0], -g[1])
            # combined: first moment both a sharp and a square have bet (opposite sides = agree, same side = clash)
            sh = {}; sq = {}; done = set()
            for t, d, w in fills:
                if w in sharp: sh.setdefault(d, t)
                elif w in S: sq.setdefault(d, t)
                for ds in list(sh):
                    if -ds in sq and 'agree' not in done: add(f'BOTH AGREE ({name})', t, ds); done.add('agree')
                    if ds in sq and 'clash' not in done: add(f'CLASH, bet sharp side ({name})', t, ds); done.add('clash')
    for k, R in sorted(T.items()):
        out['cells'][k] = stat(R)
        for mk in ('ml', 'spread', 'total'):
            s_ = stat([r for r in R if r['mk'] == mk])
            if s_ and s_['n'] >= 30: out['cells'][f'{k} | {mk}'] = s_
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'sharp_square.json'), 'w'), indent=1)
    print({k: v for k, v in out.items() if k != 'cells'})
    for k, v in out['cells'].items(): print(f"  {k:70} {v}")


if __name__ == '__main__':
    main()
