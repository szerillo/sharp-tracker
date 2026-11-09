#!/usr/bin/env python3
"""Is boxing beatable? (Sean 11/9.) Odds: data/oddsapi/compact/boxing.jsonl.gz (2023-26, moneylines, every snapshot). Results:
data/boxing/results.json (loggers/boxing_results.py, from Wikipedia records). Draws push and no contests void (two-way moneyline).
Flat 1 unit at the price. BetMGM is never bet; Pinnacle is the reference, never the bet unless a test says so.
Tests:
 1. Calibration: Pinnacle's no-vig close against the result, by price band (favourite-longshot bias).
 2. Price shopping: the best US book (DK, FD, Caesars, BetRivers) at the last snapshot before the start, when it is X% over Pinnacle's
    no-vig close.
 3. Sharp proxy, Pinnacle's move: Pinnacle's no-vig moved X points toward a fighter from its first quote to its close; bet that fighter
    at the best US book at the close (follow), or the other side (fade). And the same where a US book still has the pre-move price
    (a lagging book).
 4. Heavy favourites and big underdogs at the US books.
Usage: python3 sharp/boxing_test.py [odds file] [results file]"""
import os, sys, json, gzip, math, collections, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ODDS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data/oddsapi/compact/boxing.jsonl.gz')
RES = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'data/boxing/results.json')
US = {'draftkings': 'DK', 'fanduel': 'FD', 'williamhill_us': 'Caesars', 'betrivers': 'BetRivers'}
P = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
R = json.load(open(RES))
F = collections.defaultdict(list); meta = {}
for l in gzip.open(ODDS, 'rt'):
    try: d = json.loads(l)
    except Exception: continue
    if P(d['t']) >= P(d['start']): continue
    F[d['id']].append(d); meta[d['id']] = (d['home'], d['away'], d['start'])
def nv(q): a, b = 1 / q[0], 1 / q[1]; return a / (a + b)
rows = []
for k, S in F.items():
    r = (R.get(k) or {}).get('winner')
    if r not in ('home', 'away', 'draw'): continue
    S.sort(key=lambda d: d['t'])
    pin = [(d['t'], d['books']['pinnacle']['h2h']) for d in S if (d['books'].get('pinnacle') or {}).get('h2h')]
    last = S[-1]['books']
    us = {bk: (last.get(bk) or {}).get('h2h') for bk in US if (last.get(bk) or {}).get('h2h')}
    if not us: continue
    rows.append(dict(id=k, res=r, year=meta[k][2][:4], pin_open=nv(pin[0][1]) if pin else None, pin_close=nv(pin[-1][1]) if pin else None,
                     pin_close_q=pin[-1][1] if pin else None, us=us, us_open={bk: (S[0]['books'].get(bk) or {}).get('h2h') for bk in US}))
print(f'fights graded: {len(rows)} (with a Pinnacle quote: {sum(1 for r in rows if r["pin_close"] is not None)}); results file covers {len(R)}')
def best(r, side):
    i = 0 if side == 'home' else 1
    c = [(q[i], bk) for bk, q in r['us'].items() if q and q[i] and q[i] > 1]
    return max(c) if c else (None, None)
def pnl(r, side, price):
    if r['res'] == 'draw': return None
    return (price - 1) if r['res'] == side else -1.0
def report(label, bets, mn=30):
    B = [(r, s, p) for r, s, p in bets if pnl(r, s, p) is not None]
    n = len(B)
    if n < mn: print(f'  {label:62} n={n}'); return
    w = sum(1 for r, s, p in B if r['res'] == s); u = sum(pnl(r, s, p) for r, s, p in B); be = sum(1 / p for r, s, p in B) / n
    z = (w / n - be) / math.sqrt(be * (1 - be) / n)
    yr = collections.defaultdict(float)
    for r, s, p in B: yr[r['year']] += pnl(r, s, p)
    print(f"  {label:62} n={n:4} {w}-{n - w:<4} ROI {100 * u / n:+6.1f}%  z {z:+5.2f}  years+ {sum(1 for v in yr.values() if v > 0)}/{len(yr)}  avg price {sum(p for _, _, p in B) / n:.2f}")
print('1. Pinnacle no-vig close vs results (calibration): actual win rate minus Pinnacle\'s, by band')
for lo, hi in ((0, .15), (.15, .3), (.3, .45), (.45, .55), (.55, .7), (.7, .85), (.85, 1.01)):
    L = []
    for r in rows:
        if r['pin_close'] is None or r['res'] == 'draw': continue
        for side, p in (('home', r['pin_close']), ('away', 1 - r['pin_close'])):
            if lo <= p < hi: L.append((p, r['res'] == side))
    if L: print(f'  Pinnacle {lo:.2f}-{hi:.2f}: n={len(L):4}  Pinnacle says {100 * sum(p for p, _ in L) / len(L):5.1f}%  actual {100 * sum(w for _, w in L) / len(L):5.1f}%')
print('2. Best US book against Pinnacle\'s no-vig close (last snapshot)')
for th in (0, .02, .04, .07, .10):
    bets = []
    for r in rows:
        if r['pin_close'] is None: continue
        for side, f in (('home', r['pin_close']), ('away', 1 - r['pin_close'])):
            p, bk = best(r, side)
            if p and p * f - 1 >= th: bets.append((r, side, p))
    report(f'EV {100 * th:.0f}%+ against Pinnacle\'s fair', bets)
print('3. Pinnacle\'s move from first quote to close (sharp proxy), bet at the best US book at the close')
for th in (.02, .04, .07, .10):
    fol, fad, lag = [], [], []
    for r in rows:
        if r['pin_open'] is None: continue
        mv = r['pin_close'] - r['pin_open']
        if abs(mv) < th: continue
        side = 'home' if mv > 0 else 'away'; other = 'away' if side == 'home' else 'home'
        p, _ = best(r, side); q, _ = best(r, other)
        if p: fol.append((r, side, p))
        if q: fad.append((r, other, q))
        i = 0 if side == 'home' else 1
        old = [o[i] for o in r['us_open'].values() if o and o[i]]
        if p and old and p >= max(old) * 0.995: lag.append((r, side, p))     # a US book still at (or above) its opening price
    report(f'follow Pinnacle move {100 * th:.0f}+ pts', fol); report(f'fade Pinnacle move {100 * th:.0f}+ pts', fad)
    report(f'follow, a US book has not moved (lagging)', lag)
print('4. Price bands at the best US book (close)')
for lo, hi, lab in ((1.0, 1.25, 'heavy favourites (-400 or shorter)'), (1.25, 1.67, 'favourites -400 to -150'), (1.67, 2.5, 'near even'), (2.5, 4.0, 'dogs +150 to +300'), (4.0, 99, 'big dogs +300 or longer')):
    bets = []
    for r in rows:
        for side in ('home', 'away'):
            p, _ = best(r, side)
            if p and lo <= p < hi: bets.append((r, side, p))
    report(lab, bets)
