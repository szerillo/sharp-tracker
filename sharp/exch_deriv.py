#!/usr/bin/env python3
"""Exchange and book derivatives against Pinnacle on our own tape (11/6 list items 2 and 3).
Every 20-minute snapshot in the last 12 hours before the start: Pinnacle's no-vig fair on each derivative line it hangs (first-half /
first-quarter / first-period totals and spreads, team totals), and every bettable venue at the SAME line (Kalshi at the ask plus fee,
Novig at 1 - the other side's bid, Polymarket at the ask, FD / Caesars / DK at their price).
  A. Soft derivative prices: a venue 2%+ better than Pinnacle's fair; first time per game / market / side / venue.
  B. Stale derivatives: the same, split by whether Pinnacle's FULL-GAME line moved toward that side in the previous 20-45 minutes
     (total for totals and team totals, spread for spreads), i.e. the derivative has not caught up with the full game.
Graded on ESPN period scores (data/<sport>/schedule.json linescores); CLV against Pinnacle's last pregame fair at the same line.
Writes data/research/exch_deriv.json. Usage: python3 sharp/exch_deriv.py"""
import os, sys, json, gzip, glob, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
VEN = ('Kalshi', 'Novig', 'Polymarket', 'FD', 'Caesars', 'DK')
DER = {'1h_total', '1q_total', '1p_total', '1h_spread', '1q_spread', '1p_spread', 'tt_home', 'tt_away'}
PER = {'nba': {'1h': 2, '1q': 1}, 'nfl': {'1h': 2, '1q': 1}, 'cfb': {'1h': 2, '1q': 1}, 'cbb': {'1h': 1}, 'nhl': {'1p': 1}}
OPP = {'over': 'under', 'under': 'over', 'home': 'away', 'away': 'home'}


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def cost(r):
    if r.get('american') is not None:
        a = r['american']; return 1 / (1 + (a / 100 if a > 0 else 100 / -a))
    a = r.get('ask')
    if a is None or not 0.03 < a < 0.97: return None
    if r['venue'] == 'Kalshi': a += math.ceil(0.07 * a * (1 - a) * 100) / 100
    return a


def outcome(sp, e, mk, side, line):
    ls = e.get('linescores') or {}; h, a = ls.get('home') or [], ls.get('away') or []
    try: hs, as_ = float(e['home_team']['score']), float(e['away_team']['score'])
    except Exception: return None
    if mk.startswith('tt_'):
        v = hs if mk == 'tt_home' else as_
    else:
        n = PER.get(sp, {}).get(mk[:2])
        if not n or len(h) < n or len(a) < n: return None
        ph, pa = sum(h[:n]), sum(a[:n])
        if mk.endswith('total'): v = ph + pa
        else:
            m = (ph - pa) if side == 'home' else (pa - ph); c = m + line
            return 0.5 if c == 0 else 1 if c > 0 else 0
    return 0.5 if v == line else 1 if (v > line) == (side == 'over') else 0


