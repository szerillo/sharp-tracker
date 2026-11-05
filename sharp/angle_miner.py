#!/usr/bin/env python3
"""Angle miner (Sean, 11/5: "we now have a new database that we can fully test alongside other filters from betlabs to try to find
actionable angles"). Every Bet Labs-style filter and every two-filter combination, on every bet (home / away spread, home / away
moneyline, over / under), on every team sport in the Odds API database, graded on results at the Pinnacle close.

Guard against fitting noise: train = seasons through 2023, test = 2024 on. An angle is reported only if it clears
  train n >= 120 and ROI >= +3%,  test n >= 50 and ROI > 0,  and at least 70% of its seasons (n >= 15) are positive.
With ~200 single filters and ~15,000 pairs per bet per sport, a few will pass by luck; the test seasons are the check, and anything that
survives still goes to paper first. CLV is reported, not scored.
Output: data/research/angles.json (everything that passed), docs/angles_2026-11-05.md (ranked). Run: python3 sharp/angle_miner.py [sport ...]"""
import os, sys, json, collections, itertools, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.rule_replay import load, season_of, ET
OUT = os.path.join(ROOT, 'data', 'research', 'angles.json'); DOC = os.path.join(ROOT, 'docs', 'angles_2026-11-05.md')
SPORTS = ['nfl', 'nba', 'nhl', 'cfb', 'cbb', 'mlb', 'wnba']
TEST_FROM = {'nfl': '2024', 'cfb': '2024', 'mlb': '2024', 'wnba': '2024', 'nba': '2024-25', 'nhl': '2024-25', 'cbb': '2024-25'}
MIN = dict(train_n=120, train_roi=3.0, test_n=50, test_roi=0.0, consist=0.7, z=1.0, z_all=2.5)


def band(x, cuts, labels):
    for c, l in zip(cuts, labels):
        if x < c: return l
    return labels[-1]


def profiles(G, sport):
    """Per team per season, before each game: games, win%, margin avg, ATS%, O/U%, last margin, last ATS margin, win streak, ATS streak,
    O/U streak, rest days, road streak."""
    H = collections.defaultdict(list)
    for g in G:
        sea = season_of(sport, g['start'])
        for side, team in (('home', g['home']), ('away', g['away'])):
            L = H[(team, sea)]; n = len(L); P = {}
            P['games'] = n
            P['win_pct'] = sum(x['won'] for x in L) / n if n else None
            P['margin'] = sum(x['margin'] for x in L) / n if n else None
            ats = [x['ats'] for x in L if x['ats'] is not None]; P['ats_pct'] = sum(1 for a in ats if a > 0) / len(ats) if ats else None
            ou = [x['over'] for x in L if x['over'] is not None]; P['over_pct'] = sum(ou) / len(ou) if ou else None
            P['last_margin'] = L[-1]['margin'] if L else None; P['last_ats'] = L[-1]['ats'] if L else None
            k = 0
            for x in reversed(L):
                if x['won']: k += 1
                else: break
            P['win_streak'] = k
            k = 0
            for x in reversed(L):
                if not x['won']: k += 1
                else: break
            P['loss_streak'] = k
            k = 0
            for x in reversed(L):
                if x['ats'] is not None and x['ats'] > 0: k += 1
                else: break
            P['ats_streak'] = k
            k = 0
            for x in reversed(L):
                if x['ats'] is not None and x['ats'] < 0: k += 1
                else: break
            P['ats_fail_streak'] = k
            k = 0
            for x in reversed(L):
                if x['over'] is True: k += 1
                else: break
            P['over_streak'] = k
            k = 0
            for x in reversed(L):
                if x['over'] is False: k += 1
                else: break
            P['under_streak'] = k
            P['rest'] = (g['start'].astimezone(ET).date() - L[-1]['start'].astimezone(ET).date()).days if L else None
            k = 0
            for x in reversed(L):
                if x['side'] == 'away': k += 1
                else: break
            P['road_streak'] = k
            g[side + '_p'] = P
        if g['hs'] is None: continue
        m = g['hs'] - g['as_']; tot = g['hs'] + g['as_']
        over = (tot > g['tot_close']) if g.get('tot_close') is not None and tot != g['tot_close'] else None
        ats_h = (m + g['sp_close']) if g.get('sp_close') is not None else None
        H[(g['home'], sea)].append(dict(start=g['start'], won=m > 0, margin=m, ats=ats_h, over=over, side='home'))
        H[(g['away'], sea)].append(dict(start=g['start'], won=m < 0, margin=-m, ats=(-ats_h if ats_h is not None else None), over=over, side='away'))


