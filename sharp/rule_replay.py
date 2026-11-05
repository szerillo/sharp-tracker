#!/usr/bin/env python3
"""Item 1 (Sean, 11/5): every rule replayed on the odds database and graded on RESULTS at Pinnacle's closing price, season by season.
Not CLV: did the bet win, and what did it return flat at the close (and at the best US book). The replay uses only what the rule used
at the time: season records and over rates rebuilt from scores and closing totals in the database itself, the opener and the close
from the snapshots, days off from the schedule.

Replayable here (odds + results): nhl_pl_fav_gap, nhl_pl_fav_strong_opp, nhl_pl_dog_bigml, nhl_early_home_fav_qual,
nba_under_good_home_over, cbb_under_good_over_drop, cfb_road_dog_low_total (without the conference flag), cfb_road_streak_dog, and the
full-game cousin of nba_1h_under_hot_over (the 1H line is not in the data). Not replayable: the wind rules (weather), the 1H NFL rules
(1H lines), cbb_bigloss_vs_top5 (AP rankings), the exchange rules (exchange tape).
Writes data/research/rule_replay.json. Usage: python3 sharp/rule_replay.py"""
import os, sys, json, sqlite3, collections, datetime as dt, zoneinfo
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
DB = os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'); OUT = os.path.join(ROOT, 'data', 'research', 'rule_replay.json')
ET = zoneinfo.ZoneInfo('America/New_York')


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def season_of(sport, d):
    y = d.year
    if sport in ('nba', 'nhl', 'cbb'): return f"{y}-{str(y + 1)[2:]}" if d.month >= 8 else f"{y - 1}-{str(y)[2:]}"
    return str(y)


def load(sport):
    c = sqlite3.connect(DB)
    G = []
    for row in c.execute("""SELECT g.game_id, g.start, g.home, g.away, g.open_t, g.close_t, g.close_h, g.pin_open_home, g.pin_close_home, g.pin_open_sp, g.pin_close_sp, g.pin_open_tot, g.pin_close_tot,
                                   r.home_score, r.away_score, g.best_home, g.best_away FROM games g LEFT JOIN results r ON r.game_id=g.game_id WHERE g.sport=? ORDER BY g.start""", (sport,)):
        gid, start, home, away, ot, ct, ch, poh, pch, posp, pcsp, pot, pct_, hs, as_, bh, ba = row
        g = dict(id=gid, start=ts(start), home=home, away=away, close_h=ch, p_open=poh, p_close=pch, sp_open=posp, sp_close=pcsp, tot_open=pot, tot_close=pct_, hs=hs, as_=as_, best_home=bh, best_away=ba)
        q = c.execute("SELECT ml_home, ml_away, sp_line, sp_home, sp_away, tot_line, tot_over, tot_under FROM quotes WHERE game_id=? AND book='pinnacle' AND t=?", (gid, ct)).fetchone()
        if q: g.update(ml_home=q[0], ml_away=q[1], sp_home_dec=q[3], sp_away_dec=q[4], over_dec=q[6], under_dec=q[7])
        q0 = c.execute("SELECT ml_home, ml_away FROM quotes WHERE game_id=? AND book='pinnacle' AND t=?", (gid, ot)).fetchone()
        if q0: g.update(ml_home_open=q0[0], ml_away_open=q0[1])
        G.append(g)
    return G


def profiles(G):
    """Before each game: each team's games played, wins, over rate (vs the closing total), last start; and the away team's road streak."""
    H = collections.defaultdict(list)
    for g in G:
        for side, team in (('home', g['home']), ('away', g['away'])):
            L = H[team]; n = len(L)
            g[f'{side}_games'] = n; g[f'{side}_wins'] = sum(x['won'] for x in L); g[f'{side}_win_pct'] = int(100 * sum(x['won'] for x in L) / n) if n else None
            ov = [x['over'] for x in L if x['over'] is not None]
            g[f'{side}_over_pct'] = sum(ov) / len(ov) if ov else None; g[f'{side}_over_n'] = len(ov)
            g[f'{side}_last'] = L[-1]['start'] if L else None
            k = 0
            for x in reversed(L):
                if x['side'] == 'away': k += 1
                else: break
            g[f'{side}_road_streak'] = k
        if g['hs'] is None: continue
        tot = g['hs'] + g['as_']; over = (tot > g['tot_close']) if g['tot_close'] is not None and tot != g['tot_close'] else None
        H[g['home']].append(dict(start=g['start'], won=g['hs'] > g['as_'], over=over, side='home'))
        H[g['away']].append(dict(start=g['start'], won=g['as_'] > g['hs'], over=over, side='away'))


