#!/usr/bin/env python3
"""Market making on Kalshi and Novig, from our own tapes (Sean 11/10: "serve as a market maker at good prices ... pick up daily profits").
Every taker trade has a maker on the other side. For each pregame Kalshi and Novig trade (moneyline, spread, total) the maker's side and
price are scored against Pinnacle's no-vig price: at the time of the fill (was it a good price?), 30 minutes later, and at the close (did it
hold?), plus the settled result. Then the bettable version: a resting bid k cents under Pinnacle's fair price on every side, filled by every
taker trade at or through it, paid at our own bid.
Pinnacle fair = both sides at the same line, devigged multiplicatively, last quote within 30 minutes (close: last quote in the hour before
the start). Trades at lines Pinnacle does not quote are not scored. Soccer and tennis moneylines are left out (three-way / no start times).
Usage: python3 sharp/maker_test.py [first_day] [last_day]   -> data/research/maker_test.json"""
import os, sys, json, gzip, glob, bisect, math, datetime as dt, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SPORTS = ['nba', 'nfl', 'nhl', 'cfb', 'cbb', 'mma', 'soccer']
MKTS = ('ml', 'spread', 'total')
OTH = dict(home='away', away='home', over='under', under='over')
D0 = sys.argv[1] if len(sys.argv) > 1 else '2026-10-30'
D1 = sys.argv[2] if len(sys.argv) > 2 else '2026-11-10'
MAXAGE = 30 * 60


def ts_(s):
    if isinstance(s, (int, float)): return s / 1000.0
    s = s.replace('Z', '+00:00')
    if '.' in s:
        a, b = s.split('.'); frac, tz = b[:b.index('+')], b[b.index('+'):]; s = a + '.' + (frac + '000000')[:6] + tz
    return dt.datetime.fromisoformat(s).timestamp()


def imp(am): return 100.0 / (am + 100.0) if am > 0 else -am / (-am + 100.0)


def load():
    start = {}; res = {}
    for sp in SPORTS:
        p = os.path.join(ROOT, 'data', sp, 'schedule.json')
        if not os.path.exists(p): continue
        d = json.load(open(p)); ev = d if isinstance(d, list) else (d.get('events') if isinstance(d.get('events'), list) else list(d.values()))
        for e in ev:
            if isinstance(e, dict) and e.get('event_id') and e.get('start'):
                try: start[str(e['event_id'])] = ts_(e['start'] if len(e['start']) > 17 else e['start'].replace('Z', ':00Z'))
                except Exception: pass
    p = os.path.join(ROOT, 'data', 'state', 'results.jsonl')
    if os.path.exists(p):
        for l in open(p):
            try: x = json.loads(l)
            except Exception: continue
            if x.get('status') == 'final' and x.get('home_score') is not None: res[str(x['event_id'])] = (float(x['home_score']), float(x['away_score']))
    pin = collections.defaultdict(lambda: ([], []))
    for sp in SPORTS:
        for sub in ('ticks', 'ticks5'):
            for f in sorted(glob.glob(os.path.join(ROOT, 'data', sp, sub, '2026-*.jsonl.gz'))):
                day = os.path.basename(f)[:10]
                if not (D0 <= day <= D1): continue
                try:
                    for l in gzip.open(f, 'rt'):
                        if '"venue":"Pinnacle"' not in l: continue
                        x = json.loads(l)
                        if x.get('market') not in MKTS or x.get('american') is None: continue
                        if sp == 'soccer' and x['market'] == 'ml': continue
                        k = (str(x['event_id']), x['market'], x['side'], x.get('line'))
                        pin[k][0].append(ts_(x['ts'])); pin[k][1].append(imp(x['american']))
                except Exception as e: print('skip', f, e, file=sys.stderr)
    for k, (T, P) in pin.items():
        o = sorted(range(len(T)), key=T.__getitem__); pin[k] = ([T[i] for i in o], [P[i] for i in o])
    return start, res, pin


def last(pin, k, t, age):
    v = pin.get(k)
    if not v: return None
    i = bisect.bisect_right(v[0], t) - 1
    if i < 0 or t - v[0][i] > age: return None
    return v[1][i]


def fair(pin, ev, m, side, line, t, age=MAXAGE):
    ol = line if (line is None or m == 'total') else -line
    a = last(pin, (ev, m, side, line), t, age); b = last(pin, (ev, m, OTH[side], ol), t, age)
    return a / (a + b) if a and b else None


