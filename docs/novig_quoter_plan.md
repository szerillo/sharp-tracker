# Novig quoter: build plan (paper only)

Sean, via Kirk, 11/11: lay out the plan to build a Novig quoter, paper only; no live orders until Sean signs off. Nothing below places
an order.

Refresh 11/11 22:35 UTC: the select file was rerun through 11/10 (our Pinnacle tape starts 10/30, so in practice 10/30 to 11/10). No
headline row changed sign; every z moved by 1.1 or less; the share of edge kept to the close in the last hour moved by 1 to 8 points
(spreads 76%, totals 67%, team totals 76%, period lines 87%, moneylines 74%, props 57%). The table in section 1 is the 11/9 version and
the conclusions stand. The history file could not be refreshed in substance: see section 7.

Evidence: data/research/novig_maker_select.json (11 days, Oct 31 to Nov 9: every Novig maker fill on a market Pinnacle also
quotes, priced against Pinnacle's no-vig fair at the fill, 30 minutes later and at the close) and novig_maker_history.json (Aug 3 to
Nov 6, settled results). Current paper offers: data/state/offers_record.json.

## 0. Before building: the one assumption to test first

"Edge at fill" in the select file is measured against the last Pinnacle quote up to 30 minutes before the fill, and the two sides of
the market may come from different pulls (`fair(k, t, 1800)` in sharp/novig_maker_select.py). If Pinnacle had already moved by the time
of the fill, a stale fair makes the fill look like edge that then "decays" by +30m.

**Result (11/12): the last-hour edge survives a fresh fair.** Rerun over 10/30 to 11/11 with the fair limited to a Pinnacle quote taken
within 5 minutes, and within 2 minutes, before the fill, both sides from one pull (within 60 seconds of each other):
data/research/novig_maker_select_fresh300.json and _fresh120.json. Bids 1c under fair, last hour, cents at fill / +30m / close:

| Market | All fills (30-minute fair) | Fair within 5 minutes | Fair within 2 minutes |
|---|---|---|---|
| Game spread | 1.19 / 0.65 / 0.91 (z 33.42, 12,447 fills, 257 games) | 1.19 / 0.43 / 0.83 (z 32.1, 3,982 fills, 258 games) | 1.2 / 0.12 / 0.74 (z 28.05, 1,738 fills, 204 games) |
| Game total | 1.21 / 0.61 / 0.81 (z 28.09, 7,450 fills, 291 games) | 1.18 / 0.63 / 0.75 (z 29.91, 3,910 fills, 281 games) | 1.19 / 0.74 / 0.93 (z 26.65, 1,796 fills, 227 games) |
| Team totals | 1.23 / 0.57 / 0.94 (z 15.14, 1,240 fills, 219 games) | 1.25 / 0.63 / 1.04 (z 10.53, 298 fills, 103 games) | 1.26 / 0.68 / 1.03 (z 8.07, 140 fills, 57 games) |
| Period lines | 1.21 / 0.65 / 1.05 (z 30.86, 2,035 fills, 211 games) | 1.22 / 1.1 / 1.22 (z 33.16, 1,288 fills, 176 games) | 1.19 / 1.18 / 1.34 (z 27.79, 551 fills, 121 games) |
| Moneyline | 1.21 / 0.59 / 0.9 (z 23.32, 13,272 fills, 287 games) | 1.18 / 0.47 / 0.89 (z 24.85, 8,171 fills, 281 games) | 1.2 / 0.31 / 0.71 (z 22.24, 3,339 fills, 238 games) |
| Player props | 1.22 / 0.4 / 0.69 (z 9.12, 24,008 fills, 153 games) | 1.21 / 0.33 / 0.89 (z 9.03, 4,611 fills, 148 games) | 1.2 / 0.24 / 0.96 (z 10.92, 1,836 fills, 143 games) |

- Every market keeps a positive close mark with a 2-minute fair: 0.71c to 1.34c. Totals, team totals, period lines and props hold or
  improve. Spreads (0.91c to 0.74c) and moneylines (0.90c to 0.71c) lose about a fifth, so part of their measured edge was the stale
  fair. The last-hour edge is not an artefact of a stale Pinnacle price.
