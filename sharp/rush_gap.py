"""NFL rush-yards line gap: a book's only rushing line differs from Pinnacle's only line by 4.5+ yards; bet the side the gap favours at the book."""
import sys, json, collections, datetime as dt
sys.path.insert(0, '/home/claude/sharp-tracker')
from sharp.props_test import stat, nm
from sharp.gzlines import lines
ts = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00')) if len(s) > 17 else dt.datetime.fromisoformat(s.replace('Z', ':00+00:00'))
BOX = collections.defaultdict(list)
for l in lines('/home/claude/sharp-tracker/data/boxscores/nfl.jsonl.gz'):
    d = json.loads(l); BOX[d['start'][:10]].append(({nm(k): dict(v, _name=k) for k, v in d['players'].items()}, ts(d['start'])))
def find_box(d, names):
    st = ts(d['start']); best = None
    for day in {st.date().isoformat(), (st - dt.timedelta(days=1)).date().isoformat(), (st + dt.timedelta(days=1)).date().isoformat()}:
        for box, bst in BOX.get(day, []):
            if abs((bst - st).total_seconds()) > 3600: continue
            hit = sum(1 for n in names if n in box)
            if hit >= 3 and (best is None or hit > best[0]): best = (hit, box)
    return best[1] if best else None
rows = []
for l in lines(sys.argv[1]):
    d = json.loads(l)
    if not d.get('bookmakers'): continue
    Q = collections.defaultdict(dict); TS = {}
    for b in d['bookmakers']:
        for m in b['markets']:
            if m['key'] != 'player_rush_yds': continue
            for o in m['outcomes']:
                if o.get('point') is None: continue
                Q[nm(o['description'])].setdefault(b['key'], {})[(o['name'].lower(), o['point'])] = o['price']; TS[(nm(o['description']), b['key'])] = m.get('last_update')
    if not Q: continue
    box = find_box(d, set(Q))
    if not box: continue
    for pl, books in Q.items():
        P = books.get('pinnacle')
        if not P: continue
        pl_lines = sorted({ln for (s, ln) in P if ('over', ln) in P and ('under', ln) in P})
        if len(pl_lines) != 1: continue
        ln0 = pl_lines[0]; p = box.get(pl)
        if p is None: continue
        v = stat('nfl', 'player_rush_yds', p)
        if v is None: continue
        pu = P[('under', ln0)]; po = P[('over', ln0)]; fo = (1 / po) / (1 / po + 1 / pu)
        nb = sum(1 for bk in books if bk != 'pinnacle')
        for bk, B in books.items():
            if bk in ('pinnacle', 'betmgm'): continue
            bl = sorted({ln for (s, ln) in B if ('over', ln) in B and ('under', ln) in B})
            if len(bl) != 1 or bl[0] == ln0: continue
            side = 'over' if bl[0] < ln0 else 'under'; gap = abs(bl[0] - ln0); pr = B[(side, bl[0])]
            won = None if v == bl[0] else (v > bl[0]) == (side == 'over')
            # how many other books agree with Pinnacle (within 1 yd)?
            agree = sum(1 for k2, B2 in books.items() if k2 not in (bk, 'pinnacle') and any(abs(ln - ln0) <= 1 for (s, ln) in B2))
            lag = None
            if TS.get((pl, 'pinnacle')) and TS.get((pl, bk)): lag = (ts(TS[(pl, 'pinnacle')]) - ts(TS[(pl, bk)])).total_seconds() / 60   # + = Pinnacle newer
            rows.append(dict(season=d['start'][:4], side=side, gap=gap, pr=pr, won=won, book=bk, ln0=ln0, bl=bl[0], fo=fo, agree=agree, lag=lag, pin_fav=fo if side == 'over' else 1 - fo))
