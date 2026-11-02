#!/usr/bin/env python3
"""Rebuild the live Polymarket sharp-account list (data/state/poly_sharps_list.json) on all settled history to date, with the method
that held out of sample (docs/flow_volume_2026-11-02.md): per account, $100+ (risk-equivalent) pregame fills on settled game markets,
mean CLV vs Polymarket's two-sided close, 30+ fills on 15+ games; rank by CLV, keep the top 200. Needs the local history pull
(loggers/polymarket_history.py catalog + trades), so it is run by hand (monthly), not in CI.
Usage: python3 sharp/poly_rescore.py"""
import os, sys, json, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V
from sharp.sharp_accounts2 import Px


def main():
    W = collections.defaultdict(lambda: [0.0, 0, set(), 0.0]); MK = V.poly_markets(); last = 0
    for i, (c, st) in enumerate(MK):
        if c['tag'] == 'ufc': continue
        L = V.poly_trades(c, st)
        if len(L) < 5: continue
        P = Px([x[:4] for x in L]); cl = P.at(st); ry = 1 if c['winner'] == c['outcomes'][0] else 0
        if cl is None: continue
        last = max(last, st)
        for t, py, usd, d, w in L:
            if usd < 100 or not w: continue
            price = py if d > 0 else 1 - py; won = ry if d > 0 else 1 - ry; x = W[w]
            x[0] += 100 * ((cl if d > 0 else 1 - cl) - price); x[1] += 1; x[2].add(c['cond']); x[3] += (1 - price) / price if won else -1.0
        if i % 5000 == 0: print(f"[poly_rescore] {i}/{len(MK)}", flush=True)
    sc = {w: x for w, x in W.items() if x[1] >= 30 and len(x[2]) >= 15}
    ranked = sorted(sc, key=lambda w: -sc[w][0] / sc[w][1])
    out = dict(built=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), history_through=dt.datetime.fromtimestamp(last, dt.timezone.utc).strftime('%Y-%m-%d'),
               scored=len(sc), method='mean CLV vs Polymarket close of $100+ pregame fills, 30+ fills on 15+ games, top 200',
               accounts=[dict(w=w, rank=i + 1, clv=round(sc[w][0] / sc[w][1], 2), roi=round(100 * sc[w][3] / sc[w][1], 1), fills=sc[w][1], games=len(sc[w][2]))
                         for i, w in enumerate(ranked[:200])])
    json.dump(out, open(os.path.join(ROOT, 'data', 'state', 'poly_sharps_list.json'), 'w'), indent=0)
    print(f"[poly_rescore] {len(sc)} accounts scored through {out['history_through']}; top 200 written (CLV floor {out['accounts'][-1]['clv']})")


if __name__ == '__main__':
    main()