- Spreads at 2 minutes fall to 0.12c at +30m before recovering to 0.74c at the close: fills on fresh spread quotes get hit hard in the
  next half hour. A reason to pull spread quotes on any Pinnacle move (section 2).
- The fresh cut keeps 15% (5 minutes) and 7% (2 minutes) of the 3.48M mapped maker fills: only fills that happen to land just after one
  of our Pinnacle pulls. Which fills those are depends on our pull clock, not on the market, so it is a fair sample, but a thin one in
  team totals (140 fills at 2 minutes).
- z is the close mark clustered by game (one value per game). It is large because it measures price, not settled results.
- What the test cannot rule out: Pinnacle moving in the seconds before a fill. Our tape is 5 minutes at best; a live quoter would read
  Pinnacle in seconds (section 2).
- The comparison column for the same fills under the old 30-minute fair came out identical by construction (when a quote within 2 minutes
  exists, it is also the latest within 30), so the comparison above is fresh-fair fills against all fills.

## 1. Where to start: markets and windows

Bids 1c under Pinnacle's fair, share of the edge at fill still there at the close (11 days):

| Market | 24h+ | 6-24h | 1-6h | Last hour |
|---|---|---|---|---|
| Game spread | 50% | 114% | 51% | 73% (13,303 fills, 255 games) |
| Game total | 76% | 35% | 47% | 65% (8,033 fills, 290 games) |
| Team totals | 6% | 19% | 48% | 75% (1,258 fills, 233 games) |
| Period lines | 102% (104 fills) | 27% | 67% | 79% (2,101 fills, 218 games) |
| Moneyline | 2% | -57% | -10% | 70% (13,413 fills, 292 games) |
| Player props | -64% | -16% | -3% | 55% (23,809 fills, 156 games) |

- Start with the last hour before the start, on spreads, totals, team totals and period lines, 1c under fair. That is the one window where
  every market keeps most of its edge to the close, and these four keep 65-79%.
- Moneylines: last hour only. Earlier, a moneyline bid that fills loses the edge or worse (6-24h: -57% of the edge at fill by the close).
- Props: not in the first version. 1c under keeps nothing before the last hour; in the last hour 1c keeps 55% and 2c 59%, but props
  have the thinnest Pinnacle coverage and the most stale quotes.
- Bigger gaps are not safer on moneylines: 2c under from 6 to 24 hours closes at -1.87c, 3c under at -0.87c. On spreads, totals and
  period lines 2c under keeps about as much of its edge as 1c, or more.
- Leave out: soccer moneylines (three-way), period moneylines (ties), fair outside 8-92%, anything Pinnacle does not quote at the same
  number on both sides.

## 2. Quote logic

- Fair: Pinnacle no-vig, multiplicative devig of the two sides at the same number, both from the same pull, no older than a set age
  (start at 60 seconds live; paper uses our 5-minute tape, see section 4). No Pinnacle price, no quote.
- Price: bid 1c under fair on the side, rounded down to Novig's half cent. Quote both sides of a market only if both bids clear the
  rule; we are never trying to be first at fair.
- Size: $100 per quote in paper. Caps: one live quote per market side; $300 at risk per game; $2,500 across all open quotes. A fill
  pauses that market for 2 minutes before it re-quotes.
- Reprice: when fair moves by 0.5c or more, cancel and repost at the new price.
- Pull: Pinnacle's line or price moves 1c or more inside a minute (move first, re-quote after the next stable read); the Pinnacle quote
  is older than the age limit; a line change at Pinnacle or Novig; 5 minutes before the start; a large Novig taker print on the other
  side of the same market (someone knows something).
- Fees: Novig charges no pregame fee, so the edge is fair minus our price. Kalshi is not part of this build; ProphetX is section 2b.

## 2b. ProphetX, net of its fee (11/12)

