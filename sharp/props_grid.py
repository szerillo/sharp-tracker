"""Props price-gap rules (NBA threes unders, NHL saves / shots unders): does a higher EV threshold, the power devig, or a fresher Pinnacle
quote raise ROI? One snapshot per game (about T-10 min), graded on ESPN box scores. Flat 1u at the book price; pushes void."""
import sys, json, gzip, collections, datetime as dt
sys.path.insert(0, '/home/claude/sharp-tracker')
from sharp.props_test import stat, nm, fuzzy
from sharp.devig import devig_pair
from sharp.gzlines import lines

sp = sys.argv[1]; MKS = {'nba': ('player_threes',), 'nhl': ('player_total_saves', 'player_shots_on_goal')}[sp]
BOOKS = {'fanduel': 'FD', 'williamhill_us': 'Caesars', 'draftkings': 'DK'}
ts = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00')) if len(s) > 17 else dt.datetime.fromisoformat(s.replace('Z', ':00+00:00'))
BOX = collections.defaultdict(list)
for l in lines(f'/home/claude/sharp-tracker/data/boxscores/{sp}.jsonl.gz'):
    d = json.loads(l); BOX[d['start'][:10]].append(({nm(k): dict(v, _name=k) for k, v in d['players'].items()}, ts(d['start'])))

def find_box(d, names):
    st = ts(d['start']); best = None
    for day in {st.date().isoformat(), (st - dt.timedelta(days=1)).date().isoformat(), (st + dt.timedelta(days=1)).date().isoformat()}:
        for box, bst in BOX.get(day, []):
            if abs((bst - st).total_seconds()) > 3600: continue
            hit = sum(1 for n in names if n in box)
            if hit >= 3 and (best is None or hit > best[0]): best = (hit, box)
    return best[1] if best else None

bets = []
for l in lines(f'/home/claude/sharp-tracker/data/oddsapi/derivs/{sp}_props.jsonl.gz' if len(sys.argv) < 3 else sys.argv[2]):
    try: d = json.loads(l)
    except Exception: continue
    if not d.get('bookmakers'): continue
    Q = collections.defaultdict(dict); TSQ = {}; desc = {}
    for b in d['bookmakers']:
        for m in b['markets']:
            if m['key'] not in MKS: continue
            for o in m['outcomes']:
                if o.get('point') is None or o['name'] not in ('Over', 'Under'): continue
                k = (m['key'], nm(o.get('description'))); desc[k] = o.get('description')
                Q[k].setdefault(b['key'], {})[(o['name'].lower(), o['point'])] = o['price']
                TSQ[(k, b['key'])] = m.get('last_update') or b.get('last_update')
    if not Q: continue
    box = find_box(d, {k[1] for k in Q})
    if not box: continue
    snap = ts(d.get('snap') or d['asked']); mins_to_start = (ts(d['start']) - snap).total_seconds() / 60
    for k, books in Q.items():
        p = box.get(k[1]) or fuzzy(box, desc.get(k))
        if p is None: continue
        v = stat(sp, k[0], p)
        if v is None: continue
        P = books.get('pinnacle')
        if not P: continue
        for (s, ln) in list(P):
            if s != 'under' or ('over', ln) not in P: continue
            pu, po = P[('under', ln)], P[('over', ln)]
            fu = (1 / pu) / (1 / pu + 1 / po); fpow = devig_pair(1 / pu, 1 / po, 'power')
            cand = [(bk, B[('under', ln)], B.get(('over', ln))) for bk, B in books.items() if bk in BOOKS and ('under', ln) in B]
            if not cand: continue
            bk, pr, bo = max(cand, key=lambda c: c[1])
            ev = fu * pr - 1
            if ev < 0.02: continue
            won = 0.5 if v == ln else 1 if v < ln else 0
            if won == 0.5: continue
            pt, bt = TSQ.get((k, 'pinnacle')), TSQ.get((k, bk))
            lag = (ts(bt) - ts(pt)).total_seconds() / 60 if pt and bt else None        # book quote newer than Pinnacle's by this many min
            age = (snap - ts(pt)).total_seconds() / 60 if pt else None
            bfair = (1 / pr) / (1 / pr + 1 / bo) if bo else None
            bets.append(dict(season=d['start'][:4], mk=k[0], ev=ev, ev_pow=fpow * pr - 1, pnl=(pr - 1) if won else -1, won=won, lag=lag, age=age,
                             gap=(fu - bfair) if bfair else None, mins=mins_to_start, price=pr))

def rep(label, L):
    if not L: print(f'{label:52} n=0'); return
    n = len(L); w = sum(b['won'] for b in L); roi = 100 * sum(b['pnl'] for b in L) / n
    seas = collections.defaultdict(list)
    for b in L: seas[b['season']].append(b['pnl'])
    pos = sum(1 for s in seas.values() if sum(s) > 0)
    print(f"{label:52} n={n:5}  {w:.0f}-{n - w:.0f}  ROI {roi:+5.1f}%  seasons + {pos}/{len(seas)}  avg EV {100 * sum(b['ev'] for b in L) / n:.1f}%")

print(f'== {sp}: {len(bets)} under bets at 2%+ (proportional Pinnacle fair), snapshot T-{sorted(b["mins"] for b in bets)[len(bets)//2]:.0f} min median')
for m in MKS: rep(f'{m} all 2%+', [b for b in bets if b['mk'] == m])
print('-- EV threshold (proportional)')
for lo, hi in ((0.02, 0.03), (0.03, 0.04), (0.04, 0.06), (0.06, 9)): rep(f'EV {100*lo:.0f}-{100*hi:.0f}%', [b for b in bets if lo <= b['ev'] < hi])
for t in (0.02, 0.03, 0.04, 0.05): rep(f'EV >= {100*t:.0f}%', [b for b in bets if b['ev'] >= t])
print('-- power devig')
rep('power EV > 0 (the new check)', [b for b in bets if b['ev_pow'] > 0]); rep('power EV <= 0 (now dropped)', [b for b in bets if b['ev_pow'] <= 0])
for t in (0.02, 0.03): rep(f'power EV >= {100*t:.0f}%', [b for b in bets if b['ev_pow'] >= t])
print('-- Pinnacle freshness')
rep('Pinnacle quote not older than book (lag <= 0)', [b for b in bets if b['lag'] is not None and b['lag'] <= 0])
rep('book newer by 0-10 min', [b for b in bets if b['lag'] is not None and 0 < b['lag'] <= 10])
rep('book newer by 10+ min (now dropped)', [b for b in bets if b['lag'] is not None and b['lag'] > 10])
rep('Pinnacle quote <= 5 min old', [b for b in bets if b['age'] is not None and b['age'] <= 5])
rep('Pinnacle quote 5-20 min old', [b for b in bets if b['age'] is not None and 5 < b['age'] <= 20])
rep('Pinnacle quote 20+ min old (now dropped)', [b for b in bets if b['age'] is not None and b['age'] > 20])
print('-- fair-to-fair gap (Pinnacle fair minus book fair)')
for lo, hi in ((-1, 0.02), (0.02, 0.04), (0.04, 9)): rep(f'gap {100*lo:.0f}-{100*hi:.0f} pts', [b for b in bets if b['gap'] is not None and lo <= b['gap'] < hi])
