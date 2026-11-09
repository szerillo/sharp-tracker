# Weekly checkpoint, 2026-11-09 (Monday)

Rules applied: docs/checkpoint_rules_2026-11-02.md (including the 11/2 amendment), unchanged during this read. Graded through Sunday 11/8
(games starting before 2026-11-09 05:00 UTC). Records are cumulative from the start of each log.

## Systems (paper, data/state/fills.jsonl)

Units = stake x (decimal - 1) on wins, -stake on losses. ROI = units / staked. ROI z = mean return per unit staked / its standard error.
CLV = 100 x (fair_at_close - implied), on fills with a recorded close (diagnostic only for systems). Voided fills (trigger lapsed) excluded.

| Rule | Record | Units | ROI (z) | CLV (diagnostic) | Open | Rule outcome |
|---|---|---|---|---|---|---|
| nba_momentum | 18-40 | -11.79 | -40.7% (z -3.27) | -1.49 on 58 | 0 | **retired**: 50+ graded and ROI z -2 or worse (z -3.27 on 58) |
| xch_homedog_fade | 31-9 | +1.73 | +8.6% (z 0.91) | -0.45 on 40 | 0 | keep |
| cfb_road_dog_low_total | 7-6 | +0.38 | +5.8% (z 0.21) | -1.23 on 12 | 12 | keep |
| wind1014 | 7-2 | +4.72 | +52.4% (z 1.82) | +0.86 on 8 | 0 | keep |
| nba_under_good_home_over | 7-2 | +2.30 | +51.2% (z 1.79) | +0.86 on 7 | 1 | keep |
| nhl_early_home_fav_qual | 3-4 | -0.88 | -25.2% (z -0.71) | -0.19 on 7 | 3 | keep |
| cfb_day_over | 2-5 | -1.57 | -44.8% (z -1.26) | -1.94 on 7 | 12 | keep |
| nba_ats_hot_home | 5-2 | +1.27 | +36.3% (z 1.03) | -1.36 on 7 | 2 | keep |
| nhl_pl_dog_bigml | 2-4 | -1.15 | -38.2% (z -0.98) | -0.62 on 6 | 0 | keep |
| wind1014_1h | 5-1 | +1.91 | +63.5% (z 1.94) | -0.49 on 6 | 0 | keep |
| bounce15_1h | 1-4 | -1.57 | -62.6% (z -1.67) | -0.10 on 4 | 0 | keep |
| nba_1h_under_hot_over | 4-1 | +1.30 | +52.1% (z 1.37) | +0.89 on 5 | 0 | keep |
| nhl_pl_fav_strong_opp | 1-4 | -0.78 | -31.0% (z -0.45) | -0.42 on 5 | 0 | keep |
| cfb_road_streak_dog | 2-3 | -0.56 | -22.4% (z -0.47) | -3.37 on 2 | 4 | keep |
| cfb_wind14 | 3-1 | +1.97 | +49.3% (z 0.99) | -2.54 on 4 | 0 | keep |
| vrest8_1h | 2-2 | -0.04 | -2.0% | -0.55 on 4 | 3 | keep |
| cfb_homefav_7510_under | 1-3 | -1.05 | -52.3% (z -1.10) | -1.84 on 4 | 8 | keep |
| awfuldog | 0-4 | -2.00 | -100% | -1.29 on 3 | 0 | keep |
| others (1-2 bets each: nba_bigfav_over, nfl_road_dog_7510, nhl_bounce_home_ml, nhl_pl_fav_gap, nfl_home_dog_7510, nfl_fade_fav_bye, nhl_skid_fade_road, nba_badteams_under) | 4-7 | -1.03 | | | 5 | keep |
| nhl_loss_streak_over | 0-0 | | | | 5 | keep (first fills open) |
| **All** | 105-104 | -6.81 | -6.1% (z -1.49) | -0.85 on 199 | 55 | |

Review line (15+ graded, ROI below -15%, CLV worse than -1.5): only nba_momentum had 15+ graded and negative ROI; it is retired instead.
Retire line A (25+ graded, ROI negative, CLV -2.0 or worse): no rule with 25+ graded has CLV that bad (nba_momentum -1.49).
Nothing is near 100 graded, so nothing is promoted.

