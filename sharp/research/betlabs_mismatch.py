#!/usr/bin/env python3
"""11/26 (Sean via Kirk, td_betlabs_mismatch): why Bet Labs and our 11/5 replay (sharp/rule_replay.py) disagree on three screens moved to real
money on 11/25. Diagnosis only: no tier or board change.

For each screen: join Bet Labs' own game list (data/research/betlabs/*.txt, pulled read-only from Sean's Chrome, hash-checked) to the Odds API
database by game, then split into games in both, only in Bet Labs, only in our replay. On games in both, compare result and price. For games
only in ours, test each Bet Labs filter we apply differently. Rerun our grading on the matched games only.
Seasons compared: NHL and CBB 2020-21 to 2025-26, CFB 2020 to 2025 (the span of our replay).
Usage: python3 sharp/research/betlabs_mismatch.py ODDS_REPO_ROOT   (a checkout holding data/oddsapi/odds.sqlite and data/state/hist_schedule.json)
Writes data/research/betlabs_mismatch_2026-11-26.json and data/research/betlabs/*_matched.json."""
import os, sys, json, collections, datetime as dt, re, statistics
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'sharp'))
import rule_replay as RR
SRC = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT
RR.DB = os.path.join(SRC, 'data', 'oddsapi', 'odds.sqlite'); RR.ROOT = SRC
ET = RR.ET; BLD = os.path.join(ROOT, 'data', 'research', 'betlabs')
OUT = {}
PO = {}


def etd(g): return g['start'].astimezone(ET).date()
def pdate(s): m, d, y = map(int, s.split('/')); return dt.date(2000 + y, m, d)
def dec_from_units(res, units):
    """Bet Labs 'Units Won' is per 100 risked: a win at +188 shows 188, at -272 shows 36.8. Losses show -100."""
    return None if res != 'W' else 1 + units / 100


def am(dec): return None if not dec else round((dec - 1) * 100) if dec >= 2 else round(-100 / (dec - 1))
def roi(rows, key='dec', won='won'):
    n = len([r for r in rows if r[won] is not None]); pnl = sum(((r[key] - 1) if r[won] == 1 else -1 if r[won] == 0 else 0) for r in rows if r[won] is not None and r[key])
    w = sum(1 for r in rows if r[won] == 1); l = sum(1 for r in rows if r[won] == 0)
    return dict(n=n, record=f"{w}-{l}", units=round(pnl, 2), roi=round(100 * pnl / n, 1) if n else None)


def norm(s): return re.sub(r'[^a-z0-9 ]', '', (s or '').lower().replace('&', ' and ')).strip()


def in_window(sport, d):
    if sport == 'cfb': return 2020 <= d.year <= 2025
    s = d.year if d.month >= 8 else d.year - 1
    return 2020 <= s <= 2025


def season(sport, d): return RR.season_of(sport, dt.datetime(d.year, d.month, d.day))


def ou_streak(G):
    """Home team's over/under streak entering each game vs Pinnacle's closing total: +k = k straight overs, -k = k straight unders, 0 = last game a
    push or no game yet. Bet Labs' 'Home OU Streak' filter on screen 1792184 keeps 0, 1, 2 or 3."""
    last = collections.defaultdict(list)
    for g in G:
        sea = RR.season_of('cbb', g['start'])
        for side, team in (('home', g['home']), ('away', g['away'])):
            L = last[(team, sea)]; k = 0
            if L:
                f = L[-1]
                if f is not None:
                    for x in reversed(L):
                        if x == f: k += 1
                        else: break
                    k = k if f else -k
            g[f'{side}_ou_streak'] = k
        if g['hs'] is not None and g['tot_close'] is not None:
            t = g['hs'] + g['as_']; o = None if t == g['tot_close'] else t > g['tot_close']
            last[(g['home'], sea)].append(o); last[(g['away'], sea)].append(o)


