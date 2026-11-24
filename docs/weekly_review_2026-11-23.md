# Weekly systems review, 2026-11-23

Read only: no rule, tier or paper/live status was changed for this review. Graded games that started before Tue 11/24 05:00 UTC, from
data/state/bet_log.json (built 2026-11-24T04:38Z). The bet log starts 10/30, so "all" is since 10/30 and the 30-day and all columns
match. Records and units are flat 0.25u for every row (favourite to win 0.25u, plus money risk 0.25u), so live and paper rules compare on
one scale. "Board units" are what the board actually tracked: 0.5u on some fills before 11/18, and no units on sharp flags after 11/10.
ROI = units / risk. CLV = points against the no-vig close (+ beat the close). Lapsed, conflict-cancelled and bad-price rows are left out.

This sits next to today's checkpoint (docs/checkpoint_2026-11-23.md). That checkpoint ran the pre-agreed lines from 11/2: it retired
cfb_road_dog_low_total, cfb_day_over and steam_rev, and moved Kalshi 4+ movers to sized paper. Its records run on fills.jsonl and can
differ by a game or two from these.

## Summary

| | Last 7 days | Last 30 days / all | CLV, all | Read |
|---|---|---|---|---|
| **Live categories, total** | 90-72, -0.07u, -0.1% | 261-199, +3.20u, +2.0% | -1.73 on 332 | About break-even. Winning more than half, but the prices are slightly worse than the close |
| **Paper, total** | 195-141, +17.06u, +14.7% | 625-650, -19.10u, -4.2% | -0.87 on 1,099 | Big week (stale_book, sharp CFB/NBA) on top of a losing month |
| Wind: wind1014 / wind1014_1h / cfb_wind14 (A/B/A) | 0 / 0 / 1-6 | 8-4 / 7-2 / 14-9, +3.42u combined | +0.80 / -0.92 / -0.53 | Working. cfb_wind14's bad week is 7 games |
| nba_under_good_home_over (A) | 0-1 | 9-5, +0.97u, +26.5% | +1.37 on 10 | Working, beats the close |
| xch_homedog_fade (C) | 24-9, +0.73u | 82-28, +3.06u, +4.4% | -1.03 on 110 | Biggest live sample. Profitable but trails the close |
| nhl_skid_fade_road (C) | 2-0 | 8-1, +2.40u | -1.33 on 8 | Hot, small sample |
| tennis_serve_dog (live) | 14-14, +0.30u | 49-50, +0.94u, +3.7% | -2.26 on 97 | Flat. Profit is noise and CLV is clearly negative |
| Sharp soccer A (live since 11/21) | 10-5, +1.12u | 32-22, +3.47u, +20.5% | +0.21 on 51 | Best sharp slice. 3-3 since it went live |
| nhl_p3_under_curve (C) | 3-6-1 | 9-21-10, -3.62u, -32.5% | n/a | **Worst live rule.** 40 bets, about z -2 |
| nhl_early_home_fav_qual (B) | 4-4 | 13-12, -0.98u, -10.1% | -1.41 on 25 | Near the checkpoint review line |
| The 18 rules moved to C on 11/19 | 22-11, +1.91u, +20.0% since | (as paper before: 57-105, -28.5%) | -4.46 on 29 since | Good week, but CLV says it was luck |
| stale_book (paper) | 55-43, +6.45u, +25.8% | 116-134, +2.10u, +3.3% | **+0.57 on 249** | **Best paper candidate:** positive CLV on a real sample |
| Sharp NBA A / B / watch (paper) | 9-7 / 11-6 / 7-6 | 26-25 / 30-22 / 18-26 | -0.16 / -1.12 / -0.27 | B is +14.3% but trails the close. Not ready |
| Sharp NHL A (paper) | 5-11 | 10-26, -4.72u, -43.5% | +0.30 on 35 | Bad results, neutral CLV |

**Decisions waiting for Sean:** (1) the rule-groups question (options in section 4), (2) the wind source (MySportsWeather alone vs
the two-source average; it decided NO @ CHI 11/22 and CIN @ WSH 11/23), (3) nhl_p3_under_curve (back to paper?), (4) stale_book
(stays paper by his 11/18 call; the strongest case for a live test).


