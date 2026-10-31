# Does big money on Novig win? (2026-10-30)

Question (Sean): Novig shows the biggest open positions on each MMA fight; has bigger money been profitable?

## What can and cannot be tested

Novig does not publish other users' positions through its API: every positions endpoint (Execution "List positions", History
"List position history") returns the caller's own account only, and the public trade tape (data.novig.com, every executed fill
since 2026-08-03) has no user ids. So the "biggest positions" view cannot be rebuilt or backtested. What can be tested is the size
of each taker fill (the side that crossed the spread to get a bet down), graded against Novig's own settlement.

Code: sharp/novig_bigmoney.py. Output: data/state/novig_bigmoney.json. Pregame fills only, Aug 3 to Oct 28, moneylines.

## Results: moneyline ROI of the taker's bet, by fill size

| League (settled ML markets) | <$100 | $100-500 | $500-1k | $1k-5k | $5k+ |
|---|---|---|---|---|---|
| UFC (174 fights) | +1.3% | +5.3% | -3.6% | -1.6% (1,445 fills) | +18.2% (133 fills, 65 fights, z 1.3) |
| NFL (126 games) | +5.9% | -4.7% | -2.4% | -0.6% | -16.7% (1,217 fills) |
| NBA (109 games) | -1.5% | +0.4% | +4.6% | +6.7% | +9.3% (322 fills) |
| NCAAF (799 games) | -1.0% | -0.6% | -1.7% | +1.0% | -3.2% |
| NHL (208 games) | -1.2% | +0.9% | -3.2% | +0.5% | -8.8% |
| MLB (780 games) | -2.7% | -1.6% | -2.3% | -2.9% | -4.7% |

ROI is dollar-weighted; z is on per-market average ROI (fills inside one fight are not independent). No bucket in any league
clears z 2.

"Follow the side with more $1k+ money" (one bet per market at the last pregame price on the tape): UFC 150 fights, 68.7% winners
against 67.6% implied, +5.2%, z 0.8. NBA +14.4% (97 games, z 1.6), NHL +7.3% (188, z 1.1), NCAAF +3.1% (571, z 0.9), NFL -3.0%,
MLB -2.5% (758, z -0.8).

## Read

1. Bigger is not smarter on Novig. There is no size at which the money reliably wins, and the direction flips by league (UFC and
   NBA big fills positive, NFL and NHL big fills negative). The largest and cleanest sample, MLB (780 games, $152M of fills), is
   negative in every size bucket by about the cost of crossing the spread: what you would expect if big takers are not informed.
2. UFC is the only place the very top bucket looks good (+18% on $5k+ fills), but it is 133 fills on 65 fights over 12 weeks; a
   couple of big favorites or dogs landing decides it. Following the side with the most big money on each fight just matched the
   price (+5%, z 0.8).
3. Three months of data. Every number here is consistent with noise; none is a system.

## What would change the answer

- A record of the positions view itself. If you want to keep checking it, the only route is capturing it by hand (or with the
  browser) before each card; after ~10 cards that is a testable sample of "biggest holder's side vs result".
- More time: the tape keeps growing and this script reruns in a few minutes. Worth rerunning after the next 8-10 UFC cards.