def won(res, ev, m, side, line):
    r = res.get(ev)
    if not r: return None
    h, a = r
    if m == 'ml': d = (h - a) if side == 'home' else (a - h)
    elif m == 'spread': d = ((h - a) if side == 'home' else (a - h)) + line
    else: d = ((h + a) - line) if side == 'over' else (line - (h + a))
    return 1.0 if d > 0 else (0.0 if d < 0 else None)


def trades(start):
    """Yields (venue, sport, ev, market, maker_side, maker_line, maker_price, contracts, t)."""
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'kalshi', 'trades5', '2026-*.jsonl.gz'))):
        if not (D0 <= os.path.basename(f)[:10] <= D1): continue
        for l in gzip.open(f, 'rt'):
            try: x = json.loads(l)
            except Exception: continue
            m = x.get('market'); sp = x.get('sport'); ev = str(x.get('event_id'))
            if m not in MKTS or sp not in SPORTS or ev not in start or (sp == 'soccer' and m == 'ml'): continue
            ys = x.get('yes_side'); ln = x.get('line')
            if ys not in OTH: continue
            t = ts_(x['ts'])
            if t >= start[ev]: continue
            yp = float(x['yes_price']); c = float(x.get('count') or 0)
            if not (0.02 <= yp <= 0.98) or c <= 0: continue
            if x['taker_side'] == 'no': side, line, q = ys, ln, yp               # taker sold yes: the maker bought yes
            else: side, line, q = OTH[ys], (ln if (ln is None or m == 'total') else -ln), 1 - yp
            yield 'Kalshi', sp, ev, m, side, line, q, c, t
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'novig', 'trades5', '2026-*.jsonl.gz'))):
        if not (D0 <= os.path.basename(f)[:10] <= D1): continue
        for l in gzip.open(f, 'rt'):
            try: x = json.loads(l)
            except Exception: continue
            m = x.get('market'); sp = x.get('sport'); ev = str(x.get('event_id'))
            if m not in MKTS or sp not in SPORTS or ev not in start or (sp == 'soccer' and m == 'ml'): continue
            ts = x.get('side_if_taker'); ln = x.get('line')
            if ts not in OTH: continue
            t = ts_(x['ts'])
            if t >= start[ev]: continue
            p = float(x['price']); c = float(x.get('qty_cents') or 0) / 100.0
            if not (0.02 <= p <= 0.98) or c <= 0: continue
            yield 'Novig', sp, ev, m, OTH[ts], (ln if (ln is None or m == 'total') else -ln), 1 - p, c, t


class Acc:
    __slots__ = ('n', 'c', 'risk', 'e', 'm30', 'cm30', 'clv', 'cclv', 'pnl', 'rpnl', 'ev', 'days')
    def __init__(s):
        s.n = 0; s.c = s.risk = s.e = s.m30 = s.cm30 = s.clv = s.cclv = s.pnl = s.rpnl = 0.0; s.ev = collections.defaultdict(lambda: [0.0, 0.0]); s.days = set()
    def add(s, ev, day, q, c, e, m30, clv, w):
        s.n += 1; s.c += c; s.risk += q * c; s.e += e * c; s.days.add(day)
        if m30 is not None: s.m30 += m30 * c; s.cm30 += c
        if clv is not None: s.clv += clv * c; s.cclv += c; x = s.ev[ev]; x[0] += clv * c; x[1] += c
        if w is not None: s.pnl += (w - q) * c; s.rpnl += q * c
    def out(s):
        ms = [a / b for a, b in s.ev.values() if b > 0]; z = None
        if len(ms) > 5:
            mu = sum(ms) / len(ms); sd = (sum((x - mu) ** 2 for x in ms) / (len(ms) - 1)) ** 0.5
            z = round(mu / (sd / len(ms) ** 0.5), 2) if sd > 0 else None
        nd = max(1, len(s.days))
        return dict(fills=s.n, contracts=round(s.c), risk=round(s.risk), games=len(ms), days=nd,
                    edge_at_fill=round(100 * s.e / s.c, 2) if s.c else None,
                    after30=round(100 * s.m30 / s.cm30, 2) if s.cm30 else None,
                    clv=round(100 * s.clv / s.cclv, 2) if s.cclv else None, clv_z=z,
                    clv_usd_day=round(s.clv / nd) if s.cclv else None, clv_share=round(s.cclv / s.c, 2) if s.c else None,
                    roi=round(100 * s.pnl / s.rpnl, 1) if s.rpnl else None, pnl=round(s.pnl), graded_risk=round(s.rpnl))


