# Full tier recheck (11/6, evening)

Sean: "a thorough recheck of all systems ... wondering if any paper need to move up". Two tests behind this: `sharp/threshold_grid.py`
(every replayable Bet Labs rule: exact definition, one-notch neighbours, baseline; section in `docs/deriv_split_2026-11-06.md`) and
`sharp/paper_grid.py` (every mined paper angle with its live filter, by season, neighbours, baseline; `data/research/paper_grid.json`).
ROI is percent at Pinnacle's close, flat 1 unit. "Seasons" counts seasons with 10+ bets. Forward = the tracker record since the rule went live.

Tier rule (Sean, 11/5): B if positive every season, C if one season is negative, A when it persists over a long sample, paper when it only
partly fits. Added 11/6: an edge that exists only at its exact thresholds is at most C.

## Live rules

| rule | tier before | exact (seasons +) | neighbours | baseline | forward | verdict | tier now |
|---|---|---|---|---|---|---|---|
| wind1014 | A | Bet Labs picks at Pinnacle 160-101, +18.6%; 5 of 6 | n/a (weather) | | 3-1 | hold | A |
| cfb_wind14 | A | 135-96, +12.3%; 5 of 6 | n/a | | 2-0 | hold | A |
| cfb_q1_under_curve | A | 296-189, +15.0%; 3 of 3 (Sean's call) | gap 0.05 to 0.10 all positive | curve | none yet | hold | A |
| nhl_early_home_fav_qual | B | 258-139, +9.4%; 6 of 6 | +1.6% to +9.1% | -1.3% | 1-4 (8-11 this season at Bet Labs) | robust, every season | B |
| cfb_hot_over_low_total | B | 117-71-3, +19.5%; 6 of 6 | conference version 37-38 | | none | hold | B |
| mnf_1h | B | Bet Labs 168-118, +12.3% | not replayable (1H) | | none | hold | B |
| nhl_p3_under_curve | B | 243-185, +13.3%; every season | | curve | none yet | hold | B |
| cfb_road_dog_low_total | B | 132-113-10, +4.4%; 5 of 6 | +2.0% to +9.2% (totals 44 or less lose) | -2.4% | 4-3; 7-14-1 this season | robust but one losing season and a thin exact edge | **C** |
| nfl_home_dog_7510 | B | 47-25-1, +23%; 5 of 6 | +12.1% to +25.3% | -1.2% | 0-1 | robust, one losing season (2021) | **C** |
| awfuldog | B | 63-44-2, +12.4% (ESPN margins); 4 of 6 | +6.8% to +20.2%, grows with a worse margin | -0.2% | none | robust, two losing seasons | **C** |
| cfb_homefav_7510_under | C | 188-130, +13.6%; 5 of 6 | +5.4% to +15.2% | -3.3% | none | robust since 2020; 2003-19 +1.1% | C |
| nba_under_good_home_over | C | drop 1.5+: 171-141, +6.8% | neighbours of the 0.5 version break-even | -3.2% | 5-2 | fragile at 0.5, steadier at 1.5+ | C (1.5+ only) |
| nhl_bounce_home_ml | C | 311-252 to 529 bets, +2.4% to +9.2% depending on profile source; 5 of 6 | +0.4% to +16.7% | -2.5% | 0-2 | robust; the 3-goal line is real | C |
| nhl_pl_dog_bigml | C | 46-32 at +1.5, +11.6%; 3 of 6 (38 of 64 bets in 2022-23) | +2.1% to +17.4% | +3.0% | 1-4 | small, thin seasons | C |
| nhl_pl_fav_gap | C | 79-126 at -1.5, +1.5%; 3 of 6 | -2.6% to +5.0% | -4.9% | 0-1 | beats baseline only because every -1.5 favourite loses 5% | **paper** |
| nhl_pl_fav_strong_opp | C | 136-222 at -1.5, -0.1%; 3 of 6 | -7.7% to +1.3% | -4.9% | 1-3 | no edge at any threshold | **paper** |
| cbb_bigloss_vs_top5 | C | Bet Labs 177 +23.1% / 66 +13.0% | not replayable (AP ranks) | | none | hold | C |
| vrest8_1h | C | full-game cousin 127-93-2 but 48-49-2 since 2024 | | | 1-0 | hold | C |
| wind1014_1h | C | our 1H replay 55-51, +0.4% | | | 2-1 | hold | C |
| cbb_1h_total_curve, cfb_tt_under_curve, nhl_p1_spread_curve, nba_threes_under_gap, nhl_prop_under_gap | C | set today | | | none | hold | C |

## Paper rules: which earn a tier

| rule | exact live filter (seasons +) | neighbours | baseline | before 2020 (Bet Labs) | mechanism | verdict |
|---|---|---|---|---|---|---|
| nba_badteams_under | 143-96, +16.8%; 5 of 6 (2024-25 -7%) | every neighbour +6% to +17%; visitor -9 to -2 is 6 of 6 (+16.7%); home under 45% 6 of 6 (+15.8%) | -4.0% | approx 771-772 (-2.3%) | two bad teams, the home one poor at home: low-effort, slow games that the total does not fully price | **C candidate** (robust since 2020, no pre-2020 support) |
| nba_ats_hot_home | 245-173, +14.3%; 6 of 6 | ATS 65%+ +20.7%; 5+ or 12+ games +14%; ATS 60%+ at any rest 402-321 (+8.4%, 6 of 6); ATS 55%+ falls to +2.5%; rest 1 is -11% | -2.4% | 611-629 (-3.8%) | a team covering 60%+ is being under-priced by the market, and the 2-day rest removes back-to-backs | **C candidate** (the 60% line and 2-day rest both matter, but the no-rest version still holds 6 of 6) |
| nba_bigfav_over | 351-285, +6.9%; 5 of 6 (2025-26 -3%) | 82.5%+ 509-424 (+5.7%, 6 of 6); 80%+ 6 of 7; road favourites 85%+ 91-66 (+12.1%) | -1.6% | 1011-1038 (-3.7%) | blowouts: the trailing team speeds up, the favourite's bench scores in garbage time | **C candidate** (robust since 2020, modest edge) |
| nhl_skid_fade_road | 286-267, +7.0%; 5 of 5 full seasons (2026-27 -4% so far) | home lost 2+ +4.3% (4 of 7); lost 4+ +3.1%; without the visitor-off-a-win filter +0.8% | -1.9% | 576-623 (-7.1%); 2020 on 284-264 (+5.6%) | the puck line on a visitor against a team on a skid: the skid side is priced for a bounce-back that mostly does not come | **C candidate, weakest** (the visitor-off-a-win filter carries most of it) |
| cfb_day_over | 295-202, +14.1%; 7 of 7 | total 45-48.5 168-100 (+20.5%, 7 of 7); 48-51.5 +10.9% (6 of 7); noon-7pm +10.0% (6 of 7); any total at 2-7pm -0.1%; any time at 45-51.5 +4.3% | -3.2% | about 585-620; 2020 on 301-233 (+7.7%, 5 of 7) | not shown. The total band carries most of it; the time slot adds. Sean 11/5: a time slot is not a reason | **paper** until a mechanism is shown (the strongest numbers on the list, so worth the hunt: heat, conference mix, TV windows) |
| nhl_loss_streak_over | 388-315, +7.2%; 4 of 6 (2020-21 -7%, 2023-24 -6%) | lost 4+ +6.7% (5 of 6); over rate 45-55% +9.9% (5 of 6); any over rate +5.7% (5 of 6) | -2.1% | 794-826 (-2.3%); 2020 on +4.3% | a home team on a skid opens up / chases | paper (two losing seasons) |
| nba_roadtrip_over | 85-52, +20.9%; 6 of 6 | 4th+ road game without the last-meeting filter 225-212 (-0.1%); won last meeting alone -2.5% | -1.6% | 1164-1132 (-1.0%) | none for the interaction | paper (the two filters only work together: a fit) |
| nfl_road_dog_7510 | 89-76, +2.1%; 5 of 7 | +7 to +10.5 -0.8%; +6.5 to +9.5 -1.2% | +0.1% | | | paper (no edge) |
| cfb_road_streak_dog | 137-139, -3.7% | all negative | -2.4% | | | paper |
| nfl_fade_fav_bye, awfuldog_deep, wind1014_cold, cbb_under_good_over_drop, mlb_road_over_under (2026 -21%), bounce15_1h, nba_1h_under_hot_over, nba_under_good_home_over_small | | | | | | paper, unchanged |
| xch_homedog_fade | exchange audit +12% at the close (n 300) | | | | the home side on Novig at 20-35c inside 90 minutes is public money | paper; forward 16-6, +0.17u; revisit at 50 bets |
| nba_momentum | continuation +4 to +6 pts on the audit | | | | | paper; forward 10-24, -3.65u; candidate to retire |
| stale_book | 30-41 on our tape, +15.8% (long prices) | | | | books slow to follow Pinnacle | paper; new |

## Applied now
- nhl_pl_fav_gap and nhl_pl_fav_strong_opp: C to paper (no edge at any threshold).
- cfb_road_dog_low_total, nfl_home_dog_7510, awfuldog: B to C (robust, but each has a losing season, and the tier rule for B is every season positive).

## Proposed, waiting on Sean
- Paper to C at 0.25u: nba_badteams_under, nba_ats_hot_home, nba_bigfav_over, nhl_skid_fade_road. All are positive in 5 or 6 of 6 seasons since 2020 and hold at neighbouring thresholds; none has support before 2020 at Bet Labs, so none goes to B.
- cfb_day_over: the best numbers of any paper rule (7 of 7, +14%), held back only by the missing mechanism.
- Nothing earns tier A beyond the two wind rules and CFB Q1 unders. nhl_early_home_fav_qual is the next in line (robust, 6 of 6) but its all-time Bet Labs record is only +3.0%.

## Applied (Sean, 6:17 PM)
- nba_badteams_under, nba_ats_hot_home, nba_bigfav_over, nhl_skid_fade_road: paper to tier C, 0.25u. Their Bet Labs screens renamed from Tracked: to Tested: (1799442, 1799432, 1799443 and the visitor copy 1799444, 1799431).
- cfb_day_over stays paper. Its pre-2020 Bet Labs sample is about 585-620 (2005-19, the 2-7pm cut), and all-time 886-853 is flat: the edge exists only since 2020.
- Everything else on paper stays paper.
