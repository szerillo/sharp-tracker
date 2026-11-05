#!/usr/bin/env python3
"""Tennis form, four-plus seasons of tour-level closes (Sean, 11/5): does the hot / cold signal carry when the player stays on the same
surface vs moves to a new one, across the off-season, and with or without rest?

Prices: every Odds API tennis snapshot in data/oddsapi.sqlite (Masters / 500s / slams, 2022 to now), the last one before each match.
Matches and features: Tennis Abstract (results through June 2026; winner taken from TA, so the odds rows need no other result source),
ESPN results for later 2026 matches. Every feature is computed BEFORE the match from the player's own history:
  form10      last-10 win rate, any surface (the live rule's input)
  form10s     last-10 win rate on THIS surface (needs 5+), and how many of the last 10 were on this surface
  switch      the player's previous event was on another surface
  season      first event of the calendar year (the off-season transition), or the first event after 28+ days away
  rest        days since the player's previous event started (tourney dates; within an event = 'in event')
Cuts, each on the market favourite's side with the Pinnacle no-vig close: hot favourite (form gap 30%+) split by surface continuity,
by same-surface form, by season transition, by rest; and the hot dog the same way. Edge = win rate - no-vig price; ROI flat at Pinnacle.
Writes data/research/tennis_form.json. Usage: python3 sharp/tennis_form.py"""
import os, sys, json, math, sqlite3, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.tennis_ta as T
import sharp.tennis_ta2 as T2
import sharp.tennis_edge as TE
OUT = os.path.join(ROOT, 'data', 'research', 'tennis_form.json'); DB = os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite')


