#!/usr/bin/env python3
"""Systems validation audit (board_r10), as pre-registered in docs/validation/VALIDATION_PLAN.md (commit 130634a). Read-only.

Four gates per live rule: in-sample, permutation with the original search grid (best variant per shuffle), walk-forward with the last
complete season as the final holdout, and a permutation of the walk-forward seasons. Plus a plateau check on the grid neighbours.
Data: the Odds API database rebuilt from the repo (sharp/odds_db.py), ESPN schedule results, Open-Meteo archive weather, NFL 1H lines from
data/oddsapi/derivs/nfl.jsonl.gz. Price: Pinnacle's last quote before the start (1H: Pinnacle else the US books' median, 10 min before).
Writes data/research/validation.json, docs/validation/<rule>.md, docs/validation/SUMMARY.md and docs/validation/<rule>_hist.png (wind).
Usage: python3 sharp/validate_systems.py [rule ...]     (fixed seed 20261118)"""
import os, sys, json, gzip, bisect, itertools, collections, datetime as dt, sqlite3, zoneinfo
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.rule_replay as RR
SEED = 20261118; N_PERM = 1000; N_WF_PERM = 200; MIN_N = 30
ET = zoneinfo.ZoneInfo('America/New_York')
OUTJ = os.path.join(ROOT, 'data', 'research', 'validation.json'); DOCD = os.path.join(ROOT, 'docs', 'validation')
HOLDOUT = {'nfl': '2025', 'cfb': '2025', 'nba': '2025-26', 'nhl': '2025-26'}
ROOF_NFL = {'ARI', 'ATL', 'DAL', 'DET', 'HOU', 'IND', 'LV', 'LAR', 'LAC', 'MIN', 'NO'}   # domes, retractable roofs, SoFi


# ---------------------------------------------------------------- data
def team_hist(sport):
    """(abbr, season) -> sorted [(start, side, pf, pa)] for regular-season ESPN games with a final score."""
    H = json.load(open(os.path.join(ROOT, 'data', 'state', 'hist_schedule.json'))).get(sport) or {}
    T = collections.defaultdict(list); STYPE = {}
    for eid, h in H.items():
        STYPE[eid] = h.get('stype')
        if h.get('hs') is None or not h.get('home') or not h.get('away'): continue
        st = RR.ts(h['start'])
        if not RR.regular_season(sport, h.get('stype'), st): continue      # 11/27: also drops the 2020 NHL / NBA bubble (blank type)
        sea = season(sport, st)
        T[(h['home'], sea)].append((st, 'home', h['hs'], h['as_']))
        T[(h['away'], sea)].append((st, 'away', h['as_'], h['hs']))
    for v in T.values(): v.sort(key=lambda x: x[0])
    return T, STYPE


def season(sport, st):
    return RR.season_of(sport, st) if sport in ('nba', 'nhl', 'cbb') else str((st - dt.timedelta(days=60)).year)


def before(T, ab, sea, st):
    L = T.get((ab, sea), [])
    i = bisect.bisect_left([x[0] for x in L], st - dt.timedelta(hours=3)); return L[:i]


def load(sport):
    G = RR.load(sport); RR.profiles(G)
    c = sqlite3.connect(RR.DB); ESPN = dict(c.execute("SELECT game_id, espn_id FROM results WHERE espn_id IS NOT NULL").fetchall())
    T, STYPE = team_hist(sport)
    out = []
    for g in G:
        if g['hs'] is None or not g.get('home_ab') or not g.get('away_ab'): continue
        eid = ESPN.get(g['id']); g['espn'] = eid
        if not RR.regular_season(sport, STYPE.get(str(eid)) if eid else None, g['start']): continue          # regular season only (11/27: and not the 2020 bubble)
        if sport == 'cfb':                                                   # the CFB schedule has no season type: bowls and playoff out by date
            d = g['start'].astimezone(ET)
            if (d.month == 1 or (d.month == 12 and d.day >= 14)) and {g['home_ab'], g['away_ab']} != {'ARMY', 'NAVY'}: continue
        g['season'] = season(sport, g['start'])
        for side, ab in (('home', g['home_ab']), ('away', g['away_ab'])):
            P = before(T, ab, g['season'], g['start'])
            g[f'{side}_n2'] = len(P)
            g[f'{side}_days'] = (g['start'].astimezone(ET).date() - P[-1][0].astimezone(ET).date()).days if P else None
            g[f'{side}_last_margin'] = (P[-1][2] - P[-1][3]) if P else None
            g[f'{side}_margin_avg'] = sum(x[2] - x[3] for x in P) / len(P) if P else None
            k = 0
            for x in reversed(P):
                if x[2] < x[3]: k += 1
                else: break
            g[f'{side}_loss_streak'] = k
        out.append(g)
    # ATS records from the closing spread (home perspective), per team and season, before the game
    A = collections.defaultdict(list)
    for g in sorted(out, key=lambda g: g['start']):
        for side in ('home', 'away'):
            L = A[(g[f'{side}_ab'], g['season'])]; L2 = [x for x in L if x is not None]
            g[f'{side}_ats_pct'] = int(100 * sum(1 for x in L2 if x > 0) / len(L2)) if L2 else None; g[f'{side}_ats_n'] = len(L2)
        if g.get('sp_close') is not None:
            m = g['hs'] - g['as_'] + g['sp_close']
            A[(g['home_ab'], g['season'])].append(None if m == 0 else m); A[(g['away_ab'], g['season'])].append(None if m == 0 else -m)
    return out


