#!/usr/bin/env python3
"""Cross-sport market replay on the Odds API history (Sean, 11/5: "keep testing everything else"). The NFL replay found a few things the
market misses (dogs +7.5 to +10, following small total moves, fading rested favourites); this runs the same generic tests on every team
sport in the database so a finding has to show up in more than one place before it becomes a rule. Graded on results at the Pinnacle close
(ROI flat); CLV reported, not scored. Writes data/research/market_replay.json; a compact table to stdout.

Tests per sport:
  M1 dog ATS by closing spread band          M2 home ATS by band            M3 UNDER by closing total quintile
  M4 spread moved open->close: follow / fade (by size)                     M5 total moved open->close: follow / fade (by size)
  M6 moneyline dog by Pinnacle band          M7 rest: side off 3+ days vs 0 days (b2b), ATS and ML
  M8 Pinnacle vs the US books at the close: the side whose spread is better at a US book by 0.5+ (book disagreement)
  M9 season phase: first 15% of the season vs the rest, dog ATS and UNDER
  M10 big favourite ML (85%+) and the dog
"""
import os, sys, json, sqlite3, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.rule_replay import load, profiles, grade, season_of, DB, ET
OUT = os.path.join(ROOT, 'data', 'research', 'market_replay.json')
SPORTS = ['nba', 'nhl', 'cbb', 'cfb', 'nfl', 'mma', 'mlb', 'wnba', 'wncaab', 'euroleague', 'cfl', 'milb', 'ncaa_baseball', 'kbo', 'npb']
CLOSE_H = 6


def us_spreads(sport):
    """game_id -> {book: (sp_line, home_dec, away_dec)} at the close snapshot (US books)."""
    c = sqlite3.connect(DB); out = collections.defaultdict(dict)
    for gid, book, ln, h, a in c.execute("""SELECT q.game_id, q.book, q.sp_line, q.sp_home, q.sp_away FROM quotes q JOIN games g ON g.game_id=q.game_id AND q.t=g.close_t
                                             WHERE g.sport=? AND q.book IN ('draftkings','fanduel','betmgm','williamhill_us','betrivers','espnbet','fanatics') AND q.sp_line IS NOT NULL""", (sport,)):
        out[gid][book] = (ln, h, a)
    return out