def grade(g, market, side, line=None):
    """-> (won: 1/0/0.5, decimal at Pinnacle close, decimal at the best US book or None)"""
    if g['hs'] is None: return None
    if market == 'ml':
        dec = g.get('ml_home') if side == 'home' else g.get('ml_away'); best = g.get('best_home') if side == 'home' else g.get('best_away')
        if not dec: return None
        won = 1 if (g['hs'] > g['as_']) == (side == 'home') else 0
        return won, dec, best
    if market == 'spread':
        if g.get('sp_close') is None: return None
        ln = line if line is not None else (g['sp_close'] if side == 'home' else -g['sp_close'])
        dec = g.get('sp_home_dec') if side == 'home' else g.get('sp_away_dec')
        if line is not None and abs(abs(line) - abs(g['sp_close'])) > 1e-9: dec = 1.91     # puck line at -1.5/+1.5 is Pinnacle's main NHL spread; price taken as quoted, else standard
        if not dec: return None
        m = ((g['hs'] - g['as_']) if side == 'home' else (g['as_'] - g['hs'])) + ln
        return (1 if m > 0 else 0 if m < 0 else 0.5), dec, None
    if market == 'total':
        if g.get('tot_close') is None: return None
        dec = g.get('over_dec') if side == 'over' else g.get('under_dec')
        if not dec: return None
        tot = g['hs'] + g['as_']
        return (0.5 if tot == g['tot_close'] else 1 if (tot > g['tot_close']) == (side == 'over') else 0), dec, None


