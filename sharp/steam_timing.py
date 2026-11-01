#!/usr/bin/env python3
"""Steam timing on the exchange path (Sean, 11/1): the Bet Labs study (docs/betlabs_market_moves_2026-11-01.md) found that closes
under-react in totals and NHL moneylines, so a move is still going when steam hits. This asks WHEN to get in.

Data: the settled Kalshi + Novig game markets of sharp/flow_split.py (every taker fill, pregame). Spread / total ladders keep one
market per game: the strike whose closing mid is nearest 50c. Mid = the last yes-buy and last no-buy within 2h (EB.px_at).

Steam event: the first time in a market that the mid moved >= M points (3 / 5 / 8) inside W minutes (15 / 60), at least 30 minutes
before the start. One event per market. Direction = the side the price moved toward.
For each event, entries (all at the ask: the side's last taker price, if it printed within 30 minutes of the entry time):
  +0, +5m, +15m, +60m after the event, and T-15m (just before the start)
  dip: the first time after the event that the mid gives back >= 40% of the move (a pullback), still pregame
Each entry is graded FOLLOW (the steam side) and FADE (the other side): ROI at the result, and CLV against the last pregame mid.
Path: peak (the furthest the mid got toward the steam side before the start) vs the close, so "overshot and got bet back" is
measured directly: the share of events where the close gave back >= 2 points from the peak.
Train = games before 2026-10-01, test = October onward; a cell counts only if it holds on both.
Writes data/research/steam_timing.json and prints the table. Usage: python3 sharp/steam_timing.py"""
import os, sys, json, math, bisect, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from flow_split import market_rows

SPLIT = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc).timestamp()
MOVES = (3, 5, 8); WINS = (15, 60); STALE = 7200; ASK_FRESH = 1800; MIN_LEAD = 1800


def mid_series(L):
    """trades sorted -> (times, mids) with a two-sided mid at each trade (None when only one side is recent)."""
    T, M = [], []; ly = ln = None
    for x in L:
        if x[3] > 0: ly = x
        else: ln = x
        m = round((ly[1] + ln[1]) / 2, 4) if ly and ln and abs(ly[0] - ln[0]) <= STALE else None
        T.append(x[0]); M.append(m)
    return T, M


def mid_at(T, M, t):
    i = bisect.bisect_right(T, t) - 1
    while i >= 0 and M[i] is None: i -= 1
    return M[i] if i >= 0 else None


def ask_at(L, T, t, d):
    """the price a taker paid for the side d (+1 yes / -1 no) at the last fill before t, if within ASK_FRESH."""
    i = bisect.bisect_right(T, t) - 1
    while i >= 0 and t - L[i][0] <= ASK_FRESH:
        if L[i][3] == d: return L[i][1] if d > 0 else 1 - L[i][1]
        i -= 1
    return None


def grade(price, won, close_side):
    if price is None or not (0.02 < price < 0.98): return None
    return dict(roi=(1 - price) / price if won else -1.0, clv=None if close_side is None else 100 * (close_side - price))


