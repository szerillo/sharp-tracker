#!/usr/bin/env python3
"""Pushback timing (Sean, 11/9: when is it safe to lock a bet in). When does a Kalshi 4+ point move against a side arrive, and what does a later one cost a bet already placed? Kalshi history Aug 24 - Oct 29,
main line per game and market type (most dollars). Price = two-sided mid (last yes-taker and last no-taker within 2h), sampled every 10 min.
Open = first two-sided mid. 'Against side S by time t' = the sampled mid has been 4+ pts the other way from the open at some point by t
(the live 'Kalshi move against' tag is sticky the same way). Both sides of every market are scored.
Usage: python3 sharp/kalshi_pushback.py out.json; summary in docs/pushback_2026-11-09.md."""
import sys, os, math, collections, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from flow_split import market_rows
rows = [r for r in market_rows() if r[0] == 'Kalshi']
best = {}
for r in rows:
    usd = sum(x[2] for x in r[6] if x[0] < r[4])
    if r[3] not in best or usd > best[r[3]][0]: best[r[3]] = (usd, r)
print('markets', len(rows), 'main lines', len(best), file=sys.stderr)
CK = (24, 12, 6, 3, 2, 1, 0.5, 0.25); MV = 0.04; STEP = 600
out = []
for usd, (v, sp, mt, gk, start, ry, L) in best.values():
    if usd < 2000: continue
    pre = sorted(x for x in L if x[0] < start)
    if len(pre) < 10: continue
    ly = ln = None; i = 0; t = pre[0][0]; samp = []
    while t <= start:
        while i < len(pre) and pre[i][0] <= t:
            if pre[i][3] > 0: ly = pre[i]
            else: ln = pre[i]
            i += 1
        if ly and ln and abs(ly[0] - ln[0]) <= 7200: samp.append((t, (ly[1] + ln[1]) / 2))
        t += STEP
    if len(samp) < 6: continue
    op = samp[0][1]
    # first time the move reached 4+ toward yes / toward no
    up = next((t for t, p in samp if p - op >= MV), None); dn = next((t for t, p in samp if op - p >= MV), None)
    def at(T):
        x = [p for t, p in samp if t <= T]; return x[-1] if x else None
    for side in ('yes', 'no'):
        ag = dn if side == 'yes' else up          # move against this side
        won = ry if side == 'yes' else 1 - ry
        for X in CK:
            T = start - X * 3600; p = at(T)
            if p is None or samp[0][0] > T: continue
            ps = p if side == 'yes' else 1 - p
            if not 0.05 < ps < 0.95: continue
            if ag is not None and ag <= T: continue          # already against at the checkpoint: held, not in this group
            later = ag is not None
            q = at(start - 900); qs = None if q is None else (q if side == 'yes' else 1 - q)
            out.append(dict(sp=sp, mt=mt, X=X, later=later, lag=None if not later else (start - ag) / 3600, ps=ps, qs=qs, won=won,
                            month=gk.split('|')[1][:7]))
json.dump(out, open(sys.argv[1], 'w'))
print('rows', len(out), file=sys.stderr)
