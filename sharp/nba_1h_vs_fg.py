#!/usr/bin/env python3
"""How does the NBA 1H under system (nba_1h_under_hot_over, Bet Labs screen 1784158) line up with the full-game under on the same games?
(Sean, 11/2). Picks from 2024-25 on are copied from the screen's Past System Picks (data/research/nba_1h_under_picks_2024on.txt:
date, home, visitor, 1H line, 1H result). The full-game result comes from Polymarket's settled NBA totals: for each game, the main line =
the total market whose two-sided price at the start is closest to 50/50, graded at that line. Baseline: every other NBA game in the same
months on the same rule. Usage: python3 sharp/nba_1h_vs_fg.py"""
import os, sys, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V
from sharp.sharp_accounts2 import Px
PK = os.path.join(ROOT, 'data', 'research', 'nba_1h_under_picks_2024on.txt')


def main():
    picks = []
    for x in open(PK).read().strip().split(';'):
        d, h, v, line, res = x.split(','); m, dd, y = d.split('/')
        picks.append(dict(date=dt.date(2000 + int(y), int(m), int(dd)), home=h, vis=v, line1h=float(line), res1h=res))
    games = collections.defaultdict(list)
    for c, st in V.poly_markets():
        if c['tag'] != 'nba' or c['market'] != 'total' or c['line'] is None: continue
        games[(c['event'], c['title'])].append((c, st))
    main_line = {}
    for k, L in games.items():
        best = None
        for c, st in L:
            T = V.poly_trades(c, st)
            if len(T) < 5: continue
            cl = Px([t[:4] for t in T]).at(st)
            if cl is None: continue
            p_over = cl if c['outcomes'][0] == 'Over' else 1 - cl
            if best is None or abs(p_over - 0.5) < abs(best[1] - 0.5): best = (c, p_over)
        if best and abs(best[1] - 0.5) < 0.1:
            c = best[0]; main_line[k] = dict(date=dt.date.fromisoformat(c['event'][-10:]), title=c['title'].lower(), line=c['line'], under=c['winner'] == 'Under', month=c['event'][-10:-3])
    rows = []; used = set()
    for p in picks:
        for k, g in main_line.items():
            if abs((g['date'] - p['date']).days) <= 1 and p['home'].lower() in g['title'] and p['vis'].lower() in g['title']:
                rows.append(dict(p, fg_line=g['line'], fg_under=g['under'])); used.add(k); break
    out = dict(picks=len(picks), matched=len(rows))
    W = lambda L: (sum(L), len(L) - sum(L))
    h1 = [r['res1h'] == 'W' for r in rows]; fg = [r['fg_under'] for r in rows]
    out['1h_under'] = W(h1); out['fg_under'] = W(fg)
    both = collections.Counter((a, b) for a, b in zip(h1, fg)); out['cross'] = {f"1H {'W' if a else 'L'} / FG {'under' if b else 'over'}": n for (a, b), n in both.items()}
    # baseline: every other matched game in the same months
    months = {r['date'].strftime('%Y-%m') for r in rows}
    base = [g['under'] for k, g in main_line.items() if k not in used and g['month'] in months]
    out['baseline_fg_under_same_months'] = W(base)
    n = len(h1); a = sum(h1) / n; b = sum(fg) / n; ab = sum(x and y for x, y in zip(h1, fg)) / n
    out['phi'] = round((ab - a * b) / math.sqrt(a * (1 - a) * b * (1 - b)), 2) if 0 < a < 1 and 0 < b < 1 else None
    json.dump(dict(out, rows=[dict(r, date=str(r['date'])) for r in rows]), open(os.path.join(ROOT, 'data', 'research', 'nba_1h_vs_fg.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