def main():
    rows = market_rows()
    # one market per game x type: Kalshi ladders -> the strike closing nearest 50c
    best = {}
    for r in rows:
        v, sp, mt, gk, start, ry, L = r
        pre = sorted(x for x in L if x[0] < start)
        if len(pre) < 20: continue
        T, M = mid_series(pre); c = mid_at(T, M, start)
        if c is None: continue
        k = (v, gk)
        if k not in best or abs(c - 0.5) < abs(best[k][0] - 0.5): best[k] = (c, sp, mt, start, ry, pre, T, M)
    print(f"[steam] {len(best)} markets (one per venue x game x type) with 20+ pregame fills")
    B = collections.defaultdict(list); paths = collections.defaultdict(list)
    for (v, gk), (close, sp, mt, start, ry, L, T, M) in best.items():
        per = 'train' if start < SPLIT else 'test'
        for W in WINS:
            for mv in MOVES:
                ev = None
                for i, t in enumerate(T):
                    if t > start - MIN_LEAD: break
                    m = M[i]
                    if m is None: continue
                    q = mid_at(T, M, t - W * 60)
                    if q is None: continue
                    if abs(100 * (m - q)) >= mv: ev = (t, 1 if m > q else -1, m, q); break
                if not ev: continue
                t0, d, m0, q0 = ev
                won_f = ry if d > 0 else 1 - ry; cs = close if d > 0 else 1 - close
                # path: peak toward the steam side between the event and the start
                seg = [x for x in M[bisect.bisect_left(T, t0):bisect.bisect_left(T, start)] if x is not None]
                peak = max(seg) if d > 0 else min(seg)
                give = 100 * abs(peak - close)
                paths[(sp, mt, W, mv, per)].append(dict(cont=100 * d * (close - m0), give=give))
                ent = {'+0': t0 + 1, '+5m': t0 + 300, '+15m': t0 + 900, '+60m': t0 + 3600, 'T-15m': start - 900}
                # dip: first mid that gives back >= 40% of the move
                lvl = m0 - d * 0.4 * abs(m0 - q0)
                j = bisect.bisect_right(T, t0)
                while j < len(T) and T[j] < start - 300:
                    if M[j] is not None and (M[j] - lvl) * d <= 0: ent['dip'] = T[j] + 1; break
                    j += 1
                for name, te in ent.items():
                    if te >= start or te < t0: continue
                    for side, dd in (('follow', d), ('fade', -d)):
                        g = grade(ask_at(L, T, te, dd), won_f if side == 'follow' else 1 - won_f, cs if side == 'follow' else 1 - cs)
                        if g: B[(sp, mt, W, mv, name, side, per)].append(g)
    def st(x):
        if not x: return None
        r = [b['roi'] for b in x]; mu = sum(r) / len(r); sd = (sum((y - mu) ** 2 for y in r) / max(1, len(r) - 1)) ** .5
        c = [b['clv'] for b in x if b['clv'] is not None]
        return dict(n=len(x), roi=round(100 * mu, 1), z=round(mu / (sd / math.sqrt(len(x))), 2) if sd else 0, clv=round(sum(c) / len(c), 2) if c else None)
    # pooled by market group, plus per sport x type
    groups = collections.defaultdict(lambda: collections.defaultdict(list)); pg = collections.defaultdict(lambda: collections.defaultdict(list))
    for (sp, mt, W, mv, name, side, per), x in B.items():
        for g in ('all', f'{mt}', f'{sp} {mt}'): groups[(g, W, mv, name, side)][per] += x
    for (sp, mt, W, mv, per), x in paths.items():
        for g in ('all', f'{mt}', f'{sp} {mt}'): pg[(g, W, mv)][per] += x
    out = {}
    for k, v in groups.items(): out['|'.join(map(str, k))] = {p: st(v[p]) for p in ('train', 'test')}
    po = {}
    for k, v in pg.items():
        po['|'.join(map(str, k))] = {p: dict(n=len(v[p]), cont=round(sum(y['cont'] for y in v[p]) / len(v[p]), 2) if v[p] else None,
                                               gave2=round(sum(y['give'] >= 2 for y in v[p]) / len(v[p]), 3) if v[p] else None) for p in ('train', 'test')}
    json.dump(dict(cells=out, paths=po), open(os.path.join(ROOT, 'data', 'research', 'steam_timing.json'), 'w'), indent=1)
    f = lambda s: '-' if not s else f"{s['n']:>4} {s['roi']:+6.1f}% clv{s['clv'] if s['clv'] is not None else '-':>6}"
    for g in ('all', 'ml', 'spread', 'total'):
        for W in WINS:
            for mv in MOVES:
                p = po.get(f'{g}|{W}|{mv}')
                if not p or not p['train']['n']: continue
                print(f"\n== {g}: {mv}+ pts in {W} min | events train {p['train']['n']} test {p['test']['n']} | drift event->close train {p['train']['cont']} test {p['test']['cont']} | gave back 2+ from peak {p['train']['gave2']} / {p['test']['gave2']}")
                for name in ('+0', '+5m', '+15m', '+60m', 'dip', 'T-15m'):
                    a = out.get(f'{g}|{W}|{mv}|{name}|follow'); b = out.get(f'{g}|{W}|{mv}|{name}|fade')
                    if a: print(f"   {name:6} FOLLOW train {f(a['train'])} | test {f(a['test'])}    FADE train {f(b['train']) if b else '-'} | test {f(b['test']) if b else '-'}")


if __name__ == '__main__':
    main()
