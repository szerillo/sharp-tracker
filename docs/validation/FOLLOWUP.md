# Validation audit follow-up (board_r10)

Built 2026-11-18 18:41 UTC by sharp/validate_followup.py. Sections 1 to 3 of Kirk's 11/18 follow-up. Discovery (section 4) is in [DISCOVERY.md](DISCOVERY.md). Recommendations only: no tier in the tool was changed.

## 1. What the verdicts were based on (two-minute read)

**CLV played no part.** Every number in the audit is profit on graded results: each historical bet is placed at Pinnacle's last price before the start and settled on the final score. Because the bet is taken at the close, CLV is zero by construction. The audit asks only whether the result beats the closing price, which is the "what the market misses" question Sean cares about. CLV appears on the board as a diagnostic only.

**Correction on the bar.** The search-adjusted test (gate 2) had a bar of p < 0.05, not 0.01. The 0.01 bar belonged to gate 4, the shuffle test on the blind walk-forward results, and applied only when a system had 2 or more blind seasons.

**What the search-adjusted test protects against.** Every system was picked from a range of nearby versions (wind 10 to 14 rather than 9 to 15, a 60% ATS cutoff rather than 55%). Search enough versions of any idea and the best one will look good even on random results. The test shuffles the results, re-runs the same range, and asks how often the best version on noise matches the real system. If it does so a third of the time, the in-sample record says little on its own.

**How many of the 16 systems pass each test:**

| Test | p < 0.01 | p < 0.05 | p < 0.10 |
|---|---|---|---|
| Search-adjusted (gate 2) | 0 | 0 | 1 |
| Plain single-filter permutation | 2 | 7 | 10 |
| Blind walk-forward permutation (gate 4) | 1 | 5 | 6 |

By chance alone you would expect about 0.8 systems below 0.05 and 1.6 below 0.10 on any one of these tests. Most systems look real on the plain test and do not survive the search-adjusted one. The tiers below lean on the blind walk-forward instead, because there the version is chosen on past seasons only, so the search is already paid for. They also add the live record.

## 2. Live tracker record and how much it should move each verdict

From data/state/fills.jsonl: graded fills by rule tag, voids out, each bet scored per unit risked at the filled price. All rules: 199-182, -6.8u.

Combined estimate: the blind walk-forward ROI and the live ROI, each weighted by its number of bets (a normal precision-weighted update, same per-bet spread for both). "Live weight" is the live bets' share of that weight. **The live samples are small:** at about -110, 16 bets carry a standard error of about 24 ROI points, so 13-3 is consistent with anything from no edge to a large one. A record of that size moves a 100+ bet walk-forward estimate only a little.

