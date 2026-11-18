# Systems validation audit (board_r10): pre-registered plan

Registered 11/18/2026 before any result of this audit was computed. The commit that adds this file is the registration; any change after
it is dated below with its reason. Read-only: no bets, no tier or live/paper changes; verdicts are recommendations for Sean.

## Question

Which live systems have a real edge, and which survived because enough variants were searched to find a lucky one?

## Scope

The live rules in the tool (tier A, B or C on 11/18) that are tied to Sean's Bet Labs Tested:/Tracked: screens (17 rules, 18 screens),
wind unders first:

| Order | Rule | Bet Labs screen(s) | Tier | Market |
|---|---|---|---|---|
| 1 | wind1014 | 1772775 | A | NFL full-game under |
| 2 | wind1014_1h | 769171 | C | NFL 1H under |
| 3 | cfb_wind14 | 1783043 | C | CFB full-game under |
| 4 | cfb_hot_over_low_total | 1792204 | B | CFB over |
| 5 | awfuldog | 1772776 | C | NFL dog spread |
| 6 | nfl_home_dog_7510 | 1799433 | C | NFL home dog spread |
| 7 | vrest8_1h | 1772962 | C | NFL 1H under |
| 8 | mnf_1h | 1772963 | C | NFL 1H under |
| 9 | cfb_homefav_7510_under | 1799440 | C | CFB under |
| 10 | nba_bigfav_over | 1799443, 1799444 | C | NBA over |
| 11 | nba_badteams_under | 1799442 | C | NBA under |
| 12 | nba_ats_hot_home | 1799432 | C | NBA home spread |
| 13 | nba_under_good_home_over | 1789285 | C | NBA under |
| 14 | nhl_early_home_fav_qual | 1789284 | B | NHL home ML |
| 15 | nhl_bounce_home_ml | 1799430 | C | NHL home ML |
| 16 | nhl_skid_fade_road | 1799431 | C | NHL visitor puck line |
| 17 | cbb_bigloss_vs_top5 | 1789287 | C | CBB spread |

Second batch, if data allows: the other live tool rules not tied to a Bet Labs screen (xch_homedog_fade, cfb_q1_under_curve,
cfb_tt_under_curve, cbb_1h_total_curve, nhl_p1_spread_curve). They were built differently (exchange tape, derivative curves); if they
cannot be put through the same gates they are listed as "insufficient data" with the reason.

## Data

- Odds and results: the Odds API history database rebuilt from the compact files in the repo (sharp/odds_db.py, then --results), seasons
  2020 to 2025-26. Results from the ESPN schedule (data/state/hist_schedule.json). The 2026 football season is not in the backfill.
- Price: Pinnacle's last quote before the start (the sharpest close available) for full-game markets. First-half NFL markets: the
  10-minutes-before-kickoff snapshot in data/oddsapi/derivs/nfl.jsonl.gz, Pinnacle where quoted, else the median of the US books (as in
  sharp/nfl_1h_replay.py); available from 2023-05 only. Each system's price source is stated in its report.
- Weather: Open-Meteo archive at kickoff (data/nfl/weather/archive.json, data/cfb/weather/archive.json), average of the kickoff hour and the
  next two. MySportsWeather (what the live wind rules now fire on) has no history before 10/29/2026, and Bet Labs' own wind is only known on
  its picks, so the wind gates test the archive wind; this is stated as a limit, not hidden.
- Records, rest days, streaks, over rates: rebuilt before each game from the ESPN schedule and the database (sharp/rule_replay.py
  profiles; ATS records from the closing spread).
- Not in the data: AP rankings (cbb_bigloss_vs_top5 cannot be replayed), Bet Labs' "number of bets vs daily average" (not needed in scope).

## Grading

Flat 1 unit risked per bet at the price above; win pays decimal - 1, loss -1, push 0. ROI = profit / bets risked. Seasons: football by
calendar year, NBA/NHL/CBB by season (August start). Regular season only (ESPN season type 2).

## Gate 1: in-sample

ROI, record, units and N for the live definition over 2020 to the season before the holdout. Flags: N < 100 (thin); ROI above +25%
(too good: check for leakage); any filter that uses information not known at bet time (closing line, open-to-close move, post-game data)
is named.

## Gate 2: permutation with the original search range (1,000 shuffles)

Keep the games, prices and filters; shuffle the bet outcomes (cover / win / over) within season x price-decile strata, so each season's
base rate and the price-outcome relation stay intact. On each shuffle re-run the whole search grid below and keep the best variant (ROI,
among variants with N >= 30). p = share of shuffles whose best variant's ROI is at least the live definition's real ROI. Pass: p < 0.05.
Where a search range cannot be reconstructed, the plain single-filter permutation (shuffle, re-run only the live definition) is run instead
and labelled as the weaker test.

