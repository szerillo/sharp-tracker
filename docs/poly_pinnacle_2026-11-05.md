# Polymarket sharp accounts re-scored at Pinnacle's close, 11/5/2026

Question (Sean): the live sharp list ranks accounts by CLV against Polymarket's own two-sided close, which the accounts themselves move.
Does ranking them against Pinnacle's closing no-vig price find better accounts, and which combinations of a sharp flag with the wider
market hold up? Script: `sharp/poly_pinnacle.py`; output `data/research/poly_pinnacle.json`.

## Correction (later 11/5)
The first version of this doc was built from an earlier run in which only Polymarket lines exactly equal to Pinnacle's closing number were
priced (1,435 totals, 1,189 spreads); the residual-shift pricing had a syntax error and never ran. Fixed and rerun: 5,731 more totals and
3,781 more spreads priced within 3 points of Pinnacle's number. The tables below are from the corrected run (99,089 held-out fills).
Conclusions did not change direction; the sample is now large enough that they are firm.

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
| top 200 by Polymarket CLV (the live method) | 6,552 | 55 | **+6.8%** (z about 5.5) | +0.35 | 53.8 |
| top 200 by Pinnacle CLV | 7,337 | 44 | +4.7% | +0.29 | 52.7 |
| in both top 200s | 5,718 | 26 | **+7.6%** | +0.36 | 54.1 |
| Pinnacle top 200 only | 1,619 | 18 | -5.8% | +0.06 | 48.0 |
| Polymarket top 200 only | 834 | 29 | +1.2% | +0.27 | 51.8 |
| top 200 by past ROI at the fill | 347 | 32 | **-15.2%** | -0.04 | 41.8 |
| top 50 by past ROI | 85 | 7 | -22.7% | +0.62 | 36.5 |
| top 50 by Polymarket CLV | 180 | 18 | +4.2% | +0.77 | 51.7 |
| every qualified account | 54,334 | 732 | -2.4% | -0.08 | 49.1 |
| bottom 200 by Pinnacle CLV | 212 | 27 | -13.0% | -0.96 | 52.8 |

Verdict: **keep the live method.** Two things settled tonight. (a) Ranking accounts by Pinnacle CLV is not better; the accounts it adds
lose. (b) Ranking accounts by their past ROI, which sounds like the natural fix after "ROI decides", is much worse (-15% out of sample):
past ROI on 30-100 fills is mostly luck, so a ROI ranking selects lucky accounts and they regress. Selection should use CLV (a low-noise
measure of skill); evaluation should use ROI (the thing we are paid in). The live list already does this.

## 3. Combinations on the held-out fills of the Polymarket top 200
| split | fills | ROI at fill | CLV vs Pinnacle |
|---|---|---|---|
| fill WITH Pinnacle's open-to-close move | 2,297 | +8.3% | +1.11 |
| fill AGAINST Pinnacle's move | 1,947 | -0.3% | -0.39 |
| Pinnacle did not move | 2,308 | +11.3% | +0.21 |
| fill inside Pinnacle's fair (price below fair) | 3,563 | +9.3% | +2.29 |
| fill outside Pinnacle's fair | 2,989 | +3.8% | -1.98 |
| inside fair AND with the move | 1,532 | +10.2% | +2.46 |
| outside fair AND against the move | 1,115 | -3.5% | -2.09 |
| favourite side | 3,766 | +7.4% | +0.81 |
| dog side | 2,786 | +6.0% | -0.28 |
| moneyline / spread / total | 1,341 / 2,522 / 2,689 | +7.1% / +6.4% / +7.0% | |
| CFB | 1,497 | +13.1% | +0.65 |
| NBA | 3,188 | +4.7% | +0.12 |
| NFL | 1,447 | +1.2% | +0.43 |
| NHL | 368 | +17.0% | +0.64 |
| NBA totals / NBA sides | 1,330 / 1,858 | +4.6% / +4.7% | |
| NFL sides with the move / against | 486 / 379 | +10.2% / -6.5% | |
| NBA sides with the move / against | 562 / 442 | +5.7% / +12.8% | |
| NHL sides with the move / against | 46 / 31 | +2.4% / +2.5% | |
| inside the last hour / more than 6h out | 1,703 / 3,228 | +7.1% / +5.3% | |

Reading:
- The edge is broad: every market type, favourites and dogs, early and late. It is strongest in CFB and NHL, weakest in NFL.
- "Against Pinnacle's move" is the one split that is flat (-0.3%) rather than positive, and it carries negative CLV. It is not uniformly
  bad (NBA sides against the move were +12.8%), so it is an annotation on the board, not a filter.
- "Inside Pinnacle's fair at the fill" carries the CLV (+2.3 pts) and the better ROI (+9.3% vs +3.8%). That is the one combination worth
  carrying to the live grade: a flag whose Polymarket price is below Pinnacle's fair at the time is the better flag. Implemented next.

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
