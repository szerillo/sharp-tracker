# Weekly checkpoint, 2026-11-23 (Monday)

Rules applied: docs/checkpoint_rules_2026-11-02.md (including the 11/2 amendment), unchanged during this read. Graded through Sunday 11/22
(games starting before 2026-11-23 05:00 UTC). Records are cumulative from the start of each log. There is no 11/16 checkpoint file in the
repo, so this read covers two weeks of new results; the lines crossed below were already crossed on data through 11/15 (noted where so).

Every script used here reproduces the 11/9 tables exactly when cut at 2026-11-09 05:00 UTC (systems, steam_rev record, snapshot signals,
Polymarket sharp accounts), except two method notes: the move tape gains a few late-settled rows (565 notable vs 544), and steam_rev CLV now
reads the Kalshi close from data/state/closes.jsonl.gz (see that section).

## Systems (paper, data/state/fills.jsonl)

Units = stake x (decimal - 1) on wins, -stake on losses. ROI = units / staked. ROI z = mean return per unit staked / its standard error.
CLV = 100 x (fair_at_close - implied), on fills with a recorded close (diagnostic only for systems). Voided fills (trigger lapsed) excluded.
Open = logged, not yet graded.

| Rule | Record | Units | ROI (z) | CLV (diagnostic) | Open | Rule outcome |
|---|---|---|---|---|---|---|
| xch_homedog_fade | 82-27 | +2.62 | +5.5% (z 0.99) | -0.41 on 109 | 0 | keep. Past 100 graded, so no longer barred from promotion; the rules set no promote line for systems, so any tier move is Sean's call |
| nba_momentum | 18-40 | -11.79 | -40.7% (z -3.27) | -1.49 on 58 | 0 | retired 11/9 |
| cfb_road_dog_low_total | 14-16 | -0.81 | -5.6% (z -0.48) | -3.57 on 27 | 4 | **retired**: 25+ graded, ROI negative and CLV 2.0+ worse than the close |
| cfb_day_over | 11-16 | -3.04 | -22.9% (z -1.10) | -2.29 on 27 | 11 | **retired**: 25+ graded, ROI negative and CLV 2.0+ worse than the close |
| nhl_early_home_fav_qual | 13-12 | -1.87 | -15.3% (z -0.82) | -1.25 on 25 | 3 | keep. **Near two lines**: ROI is below -15% (review needs CLV worse than -1.5 too) and retire needs CLV -2.0 or worse |
| cfb_wind14 | 14-9 | +8.62 | +48.6% (z 1.01) | -0.84 on 23 | 0 | keep |
| nba_ats_hot_home | 10-9 | +0.48 | +5.7% (z -0.03) | -1.06 on 19 | 1 | keep |
| nba_under_good_home_over | 9-5 | +1.76 | +25.1% (z 0.97) | +0.82 on 12 | 0 | keep |
| wind1014 | 9-4 | +3.83 | +31.3% (z 1.35) | +0.24 on 11 | 1 | keep |
| nhl_loss_streak_over | 4-9 | -2.87 | -45.9% (z -1.58) | -8.78 on 13 | 1 | keep. **Near the review line** (15 graded with ROI below -15% and CLV worse than -1.5) |
| nba_bigfav_over | 6-5 | +0.36 | +7.1% (z 0.20) | -0.49 on 11 | 1 | keep |
| wind1014_1h | 8-2 | +2.58 | +54.4% (z 2.16) | -1.07 on 10 | 0 | keep |
| cfb_homefav_7510_under | 4-6 | -1.10 | -22.0% (z -0.69) | -3.26 on 10 | 3 | keep. On course for review at 15 graded |
| nhl_skid_fade_road | 8-1 | +3.78 | +89.0% (z 2.74) | -1.33 on 9 | 2 | keep |
| nba_roadtrip_over | 5-4 | -0.14 | -4.0% (z 0.19) | -3.38 on 9 | 5 | keep |
| cfb_road_streak_dog | 5-4 | -0.01 | -0.3% (z 0.15) | -5.46 on 6 | 0 | keep |
| bounce15_1h | 2-6 | -2.17 | -54.1% (z -1.80) | -0.86 on 7 | 1 | keep |
| nhl_pl_fav_strong_opp | 3-5 | -0.07 | -1.7% (z 0.10) | -1.60 on 8 | 0 | keep |
| vrest8_1h | 3-5 | -1.03 | -25.8% (z -0.71) | -1.76 on 8 | 1 | keep |
| nhl_pl_dog_bigml | 3-4 | -0.65 | -18.5% (z -0.48) | -1.20 on 7 | 0 | keep |
| nba_1h_under_hot_over | 5-1 | +1.53 | +55.6% (z 1.84) | +0.35 on 6 | 0 | keep |
| nhl_bounce_home_ml | 2-4 | -1.32 | -44.0% (z -1.24) | -3.23 on 6 | 0 | keep |
| nba_badteams_under | 4-2 | +0.73 | +29.4% (z 0.62) | +0.97 on 6 | 0 | keep |
| cbb_under_good_over_drop | 3-3 | -0.20 | -6.8% (z -0.16) | -0.82 on 5 | 1 | keep |
| others (1-5 bets each: nfl_fade_fav_bye, nfl_home_dog_7510, awfuldog, nfl_road_dog_7510, nba_under_good_home_over_small, nhl_pl_fav_gap) | 4-16 | -6.37 | | | 6 | keep |
| **All** | 249-215 | -7.14 | -3.1% (z -1.33) | -1.60 on 450 | 41 | |

