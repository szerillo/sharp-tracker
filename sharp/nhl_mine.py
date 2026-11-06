#!/usr/bin/env python3
"""Item 6, NHL (Sean 11/6): why does the early-season home favourite against a winning opponent pay, and what does overtime do to it?
Odds database 2020-26, Pinnacle close, records rebuilt from the ESPN schedule (rule_replay.profiles). Writes data/research/nhl_mine.json."""
import os, sys, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.rule_replay as RR


def main():
    G = RR.load('nhl'); RR.profiles(G)
    G = [g for g in G if g['hs'] is not None and g.get('ml_home') and g.get('ml_away') and g['p_close'] is not None and g['close_h'] is not None and g['close_h'] <= 6 and g['home_games'] is not None and g['away_games'] is not None]
    H = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, 0, 0])     # n, w, pl, expected wins, ot games, regulation wins
    def add(k, g, side):
        dec = g['ml_home'] if side == 'home' else g['ml_away']; p = g['p_close'] if side == 'home' else 1 - g['p_close']
        won = (g['hs'] > g['as_']) == (side == 'home'); x = H[k]
        x[0] += 1; x[1] += won; x[2] += (dec - 1) if won else -1; x[3] += p; x[4] += bool(g['ot']); x[5] += won and not g['ot']
    for g in G:
        fav = 'home' if g['p_close'] >= .5 else 'away'; dog = 'away' if fav == 'home' else 'home'
        gn = g[f'{fav}_games'] + 1; od = g[f'{dog}_win_pct']
        if od is None: continue
        gb = 'games 1-10' if gn <= 10 else 'games 11-24' if gn <= 24 else 'games 25-50' if gn <= 50 else 'games 51+'
        ob = 'opp under 45%' if od < 45 else 'opp 45-50%' if od < 51 else 'opp 51-60%' if od <= 60 else 'opp 61%+'
        add(f'{fav} fav | {gb} | {ob}', g, fav)
        add(f'{fav} fav | {gb} | all opponents', g, fav)
        add(f'{fav} fav | all | {ob}', g, fav)
        if fav == 'home' and gn <= 24 and od >= 51:
            add(f'RULE home fav, game <=24, opp 51%+ | season {RR.season_of("nhl", g["start"])}', g, fav)
            fw = g['home_win_pct'] or 0
            add(f'RULE | fav own win% {"under 50" if fw < 50 else "50-60" if fw <= 60 else "61+"}', g, fav)
            add(f'RULE | price {"-150 or shorter" if g["ml_home"] <= 1.667 else "-149 to -120" if g["ml_home"] <= 1.833 else "-119 to -100"}', g, fav)
            dg = g[f'{dog}_games']; add(f'RULE | opponent games played {"under 8" if dg < 8 else "8-15" if dg <= 15 else "16+"}', g, fav)
        add(f'ALL favourites | {"OT game" if g["ot"] else "regulation"}', g, fav)
    R = {}
    for k in sorted(H):
        n, w, pl, ew, ot, rw = H[k]
        R[k] = dict(n=n, record=f'{w}-{n - w}', roi=round(100 * pl / n, 1), win=round(100 * w / n, 1), expected=round(100 * ew / n, 1), ot_share=round(100 * ot / n, 1), reg_win=round(100 * rw / n, 1))
        if n >= 40: print(f"{k:62s} n={n:4d} {w}-{n - w} ROI {R[k]['roi']:+6.1f}%  win {R[k]['win']} vs {R[k]['expected']} exp  OT {R[k]['ot_share']}%")
    json.dump(R, open(os.path.join(ROOT, 'data', 'research', 'nhl_mine.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