def eband(e):
    c = e * 100
    return ('paid 2c+ over fair' if c < -2 else 'paid 1-2c over fair' if c < -1 else 'paid 0-1c over fair' if c < 0 else
            'paid 0-1c under fair' if c < 1 else 'paid 1-2c under fair' if c < 2 else 'paid 2-4c under fair' if c < 4 else 'paid 4c+ under fair')


def tband(h): return '24h+' if h >= 24 else '6-24h' if h >= 6 else '1-6h' if h >= 1 else 'last hour'


def main():
    start, res, pin = load()
    print(f'{len(start)} games with a start, {len(res)} results, {len(pin)} Pinnacle series', file=sys.stderr)
    A = collections.defaultdict(Acc); seen = collections.Counter()
    for v, sp, ev, m, side, line, q, c, t in trades(start):
        seen[v] += 1
        f = fair(pin, ev, m, side, line, t)
        if f is None: seen[v + ' no Pinnacle price at that line'] += 1; continue
        st = start[ev]; day = dt.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')
        e = f - q
        if abs(e) > 0.15: seen[v + ' 15c+ from Pinnacle (dropped)'] += 1; continue
        f30 = fair(pin, ev, m, side, line, t + 1800) if t + 1800 < st else None
        fc = fair(pin, ev, m, side, line, st, 3600)
        w = won(res, ev, m, side, line)
        m30 = (f30 - q) if f30 is not None else None; clv = (fc - q) if fc is not None else None
        for key in (('all', v), ('edge', v, eband(e)), ('sport', v, sp, m), ('time', v, tband((st - t) / 3600)),
                    ('size', v, 'under $100' if q * c < 100 else '$100-1k' if q * c < 1000 else '$1k-10k' if q * c < 1e4 else '$10k+'),
                    ('price', v, 'under 25c' if q < .25 else '25-40c' if q < .4 else '40-60c' if q < .6 else '60-75c' if q < .75 else '75c+')):
            A[key].add(ev, day, q, c, e, m30, clv, w)
        # resting bid k cents under fair, whole-cent prices; filled by any taker trade at or through it, paid at our bid
        for k in (1, 2, 3):
            b = math.floor((f - k / 100.0) * 100 + 1e-9) / 100.0
            if q <= b + 1e-9:
                for key in (('rest', v, k), ('rest_time', v, k, tband((st - t) / 3600)), ('rest_sport', v, k, sp, m)):
                    A[key].add(ev, day, b, c, f - b, (f30 - b) if f30 is not None else None, (fc - b) if fc is not None else None, w)
                if (st - t) / 3600 >= 1 and m != 'ml': pass
    out = dict(days=[D0, D1], seen=dict(seen), rows={'|'.join(map(str, k)): a.out() for k, a in A.items()})
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'maker_test.json'), 'w'), indent=0)
    print(json.dumps(dict(seen), indent=1))
    def show(title, pre):
        print('\n' + title)
        for k in sorted(out['rows']):
            if k.startswith(pre):
                r = out['rows'][k]
                print(f"  {k[len(pre):]:<34} fills {r['fills']:>7}  risk ${r['risk']:>11,}  edge at fill {str(r['edge_at_fill']):>6}c  +30m {str(r['after30']):>6}c  close {str(r['clv']):>6}c (z {r['clv_z']}, {r['games']} games)  $/day at close {str(r['clv_usd_day']):>7}  settled ROI {r['roi']}% on ${r['graded_risk']:,}")
    for v in ('Kalshi', 'Novig'):
        show(f'{v}: every maker fill', f'all|{v}')
        show(f'{v}: by the maker\'s price against Pinnacle fair at the fill', f'edge|{v}|')
        show(f'{v}: by sport and market', f'sport|{v}|')
        show(f'{v}: by time to the start', f'time|{v}|')
        show(f'{v}: by fill size', f'size|{v}|')
        show(f'{v}: by price', f'price|{v}|')
        show(f'{v}: resting bid k cents under Pinnacle fair', f'rest|{v}|')
        show(f'{v}: resting bid, by time to the start', f'rest_time|{v}|')
        show(f'{v}: resting bid, by sport and market', f'rest_sport|{v}|')


if __name__ == '__main__': main()
