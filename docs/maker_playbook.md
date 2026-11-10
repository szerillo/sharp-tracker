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