def main():
    R = {}
    for sport in SPORTS:
        G = load(sport)
        if not G: continue
        profiles(G)
        G = [g for g in G if g['hs'] is not None and g['close_h'] is not None and g['close_h'] <= CLOSE_H]
        if len(G) < 200: continue
        T = collections.defaultdict(list)
        # season length for the phase test
        seasons = collections.defaultdict(list)
        for g in G: seasons[season_of(sport, g['start'])].append(g['start'])
        phase = {}
        for s, L in seasons.items():
            L.sort(); cut = L[int(0.15 * len(L))]; phase[s] = cut
        US = us_spreads(sport)
        for g in G:
            s = season_of(sport, g['start']); early = g['start'] < phase[s]
            fav_sp = None
            if g.get('sp_close') is not None:
                fav_sp = 'home' if g['sp_close'] < 0 else 'away' if g['sp_close'] > 0 else None
            dog_sp = 'away' if fav_sp == 'home' else 'home' if fav_sp == 'away' else None
            sz = abs(g['sp_close']) if g.get('sp_close') is not None else None
            band = None if sz is None else 'pk-2.5' if sz < 3 else '3' if sz == 3 else '3.5-6.5' if sz < 7 else '7' if sz == 7 else '7.5-10' if sz <= 10 else '10.5-14' if sz <= 14 else '14.5+'
            if dog_sp and band:
                gr = grade(g, 'spread', dog_sp)
                if gr:
                    T[f'M1 dog ATS by spread band | {band}'].append((g, gr))
                    if dog_sp == 'home': T[f'M1b HOME dog ATS by band | {band}'].append((g, gr))
                    else: T[f'M1c ROAD dog ATS by band | {band}'].append((g, gr))
                    if early: T['M9 early season (first 15%): dog ATS'].append((g, gr))
                    else: T['M9b rest of season: dog ATS'].append((g, gr))
            if band:
                gr = grade(g, 'spread', 'home')
                if gr: T[f'M2 home ATS by band | {"home fav" if fav_sp == "home" else "home dog" if fav_sp == "away" else "pick"} {band}'].append((g, gr))
            # totals
            if g.get('tot_close') is not None and sport != 'mma':      # MMA results are win/loss only
                gr = grade(g, 'total', 'under')
                if gr:
                    T['M3 UNDER by closing total | all'].append((g, gr))
                    if early: T['M9c early season: UNDER'].append((g, gr))
                    if g.get('tot_open') is not None:
                        mv = g['tot_close'] - g['tot_open']
                        if mv != 0:
                            size = 'small' if abs(mv) <= 1 else 'medium' if abs(mv) <= 2 else 'large'
                            if mv < 0: T[f'M5 total moved DOWN, follow (UNDER) | {size}'].append((g, gr))
                            else:
                                go = grade(g, 'total', 'over')
                                if go: T[f'M5b total moved UP, follow (OVER) | {size}'].append((g, go))
            # spread moves
            if g.get('sp_open') is not None and g.get('sp_close') is not None and g['sp_open'] != g['sp_close']:
                mv = g['sp_close'] - g['sp_open']          # home number; negative = moved toward the home side
                toward = 'home' if mv < 0 else 'away'; size = 'small (0.5-1)' if abs(mv) <= 1 else 'medium (1.5-2.5)' if abs(mv) <= 2.5 else 'large (3+)'
                gr = grade(g, 'spread', toward)
                if gr: T[f'M4 spread move, FOLLOW | {size}'].append((g, gr))
                gf = grade(g, 'spread', 'away' if toward == 'home' else 'home')
                if gf: T[f'M4b spread move, FADE | {size}'].append((g, gf))
            # moneyline bands
            if g.get('p_close') is not None:
                fav = 'home' if g['p_close'] >= .5 else 'away'; dog = 'away' if fav == 'home' else 'home'; pf = max(g['p_close'], 1 - g['p_close'])
                b = f"{int(pf * 20) * 5}-{int(pf * 20) * 5 + 4}%"
                gd = grade(g, 'ml', dog)
                if gd: T[f'M6 ML dog by favourite band | {b}'].append((g, gd))
                gfv = grade(g, 'ml', fav)
                if gfv and pf >= .85: T['M10 ML favourite 85%+'].append((g, gfv))
                if gd and pf >= .85: T['M10b ML dog vs 85%+ favourite'].append((g, gd))
                # M11 moneyline move open -> close (no-vig points): follow the side the market moved toward / fade it
                if g.get('p_open') is not None:
                    mv = 100 * (g['p_close'] - g['p_open'])
                    if abs(mv) >= 1:
                        toward = 'home' if mv > 0 else 'away'; size = 'small 1-3' if abs(mv) < 3 else 'medium 3-6' if abs(mv) < 6 else 'large 6+'
                        gt = grade(g, 'ml', toward); gf2 = grade(g, 'ml', 'away' if toward == 'home' else 'home')
                        if gt: T[f'M11 ML move, FOLLOW at the close | {size}'].append((g, gt))
                        if gt and size == 'large 6+': T[f"M11d large move FOLLOW at the close, by direction | toward the {'favourite' if (g['p_close'] >= .5) == (toward == 'home') else 'dog'}"].append((g, gt))
                        if gf2: T[f'M11b ML move, FADE at the close | {size}'].append((g, gf2))
                        # and at the OPEN price (what the mover got): bet the side the market will move toward, at its opening price
                        if gt and g.get('ml_home_open') and g.get('ml_away_open'):
                            od = g['ml_home_open'] if toward == 'home' else g['ml_away_open']
                            T[f'M11c side the market moved toward, at its OPENING price | {size}'].append((g, (gt[0], od, None, gt[3], gt[4])))
            # rest
            for side in ('home', 'away'):
                last = g.get(f'{side}_last')
                if not last: continue
                off = (g['start'].astimezone(ET).date() - last.astimezone(ET).date()).days
                other = 'away' if side == 'home' else 'home'; olast = g.get(f'{other}_last')
                ooff = (g['start'].astimezone(ET).date() - olast.astimezone(ET).date()).days if olast else None
                if ooff is None: continue
                tag = 'b2b vs rested (2+ days)' if off == 1 and ooff >= 2 else 'rested (3+) vs b2b' if off >= 3 and ooff == 1 else None
                if not tag: continue
                gm = grade(g, 'ml', side); gs = grade(g, 'spread', side)
                if gm: T[f'M7 rest, ML | {tag}'].append((g, gm))
                if gs: T[f'M7b rest, ATS | {tag}'].append((g, gs))
            # book disagreement at the close
            u = US.get(g['id'])
            if u and g.get('sp_close') is not None:
                for book, (ln, h, a) in u.items():
                    d = ln - g['sp_close']            # home number at the book minus Pinnacle's: positive = home side gets more points at the book
                    if abs(d) >= 0.5:
                        side = 'home' if d > 0 else 'away'
                        dec = h if side == 'home' else a          # the book's own price on that number (an alternate puck line is heavily juiced)
                        gr = grade(g, 'spread', side, line=(ln if side == 'home' else -ln))
                        if gr and dec: T[f'M8 US book gives 0.5+ more than Pinnacle: take it at its price | {book}'].append((g, (gr[0], dec, None, gr[3], gr[4])))
                        # M8c the other way round: the US book lags Pinnacle, so bet the side Pinnacle has moved toward, at Pinnacle's close
                        other = 'away' if side == 'home' else 'home'
                        gp = grade(g, 'spread', other)
                        if gp: T[f'M8c a US book lags Pinnacle by 0.5+: bet the side Pinnacle favours, at Pinnacle | {book}'].append((g, gp))
                if sport != 'mma': pass
        # fold
        S = {}
        for name, hits in T.items():
            by = collections.defaultdict(lambda: dict(n=0, w=0, l=0, p=0, pnl=0.0, clv=[], lm=[]))
            for g, (won, dec, best, clv, lm) in hits:
                for t in (by[season_of(sport, g['start'])], by['all']):
                    t['n'] += 1; t['w'] += won == 1; t['l'] += won == 0; t['p'] += won == 0.5; t['pnl'] += (dec - 1) if won == 1 else -1 if won == 0 else 0
                    if clv is not None: t['clv'].append(clv)
                    if lm is not None: t['lm'].append(lm)
            S[name] = {k: dict(n=v['n'], record=f"{v['w']}-{v['l']}" + (f"-{v['p']}" if v['p'] else ''), win_pct=round(v['w'] / max(1, v['w'] + v['l']), 3), roi=round(100 * v['pnl'] / v['n'], 1),
                               clv=round(sum(v['clv']) / len(v['clv']), 2) if v['clv'] else None) for k, v in sorted(by.items())}
        R[sport] = S
        print(f"\n==== {sport} ({len(G)} graded games)")
        for name in sorted(S):
            a = S[name]['all']
            if a['n'] < 60: continue
            yrs = [v['roi'] > 0 for k, v in S[name].items() if k != 'all' and v['n'] >= 15]
            print(f"  {name[:78]:78} n={a['n']:5} {a['record']:13} {a['win_pct']:.3f} ROI {a['roi']:+6.1f}  +yrs {sum(yrs)}/{len(yrs)}")
    json.dump(R, open(OUT, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
