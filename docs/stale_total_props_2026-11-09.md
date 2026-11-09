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
