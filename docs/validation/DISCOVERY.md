# Discovery search (board_r10 follow-up)

Built 2026-11-18 18:44 UTC by sharp/discover_report.py from sharp/discover_angles.py (seed 20261119). Plan: [DISCOVERY_PLAN.md](DISCOVERY_PLAN.md), registered before the search ran. Read-only: nothing was added to the board.

## Bottom line

The search tried 2,874 candidate angles across NFL, CFB, NBA and NHL. 1,877 of them had 100+ bets in the training seasons. **None survives the search-adjusted test** (the best search p is 0.243). The reason is the size of the search: when the outcomes are shuffled, the best angle in each sport still shows a median ROI of +17% to +19% (table below). Any real angle would have to beat that to stand out.

The stronger evidence is the walk-forward of the search itself. Each season, the procedure takes the top 5 angles found on earlier seasons (plain p < 0.05) and bets them blind the next season. That is how a newly found angle would actually be used. It does not make money in any sport beyond what chance allows:

| Sport | Candidates (eligible) | Best ROI on shuffled data, median / 95th pct | Walk-forward of the search: ROI on N | p | Seasons |
|---|---|---|---|---|---|
| NFL | 838 (286) | +19.0% / +25.9% | -1.7% on 900 | 0.510 | 2022, 2023, 2024, 2025 |
| CFB | 604 (457) | +16.9% / +23.6% | +2.9% on 1076 | 0.070 | 2022, 2023, 2024, 2025 |
| NBA | 796 (647) | +18.3% / +25.3% | +0.4% on 927 | 0.245 | 2022-23, 2023-24, 2024-25, 2025-26 |
| NHL | 636 (487) | +18.2% / +26.0% | -5.9% on 877 | 0.490 | 2022-23, 2023-24, 2024-25, 2025-26 |

In plain terms: mining the price and results history for new single or two-condition angles turns up angles that look strong in-sample (+15% to +20% on 100+ bets). They do about as well as a random pick in the following season. These markets (Pinnacle closes in the major US sports) are hard to beat on records, rest, form, ATS, line size, line move and weather alone. The results that held up in the audit (the wind under, the NHL early-season favourite) came from specific ideas that were tested, not from a broad search.

## Candidates worth a look anyway

The 10 lowest search-adjusted p-values overall, plus the top 3 per sport by plain p. None passes; they are listed so Sean can decide whether any is worth a paper tag to build a forward record. Holdout = the last complete season, never used to choose. WF picked = seasons in which the walk-forward of the search chose this angle.

| Angle | Training N | Training ROI | Plain p | Search p | Holdout ROI (N) | WF picked |
|---|---|---|---|---|---|---|
| CFB over, when the home team is on a 3+ game losing streak and line in the middle third | 120 | +19.4% | 0.005 | 0.243 | +0.0% (25) | 2025 +0.0%/25 |
| CFB road team spread, when lost its last game big and line moved against it | 122 | +19.1% | 0.008 | 0.267 | -3.2% (34) | 2025 -3.2%/34 |
| CFB road team spread, when lost its last game big and line in the lower third | 137 | +18.2% | 0.004 | 0.344 | -34.9% (21) | 2024 +18.6%/36; 2025 -34.9%/21 |
| CFB road team spread, when win% 40 or less and line moved against it | 189 | +17.4% | 0.006 | 0.445 | -0.2% (36) | 2023 +23.7%/48; 2024 +17.3%/40; 2025 -0.2%/36 |
| NFL home team spread, when ATS 60%+ and opponent win% 40 or less | 111 | +19.4% | 0.007 | 0.458 | +14.2% (19) | 2025 +14.2%/19 |
| CFB over, when the home team is on a 3+ game losing streak and line did not move | 122 | +16.9% | 0.007 | 0.503 | -0.5% (32) | 2025 -0.5%/32 |
| NBA over, when the home team 2+ more days of rest than the opponent and line in the middle third | 105 | +18.2% | 0.008 | 0.507 | +37.2% (17) | 2025-26 +37.2%/17 |
| NBA home team spread, when 2+ more days of rest than the opponent and is the underdog | 104 | +17.9% | 0.009 | 0.542 | +40.8% (18) | 2025-26 +40.8%/18 |
| NBA home team spread, when ATS 60%+ and line did not move | 123 | +17.3% | 0.008 | 0.611 | +34.4% (13) | 2025-26 +34.4%/13 |
| NHL road team moneyline, when win% 40 or less and opponent on a back-to-back | 155 | +16.8% | 0.008 | 0.663 | -2.9% (24) | 2023-24 -19.8%/21; 2024-25 +24.4%/28; 2025-26 -2.9%/24 |
| NFL home team spread, when ATS 60%+ and line moved toward it | 119 | +16.1% | 0.003 | 0.819 | -4.1% (31) | 2025 -4.1%/31 |
| NFL over, when the home team's ATS is 60%+ and the home team is the favourite | 220 | +10.6% | 0.004 | 0.998 | +7.1% (39) | never |
| CFB road team spread, when win% 40 or less and line in the upper third | 291 | +13.4% | 0.000 | 0.900 | +7.6% (46) | 2022 +17.8%/61; 2023 +24.0%/61; 2024 -4.2%/54 |
| CFB under, when the home team's win% is 60+ and line in the upper third | 398 | +10.3% | 0.000 | 0.997 | +18.0% (56) | 2022 -2.7%/105 |
| CFB road team spread, when line moved against it and is the underdog | 639 | +9.7% | 0.000 | 0.999 | -7.7% (159) | never |
| NBA home team spread, when ATS 60%+ and is the favourite | 517 | +10.3% | 0.000 | 1.000 | -10.8% (95) | never |
| NBA home team spread, when ATS 60%+ | 706 | +5.3% | 0.000 | 1.000 | -4.1% (129) | never |
| NBA home team spread, when ATS 60%+ and line in the middle third | 200 | +16.9% | 0.002 | 0.677 | -15.7% (36) | 2023-24 +23.9%/33; 2024-25 -2.4%/50; 2025-26 -15.7%/36 |
| NHL under, when the home team's win% is 60+ and line in the middle third | 408 | +8.7% | 0.003 | 1.000 | -19.5% (71) | never |
| NHL road team moneyline, when opponent on a back-to-back and is the favourite | 298 | +11.1% | 0.005 | 0.995 | -18.0% (68) | 2022-23 +7.6%/52; 2024-25 -3.3%/49 |
| NHL over, when the visitor win% 40 or less and line did not move | 888 | +4.9% | 0.005 | 1.000 | -5.1% (117) | never |