Retire line A (25+ graded, ROI negative, CLV -2.0 or worse): cfb_road_dog_low_total (30 graded, -5.6%, CLV -3.57) and cfb_day_over (27 graded,
-22.9%, CLV -2.29). Both are retired.
Retire line B (50+ graded, ROI z -2 or worse): only xch_homedog_fade has 50+ open to it and its z is +0.99.
Review line (15+ graded, ROI below -15%, CLV worse than -1.5): none. nhl_early_home_fav_qual has ROI -15.3% but CLV -1.25.

## steam_rev (paper, data/kalshi/steam_rev_paper.jsonl, graded on Kalshi settlement)

1u to risk at the logged ask. CLV = 100 x (Kalshi close mid on the bet side - entry price). Method note: data/<sport>/ticks now keep only
11/13 on, so the Kalshi close comes from data/state/closes.jsonl.gz (p_close, the last mid before the start, same side and line). Check: on the
401 bets since 11/14 the tick method gives -0.51 (z -2.19) and closes.jsonl gives -0.60 (z -2.63); on the 185 bets read on 11/9 closes.jsonl
gives +0.08 against the -0.15 printed then. Record matches flow_live.json steam.record (n 725, won 365, units -15.87; -15.89 here before
per-bet rounding).

| Slice | Record | Units | ROI (z) | CLV vs Kalshi close (z) | Rule outcome |
|---|---|---|---|---|---|
| **All** | 365-360 | -15.89 | -2.2% (z -0.55) | -0.42 on 722 (z -2.57) | **retired**: 50+ graded, CLV at or below zero with z -1 or worse (already met on data through 11/15: -0.47 on 470, z -2.31) |
| Moneyline | 123-122 | -8.61 | -3.5% | -0.52 on 242 (z -1.50) | |
| Spread | 106-114 | -9.35 | -4.3% | +0.12 on 220 (z 0.45) | |
| Total | 136-124 | +2.08 | +0.8% | -0.78 on 260 (z -3.48) | |
| Steam 5+ pts | 67-63 | -7.35 | -5.7% | +0.00 on 129 | |

50 logged bets are still open. Five graded bets have no Kalshi close in closes.jsonl.

**Grading fault found (not fixed, for Sean):** flow_live.steam_paper grades each bet with `(ticker result == yes) == bet_yes`, but bet_yes is
set on the home / over orientation of the tick row, not on the ticker's own YES. On spread tickers whose YES is the road team (for example
KXNBASPREAD-26NOV01BOSORL-BOS8) the result is flipped. 79 of 220 graded spread bets disagree with the side's outcome in closes.jsonl, plus 3
moneylines. Graded on closes.jsonl outcomes instead, the record is 371-354, -12.05u (-1.7%); spreads 111-109, -4.26u. The retire call rests on
CLV, which this does not touch.

## Tennis first-set favourites (tier C, data/tennis/fs_graded.json, matches tennis_watch.json record)

| Rule | Graded | Record | Units (1u) | ROI (z) | CLV | Rule outcome |
|---|---|---|---|---|---|---|
| tennis_fs_fav | 49 | 34-15 | +4.01 | +8.2% (z 0.77) | 3 scored, too few to read | keep (first read at 300; early retire only at 100+ with ROI z -2) |

One more match graded after Sunday (record now 50, 34-16, +3.01u).

## Watch signals (not bet)

### Snapshot signals (sharp/signal_grade.py; CLV = Pinnacle no-vig from first seen to the start)

W-L at the snapshot line against final scores; CLV only where recorded. ROI only where the snapshot logged a Kalshi ask.

