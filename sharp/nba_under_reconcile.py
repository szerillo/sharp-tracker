#!/usr/bin/env python3
"""Reconcile nba_under_good_home_over: Bet Labs export (home|away|home pts|away pts|line|W/L|profit|total move|visitor rest|home rest|home over%) joined to the odds database and our replay (11/6). Usage: python3 sharp/nba_under_reconcile.py"""
import sys, os, json, collections, datetime as dt
sys.path.insert(0, __import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__), '..')))
import sharp.rule_replay as RR
ET = RR.ET
G = RR.load('nba'); RR.profiles(G)
idx = {}
for g in G:
    d = g['start'].astimezone(ET).date()
    idx[(d, g['away'], g['home'])] = g
def days_off(g, side): return (g['start'].astimezone(ET).date() - g[f'{side}_last'].astimezone(ET).date()).days if g.get(f'{side}_last') else None
def ours(g):
    if g['hs'] is None or g.get('close_h') is None or g['close_h'] > 6: return False
    ho, ao = days_off(g, 'home'), days_off(g, 'away')
    return g['home_over_n'] >= 1 and int(100 * (g['home_over_pct'] or 0)) >= 58 and ho is not None and ao is not None and 1 <= ho <= 2 and 1 <= ao <= 3 and g['tot_open'] is not None and g['tot_close'] is not None and g['tot_open'] - g['tot_close'] >= 0.5
def res_at(g, line, dec=1.95):
    t = g['hs'] + g['as_']
    if t == line: return 0.5, 0
    w = t < line; return (1 if w else 0), ((dec - 1) if w else -1)
BL = []
for l in open(__import__('os').path.join(__import__('os').path.dirname(__file__), '..', 'data', 'research', 'betlabs', 'nba_under_1789285.txt')):
    f = l.strip().split('|')
    if len(f) < 12: continue
    m, d, y = f[0].split('/'); D = dt.date(2000 + int(y), int(m), int(d))
    BL.append(dict(date=D, home=f[1], away=f[2], hs=int(f[3]), as_=int(f[4]), line=float(f[5]), res=f[6], profit=float(f[7]), move=float(f[8]), arest=int(f[9]), hrest=int(f[10]), hover=int(f[11])))
def roi(L): 
    n = len([x for x in L if x[0] != .5]); u = sum(x[1] for x in L); w = sum(1 for x in L if x[0] == 1); lo = sum(1 for x in L if x[0] == 0)
    return f"{w}-{lo} ({100*u/max(1,w+lo):+.1f}%)"
matched = []; unmatched = []
for b in BL:
    g = idx.get((b['date'], b['away'], b['home']))
    (matched if g else unmatched).append((b, g))
print('Bet Labs picks', len(BL), 'matched to our DB', len(matched), 'unmatched', len(unmatched))
print('  unmatched by season:', collections.Counter(b['date'].year if b['date'].month >= 8 else b['date'].year - 1 for b, _ in unmatched))
# Bet Labs own grading
blr = [((1 if b['res']=='W' else 0 if b['res']=='L' else .5), b['profit']/100) for b in BL]
print('Bet Labs as exported:', roi(blr))
# same games at Pinnacle close
pin = []; linediff = collections.Counter(); scorediff = 0
for b, g in matched:
    if g['hs'] is None or g['tot_close'] is None: continue
    if (g['hs'], g['as_']) != (b['hs'], b['as_']): scorediff += 1
    linediff[round(g['tot_close'] - b['line'], 1)] += 1
    dec = g.get('under_dec') or 1.95
    pin.append(res_at(g, g['tot_close'], dec))
print('Bet Labs picks graded at Pinnacle close:', roi(pin), '| score mismatches', scorediff)
print('  Pinnacle close minus Bet Labs line:', sorted(linediff.items(), key=lambda x: -x[1])[:8])
# our hits
our = [g for g in G if ours(g)]
blkeys = {(b['date'], b['away'], b['home']) for b in BL}
k = lambda g: (g['start'].astimezone(ET).date(), g['away'], g['home'])
inb = [g for g in our if k(g) in blkeys]; notb = [g for g in our if k(g) not in blkeys]
gr = lambda L: roi([res_at(g, g['tot_close'], g.get('under_dec') or 1.95) for g in L])
print('Our replay hits', len(our), gr(our)); print('  also Bet Labs picks', len(inb), gr(inb)); print('  ours only', len(notb), gr(notb))
oursk = {k(g) for g in our}
blonly = [(b, g) for b, g in matched if k(g) not in oursk]
print('Bet Labs only (matched to DB, not in our replay)', len(blonly), roi([res_at(g, g['tot_close'], g.get('under_dec') or 1.95) for b, g in blonly if g['hs'] is not None and g['tot_close'] is not None]))
# why do Bet Labs-only games miss our filter?
why = collections.Counter()
for b, g in blonly:
    ho, ao = days_off(g, 'home'), days_off(g, 'away'); r = []
    if g.get('close_h') is None or g['close_h'] > 6: r.append('no close within 6h')
    if not (g['home_over_n'] >= 1 and int(100 * (g['home_over_pct'] or 0)) >= 58): r.append(f"our home over% {int(100*(g['home_over_pct'] or 0))} (BL {b['hover']})")
    if not (ho is not None and 1 <= ho <= 2): r.append(f'home days off {ho} (BL rest {b["hrest"]})')
    if not (ao is not None and 1 <= ao <= 3): r.append(f'away days off {ao} (BL rest {b["arest"]})')
    if not (g['tot_open'] is not None and g['tot_close'] is not None and g['tot_open'] - g['tot_close'] >= 0.5): r.append('our drop')
    why[' + '.join(sorted(x.split(' ')[0]+' '+x.split(' ')[1] for x in r))] += 1
