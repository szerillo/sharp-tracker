#!/usr/bin/env python3
"""Tennis market tests on the Odds API history (2022-26 tour + slams; Sean, 11/5: "keep testing everything else"). Results from Tennis Abstract
(tennis_form.join). Graded flat at the Pinnacle close; CLV shown, not scored.
  T1 favourite / dog by Pinnacle band (is any band mispriced?)          T2 open->close move: follow / fade, by size
  T3 the US books vs Pinnacle at the close: best US price on each side when it beats Pinnacle's no-vig by 2%+ (the "free" edge)
  T4 the hot favourite (form gap 30%+) split by whether the market moved toward or against them from the open
  T5 settled favourite x move                                             T6 bo5 (slams) vs bo3; by surface; by tour
Writes data/research/tennis_market.json."""
import os, sys, json, sqlite3, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.tennis_ta as T, sharp.tennis_ta2 as T2, sharp.tennis_form as TF, sharp.tennis_edge as TE
DB = TF.DB; OUT = os.path.join(ROOT, 'data', 'research', 'tennis_market.json')
US = ('draftkings', 'fanduel', 'williamhill_us', 'betmgm', 'betrivers', 'espnbet', 'fanatics')


def rows():
    c = sqlite3.connect(DB); out = []
    for gid, key, start, home, away, ph, po, ch, ot, ct in c.execute(
            "SELECT game_id, key, start, home, away, pin_close_home, pin_open_home, close_h, open_t, close_t FROM games WHERE sport='tennis' AND pin_close_home IS NOT NULL AND close_h <= 16"):
        qc = c.execute("SELECT ml_home, ml_away FROM quotes WHERE game_id=? AND book='pinnacle' AND t=?", (gid, ct)).fetchone()
        if not qc or not qc[0] or not qc[1]: continue
        us = {b: (h, a) for b, h, a in c.execute("SELECT book, ml_home, ml_away FROM quotes WHERE game_id=? AND t=? AND book IN (%s)" % ','.join('?' * len(US)), (gid, ct, *US)) if h and a}
        out.append(dict(id=gid, key=key, start=start, home=home, away=away, p_home=ph, p_home_open=po, dec_home=qc[0], dec_away=qc[1], us=us, open_h=(dt.datetime.fromisoformat(start.replace('Z', '+00:00')) - dt.datetime.fromisoformat(ot.replace('Z', '+00:00'))).total_seconds() / 3600))
    return out


