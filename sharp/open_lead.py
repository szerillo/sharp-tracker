#!/usr/bin/env python3
"""What predicts the side the market moves toward, at the open? (docs/review_2026-11-10.md; the 11/5 replay: the side the market moves
toward wins at its opening price in every sport and is gone by the close.) Odds API history 2020-26 (data/oddsapi/odds.sqlite).
The open = a game's first snapshot with Pinnacle and 2+ US books on the market. Tests, all knowable at that snapshot:
  1. Who leads: when Pinnacle and the US books disagree at the open, which one moves to the other by the close.
  2. Moneyline: the side Pinnacle's no-vig price likes more than the best bettable US book's price (FD, Caesars, BetRivers, DK), by size of
     the gap; bet at that US price. ROI on results, and the same price against Pinnacle's close.
  3. Spreads and totals: a bettable US book hanging a number 0.5+ better than Pinnacle's line for a side; bet it there.
  4. The same three at the first time the gap appears later (not at the open), by hours to the start, for contrast.
Flat 1 unit, graded at the US book's price and line. Usage: python3 sharp/open_lead.py -> data/research/open_lead.json"""
import os, sys, json, sqlite3, collections, statistics as st, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DB = os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite')
BET = ('fanduel', 'williamhill_us', 'betrivers', 'draftkings')            # where Sean bets (never BetMGM)
US = ('draftkings', 'fanduel', 'williamhill_us', 'betmgm', 'betrivers', 'espnbet', 'fanatics')
SPORTS = ('nba', 'nfl', 'nhl', 'cfb', 'cbb', 'mlb', 'wnba')


def nv(a, b):
    if not a or not b or a <= 1 or b <= 1: return None
    pa, pb = 1 / a, 1 / b; return pa / (pa + pb)


class Rec:
    def __init__(s): s.x = []; s.ev = []; s.seas = collections.defaultdict(float); s.w = s.l = 0
    def add(s, dec, won, season, evc=None):
        if won is None: return
        r = (dec - 1) if won else -1.0; s.x.append(r); s.seas[season] += r; s.w += 1 if won else 0; s.l += 0 if won else 1
        if evc is not None: s.ev.append(evc)
    def out(s):
        n = len(s.x)
        if not n: return dict(n=0)
        m = sum(s.x) / n; sd = (sum((v - m) ** 2 for v in s.x) / max(1, n - 1)) ** 0.5
        return dict(n=n, w=s.w, l=s.l, roi=round(100 * m, 1), z=round(m / (sd / n ** 0.5), 2) if sd else None, seasons=len(s.seas), seasons_pos=sum(1 for v in s.seas.values() if v > 0),
                    ev_close=round(100 * sum(s.ev) / len(s.ev), 2) if s.ev else None, ev_n=len(s.ev))


def season(sport, start):
    y, m = int(start[:4]), int(start[5:7])
    return y if sport in ('mlb', 'wnba') else (y if m >= 7 else y - 1)


