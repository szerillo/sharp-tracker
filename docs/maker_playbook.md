# Resting offers: the playbook (11/10)

What the tests support, where the live list is, and what has to be true before money goes in. Sources: docs/maker_2026-11-10.md
(11 days, Kalshi and Novig game lines against Pinnacle) and docs/overnight_2026-11-10.md sections 1, 5 and 8 (Kalshi makers over two
months, Novig makers over three months, Novig maker fills against Pinnacle at the fill in every market type).

## Where the offers are
The board's "Offers to rest" section (sharp/offers_live.py, every 10 minutes): each side where a bid under Pinnacle's fair price would be
first in line, with the price to rest and what is kept after fees. Paper only. Its record (sharp/offers_grade.py) shows how many would
have filled inside an hour, counted at $100 a fill, and how filled and unfilled offers closed against Pinnacle.

## The rules the data supports

| Venue | Market | Bid | When | Evidence (kept at the close) |
|---|---|---|---|---|
| Novig | Spreads, totals | 1c under Pinnacle's fair | inside 24 hours | +0.84c / +0.71c; 2c bids +1.8c / +1.5c |
| Novig | Team totals, period lines | 1 to 2c under | inside 24 hours | +0.6c to +0.9c at 1c; thin ($20-35k a day filled) |
| Novig | Player props | 2c under (1c in the last hour) | inside 24 hours | +0.70c at 2c, +1.31c at 3c; 1c only holds in the last hour |
| Novig | Moneylines | 1c under | last hour only | +0.86c in the last hour; negative earlier |
| ProphetX | Props (softest), game and first-half lines | 2c under | inside 24 hours | no fill history yet; books sit 1.8 to 2.9c under fair on props; 2% of net profit per market |
| Kalshi | anything | 2c under | inside 24 hours | tracking only: makers lost 1.4% after the maker fee over two months |

Do not: rest moneylines early; rest props at 1c outside the last hour; leave a bid up after Pinnacle moves (reprice or pull); treat a
fill 3c+ under fair on Kalshi or on a moneyline as a gift (those fills lost).

## Size and risk
- The edge is about 1% of the money put up, per fill. Fills are not hedged: over 11 days Novig's makers won 5% and Kalshi's lost 5% on
  the same slate. Daily swings will be many times the expected profit.
- Start size: $50 to $100 a bid, no more than 0.25u ($125) at risk on one game side, in line with the board's cap.
- The whole pool for everyone resting 1c under fair on Novig in the last hour is about $15,000 a day. A new, small maker gets a small
  share of it.

## Before money
1. A week of the paper record: fill rate inside an hour above ~10%, and filled offers closing at or above the offer price against Pinnacle.
2. ProphetX: matched volume on the markets we would quote (logged from 11/10), and its real maker fee from Sean's account.
3. Orders are placed by Sean (or by a tool he runs on his own keys). Nothing in this repo places an order.

## What is not known
- Queue position: when our bid only matches the best bid we are behind whoever was there first. The scan lists only bids that improve
  the best bid, so this bites when someone improves over us.
- Who the other makers are and how fast they reprice. Our Pinnacle reading is up to 20 minutes old on the 10-minute tape.
- Settled results for a small maker. All of the above is closing-line value and the all-makers average.

## Parlays on Kalshi (11/10, sharp/kalshi_parlays.py, data/research/kalshi_parlays.json)

Sean 11/10: "think offering parlays even more lucrative". Kalshi lists every parlay as a settled public market with its legs, so the
makers can be scored. Sample: for each hour from Oct 27 to Nov 10, the first 2,000 parlays settled in that hour (664,000 markets,
435,098 with trades). The taker is scored as the YES side at the last price (a trade check had the taker on YES 93 of 106 times, and
44 of 60 sampled parlays had a single trade).

| Group | Parlays | Takers paid | Makers kept | % of taker stakes | % of maker money | z (by day) |
|---|---|---|---|---|---|---|
| All | 435,098 | $35.7M | -$291,507 | -0.8% | -0.15% | -0.2 |
| 2 legs | 44,626 | $9.6M | $1,564,910 | 16.3% | 7.1% | 3.7 |
| 3 legs | 55,337 | $7.4M | $474,386 | 6.4% | 2.1% | 2.3 |
| 4-5 legs | 95,308 | $8.0M | $2,789 | 0.0% | 0.0% | 0.0 |
| 6+ legs | 239,827 | $10.8M | -$2,333,592 | -21.7% | -2.0% | -2.5 |
| Priced 50c and up | 50,111 | $20.5M | -$1,139,783 | -5.6% | -25.1% | -3.6 |
| Priced 30-50c | 44,611 | $5.1M | $439,470 | 8.7% | 5.6% | 1.5 |
| Same game | 4,605 | $0.5M | $110,813 | 20.9% | 3.1% | 1.9 |
| Two games | 48,141 | $9.7M | $1,472,307 | 15.2% | 6.2% | 3.3 |
| Three or more games | 382,352 | $25.5M | -$1,874,627 | -7.4% | -1.1% | -1.5 |

Read: makers as a group broke even over 15 days; the single day first looked at (11/10, +21.1%) was a good day. The money is in short
parlays: two legs kept 16.3% of stakes and was positive in every sport sampled (NFL 50.1%, tennis 21.0%, NBA 15.7%, CFB 10.2%,
soccer 8.2%, NHL 7.0%); three legs kept 6.4%. Long parlays (6+ legs) and heavy favorites (50c and up) lost. NBA parlays of 4+ legs
lost 52.6% of stakes over 14 days.
Limits: 15 days; the last price stands in for each fill; the 50c-and-up loss may be partly takers on the NO side; each hour is capped
at 2,000 parlays. Not compared with Pinnacle leg prices yet, so this is what makers earned, not what a Pinnacle-priced quote would earn.

### Older sample, Sept 25 to Oct 26 (data/research/kalshi_parlays_older.json; one page of 1,000 parlays per hour, 32 days)

| Group | Parlays | Takers paid | Makers kept | % of taker stakes | z (by day) |
|---|---|---|---|---|---|
| All | 584,635 | $50.4M | -$161,983 | -0.3% | -0.1 |
| 2 legs | 64,170 | $15.2M | $539,868 | 3.6% | 1.2 |
| 3 legs | 78,236 | $9.7M | $508,824 | 5.2% | 2.3 |
| 4-5 legs | 137,038 | $11.4M | $368,730 | 3.2% | 0.9 |
| 6+ legs | 305,191 | $14.2M | -$1,579,405 | -11.2% | -1.8 |
| Priced 50c and up | 69,041 | $29.1M | -$2,129,738 | -7.3% | -4.2 |
| Same game | 4,671 | $0.5M | -$36,043 | -7.1% | -0.8 |

Read: the two-leg 16.3% from Oct 27 to Nov 10 did not repeat (3.6% here). Across both samples (47 days) two- and three-leg parlays
kept makers a few percent of stakes, in line with the roughly 2% markup over the legs seen on the live log, and makers as a whole
broke even. What repeats in both samples is the losing side: parlays of 6+ legs and parlays priced 50c and up cost makers money.
Parlays are not clearly richer than Novig straights (1.9%) once the bad two weeks of luck are averaged out, and they swing far more.
