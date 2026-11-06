#!/usr/bin/env python3
"""List item 4 (Sean 11/6): sharp flags against the opening number. When a top Polymarket account flags a side, how much of Pinnacle's
open-to-close move has already happened, and how much is still to come? A flag that arrives after the move is chasing; one that arrives
before it is the information.
Flags as in sharp/flag_wait.py (accounts scored before 9/1, a top-50 account or two top-200 accounts on one side, none on the other),
moneyline markets only (the number cannot change), matched to the odds database. Pinnacle's no-vig probability for the flagged side at
the open, at the last snapshot before the flag, and at the close. Writes data/research/flag_move.json. Usage: python3 sharp/flag_move.py"""
import os, sys, json, sqlite3, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V, sharp.poly_pinnacle as PP
from sharp.sharp_accounts2 import Px
CUT = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc).timestamp()
DB = os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'); OUT = os.path.join(ROOT, 'data', 'research', 'flag_move.json')


def nv(a, b):
    if not a or not b: return None
    return (1 / a) / (1 / a + 1 / b)


def main():
    S = json.load(open(os.path.join(ROOT, 'data', 'research', 'poly_wallet_scores.json')))
    rank = {w['w']: w['clv_rank'] for w in S['wallets'] if w['clv_rank'] <= 200}
    I = PP.index(); c = sqlite3.connect(DB); rows = []
    for cm, st in V.poly_markets():
        if st < CUT or cm['market'] != 'ml' or cm['tag'] == 'ufc': continue
        L = V.poly_trades(cm, st)
        if len(L) < 5: continue
        fills = [(t, d, rank[w], py) for t, py, usd, d, w in L if usd >= 100 and w in rank]
        sides = collections.defaultdict(set); flag = None
        for t, d, r, py in fills:
            sides[d].add(r)
            if sides[-d]: continue
            if r <= 50 or len(sides[d]) >= 2: flag = (t, d, py); break
        if not flag or flag[0] + 300 >= st: continue
        m = PP.match(I, cm, st)
        if not m: continue
        g, side0 = m; t0, d, py = flag
        side = side0 if d > 0 else ('away' if side0 == 'home' else 'home')
        Q = c.execute("SELECT t, ml_home, ml_away FROM quotes WHERE game_id=? AND book='pinnacle' AND ml_home IS NOT NULL ORDER BY t", (g['id'],)).fetchall()
        Q = [(dt.datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp(), nv(h, a)) for t, h, a in Q]
        Q = [(t, p) for t, p in Q if p is not None and t < st]
        if len(Q) < 2: continue
        before = [p for t, p in Q if t <= t0]
        if not before: continue
        f = (lambda p: p) if side == 'home' else (lambda p: 1 - p)
        po, pf, pc = f(Q[0][1]), f(before[-1]), f(Q[-1][1])
        ry = 1 if cm['winner'] == cm['outcomes'][0] else 0; won = ry if d > 0 else 1 - ry
        price = py if d > 0 else 1 - py
        rows.append(dict(sport=PP.TAG.get(cm['tag']), lead_h=(st - t0) / 3600, open=po, at_flag=pf, close=pc, won=won, price=price))
    print('flags matched:', len(rows), flush=True)

    def summ(L):
        if not L: return None
        n = len(L); tot = sum(r['close'] - r['open'] for r in L); pre = sum(r['at_flag'] - r['open'] for r in L); post = sum(r['close'] - r['at_flag'] for r in L)
        w = sum(r['won'] for r in L); pl = sum((1 - r['price']) / r['price'] if r['won'] else -1 for r in L)
        return dict(n=n, move_open_to_close_pts=round(100 * tot / n, 2), before_flag_pts=round(100 * pre / n, 2), after_flag_pts=round(100 * post / n, 2),
                    share_after_flag=round(post / tot, 2) if abs(tot) > 1e-9 else None,
                    flagged_side_already_moved_up_share=round(sum(1 for r in L if r['at_flag'] - r['open'] >= 0.01) / n, 2),
                    record=f"{w}-{n - w}", roi_at_poly_price=round(100 * pl / n, 1),
                    clv_vs_pinnacle_close_pts=round(100 * sum(r['close'] - r['price'] for r in L) / n, 2))
    R = dict(all=summ(rows))
    for sp in sorted({r['sport'] for r in rows}): R[f'sport {sp}'] = summ([r for r in rows if r['sport'] == sp])
    for lab, lo, hi in (('lead 24h+', 24, 1e9), ('lead 6-24h', 6, 24), ('lead 1-6h', 1, 6), ('lead under 1h', 0, 1)): R[lab] = summ([r for r in rows if lo <= r['lead_h'] < hi])
    R['Pinnacle had already moved 1+ pt toward the side before the flag'] = summ([r for r in rows if r['at_flag'] - r['open'] >= 0.01])
    R['Pinnacle had not moved toward the side (flag first)'] = summ([r for r in rows if r['at_flag'] - r['open'] < 0.01])
    for k, v in R.items():
        if v: print(f"{k:66s} n={v['n']:4d} open->close {v['move_open_to_close_pts']:+.2f}  before {v['before_flag_pts']:+.2f}  after {v['after_flag_pts']:+.2f}  share after {v['share_after_flag']}  {v['record']} ROI {v['roi_at_poly_price']:+.1f}%  CLV {v['clv_vs_pinnacle_close_pts']:+.2f}")
    json.dump(R, open(OUT, 'w'), indent=1); print('wrote', OUT)


if __name__ == '__main__':
    main()