print('  why missed:', why.most_common())
why2 = collections.Counter()
for g in notb:
    d = k(g); near = [b for b in BL if b['date'] == d[0] and b['home'] == g['home']]
    why2['BL has the game' if near else 'BL does not list it'] += 1
print('  ours-only:', why2)
# by season comparisons
S = collections.defaultdict(lambda: [[], []])
for b in BL: S[b['date'].year if b['date'].month >= 8 else b['date'].year - 1][0].append(((1 if b['res']=='W' else 0 if b['res']=='L' else .5), b['profit']/100))
for g in our: d = k(g)[0]; S[d.year if d.month >= 8 else d.year - 1][1].append(res_at(g, g['tot_close'], g.get('under_dec') or 1.95))
for s in sorted(S): print(' ', s, 'Bet Labs', roi(S[s][0]), '| ours', roi(S[s][1]))
json.dump(dict(our=[k(g)[0].isoformat()+'|'+g['away']+'|'+g['home'] for g in our]), open('/dev/null','w'))
c3 = collections.Counter(int(100*(g['home_over_pct'] or 0)) - b['hover'] for b, g in matched); print('our home over% minus BL:', sorted(c3.items(), key=lambda x: -x[1])[:12])
c4 = collections.Counter((b['move'], None if g['tot_open'] is None or g['tot_close'] is None else round(g['tot_close']-g['tot_open'],1)) for b, g in matched)
print('BL move vs our close-open (top):', c4.most_common(12))
print('--- ours-only: our drop, Pinnacle-open drop, home over%')
cc = collections.Counter()
for g in notb:
    pdrop = None if g['pin_tot_open'] is None else round(g['pin_tot_open'] - g['tot_close'], 1)
    cc[(round(g['tot_open'] - g['tot_close'], 1), pdrop)] += 1
print(cc.most_common(15))
def variant(opener, minover=58, mindrop=0.5):
    L = []
    for g in G:
        if g['hs'] is None or g.get('close_h') is None or g['close_h'] > 6 or g['tot_close'] is None: continue
        ho, ao = days_off(g, 'home'), days_off(g, 'away'); o = g[opener]
        if g['home_over_n'] >= 1 and int(100 * (g['home_over_pct'] or 0)) >= minover and ho is not None and ao is not None and 1 <= ho <= 2 and 1 <= ao <= 3 and o is not None and o - g['tot_close'] >= mindrop:
            L.append(g)
    return L
for op in ('tot_open', 'pin_tot_open'):
    for md in (0.5, 1.0, 1.5):
        L = variant(op, mindrop=md); print(f'  open={op} drop>={md}:', len(L), gr(L), '| in BL', sum(k(g) in blkeys for g in L))
print('ours-only by month:', sorted(collections.Counter(g['start'].astimezone(ET).month for g in notb).items()))
print('overlap by month:', sorted(collections.Counter(g['start'].astimezone(ET).month for g in inb).items()))
po = [g for g in notb if g['start'].astimezone(ET).month in (4,5,6) ]; print('ours-only Apr-Jun', len(po), gr(po))
print('ours-only home over% distribution:', sorted(collections.Counter(int(100*g['home_over_pct']) for g in notb).items()))
print('ours-only home games played:', sorted(collections.Counter(min(g['home_over_n'],20) for g in notb).items()))
print('overlap home over_n:', sorted(collections.Counter(min(g['home_over_n'],20) for g in inb).items()))
print('--- robustness grid (our opener), ROI at Pinnacle close')
for mo in (54, 56, 58, 60, 62, 65):
    print('  over%>=', mo, ' | '.join(f"drop>={md}: {len(L)} {gr(L)}" for md in (0.5, 1.0, 1.5, 2.0) for L in [variant('tot_open', mo, md)]))
L = [g for g in G if g['hs'] is not None and g.get('close_h') is not None and g['close_h'] <= 6 and g['tot_close'] is not None and days_off(g,'home') in (1,2) and days_off(g,'away') in (1,2,3) and g['tot_open'] is not None and g['tot_open']-g['tot_close']>=0.5]
print('  baseline: every game with the same rest and a 0.5+ drop:', len(L), gr(L))

print('BL visitor rest vs our away days off:', collections.Counter((b['arest'], days_off(g,'away')) for b, g in matched).most_common(5))
print('BL home rest vs our home days off:', collections.Counter((b['hrest'], days_off(g,'home')) for b, g in matched).most_common(5))
