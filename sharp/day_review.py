#!/usr/bin/env python3
"""One-day review of every watch signal (Sean, 11/1): how each family did by sport once results were in, and whether tailing at the
signal or waiting got the better number.

Families (all for games that started on the ET day under review):
  moves      every 2+ pt move on the fast tape (data/state/moves.json + moves.jsonl.gz); "notable" = Pinnacle origin or Kalshi $1k+
             fills net with the move (the page's definition). One per game x market x side (the first).
  bigsmall   Kalshi fills, risk-equivalent dollars (contracts x min(p, 1-p)): first time big ($500+ fills) money is net $1,000+ on a
             side while small ($50 and under) money is net the other way, on the game's main line (most dollars). Soccer moneyline out.
  kmove4     Kalshi main-line mid moved 4+ points from the first tight two-sided price we logged; first time it happens.
  systems    paper fills (data/state/fills.jsonl), graded by settle.py.
Price path: the side's probability at the same line, from Kalshi, then Novig, then Pinnacle (5-minute tape, 20-minute log as a
fallback), at the signal, +15m, +1h, +3h, 1h before start and the last pregame print. A positive change = the price got worse
after the signal (tailing right away was better). Results are flat 1u at the signal mid (no vig, no fee), so read them as direction.
Usage: python3 sharp/day_review.py [YYYY-MM-DD]   (ET day; default yesterday). Writes data/research/day_review_<date>.json."""
import os, sys, json, gzip, glob, collections, datetime as dt, bisect
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import pandas as pd
from sharp import moves as MV

from zoneinfo import ZoneInfo
ET = ZoneInfo('America/New_York')
DAY = sys.argv[1] if len(sys.argv) > 1 else (dt.datetime.now(ET) - dt.timedelta(days=1)).date().isoformat()
D0 = dt.datetime.fromisoformat(DAY).replace(tzinfo=ET); LO, HI = D0.astimezone(dt.timezone.utc), (D0 + dt.timedelta(days=1)).astimezone(dt.timezone.utc)
SPORTS = ('nfl', 'nba', 'nhl', 'cfb', 'cbb', 'soccer')
OTHER = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}
PREF = ('Kalshi', 'Novig', 'Pinnacle')


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def files(sp, sub, days=4):
    out = []
    for i in range(-days, 2):
        f = os.path.join(ROOT, 'data', sp, sub, (D0 + dt.timedelta(days=i)).date().isoformat() + '.jsonl.gz')
        if os.path.exists(f): out.append(f)
    return out


def results():
    R = {}
    for l in open(os.path.join(ROOT, 'data', 'state', 'results.jsonl')):
        r = json.loads(l)
        if r.get('status') == 'final' and r.get('home_score') is not None: R[r['event_id']] = r
    return R


def grade(r, market, home_line, side):
    """1 win, 0.5 push, 0 loss (Asian quarter lines average the two halves); None if ungradable."""
    if r is None: return None
    h, a = r['home_score'], r['away_score']
    if market.startswith('1h_'):
        if r.get('f5_home') is None: return None
        h, a = r['f5_home'], r['f5_away']; market = market[3:]
    def one(l):
        if market == 'ml': x = h - a
        elif market == 'spread': x = h + l - a
        elif market == 'total': x = (h + a) - l
        else: return None
        res = 1.0 if x > 0 else (0.5 if x == 0 else 0.0)
        return res if side in ('home', 'over') else 1 - res
    l = home_line or 0.0
    if market != 'ml' and abs((l * 4) % 2) == 1:            # quarter line
        a_, b_ = one(l - 0.25), one(l + 0.25)
        return None if a_ is None else (a_ + b_) / 2
    return one(l)


def pnl(res, p):
    """Flat 1u at probability p: win, loss, push, and Asian quarter-line half results."""
    if res is None or p is None or not 0 < p < 1: return None
    win = (1 - p) / p
    return {1.0: win, 0.75: win / 2, 0.5: 0.0, 0.25: -0.5, 0.0: -1.0}.get(res)


