#!/usr/bin/env python3
"""List item 3 (Sean 11/6): what line shopping is worth on our own rules, 2020-26.
Every replay pick (sharp/rule_replay.py and sharp/nfl_replay.py, via sharp/sys_vs_poly.picks) graded at the closing snapshot four ways:
  Pinnacle      - the replays' own grade (Pinnacle's closing number and price)
  one book      - DraftKings alone (the typical single-account bettor)
  best of 4 US  - the best of DraftKings, FanDuel, Caesars, BetRivers: the best number for the side first, then the best price at it
  best of 7     - the same four plus BetOnline, Bovada, LowVig (offshore; context only)
Each bet is graded on the book's own number, so a half point that turns a loss into a push or a win counts. BetMGM is never used.
Writes data/research/line_shop.json. Usage: python3 sharp/line_shop.py"""
import os, sys, json, sqlite3, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.sys_vs_poly as SV, sharp.rule_replay as RR
DB = os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'); OUT = os.path.join(ROOT, 'data', 'research', 'line_shop.json')
US4 = ('draftkings', 'fanduel', 'williamhill_us', 'betrivers'); OFF = ('betonlineag', 'bovada', 'lowvig')


def result(g, mk, side, line):
    hs, as_ = g['hs'], g['as_']
    if mk == 'ml': return 1 if (hs > as_) == (side == 'home') else 0
    if mk == 'spread':
        m = (hs - as_ if side == 'home' else as_ - hs) + line; return 0.5 if m == 0 else 1 if m > 0 else 0
    t = hs + as_; return 0.5 if t == line else 1 if (t > line) == (side == 'over') else 0


def offer(q, mk, side):
    """(line for the side, decimal) from a quotes row (book, ml_home, ml_away, sp_line, sp_home, sp_away, tot_line, tot_over, tot_under)."""
    b, mh, ma, sl, sh, sa, tl, to, tu = q
    if mk == 'ml': d = mh if side == 'home' else ma; return (0, d) if d else None
    if mk == 'spread':
        if sl is None: return None
        d = sh if side == 'home' else sa; return ((sl if side == 'home' else -sl), d) if d else None
    if tl is None: return None
    d = to if side == 'over' else tu; return (tl, d) if d else None


def best(offers, mk, side):
    if not offers: return None
    if mk == 'ml': return max(offers, key=lambda x: x[1])
    key = (lambda x: (x[0], x[1])) if mk == 'spread' or side == 'under' else (lambda x: (-x[0], x[1]))     # more points for a side / under; fewer for an over
    return max(offers, key=key)


def main():
    P = SV.picks(); c = sqlite3.connect(DB)
    print('replay picks:', len(P), flush=True)
    ct = {r[0]: r[1] for r in c.execute("SELECT game_id, close_t FROM games")}
    H = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0.0]))     # rule -> way -> [n, w, l, pl]
    gain = collections.defaultdict(list)
    for i, p in enumerate(P):
        g = p['g']; t = ct.get(g['id'])
        if not t or g.get('hs') is None: continue
        if p['mk'] == 'spread' and p['g']['sport'] == 'nhl': continue          # puck-line rules use a fixed -1.5/+1.5, not the main number
        Q = c.execute("SELECT book, ml_home, ml_away, sp_line, sp_home, sp_away, tot_line, tot_over, tot_under FROM quotes WHERE game_id=? AND t=?", (g['id'], t)).fetchall()
        O = {q[0]: offer(q, p['mk'], p['side']) for q in Q}
        ways = dict(Pinnacle=(None, p['dec'], p['won']))
        dk = O.get('draftkings')
        if dk: ways['one book (DK)'] = (dk[0], dk[1], result(g, p['mk'], p['side'], dk[0]))
        b4 = best([O[b] for b in US4 if O.get(b)], p['mk'], p['side'])
        if b4: ways['best of 4 US'] = (b4[0], b4[1], result(g, p['mk'], p['side'], b4[0]))
        b7 = best([O[b] for b in US4 + OFF if O.get(b)], p['mk'], p['side'])
        if b7: ways['best of 7 (with offshore)'] = (b7[0], b7[1], result(g, p['mk'], p['side'], b7[0]))
        if not (dk and b4): continue           # compare like for like: picks every way can price
        name = p['rule'] if p['live'] else 'generic: ' + p['rule'].split(' | ')[0][:60]
        for way, (ln, d, won) in ways.items():
            for k in (name, 'ALL live rules' if p['live'] else 'ALL generic bets'):
                x = H[k][way]; x[0] += 1; x[1] += won == 1; x[2] += won == 0; x[3] += (d - 1) if won == 1 else -1 if won == 0 else 0
        pl = lambda w: (ways[w][1] - 1) if ways[w][2] == 1 else -1 if ways[w][2] == 0 else 0
        gain['best4 minus DK'].append(pl('best of 4 US') - pl('one book (DK)'))
        gain['best4 minus Pinnacle'].append(pl('best of 4 US') - pl('Pinnacle'))
    R = {}
    for k in sorted(H, key=lambda k: (not k.startswith('ALL'), k)):
        R[k] = {w: dict(n=x[0], record=f'{x[1]}-{x[2]}', roi=round(100 * x[3] / max(1, x[0]), 1)) for w, x in H[k].items()}
        if k.startswith('ALL') or H[k]['Pinnacle'][0] >= 40:
            print(f"\n{k}\n  " + '  |  '.join(f"{w}: {v['record']} {v['roi']:+.1f}%" for w, v in R[k].items()))
    G = {k: dict(n=len(v), mean_units_per_bet=round(sum(v) / len(v), 4)) for k, v in gain.items() if v}
    print('\n', G)
    json.dump(dict(gain=G, rules=R), open(OUT, 'w'), indent=1); print('wrote', OUT)


if __name__ == '__main__':
    main()
