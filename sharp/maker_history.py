#!/usr/bin/env python3
"""Kalshi makers on the long history (overnight 11/10; docs/maker_2026-11-10.md had 11 days). Every pregame trade on Kalshi's settled game
markets (data/kalshi/history, the kalshi-history release): the maker holds the side the taker did not take, at 1 - the taker's price.
Scored two ways: against Kalshi's own close (last pregame trade, both-sided within 2 hours) and on the settled result. Maker fee
0.0175 x p x (1 - p) per contract applied to every row. Games matched to ESPN starts as in sharp/exchange_backtest.py.
z is clustered by game. Usage: python3 sharp/maker_history.py   -> data/research/maker_history.json"""
import os, sys, re, json, gzip, glob, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
from sharp import sports as SP
import sharp.exchange_backtest as X
KH = os.path.join(ROOT, 'data', 'kalshi', 'history')
FEE = 0.0175


class Acc:
    def __init__(s): s.n = 0; s.c = 0.0; s.risk = 0.0; s.pnl = collections.defaultdict(float); s.clv = collections.defaultdict(float); s.cc = 0.0; s.fee = 0.0; s.months = collections.defaultdict(lambda: [0.0, 0.0])
    def add(s, g, q, c, won, clv, month):
        s.n += 1; s.c += c; s.risk += q * c; f = FEE * q * (1 - q) * c; s.fee += f; s.pnl[g] += (won - q) * c - f; s.months[month][0] += (won - q) * c - f; s.months[month][1] += q * c
        if clv is not None: s.clv[g] += clv * c; s.cc += c
    def out(s):
        def z(d, denom):
            if len(d) < 8 or not denom: return None
            se = sum(v * v for v in d.values()) ** 0.5 / denom; m = sum(d.values()) / denom
            return round(m / se, 2) if se else None
        tot = sum(s.pnl.values()); cl = sum(s.clv.values())
        mp = [v[0] / v[1] for v in s.months.values() if v[1] > 0]
        return dict(fills=s.n, games=len(s.pnl), risk=round(s.risk), roi=round(100 * tot / s.risk, 2) if s.risk else None, roi_z=z(s.pnl, s.risk), pnl=round(tot),
                    clv=round(100 * cl / s.cc, 2) if s.cc else None, clv_net=round(100 * (cl - s.fee * (s.cc / s.c if s.c else 0)) / s.cc, 2) if s.cc else None, clv_z=z(s.clv, s.cc),
                    months=len(mp), months_pos=sum(1 for x in mp if x > 0))


def main():
    sched = X.Sched(); mk = {}
    for f in glob.glob(os.path.join(KH, 'markets*.jsonl')):
        for l in open(f):
            try: r = json.loads(l); mk[r['ticker']] = r
            except Exception: pass
    A = collections.defaultdict(Acc); seen = collections.Counter(); rng = {}
    for f in sorted(glob.glob(os.path.join(KH, 'trades', '*.jsonl.gz'))):
        series = os.path.basename(f)[:-9]; pre = next((k for k in X.KSERIES_SPORT if series.startswith(k)), None)
        if not pre: continue
        sport = X.KSERIES_SPORT[pre]; mtype = {'GAME': 'ml', 'SPREAD': 'spread', 'TOTAL': 'total', 'FIGHT': 'ml'}.get(series[len(pre):])
        if not mtype: continue
        soccer = sport in ('epl', 'laliga', 'bundesliga', 'seriea', 'ligue1', 'mls', 'ucl'); grp = 'soccer' if soccer else sport
        by = collections.defaultdict(list)
        try:
            for l in gzip.open(f, 'rt'):
                r = json.loads(l); by[r['ticker']].append((X.ts(r['ts']), r['yes'], r['n'], r['taker']))
        except (EOFError, OSError, ValueError): pass
        for tk, L in by.items():
            m = mk.get(tk)
            if not m or m.get('result') not in ('yes', 'no'): seen['no result'] += 1; continue
            pe = SP.kalshi_event(m['event_ticker'].split('-', 1)[1])
            if not pe: seen['no event parse'] += 1; continue
            g = sched.kalshi(sport, pe[0], pe[1], home_first=soccer or sport == 'mma')
            if not g: seen['no schedule match ' + grp] += 1; continue
            start = X.ts(g['start']); pre_ = sorted(x for x in L if x[0] < start)
            if len(pre_) < 5: continue
            # Kalshi's close: last pregame trade, with both a yes-taker and a no-taker print in the last 2 hours (a two-sided mid)
            ly = next((p for t, p, n, tk_ in reversed(pre_) if tk_ == 'yes' and start - t < 7200), None); ln = next((p for t, p, n, tk_ in reversed(pre_) if tk_ == 'no' and start - t < 7200), None)
            close = (ly + ln) / 2 if ly is not None and ln is not None and abs(ly - ln) <= 0.05 else None
            res = 1.0 if m['result'] == 'yes' else 0.0; gid = (sport, g['start'], g['away'], g['home']); month = g['start'][:7]
            rng[grp] = (min(rng.get(grp, ('9', ''))[0], g['start'][:10]), max(rng.get(grp, ('', ''))[1], g['start'][:10]))
            for t, yp, n, taker in pre_:
                if not (0.02 <= yp <= 0.98) or n <= 0: continue
                if taker == 'no': q, won, clv = yp, res, (close - yp) if close is not None else None                 # the maker bought yes
                else: q, won, clv = 1 - yp, 1 - res, ((1 - close) - (1 - yp)) if close is not None else None           # the maker bought no
                h = (start - t) / 3600; usd = q * n
                for key in (('all',), ('sport', grp, mtype), ('sportall', grp), ('time', '24h+' if h >= 24 else '6-24h' if h >= 6 else '1-6h' if h >= 1 else 'last hour'),
                            ('size', 'under $100' if usd < 100 else '$100-1k' if usd < 1000 else '$1k-10k' if usd < 1e4 else '$10k+'),
                            ('price', 'under 25c' if q < .25 else '25-40c' if q < .4 else '40-60c' if q < .6 else '60-75c' if q < .75 else '75c+'),
                            ('price_ml', grp, 'under 25c' if q < .25 else '25-40c' if q < .4 else '40-60c' if q < .6 else '60-75c' if q < .75 else '75c+') if mtype == 'ml' else None,
                            ('year', g['start'][:4]), ('combo', 'last hour, under $1k' if h < 1 and usd < 1000 else 'other'),
                            ('dogtime', ('maker under 40c' if q < .4 else 'maker 60c+' if q >= .6 else 'maker 40-60c') + ', ' + ('last hour' if h < 1 else '1-24h' if h < 24 else '24h+'))):
                    if key: A[key].add(gid, q, n, won, clv, month)
    out = dict(seen=dict(seen), ranges=rng, rows={'|'.join(k): a.out() for k, a in A.items()})
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'maker_history.json'), 'w'), indent=0)
    print(dict(seen)); print(rng)
    for k in sorted(out['rows']):
        r = out['rows'][k]
        print(f"{k:<44} fills {r['fills']:>8} games {r['games']:>5} risk ${r['risk']:>12,} | settled ROI after fee {str(r['roi']):>6}% (z {r['roi_z']}) ${r['pnl']:>10,} months+ {r['months_pos']}/{r['months']} | vs Kalshi close {str(r['clv']):>6}c net {str(r['clv_net']):>6}c (z {r['clv_z']})")


if __name__ == '__main__': main()
