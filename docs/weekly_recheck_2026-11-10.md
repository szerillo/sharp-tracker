# Weekly rule recheck (11/10)

Scheduled run. No tier or wind-rule change made here; everything below is a recommendation for Sean.
ROI is percent at Pinnacle's close, flat 1 unit. "Forward" is the tracker record in `data/state/bet_log.json` (settled bets, units at the logged size).
Replays rebuilt today from repo data only (no Odds API credits): `rule_replay.py`, `deriv_split.py`, `nba_under_reconcile.py`, `nba_1h_reconcile.py`, `nfl_replay.py`, `nfl_1h_replay.py`, `cfb_replay.py`.
Tier rule: B every season positive, C one season negative, A only over a long sample, paper when it only partly fits or our own replay is flat or negative; an edge only at its exact thresholds is at most C; under ~30 forward bets does not move a tier.

Run note: `sharp/odds_db.py` crashed on `data/oddsapi/derivs/_games.json.gz` (a JSON list, not a pull). One-line guard added (skip non-dict files) so the odds database builds; no other code changed.

## Recommended changes

| rule | now | recommend | reason |
|---|---|---|---|
| cfb_road_dog_low_total | C | **down to paper** | 2025 -1.0% and 2026 -33.3% (7-14-1): two negative seasons in a row; non-conference version -7.2% |
| mnf_1h | B | **down to C** | Bet Labs 4 of 6 seasons; our 1H replay 33-28 (+6.4%) has 2024 at -25.1%; full-game MNF 2024 -23.3% |
| cfb_wind14 | A | **down to C** (B if Sean counts the Bet Labs picks) | our own wind replay 206-182 (+1.9%) with 2024 -32.7% and 2026 -9.9%; the edge sits in Bet Labs' wind source, same case as wind1014_1h on 11/6 |
| nhl_pl_dog_bigml | C | **down to paper** | 40-25 (+9.9%) but 4 of 7 seasons negative and 38 of 65 bets in 2022-23 |
| nba_momentum (paper) | P | **retire** | forward 18-40, -6.18u on 58 bets |
| stale_book (paper) | P | **retire or rework** | forward 20-43, -4.91u on 63 bets (-31%) |

Everything else: hold. Nothing earns an up move this week.

## Live rules

| rule | tier | replay by season | forward | rec |
|---|---|---|---|---|
| wind1014 | A | ERA5 replay 153-97-3, +18.5%: 2020 +1.7, 2021 +17.2, 2022 +34.6, 2023 +24.7, 2024 -9.4, 2025 +40.1; Bet Labs all-time 533-376 | 7-2, +2.50u | hold: long sample; 15-19 mph neighbour +6.7%, 6-9 mph -9.3% |
| cfb_wind14 | A | NASA wind 14+ 206-182-4, +1.9%: 2020 +16.1, 2021 +15.2, 2022 +3.8, 2023 +7.2, 2024 -32.7, 2025 +7.1, 2026 -9.9; Bet Labs picks at Pinnacle 135-96 (+12.3%) | 3-1, +1.02u | down (see above) |
| cfb_q1_under_curve | A | 296-189, +15.0%, every season (curve_live docstring; not rerun) | 4-7, -1.47u | hold (11 bets) |
| nhl_early_home_fav_qual | B | 258-140, +9.2%: +26.3, +13.8, +5.9, +10.2, +6.6, +14.6; 2026-27 so far 8-12, -31.6%; derivs split 3 of 3 | 3-4, -0.76u | hold; if 2026-27 ends negative it meets the C rule |
| cfb_hot_over_low_total | B | 117-71-3, +19.5%: 2021 +19.1, 2022 +22.7, 2023 +26.4, 2024 +18.1, 2025 +13.4, 2026 +19.2 | none | hold (191 bets is not yet a long sample for A) |
| mnf_1h | B | 1H replay 33-28, +6.4%: 2023 +31.1, 2024 -25.1, 2025 +16.1 (baseline other slots -10.5%) | none | down to C |
| nhl_p3_under_curve | B | 243-185, +13.3%, every season (not rerun) | 0-2 at B; 1-6-2 paper | hold (11 bets); watch |
| cfb_road_dog_low_total | C | 132-113-10, +4.4%: 2020 +6.6, 2021 +22.0, 2022 +4.7, 2023 +12.5, 2024 +8.0, 2025 -1.0, 2026 -33.3 | 7-6, +0.16u | down to paper |
| nfl_home_dog_7510 | C | 46-24-1, +23.7%: +36.5, -3.8, +13.1, +16.4, +56.3, +32.5; all dogs 7.5-10 +8.1% | 0-1 | hold |
| awfuldog | C | 46-35-1, +8.6%: +6.8, -3.8, +29.0, +2.8, +13.4, +27.2; -7 to -13 band -2.9% | 0-4, -1.06u | hold |
| cfb_homefav_7510_under | C | derivs window 81-61, +9.8%: 2023 +1, 2024 +3, 2025 +24 | 1-3, -0.54u | hold |
| nba_under_good_home_over (1.5+ drop) | C | 171-141, +6.8%; neighbours +1.1% to +5.2%; 0.5 version 215-210 (-1.4%, 3 of 7 negative); Bet Labs picks at Pinnacle 213-174 (+7.4%) | 7-2, +1.23u | hold at C (exact-cell edge caps it at C) |
| nhl_bounce_home_ml | C | not in today's replays; 11/6: 5 of 6 | 0-2 | hold |
| nhl_pl_dog_bigml | C | 40-25, +9.9%: -12.0 (n2), +8.6 (n5), +19.1 (n38), -12.5 (n2), +43.7 (n6), -14.3 (n8), -55.8 (n4) | 2-4, -0.58u | down to paper |
| vrest8_1h | C | 1H replay 100-88, +3.8%: +3.7, -1.2, +1.5 (baseline -16.1%); full game 2025 -27.8% | 2-2, -0.05u | hold |
| wind1014_1h | C | 1H replay 56-51, +1.3%: -15.2, -9.9, +46.1 | 5-1, +0.99u | hold |
| nba_ats_hot_home, nba_badteams_under, nba_bigfav_over, nhl_skid_fade_road | C | 11/6 paper grid (not rerun) | 5-2 / 1-0 / 1-1 / 1-0 | hold |
| cbb_bigloss_vs_top5 | C | not replayable (AP ranks) | none | hold |
| cbb_1h_total_curve | C | 313-231, +9.7%, 3 of 3 (not rerun) | 1-1 | hold |
| cfb_tt_under_curve | C | 210-176, +7.3%, 2025 -4.5% (not rerun) | 0-5 at C; 5-6 paper | hold (16 bets); watch |
| nhl_p1_spread_curve | C | set 11/6 | 2-2 | hold |
| nba_threes_under_gap | C | 2453-2198, +7.9%, 4 of 4 (props backtest) | 4-2, +0.49u | hold |
| nhl_prop_under_gap | C | saves 99-54 (+24.9%); shots 1098-1075 (+5.3%) | 0-3 at C; 0-2 paper | hold (5 bets) |

