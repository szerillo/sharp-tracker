# Weekly rule recheck (11/24)

Scheduled run. No tier, rule or wind setting was changed; everything below is a recommendation for Sean.

- Replay ROI is percent at Pinnacle's close, flat 1 unit.
- "Forward" is the tracker record in `data/state/bet_log.json` (built 11/24 09:37Z), games started before 11/24 09:00Z, every category the rule has logged under (paper, lean C, system), graded flat 1u (favourite to win 1u, plus money risk 1u). z is against break-even at the prices taken.
- Replays rebuilt today from repo data only (no Odds API credits): `odds_db.py` (the sqlite is gitignored, so it was rebuilt first), `rule_replay.py`, `deriv_split.py`, `nba_under_reconcile.py`, `nba_1h_reconcile.py`, `nfl_replay.py`, `nfl_1h_replay.py`, `cfb_replay.py`. The historical replays match 11/10 except wind1014 (2024 now -11.3%, was -9.4%, after a weather-cache refresh). The 2026-27 in-season rows did not grow (the Odds API history in the repo has not been extended since 11/10).
- The curve rules (`curve_live.py`) and prop rules (`props_live.py`) have no replay script in the list; their backtest numbers are quoted from the last saved test.
- Tier convention used (from the run's instructions): B if positive every season; C if one season is negative or the two tests disagree; A only over a long sample; paper when it only partly fits or our own replay is flat or negative; an edge only at its exact thresholds is at most C; under ~30 forward bets does not move a tier.

## Conflicts to flag

1. **Tier convention vs the 11/18 ruling.** On 11/18 Sean made the full Bet Labs backtest the primary evidence (`docs/validation/PUSHBACK.md`), kept every bettable rule bettable and moved every paper rule to C. The convention above leans on our own replay. Where the two disagree and nothing new has happened since 11/18, the rule is listed under "already ruled" with a hold, not re-proposed.
2. **Wind rule source.** The run's instructions grade "the rule's blend (OM latest + MSW latest)". Since 11/14 the live NFL and CFB wind rules fire on MySportsWeather alone, with Open-Meteo only as a fallback (`sharp/systems.py` `rule_wind`). The `DESC` text in `systems.py` still says "average". Both are graded below.
3. **ERA5 truth in `wx_accuracy.py`.** It uses ERA5 kickoff-hour wind (`wind_kick`), and its NFL games stop at 11/2 (11 games), because `data/nfl/weather/archive.json` is filled only by `nfl_replay.py` for games in the Odds API history. The rule was backtested on the 3-hour average. I pulled ERA5 3-hour averages for the 41 NFL games in the forecast log (scratch only, nothing written to the repo) and report them next to the script's numbers.

## Proposed, waiting on Sean

| rule | now | proposed | reason |
|---|---|---|---|
| nhl_p3_under_curve | C | **paper** | forward 9-22-11, -16.0u flat, -44.4%, z -2.56 on 42 fires, both halves negative; the 11/9 fixes (current-season period share, moneyline strength in the match) are still not in `deriv_curve.py` |
| cfb_q1_under_curve | A | **B** | 296-189 (+15.0%) is three seasons (derivatives from 2023), not the long sample A needs; forward 18-24, -13.9% on 42, negative in both halves (z -0.90, not significant) |
| mnf_1h | B | **paper** (C on the season rule alone) | the trigger is a kickoff slot, the same reason cfb_day_over went to paper on 11/21; our 1H replay 33-28 (+6.4%) has 2024 at -25.1%; no forward fires |
| cfb_road_dog_low_total | C | **paper** | replay 2025 -1.0% and 2026 -33.3% (7-14-1); non-conference -7.2%; forward now 14-16, -9.9% on 30 |
| former paper rules with a flat or negative replay (cfb_road_streak_dog, cbb_under_good_over_drop, nhl_pl_fav_gap, nhl_pl_fav_strong_opp, nhl_pl_dog_bigml, nba_1h_under_hot_over, bounce15_1h, nba_under_good_home_over_small, wind1014_cold, awfuldog_deep) | C (11/18 blanket) | **paper** | each was paper for its own replay result before the 11/18 blanket move; none has 30 forward bets (combined 23-25); replays in the paper-rule table below |
| nba_momentum, stale_book | paper | **retire** (unchanged from 11/10) | nba_momentum 18-40, -32.3% (no fires since); stale_book 116-137, +2.1% on 253, halves -17% / +22% |

Nothing earns an up move. Sharp C is ahead but has 27 graded rows (below).

## Already ruled (hold; convention would read lower)

| rule | tier | convention reading | why hold |
|---|---|---|---|
| cfb_wind14 | A | C (our NASA replay +1.9%, 2024 -32.7%, 2026 -9.9%) | Sean 11/18: Bet Labs 557-403 both eras; no new replay data. Forward 14-9 (+20.2%) but 1-6 in the last 7 days |
| awfuldog | A | C (2021 -3.8%; -7 to -13 band -2.9%) | Sean 11/18 (Bet Labs 254-164). Forward 0-4 |
| nba_under_good_home_over | A | C (edge only at the 1.5 drop; 0.5 drop -1.3%, 3 of 7 negative) | Sean 11/18 (Bet Labs 756-581). Forward 9-5, +26.5% |
| wind1014_1h | B | C (our 1H replay +1.3%, 2023 -15.2%, 2024 -9.9%) | Sean 11/18 (Bet Labs 407-303). Forward 7-2 |
| vrest8_1h | B | C (2024 -1.2%) | Sean 11/18 (Bet Labs 459-364). Forward 3-5 |
| nba_ats_hot_home, nba_badteams_under, nba_bigfav_over, nhl_bounce_home_ml, nhl_skid_fade_road | C | paper (Bet Labs before 2021 negative: fails the two-window test) | Sean 11/18 kept them at C knowing this. Forward below |

## Live rules

| rule | tier | replay by season | forward (flat 1u) | rec |
|---|---|---|---|---|
| wind1014 | A | ERA5 3h replay 153-98-3, +18.0%: 2020 +1.7, 2021 +17.2, 2022 +34.6, 2023 +24.7, 2024 -11.3, 2025 +40.1; neighbours 15-19 +6.7%, 6-9 -9.6%; Bet Labs 537-380 | 8-4, +31.1% | hold (long sample, both Bet Labs eras); see wind section on the MSW source |
| cfb_wind14 | A | NASA 14+ 206-182-4, +1.9%: 2020 +16.1, 2021 +15.2, 2022 +3.8, 2023 +7.2, 2024 -32.7, 2025 +7.1, 2026 -9.9; 10-13 band +2.4% | 14-9, +20.2% | hold (already ruled) |
| awfuldog | A | 46-35-1, +8.6%: +6.8, -3.8, +29.0, +2.8, +13.4, +27.2 | 0-4, -100% | hold (already ruled) |
| nba_under_good_home_over | A | drop 1.5+ 171-141, +6.8%; drop 0.5+ 215-210-7, -1.3% (2020 -3.5, 2021 +3.7, 2022 -3.3, 2023 +7.5, 2024 -13.8, 2025 +1.7, 2026 +14.7); Bet Labs picks at Pinnacle 213-174, +7.4% | 9-5, +26.5% | hold (already ruled) |
| cfb_q1_under_curve | A | 296-189, +15.0%, every season 2023-25 (11/6 test, not rerun) | 18-24, -13.9% (42) | **down to B** |
| wind1014_1h | B | 1H 56-51, +1.3%: 2023 -15.2, 2024 -9.9, 2025 +46.1; 14 mph 8-4, 15+ -2.5% | 7-2, +51.8% | hold (already ruled) |
| vrest8_1h | B | 1H 100-88, +3.8%: +3.7, -1.2, +1.5 (baseline -16.1%); full game 2025 -27.8% | 3-5, -27.9% | hold (already ruled) |
| mnf_1h | B | 1H 33-28, +6.4%: 2023 +31.1, 2024 -25.1, 2025 +16.1; Sunday night -2.1%, other slots -10.5% | none | **down to paper** |
| nhl_early_home_fav_qual | B | 258-140, +9.2%: +26.3, +13.8, +5.9, +10.2, +6.6, +14.6; 2026-27 so far 8-12, -31.6%; derivs 3 of 3 | 13-12, -10.1% (25) | hold; if 2026-27 ends negative it meets the C rule |
| cfb_hot_over_low_total | B | non-conference 117-71-3, +19.5%: 2021 +19.1, 2022 +22.7, 2023 +26.4, 2024 +18.1, 2025 +13.4, 2026 +19.2 | none | hold (A needs a longer sample) |
| cbb_bigloss_vs_top5 | B | not replayable (AP ranks); Bet Labs 151-92 | none | hold |
| nfl_home_dog_7510 | C | 46-24-1, +23.7%: +36.5, -3.8, +13.1, +16.4, +56.3, +32.5; all dogs 7.5-10 +8.1% | 0-4, -100% | hold |
| cfb_homefav_7510_under | C | derivs window 81-61, +9.8%: 2023 +1, 2024 +3, 2025 +24 | 4-6, -21.8% | hold |
| nba_ats_hot_home | C | Bet Labs before 2021 -4.0% | 11-9, +5.8% | hold (already ruled) |
| nba_badteams_under | C | Bet Labs before 2021 -2.2% | 4-2, +28.5% | hold (already ruled) |
| nba_bigfav_over | C | Bet Labs before 2021 -3.5% | 6-5, +6.5% | hold (already ruled) |
| nhl_bounce_home_ml | C | Bet Labs before 2021 -0.4% | 2-4, -41.1% | hold (already ruled) |
| nhl_skid_fade_road | C | Bet Labs before 2021 -6.6% | 8-1, +68.2%, z +2.31 (9) | hold (under 30) |
| nhl_loss_streak_over | C | 6 of 7 (11/18 evidence) | 4-9, -42.0% (13) | hold; watch |
| nba_roadtrip_over | C | 6 of 6 (11/18 evidence) | 6-4, +16.7% | hold |
| nfl_road_dog_7510 | C | 4 of 7 | 1-3 | hold |
| nfl_fade_fav_bye | C | favourite off a bye ATS 71-90 (-12.7% for the favourite) | 2-3 | hold |
| cfb_road_dog_low_total | C | 132-113-10, +4.4%: +6.6, +22.0, +4.7, +12.5, +8.0, -1.0, -33.3 | 14-16, -9.9% (30) | **down to paper** |
| cbb_1h_total_curve | C | 313-231, +9.7%, 3 of 3 (not rerun) | 4-4-1 | hold |
| cfb_tt_under_curve | C | 210-176, +7.3%, 2025 -4.5% (not rerun) | 18-20, -8.7% (38) | hold |
| nhl_p1_spread_curve | C | set 11/6 | 7-3, +19.2% | hold |
| nhl_p3_under_curve | C | 243-185, +13.3% leave-one-season-out (not rerun); 2026-27 third periods score 2.44 a game vs 2.10-2.16 in the pool | 9-22-11, -44.4%, z -2.56 (42) | **down to paper** |
| nba_threes_under_gap | C | 2453-2198, +7.9%, 4 of 4 (props backtest) | 12-9, +15.4% | hold |
| nhl_prop_under_gap | C | saves 99-54, +24.9%; shots +5.3% | 18-17, +5.8% (35) | hold |
| nfl_prop_under_gap | C | rush yards 65-35, +21.9%, 4 of 4 | 5-14, -25.3% (19) | hold; watch |
| xch_homedog_fade | C | exchange audit, two months | 82-28, +4.4% (110), z +0.73 | hold |

Other forward rows (not in the three rule files): tennis_serve_dog 49-50, +3.7% (99); tennis_fs_fav 34-16, +8.7% (50); mma_steam_fav 5-0; tennis_hot_fav 31-16, -7.7%; tennis_hot_dog 12-29, -31.3% (paper).

## Paper rules and the 11/18 former-paper group

| rule | replay | forward | rec |
|---|---|---|---|
| cfb_road_streak_dog | 214-210-10, -2.0%: 2024 -10.3, 2025 -9.6, 2026 -7.3; derivs 0 of 3 | 5-4 | paper |
| cbb_under_good_over_drop | 495-498-11, -5.0%, 2 of 6 (control -0.6%) | 4-3 | paper |
| nhl_pl_fav_gap | 79-127, +1.0%, 3 of 7 | 0-1 | paper |
| nhl_pl_fav_strong_opp | 136-223, -0.3%, 3 of 7 | 3-5 | paper |
| nhl_pl_dog_bigml | 40-25, +9.9%; 4 of 7 negative, 38 of 65 in 2022-23 | 3-4 | paper |
| nba_1h_under_hot_over | Bet Labs picks at Pinnacle 1H 85-90 (-5.9%); ours 83-86 (-4.8%) | 5-1 | paper |
| bounce15_1h | 1H 52-59, -10.5%, 0 of 3 full seasons | 2-6 | paper |
| nba_under_good_home_over_small | drop 0.5-1.0 part of 215-210 (-1.3%) | 1-1 | paper |
| wind1014_cold | cold band 27-27-1, -3.4% | none | paper |
| awfuldog_deep | 14-16 in the six-season replay | none | paper |
| cfb_day_over | paper since 11/21 | 11-16, -22.6% | stay paper |
| kalshi_nhl_flow | | 20-14, +1.7% | stay paper |
| stale_book / stale_book_sb4 | | 116-137, +2.1% (253) / 4-6 | retire or rework (as 11/10) |
| wncaab_move_follow / wncaab_dog_7_10 | | 22-24, -8.9% / 1-4 | stay paper |
| nba_momentum | | 18-40, -32.3% | retire |

## Sharp grades (bet_log, games since 11/8, flat 1u at the flagged price)

| grade | graded | record | flat units | ROI | win % vs avg price | z |
|---|---|---|---|---|---|---|
| sharp A | 206 | 96-110 | -13.98 | -5.4% | 46.6% vs 49.3% | -0.77 |
| sharp B | 72 | 42-30 | +18.52 | +16.5% | 58.3% vs 51.5% | +1.54 |
| sharp C | 27 | 19-8 | +10.31 | +31.3% | 70.4% vs 54.1% | +1.78 |
| sharp watch | 31 | 14-17 | -7.86 | -15.0% | 45.2% vs 53.2% | -0.95 |

Grade C (sharps plus market move, no flag; first row 11/9, 1 pending) is 9-4 (+30.9%) and 10-4 (+31.6%) in its two halves, spread over CBB 5-3, NBA 6-3, NFL 4-1, NHL 2-1, CFB 2-0. 16 of 28 rows are totals. 27 graded is under 30, so no call yet; at this rate it reaches 50 in three to four weeks.
Grade A is the weakest of the three for the third week. Since 11/10 its NHL rows are 11-21 (-32.3%) and CBB 5-6 (-25.9%), while NFL (12-10, +27.2%) and soccer (10-5, +20.7%) are positive. B is ahead in every sport but NHL (0-2).
Grade order (C over B over A) runs against the definitions. That is worth a look at the A criteria, still on samples where only A has 200+.

## Wind forecast check

`data/research/wx_accuracy.json` was built 11/24 01:14Z (Monday's weekly.yml), so it is current; I reran the script read-only to get the windy split with band agreement. Windy = actual or either latest forecast 10+ mph. Band = both sides inside 10-14 mph or both outside.

| actual | forecast | games | MAE mph | bias mph | 10-14 band agree |
|---|---|---|---|---|---|
| ASOS (measured), all | Open-Meteo latest | 122 | 3.03 | +0.38 | 81% |
| | MySportsWeather latest (live rule since 11/14) | 122 | 2.85 | +0.94 | 71% |
| | blend (OM latest + MSW latest) | 122 | 2.67 | +0.66 | 80% |
| ASOS, windy | Open-Meteo latest | 44 | 4.06 | -0.71 | 52% |
| | MySportsWeather latest | 44 | 4.41 | +1.86 | 23% |
| | blend | 44 | 3.71 | +0.57 | **48%** |
| ERA5 kickoff hour (script), NFL to 11/2 | Open-Meteo latest | 11 | 1.78 | +0.25 | 91% |
| | MySportsWeather latest | 11 | 2.63 | +1.15 | 82% |
| | blend | 11 | 1.52 | +0.70 | 82% |
| ERA5 kickoff hour, windy | Open-Meteo latest | 3 | 2.33 | -1.47 | 67% |
| | MySportsWeather latest | 3 | 4.57 | +4.57 | 33% |
| | blend | 3 | 1.92 | +1.55 | **33%** |
| ERA5 3h average (the backtest's measure), NFL 10/29 to 11/23 | Open-Meteo latest | 38 | 1.58 | +0.73 | 79% |
| | MySportsWeather latest | 38 | 2.42 | +1.46 | 68% |
| | blend | 38 | 1.70 | +1.10 | 76% |
| ERA5 3h average, windy | Open-Meteo latest | 17 | 1.87 | +0.79 | 59% |
| | MySportsWeather latest | 17 | 3.38 | **+3.08** | **29%** |
| | blend | 17 | 2.28 | +1.94 | **47%** |

ERA5 3h rows: pulled today from the Open-Meteo archive API for the NFL games in `wx_accuracy.py`'s set (38 of 41 returned; 3 connection resets). The last ~5 days of the archive are preliminary, not final ERA5. Kept to games before 11/19 (final ERA5 only): blend 28 games, MAE 1.77, bias +1.04, band 79%; windy 12 games, Open-Meteo +0.12 / 67%, MySportsWeather +3.49 / 25%, blend +1.81 / 50%. One SoFi game (roofed, never a wind play) is in the set (blend 17.1 vs ERA5 10.6); dropping it lowers the windy bias.
Rule fires: the blend put 10 of 38 NFL games in 10-14 mph; ERA5 3h agreed on 4. ERA5 had 7 games in the band.

**Flags.**
- The blend's band agreement on windy games is under 75% on every truth: 48% ASOS (44 games), 33% ERA5 kickoff hour (3), 47% ERA5 3h (17).
- The blend's windy bias stays inside +/-2 mph (+0.57 ASOS, +1.55 and +1.94 ERA5) but sits at the edge on the ERA5 3h measure.
- The live rule fires on MySportsWeather alone, and that source is worse on every windy cut: +3.08 mph bias against ERA5 3h (17 games) and 23-29% band agreement. On the backtest's own measure the live input reads about 3 mph high on windy games, so it fires on games ERA5 puts under 10 mph. This bears on the open 11/22 decision (MySportsWeather alone vs the two-source average): on accuracy, Open-Meteo latest alone is the closest to ERA5 on windy games, and the blend is second.
- `wx_accuracy.py`'s ERA5 truth will stay at 11 games until `data/nfl/weather/archive.json` is filled past 11/2, and it uses kickoff-hour wind rather than the 3h average the rule was tested on. Both are one-line changes, left for Sean to approve.