class Paths:
    """(event, market, home_line, venue) -> sorted [(t, p_home_or_over)] from the 5-minute tape plus the 20-minute log."""
    def __init__(self, sp):
        rows = MV.read_jl(files(sp, 'ticks5') + files(sp, 'ticks'), keep=lambda r: r.get('venue') in PREF and r.get('market') in MV.MARKETS)
        df = MV.frame(rows, list(PREF))
        self.s = collections.defaultdict(list)
        if df.empty: return
        for ev, v, m, hl, t, p in df[['event_id', 'venue', 'market', 'home_line', 'ts', 'p']].itertuples(index=False):
            self.s[(ev, m, float(hl), v)].append((t.to_pydatetime(), float(p)))
        for k in self.s: self.s[k].sort()

    def at(self, ev, m, hl, side, t, max_age_min=30):
        for v in PREF:
            L = self.s.get((ev, m, float(hl or 0.0), v))
            if not L: continue
            i = bisect.bisect_right([x[0] for x in L], t) - 1
            if i >= 0 and (t - L[i][0]).total_seconds() <= max_age_min * 60:
                p = L[i][1]; return (p if side in ('home', 'over') else 1 - p), v
        return None, None


def path(P, ev, m, hl, side, t0, start):
    pts = {'signal': t0 + dt.timedelta(minutes=5), '+15m': t0 + dt.timedelta(minutes=15), '+1h': t0 + dt.timedelta(hours=1), '+3h': t0 + dt.timedelta(hours=3),
           'T-1h': start - dt.timedelta(hours=1), 'close': start - dt.timedelta(minutes=1)}
    out = {}
    for k, t in pts.items():
        if t >= start or (k not in ('signal', 'close') and t <= t0): continue
        p, v = P.at(ev, m, hl, side, t, max_age_min=60 if k == 'close' else 30)
        if p is not None: out[k] = round(p, 4)
    return out


def sched():
    S = {}
    for sp in SPORTS:
        p = os.path.join(ROOT, 'data', sp, 'schedule.json')
        if os.path.exists(p):
            for k, v in json.load(open(p)).items():
                st = ts(v['start'])
                if LO <= st < HI: S[k] = dict(v, sport=sp, st=st)
    return S


def sig_moves(S):
    allm = {}
    for f in (os.path.join(ROOT, 'data', 'state', 'moves.json'),):
        d = json.load(open(f))
        for sp, v in d['sports'].items():
            for val in v.values():
                if isinstance(val, list):
                    for x in val:
                        if isinstance(x, dict) and 'p0' in x and x.get('event_id') in S: allm[x['id']] = x
    with gzip.open(os.path.join(ROOT, 'data', 'state', 'moves.jsonl.gz'), 'rt') as fh:
        for l in fh:
            x = json.loads(l)
            if x.get('event_id') in S: allm[x['id']] = x
    first = {}
    for x in sorted(allm.values(), key=lambda x: x['ts']):
        if x['sport'] == 'soccer' and x['market'] == 'ml': continue
        k = (x['event_id'], x['market'], x['side'])
        if k in first: continue
        k_ = x.get('kalshi') or {}
        notable = x['origin'] == 'Pinnacle' or bool(k_.get('big_n') and (k_.get('big_net') or 0) > 0)
        first[k] = dict(family='moves_notable' if notable else 'moves_other', event_id=x['event_id'], market=x['market'], home_line=x['line'] if x['market'] != 'ml' else 0.0,
                        side=x['side'], t0=ts(x['ts']), origin=x['origin'], size_pts=x.get('size_pts'))
    return list(first.values())


