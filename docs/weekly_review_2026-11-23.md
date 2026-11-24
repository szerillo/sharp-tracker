# Weekly systems review, 2026-11-23 (revised 11/24: judged on profit, not CLV)

Read only: no rule, tier or paper/live status was changed for this review.

**Revision, 11/24 (Sean via Kirk).** The project's premise is finding edges the market misses, which CLV may not capture. So no
keep, retire, promote or paper call in this review rests on CLV. Every call is judged on realized profit:
- units and ROI at the actual prices taken
- sample size
- a significance read
- whether the result holds in both halves of the sample

CLV stays in the tables as information only. The first version of this review leaned on CLV in a few places: it called stale_book
ready, it discounted the 11/19 group's good week, and it pointed to tennis_serve_dog's CLV. Those calls are redone below.

**Method.** Graded games that started before Tue 11/24 05:00 UTC, from data/state/bet_log.json (built 2026-11-24T04:38Z). The log
starts 10/30.
- **Units:** every row at flat 0.25u (favourite to win 0.25u, plus money risk 0.25u). ROI = units / risk.
- **Significance, two ways:**
  - A bootstrap of the bets gives a 90% range for ROI.
  - A break-even test re-plays every bet 4,000 times with the win chance its own price implies. That gives the chance of a result at
    least this good, or at least this bad, if the rule had no edge at those prices.
- **Holds across sub-periods:** ROI in the first and second half of each rule's bets, in date order.
- **Caveat:** with about 60 slices tested, about 3 will look significant at 5% by luck alone. That is why the halves are read too.
- **Bet Labs backtests:** these live samples are small next to the full Bet Labs backtests the systems were chosen on. Sean's 11/18
  call makes those the primary evidence, so a live read below is a flag, not a verdict.

## Summary (profit basis)

| | Graded | Units | ROI (90% range) | Break-even test | Halves | Read |
|---|---|---|---|---|---|---|
| **Live categories, total** | 460 | +3.20 | +2.0% | | | Break-even so far |
| **nhl_p3_under_curve (live C)** | 42 | -4.00 | -34.0% (-54 to -13) | 0.3% chance this bad if break-even | -51% / -17% | **Clearly losing, both halves.** Strongest case to move to paper |
| cfb_q1_under_curve (live A) | 42 | -1.56 | -13.9% (-38 to +11) | 21% | -14% / -13% | Losing steadily, not significant. Tier A on a 296-189 backtest; watch |
| nhl_early_home_fav_qual (live B) | 25 | -0.98 | -10.1% (-37 to +16) | 26% | +9% / -22% | Noise |
| nhl_loss_streak_over (live C) | 13 | -1.51 | -42.0% (-85 to +1) | 5% | -66% / -25% | Bad and consistent, small sample |
| tennis_serve_dog (live) | 99 | +0.94 | +3.7% (-14 to +21) | 36% chance this good if break-even | +8% / 0% | Flat. No evidence for or against. Keep |
| xch_homedog_fade (live C) | 110 | +3.06 | +4.4% (-5 to +14) | 24% | +7% / +2% | Positive in both halves, not significant |
| Wind: wind1014 / wind1014_1h / cfb_wind14 | 12 / 9 / 23 | +0.98 / +1.24 / +1.20 | +31% / +52% / +20% | 11% / 10% / 19% | mixed | All positive. wind1014_1h's 90% range sits above zero |
| nhl_skid_fade_road (live C) | 9 | +2.40 | +68.2% (+37 to +113) | 1.3% | +115% / +39% | Significant on 9 bets |
| The 11/19 tier-C group, since the move | 33 | +1.91 | +20.0% (-10 to +52) | 11% | +47% / -1% | Good so far, not yet significant |
| Same rules, before the move (paper) | 162 | -12.83 | -28.5% | | | Most of it nba_momentum (-6.18u, retired 11/9). The other 17: -5.46u on 137 |
| Sharp soccer A (live since 11/21) | 54 | +3.47 | +20.5% (-4 to +44) | 9% | +11% / +30% | Positive in both halves. Its live call holds on profit |
| Sharp NBA B (paper) | 52 | +2.75 | +14.3% (-4 to +34) | 13.5% | +4% / +29% | **Best paper candidate on profit**, short of significant |
| tennis_fs_fav (paper) | 50 | +2.06 | +8.7% (-6 to +23) | 20% | +20% / +1% | Promising. First read is set at 300 |
| stale_book (paper) | 253 | +1.35 | +2.1% (-9 to +14) | 39% | -17% / +22% | **Not ready.** Break-even on profit and flips between halves (the first version called it ready on CLV) |
| Kalshi 4+ movers (sized paper) | 1,515 | +2.90 | +0.5% (-3 to +4) | 41% | +5% / -4% | No profit edge. -3 to -4% after Kalshi's fee |
| Sharp NHL A (paper) | 37 | -4.47 | -40.3% (-65 to -16) | 0.5% | -42% / -38% | Significantly bad (paper) |