| System | Live record | Live ROI (N) | Blind WF ROI (N) | Combined ROI | P(ROI > 0): history only, then with live | Live weight |
|---|---|---|---|---|---|---|
| wind1014 | 8-4, +3.6u | +30.0% (12) | +28.3% (104) | +28.5% +/- 8.5 | 1.00 then 1.00 | 10% |
| cfb_hot_over_low_total | none | n/a (0) | +17.8% (119) | +17.8% +/- 8.6 | 0.98 then 0.98 | 0% |
| nhl_early_home_fav_qual | 12-10, -1.0u | -9.1% (22) | +9.3% (222) | +7.6% +/- 5.1 | 0.96 then 0.93 | 9% |
| nhl_skid_fade_road | 6-1, +3.5u | +100.4% (7) | +8.0% (169) | +11.7% +/- 8.0 | 0.84 then 0.93 | 4% |
| vrest8_1h | 3-5, -1.0u | -25.8% (8) | +37.4% (24) | +21.6% +/- 16.0 | 0.98 then 0.91 | 25% |
| mnf_1h | none | n/a (0) | +24.1% (25) | +24.1% +/- 19.1 | 0.90 then 0.90 | 0% |
| wind1014_1h | 7-2, +2.3u | +52.0% (9) | +8.4% (25) | +19.9% +/- 16.9 | 0.66 then 0.88 | 26% |
| cfb_homefav_7510_under | 4-6, -1.1u | -22.0% (10) | +8.7% (180) | +7.1% +/- 6.9 | 0.89 then 0.85 | 5% |
| nba_badteams_under | 3-1, +0.7u | +36.5% (4) | +3.7% (193) | +4.4% +/- 6.9 | 0.70 then 0.74 | 2% |
| awfuldog | 0-4, -2.0u | -100.0% (4) | +12.7% (70) | +6.6% +/- 10.8 | 0.87 then 0.73 | 5% |
| nba_bigfav_over | 5-4, +0.4u | +8.3% (9) | +2.7% (370) | +2.9% +/- 4.9 | 0.71 then 0.72 | 2% |
| nba_ats_hot_home | 9-6, +1.0u | +13.7% (15) | +3.2% (74) | +5.0% +/- 10.4 | 0.61 then 0.68 | 17% |
| cfb_wind14 | 13-3, +9.9u | +61.8% (16) | -4.2% (128) | +3.2% +/- 8.0 | 0.31 then 0.66 | 11% |
| nhl_bounce_home_ml | 2-4, -1.3u | -44.0% (6) | +3.3% (114) | +0.9% +/- 8.8 | 0.64 then 0.54 | 5% |
| nfl_home_dog_7510 | 0-4, -2.0u | -100.0% (4) | +12.4% (36) | +1.1% +/- 14.6 | 0.79 then 0.53 | 10% |
| nba_under_good_home_over | 9-4, +2.3u | +34.7% (13) | -11.6% (65) | -3.8% +/- 11.0 | 0.17 then 0.36 | 17% |
| cbb_bigloss_vs_top5 | none | n/a (0) | n/a (0) | n/a | n/a | n/a |
| xch_homedog_fade | 61-21, +2.1u | +5.0% (82) | n/a (0) | n/a | n/a | n/a |
| cfb_q1_under_curve | none | n/a (0) | n/a (0) | n/a | n/a | n/a |
| cfb_tt_under_curve | none | n/a (0) | n/a (0) | n/a | n/a | n/a |
| cbb_1h_total_curve | none | n/a (0) | n/a (0) | n/a | n/a | n/a |
| nhl_p1_spread_curve | none | n/a (0) | n/a (0) | n/a | n/a | n/a |

Live record of the other tracker rules (paper, not in this audit): nba_momentum 18-40, -11.8u; cfb_road_dog_low_total 11-12, -0.7u; cfb_day_over 4-14, -5.1u; nhl_loss_streak_over 2-8, -3.1u; cfb_road_streak_dog 4-4, -0.3u; bounce15_1h 2-5, -1.7u; nhl_pl_dog_bigml 3-4, -0.6u; nhl_pl_fav_strong_opp 2-5, -0.3u; cbb_under_good_over_drop 3-3, -0.2u; nba_1h_under_hot_over 4-1, +1.3u; nba_roadtrip_over 2-2, -0.1u; nfl_fade_fav_bye 2-1, +0.4u; nfl_road_dog_7510 0-2, -1.0u; nhl_pl_fav_gap 0-1, -0.5u; nba_under_good_home_over_small 0-1, -0.5u.

## 3. Sizing tiers

Rules: [TIER_RULES.md](TIER_RULES.md), committed before this scoring. Tier A = real money, full size. Tier B = real money, half size. Tier C = paper. The retire flag is only a prompt for Sean, and a system winning live is never flagged.

