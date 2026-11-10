#!/usr/bin/env python3
"""Does the first move after the open keep going? (docs/review_2026-11-10.md: "what predicts the side the market moves toward at the
open"; sharp/open_lead.py found Pinnacle's opener is no better than the US books' and that moneyline price gaps hold.)
Odds API history 2020-26 (data/oddsapi/odds.sqlite). For each game with a result, Pinnacle's no-vig moneyline and its spread and total
lines at every snapshot. The signal is Pinnacle's move from one snapshot to the next early in the week (the first move after the open, and
any later move with 6+ hours left). Tests:
  1. Continuation: after Pinnacle moves X toward a side, how much further does it go by the close (the remaining move, same sign = positive).
  2. The bet: that side at the best bettable US price (FD, Caesars, BetRivers, DK) at the snapshot after the move. Moneyline: any price
     +200 or shorter. Spread and total: the US book must still hang Pinnacle's old number or better, at -125 or better.
  3. The other side (fade), same pricing.
Flat 1 unit. Usage: python3 sharp/open_momentum.py -> data/research/open_momentum.json"""
import os, sys, json, sqlite3, collections, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from open_lead import nv, Rec, season, BET, SPORTS, DB, ROOT


def main():
    c = sqlite3.connect(DB)
    G = {r[0]: r for r in c.execute("select g.game_id, g.sport, g.start, r.home_score, r.away_score from games g join results r using(game_id) " f"where g.sport in ({','.join('?' * len(SPORTS))})", SPORTS)}
    R = collections.defaultdict(Rec); CONT = collections.defaultdict(lambda: [0, 0.0, 0])
    cur = c.execute(f"select game_id, t, book, ml_home, ml_away, sp_line, sp_home, sp_away, tot_line, tot_over, tot_under from quotes where sport in ({','.join('?' * len(SPORTS))}) order by game_id, t", SPORTS)
    def game(gid, snaps):
        g = G.get(gid)
        if not g or g[3] is None or len(snaps) < 3: return
        _, sport, start, hs, as_ = g; se = season(sport, start); st_ = dt.datetime.fromisoformat(start.replace('Z', '+00:00')); margin = hs - as_; total = hs + as_
        P = [(t, B.get('pinnacle'), B) for t, B in snaps if B.get('pinnacle')]
        if len(P) < 3: return
        lastp = P[-1][1]; cml = nv(lastp[0], lastp[1]); csp = lastp[2]; ctot = lastp[5]
        done = set()
        for i in range(1, len(P) - 1):
            t, p, B = P[i]; p0 = P[i - 1][1]
            h = (st_ - dt.datetime.fromisoformat(t.replace('Z', '+00:00'))).total_seconds() / 3600
            if h < 6: break
            first = 'first move after the open' if i == 1 else 'later move, 6h+ out'
            hb = '48h+' if h >= 48 else '24-48h' if h >= 24 else '6-24h'
            bet = {b: B[b] for b in BET if b in B}
            # ---- moneyline: Pinnacle fair moved 1.5+ points
            f0, f1 = nv(p0[0], p0[1]), nv(p[0], p[1])
            if f0 is not None and f1 is not None and abs(f1 - f0) >= 0.015 and ('ml', first) not in done and margin != 0:
                done.add(('ml', first)); d = 1 if f1 > f0 else -1; size = '1.5-3 pts' if abs(f1 - f0) < 0.03 else '3+ pts'
                if cml is not None:
                    k = CONT[('ml', first, size)]; k[0] += 1; k[1] += 100 * (cml - f1) * d; k[2] += 1 if (cml - f1) * d > 0 else 0
                for lab, side in (('follow', d), ('fade', -d)):
                    idx = 0 if side > 0 else 1; won = (margin > 0) if side > 0 else (margin < 0)
                    best = max(((q[idx], b) for b, q in bet.items() if q[idx] and 1 < q[idx] <= 3.0), default=None)
                    if best:
                        ev = ((cml if side > 0 else 1 - cml) * best[0] - 1) if cml is not None else None
                        for key in ((f'ml {lab}', first, 'all'), (f'ml {lab}', first, size), (f'ml {lab}', first, sport), (f'ml {lab}', first, hb)): R[key].add(best[0], won, se, ev)
            # ---- spread: Pinnacle's home line moved 0.5+
            if p0[2] is not None and p[2] is not None and abs(p[2] - p0[2]) >= 0.5 and ('sp', first) not in done:
                done.add(('sp', first)); mv = p[2] - p0[2]; d = -1 if mv > 0 else 1          # home line up (more points to home) = money on the away side
                if csp is not None:
                    k = CONT[('spread', first, '0.5' if abs(mv) < 1 else '1+')]; k[0] += 1; k[1] += (csp - p[2]) * (1 if mv > 0 else -1); k[2] += 1 if (csp - p[2]) * mv > 0 else 0
                for lab, side in (('follow', d), ('fade', -d)):
                    cand = []
                    for b, q in bet.items():
                        if q[2] is None: continue
                        # follow: still get Pinnacle's old number or better for the side; fade: get the new number or better for the other side
                        ref = p0[2] if lab == 'follow' else p[2]
                        ok = (q[2] >= ref) if side > 0 else (q[2] <= ref); dec = q[3] if side > 0 else q[4]
                        if ok and dec and dec >= 1.8: cand.append((q[2] if side > 0 else -q[2], dec, q[2]))
                    if not cand: continue
                    _, dec, line = max(cand); ats = (margin + line) * side; won = None if ats == 0 else ats > 0
                    for key in ((f'spread {lab}', first, 'all'), (f'spread {lab}', first, sport), (f'spread {lab}', first, '0.5' if abs(mv) < 1 else '1+'), (f'spread {lab}', first, hb)): R[key].add(dec, won, se)
            # ---- total: Pinnacle's total moved 0.5+
            if p0[5] is not None and p[5] is not None and abs(p[5] - p0[5]) >= 0.5 and ('tot', first) not in done:
                done.add(('tot', first)); mv = p[5] - p0[5]; d = 1 if mv > 0 else -1           # total up = money on the over
                if ctot is not None:
                    k = CONT[('total', first, '0.5' if abs(mv) < 1 else '1+')]; k[0] += 1; k[1] += (ctot - p[5]) * d; k[2] += 1 if (ctot - p[5]) * d > 0 else 0
                for lab, side in (('follow', d), ('fade', -d)):
                    cand = []
                    for b, q in bet.items():
                        if q[5] is None: continue
                        ref = p0[5] if lab == 'follow' else p[5]
                        ok = (q[5] <= ref) if side > 0 else (q[5] >= ref); dec = q[6] if side > 0 else q[7]
                        if ok and dec and dec >= 1.8: cand.append((-q[5] if side > 0 else q[5], dec, q[5]))
                    if not cand: continue
                    _, dec, line = max(cand); d_ = (total - line) * side; won = None if d_ == 0 else d_ > 0
                    for key in ((f'total {lab}', first, 'all'), (f'total {lab}', first, sport), (f'total {lab}', first, '0.5' if abs(mv) < 1 else '1+'), (f'total {lab}', first, hb)): R[key].add(dec, won, se)
    gid = None; snaps = []; t0 = None; B = {}
    for g_, t, book, mh, ma, sl, sh, sa, tl, to, tu in cur:
        if g_ != gid:
            if gid is not None:
                if B: snaps.append((t0, B))
                game(gid, snaps)
            gid = g_; snaps = []; t0 = t; B = {}
        if t != t0:
            if B: snaps.append((t0, B))
            t0 = t; B = {}
        B[book] = (mh, ma, sl, sh, sa, tl, to, tu)
    if gid is not None:
        if B: snaps.append((t0, B))
        game(gid, snaps)
    out = dict(cont={' | '.join(k): dict(n=v[0], more=round(v[1] / v[0], 2), kept_going=round(v[2] / v[0], 3)) for k, v in CONT.items() if v[0] >= 30}, rows={' | '.join(k): r.out() for k, r in R.items()})
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'open_momentum.json'), 'w'), indent=0)
    print('1. After the move, how much further by the close (ml: points of probability; spread and total: points of line)')
    for k in sorted(out['cont']): v = out['cont'][k]; print(f"  {k:<52} n {v['n']:>6}  further {v['more']:+.2f}  kept going {100 * v['kept_going']:.0f}%")
    print('2-3. Bets at the best US price after the move')
    for k in sorted(out['rows']):
        r = out['rows'][k]
        if r['n'] >= 60: print(f"  {k:<58} n {r['n']:>6} {r['w']}-{r['l']}  ROI {r['roi']:+.1f}% (z {r['z']})  seasons+ {r['seasons_pos']}/{r['seasons']}" + (f"  EV at close {r['ev_close']:+.2f}%" if r.get('ev_close') is not None else ''))


if __name__ == '__main__': main()
