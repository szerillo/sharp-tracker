#!/usr/bin/env python3
"""Threshold robustness for every replayable Bet Labs rule (11/6).

Each rule is replayed on the odds database at its exact definition, then with each threshold moved one or two notches either way.
Every cell is graded on results at Pinnacle's close, flat 1 unit at Pinnacle's price (rule_replay.grade). A rule whose edge only shows at
its exact numbers and fades at the neighbours is over-fitted; a real edge should survive small changes. Baseline = every game with the
same market and side and the rule's non-threshold filters.

Same method as the nba_under_good_home_over grid (docs/deriv_split_2026-11-06.md). Skipped: weather rules (wind / heat), and
cbb_bigloss_vs_top5 (needs historical AP ranks, not in the data). No network calls.
Writes data/research/threshold_grid.json. Usage: python3 sharp/threshold_grid.py"""
import os, sys, json, bisect, collections, datetime as dt, statistics
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.rule_replay as RR
OUT = os.path.join(ROOT, 'data', 'research', 'threshold_grid.json')
CURRENT = {'nhl': '2026-27', 'cfb': '2026', 'nfl': '2026'}     # season in progress: shown, not counted in "seasons positive"
TIER = {'nhl_pl_fav_gap': 'C', 'nhl_pl_fav_strong_opp': 'C', 'nhl_pl_dog_bigml': 'C', 'nhl_early_home_fav_qual': 'B', 'nhl_bounce_home_ml': 'C',
        'cfb_road_dog_low_total': 'B', 'cfb_homefav_7510_under': 'C', 'nfl_home_dog_7510': 'B', 'awfuldog': 'B'}
try:
    import sharp.systems as S_
    TIER.update({k: v['tier'] for k, v in S_.EVIDENCE.items() if k in TIER and isinstance(v, dict) and v.get('tier')})
except Exception: pass


def season(sport, g):
    if sport in ('nfl', 'cfb'): return RR.season_of(sport, g['start'] - dt.timedelta(days=60))     # January bowls / playoffs belong to the season before
    return RR.season_of(sport, g['start'])


def summarise(sport, hits):
    by = collections.defaultdict(lambda: [0, 0, 0, 0.0])
    for g, gr in hits:
        won, dec = gr[0], gr[1]; pnl = (dec - 1) if won == 1 else -1 if won == 0 else 0
        for k in (season(sport, g), 'all'):
            t = by[k]; t[0] += won == 1; t[1] += won == 0; t[2] += won == 0.5; t[3] += pnl
    def one(t):
        n = t[0] + t[1] + t[2]
        return dict(n=n, record=f"{t[0]}-{t[1]}" + (f"-{t[2]}" if t[2] else ''), roi=round(100 * t[3] / n, 1) if n else None)
    out = {k: one(v) for k, v in sorted(by.items())}
    full = [k for k in out if k not in ('all', CURRENT.get(sport))]
    out.setdefault('all', dict(n=0, record='0-0', roi=None))
    out['seasons_pos'] = sum(1 for k in full if (out[k]['roi'] or 0) > 0); out['seasons_full'] = len(full)
    return out


def run(sport, games, pick, params):
    """pick(g, **params) -> (market, side, line) or None"""
    hits = []
    for g in games:
        p = pick(g, **params)
        if not p: continue
        gr = RR.grade(g, *p)
        if gr: hits.append((g, gr))
    return summarise(sport, hits)


