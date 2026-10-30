# Exchange signal audit, 2026-10-29

**Preliminary draft on partial data (Novig results only back to 10/25, Kalshi NFL partial). Superseded by the full run once the history pulls finish.**

Novig public tape (every taker fill since 2026-08-03) and Kalshi settled sports markets with their full trade tape, aligned to ESPN kickoff times. One row per two-outcome market; 'yes' is the Kalshi ticker outcome or Novig's first listed outcome. Pre-kickoff trades only. Train = first 70% of each sport x venue by date, holdout = last 30%. ROI is per $1 risked at the exchange price, before fees (Kalshi taker fee is about 7% of p(1-p) per contract, 1.75c at 50/50; Novig charges no fee on taker fills today). Nothing here was tuned on the holdout.

Liquidity floor: markets with >= $2,000 and >= 10 pre-kickoff trades (1290 of 2381 markets). Prices are two-sided mids where the last yes-buy and no-buy printed within 2h of each other (close_sides = 2), else the last print. 'Main' = the most-traded strike per game and market type; alt lines are kept but flagged.

## 0. Sample

| venue | sport | markets | main lines | two-sided close | with T-24h price | with T-6h | $ pre-kickoff |
|---|---|---|---|---|---|---|---|
| Kalshi | nfl | 44 | 22 | 44 | 21 | 26 | $18,982,900 |
| Novig | bundesliga | 17 | 13 | 14 | 12 | 16 | $145,403 |
| Novig | cfb | 343 | 95 | 274 | 241 | 313 | $12,650,999 |
| Novig | epl | 21 | 11 | 21 | 17 | 21 | $784,391 |
| Novig | laliga | 20 | 12 | 19 | 17 | 20 | $893,635 |
| Novig | ligue1 | 5 | 4 | 5 | 4 | 5 | $37,560 |
| Novig | mlb | 16 | 6 | 16 | 6 | 16 | $936,158 |
| Novig | mls | 50 | 32 | 44 | 32 | 48 | $734,761 |
| Novig | mma | 7 | 7 | 7 | 7 | 7 | $174,077 |
| Novig | nba | 600 | 144 | 513 | 154 | 560 | $31,669,600 |
| Novig | nfl | 64 | 29 | 52 | 48 | 62 | $1,422,282 |
| Novig | nhl | 62 | 35 | 55 | 29 | 58 | $1,931,175 |
| Novig | seriea | 41 | 23 | 40 | 27 | 40 | $545,958 |

## 1. How good is the exchange price, and when? (calibration)

Brier score and log loss of the last trade before T-24h, T-6h, T-1h and the final pre-kickoff trade, against the result. Lower is better; 0.25 Brier = coin flip. If the close is sharper than T-6h the market learns something in the last hours; the size of that gap is the ceiling for any timing edge.

Main lines only (one market per game x type), so the games are the sample, not the alt strikes.

| venue | sport | n(close) | Brier 24h | Brier 6h | Brier 1h | Brier close | logloss close | n(24h) |
|---|---|---|---|---|---|---|---|---|
| Novig | cfb | 95 | 0.2541 (n=54) | 0.2566 (n=88) | 0.2508 (n=95) | 0.2494 (n=95) | 0.6927 | 54 |
| Novig | nba | 144 | 0.2347 (n=52) | 0.2352 (n=130) | 0.2320 (n=144) | 0.2302 (n=144) | 0.6493 | 52 |

Reliability of the close (all sports, main lines, by venue): bucket = implied probability, hit = how often yes won.

| venue | bucket | n | implied avg | hit rate | gap |
|---|---|---|---|---|---|
| Novig | 0.4-0.5 | 147 | 0.464 | 0.374 | -0.090 |
| Novig | 0.5-0.6 | 182 | 0.530 | 0.478 | -0.052 |

## 2. Structural drift: does one side systematically beat the exchange price?

Buy every yes at the T-24h price (or the close) and hold to settlement, grouped by what yes is. A market with no edge sits near the fee-free break-even of 0%; favorite/dog is defined by the T-24h price. This is the cheapest possible test of market efficiency and the baseline every signal below must beat.

