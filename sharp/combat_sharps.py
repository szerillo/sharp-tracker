#!/usr/bin/env python3
"""Combat-sports sharps on Polymarket, scored against Pinnacle (Sean 11/9: a longer feed of sharp action for MMA / boxing).
Polymarket: data/polymarket/combat/{catalog.jsonl, trades/} (loggers/poly_combat.py; UFC from April 2024, boxing from December 2023; the
market resolution is the result). Pinnacle: data/oddsapi/compact/<mma|boxing>.jsonl.gz (2022-25, many snapshots) plus the 2026 fight-day
snapshots in data/oddsapi/<mma>/ (22:00 and 02:00 UTC) and compact/<plan>_lines_at (boxing 2026: 6 hours and 10 minutes out). A Polymarket fight is matched to an Odds API fight by both surnames and a start
within 2 days. Fills: taker BUYs before the start (Pinnacle's commence time).
Per wallet and fight: dollar-weighted price paid for the fighter, CLV = Pinnacle no-vig close for him minus that price (points).
Walk-forward: rank wallets on fights before each cutoff (8+ fights, $2k+), follow the top 50 after it; entry = the first fill of a top
wallet on a fight ($100+), at that fill's price plus 1 point (a follower's cost). Graded on CLV vs Pinnacle's close, on how far Pinnacle
moved toward the side after the fill (is the wallet early?), and on results at the entry price.
Usage: python3 sharp/combat_sharps.py [mma|boxing|both]"""
import os, sys, json, gzip, glob, re, math, bisect, collections, unicodedata, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WHICH = sys.argv[1] if len(sys.argv) > 1 else 'both'
P = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00').replace('+00', '+00:00') if s.endswith('+00') else s.replace('Z', '+00:00'))
def norm(s): return re.sub(r'[^a-z ]', ' ', unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()).split()
def sur(s):
    w = [x for x in norm(s) if x not in ('jr', 'sr', 'ii', 'iii', 'de', 'da', 'dos', 'van', 'la')]
    return w[-1] if w else ''

# ---- Pinnacle series per Odds API fight: name -> [(ts, no-vig prob)]
PIN = {}; FIGHTS = collections.defaultdict(list)     # (date) -> [(odds id, home, away, start)]
def add(fid, home, away, start, t, q):
    if not q or not q[0] or not q[1]: return
    a, b = 1 / q[0], 1 / q[1]; ph = a / (a + b)
    if fid not in PIN: PIN[fid] = dict(home=home, away=away, start=start, s=[]); FIGHTS[start[:10]].append(fid)
    PIN[fid]['s'].append((P(t).timestamp(), ph))
plans = {'mma': ['mma'], 'boxing': ['boxing'], 'both': ['mma', 'boxing']}[WHICH]
for plan in plans:
    for p in (os.path.join(ROOT, 'data/oddsapi/compact', f'{plan}.jsonl.gz'), os.path.join(ROOT, 'data/oddsapi/compact', f'{plan}_lines_at.jsonl.gz')):
        if not os.path.exists(p): continue
        for l in gzip.open(p, 'rt'):
            try: d = json.loads(l)
            except Exception: continue
            if d['t'] < d['start']: add(d['id'], d['home'], d['away'], d['start'], d['t'], ((d['books'].get('pinnacle') or {}).get('h2h')))
    for f in sorted(glob.glob(os.path.join(ROOT, 'data/oddsapi', plan, '2026-*.json.gz'))):
        try: x = json.load(gzip.open(f))
        except Exception: continue
        X = x.get('data', x) if isinstance(x, dict) else x
        t = os.path.basename(f)[:15]; t = f'{t[:13]}:{t[13:15]}:00Z'
        for e in X:
            if t >= e['commence_time']: continue
            for b in e.get('bookmakers') or []:
                if b['key'] != 'pinnacle': continue
                for m in b['markets']:
                    if m['key'] != 'h2h': continue
                    o = {z['name']: z['price'] for z in m['outcomes']}
                    add(e['id'], e['home_team'], e['away_team'], e['commence_time'], t, (o.get(e['home_team']), o.get(e['away_team'])))
for v in PIN.values(): v['s'].sort()
print(f'[combat] Pinnacle-priced fights: {len(PIN)}', flush=True)

def match(outs, start):
    s0, s1 = sur(outs[0]), sur(outs[1]); d = P(start).date()
    for k in (0, -1, 1, -2, 2):
        for fid in FIGHTS.get((d + dt.timedelta(days=k)).isoformat(), []):
            f = PIN[fid]; h, a = sur(f['home']), sur(f['away'])
            if {s0, s1} == {h, a}: return fid, {outs[0]: 'home' if s0 == h else 'away', outs[1]: 'home' if s1 == h else 'away'}
    return None, None
def pin_for(fid, side, t=None):
    S = PIN[fid]['s']
    if t is None: p = S[-1][1]
    else:
        i = bisect.bisect_right(S, (t, 9)) - 1
        if i < 0: return None
        p = S[i][1]
    return p if side == 'home' else 1 - p