def grid(name, sport, games, pick, axes, exact, baseline_pick, note=''):
    """axes: {param: [values]} (exact value included); every combination is run."""
    keys = list(axes)
    import itertools
    cells = []
    for combo in itertools.product(*[axes[k] for k in keys]):
        P = dict(zip(keys, combo))
        if 'lo' in P and 'hi' in P and P['lo'] > P['hi']: continue
        r = run(sport, games, pick, P)
        dist = max(abs(axes[k].index(P[k]) - axes[k].index(exact[k])) for k in keys)
        cells.append(dict(params=P, dist=dist, **{k: r['all'][k] for k in ('n', 'record', 'roi')}, seasons_pos=r['seasons_pos'], seasons_full=r['seasons_full']))
    ex = run(sport, games, pick, exact); base = run(sport, games, baseline_pick, {})
    nb1 = [c['roi'] for c in cells if c['dist'] == 1 and c['roi'] is not None and c['n'] >= 15]
    nb = [c['roi'] for c in cells if c['dist'] >= 1 and c['roi'] is not None and c['n'] >= 15]
    e, b = ex['all']['roi'], base['all']['roi']
    med1 = statistics.median(nb1) if nb1 else None
    # NO EDGE: the exact definition itself clears neither +2% nor the baseline by 1.5%
    if e is None or e <= max(2.0, b + 1.5): verdict = 'NO EDGE'
    elif med1 is not None and med1 > 0 and med1 >= 0.5 * e and med1 >= b + 2: verdict = 'ROBUST'
    else: verdict = 'FRAGILE'
    full_pos = ex['seasons_pos'] == ex['seasons_full']
    tier = 'paper' if verdict == 'NO EDGE' else 'B' if (verdict == 'ROBUST' and full_pos) else 'C'
    return dict(rule=name, sport=sport, note=note, axes=axes, exact_params=exact, exact=ex, baseline=base['all'], baseline_seasons=f"{base['seasons_pos']} of {base['seasons_full']}",
                cells=cells, neighbour_1notch_median=round(med1, 1) if med1 is not None else None, neighbour_1notch_range=[min(nb1), max(nb1)] if nb1 else None, neighbour_range=[min(nb), max(nb)] if nb else None, verdict=verdict, current_tier=TIER.get(name), suggested_tier=tier)


# ---------------- NHL
def nhl_games():
    G = RR.load('nhl'); RR.profiles(G)
    # last-game margin per team (regular season, ESPN schedule), for nhl_bounce_home_ml
    E = json.load(open(os.path.join(ROOT, 'data', 'state', 'hist_schedule.json'))).get('nhl') or {}
    sched = collections.defaultdict(list)
    for h in E.values():
        if h.get('hs') is None or not h.get('home') or not h.get('away') or (h.get('stype') is not None and h['stype'] != 2): continue
        st = RR.ts(h['start']); sn = RR.season_of('nhl', st)
        sched[(h['home'], sn)].append((st, h['hs'] - h['as_'])); sched[(h['away'], sn)].append((st, h['as_'] - h['hs']))
    for v in sched.values(): v.sort()
    keys = {k: [x[0] for x in v] for k, v in sched.items()}
    out = []
    for g in G:
        if g['p_close'] is None or g['close_h'] is None or g['close_h'] > 6 or g['hs'] is None or g['home_games'] < 1 or g['away_games'] < 1: continue
        g['fav'] = 'home' if g['p_close'] >= .5 else 'away'; g['dog'] = 'away' if g['fav'] == 'home' else 'home'
        g['wf'], g['wd'] = g[f"{g['fav']}_win_pct"], g[f"{g['dog']}_win_pct"]
        do = g.get('ml_away_open') if g['dog'] == 'away' else g.get('ml_home_open'); g['dog_open_am'] = (do - 1) * 100 if do else None
        ab, sn = g.get('home_ab'), RR.season_of('nhl', g['start']); g['home_last_margin'] = None
        if ab and (ab, sn) in sched:
            i = bisect.bisect_left(keys[(ab, sn)], g['start'] - dt.timedelta(hours=3))
            if i: g['home_last_margin'] = sched[(ab, sn)][i - 1][1]
        out.append(g)
    return out


