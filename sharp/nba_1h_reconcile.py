#!/usr/bin/env python3
"""Reconcile nba_1h_under_hot_over (11/6): the Bet Labs pick list (ScreenId 1784158, 2023-24 on: home|away|home 1H|away 1H|1H line|W/L|
profit|visitor over%) joined to the odds database, graded at Pinnacle's 1H total about 10 minutes before tip (derivs/nba_full) on ESPN
period scores, against our replay of the same filter (visitor over% 71+ vs closing totals). Usage: python3 sharp/nba_1h_reconcile.py"""
import os, sys, json, sqlite3, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.rule_replay as RR
from sharp.gzlines import lines
ET = RR.ET
G = RR.load('nba'); RR.profiles(G)
idx = {(g['start'].astimezone(ET).date(), g['away'], g['home']): g for g in G}
conn = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
ESPN = {r[0]: r[1] for r in conn.execute("SELECT game_id, espn_id FROM results")}
LS = json.load(open(os.path.join(ROOT, 'data', 'state', 'linescores.json'))).get('nba', {})
H1 = {}
for l in lines(os.path.join(ROOT, 'data', 'oddsapi', 'derivs', 'nba_full.jsonl.gz')):
    try: d = json.loads(l)
    except Exception: continue
    for b in d.get('bookmakers') or []:
        if b['key'] != 'pinnacle': continue
        for m in b['markets']:
            if m['key'] == 'totals_h1':
                u = [o for o in m['outcomes'] if o['name'] == 'Under']
                if u: H1[d['game_id']] = (u[0]['point'], u[0]['price'])
def h1score(g):
    ls = LS.get(str(ESPN.get(g['id'])))
    return (sum(ls['h'][:2]), sum(ls['a'][:2])) if ls and len(ls['h']) >= 2 and len(ls['a']) >= 2 else None
def grade(g):
    if g['id'] not in H1: return None
    sc = h1score(g)
    if not sc: return None
    ln, dec = H1[g['id']]; t = sc[0] + sc[1]
    return (0.5, 0) if t == ln else ((1, dec - 1) if t < ln else (0, -1))
def roi(L):
    w = sum(1 for x in L if x[0] == 1); lo = sum(1 for x in L if x[0] == 0); u = sum(x[1] for x in L)
    return f"{w}-{lo} ({100 * u / max(1, w + lo):+.1f}%)"
BL = []
for l in open(os.path.join(ROOT, 'data', 'research', 'betlabs', 'nba_1h_under_1784158.txt')):
    f = l.strip().split('|')
    m, d, y = f[0].split('/'); BL.append(dict(date=dt.date(2000 + int(y), int(m), int(d)), home=f[1], away=f[2], hs=int(f[3]), as_=int(f[4]), line=float(f[5]), res=f[6], profit=float(f[7]), vover=int(f[8])))
sea = lambda D: D.year if D.month >= 8 else D.year - 1
print('Bet Labs picks (2023-24 on):', len(BL), roi([((1 if b['res'] == 'W' else 0 if b['res'] == 'L' else .5), b['profit'] / 100) for b in BL]), '(its own lines and prices)')
M = [(b, idx.get((b['date'], b['away'], b['home']))) for b in BL]; Mm = [(b, g) for b, g in M if g]
print('matched to our database:', len(Mm))
sm = sum(1 for b, g in Mm if h1score(g) and h1score(g) != (b['hs'], b['as_'])); print('1H score mismatches vs ESPN:', sm)
pin = [(b, g, grade(g)) for b, g in Mm]; pin = [x for x in pin if x[2]]
print('Bet Labs picks at Pinnacle 1H line:', len(pin), roi([x[2] for x in pin]))
ld = collections.Counter(round(H1[g['id']][0] - b['line'], 1) for b, g, _ in pin); print('  Pinnacle 1H line minus Bet Labs line:', ld.most_common(8))
for s in sorted({sea(b['date']) for b, g, _ in pin}):
    L = [x for x in pin if sea(x[0]['date']) == s]
    print(f"  {s}: Bet Labs own {roi([((1 if b['res'] == 'W' else 0 if b['res'] == 'L' else .5), b['profit'] / 100) for b, _, _ in L])} | at Pinnacle {roi([x[2] for x in L])}")
ours = [g for g in G if g['id'] in H1 and g['hs'] is not None and g['away_over_n'] >= 1 and int(100 * (g['away_over_pct'] or 0)) >= 71]
blk = {(b['date'], b['away'], b['home']) for b in BL}; k = lambda g: (g['start'].astimezone(ET).date(), g['away'], g['home'])
gl = lambda L: roi([x for x in (grade(g) for g in L) if x])
print('our replay (visitor over% 71+, games with a Pinnacle 1H line):', len(ours), gl(ours))
print('  also Bet Labs:', gl([g for g in ours if k(g) in blk]), '| ours only:', gl([g for g in ours if k(g) not in blk]))
print('  ours only, by visitor games played:', sorted(collections.Counter(min(g['away_over_n'], 10) for g in ours if k(g) not in blk).items()))
ov = collections.Counter(int(100 * (g['away_over_pct'] or 0)) - b['vover'] for b, g, _ in pin); print('  our visitor over% minus Bet Labs:', ov.most_common(8))
# what Bet Labs counts: by visitor over% band and month
for lab, f in (('visitor over 100% (first games)', lambda b: b['vover'] == 100), ('71-99%', lambda b: b['vover'] < 100)):
    L = [x for x in pin if f(x[0])]; print(f'  Bet Labs picks {lab}: at Pinnacle {roi([x[2] for x in L])}')
base = [x for x in (grade(g) for g in G if g['id'] in H1 and g['hs'] is not None) if x]
print('every NBA game, 1H under at Pinnacle:', roi(base))
oct_ = [x for x in (grade(g) for g in G if g['id'] in H1 and g['hs'] is not None and g['start'].astimezone(ET).month in (10, 11)) if x]
print('every Oct-Nov game, 1H under:', roi(oct_))