## 1. Every rule, last 7 days / 30 days / all (flat 0.25u: record, units, ROI)

| Rule | Status | Since | Last 7 days | Last 30 days | All (log from 10/30) | Board units, all | CLV, all |
|---|---|---|---|---|---|---|---|
| tennis_serve_dog | live | 11/17 only real-money tennis angle | 14-14, +0.30u, +4.1% | 49-50, +0.94u, +3.7% | 49-50, +0.94u, +3.7% | +0.94 | -2.26 (97) |
| sharp soccer A | live 0.25u | 11/21 paper to live | 10-5, +1.12u, +20.7% | 32-22, +3.47u, +20.5% | 32-22, +3.47u, +20.5% | +2.18 | +0.21 (51) |
| sharp soccer B | live 0.25u | 11/21 paper to live | - | 1-2, -0.39u, -23.8% | 1-2, -0.39u, -23.8% | -0.39 | -2.38 (2) |
| cfb_q1_under_curve | live A | curve, 0.25u since 11/18 | 6-6, +0.08u, +2.4% | 18-24, -1.56u, -13.9% | 18-24, -1.56u, -13.9% | -3.20 | - |
| cfb_wind14 | live A | 11/18 re-tier (PUSHBACK) | 1-6, -1.32u, -71.5% | 14-9, +1.20u, +20.2% | 14-9, +1.20u, +20.2% | +3.72 | -0.53 (22) |
| nba_under_good_home_over | live A | 11/18 re-tier (PUSHBACK) | 0-1, -0.26u, -100.0% | 9-5, +0.97u, +26.5% | 9-5, +0.97u, +26.5% | +1.94 | +1.37 (10) |
| wind1014 | live A | 11/18 re-tier (PUSHBACK) | - | 8-4, +0.98u, +31.1% | 8-4, +0.98u, +31.1% | +1.96 | +0.80 (10) |
| awfuldog | live A | 11/18 re-tier (PUSHBACK) | - | 0-4, -1.06u, -100.0% | 0-4, -1.06u, -100.0% | -2.11 | -0.61 (3) |
| nhl_early_home_fav_qual | live B | 11/18 re-tier (PUSHBACK) | 4-4, -0.81u, -22.3% | 13-12, -0.98u, -10.1% | 13-12, -0.98u, -10.1% | -2.20 | -1.41 (25) |
| wind1014_1h | live B | 11/18 re-tier (PUSHBACK) | - | 7-2, +1.24u, +51.8% | 7-2, +1.24u, +51.8% | +2.48 | -0.92 (9) |
| vrest8_1h | live B | 11/18 re-tier (PUSHBACK) | - | 3-5, -0.59u, -27.9% | 3-5, -0.59u, -27.9% | -1.19 | -4.49 (8) |
| xch_homedog_fade | live C | 11/14 paper to C | 24-9, +0.73u, +3.5% | 82-28, +3.06u, +4.4% | 82-28, +3.06u, +4.4% | +3.06 | -1.03 (110) |
| nhl_p3_under_curve | live C | 11/14 B to paper, 11/18 paper to C | 3-6-1, -0.81u, -29.5% | 9-21-10, -3.62u, -32.5% | 9-21-10, -3.62u, -32.5% | -5.42 | - |
| cfb_tt_under_curve | live C | curve, 0.25u since 11/18 | 6-2, +1.00u, +43.7% | 18-20, -0.95u, -8.7% | 18-20, -0.95u, -8.7% | -0.95 | -3.41 (18) |
| nhl_prop_under_gap | live C | props (lean C) | 7-6, +0.51u, +14.8% | 17-17, +0.29u, +3.3% | 17-17, +0.29u, +3.3% | +0.30 | - |
| nba_threes_under_gap | live C | props (lean C) | 5-4, +0.35u, +14.4% | 12-9, +0.88u, +15.4% | 12-9, +0.88u, +15.4% | +0.88 | - |
| nba_ats_hot_home | live C | 11/18 re-tier (PUSHBACK) | 2-4, -0.60u, -35.8% | 11-9, +0.32u, +5.8% | 11-9, +0.32u, +5.8% | +0.32 | -1.42 (20) |
| nfl_prop_under_gap | live C | props (lean C) | 3-4, +0.34u, +19.3% | 5-12, -0.70u, -16.5% | 5-12, -0.70u, -16.5% | -0.70 | - |
| nhl_loss_streak_over | live C | 11/19 paper to C (blanket) | 2-1, +0.22u, +27.8% | 4-9, -1.51u, -42.0% | 4-9, -1.51u, -42.0% | -1.51 | -9.43 (13) |
| nba_bigfav_over | live C | 11/18 re-tier (PUSHBACK) | 1-1, -0.03u, -6.3% | 6-5, +0.19u, +6.5% | 6-5, +0.19u, +6.5% | +0.19 | +0.06 (11) |
| nba_roadtrip_over | live C | 11/19 paper to C (blanket) | 4-2, +0.46u, +28.3% | 6-4, +0.45u, +16.7% | 6-4, +0.45u, +16.7% | +0.45 | -4.03 (10) |
| nhl_p1_spread_curve | live C | curve, 0.25u since 11/18 | 1-0, +0.25u, +48.0% | 7-3, +0.82u, +19.2% | 7-3, +0.82u, +19.2% | +0.82 | -3.78 (9) |
| cfb_homefav_7510_under | live C | 11/18 re-tier (PUSHBACK) | 0-1, -0.25u, -100.0% | 4-6, -0.58u, -21.8% | 4-6, -0.58u, -21.8% | -0.58 | -2.74 (9) |
| cbb_1h_total_curve | live C | curve, 0.25u since 11/18 | 2-1-1, +0.22u, +19.8% | 4-4-1, -0.12u, -4.7% | 4-4-1, -0.12u, -4.7% | -0.12 | -3.00 (7) |
| nhl_skid_fade_road | live C | 11/18 re-tier (PUSHBACK) | 2-0, +0.50u, +35.1% | 8-1, +2.40u, +68.2% | 8-1, +2.40u, +68.2% | +2.40 | -1.33 (8) |
| cfb_road_streak_dog | live C | 11/19 paper to C (blanket) | 1-0, +0.25u, +98.0% | 5-4, +0.01u, +0.5% | 5-4, +0.01u, +0.5% | +0.01 | -4.83 (6) |
| bounce15_1h | live C | 11/19 paper to C (blanket) | 0-1, -0.27u, -100.0% | 2-6, -1.09u, -49.7% | 2-6, -1.09u, -49.7% | -1.09 | -0.60 (7) |
| nhl_pl_fav_strong_opp | live C | 11/19 paper to C (blanket) | 1-1, +0.03u, +6.4% | 3-5, +0.11u, +5.4% | 3-5, +0.11u, +5.4% | +0.11 | -1.37 (8) |
| cbb_under_good_over_drop | live C | 11/19 paper to C (blanket) | 1-0, +0.25u, +90.5% | 4-3, +0.23u, +12.0% | 4-3, +0.23u, +12.0% | +0.23 | +0.17 (7) |
| nhl_pl_dog_bigml | live C | 11/19 paper to C (blanket) | - | 3-4, -0.33u, -17.1% | 3-4, -0.33u, -17.1% | -0.33 | -1.39 (7) |
| nba_1h_under_hot_over | live C | 11/19 paper to C (blanket) | 1-0, +0.25u, +90.5% | 5-1, +0.96u, +57.5% | 5-1, +0.96u, +57.5% | +1.68 | +0.74 (5) |
| nba_badteams_under | live C | 11/18 re-tier (PUSHBACK) | 1-1, -0.01u, -1.9% | 4-2, +0.49u, +28.5% | 4-2, +0.49u, +28.5% | +0.48 | +1.18 (6) |
| nhl_bounce_home_ml | live C | 11/18 re-tier (PUSHBACK) | 0-1, -0.35u, -100.0% | 2-4, -0.86u, -41.1% | 2-4, -0.86u, -41.1% | -0.86 | -3.45 (6) |
| nfl_fade_fav_bye | live C | 11/19 paper to C (blanket) | 0-2, -1.22u, -100.0% | 2-3, -1.01u, -49.3% | 2-3, -1.01u, -49.3% | -1.01 | -7.75 (4) |
| mma_steam_fav | live C | MMA lean C | 2-0, +0.50u, +68.3% | 5-0, +1.25u, +45.6% | 5-0, +1.25u, +45.6% | +1.25 | -0.13 (2) |
| nfl_road_dog_7510 | live C | 11/19 paper to C (blanket) | 1-1, -0.02u, -4.2% | 1-3, -0.57u, -52.6% | 1-3, -0.57u, -52.6% | -0.57 | -3.01 (4) |
| nfl_home_dog_7510 | live C | 11/19 B to C | - | 0-4, -1.14u, -100.0% | 0-4, -1.14u, -100.0% | -1.14 | -3.82 (3) |
| nba_under_good_home_over_small | live C | 11/19 paper to C (blanket) | 1-0, +0.25u, +92.6% | 1-1, -0.02u, -2.9% | 1-1, -0.02u, -2.9% | -0.02 | -2.29 (2) |
| nhl_pl_fav_gap | live C | 11/19 paper to C (blanket) | - | 0-1, -0.25u, -100.0% | 0-1, -0.25u, -100.0% | -0.25 | -1.23 (1) |
| stale_book | paper | paper since added | 55-43, +6.45u, +25.8% | 116-134, +2.10u, +3.3% | 116-134, +2.10u, +3.3% | +2.10 | +0.57 (249) |
| sharp cfb A | paper | 11/10 sharp flags to paper | 11-4, +1.73u, +40.3% | 35-39, -1.96u, -9.3% | 35-39, -1.96u, -9.3% | -2.67 | +0.21 (54) |
| tennis_serve_fav | paper | 11/17 tennis to paper (serve dog only) | 14-2, +2.04u, +14.1% | 38-15, -2.10u, -4.6% | 38-15, -2.10u, -4.6% | -2.10 | -1.95 (52) |
| sharp nba B | paper | 11/10 sharp flags to paper | 11-6, +1.84u, +38.1% | 30-22, +2.75u, +14.3% | 30-22, +2.75u, +14.3% | +0.97 | -1.12 (51) |
| sharp nba A | paper | 11/10 sharp flags to paper | 9-7, +0.96u, +19.5% | 26-25, +0.52u, +2.9% | 26-25, +0.52u, +2.9% | -2.94 | -0.16 (51) |
| tennis_fs_fav | paper | 11/17 tennis to paper (serve dog only) | 4-2, +0.35u, +10.8% | 34-16, +2.06u, +8.7% | 34-16, +2.06u, +8.7% | +2.06 | -1.90 (48) |
| tennis_hot_fav | paper | 11/17 tennis to paper (serve dog only) | 15-4, +1.37u, +9.0% | 31-16, -2.85u, -7.7% | 31-16, -2.85u, -7.7% | -5.31 | -4.17 (47) |
| wncaab_move_follow | paper | paper since added | 11-11, -0.29u, -4.7% | 22-24, -1.13u, -8.9% | 22-24, -1.13u, -8.9% | -1.13 | - |
| sharp nba watch | paper | 11/10 sharp flags to paper | 7-6, +0.44u, +10.4% | 18-26, -3.98u, -22.9% | 18-26, -3.98u, -22.9% | -2.09 | -0.27 (44) |
| sharp nfl A | paper | 11/10 sharp flags to paper | 6-5, +1.47u, +47.0% | 16-26, -1.37u, -10.3% | 16-26, -1.37u, -10.3% | -7.51 | +0.03 (39) |
| tennis_hot_dog | paper | 11/17 tennis to paper (serve dog only) | 3-11, -1.67u, -47.3% | 12-29, -3.22u, -31.3% | 12-29, -3.22u, -31.3% | -3.22 | -0.98 (40) |
| sharp nhl A | paper | 11/10 sharp flags to paper | 5-11, -1.92u, -39.2% | 10-26, -4.72u, -43.5% | 10-26, -4.72u, -43.5% | -3.79 | +0.30 (35) |
| kalshi_nhl_flow | paper | paper since added | - | 20-14, +0.29u, +1.7% | 20-14, +0.29u, +1.7% | +0.29 | -2.25 (21) |
| sharp cbb B | paper | 11/10 sharp flags to paper | 1-1, +0.06u, +11.1% | 8-7, -0.08u, -1.8% | 8-7, -0.08u, -1.8% | -0.08 | +0.49 (11) |
| sharp cfb B | paper | 11/10 sharp flags to paper | 1-1, -0.04u, -7.1% | 8-3, +3.22u, +49.5% | 8-3, +3.22u, +49.5% | +0.74 | -0.07 (8) |
| stale_book_sb4 | paper | paper since added | 2-2, +0.17u, +14.8% | 4-6, -0.64u, -20.7% | 4-6, -0.64u, -20.7% | -0.64 | +3.24 (10) |
| sharp cbb A | paper | 11/10 sharp flags to paper | - | 4-6, -1.23u, -35.2% | 4-6, -1.23u, -35.2% | +0.87 | -7.35 (9) |
| sharp nba C | paper | 11/10 sharp flags to paper | 3-2, +0.17u, +11.6% | 6-3, +0.67u, +26.1% | 6-3, +0.67u, +26.1% | +0.25 | +1.62 (9) |
| sharp nfl B | paper | 11/10 sharp flags to paper | 1-0, +0.25u, +47.1% | 7-1, +1.60u, +44.4% | 7-1, +1.60u, +44.4% | +0.25 | +0.32 (7) |
| sharp cbb C | paper | 11/10 sharp flags to paper | 2-2, -0.13u, -9.8% | 5-3, +0.32u, +12.7% | 5-3, +0.32u, +12.7% | - | -2.38 (7) |
| sharp nfl C | paper | 11/10 sharp flags to paper | 1-0, +0.25u, +75.2% | 4-1, +0.86u, +53.3% | 4-1, +0.86u, +53.3% | - | +0.69 (5) |
| wncaab_dog_7_10 | paper | paper since added | 1-2, -0.29u, -35.9% | 1-4, -0.82u, -60.9% | 1-4, -0.82u, -60.9% | -0.82 | - |
| sharp nhl C | paper | 11/10 sharp flags to paper | 2-1, +0.20u, +19.5% | 2-1, +0.20u, +19.5% | 2-1, +0.20u, +19.5% | - | -0.31 (3) |
| sharp cfb C | paper | 11/10 sharp flags to paper | 2-0, +0.53u, +100.0% | 2-0, +0.53u, +100.0% | 2-0, +0.53u, +100.0% | - | +2.96 (2) |
| sharp nhl B | paper | 11/10 sharp flags to paper | - | 0-2, -1.20u, -100.0% | 0-2, -1.20u, -100.0% | - | -2.75 (2) |
| kmove (Kalshi 4+ mover) | paper (sized) | 11/23 watch to sized paper (checkpoint) | 269-223, +3.52u, +1.8% | 827-688, +2.90u, +0.5% | 827-688, +2.90u, +0.5% | - | -0.80 (1381) |
| nba_momentum | retired | 11/9 checkpoint | - | 18-40, -6.18u, -32.3% | 18-40, -6.18u, -32.3% | -6.18 | -1.51 (57) |
| cfb_road_dog_low_total | retired | 11/23 checkpoint | 4-4, -0.06u, -2.7% | 14-16, -0.79u, -9.9% | 14-16, -0.79u, -9.9% | -0.79 | -4.22 (27) |
| cfb_day_over | retired | 11/21 paper, 11/23 retired | 8-2, +1.46u, +55.0% | 11-16, -1.66u, -22.6% | 11-16, -1.66u, -22.6% | -1.66 | -2.34 (23) |

