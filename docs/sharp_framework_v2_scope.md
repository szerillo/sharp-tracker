# Sharp framework v2: scope (2026-10-30, not started)

## The problem with v1

The current "sharp" view is an off-market scanner: every venue's price is compared with an exchange-anchored fair number and
the gaps are listed. That is what OddsJam, Unabated and every positive-EV screen already do, and it tells you where a soft book
is slow, not where sharp money is. The ticket/money percentages on the page come from Action Network's consensus feed; they
are public-side counts from a handful of retail books and have failed every test we have run against them (RLM and public
fields appeared in all 54 Bet Labs screen-sides and none survived; the AN public-money families in the systems engine have
no CLV edge). Both get dropped from the primary view.

What we actually want to know, per market, is: who moved first, how much was it worth to follow, and is the move still live.

## What v2 shows: the move tape

One row per move on a game market, newest first, filterable by sport. A move is a change of at least 2 cents (devigged
probability) or half a point of number at a venue between two snapshots. Each row carries:

| Column | Source | Why it matters |
|---|---|---|
| Origin venue | first venue to move in that direction within the snapshot window | Pinnacle or Circa origin is sharp by construction; a DK-first move is a promo or a liability dump |
| Limit tier at the move | Pinnacle maxRiskStake at the snapshot | moves made at full limits are the ones the book was willing to be hit on |
| Exchange flow | Novig trade tape and Kalshi fills in the 30 minutes around the move: notional, taker side, largest single fill | tells you whether real money crossed the spread or a maker just re-quoted |
| Followers | venues that matched within 1 / 2 / 3 snapshots, and the ones that have not | the stuck books are the bet; the follow rate is the move's credibility score |
| Stuck rate | share of soft books still at the old price now | live actionability |
| Distance to close | once settled: Pinnacle close minus the price right after the move | the only grade that matters; CLV in cents |
| Result | once settled: win / loss / push of following the move | secondary, shown with the CLV |

Summary tiles above the tape, per sport, gated at 150 settled events as today: follow rate by origin venue, CLV of
following each origin venue, CLV by limit tier, CLV by exchange-flow bucket, and the same for moves against the public side
(the only use of public percentages left, as a conditioning variable, not a signal).

## What has to change in the data to make that honest

1. Cadence. Twenty-minute snapshots cannot say who moved first: most steam resolves across every venue inside five minutes.
   A second logger runs every 5 minutes for Pinnacle (guest API, limits included), Novig (public book, best bid per outcome)
   and Kalshi (orderbook top and recent trades) only. These three are cheap and have no scraping risk. Soft books stay at 20
   minutes through Action Network, which is enough to measure follow and stuck rates at the 1/2/3-snapshot grain.
   GitHub Actions cron has a 5-minute floor and real jitter of 1 to 4 minutes; each tick records its true timestamp and the
   analysis works on timestamps, not on tick count. Expected volume: about 3 to 6k rows per sport per day across the three
   venues; data/<sport>/ticks5/YYYY-MM-DD.jsonl.gz, rolled off at 30 days once settled (the derived move table is kept).
2. Novig trade tape. novig_tape.py already pulls settled-market history; for live moves it needs the public trades endpoint
   per active market at the 5-minute cadence, stored as fills (ts, market, side, price, size, taker side where exposed).
3. Kalshi trades. GET /markets/trades per active ticker, cursor-paged, same cadence.
4. Move table. sharp/moves.py builds data/state/moves.sqlite from the 5-minute tape plus the 20-minute soft-book tape: one
   row per (event, market, main line, direction, origin venue, ts), with the columns above filled as follow-ups arrive and
   closed out at settlement. move_signals.py M1 to M6 are re-pointed at this table rather than recomputed from scratch.
5. Pre-registration. Before the first row is published the tests are written down with their gates: follow rate by origin
   (null: equal across venues), CLV of following a Pinnacle full-limit move (null: zero after the 2-cent cost of crossing),
   CLV of following exchange flow above $5k notional when Pinnacle has not moved (null: zero), and a timing split at 6 hours to
   kickoff. Everything else in the summary tiles is descriptive and labelled so.

## What gets removed

- The venue-vs-fair gap list as the primary view. It stays as a secondary "stale prices now" table because it is still the
  outlet for acting on a move, but it is no longer presented as the sharp signal.
- The AN ticket and money percentage columns and the sharp10 confirmation flag. The families stay in the systems engine as
  paper tags until their 100-fill gate, then are retired if CLV is not positive; nothing else in the product depends on them.
- The Polymarket feed from the move logic (illiquid on game lines; kept in the data for futures only).

## Effort and order

1. loggers/fast.py (Pinnacle + Novig + Kalshi, 5 minutes) and prices_fast.yml: half a day. Start first so the tape accrues
   while the rest is built.
2. Novig and Kalshi trade pulls into the same logger: half a day.
3. sharp/moves.py and the moves table, with move_signals re-pointed: one day.
4. Move-tape page and summary tiles, replacing the gap list as the sharp tab's landing view: one day.
5. Pre-registration doc with gates, then 150 settled events per sport before anything is published (NBA and NHL reach that
   in about three weeks at the current schedule; NFL and CFB need the full season).

## Open questions for Sean

- Circa and Bookmaker are the other sharp-origin venues worth logging; neither has a public API. Skip unless a paid
  aggregator key arrives (ROADMAP §0 step 4).
- Whether to keep the 20-minute AN soft-book feed at all once follow rates are measured, or replace it with a paid screen.
