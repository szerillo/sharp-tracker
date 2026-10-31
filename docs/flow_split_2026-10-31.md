# Big money vs small money on the exchanges (2026-10-31)

Question (Sean, 10/31): Pinnacle may not be the sharpest number, given its limits. On Kalshi and Novig, do the big fills ($250 / $500 / $1,000 and up) carry signal compared with the $1 to $50 fills, roughly a 10x size gap? This is the exchange version of "money % vs ticket %", built from real fill sizes rather than a sportsbook's reported splits.

## Method (sharp/flow_split.py)

- Data:
  - Kalshi: full trade history for game markets (taker side is labelled).
  - Novig: the public trade tape since 2026-08-03 (taker fills), graded on Novig's own settlement.
  - Two-outcome game markets only (moneyline, spread, total). Pregame fills only.
- **Fill size = risk-equivalent dollars**: contracts × min(price, 1 − price), so the stake on the dog side and the to-win on the favorite side.
  - Example: $9,000 on a -900 favorite (to win $1,000) counts as $1,000, the same as $1,000 on the +900 dog.
  - At -110 this is about the stake, so $500 / $50 still mean what they say on spreads and totals.
  - Sean's correction on 10/31: the first run used stake dollars, which inflates heavy favorites. Its numbers are kept in data/state/flow_split_stake.json.
- Entry times: T-6h, T-1h, T-15m. At each entry time, from fills before it:
  - `big_net` = net risk-equivalent dollars in fills at or above the threshold (250 / 500 / 1000);
  - `small_net` = the same for fills of $50 or less.
- Signals:
  - **DIV**: big and small money on opposite sides, with |big_net| at or above the threshold. Bet the big side.
  - **BIG**: big money net by at least the threshold, small money ignored. Bet the big side.
