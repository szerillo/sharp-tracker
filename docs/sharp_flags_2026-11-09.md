# Polymarket sharp flags: what the live losses are made of (11/9)

The 11/9 checkpoint: sharp flags 72-94, -18.9% ROI, with spreads (-28.7%) and totals (-29.6%) carrying the loss and moneylines near even.
The 11/5 history test had the edge equal across moneylines, spreads and totals (+6-7% each, held out). Data: data/state/sharp_paper.jsonl
(174 flags, 166 graded) joined to data/polymarket/sharp_fills.jsonl (the accounts' own fills).

## 1. Not a follower-price problem
Our flag price against the price-weighted average of the flagging accounts' own fills before the flag:

| Market | Flags | Paid more than the accounts (mean / median) | ROI at our price | ROI at the accounts' price |
|---|---|---|---|---|
| Moneyline | 73 | +1.30 / +0.91 pts | -4.6% | -1.5% |
| Spread | 57 | +1.94 / +1.12 pts | -28.6% | -26.4% |
| Total | 40 | +1.47 / +1.00 pts | -29.6% | -26.7% |

Following costs 1-2 points in every market, which is in line with the history test. The spreads and totals lost at the accounts' own
prices too.

## 2. Alternate-line longshots
Polymarket lists every spread and total line as its own market. One account (0xbc43c8, rank 143, +0.98 CLV, top 50 in the NFL) buys
NFL alternate spreads at 17-30%: Dolphins -3.5 as the underdog at 17%, Jets +3.5 against Kansas City at 30%, Seahawks -10.5 and -13.5.
It was the largest buyer on 20 flagged spread and total bets: 1-19, -18.2u. All live flags by price:

| | Price under 40% | 40-60% | Over 60% |
|---|---|---|---|
| Moneyline | 18, 6-12, +1.6% | 31, 14-17, -12.6% | 22, 16-6, -0.6% |
| Spread | **13, 0-13** (3.2 wins expected) | 38, 18-20, -10.3% | 5, 4-1 |
| Total | 1, 0-1 | 37, 14-23, -25.8% | 1, 0-1 |

The 11/5 history test priced spreads and totals only within 3 points of Pinnacle's number, so these alternate lines were never part of
the evidence for the sharp edge.

## 3. Laddered lines counted as separate bets (fixed)
The same account (and others) buys several adjacent lines of one game: Utah-Dallas over 225.5, 226.5 and 227.5; Washington-Atlanta under
228.5 and 229.5. Each line was logged, graded and sized as its own bet (0.5u each in the tracker). 166 graded flags are 150 distinct
game, market and side bets; 11 games had 2-3 lines logged.

Fixed in sharp/sharp_live.py (a later line of an already-logged game, market and side is not logged; the board row is marked `ladder`),
sharp/bet_log.py (the tracker counts the first line only) and sharp/audit.py (the completeness check matches).

## 4. What is left
One bet per game, market and side, price 40% or higher: **119 flags, 60-59, -10.4%, against 65.7 wins expected** (about 1 standard
deviation short). Moneylines 29-23, spreads 17-15, totals 14-21. Totals are the weak spot (35 bets, about 4 wins short).

## Recommendations (not changed; Sean is giving the sharp rules another week)
- **Price floor 40% for sharp flags**, with flags below it as watch rows. Two sources agree: live (32 flags, 6-26) and the 11/5 history
  (the accounts' dog bets won money but did not beat Pinnacle's close, -0.28, against +0.81 on favourites).
- **Alternate lines more than 3 points from Pinnacle's number: watch only** until tested on the account history.
- Keep reading totals at the next checkpoint.