**Decisions waiting for Sean** (none made here):
1. nhl_p3_under_curve back to paper?
2. The rule-groups options (section 4, now with profit evidence).
3. Re-decide the checkpoint calls that rested on CLV (section 5).
4. Adopt profit-based checkpoint lines (section 6).
5. The wind source, MySportsWeather alone vs the two-source average (open since 11/22).

## 1. Every rule, last 7 days / 30 days / all (flat 0.25u: record, units, ROI; CLV is information only)

| Rule | Status | Since | Last 7 days | Last 30 days | All (log from 10/30) | Board units, all | CLV, all (info only) |
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

## 1b. Significance on profit, every rule with 5+ graded bets (sorted from worst to best)

| Rule or group | Graded | Units (0.25u) | ROI | ROI 90% range (bootstrap) | Chance of a result this good if break-even | Chance of a result this bad if break-even | ROI, 1st half / 2nd half |
|---|---|---|---|---|---|---|---|
| 18 promoted: all | 195 | -11.64 | -20.4% | -32% to -9% | 0.999 | 0.001 | -27% / -14% |
| nhl_p3_under_curve | 42 | -4.00 | -34.0% | -54% to -13% | 0.997 | 0.003 | -51% / -17% |
| nba_momentum | 58 | -6.18 | -32.3% | -53% to -14% | 0.996 | 0.004 | -36% / -30% |
| sharp nhl A | 37 | -4.47 | -40.3% | -64% to -16% | 0.995 | 0.005 | -42% / -38% |
| sharp nba watch | 44 | -3.98 | -22.9% | -44% to -2% | 0.953 | 0.047 | -28% / -18% |
| nhl_loss_streak_over | 13 | -1.51 | -42.0% | -85% to +1% | 0.953 | 0.048 | -66% / -25% |
| tennis_hot_dog | 41 | -3.22 | -31.3% | -58% to -2% | 0.942 | 0.059 | -53% / -10% |
| group1 all | 44 | -2.58 | -20.4% | -45% to +7% | 0.914 | 0.086 | -42% / -1% |
| nfl_fade_fav_bye | 5 | -1.01 | -49.3% | -100% to +52% | 0.931 | 0.088 | -7% / -65% |
| cfb_day_over | 27 | -1.66 | -22.6% | -51% to +7% | 0.911 | 0.089 | -71% / +24% |
| sharp cbb A | 10 | -1.23 | -35.2% | -73% to +12% | 0.912 | 0.091 | +13% / -68% |
| bounce15_1h | 8 | -1.09 | -49.7% | -100% to -2% | 0.875 | 0.129 | -100% / -4% |
| nhl_bounce_home_ml | 6 | -0.86 | -41.1% | -100% to +20% | 0.865 | 0.148 | -100% / +14% |
| wncaab_dog_7_10 | 5 | -0.82 | -60.9% | -100% to +15% | 0.939 | 0.155 | -100% / -36% |
| tennis_hot_fav | 47 | -2.85 | -7.7% | -22% to +6% | 0.829 | 0.172 | -27% / +9% |
| vrest8_1h | 8 | -0.59 | -27.9% | -77% to +23% | 0.828 | 0.176 | -4% / -52% |
| sharp cfb A | 74 | -1.96 | -9.3% | -27% to +8% | 0.804 | 0.196 | -17% / -1% |
| cfb_q1_under_curve | 42 | -1.56 | -13.9% | -38% to +11% | 0.790 | 0.210 | -14% / -13% |
| nfl_prop_under_gap | 19 | -1.20 | -25.3% | -72% to +23% | 0.758 | 0.242 | -35% / -16% |
| stale_book_sb4 | 10 | -0.64 | -20.7% | -68% to +35% | 0.756 | 0.246 | -34% / -5% |
| nhl_early_home_fav_qual | 25 | -0.98 | -10.1% | -37% to +16% | 0.744 | 0.256 | +9% / -22% |
| cfb_road_dog_low_total | 30 | -0.79 | -9.9% | -36% to +17% | 0.741 | 0.259 | -10% / -10% |
| tennis_serve_fav | 53 | -2.10 | -4.6% | -18% to +8% | 0.734 | 0.267 | -11% / +2% |
| wncaab_move_follow | 46 | -1.13 | -8.9% | -34% to +13% | 0.728 | 0.272 | -9% / -9% |
| sharp nfl A | 43 | -1.62 | -12.0% | -38% to +14% | 0.727 | 0.273 | -50% / +27% |
| cfb_homefav_7510_under | 10 | -0.58 | -21.8% | -62% to +34% | 0.731 | 0.287 | -22% / -22% |
| cfb_tt_under_curve | 38 | -0.95 | -8.7% | -34% to +16% | 0.705 | 0.295 | -37% / +19% |
| nhl_pl_dog_bigml | 7 | -0.33 | -17.1% | -73% to +38% | 0.686 | 0.314 | -32% / -6% |
| cbb_1h_total_curve | 9 | -0.12 | -4.7% | -55% to +46% | 0.583 | 0.425 | -8% / -2% |
| sharp cbb B | 15 | -0.08 | -1.8% | -42% to +41% | 0.566 | 0.434 | -4% / +0% |
| cfb_road_streak_dog | 9 | +0.01 | +0.5% | -46% to +49% | 0.559 | 0.441 | -53% / +38% |
| kalshi_nhl_flow | 34 | +0.29 | +1.7% | -18% to +20% | 0.466 | 0.534 | +10% / -4% |
| nhl_prop_under_gap | 34 | +0.29 | +3.3% | -26% to +32% | 0.442 | 0.558 | +8% / -1% |
| nhl_pl_fav_strong_opp | 8 | +0.11 | +5.4% | -73% to +92% | 0.438 | 0.572 | -14% / +25% |
| kmove (Kalshi 4+ mover) | 1515 | +2.90 | +0.5% | -3% to +4% | 0.409 | 0.591 | +5% / -4% |
| sharp nba A | 51 | +0.52 | +2.9% | -18% to +23% | 0.407 | 0.593 | -10% / +15% |
| nba_bigfav_over | 11 | +0.19 | +6.5% | -46% to +58% | 0.401 | 0.611 | +18% / -3% |
| stale_book | 253 | +1.35 | +2.1% | -9% to +14% | 0.387 | 0.613 | -17% / +22% |
| tennis_serve_dog | 99 | +0.94 | +3.7% | -14% to +21% | 0.357 | 0.643 | +8% / -0% |
| nba_ats_hot_home | 20 | +0.32 | +5.8% | -32% to +41% | 0.339 | 0.661 | +34% / -22% |
| group2 all | 49 | +0.88 | +6.0% | -16% to +27% | 0.331 | 0.669 | +12% / +1% |
| sharp cbb C | 8 | +0.32 | +12.7% | -33% to +58% | 0.332 | 0.680 | +36% / -10% |
| cbb_under_good_over_drop | 7 | +0.23 | +12.0% | -43% to +64% | 0.276 | 0.733 | +30% / -2% |
| nba_threes_under_gap | 21 | +0.88 | +15.4% | -20% to +50% | 0.248 | 0.751 | +19% / +12% |
| xch_homedog_fade | 110 | +3.06 | +4.4% | -5% to +14% | 0.239 | 0.760 | +7% / +2% |
| nhl_p1_spread_curve | 10 | +0.82 | +19.2% | -19% to +46% | 0.228 | 0.782 | +6% / +31% |
| nba_roadtrip_over | 10 | +0.45 | +16.7% | -40% to +56% | 0.215 | 0.792 | -21% / +52% |
| tennis_fs_fav | 50 | +2.06 | +8.7% | -6% to +23% | 0.196 | 0.804 | +20% / +1% |
| cfb_wind14 | 23 | +1.20 | +20.2% | -14% to +54% | 0.191 | 0.809 | +63% / -18% |
| sharp nba C | 9 | +0.67 | +26.1% | -18% to +69% | 0.173 | 0.832 | +46% / +12% |
| nba_badteams_under | 6 | +0.49 | +28.5% | -34% to +84% | 0.172 | 0.846 | +80% / -34% |
| sharp nba B | 52 | +2.75 | +14.3% | -4% to +34% | 0.135 | 0.865 | +4% / +29% |
| nba_1h_under_hot_over | 6 | +0.96 | +57.5% | -7% to +91% | 0.140 | 0.876 | +25% / +90% |
| nba_under_good_home_over | 14 | +0.97 | +26.5% | -15% to +67% | 0.113 | 0.887 | +40% / +13% |
| wind1014 | 12 | +0.98 | +31.1% | -17% to +66% | 0.111 | 0.891 | +63% / -1% |
| 18 promoted: since 11/19 | 33 | +1.91 | +20.0% | -10% to +52% | 0.107 | 0.892 | +46% / -1% |
| wind1014_1h | 9 | +1.24 | +51.8% | +7% to +95% | 0.095 | 0.908 | +43% / +59% |
| sharp soccer A | 54 | +3.47 | +20.5% | -4% to +44% | 0.089 | 0.911 | +11% / +30% |
| sharp nfl C | 5 | +0.86 | +53.3% | -14% to +104% | 0.080 | 0.956 | +2% / +78% |
| sharp nfl B | 8 | +1.60 | +44.4% | +20% to +80% | 0.060 | 0.956 | +47% / +40% |
| sharp cfb B | 11 | +3.22 | +49.5% | +5% to +154% | 0.015 | 0.985 | +235% / -1% |
| nhl_skid_fade_road | 9 | +2.40 | +68.2% | +36% to +112% | 0.013 | 0.991 | +115% / +39% |
| mma_steam_fav | 5 | +1.25 | +45.6% | +37% to +60% | 0.130 | 1.000 | +40% / +50% |

