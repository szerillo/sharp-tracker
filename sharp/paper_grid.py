#!/usr/bin/env python3
"""Paper-rule recheck (Sean, 11/6: "wondering if any paper need to move up"). Every mined paper angle replayed on the odds database at
Pinnacle's close with the LIVE filter from sharp/systems.py, by season, plus a grid of neighbouring thresholds and the baseline (the
same bet on every game). A rule earns a tier only if it is positive every season (B) or all but one (C), its neighbours hold up, and
there is a reason behind it. Writes data/research/paper_grid.json. Usage: python3 sharp/paper_grid.py"""
import os, sys, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp import rule_replay as RR
from sharp.angle_miner import profiles
from sharp.rule_replay import season_of, ET

CACHE = {}


def games(sport):
    if sport not in CACHE:
        G = RR.load(sport); profiles(G, sport)
        CACHE[sport] = [g for g in G if g['hs'] is not None and g.get('close_h') is not None and g['close_h'] <= 6]
    return CACHE[sport]


def rec(L, sport, market, side):
    by = collections.defaultdict(lambda: [0, 0, 0.0])
    for g in L:
        gr = RR.grade(g, market, side)
        if not gr: continue
        won, dec = gr[0], gr[1]
        for s in (season_of(sport, g['start']), 'all'):
            x = by[s]; x[0] += won == 1; x[1] += won == 0; x[2] += (dec - 1) if won == 1 else -1 if won == 0 else 0
    out = {s: dict(w=v[0], l=v[1], roi=round(100 * v[2] / max(1, v[0] + v[1]), 1)) for s, v in by.items()}
    a = out.get('all', dict(w=0, l=0, roi=0))
    seas = {s: v for s, v in out.items() if s != 'all'}
    a['pos'] = sum(1 for v in seas.values() if v['roi'] > 0 and v['w'] + v['l'] >= 10); a['nseas'] = sum(1 for v in seas.values() if v['w'] + v['l'] >= 10)
    return a, seas


def fmt(a): return f"{a['w']}-{a['l']} {a['roi']:+.1f}% ({a['pos']}/{a['nseas']} seasons)"


RULES = {}
def rule(name, sport, market, side, grid):
    RULES[name] = (sport, market, side, grid)


# ---- NBA
def ats_hot_home(min_ats=.60, min_n=8, rest=2):
    return lambda g: g['home_p']['games'] >= 3 and g['away_p']['games'] >= 3 and g['home_p'].get('ats_pct') is not None and g['home_p']['games'] >= min_n and g['home_p']['ats_pct'] >= min_ats and g['home_p'].get('rest') == rest
rule('nba_ats_hot_home', 'nba', 'spread', 'home', {'ATS 60%+, 8+ games, rest 2 (live)': ats_hot_home(), 'ATS 55%+': ats_hot_home(.55), 'ATS 65%+': ats_hot_home(.65), '5+ games': ats_hot_home(min_n=5), '12+ games': ats_hot_home(min_n=12), 'rest 1': ats_hot_home(rest=1), 'rest 3': ats_hot_home(rest=3), 'ATS 60%+, any rest': lambda g: g['home_p']['games'] >= 8 and (g['home_p'].get('ats_pct') or 0) >= .6, 'every home spread, rest 2': lambda g: g['home_p'].get('rest') == 2})

def badteams(lo=-7, hi=-2, home_max=.40):
    return lambda g: g['home_p']['games'] >= 3 and g['away_p']['games'] >= 3 and g['away_p'].get('margin') is not None and lo <= g['away_p']['margin'] < hi and g['home_p'].get('split_pct') is not None and g['home_p']['split_pct'] < home_max
rule('nba_badteams_under', 'nba', 'total', 'under', {'visitor margin -7 to -2, home wins <40% at home (live)': badteams(), 'visitor -9 to -2': badteams(-9), 'visitor -7 to 0': badteams(hi=0), 'visitor -5 to -2': badteams(-5), 'home <35%': badteams(home_max=.35), 'home <45%': badteams(home_max=.45), 'home <50%': badteams(home_max=.5), 'visitor -7 to -2, any home': lambda g: g['away_p']['games'] >= 3 and g['away_p'].get('margin') is not None and -7 <= g['away_p']['margin'] < -2, 'every under': lambda g: True})

