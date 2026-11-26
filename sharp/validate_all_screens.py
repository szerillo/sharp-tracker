#!/usr/bin/env python3
"""11/25 (Sean via Kirk): TIER_RULES.md version 2, applied exactly as written (thresholds unchanged, no tuning), to EVERY saved Bet Labs screen
labeled Tested: or Tracked: in data/betlabs/records.json (cross-checked against data/state/betlabs_inventory.json), not only the 17 scored on
11/18-19. Same z-test and era split as sharp/validate_pushback.py. Writes data/research/validation_all_screens.json. Read-only scoring; the
tier changes it supports are applied in sharp/systems.py with a dated note."""
import os, sys, json, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
rd = lambda *p: json.load(open(os.path.join(ROOT, *p)))
REC = rd('data', 'betlabs', 'records.json'); INVF = rd('data', 'state', 'betlabs_inventory.json')
INV = {str(s['id']): s for s in INVF['screens']}
J = rd('data', 'research', 'validation.json')          # our rebuild with a blind walk-forward (16 rules); check 1 needs both numbers
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
DIFFSRC = {'wind1014': "Open-Meteo archive wind, not Bet Labs' wind", 'cfb_wind14': "Open-Meteo archive wind, not Bet Labs' wind",
           'cfb_hot_over_low_total': "Open-Meteo archive temperature and wind, not Bet Labs' weather",
           'wind1014_1h': 'Open-Meteo wind and a Pinnacle or US-book 1H line from 2023 only', 'vrest8_1h': 'Pinnacle or US-book 1H line from 2023 only',
           'mnf_1h': 'Pinnacle or US-book 1H line from 2023 only', 'nba_under_good_home_over': "the tool's 1.5-point total drop (the screen starts at 0.5)"}


def ztest(w, l, roi):
    n = w + l
    if n < 2 or roi is None or w == 0: return None
    r = roi / 100; b = (r * n + l) / w; p = w / n; var = p * b * b + (1 - p) - r * r
    return 1 - Phi(r / math.sqrt(var / n))


def era(s, keep):
    rows = [v for k, v in s['seasons'].items() if keep(int(k[:4]))]
    w, l, p_, u = (sum(r[i] for r in rows) for i in range(4))
    return dict(w=w, l=l, p=p_, units=round(u, 2), roi=round(100 * u / max(1, w + l + p_), 1))


rec = lambda x: f"{x['w']}-{x['l']}, {x['roi']:+.1f}%"
sys.path.insert(0, os.path.join(ROOT, 'sharp'))
import systems as S      # current board tier per rule
# board tier before the 11/25 changes this scoring led to (systems.py TIER_1125)
PRE_1125 = {'bounce15_1h': 'P', 'nhl_pl_fav_gap': 'P', 'nhl_pl_fav_strong_opp': 'P', 'nhl_pl_dog_bigml': 'C', 'nba_1h_under_hot_over': 'C',
            'cfb_road_dog_low_total': 'C', 'cbb_under_good_over_drop': 'P', 'cfb_road_streak_dog': 'P'}