def wx_map(sport):
    return json.load(open(os.path.join(ROOT, 'data', sport, 'weather', 'archive.json')))


def nfl_1h():
    """game_id -> dict(tot=(line, over_dec, under_dec), sp=(home_line, home_dec, away_dec), h1=(home pts, away pts))"""
    import sharp.nfl_1h_replay as H1
    D = {}
    for l in gzip.open(os.path.join(ROOT, 'data', 'oddsapi', 'derivs', 'nfl.jsonl.gz'), 'rt'):
        r = json.loads(l)
        if r.get('bookmakers'): D[r['game_id']] = r
    LS = json.load(open(os.path.join(ROOT, 'data', 'state', 'linescores.json'))).get('nfl', {})
    return D, LS, H1.lines


# ---------------------------------------------------------------- grading helpers
def tot_bet(g, side):
    gr = RR.grade(g, 'total', side)
    return (gr[0], gr[1]) if gr else None


def ml_bet(g, side):
    gr = RR.grade(g, 'ml', side)
    return (gr[0], gr[1]) if gr else None


def sp_bet(g, side):
    gr = RR.grade(g, 'spread', side)
    return (gr[0], gr[1]) if gr else None


# ---------------------------------------------------------------- systems: base bets, features, grid, live variant
def systems():
    S = {}

    def wind_full(G, W):
        rows = []
        for g in G:
            if g['home_ab'] in ROOF_NFL or g.get('neutral'): continue
            w = W.get(f"{g['home_ab']}|{g['start']:%Y-%m-%dT%H}")
            b = tot_bet(g, 'under')
            if not w or w.get('wind') is None or not b: continue
            rows.append(dict(g=g, won=b[0], dec=b[1], f=dict(wind=w['wind'])))
        return rows
    band_grid = [dict(lo=lo, hi=hi) for lo in (8, 9, 10, 11, 12) for hi in (12, 13, 14, 15, 16, 99) if lo < hi]
    band_sel = lambda f, v: v['lo'] <= round(f['wind']) <= v['hi']
    S['wind1014'] = dict(sport='nfl', label='NFL wind 10-14 under', price='Pinnacle full-game close', base='wind_full', grid=band_grid,
                         live=dict(lo=10, hi=14), sel=band_sel, params=('lo', 'hi'), leak='none: kickoff-hour wind is a forecast quantity; the archive is observed (see limits)')
    S['wind1014_1h'] = dict(sport='nfl', label='NFL 1H wind 10-13 under', price='1H line 10 min before kickoff: Pinnacle, else US-book median', base='wind_1h',
                            grid=band_grid, live=dict(lo=10, hi=13), sel=band_sel, params=('lo', 'hi'), leak='none')
    S['cfb_wind14'] = dict(sport='cfb', label='CFB wind 14+ under', price='Pinnacle full-game close', base='cfb_wind',
                           grid=[dict(t=t) for t in range(10, 19)], live=dict(t=14), sel=lambda f, v: round(f['wind']) >= v['t'], params=('t',), leak='none')
    S['cfb_hot_over_low_total'] = dict(sport='cfb', label='CFB hot weather over, total 55 or less', price='Pinnacle full-game close', base='cfb_over',
        grid=[dict(T=T, W=W, C=C, nc=nc) for T in (80, 85, 90) for W in (8, 10, 12) for C in (50, 55, 60, 999) for nc in (True, False)],
        live=dict(T=85, W=10, C=55, nc=True),
        sel=lambda f, v: f['temp'] >= v['T'] and round(f['wind']) <= v['W'] and f['tot'] <= v['C'] and (not v['nc'] or f['conf'] is False),
        params=('T', 'W', 'C', 'nc'), leak='closing total in the filter (Bet Labs "Closing Total Range"); the bet is graded at the same close, so no extra edge leaks in at the close, but a bet placed earlier sees a different number')
    S['awfuldog'] = dict(sport='nfl', label='NFL awful-team dog ATS', price='Pinnacle full-game close', base='nfl_dog',
        grid=[dict(m=m) for m in (-7, -9, -11, -13, -15, -17)], live=dict(m=-13),
        sel=lambda f, v: f['n'] >= 2 and f['marg'] <= v['m'], params=('m',), leak='none')
    S['nfl_home_dog_7510'] = dict(sport='nfl', label='NFL home dog 7.5 to 10', price='Pinnacle full-game close', base='nfl_home_dog',
        grid=[dict(lo=lo, hi=hi) for lo in (6, 6.5, 7, 7.5, 8) for hi in (9, 9.5, 10, 10.5, 11, 14) if lo < hi], live=dict(lo=7.5, hi=10),
        sel=lambda f, v: v['lo'] <= f['sp'] <= v['hi'], params=('lo', 'hi'), leak='closing spread in the filter (graded at the same close)')
    S['vrest8_1h'] = dict(sport='nfl', label='NFL 1H visitor off 8-30 days under', price='1H line 10 min before kickoff: Pinnacle, else US-book median', base='nfl_1h_under',
        grid=[dict(lo=lo, hi=hi) for lo in (6, 7, 8, 9, 10) for hi in (13, 15, 30)], live=dict(lo=8, hi=30),
        sel=lambda f, v: f['outdoor'] and f['vdays'] is not None and v['lo'] <= f['vdays'] <= v['hi'], params=('lo', 'hi'), leak='none')
    S['mnf_1h'] = dict(sport='nfl', label='NFL 1H Monday night under', price='1H line 10 min before kickoff: Pinnacle, else US-book median', base='nfl_1h_under',
        grid=[dict(d=d) for d in ('mon', 'thu', 'sun_night', 'mon_thu')], live=dict(d='mon'),
        sel=lambda f, v: f['outdoor'] and (f['day'] == v['d'] or (v['d'] == 'mon_thu' and f['day'] in ('mon', 'thu'))), params=('d',), leak='none')
    S['cfb_homefav_7510_under'] = dict(sport='cfb', label='CFB home fav 7.5 to 10 under', price='Pinnacle full-game close', base='cfb_under_all',
        grid=[dict(lo=lo, hi=hi) for lo in (6, 6.5, 7, 7.5, 8) for hi in (9, 9.5, 10, 10.5, 11, 14) if lo < hi], live=dict(lo=7.5, hi=10),
        sel=lambda f, v: f['hsp'] is not None and -v['hi'] <= f['hsp'] <= -v['lo'], params=('lo', 'hi'), leak='closing spread in the filter (graded at the same close)')
    S['nba_bigfav_over'] = dict(sport='nba', label='NBA big favourite over', price='Pinnacle full-game close', base='nba_over',
        grid=[dict(t=t) for t in (0.75, 0.78, 0.80, 0.82, 0.855, 0.88, 0.90)], live=dict(t=0.855),
        sel=lambda f, v: f['fav'] is not None and f['fav'] >= v['t'], params=('t',), leak='closing moneyline in the filter (graded at the same close)')
    S['nba_badteams_under'] = dict(sport='nba', label='NBA weak home team vs weak visitor under', price='Pinnacle full-game close', base='nba_under',
        grid=[dict(h=h, vlo=vlo, vhi=vhi) for h in (30, 35, 40, 45) for vlo in (25, 30, 35) for vhi in (40, 45, 50)], live=dict(h=40, vlo=30, vhi=45),
        sel=lambda f, v: f['hn'] >= 8 and f['hw'] is not None and f['aw'] is not None and f['hw'] <= v['h'] and v['vlo'] <= f['aw'] <= v['vhi'], params=('h', 'vlo', 'vhi'), leak='none')
    S['nba_ats_hot_home'] = dict(sport='nba', label='NBA hot home team ATS, 2 days rest', price='Pinnacle full-game close', base='nba_home_sp',
        grid=[dict(a=a, r=r) for a in (55, 60, 65, 70) for r in (1, 2, 3)], live=dict(a=60, r=2),
        sel=lambda f, v: f['hn'] >= 8 and f['ats'] is not None and f['ats'] >= v['a'] and f['hdays'] == v['r'], params=('a', 'r'), leak='none')
    S['nba_under_good_home_over'] = dict(sport='nba', label='NBA under, good home over team, total down', price='Pinnacle full-game close', base='nba_under',
        grid=[dict(d=d, o=o) for d in (0.5, 1, 1.5, 2, 3) for o in (50, 55, 58, 62, 65)], live=dict(d=1.5, o=58),
        sel=lambda f, v: f['drop'] is not None and f['drop'] >= v['d'] and f['hov'] is not None and f['hov'] >= v['o'] and f['hdays'] in (1, 2) and f['adays'] in (1, 2, 3),
        params=('d', 'o'), leak='open-to-close total move in the filter: only known at the close, where it is graded; a bet placed earlier would not know the full drop')
    S['nhl_early_home_fav_qual'] = dict(sport='nhl', label='NHL early-season home fav vs quality opponent ML', price='Pinnacle full-game close', base='nhl_home_ml',
        grid=[dict(G=G, w=w) for G in (16, 20, 24, 28, 32) for w in (48, 50, 51, 53, 55)], live=dict(G=24, w=51),
        sel=lambda f, v: f['fav'] and f['gn'] <= v['G'] and f['ow'] is not None and f['ow'] >= v['w'], params=('G', 'w'), leak='closing moneyline decides favourite (graded at the same close)')
    S['nhl_bounce_home_ml'] = dict(sport='nhl', label='NHL bounce home ML off a 3+ goal loss', price='Pinnacle full-game close', base='nhl_home_ml',
        grid=[dict(lo=lo, hi=hi, m=m) for lo in (45, 50, 55) for hi in (60, 64, 70) for m in (2, 3, 4)], live=dict(lo=50, hi=64, m=3),
        sel=lambda f, v: f['hw'] is not None and v['lo'] <= f['hw'] <= v['hi'] and f['hlm'] is not None and -20 <= f['hlm'] <= -v['m'], params=('lo', 'hi', 'm'), leak='none')
    S['nhl_skid_fade_road'] = dict(sport='nhl', label='NHL road team off a win vs home skid, puck line', price='Pinnacle close on the main NHL spread (puck line)', base='nhl_away_sp',
        grid=[dict(k=k) for k in (2, 3, 4, 5)], live=dict(k=3),
        sel=lambda f, v: f['alm'] is not None and 1 <= f['alm'] <= 20 and v['k'] <= f['hls'] <= 12, params=('k',), leak='none')
    return S


