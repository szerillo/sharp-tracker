#!/usr/bin/env python3
"""Builds docs/validation/SUMMARY.md from data/research/validation.json (written by sharp/validate_systems.py). No new numbers here:
it only ranks and formats what the audit script computed, plus the multiple-testing count from the same file."""
import os, json, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
J = json.load(open(os.path.join(ROOT, 'data', 'research', 'validation.json'))); OUT = os.path.join(ROOT, 'docs', 'validation', 'SUMMARY.md')
ORDER = ['wind1014', 'wind1014_1h', 'cfb_wind14', 'cfb_hot_over_low_total', 'awfuldog', 'nfl_home_dog_7510', 'vrest8_1h', 'mnf_1h', 'cfb_homefav_7510_under',
         'nba_bigfav_over', 'nba_badteams_under', 'nba_ats_hot_home', 'nba_under_good_home_over', 'nhl_early_home_fav_qual', 'nhl_bounce_home_ml', 'nhl_skid_fade_road']
INSUFF = [('cbb_bigloss_vs_top5', 'CBB spread', 'needs AP top-5 rankings at game time; not in the data'),
          ('xch_homedog_fade', 'exchange tape', 'built on exchange order flow (2025-26 only); no multi-season history to permute or walk forward'),
          ('cfb_q1_under_curve', 'CFB 1Q total', 'derivative curve lines exist only from 2023; one in-sample season before the holdout'),
          ('cfb_tt_under_curve', 'CFB team total', 'derivative curve lines exist only from 2023; one in-sample season before the holdout'),
          ('cbb_1h_total_curve', 'CBB 1H total', 'no CBB derivative (1H) line history in the repo'),
          ('nhl_p1_spread_curve', 'NHL 1P spread', 'no NHL period line history in the repo')]
RANK = {'KEEP': 0, 'WATCH': 1, 'PAPER ONLY': 2, 'RETIRE': 3, 'INSUFFICIENT DATA': 4}
pct = lambda x: 'n/a' if x is None else f"{100 * x:+.1f}%"
p3 = lambda x: 'n/a' if x is None else f"{x:.3f}"


def why(R):
    v = R['verdict']; g = f"grid p {p3(R['p_grid'])}"; w = f"walk-forward {pct(R['wf_roi'])} on {R['wf_n']}"
    if v == 'KEEP': return f"survives the full search ({g}) and holds out of sample ({w}, p {p3(R['p_wf'])})"
    if v == 'WATCH':
        bits = []
        if R['p_wf'] is None or R['p_wf'] >= R['wf_bar']: bits.append(f"out-of-sample not significant (p {p3(R['p_wf'])})")
        if (R['holdout_roi'] or 0) <= 0: bits.append(f"holdout {pct(R['holdout_roi'])}")
        if R['n'] < 100: bits.append(f"only {R['n']} bets")
        return f"passes the search test ({g}) but " + ', '.join(bits)
    if v == 'PAPER ONLY':
        s = f"edge is within what searching {R['grid_size']} variants finds by luck ({g}); {w}"
        if R['p_wf'] is not None and R['p_wf'] < R['wf_bar']: s += f", itself significant (p {p3(R['p_wf'])})"
        return s
    if v == 'RETIRE': return f"no edge beyond search luck ({g}) and {w}"
    return f"only {R['n']} in-sample bets"


rows = sorted([J[k] for k in ORDER if k in J], key=lambda R: (RANK[R['verdict']], R['p_grid'] if R['p_grid'] is not None else 9))
done = [k for k in ORDER if k in J]; todo = [k for k in ORDER if k not in J]
n_var = sum(R['grid_size'] for R in rows); n_sys = len(rows)
L = ['# Systems validation audit (board_r10): summary', '',
     f"Built {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC by sharp/validate_summary.py from data/research/validation.json. Plan: [VALIDATION_PLAN.md](VALIDATION_PLAN.md) (registered before any result). "
     "Read-only: verdicts are recommendations; no tier or live/paper status was changed.", '']
TOP = os.path.join(ROOT, 'docs', 'validation', '_read.md')
if os.path.exists(TOP) and not todo: L += open(TOP).read().rstrip().split('\n') + ['']
if todo: L += [f"**Checkpoint: {len(done)} of {len(ORDER)} replayable systems done. Still running: {', '.join(todo)}.**", '']
L += ['## Ranked table', '', '| # | System | Sport | N | ROI | Permutation p (grid) | p (single filter, weaker) | Walk-forward OOS ROI (N) | Holdout ROI (N) | Plateau | Verdict | Reason |',
      '|---|---|---|---|---|---|---|---|---|---|---|---|']
for i, R in enumerate(rows, 1):
    L.append(f"| {i} | [{R['rule']}]({R['rule']}.md) | {R['sport'].upper()} | {R['n']} | {pct(R['roi'])} | {p3(R['p_grid'])} | {p3(R['p_single'])} | {pct(R['wf_roi'])} ({R['wf_n']}) | "
             f"{pct(R['holdout_roi'])} ({R['holdout_n']}) | {'yes' if R['plateau'] else 'no'} | {R['verdict']} | {why(R)} |")
for k, mk, r in INSUFF:
    L.append(f"| - | {k} | {mk} | - | - | - | - | - | - | - | INSUFFICIENT DATA | {r} |")
exp = 0.05 * n_sys
L += ['', 'N and ROI are in-sample (2020 to the season before the holdout), flat 1 unit at the price stated in each report. Walk-forward OOS covers every season from the third on, '
      'holdout included, each bet with the variant fitted on earlier seasons only.', '',
      '## Multiple testing', '',
      f"{n_sys} systems and {n_var} grid variants were tested. Gate 2 already corrects for each system's own grid (best variant per shuffle). Across systems, about "
      f"{exp:.1f} of {n_sys} would pass gate 2 at p < 0.05 by luck alone; {sum(1 for R in rows if R['p_grid'] is not None and R['p_grid'] < 0.05)} did. "
      f"With a Bonferroni bar across systems (0.05 / {n_sys} = {0.05 / max(1, n_sys):.4f}), {sum(1 for R in rows if R['p_grid'] is not None and R['p_grid'] < 0.05 / max(1, n_sys))} pass.", '',
      '## Limits', '',
      '- Wind: the gates test Open-Meteo archive wind, not MySportsWeather (no history before 10/29/2026) or Bet Labs\' own wind. A bet placed on a forecast sees a different number.',
      '- NFL first-half lines exist from 2023-05 only, so the 1H rules have 3 seasons (2023 to 2025): one walk-forward season before the holdout.',
      '- Filters that use the closing number (spread, total, moneyline, open-to-close move) are graded at that same close; a bet placed earlier sees a different number, so the live edge can be smaller.',
      '- 2026 football and the 2026-27 NBA/NHL seasons are partial and are left out of every gate.', '']
open(OUT, 'w').write('\n'.join(L) + '\n'); print(OUT, len(rows), 'rows')