def main():
    bets = []
    for sp in ('nba', 'nfl', 'nhl', 'cfb', 'cbb'):
        try: S = json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json')))
        except Exception: continue
        done = {k: e for k, e in S.items() if e.get('completed') and e.get('linescores')}
        if not done: continue
        win = {}
        for k, e in done.items():
            st = ts(e['start'].replace('Z', ':00Z') if len(e['start']) == 17 else e['start']); win[k] = (st, (st - dt.timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M'), st.strftime('%Y-%m-%dT%H:%M'))
        R = collections.defaultdict(list)
        for f in sorted(glob.glob(os.path.join(ROOT, 'data', sp, 'ticks', '*.jsonl.gz'))):
            for l in lines(f):
                if '"Pinnacle"' not in l and not any(f'"{v}"' in l for v in VEN): continue
                try: r = json.loads(l)
                except Exception: continue
                w = win.get(r.get('event_id'))
                if not w or not (w[1] <= r['ts'][:16] < w[2]): continue
                if r['market'] in DER or r['market'] in ('total', 'spread'): R[r['event_id']].append(r)
        for ev, L in R.items():
            e = done[ev]; st = win[ev][0]
            snaps = collections.defaultdict(list)
            for r in L: snaps[r['ts'][:16]].append(r)
            order = sorted(snaps); full_hist = []; seen = set(); last_fair = {}
            for k in order:
                S_ = snaps[k]; t = ts(S_[0]['ts'])
                P = collections.defaultdict(dict)
                for r in S_:
                    if r['venue'] == 'Pinnacle': P[(r['market'], r.get('line') if r['market'].endswith('total') or r['market'].startswith('tt_') else abs(r.get('line') or 0))][r['side']] = r
                # Pinnacle full game: home spread and total
                fs = next((r.get('line') for r in S_ if r['venue'] == 'Pinnacle' and r['market'] == 'spread' and r['side'] == 'home'), None)
                ft = next((r.get('line') for r in S_ if r['venue'] == 'Pinnacle' and r['market'] == 'total'), None)
                if fs is not None or ft is not None: full_hist.append((t, fs, ft))
                prev = [x for x in full_hist if 1200 <= (t - x[0]).total_seconds() <= 2700]
                fair = {}
                for (mk, _), sides in P.items():
                    if mk not in DER or len(sides) != 2: continue
                    a, b = list(sides.values()); ca, cb = cost(a), cost(b)
                    if not ca or not cb: continue
                    fair[(mk, a['side'], a.get('line'))] = ca / (ca + cb); fair[(mk, b['side'], b.get('line'))] = cb / (ca + cb)
                last_fair.update(fair)
                for r in S_:
                    if r['venue'] not in VEN or r['market'] not in DER: continue
                    f = fair.get((r['market'], r['side'], r.get('line')))
                    if f is None: continue
                    c = cost(r)
                    if not c: continue
                    evv = f / c - 1
                    if evv < 0.02: continue
                    key = (ev, r['market'], r['side'], r.get('line'), r['venue'])
                    if key in seen: continue
                    seen.add(key)
                    moved = None
                    if prev and full_hist:
                        p0 = prev[0]; now = full_hist[-1]
                        if r['market'].endswith('total') or r['market'].startswith('tt_'):
                            if p0[2] is not None and now[2] is not None:
                                d = now[2] - p0[2]
                                if r['market'] == 'tt_home' and p0[1] is not None and now[1] is not None: d = d / 2 - (now[1] - p0[1]) / 2
                                if r['market'] == 'tt_away' and p0[1] is not None and now[1] is not None: d = d / 2 + (now[1] - p0[1]) / 2
                                moved = d if r['side'] == 'over' else -d
                        elif p0[1] is not None and now[1] is not None:
                            d = p0[1] - now[1]; moved = d if r['side'] == 'home' else -d          # home -3 to -4: moved 1 toward home
                    won = outcome(sp, e, r['market'], r['side'], r.get('line'))
                    if won is None: continue
                    bets.append(dict(sport=sp, ev=ev, mk=r['market'], side=r['side'], line=r.get('line'), venue=r['venue'], cost=c, fair=f, edge=evv, moved=moved, won=won,
                                     hours=(st - t).total_seconds() / 3600, key=key))
            for b in bets:
                if b['ev'] == ev and 'close' not in b:
                    cf = last_fair.get((b['mk'], b['side'], b['line']))
                    if cf is not None: b['close'] = cf
    def rec(L):
        w = sum(1 for b in L if b['won'] == 1); l = sum(1 for b in L if b['won'] == 0)
        pl = sum((1 / b['cost'] - 1) if b['won'] == 1 else -1 if b['won'] == 0 else 0 for b in L)
        c = [b['close'] / b['cost'] - 1 for b in L if b.get('close')]
        exp = sum(b['close'] if b.get('close') else b['fair'] for b in L if b['won'] != 0.5)
        return dict(n=len(L), w=w, l=l, roi=round(100 * pl / max(1, w + l), 1), edge=round(100 * sum(b['edge'] for b in L) / max(1, len(L)), 1),
                    ev_close=round(100 * sum(c) / len(c), 1) if c else None, exp_wins=round(exp, 1))
    R = {}
    def add(k, L):
        if not L: return
        R[k] = x = rec(L)
        print(f"{k:58s} n={x['n']:5d} {x['w']}-{x['l']} (exp {x['exp_wins']}) ROI {x['roi']:+.1f}%  edge {x['edge']:.1f}%  EV at close {x['ev_close']}")
    add('all', bets)
    for v in VEN: add(f'venue {v}', [b for b in bets if b['venue'] == v])
    for m in sorted({b['mk'] for b in bets}): add(f'market {m}', [b for b in bets if b['mk'] == m])
    for sp in ('nba', 'nfl', 'nhl', 'cfb', 'cbb'): add(f'sport {sp}', [b for b in bets if b['sport'] == sp])
    add('B: full game moved toward the side first (stale derivative)', [b for b in bets if b['moved'] is not None and b['moved'] >= 0.5])
    add('B: full game flat', [b for b in bets if b['moved'] is not None and abs(b['moved']) < 0.5])
    add('B: full game moved away', [b for b in bets if b['moved'] is not None and b['moved'] <= -0.5])
    for v in ('Kalshi', 'Novig', 'FD', 'Caesars', 'DK'): add(f'B stale | venue {v}', [b for b in bets if b['venue'] == v and b['moved'] is not None and b['moved'] >= 0.5])
    for lab, lo, hi in (('edge 2-4%', .02, .04), ('edge 4-8%', .04, .08), ('edge 8%+', .08, 9)): add(lab, [b for b in bets if lo <= b['edge'] < hi])
    for lab, lo, hi in (('6-12h out', 6, 12), ('1-6h', 1, 6), ('inside 1h', 0, 1)): add(f'timing {lab}', [b for b in bets if lo <= b['hours'] < hi])
    json.dump(dict(results=R), open(os.path.join(ROOT, 'data', 'research', 'exch_deriv.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
