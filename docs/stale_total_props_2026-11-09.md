# Game total moved, player props did not: do the stale props win? (11/9)

Sean's idea: when a game total moves but a book's player props do not follow, the props are stale. Bet the prop in the direction of the
total move (total up: over; total down: under) at the book's unchanged line.

## Data
- Prop snapshots already on hand: NBA threes and NFL rushing yards / anytime TD at 3 hours and 10 minutes before the start; NHL shots and
  saves at 1 hour and 10 minutes. 2023-26.
- The game total: Pinnacle's (median book total when Pinnacle is missing) from the Odds API game-line history at the snapshot nearest each
  prop time. Games with both: NBA 1,540, NFL 541, NHL 792.
- "Prop flat" = the book's main line unchanged and its no-vig over price moved under 3 points toward the total's direction. Bets at FD,
  Caesars or DK at the late snapshot, best of the three, one bet per player, market and game. Graded on ESPN box scores; pushes void.
- Baseline = the same props in games where the total did not move.

## Results

| Market | Total move, bet | Prop flat at the book | Prop moved with the total | Baseline (total flat) |
|---|---|---|---|---|
| NBA threes | up 2+, over | 1,218 bets, -1.8%, 2/4 seasons | 57, -11.3% | over -7.6% |
| NBA threes | down 2+, under | 981, -1.6%, 2/4 | 40, +19.1% | under -2.2% |
| NBA threes | up 3+, over | 363, -1.1% | | |
| NBA threes | down 3+, under | 352, -5.1% | | |
| NBA threes | 4+ either way | 143 over -6.9%, 213 under -11.9% | | |
| NFL rushing yards | up / down 1.5+ | 38 over -25%, 30 under -5% | | over -2.1%, under -6.9% |
| NFL anytime TD Yes | total up 1.5+, price flat | 166, +11.9% | 77, -6.8% | total down 1.5+, Yes: +17.6% (same band effect) |
| NHL shots | up / down 0.5+ | 327 over -4.1%, 369 under +2.7% | | over -8.1%, under -2.3% |
| NHL saves | up 0.5+, over | 28 bets, 20-8, +32%, 4/4 seasons | | over -10.7% |

## Read
- **No edge in the 3-hour window.** Stale props after a late total move lose, about the vig. Bigger total moves make it worse, not better
  (NBA threes 4+: -7% to -12%).
- The one useful detail: NBA threes overs lose 7.6% in general but only 1.8% after the total rises 2+ with the prop flat. So the total
  move carries a little information about threes overs; it is not enough to beat the vig.
- Pinnacle almost never moves a prop in this window either (16 cases of 1,218). The books and Pinnacle both leave props alone after
  late total moves, and the results say they are right to: late total moves (pace, officials, weather) do not carry over to threes or
  rushing yards.
- NFL anytime TD: the "total up, price flat" slice wins, but so does "total down, price flat". That is the 25-50% band effect already
  live, not the total move.
- NHL saves overs after the total rises: 20-8 in 28 bets, every season positive. Too small to act on; on the watch list.

## What this does not cover
The total usually moves most between the open and a few hours before the start, which this data cannot see: our prop snapshots start 3
hours out (1 hour for NHL). The test that matters for Sean's idea is the open (or 6-12 hours out) against the late snapshot. That needs
an earlier prop pull: NFL anytime TD and rushing yards at 6 hours out is about 19,000 credits; NBA threes at 6 hours about 40,000. We are
about 72,000 above the 3M floor, so the NFL pull fits and the NBA one would need the floor lowered.

Script: scratchpad stale_total.py / stale_an.py (not in the repo; reproducible from data/oddsapi/derivs and data/oddsapi/compact).

## Update (5 AM): NFL, every prop market, 6 hours out against 10 minutes out
Pulled: all 12 NFL prop markets 6 hours before kickoff, 644 games from October 2024 to now (data/oddsapi/derivs/nfl_props_t360m.jsonl.gz;
the pull stopped itself at the 3M credit floor). The test needs Pinnacle's game total at both times, and our game-line history has a
snapshot 6 hours out for only about half of NFL games and stops in February 2026 (the 2026 season is not in it). So only **154 games**
could be tested.

With the total up or down 1+ point and the book's prop unchanged (bet with the move), by market:
- Larger cells (130-280 bets): receptions over +4.2% / under -10.7%; receiving yards over +5.2% / under -15.6%; anytime TD Yes -6.7%
  after a rise (the plain 25-50% band is +12.9% here, so the total move adds nothing).
- Small cells (25-60 bets): rush attempts over +15%, rush yards over +3%, rush+receiving yards over +21%, pass completions over +11%,
  pass TDs over +10%; every under after a drop loses (-9% to -27%).
- Moves of 2+ points: under 20 bets in every market.

Read: nothing reliable; a slight lean toward overs after the total rises and against unders after it drops, on samples too small to mean
anything. The bottleneck is the game total, not the props: a historical Odds API pull of NFL spreads and totals at each kickoff window, 6
hours out, for 2024-26, is roughly 200 snapshots at about 20 credits each (about 4,000 credits), which would bring all 644 games in.

## Update (6 AM): NFL with the game lines pulled (556 games, every market)
Pulled Pinnacle and US-book spreads and totals 6 hours and 10 minutes before every kickoff in the props file (loggers/oddsapi_lines_at.py,
558 calls, 11,160 credits; 2,988,791 left). 556 of 644 games now testable. Bets at the book's unchanged line, 10 minutes out, with the
move; "team total" = the player's team's implied total from the spread and total. Seasons 2024-26.

| Market | Game total up 1+: over at a flat prop | Game total down 1+: under at a flat prop | Team total down 1+: under, flat | Baseline (no move): over / under |
|---|---|---|---|---|
| Receptions | 733 bets, -4.1% | 759, +0.6% | 114, +11.0% (team down 1.5+: 30, +31.7%) | -5.4% / -3.7% |
| Receiving yards | 579, -4.2% | 589, -5.9% | 88, +9.7% (prop moved too: 71, +17.8%) | -2.8% / -7.4% |
| Rushing yards | 270, 0.0% | 304, -10.6% | 52, +2.3% | -5.7% / -4.1% |
| Rush attempts | 213, -11.3% | 240, -6.0% | 36, -1.8% | -12.8% / +1.2% |
| Rush + receiving yards | 128, +2.3% | 128, -8.9% | small | -13.7% / +0.6% |
| Passing yards | 104, -1.5% | 92, -3.5% | small | -2.3% / -7.6% |
| Passing TDs | 147, -4.0% | 161, -20.2% | small | -0.3% / -5.7% |
| Completions / attempts / INTs | -11% to -13% | -3% to +3% | small | -6% to -8% / -3% to -7% |
| Anytime TD Yes (price flat) | 1,189, -2.9% | 1,231, +15.1% | 190, -1.1% | +13.0% (the 25-50% band effect) |

Moves of 2+ points: 40-100 bets per market, nothing consistent.

**Read: no stale-prop edge in the 6-hours-to-close window, in any of the 12 markets.** A flat prop after the total moves loses about what
props lose anyway. The anytime TD Yes after a total RISE is worse than the baseline (-2.9% against +13.0%), the opposite of the idea.

The one consistent lean is unders on receiving props when the player's own team total drops a point or more: receptions 114 bets +11.0%,
receiving yards 88 bets +9.7% (and +17.8% where the prop did move, but not enough). z about 1.0-1.4, 2 of 3 seasons. Watch list, not a
rule. It is also the slice a 24-hours-out snapshot would test best, since the bigger team-total moves happen earlier in the week.