rows = []
for sid, s in REC['screens'].items():
    A = s['all_time']; E1 = era(s, lambda y: y <= 2020); E2 = era(s, lambda y: y >= 2021)
    n_all = A['w'] + A['l']; pa = ztest(A['w'], A['l'], A['roi']); p1 = ztest(E1['w'], E1['l'], E1['roi']); p2 = ztest(E2['w'], E2['l'], E2['roi'])
    both = E1['roi'] > 0 and E2['roi'] > 0
    if n_all >= 300 and pa is not None and pa < 0.01 and both and p2 is not None and p2 < 0.10: base = 'A'
    elif pa is not None and pa < 0.05 and both: base = 'B'
    else: base = 'C'
    rule = (s.get('rules') or [None])[0]; I = INV.get(sid, {}); tier = base; notes = []
    if base == 'C':
        if E1['roi'] <= 0 and E2['roi'] <= 0: notes.append(f"Negative in both eras ({rec(E1)} to 2020, {rec(E2)} from 2021).")
        elif E1['roi'] <= 0: notes.append(f"Bet Labs' own record to 2020 is {rec(E1)}: the edge exists only from 2021 on.")
        elif E2['roi'] <= 0: notes.append(f"The Mar 2021 on era is {rec(E2)}: not positive in both eras.")
        elif pa is None or pa >= 0.05: notes.append(f"All-time {rec(A)} is not strong enough to rule out luck (p {pa:.3f}).")
    elif base == 'B':
        why = []
        if n_all < 300: why.append(f"only {n_all} all-time bets")
        if pa >= 0.01: why.append(f"all-time p {pa:.3f}, above 0.01")
        if p2 is None or p2 >= 0.10: why.append(f"the Mar 2021 on era ({rec(E2)}) is not significant on its own (p {p2:.2f})")
        notes.append('B, not A, because ' + ' and '.join(why) + '.')
    else: notes.append('Meets every Tier A bar.')
    # overfitting check 1 (needs our in-sample AND blind walk-forward ROI, both <= 0, on the same kind of data)
    R = J.get(rule)
    if R:
        dead = (R['roi'] or 0) <= 0 and (R['wf_roi'] or 0) <= 0
        if dead and rule in DIFFSRC: notes.append(f"Flag, no move: our rebuild shows no edge but used {DIFFSRC[rule]}.")
        elif dead and tier != 'C':
            tier = 'B' if tier == 'A' else 'C'
            notes.append(f"Down one tier (check 1): our rebuild on the same kind of data shows no edge (in-sample {100 * R['roi']:+.1f}%, blind {100 * R['wf_roi']:+.1f}%).")
        elif (R['wf_roi'] or 0) <= 0: notes.append(f"Flag, no move: our blind walk-forward was {100 * R['wf_roi']:+.1f}% on {R['wf_n']} bets (in-sample {100 * R['roi']:+.1f}%).")
    elif base != 'C': notes.append('Check 1 not applicable: no blind walk-forward of ours on file for this rule (the 11/5 replays are in-sample only), so no move.')
    if I.get('status') == 'DIFFERENT FILTERS': notes.append("Flag, no move (check 2): the tool's live filter differs from the saved screen.")
    e = S.EVIDENCE.get(rule, {}); cur = PRE_1125.get(rule, e.get('tier'))
    rows.append(dict(screen=int(sid), name=s['name'], kind=s['name'].split(':')[0], sport=s.get('sport'), rule=rule, current=cur,
                     current_live=cur in ('A', 'B', 'C'), inv_status=I.get('status'), all_time=dict(A, n_wl=n_all), to2020=E1, since2021=E2,
                     since_saved=s.get('since_saved'), p_all=pa, p_to2020=p1, p_since2021=p2, both_eras=both, base=base, tier=tier, notes=notes,
                     rescored_1118=rule in ('wind1014', 'wind1014_1h', 'cfb_wind14', 'cfb_hot_over_low_total', 'awfuldog', 'nfl_home_dog_7510', 'vrest8_1h', 'mnf_1h',
                                            'cfb_homefav_7510_under', 'nba_bigfav_over', 'nba_badteams_under', 'nba_ats_hot_home', 'nba_under_good_home_over',
                                            'nhl_early_home_fav_qual', 'nhl_bounce_home_ml', 'nhl_skid_fade_road', 'cbb_bigloss_vs_top5')))
out = dict(built=REC['pulled_at'], rules='docs/validation/TIER_RULES.md version 2, unchanged', inventory_built=INVF['built'],
           records_missing_from_pull=REC.get('missing_from_pull'), not_in_inventory=[r['screen'] for r in rows if str(r['screen']) not in INV],
           inventory_not_in_records=[s for s in INV if s not in REC['screens']], rows=rows)
json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'validation_all_screens.json'), 'w'), indent=1)
if __name__ == '__main__':
    for r in rows:
        print(r['screen'], r['rule'], r['current'], '->', r['tier'], f"n{r['all_time']['n_wl']} p{r['p_all']:.4f}" if r['p_all'] is not None else 'p-', rec(r['to2020']), '|', rec(r['since2021']),
              f"p2 {r['p_since2021']:.3f}" if r['p_since2021'] is not None else '', '|', ' '.join(r['notes'])[:200], '| 1118' if r['rescored_1118'] else '')
    print('not in inventory', out['not_in_inventory'], 'inv not in records', out['inventory_not_in_records'])
