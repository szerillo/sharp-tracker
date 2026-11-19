#!/usr/bin/env python3
"""board_r10 pushback: compares the Bet Labs backtest each system was selected on with our rebuild and the live paper record, and re-tiers
with docs/validation/TIER_RULES.md version 2 (full Bet Labs backtest as primary evidence). Writes docs/validation/PUSHBACK.md and
data/research/validation_pushback.json. Read-only: no tier in the tool is changed, nothing is retired."""
import os, json, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
rd = lambda *p: json.load(open(os.path.join(ROOT, *p)))
J = rd('data', 'research', 'validation.json'); F = rd('data', 'research', 'validation_followup.json'); BW = rd('data', 'research', 'betlabs_windows.json')
# 11/19: primary source is now data/betlabs/records.json (Sean's saved screens, full backtest, per-season splits; sharp/betlabs_records.py).
# Eras from its per-season splits: seasons starting 2020 or earlier vs 2021 on. betlabs_windows.json (pulled 11/6) is the fallback.
REC = rd('data', 'betlabs', 'records.json') if os.path.exists(os.path.join(ROOT, 'data', 'betlabs', 'records.json')) else None
SRC = 'data/betlabs/records.json, pulled ' + REC['pulled_at'][:10] if REC else 'betlabs_windows.json, pulled 11/6'
def rec_windows(k):
    if not REC: return None
    S = [s for s in REC['screens'].values() if k in s.get('rules', [])]
    if not S: return None
    s = S[0]; out = {'all': dict(w=s['all_time']['w'], l=s['all_time']['l'], roi=s['all_time']['roi'])}
    for name, keep in (('to2020', lambda y: y <= 2020), ('since2021', lambda y: y >= 2021)):
        rows = [v for kk, v in s['seasons'].items() if keep(int(kk[:4]))]
        w, l, p_, u = sum(r[0] for r in rows), sum(r[1] for r in rows), sum(r[2] for r in rows), sum(r[3] for r in rows)
        out[name] = dict(w=w, l=l, roi=round(100 * u / max(1, w + l + p_), 1))
    return out
INV = {s['rule']: s for s in rd('data', 'state', 'betlabs_inventory.json')['screens'] if s.get('rule')}
OUT = os.path.join(ROOT, 'docs', 'validation', 'PUSHBACK.md'); OUTJ = os.path.join(ROOT, 'data', 'research', 'validation_pushback.json')
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
pct = lambda x: 'n/a' if x is None else f"{100 * x:+.1f}%"
OLD = {r['rule']: r['tier'] for r in F['rows']}; LIVE = {r['rule']: r['live'] for r in F['rows']}
# where the rule came from, and where our rebuild's data differs from Bet Labs' (TIER_RULES v2, check 1)
MINED = {'nba_ats_hot_home', 'nba_badteams_under', 'nba_bigfav_over', 'nhl_bounce_home_ml', 'nhl_skid_fade_road', 'cfb_homefav_7510_under', 'nfl_home_dog_7510'}
DIFFSRC = {'wind1014': 'Open-Meteo archive wind, not Bet Labs\' wind', 'cfb_wind14': 'Open-Meteo archive wind, not Bet Labs\' wind',
           'cfb_hot_over_low_total': 'Open-Meteo archive temperature and wind, not Bet Labs\' weather',
           'wind1014_1h': 'Open-Meteo wind and a Pinnacle or US-book 1H line from 2023 only', 'vrest8_1h': 'Pinnacle or US-book 1H line from 2023 only',
           'mnf_1h': 'Pinnacle or US-book 1H line from 2023 only',
           'nba_under_good_home_over': "the tool's 1.5-point total drop (the screen starts at 0.5)"}
ORDER = ['wind1014', 'wind1014_1h', 'cfb_wind14', 'cfb_hot_over_low_total', 'awfuldog', 'nfl_home_dog_7510', 'vrest8_1h', 'mnf_1h', 'cfb_homefav_7510_under',
         'nba_bigfav_over', 'nba_badteams_under', 'nba_ats_hot_home', 'nba_under_good_home_over', 'nhl_early_home_fav_qual', 'nhl_bounce_home_ml', 'nhl_skid_fade_road',
         'cbb_bigloss_vs_top5']


