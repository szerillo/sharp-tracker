#!/usr/bin/env python3
"""Does big money on Novig win? Backtest on the public trade tape (data/novig/tape: every STRAIGHT taker fill since 2026-08-03, no user
ids) graded against Novig's own settlement (data/novig/catalog, result WIN/LOSS per outcome).

Novig's app shows the biggest open positions per market, but the API exposes positions only for the caller's own account and the tape
has no user ids, so positions cannot be rebuilt. The testable proxy is the size of each taker fill (a taker is the aggressive side:
they crossed the spread to get the bet down).

  1. Per fill, by size bucket: dollar-weighted ROI and flat ROI of the bet the taker made, pregame fills only, moneylines (and, for
     comparison, every game market).
  2. Per fight / game ("position proxy"): net taker dollars in $1k+ fills on each side before the start; follow the side with more big
     money at the last pregame price on the tape. One bet per market.
  3. Timing: big fills more than 24h out vs inside 2h.
Prints a report and writes data/state/novig_bigmoney.json. Usage: python3 sharp/novig_bigmoney.py [--league UFC]"""
import os, sys, json, gzip, glob, math, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
from novig_catalog import CDIR
import datetime as dt
BUCKETS = [(0, 100), (100, 500), (500, 1000), (1000, 5000), (5000, 1e12)]
BIG = 1000.0
ARGS = sys.argv[1:]


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


LEAGUES = [ARGS[ARGS.index('--league') + 1]] if '--league' in ARGS else ['UFC', 'NFL', 'NBA', 'NCAAF', 'NHL', 'MLB']
GAME_TYPES = {'MONEY', 'MONEYLINE', 'SPREAD', 'TOTAL'}


def load_cat():
    """Only settled game markets in the leagues asked for, slimmed to what the grade needs (the full catalog is ~1M markets)."""
    cat = {}
    for f in sorted(glob.glob(os.path.join(CDIR, '*.jsonl.gz'))):
        for l in gzip.open(f, 'rt'):
            if '"result"' not in l: continue
            v = json.loads(l)
            if v.get('league') not in LEAGUES or v.get('type') not in GAME_TYPES or not v.get('start_ts'): continue
            cat[v['market']] = dict(league=v['league'], type=v['type'], start_ts=v['start_ts'], result=v['result'], event=v.get('event'))
    return cat