def rep(label, L):
    L = [r for r in L if r['won'] is not None]
    if not L: print(f'{label:50} n=0'); return
    w = sum(r['won'] for r in L); n = len(L); pnl = sum((r['pr'] - 1) if r['won'] else -1 for r in L)
    seas = collections.defaultdict(float)
    for r in L: seas[r['season']] += (r['pr'] - 1) if r['won'] else -1
    print(f"{label:50} n={n:4} {w}-{n-w} ROI {100*pnl/n:+5.1f}%  avg price {sum(r['pr'] for r in L)/n:.3f}  " + ' '.join(f'{k}:{100*v/sum(1 for r in L if r["season"]==k):+.0f}%' for k, v in sorted(seas.items())))
G = [r for r in rows if r['gap'] >= 4.5]
rep('gap 4.5+ all', G); rep('  over (book line lower)', [r for r in G if r['side'] == 'over']); rep('  under (book line higher)', [r for r in G if r['side'] == 'under'])
rep('  gap 4.5-7', [r for r in G if r['gap'] <= 7]); rep('  gap 7.5-12', [r for r in G if 7 < r['gap'] <= 12]); rep('  gap 12.5+', [r for r in G if r['gap'] > 12])
rep('  2+ other books agree with Pinnacle', [r for r in G if r['agree'] >= 2]); rep('  0-1 other books agree', [r for r in G if r['agree'] < 2])
rep('  Pinnacle quote newer than book (stale book)', [r for r in G if r['lag'] is not None and r['lag'] > 0]); rep('  book quote newer or same', [r for r in G if r['lag'] is not None and r['lag'] <= 0])
rep('  Pinnacle line under 30 yds', [r for r in G if r['ln0'] < 30]); rep('  Pinnacle line 30-60', [r for r in G if 30 <= r['ln0'] < 60]); rep('  Pinnacle line 60+', [r for r in G if r['ln0'] >= 60])
rep('gap 2.5-4 (neighbour)', [r for r in rows if 2.5 <= r['gap'] < 4.5]); rep('gap 1.5-2 (neighbour)', [r for r in rows if 1.5 <= r['gap'] < 2.5])
for bk in sorted({r['book'] for r in G}): rep(f'  {bk}', [r for r in G if r['book'] == bk])
# dedupe: one bet per player-game (best gap)
best = {}
for i, r in enumerate(G):
    k = (r['season'], r['ln0'], r['fo'], r['side'])  # proxy for player-game-side
    if k not in best or r['gap'] > G[best[k]]['gap']: best[k] = i
rep('gap 4.5+, one per player-game-side', [G[i] for i in best.values()])
print('--- outlier book (2+ other books within 1 yd of Pinnacle), one per player-game-side')
A = [r for r in G if r['agree'] >= 2]; best = {}
for i, r in enumerate(A):
    k = (r['season'], r['ln0'], r['fo'], r['side'])
    if k not in best or r['gap'] > A[best[k]]['gap']: best[k] = i
D = [A[i] for i in best.values()]
rep('all', D); rep('  Pinnacle line under 60', [r for r in D if r['ln0'] < 60]); rep('  Pinnacle line 60+', [r for r in D if r['ln0'] >= 60])
rep('  gap 4.5-7', [r for r in D if r['gap'] <= 7]); rep('  over', [r for r in D if r['side'] == 'over']); rep('  under', [r for r in D if r['side'] == 'under'])
A2 = [r for r in rows if 2.5 <= r['gap'] < 4.5 and r['agree'] >= 2]; best = {}
for i, r in enumerate(A2):
    k = (r['season'], r['ln0'], r['fo'], r['side'])
    if k not in best: best[k] = i
rep('neighbour: outlier by 2.5-4 yds, deduped', [A2[i] for i in best.values()])
import math
L = [r for r in D if r['won'] is not None]; w = sum(r['won'] for r in L); n = len(L)
print(f'z vs 52.4% breakeven: {(w/n - 0.524)/math.sqrt(0.25/n):+.2f}  (n={n})')
