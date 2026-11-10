#!/usr/bin/env python3
"""Where could we rest an offer? (Sean 11/10: "any softer markets we can reprice ... scan Kalshi and Novig daily for opportunities that
are way off from market, to offer.") For every pregame Kalshi and Novig quote in the tick files, on any market where Pinnacle quotes both
sides at the same line: room = Pinnacle no-vig fair minus the venue's best bid on that side (how far under fair the best bid sits; a bid
of ours inside that gap is first in line), and the venue's spread. Summed by venue, sport and market, with the maker fills that happened
in those markets (trades5). One observation per market side per tick.
Usage: python3 sharp/offer_scan.py [first_day] [last_day]"""
import os, sys, json, gzip, glob, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maker_test as M
D0 = sys.argv[1] if len(sys.argv) > 1 else '2026-11-07'; D1 = sys.argv[2] if len(sys.argv) > 2 else '2026-11-09'
SP = ['nba', 'nfl', 'nhl', 'cfb', 'cbb', 'mma', 'soccer', 'tennis']


def grp(m): return 'player props' if m.startswith('prop_') else m


def main():
    start = {}
    for sp in SP:
        p = os.path.join(M.ROOT, 'data', sp, 'schedule.json')
        if not os.path.exists(p): continue
        d = json.load(open(p)); ev = d if isinstance(d, list) else (d.get('events') if isinstance(d.get('events'), list) else list(d.values()))
        for e in ev:
            if isinstance(e, dict) and e.get('event_id') and e.get('start'):
                try: start[str(e['event_id'])] = M.ts_(e['start'] if len(e['start']) > 17 else e['start'].replace('Z', ':00Z'))
                except Exception: pass
    R = collections.defaultdict(lambda: dict(room=[], spread=[], mk=set(), nopin=0, n=0))
    tot = lambda m: 'total' in m or m.startswith('prop_') or 'tt_' in m
    for sp in SP:
        files = [f for f in sorted(glob.glob(os.path.join(M.ROOT, 'data', sp, 'ticks', '2026-*.jsonl.gz'))) if D0 <= os.path.basename(f)[:10] <= D1]
        pin = collections.defaultdict(lambda: ([], [])); ex = []
        for f in files:
            try:
                for l in gzip.open(f, 'rt'):
                    try: x = json.loads(l)
                    except Exception: continue
                    v = x.get('venue'); m = x.get('market')
                    if v not in ('Pinnacle', 'Kalshi', 'Novig') or not m or (sp == 'soccer' and m == 'ml'): continue
                    ev = str(x['event_id'])
                    if ev not in start: continue
                    t = M.ts_(x['ts'])
                    if t >= start[ev]: continue
                    k = (ev, m, x.get('side'), x.get('line'), x.get('participant') if m.startswith('prop_') else None)
                    if v == 'Pinnacle':
                        if x.get('american') is not None: pin[k][0].append(t); pin[k][1].append(M.imp(x['american']))
                    else: ex.append((v, k, t, x.get('bid'), x.get('ask')))
            except Exception as e: print('skip', f, e, file=sys.stderr)
        for k, (T, P) in pin.items():
            o = sorted(range(len(T)), key=T.__getitem__); pin[k] = ([T[i] for i in o], [P[i] for i in o])
        for v, k, t, b, a in ex:
            ev, m, side, line, pk = k; r = R[(v, sp, grp(m))]; r['n'] += 1
            o = M.OTH.get(side)
            ia = M.last(pin, k, t, 1800); ib = M.last(pin, (ev, m, o, line if (line is None or tot(m)) else -line, pk), t, 1800) if o else None
            if not (ia and ib): r['nopin'] += 1; continue
            fair = ia / (ia + ib); r['mk'].add(k); r['room'].append(fair - (b if b else 0.0))
            if b and a: r['spread'].append(a - b)
    print(f'{D0} to {D1}. room = Pinnacle fair minus the best bid (cents). One row per venue, sport, market with 200+ priced quotes.')
    print(f"{'venue':<7}{'sport':<7}{'market':<14}{'quotes':>8}{'sides':>7}{'no Pinn':>8}{'spread':>8}{'room med':>9}{'room 2c+':>9}{'room 4c+':>9}")
    out = []
    for (v, sp, m), r in R.items():
        if len(r['room']) < 200: continue
        rm = r['room']; out.append((v, sp, m, len(rm), len(r['mk']), r['nopin'] / max(1, r['n']), st.median(r['spread']) if r['spread'] else None,
                                    st.median(rm), sum(1 for x in rm if x >= .02) / len(rm), sum(1 for x in rm if x >= .04) / len(rm)))
    for o in sorted(out, key=lambda o: -o[9]):
        print(f"{o[0]:<7}{o[1]:<7}{o[2]:<14}{o[3]:>8}{o[4]:>7}{o[5]:>8.0%}{(100 * o[6] if o[6] is not None else float('nan')):>7.1f}c{100 * o[7]:>8.1f}c{o[8]:>9.0%}{o[9]:>9.0%}")
    json.dump([dict(zip(('venue', 'sport', 'market', 'quotes', 'sides', 'no_pinnacle', 'spread', 'room_med', 'room2', 'room4'), o)) for o in out],
              open(os.path.join(M.ROOT, 'data', 'research', 'offer_scan.json'), 'w'))


if __name__ == '__main__': main()