def main():
    cat = load_cat(); print(f"[bigmoney] {len(cat):,} settled game markets in {LEAGUES}", flush=True)
    by_league = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'novig', 'tape', '*.jsonl.gz'))):
        for l in gzip.open(f, 'rt'):
            i = l.find('"market": "'); mid = l[i + 11:i + 47] if i >= 0 else None
            if mid not in cat: continue
            r = json.loads(l); m = cat.get(r['market'])
            if not m or r['outcome'] not in m['result']: continue
            t = ts(r['ts']); st = m['start_ts'] / 1000
            if t >= st: continue                                   # pregame only
            res = m['result'][r['outcome']]
            if res not in ('WIN', 'LOSS'): continue
            cost = r['price'] * r['qty']; pnl = (r['qty'] - cost) if res == 'WIN' else -cost
            by_league[m['league']].append(dict(m=r['market'], o=r['outcome'], typ=m['type'], cost=cost, pnl=pnl, price=r['price'], won=res == 'WIN', t=t, ttk=(st - t) / 3600, event=m.get('event')))
    out = {}
    for lg in LEAGUES:
        F = by_league.get(lg, [])
        if not F: continue
        rep = dict(fills=len(F), dollars=round(sum(x['cost'] for x in F)), markets=len({x['m'] for x in F}))
        for scope, sel in (('moneyline', lambda x: x['typ'] in ('MONEY', 'MONEYLINE')), ('all game markets', lambda x: x['typ'] in ('MONEY', 'MONEYLINE', 'SPREAD', 'TOTAL'))):
            G = [x for x in F if sel(x)]
            rows = []
            for lo, hi in BUCKETS:
                B = [x for x in G if lo <= x['cost'] < hi]
                if not B: continue
                d = sum(x['cost'] for x in B); p = sum(x['pnl'] for x in B)
                flat = [x['pnl'] / x['cost'] for x in B if x['cost'] > 0]
                mu = sum(flat) / len(flat); sd = (sum((v - mu) ** 2 for v in flat) / max(1, len(flat) - 1)) ** 0.5
                # market-level clustering: z on per-market mean flat ROI
                pm = collections.defaultdict(list)
                for x in B: pm[x['m']].append(x['pnl'] / x['cost'])
                mm = [sum(v) / len(v) for v in pm.values()]; mmu = sum(mm) / len(mm); msd = (sum((v - mmu) ** 2 for v in mm) / max(1, len(mm) - 1)) ** 0.5
                rows.append(dict(bucket=f"${lo:,.0f}-{'' if hi > 1e11 else f'${hi:,.0f}'}".replace('-', '+') if hi > 1e11 else f"${lo:,.0f}-${hi:,.0f}", fills=len(B), markets=len(pm), dollars=round(d),
                                 roi_dollar=round(100 * p / d, 2), roi_flat=round(100 * mu, 2), z_market=round(mmu / (msd / math.sqrt(len(mm))), 2) if len(mm) > 2 and msd > 0 else None,
                                 avg_price=round(sum(x['price'] for x in B) / len(B), 3)))
            rep[scope] = rows
        # position proxy: per moneyline market, net big-fill dollars per outcome before the start
        pos = []
        mk = collections.defaultdict(list)
        for x in F:
            if x['typ'] in ('MONEY', 'MONEYLINE'): mk[x['m']].append(x)
        for mid, L in mk.items():
            big = collections.Counter()
            for x in L:
                if x['cost'] >= BIG: big[x['o']] += x['cost']
            if not big: continue
            (o1, d1), *rest = big.most_common(); d2 = rest[0][1] if rest else 0
            if d1 - d2 < BIG: continue
            last = max((x for x in L if x['o'] == o1), key=lambda x: x['t'])      # last pregame fill on that outcome = the price you could still get
            won = last['won']; pr = last['price']; pnl = (1 - pr) / pr if won else -1.0
            pos.append(dict(market=mid, event=L[0]['event'], big_dollars=round(d1), other_big=round(d2), price=pr, won=won, roi=pnl))
        if pos:
            r_ = [p['roi'] for p in pos]; mu = sum(r_) / len(r_); sd = (sum((v - mu) ** 2 for v in r_) / max(1, len(r_) - 1)) ** 0.5
            exp = sum(p['price'] for p in pos) / len(pos)
            rep['follow_big_money'] = dict(markets=len(pos), win=round(sum(p['won'] for p in pos) / len(pos), 3), implied=round(exp, 3), roi_flat=round(100 * mu, 2),
                                           z=round(mu / (sd / math.sqrt(len(r_))), 2) if len(r_) > 2 and sd > 0 else None,
                                           by_size={k: (lambda S: dict(n=len(S), roi=round(100 * sum(p['roi'] for p in S) / len(S), 1), win=round(sum(p['won'] for p in S) / len(S), 3)) if S else None)(
                                               [p for p in pos if lo <= p['big_dollars'] < hi]) for k, (lo, hi) in {'$1k-5k': (1000, 5000), '$5k-20k': (5000, 20000), '$20k+': (20000, 1e12)}.items()})
        # timing of big fills
        T = {}
        for name, sel in (('more than 24h out', lambda x: x['ttk'] > 24), ('2-24h', lambda x: 2 < x['ttk'] <= 24), ('last 2h', lambda x: x['ttk'] <= 2)):
            B = [x for x in F if x['cost'] >= BIG and x['typ'] in ('MONEY', 'MONEYLINE') and sel(x)]
            if B: T[name] = dict(fills=len(B), dollars=round(sum(x['cost'] for x in B)), roi_dollar=round(100 * sum(x['pnl'] for x in B) / sum(x['cost'] for x in B), 2))
        rep['big_fills_by_timing'] = T
        out[lg] = rep
        print(f"\n=== {lg}: {rep['fills']:,} pregame taker fills, ${rep['dollars']:,}, {rep['markets']} settled markets ===")
        for scope in ('moneyline', 'all game markets'):
            print(f"  {scope}:")
            for r in rep.get(scope, []): print(f"    {r['bucket']:>14}  fills {r['fills']:>7,}  mkts {r['markets']:>5}  ${r['dollars']:>11,}  ROI$ {r['roi_dollar']:+6.2f}%  flat {r['roi_flat']:+6.2f}%  z(mkt) {r['z_market']}  avg px {r['avg_price']}")
        if 'follow_big_money' in rep: print(f"  follow the side with more $1k+ money: {rep['follow_big_money']}")
        print(f"  $1k+ fills by timing: {rep['big_fills_by_timing']}")
    json.dump(out, open(os.path.join(ROOT, 'data', 'state', 'novig_bigmoney.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