def match_by_score(bl, G, sport):
    """Bet Labs row -> odds game: same ET date (or a day either side), same final score (home/visitor as listed, or flipped for a neutral site)."""
    by = collections.defaultdict(list)
    for g in G:
        if g['hs'] is not None: by[etd(g)].append(g)
    out = []
    for r in bl:
        d = r['date']; cand = []
        for dd in (d, d - dt.timedelta(days=1), d + dt.timedelta(days=1)):
            for g in by.get(dd, []):
                if (g['hs'], g['as_']) == (r['hs'], r['vs']): cand.append((dd != d, False, g))
                elif (g['hs'], g['as_']) == (r['vs'], r['hs']): cand.append((dd != d, True, g))
        def sc(c):
            g = c[2]; a = norm(r['home']).split(); b = norm(r['visitor']).split()
            hh, aa = (g['away'], g['home']) if c[1] else (g['home'], g['away'])
            return (sum(1 for t in a if t in norm(hh).split()) + sum(1 for t in b if t in norm(aa).split()), -c[0])
        cand.sort(key=sc, reverse=True)
        best = cand[0] if cand and sc(cand[0])[0] >= 1 else None
        out.append((r, best[2] if best else None, best[1] if best else None))
    return out


# ------------------------------------------------------------------------------------------------------------------ NHL 1784155
def nhl():
    bl = []
    for line in open(os.path.join(BLD, 'nhl_strong_opp_1784155.txt')):
        d, home, vis, ln, res, units, ha, ow = line.strip().split('|')     # home nickname | visitor nickname | ... | the side played (H/A)
        bl.append(dict(date=pdate(d), home=home, vis=vis, line=float(ln), res=res, units=float(units), ha=ha, opp_win=int(ow)))
    bl = [r for r in bl if in_window('nhl', r['date'])]
    G = RR.load('nhl'); RR.profiles(G)
    # playoff games: ESPN season type 3 in the complete schedule (Bet Labs' screen is regular season only; our replay did not filter)
    E = json.load(open(os.path.join(SRC, 'data', 'state', 'hist_schedule.json'))).get('nhl') or {}
    po = {(h.get('home'), h.get('away'), h['start'][:10]) for h in E.values() if h.get('stype') == 3}
    global PO; PO = {g['id']: True for g in G if (g.get('home_ab'), g.get('away_ab'), g['start'].strftime('%Y-%m-%d')) in po}
    by = collections.defaultdict(list)
    for g in G: by[etd(g)].append(g)
    nick = lambda full: norm(full).split()[-1]
    def find(r):
        for dd in (r['date'], r['date'] - dt.timedelta(days=1), r['date'] + dt.timedelta(days=1)):
            for g in by.get(dd, []):
                if (nick(g['home']), nick(g['away'])) == (norm(r['home']).split()[-1], norm(r['vis']).split()[-1]): return g
        return None
    # our replay's set, exactly as sharp/rule_replay.py builds it
    ours = {}
    for g in G:
        if not (g['p_close'] is not None and g['close_h'] is not None and g['close_h'] <= 6): continue
        if g['hs'] is None or g['home_games'] < 1 or g['away_games'] < 1: continue
        fav = 'home' if g['p_close'] >= .5 else 'away'; dog = 'away' if fav == 'home' else 'home'
        if g[f'{dog}_win_pct'] >= 66 and in_window('nhl', etd(g)):
            gr = RR.grade(g, 'spread', fav, -1.5)
            if gr: ours[g['id']] = dict(g=g, side=fav, won=gr[0], dec=gr[1])
    rows = []; missing = []
    for r in bl:
        g = find(r)
        if not g: missing.append(r); continue
        side = 'home' if r['ha'] == 'H' else 'away'; o = ours.get(g['id'])
        dog = 'away' if side == 'home' else 'home'
        # our grade of Bet Labs' own bet: the team at Bet Labs' line (-1.5, or +1.5 when Bet Labs lists the favorite at +1.5)
        gr = RR.grade(g, 'spread', side, r['line']) if g['hs'] is not None else None
        rows.append(dict(date=str(r['date']), game=f"{g['away']} @ {g['home']}", gid=g['id'], side=side, bl_line=r['line'], bl_res=r['res'], bl_dec=dec_from_units(r['res'], r['units']),
                         bl_won=1 if r['res'] == 'W' else 0 if r['res'] == 'L' else None, bl_opp_win=r['opp_win'], our_opp_win=g.get(f'{dog}_win_pct'), our_opp_games=g.get(f'{dog}_games'),
                         our_fav_close=('home' if (g['p_close'] or 0) >= .5 else 'away') if g['p_close'] is not None else None, close_ok=g['close_h'] is not None and g['close_h'] <= 6 and g['p_close'] is not None,
                         in_ours=bool(o), our_won=gr[0] if gr else None, our_dec=gr[1] if gr else None, playoff=PO.get(g['id'])))
    bl_ids = {x['gid'] for x in rows}
    only_ours = [o for k, o in ours.items() if k not in bl_ids]
    # why only in ours: Bet Labs' win% check on the same game, by the number of games the opponent had played and by the win% band
    oo = []
    for o in only_ours:
        g = o['g']; dog = 'away' if o['side'] == 'home' else 'home'
        oo.append(dict(date=str(etd(g)), game=f"{g['away']} @ {g['home']}", gid=g['id'], side=o['side'], our_opp_win=g[f'{dog}_win_pct'], opp_games=g[f'{dog}_games'], opp_wins=g[f'{dog}_wins'],
                       won=o['won'], dec=o['dec'], p_close=g['p_close'], sp_close=g['sp_close'], playoff=PO.get(g['id'])))
    return 'nhl_pl_fav_strong_opp', bl, rows, missing, list(ours.values()), oo