# ---- Polymarket fills per wallet and fight
C = [json.loads(l) for l in open(os.path.join(ROOT, 'data/polymarket/combat/catalog.jsonl'))]
C = [c for c in C if (c['tag'] in ('ufc', 'mma')) == (WHICH != 'boxing') or WHICH == 'both']
rows = []; nm = 0
for c in C:
    tp = os.path.join(ROOT, 'data/polymarket/combat/trades', c['cond'] + '.jsonl.gz')
    if not os.path.exists(tp): continue
    fid, side_of = match(c['outcomes'], c['start'])
    if not fid: continue
    nm += 1; st = P(PIN[fid]['start']).timestamp(); close = {o: pin_for(fid, side_of[o]) for o in c['outcomes']}
    agg = collections.defaultdict(lambda: [0.0, 0.0, None, 0.0])     # (wallet, outcome) -> usd, price*usd, first ts, first fill usd
    for l in gzip.open(tp, 'rt'):
        t = json.loads(l)
        if t.get('truncated') or t.get('side') != 'BUY' or not t.get('wallet') or t['ts'] >= st: continue
        u = t['price'] * t['size']
        if u < 5 or not 0.02 < t['price'] < 0.98: continue
        a = agg[(t['wallet'], t['outcome'])]; a[0] += u; a[1] += t['price'] * u
        if a[2] is None or t['ts'] < a[2]: a[2] = t['ts']; a[3] = u
    for (w, o), (u, pu, t0, u0) in agg.items():
        if o not in side_of: continue
        px = pu / u; won = c['winner'] == o
        rows.append(dict(w=w, fight=c['cond'], tag=c['tag'], o=o, usd=u, px=px, t0=t0, u0=u0, start=st, clv=100 * (close[o] - px),
                         pin_at=pin_for(fid, side_of[o], t0), pin_close=close[o], won=won, date=PIN[fid]['start'][:10]))
print(f'[combat] Polymarket fights matched to Pinnacle: {nm} of {len(C)}; wallet-fight rows {len(rows)}', flush=True)

def follow(cut, until, top=50, minf=8, minusd=2000):
    past = collections.defaultdict(list)
    for r in rows:
        if r['date'] < cut: past[r['w']].append(r)
    sc = []
    for w, L in past.items():
        fights = {r['fight'] for r in L}
        if len(fights) < minf or sum(r['usd'] for r in L) < minusd: continue
        m = sum(r['clv'] for r in L) / len(L); sd = (sum((r['clv'] - m) ** 2 for r in L) / max(1, len(L) - 1)) ** .5
        sc.append((m / (sd / len(L) ** .5) if sd else 0, m, w, len(fights)))
    sc.sort(reverse=True); T = {w for _, _, w, _ in sc[:top]}; B = {w for _, _, w, _ in sc[-top:]}
    out = {}
    for lab, S in (('top', T), ('bottom', B)):
        first = {}
        for r in rows:
            if r['w'] in S and cut <= r['date'] < until and r['u0'] >= 100:
                k = (r['fight'], r['o'])
                if k not in first or r['t0'] < first[k]['t0']: first[k] = r
        bets = list(first.values()); out[lab] = bets
    return sc, out
def report(lab, L):
    n = len(L)
    if not n: print(f'  {lab:44} n=0'); return
    clv = [r['pin_close'] - (r['px'] + .01) for r in L]
    mv = [r['pin_close'] - r['pin_at'] for r in L if r['pin_at'] is not None]
    pn = [((1 / (r['px'] + .01) - 1) if r['won'] else -1) for r in L]
    w = sum(r['won'] for r in L)
    print(f"  {lab:44} n={n:4} {w}-{n - w:<4} ROI {100 * sum(pn) / n:+6.1f}%  CLV vs Pinnacle close {100 * sum(clv) / n:+5.2f} pts  "
          f"Pinnacle moved toward the side after the fill {100 * sum(mv) / len(mv) if mv else 0:+5.2f} pts (n {len(mv)})")
for lab_s, f in (('UFC / MMA', lambda r: r['tag'] in ('ufc', 'mma')), ('boxing', lambda r: r['tag'] == 'boxing')):
    R = [r for r in rows if f(r)]
    if not R: continue
    print(f'==== {lab_s}: {len({r["fight"] for r in R})} fights, {len({r["w"] for r in R})} wallets')
    report('every wallet, first fill per fight and side', [r for r in R if r['u0'] >= 100])
    big = [r for r in R if r['u0'] >= 1000]; report('first fills of $1k+', big)
    for cut, until in (('2025-01-01', '2025-07-01'), ('2025-07-01', '2026-01-01'), ('2026-01-01', '2026-06-01'), ('2026-06-01', '2026-12-31')):
        sc, out = follow(cut, until)
        if not sc: continue
        print(f'  -- ranked on fights before {cut} ({len(sc)} wallets qualified), followed {cut} to {until}')
        report('top 50 by CLV t-stat', [r for r in out['top'] if f(r)]); report('bottom 50', [r for r in out['bottom'] if f(r)])
