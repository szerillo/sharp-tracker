#!/usr/bin/env python3
"""Polymarket sharp accounts, round 2 cuts (Sean, 11/2: "bigger than $100 and isolate? head-to-head against one another? multiple
positions on the game? a variety of other ways of looking at it").

Accounts are ranked on train (games before 2026-09-01; data/research/poly_wallet_scores.json from sharp/sharp_accounts.py: mean CLV
of their $100+ pregame fills vs Polymarket's close, 30+ fills on 15+ games). Everything below is on holdout markets only (Sep 1 on).
Entry is always the two-sided mid 5 minutes after the triggering fill (or at the stated time), never the account's own price.
Graded on CLV vs Polymarket's pregame close (points) and the result (flat 1u ROI at entry).

Cuts:
  A  size of the triggering fill, isolated bands: $100-500 / $500-2k / $2k-10k / $10k+ (top 200, first fill in that band per market)
  B  account rank band: 1-50 / 51-200 / 201-1000 (first $100+ fill per market)
  C  agreement at the trigger: other top-200 accounts already on the same side only / on the other side (head-to-head) / none yet
  D  head-to-head markets: top-200 money on both sides before T-15m; bet the side with more top-200 dollars, or the better-ranked
     account's side, entering at T-15m
  E  multiple positions: the account's 1st fill vs its 2nd same-side fill (adding) vs a fill after it already bet the other side (flip)
  F  net position: no timing, bet the side of the top-200 accounts' net dollars at T-6h / T-1h / T-15m (net $1k+ / $5k+), entry then
  G  timing of the trigger fill: 24h+ / 6-24h / 1-6h / under 1h before the start
  H  market type and price: ml / spread / total; followed side priced under 40c / 40-60c / over 60c
Writes data/research/sharp_accounts2.json. Usage: python3 sharp/sharp_accounts2.py"""
import os, sys, json, math, bisect, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V
LAG = 300


class Px:
    """Two-sided mid at any time (same rule as exchange_backtest.px_at: last yes-buy and last no-buy within 2h, averaged), O(log n)."""
    def __init__(self, L4):
        self.t = [x[0] for x in L4]; ly = ln = None; self.ly = []; self.ln = []
        for i, x in enumerate(L4):
            if x[3] > 0: ly = i
            else: ln = i
            self.ly.append(ly); self.ln.append(ln)
        self.L = L4

    def at(self, cut):
        i = bisect.bisect_right(self.t, cut) - 1
        if i < 0: return None
        a, b = self.ly[i], self.ln[i]
        if a is None or b is None or abs(self.L[a][0] - self.L[b][0]) > 7200: return None
        return (self.L[a][1] + self.L[b][1]) / 2


def stat(R):
    out = {}
    for key in ('clv', 'roi'):
        x = [r[key] for r in R if r.get(key) is not None]
        if not x: continue
        mu = sum(x) / len(x); sd = (sum((v - mu) ** 2 for v in x) / max(1, len(x) - 1)) ** 0.5
        out[key] = round(mu * (100 if key == 'roi' else 1), 2); out[key + '_z'] = round(mu / (sd / math.sqrt(len(x))), 2) if sd and len(x) > 1 else None
        out['n'] = len(x)
    return out