def features(g, sport):
    """One categorical value per feature for this game. Team features are given for home and away (and by role fav/dog via 'role')."""
    F = {}
    sp = g.get('sp_close'); tc = g.get('tot_close'); p = g.get('p_close')
    F['role'] = 'home fav' if sp is not None and sp < 0 else 'home dog' if sp is not None and sp > 0 else 'pick' if sp == 0 else None
    sz = abs(sp) if sp is not None else None
    F['spread'] = None if sz is None else band(sz, [3, 3.5, 7, 7.5, 10.5, 14.5], ['pk-2.5', '3', '3.5-6.5', '7', '7.5-10', '10.5-14', '14.5+']) if sport in ('nfl', 'cfb') else band(sz, [2, 4, 6, 9, 12], ['0-1.5', '2-3.5', '4-5.5', '6-8.5', '9-11.5', '12+']) if sport in ('nba', 'cbb', 'wnba') else ('-1.5' if sz == 1.5 else 'other')
    if tc is not None:
        if sport == 'nfl': F['total'] = band(tc, [41, 44.5, 48.5, 52.5], ['<41', '41-44', '44.5-48', '48.5-52', '52.5+'])
        elif sport == 'cfb': F['total'] = band(tc, [45, 52, 58, 65], ['<45', '45-51.5', '52-57.5', '58-64.5', '65+'])
        elif sport == 'nba': F['total'] = band(tc, [215, 225, 232, 240], ['<215', '215-224', '225-231', '232-239', '240+'])
        elif sport == 'cbb': F['total'] = band(tc, [130, 140, 150, 160], ['<130', '130-139', '140-149', '150-159', '160+'])
        elif sport == 'nhl': F['total'] = band(tc, [5.75, 6.25, 6.75], ['5.5-', '6', '6.5', '7+'])
        elif sport == 'mlb': F['total'] = band(tc, [7.75, 8.75, 9.75], ['7.5-', '8-8.5', '9-9.5', '10+'])
        elif sport == 'wnba': F['total'] = band(tc, [155, 162, 170], ['<155', '155-161', '162-169', '170+'])
    if p is not None: F['ml_fav'] = band(max(p, 1 - p), [.55, .6, .65, .7, .75, .8, .85], ['50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '85+'])
    d = g['start'].astimezone(ET)
    F['day'] = 'weekend' if d.weekday() >= 5 else 'weekday'
    F['night'] = 'night (7pm+ ET)' if d.hour >= 19 else 'day'
    if g.get('sp_open') is not None and sp is not None:
        mv = sp - g['sp_open']
        F['sp_move'] = 'toward home 1.5+' if mv <= -1.5 else 'toward home 0.5-1' if mv < 0 else 'flat' if mv == 0 else 'toward away 0.5-1' if mv <= 1 else 'toward away 1.5+'
    if g.get('tot_open') is not None and tc is not None:
        mv = tc - g['tot_open']
        F['tot_move'] = 'down 1.5+' if mv <= -1.5 else 'down 0.5-1' if mv < 0 else 'flat' if mv == 0 else 'up 0.5-1' if mv <= 1 else 'up 1.5+'
    for side in ('home', 'away'):
        P = g.get(side + '_p') or {}
        if P.get('games', 0) >= 3:
            F[side + ' win%'] = band(P['win_pct'], [.35, .5, .65], ['<35', '35-49', '50-64', '65+'])
            F[side + ' margin'] = band(P['margin'], [-7, -2, 2, 7], ['-7 or worse', '-7 to -2', 'even', '+2 to +7', '+7 or better']) if sport in ('nfl', 'cfb', 'nba', 'cbb', 'wnba') else band(P['margin'], [-.75, -.2, .2, .75], ['-.75 or worse', '-.75 to -.2', 'even', '+.2 to +.75', '+.75 or better'])
            if P.get('ats_pct') is not None: F[side + ' ats%'] = band(P['ats_pct'], [.4, .6], ['<40', '40-59', '60+'])
            if P.get('over_pct') is not None: F[side + ' over%'] = band(P['over_pct'], [.4, .6], ['<40', '40-59', '60+'])
        if P.get('last_margin') is not None:
            lm = P['last_margin']; big = 14 if sport in ('nfl', 'cfb', 'nba', 'cbb', 'wnba') else 3
            F[side + ' last'] = 'blowout loss' if lm <= -big else 'loss' if lm < 0 else 'win' if lm < big else 'blowout win'
        if P.get('last_ats') is not None:
            la = P['last_ats']; big = 14 if sport in ('nfl', 'cfb', 'nba', 'cbb', 'wnba') else 2
            F[side + ' last ats'] = 'lost ATS big' if la <= -big else 'lost ATS' if la < 0 else 'push' if la == 0 else 'covered' if la < big else 'covered big'
        if P.get('games', 0) >= 3:
            F[side + ' streak'] = 'won 3+' if P['win_streak'] >= 3 else 'lost 3+' if P['loss_streak'] >= 3 else 'neither'
            F[side + ' ats streak'] = 'covered 3+' if P['ats_streak'] >= 3 else 'failed 3+' if P['ats_fail_streak'] >= 3 else 'neither'
            F[side + ' ou streak'] = 'over 3+' if P['over_streak'] >= 3 else 'under 3+' if P['under_streak'] >= 3 else 'neither'
        if P.get('rest') is not None:
            r = P['rest']
            if sport in ('nfl', 'cfb'): F[side + ' rest'] = 'short (<7)' if r < 7 else 'normal' if r <= 7 else 'extra (8+)'
            else: F[side + ' rest'] = 'b2b' if r == 1 else '2 days' if r == 2 else '3+ days'
        if P.get('road_streak') is not None and side == 'away': F['road trip'] = 'first away' if P['road_streak'] == 0 else '2nd-3rd away' if P['road_streak'] <= 2 else '4th+ away'
    return {k: v for k, v in F.items() if v is not None}


def outcomes(g):
    """Per bet: (won 1/0/0.5, decimal) or None."""
    O = {}
    if g['hs'] is None: return O
    m = g['hs'] - g['as_']
    if g.get('sp_close') is not None and g.get('sp_home_dec') and g.get('sp_away_dec'):
        a = m + g['sp_close']; O['home ATS'] = ((1 if a > 0 else 0 if a < 0 else .5), g['sp_home_dec']); O['away ATS'] = ((1 if a < 0 else 0 if a > 0 else .5), g['sp_away_dec'])
    if g.get('ml_home') and g.get('ml_away'):
        O['home ML'] = ((1 if m > 0 else 0), g['ml_home']); O['away ML'] = ((1 if m < 0 else 0), g['ml_away'])
    if g.get('tot_close') is not None and g.get('over_dec') and g.get('under_dec'):
        t = g['hs'] + g['as_']
        O['over'] = ((.5 if t == g['tot_close'] else 1 if t > g['tot_close'] else 0), g['over_dec']); O['under'] = ((.5 if t == g['tot_close'] else 1 if t < g['tot_close'] else 0), g['under_dec'])
    return O


def mine(sport):
    G = load(sport)
    G = [g for g in G if g['hs'] is not None and g.get('close_h') is not None and g['close_h'] <= 6]
    if len(G) < 300: return []
    profiles(G, sport)
    # accumulate: key (bet, filterA, filterB or None) -> season -> [n, w, l, pnl]
    acc = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0.0, 0.0]))
    for g in G:
        F = features(g, sport); O = outcomes(g)
        if not O: continue
        sea = season_of(sport, g['start'])
        items = sorted(F.items())
        singles = [(k, v) for k, v in items]
        pairs = list(itertools.combinations(singles, 2))
        for bet, (won, dec) in O.items():
            pnl = (dec - 1) if won == 1 else -1.0 if won == 0 else 0.0
            for s in singles:
                a = acc[(bet, s, None)][sea]; a[0] += 1; a[1] += won == 1; a[2] += won == 0; a[3] += pnl; a[4] += pnl * pnl
            for pr in pairs:
                a = acc[(bet, pr[0], pr[1])][sea]; a[0] += 1; a[1] += won == 1; a[2] += won == 0; a[3] += pnl; a[4] += pnl * pnl
    tf = TEST_FROM[sport]; res = []; passed_single = set()
    def stats(S):
        tr = [0, 0, 0, 0.0, 0.0]; te = [0, 0, 0, 0.0, 0.0]
        for sea, a in S.items():
            t = te if sea >= tf else tr
            for i in range(4): t[i] += a[i]
            t[4] += a[4]
        return tr, te
    keys = sorted(acc, key=lambda k: k[2] is not None)        # singles first, so a pair can be checked against its parents
    for (bet, f1, f2) in keys:
        S = acc[(bet, f1, f2)]
        tr, te = stats(S)
        if tr[0] < MIN['train_n'] or te[0] < MIN['test_n']: continue
        roi_tr = 100 * tr[3] / tr[0]; roi_te = 100 * te[3] / te[0]
        if roi_tr < MIN['train_roi'] or roi_te <= MIN['test_roi']: continue
        # z-scores from the per-bet pnl variance (sd ~1 for a -110 spread, larger for dogs): both halves must clear 1.5
        def z(t):
            var = t[4] / t[0] - (t[3] / t[0]) ** 2
            return (t[3] / t[0]) / ((var ** .5) / (t[0] ** .5)) if var > 0 else 0
        z_tr, z_te = z(tr), z(te); al = [tr[i] + te[i] for i in range(5)]; z_all = z(al)
        if z_tr < MIN['z'] or z_te < MIN['z'] or z_all < MIN['z_all']: continue
        if f2 is not None and ((bet, f1) in passed_single or (bet, f2) in passed_single): continue     # the pair adds a filter to an angle that already passes on its own
        if f2 is None: passed_single.add((bet, f1))
        yrs = [a[3] > 0 for sea, a in S.items() if a[0] >= 15]
        if not yrs or sum(yrs) / len(yrs) < MIN['consist']: continue
        allv = [sum(a[i] for a in S.values()) for i in range(4)]
        res.append(dict(sport=sport, bet=bet, filters=[f"{f1[0]} = {f1[1]}"] + ([f"{f2[0]} = {f2[1]}"] if f2 else []), z_train=round(z_tr, 2), z_test=round(z_te, 2),
                        train=dict(n=tr[0], record=f"{tr[1]}-{tr[2]}", roi=round(roi_tr, 1)), test=dict(n=te[0], record=f"{te[1]}-{te[2]}", roi=round(roi_te, 1)),
                        all=dict(n=allv[0], record=f"{allv[1]}-{allv[2]}", roi=round(100 * allv[3] / allv[0], 1)), seasons_pos=f"{sum(yrs)}/{len(yrs)}",
                        by_season={s: dict(n=a[0], record=f"{a[1]}-{a[2]}", roi=round(100 * a[3] / a[0], 1)) for s, a in sorted(S.items())}))
    # score: test ROI weighted by sqrt(n), prefer singles
    res.sort(key=lambda r: -(r['test']['roi'] * (r['test']['n'] ** .5) * (1.3 if len(r['filters']) == 1 else 1)))
    print(f"[angles] {sport}: {len(G)} games, {len(res)} angles passed", flush=True)
    return res


