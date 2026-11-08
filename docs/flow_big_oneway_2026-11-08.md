# Heavy one-way big money as opposition? (11/8)

Sean, 11/8: Celtics/Bucks Over 223.5 (tier C) drifted 2 points down with $47,889 of $500+ exchange money on the under and the board
showed it clean. Should heavy big money on the other side count against a bet even when small money agrees with it (not the
"divergent" shape the board uses)?

Method: sharp/flow_split.py re-run with one-way thresholds $1K / $5K / $10K / $25K (BIG = big money net that far on one side, small
money ignored; DIV = big and small on opposite sides). 82,092 settled two-outcome game markets (17,405 Kalshi, 64,687 Novig), pregame
taker fills, entry at T-6h / T-1h / T-15m at the two-sided mid, flat 1u, graded on the result and on CLV.

## Following heavy one-way big money (BIG)

| Venue | Entry | $5K | $10K | $25K |
|---|---|---|---|---|
| Kalshi | T-6h | 333, +4.0% (z 0.7) | 174, +5.4% (z 0.6) | 75, +2.4% (z 0.2) |
| Kalshi | T-1h | 600, -6.6% (z -1.6) | 336, -9.6% (z -1.7) | 136, -0.9% (z -0.1) |
| Kalshi | T-15m | 765, -0.1% | 472, +1.9% (z 0.4) | 205, +0.7% (z 0.1) |
| Novig | T-6h | 623, -0.7% | 209, -1.1% | 19, -3.1% |
| Novig | T-1h | 1,219, -1.9% | 477, -3.2% (z -0.7) | 78, -11.2% (z -1.0) |
| Novig | T-15m | 1,468, -1.2% | 642, -2.6% (z -0.6) | 121, -18.4% (z -2.05) |

CLV on the big side is slightly positive (about +0.1 to +0.35 points): the price follows the money a little, the result does not.

## Read
- Following one-way big money is flat to negative at every size and time; no cell clears z 2 in the direction of the money.
- If anything the biggest late one-way money loses (Novig $25K at T-15m: -18.4%, z -2.05, one cell of 48 searched).
- So heavy one-way big money is **not** evidence against a bet. Counting it as opposition would hold good bets for no reason.
- Unchanged: the board's big-money signal stays the divergent shape (big against small), which is the only shape with any lift
  (docs/flow_split_2026-10-31.md), and stays watch-only context.
