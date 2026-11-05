# Polymarket sharp accounts re-scored at Pinnacle's close, 11/5/2026

Question (Sean): the live sharp list ranks accounts by CLV against Polymarket's own two-sided close, which the accounts themselves move.
Does ranking them against Pinnacle's closing no-vig price find better accounts, and which combinations of a sharp flag with the wider
market hold up? Script: `sharp/poly_pinnacle.py`; output `data/research/poly_pinnacle.json`.

## Method
- 36,513 settled Polymarket game markets with a trade file (2024-06 to 2026-11). Each is matched to the Odds API database by sport, start
  (within 3 hours) and team or fighter names (outcomes for sides, the "A vs. B" title for totals and fighters). Matched: NBA 11,490, NFL 4,084,
  CFB 3,272, NHL 3,826, CBB 882, MLB 1,970, UFC 265. Unmatched are mostly 2026 MLB and WNBA (our tables stop at the 2025 season) and soccer.
- Fair price at Pinnacle's close: moneylines from the two closing prices (no-vig). Spreads and totals at Pinnacle's own number from the two
  closing prices; at a Polymarket line up to 3 points off Pinnacle's close, Pinnacle's close shifted along the sport's empirical residual
  distribution (actual total minus closing total; margin against the closing spread, pooled with its mirror). Scored: 8,266 ML, 1,189 spread,
  1,435 total markets.
- Accounts: $100+ risk-equivalent pregame fills, 30+ fills on 15+ games in the first two thirds of the history (to 2026-06-11); 2,680 qualify.
  Held out: the last third (June to November 2026, 53,593 fills). ROI is at the account's own fill price; CLV in probability points.

## 1. Do the two rankings agree?
Spearman 0.75; 129 of 200 accounts shared between the two top-200 lists. Mean CLV of the qualified pool is slightly negative by both
yardsticks (-0.4 pts), so the pool as a whole is not sharp; the ranking is doing the work.

## 2. Out of sample: following the top 200 (June-November 2026)
| list | fills | accounts active | ROI at fill | CLV vs Pinnacle | win% |
|---|---|---|---|---|---|
| top 200 by Polymarket CLV (the live method) | 2,523 | 48 | **+6.6%** | +0.36 | 53.1 |
| top 200 by Pinnacle CLV | 2,314 | 39 | +4.3% | +0.30 | 52.4 |
| in both top 200s | 2,117 | 28 | **+6.8%** | +0.38 | 53.4 |
| Pinnacle top 200 only | 197 | 11 | -23.2% | -0.50 | 41.6 |
| Polymarket top 200 only | 406 | 20 | +5.0% | +0.27 | 51.2 |
| top 50 by either | ~230 | ~16 | -7 to -10% | +0.4 to +0.8 | 46-48 |
| every qualified account | 25,365 | 543 | -4.7% | 0.0 | 47.7 |
| bottom 200 by Pinnacle CLV | 185 | 27 | -13.7% | -1.04 | 54.6 |

Verdict: the Pinnacle yardstick does not find better accounts. The accounts it adds that the Polymarket ranking does not have lose
heavily; the accounts both lists share carry the result. **Keep the live method.** Being in both lists is a mild extra filter (+6.8% vs +6.6%,
same accounts for the most part); not worth a code change. The top 50 is worse than the top 200 by either yardstick (thin, n about 230),
so do not tighten the list.

The first pass of this test, before totals were matched, had both lists negative out of sample (-7% and -4%). Totals are where the
held-out edge is (next section); a list test without totals is a test of the wrong markets.

## 3. Combinations on the held-out fills of the Polymarket top 200
| split | fills | ROI at fill | CLV vs Pinnacle |
|---|---|---|---|
| fill WITH Pinnacle's open-to-close move | 760 | +5.5% | +1.34 |
| fill AGAINST Pinnacle's move | 669 | **-8.4%** | -0.56 |
| Pinnacle did not move | 1,094 | +16.4% | +0.24 |
| fill already inside Pinnacle's fair (price below fair) | 1,371 | +7.1% | +2.14 |
| fill outside Pinnacle's fair | 1,152 | +5.9% | -1.75 |
| favourite side | 1,428 | +5.0% | +0.32 |
| dog side | 1,095 | +8.5% | +0.41 |
| inside fair AND with the move | 519 | +5.7% | +2.49 |
| outside fair AND against the move | 408 | **-8.0%** | -2.01 |
| moneyline | 1,460 | +5.9% | +0.47 |
| spread | 596 | -0.5% | +0.41 |
| total | 467 | **+17.6%** | -0.05 |
| CFB | 596 | +13.5% | +0.53 |
| NBA | 955 | -2.0% | +0.16 |
| NFL | 564 | -0.4% | +0.54 |
| NHL | 362 | +19.1% | +0.10 |
| UFC | 46 | +80% (thin) | +2.17 |
| inside the last hour before start | 689 | +5.8% | +0.21 |
| more than 6 hours out | 1,303 | +1.2% | +0.56 |

The Pinnacle top 200 shows the same pattern (against the move -12.8%, no move +16.8%, totals +20.0%, NHL +24.5%, NBA -2.0%).

Reading:
- The one clean negative is **a sharp fill against the direction Pinnacle moved** (-8 to -13% both lists, both ways of ranking). The
  "with the move" side is positive and carries the CLV. "No move" is the best bucket at fill price but its CLV is flat; those are mostly thin
  markets where Pinnacle did not move at all, so the ROI there is noisier than it looks.
- Totals and NHL carry the held-out ROI; NBA and NFL sides are flat at fill price even though their CLV is positive. At the prices we get
  after the flag (the tracker's own grading), a flat-at-fill market is a loser, so NBA/NFL sharp sides should stay watch-weight unless a
  system or the market move also agrees.
- Price already inside Pinnacle's fair at the fill is where the CLV sits (+2.1 pts), but it does not separate ROI (+7.1 vs +5.9). CLV
  without ROI on 1,152 fills is a reminder that Pinnacle's close is not the whole truth on these markets.

## What changed in the tool
- `sharp/bet_log.py`: every bet now carries `move_at_flag` = Pinnacle's (or the consensus line's) move from our first tape point to the
  flag, toward or against the side taken (points of no-vig probability for moneylines, number for spreads and totals; puck and run lines
  excluded). The tracker shows "Market had moved toward / against this side before the flag" on each bet, with a filter "Flagged against
  the market move". This is the live version of the one split that lost out of sample; it is an annotation, not a rule, until the
  tracker's own bets confirm it at our prices.
- The live list method (CLV vs Polymarket's close, top 200) is unchanged: it beat the alternative.

## Not done / caveats
- MLB and WNBA 2026 markets are unmatched until the odds tables cover 2026 (credits). Soccer is unmatched (3-way markets, partial tables).
- "ROI at fill" is the account's price, not ours. The tracker's own `clv`/`clv_nv` on sharp rows remains the test that matters for the board.
- The residual-shift pricing for off-number lines is an approximation (the shift uses the sport's whole-history residuals, not the game's).