def main():
    sports = sys.argv[1:] or SPORTS
    R = {}
    for sp in sports: R[sp] = mine(sp)
    prev = json.load(open(OUT)) if os.path.exists(OUT) and sys.argv[1:] else {}
    prev.update(R); json.dump(prev, open(OUT, 'w'), separators=(',', ':'))
    lines = ['# Angle miner, Odds API 2020-26 (Pinnacle closes, results)', '',
             f"Train = seasons through 2023, test = 2024 on. Bar: train n >= {MIN['train_n']} and ROI >= +{MIN['train_roi']:.0f}%, test n >= {MIN['test_n']} and ROI > 0, z >= {MIN['z']} on both halves and {MIN['z_all']} overall, 70%+ of seasons positive; a pair is dropped when one of its filters passes alone. "
             'Top 25 per sport by test ROI x sqrt(n). Everything here is a candidate for PAPER, not a bet: with this many filters some pass by luck.', '']
    for sp, res in prev.items():
        lines += [f'## {sp.upper()}: {len(res)} angles passed', '', '| bet | filters | train | test | all | seasons + | z train / test |', '|---|---|---|---|---|---|---|']
        for r in res[:25]:
            lines.append(f"| {r['bet']} | {' AND '.join(r['filters'])} | {r['train']['record']} ({r['train']['roi']:+.1f}%) | {r['test']['record']} ({r['test']['roi']:+.1f}%) | {r['all']['record']} ({r['all']['roi']:+.1f}%) | {r['seasons_pos']} | {r['z_train']} / {r['z_test']} |")
        lines.append('')
    open(DOC, 'w').write('\n'.join(lines))
    print(f"[angles] wrote {DOC}")


if __name__ == '__main__':
    main()