## Paper rules

| rule | replay | forward | rec |
|---|---|---|---|
| nhl_pl_fav_gap | 79-127, +1.0% | 0-1 | stay paper |
| nhl_pl_fav_strong_opp | 136-223, -0.3% | 1-4 | stay paper |
| cfb_road_streak_dog | 214-210-10, -2.0%; derivs window 0 of 3 | 2-3 | stay paper |
| cbb_under_good_over_drop | 495-498-11, -5.0% | none | stay paper |
| nba_1h_under_hot_over | Bet Labs picks at Pinnacle 1H 85-90 (-5.9%); ours 83-86 (-4.8%) | 4-1 | stay paper |
| bounce15_1h | 1H replay 52-59, -10.5% | 1-4 | stay paper |
| cfb_day_over | 11/6 grid 7 of 7 | 2-5 | stay paper |
| xch_homedog_fade | exchange audit | 31-10, +1.52u (42 bets) | stay paper; revisit at 50 |
| kalshi_nhl_flow | | 20-14, +0.29u | stay paper |
| nba_momentum | | 18-40, -6.18u | retire |
| stale_book | | 20-43, -4.91u | retire or rework |
| NFL rush-yards outlier, NFL anytime TD | props backtest | none logged | stay paper |

## Sharp grades (bet_log since 11/2)

| grade | settled | record | units | ROI | avg price |
|---|---|---|---|---|---|
| sharp A | 114 | 45-69 | -13.01 | -27.5% | 0.474 |
| sharp B | 31 | 19-12 | +1.30 | +16.7% | 0.551 |
| sharp C | 0 of 1 | pending (one row, NBA Over 225.5, 11/10 01:00Z, result not in yet) | | | |

Grade A wins 39.5% at an average price of 47.4%, over 114 bets. The losses sit in "a top-200 account also in this sport" (34-49, -8.52u) and NFL (5-19). Grade B is ahead at 61.3% against 55.1%. Over 30 bets each, so this is worth a look at the A criteria; Grade C has no graded rows yet (`sharp_c_paper.jsonl` has 1 row).

## Wind forecast check

Source: `data/research/wx_accuracy.json` (built 11/9 23:15Z, rerun today with the same games). The windy split comes from the script's printout; band agreement on windy games was computed with the same code. Windy = actual or either latest forecast 10+ mph.

| actual | forecast | games | MAE mph | bias mph | 10-14 band agree |
|---|---|---|---|---|---|
| ASOS (measured) | Open-Meteo latest | 89 | 2.79 | +0.48 | 85% |
| | MySportsWeather latest | 89 | 2.69 | +1.04 | 74% |
| | blend (rule) | 89 | 2.49 | +0.76 | 84% |
| ASOS, windy | Open-Meteo latest | 27 | 3.64 | -1.02 | 56% |
| | MySportsWeather latest | 27 | 4.38 | +1.94 | 15% |
| | blend (rule) | 27 | 3.52 | +0.46 | **48%** |
| ERA5 (NFL) | Open-Meteo latest | 11 | 1.78 | +0.25 | 91% |
| | MySportsWeather latest | 11 | 2.63 | +1.15 | 82% |
| | blend (rule) | 11 | 1.52 | +0.70 | 82% |
| ERA5, windy | Open-Meteo latest | 3 | 2.33 | -1.47 | 67% |
| | MySportsWeather latest | 3 | 4.57 | +4.57 | 33% |
| | blend (rule) | 3 | 1.92 | +1.55 | **33%** |

Flag: the blend's band agreement on windy games is under 75% on both truths (48% on ASOS, 27 games; 33% on ERA5, 3 games). Bias on windy games stays inside +/-2 mph (+0.46 ASOS, +1.55 ERA5). MySportsWeather carries most of the miss on windy games (+1.94 and +4.57 mph bias, 15% and 33% band agreement); Open-Meteo latest alone agrees more often. The windy subset is chosen on the forecasts as well as the actual, which pulls band agreement down, and ERA5 has only 3 windy NFL games, so this is a watch item, not proof. The NFL rule was backtested on ERA5, so the ERA5 sample is the one to grow.
