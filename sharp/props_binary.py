"""Yes/No player props against Pinnacle (Sean 11/8: "have we tested all different types of props markets"): NBA double-double, NHL anytime
goal, NFL anytime touchdown. These have no line, so the first pass (sharp/props_test.py) skipped them. One snapshot per game 10 minutes
before the start; Pinnacle's Yes/No no-vig is the fair; a book's Yes or No price 2%+ better than that fair is a bet at the book.
Graded on the ESPN box score (double-double: 10+ in two of points, rebounds, assists, steals, blocks; anytime goal: goals 1+;
anytime TD: rushing + receiving TDs 1+). Usage: python3 sharp/props_binary.py nba|nhl|nfl <snapshot.jsonl.gz>"""
import sys, os, json, re, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.props_test import nm, num
from sharp.gzlines import lines
from sharp.devig import devig_pair
sp, path = sys.argv[1], sys.argv[2]
MK = {'nba': 'player_double_double', 'nhl': 'player_goal_scorer_anytime', 'nfl': 'player_anytime_td'}[sp]
NICE = dict(draftkings='DK', fanduel='FD', williamhill_us='Caesars', betrivers='BetRivers', betonlineag='BetOnline', bovada='Bovada', betmgm='BetMGM', lowvig='LowVig', circasports='Circa')
ts = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00')) if len(s) > 17 else dt.datetime.fromisoformat(s.replace('Z', ':00+00:00'))
BOX = collections.defaultdict(list)
for l in lines(os.path.join(ROOT, 'data', 'boxscores', f'{sp}.jsonl.gz')):
    d = json.loads(l); BOX[d['start'][:10]].append(({nm(k): dict(v, _name=k) for k, v in d['players'].items()}, ts(d['start'])))
def find_box(d, names):
    st = ts(d['start']); best = None
    for day in {st.date().isoformat(), (st - dt.timedelta(days=1)).date().isoformat(), (st + dt.timedelta(days=1)).date().isoformat()}:
        for box, bst in BOX.get(day, []):
            if abs((bst - st).total_seconds()) > 3600: continue
            hit = sum(1 for n in names if n in box)
            if hit >= 3 and (best is None or hit > best[0]): best = (hit, box)
    return best[1] if best else None
def yes(p):
    g = lambda *ks: next((num(p[k]) for k in ks if k in p and num(p[k]) is not None), None)
    if sp == 'nba':
        v = [g('points'), g('rebounds'), g('assists'), g('steals'), g('blocks')]
        if v[0] is None: return None
        return sum(1 for x in v if x is not None and x >= 10) >= 2
    if sp == 'nhl':
        gl = g('forwards.goals', 'defenses.goals'); return None if gl is None else gl >= 1
    if sp == 'nfl':
        r, c = g('rushing.rushingTouchdowns'), g('receiving.receivingTouchdowns')
        if r is None and c is None: return None
        return (r or 0) + (c or 0) >= 1
bets = []; skip = collections.Counter()
for l in lines(path):
    try: d = json.loads(l)
    except Exception: continue
    Q = collections.defaultdict(dict)
    for b in d.get('bookmakers') or []:
        for m in b['markets']:
            if m['key'] != MK: continue
            for o in m['outcomes']:
                Q[nm(o.get('description'))].setdefault(b['key'], {})[o['name']] = o['price']
    if not Q: continue
    box = find_box(d, set(Q))
    if not box: skip['no box'] += 1; continue
    for pl, books in Q.items():
        P = books.get('pinnacle')
        if not P or 'Yes' not in P or 'No' not in P: skip['no Pinnacle two-way'] += 1; continue
        p = box.get(pl)
        if p is None: skip['player not in box'] += 1; continue
        y = yes(p)
        if y is None: skip['no stat'] += 1; continue
        fy = (1 / P['Yes']) / (1 / P['Yes'] + 1 / P['No']); fpow = devig_pair(1 / P['Yes'], 1 / P['No'], 'power')
        bets.append(dict(season=d['start'][:4], book='Pinnacle', side='Yes', pr=P['Yes'], ev=fy * P['Yes'] - 1, won=y, fair=fy))
        bets.append(dict(season=d['start'][:4], book='Pinnacle', side='No', pr=P['No'], ev=(1 - fy) * P['No'] - 1, won=not y, fair=1 - fy))
        for bk, B in books.items():
            if bk in ('pinnacle', 'betmgm'): continue
            for side, f, fp, w in (('Yes', fy, fpow, y), ('No', 1 - fy, 1 - fpow, not y)):
                pr = B.get(side)
                if not pr: continue
                bets.append(dict(season=d['start'][:4], book=NICE.get(bk, bk), side=side, pr=pr, ev=f * pr - 1, ev_pow=fp * pr - 1, won=w, fair=f, pg=(d['game_id'], pl)))
