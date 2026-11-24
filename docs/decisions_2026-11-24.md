# Decisions applied 2026-11-24 (Sean, via Kirk)

Approved by Sean on 11/24 about 12:35 PM ET; applied in code the same afternoon. Cutoff for every change below: games starting from
**2026-11-24 19:00 UTC (2:00 PM ET)**. Games that started earlier keep the status they were tracked under, so no record is re-scored
backwards. Paper and logging only: nothing here places a bet.

## Status changes (rule: old -> new)

| # | Rule | Old | New | Why (one sentence) |
|---|---|---|---|---|
| 1 | nhl_p3_under_curve | tier C (0.25u) | paper | Forward 9-22, -44% on 42 with both halves negative, and the 11/9 fixes are still not in the curve. |
| 2 | nhl_skid_fade_road | tier C | paper | Mined on 2020-26; Bet Labs 2003-19 (unseen seasons) -7.1%. |
| 2 | nfl_fade_fav_bye | tier C | paper | Bet Labs 2003-19 -6.7%. |
| 2 | cfb_day_over | retired (11/23) | paper (logs again) | Already off the board since 11/21 (no mechanism); the 11/23 retire label rested on CLV, so it goes back to logging as paper. |
| 2 | nba_ats_hot_home | tier C | paper | Bet Labs 2003-19 -3.9%. |
| 2 | nba_bigfav_over | tier C | paper | Bet Labs 2003-19 -3.7%. |
| 2 | nhl_loss_streak_over | tier C | paper | Bet Labs 2003-19 -2.3%. |
| 2 | nba_badteams_under | tier C | paper | Bet Labs 2003-19 -2.3%. |
| 2 | nfl_road_dog_7510 | tier C | paper | Negative before 2020; also rule group 1. |
| 2 | mlb_road_over_under | tier C | paper | Negative before 2020; Bet Labs 2026 season -21%. Out of season. |
| 2 | nba_roadtrip_over | tier C | paper | Bet Labs 2003-19 -1.0%, since 2020 -6.9%. |
| 2 | nhl_bounce_home_ml | tier C | paper | Not positive before 2020. |
| 2 | cfb_homefav_7510_under, nfl_home_dog_7510 | tier C | tier C (unchanged) | Marginal before 2020 (+1.1%, +1.8%); re-read under the profit lines. |
| 3 | bounce15_1h | tier C | paper | Rule group 1 (option B): failed our own multi-season profit replay before the 11/18 blanket move. |
| 3 | nhl_pl_fav_strong_opp | tier C | paper | Group 1. |
| 3 | nhl_pl_fav_gap | tier C | paper | Group 1. |
| 3 | nba_under_good_home_over_small | tier C | paper | Group 1. |
| 3 | cfb_road_streak_dog | tier C | paper | Group 1. |
| 3 | cbb_under_good_over_drop | tier C | paper | Group 1. |
| 3 | awfuldog_deep | tier C | paper | Group 1 (no bets yet). |
| 3 | wind1014_cold | tier C | paper | Group 1 (no bets yet). A 10-14 mph NFL game at 35F or colder (Open-Meteo temperature) now logs as paper, not a bet. |
| 5 | cfb_road_dog_low_total | retired (11/23) | tier C (0.25u), its pre-11/23 status | The retirement rested on CLV; 14-16, -9.9% on 30 does not meet the profit retire line. |
| 5 | steam_rev | retired (11/23) | paper (logging resumes) | The retirement rested on CLV; -2.2% on 725 is not significantly below break-even. |
| 5 | Kalshi 4+ movers | sized paper (11/23) | watch, its pre-checkpoint status | The promotion rested on a CLV z; +0.5% on 1,515 (below zero after the fee) is no profit edge. |
| 6 | Sharp flags, NBA grade B | paper | live test, 0.25u | +11.6% on 53, the best paper slice; small, so a small size. |

Rule group 1 also contains nfl_road_dog_7510 and nfl_fade_fav_bye (both in item 2).

## Behaviour changes

