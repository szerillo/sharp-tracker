# NBA under reconciliation and full-game systems split into derivatives (11/6)

Scripts: `sharp/nba_under_reconcile.py`, `sharp/deriv_split.py` (writes `data/research/deriv_split.json`).

## nba_under_good_home_over: why Bet Labs and our replay disagree

Bet Labs export (system 1789285, 445 picks, 2019-20 on) joined game by game to the odds database (405 matched; the 40 unmatched are 2019-20, before our data):
- Bet Labs as exported, at its own prices: 236-202, +3.6%. The +9.6% headline is the 2003-26 total; since 2019 it is +3.6%.
- Bet Labs' own picks graded at Pinnacle's close: 213-174, +7.4%. Scores match on every game. Lines are within half a point on 294 of 405.
- Our replay: 432 picks, 215-210, -1.4%. Of those, 290 are also Bet Labs picks (156-127, +7.6%), and 142 are ours only (59-83, -19.2%).
- Bet Labs picks our filter misses: 115 (57-47, +7.0%). Reasons: our opening total shows no 0.5+ drop (59), our home over% under 58 (45), no close inside 6 hours (16).
- Rest days match exactly (Bet Labs rest = our days off). Over% matches on 227 of 405, with ours usually 1-5 points lower.

So the data is not off: the same games grade the same. The two filters disagree on the borderline games (home over% 58-61, and whether the total dropped half a point from the open, which depends on whose opener). The 142 borderline games we add went 59-83.

Robustness grid on our data (ROI at Pinnacle's close; every game with the same rest and a 0.5 drop is -3.2% on 2,646):

| home over% | drop 0.5+ | 1.0+ | 1.5+ | 2.0+ |
|---|---|---|---|---|
| 54+ | -2.2% (788) | -0.2% | +2.0% | -0.2% |
| 56+ | -2.6% (608) | -1.1% | +1.9% | -0.5% |
| 58+ | -1.4% (432) | +2.0% | +6.8% (315) | +5.2% |
| 60+ | -1.9% (345) | +1.6% | +5.0% | +3.5% |
| 62+ | -4.8% (240) | -1.3% | +1.1% | -0.3% |
| 65+ | -3.7% (151) | +0.1% | -1.4% | -4.3% |

Reading: Bet Labs' exact game list is profitable, but moving a threshold a notch either way takes it to about break-even. The best neighbourhood is a bigger drop (1.5+), +5-7%. That pattern (one exact definition works, its neighbours don't) is what an over-fitted screen looks like. Recommendation: paper, or keep tier C only on games with a drop of 1.5 points or more.

## Full-game systems split into derivatives

Pinnacle derivative prices about 10 minutes before the start (mid-2023 to 2025-26, three seasons), graded on ESPN period scores. "Every game" = the same bet on every game in the window.

| rule | full game (same games) | best split | other splits |
|---|---|---|---|
| nba_under_good_home_over | 126-122, -1.1% | home team total under +3.1% (2/3 seasons) | 1H under -1.9%, 1Q under +2.9% (1/3), away TT under -13.9% |
| nba_1h_under_hot_over (visitor over 71%+) | 81-82, -3.3% | away TT under +8.9% (2/3) | **1H under 77-85, -7.8%, 0 of 3 seasons** |
| cfb_road_dog_low_total (TCU) | 70-62, +2.9% | 1Q road spread +6.9% (2/3) | 1H road spread -1.1%, 1H under -11.6% (0/3), 1H over +2.6% |
| cfb_homefav_7510_under | 81-61, +9.8% (3/3) | home TT under +6.1% (2/3) | 1H under -1.7%, 1Q under -1.2%, away TT under +3.2% |
| cfb_road_streak_dog | 104-113, -7.2% | 1H over +4.5% (2/3) | 1H road spread -7.7%, 1H under -13.7% |

No split clears the bar (every season positive, 100+ bets). The derivatives follow the full game: where the full-game rule works, its splits are weaker; where it does not, the splits do not rescue it. Splitting is not a source of extra edge.

The flag: `nba_1h_under_hot_over` (tier C, sized 0.5u by Sean) is the 1H under itself, and on real Pinnacle 1H lines it is 77-85, -7.8%, negative every season. Bet Labs' visitor over% may be defined differently, so this needs the same game-by-game reconciliation before the next fire.