# ------------------------------------------------------------------------------------------------------------------ CBB 1792184
def cbb():
    bl = []
    for line in open(os.path.join(BLD, 'cbb_under_good_over_drop_1792184.txt')):
        p = line.rstrip('\n').split('|')
        if len(p) < 13: continue
        bl.append(dict(date=pdate(p[0]), home=p[1], visitor=p[2], hs=int(p[3]), vs=int(p[4]), total=float(p[5]), res=p[6], units=float(p[7]), chg=float(p[8]), dow=p[9], h_over=int(p[10]), v_over=int(p[11]), h_streak=int(p[12])))
    bl = [r for r in bl if in_window('cbb', r['date'])]
    G = RR.load('cbb'); RR.profiles(G); ou_streak(G)
    ours = {}
    for g in G:
        if not (g['close_h'] is not None and g['close_h'] <= 6): continue
        if g['hs'] is None or g['start'].astimezone(ET).weekday() > 4: continue
        if g['home_over_n'] >= 3 and g['away_over_n'] >= 3 and g['home_over_pct'] >= .5 and g['away_over_pct'] >= .59 and g['tot_open'] is not None and g['tot_close'] is not None and g['tot_open'] - g['tot_close'] >= 0.5 and in_window('cbb', etd(g)):
            gr = RR.grade(g, 'total', 'under')
            if gr: ours[g['id']] = dict(g=g, won=gr[0], dec=gr[1])
    rows = []; missing = []
    for r, g, flip in match_by_score(bl, G, 'cbb'):
        if not g: missing.append(r); continue
        gr = RR.grade(g, 'total', 'under')
        hk, ak = ('away', 'home') if flip else ('home', 'away')
        rows.append(dict(date=str(r['date']), game=f"{g['away']} @ {g['home']}", gid=g['id'], flip=flip, bl_total=r['total'], our_total=g['tot_close'], our_open=g['tot_open'], bl_chg=r['chg'],
                         our_chg=round(g['tot_close'] - g['tot_open'], 1) if g['tot_open'] is not None and g['tot_close'] is not None else None, bl_res=r['res'], bl_dec=dec_from_units(r['res'], r['units']),
                         bl_won=1 if r['res'] == 'W' else 0 if r['res'] == 'L' else None, bl_h_over=r['h_over'], bl_v_over=r['v_over'], bl_h_streak=r['h_streak'],
                         our_h_over=round(100 * g[f'{hk}_over_pct']) if g[f'{hk}_over_pct'] is not None else None, our_h_n=g[f'{hk}_over_n'],
                         our_v_over=round(100 * g[f'{ak}_over_pct']) if g[f'{ak}_over_pct'] is not None else None, our_v_n=g[f'{ak}_over_n'], our_h_streak=g[f'{hk}_ou_streak'],
                         close_ok=g['close_h'] is not None and g['close_h'] <= 6, in_ours=g['id'] in ours, our_won=gr[0] if gr else None, our_dec=gr[1] if gr else None))
    bl_ids = {x['gid'] for x in rows}
    oo = []
    for k, o in ours.items():
        if k in bl_ids: continue
        g = o['g']
        oo.append(dict(date=str(etd(g)), game=f"{g['away']} @ {g['home']}", gid=k, our_h_over=round(100 * g['home_over_pct']), our_v_over=round(100 * g['away_over_pct']), h_n=g['home_over_n'], v_n=g['away_over_n'],
                       h_streak=g['home_ou_streak'], chg=round(g['tot_close'] - g['tot_open'], 1), won=o['won'], dec=o['dec']))
    return 'cbb_under_good_over_drop', bl, rows, missing, list(ours.values()), oo