- **4. Kalshi move against: a shown warning, not a hard block.** For games from the cutoff a Kalshi 4+ point move against no longer holds
  a system, lean, curve or tennis bet and no longer drops a sharp flag (soccer A/B and NBA B stay live with it). Every such row shows a
  bold "⚠ Kalshi moved the other way" next to the bet, and the tracker keeps the tag (`kalshi_warn`) so the record can be split.
  Phone pushes for sharp flags now go out with a WARNING line instead of being suppressed. Conflicting systems still cancel; other
  signals against a sharp flag (sharp accounts, big money, bet back, sharp move) still hold it as before.
- **5. Profit-only lines adopted** in docs/checkpoint_rules_2026-11-02.md (11/24 amendment). The 11/10 sharp-flag rule ("paper until
  they beat Pinnacle's close") is replaced: a sport x grade slice goes live only on the profit promote line.
- **6. NBA sharp B** sizes at 0.25u (favourite: to win 0.25u; plus money: risk 0.25u; Sean 11/24: 0.25u is the minimum live size, so no 0.10u tests) on games from the cutoff; NBA A and single-account
  (watch) flags stay paper. Re-read at 100 graded (53 graded on 11/24).
- **7. Wind source:** the NFL and CFB wind rules fire on MySportsWeather's sustained wind alone (Open-Meteo only when MySportsWeather has
  no reading), as the code has done since 11/14. The rule descriptions that still said "average of the two sources" now say so.
  Checked 11/24 for the holiday games: KC @ BUF (Thu 8:20 PM ET) reads MySportsWeather 10 mph, gusts 26, so wind1014 and wind1014_1h
  are triggered and show WAIT until 12 hours before kickoff; DEN @ PIT (Fri 3:00 PM ET) reads MySportsWeather 20-21 mph, outside
  10-14, so no wind play. The cold split (35F or colder) still uses Open-Meteo's temperature; MySportsWeather has 37F for KC @ BUF.

## Calendar

| Date | What |
|---|---|
| 2026-12-08 (Tue) | Re-read the Kalshi-move-against warning: games from 11/24 19:00Z with the tag, bet anyway vs the rest, on profit (units, ROI, break-even test, halves). Decide: keep as a warning, go back to a block, or drop the tag. |
| at 100 graded | Re-read NBA sharp B under the profit promote line (53 graded on 11/24). |
| each Monday checkpoint | cfb_homefav_7510_under and nfl_home_dog_7510 under the profit lines. |

## Applied 2026-11-24 4:45 PM ET (Sean, via Kirk)

| Change | Old | New |
|---|---|---|
| Kalshi move against | shown warning (2:00 PM) | **cancels** every system, lean, curve, tennis and sharp row again, with or without big money or any other tag, for games starting from 4:45 PM ET 11/24. Games that started 2:00-4:45 PM ET keep the warning. The tag keeps logging and both sides are paper-graded in data/state/against_panel.json; re-read 12/8. Pushes for sharp flags with a Kalshi move against stop again. |
| stale_book_sb4 | paper | **killed**: no new rows (history kept) |
| stale_book | paper, every row | paper, judged **only on checkable rows** (quote time logged, within 25 min of the Pinnacle snapshot, book not wide); rows without that are excluded from the record. Kill if the first 100 graded checkable rows are not positive in both halves (stale_live.json checkable_test). |
| Wind source (wind1014, wind1014_1h, wind1014_cold, cfb_wind14) | MySportsWeather, Open-Meteo fallback | **the latest Bet Labs pull** of Sean's saved screens (NFL Wind 10-14 Under 1772775, NFL 1H Wind 10-13 Under 769171, CFB Wind 14 Plus Under 1783043): a game fires when the pull lists it. MySportsWeather, then Open-Meteo, only when no pull is under 16 hours old, and shown on the row as a cross-check. A game MySportsWeather has in the band that Bet Labs does not list is a flag only, no bet. The cold split (35F or colder, paper) still uses Open-Meteo's temperature. |

Why: Sean's Bet Labs weather screens carry the proven backtests; MySportsWeather has little backtest of its own (docs/wind_source_2026-11-24.md).