## steam_rev (paper, data/kalshi/steam_rev_paper.jsonl, graded on Kalshi settlement)

1u to risk at the logged ask. CLV = 100 x (Kalshi close mid on the bet side - entry price), close = the last two-sided Kalshi quote for the
ticker before the start in data/<sport>/ticks and ticks5 (median 3.5 minutes before the start, median spread 1c). Matches the
flow_live.json record (n 185, won 91, units -1.49).

| Slice | Record | Units | ROI (z) | CLV vs Kalshi close (z) | Rule outcome |
|---|---|---|---|---|---|
| **All** | 91-94 | -1.49 | -0.8% (z -0.10) | -0.15 on 185 (z -0.34) | keep: 50+ graded, CLV at or below zero but z above -1; no promotion (z not 2+) |
| Moneyline | 24-29 | -3.76 | -7.1% | +0.48 on 53 | |
| Spread | 31-33 | +0.47 | +0.7% | +0.04 on 64 | |
| Total | 36-32 | +1.80 | +2.7% | -0.82 on 68 (z -1.81) | |
| Steam 5+ pts | 12-14 | -3.37 | -13.0% | | |

53 logged bets are still open (start on or after 11/9, or not yet settled).

## Tennis first-set favourites (tier C, data/state/tennis_watch.json record)

| Rule | Graded | Record | Units (1u) | CLV | Rule outcome |
|---|---|---|---|---|---|
| tennis_fs_fav | 34 | 21-13 | 0.00 | -0.47 on 3 | keep (first read at 300; early retire only at 100+ with ROI z -2) |

## Watch signals (not bet)

### Snapshot signals (python3 sharp/signal_grade.py; CLV = Pinnacle no-vig from first seen to the start)

W-L at the snapshot line against final scores; CLV only where recorded. ROI is only available on moneylines with a logged ask.

| Signal | W-L-P | CLV (z) | Rule outcome |
|---|---|---|---|
| Kalshi 4+ movers (kmove) | 288-218 | +0.59 on 88 (z 2.68) | keep. Promote test needs 150+ graded on CLV (88 so far) and ROI not below -5%; priced moneylines 122 at -1.0% (z -0.12). **Near the promote line** |
| Steam bet-back (back) | 118-123 | +0.64 on 52 (z 1.87) | keep (priced moneylines 93 at -11.2%) |
| Big vs small money (big) | 77-101 | +0.21 on 85 (z 1.32) | keep |
| Sharp move snapshot (move) | 96-81-3 | -0.11 on 137 (z -0.86) | keep |
| All snapshot signals | 579-523-3 | +0.24 on 362 (z 2.49) | |

### Move tape (data/state/moves.jsonl.gz, settled rows with clv_pts)

Notable = origin Pinnacle, or Kalshi big_n > 0 with big_net > 0.

| Slice | Settled | CLV (z) | Rule outcome |
|---|---|---|---|
| **Notable moves** | 544 (W-L 266-278) | -0.52 (z -5.29) | **past 300 settled with the retire line met (CLV at or below zero, z -1 or worse). Not bet, so under the 11/2 amendment Sean decides; left on the page and logging until he does** |
| Notable, Pinnacle origin | 410 | -0.34 (z -3.43) | |
| Notable, Kalshi big money | 134 | -1.10 (z -4.18) | |
| All settled moves | 1,613 | -0.84 (z -10.26) | |
| Exchange-led, Pinnacle followed | 159 | +0.38 (z 1.89) | not a defined signal; see worth watching |
| Exchange-led, Pinnacle did not follow | 1,044 | -1.22 (z -10.68) | |

## Polymarket sharp accounts (first read: 166 graded flags, past the 150 line)

data/state/sharp_paper.jsonl. 1u = 1 unit to risk at the Polymarket ask; sized = Sean's sizing (u). CLV vs Polymarket's close as logged.