# ------------------------------------------------------------------------------------------------------------------ CFB 1792198
def cfb():
    bl = []
    for line in open(os.path.join(BLD, 'cfb_road_streak_dog_1792198.txt')):
        p = line.rstrip('\n').split('|')
        bl.append(dict(date=pdate(p[0]), home=p[1], visitor=p[2], hs=int(p[3]), vs=int(p[4]), line=float(p[5]), res=p[6], units=float(p[7]), play=p[8], total=float(p[9]), streak=int(p[10])))
    bl = [r for r in bl if in_window('cfb', r['date'])]
    G = RR.load('cfb'); RR.profiles(G)
    # prior consecutive road games entering the game, from the complete ESPN schedule (RR.profiles' away_road_streak)
    ours = {}
    for g in G:
        if not (g['close_h'] is not None and g['close_h'] <= 8): continue
        if g['hs'] is None or g['sp_close'] is None or g['tot_close'] is None: continue
        if g['sp_close'] < 0 and g['tot_close'] <= 54 and 2 <= g['away_road_streak'] + 1 <= 5 and g['away_games'] >= 1 and in_window('cfb', etd(g)):
            gr = RR.grade(g, 'spread', 'away')
            if gr: ours[g['id']] = dict(g=g, won=gr[0], dec=gr[1])
    rows = []; missing = []
    for r, g, flip in match_by_score(bl, G, 'cfb'):
        if not g: missing.append(r); continue
        gr = RR.grade(g, 'spread', 'home' if flip else 'away')
        ak = 'home' if flip else 'away'
        rows.append(dict(date=str(r['date']), game=f"{g['away']} @ {g['home']}", gid=g['id'], flip=flip, bl_line=r['line'], our_line=(g['sp_close'] if flip else -g['sp_close']) if g['sp_close'] is not None else None,
                         bl_total=r['total'], our_total=g['tot_close'], bl_streak=r['streak'], our_prior_road=g.get(f'{ak}_road_streak'), conf=g.get('conf'),
                         bl_res=r['res'], bl_dec=dec_from_units(r['res'], r['units']), bl_won=1 if r['res'] == 'W' else 0 if r['res'] == 'L' else None,
                         close_ok=g['close_h'] is not None and g['close_h'] <= 8, in_ours=g['id'] in ours, our_won=gr[0] if gr else None, our_dec=gr[1] if gr else None))
    bl_ids = {x['gid'] for x in rows}
    oo = []
    for k, o in ours.items():
        if k in bl_ids: continue
        g = o['g']
        oo.append(dict(date=str(etd(g)), game=f"{g['away']} @ {g['home']}", gid=k, prior_road=g['away_road_streak'], conf=g.get('conf'), line=-g['sp_close'], total=g['tot_close'], won=o['won'], dec=o['dec']))
    return 'cfb_road_streak_dog', bl, rows, missing, list(ours.values()), oo