## 2. Paper and live moves in the last two weeks, and results since

The 18-rule move on 11/18 counts games starting from 11/19 04:00 UTC. As a group: 22-11, +1.91u, +20.0% since, but CLV -4.46 on 29.
The prices they got were well worse than the close, so the week reads as variance more than edge. Before the move, as paper, the same
rules went 57-105 (-28.5%), most of it nba_momentum (18-40, retired 11/9).

| Rule | Move (date, why) | Since the move | CLV since |
|---|---|---|---|
| xch_homedog_fade | paper -> tier C (Sean 11/14) | 39-13, +1.79u, +5.4% | -1.07 (52) |
| nhl_p3_under_curve | paper -> tier C (Sean 11/18; had gone B -> paper 11/14 after 0-5) | 3-4-1, -0.31u, -13.8% | - |
| nfl_home_dog_7510 | B -> C (Sean 11/19, PUSHBACK re-score) | no graded bets yet | - |
| tennis_serve_dog | only real-money tennis angle (Sean 11/16) | 14-14, +0.30u, +4.1% | -2.16 (26) |
| sharp soccer A | paper -> live 0.25u (Sean 11/21) | 3-3, -0.17u, -7.7% | +0.89 (5) |
| sharp soccer B | paper -> live 0.25u (Sean 11/21) | no graded bets yet | - |
| cfb_day_over | paper -> C 11/19; back to paper 11/21 (Sean); retired 11/23 (checkpoint) | 7-2, +1.21u, +50.5% | -2.68 (6) |
| cfb_road_dog_low_total | paper -> C 11/19; retired 11/23 (checkpoint retire line A) | 3-4, -0.31u, -16.3% | -1.17 (6) |
| awfuldog_deep | paper -> tier C (Sean 11/18 blanket move) | no graded bets yet | - |
| wind1014_cold | paper -> tier C (Sean 11/18 blanket move) | no graded bets yet | - |
| nfl_road_dog_7510 | paper -> tier C (Sean 11/18 blanket move) | 1-1, -0.02u, -4.2% | -5.74 (2) |
| nhl_loss_streak_over | paper -> tier C (Sean 11/18 blanket move) | 2-0, +0.50u, +97.0% | -7.38 (2) |
| mlb_road_over_under | paper -> tier C (Sean 11/18 blanket move) | no graded bets yet | - |
| nba_roadtrip_over | paper -> tier C (Sean 11/18 blanket move) | 4-1, +0.72u, +52.4% | -8.84 (5) |
| nfl_fade_fav_bye | paper -> tier C (Sean 11/18 blanket move) | 0-2, -1.22u, -100.0% | -14.75 (2) |
| bounce15_1h | paper -> tier C (Sean 11/18 blanket move) | 0-1, -0.27u, -100.0% | -0.58 (1) |
| nba_momentum | paper -> tier C (Sean 11/18 blanket move) | no graded bets yet | - |
| nhl_pl_fav_gap | paper -> tier C (Sean 11/18 blanket move) | no graded bets yet | - |
| nhl_pl_fav_strong_opp | paper -> tier C (Sean 11/18 blanket move) | 1-0, +0.28u, +112.8% | -2.64 (1) |
| nhl_pl_dog_bigml | paper -> tier C (Sean 11/18 blanket move) | no graded bets yet | - |
| nba_1h_under_hot_over | paper -> tier C (Sean 11/18 blanket move) | 1-0, +0.25u, +90.5% | -2.75 (1) |
| nba_under_good_home_over_small | paper -> tier C (Sean 11/18 blanket move) | 1-0, +0.25u, +92.6% | -3.07 (1) |
| cfb_road_streak_dog | paper -> tier C (Sean 11/18 blanket move) | 1-0, +0.25u, +98.0% | +5.00 (1) |
| cbb_under_good_over_drop | paper -> tier C (Sean 11/18 blanket move) | 1-0, +0.25u, +90.5% | -2.28 (1) |