def main():
    M = T.load(); T.elo_run(M); T2.annotate(M); TF.features(M)
    R0 = rows(); J = TF.join(M, R0)
    print(f"tennis: {len(R0)} priced matches, {len(J)} joined to results")
    R = []
    for r, m in J:
        home_is_w = TE.key_ta(r['home']) == TE.key_ta(m['wn'])
        fav = 'home' if r['p_home'] >= .5 else 'away'; pf = r['p_home'] if fav == 'home' else 1 - r['p_home']
        po = r['p_home_open']; pf_open = (po if fav == 'home' else 1 - po) if po is not None else None
        fav_won = (fav == 'home') == home_is_w
        F = 'w_' if fav_won else 'l_'; D = 'l_' if fav_won else 'w_'
        dec_f = r['dec_home'] if fav == 'home' else r['dec_away']; dec_d = r['dec_away'] if fav == 'home' else r['dec_home']
        best_f = max([v[0 if fav == 'home' else 1] for v in r['us'].values()] or [None]); best_d = max([v[1 if fav == 'home' else 0] for v in r['us'].values()] or [None])
        R.append(dict(year=r['start'][:4], surface=m['surface'], bo=m['bo'], tour=m['tour'], pf=pf, pf_open=pf_open, move=(pf - pf_open) if pf_open is not None else None, open_h=r['open_h'],
                      fav_won=fav_won, dec_f=dec_f, dec_d=dec_d, best_f=best_f, best_d=best_d,
                      gap=(m.get(F + 'f10') - m.get(D + 'f10')) if m.get(F + 'f10') is not None and m.get(D + 'f10') is not None else None,
                      settled=bool(m.get(F + 'prev_surface') == m['surface'] and (m.get(F + 'same_share') or 0) >= .4 and m.get(F + 'rest') is not None and 8 <= m[F + 'rest'] <= 27 and not m.get(F + 'in_event'))))
    out = {}

    def cut(name, keyf, side, rows_, min_n=40, price=None):
        Tt = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0.0]))
        for r in rows_:
            k = keyf(r)
            if k is None: continue
            s = side(r) if callable(side) else side; win = r['fav_won'] if s == 'fav' else not r['fav_won']
            dec = (price(r, s) if price else (r['dec_f'] if s == 'fav' else r['dec_d']))
            if not dec: continue
            for yk in (r['year'], 'all'):
                t = Tt[k][yk]; t[0] += 1; t[1] += win; t[2] += (dec - 1) if win else -1
        res = {}
        for k, Y in Tt.items():
            a = Y['all']
            if a[0] < min_n: continue
            yrs = [v[2] > 0 for y, v in Y.items() if y != 'all' and v[0] >= 15]
            res[str(k)] = dict(n=a[0], won=a[1], win_pct=round(a[1] / a[0], 3), roi=round(100 * a[2] / a[0], 1), pos_years=f"{sum(yrs)}/{len(yrs)}")
        out[name] = res
        print(f"\n== {name}")
        for k, v in sorted(res.items(), key=lambda kv: kv[0]): print(f"   {k:48} n={v['n']:5} {v['won']}-{v['n'] - v['won']:<5} {v['win_pct']:.3f} ROI {v['roi']:+6.1f}  +yrs {v['pos_years']}")

    band = lambda r: f"{int(r['pf'] * 20) * 5}-{int(r['pf'] * 20) * 5 + 4}%"
    cut('T1 favourite by Pinnacle band', band, 'fav', R)
    cut('T1b dog by Pinnacle band', band, 'dog', R)
    mv = lambda r: None if r['move'] is None or abs(r['move']) < 0.005 else ('toward fav ' + ('small <3%' if abs(r['move']) < .03 else 'medium 3-6%' if abs(r['move']) < .06 else 'large 6%+')) if r['move'] > 0 else ('toward dog ' + ('small <3%' if abs(r['move']) < .03 else 'medium 3-6%' if abs(r['move']) < .06 else 'large 6%+'))
    cut('T2 open->close move: bet the FAVOURITE at the close', mv, 'fav', R)
    cut('T2b open->close move: bet the DOG at the close', mv, 'dog', R)
    cut('T2c no move (open = close): favourite', lambda r: 'flat' if r['move'] is not None and abs(r['move']) < 0.005 else None, 'fav', R)
    # T3: US book beats Pinnacle's no-vig on a side by 2%+ (implied prob at the book below Pinnacle's fair)
    def edge_side(r):
        out_ = []
        if r['best_f'] and 1 / r['best_f'] <= r['pf'] - .01: out_.append('fav')
        if r['best_d'] and 1 / r['best_d'] <= (1 - r['pf']) - .01: out_.append('dog')
        return out_
    E = [dict(r, side=s) for r in R for s in edge_side(r)]
    cut('T3 best US price beats Pinnacle no-vig by 1%+ (rare: 2%+ happens in 0.6% of matches): take it (at the US price)', lambda r: r['side'] + (' (fav 60-85%)' if .6 <= r['pf'] <= .85 else ' (other)'), lambda r: r['side'], E, price=lambda r, s: r['best_f'] if s == 'fav' else r['best_d'])
    cut('T3b same, graded at Pinnacle\'s price (is the side itself good?)', lambda r: r['side'], lambda r: r['side'], E)
    hot = [r for r in R if r['gap'] is not None and r['gap'] >= .3 and .6 <= r['pf'] <= .85]
    cut('T4 hot favourite by the open->close move', lambda r: None if r['move'] is None else 'market moved toward the hot fav' if r['move'] >= .01 else 'moved against' if r['move'] <= -.01 else 'flat', 'fav', hot, 25)
    cut('T4b hot favourite at the OPEN price (bet when first posted)', lambda r: 'hot fav' if r['pf_open'] else None, 'fav', hot, 25, price=lambda r, s: 1 / r['pf_open'] * (1 - .025))
    cut('T5 settled hot favourite by move', lambda r: ('settled' if r['settled'] else 'unsettled') + (' / moved toward' if r['move'] is not None and r['move'] >= .01 else ' / against' if r['move'] is not None and r['move'] <= -.01 else ' / flat'), 'fav', hot, 20)
    cut('T6 favourite by format and tour', lambda r: f"{r['tour']} bo{r['bo']} {r['surface']}", 'fav', R)
    cut('T6b dog by format and tour', lambda r: f"{r['tour']} bo{r['bo']} {r['surface']}", 'dog', R)
    cut('T7 how early the first snapshot was: favourite', lambda r: 'opened 3+ days out' if r['open_h'] >= 72 else 'opened 1-3 days' if r['open_h'] >= 24 else 'opened same day', 'fav', R)
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