def summarize(name, bl, rows, missing, ours, oo):
    both = [r for r in rows if r['in_ours']]; bl_only = [r for r in rows if not r['in_ours']]
    blw = lambda R: roi([dict(won=r['bl_won'], dec=r['bl_dec'] or 2) for r in R])
    S = dict(betlabs=roi([dict(won=1 if r['res'] == 'W' else 0 if r['res'] == 'L' else None, dec=dec_from_units(r['res'], r['units']) or 2) for r in bl]),
             ours=roi([dict(won=o['won'] if o['won'] in (0, 1) else None, dec=o['dec']) for o in ours]),
             matched_to_odds_db=len(rows), betlabs_not_in_odds_db=len(missing), in_both=len(both), only_betlabs=len(bl_only), only_ours=len(oo),
             both_betlabs_grade=blw(both), both_our_grade=roi([dict(won=r['our_won'] if r['our_won'] in (0, 1) else None, dec=r['our_dec']) for r in both]),
             all_matched_betlabs_grade=blw(rows), all_matched_our_grade=roi([dict(won=r['our_won'] if r['our_won'] in (0, 1) else None, dec=r['our_dec']) for r in rows]),
             only_ours_grade=roi([dict(won=o['won'] if o['won'] in (0, 1) else None, dec=o['dec']) for o in oo]))
    same = [r for r in rows if r['bl_won'] is not None and r['our_won'] in (0, 1)]
    S['same_result_share'] = round(sum(1 for r in same if r['bl_won'] == r['our_won']) / len(same), 3) if same else None
    S['result_differs'] = [dict(date=r['date'], game=r['game'], bl=r['bl_res'], ours=r['our_won'], **({k: r[k] for k in ('bl_total', 'our_total') if k in r}), **({k: r[k] for k in ('bl_line', 'our_line') if k in r})) for r in same if r['bl_won'] != r['our_won']]
    # price on wins (Bet Labs shows its price only through units won on a win)
    wins = [r for r in rows if r['bl_won'] == 1 and r['our_dec'] and r['bl_dec']]
    if wins:
        gap = [100 * (1 / r['bl_dec'] - 1 / r['our_dec']) for r in wins]      # + = Bet Labs' price was better (lower implied probability)
        S['price_on_wins'] = dict(n=len(wins), betlabs_avg_dec=round(statistics.mean(r['bl_dec'] for r in wins), 3), ours_avg_dec=round(statistics.mean(r['our_dec'] for r in wins), 3),
                                  avg_gap_cents=round(-statistics.mean(gap), 2))
        # Bet Labs' results graded at our prices, and our results at Bet Labs' win prices
        S['betlabs_results_at_our_prices'] = roi([dict(won=r['bl_won'], dec=r['our_dec']) for r in rows if r['our_dec'] and r['bl_won'] is not None])
    OUT[name] = dict(summary=S, matched=rows, betlabs_missing=[{k: str(v) for k, v in r.items()} for r in missing], only_ours=oo)
    json.dump(dict(matched=rows, betlabs_missing=[{k: str(v) for k, v in r.items()} for r in missing], only_ours=oo), open(os.path.join(BLD, f'{name}_matched.json'), 'w'), indent=0, default=str)
    print('\n==', name); print(json.dumps({k: v for k, v in S.items() if k != 'result_differs'}, indent=1)); print('result differs', len(S['result_differs']))


if __name__ == '__main__':
    only = sys.argv[2:] or ['nhl', 'cbb', 'cfb']
    op = os.path.join(ROOT, 'data', 'research', 'betlabs_mismatch_2026-11-26.json')
    if os.path.exists(op): OUT.update(json.load(open(op)))
    for f in (nhl, cbb, cfb):
        if f.__name__ in only: summarize(*f())
    json.dump(OUT, open(os.path.join(ROOT, 'data', 'research', 'betlabs_mismatch_2026-11-26.json'), 'w'), indent=1, default=str)