| Slice | Record | Units 1u (sized) | ROI 1u (z) | CLV vs Polymarket close (z) |
|---|---|---|---|---|
| **All** | 72-94 | -31.34 (-13.72) | -18.9% (z -2.48) | -0.14 on 123 (z -0.60) |
| Grade A | 46-66 | -23.56 (-12.18) | -21.0% | +0.09 on 85 |
| Grade B | 19-16 | -0.21 (+0.53) | -0.6% | -0.92 on 28 (z -2.04) |
| Watch | 7-12 | -7.57 (-2.07) | -39.9% | +0.05 on 10 |
| Moneyline | 36-35 | -3.74 | -5.3% | -0.04 on 46 |
| Spread | 22-34 | -16.05 | -28.7% | -0.26 on 45 |
| Total | 14-25 | -11.56 | -29.6% | -0.14 on 32 |
| NFL | 8-21 | -16.20 | -55.9% | +1.04 on 19 |
| NBA | 23-31 | -14.31 | -26.5% | -0.63 on 36 |

**Vs Pinnacle's no-vig close** (data/<sport>/ticks and ticks5, venue Pinnacle; the two sides at the flag's line devigged multiplicatively from the
last Pinnacle quote of each before the start). 76 of 166 flags scored; not scored: 41 no event id, 44 no Pinnacle quote at the flag's line,
3 soccer three-way moneylines, 2 no Pinnacle ticks for the market.

| Slice | Scored | CLV vs Pinnacle close (z) |
|---|---|---|
| Pinnacle quote at that line within 60 minutes of the start (the close) | 57 | -0.57 (z -1.80) |
| of which moneyline / spread / total | 37 / 12 / 8 | +0.05 / -2.04 / -1.19 |
| Same 40 flags with a Polymarket CLV too: Pinnacle vs Polymarket | 40 | -0.90 vs -0.55 |
| Any last quote at that line (includes lines Pinnacle had moved off, up to days earlier) | 76 | -1.12 (z -3.46) |

Rule outcome: **keep**. Polymarket-close CLV -0.14 (z -0.60) does not meet the retire line (z -1 or worse); nothing near promotion.
Against Pinnacle's close it is -0.57 (z -1.80) on 57, so the outside yardstick is worse than Polymarket's own.

**System bets with sharps on the same side vs against** (data/state/sys_sharp_tags.jsonl joined to fills.jsonl by fill_id; 82 of 87 tags
found in fills, 9 still open or void):

| Sharps on the system bet | Record | Units | ROI | CLV |
|---|---|---|---|---|
| With only | 13-15 | -1.71 | -11.4% | -1.03 on 25 |
| Against only | 13-7 | +1.98 | +19.8% | -0.03 on 19 |
| Both sides | 7-18 | -6.11 | -48.9% | -1.10 on 25 |

Sharps with the system bet did not help so far (73 graded, too few to act on).

## Changes

1. **nba_momentum retired** (systems rule: 58 graded, ROI z -3.27). Removed from RULES in sharp/systems.py with a comment citing this
   checkpoint; its firing block now checks RULES, so no new fills. Past fills stay on the record.
2. Notable moves passed 300 settled with the retire line met: flagged for Sean's decision (11/2 amendment), no change made.
3. Nothing promoted. No other rule or signal crossed a line.

## Worth watching

- Kalshi 4+ movers: CLV +0.59, z 2.68 on 88. If it holds to 150 CLV-graded it meets the promote line on CLV; ROI on priced
  moneylines is -1.0%, inside the -5% floor.
- Exchange moves that Pinnacle then followed: +0.38 on 159 (z 1.89), against -1.22 on 1,044 not followed. Last week +0.96 on 9 NBA.
- Polymarket sharp flags: flat on Polymarket's close, negative on Pinnacle's (-0.57 on 57), and -18.9% ROI on 166. Spreads and totals carry
  the loss; moneylines are near zero on both yardsticks.
- steam_rev totals: CLV -0.82 (z -1.81) on 68, the weakest market.
- Next systems near a line: none at 25+ graded besides xch_homedog_fade (positive). cfb_day_over (2-5, CLV -1.94) and
  cfb_homefav_7510_under (1-3, CLV -1.84) are the ones to watch as they reach 15 and 25.