## 2. Paper and live moves in the last two weeks, and results since

| Rule | Move (date, why) | Since the move | CLV since (info only) |
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

Also in the period:
- 11/10: every sharp flag moved to paper, no units, until it beats Pinnacle's close. That is a CLV criterion; see section 5.
- 11/14: nhl_p3_under_curve went B to paper after 0-5, then back to tier C on 11/18.
- 11/18: everything sized at 0.25u, and tiers re-scored on the full Bet Labs backtests.
- 11/23: the checkpoint retired three rules and moved Kalshi movers to sized paper (section 5).

## 3. Flags (profit basis)

**Live rules underperforming:**
- **nhl_p3_under_curve (C): -34.0% on 42 bets, -4.00u.** There is a 0.3% chance of a result this bad if it were break-even at its
  prices, and both halves are negative (-51%, -17%). It went 0-5 into its first demotion on 11/14, came back on the 11/18 sizing
  call, and is 3-4-1 since. This is the one live rule whose live record alone makes a case. It has no Bet Labs backtest; it is our
  own curve rule. Recommend: paper.
- nhl_loss_streak_over (C): -42.0% on 13, 5% chance if break-even, both halves negative. Bad, but 13 bets.
- cfb_q1_under_curve (A): -13.9% on 42, both halves about -14%. Not significant (21%), but steady. Its pre-live test was 296-189
  (+15.0%, every season +10 to +19). Live is well below that. Watch; no change yet.