## nba_1h_under_hot_over: Bet Labs picks pulled and reconciled (evening)

Bet Labs ScreenId 1784158 picks, 2023-24 on (199), saved to `data/research/betlabs/nba_1h_under_1784158.txt`; `sharp/nba_1h_reconcile.py`.
- Our data agrees with Bet Labs: 198 of 199 games matched, 1H scores identical on all of them, visitor over% identical on 152 of 178, Pinnacle's 1H line within half a point on 153.
- Bet Labs' own record on these picks, at its own lines: 103-96, -1.2%. At Pinnacle's 1H line: 85-90, -5.9%. By season at Pinnacle: 2023-24 -22.4%, 2024-25 +8.7%, 2025-26 -1.6%.
- Our replay of the filter: 83-86, -4.8% (165 of its 169 games are Bet Labs picks).
- Split: picks where the visitor is 100% over (its first game or two) went 24-36 (-22.9%); 71-99% went 61-54 (+3.0%).
- Every NBA 1H under at Pinnacle is -3.2% over the same window.

The rule's headline record comes from before 2023. Over the last three seasons it has no edge at Bet Labs' own prices. Recommendation: paper.

## Threshold robustness, every replayable Bet Labs rule (11/6)

Script: `sharp/threshold_grid.py` (writes `data/research/threshold_grid.json`). Same method as the nba_under_good_home_over grid above.

How to read it:
- Each rule is replayed at its exact definition, then with each threshold moved one or two notches either way.
- Every cell is graded on results at Pinnacle's close, flat 1 unit at Pinnacle's price. Cells show ROI (bets). The exact definition is in bold.
- Baseline = every game with the same market and side and the rule's other filters.
- Seasons count full seasons only. The season in progress (2026-27 NHL, 2026 CFB and NFL) is shown but not counted.
- Verdict rule: NO EDGE if the exact definition is under +2% or within 1.5% of the baseline. ROBUST if the median of the one-notch neighbours is positive, at least half the exact ROI, and 2% or more above the baseline. Otherwise FRAGILE.
- Skipped: the weather rules, and cbb_bigloss_vs_top5 (needs historical AP ranks, which are not in the data).
- NHL puck lines: 7,365 of 7,394 games closed at Pinnacle -1.5 / +1.5, so nearly every bet is graded at Pinnacle's real price.

### nhl_pl_fav_gap (fav -1.5, opponent win% higher by 22+)

Exact: 79-126, +1.5% on 205. 3 of 6 seasons positive. Baseline (every NHL fav -1.5): -4.9% on 7,394.
By season: 2020-21 -79.0% (14), 2021-22 -3.4% (50), 2022-23 +12.6% (39), 2023-24 -16.8% (26), 2024-25 +34.2% (34), 2025-26 +1.5% (36), 2026-27 +52.0% (6).

| win% gap | 16+ | 19+ | 22+ | 25+ | 28+ |
|---|---|---|---|---|---|
| ROI (n) | -2.6% (329) | +5.0% (258) | **+1.5% (205)** | +4.3% (171) | +1.9% (137) |

The whole grid beats the -4.9% baseline, so a big gap does help the favourite. But no cell gets clear of break-even by much, and half the seasons lose. Verdict: NO EDGE.

### nhl_pl_fav_strong_opp (fav -1.5 vs opponent winning 66%+)

Exact: 136-222, -0.1% on 358. 3 of 6 seasons. Baseline -4.9% on 7,394.
By season: 2020-21 +15.6% (18), 2021-22 +6.5% (77), 2022-23 -0.1% (65), 2023-24 -35.5% (63), 2024-25 +25.5% (71), 2025-26 -4.2% (48), 2026-27 -10.4% (16).

| opponent win% | 60+ | 63+ | 66+ | 69+ | 72+ |
|---|---|---|---|---|---|
| ROI (n) | -0.1% (936) | +1.3% (578) | **-0.1% (358)** | -7.7% (190) | -5.5% (139) |

Break-even at best, and worse as the opponent gets stronger. Verdict: NO EDGE.

### nhl_pl_dog_bigml (dog +1.5 when it opened +181 to +196)

