# Every live system re-tested on the corrected database, 11/5/2026 (afternoon)

Database state: Odds API 2020-26 with real market opens (first two-book number; 06:00/12:00 UTC snapshots added), Pinnacle closes and
prices, ESPN regular-season records (preseason excluded, OT flagged), conference and neutral-site flags, Open-Meteo kickoff weather for
NFL. Graded on results at Pinnacle's closing price, flat stakes. Bet Labs' own pick lists (graded at Pinnacle) are the second test
for rules that came from Bet Labs. Tier changes are applied in sharp/systems.py.

| rule | corrected replay 2020-26 | seasons + | Bet Labs' own picks at Pinnacle | tier |
|---|---|---|---|---|
| wind1014 (NFL under, 10-14 mph) | 161-103-3, +18.1%; mild weather 134-76 (+23.7%); cold (<40F) 27-27 | 6/7 | n/a | **A** (cold games paper) |
| wind1014_1h | not in the data (1H) | | | A, unchanged |
| vrest8_1h (visitor off bye, 1H under) | full-game cousin 132-93-2, +13.7% | 4/7 | | C |
| mnf_1h | full-game cousin 72-56-2, +8.8% (SNF 60-46-2 +10.2%, TNF 59-57) | 6/7 | | B |
| awfuldog | -7 to -13 band 91-76-5 (+5.0%); -13 or worse 14-16 | 4/5 | | C (re-banded), deep band paper |
| bounce15_1h | full-game cousin 125-104-5, +5.5% | 5/7 | | B |
| nfl_home_dog_7510 (new) | 47-25-1 (+23%); all dogs 7.5-10 136-97-3 (+10.3%) | 6/7 | | C |
| nfl_fade_fav_bye (new) | favourite off a bye 124-145-7 ATS (-9.0%) | 6/7 for the dog | | P |
| cfb_wind14 | not replayed (no CFB stadium weather yet) | | | A, unchanged |
| cfb_road_dog_low_total | conference games 132-113-10, +4.4%; non-conference -7.2% | 5/6 | 153-117 | **B** |
| cfb_road_streak_dog | 214-210-10, -2.0% | 3/7 | 49-41 (uses a bet-volume filter we lack) | P |
| cfb_hot_over_low_total | not replayed (weather) | | | C, unchanged |
| nhl_early_home_fav_qual | 258-139 ML, +9.4% (+9.3% best US) | 6/6 | | **B**, best rule in the book |
| nhl_pl_fav_gap | 79-126 at -1.5, +1.5% | 3/7 | 109-138 since 2020 | C |
| nhl_pl_fav_strong_opp | 136-222 at -1.5, -0.1%; the 360 games Bet Labs also picks +3.6% | 3/7 | 405, +7.4% | C |
| nhl_pl_dog_bigml | 40-24 at +1.5, +11.6% (thin) | 4/7 | | C |
| nba_under_good_home_over | 215-210-7, -1.3% (filter now within half a point of Bet Labs' on 341/396 of its picks) | 3/7 | 392, +7.8%, 6/7 | **C** (the two tests disagree) |
| nba_1h_under_hot_over | 1H not in the data; full-game cousin 132-129 | | | B (Sean), flagged |
| cbb_under_good_over_drop | 495-498-11, -5.0% | 1/6 | 309-262, +3.5%, 3 of last 4 negative | **P** |
| cbb_bigloss_vs_top5 | not replayable (AP rank) | | | C, unchanged |
| tennis hot favourite, settled | 142-31 vs close, about +9%, all 5 years | 5/5 | n/a | **B** |
| tennis hot dog / serve angles | +4.7% / slams only | | | P |
| mma_steam_fav (new) | 136-53 at the close, +6.6% | 4/5 | | C |
| xch_homedog_fade, nba_momentum | exchange tape only, not in this data | | | P |

Line-move note: with real opens, following or fading spread and total moves at the close is 50/50 or negative in every sport. The
morning's NFL "follow a small total move" (+17%) was a late-open artifact and is not a rule. The side the market moves toward wins at its
opening price (CFB large moves +19%, MLB +8%, MMA +20%): that is the sharp tracker's job, not a closing-line system.

## New paper angles from the miner (tier P, on the board from the next run)
- `nba_ats_hot_home`: home team covering 60%+ this season (8+ games), exactly 2 days rest: home spread. 311-228, 7 of 7 seasons.
- `nba_bigfav_over`: moneyline favourite 85%+: over. 272-202, 6 of 6.
- `nhl_loss_streak_over`: home team lost 3+ straight, season over rate 40-60%: over. 385-290, 5 of 6.
MLB road-team unders (342-246) wait for the season.

## Evening: NFL favourite-off-a-bye reconciled
Our 120-143 "favourite off a bye" counted week 1 as a bye (every team is 12+ days off after the previous season) and the games after the
playoff break. True byes only (12-20 days since the last game): favourite 70-84 ATS, the dog +5.4% on 154 games 2020-26. Bet Labs' screen
is wider (opponent off 8-30 days, which also catches the long week after a Thursday game): 203-188 (-0.4%) since 2020 and 356-389 (-6.5%)
in 2003-19. No edge either way; `nfl_fade_fav_bye` stays paper with the reason on the board. Also stale above: the NHL puck-line rules do
not need a regulation-win% change; the Bet Labs match came from using regular-season records, not from excluding overtime losses.
Same correction applied to the visitor-rest cousin: with week 1 excluded, visitor off 8-30 days (Bet Labs' definition) full-game under is
213-162 (+10.3%), 5 of 7 seasons; the 12-20 day byes 72-54 and the 8-11 day long weeks 139-107 carry it equally. `vrest8_1h` stays tier C
on its own first-half record (Bet Labs 4 of 7 seasons positive); the full-game cousin is now a candidate for a future paper rule.
