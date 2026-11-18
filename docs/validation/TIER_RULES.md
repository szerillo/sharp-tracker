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

## Changes

- 11/18/2026: written.
