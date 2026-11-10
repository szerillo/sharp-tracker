#!/usr/bin/env python3
"""Novig makers against Pinnacle at the time of each fill, every market type we log (overnight 11/10). The 11-day maker test
(sharp/maker_test.py) had game lines only, from our own polled tape. Novig's public CSV has every fill with the maker's side, and our
ticks carry Novig's market and outcome ids, so every maker fill on a market in our ticks (game lines, period lines, team totals, player
props) can be priced against Pinnacle's no-vig fair at that moment and at the close.
Also the resting-bid version: a bid k cents under Pinnacle's fair (half-cent prices), filled by every maker fill at or under it, paid at
our bid. Pregame only; Pinnacle fair = both sides at the same line, last quote inside 30 minutes (close: inside the hour before the start).
Runs on a GitHub runner (data.novig.com). Usage: python3 sharp/novig_maker_select.py [first_day] [last_day]"""
import os, sys, csv, json, gzip, glob, math, bisect, time, collections, datetime as dt, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import maker_test as M
from novig_maker_history import fetch_to, BASE
D0 = sys.argv[1] if len(sys.argv) > 1 else '2026-10-30'; D1 = sys.argv[2] if len(sys.argv) > 2 else (dt.date.today() - dt.timedelta(days=1)).isoformat()
SPORTS = ['nba', 'nfl', 'nhl', 'cfb', 'cbb', 'mma', 'soccer']
THREE = ('1h_ml', '1q_ml', '1p_ml')            # a tie is a third outcome there; not comparable with Pinnacle's two-way price
def tot(m): return 'total' in m or m.startswith('prop_') or 'tt_' in m
def grp(m): return 'player props' if m.startswith('prop_') else 'team totals' if 'tt_' in m else 'period lines' if m[:3] in ('1h_', '1q_', '1p_') else 'game ' + m


def main():
    start = {}; NV = {}; pin = collections.defaultdict(lambda: ([], []))
    for sp in SPORTS:
        p = os.path.join(ROOT, 'data', sp, 'schedule.json')
        if not os.path.exists(p): continue
        d = json.load(open(p)); ev = d if isinstance(d, list) else (d.get('events') if isinstance(d.get('events'), list) else list(d.values()))
        for e in ev:
            if isinstance(e, dict) and e.get('event_id') and e.get('start'):
                try: start[str(e['event_id'])] = M.ts_(e['start'] if len(e['start']) > 17 else e['start'].replace('Z', ':00Z'))
                except Exception: pass
        for sub in ('ticks', 'ticks5'):
            for f in sorted(glob.glob(os.path.join(ROOT, 'data', sp, sub, '2026-*.jsonl.gz'))):
                try:
                    for l in gzip.open(f, 'rt'):
                        isp = '"venue":"Pinnacle"' in l
                        if not isp and '"venue":"Novig"' not in l: continue
                        try: x = json.loads(l)
                        except Exception: continue
                        m = x.get('market') or ''
                        if m in THREE or (sp == 'soccer' and m == 'ml') or x.get('side') not in M.OTH: continue
                        k = (str(x['event_id']), m, x['side'], x.get('line'), x.get('participant') if m.startswith('prop_') else None)
                        if isp:
                            if x.get('american') is not None: pin[k][0].append(M.ts_(x['ts'])); pin[k][1].append(M.imp(x['american']))
                        else:
                            e_ = x.get('extra') or {}
                            if e_.get('market_id') and e_.get('outcome_id'): NV[(e_['market_id'], e_['outcome_id'])] = (sp, k)
                except Exception as ex: print('skip', f, ex, flush=True)
        print(f'{sp}: {len(NV)} Novig outcomes mapped, {len(pin)} Pinnacle series ({round(time.time() - T0)}s)', flush=True)
    for k, (T, P) in pin.items():
        o = sorted(range(len(T)), key=T.__getitem__); pin[k] = ([T[i] for i in o], [P[i] for i in o])
    def fair(k, t, age):
        ev, m, side, line, pk = k
        a = M.last(pin, k, t, age); b = M.last(pin, (ev, m, M.OTH[side], line if (line is None or tot(m)) else -line, pk), t, age)
        return a / (a + b) if a and b else None
    A = collections.defaultdict(M.Acc); seen = collections.Counter(); days = []
    d = dt.date.fromisoformat(D0); end = dt.date.fromisoformat(D1); tmp = os.path.join(tempfile.gettempdir(), 'novig_trades.csv')
    while d <= end:
        ds = d.isoformat(); d += dt.timedelta(days=1)
        if not fetch_to(f"{BASE}/{ds}/trades.csv", tmp): print(f'{ds}: no file', flush=True); continue
        n = 0
        with open(tmp, newline='') as fh:
            for r in csv.DictReader(fh):
                if r.get('side') != 'MAKER' or r.get('tradeType') != 'STRAIGHT': continue
                hit = NV.get((r['marketId'], r['outcomeId']))
                if not hit: continue
                sp, k = hit; ev = k[0]
                if ev not in start: continue
                try: qty = float(r['qty']); cost = float(r['cost']); t = M.ts_(r['timestamp'])
                except Exception: continue
                st = start[ev]
                if qty <= 0 or t >= st: continue
                q = cost / qty
                if not 0.02 <= q <= 0.98: continue
                seen['maker fills on mapped markets'] += 1
                f = fair(k, t, 1800)
                if f is None: seen['no Pinnacle price at that line then'] += 1; continue
                e = f - q
                if abs(e) > 0.15: seen['15c+ from Pinnacle (dropped)'] += 1; continue
                f30 = fair(k, t + 1800, 1800) if t + 1800 < st else None; fc = fair(k, st, 3600)
                g = grp(k[1]); h = (st - t) / 3600; n += 1
                for key in (('all', g), ('sport', g, sp), ('edge', g, M.eband(e)), ('time', g, M.tband(h)),
                            ('size', g, 'under $100' if cost < 100 else '$100-1k' if cost < 1000 else '$1k+')):
                    a = A[key]; a.v = 'Novig'; a.add(ev, ds, q, qty, e, (f30 - q) if f30 is not None else None, (fc - q) if fc is not None else None, None)
                for kc in (1, 2, 3):
                    b = math.floor((f - kc / 100.0) * 200 + 1e-9) / 200.0
                    if q <= b + 1e-9:
                        for key in (('rest', g, f'{kc}c under'), ('rest sport', g, f'{kc}c under', sp), ('rest time', g, f'{kc}c under', M.tband(h))):
                            a = A[key]; a.v = 'Novig'; a.add(ev, ds, b, qty, f - b, (f30 - b) if f30 is not None else None, (fc - b) if fc is not None else None, None)
        days.append(ds); print(f'{ds}: {n} maker fills priced ({round(time.time() - T0)}s)', flush=True)
    out = dict(days=days, seen=dict(seen), rows={' | '.join(map(str, k)): a.out() for k, a in A.items()})
    os.makedirs(os.path.join(ROOT, 'data', 'research'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'novig_maker_select.json'), 'w'), indent=0)
    print(dict(seen))
    for k in sorted(out['rows']):
        r = out['rows'][k]
        if r['fills'] >= 100: print(f"{k:<62} fills {r['fills']:>7} games {r['games']:>4} risk ${r['risk']:>11,} (${round(r['risk'] / max(1, len(days))):>9,}/day) edge at fill {str(r['edge_at_fill']):>6}c  +30m {str(r['after30']):>6}c  close {str(r['clv']):>6}c (z {r['clv_z']}) on {r['clv_share']}  $/day {r['clv_usd_day']}")


T0 = time.time()
if __name__ == '__main__': main()