| Signal | W-L-P | CLV (z) | Priced ROI at the ask | Rule outcome |
|---|---|---|---|---|
| Kalshi 4+ movers (kmove) | 824-672 | +0.54 on 283 (z 3.83) | moneylines 415 at -1.3% (z -0.24); -4.1% after the Kalshi taker fee. All markets 1,496 at -0.1%, -3.2% after fee | **promoted** to a sized paper record: 150+ CLV-graded, CLV z 2+, ROI not below -5% (already met on data through 11/15: +0.64 on 181, z 3.35) |
| Steam bet-back (back) | 408-399 | +0.31 on 164 (z 1.84) | moneylines 299 at -7.4% | keep |
| Big vs small money (big) | 327-353 | +0.05 on 335 (z 0.62) | none logged | keep |
| Sharp move snapshot (move) | 267-235-5 | -0.03 on 399 (z -0.33) | none logged | keep |
| All snapshot signals | 1826-1659-5 | +0.18 on 1,181 (z 3.14) | | |

### Move tape (data/state/moves.jsonl.gz, settled rows with clv_pts)

Notable = origin Pinnacle, or Kalshi big_n > 0 with big_net > 0.

| Slice | Settled | CLV (z) | Rule outcome |
|---|---|---|---|
| **Notable moves** | 1,396 (W-L 681-715) | -0.49 (z -7.53) | past 300 settled with the retire line met. Not bet, so under the 11/2 amendment Sean decides; flagged since 11/9, left on the page and logging |
| Notable, Pinnacle origin | 1,108 (545-563) | -0.35 (z -5.33) | |
| Notable, Kalshi big money | 288 (136-152) | -1.01 (z -5.58) | |
| All settled moves | 4,418 (2264-2154) | -0.74 (z -14.11) | |
| Exchange-led, Pinnacle followed | 480 (242-238) | +0.30 (z 2.03) | not a defined signal; see worth watching |
| Exchange-led, Pinnacle did not follow | 2,830 (1477-1353) | -1.07 (z -14.65) | |

## Polymarket sharp accounts (409 graded flags)

data/state/sharp_paper.jsonl. 1u = 1 unit to risk at the Polymarket ask; sized = the units the board tracked (none on flags logged from 11/10
except soccer grade A / B with nothing against, live from 11/21). CLV vs Polymarket's close as logged. 29 flags open.

| Slice | Record | Units 1u (sized) | ROI 1u (z) | CLV vs Polymarket close (z) |
|---|---|---|---|---|
| **All** | 196-213 | -26.01 (-16.62) | -6.4% (z -1.16) | -0.37 on 294 (z -1.24) |
| Grade A | 123-146 | -25.90 (-15.43) | -9.6% | -0.17 on 200 |
| Grade B | 55-41 | +11.18 (+0.89) | +11.6% | -1.04 on 71 (z -1.26) |
| Watch | 18-26 | -11.29 (-2.09) | -25.7% | -0.03 on 23 |
| Moneyline | 84-87 | -9.37 | -5.5% | -0.14 on 102 |
| Spread | 63-63 | -5.15 | -4.1% | -0.26 on 107 |
| Total | 49-63 | -11.49 | -10.3% | -0.77 on 85 |
| NBA | 73-76 | -11.46 | -7.7% | -0.48 on 90 |
| CFB | 43-42 | +3.05 | +3.6% | -0.60 on 67 |
| NFL | 26-31 | -6.84 | -12.0% | +0.67 on 42 (z 2.29) |
| Soccer | 32-23 | +10.96 | +19.9% | -0.05 on 45 (z -0.14) |
| NHL | 9-27 | -18.61 | -51.7% | -0.05 on 35 |
| CBB | 13-14 | -3.11 | -11.5% | -3.31 on 15 |
| Logged since 11/10 (no units) | 112-105 | +10.44 | +4.8% | -0.48 on 157 |
| Games 11/16 to 11/22 | 63-44 | +23.10 | +21.6% (z 1.92) | +0.18 on 79 |

**Vs Pinnacle's no-vig close** (closes.jsonl.gz Pinnacle rows, the two sides at the flag's line devigged multiplicatively from the last
Pinnacle quote of each before the start; the 11/13-on ticks alone no longer cover the early flags). 227 of 409 scored; not scored: 134 no
Pinnacle quote at the flag's line, 32 soccer three-way moneylines or no side, 16 no event id.