def base_rows(name, G, ctx):
    rows = []
    if name == 'wind_full':
        W = ctx['W']
        for g in G:
            if g['home_ab'] in ROOF_NFL or g.get('neutral'): continue
            w = W.get(f"{g['home_ab']}|{g['start']:%Y-%m-%dT%H}"); b = tot_bet(g, 'under')
            if w and w.get('wind') is not None and b: rows.append((g, b, dict(wind=w['wind'])))
    elif name in ('wind_1h', 'nfl_1h_under'):
        W = ctx['W']; D, LS, lines = ctx['H1']
        for g in G:
            d = D.get(g['id']); ls = LS.get(str(g.get('espn')))
            if not d or not ls or len(ls.get('h', [])) < 2: continue
            L = lines(d); t = L.get('totals_h1')
            if not t: continue
            pts = sum(ls['h'][:2]) + sum(ls['a'][:2]); ln, ov, un = t[0], t[1], t[2]
            won = 0.5 if pts == ln else 1 if pts < ln else 0
            outdoor = g['home_ab'] not in ROOF_NFL and not g.get('neutral')
            et = g['start'].astimezone(ET); wd = et.strftime('%a')
            day = 'mon' if wd == 'Mon' else 'thu' if wd == 'Thu' else 'sun_night' if (wd == 'Sun' and et.hour >= 19) else 'other'
            f = dict(outdoor=outdoor, vdays=g.get('away_days'), day=day)
            if name == 'wind_1h':
                if not outdoor: continue
                w = W.get(f"{g['home_ab']}|{g['start']:%Y-%m-%dT%H}")
                if not w or w.get('wind') is None: continue
                f['wind'] = w['wind']
            rows.append((g, (won, un), f))
    elif name == 'cfb_wind':
        W = ctx['W']
        for g in G:
            if g.get('neutral'): continue
            w = W.get(f"{g['home_ab']}|{g['start']:%Y-%m-%dT%H}"); b = tot_bet(g, 'under')
            if w and w.get('wind') is not None and b: rows.append((g, b, dict(wind=w['wind'])))
    elif name == 'cfb_over':
        W = ctx['W']
        for g in G:
            if g.get('neutral'): continue
            w = W.get(f"{g['home_ab']}|{g['start']:%Y-%m-%dT%H}"); b = tot_bet(g, 'over')
            if w and w.get('wind') is not None and w.get('temp') is not None and b and g.get('tot_close') is not None:
                rows.append((g, b, dict(wind=w['wind'], temp=w['temp'], tot=g['tot_close'], conf=None if g.get('conf') is None else bool(g['conf']))))
    elif name == 'nfl_dog':
        for g in G:
            if g.get('sp_close') is None or g['sp_close'] == 0: continue
            dog = 'home' if g['sp_close'] > 0 else 'away'; b = sp_bet(g, dog)
            if b: rows.append((g, b, dict(n=g[f'{dog}_n2'], marg=g[f'{dog}_margin_avg'] if g[f'{dog}_margin_avg'] is not None else 99)))
    elif name == 'nfl_home_dog':
        for g in G:
            if g.get('sp_close') is None or g['sp_close'] <= 0: continue
            b = sp_bet(g, 'home')
            if b: rows.append((g, b, dict(sp=g['sp_close'])))
    elif name == 'cfb_under_all':
        for g in G:
            b = tot_bet(g, 'under')
            if b: rows.append((g, b, dict(hsp=g.get('sp_close'))))
    elif name in ('nba_over', 'nba_under'):
        side = name.split('_')[1]
        for g in G:
            b = tot_bet(g, side)
            if not b: continue
            p = g.get('p_close'); hov = g.get('home_over_pct')
            rows.append((g, b, dict(fav=max(p, 1 - p) if p is not None else None, hn=g['home_n2'], hw=g.get('home_win_pct'), aw=g.get('away_win_pct'),
                                    drop=(g['tot_open'] - g['tot_close']) if g.get('tot_open') is not None and g.get('tot_close') is not None else None,
                                    hov=int(100 * hov) if hov is not None else None, hdays=g.get('home_days'), adays=g.get('away_days'))))
    elif name == 'nba_home_sp':
        for g in G:
            b = sp_bet(g, 'home')
            if b: rows.append((g, b, dict(hn=g['home_n2'], ats=g.get('home_ats_pct') if g.get('home_ats_n', 0) >= 8 else None, hdays=g.get('home_days'))))
    elif name == 'nhl_home_ml':
        for g in G:
            b = ml_bet(g, 'home')
            if b and g.get('p_close') is not None:
                rows.append((g, b, dict(fav=g['p_close'] > 0.5, gn=g['home_n2'] + 1, ow=g.get('away_win_pct'), hw=g.get('home_win_pct'), hlm=g.get('home_last_margin'))))
    elif name == 'nhl_away_sp':
        for g in G:
            b = sp_bet(g, 'away')
            if b: rows.append((g, b, dict(alm=g.get('away_last_margin'), hls=g.get('home_loss_streak', 0))))
    return rows