The fee, as settled by Kirk from ProphetX's CFTC self-certification (filed 6/12/26, effective 6/29, extended 12 months on 8/15/26): 2% of
net proceeds per market, assessed at settlement, on single-event contracts; the same for makers and takers. A market we lose pays
nothing, so it is 2% of the profit on a winning contract. Parlays and RFQs pay no fee. A maker rebate returns a share of fees monthly by
make volume (marginal tiers): $0-50k 0%, $50k-750k 20%, $750k-3M 40%, $3M-7.5M 60%, over $7.5M 80%. At our paper caps (under $50k a
month) the rebate is 0.

Expected fee per $1 contract bought at price q with fair p: 0.02 x p x (1 - q). About 0.5c at 50%, 0.35c at 80% or 20%. The paper
offers already net it this way (sharp/offers_live.py).

We have no ProphetX fill history (no public trade feed), so the stand-in is Novig's last hour (select file, 10/30 to 11/10): the edge a
filled bid still had at the close, less the fee at 50% (the worst case):

| Market | 1c under: close, after fee | 2c under: close, after fee | 3c under: close, after fee |
|---|---|---|---|
| Game spread | 0.91c, 0.41c | 1.75c, 1.25c | 2.65c, 2.15c |
| Game total | 0.81c, 0.31c | 1.65c, 1.15c | 1.97c, 1.47c |
| Team totals | 0.94c, 0.44c | 1.88c, 1.38c | 2.81c, 2.31c |
| Period lines | 1.05c, 0.55c | 2.06c, 1.56c | 3.05c, 2.55c |
| Moneyline | 0.90c, 0.40c | 1.25c, 0.75c | 1.27c, 0.77c |
| Player props | 0.69c, 0.19c | 1.38c, 0.88c | 2.03c, 1.53c |

Read:
- At 1c under the fee takes about half of what is left at the close; props keep 0.19c, totals 0.31c. Not worth quoting at 1c.
- At 2c under (the paper rule for ProphetX) every group clears the fee in the last hour: period lines 1.56c, team totals 1.38c,
  spreads 1.25c, totals 1.15c, props 0.88c, moneylines 0.75c. Fills at 2c under are rarer (on Novig, spreads 1,848 fills at 2c vs 12,447
  at 1c).
- Moneylines gain little from 2c to 3c (0.75c to 0.77c after fee): the extra gap is mostly picked off.
- ProphetX's own quotes already sit 1.8 to 2.9c under fair on props, so a 2c bid there is often not first in line; the paper offers only
  count a bid that would improve the book.
- These are Novig's numbers with Novig's takers. ProphetX's flow may be softer or sharper; only ProphetX fills would settle it, and there
  is no feed for them. Paper only; nothing live.

## 3. Adverse selection: how the quoter avoids getting picked off

The 11 days show it directly: the larger the gap to fair at the fill, the more often Pinnacle was about to move toward the filler
(moneylines 2-3c under go negative by the close). The defences:
1. Fresh fair or no quote (section 2). A stale fair is how a resting bid gets picked off.
2. Last-hour window first, where fills keep the most edge.
3. Pull on Pinnacle movement before re-quoting, never after.
4. Small size and per-game caps, so one sharp hit costs one quote.
5. Measure it every day: each paper fill is marked at +5m, +30m and the close. If the +30m mark falls under half the edge at fill for a
   market for a week, that market comes out.
6. Watch who fills us: fills that come with a Pinnacle move inside 5 minutes are tagged; if they are most of the fills in a market,
   that market comes out.

## 4. Paper fills against the public tape

Novig's public trade file lists every fill with its time, outcome, price and size, maker and taker rows separately. A paper quote at
price b on an outcome is filled by the tape like this:
- Trade-through (counts): a maker fill on the same outcome at a price worse for the maker than b while our quote is live (someone else's
  resting order filled at a price ours beats). Price priority says ours would have filled first.
- Touch (counts only if we were first): a fill at exactly b counts only if our quote improved the best bid when posted (the paper offers
  already require this). If we joined an existing price level, a touch does not count: we cannot see the queue ahead of us.
