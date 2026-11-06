#!/usr/bin/env python3
"""Stale US books vs Pinnacle on our own tape (Sean 11/6, list item 1).
Every 20-minute snapshot in data/<sport>/ticks/*.jsonl.gz: Pinnacle's no-vig fair for each side (moneyline; spread and total at
Pinnacle's own number), and every US book's price at the SAME number. A book quote with expected value of 2%+ against that fair is an
opportunity; the first time each (game, market, side, book) crosses the bar is the bet. Split by whether Pinnacle moved toward that side
in the previous 40 minutes (the book is lagging a move) or not (the book simply disagrees).
Graded flat at the book's price on ESPN finals (data/state/hist_schedule.json); CLV against Pinnacle's last pregame no-vig fair at the
same number. Kalshi graded at the ask plus the taker fee. Writes data/research/stale_books.json.
Usage: python3 sharp/stale_books.py [sports...]"""
import os, sys, json, gzip, glob, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
BOOKS = ('DK', 'FD', 'Caesars', 'BetRivers', 'Fanatics', 'theScore', 'Kalshi')
OUT = os.path.join(ROOT, 'data', 'research', 'stale_books.json')
OPP = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}


def dec(r):
    if r.get('venue') == 'Kalshi':
        a = r.get('ask')
        if a is None or not 0.02 < a < 0.98: return None
        fee = math.ceil(0.07 * a * (1 - a) * 100) / 100
        return 1 / (a + fee)
    a = r.get('american')
    if a is None: return None
    return 1 + (a / 100 if a > 0 else 100 / -a)


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def main():
    sports = sys.argv[1:] or ['nba', 'nhl', 'nfl', 'cfb', 'cbb']
    H = json.load(open(os.path.join(ROOT, 'data', 'state', 'hist_schedule.json')))
    bets = []
    for sp in sports:
        R = collections.defaultdict(list)          # (event, market) -> rows
        for f in sorted(glob.glob(os.path.join(ROOT, 'data', sp, 'ticks', '*.jsonl.gz'))):
            try:
                for l in gzip.open(f, 'rt'):
                    r = json.loads(l)
                    if r.get('market') in ('ml', 'spread', 'total') and (r['venue'] == 'Pinnacle' or r['venue'] in BOOKS): R[(r['event_id'], r['market'])].append(r)
            except (EOFError, OSError): pass
        G = H.get(sp, {})
        for (ev, mk), L in R.items():
            g = G.get(str(ev))
            if not g or not g.get('final') or g.get('hs') is None: continue
            start = ts(g['start'].replace('Z', ':00Z') if len(g['start']) == 17 else g['start'])
            L = [r for r in L if ts(r['ts']) < start]
            if not L: continue
            snaps = collections.defaultdict(list)
            for r in L: snaps[r['ts'][:16]].append(r)
            order = sorted(snaps)
            pin_hist = []                     # (t, line_key, {side: fair})
            done = set(); last_fair = {}
            for k in order:
                S = snaps[k]; t = ts(S[0]['ts'])
                P = [r for r in S if r['venue'] == 'Pinnacle']
                if P:
                    by = {}
                    for r in P: by.setdefault(r['side'], r)
                    sides = list(by)
                    if len(sides) == 2:
                        a, b = by[sides[0]], by[sides[1]]
                        da, db = dec(a), dec(b)
                        if da and db:
                            pa = (1 / da) / (1 / da + 1 / db)
                            fair = {sides[0]: (pa, a.get('line')), sides[1]: (1 - pa, b.get('line'))}
                            pin_hist.append((t, fair)); last_fair = fair
                if not pin_hist or (t - pin_hist[-1][0]).total_seconds() > 1800: continue
                fair = pin_hist[-1][1]
                prev = [x for x in pin_hist if 1200 <= (t - x[0]).total_seconds() <= 2700]
                for r in S:
                    if r['venue'] == 'Pinnacle' or r['side'] not in fair: continue
                    p, ln = fair[r['side']]
                    if mk != 'ml' and r.get('line') != ln: continue
                    d = dec(r)
                    if not d: continue
                    ev_ = p * d - 1
                    if ev_ < 0.02: continue
                    key = (ev, mk, r['side'], r['venue'])
                    if key in done: continue
                    done.add(key)
                    moved = None
                    if prev:
                        q = prev[0][1].get(r['side'])
                        if q and q[1] == ln: moved = round(100 * (p - q[0]), 1)
                    bets.append(dict(sport=sp, ev=ev, mk=mk, side=r['side'], book=r['venue'], line=r.get('line'), dec=d, fair=p, edge=round(100 * ev_, 1), t=k, moved=moved,
                                     hours=round((start - t).total_seconds() / 3600, 1), hs=g['hs'], as_=g['as_']))
            # close: last Pinnacle fair before the start
            for b in bets:
                if b['ev'] == ev and b['mk'] == mk and 'close' not in b and last_fair.get(b['side']) and (mk == 'ml' or last_fair[b['side']][1] == b['line']):
                    b['close'] = last_fair[b['side']][0]
    # grade
    for b in bets:
        hs, as_ = b['hs'], b['as_']
        if b['mk'] == 'ml': won = 1 if (hs > as_) == (b['side'] == 'home') else 0 if hs != as_ else 0.5
        elif b['mk'] == 'spread':
            m = (hs - as_ if b['side'] == 'home' else as_ - hs) + b['line']; won = 0.5 if m == 0 else 1 if m > 0 else 0
        else:
            tot = hs + as_; won = 0.5 if tot == b['line'] else 1 if (tot > b['line']) == (b['side'] == 'over') else 0
        b['won'] = won; b['pl'] = (b['dec'] - 1) if won == 1 else -1 if won == 0 else 0
        b['clv'] = round(100 * (b['close'] * b['dec'] - 1), 2) if b.get('close') else None

    def rec(L):
        w = sum(1 for b in L if b['won'] == 1); l = sum(1 for b in L if b['won'] == 0)
        c = [b['clv'] for b in L if b['clv'] is not None]
        return dict(n=len(L), w=w, l=l, roi=round(100 * sum(b['pl'] for b in L) / max(1, w + l), 1), edge=round(sum(b['edge'] for b in L) / max(1, len(L)), 1),
                    clv=round(sum(c) / len(c), 2) if c else None)
    R = {}
    def add(name, L):
        if L: R[name] = rec(L); x = R[name]; print(f"{name:52s} n={x['n']:4d} {x['w']}-{x['l']} ROI {x['roi']:+.1f}%  edge at bet {x['edge']:.1f}%  EV at close {x['clv']}")
    add('all', bets)
    for k in ('edge 2-4%', 'edge 4-7%', 'edge 7%+'):
        lo, hi = {'edge 2-4%': (2, 4), 'edge 4-7%': (4, 7), 'edge 7%+': (7, 999)}[k]
        add(k, [b for b in bets if lo <= b['edge'] < hi])
    add('after a Pinnacle move toward the side (1+ pt)', [b for b in bets if b['moved'] is not None and b['moved'] >= 1])
    add('no Pinnacle move (book simply disagrees)', [b for b in bets if b['moved'] is not None and abs(b['moved']) < 1])
    add('Pinnacle moved away from the side', [b for b in bets if b['moved'] is not None and b['moved'] <= -1])
    for bk in BOOKS: add(f'book {bk}', [b for b in bets if b['book'] == bk])
    for bk in BOOKS: add(f'book {bk}, after a Pinnacle move', [b for b in bets if b['book'] == bk and b['moved'] is not None and b['moved'] >= 1])
    for mk in ('ml', 'spread', 'total'): add(f'market {mk}', [b for b in bets if b['mk'] == mk])
    for sp in sports: add(f'sport {sp}', [b for b in bets if b['sport'] == sp])
    for lab, lo, hi in (('6h+ before start', 6, 999), ('1-6h', 1, 6), ('inside 1h', 0, 1)): add(f'timing {lab}', [b for b in bets if lo <= b['hours'] < hi])
    json.dump(dict(results=R, bets=bets[:5000]), open(OUT, 'w'))
    print('wrote', OUT, len(bets), 'bets')


if __name__ == '__main__':
    main()