| venue | sport | group | at T-24h: n / ROI / win% | at close: n / ROI / win% | holdout close ROI (n) |
|---|---|---|---|---|---|
| Novig | cfb | over | 53 / -1.6% / 0.491 | 93 / -8.9% / 0.462 | +0.5% (4) |
| Novig | nba | favorite (p>=.5) | 20 / -26.3% / 0.450 | 49 / -21.8% / 0.449 | -28.7% (8) |
| Novig | nba | over | 13 / +9.8% / 0.538 | 54 / -23.5% / 0.389 | -16.5% (9) |
| Novig | nba | underdog (p<.5) | 19 / -61.9% / 0.158 | 41 / -66.9% / 0.146 | -48.5% (9) |

## 3. Momentum vs reversion: does the move from T-6h to the close carry information the close hasn't priced?

Move = close - p(T-6h), in cents. Strategy 'continuation': buy yes at the close when the move was >= +3c, buy no when <= -3c. 'Reversion' is the opposite. The logistic test adds the move to logit(close) and asks whether its coefficient is positive (continuation) or negative (reversion) out of sample.

| venue | sport | n moves >=3c | continuation ROI train / hold (n) | reversion = negative of that | logit coef on move (se) train | holdout logloss: close only vs close+move |
|---|---|---|---|---|---|---|
| Novig | cfb | 28 | +22.1% / n/a (28/0) | reversion | +2.175 (0.927) per 10c | 0.6868 vs 0.7459 (n=4) |
| Novig | nba | 28 | +29.5% / +84.3% (25/3) | reversion | +0.669 (0.734) per 10c | 0.6443 vs 0.5770 (n=26) |

## 4. Late taker flow: follow the money in the last 6h / 2h?

Signed taker dollars (yes buys minus no buys) in the window, as a share of window volume. Strategy: when |flow share| >= 0.3 and window volume >= $500, buy the side the takers bought, at the close. This is the exchange version of 'sharp money', with the advantage that every dollar is real and timestamped.

| venue | sport | lines | window | n | train ROI / win% | holdout ROI / win% (n) | z vs break-even (holdout) |
|---|---|---|---|---|---|---|---|
| Kalshi | nfl | all | 6h | 43 | +8.0% / 0.487 | -19.7% / 0.500 (4) | +0.00 |
| Kalshi | nfl | all | 2h | 43 | +8.0% / 0.487 | -19.7% / 0.500 (4) | +0.00 |
| Novig | cfb | main | 6h | 67 | -1.5% / 0.500 | -35.3% / 0.333 (3) | -0.57 |
| Novig | cfb | main | 2h | 56 | +0.9% / 0.509 | -35.3% / 0.333 (3) | -0.61 |
| Novig | cfb | all | 6h | 233 | +1.7% / 0.511 | -60.3% / 0.200 (10) | -1.76 |
| Novig | cfb | all | 2h | 205 | +3.3% / 0.515 | -43.7% / 0.273 (11) | -1.45 |
| Novig | nba | main | 6h | 72 | -13.9% / 0.456 | -4.4% / 0.467 (15) | -0.02 |
| Novig | nba | main | 2h | 83 | +1.4% / 0.529 | +32.3% / 0.615 (13) | +1.05 |
| Novig | nba | all | 6h | 375 | -2.1% / 0.508 | +33.5% / 0.637 (80) | +2.61 |
| Novig | nba | all | 2h | 358 | +1.6% / 0.527 | +16.5% / 0.561 (66) | +1.35 |
| Novig | nfl | all | 6h | 49 | +13.3% / 0.514 | +13.9% / 0.667 (12) | -0.38 |
| Novig | nfl | all | 2h | 46 | +15.6% / 0.514 | +10.0% / 0.556 (9) | -1.01 |
| Novig | nhl | all | 6h | 41 | -8.9% / 0.467 | +5.2% / 0.636 (11) | +0.16 |
| Novig | nhl | all | 2h | 41 | -0.7% / 0.500 | -24.6% / 0.455 (11) | -1.07 |