Exact: 40-24, +11.6% on 64. 3 of 6 seasons. Baseline (every NHL dog +1.5): +3.0% on 7,394.
By season: 2020-21 -12.0% (2), 2021-22 +8.6% (5), 2022-23 +19.1% (38), 2023-24 -12.5% (2), 2024-25 +43.7% (6), 2025-26 -14.3% (8), 2026-27 -41.0% (3).

| opening ML from \ to | +186 | +196 | +206 | +216 |
|---|---|---|---|---|
| +161 | +10.2% (126) | +10.8% (161) | +7.6% (198) | +7.6% (214) |
| +171 | +10.1% (77) | +11.0% (112) | +6.7% (149) | +6.7% (165) |
| +181 | +9.9% (29) | **+11.6% (64)** | +5.1% (101) | +5.3% (117) |
| +191 | n/a | +17.4% (20) | +2.1% (57) | +3.1% (73) |

The neighbours hold up, and widening the band down to +161 keeps about +10% on 2.5 times the bets. The upper edge matters: past +196 the ROI falls toward the baseline. Caveat: 38 of the 64 exact bets are from 2022-23, so the season split is thin. Verdict: ROBUST (small sample).

### nhl_early_home_fav_qual (home ML fav, game 24 or earlier, opponent 51%+)

Exact: 258-139, +9.4% on 397. 6 of 6 seasons. Baseline (every NHL home fav ML): -1.3% on 4,568.
By season: 2020-21 +26.3% (22), 2021-22 +13.8% (87), 2022-23 +5.9% (82), 2023-24 +10.2% (56), 2024-25 +6.6% (59), 2025-26 +14.6% (72), 2026-27 -28.0% (19).

| home game number \ opponent win% | 45+ | 48+ | 51+ | 54+ | 57+ |
|---|---|---|---|---|---|
| 16 or earlier | +2.5% (417) | +4.7% (372) | +8.9% (251) | +9.1% (234) | +10.1% (208) |
| 20 or earlier | +3.2% (534) | +4.7% (471) | +9.1% (329) | +9.0% (302) | +10.0% (257) |
| 24 or earlier | +2.9% (635) | +4.6% (556) | **+9.4% (397)** | +8.5% (357) | +10.9% (297) |
| 28 or earlier | +0.5% (762) | +1.6% (661) | +5.3% (476) | +5.6% (412) | +6.5% (338) |
| 32 or earlier | +0.7% (882) | +1.8% (749) | +4.3% (547) | +3.8% (468) | +5.3% (379) |

The shape is smooth: a stronger opponent and an earlier game both help. The 51% line is where it starts working, and anything above it holds. Every cell is above the baseline. The current season is 8-11 so far. Verdict: ROBUST.

### nhl_bounce_home_ml (home team off a 3+ goal loss, win% 50 to under 65: home ML)

Live filter from `sharp/systems.py`: both teams 3+ games played (the description says 8+; the result barely changes). Last-game margin from the ESPN regular-season schedule.
Exact: 332-197, +9.2% on 529. 5 of 6 seasons. Baseline (every NHL home ML, both teams 3+ games): -2.5% on 7,219.
By season: 2020-21 +6.3% (43), 2021-22 +18.1% (96), 2022-23 -15.7% (83), 2023-24 +9.0% (113), 2024-25 +14.4% (103), 2025-26 +15.4% (82), 2026-27 +44.0% (9).

| home win% \ lost last game by | 2+ | 3+ | 4+ |
|---|---|---|---|
| 45 to 60 | +0.5% (878) | +4.3% (564) | +8.9% (264) |
| 45 to 65 | +0.4% (1,086) | +5.9% (705) | +8.8% (323) |
| 45 to 70 | +0.5% (1,179) | +5.9% (770) | +8.0% (347) |
| 50 to 60 | +3.5% (605) | +8.0% (388) | +10.6% (185) |
| 50 to 65 | +2.6% (813) | **+9.2% (529)** | +10.1% (244) |
| 50 to 70 | +2.5% (906) | +8.9% (594) | +8.9% (268) |
| 55 to 60 | +5.4% (273) | +16.2% (171) | +16.7% (91) |
| 55 to 65 | +3.1% (481) | +14.5% (312) | +13.5% (150) |
| 55 to 70 | +2.8% (574) | +13.1% (377) | +11.3% (174) |