- Size: our fill = min(our remaining size, the tape fill's size).
- Live window: a quote is live from its post time plus 5 seconds (latency) until it is repriced, pulled or filled. Repricing and pulls are
  simulated from the Pinnacle tape timestamps, so the paper quoter can only react as fast as our tape (5 minutes); a live quoter would
  react in seconds, so paper understates how many bad fills a live quoter dodges and overstates how many good fills it gets.
- No impact: we assume a taker who hit someone else would have hit us instead, and that our quote does not change anyone's behaviour.
- Grading: edge at fill, +30m and close against Pinnacle's no-vig; then settled result. Dollars per day and fill rate by market and
  window.

## 5. The 9 AM paper offers: is that already a version of this?

Partly. sharp/offers_live.py posts static paper offers every 10 minutes (Novig 1c under fair on spreads, totals, team totals and period
lines; props 2c, 1c in the last hour; moneylines last hour only) and sharp/offers_grade.py checks whether each would have filled inside an
hour at $100. It has no repricing, no pulls and no caps, so it is a version 0 of section 2 without the defences in section 3.

The 9 AM check-in did not run (the scheduled task was disabled when this session's container was replaced). The record at 20:22 UTC
11/11:
- 5,160 offers logged; 2,720 not started yet; 2,310 on markets our tape does not watch, so they cannot be graded; 130 graded.
- 56 of 130 filled inside an hour (43%), $61 a fill. Filled offers closed 1.1c better than our price (38 with a close), unfilled ones
  1.75c better (48). Novig game lines: 51 of 109 filled (47%), filled +1.01c, unfilled +1.70c.
- Read: fills still close in our favour, but the filled offers did worse than the ones that did not fill, which is the adverse selection
  in section 3 showing up on day one. 130 offers is far too few to size anything.
- Coverage is the bigger problem: 2,310 of 2,440 started offers sit on markets the 5-minute tape does not follow. The paper quoter needs
  the Novig public file (section 4) to grade every offer, not the tape.

## 6. Build steps (paper)

1. The fresh-fair test in section 0. Stop if the last-hour edge does not survive it.
2. sharp/novig_paper_quoter.py: replays a day from our Pinnacle tape and the Novig public file, posts, reprices and pulls by section 2,
   fills by section 4, writes data/research/novig_paper_quoter.json. Run over the 11 days in the select file first.
3. Daily job on a runner (the Novig public file is only reachable from GitHub runners), grading yesterday.
4. Board section next to "Offers to rest": fills, edge at fill / +30m / close, dollars per day, by market.
5. Two weeks of paper, then Sean decides. A live version would need his Novig keys as secrets, a quoter he runs himself, and a faster
   Pinnacle read than our tape; none of that is built or started.

## 8. Paper quoter replay, 10/30 to 11/11 (11/12; development data, not the test)

sharp/novig_paper_quoter.py over 13 game days, 1,138 games, with the rules in its header (data/research/novig_paper_quoter_2026-10-30_2026-11-11.json).
Edge columns are cents per filled contract: at the fill / at the next Pinnacle reading / +30 minutes / the close. "Sides filled" is the
share of market sides the quoter posted on that got any fill.

With the registered caps ($300 filled per game, $2,500 filled and unsettled at once):

| Group | Fills | Filled | Sides filled | Edge (fill / next / +30m / close) | Close, 90% low | $/day at close |
|---|---|---|---|---|---|---|
| All headline groups | 908 | $25,499 | 7.2% | 1.21 / 1.1 / 0.92 / 0.91 | 0.86 | $42.96 |
| Game spread | 165 | $4,924 | 9.2% | 1.16 / 1.0 / 0.69 / 0.78 | 0.73 | $6.09 |
| Game total | 254 | $7,766 | 11.1% | 1.21 / 1.09 / 0.98 / 0.82 | 0.77 | $10.21 |
| Team totals | 160 | $3,142 | 3.6% | 1.19 / 0.95 / 1.1 / 1.16 | 0.91 | $5.63 |
| Period lines | 145 | $5,404 | 8.6% | 1.25 / 1.21 / 1.0 / 1.07 | 0.95 | $9.12 |
| Moneyline | 184 | $4,263 | 9.2% | 1.22 / 1.12 / 0.89 / 0.86 | 0.57 | $11.91 |
| Player props (not tested) | 521 | $10,303 | 3.2% | 1.24 / 1.01 / 0.8 / 0.69 | 0.62 | $11.73 |

Without the caps (reporting only):

| Group | Fills | Filled | Sides filled | Edge (fill / next / +30m / close) | Close, 90% low | $/day at close |
|---|---|---|---|---|---|---|
| All headline groups | 3,293 | $93,800 | 17.7% | 1.2 / 1.09 / 0.88 / 0.91 | 0.92 | $163.57 |
| Game spread | 696 | $20,861 | 25.4% | 1.18 / 1.06 / 0.82 / 0.91 | 0.89 | $30.08 |
| Game total | 948 | $25,426 | 27.2% | 1.18 / 1.04 / 0.82 / 0.79 | 0.83 | $31.85 |
| Team totals | 315 | $7,915 | 7.6% | 1.2 / 0.9 / 0.67 / 0.96 | 0.83 | $12.05 |
| Period lines | 493 | $17,815 | 22.5% | 1.23 / 1.17 / 0.99 / 1.07 | 0.97 | $30.02 |
| Moneyline | 841 | $21,783 | 21.8% | 1.2 / 1.11 / 0.94 / 0.91 | 0.72 | $59.58 |
| Player props (not tested) | 4,330 | $83,755 | 16.8% | 1.22 / 0.74 / 0.7 / 0.85 | 0.78 | $116.72 |

Read:
- The edge holds on our own fills: 0.91c at the close in the headline groups, 90% lower bound 0.86c, and the next Pinnacle reading after a
  fill is 1.10c, so on average we are not picked off. Every headline group clears the 0.40c bar with room.
- The caps dropped 6,194 of 13,817 fills (45%). With them, $43 a day at the close and 7.2% of sides filled; without them, $164 a day
  and 17.7%. The fill-rate bar in the prereg (10%) is therefore mostly a test of our own caps (Sean's call, docs/novig_quoter_prereg.md).
- Quotes mostly ended stale (27,722 of 36,409): many Pinnacle series in our tape update only every 20 minutes, so a quote dies 10 minutes
  after its reading. A faster Pinnacle read would quote more of the hour.
- No settled results yet: the Novig results backfill was broken (fixed 11/12, catch-up running); the settled check comes with it.
- 91% of headline fills were trade-throughs, not touches, so the queue assumption matters little.

## 7. Multiple testing note on the history file

Date range caveat (found 11/11): the history file counts settled fills only, and Novig's history API has rejected our key since about
11/4 ("signature verification failed", 401), so no settled results reach the catalog after that. Fills from about 10/29 on are dropped
(6,017,596 as "no win/loss result"). The file says Aug 3 to Nov 10 but in substance covers Aug 3 to about Oct 28; a rerun on 11/11
returned every row unchanged. Fix: Sean updates the NOVIG_KEY_ID / NOVIG_PRIVATE_KEY secrets (the key was due for rotation); the
tracker job's backfill then fills the gap and the history run can be repeated.

novig_maker_history.json reports 392 cuts. "type time | team total | last hour" (+10.37%, z 3.25) is one of them: 10 cuts reach z 3.25 or
more, against 0.45 expected by chance alone; Bonferroni puts its adjusted p at about 0.45 (the critical z for 392 cuts at 5% is 3.83).
The cuts overlap, so Bonferroni is strict. The neighbouring team-total windows are -2.74% (24h+), -0.63% (6-24h) and +0.71% (1-6h).
Read: the last-hour team-total result is consistent with the last-hour pattern in section 1 (team totals keep 75% of the edge to the
close in the select file), but on its own it is not significant after correcting for the number of cuts.