def sig_bigsmall(S):
    fl = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'kalshi', 'trades5', '*.jsonl.gz'))):
        try:
            with gzip.open(f, 'rt') as fh:
                for l in fh:
                    try: t = json.loads(l)
                    except Exception: continue
                    e = S.get(t.get('event_id'))
                    if not e or t.get('market') not in ('ml', 'spread', 'total') or not t.get('yes_side'): continue
                    if e['sport'] == 'soccer' and t['market'] == 'ml': continue
                    tt = ts(t['ts'])
                    if tt >= e['st']: continue
                    yes = t['taker_side'] == 'yes'; side = t['yes_side'] if yes else OTHER.get(t['yes_side'])
                    if not side: continue
                    usd = t['count'] * min(t['yes_price'], 1 - t['yes_price'])
                    hl = 0.0 if t['market'] == 'ml' else (t['line'] if t['market'] == 'total' or t['yes_side'] == 'home' else -t['line'])
                    fl[(t['event_id'], t['market'], hl)].append((tt, side, usd))
        except (EOFError, OSError): pass
    tot = collections.defaultdict(float); main = {}
    for (ev, m, hl), L in fl.items():
        s = sum(u for _, _, u in L)
        if s > tot[(ev, m)]: tot[(ev, m)] = s; main[(ev, m)] = hl
    out = []
    for (ev, m), hl in main.items():
        L = sorted(fl[(ev, m, hl)]); pos = 'over' if m == 'total' else 'home'
        big = small = 0.0
        for tt, side, u in L:
            sg = 1 if side == pos else -1
            if u >= 500: big += sg * u
            if u <= 50: small += sg * u
            if abs(big) >= 1000 and small != 0 and (big > 0) != (small > 0):
                out.append(dict(family='bigsmall', event_id=ev, market=m, home_line=hl, side=pos if big > 0 else OTHER[pos], t0=tt, big_net=round(abs(big)), small_net=round(abs(small))))
                break
    return out


def sig_kmove(S, P):
    out = []
    by = collections.defaultdict(list)
    for (ev, m, hl, v), L in P.s.items():
        if v == 'Kalshi' and ev in S and not (S[ev]['sport'] == 'soccer' and m == 'ml'): by[(ev, m)].append((hl, L))
    for (ev, m), Ls in by.items():
        Ls = [(hl, [x for x in L if x[0] < S[ev]['st']]) for hl, L in Ls]
        Ls = [(hl, L) for hl, L in Ls if len(L) >= 10]
        if not Ls: continue
        hl, L = min(Ls, key=lambda z: abs(z[1][0][1] - 0.5))          # main line: the strike nearest even money at first sight
        p0 = L[0][1]
        for t, p in L:
            if abs(p - p0) >= 0.04:
                out.append(dict(family='kmove4', event_id=ev, market=m, home_line=hl, side=('home' if m != 'total' else 'over') if p > p0 else ('away' if m != 'total' else 'under'),
                                t0=t, first=round(p0, 3), at=round(p, 3)))
                break
    return out


def sig_systems(S):
    out = []
    for l in open(os.path.join(ROOT, 'data', 'state', 'fills.jsonl')):
        r = json.loads(l)
        if r['event_id'] not in S or not str(r.get('rule_tag', '')).startswith('paper:') or r.get('result') == 'void': continue
        hl = r['line'] if r['market'].endswith('total') or r['side'] == 'home' else (-r['line'] if r['line'] is not None else 0.0)
        out.append(dict(family='systems', event_id=r['event_id'], market=r['market'], home_line=hl if r['market'] != 'ml' else 0.0, side=r['side'], t0=ts(r['ts_utc']),
                        tag=r['rule_tag'][6:], fill_price=r['price_american'], fill_implied=r['implied'], result=r.get('result'), pnl_units=r.get('pnl_units'), stake=r.get('stake')))
    return out