- nhl_early_home_fav_qual (B): -10.1% on 25, halves +9% and -22%. Noise on profit. Its Bet Labs backtest is +3.7% on 1,953.
- Too small to read (under 10 bets each): nfl_home_dog_7510 0-4, awfuldog 0-4, vrest8_1h 3-5, nfl_fade_fav_bye 2-3, bounce15_1h 2-6,
  nhl_bounce_home_ml 2-4, cfb_homefav_7510_under 4-6. Each of these sits on a Bet Labs backtest of hundreds of bets, which outweighs
  a 4 to 10 bet live run.

**tennis_serve_dog (the only live tennis angle):** 49-50, +0.94u, +3.7% on 99. The 90% range is -14% to +21%, with a 36% chance of
a result this good if break-even. The halves are +8% and 0%. No evidence of an edge yet, and none against it. Keep it as it is; read
again at 200. (The first version flagged its CLV; that no longer counts.)

**The 11/19 tier-C group:** 22-11, +1.91u, +20.0% since the move. Not yet significant (11%), and the halves are +47% and -1%.
Before the move, as paper, the same rules lost -12.83u on 162, mostly nba_momentum (already retired). The other 17 rules lost -5.46u
on 137 as paper. Fair read: a good first week after a losing paper run. Too early to say the move was right or wrong.