def main():
    R = {}
    def rec(name, sport, hits):
        by = collections.defaultdict(lambda: dict(n=0, w=0, l=0, p=0, pnl=0.0, pnl_best=0.0, n_best=0))
        for g, gr in hits:
            won, dec, best = gr; s = by[season_of(sport, g['start'])]; a = by['all']
            for t in (s, a):
                t['n'] += 1; t['w'] += won == 1; t['l'] += won == 0; t['p'] += won == 0.5
                t['pnl'] += (dec - 1) if won == 1 else -1 if won == 0 else 0
                if best: t['pnl_best'] += (best - 1) if won == 1 else -1 if won == 0 else 0; t['n_best'] += 1
        R[name] = {k: dict(n=v['n'], record=f"{v['w']}-{v['l']}" + (f"-{v['p']}" if v['p'] else ''), roi_pinnacle=round(100 * v['pnl'] / v['n'], 1), roi_best_us=round(100 * v['pnl_best'] / v['n_best'], 1) if v['n_best'] else None) for k, v in sorted(by.items())}
    days_off = lambda g, side: (g['start'].astimezone(ET).date() - g[f'{side}_last'].astimezone(ET).date()).days if g.get(f'{side}_last') else None
    # ---- NHL
    G = load('nhl'); profiles(G); G = [g for g in G if g['p_close'] is not None and g['close_h'] is not None and g['close_h'] <= 6]
    hits = collections.defaultdict(list)
    for g in G:
        if g['hs'] is None or g['home_games'] < 1 or g['away_games'] < 1: continue
        fav = 'home' if g['p_close'] >= .5 else 'away'; dog = 'away' if fav == 'home' else 'home'
        wf, wd = g[f'{fav}_win_pct'], g[f'{dog}_win_pct']
        if wd - wf >= 22:
            gr = grade(g, 'spread', fav, -1.5)
            if gr: hits['nhl_pl_fav_gap (fav -1.5, opponent win% higher by 22+)'].append((g, gr))
        if wd >= 66:
            gr = grade(g, 'spread', fav, -1.5)
            if gr: hits['nhl_pl_fav_strong_opp (fav -1.5, opponent wins 66%+)'].append((g, gr))
        dog_open = g.get('ml_away_open') if dog == 'away' else g.get('ml_home_open')
        if dog_open and 181 <= (dog_open - 1) * 100 <= 196:
            gr = grade(g, 'spread', dog, 1.5)
            if gr: hits['nhl_pl_dog_bigml (dog +1.5 when it opened +181 to +196)'].append((g, gr))
        if fav == 'home' and g['home_games'] + 1 <= 24 and wd >= 51:
            gr = grade(g, 'ml', 'home')
            if gr: hits['nhl_early_home_fav_qual (home fav ML, game 24 or earlier, opponent 51%+)'].append((g, gr))
    for k, v in hits.items(): rec(k, 'nhl', v)
    # ---- NBA
    G = load('nba'); profiles(G); G = [g for g in G if g['close_h'] is not None and g['close_h'] <= 6]
    hits = collections.defaultdict(list)
    for g in G:
        if g['hs'] is None: continue
        ho, ao = days_off(g, 'home'), days_off(g, 'away')
        if g['home_over_n'] >= 1 and int(100 * (g['home_over_pct'] or 0)) >= 58 and ho is not None and ao is not None and 1 <= ho <= 2 and 1 <= ao <= 3 and g['tot_open'] is not None and g['tot_close'] is not None and g['tot_open'] - g['tot_close'] >= 0.5:
            gr = grade(g, 'total', 'under')
            if gr: hits['nba_under_good_home_over (home over 58%+, rest 1-2 / 1-3, total down 0.5+)'].append((g, gr))
        if g['away_over_n'] >= 1 and int(100 * (g['away_over_pct'] or 0)) >= 71:
            gr = grade(g, 'total', 'under')
            if gr: hits['nba_1h_under_hot_over, FULL-GAME cousin (visitor over 71%+: under)'].append((g, gr))
        # the same without the drop condition, and with a rise (what the drop adds)
        if g['home_over_n'] >= 1 and int(100 * (g['home_over_pct'] or 0)) >= 58 and ho is not None and ao is not None and 1 <= ho <= 2 and 1 <= ao <= 3 and g['tot_open'] is not None and g['tot_close'] is not None and g['tot_open'] - g['tot_close'] < 0.5:
            gr = grade(g, 'total', 'under')
            if gr: hits['nba under, same spot but the total did NOT drop (control)'].append((g, gr))
    for k, v in hits.items(): rec(k, 'nba', v)
    # ---- CBB
    G = load('cbb'); profiles(G); G = [g for g in G if g['close_h'] is not None and g['close_h'] <= 6]
    hits = collections.defaultdict(list)
    for g in G:
        if g['hs'] is None or g['start'].astimezone(ET).weekday() > 4: continue
        if g['home_over_n'] >= 3 and g['away_over_n'] >= 3 and g['home_over_pct'] >= .5 and g['away_over_pct'] >= .59 and g['tot_open'] is not None and g['tot_close'] is not None:
            gr = grade(g, 'total', 'under')
            if gr: hits['cbb_under_good_over_drop (weekday, home over 50%+, visitor 59%+, total down 0.5+)' if g['tot_open'] - g['tot_close'] >= 0.5 else 'cbb under, same teams but no drop (control)'].append((g, gr))
    for k, v in hits.items(): rec(k, 'cbb', v)
    # ---- CFB
    G = load('cfb'); profiles(G); G = [g for g in G if g['close_h'] is not None and g['close_h'] <= 8]
    hits = collections.defaultdict(list)
    for g in G:
        if g['hs'] is None or g['sp_close'] is None or g['tot_close'] is None: continue
        if g['sp_close'] <= -7 and g['tot_close'] <= 48:
            gr = grade(g, 'spread', 'away')
            if gr: hits['cfb_road_dog_low_total (home -7 or more, total 48 or under: road dog; conference flag unavailable)'].append((g, gr))
        if g['sp_close'] < 0 and g['tot_close'] <= 54 and 2 <= g['away_road_streak'] + 1 <= 5 and g['away_games'] >= 1:
            gr = grade(g, 'spread', 'away')
            if gr: hits['cfb_road_streak_dog (home fav, total 54 or under, visitor on road game 2-5 in a row)'].append((g, gr))
    for k, v in hits.items(): rec(k, 'cfb', v)
    json.dump(R, open(OUT, 'w'), indent=1)
    for k, v in R.items():
        print(f"\n== {k}")
        for s, x in v.items(): print(f"  {s:8} n={x['n']:5} {x['record']:12} ROI Pinnacle {x['roi_pinnacle']:+6.1f}" + (f"  best US {x['roi_best_us']:+6.1f}" if x['roi_best_us'] is not None else ''))


if __name__ == '__main__':
    main()
