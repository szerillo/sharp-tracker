# Sizing tiers for validated systems (board_r10 follow-up)

Written 11/18/2026 at Sean's request, to replace the keep / watch / paper only / retire verdicts with tiers he can size from. Committed
before the re-scoring script was run. Honest limit: the inputs (walk-forward results, p-values, the live record) were already visible from
the first audit and Kirk's pull, so this is not blind the way VALIDATION_PLAN.md was. The thresholds below were written once and are not
tuned afterwards; any later change is dated at the bottom with its reason. Recommendations only: no tier in the tool is changed by this.

## Inputs per system (all from sharp/validate_systems.py and sharp/validate_followup.py)

- Walk-forward (WF): every season from the third on, bet blind with the variant fitted on earlier seasons only. ROI, N, and its gate 4
  permutation p (p_wf). This is the main evidence, because the variant is never chosen on the seasons it is scored on.
- Search-adjusted p (p_grid, gate 2) and plain single-filter p (p_single), in-sample.
- Live record: data/state/fills.jsonl, graded fills for the rule's tag (paper prefix ignored), voids excluded, per unit risked at the
  filled price.
- Combined estimate: a normal (precision-weighted) update. Prior = WF ROI with standard error sd / sqrt(N_wf), sd = the per-bet profit
  standard deviation in the walk-forward bets. Live = live ROI with standard error sd / sqrt(N_live), using the same sd (a live sample
  this small cannot estimate its own spread). Output: combined ROI, its standard error, and P(true ROI > 0).

## Tiers

- **Tier A, real money, full size.** All of: p_wf < 0.01; WF N >= 100; WF ROI >= +5%; combined P(ROI > 0) >= 0.975; p_grid < 0.20 or
  a live record of 50+ bets with ROI > 0; and no live collapse (not 20+ live bets at ROI <= -10%).
  Why p_grid still counts here: Sean built most screens while able to see every season, holdout included, so the walk-forward does
  not fully remove the search. A weak search-adjusted bar (0.20, not 0.05) or a real forward record covers that gap.
- **Tier B, real money, reduced size (half of Tier A).** Not Tier A, and all of: combined P(ROI > 0) >= 0.90; WF N >= 60; WF ROI > 0;
  p_wf < 0.05 or p_single < 0.05; no live collapse.
- **Tier C, paper.** Everything else. Logged and graded, no money.
- **Retire flag (Sean decides).** Combined ROI <= 0 and the live record is not winning (live units <= 0, or no live bets). A system
  that is winning live is never flagged on the historical test alone; it stays Tier C at worst.
- Systems with no replayable history (insufficient data) can reach Tier C only, whatever the live record, until a replay exists.

## Why these numbers

- P(ROI > 0) of 0.975 and 0.90 are the one-sided 2-sigma and 1.3-sigma points; full size needs the stronger one.
- WF N of 100 and 60: below about 60 blind bets at -110 the standard error of ROI is above 12 points, wider than any edge here.
- +5% WF ROI for full size: below that, ordinary price variation between shops and the close eats most of the edge.

## Version 2 (11/18/2026, after Sean's pushback): full backtest as the primary evidence

Written before re-scoring. Supersedes the tiers above; version 1 is kept for the record. Recommendations only, and nothing is retired.

Primary evidence: the Bet Labs record on Sean's saved screen as Bet Labs reports it at its own prices. Source from 11/19: data/betlabs/records.json
(sharp/betlabs_records.py; all-time record, per-season splits, record since saved, refreshed with the Bet Labs pull; history in records_history.jsonl).
Eras: seasons starting 2020 or earlier vs 2021 on, summed from its per-season splits. Before 11/19: data/research/betlabs_windows.json (pulled 11/6;
all years from 2003, 2003 to Feb 2021, Mar 2021 on). Significance is a one-sided z-test of ROI, with each window's per-bet spread worked out from
its own W-L and ROI (the average payout implied by them).

- **Tier A, full size.** Bet Labs all-time N >= 300 and p < 0.01; both eras (2003 to Feb 2021, Mar 2021 on) positive; the Mar 2021 on era p < 0.10.
- **Tier B, reduced size.** Not A, and: all-time p < 0.05 with both eras positive.
- **Tier C, paper.** Everything else, including any system whose edge exists only from 2020 on in Bet Labs (2003 to Feb 2021 negative or flat).

Overfitting checks (each moves a system down at most one tier, and each is written as one plain sentence in PUSHBACK.md):

1. Our own rebuild, on the same kind of data, shows no edge: in-sample ROI <= 0 and blind walk-forward ROI <= 0. If our rebuild used a different
   data source than Bet Labs (Open-Meteo instead of Bet Labs' wind, a US-book or Pinnacle 1H line, a different filter definition), it does not move
   the tier; it is flagged as "our rebuild may be the weak part".
2. The tool's live filter differs from the saved screen it is tested on ("different filters" in the 11/18 inventory): flagged, no move.

Not used: the live paper record (only as a tiebreak between two otherwise equal systems; none needed it), and the search-adjusted p, since the
variants Sean tried are not recorded anywhere. The plain single-filter p is shown instead.

## Changes

- 11/18/2026: written.
- 11/18/2026, later: version 2 added after Sean's pushback (full Bet Labs backtest as primary evidence).
- 11/19/2026: primary evidence source moved to data/betlabs/records.json (Sean's saved screens' full backtests, logged on every Bet Labs pull). Thresholds unchanged.
- 11/19/2026: nfl_home_dog_7510 moved from Tier B to Tier C on the board (Sean approved the PUSHBACK.md re-score: 0-3 since saved, all-time 119-87, p 0.071). Still bettable at 0.25u.
- 11/25/2026 (Sean via Kirk): version 2 applied, unchanged, to all 32 saved Tested:/Tracked: screens, not only the 17 scored on 11/18-19 (PUSHBACK.md section 5, sharp/validate_all_screens.py). To real money at 0.25u for games from 2026-11-26 00:30Z: bounce15_1h (paper to B), nhl_pl_fav_gap (paper to A), nhl_pl_fav_strong_opp (paper to A), nhl_pl_dog_bigml (C to A), nba_1h_under_hot_over (C to B), cfb_road_dog_low_total (C to B), cbb_under_good_over_drop (paper to B), cfb_road_streak_dog (paper to B). The tool splits nba_under_good_home_over_small and wind1014_cold follow their passing screens (tier A). Failures stay paper or tier C; nothing retired. Check 1 is applied only where a blind walk-forward of ours exists.
- 11/25/2026: vrest8_1h and mnf_1h match Bet Labs' Dome Closed flag for SoFi (counted as open); other roofed venues stay excluded.
