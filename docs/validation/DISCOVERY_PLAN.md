# Discovery search (board_r10 follow-up): pre-registered plan

Registered 11/18/2026 before any discovery result was computed. Read-only: candidates found here start as paper, and promoting any is
Sean's call. Script: sharp/discover_angles.py, fixed seed 20261119. Results: docs/validation/DISCOVERY.md, data/research/discovery.json.

## What data is searched, and what is not

- Searched: the Odds API history database (Pinnacle last quote before the start, the sharpest close available), ESPN schedule results,
  and the Open-Meteo weather archive, 2020 to the 2025 / 2025-26 seasons, regular season only (same loaders as the audit). Sports: NFL,
  CFB, NBA, NHL.
- Not searched for angles: CBB (no ESPN schedule history in the repo, so no records, rest or form); Bet Labs history (the repo holds pick
  lists for 5 screens only, no game-level Bet Labs database); the tracker's paper logs (605 fills since late October; reported as a
  forward record per rule with the sample size each needs, not mined).

## Search space (fixed now)

Bets: NFL, CFB, NBA: home spread, away spread, over, under. NHL: home moneyline, away moneyline, over, under. Flat 1 unit at the Pinnacle
close.

Conditions, about the team bet on ("side") and its opponent for spreads and moneylines, about the home team for totals:

1. Role: favourite, underdog (closing line).
2. Size: closing spread (NHL: moneyline probability) or closing total in the sport's lower, middle or upper third (cut points from the
   training seasons).
3. Move, open to close: toward the side by at least m, against the side by at least m, or flat (less than half of m). Totals: up by at
   least m, down by at least m. m = 1 point (NFL, CFB, NBA spreads), 1 (NFL totals), 2 (CFB, NBA totals), 0.5 goals (NHL totals), 3
   probability points (NHL moneyline).
4. Rest: side on a back-to-back, opponent on a back-to-back, side 2+ more days of rest than the opponent (NBA, NHL); side off a bye
   (13+ days), opponent off a bye, side on a short week (5 days or fewer) (NFL); not used for CFB.
5. Form (after 8+ games NBA/NHL, 3+ NFL/CFB): side win% at least 60, at most 40; opponent win% at least 60, at most 40; side lost its
   last game by a big margin (NFL 14, CFB 21, NBA 15, NHL 3); side won its last by that margin; side on a 3+ game losing streak.
6. ATS (NFL, CFB, NBA; 4+ ATS games NFL/CFB, 8+ NBA): side ATS% at least 60, at most 40.
7. Over rate (NBA, NHL totals; 8+ games): home and visitor both at least 60%, both at most 40%.
8. Weather (NFL, CFB totals, outdoor only): wind at least 15 mph, temperature at most 32 F, temperature at least 85 F.

Candidates: every single condition, and every pair of conditions from two different families, on every bet type it applies to.
A candidate needs N >= 100 in the training seasons to be eligible.

## Seasons

- Holdout: 2025 (NFL, CFB), 2025-26 (NBA, NHL). Never used to choose or rank; reported separately.
- Training: 2020 (2020-21 NBA, 2021-22 NHL) to the season before the holdout.

## Tests

- Plain p: 1,000 shuffles of outcomes within season x price-decile strata, this candidate only.
- Search-adjusted p: on each of the same shuffles, the best eligible candidate ROI across the whole sport (every bet type and
  condition); p = share of shuffles where that best is at least the candidate's real ROI. This charges each candidate for the full
  search, the same idea as audit gate 2 but over a much larger family.
- Walk-forward of the search itself: for each season Y from the third training season through the holdout, run the search on seasons
  before Y, take the top 5 eligible candidates by ROI with plain p < 0.05, bet them blind in Y. Pooled ROI and N per sport, and a
  permutation p for it (200 shuffles of season Y outcomes, picks held fixed). This answers whether the search finds anything that lasts.
- Per candidate: holdout ROI and N, and the walk-forward ROI and N of the seasons in which the walk-forward picked it.

## Reporting

Shortlist: candidates with search-adjusted p < 0.20, plus the top 10 per sport by plain p, with N, training ROI, holdout ROI, both
p-values and a plain-English description. Tiering any candidate uses docs/validation/TIER_RULES.md; with no live record, the best a new
candidate can get is the tier its numbers earn, and Sean decides whether it goes on the board as paper.

## Changes

- 11/18/2026: registered.