def main():
    S = json.load(open(os.path.join(ROOT, 'data', 'research', 'poly_wallet_scores.json')))
    rank = {w['w']: i + 1 for i, w in enumerate(S['wallets'])}; nsc = len(rank)
    cut = dt.datetime.fromisoformat(S['train_cut'] + 'T00:00:00+00:00').timestamp()
    MK = [x for x in V.poly_markets() if x[1] >= cut]
    T = collections.defaultdict(list)
    def rec(key, px, d, ry, cl):
        if px is None: return
        price = px if d > 0 else 1 - px
        if not 0.05 < price < 0.95: return
        T[key].append(dict(clv=None if cl is None else 100 * ((cl if d > 0 else 1 - cl) - price), roi=(1 - price) / price if (ry if d > 0 else 1 - ry) else -1.0))
    for i, (c, st) in enumerate(MK):
        L = V.poly_trades(c, st)
        if len(L) < 5: continue
        L4 = [x[:4] for x in L]; P = Px(L4); cl = P.at(st); ry = 1 if c['winner'] == c['outcomes'][0] else 0
        fills = [(t, d, usd, rank[w]) for t, py, usd, d, w in L if w in rank and usd >= 100]
        top = [f for f in fills if f[3] <= 200]
        # A: size bands, top 200, first fill in band
        for lo, hi, name in ((100, 500, '$100-500'), (500, 2000, '$500-2k'), (2000, 10000, '$2k-10k'), (10000, 1e12, '$10k+')):
            f = next((f for f in top if lo <= f[2] < hi), None)
            if f and f[0] + LAG < st: rec(f'A size {name}', P.at(f[0] + LAG), f[1], ry, cl)
        # B: rank bands, first $100+ fill
        for lo, hi, name in ((1, 50, 'rank 1-50'), (51, 200, 'rank 51-200'), (201, 1000, 'rank 201-1000'), (1001, nsc, f'rank 1001-{nsc}')):
            f = next((f for f in fills if lo <= f[3] <= hi), None)
            if f and f[0] + LAG < st: rec(f'B {name}', P.at(f[0] + LAG), f[1], ry, cl)
        # C: agreement at each top-200 account's first fill (one record per account x market)
        seen = {}
        for t, d, usd, r in top:
            if r in seen: continue
            same = any(v == d for v in seen.values()); opp = any(v != d for v in seen.values())
            cls = 'head-to-head (another top-200 on the other side)' if opp else ('joins a top-200 on the same side' if same else 'first top-200 in')
            if t + LAG < st: rec(f'C {cls}', P.at(t + LAG), d, ry, cl)
            seen[r] = d
        # D / F: net top-200 dollars before an entry time
        for ename, sec in (('T-6h', 21600), ('T-1h', 3600), ('T-15m', 900)):
            E = st - sec; pre = [f for f in top if f[0] < E]
            if not pre: continue
            net = sum(f[1] * f[2] for f in pre); sides = {f[1] for f in pre}
            for thr in (1000, 5000):
                if abs(net) >= thr: rec(f'F net top-200 ${thr // 1000}k+ at {ename}', P.at(E), 1 if net > 0 else -1, ry, cl)
            if ename == 'T-15m' and len(sides) == 2:
                rec('D head-to-head: side with more top-200 $', P.at(E), 1 if net > 0 else -1, ry, cl)
                best = min(pre, key=lambda f: f[3]); rec('D head-to-head: best-ranked account side', P.at(E), best[1], ry, cl)
                rec('D head-to-head: side with fewer top-200 $', P.at(E), -1 if net > 0 else 1, ry, cl)
        # E: 1st fill / 2nd same-side fill / flip, per top-200 account
        hist = collections.defaultdict(list)
        for t, d, usd, r in top:
            h = hist[r]
            if not h: kind = '1st fill'
            elif d not in h: kind = 'flip (already bet the other side)'
            elif all(x == d for x in h) and len(h) == 1: kind = 'adds same side (2nd fill)'
            else: kind = None
            if kind and t + LAG < st: rec(f'E {kind}', P.at(t + LAG), d, ry, cl)
            h.append(d)
        # G / H: first top-200 fill per market
        f = top[0] if top else None
        if f and f[0] + LAG < st:
            hrs = (st - f[0]) / 3600
            rec('G ' + ('24h+ out' if hrs >= 24 else '6-24h out' if hrs >= 6 else '1-6h out' if hrs >= 1 else 'under 1h out'), P.at(f[0] + LAG), f[1], ry, cl)
            px = P.at(f[0] + LAG)
            if px is not None:
                price = px if f[1] > 0 else 1 - px
                rec(f"H {c['market']}", px, f[1], ry, cl)
                rec('H price ' + ('under 40c (dog)' if price < 0.4 else '40-60c' if price <= 0.6 else 'over 60c (fav)'), px, f[1], ry, cl)
                rec(f"H sport {c['tag']}", px, f[1], ry, cl)
        if i % 3000 == 0: print(f"[sharp_accounts2] {i}/{len(MK)} holdout markets", flush=True)
    res = {k: stat(v) for k, v in sorted(T.items())}
    json.dump(dict(train_cut=S['train_cut'], lag_s=LAG, cells=res), open(os.path.join(ROOT, 'data', 'research', 'sharp_accounts2.json'), 'w'), indent=1)
    for k, v in res.items(): print(f"  {k:55} n {v.get('n', 0):5}  CLV {v.get('clv')} (z {v.get('clv_z')})  ROI {v.get('roi')}% (z {v.get('roi_z')})")


if __name__ == '__main__':
    main()