def ztest(w, l, roi):
    """one-sided p for ROI > 0 from a W-L record and its ROI (per-bet spread from the payout the record implies)."""
    n = w + l
    if n < 2 or roi is None or w == 0: return None, None
    r = roi / 100; b = (r * n + l) / w; p = w / n; var = p * b * b + (1 - p) - r * r
    z = r / math.sqrt(var / n); return z, 1 - Phi(z)


def rec(x): return f"{x['w']}-{x['l']}, {x['roi']:+.1f}%" if x else 'n/a'


rows = []
for k in ORDER:
    W = rec_windows(k) or BW['rules'].get(k, {}); A, E1, E2 = W.get('all'), W.get('to2020'), W.get('since2021'); I = INV.get(k, {})
    za, pa = ztest(A['w'], A['l'], A['roi']) if A else (None, None)
    z1, p1 = ztest(E1['w'], E1['l'], E1['roi']) if E1 else (None, None)
    z2, p2 = ztest(E2['w'], E2['l'], E2['roi']) if E2 else (None, None)
    R = J.get(k); n_all = A['w'] + A['l'] if A else 0
    both = bool(E1 and E2 and E1['roi'] > 0 and E2['roi'] > 0)
    # base tier from the full backtest
    if A and n_all >= 300 and pa < 0.01 and both and p2 is not None and p2 < 0.10: base = 'A'
    elif A and pa is not None and pa < 0.05 and both: base = 'B'
    else: base = 'C'
    notes, tier = [], base
    if base == 'C':
        if not A: notes.append('No Bet Labs window record on file for this screen, so the full backtest cannot be scored.')
        elif E1 and E1['roi'] <= 0: notes.append(f"Bet Labs' own record before 2021 is {rec(E1)}: the edge exists only from 2020 on, which is the same window it was found in.")
        elif pa is not None and pa >= 0.05: notes.append(f"Bet Labs' all-time record ({rec(A)}) is not strong enough to rule out luck (p {pa:.3f}).")
    elif base == 'B':
        why = []
        if n_all < 300: why.append(f"only {n_all} all-time bets")
        if pa >= 0.01: why.append(f"all-time p {pa:.3f}, above 0.01")
        if p2 is None or p2 >= 0.10: why.append(f"the Mar 2021 on era ({rec(E2)}) is not significant on its own (p {p2:.2f})")
        notes.append('Reduced size because ' + ' and '.join(why) + '.')
    # overfitting check 1: our rebuild on the same kind of data shows nothing
    rebuild_flag = None
    if R:
        dead = (R['roi'] or 0) <= 0 and (R['wf_roi'] or 0) <= 0
        if dead and k in DIFFSRC: rebuild_flag = f"Our rebuild shows no edge, but it used {DIFFSRC[k]}; our rebuild may be the weak part, so no downgrade."
        elif dead and tier != 'C':
            tier = 'B' if tier == 'A' else 'C'
            notes.append(f"Down one tier: our own rebuild on the same kind of data (Pinnacle closes, 2020 to 2025) shows no edge: in-sample {pct(R['roi'])} on {R['n']}, blind {pct(R['wf_roi'])} on {R['wf_n']}.")
        elif k in DIFFSRC: rebuild_flag = f"Our rebuild used {DIFFSRC[k]}."
    if I.get('status') == 'DIFFERENT FILTERS': notes.append("Flag, no move: the tool's live filter differs from this saved screen (11/18 inventory).")
    if not notes and tier == 'A': notes.append('Meets every Tier A bar on the full Bet Labs backtest.')
    # reproduction check: our rebuild vs Bet Labs over the overlapping recent era
    repro = None
    if R and E2:
        ours = R['roi'] or 0; bl = E2['roi'] / 100
        repro = 'n/a (Bet Labs negative too)' if bl <= 0 else 'yes' if ours >= 0.5 * bl else 'partly' if ours > 0 else 'no'
        if repro in ('partly', 'no') and k in DIFFSRC and not rebuild_flag:
            rebuild_flag = f"Our rebuild {'only partly reproduces' if repro == 'partly' else 'does not reproduce'} Bet Labs ({pct(ours)} vs {E2['roi']:+.1f}% since 2021), but it used {DIFFSRC[k]}; our rebuild may be the weak part, so no downgrade."
    if R and (R['wf_roi'] or 0) <= 0 and not any('Down one tier' in x for x in notes):
        notes.append(f"Flag, no move: our blind walk-forward was {pct(R['wf_roi'])} on {R['wf_n']} bets.")
    rows.append(dict(rule=k, origin='mined from our 2020-26 data, screen saved 10/28 to 11/3' if k in MINED else "Sean's Bet Labs screen", screen=I.get('id'),
                     screen_status=I.get('status'), bl_all=A, bl_to2020=E1, bl_since2021=E2, p_all=pa, p_to2020=p1, p_since2021=p2,
                     rebuild=dict(n_in=R['n'], roi_in=R['roi'], n_hold=R['holdout_n'], roi_hold=R['holdout_roi'], wf_n=R['wf_n'], wf_roi=R['wf_roi'], seasons=R['seasons'],
                                  price=R['price'], p_single=R['p_single']) if R else None,
                     live=LIVE.get(k), old_tier=OLD.get(k, 'C'), base=base, tier=tier, notes=notes, rebuild_flag=rebuild_flag, reproduces=repro))