def main():
    c = sqlite3.connect(DB)
    G = {r[0]: r for r in c.execute("select g.game_id, g.sport, g.start, r.home_score, r.away_score, g.pin_close_home, g.pin_close_sp, g.pin_close_tot from games g join results r using(game_id) "
                                    f"where g.sport in ({','.join('?' * len(SPORTS))})", SPORTS)}
    R = collections.defaultdict(Rec); LEAD = collections.defaultdict(lambda: [0, 0, 0.0, 0.0]); n_games = collections.Counter()
    cur = c.execute(f"select game_id, t, book, ml_home, ml_away, sp_line, sp_home, sp_away, tot_line, tot_over, tot_under from quotes where sport in ({','.join('?' * len(SPORTS))}) order by game_id, t", SPORTS)
    def game(gid, snaps):
        g = G.get(gid)
        if not g or g[3] is None: return
        _, sport, start, hs, as_, pc_home, pc_sp, pc_tot = g; se = season(sport, start); st_ = dt.datetime.fromisoformat(start.replace('Z', '+00:00'))
        margin = hs - as_; total = hs + as_
        done = set(); first = {}
        last = snaps[-1][1]; lp = last.get('pinnacle')
        pin_close_ml = nv(lp[0], lp[1]) if lp else None
        prev_pf = None
        for i, (t, B) in enumerate(snaps):
            tt = dt.datetime.fromisoformat(t.replace('Z', '+00:00')); h = (st_ - tt).total_seconds() / 3600
            if h <= 0: continue
            hb = '48h+' if h >= 48 else '24-48h' if h >= 24 else '6-24h' if h >= 6 else 'under 6h'
            p = B.get('pinnacle')
            if not p: continue
            us = [B[b] for b in US if b in B]; bet = {b: B[b] for b in BET if b in B}
            # ---- moneyline
            pf = nv(p[0], p[1])
            um = [x for x in (nv(q[0], q[1]) for q in us) if x is not None]
            if pf is not None and len(um) >= 2 and sport != 'nhl_3way':
                is_open = 'ml' not in first
                if is_open:
                    first['ml'] = 1; n_games[sport + ' ml'] += 1
                    gap = pf - st.median(um)                                    # Pinnacle minus the US books, home side, at the open
                    if pin_close_ml is not None and abs(gap) >= 0.01:
                        uc = [x for x in (nv(q[0], q[1]) for b_, q in last.items() if b_ in US) if x is not None]
                        if len(uc) >= 2:
                            k = LEAD[(sport, 'ml', '1-2 pts' if abs(gap) < 0.02 else '2-4 pts' if abs(gap) < 0.04 else '4+ pts')]
                            k[0] += 1; k[2] += (pin_close_ml - pf) * (-1 if gap > 0 else 1) / abs(gap); k[3] += (st.median(uc) - st.median(um)) * (1 if gap > 0 else -1) / abs(gap)
                for side, fair, idx, won in (('home', pf, 0, margin > 0), ('away', 1 - pf, 1, margin < 0)):
                    if margin == 0: continue
                    best = max(((q[idx], b) for b, q in bet.items() if q[idx] and q[idx] > 1), default=None)
                    if not best: continue
                    ev = fair * best[0] - 1
                    evc = ((pin_close_ml if side == 'home' else 1 - pin_close_ml) * best[0] - 1) if pin_close_ml is not None else None
                    for thr in (0.02, 0.04, 0.07):
                        if ev >= thr and best[0] <= 3.0:
                            if is_open: R[('ml at the open', f'EV {int(thr * 100)}%+', sport)].add(best[0], won, se, evc); R[('ml at the open', f'EV {int(thr * 100)}%+', 'all')].add(best[0], won, se, evc)
                            key = ('ml', side, thr)
                            if key not in done and not is_open:
                                R[('ml first seen later', f'EV {int(thr * 100)}%+', hb)].add(best[0], won, se, evc)
                                # the live stale-book lean's condition: Pinnacle moved 1+ point toward the side since the last snapshot
                                if prev_pf is not None:
                                    mv = (pf - prev_pf) if side == 'home' else (prev_pf - pf)
                                    R[('ml first seen later', f'EV {int(thr * 100)}%+', 'Pinnacle just moved 1+ toward the side' if mv >= 0.01 else 'Pinnacle moved 1+ away' if mv <= -0.01 else 'Pinnacle had not moved')].add(best[0], won, se, evc)
                            done.add(key)
            if pf is not None: prev_pf = pf
            # ---- spread: a bettable book's home line better than Pinnacle's for a side
            if p[2] is not None and p[3] and p[4]:
                is_open = 'sp' not in first; first['sp'] = 1
                pl = p[2]
                if is_open and pc_sp is not None:
                    ul = [q[2] for q in us if q[2] is not None]
                    if len(ul) >= 2 and abs(st.median(ul) - pl) >= 0.5:
                        d = st.median(ul) - pl; uc = [q[2] for b_, q in last.items() if b_ in US and q[2] is not None]
                        if len(uc) >= 2:
                            k = LEAD[(sport, 'spread', '0.5' if abs(d) < 1 else '1+')]; k[0] += 1; k[2] += (pc_sp - pl) / d; k[3] += (st.median(uc) - st.median(ul)) / -d
                for side in ('home', 'away'):
                    cand = []
                    for b, q in bet.items():
                        if q[2] is None: continue
                        gain = (q[2] - pl) if side == 'home' else (pl - q[2])          # home line higher = better for home; lower = better for away
                        dec = q[3] if side == 'home' else q[4]
                        if gain >= 0.5 and dec and dec >= 1.8: cand.append((gain, dec, q[2], b))
                    if not cand: continue
                    gain, dec, line, b = max(cand)
                    ats = (margin + line) if side == 'home' else -(margin + line)
                    won = None if ats == 0 else ats > 0
                    lab = '0.5' if gain < 1 else '1' if gain < 1.5 else '1.5+'
                    key = ('sp', side)
                    if is_open: R[('spread at the open', f'{lab} better than Pinnacle', sport)].add(dec, won, se); R[('spread at the open', f'{lab} better than Pinnacle', 'all')].add(dec, won, se)
                    elif key not in done: R[('spread first seen later', f'{lab} better than Pinnacle', hb)].add(dec, won, se)
                    done.add(key)
            # ---- total
            if p[5] is not None and p[6] and p[7]:
                is_open = 'tot' not in first; first['tot'] = 1
                pl = p[5]
                if is_open and pc_tot is not None:
                    ul = [q[5] for q in us if q[5] is not None]
                    if len(ul) >= 2 and abs(st.median(ul) - pl) >= 0.5:
                        d = st.median(ul) - pl; uc = [q[5] for b_, q in last.items() if b_ in US and q[5] is not None]
                        if len(uc) >= 2:
                            k = LEAD[(sport, 'total', '0.5' if abs(d) < 1 else '1+')]; k[0] += 1; k[2] += (pc_tot - pl) / d; k[3] += (st.median(uc) - st.median(ul)) / -d
                for side in ('over', 'under'):
                    cand = []
                    for b, q in bet.items():
                        if q[5] is None: continue
                        gain = (pl - q[5]) if side == 'over' else (q[5] - pl)
                        dec = q[6] if side == 'over' else q[7]
                        if gain >= 0.5 and dec and dec >= 1.8: cand.append((gain, dec, q[5], b))
                    if not cand: continue
                    gain, dec, line, b = max(cand)
                    d_ = (total - line) if side == 'over' else (line - total); won = None if d_ == 0 else d_ > 0
                    lab = '0.5' if gain < 1 else '1' if gain < 1.5 else '1.5+'
                    key = ('tot', side)
                    if is_open: R[('total at the open', f'{lab} better than Pinnacle', sport)].add(dec, won, se); R[('total at the open', f'{lab} better than Pinnacle', 'all')].add(dec, won, se); R[('total at the open', f'{lab} better than Pinnacle', side)].add(dec, won, se)
                    elif key not in done: R[('total first seen later', f'{lab} better than Pinnacle', hb)].add(dec, won, se)
                    done.add(key)
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
    out = dict(rows={' | '.join(k): r.out() for k, r in R.items()}, lead={' | '.join(k): dict(n=v[0], pinnacle_moved_to_us=round(v[2] / v[0], 2), us_moved_to_pinnacle=round(v[3] / v[0], 2)) for k, v in LEAD.items() if v[0] >= 30},
               games=dict(n_games))
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'open_lead.json'), 'w'), indent=0)
    print('1. Who leads (share of the opening gap each side closed by the close)')
    for k in sorted(out['lead']): v = out['lead'][k]; print(f"  {k:<28} n {v['n']:>5}  Pinnacle moved to the US books {v['pinnacle_moved_to_us']:+.2f}   US books moved to Pinnacle {v['us_moved_to_pinnacle']:+.2f}")
    print('2-4. Bets')
    for k in sorted(out['rows']):
        r = out['rows'][k]
        if r['n'] >= 40: print(f"  {k:<62} n {r['n']:>5} {r['w']}-{r['l']}  ROI {r['roi']:+.1f}% (z {r['z']})  seasons+ {r['seasons_pos']}/{r['seasons']}" + (f"  EV at Pinnacle's close {r['ev_close']:+.2f}% on {r['ev_n']}" if r.get('ev_close') is not None else ''))


if __name__ == '__main__': main()