Of the 130 eligible angles with plain p < 0.05 in training, 50 were also positive in the holdout on 20+ bets. Chance alone would put about half of them there.

## The tracker's paper logs: when are they big enough?

The paper logs are too young to mine: 381 graded fills across 30 rules since late October. To tell a real edge from zero with 80% confidence (one-sided 5% test) at about -110 takes about **559 bets for a +10% edge** and **2,233 for +5%**. The table projects each rule's current pace (graded fills per week since its first fill) forward. Most rules need a season or more, and football rules only fill on game days, so their pace stops when the season ends.

| Rule | Graded fills | Units | Fills per week | Weeks to 558 (+10% edge) |
|---|---|---|---|---|
| xch_homedog_fade | 82 | +2.1 | 31.9 | 15 |
| nba_momentum | 58 | -11.8 | 23.9 | 21 |
| cfb_road_dog_low_total | 23 | -0.7 | 8.9 | 60 |
| nhl_early_home_fav_qual | 22 | -1.0 | 8.6 | 63 |
| cfb_day_over | 18 | -5.1 | 10.5 | 52 |
| cfb_wind14 | 16 | +9.9 | 6.2 | 88 |
| nba_ats_hot_home | 15 | +1.0 | 8.8 | 63 |
| nba_under_good_home_over | 13 | +2.3 | 5.4 | 102 |
| wind1014 | 12 | +3.6 | 4.7 | 118 |
| cfb_homefav_7510_under | 10 | -1.1 | 5.8 | 95 |
| nhl_loss_streak_over | 10 | -3.1 | 6.4 | 87 |
| wind1014_1h | 9 | +2.3 | 3.5 | 158 |
| nba_bigfav_over | 9 | +0.4 | 5.2 | 105 |
| vrest8_1h | 8 | -1.0 | 3.5 | 158 |
| cfb_road_streak_dog | 8 | -0.3 | 4.3 | 128 |
| bounce15_1h | 7 | -1.7 | 2.6 | 215 |
| nhl_pl_dog_bigml | 7 | -0.6 | 2.7 | 203 |
| nhl_pl_fav_strong_opp | 7 | -0.3 | 2.7 | 203 |
| nhl_skid_fade_road | 7 | +3.5 | 4.1 | 136 |
| nhl_bounce_home_ml | 6 | -1.3 | 3.5 | 158 |
| cbb_under_good_over_drop | 6 | -0.2 | 6.0 | 93 |
| nba_1h_under_hot_over | 5 | +1.3 | 1.9 | 285 |
| nfl_home_dog_7510 | 4 | -2.0 | 2.3 | 238 |
| awfuldog | 4 | -2.0 | 2.3 | 238 |
| nba_badteams_under | 4 | +0.7 | 2.8 | 199 |
| nba_roadtrip_over | 4 | -0.1 | 4.0 | 139 |
| nfl_fade_fav_bye | 3 | +0.4 | 1.8 | 318 |
| nfl_road_dog_7510 | 2 | -1.0 | 1.2 | 478 |
| nhl_pl_fav_gap | 1 | -0.5 | 0.4 | 1276 |
| nba_under_good_home_over_small | 1 | -0.5 | 1.0 | 558 |

## What is not searched, and why

- CBB: no ESPN schedule history in the repo, so no records, rest or form. It could be added by backfilling the CBB schedule; line-only angles in CBB were not searched.
- Bet Labs history: the repo holds pick lists for 5 screens only, not a game-level Bet Labs database, so there is nothing to mine beyond the systems already audited.
- First-half, period and team-total markets: line history is too short (NFL 1H from 2023, CFB curves from 2023) for a training set plus a holdout.