**Paper rules closest to live, on profit.** None clears a 100-bet significance bar yet. In order:
1. **Sharp NBA B:** 30-22, +2.75u, +14.3% on 52; 13.5% if break-even; positive in both halves (+4%, +29%). Sharp NBA A is 26-25,
   +2.9%. Together, NBA A+B: 56-47, +3.27u. It would need about 50 more flags at this rate to clear 10%. A small live test (B only,
   0.25u) is the option to offer Sean.
2. **tennis_fs_fav:** 34-16, +2.06u, +8.7% on 50; 20%; halves +20% and +1%.
3. **Too small to call, though the profit is real so far:**
   - sharp NFL B: 7-1, +44%, 90% range above zero
   - sharp CFB B: 8-3, +49.5%, but one half carries it
   - mma_steam_fav: 5-0
   - nba_threes_under_gap: 12-9, +15.4%, both halves positive; already live as a C prop
- **stale_book is no longer on this list:** +2.1% on 253, 39% chance if break-even, halves -17% and +22%. It was the first
  version's top pick only because of its CLV.
- Sharp NHL A is the clearest paper loser: -40.3% on 37, both halves negative.

## 4. The rule-groups question (open since 11/21), with profit evidence

On 11/21 Sean moved cfb_day_over back to paper: a kickoff time slot is no reason for a bet. He asked which other rules have faulty
logic or simplistic triggers. The three groups below are unchanged from the first version. What is new is the profit evidence.

- **Group 1, failed our own replay before the 11/18 blanket move:**
  - Rules: nfl_road_dog_7510, nfl_fade_fav_bye, bounce15_1h, nhl_pl_fav_strong_opp, nhl_pl_fav_gap, nba_under_good_home_over_small,
    cfb_road_streak_dog, cbb_under_good_over_drop. awfuldog_deep and wind1014_cold have no bets yet.
  - Live and paper on this log: 44 bets, -2.58u, -20.4% (90% range -45% to +7%). 8.6% chance of a result this bad if break-even.
    Halves -42% and -1%.
  - That replay failure was itself a profit test: negative ROI in our own multi-season rebuild.
- **Group 2, mined triggers with no mechanism:**
  - Rules: nba_ats_hot_home, nhl_loss_streak_over, nhl_skid_fade_road, nhl_pl_dog_bigml, mlb_road_over_under (out of season).
  - 49 bets, +0.88u, +6.0% (-16% to +27%). Halves +12% and +1%. No profit case against the group as a whole.
  - Inside it, nhl_skid_fade_road is +68% on 9 (1.3% chance if break-even) and nhl_loss_streak_over is -42% on 13 (5%).
- **Group 3, day-of-week trigger:** mnf_1h (tier B). No graded bets on this log. Its Bet Labs screen is 169-120 (+11.7%).

**Options, on profit:**
- **A. Keep all at tier C** and let the checkpoint lines decide (section 6 proposes profit-based ones). Group 2 has no profit case
  against it, and group 1's is not significant.
- **B. Group 1 to paper.** It failed our own profit replay and is -20.4% live on 44 (8.6%). Best supported on profit.
- **C. Groups 1 + 2 to paper.** The profit evidence does not support moving group 2 as a group (+6% on 49). This is a logic call
  only, and it would bench the one rule here with a significant live profit (nhl_skid_fade_road).