Also moved in the period, with no graded bets of their own to show here:
- 11/10: every sharp flag to paper, no units, until they beat Pinnacle's close.
- 11/14: nhl_p3_under_curve B to paper after 0-5. Back to tier C 11/18.
- 11/18: everything sized at 0.25u. Tiers re-scored on the full Bet Labs backtests (PUSHBACK.md).
- 11/23 checkpoint:
  - steam_rev retired: CLV -0.42 on 722, z -2.57.
  - Kalshi 4+ movers moved from watch to sized paper. On Pinnacle's close: CLV +0.54 on 283, z 3.83. On the no-vig close used here: -0.80 on 1,381, +0.5% ROI. The two yardsticks disagree.

## 3. Flags

**Live rules underperforming.** Sample size and how likely it is noise. z is roughly ROI / its standard error on 0.25u bets:
- **nhl_p3_under_curve (C): 9-21-10, -32.5% on 40, about z -2. Not noise at this size.** It went B to paper after 0-5 on 11/14, then
  back to C with the 11/18 blanket sizing call, and is 3-4-1 since. This is the one live rule I would put in front of Sean to move back to paper.
- nhl_early_home_fav_qual (B): 13-12, -10.1%, CLV -1.41 on 25. About z -0.6, so noise on results, but the checkpoint has it near the
  review line (review if CLV passes -1.5, retire at -2.0).
