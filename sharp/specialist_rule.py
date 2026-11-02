#!/usr/bin/env python3
"""Should sport specialists count toward the 'two accounts on one side' flag? (Sean, 11/2). Walk-forward, scored on games before
2026-09-01, followed after (as round 3). Groups from train: GENERAL top 200 (30+ fills on 15+ games; rank 1-50 = top 50), each sport's
top 50 (20+ fills on 10+ games in that sport), BOTH = general top 200 and in the sport top 50, SPECIALIST = sport top 50 not in the
general top 200 (UFC excluded throughout). Rules, per test market (first moment the rule is met, entry at the two-sided mid 5 minutes
later, CLV vs Polymarket's close and ROI):
  R0 live rule    a general top-50 or a BOTH account bets, or 2+ general top-200 on one side; no general top-200 on the other side yet
  R1              R0, plus a specialist counts as the second account (2+ on one side with at least one general top-200)
  R1b             R1, and a specialist on the other side also blocks
  R2              R0, plus any 2 accounts from general top 200 or specialists
  R1-only / R2-only  the markets the wider rule adds over R0 (the incremental flags), with their own CLV
Writes data/research/specialist_rule.json. Usage: python3 sharp/specialist_rule.py"""
import os, sys, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V
from sharp.sharp_accounts2 import Px
SPORT = {'epl': 'soccer', 'ucl': 'soccer', 'mls': 'soccer', 'bundesliga': 'soccer'}
CUT = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc).timestamp(); LAG = 300


def main():
    MK = [m for m in V.poly_markets() if m[0]['tag'] != 'ufc']
    G = collections.defaultdict(lambda: [0.0, 0, set()]); S = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0, set()]))
    tests = []; ready = None
    for i, (c, st) in enumerate(MK):
        L = V.poly_trades(c, st)
        if len(L) < 5: continue
        X = Px([x[:4] for x in L]); cl = X.at(st)
        if cl is None: continue
        sp = SPORT.get(c['tag'], c['tag'])
        if st < CUT:
            for t, py, usd, d, w in L:
                if usd < 100 or not w: continue
                v = 100 * ((cl if d > 0 else 1 - cl) - (py if d > 0 else 1 - py))
                g = G[w]; g[0] += v; g[1] += 1; g[2].add(c['cond']); s = S[sp][w]; s[0] += v; s[1] += 1; s[2].add(c['cond'])
            continue
        if ready is None:
            gen = sorted([w for w, x in G.items() if x[1] >= 30 and len(x[2]) >= 15], key=lambda w: -G[w][0] / G[w][1])
            rank = {w: i + 1 for i, w in enumerate(gen[:200])}
            s50 = {sp_: set(sorted([w for w, x in W.items() if x[1] >= 20 and len(x[2]) >= 10], key=lambda w: -W[w][0] / W[w][1])[:50]) for sp_, W in S.items()}
            ready = True
        both = s50.get(sp, set()) & set(rank); spec = s50.get(sp, set()) - set(rank)
        fills = [(t, d, w) for t, py, usd, d, w in L if usd >= 100 and (w in rank or w in spec)]
        if not fills: continue
        ry = 1 if c['winner'] == c['outcomes'][0] else 0
        tests.append((c['event'], st, ry, cl, X, fills, {w: rank[w] for w in rank}, both, spec))
        if i % 5000 == 0: print(f"[specialist_rule] {i}/{len(MK)}", flush=True)
    def trig(fills, rank, both, spec, rule):
        G_ = collections.defaultdict(set); A_ = collections.defaultdict(set)      # general accounts / general+specialists per side
        for t, d, w in fills:
            isg = w in rank
            if isg: G_[d].add(w)
            A_[d].add(w)
            blocked = bool(G_[-d]) or (rule == 'R1b' and bool(A_[-d]))
            if blocked: continue
            if isg and (rank[w] <= 50 or w in both): return t, d
            if len(G_[d]) >= 2: return t, d
            if rule in ('R1', 'R1b') and len(A_[d]) >= 2 and G_[d]: return t, d
            if rule == 'R2' and len(A_[d]) >= 2: return t, d
        return None
    days = (max(x[1] for x in tests) - CUT) / 86400; out = {'days': round(days, 1), 'rules': {}}
    got = {}
    for rule in ('R0', 'R1', 'R1b', 'R2'):
        R = {}
        for k, (ev, st, ry, cl, X, fills, rank, both, spec) in enumerate(tests):
            tr = trig(fills, rank, both, spec, rule)
            if not tr or tr[0] + LAG >= st: continue
            px = X.at(tr[0] + LAG)
            if px is None: continue
            d = tr[1]; price = px if d > 0 else 1 - px
            if not 0.05 < price < 0.95: continue
            won = ry if d > 0 else 1 - ry
            R[k] = (100 * ((cl if d > 0 else 1 - cl) - price), (1 - price) / price if won else -1.0, ev)
        got[rule] = R
    def st_(R):
        V_ = list(R.values()); n = len(V_)
        if n < 5: return dict(n=n)
        m = sum(v[0] for v in V_) / n; sd = (sum((v[0] - m) ** 2 for v in V_) / (n - 1)) ** .5
        r = sum(v[1] for v in V_) / n; rs = (sum((v[1] - r) ** 2 for v in V_) / (n - 1)) ** .5
        return dict(markets=n, per_day=round(n / days, 1), games_per_day=round(len({v[2] for v in V_}) / days, 1), clv=round(m, 2), clv_z=round(m / (sd / n ** .5), 2),
                    roi=round(100 * r, 1), roi_z=round(r / (rs / n ** .5), 2))
    for rule, R in got.items():
        out['rules'][rule] = st_(R)
        if rule != 'R0': out['rules'][f'{rule}-only (added over R0)'] = st_({k: v for k, v in R.items() if k not in got['R0']})
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'specialist_rule.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