# ---------------------------------------------------------------- statistics
def profit(won, dec): return np.where(won == 1, dec - 1, np.where(won == 0, -1.0, 0.0))


def strata(seasons, dec):
    """season x price-decile id per bet (deciles of the implied probability within the season)."""
    sid = np.zeros(len(dec), dtype=int); k = 0
    for s in sorted(set(seasons)):
        ix = np.where(seasons == s)[0]; p = 1 / dec[ix]
        q = np.quantile(p, np.linspace(0, 1, 11)[1:-1]) if len(ix) >= 20 else []
        d = np.searchsorted(q, p, side='right')
        for j in np.unique(d): sid[ix[d == j]] = k; k += 1
    return sid


def shuffle(won, sid, rng, only=None):
    w = won.copy()
    for k in np.unique(sid if only is None else sid[only]):
        ix = np.where(sid == k)[0]
        if only is not None: ix = ix[only[ix]]
        w[ix] = w[rng.permutation(ix)]
    return w


def roi(mask, pr):
    n = mask.sum(); return (pr[mask].sum() / n, int(n)) if n else (None, 0)


def run(rule, cfg, rows, rng):
    seasons = np.array([g['season'] for g, b, f in rows]); won = np.array([b[0] for g, b, f in rows], dtype=float)
    dec = np.array([b[1] for g, b, f in rows], dtype=float); feats = [f for g, b, f in rows]
    hold = HOLDOUT[cfg['sport']]; all_seasons = sorted(set(seasons))
    full = [s for s in all_seasons if s <= hold]                       # 2026 football / 2026-27 partial seasons are not complete: excluded
    keep = np.isin(seasons, full); seasons, won, dec = seasons[keep], won[keep], dec[keep]; feats = [f for f, k in zip(feats, keep) if k]
    grid = cfg['grid']; key = lambda v: tuple(v[p] for p in cfg['params'])
    M = np.array([[bool(cfg['sel'](f, v)) for f in feats] for v in grid]); li = [key(v) for v in grid].index(key(cfg['live']))
    pr = profit(won, dec); ins = seasons != hold
    # gate 1
    m_live = M[li] & ins; r1, n1 = roi(m_live, pr); w1 = int((won[m_live] == 1).sum()); l1 = int((won[m_live] == 0).sum()); u1 = float(pr[m_live].sum())
    by_season = {s: roi(M[li] & (seasons == s), pr) for s in full}
    # gate 2: permutation over the in-sample seasons, best grid variant per shuffle
    sid = strata(seasons, dec); best = []
    for _ in range(N_PERM):
        ws = shuffle(won, sid, rng); ps = profit(ws, dec)
        b = -9
        for i in range(len(grid)):
            m = M[i] & ins; n = m.sum()
            if n >= MIN_N: b = max(b, ps[m].sum() / n)
        best.append(b)
    best = np.array(best); p2 = float((best >= r1).mean()) if r1 is not None else None
    # single-filter permutation (reported beside it)
    single = []
    for _ in range(min(N_PERM, 1000)):
        ws = shuffle(won, sid, rng); ps = profit(ws, dec); single.append(ps[m_live].sum() / max(1, m_live.sum()))
    p2s = float((np.array(single) >= r1).mean()) if r1 is not None else None
    # gate 3: walk-forward
    wf = []
    for t in range(2, len(full)):
        tr = np.isin(seasons, full[:t]); te = seasons == full[t]
        cand = [(roi(M[i] & tr, pr)[0], i) for i in range(len(grid)) if (M[i] & tr).sum() >= MIN_N]
        if not cand: continue
        i = max(cand)[1]; r, n = roi(M[i] & te, pr)
        wf.append(dict(season=full[t], variant=grid[i], roi=r, n=n, holdout=full[t] == hold, idx=i))
    oos = [w for w in wf if not w['holdout']]; ho = [w for w in wf if w['holdout']]
    def pooled(L, P):
        m = np.zeros(len(won), bool)
        for w in L: m |= M[w['idx']] & (seasons == w['season'])
        return roi(m, P), m
    (r_oos, n_oos), _ = pooled(oos, pr); (r_all, n_all), m_wf = pooled(wf, pr)
    # gate 4: permutation of the walk-forward seasons only
    wfs = np.isin(seasons, [w['season'] for w in wf]); g4 = []
    for _ in range(N_WF_PERM):
        ws = shuffle(won, sid, rng, only=wfs); ps = profit(ws, dec); g4.append(ps[m_wf].sum() / max(1, m_wf.sum()))
    p4 = float((np.array(g4) >= r_all).mean()) if r_all is not None else None
    n_wf_seasons = len(wf); bar4 = 0.05 if n_wf_seasons == 1 else 0.01
    # plateau: neighbours one grid step away in one parameter
    vals = {p: sorted({v[p] for v in grid}, key=lambda x: (0, x, '') if isinstance(x, (int, float)) and not isinstance(x, bool) else (1, 0, str(x))) for p in cfg['params']}
    neigh = []
    for p in cfg['params']:
        L = vals[p]; j = L.index(cfg['live'][p])
        for jj in (j - 1, j + 1):
            if 0 <= jj < len(L):
                v = dict(cfg['live']); v[p] = L[jj]
                if key(v) in [key(x) for x in grid]:
                    i = [key(x) for x in grid].index(key(v)); r, n = roi(M[i] & ins, pr); neigh.append(dict(variant=v, roi=r, n=n))
    nr = [x['roi'] for x in neigh if x['roi'] is not None]
    plateau = bool(bool(nr) and r1 is not None and r1 > 0 and all(x > 0 for x in nr) and float(np.median(nr)) >= 0.5 * r1)
    grid_rois = [(grid[i], *roi(M[i] & ins, pr)) for i in range(len(grid))]
    # verdict
    g2ok = p2 is not None and p2 < 0.05; g4ok = p4 is not None and p4 < bar4
    ho_r = ho[0]['roi'] if ho else None
    if n1 < 20: verdict = 'INSUFFICIENT DATA'
    elif g2ok and g4ok and n1 >= 100 and (ho_r or 0) > 0: verdict = 'KEEP'
    elif g2ok: verdict = 'WATCH'
    elif (r_all or 0) > 0: verdict = 'PAPER ONLY'
    else: verdict = 'RETIRE'
    return dict(rule=rule, label=cfg['label'], sport=cfg['sport'], price=cfg['price'], leak=cfg['leak'], live=cfg['live'], seasons=full, holdout=hold,
                n=n1, roi=r1, record=f"{w1}-{l1}", units=u1, by_season={s: dict(roi=v[0], n=v[1]) for s, v in by_season.items()},
                flags=[x for x in ('N < 100 (thin)' if n1 < 100 else None, 'ROI above +25%: check for leakage' if (r1 or 0) > 0.25 else None) if x],
                p_grid=p2, p_single=p2s, grid_size=len(grid), perm_best=best.tolist(),
                wf=[{k: v for k, v in w.items() if k != 'idx'} for w in wf], oos_roi=r_oos, oos_n=n_oos, wf_roi=r_all, wf_n=n_all, p_wf=p4, wf_bar=bar4,
                holdout_roi=ho_r, wf_sd=float(pr[m_wf].std(ddof=1)) if m_wf.sum() > 1 else None, wf_units=float(pr[m_wf].sum()), wf_record=f"{int((won[m_wf] == 1).sum())}-{int((won[m_wf] == 0).sum())}", holdout_n=ho[0]['n'] if ho else 0, plateau=plateau, neighbours=neigh, grid_rois=grid_rois, verdict=verdict,
                n_bets_base=int(len(won)))