def bigfav(p=.85):
    return lambda g: g['p_close'] is not None and max(g['p_close'], 1 - g['p_close']) >= p
rule('nba_bigfav_over', 'nba', 'total', 'over', {'favourite 85%+ (live)': bigfav(), '80%+': bigfav(.8), '82.5%+': bigfav(.825), '87.5%+': bigfav(.875), '90%+': bigfav(.9), 'home fav 85%+': lambda g: g['p_close'] is not None and g['p_close'] >= .85, 'road fav 85%+': lambda g: g['p_close'] is not None and g['p_close'] <= .15, 'every over': lambda g: True})

def roadtrip(k=4, need_last=True):
    return lambda g: g['away_p']['games'] >= 3 and g['away_p'].get('road_streak', 0) >= k and (not need_last or (g['away_p'].get('h2h_last') is not None and g['away_p']['h2h_last'] > 0))
rule('nba_roadtrip_over', 'nba', 'total', 'over', {'4th+ road game, won last meeting (live)': roadtrip(), '3rd+ road game': roadtrip(3), '5th+ road game': roadtrip(5), '4th+ road game, any last meeting': roadtrip(need_last=False), 'won last meeting, any road streak': lambda g: g['away_p'].get('h2h_last') is not None and g['away_p']['h2h_last'] > 0, 'every over': lambda g: True})

# ---- NHL
def loss_streak_over(k=3, lo=.40, hi=.60):
    return lambda g: g['home_p']['games'] >= 3 and g['away_p']['games'] >= 3 and g['home_p'].get('loss_streak', 0) >= k and g['home_p'].get('over_pct') is not None and lo <= g['home_p']['over_pct'] < hi
rule('nhl_loss_streak_over', 'nhl', 'total', 'over', {'home lost 3+, over rate 40-60% (live)': loss_streak_over(), 'lost 2+': loss_streak_over(2), 'lost 4+': loss_streak_over(4), 'over rate 35-65%': loss_streak_over(lo=.35, hi=.65), 'over rate 45-55%': loss_streak_over(lo=.45, hi=.55), 'lost 3+, any over rate': loss_streak_over(lo=0, hi=1.01), 'every over': lambda g: True})

def skid_fade(k=3, need_win=True):
    return lambda g: g['home_p']['games'] >= 3 and g['away_p']['games'] >= 3 and g['home_p'].get('loss_streak', 0) >= k and (not need_win or (g['away_p'].get('last_margin') is not None and g['away_p']['last_margin'] > 0))
rule('nhl_skid_fade_road', 'nhl', 'spread', 'away', {'home lost 3+, visitor off a win: road puck line (live)': skid_fade(), 'home lost 2+': skid_fade(2), 'home lost 4+': skid_fade(4), 'home lost 3+, visitor any': skid_fade(need_win=False), 'visitor off a win, any home': lambda g: g['away_p']['games'] >= 3 and g['away_p'].get('last_margin') is not None and g['away_p']['last_margin'] > 0, 'every road puck line': lambda g: True})

def bounce_home(m=-3, lo=.50, hi=.65, min_n=8):
    return lambda g: g['home_p']['games'] >= min_n and g['home_p'].get('last_margin') is not None and g['home_p']['last_margin'] <= m and g['home_p'].get('win_pct') is not None and lo <= g['home_p']['win_pct'] < hi
rule('nhl_bounce_home_ml (tier C)', 'nhl', 'ml', 'home', {'lost by 3+, record 50-64%, 8+ games (live)': bounce_home(), 'lost by 2+': bounce_home(-2), 'lost by 4+': bounce_home(-4), 'record 45-70%': bounce_home(lo=.45, hi=.70), 'record 55-64%': bounce_home(lo=.55), 'record 50-75%': bounce_home(hi=.75), 'lost by 3+, any record': bounce_home(lo=0, hi=1.01), 'every home ML': lambda g: True})

# ---- CFB
def day_over(h0=14, h1=19, lo=45, hi=51.5):
    def f(g):
        h = g['start'].astimezone(ET).hour
        return h0 <= h < h1 and g['tot_close'] is not None and lo <= g['tot_close'] <= hi and not g.get('neutral')
    return f
