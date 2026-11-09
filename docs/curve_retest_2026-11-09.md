# Curve leans: retest after the live start (11/9)

Live since 11/6 (data/state/curve_paper.jsonl): NHL third-period unders 0-8 (one push), CFB first-quarter unders 4-7, CFB team-total
unders 5-11, NHL first-period spreads 2-2.

## 1. Correction: closing line value is the wrong yardstick here
Earlier tonight I said the curve was "off" because 0 of 16 curve leans beat Pinnacle's derivative close. That was a mistake. These rules
bet only when the curve disagrees with Pinnacle's derivative price by 5-7 points, so losing to Pinnacle's close is built in: Pinnacle's
close sits near its own price at the flag. Like the systems, the curve leans are judged on results.

## 2. Grading is correct
Every live NHL and CFB row was checked against ESPN's period scores and finals (schedule.json). The third periods really did have 3+
goals in 7 of 9 games; the team totals graded the right team.

## 3. NHL third-period unders: two real problems
**This season's third periods score more.** Goals per third period:

| Season | Games | Third-period goals | Under 2.0 (no push) |
|---|---|---|---|
| 2023 | 1,399 | 2.12 | 0.499 |
| 2024 | 1,315 | 2.16 | 0.485 |
| 2025 | 1,305 | 2.15 | 0.492 |
| 2026 (Jan-Jun) | 183 | 2.10 | 0.500 |
| 2026-27 so far | 84 | **2.44** | **0.339** |

The curve treats every past season alike, so it still prices the third period at the 2023-25 rate. Pinnacle has moved: its under 2.0
sits at 0.43-0.46. 84 games is small (the gap is about 2 standard errors), but it is the direction the live losses point.

**The fires come from one noisy cell.** The curve matches past games on the full-game total and the home spread. In the NHL the spread
is the puck line, always plus or minus 1.5, so it only says which team is favoured. 7 of the 8 under-2.0 fires came from the same
inputs (total 6.5, home team +1.5), where the curve reads 0.547. The same total with the home team -1.5 reads 0.496; total 6.0 reads
0.466. A 5-point swing on the puck-line sign is sampling noise in a few hundred neighbours, and the rule fires exactly where the noise
runs high.

The backtest itself is clean: each game was priced only from other seasons (sharp/deriv_curve.py, leave-one-season-out), so the
243-185 record is not in-sample. It was earned in seasons whose scoring matched the pool.

**Recommendation:** hold nhl_p3_under_curve. Fix two things before it fires again: (a) scale period scoring by the current season's share
(season to date, shrunk toward the pool until about 300 games); (b) match NHL games on the moneyline-implied strength instead of the
puck line. Then re-run the backtest walk-forward (prior seasons only) and check that the fires are not concentrated in one cell.

## 4. CFB first-quarter and team-total unders: variance so far
- This season's first quarters score less, not more: 19.7% of the final score against 21.4-22.3% in every pool season (117 games). That
  helps the unders.
- At the backtest win rates (first quarter 61%, team totals 54%), 4-7 and 5-11 are unlucky (about a 4% and 6% chance) but not evidence
  the rule broke. Keep both as they are.

## 5. Every curve rule could carry the same blind spot
None of the curve rules adjusts for the current season. NHL is where it bit first because the third-period shift is large. The same
season-share fix should go into all of them.
