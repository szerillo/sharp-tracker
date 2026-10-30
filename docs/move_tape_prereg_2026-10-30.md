# Move tape: pre-registered tests and gates (2026-10-30)

Written before the first settled move on the 5-minute tape. Nothing in the Moves tab tiles is a result until the gate below is
met, and the tests are the ones listed here, graded the way described here. Code: loggers/fast.py (tape), sharp/moves.py (table),
index.html Moves tab (view). Scope and rationale: docs/sharp_framework_v2_scope.md.

## Definitions (fixed)

- Venues on the fast tape: Pinnacle (guest API, maxRiskStake limit), Novig (public listing best bid per outcome; signed key when
  present), Kalshi (top of book). Soft books on the 20-minute tape: DK, FD, Caesars, BetRivers, Fanatics, theScore. BetMGM is
  logged but never a bettable outlet. Action Network ticket and money percentages are not inputs to anything here.
- Probability: books devigged two-way (multiplicative) per venue per snapshot; exchanges use the bid/ask mid, and only when the
  book is two-sided and inside 4 cents. Three-way markets are excluded.
- Markets: full-game moneyline, spread, total, on the main line (Pinnacle's most-quoted number for the game; the most-quoted
  number across venues when Pinnacle has none). Alternate lines are not moves.
- Move: a change of 2.0 probability points or more between two consecutive observations of one fast venue, before kickoff.
  Moves in the same direction on the same market within 15 minutes are one move; the earliest venue is the origin and the
  others are "with". Following: a venue moving 1.0 point or more in the same direction after the origin timestamp, measured in
  minutes. Stuck: a soft book whose last observation (at most 45 minutes old, game not started) has not followed.
- Flow: Kalshi taker trades on the same event and market within 30 minutes either side of the origin, in dollars at risk,
  signed with the move direction; Novig fills on the same market (unsigned dollars) when the public tape is on disk.
- Grade: close = Pinnacle's last pre-kickoff probability on the main line (Novig when Pinnacle has none). CLV of a move =
  (close - origin price after the move) in the move direction, in points. Stuck-book CLV = (close - the stuck book's price at the
  origin) in the move direction. Result = outcome of the side the move pointed to, from the graded closes; pushes excluded.
- Cadence: GitHub Actions cron has 1 to 4 minutes of jitter; all windows use true timestamps, never snapshot counts.

## Gate

150 settled events per sport on the fast tape before any tile is published; previews are labelled. NBA and NHL reach it in
roughly three weeks; NFL and CFB need most of the season; soccer and MMA are reported but not expected to gate this year.

## Tests (per sport, settled moves only)

| # | Question | Statistic | Null | Decision |
|---|---|---|---|---|
| T1 | Does a Pinnacle-origin move keep going? | mean CLV of Pinnacle-origin moves; share with CLV >= 0 | mean CLV = 0 (the move is fully priced at Pinnacle's new number) | positive at z >= 2 on n >= 100 |
| T2 | Is following a Pinnacle move at a stuck soft book worth it after the price? | mean stuck-book CLV minus 2.0 points (the cost of crossing a -110 book) | <= 0 | positive at z >= 2 on n >= 100 stuck-book bets |
| T3 | Do exchange-origin moves lead Pinnacle? | share of Novig/Kalshi-origin moves Pinnacle follows within 30 minutes; CLV of those moves vs Pinnacle's close | follow rate equal to the base rate of Pinnacle moving 1+ point in any 30-minute window; CLV = 0 | both positive at z >= 2 on n >= 100 |
| T4 | Does Kalshi flow with the move add information? | CLV of moves with $1k+ net taker dollars with the move vs moves with no trades | equal | difference at z >= 2, each bucket n >= 50 |
| T5 | Does the Pinnacle limit at the move matter? | CLV by limit tercile for Pinnacle-origin moves | equal across terciles | monotone and top vs bottom at z >= 2 |
| T6 | Timing | CLV by hours to kickoff (>24h, 6-24h, 1-6h, <1h) | equal | descriptive only, no decision |

Everything else on the tab (follow rates by venue, by-market splits, the Novig dollars) is descriptive and stays labelled so.
A test that passes in one sport is not applied to another without that sport's own gate.

## What a pass changes

A pass on T1 or T2 makes "Pinnacle moved, book X has not" a system in sharp/systems.py with a paper ledger, graded on real closes
like every other tag, with the usual 100-fill gate before anything is called a result. A pass on T3 does the same for "exchange
moved, Pinnacle has not". A fail retires the family; the tape stays as a view.

## Known limitations, stated up front

- The tape starts 2026-10-30; nothing before that is on it. The 20-minute pre-registered move tests (sharp/move_signals.py, M1 to
  M6) continue on the older tape and are reported separately.
- Line changes (a spread moving from -3 to -3.5) are not moves on this tape; only price moves on the main number are. A number
  change shows up as the venue leaving the main line.
- Novig flow is direction-blind for now (the public tape carries outcome ids, not names).
- Circa and Bookmaker are not logged (no public API).