Search grids (the live definition marked *):

| Rule | Grid |
|---|---|
| wind1014 | kickoff wind in [lo, hi]: lo in {8, 9, 10*, 11, 12}, hi in {12, 13, 14*, 15, 16, none}, lo < hi; outdoor only |
| wind1014_1h | same grid; live [10, 13]; outdoor only |
| cfb_wind14 | wind >= t, t in {10, 11, 12, 13, 14*, 15, 16, 17, 18} |
| cfb_hot_over_low_total | temp >= T in {80, 85*, 90}; wind <= W in {8, 10*, 12}; total <= C in {50, 55*, 60, none}; non-conference* or any |
| awfuldog | dog whose season average margin <= m after 2+ games, m in {-7, -9, -11, -13*, -15, -17} |
| nfl_home_dog_7510 | home dog, spread in [lo, hi]: lo in {6, 6.5, 7, 7.5*, 8}, hi in {9, 9.5, 10*, 10.5, 11, 14} |
| vrest8_1h | visitor days off in [lo, hi]: lo in {6, 7, 8*, 9, 10}, hi in {13, 15, 30*}; outdoor |
| mnf_1h | day in {Monday*, Thursday, Sunday night, Monday or Thursday}; outdoor |
| cfb_homefav_7510_under | home spread in [-hi, -lo]: lo in {6, 6.5, 7, 7.5*, 8}, hi in {9, 9.5, 10*, 10.5, 11, 14} |
| nba_bigfav_over | favourite no-vig probability >= t, t in {0.75, 0.78, 0.80, 0.82, 0.855*, 0.88, 0.90} |
| nba_badteams_under | home 8+ games, home win% <= h in {30, 35, 40*, 45}; visitor win% in [vlo, vhi], vlo in {25, 30*, 35}, vhi in {40, 45*, 50} |
| nba_ats_hot_home | home 8+ games, home ATS% >= a in {55, 60*, 65, 70}; days between games = r in {1, 2*, 3} |
| nba_under_good_home_over | total dropped open to close >= d in {0.5, 1, 1.5*, 2, 3}; home over% >= o in {50, 55, 58*, 62, 65}; home 1-2 and visitor 1-3 days between games |
| nhl_early_home_fav_qual | home favourite, game number <= G in {16, 20, 24*, 28, 32}; opponent win% >= w in {48, 50, 51*, 53, 55} |
| nhl_bounce_home_ml | home win% in [lo, hi]: lo in {45, 50*, 55}, hi in {60, 64*, 70}; last game lost by >= m in {2, 3*, 4} |
| nhl_skid_fade_road | visitor won its last game; home lost >= k straight, k in {2, 3*, 4, 5}; visitor puck line |

(nba_under_good_home_over: the tool's live part is the 1.5+ drop; Bet Labs' screen starts at 0.5, which is the tool's paper part.)

## Gate 3: walk-forward

For each season Y+1 from the third season on: pick the best grid variant (N >= 30) on all seasons up to Y, bet it blind in Y+1. The last
complete season (2025 for NFL/CFB, 2025-26 for NBA/NHL/CBB) is the final holdout: it is never used to choose between variants or systems;
it is bet with the variant fitted on every earlier season and reported on its own. Reported: out-of-sample ROI and N per season, pooled.

## Gate 4: walk-forward permutation (200 shuffles)

Shuffle outcomes only in the out-of-sample seasons (same strata), keep the fitted variants, recompute the pooled out-of-sample ROI.
p = share of shuffles at or above the real out-of-sample ROI. Pass: p < 0.05 with 1 out-of-sample season, p < 0.01 with 2 or more.

## Plateau

Neighbours = grid variants one step away in one parameter. Plateau = every neighbour has ROI > 0 and the median neighbour ROI is at
least half the live definition's ROI. The report recommends the middle of the plateau, not the peak.

## Verdicts (recommendations only)

- KEEP: gate 2 and gate 4 pass, N >= 100, holdout ROI > 0.
- WATCH: gate 2 passes but gate 4 fails, the holdout is <= 0, or N < 100.
- PAPER ONLY: gate 2 fails, pooled out-of-sample ROI > 0.
- RETIRE: gate 2 fails and pooled out-of-sample ROI <= 0.
- INSUFFICIENT DATA: the rule cannot be replayed on the data above.

## Multiple testing

The report counts systems and grid variants tested in total, and the number of systems expected to pass gate 2 by luck at p < 0.05.

## Reproducibility

All numbers come from sharp/validate_systems.py (fixed seed 20261118). Outputs: docs/validation/<rule>.md per system,
docs/validation/SUMMARY.md, data/research/validation.json. Nothing is computed by hand.

## Changes

- 11/18/2026: registered.
