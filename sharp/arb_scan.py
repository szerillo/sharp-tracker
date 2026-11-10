#!/usr/bin/env python3
"""Locks and ladder violations on our own tape (overnight 11/10; proposed 11/9: "cross-venue arbitrage and Kalshi ladder violations").
From the 5-minute and 10-minute ticks (pregame, game markets and team totals), per pull:
  A. Cross-venue lock: Kalshi's ask on one side (plus its taker fee) + Novig's ask on the other side of the same market and line < $1,
     quotes within 3 minutes of each other. Also Kalshi vs Polymarket and Novig vs Polymarket.
  B. Kalshi ladder violation: on a spread or total ladder, the ask at an easier line is under the bid at a harder line (buy the easier,
     sell the harder: cannot lose, wins both in between). Fees on both legs.
An opportunity is counted once per market side per pull; "episodes" merges pulls less than 20 minutes apart.
Usage: python3 sharp/arb_scan.py [first_day] [last_day]"""
import os, sys, json, gzip, glob, math, collections, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
D0 = sys.argv[1] if len(sys.argv) > 1 else '2026-10-30'; D1 = sys.argv[2] if len(sys.argv) > 2 else '2026-11-10'
OTH = dict(home='away', away='home', over='under', under='over')
kfee = lambda p: math.ceil(0.07 * p * (1 - p) * 100 - 1e-9) / 100
def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def main():
    locks = collections.defaultdict(list); lad = collections.defaultdict(list); pulls = collections.Counter()
    for sp in ('nba', 'nfl', 'nhl', 'cfb', 'cbb', 'mma', 'soccer'):
        sched = {}
        try:
            d = json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json'))); ev = d if isinstance(d, list) else (d.get('events') if isinstance(d.get('events'), list) else list(d.values()))
            for e in ev:
                if isinstance(e, dict) and e.get('event_id') and e.get('start'): sched[str(e['event_id'])] = ts(e['start'] if len(e['start']) > 17 else e['start'].replace('Z', ':00Z'))
        except Exception: continue
        for sub in ('ticks5', 'ticks'):
            for f in sorted(glob.glob(os.path.join(ROOT, 'data', sp, sub, '2026-*.jsonl.gz'))):
                if not (D0 <= os.path.basename(f)[:10] <= D1): continue
                Q = collections.defaultdict(dict)      # (bucket, ev, market) -> {(venue, side, line): (bid, ask, t)}
                try:
                    for l in gzip.open(f, 'rt'):
                        if '"bid"' not in l: continue
                        try: x = json.loads(l)
                        except Exception: continue
                        v = x.get('venue'); m = x.get('market') or ''
                        if v not in ('Kalshi', 'Novig', 'Polymarket') or m.startswith('prop_') or x.get('side') not in OTH: continue
                        if sp == 'soccer' and m.endswith('ml'): continue
                        if m in ('1h_ml', '1q_ml', '1p_ml'): continue
                        e = str(x['event_id'])
                        if e not in sched: continue
                        t = ts(x['ts'])
                        if t >= sched[e] - 300: continue
                        Q[(int(t // 180), e, m)][(v, x['side'], x.get('line'))] = (x.get('bid'), x.get('ask'), t)
                except Exception as ex: print('skip', f, ex, file=sys.stderr); continue
                for (bk, e, m), D in Q.items():
                    pulls[sub] += 1
                    # A. locks across venues (and inside one venue)
                    for (v1, s1, l1), (b1, a1, t1) in D.items():
                        if not a1 or not 0.03 < a1 < 0.97: continue
                        l2 = l1 if (l1 is None or 'total' in m or 'tt_' in m) else -l1
                        for v2 in ('Kalshi', 'Novig', 'Polymarket'):
                            if v2 < v1: continue
                            o = D.get((v2, OTH[s1], l2))
                            if not o or not o[1] or not 0.03 < o[1] < 0.97: continue
                            if v1 == v2 and s1 > OTH[s1]: continue
                            cost = a1 + (kfee(a1) if v1 == 'Kalshi' else 0) + o[1] + (kfee(o[1]) if v2 == 'Kalshi' else 0)
                            if cost < 0.995: locks[(v1 + ' + ' + v2, sp, m.split('_')[-1] if m.startswith('1') else m)].append((e, m, s1, l1, round(1 - cost, 4), t1, sub))
                    # B. Kalshi ladders
                    K = collections.defaultdict(list)
                    for (v, s, ln), (b, a, t) in D.items():
                        if v == 'Kalshi' and ln is not None: K[s].append((ln, b, a))
                    for s, L in K.items():
                        # easier = higher line for home/away (more points) and under (higher total); lower line for over
                        easy_first = sorted(L, key=lambda z: -z[0] if s in ('home', 'away', 'under') else z[0])
                        best = 0; pair = None
                        for i, (le, be, ae) in enumerate(easy_first):
                            if not ae or not 0.03 < ae < 0.97: continue
                            for lh, bh, ah in easy_first[i + 1:]:
                                if not bh or not 0.03 < bh < 0.97 or lh == le: continue
                                edge = bh - ae - kfee(ae) - kfee(bh)            # buy the easier at its ask, sell the harder at its bid
                                if edge > best: best = edge; pair = (le, lh)
                        if best >= 0.005: lad[(sp, m)].append((e, s, pair, round(best, 4), bk * 180, sub))
    def episodes(L, tk, key):
        E = collections.defaultdict(list)
        for x in L: E[key(x)].append(x[tk])
        n = 0
        for v in E.values():
            v.sort(); n += 1 + sum(1 for a, b in zip(v, v[1:]) if b - a > 1200)
        return n
    print(f'{D0} to {D1}; market pulls scanned: {dict(pulls)}')
    print('A. Locks (cost under 99.5c after Kalshi fee)')
    for k, L in sorted(locks.items(), key=lambda kv: -len(kv[1])):
        g = sorted(x[4] for x in L)
        print(f"  {k[0]:<22} {k[1]:<7} {k[2]:<10} sightings {len(L):>5}  episodes {episodes(L, 5, lambda x: x[:4]):>4}  games {len({x[0] for x in L}):>4}  profit median {100 * g[len(g) // 2]:.1f}c  max {100 * g[-1]:.1f}c")
    print('B. Kalshi ladder violations (0.5c+ after both fees)')
    for k, L in sorted(lad.items(), key=lambda kv: -len(kv[1])):
        g = sorted(x[3] for x in L)
        print(f"  {k[0]:<7} {k[1]:<12} sightings {len(L):>5}  episodes {episodes(L, 4, lambda x: x[:2]):>4}  games {len({x[0] for x in L}):>4}  edge median {100 * g[len(g) // 2]:.1f}c  max {100 * g[-1]:.1f}c")
    json.dump(dict(locks={' | '.join(k): len(v) for k, v in locks.items()}, ladders={' | '.join(k): len(v) for k, v in lad.items()},
                   lock_examples=[x for L in locks.values() for x in sorted(L, key=lambda x: -x[4])[:3]], ladder_examples=[x for L in lad.values() for x in sorted(L, key=lambda x: -x[3])[:3]]),
              open(os.path.join(ROOT, 'data', 'research', 'arb_scan.json'), 'w'), default=str)


if __name__ == '__main__': main()