# ---------------------------------------------------------------- reports
def pct(x): return 'n/a' if x is None else f"{100 * x:+.1f}%"


def reason(R):
    if R['verdict'] == 'INSUFFICIENT DATA': return f"only {R['n']} in-sample bets"
    bits = [f"grid p {R['p_grid']:.3f}", f"walk-forward {pct(R['wf_roi'])} on {R['wf_n']} (p {R['p_wf']:.3f})", f"holdout {pct(R['holdout_roi'])} on {R['holdout_n']}"]
    if not R['plateau']: bits.append('no plateau')
    return '; '.join(bits)


def report(R, hist_png=None):
    v = ', '.join(f"{k} {x}" for k, x in R['live'].items())
    L = [f"# {R['label']} ({R['rule']})", "", f"Verdict: **{R['verdict']}** ({reason(R)})", "",
         f"Live definition: {v}. Price: {R['price']}. Seasons: {', '.join(R['seasons'])}; holdout {R['holdout']}. Base pool: {R['n_bets_base']} bets of this market.", "",
         "## Gate 1: in-sample (all seasons before the holdout)", "",
         f"N {R['n']}, record {R['record']}, units {R['units']:+.2f}, ROI {pct(R['roi'])}. Flags: {', '.join(R['flags']) or 'none'}. Leakage review: {R['leak']}.", "",
         "| Season | N | ROI |", "|---|---|---|"] + [f"| {s} | {x['n']} | {pct(x['roi'])} |" for s, x in R['by_season'].items()] + ["",
         "## Gate 2: permutation (1,000 shuffles within season x price decile)", "",
         f"Best of {R['grid_size']} grid variants per shuffle (N >= {MIN_N}): p = {R['p_grid']:.3f}. Plain single-filter permutation (weaker): p = {R['p_single']:.3f}.", ""]
    if hist_png: L += [f"![shuffled best-variant ROIs]({os.path.basename(hist_png)})", ""]
    L += ["## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)", "", "| Season | Variant fitted | N | ROI |", "|---|---|---|---|"]
    L += [f"| {w['season']}{' (holdout)' if w['holdout'] else ''} | {', '.join(f'{k} {x}' for k, x in w['variant'].items())} | {w['n']} | {pct(w['roi'])} |" for w in R['wf']]
    L += ["", f"Out-of-sample before the holdout: {pct(R['oos_roi'])} on {R['oos_n']}. Holdout: {pct(R['holdout_roi'])} on {R['holdout_n']}. All walk-forward seasons: {pct(R['wf_roi'])} on {R['wf_n']}.", "",
          "## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)", "",
          f"p = {R['p_wf']:.3f} (bar {R['wf_bar']} with {len(R['wf'])} walk-forward season(s)).", "",
          "## Plateau (grid neighbours of the live definition, in-sample)", "", "| Variant | N | ROI |", "|---|---|---|"]
    L += [f"| {', '.join(f'{k} {x}' for k, x in x_['variant'].items())} | {x_['n']} | {pct(x_['roi'])} |" for x_ in R['neighbours']]
    L += ["", f"Plateau: {'yes' if R['plateau'] else 'no'}.", "", "## Whole grid (in-sample)", "", "| Variant | N | ROI |", "|---|---|---|"]
    L += [f"| {', '.join(f'{k} {x}' for k, x in v_.items())} | {n} | {pct(r)} |" for v_, r, n in sorted(R['grid_rois'], key=lambda x: -(x[1] if x[1] is not None else -9))]
    return '\n'.join(L) + '\n'


