#!/usr/bin/env python3
"""Do US books misprice derivatives against Pinnacle? (Sean 11/5: "finding market inefficiencies ... have to exist somewhere".)
From data/oddsapi/derivs/<sport>.jsonl.gz (one snapshot 10-14 minutes before the start, every book at the same moment):
  A. line gap: a US book's main line differs from Pinnacle's main line on the same market; bet the side the gap favours at that book
     (1H total 21.5 at DK vs 20.5 at Pinnacle -> under 21.5 at DK).
  B. price gap: same line as Pinnacle, and the book's price beats Pinnacle's no-vig fair by 2%+ of expected value.
Markets: totals_h1, spreads_h1, team_totals (main line = the pair whose two prices are both between 1.60 and 2.40). Graded on
half-time (ESPN linescores) or final team scores, flat stakes at the book's price. Writes data/research/deriv_soft_<sport>.json.
Usage: python3 sharp/deriv_soft.py nfl"""
import os, sys, json, gzip, sqlite3, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
US = ('draftkings', 'fanduel', 'williamhill_us', 'betrivers', 'betonlineag', 'lowvig', 'circasports', 'bovada')
NICE = dict(draftkings='DK', fanduel='FD', williamhill_us='Caesars', betrivers='BetRivers', betonlineag='BetOnline', lowvig='LowVig', circasports='Circa', bovada='Bovada')


def main_pair(outs, key):
    """{group: (line, over/home dec, under/away dec)} for the main line. group = team (team totals) or '' (totals/spreads)."""
    G = collections.defaultdict(dict)
    for o in outs:
        g = (o.get('description') or '') if key == 'team_totals' else ''
        if key == 'spreads_h1': G[(g, abs(o.get('point') or 0))][o['name']] = o
        else: G[(g, o.get('point'))][o['name']] = o
    best = {}
    for (g, ln), d in G.items():
        if key == 'spreads_h1':
            if len(d) != 2: continue
            a, b = list(d.values())
            if not (1.6 <= a['price'] <= 2.4 and 1.6 <= b['price'] <= 2.4): continue
            cand = (a, b)
        else:
            if 'Over' not in d or 'Under' not in d: continue
            if not (1.6 <= d['Over']['price'] <= 2.4 and 1.6 <= d['Under']['price'] <= 2.4): continue
            cand = (d['Over'], d['Under'])
        score = abs(cand[0]['price'] - cand[1]['price'])
        if g not in best or score < best[g][0]: best[g] = (score, cand)
    return {g: c for g, (_, c) in best.items()}