def dd(d): return dt.date(d // 10000, d // 100 % 100, d % 100)


def features(M):
    """Per match, per player: form on this surface, share of the last 10 on this surface, previous event's surface, days since the
    previous event, first event of the year."""
    hist = collections.defaultdict(list)            # player -> [(date, surface, won, tid)]
    for m in M:
        for who in ('w', 'l'):
            p = m[who]; H = hist[p]; s = m['surface']
            last10 = H[-10:]
            ss = [x for x in H if x[1] == s][-10:]
            m[f'{who}_f10'] = sum(x[2] for x in last10) / len(last10) if len(last10) >= 8 else None
            m[f'{who}_f10s'] = sum(x[2] for x in ss) / len(ss) if len(ss) >= 5 else None
            m[f'{who}_same_share'] = sum(1 for x in last10 if x[1] == s) / len(last10) if last10 else None
            prev = next((x for x in reversed(H) if x[3] != m.get('tid')), None)
            m[f'{who}_prev_surface'] = prev[1] if prev else None
            m[f'{who}_rest'] = (dd(m['date']) - dd(prev[0])).days if prev else None
            m[f'{who}_in_event'] = bool(H and H[-1][3] == m.get('tid'))
            m[f'{who}_season_first'] = bool(prev) and prev[0] // 10000 < m['date'] // 10000 and not m[f'{who}_in_event']
        for who in ('w', 'l'): hist[m[who]].append((m['date'], m['surface'], who == 'w', m.get('tid')))


def odds_rows():
    """Last Pinnacle snapshot before each match, from the database (tennis), with the best US price."""
    c = sqlite3.connect(DB)
    out = []
    for gid, key, start, home, away, ph, pa, close_h, bh, ba in c.execute(
            "SELECT game_id, key, start, home, away, pin_close_home, pin_close_away, close_h, best_home, best_away FROM games WHERE sport='tennis' AND pin_close_home IS NOT NULL AND close_h <= 16"):
        dec_h = None
        q = c.execute("SELECT ml_home, ml_away FROM quotes WHERE game_id=? AND book='pinnacle' AND ml_home IS NOT NULL ORDER BY t DESC", (gid,)).fetchall()
        # the decimal prices at the close snapshot (the last pre-start Pinnacle quote)
        qq = c.execute("SELECT ml_home, ml_away, t FROM quotes WHERE game_id=? AND book='pinnacle' AND ml_home IS NOT NULL AND t < ? ORDER BY t DESC LIMIT 1", (gid, start)).fetchone()
        if not qq: continue
        out.append(dict(id=gid, key=key, start=start, home=home, away=away, p_home=ph, dec_home=qq[0], dec_away=qq[1], best_home=bh, best_away=ba))
    return out


def join(M, rows):
    """Odds row -> TA match by the two players' keys (either order) and the date window; winner from TA."""
    idx = collections.defaultdict(list)
    for m in M:
        if m['level'] in ('qual_itf', 'futures'): continue
        idx[frozenset((TE.key_ta(m['wn']), TE.key_ta(m['ln'])))].append(m)
    J = []
    for r in rows:
        k = frozenset((TE.key_ta(r['home']), TE.key_ta(r['away'])))
        d = dt.date.fromisoformat(r['start'][:10]); best = None
        for m in idx.get(k, []):
            gap = (d - dd(m['date'])).days
            if -2 <= gap <= 21 and (best is None or gap < best[0]): best = (gap, m)
        if best: J.append((r, best[1]))
    return J


def main():
    M = T.load(); T.elo_run(M); T.serve_profiles(M); T2.annotate(M); features(M)
    rows = odds_rows(); J = join(M, rows)
    print(f"tennis odds rows {len(rows)}, joined to Tennis Abstract {len(J)} ({min(r['start'] for r, m in J)[:10]} to {max(r['start'] for r, m in J)[:10]})")
    R = []
    for r, m in J:
        home_is_w = TE.key_ta(r['home']) == TE.key_ta(m['wn'])
        fav = 'home' if r['p_home'] >= .5 else 'away'; pf = r['p_home'] if fav == 'home' else 1 - r['p_home']
        fav_is_w = (fav == 'home') == home_is_w
        F = 'w_' if fav_is_w else 'l_'; D = 'l_' if fav_is_w else 'w_'
        R.append(dict(year=r['start'][:4], surface=m['surface'], pf=pf, fav_won=fav_is_w,
                      dec_fav=r['dec_home'] if fav == 'home' else r['dec_away'], dec_dog=r['dec_away'] if fav == 'home' else r['dec_home'],
                      **{f'fav_{k}': m.get(F + k) for k in ('f10', 'f10s', 'same_share', 'prev_surface', 'rest', 'in_event', 'season_first', 'layoff', 'switch')},
                      **{f'dog_{k}': m.get(D + k) for k in ('f10', 'f10s', 'same_share', 'prev_surface', 'rest', 'in_event', 'season_first', 'layoff', 'switch')}))
    res = dict(n=len(R), years=dict(collections.Counter(r['year'] for r in R)))

    def cut(name, keyf, side, rows_, min_n=40):
        Tt = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])
        for r in rows_:
            k = keyf(r)
            if k is None: continue
            s = side(r) if callable(side) else side; win = r['fav_won'] if s == 'fav' else not r['fav_won']
            q = r['pf'] if s == 'fav' else 1 - r['pf']; dec = r['dec_fav'] if s == 'fav' else r['dec_dog']
            t = Tt[k]; t[0] += 1; t[1] += win; t[2] += q; t[3] += (dec - 1) if win else -1
        out = {}
        for k, (n, w, q, pnl) in sorted(Tt.items(), key=lambda kv: str(kv[0])):
            if n < min_n: continue
            out[str(k)] = dict(n=n, win=round(w / n, 3), price=round(q / n, 3), edge=round(100 * (w - q) / n, 1), se=round(100 * math.sqrt((q / n) * (1 - q / n) / n), 1), roi=round(100 * pnl / n, 1))
        res[name] = out
    F_ = [r for r in R if r['fav_f10'] is not None and r['dog_f10'] is not None]
    gap = lambda r: r['fav_f10'] - r['dog_f10']
    hotfav = [r for r in F_ if gap(r) >= .3 and .6 <= r['pf'] <= .85]
    hotdog = [r for r in F_ if .1 <= -gap(r) < .3 and .5 <= r['pf'] <= .85]
    cut('0 baseline: form gap, by year (bet the hotter side; fav 60-85% for hot fav)', lambda r: f"{r['year']} {'hot fav' if gap(r) >= .3 and .6 <= r['pf'] <= .85 else 'hot dog' if .1 <= -gap(r) < .3 and .5 <= r['pf'] <= .85 else None}" if (gap(r) >= .3 and .6 <= r['pf'] <= .85) or (.1 <= -gap(r) < .3 and .5 <= r['pf'] <= .85) else None,
        lambda r: 'fav' if gap(r) > 0 else 'dog', F_, min_n=20)
    cut('1a hot favourite (all years)', lambda r: 'hot fav 60-85%', 'fav', hotfav)
    cut('1b hot dog (all years)', lambda r: 'hot dog', 'dog', hotdog)
    # surface continuity: was the favourite's last-10 built on this surface?
    share = lambda x: None if x is None else ('mostly this surface (7+ of 10)' if x >= .7 else 'mixed (4-6 of 10)' if x >= .4 else 'mostly other surfaces (0-3 of 10)')
    cut('2a hot fav by where the form came from (fav last 10 on this surface)', lambda r: share(r['fav_same_share']), 'fav', hotfav)
    cut('2b hot fav: fav previous event on the same surface vs a switch', lambda r: None if r['fav_prev_surface'] is None else ('same surface' if r['fav_prev_surface'] == r['surface'] else 'switched surface'), 'fav', hotfav)
    cut('2c hot fav: is the fav also hotter on THIS surface (same-surface last 10, 5+)?', lambda r: None if r['fav_f10s'] is None or r['dog_f10s'] is None else ('also hotter on this surface by 20%+' if r['fav_f10s'] - r['dog_f10s'] >= .2 else 'not hotter on this surface'), 'fav', hotfav)
    cut('2d same-surface form gap alone (fav 60-85%), bet the hotter side', lambda r: None if r['fav_f10s'] is None or r['dog_f10s'] is None or not .6 <= r['pf'] <= .85 else ('fav hotter on surface 30%+' if r['fav_f10s'] - r['dog_f10s'] >= .3 else 'dog hotter on surface 10-30%' if .1 <= r['dog_f10s'] - r['fav_f10s'] < .3 else None),
        lambda r: 'fav' if r['fav_f10s'] > r['dog_f10s'] else 'dog', F_)
    cut('2e hot dog by where the dog\'s form came from', lambda r: share(r['dog_same_share']), 'dog', hotdog, 25)
    cut('2f hot dog: dog previous event same surface vs switch', lambda r: None if r['dog_prev_surface'] is None else ('same surface' if r['dog_prev_surface'] == r['surface'] else 'switched surface'), 'dog', hotdog, 25)
    # off-season transition
    cut('3a hot fav: first event of the year (off-season) vs in season', lambda r: 'fav first event of the year' if r['fav_season_first'] else 'in season', 'fav', hotfav, 20)
    # rest
    rest = lambda x, ie: 'in event (already played here)' if ie else (None if x is None else 'quick turnaround (next event, under 8 days)' if x < 8 else '8-27 days' if x < 28 else '28+ days (layoff)')
    cut('4a hot fav by the fav\'s rest', lambda r: rest(r['fav_rest'], r['fav_in_event']), 'fav', hotfav, 25)
    cut('4b hot fav by the dog\'s rest', lambda r: rest(r['dog_rest'], r['dog_in_event']), 'fav', hotfav, 25)
    cut('4c hot dog by the dog\'s rest', lambda r: rest(r['dog_rest'], r['dog_in_event']), 'dog', hotdog, 25)
    cut('4d hot fav x surface continuity x rest', lambda r: None if r['fav_prev_surface'] is None else f"{'same surface' if r['fav_prev_surface'] == r['surface'] else 'switched'} / {'in event or under 8 days' if r['fav_in_event'] or (r['fav_rest'] or 99) < 8 else '8+ days'}", 'fav', hotfav, 25)
    cut('5 by surface (hot fav)', lambda r: r['surface'], 'fav', hotfav, 25)
    json.dump(res, open(OUT, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k in ('n', 'years')}))
    for k, v in res.items():
        if not isinstance(v, dict) or not v or not isinstance(next(iter(v.values())), dict): continue
        print(f"\n== {k}")
        for kk, vv in v.items(): print(f"  {kk:46} n={vv['n']:4} win {vv['win']:.3f} price {vv['price']:.3f} edge {vv['edge']:+5.1f} ±{vv['se']:.1f}  ROI {vv['roi']:+5.1f}")


if __name__ == '__main__':
    main()