def histogram(R, path):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 3.6), dpi=130)
    ax.hist([100 * x for x in R['perm_best']], bins=40, color='#9aa7b8')
    ax.axvline(100 * R['roi'], color='#c0392b', lw=2, label=f"real ROI {pct(R['roi'])}")
    ax.set_xlabel('best grid variant ROI on shuffled outcomes (%)'); ax.set_ylabel('shuffles')
    ax.set_title(f"{R['label']}: p = {R['p_grid']:.3f}"); ax.legend(frameon=False); fig.tight_layout(); fig.savefig(path); plt.close(fig)


def main():
    want = sys.argv[1:]; S = systems(); rng = np.random.default_rng(SEED)
    out = json.load(open(OUTJ)) if os.path.exists(OUTJ) else {}
    os.makedirs(DOCD, exist_ok=True); cache = {}
    for rule, cfg in S.items():
        if want and rule not in want: continue
        sp = cfg['sport']
        if sp not in cache: cache[sp] = load(sp); print(f'[validate] {sp}: {len(cache[sp])} regular-season games', flush=True)
        ctx = {}
        if sp in ('nfl', 'cfb'): ctx['W'] = wx_map(sp)
        if cfg['base'] in ('wind_1h', 'nfl_1h_under'): ctx['H1'] = nfl_1h()
        rows = base_rows(cfg['base'], cache[sp], ctx)
        R = run(rule, cfg, rows, np.random.default_rng(SEED + sum(map(ord, rule))))
        png = os.path.join(DOCD, f'{rule}_hist.png') if 'wind' in rule else None
        if png and R['roi'] is not None: histogram(R, png)
        open(os.path.join(DOCD, f'{rule}.md'), 'w').write(report(R, png))
        out[rule] = {k: v for k, v in R.items() if k != 'perm_best'}
        json.dump(out, open(OUTJ, 'w'), indent=1, default=str)
        print(f"[validate] {rule}: N {R['n']} ROI {pct(R['roi'])} p_grid {R['p_grid']} p_single {R['p_single']} wf {pct(R['wf_roi'])}/{R['wf_n']} p_wf {R['p_wf']} hold {pct(R['holdout_roi'])}/{R['holdout_n']} plateau {R['plateau']} -> {R['verdict']}", flush=True)


if __name__ == '__main__': main()