## 5. Big trades: is the largest pre-kickoff trade informed?

The single largest trade in the market (top of the top-5% by size). Direction = side the taker bought. 'Continued' = the close moved further in that direction; ROI = buying that side at the big trade's own price and holding to settlement.

| venue | sport | n | median big trade $ | continued to close | ROI at trade price train / hold (n) | win% hold |
|---|---|---|---|---|---|---|
| Novig | cfb | 343 | $3,886 | 40.5% | +2.1% / -26.6% (16) | 0.375 |
| Novig | nba | 600 | $2,722 | 35.0% | -2.7% / +14.8% (137) | 0.547 |
| Novig | nfl | 64 | $2,497 | 37.5% | +16.3% / -1.2% (16) | 0.625 |
| Novig | nhl | 62 | $1,868 | 21.0% | -18.6% / +2.3% (18) | 0.556 |

## 6. Who moves first: Kalshi vs Novig on the same market

Hourly last-trade prices on markets both exchanges list (same game, market, side, line). Corr(dK_t, dN_t-1) > Corr(dN_t, dK_t-1) means Novig leads. Strategy 'follow the leader': when one venue moved >= 3c in hour t and the other moved < 1c, buy the laggard toward the leader's direction at the laggard's price; graded against the laggard's own close (CLV, in cents) and against the result.

Not enough overlapping markets yet (Kalshi pull still running or sports not yet aligned).

## 7. Timing: which hours' moves stick?

For every hourly move of >= 2c, did the close end up on the same side of the post-move price (the move 'stuck') or come back? Grouped by ET hour of day and by hours-to-kickoff. Sharp moves should stick; public moves should mean-revert. Share > 50% with n in the hundreds is a real timing signal.

| venue | ET hour bucket | n moves | stuck share | avg |move| c |
|---|---|---|---|---|
| Novig | 0-5am | 1095 | 34.9% | 10.9 |
| Novig | 6-9am | 1132 | 33.7% | 9.5 |
| Novig | 10am-1pm | 1688 | 35.5% | 9.5 |
| Novig | 2-5pm | 1566 | 36.5% | 9.1 |
| Novig | 6-9pm | 1257 | 31.6% | 8.9 |
| Novig | 10pm-12 | 404 | 37.9% | 10.5 |

| venue | hours to kickoff | n moves | stuck share |
|---|---|---|---|
| Kalshi | 3d+ | 170 | 38.2% |
| Novig | <1h | 1254 | 29.3% |
| Novig | 1-3h | 816 | 33.1% |
| Novig | 3-6h | 899 | 35.4% |
| Novig | 6-12h | 1200 | 34.3% |
| Novig | 12-24h | 1138 | 38.4% |
| Novig | 1-3d | 1159 | 37.0% |
| Novig | 3d+ | 676 | 37.0% |

## 8. Does volume make the close sharper?

| venue | sport | volume tercile | n | Brier close | ROI buying favorite at close |
|---|---|---|---|---|---|
| Novig | cfb | low (median $4,898) | 32 | 0.2450 | +5.8% |
| Novig | cfb | mid (median $25,097) | 31 | 0.2404 | +7.3% |
| Novig | cfb | high (median $136,368) | 32 | 0.2627 | -3.7% |
| Novig | nba | low (median $8,908) | 48 | 0.2331 | -8.7% |
| Novig | nba | mid (median $92,648) | 48 | 0.2447 | +6.8% |
| Novig | nba | high (median $267,401) | 48 | 0.2127 | +5.2% |

## 9. Reading it

A signal survives only if (a) the holdout ROI is positive and the holdout z is above about 2, (b) train and holdout agree in sign, and (c) the effect is monotone where it should be (bigger flow / bigger move / bigger trade = bigger edge). Anything that passes goes into sharp/systems.py as a forward paper test with its own tag, same as the Bet Labs systems. Nothing in this document is a bet recommendation on its own.
