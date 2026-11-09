"""Outlier-book test on every prop market (Sean 11/9; follows the NFL rushing-yards result in docs/nfl_props_2026-11-08.md).
For each player and market: Pinnacle hangs exactly one two-way line; a book hangs exactly one line off it. Bet the side the gap favours at
that book (book line lower -> over, higher -> under). 'Outlier' = 2+ other books within NEAR of Pinnacle's line, so the odd one out is the
book, not Pinnacle. One snapshot per game; graded on ESPN box scores; one bet per player, game and side (largest gap). BetMGM excluded.
Usage: python3 sharp/prop_outlier.py <sport> <snapshot.jsonl.gz> [out.json]"""
import sys, os, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.props_test import stat, nm
from sharp.gzlines import lines
sp, path = sys.argv[1], sys.argv[2]
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
BIG = lambda ln: ln >= 15                      # yards / points / outs-type markets vs count markets
def bucket(gap, ln):
    if BIG(ln): return '1-2.5' if gap < 3 else '3-4' if gap < 4.5 else '4.5-7' if gap < 7.5 else '7.5+'
    return '0.5' if gap < 1 else '1' if gap < 1.5 else '1.5+'
near = lambda ln: 1.0 if BIG(ln) else 0.5
rows = []; skip = collections.Counter()
for l in lines(path):
    try: d = json.loads(l)
    except Exception: continue
    if not d.get('bookmakers'): continue
    Q = collections.defaultdict(lambda: collections.defaultdict(dict)); TS = {}
    for b in d['bookmakers']:
        if b['key'] == 'betmgm': continue
        for m in b['markets']:
            for o in m['outcomes']:
                if o.get('point') is None or o['name'] not in ('Over', 'Under'): continue
                Q[(m['key'], nm(o.get('description')))][b['key']][(o['name'].lower(), o['point'])] = o['price']
                TS[(m['key'], nm(o.get('description')), b['key'])] = m.get('last_update')
    if not Q: continue
    box = find_box(d, {k[1] for k in Q})
    if not box: skip['no box'] += 1; continue
    for (mk, pl), books in Q.items():
        P = books.get('pinnacle')
        if not P: continue
        two = lambda B: sorted({ln for (s, ln) in B if ('over', ln) in B and ('under', ln) in B})
        pl_l = two(P)
        if len(pl_l) != 1: continue
        ln0 = pl_l[0]; p = box.get(pl)
        if p is None: continue
        v = stat(sp, mk, p)
        if v is None: continue
        L = {bk: two(B) for bk, B in books.items() if bk != 'pinnacle'}
        for bk, bl in L.items():
            if len(bl) != 1 or bl[0] == ln0: continue
            gap = abs(bl[0] - ln0); side = 'over' if bl[0] < ln0 else 'under'; pr = books[bk][(side, bl[0])]
            agree = sum(1 for k2, l2 in L.items() if k2 != bk and any(abs(x - ln0) <= near(ln0) for x in l2))
            lag = None
            if TS.get((mk, pl, 'pinnacle')) and TS.get((mk, pl, bk)):
                try: lag = (ts(TS[(mk, pl, 'pinnacle')]) - ts(TS[(mk, pl, bk)])).total_seconds() / 60
                except Exception: pass
            won = None if v == bl[0] else (v > bl[0]) == (side == 'over')
            rows.append(dict(mk=mk, pg=(d.get('game_id') or d['start'], pl, side), season=d['start'][:4], gap=gap, b=bucket(gap, ln0), ln0=ln0, side=side, pr=pr,
                             won=won, book=bk, agree=agree, lag=lag))
def dd(L):
    g = {}
    for r in L:
        if r['pg'] not in g or r['gap'] > g[r['pg']]['gap'] or (r['gap'] == g[r['pg']]['gap'] and r['pr'] > g[r['pg']]['pr']): g[r['pg']] = r
    return list(g.values())
def stats(L):
    L = [r for r in L if r['won'] is not None]
    if not L: return None
    n = len(L); w = sum(r['won'] for r in L); pnl = sum((r['pr'] - 1) if r['won'] else -1 for r in L)
    be = sum(1 / r['pr'] for r in L) / n
    seas = collections.defaultdict(lambda: [0, 0.0])
    for r in L: seas[r['season']][0] += 1; seas[r['season']][1] += (r['pr'] - 1) if r['won'] else -1
    pos = sum(1 for s in seas.values() if s[1] > 0)
    return dict(n=n, w=w, l=n - w, roi=round(100 * pnl / n, 1), z=round((w / n - be) / math.sqrt(be * (1 - be) / n), 2), pos=pos, ns=len(seas),
                seasons={k: f'{v[0]} {100 * v[1] / v[0]:+.0f}%' for k, v in sorted(seas.items())})
def line(label, s):
    if not s or s['n'] < 25: return
    print(f"{label:58} n={s['n']:5} {s['w']}-{s['l']:<5} ROI {s['roi']:+6.1f}%  z {s['z']:+5.2f}  seasons+ {s['pos']}/{s['ns']}  " + ' '.join(f'{k[2:]}:{v.split()[1]}' for k, v in s['seasons'].items()))
OUT = {}
print(f'== {sp}: {len(rows)} off-line book quotes; skipped {dict(skip)}')
for mk in sorted({r['mk'] for r in rows}):
    R = [r for r in rows if r['mk'] == mk]
    for b in ('0.5', '1', '1.5+', '1-2.5', '3-4', '4.5-7', '7.5+'):
        RB = [r for r in R if r['b'] == b]
        if not RB: continue
        out = dd([r for r in RB if r['agree'] >= 2]); notout = dd([r for r in RB if r['agree'] < 2])
        so, sn = stats(out), stats(notout)
        OUT[f'{mk}|{b}|outlier'] = so; OUT[f'{mk}|{b}|pinnacle odd'] = sn
        line(f'{mk.replace("player_","").replace("batter_","b.").replace("pitcher_","p.")} gap {b}: OUTLIER book', so)
        line(f'{"":>{len(mk.replace("player_","").replace("batter_","b.").replace("pitcher_","p."))}} gap {b}: Pinnacle the odd one', sn)
print('-- all markets pooled')
for b in ('0.5', '1', '1.5+', '1-2.5', '3-4', '4.5-7', '7.5+'):
    o = stats(dd([r for r in rows if r['b'] == b and r['agree'] >= 2]))
    OUT[f'ALL|{b}|outlier'] = o; line(f'all markets gap {b}: OUTLIER book', o)
for b in ('1.5+', '4.5-7', '7.5+'):
    for s_ in ('over', 'under'):
        o = stats(dd([r for r in rows if r['b'] == b and r['agree'] >= 2 and r['side'] == s_])); OUT[f'ALL|{b}|outlier|{s_}'] = o; line(f'  gap {b} outlier, {s_}', o)
    o = stats(dd([r for r in rows if r['b'] == b and r['agree'] >= 2 and r['lag'] is not None and r['lag'] > 0])); OUT[f'ALL|{b}|outlier|pin newer'] = o; line(f'  gap {b} outlier, Pinnacle quote newer than the book', o)
    o = stats(dd([r for r in rows if r['b'] == b and r['agree'] >= 2 and r['book'] in ('fanduel', 'draftkings', 'williamhill_us')])); OUT[f'ALL|{b}|outlier|FD DK Caesars'] = o; line(f'  gap {b} outlier, FD / DK / Caesars only', o)
if len(sys.argv) > 3: json.dump(OUT, open(sys.argv[3], 'w'), indent=1)