def nhl(R):
    G = nhl_games()
    fav_pl = lambda g, **k: ('spread', g['fav'], -1.5)
    R.append(grid('nhl_pl_fav_gap', 'nhl', G, lambda g, gap: ('spread', g['fav'], -1.5) if g['wd'] - g['wf'] >= gap else None,
                  {'gap': [16, 19, 22, 25, 28]}, {'gap': 22}, fav_pl, 'opponent win% minus favourite win%, whole percents'))
    R.append(grid('nhl_pl_fav_strong_opp', 'nhl', G, lambda g, opp: ('spread', g['fav'], -1.5) if g['wd'] >= opp else None,
                  {'opp': [60, 63, 66, 69, 72]}, {'opp': 66}, fav_pl, 'opponent win%, whole percents'))
    R.append(grid('nhl_pl_dog_bigml', 'nhl', G, lambda g, lo, hi: ('spread', g['dog'], 1.5) if g['dog_open_am'] is not None and lo <= g['dog_open_am'] <= hi else None,
                  {'lo': [161, 171, 181, 191], 'hi': [186, 196, 206, 216]}, {'lo': 181, 'hi': 196}, lambda g, **k: ('spread', g['dog'], 1.5), 'opening dog ML, American'))
    R.append(grid('nhl_early_home_fav_qual', 'nhl', G,
                  lambda g, maxgame, opp: ('ml', 'home', None) if g['fav'] == 'home' and g['home_games'] + 1 <= maxgame and g['away_win_pct'] >= opp else None,
                  {'maxgame': [16, 20, 24, 28, 32], 'opp': [45, 48, 51, 54, 57]}, {'maxgame': 24, 'opp': 51}, lambda g, **k: ('ml', 'home', None) if g['fav'] == 'home' else None,
                  'home game number (this game) and opponent win%'))
    def bounce(g, loss, lo, hi, ming=3):
        if g['home_games'] < ming or g['away_games'] < ming or g['home_last_margin'] is None: return None
        wp = g['home_wins'] / g['home_games']
        return ('ml', 'home', None) if g['home_last_margin'] <= -loss and lo / 100 <= wp < hi / 100 else None
    R.append(grid('nhl_bounce_home_ml', 'nhl', G, bounce, {'loss': [2, 3, 4], 'lo': [40, 45, 50, 55], 'hi': [60, 65, 70, 75]}, {'loss': 3, 'lo': 50, 'hi': 65},
                  lambda g, **k: ('ml', 'home', None) if g['home_games'] >= 3 and g['away_games'] >= 3 else None,
                  'live filter (sharp/systems.py): both teams 3+ games, home lost last game by 3+, home win% 50 to under 65'))
    r = R[-1]; r['extra'] = {f'min games {m}': run('nhl', G, bounce, dict(loss=3, lo=50, hi=65, ming=m))['all'] for m in (3, 8, 15)}


# ---------------- CFB
def cfb(R):
    G = RR.load('cfb'); RR.profiles(G)
    G = [g for g in G if g['close_h'] is not None and g['close_h'] <= 8 and g['hs'] is not None and g['sp_close'] is not None and g['tot_close'] is not None]
    C = [g for g in G if g.get('conf')]
    R.append(grid('cfb_road_dog_low_total', 'cfb', C, lambda g, dog, tot: ('spread', 'away', None) if g['sp_close'] <= -dog and g['tot_close'] <= tot else None,
                  {'dog': [6, 6.5, 7, 7.5, 8], 'tot': [44, 46, 48, 50, 52]}, {'dog': 7, 'tot': 48}, lambda g, **k: ('spread', 'away', None) if g['sp_close'] < 0 else None,
                  'conference games; road dog of at least X, total at most Y'))
    R.append(grid('cfb_homefav_7510_under', 'cfb', G, lambda g, lo, hi: ('total', 'under', None) if -hi <= g['sp_close'] <= -lo else None,
                  {'lo': [6.5, 7, 7.5, 8], 'hi': [9.5, 10, 10.5, 11]}, {'lo': 7.5, 'hi': 10}, lambda g, **k: ('total', 'under', None) if g['sp_close'] < 0 else None,
                  'home favourite of lo to hi at the close'))


