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
of the fill, a stale fair makes the fill look like edge that then "decays" by +30m, which is exactly the decay pattern below. So part of
the decay may be measurement, not adverse selection, and part of the edge may not exist.

Test: rerun the select script with the fair limited to a Pinnacle quote taken within 2 minutes (and 5 minutes) before the fill, both
sides from the same pull, and compare edge at fill, +30m and close by market and window against the 30-minute version. Decide the build
only if the last-hour edge at close survives the fresh-fair version. Our 5-minute tape is the limit on how fresh this can be; anything
the 2-minute cut drops for lack of a quote is reported, not filled in.

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
- Fees: Novig charges no pregame fee, so the edge is fair minus our price. Kalshi and ProphetX are not part of this build.

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
