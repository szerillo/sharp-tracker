#!/usr/bin/env python3
"""Does the number of sharp accounts on a side add signal? (Sean, 11/2: "should we leave alone anything that does not have multiple
sharps on it?"). Same walk-forward and groups as sharp/specialist_rule.py (scored on games before 2026-09-01, followed after, UFC excluded,
entry at the two-sided mid 5 minutes after the trigger, CLV vs Polymarket's close and ROI). Live rule R0 flags, split by:
  trigger   what fired it: one top-50 account / one top-200 account also in its sport's top 50 / two top-200 accounts
  count     top-200 accounts on the side when it fired (1, 2, 3+)
  by start  top-200 accounts on the side by the start (1, 2, 3+), entry still at the flag (look-ahead: describes, cannot be bet)
And two stricter rules, each entered 5 minutes after its own trigger:
  R2only    wait for 2+ top-200 accounts on the side (single top-50 / sport-proven accounts no longer flag alone)
  R3only    wait for 3+
Writes data/research/account_count.json. Usage: python3 sharp/account_count.py"""
import os, sys, json, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V
from sharp.sharp_accounts2 import Px
SPORT = {'epl': 'soccer', 'ucl': 'soccer', 'mls': 'soccer', 'bundesliga': 'soccer'}
CUT = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc).timestamp(); LAG = 300


def stat(V_, days):
    n = len(V_)
    if n < 5: return dict(n=n)
    m = sum(v[0] for v in V_) / n; sd = (sum((v[0] - m) ** 2 for v in V_) / (n - 1)) ** .5
    r = sum(v[1] for v in V_) / n; rs = (sum((v[1] - r) ** 2 for v in V_) / (n - 1)) ** .5
    return dict(n=n, per_day=round(n / days, 1), clv=round(m, 2), clv_z=round(m / (sd / n ** .5), 2), roi=round(100 * r, 1), roi_z=round(r / (rs / n ** .5), 2))


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
        both = s50.get(sp, set()) & set(rank)
        fills = [(t, d, w) for t, py, usd, d, w in L if usd >= 100 and w in rank and t < st]
        if fills: tests.append((c['event'], st, 1 if c['winner'] == c['outcomes'][0] else 0, cl, X, fills, both, c['tag']))
    days = (max(x[1] for x in tests) - CUT) / 86400
    rank_ok = lambda w: True
    C = collections.defaultdict(list)
    def grade(X, t, d, st, cl, ry):
        if t + LAG >= st: return None
        px = X.at(t + LAG)
        if px is None: return None
        price = px if d > 0 else 1 - px
        if not 0.05 < price < 0.95: return None
        won = ry if d > 0 else 1 - ry
        return (100 * ((cl if d > 0 else 1 - cl) - price), (1 - price) / price if won else -1.0)
    for ev, st, ry, cl, X, fills, both, tag in tests:
        side = collections.defaultdict(set); r0 = r2 = r3 = None
        for t, d, w in fills:
            side[d].add(w)
            if side[-d]: continue
            top = rank[w] <= 50 if w in rank else False
            if r0 is None and (top or w in both or len(side[d]) >= 2):
                r0 = (t, d, 'one top-50 account' if (top and len(side[d]) == 1) else 'one top-200 also in its sport top 50' if len(side[d]) == 1 else 'two+ top-200 accounts', len(side[d]))
            if r2 is None and len(side[d]) >= 2: r2 = (t, d)
            if r3 is None and len(side[d]) >= 3: r3 = (t, d)
        if r0:
            t, d, why, n = r0; g = grade(X, t, d, st, cl, ry)
            if g:
                fin = len({w for t_, d_, w in fills if d_ == d}); opp = any(d_ == -d for t_, d_, w in fills if t_ > t)
                C['R0 all'].append(g); C['trigger: ' + why].append(g); C['count at flag: ' + ('3+' if n >= 3 else str(n))].append(g)
                C['count by start: ' + ('3+' if fin >= 3 else str(fin)) + (' (a sharp took the other side later)' if opp else '')].append(g)
                C[f'sport {tag}: count at flag ' + ('1' if n == 1 else '2+')].append(g)
        for nm, tr in (('R2only (wait for 2+)', r2), ('R3only (wait for 3+)', r3)):
            if tr:
                g = grade(X, tr[0], tr[1], st, cl, ry)
                if g: C[nm].append(g)
    out = dict(days=round(days, 1), cells={k: stat(v, days) for k, v in sorted(C.items())})
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'account_count.json'), 'w'), indent=1)
    for k, v in out['cells'].items(): print(f"  {k:70} {v}")


if __name__ == '__main__':
    main()