# ---------------- NFL (team keys and season margins built as in sharp/nfl_replay.py, without the weather pull)
def nfl(R):
    import sharp.oddsapi_edge as E
    T = json.load(open(os.path.join(ROOT, 'data', 'state', 'espn_teams.json')))['nfl']; A = {E.norm(t['name']): ab for ab, t in T.items()}
    G = RR.load('nfl'); RR.profiles(G)
    for g in G: g['hab'] = A.get(E.norm(g['home'])); g['aab'] = A.get(E.norm(g['away']))
    G = [g for g in G if g['hs'] is not None and g['close_h'] is not None and g['close_h'] <= 8 and g['hab'] and g['aab'] and g['hab'] not in ('AFC', 'NFC')]
    hist = collections.defaultdict(list)
    for g in G:
        sn = season('nfl', g)
        for side, team in (('home', g['hab']), ('away', g['aab'])):
            L = hist[(team, sn)]; g[f'{side}_margin_avg'] = sum(L) / len(L) if L else None; g[f'{side}_n'] = len(L)
        if g['sp_close'] is not None:
            hist[(g['hab'], sn)].append(g['hs'] - g['as_']); hist[(g['aab'], sn)].append(g['as_'] - g['hs'])
    G = [g for g in G if g['sp_close'] is not None and g['sp_close'] != 0]
    for g in G: g['dog'] = 'away' if g['sp_close'] < 0 else 'home'
    R.append(grid('nfl_home_dog_7510', 'nfl', G, lambda g, lo, hi: ('spread', 'home', None) if lo <= g['sp_close'] <= hi else None,
                  {'lo': [6.5, 7, 7.5, 8], 'hi': [9.5, 10, 10.5, 11]}, {'lo': 7.5, 'hi': 10}, lambda g, **k: ('spread', 'home', None) if g['sp_close'] > 0 else None,
                  'home dog of lo to hi at the close'))
    def awful(g, margin, ming):
        d = g['dog']; m = g[f'{d}_margin_avg']
        return ('spread', d, None) if m is not None and g[f'{d}_n'] >= ming and m <= margin else None
    R.append(grid('awfuldog', 'nfl', G, awful, {'margin': [-9, -11, -13, -15, -17], 'ming': [1, 2, 3]}, {'margin': -13, 'ming': 1},
                  lambda g, **k: ('spread', g['dog'], None) if g[f"{g['dog']}_n"] >= 1 else None, 'dog season point margin per game (this season) at most X, after Y+ games'))


def main():
    R = []
    nhl(R); cfb(R); nfl(R)
    json.dump(dict(generated=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), method=__doc__.split('\n\n')[1], skipped=['cbb_bigloss_vs_top5 (no historical AP ranks)', 'weather rules'], rules=R), open(OUT, 'w'), indent=1)
    for r in R:
        e = r['exact']
        print(f"\n== {r['rule']} ({r['note']})  exact {r['exact_params']}: n={e['all']['n']} {e['all']['record']} {e['all']['roi']:+.1f}%  seasons {e['seasons_pos']} of {e['seasons_full']}"
              f"  | baseline n={r['baseline']['n']} {r['baseline']['roi']:+.1f}%  | 1-notch median {r['neighbour_1notch_median']}  range {r['neighbour_range']}  -> {r['verdict']} (tier {r['current_tier']} -> {r['suggested_tier']})")
        print('   by season:', ', '.join(f"{k} {v['record']} {v['roi']:+.1f}%" for k, v in e.items() if isinstance(v, dict) and k != 'all'))
        for c in r['cells']: print(f"   {c['params']}  n={c['n']:5} {c['record']:12} {c['roi'] if c['roi'] is not None else 0:+6.1f}%  {c['seasons_pos']}/{c['seasons_full']}" + ('  <- exact' if c['dist'] == 0 else ''))
        for k, v in (r.get('extra') or {}).items(): print(f"   {k}: n={v['n']} {v['record']} {v['roi']:+.1f}%")


if __name__ == '__main__':
    main()