def rep(label, L):
    if len(L) < 20: return
    n = len(L); w = sum(1 for b in L if b['won']); pnl = sum((b['pr'] - 1) if b['won'] else -1 for b in L)
    seas = collections.defaultdict(lambda: [0, 0.0])
    for b in L: seas[b['season']][0] += 1; seas[b['season']][1] += (b['pr'] - 1) if b['won'] else -1
    print(f"{label:56} n={n:6} {w}-{n-w} ROI {100*pnl/n:+6.1f}%  avg price {sum(b['pr'] for b in L)/n:.2f}  " + ' '.join(f'{k}:{100*v[1]/v[0]:+.0f}%' for k, v in sorted(seas.items())))
print(f'== {sp} {MK}: {len(bets)} priced bets; skipped {dict(skip)}')
rep('Pinnacle Yes at its own price', [b for b in bets if b['book'] == 'Pinnacle' and b['side'] == 'Yes'])
rep('Pinnacle No at its own price', [b for b in bets if b['book'] == 'Pinnacle' and b['side'] == 'No'])
G = [b for b in bets if b['book'] != 'Pinnacle' and b['ev'] >= 0.02]
rep('book 2%+ better than Pinnacle fair, both sides', G)
for side in ('Yes', 'No'):
    S = [b for b in G if b['side'] == side]
    rep(f'  {side}', S)
    rep(f'  {side} EV 2-5%', [b for b in S if b['ev'] < 0.05]); rep(f'  {side} EV 5-10%', [b for b in S if 0.05 <= b['ev'] < 0.10]); rep(f'  {side} EV 10%+', [b for b in S if b['ev'] >= 0.10])
    rep(f'  {side} power-devig EV > 0', [b for b in S if b.get('ev_pow', 0) > 0]); rep(f'  {side} power-devig EV <= 0', [b for b in S if b.get('ev_pow', 0) <= 0])
    rep(f'  {side}, Pinnacle fair under 25%', [b for b in S if b['fair'] < 0.25]); rep(f'  {side}, fair 25-50%', [b for b in S if 0.25 <= b['fair'] < 0.5]); rep(f'  {side}, fair 50%+', [b for b in S if b['fair'] >= 0.5])
    for bk in sorted({b['book'] for b in S}): rep(f'    {side} at {bk}', [b for b in S if b['book'] == bk])
if sp == 'nfl':
    print('--- anytime TD Yes, Pinnacle fair 25-50%: one bet per player and game at the best price (the only 4/4 cut above)')
    def dd(L):
        grp = collections.defaultdict(list)
        for b in L: grp[b['pg']].append(b)
        return [max(G, key=lambda b: b['pr']) for G in grp.values()]
    Y = [b for b in bets if b['book'] != 'Pinnacle' and b['side'] == 'Yes' and b['ev'] >= 0.02]
    D = dd([b for b in Y if 0.25 <= b['fair'] < 0.5])
    rep('deduped, best price', D)
    rep('  EV 2-5%', [b for b in D if b['ev'] < 0.05]); rep('  EV 5-10%', [b for b in D if 0.05 <= b['ev'] < 0.10]); rep('  EV 10%+', [b for b in D if b['ev'] >= 0.10])
    rep('  power-devig EV > 0', [b for b in D if b.get('ev_pow', 0) > 0]); rep('  power-devig EV <= 0', [b for b in D if b.get('ev_pow', 0) <= 0])
    rep('  at FD / DK / Caesars only', dd([b for b in Y if 0.25 <= b['fair'] < 0.5 and b['book'] in ('FD', 'DK', 'Caesars')]))
    rep('neighbour: fair 15-25%, deduped', dd([b for b in Y if 0.15 <= b['fair'] < 0.25])); rep('neighbour: fair 50%+, deduped', dd([b for b in Y if b['fair'] >= 0.5]))
    rep('all Yes 2%+, deduped', dd(Y))