rule('cfb_day_over', 'cfb', 'total', 'over', {'2-7pm ET kickoff, total 45-51.5 (paper)': day_over(), 'noon-7pm': day_over(12), '2-7pm, total 42-54.5': day_over(lo=42, hi=54.5), '2-7pm, total 48-51.5': day_over(lo=48), '2-7pm, total 45-48.5': day_over(hi=48.5), '2-7pm, any total': day_over(lo=0, hi=999), 'any time, total 45-51.5': day_over(0, 24), 'every over': lambda g: True})

def road_streak_dog(k0=2, k1=5, tmax=54):
    return lambda g: g['sp_close'] is not None and g['sp_close'] < 0 and g['tot_close'] is not None and g['tot_close'] <= tmax and k0 <= (g['away_p'].get('road_streak') or 0) + 1 <= k1 and bool(g.get('conf'))
rule('cfb_road_streak_dog', 'cfb', 'spread', 'away', {'conference road dog, road game 2-5, total <= 54 (paper)': road_streak_dog(), 'road game 2-3': road_streak_dog(2, 3), 'road game 3-5': road_streak_dog(3, 5), 'total <= 48': road_streak_dog(tmax=48), 'any total': road_streak_dog(tmax=999), 'every conference road dog': lambda g: g['sp_close'] is not None and g['sp_close'] < 0 and bool(g.get('conf'))})

# ---- NFL
def home_dog(lo=7.5, hi=10, home=True):
    return lambda g: g['sp_close'] is not None and (lo <= g['sp_close'] <= hi if home else lo <= -g['sp_close'] <= hi)
rule('nfl_road_dog_7510', 'nfl', 'spread', 'away', {'road dog +7.5 to +10 (paper)': home_dog(home=False), 'road dog +7 to +10.5': home_dog(7, 10.5, False), 'road dog +6.5 to +9.5': home_dog(6.5, 9.5, False), 'road dog +10.5 to +14': home_dog(10.5, 14, False), 'every road dog': lambda g: g['sp_close'] is not None and g['sp_close'] < 0})
rule('nfl_home_dog_7510 (tier B)', 'nfl', 'spread', 'home', {'home dog +7.5 to +10 (live)': home_dog(), 'home dog +7 to +10.5': home_dog(7, 10.5), 'home dog +6.5 to +9.5': home_dog(6.5, 9.5), 'home dog +6 to +12': home_dog(6, 12), 'home dog +10.5 to +14': home_dog(10.5, 14), 'every home dog': lambda g: g['sp_close'] is not None and g['sp_close'] > 0})

# awfuldog is covered by sharp/threshold_grid.py (ESPN-schedule season margins); the miner's profiles only see games in the odds database


def main():
    out = {}
    for name, (sport, market, side, grid) in RULES.items():
        G = games(sport)
        print(f'\n== {name}  [{sport} {market} {side}]')
        R = {}
        for lab, f in grid.items():
            L = [g for g in G if g['sp_close'] is not None and f(g)] if market in ('spread',) else [g for g in G if f(g)]
            if market == 'spread' and side == 'dog':
                by = collections.defaultdict(lambda: [0, 0, 0.0])
                for g in L:
                    gr = RR.grade(g, 'spread', dog_side(g))
                    if not gr: continue
                    won, dec = gr[0], gr[1]
                    for s in (season_of(sport, g['start']), 'all'):
                        x = by[s]; x[0] += won == 1; x[1] += won == 0; x[2] += (dec - 1) if won == 1 else -1 if won == 0 else 0
                allr = {s: dict(w=v[0], l=v[1], roi=round(100 * v[2] / max(1, v[0] + v[1]), 1)) for s, v in by.items()}
                a = allr.pop('all', dict(w=0, l=0, roi=0)); seas = allr
                a['pos'] = sum(1 for v in seas.values() if v['roi'] > 0 and v['w'] + v['l'] >= 10); a['nseas'] = sum(1 for v in seas.values() if v['w'] + v['l'] >= 10)
            else:
                a, seas = rec(L, sport, market, side)
            R[lab] = dict(all=a, seasons=dict(sorted(seas.items())))
            print(f"  {lab:58s} {fmt(a):34s} " + ' '.join(f"{s[-2:] if '-' in s else s[2:]}:{v['roi']:+.0f}" for s, v in sorted(seas.items()) if v['w'] + v['l'] >= 10))
        out[name] = dict(sport=sport, market=market, side=side, grid=R)
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'paper_grid.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