- **D. Groups 1 + 2 + 3.** Adds mnf_1h, which has a positive Bet Labs backtest and no live sample. Logic only.
- **E. Per rule.** On profit, the names with a case: nhl_loss_streak_over (-42% on 13, both halves) plus group 1. On profit, the one
  to keep is nhl_skid_fade_road.

## 5. The 11/23 checkpoint calls that rested on CLV (for Sean to re-decide; nothing reversed here)

| Call | Line used | CLV part of the decision? | Profit evidence | Re-decide? |
|---|---|---|---|---|
| cfb_road_dog_low_total retired | Systems retire line A: 25+ graded, ROI negative AND CLV 2.0+ worse than the close | **Yes**: without the CLV test, negative ROI alone does not trigger line A | 14-16, -0.79u, -9.9% on 30; 26% chance this bad if break-even; halves -10% / -10% | **Yes.** Losing in both halves, not significant. On profit alone it would stay, or go to the review list |
| cfb_day_over retired | Same line A | **Yes** | 11-16, -1.66u, -22.6% on 27; 9% chance; halves -71% / +25% | Profit is borderline and inconsistent. Sean had already moved it to paper on 11/21 on logic grounds, so it stays off the board either way. Only the retire label rests on CLV |
| steam_rev retired | Top-down retire line: 50+ graded, CLV at or below zero, z -1 or worse | **Yes, entirely** | 365-360, -15.89u, -2.2% on 725 (z -0.55); -1.7% on the corrected grading (371-354). Not significantly below break-even | **Yes.** On profit, a small loss that is not significant |
| Kalshi 4+ movers promoted from watch to sized paper | Top-down promote line: 150+ graded, CLV z 2+, ROI not below -5% | **Yes**: the CLV z was the trigger; the ROI part is only a floor | +0.5% on 1,515 (-3% to +4%); halves +5% / -4%; -3 to -4% after Kalshi's taker fee | **Yes.** No profit edge. It is paper, so it costs nothing to leave, but it was promoted on CLV |

Also CLV-based and older: on 11/10 the sharp flags went to paper "until they beat Pinnacle's close". On profit, soccer A (+20.5% on
54) and NBA B (+14.3% on 52) are the positive slices; NHL A (-40%) and NBA watch (-23%) are the negative ones.

## 6. The 11/2 checkpoint lines use CLV: proposed profit-based replacements (for Sean)

What docs/checkpoint_rules_2026-11-02.md says now:
- Systems: CLV is "a diagnostic, not the verdict". Even so, retire line A and the review line both require a CLV test.
- Top-down signals: "CLV is the main test", for both retire and promote.

Proposed replacement. Profit only, CLV reported but never deciding. It applies the same way to systems and signals that are bet or
paper-bet.

- **Retire:** at 50+ graded, when the break-even test gives a 5% or smaller chance of a result this bad AND ROI is negative in both
  halves. Or at 25+ graded with a 1% or smaller chance. For a rule picked on a Bet Labs backtest, also require that the live 90% ROI
  range sits entirely below the backtest's ROI. A small live sample should not overrule a large backtest without that.
- **Review (flag on the page, no change):** at 15+ graded, with a 10% or smaller chance of a result this bad.
- **Promote, paper to live (tier C, 0.25u):** at 100+ graded, a 10% or smaller chance of a result this good if break-even, after any
  fees, AND ROI positive in both halves.
- **Promote, watch to sized paper:** at 150+ graded, the same test.
- **Tennis first-set favourites:** keep the first read at 300; retire early only at 100+ with a 5% or smaller chance.
- **Unchanged:** one week is never enough on its own; each checkpoint writes what it read and why.

Under these lines, today:
- **Retire:** nhl_p3_under_curve would meet it (42 graded, 0.3%, both halves negative). It has no backtest to check against.
- **Review:** nhl_loss_streak_over would join the list. Sharp NHL A also qualifies, but it is paper.
- **Promote:** nothing yet; none reaches 100 graded with a significant profit.
- **Checkpoint calls:** cfb_road_dog_low_total, steam_rev and the Kalshi-mover promotion would not have happened.
