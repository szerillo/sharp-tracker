#!/usr/bin/env python3
"""Wider exchange-signal grid (Sean, 10/31: "raise the bar ... try 3%, 4% ... variety of ways"), with an honest train/test split.

Data: the same settled two-outcome game markets as sharp/flow_split.py (Kalshi history + Novig public tape), pregame taker fills,
fill size in risk-equivalent dollars (contracts x min(p, 1-p)). For every market and entry time (T-6h, T-3h, T-1h, T-15m) it builds
one feature row: two-sided mid now, at kickoff, 1h and 3h earlier and at the first two-sided print; big / small net and gross dollars
at several size cuts. Families of signals (each bet = the side named, at the entry mid, one bet per game x market type x signal):

  MOVE_F / MOVE_X   the mid moved >= m points (2/3/4/6) over the window (1h / 3h / since open): follow it / fade it
  DIV               big money (>= S) net >= S on one side, small money (<= s) net the other way; optional bars on how one-sided
                    each is (share of gross: big 0/50/80%, small 0/20/40%)
  DIV+MOVE          DIV and the price already moved >= m toward the big side (agree) or away from it (against)
  STEAM             price moved >= m toward a side AND big money is net >= S on that same side (small money ignored)
Each also split by market type (ml / spread / total) and by price (favorite / dog side).

Train = games before 2026-10-01, test = October onward. A cell is only "found" if it is n >= 100 and z >= 2 on train; its
test result is then read once. With hundreds of cells, ~2.5% clear z 2 on train by luck alone, so the count of train hits that keep
their sign on test is the noise check.
Writes data/state/flow_grid.json. Usage: python3 sharp/flow_grid.py"""
import os, sys, json, math, collections, datetime as dt, itertools
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import sharp.exchange_backtest as EB
from flow_split import market_rows

ENTRIES = {'T-6h': 6 * 3600, 'T-3h': 3 * 3600, 'T-1h': 3600, 'T-15m': 900}
BIGS = (250.0, 500.0, 1000.0, 2500.0); SMALLS = (25.0, 50.0, 100.0)
SPLIT = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc).timestamp()


def mid(pre, t):
    p, two = EB.px_at(pre, t)
    return p if two == 2 else None


def build(rows):
    F = []
    for v, sp, mt, gk, start, ry, L in rows:
        pre_all = sorted(x for x in L if x[0] < start)
        if len(pre_all) < 5: continue
        close = mid(pre_all, start)
        first2 = None; ly = ln = None
        for x in pre_all:                       # first time a two-sided mid exists (a yes-buy and a no-buy within 2h)
            if x[3] > 0: ly = x[0]
            else: ln = x[0]
            if ly is not None and ln is not None and abs(ly - ln) <= 2 * 3600: first2 = x[0]; break
        for en, sec in ENTRIES.items():
            E = start - sec; pre = [x for x in pre_all if x[0] < E]
            if len(pre) < 5: continue
            p = mid(pre, E)
            if p is None or not (0.03 < p < 0.97): continue
            f = dict(v=v, sp=sp, mt=mt, gk=gk, start=start, ry=ry, en=en, p=p, close=close)
            for w, ws in (('1h', 3600), ('3h', 3 * 3600)):
                q = mid(pre, E - ws); f['mv_' + w] = None if q is None else 100 * (p - q)
            f['mv_open'] = None if first2 is None or first2 >= E - 1800 else (lambda q: None if q is None else 100 * (p - q))(mid(pre, first2 + 1))
            for S in BIGS:
                b = [x for x in pre if x[2] >= S]; f[f'bn{int(S)}'] = sum(x[2] * x[3] for x in b); f[f'bg{int(S)}'] = sum(x[2] for x in b)
            for s in SMALLS:
                b = [x for x in pre if x[2] <= s]; f[f'sn{int(s)}'] = sum(x[2] * x[3] for x in b); f[f'sg{int(s)}'] = sum(x[2] for x in b)
            F.append(f)
    return F


def grade(f, d):
    price = f['p'] if d > 0 else 1 - f['p']; won = f['ry'] if d > 0 else 1 - f['ry']
    clv = None if f['close'] is None else 100 * ((f['close'] if d > 0 else 1 - f['close']) - price)
    return dict(roi=(1 - price) / price if won else -1.0, won=won, price=price, clv=clv)


def stats(B):
    if not B: return None
    r = [b['roi'] for b in B]; mu = sum(r) / len(r); sd = (sum((x - mu) ** 2 for x in r) / max(1, len(r) - 1)) ** 0.5
    c = [b['clv'] for b in B if b['clv'] is not None]
    return dict(n=len(B), roi=round(100 * mu, 2), z=round(mu / (sd / math.sqrt(len(B))), 2) if len(B) > 2 and sd > 0 else 0.0,
                clv=round(sum(c) / len(c), 2) if c else None)


