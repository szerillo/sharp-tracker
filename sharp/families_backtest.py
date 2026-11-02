#!/usr/bin/env python3
"""Backtest of the watch's Strongest rule (Sean, 11/2: "are we really able to backtest where 3 of 3 or 2 of 3 would have triggered?").

Long version, Polymarket only (settled game moneylines / spreads / totals with $10k+ volume, mid-2024 to now): every family is rebuilt
from the market's own public tape, as of one hour before the start (T-1h):
  ACCOUNTS  a top-200 account (mean CLV vs close of its $100+ pregame fills, 30+ fills on 15+ games, scored walk-forward on games
            before the period: cutoffs 2025-07-01, 2025-11-01, 2026-03-01, 2026-09-01) has a $100+ fill on a side before T-1h, and none
            is on the other side
  PRICE     the two-sided mid moved 4+ pts from its first two-sided price to T-1h (stands in for the live Kalshi 4+ move; the Pinnacle
            sharp move and the Kalshi bet back cannot be rebuilt this far back)
  MONEY     big vs small before T-1h, as live: $500+ fills net $1,000+ one way, $50-and-under fills net the other way, risk-equivalent,
            above the display floor ($10k traded, $2.5k big net)
Classes per market (one side): 3 of 3; accounts + price; accounts + money; accounts only; price + money without accounts; and any
other-family signal with an account against. Entry at the T-1h two-sided mid; graded on CLV vs Polymarket's close and on the result.
Only markets that start after the first cutoff are graded. Writes data/research/families_backtest.json.
Usage: python3 sharp/families_backtest.py"""
import os, sys, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V
from sharp.sharp_accounts2 import Px
CUTS = [dt.datetime.fromisoformat(d + 'T00:00:00+00:00').timestamp() for d in ('2025-07-01', '2025-11-01', '2026-03-01', '2026-09-01')]
BIG, SMALL, DIV, SHOW_T, SHOW_B, MOVE = 500.0, 50.0, 1000.0, 10000.0, 2500.0, 4.0


def stat(R):
    n = len(R)
    if n < 10: return dict(n=n)
    def zz(x):
        m = sum(x) / len(x); s = (sum((v - m) ** 2 for v in x) / max(1, len(x) - 1)) ** .5
        return round(m, 3), round(m / (s / math.sqrt(len(x))), 2) if s else None
    c, cz = zz([r[0] for r in R]); r_, rz = zz([r[1] for r in R])
    return dict(n=n, clv=round(c, 2), clv_z=cz, roi=round(100 * r_, 1), roi_z=rz)


def main():
    MK = [m for m in V.poly_markets() if m[0]['tag'] != 'ufc']
    G = collections.defaultdict(lambda: [0.0, 0, set()]); top = set(); ci = 0
    T = collections.defaultdict(list); days = collections.defaultdict(set)
    for i, (c, st) in enumerate(MK):
        while ci < len(CUTS) and st >= CUTS[ci]:                       # walk forward: rescore at each cutoff on everything before it
            top = set(sorted([w for w, x in G.items() if x[1] >= 30 and len(x[2]) >= 15], key=lambda w: -G[w][0] / G[w][1])[:200]); ci += 1
        L = V.poly_trades(c, st)
        if len(L) < 5: continue
        L4 = [x[:4] for x in L]; X = Px(L4); cl = X.at(st)
        if cl is None: continue
        if ci > 0:
            E = st - 3600; pre = [x for x in L if x[0] < E]; px = X.at(E)
            if pre and px is not None:
                acc = {1: set(), -1: set()}
                for t, py, usd, d, w in pre:
                    if usd >= 100 and w in top: acc[d].add(w)
                a_side = 1 if acc[1] and not acc[-1] else (-1 if acc[-1] and not acc[1] else 0); a_against = bool(acc[1] and acc[-1])
                p0 = next((X.at(x[0]) for x in pre if X.at(x[0]) is not None), None)
                p_side = 0 if p0 is None or abs(100 * (px - p0)) < MOVE else (1 if px > p0 else -1)
                tot = sum(x[2] for x in pre)
                bn = sum(x[2] * x[3] for x in pre if x[2] >= BIG); sn = sum(x[2] * x[3] for x in pre if x[2] <= SMALL)
                m_side = (1 if bn > 0 else -1) if abs(bn) >= max(DIV, SHOW_B) and sn != 0 and (bn > 0) != (sn > 0) and tot >= SHOW_T else 0
                sides = {s for s in (a_side, p_side, m_side) if s}
                def grade(d):
                    price = px if d > 0 else 1 - px
                    if not 0.05 < price < 0.95: return None
                    won = (1 if c['winner'] == c['outcomes'][0] else 0) if d > 0 else (0 if c['winner'] == c['outcomes'][0] else 1)
                    return (100 * ((cl if d > 0 else 1 - cl) - price), (1 - price) / price if won else -1.0)
                cls = None
                if len(sides) == 1:
                    d = next(iter(sides)); fams = (a_side == d) + (p_side == d) + (m_side == d)
                    if a_side: cls = '3 of 3' if fams == 3 else ('accounts + price' if p_side else 'accounts + money' if m_side else 'accounts only')
                    elif p_side and m_side: cls = 'price + money, no accounts' + (' (an account against)' if a_against else '')
                    elif p_side: cls = 'price only' + (' (an account against)' if a_against else '')
                    elif m_side: cls = 'money only' + (' (an account against)' if a_against else '')
                if cls:
                    g = grade(d)
                    if g:
                        T[cls].append(g); days[cls].add(c['date'])
                        if a_side: T['STRONGEST (accounts + 1 or 2 others)' if fams >= 2 else '_acc1'].append(g)
                        T[f"{cls} | {c['tag'] if c['tag'] in ('nba', 'nfl', 'nhl', 'cfb', 'mlb', 'wnba') else 'soccer'}"].append(g)
        for t, py, usd, d, w in L:                                       # add to the record only after the market is graded
            if usd < 100 or not w: continue
            g_ = G[w]; g_[0] += 100 * ((cl if d > 0 else 1 - cl) - (py if d > 0 else 1 - py)); g_[1] += 1; g_[2].add(c['cond'])
        if i % 10000 == 0: print(f"[families] {i}/{len(MK)}", flush=True)
    span = (MK[-1][1] - CUTS[0]) / 86400
    out = dict(graded_from='2025-07-01', days=round(span), cells={k: dict(stat(v), per_day=round(len(v) / span, 1)) for k, v in sorted(T.items()) if not k.startswith('_')})
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'families_backtest.json'), 'w'), indent=1)
    for k, v in out['cells'].items():
        if '|' not in k: print(f"  {k:52} {v}")
    print('  -- by sport --')
    for k, v in out['cells'].items():
        if '|' in k and v.get('n', 0) >= 30: print(f"  {k:52} {v}")


if __name__ == '__main__':
    main()