def main():
    S = sched(); R = results()
    print(f"[day_review] {DAY} ET: {len(S)} games scheduled, {sum(1 for k in S if k in R)} final in results.jsonl", flush=True)
    paths = {sp: Paths(sp) for sp in SPORTS}
    sigs = sig_moves(S) + sig_bigsmall(S) + sig_systems(S)
    for sp in SPORTS: sigs += sig_kmove({k: v for k, v in S.items() if v['sport'] == sp}, paths[sp])
    rows = []
    for s in sigs:
        e = S[s['event_id']]; P = paths[e['sport']]; mk = s['market']
        pa = path(P, s['event_id'], mk, s['home_line'], s['side'], s['t0'], e['st']) if not mk.startswith('1h_') else {}
        res = grade(R.get(s['event_id']), mk, s['home_line'], s['side'])
        p_sig = pa.get('signal')
        rows.append(dict(s, sport=e['sport'], game=f"{e['away']}@{e['home']}", start=e['st'].isoformat(), lead_h=round((e['st'] - s['t0']).total_seconds() / 3600, 1),
                         t0=s['t0'].isoformat(), path=pa, res=res, pnl_sig=pnl(res, p_sig) if mk != '' else None))
    json.dump(rows, open(os.path.join(ROOT, 'data', 'research', f'day_review_{DAY}.json'), 'w'), indent=0, default=str)
    report(rows)


def report(rows):
    fams = ['moves_notable', 'moves_other', 'bigsmall', 'kmove4', 'systems']
    print("\nResults (flat 1u at the signal mid; systems at the fill price, stake as flagged)")
    print(f"{'family':14} {'sport':7} {'n':>3} {'graded':>6} {'W-L-P':>9} {'units':>7} {'CLV pts':>8}")
    for f in fams:
        for sp in list(SPORTS) + ['all']:
            L = [r for r in rows if r['family'] == f and (sp == 'all' or r['sport'] == sp)]
            if not L: continue
            G = [r for r in L if r['res'] is not None]
            w = sum(1 for r in G if r['res'] == 1); lo = sum(1 for r in G if r['res'] == 0); pu = len(G) - w - lo
            if f == 'systems': u = sum((r['pnl_units'] or 0) for r in G if r.get('result') not in (None, 'void'))
            else: u = sum(r['pnl_sig'] for r in G if r['pnl_sig'] is not None)
            cl = [100 * (r['path']['close'] - r['path']['signal']) for r in L if 'close' in r['path'] and 'signal' in r['path']]
            print(f"{f:14} {sp:7} {len(L):>3} {len(G):>6} {f'{w}-{lo}-{pu}':>9} {u:>+7.2f} {(sum(cl) / len(cl) if cl else float('nan')):>+8.2f}")
    print("\nTiming: side probability change after the signal, in points (positive = price got worse, tailing at once was better)")
    print(f"{'family':14} {'sport':7} " + ' '.join(f"{k:>11}" for k in ('+15m', '+1h', '+3h', 'T-1h', 'close')))
    for f in fams:
        for sp in list(SPORTS) + ['all']:
            L = [r for r in rows if r['family'] == f and (sp == 'all' or r['sport'] == sp) and 'signal' in r['path']]
            if not L: continue
            cells = []
            for k in ('+15m', '+1h', '+3h', 'T-1h', 'close'):
                d = [100 * (r['path'][k] - r['path']['signal']) for r in L if k in r['path']]
                worse = sum(1 for x in d if x > 0.5); better = sum(1 for x in d if x < -0.5)
                cells.append(f"{(sum(d) / len(d)):+.1f} {worse}/{better}" if d else '—')
            print(f"{f:14} {sp:7} " + ' '.join(f"{c:>11}" for c in cells))
    print("  (cells: mean change, then count worse/better by more than half a point)")
    print("\nBy lead time (all families but systems): signal more than 6h before start vs inside 6h")
    for f in fams[:-1]:
        for lab, sel in (('>6h', lambda r: r['lead_h'] > 6), ('<=6h', lambda r: r['lead_h'] <= 6)):
            L = [r for r in rows if r['family'] == f and sel(r) and r['res'] is not None and r['pnl_sig'] is not None]
            cl = [100 * (r['path']['close'] - r['path']['signal']) for r in L if 'close' in r['path'] and 'signal' in r['path']]
            if L: print(f"  {f:14} {lab:5} n {len(L):>3}  units {sum(r['pnl_sig'] for r in L):+6.2f}  CLV {(sum(cl) / len(cl) if cl else float('nan')):+.2f}")


if __name__ == '__main__':
    main()