- tennis_serve_dog (live): 49-50, +3.7% on 99, CLV -2.26 on 97. The profit is noise (z about 0.3). Negative CLV on 97 bets is the
  real warning: the prices taken are worse than where these close. Not a retire case yet. It is the only live tennis angle.
- Small and bad, too few bets to judge:
  - nfl_home_dog_7510 0-4 (B to C on 11/19)
  - awfuldog (A) 0-4
  - vrest8_1h (B) 3-5, CLV -4.49
  - nfl_fade_fav_bye 2-3, CLV -7.75
  - bounce15_1h 2-6
  - nhl_loss_streak_over 4-9, CLV -9.43 (near the review line)
  - cfb_homefav_7510_under 4-6, CLV -2.74
  - nhl_bounce_home_ml 2-4

  All are under 15 graded bets. Under the 11/2 checkpoint lines, nothing below 15 can be reviewed and nothing below 25 can be retired.
- cfb_wind14 (A): 1-6 this week but 14-9 overall (+20%). One bad weekend. No flag.

**Paper rules that look closest to ready.** None clears a clean bar. In order:
1. **stale_book:** 116-134, +3.3% on 250, **CLV +0.57 on 249**, and +25.8% this week. It is the only paper line with positive CLV on a
   real sample. Sean's 11/18 call keeps stale-book flags as they are. A small live test (tier C, 0.25u) is the option to offer.
