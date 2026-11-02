#!/usr/bin/env python3
"""Do the exchanges lag Pinnacle? (timing step 2, docs/steam_timing_2026-11-01.md). For every Pinnacle-origin move on the move tape
(data/state/moves.jsonl.gz: 2+ pt devigged move inside 15 minutes), look up what a taker could pay at Kalshi and Novig on the moved
side over the next 60 minutes (5-minute fast tape, same market and line, ask, Kalshi fee included), and compare it with
  edge   = Pinnacle's new devigged price minus that cost (is the exchange still on the old number?)
  clv    = the market's last pregame price (the tape's close for the move) minus that cost
at the first tick after the move (+0-5 min), +15m, +30m and +60m. Positive = the stale exchange price was worth taking.
Writes data/research/catchup.json. Usage: python3 sharp/catchup.py"""
import os, sys, json, gzip, glob, math, bisect, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
KFEE = 0.07


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def kfee(p): return math.ceil(KFEE * p * (1 - p) * 100) / 100


def main():
    M = [json.loads(l) for l in gzip.open(os.path.join(ROOT, 'data', 'state', 'moves.jsonl.gz'), 'rt')]
    P = [m for m in M if m['origin'] == 'Pinnacle' and m.get('close') is not None]
    need = {(m['sport'], m['event_id']) for m in P}
    # exchange asks per (event, market, line, side, venue): sorted [(t, ask)]
    Q = collections.defaultdict(list)
    for sp in {s for s, _ in need}:
        for f in sorted(glob.glob(os.path.join(ROOT, 'data', sp, 'ticks5', '*.jsonl.gz'))):
            try:
                for l in gzip.open(f, 'rt'):
                    if '"Kalshi"' not in l and '"Novig"' not in l: continue
                    r = json.loads(l)
                    if (sp, r.get('event_id')) not in need or r.get('ask') is None or r.get('bid') is None: continue
                    if r['ask'] - r['bid'] > 0.06: continue
                    Q[(r['event_id'], r['market'], r.get('line'), r['side'], r['venue'])].append((ts(r['ts']), r['ask']))
            except (EOFError, OSError): pass
    for k in Q: Q[k].sort()
    OFFS = {'+0': 0, '+15m': 15, '+30m': 30, '+60m': 60}
    out = collections.defaultdict(list)
    for m in P:
        t0 = ts(m['ts']); side = m['side']
        p_new = m['p1'] if side in ('home', 'over') else 1 - m['p1']; p_close = m['close'] if side in ('home', 'over') else 1 - m['close']
        for v in ('Kalshi', 'Novig'):
            L = Q.get((m['event_id'], m['market'], m['line'], side, v)) or (Q.get((m['event_id'], m['market'], None, side, v)) if m['market'] == 'ml' else None)
            if not L: continue
            T = [x[0] for x in L]
            for name, off in OFFS.items():
                tt = t0 + dt.timedelta(minutes=off); i = bisect.bisect_left(T, tt)
                if i >= len(L) or (L[i][0] - tt).total_seconds() > 600 or L[i][0] >= ts(m['start']): continue
                ask = L[i][1]; cost = ask + (kfee(ask) if v == 'Kalshi' else 0)
                out[(v, name)].append(dict(edge=100 * (p_new - cost), clv=100 * (p_close - cost), sport=m['sport'], size=m['size_pts']))
    res = {}
    for (v, name), L in sorted(out.items()):
        e = [x['edge'] for x in L]; c = [x['clv'] for x in L]
        res[f'{v} {name}'] = dict(n=len(L), edge_mean=round(sum(e) / len(e), 2), edge_pos=round(sum(x > 0 for x in e) / len(e), 2),
                                  clv_mean=round(sum(c) / len(c), 2), clv_pos=round(sum(x > 0 for x in c) / len(c), 2))
        print(f"{v:7} {name:5} n {len(L):3}  vs Pinnacle's new price {res[f'{v} {name}']['edge_mean']:+.2f} pts ({100 * res[f'{v} {name}']['edge_pos']:.0f}% positive)   CLV {res[f'{v} {name}']['clv_mean']:+.2f} ({100 * res[f'{v} {name}']['clv_pos']:.0f}% positive)")
    json.dump(dict(moves=len(P), cells=res), open(os.path.join(ROOT, 'data', 'research', 'catchup.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