- Bets and grading:
  - One bet per game × market type.
  - Entry at the two-sided mid at that time (no fee).
  - Graded on the result (flat 1u ROI) and on CLV (the same side's mid at kickoff minus the entry mid).

## Results (risk-equivalent sizing)

| Venue | Entry | Size | Kind | Games | ROI | z | CLV pts | Stake-dollar run |
|---|---|---|---|---|---|---|---|---|
| Kalshi | T-15m | $250 | DIV | 662 | +7.6% | 1.68 | 0.0 | |
| Kalshi | T-15m | $500 | DIV | 604 | +6.9% | 1.52 | +0.1 | +2.6% |
| Kalshi | T-15m | $1,000 | DIV | 519 | +2.7% | 0.56 | +0.1 | +5.6% |
| Novig | T-6h | $250 | DIV | 2,155 | +3.5% | 1.50 | +0.1 | |
| Novig | T-6h | $500 | DIV | 1,855 | +2.5% | 1.02 | +0.1 | +2.8% |
| Novig | T-6h | $1,000 | DIV | 1,488 | +1.6% | 0.61 | +0.2 | +5.2% (z 2.19) |
| Novig | T-1h / T-15m | any | DIV | 2,100-3,000 | -0.8% to +0.9% | under 0.5 | 0.0 | |
| Kalshi | T-6h | any | DIV | 300-450 | -1.7% to -3.9% | negative | 0.0 | |
| Either | any | any | BIG | | -3.5% to +2.0% | under 1.1 | | |

Full grid (by sport too): data/state/flow_split.json.

## Read

1. **Most of the first run's edge was the favorite effect Sean flagged.** Calibrated, Novig T-6h $1k divergence falls from +5.2% (z 2.2) to +1.6% (z 0.6). Kalshi T-15m $1k falls from +5.6% to +2.7%.
2. **No cell clears z 2.** The best are:
   - Kalshi 15 minutes out, $250-500 against small money: +7%, z 1.5-1.7, about 600 games, mostly NFL and NBA; CFB is negative.
   - Novig 6 hours out, $250: +3.5%, z 1.5.
   That is with 36 cells searched.
3. **Following big money alone (BIG) loses or is flat everywhere.** Divergence remains the only shape with any lift.
4. **CLV is about zero throughout.** The price does not follow the big side by kickoff.

Verdict: **tier C, watch only, no fills.** On the evidence so far, big vs small money on the exchanges is not a bettable signal by itself. It is kept as context next to the rules and re-tested once a month of live divergent markets has settled.

## Live (sharp/flow_live.py, runs in the tracker workflow)

- Source: every pregame Kalshi taker fill logged by the 5-minute feed (data/kalshi/trades5).
- Per upcoming game × market, on the main line (the line with the most dollars):
  - big = $500+ fills per side; small = $50-and-under fills per side, both in risk-equivalent dollars.
- A market is listed when big money is net $1,000+ on one side and small money is net the other way.
- Excluded: soccer moneylines (three-way: a "no" on one team is not a bet on the other).
- Note: the live list uses the backtest's sign test for small money, so a market can be listed with only a few dollars of small money against. A bigger small-money gap is the more meaningful row.
- Output: data/state/flow_live.json, shown on the Today page under "Watch: big money vs small money".

Novig: live trades are now pulled every 5 minutes into data/novig/trades5 (raw: market, outcome, price, quantity, take id). Novig's API does not say whether a trade's outcome is the taker's side. Those rows are therefore checked against Novig's next-day public tape, which labels taker and maker, before `NOVIG_VERIFIED` is switched on and Novig joins the live list.

## Round 2: wider grid, higher bars, train/test split (sharp/flow_grid.py)

Sean asked to raise the bar (3 and 4 points, not just 2) and to try more variations.

### What was tested

9,958 versions across:
- 2 venues × 4 entry times (T-6h, T-3h, T-1h, T-15m);
- six slices: all, moneyline, spread, total, favorite side, dog side.

Signal families:
- **Price move, follow or fade.** Kalshi or Novig mid moved 2 / 3 / 4 / 6+ points over the last 1h, the last 3h, or since the first two-sided price.
- **Big vs small divergence with stricter bars.**
  - big cut $250 / $500 / $1,000 / $2,500;
  - small cut $25 / $50 / $100;
  - big money at least 0 / 50 / 80% one-sided;
  - small money at least 0 / 20 / 40% one-sided the other way.
- **Divergence plus a price move** of 2 / 3 / 4 points, with the move toward the big side or against it.
- **Steam:** the price moved 2 / 3 / 4+ points toward a side that big money is also on.

How each version was judged:
- Each version is found on August-September only (n ≥ 100, z ≥ 2) and then read once on October.
- Grades were run twice: entering at the two-sided mid, and entering at the side's last taker price (the ask) if it printed within 30 minutes.
  - The mid lags a moving price when one side has not traded lately, which flatters follow-the-move signals.
  - The ask run removes that. Its results are in data/research/flow_grid_ask.json.

### Results

**Big vs small money: nothing.**
- Mid entry: 26 train finds against about 78 expected by luck. 14 stayed positive in October, a coin flip.
- Ask entry: 38 finds against about 63 by luck; 20 held.
- Stricter one-sidedness bars and the $2,500 cut did not change that.
- Divergence plus a move "against" the big side (the value case) looked best on train (+20-30%) and lost in October in every version.

**Kalshi follow-the-move since the open: the one live candidate.** Paying the ask, one bet per game × market:

| Move since first price | Entry | Aug (thin) | Sep | Oct |
|---|---|---|---|---|
| 2+ pts | T-1h | n 53, +6.6% | n 346, -0.7% | n 844, +8.4% (z 2.6) |
| 3+ pts | T-1h | n 43, +6.4% | n 284, +0.3% | n 658, +10.1% (z 2.9) |
| 4+ pts | T-1h | n 33, -17.6% | n 215, -0.1% | n 502, +13.4% (z 3.4) |
| 4+ pts | T-15m | n 45, -12.5% | n 236, +3.8% | n 555, +13.3% (z 3.4) |
| 6+ pts | T-15m | n 25, -13.2% | n 159, +1.8% | n 366, +13.9% (z 3.2) |

Fading the same moves loses by about the same amount.

**Raising the bar** from 2 to 3 to 4 points helps in October (+8% → +10% → +13%), and the 1h and 3h windows show the same steady rise, but it does nothing in September. Before Kalshi's fee (about 1.5-2 cents a contract near even money, roughly 3-4% of stake) it fails the train test. After the fee, September is negative.

**Novig moves:** follow and fade are both flat at every bar. The few 6-point cells are 25-55 games.

Verdict: **Kalshi follow-the-move is a forward test, not a system.** It fails the train test and only works in October. That may be a regime change (NBA and NHL returned, NFL volume grew) or one hot month.

It is now live on the Today page, as tier C research: "Watch: Kalshi moved 4+ points since its first price".
- The first price is the first tight two-sided Kalshi price the logger saw, which can be later than the true open.
- Each listed market's result should be graded through November before anything is promoted.