| Tier | System | Old verdict | Blind WF ROI (N, record) | p_wf | Search p | Plain p | Live | Combined P(ROI > 0) | Retire flag | Why |
|---|---|---|---|---|---|---|---|---|---|---|
| B | wind1014 | PAPER ONLY | +28.3% (104, 69-35) | 0.000 | 0.314 | 0.056 | 8-4, +3.6u | 1.00 | no | misses Tier A on: search p < 0.20 or 50+ winning live bets |
| B | cfb_hot_over_low_total | PAPER ONLY | +17.8% (119, 73-46) | 0.020 | 0.323 | 0.038 | none | 0.98 | no | misses Tier A on: blind p_wf < 0.01, search p < 0.20 or 50+ winning live bets |
| B | nhl_early_home_fav_qual | PAPER ONLY | +9.3% (222, 146-76) | 0.015 | 0.087 | 0.012 | 12-10, -1.0u | 0.93 | no | misses Tier A on: blind p_wf < 0.01, combined P(ROI>0) >= 0.975 |
| C | nhl_skid_fade_road | PAPER ONLY | +8.0% (169, 91-78) | 0.230 | 0.262 | 0.050 | 6-1, +3.5u | 0.93 | no | misses Tier B on: p_wf or plain p < 0.05 |
| C | vrest8_1h | PAPER ONLY | +37.4% (24, 17-7) | 0.020 | 0.398 | 0.157 | 3-5, -1.0u | 0.91 | no | misses Tier B on: WF N >= 60 |
| C | mnf_1h | PAPER ONLY | +24.1% (25, 16-9) | 0.090 | 0.534 | 0.508 | none | 0.90 | no | misses Tier B on: combined P(ROI>0) >= 0.90, WF N >= 60, p_wf or plain p < 0.05 |
| C | wind1014_1h | PAPER ONLY | +8.4% (25, 14-11) | 0.180 | 0.842 | 0.381 | 7-2, +2.3u | 0.88 | no | misses Tier B on: combined P(ROI>0) >= 0.90, WF N >= 60, p_wf or plain p < 0.05 |
| C | cfb_homefav_7510_under | PAPER ONLY | +8.7% (180, 101-78) | 0.015 | 0.127 | 0.007 | 4-6, -1.1u | 0.85 | no | misses Tier B on: combined P(ROI>0) >= 0.90 |
| C | nba_badteams_under | PAPER ONLY | +3.7% (193, 102-89) | 0.150 | 0.669 | 0.121 | 3-1, +0.7u | 0.74 | no | misses Tier B on: combined P(ROI>0) >= 0.90, p_wf or plain p < 0.05 |
| C | awfuldog | PAPER ONLY | +12.7% (70, 39-27) | 0.100 | 0.459 | 0.245 | 0-4, -2.0u | 0.73 | no | misses Tier B on: combined P(ROI>0) >= 0.90, p_wf or plain p < 0.05 |
| C | nba_bigfav_over | PAPER ONLY | +2.7% (370, 193-170) | 0.200 | 0.176 | 0.018 | 5-4, +0.4u | 0.72 | no | misses Tier B on: combined P(ROI>0) >= 0.90 |
| C | nba_ats_hot_home | PAPER ONLY | +3.2% (74, 39-35) | 0.325 | 0.301 | 0.000 | 9-6, +1.0u | 0.68 | no | misses Tier B on: combined P(ROI>0) >= 0.90 |
| C | cfb_wind14 | RETIRE | -4.2% (128, 63-63) | 0.390 | 0.705 | 0.306 | 13-3, +9.9u | 0.66 | no | misses Tier B on: combined P(ROI>0) >= 0.90, WF ROI > 0, p_wf or plain p < 0.05 |
| C | nhl_bounce_home_ml | PAPER ONLY | +3.3% (114, 64-50) | 0.175 | 0.267 | 0.012 | 2-4, -1.3u | 0.54 | no | misses Tier B on: combined P(ROI>0) >= 0.90 |
| C | nfl_home_dog_7510 | PAPER ONLY | +12.4% (36, 21-14) | 0.230 | 0.234 | 0.053 | 0-4, -2.0u | 0.53 | no | misses Tier B on: combined P(ROI>0) >= 0.90, WF N >= 60, p_wf or plain p < 0.05 |
| C | nba_under_good_home_over | RETIRE | -11.6% (65, 29-35) | 0.610 | 0.435 | 0.040 | 9-4, +2.3u | 0.36 | no | misses Tier B on: combined P(ROI>0) >= 0.90, WF ROI > 0 |
| C | cbb_bigloss_vs_top5 | INSUFFICIENT DATA | n/a (0) | n/a | n/a | n/a | none | n/a | no | no replayable history: Tier C at most until a replay exists |
| C | xch_homedog_fade | INSUFFICIENT DATA | n/a (0) | n/a | n/a | n/a | 61-21, +2.1u | n/a | no | no replayable history: Tier C at most until a replay exists |
| C | cfb_q1_under_curve | INSUFFICIENT DATA | n/a (0) | n/a | n/a | n/a | none | n/a | no | no replayable history: Tier C at most until a replay exists |
| C | cfb_tt_under_curve | INSUFFICIENT DATA | n/a (0) | n/a | n/a | n/a | none | n/a | no | no replayable history: Tier C at most until a replay exists |
| C | cbb_1h_total_curve | INSUFFICIENT DATA | n/a (0) | n/a | n/a | n/a | none | n/a | no | no replayable history: Tier C at most until a replay exists |
| C | nhl_p1_spread_curve | INSUFFICIENT DATA | n/a (0) | n/a | n/a | n/a | none | n/a | no | no replayable history: Tier C at most until a replay exists |

Totals: Tier A 0, Tier B 3, Tier C 19; retire flags 0.