| Slice | Scored | CLV vs Pinnacle close (z) |
|---|---|---|
| Pinnacle quote at that line within 60 minutes of the start (the close) | 174 | -0.51 (z -2.15) |
| of which moneyline / spread / total | 126 / 24 / 24 | -0.39 / -0.71 / -0.93 |
| of which grade A / B / watch | 101 / 43 / 30 | -0.24 / -0.63 / -1.22 |
| Same 113 flags with a Polymarket CLV too: Pinnacle vs Polymarket | 113 | -0.28 vs -0.16 |
| Any last quote at that line (includes lines Pinnacle had moved off) | 227 | -1.09 (z -5.15) |

Rule outcome: **flagged for Sean, no change.** Polymarket-close CLV is -0.37 with z -1.24, which meets the top-down retire line (50+ graded,
CLV at or below zero, z -1 or worse); Pinnacle's close agrees (-0.51, z -2.15 on 174). But since 11/10 the flags carry no units (Sean, until
they beat Pinnacle's close), so outside soccer they are a watch signal that is not bet, and the 11/2 amendment applies: past 300 settled, the
call is Sean's. The only bet slice, soccer (live from 11/21), is -0.05 on 45 (z -0.14) on Polymarket's close and not near the line.

**System bets with sharps on the same side vs against** (data/state/sys_sharp_tags.jsonl joined to fills.jsonl by fill_id; 172 of 177 tags
found in fills, 27 open or void):

| Sharps on the system bet | Record | Units | ROI | CLV |
|---|---|---|---|---|
| With only | 28-30 | -4.38 | -14.5% | -1.62 on 55 |
| Against only | 31-21 | +2.42 | +9.8% | -2.72 on 50 |
| Both sides | 13-22 | -6.67 | -38.7% | -1.07 on 35 |

Sharps on the same side still have not helped system bets (145 graded); the held-against rule (no bet against the sharps) has cost results so
far, but CLV is worse on those bets, so the record looks like noise.

## Changes

1. **cfb_road_dog_low_total retired** (systems retire line A: 30 graded, ROI -5.6%, CLV -3.57 on 27). Removed from RULES in sharp/systems.py
   with a comment citing this checkpoint; its firing block now checks RULES, so no new fills. In sharp/bet_log.py it joins DEMOTED_FROM at
   2026-11-23 17:45 UTC, so its tier C fills on games that already started keep their record and its 4 open fills show as paper.
2. **cfb_day_over retired** (same line: 27 graded, ROI -22.9%, CLV -2.29 on 27; it was already back to paper since 11/21). Removed from RULES
   the same way; its firing block checks RULES. Its 11 open fills stay paper and keep grading.
3. **steam_rev retired** (top-down retire line for a paper-bet signal: CLV -0.42 on 722, z -2.57). sharp/flow_live.py sets
   STEAM_REV_RETIRED = '2026-11-23': no new paper logs, logged bets keep grading, flow_live.json steam carries retired. The bet-back watch
   signal on the page stays (a separate snapshot signal, CLV +0.31, z 1.84).
4. **Kalshi 4+ movers promoted** from watch to a sized paper record (CLV +0.54 on 283, z 3.83; ROI -1.3% on priced moneylines). sharp/signal_grade.py
   now writes kmove_paper to data/research/signal_grade.json: every frozen kmove snapshot for games from 2026-11-23 18:00 UTC, 1u to risk at
   the snapshot's Kalshi ask plus the taker fee, graded at its line against the final score. Paper only, no units on the board.
5. Page text (index.html) for the Kalshi move and bet-back signals updated to say the above.
6. Not changed, for Sean: notable moves (flagged since 11/9), Polymarket sharp flags (retire line met, not bet outside soccer), and the steam_rev
   spread grading fault.

## Worth watching

- nhl_early_home_fav_qual: 13-12, ROI -15.3%, CLV -1.25 on 25. Review if CLV slips past -1.5; retire if it reaches -2.0 with ROI still negative.
- nhl_loss_streak_over (4-9, CLV -8.78 on 13) and cfb_homefav_7510_under (4-6, CLV -3.26 on 10) are on course for the review line at 15.
- xch_homedog_fade passed 100 graded: +5.5% ROI (z 0.99) with CLV -0.41 (z -3.39). Wins against a worse close, which the systems rules allow.
- Exchange moves Pinnacle then followed: +0.30 on 480 (z 2.03), against -1.07 on 2,830 not followed. Still not a defined signal.
- Polymarket sharp flags: a +21.6% week (63-44) on Polymarket prices, but CLV stays negative on both yardsticks. NFL is the one sport with
  positive CLV (+0.67 on 42, z 2.29) while losing (-12.0%).
- kmove paper: first graded fills from tonight; the ROI after fees (-4.1% on moneylines) sits close to the -5% floor.