D = ['# Pushback on the tiers (board_r10, Sean 11/18)', '',
     'Built by sharp/validate_pushback.py. Tier rules: [TIER_RULES.md](TIER_RULES.md), version 2, committed before this scoring. Recommendations only: no tier in the tool '
     'was changed and nothing is retired.', '',
     f"Bet Labs numbers: {SRC} (sharp/betlabs_records.py; the full backtest of each saved screen, refreshed with the Bet Labs pull). "
     "Re-scored 11/19 on it: the only tier that moves against the 11/18 scoring is nfl_home_dog_7510, B to C, after its 0-3 start since it was saved "
     "(all-time 119-87 now, p 0.071). Sean approved it on 11/19 and the board now shows it as Tier C (still bettable at 0.25u).", '',
     '## Short answer', '',
     "Sean is right about the evidence that drove the first verdicts. They rested on our rebuild, which only covers 2020 to 2025 (the Odds API history starts in 2020), uses "
     "Pinnacle closes, and uses our own weather and 1H data. His systems were selected on Bet Labs backtests that go back to 2003 and are often 3 to 5 times larger. For "
     "his own Bet Labs screens the bigger backtest should be the primary evidence, and the re-tier below uses it.", '',
     "Two things still hold. First, seven of the live rules were not Bet Labs screens to begin with. They were mined from our 2020-26 data in late October (out of "
     "roughly 100,000 tests per sport) and saved as screens afterwards. For those, the 2020-26 record is the sample they were picked on, and Bet Labs' record before 2021 is "
     "the real test: for five of the seven, it is negative. Second, where our rebuild could not reproduce a Bet Labs record because it used different data (wind, 1H lines), "
     "that is now treated as a weakness in our rebuild, not in the system.", '',
     "One caution that still applies to the Bet Labs numbers: Sean's saved Tested:/Tracked: screens are the survivors of the screens he built on that same Bet Labs history, so "
     "their p-values are in-sample too. That is why Tier A also needs both eras positive and the Mar 2021 on era to stand on its own (p < 0.10).", '',
     '## 1. Which sample drove each verdict', '',
     f"(a) Bet Labs as reported on the saved screen, at Bet Labs' prices, all years from 2003 ({SRC}; eras split by season: 2020 and earlier vs 2021 on). (b) Our rebuild: Odds API, Pinnacle close, "
     "2020 to 2025 (NFL 1H 2023 to 2025), in-sample plus the 2025 / 2025-26 holdout. (c) Live paper record from fills.jsonl. \"Reproduces\" = our rebuild and Bet Labs' "
     "Mar 2021 on record are both positive, ours at least half of Bet Labs' ROI; partly = ours positive but smaller.", '',
     '| System | Origin | (a) Bet Labs all-time | (a) seasons to 2020 | (a) seasons 2021 on | (b) Our rebuild in-sample | (b) Holdout | (b) Data | (c) Live | Reproduces |',
     '|---|---|---|---|---|---|---|---|---|---|']
