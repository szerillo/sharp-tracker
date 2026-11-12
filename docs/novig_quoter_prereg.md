# Novig paper quoter: pre-registered go/no-go test

Written 11/12/2026 before any of the test data exists (Sean's order, 11/12 evening: "write the pass bar NOW, before the data"). The
commit that adds this file is the registration. Paper only: no orders, no trading keys, nothing live. After the test it is Sean's call.

## What is tested

The paper quoter in sharp/novig_paper_quoter.py, with the rules written in its header, unchanged:
- Last hour before the start, until 5 minutes before it. $100 bids 1c under Pinnacle's no-vig fair (half-cent prices).
- Fair: both Pinnacle sides at the same number from one pull, no older than 10 minutes.
- Game spreads pulled on any Pinnacle move; other markets repriced on a 0.5c move and pulled on a 1c move; back only after an unchanged
  reading. Cancelled when no fresh reading for 10 minutes. 2 minutes out after a fill.
- Caps: $300 filled per game, $2,500 filled and unsettled at once.
- Fills only from Novig maker trades on the same outcome: trade-throughs always, touches only when our bid was first in line.

## Data

- Test period: games starting 11/13/2026 through 11/26/2026 (UTC dates), 14 game days, from the daily run (novig_quoter.yml, dispatched
  by pulse.yml about 5:20 AM ET, two days behind). Evaluated after the run that covers 11/26 and after the Novig results backfill has
  settled those games.
- The replay of 10/30 to 11/11 is development data. It informed the rules and does not count.
- Groups tested: game spread, game total, team totals, period lines, game moneyline. Player props are logged and reported, not tested.

## Pass bar, per group

A group is evaluated only with at least 150 fills on at least 40 games; otherwise it is "insufficient", which is not a pass.

A group passes when all three hold:
1. Close edge on filled contracts (Pinnacle no-vig at the start minus our price, weighted by contracts) is at least 0.40c, and its 90%
   lower bound, clustered by game, is above 0.
2. The +5 minute mark on filled contracts is at least 0.00c (on average we are not picked off within five minutes).
3. Settled results are not significantly worse than the close says: the per-game mean of (settled P&L minus close-expected P&L) is
   above -2 standard errors.

A group is excluded and flagged if its +5 minute mark is below -0.25c or its close edge is below 0, whatever its sample.

## Go / no-go

GO for Sean's decision requires all of:
- At least 2 groups pass.
- Pooled over the passing groups: close edge at least 0.40c with a 90% lower bound above 0.
- Pooled over the passing groups: at least $10 a day expected at the close at the paper sizes (a floor that shows it trades at all,
  not a business case; real money scales with size and with how much of the book we take).
- Side fill rate at least 10%: of the market sides the quoter posted on in the passing groups, at least 1 in 10 got any fill.

Otherwise NO-GO. Either way the full table for every group is reported, passing or not.

## Why these numbers

- 0.40c: the plan's fresh-fair test had every headline group's last-hour close mark between 0.71c and 1.34c on the market's own fills;
  our quoter fills only when someone trades through or into our price, which selects for informed flow, so a lower bar than the market
  average is the honest test. Under 0.40c, ProphetX-style fees or any execution slippage would eat it.
- +5 minutes at 0: the plan's spread fills fell to 0.12c by +30 minutes; a quoter that is underwater five minutes after its fills is
  being picked off, whatever the close says.
- The settled check guards against the close mark being wrong (for example a stale Pinnacle close).
- Requiring 2 of 5 groups and a pooled bound limits passing by chance across five tests.

## Rules for the two weeks

- No change to the quoting or fill rules during the test. A change to either restarts the 14 days, with a dated note below.
- Bug fixes that do not change quotes or fills (logging, grading of results) are allowed and noted below.
- Cuts added after the data is seen are exploratory and do not count toward the decision.
- The quoter is a replay of the public file two days behind, not a live order book: the record shows what resting bids at these rules
  would have filled against real trades, not what a live quoter with second-by-second Pinnacle reads would do.

## Changes

- 11/12: registered.
