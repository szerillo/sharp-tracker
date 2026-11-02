#!/usr/bin/env python3
"""How long after a sharp-account flag before we can be fairly sure no sharp takes the other side? (Sean, 11/2.)
Accounts scored on games before 2026-09-01 (data/research/poly_wallet_scores.json, top 200 by CLV); flags on games since, with the
backtested rule (a top-50 account, or 2+ top-200 accounts on one side, none on the other). For each flag: when (if ever) a top-200
account first bets the other side before the start. Then the trade-off of waiting X before entering: enter only if no sharp has taken
the other side by flag + X, at the two-sided mid then, vs entering 5 minutes after the flag regardless.
Writes data/research/flag_wait.json. Usage: python3 sharp/flag_wait.py"""
import os, sys, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V
from sharp.sharp_accounts2 import Px
CUT = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc).timestamp()
WAITS = [300, 900, 1800, 3600, 7200, 4 * 3600, 8 * 3600]


def main():
    S = json.load(open(os.path.join(ROOT, 'data', 'research', 'poly_wallet_scores.json')))
    rank = {w['w']: w['clv_rank'] for w in S['wallets'] if w['clv_rank'] <= 200}
    gaps = []; rows = []
    for c, st in V.poly_markets():
        if st < CUT or c['tag'] == 'ufc': continue
        L = V.poly_trades(c, st)
        if len(L) < 5: continue
        X = Px([x[:4] for x in L]); cl = X.at(st)
        if cl is None: continue
        fills = [(t, d, rank[w]) for t, py, usd, d, w in L if usd >= 100 and w in rank]
        sides = collections.defaultdict(set); flag = None
        for t, d, r in fills:
            sides[d].add(r)
            if sides[-d]: continue
            if r <= 50 or len(sides[d]) >= 2: flag = (t, d); break
        if not flag or flag[0] + 300 >= st: continue
        t0, d = flag; opp = next((t for t, dd, r in fills if t > t0 and dd == -d), None)
        lead = st - t0; gaps.append((opp - t0) if opp else None)
        ry = 1 if c['winner'] == c['outcomes'][0] else 0; won = ry if d > 0 else 1 - ry; q = cl if d > 0 else 1 - cl
        rows.append(dict(t0=t0, st=st, opp=opp, d=d, q=q, won=won, X=X))
    n = len(rows); out = dict(flags=n, opposed=sum(g is not None for g in gaps))
    og = sorted(g for g in gaps if g is not None)
    out['time_to_opposing_hours_quantiles'] = {f"p{p}": round(og[int(len(og) * p / 100)] / 3600, 2) for p in (25, 50, 75, 90)} if og else None
    out['share_opposed_by'] = {f"{w // 60}m": round(sum(1 for g in gaps if g is not None and g <= w) / n, 3) for w in WAITS}
    out['lead_hours_median'] = round(sorted(r['st'] - r['t0'] for r in rows)[n // 2] / 3600, 1)
    def entry(rws, wait):
        R = []
        for r in rws:
            E = r['t0'] + wait
            if E >= r['st']: continue
            if r['opp'] is not None and r['opp'] <= E: continue        # a sharp took the other side before we entered: skip
            px = r['X'].at(E)
            if px is None: continue
            price = px if r['d'] > 0 else 1 - px
            if not 0.05 < price < 0.95: continue
            R.append((100 * (r['q'] - price), (1 - price) / price if r['won'] else -1.0))
        if not R: return None
        m = sum(x[0] for x in R) / len(R); sd = (sum((x[0] - m) ** 2 for x in R) / max(1, len(R) - 1)) ** .5
        roi = sum(x[1] for x in R) / len(R)
        return dict(n=len(R), clv=round(m, 2), clv_z=round(m / (sd / math.sqrt(len(R))), 2), roi=round(100 * roi, 1),
                    units_per_flag=round(sum(x[0] for x in R) / n, 3))
    out['enter_after_wait_if_still_unopposed'] = {f"{w // 60}m": entry(rows, w) for w in WAITS}
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'flag_wait.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