for r in rows:
    b = r['rebuild']; L = r['live'] or {}
    D.append(f"| {r['rule']} | {r['origin']} | {rec(r['bl_all'])}{f' (p {r['p_all']:.3f})' if r['p_all'] is not None else ''} | {rec(r['bl_to2020'])} | {rec(r['bl_since2021'])} | "
             + (f"{b['n_in']} bets, {pct(b['roi_in'])} ({b['seasons'][0]} to {b['seasons'][-2]}) | {b['n_hold']}, {pct(b['roi_hold'])} | {DIFFSRC.get(r['rule'], b['price'])} | " if b else "not rebuilt | | AP ranks not in our data | ")
             + (f"{L['w']}-{L['l']}, {L['units']:+.1f}u" if L.get('n') else 'none') + f" | {r['reproduces'] or 'n/a'} |")
big = [r for r in rows if r['bl_all'] and r['rebuild'] and (r['bl_all']['w'] + r['bl_all']['l']) >= 3 * (r['rebuild']['n_in'] + r['rebuild']['n_hold'])]
D += ['', f"Our rebuild is less than a third the size of the Bet Labs sample for {len(big)} of {len(rows)} systems ({', '.join(r['rule'] for r in big)}), because the "
      "Odds API history starts in 2020 and Bet Labs goes back to 2003. Bet Labs' records are at its own prices, not Pinnacle's close.", '',
      "Our rebuild did not reproduce (or only partly reproduced, under half the ROI) Bet Labs' Mar 2021 on record for: " + ', '.join(f"{r['rule']} ({r['reproduces']}; {DIFFSRC.get(r['rule'], 'same kind of data')})" for r in rows if r['reproduces'] in ('no', 'partly')) +
      ". Where the data differs, it may be our rebuild, not the system, that is weak.", '',
      '## 2. Did the live record drive any downgrade?', '',
      "No. The first audit's verdicts did not use it at all. The first tiering (FOLLOWUP.md) blended it in. Re-running that tiering on history alone gives the same tier "
      "for every system: the live record moved some probabilities (nhl_early_home_fav_qual 0.96 to 0.93, cfb_homefav_7510_under 0.89 to 0.85, cfb_wind14 0.31 to 0.66) "
      "but crossed no tier line. In version 2 below it is not used at all, except as a tiebreak, and no tiebreak was needed.", '',
      '## 3. The search penalty: how many variants were assumed', '',
      "The variant counts were my guess, not a record of what Sean or Bet Labs tried. For each rule I built a grid of nearby versions (6 to 75 per rule: wind bands, spread "
      "ranges, win% cutoffs) and charged the system for the best of them. Bet Labs does not save the variants tried before a screen is saved, and Sean's saved Tested:/Tracked: "
      "screens hold one version per rule (two for nba_bigfav_over, the home and visitor sides of the same rule). So, as Kirk asked, version 2 drops the search penalty and "
      "uses the plain single-filter test plus the full Bet Labs record. The search penalty did matter for the seven mined rules: for those the search was real and larger "
      "than my grids (about 100,000 tests per sport), which is why their pre-2021 Bet Labs record is the test that counts.", '',
      '## 4. Re-tier (full backtest primary)', '',
      '| System | Before (follow-up) | After (v2) | Bet Labs all-time p | Mar 2021 on p | Why, in one sentence each |', '|---|---|---|---|---|---|']
for r in rows:
    why = ' '.join(r['notes'] + ([r['rebuild_flag']] if r['rebuild_flag'] else []))
    D.append(f"| {r['rule']} | {r['old_tier']} | **{r['tier']}** | {'n/a' if r['p_all'] is None else f'{r['p_all']:.4f}'} | {'n/a' if r['p_since2021'] is None else f'{r['p_since2021']:.3f}'} | {why} |")
D += ['', 'Not in this table: xch_homedog_fade and the four curve rules (no Bet Labs screen and no multi-season replay; they stay where Sean has them).', '']
open(OUT, 'w').write('\n'.join(D) + '\n'); json.dump(rows, open(OUTJ, 'w'), indent=1, default=str)
for r in rows: print(r['rule'], r['old_tier'], '->', r['tier'], r['p_all'] and round(r['p_all'], 4), r['p_since2021'] and round(r['p_since2021'], 3), r['reproduces'], '|', ' '.join(r['notes'])[:150])