def main():
    sp = sys.argv[1] if len(sys.argv) > 1 else 'nfl'
    D = [json.loads(l) for l in gzip.open(os.path.join(ROOT, 'data', 'oddsapi', 'derivs', f'{sp}.jsonl.gz'), 'rt')]
    LS = json.load(open(os.path.join(ROOT, 'data', 'state', 'linescores.json'))).get(sp, {})
    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    RES = {r[0]: r[1:] for r in conn.execute("SELECT game_id, espn_id, home_score, away_score FROM results")}
    H = collections.defaultdict(list)
    for d in D:
        if not d['bookmakers'] or d['game_id'] not in RES: continue
        eid, hs, as_ = RES[d['game_id']]; ls = LS.get(str(eid))
        if hs is None: continue
        h1 = (sum(ls['h'][:2]), sum(ls['a'][:2])) if ls and len(ls.get('h', [])) >= 2 else None
        B = {b['key']: {m['key']: m['outcomes'] for m in b['markets']} for b in d['bookmakers']}
        if 'pinnacle' not in B: continue
        for mk in ('totals_h1', 'spreads_h1', 'team_totals'):
            if mk != 'team_totals' and h1 is None: continue
            P = main_pair(B['pinnacle'].get(mk, []), mk)
            for book in US:
                if mk not in B.get(book, {}): continue
                Q = main_pair(B[book][mk], mk)
                for g, (q1, q2) in Q.items():
                    if g not in P: continue
                    p1, p2 = P[g]
                    if mk == 'spreads_h1':
                        # align by team name: q1/p1 are the same team
                        if q1['name'] != p1['name']: p1, p2 = p2, p1
                        if q1['name'] != p1['name']: continue
                        home_is_1 = q1['name'] == d['home']
                        m1 = (h1[0] - h1[1]) if home_is_1 else (h1[1] - h1[0])      # team 1's 1H margin
                        def res(side, ln):      # side 1 or 2, ln = that side's points
                            c = (m1 if side == 1 else -m1) + ln; return 0.5 if c == 0 else 1 if c > 0 else 0
                        gap = q1['point'] - p1['point']           # positive: book gives team 1 more points than Pinnacle
                        fair1 = (1 / p1['price']) / (1 / p1['price'] + 1 / p2['price'])
                        if gap != 0:
                            side = 1 if gap > 0 else 2; ln = q1['point'] if side == 1 else q2['point']; price = q1['price'] if side == 1 else q2['price']
                            H[f'{mk} | A line gap {abs(gap):g}' if abs(gap) < 1.5 else f'{mk} | A line gap 1.5+'].append((res(side, ln), price, NICE[book]))
                        else:
                            for side, q, f in ((1, q1, fair1), (2, q2, 1 - fair1)):
                                ev = f * q['price'] - 1
                                if ev >= 0.02: H[f'{mk} | B price gap EV {"2-4%" if ev < 0.04 else "4%+"}'].append((res(side, q['point']), q['price'], NICE[book]))
                    else:
                        if mk == 'team_totals':
                            pts = hs if g == d['home'] else as_ if g == d['away'] else None
                        else: pts = sum(h1)
                        if pts is None: continue
                        def res(over, ln): return 0.5 if pts == ln else 1 if (pts > ln) == over else 0
                        gap = q1['point'] - p1['point']           # book line minus Pinnacle line (Over outcome)
                        fo = (1 / p1['price']) / (1 / p1['price'] + 1 / p2['price'])
                        if gap != 0:
                            over = gap < 0           # book lower than Pinnacle -> over at the book
                            H[f'{mk} | A line gap {abs(gap):g}' if abs(gap) < 1.5 else f'{mk} | A line gap 1.5+'].append((res(over, q1['point']), q1['price'] if over else q2['price'], NICE[book]))
                        else:
                            for over, q, f in ((True, q1, fo), (False, q2, 1 - fo)):
                                ev = f * q['price'] - 1
                                if ev >= 0.02: H[f'{mk} | B price gap EV {"2-4%" if ev < 0.04 else "4%+"}'].append((res(over, q['point']), q['price'], NICE[book]))
    R = {}
    for k in sorted(H):
        L = H[k]; w = sum(1 for x in L if x[0] == 1); l = sum(1 for x in L if x[0] == 0)
        pl = sum((p - 1) if r == 1 else -1 if r == 0 else 0 for r, p, _ in L)
        bk = collections.defaultdict(lambda: [0, 0, 0.0])
        for r, p, b in L:
            x = bk[b]; x[0] += r == 1; x[1] += r == 0; x[2] += (p - 1) if r == 1 else -1 if r == 0 else 0
        R[k] = dict(w=w, l=l, roi=round(100 * pl / max(1, w + l), 1), books={b: f'{a}-{c} {100 * u / max(1, a + c):+.1f}%' for b, (a, c, u) in sorted(bk.items(), key=lambda x: -(x[1][0] + x[1][1]))})
        print(f"{k:42s} {w}-{l}  {R[k]['roi']:+.1f}%   " + ' | '.join(f'{b} {v}' for b, v in list(R[k]['books'].items())[:5]))
    json.dump(R, open(os.path.join(ROOT, 'data', 'research', f'deriv_soft_{sp}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