def signals():
    """-> list of (name, fn(f) -> direction +1/-1 or 0, strength)"""
    S = []
    for w, m in itertools.product(('1h', '3h', 'open'), (2, 3, 4, 6)):
        def mv(f, w=w, m=m):
            x = f['mv_' + w]; return (0, 0) if x is None or abs(x) < m else ((1 if x > 0 else -1), abs(x))
        S.append((f'MOVE_F {w} >={m}pt', mv, 1)); S.append((f'MOVE_X {w} >={m}pt', mv, -1))
    for Bv, sv, bsh, ssh in itertools.product(BIGS, SMALLS, (0, .5, .8), (0, .2, .4)):
        def dv(f, B=int(Bv), s=int(sv), bsh=bsh, ssh=ssh):
            bn, bg, sn, sg = f[f'bn{B}'], f[f'bg{B}'], f[f'sn{s}'], f[f'sg{s}']
            if abs(bn) < B or not sg or (bn > 0) == (sn > 0) or sn == 0: return (0, 0)
            if abs(bn) / bg < bsh or abs(sn) / sg < ssh: return (0, 0)
            return (1 if bn > 0 else -1), abs(bn)
        S.append((f'DIV big>={int(Bv)} small<={int(sv)} bigshare>={int(100*bsh)}% smallshare>={int(100*ssh)}%', dv, 1))
    for Bv, w, m in itertools.product((250.0, 500.0, 1000.0), ('1h', '3h', 'open'), (2, 3, 4)):
        for mode in ('agree', 'against'):
            def dm(f, B=int(Bv), w=w, m=m, mode=mode):
                bn, sn, x = f[f'bn{B}'], f['sn50'], f['mv_' + w]
                if abs(bn) < B or sn == 0 or (bn > 0) == (sn > 0) or x is None or abs(x) < m: return (0, 0)
                d = 1 if bn > 0 else -1
                return (d, abs(bn)) if ((x > 0) == (d > 0)) == (mode == 'agree') else (0, 0)
            S.append((f'DIV+MOVE {mode} big>={int(Bv)} {w} >={m}pt', dm, 1))
        def st(f, B=int(Bv), w=w, m=m):
            bn, x = f[f'bn{B}'], f['mv_' + w]
            if abs(bn) < B or x is None or abs(x) < m or (bn > 0) != (x > 0): return (0, 0)
            return (1 if bn > 0 else -1), abs(bn)
        S.append((f'STEAM big>={int(Bv)} {w} >={m}pt', st, 1))
    return S


def main():
    rows = market_rows(); print(f"[flow_grid] {len(rows)} settled markets", flush=True)
    F = build(rows); print(f"[flow_grid] {len(F)} market x entry rows", flush=True)
    del rows
    SUBS = {'all': lambda f, d: True, 'ml': lambda f, d: f['mt'] == 'ml', 'spread': lambda f, d: f['mt'] == 'spread', 'total': lambda f, d: f['mt'] == 'total',
            'fav side': lambda f, d: f['mt'] != 'total' and (f['p'] if d > 0 else 1 - f['p']) > 0.5, 'dog side': lambda f, d: f['mt'] != 'total' and (f['p'] if d > 0 else 1 - f['p']) < 0.5}
    out = []
    for name, fn, sign in signals():
        hits = collections.defaultdict(dict)        # (venue, entry, sub) -> gk -> (strength, bet)
        for f in F:
            d, strength = fn(f)
            if not d: continue
            d *= sign
            for sub, ok in SUBS.items():
                if not ok(f, d): continue
                k = (f['v'], f['en'], sub); cur = hits[k].get(f['gk'])
                if cur is None or strength > cur[0]: hits[k][f['gk']] = (strength, dict(grade(f, d), train=f['start'] < SPLIT, sp=f['sp']))
        for (v, en, sub), H in hits.items():
            B = [b for _, b in H.values()]
            tr = stats([b for b in B if b['train']]); te = stats([b for b in B if not b['train']])
            out.append(dict(signal=name, venue=v, entry=en, sub=sub, train=tr, test=te, all=stats(B)))
    found = [r for r in out if r['train'] and r['train']['n'] >= 100 and r['train']['z'] >= 2]
    held = [r for r in found if r['test'] and r['test']['n'] >= 30 and r['test']['roi'] > 0]
    eligible = [r for r in out if r['train'] and r['train']['n'] >= 100]
    json.dump(dict(cells=len(out), eligible=len(eligible), found=len(found), held=len(held), rows=out), open(os.path.join(ROOT, 'data', 'state', 'flow_grid.json'), 'w'))
    print(f"\n{len(out)} cells, {len(eligible)} with train n>=100; {len(found)} clear z>=2 on train (luck alone ~{0.025*len(eligible):.0f}); {len(held)} of those positive on Oct test (n>=30)")
    print(f"{'signal':58} {'venue':6} {'entry':5} {'sub':8} | train n  ROI    z    CLV | test n  ROI    z    CLV")
    for r in sorted(found, key=lambda r: -r['train']['z'])[:60]:
        t, e = r['train'], r['test'] or dict(n=0, roi=0, z=0, clv=None)
        print(f"{r['signal'][:58]:58} {r['venue']:6} {r['entry']:5} {r['sub']:8} | {t['n']:6} {t['roi']:+5.1f}% {t['z']:4.1f} {str(t['clv']):>5} | {e['n']:5} {e['roi']:+5.1f}% {e['z']:4.1f} {str(e['clv']):>5}")
    # move bar summary: does a bigger move bar help? (all subs, all entries)
    print("\nMove bar (follow / fade), all markets, by venue x window x bar, full sample:")
    for v in ('Kalshi', 'Novig'):
        for w in ('1h', '3h', 'open'):
            line = []
            for m in (2, 3, 4, 6):
                for kind in ('F', 'X'):
                    rr = [r for r in out if r['venue'] == v and r['sub'] == 'all' and r['entry'] == 'T-1h' and r['signal'] == f'MOVE_{kind} {w} >={m}pt']
                    if rr and rr[0]['all']: line.append(f"{kind}{m}: n{rr[0]['all']['n']} {rr[0]['all']['roi']:+.1f}% z{rr[0]['all']['z']}")
            print(f"  {v:6} T-1h, move over {w:4}: " + ' | '.join(line))


if __name__ == '__main__':
    main()
