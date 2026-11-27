# Bet Labs vs our replay: three screens moved to real money on 11/25

Sean, 11/26 (td_betlabs_mismatch). Diagnosis only: no tier, rule or board change. nba_under_good_home_over_small and wind1014_cold stay tier A (Sean's decision).

Method: Bet Labs' own past picks for each screen (pulled read-only from Sean's Chrome on 11/26 and hash-checked against the page; data/research/betlabs/*.txt), joined game by game to the Odds API database (data/oddsapi/odds.sqlite, Pinnacle close) by date and final score, or by date and team names for NHL. Seasons compared: NHL and CBB 2020-21 to 2025-26, CFB 2020 to 2025, which is the span of our replay. Code: sharp/research/betlabs_mismatch.py. Game-level files: data/research/betlabs/{rule}_matched.json. Summary: data/research/betlabs_mismatch_2026-11-26.json.

## First, a correction on our side

The "ours" records in PUSHBACK.md section 5 were doubled. When I summed data/research/rule_replay.json, I added each season row and the all-seasons row together. The real replay records are:

- nhl_pl_fav_strong_opp: 136-222 (358 bets, not 716)
- cbb_under_good_over_drop: 495-498-11 (1,004, not 1,986)
- cfb_road_streak_dog: 214-210-10 (434, not 848)

The ROI figures (-0.1%, -5.0%, -2.0%) were right. So our replay is not 1.8x / 3.5x / 10x Bet Labs' game count. It is 0.9x for NHL, 1.8x for CBB and 5x for CFB. Section 5 is corrected. The same doubling affected the other replay records on that line (nhl_pl_fav_gap, nhl_pl_dog_bigml, the nba_1h cousin, cfb_road_dog_low_total), but not bounce15_1h. No tier was set on those numbers.

## Results

| | NHL 1784155 | CBB 1792184 | CFB 1792198 |
|---|---|---|---|
| Bet Labs' list, our window | 393: 162-231, +30.9u, +7.9% | 571: 309-262, +19.2u, +3.4% | 84: 45-39, +1.7u, +2.1% |
| Our replay, same window | 342: 131-211, +0.4% | 993: 495-498, -5.0% | 386: 196-190, -1.5% |
| Bet Labs games found in the odds database | 392 | 526 (50 not in it) | 73 (11 not in it) |
| In both | 308 | 221 | 61 |
| Only in Bet Labs (game in our database, rule did not fire) | 84 | 305 | 12 |
| Only in ours | 34 | 783 | 333 |
| Same win/loss on matched games | 100% | 99% (5 differ, different totals) | 98.6% (1 differs) |
| Price on matched wins, Bet Labs vs Pinnacle close | 2.625 vs 2.562 decimal (about 2 cents better at Bet Labs) | 1.910 vs 1.907 (no gap) | 1.906 vs 1.938 (ours better) |
| **Bet Labs' games graded at our Pinnacle close** | **377 graded: 156-221, +22.6u, +6.0% (p 0.19)** | **502: 274-228, +20.2u, +4.0% (p 0.17)** | **69: 38-31, +4.6u, +6.7% (p 0.28)** |
| The same games at Bet Labs' prices | 392: +8.1% | 521: +4.1% | 73: +4.2% |
| The games only in ours | 34: +1.4% | 775 graded: -6.6% | 325 graded: -2.1% |

The read is right. On all three screens our replay tested a different, looser set of games. On Bet Labs' own games, our results and our Pinnacle closing prices agree with Bet Labs:

- **NHL:** price explains about 2 of Bet Labs' 8 points, and +6.0% remains.
- **CBB:** price explains nothing; we get +4.0% against Bet Labs' +4.1%.
- **CFB:** our prices do better.

The old -0.1%, -5.0% and -2.0% belong to the looser cousin, not the screen.

None of these windows is significant on its own: p runs from 0.11 to 0.35 on six seasons. The 11/25 tiers rest on Bet Labs' full history back to 2005, which this check doesn't change.

## Why the game sets differ

### NHL: nhl_pl_fav_strong_opp, opponent win % 66+, favorite on the puck line

**Only in ours: 34 games, +1.4%.**
- 23 are playoff games. The screen is regular season only, and our replay didn't filter season type. Those 23 went +13.6%.
- The other 11 are near pick'em closes, where Pinnacle's favorite differs from Bet Labs' (-24%).

**Only in Bet Labs: 84 games, +13.9% at our prices on 69 graded.**
- **41: our opponent win % was under 66.**
  - 34 of these are 2020-21. In that shortened season our win % disagreed with Bet Labs' on 47 of 50 matched games. In every other season it matched exactly (336 of 392 matched games agree to the point).
  - 7 are Utah games (2024 on), where our replay had no record for the new team.
- **22:** no Pinnacle closing snapshot within 6 hours of the start.
- **8:** Pinnacle's closing favorite was the other team.
- **13:** not classified.

**What the screen measures:** opponent win % is wins over games played, matching Bet Labs exactly outside 2020-21. Favorite and dog are judged at the close. The prior question about points % vs win % and the value entering the game vs at season end is settled: Bet Labs uses wins / games played entering the game, the same as ours.

**Bet Labs' bet type:** usually the favorite at -1.5. In 18 games Bet Labs lists the favorite at +1.5, and two rows have a 0 line. We graded those at Bet Labs' line.

**Live tool:** it uses the same win % definition. It does not check season type, so it would fire in the playoffs, as the replay did. That is a flag for Sean, not changed here.

### CBB: cbb_under_good_over_drop, weekday, home over 50%+, visitor over 59%+, total down 0.5+, home O/U streak 0-3

**Only in ours: 775 graded, -6.6%.**
- **436 had the home team outside a 0-3 O/U streak (-5.5%).** Our 11/5 replay never applied the screen's Home OU Streak filter. On matched games, Bet Labs' streak is the home team's current over streak entering the game, and it agrees with ours on 354 of 526.
- **339 inside the streak band still lost (-8.1%).** They fail Bet Labs' own numbers:
  - Our season over % matched Bet Labs' exactly on only 102 of 526 home teams and 95 visitors.
  - The open-to-close total change matched exactly on only 91 of 526.
  - Bet Labs uses its own opener and closer and its own closing totals to grade past overs. Our opener is the first market quote seen and our close is Pinnacle's, so a 0.5-point drop flips in and out.

**Only in Bet Labs: 305 games.** By our numbers:
- the visitor was under 59% over (66 games, plus overlaps);
- the total didn't drop 0.5 (50);
- the 3-game minimum blocked it (47). Bet Labs has no minimum, and its early-season rows show 100%;
- the home team was under 50% (34).

**Live tool:** I rebuilt the live tool's version (6-game minimum, streak 0-3) on the same data. It picks 474 games at -6.0%. Only 172 of them are Bet Labs' games (+2.0%); the other 302 lose 10.6%. So the tool firing on its own numbers mostly bets the cousin, not the screen. Price is not the issue here; the definitions of over % and line drop are.

### CFB: cfb_road_streak_dog, conference road dog on a road streak, total 54 or less, heavy-bet day

**Only in ours: 325 graded, -2.1%.**
- **162 were non-conference games (-4.4%).** Our replay never applied the screen's conference filter.
- **171 conference games were not on Bet Labs' list (+0.1% on 169).** That is the bet-volume filter ("Number of Bets Compared To Daily Avg 1.01+"), which only Bet Labs can see. It keeps about 73 of the roughly 230 conference games that pass everything else, and the edge sits in those 73.

**Streak definition:** the same in both. Bet Labs' -2 is "this is the second road game in a row": 64 of 73 matched games have exactly one prior road game in our schedule. Our replay's "prior road games + 1 in 2-5" is the same count.

**Only in Bet Labs: 12 games.** In our schedule, 7 have no road game the week before. Four have no Pinnacle close or line, and in one the road team closed as the favorite at Pinnacle.

**Live tool:** it already takes the bet-volume filter from Bet Labs' list (11/14), so it bets the screen, not the cousin.

## Recommendation (Sean's call; nothing changed)

- **nhl_pl_fav_strong_opp: keep at real money.** On Bet Labs' own games our Pinnacle closing prices return +6.0% on 377. The replay's -0.1% came from a broken 2020-21 record, missing Utah games, playoff games and missing closes, not the screen. Worth adding a regular-season check to the live rule.
- **cbb_under_good_over_drop: back to paper as built.** Bet Labs' own games hold up at our prices (+4.0% on 502), but the tool computes the filters itself and its version is mostly different games at -6.0%. It should only be real money if fills are limited to games on Bet Labs' list, the way cfb_road_streak_dog works.
- **cfb_road_streak_dog: keep at real money.** The replay gap is the conference and bet-volume filters our replay skipped. On Bet Labs' games our prices return +6.7%, and the live tool already requires Bet Labs' list. The sample is small: 84 games in six seasons.

## 11/27 follow-up (td_replay_fixes)

Fixed:
- **2020-21 NHL win %.** ESPN left the season type blank on the August 2020 bubble games. Because the replay's season starts in August, those games landed in 2020-21 records (Carolina had 8 extra). The bubble is now excluded (`sharp/rule_replay.py` `regular_season`). Our opponent win % now matches Bet Labs on all 392 matched games, up from 345.
- **Utah.** ESPN calls the franchise UTAH in 2024-25 and UTA from 2025-26, the reverse of `data/state/espn_teams.json`. All 191 Utah games had no result. `sharp/odds_db.py` now matches either abbreviation and stores ESPN's own, and the 191 games have results after a results rebuild.
- **Playoffs.** The replay now keeps only regular-season games, as the saved screens do.
- **The double count.** `rule_replay.summary_record()` and `season_rows()` now read the file. `tests/test_replay_fixes.py` checks that the season rows add up to the all-seasons row and that summing every row doubles it.

Rerun on the current database (2020-21 through 11/24/26): nhl_pl_fav_strong_opp is 146-243, -0.6% (was 136-222, -0.1%). Every rule's before and after is in the 11/27 report.

**Correction to the NHL read above.** 18 of Bet Labs' 392 NHL rows list the favorite at +1.5, and two at 0. Section 2 graded those at Bet Labs' line. The live tool always bets the favorite at -1.5. On those same 389 games, graded as the tool bets them (Bet Labs' team at -1.5, Pinnacle close), the result is 159-230 at -1.5, +1.1% (p 0.44). On the 370 games where Bet Labs itself bet -1.5, it is +4.8% (p 0.25). With the Utah results added, Bet Labs' lines at our prices are +4.7% on 389, down from +6.0% on 377. So for the bet the tool actually places, the price and line gap explains most of Bet Labs' edge. The 11/26 "keep at real money" call for nhl_pl_fav_strong_opp rested on +6.0% and is weaker than it looked. That is Sean's call; nothing has changed.