2. Sharp NBA B: 30-22, +14.3%, but CLV -1.12 on 51. NBA A is 26-25 (+2.9%). On the checkpoint's numbers, NBA sharp is 73-76, -7.7%.
   Not ready on CLV.
3. tennis_fs_fav: 34-16, +8.7% on 50, CLV -1.9. The checkpoint sets its first read at 300 bets.
4. Too small to call:
   - nba_threes_under_gap (props): 12-9, +15.4%
   - mma_steam_fav: 5-0
   - nba_1h_under_hot_over: 5-1, CLV +0.74
   - nba_badteams_under: 4-2, CLV +1.18

## 4. The rule-groups question (open since 11/21)

On 11/21 Sean moved cfb_day_over back to paper: a kickoff time slot is no reason for a bet. He asked which other rules have faulty
logic or simplistic triggers. The checkpoint has since retired cfb_day_over and cfb_road_dog_low_total on its own lines. Updated
groups, with results:

- **Group 1, failed our own replay before the 11/18 blanket move** (all tier C now):
  - nfl_road_dog_7510 1-3
  - nfl_fade_fav_bye 2-3
  - bounce15_1h 2-6
  - nhl_pl_fav_strong_opp 3-5
  - nhl_pl_fav_gap 0-1
  - nba_under_good_home_over_small 1-1
  - cfb_road_streak_dog 5-4
  - cbb_under_good_over_drop 4-3
  - awfuldog_deep: no bets yet
  - wind1014_cold: no bets yet

  Combined: 18-26 on the log.
- **Group 2, mined triggers with no mechanism:**
  - nba_ats_hot_home 11-9
  - nhl_loss_streak_over 4-9
  - nhl_skid_fade_road 8-1
  - nhl_pl_dog_bigml 3-4
  - mlb_road_over_under: out of season

  nba_momentum was already retired 11/9.
- **Group 3, day-of-week trigger:** mnf_1h (tier B), no graded bets on this log yet.

Options, plainly:
- **A. Leave all as tier C** and let the checkpoint lines decide (review at 15 graded, retire at 25 or 50). Costs nothing now. The
  logic objection stays unaddressed, and these rules keep 0.25u bets on the board.
- **B. Group 1 to paper.** They failed the replay and are 18-26 live. Removes about 5 to 10 board bets a week.
- **C. Groups 1 + 2 to paper.** Applies the "needs a mechanism" bar to everything. It costs nhl_skid_fade_road, which is 8-1 (hot,
  but 9 bets is noise).
- **D. 1 + 2 + 3.** Same as C, plus moving mnf_1h off tier B.
- **E. Per rule.** Sean picks names.

Any move would apply to games not yet started, the same way cfb_day_over was handled. Nothing has moved without his OK.