Minimum games: 3+ +9.2% (529), 8+ +9.6% (501), 15+ +10.2% (463).
A 2-goal loss is not enough (about +0.5% to +5%). From 3 goals on, the edge holds across every band, and a higher floor on the record helps. Verdict: ROBUST.

### cfb_road_dog_low_total (conference game, road dog 7+, total 48 or less: road spread)

Exact: 132-113-10, +4.4% on 255. 5 of 6 seasons (2025 -1.0%). Baseline (every conference road dog): -2.4% on 1,764.
By season: 2020 +6.6% (20), 2021 +22.0% (27), 2022 +4.7% (37), 2023 +12.5% (51), 2024 +8.0% (46), 2025 -1.0% (52), 2026 -33.3% (22).

| road dog of at least \ total at most | 44 | 46 | 48 | 50 | 52 |
|---|---|---|---|---|---|
| 6 | -10.9% (112) | +3.2% (203) | +4.2% (291) | +6.1% (394) | +3.4% (503) |
| 6.5 | -8.6% (105) | +6.7% (191) | +8.2% (273) | +8.9% (373) | +5.5% (480) |
| 7 | -14.1% (98) | +2.0% (177) | **+4.4% (255)** | +7.0% (345) | +3.9% (446) |
| 7.5 | -10.8% (90) | +4.8% (163) | +6.9% (237) | +9.2% (322) | +6.0% (417) |
| 8 | -6.9% (78) | +8.3% (147) | +8.8% (217) | +10.5% (297) | +6.7% (387) |

The exact definition sits at the low end of its neighbourhood. Totals of 46 to 52 all work. Only the very lowest totals (44 or less) lose. The 2026 season so far is 7-14-1. Verdict: ROBUST.

### cfb_homefav_7510_under (home fav 7.5 to 10: under)

Exact: 188-130-4, +13.7% on 322. 5 of 6 seasons (2023 -15.2%). Baseline (every CFB home fav under): -3.3% on 3,190.
By season: 2020 +33.9% (26), 2021 +8.8% (38), 2022 +18.8% (60), 2023 -15.2% (50), 2024 +8.0% (56), 2025 +19.7% (58), 2026 +35.9% (34).

| fav of at least \ at most | 9.5 | 10 | 10.5 | 11 |
|---|---|---|---|---|
| 6.5 | +7.8% (465) | +11.0% (547) | +7.4% (610) | +6.2% (649) |
| 7 | +5.4% (350) | +9.9% (432) | +5.6% (495) | +4.3% (534) |
| 7.5 | +8.3% (240) | **+13.7% (322)** | +7.5% (385) | +5.7% (424) |
| 8 | +7.0% (143) | +15.2% (225) | +6.6% (288) | +4.4% (327) |

Every cell is +4% or better, against a -3.3% baseline. The 10 cap is the best column. Games at exactly -10 do a lot of the work, so the exact ROI overstates the band a little. Verdict: ROBUST.

### nfl_home_dog_7510 (home dog +7.5 to +10 at the close: home spread)

Exact: 47-25-1, +23.0% on 73. 5 of 6 seasons (2021 -12.1%). Baseline (every NFL home dog): -1.2% on 672.
By season: 2020 +39.9% (15), 2021 -12.1% (11), 2022 +15.8% (13), 2023 +13.7% (9), 2024 +61.6% (7), 2025 +29.6% (16), 2026 -8.5% (2).

| dog of at least \ at most | 9.5 | 10 | 10.5 | 11 |
|---|---|---|---|---|
| 6.5 | +14.5% (121) | +14.4% (135) | +13.5% (141) | +14.5% (148) |
| 7 | +13.1% (90) | +13.1% (104) | +12.1% (110) | +13.5% (117) |
| 7.5 | +25.3% (59) | **+23.0% (73)** | +20.8% (79) | +22.0% (86) |
| 8 | +25.1% (23) | +20.6% (37) | +16.9% (43) | +19.5% (50) |

