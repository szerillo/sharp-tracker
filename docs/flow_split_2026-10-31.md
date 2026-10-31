# Big money vs small money on the exchanges (2026-10-31)

Question (Sean, 10/31): Pinnacle may not be the sharpest number, given its limits. On Kalshi and Novig, do the big fills ($250 / $500 / $1,000 and up) carry signal compared with the $1 to $50 fills, roughly a 10x size gap? This is the exchange version of "money % vs ticket %", built from real fill sizes rather than a sportsbook's reported splits.

## Method (sharp/flow_split.py)

- Data:
  - Kalshi: full trade history for game markets (taker side is labelled).
  - Novig: the public trade tape since 2026-08-03 (taker fills), graded on Novig's own settlement.
  - Two-outcome game markets only (moneyline, spread, total). Pregame fills only.
- Entry times: T-6h, T-1h, T-15m. At each entry time, from fills before it:
  - `big_net` = net taker dollars in fills at or above the threshold (250 / 500 / 1000);
  - `small_net` = net taker dollars in fills of $50 or less.
- Signals:
  - **DIV**: big and small money on opposite sides, with |big_net| at or above the threshold. Bet the big side.
  - **BIG**: big money net by at least the threshold, small money ignored. Bet the big side.
- Bets and grading:
  - One bet per game × market type.
  - Entry at the two-sided mid at that time (no fee).
  - Graded on the result (flat 1u ROI) and on CLV (the same side's mid at kickoff minus the entry mid).

## Results ($500 and $1,000 thresholds)

| Venue | Entry | Size | Kind | Games | ROI | z | CLV pts |
|---|---|---|---|---|---|---|---|
| Novig | T-6h | $1,000 | DIV | 1,618 | **+5.2%** | 2.19 | +0.1 |
| Novig | T-6h | $500 | DIV | 1,982 | +2.8% | 1.32 | +0.1 |
| Novig | T-6h | $1,000 | BIG | 2,846 | +1.4% | 0.81 | +0.1 |
| Novig | T-15m | $1,000 | DIV | 2,481 | +2.3% | 1.24 | 0.0 |
| Novig | T-1h | $1,000 | DIV | 2,337 | +1.3% | 0.64 | 0.0 |
| Kalshi | T-15m | $1,000 | DIV | 703 | **+5.6%** | 1.72 | +0.1 |
| Kalshi | T-15m | $500 | DIV | 796 | +2.6% | 0.84 | +0.1 |
| Kalshi | T-1h | $1,000 | DIV | 578 | +1.4% | 0.37 | 0.0 |
| Kalshi | T-6h | $1,000 | DIV | 414 | 0.0% | 0.00 | 0.0 |
| Kalshi | T-15m | $1,000 | BIG | 1,708 | 0.0% | 0.01 | +0.1 |

Full grid (including $250, every entry time and the per-sport split): data/state/flow_split.json.

## Read

1. **Divergence beats raw size.** Following big money alone (BIG) is flat everywhere. The edge, where there is any, is when big and small money disagree. That matches the money% vs ticket% intuition.
2. **$1,000 beats $500, and $500 beats $250.** The bigger the size gap, the better the result.
3. **It is not stable.**
   - Novig T-6h $1k DIV by month: August +12.5%, September +5.5%, October +1.9%.
   - Kalshi T-15m $1k DIV is all October (+8.3%); August and September are about flat.
   - There are 24 cells in the grid, and the best ones are the ones quoted.
4. **CLV is about zero.** The price does not move toward the big side after the signal. If the result edge is real, the market is not pricing it in by kickoff (the same pattern as the CLV-negative winners in the Bet Labs line-move audit). It is also what noise looks like.

Verdict: **tier C, watch only.** It goes on the Today page as a watch list, not into fills, and gets re-checked once a month of live divergent markets has settled.

## Live (sharp/flow_live.py, runs in the tracker workflow)

- Source: every pregame Kalshi taker fill logged by the 5-minute feed (data/kalshi/trades5).
- Per upcoming game × market, on the main line (the line with the most dollars):
  - big = $500+ fills per side; small = $50-and-under fills per side.
- A market is listed when big money is net $1,000+ on one side and small money is net the other way.
- Excluded: soccer moneylines (three-way: a "no" on one team is not a bet on the other).
- Note: the live list uses the backtest's sign test for small money, so a market can be listed with only a few dollars of small money against. A bigger small-money gap is the more meaningful row.
- Output: data/state/flow_live.json, shown on the Today page under "Watch: big money vs small money".

Novig: live trades are now pulled every 5 minutes into data/novig/trades5 (raw: market, outcome, price, quantity, take id). Novig's API does not say whether a trade's outcome is the taker's side. Those rows are therefore checked against Novig's next-day public tape, which labels taker and maker, before `NOVIG_VERIFIED` is switched on and Novig joins the live list.