Every neighbour is +12% or better. Adding the +7 games cuts the ROI to about +13%, so the +7.5 floor matters, but the edge does not depend on it. The sample is small (about 12 bets a season). Verdict: ROBUST.

### awfuldog (NFL dog with season point margin -13 or worse: spread)

Margins rebuilt per team per season from the odds database, as in `sharp/nfl_replay.py`. The bounce15_1h skip is not applied.
Exact (1+ games): 63-44-2, +12.4% on 109. 4 of 6 seasons (2020 -0.5%, 2021 -4.0%). Baseline (every NFL dog, 1+ games): -0.2% on 1,609.
By season: 2020 -0.5% (19), 2021 -4.0% (28), 2022 +92.0% (4), 2023 +7.7% (16), 2024 +15.2% (17), 2025 +34.1% (17), 2026 +18.8% (8).

| season margin \ minimum games | 1+ | 2+ | 3+ |
|---|---|---|---|
| -9 or worse | +7.1% (287) | +5.0% (259) | +0.8% (224) |
| -11 or worse | +9.7% (167) | +6.8% (144) | +2.4% (118) |
| -13 or worse | **+12.4% (109)** | +10.2% (88) | +5.2% (70) |
| -15 or worse | +20.2% (60) | +16.4% (44) | +7.4% (33) |
| -17 or worse | +26.4% (30) | +32.4% (20) | +14.8% (11) |

The edge grows smoothly as the margin gets worse. That is the shape of a real effect, not a tuned cutoff. It fades as the minimum games rises, so much of it comes from early-season games where a team has one or two bad results. This replay gives 63-44-2 (+12.4%); the EVIDENCE line in systems.py says 61-50 (+5.5%) from an earlier run, so the exact record depends on how margins and closes are matched. Verdict: ROBUST.

### Summary

| rule | current tier | exact ROI (bets), seasons + | one-notch neighbour range (15+ bets, diagonals included) | all neighbours | baseline | verdict | suggested tier |
|---|---|---|---|---|---|---|---|
| nhl_pl_fav_gap | C | +1.5% (205), 3 of 6 | +4.3% to +5.0% | -2.6% to +5.0% | -4.9% | NO EDGE | paper |
| nhl_pl_fav_strong_opp | C | -0.1% (358), 3 of 6 | -7.7% to +1.3% | -7.7% to +1.3% | -4.9% | NO EDGE | paper |
| nhl_pl_dog_bigml | C | +11.6% (64), 3 of 6 | +2.1% to +17.4% | +2.1% to +17.4% | +3.0% | ROBUST (thin) | C |
| nhl_early_home_fav_qual | B | +9.4% (397), 6 of 6 | +1.6% to +9.1% | +0.5% to +10.9% | -1.3% | ROBUST | B |
| nhl_bounce_home_ml | C | +9.2% (529), 5 of 6 | +0.4% to +16.7% | -0.1% to +16.7% | -2.5% | ROBUST | C |
| cfb_road_dog_low_total | B | +4.4% (255), 5 of 6 | +2.0% to +9.2% | -14.1% to +10.5% | -2.4% | ROBUST | C |
| cfb_homefav_7510_under | C | +13.7% (322), 5 of 6 | +5.4% to +15.2% | +4.3% to +15.2% | -3.3% | ROBUST | C |
| nfl_home_dog_7510 | B | +23.0% (73), 5 of 6 | +12.1% to +25.3% | +12.1% to +25.3% | -1.2% | ROBUST | C |
| awfuldog | B | +12.4% (109), 4 of 6 | +6.8% to +20.2% | +0.8% to +32.4% | -0.2% | ROBUST | C |

Suggested tier rule: B if positive every full season and robust; C if a season is negative or the edge is fragile; paper if no edge.

Reading:
- No rule here is fragile the way nba_under_good_home_over was. Where an edge exists, the neighbours keep most of it.
- The two NHL favourite puck-line rules have no edge at any threshold. They beat the baseline only because every -1.5 favourite loses about 5%.
- nhl_early_home_fav_qual is the only rule that is robust and positive every season. It stays B.
- cfb_road_dog_low_total, nfl_home_dog_7510 and awfuldog are robust but each has a losing full season (two for awfuldog), so the strict rule puts them at C. These are suggestions only; no tier was changed.
