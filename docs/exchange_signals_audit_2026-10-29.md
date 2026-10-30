# Exchange signal audit, 2026-10-29

Novig public tape (every taker fill since 2026-08-03) and Kalshi settled sports markets with their full trade tape, aligned to ESPN kickoff times. One row per two-outcome market; 'yes' is the Kalshi ticker outcome or Novig's first listed outcome. Pre-kickoff trades only. Train = first 70% of each sport x venue by date, holdout = last 30%. ROI is per $1 risked at the exchange price, before fees (Kalshi taker fee is about 7% of p(1-p) per contract, 1.75c at 50/50; Novig charges no fee on taker fills today). Nothing here was tuned on the holdout.

Liquidity floor: markets with >= $2,000 and >= 10 pre-kickoff trades (23033 of 47169 markets). Prices are two-sided mids where the last yes-buy and no-buy printed within 2h of each other (close_sides = 2), else the last print. 'Main' = the most-traded strike per game and market type; alt lines are kept but flagged.

## 0. Sample

| venue | sport | markets | main lines | two-sided close | with T-24h price | with T-6h | $ pre-kickoff |
|---|---|---|---|---|---|---|---|
| Kalshi | bundesliga | 36 | 20 | 33 | 36 | 36 | $774,034 |
| Kalshi | cfb | 867 | 440 | 742 | 835 | 849 | $85,171,227 |
| Kalshi | epl | 117 | 39 | 116 | 116 | 117 | $13,442,234 |
| Kalshi | laliga | 136 | 48 | 134 | 121 | 131 | $24,794,556 |
| Kalshi | ligue1 | 21 | 11 | 19 | 21 | 21 | $855,361 |
| Kalshi | mls | 295 | 135 | 291 | 295 | 295 | $9,216,706 |
| Kalshi | nba | 1769 | 560 | 1598 | 636 | 1613 | $57,440,508 |
| Kalshi | nfl | 4611 | 713 | 4215 | 4207 | 4444 | $297,473,454 |
| Kalshi | nhl | 1119 | 625 | 1014 | 885 | 1104 | $25,048,513 |
| Kalshi | seriea | 133 | 50 | 127 | 133 | 133 | $7,936,152 |
| Kalshi | ucl | 42 | 14 | 42 | 35 | 40 | $9,612,307 |
| Novig | bundesliga | 115 | 82 | 100 | 78 | 112 | $1,293,441 |
| Novig | cfb | 2820 | 816 | 2160 | 2094 | 2626 | $82,002,154 |
| Novig | epl | 266 | 139 | 252 | 238 | 263 | $7,767,576 |
| Novig | laliga | 246 | 160 | 230 | 175 | 241 | $5,442,265 |
| Novig | ligue1 | 114 | 87 | 100 | 63 | 111 | $1,262,738 |
| Novig | mlb | 5158 | 2938 | 4706 | 827 | 4857 | $283,740,764 |
| Novig | mls | 437 | 299 | 367 | 352 | 430 | $6,859,017 |
| Novig | mma | 131 | 122 | 129 | 106 | 125 | $2,607,920 |
| Novig | nba | 1408 | 423 | 1187 | 235 | 1255 | $58,436,593 |
| Novig | nfl | 2458 | 688 | 2112 | 2018 | 2368 | $239,818,151 |
| Novig | nhl | 363 | 199 | 330 | 154 | 354 | $9,592,809 |
| Novig | seriea | 212 | 141 | 198 | 131 | 207 | $2,883,706 |
| Novig | ucl | 159 | 82 | 143 | 100 | 158 | $3,870,592 |

## 1. How good is the exchange price, and when? (calibration)

Brier score and log loss of the last trade before T-24h, T-6h, T-1h and the final pre-kickoff trade, against the result. Lower is better; 0.25 Brier = coin flip. If the close is sharper than T-6h the market learns something in the last hours; the size of that gap is the ceiling for any timing edge.

Main lines only (one market per game x type), so the games are the sample, not the alt strikes.

| venue | sport | n(close) | Brier 24h | Brier 6h | Brier 1h | Brier close | logloss close | n(24h) |
|---|---|---|---|---|---|---|---|---|
| Kalshi | cfb | 440 | 0.1379 (n=423) | 0.1380 (n=433) | 0.1385 (n=439) | 0.1387 (n=440) | 0.4189 | 423 |
| Kalshi | laliga | 48 | 0.2074 (n=40) | 0.1945 (n=46) | 0.1997 (n=48) | 0.1996 (n=48) | 0.5845 | 40 |
| Kalshi | mls | 135 | 0.2301 (n=135) | 0.2299 (n=135) | 0.2302 (n=135) | 0.2262 (n=135) | 0.6442 | 135 |
| Kalshi | nba | 560 | 0.2317 (n=198) | 0.2442 (n=509) | 0.2429 (n=549) | 0.2390 (n=560) | 0.6695 | 198 |
| Kalshi | nfl | 713 | 0.2431 (n=603) | 0.2427 (n=644) | 0.2415 (n=686) | 0.2414 (n=713) | 0.6754 | 603 |
| Kalshi | nhl | 625 | 0.2400 (n=527) | 0.2364 (n=617) | 0.2351 (n=625) | 0.2347 (n=625) | 0.6615 | 527 |
| Kalshi | seriea | 50 | 0.2066 (n=50) | 0.2083 (n=50) | 0.2087 (n=50) | 0.2029 (n=50) | 0.5902 | 50 |
| Novig | bundesliga | 82 | 0.2367 (n=56) | 0.2486 (n=80) | 0.2528 (n=80) | 0.2511 (n=82) | 0.6972 | 56 |
| Novig | cfb | 816 | 0.2497 (n=604) | 0.2493 (n=767) | 0.2486 (n=811) | 0.2481 (n=816) | 0.6892 | 604 |
| Novig | epl | 139 | 0.2327 (n=128) | 0.2283 (n=138) | 0.2291 (n=139) | 0.2287 (n=139) | 0.6479 | 128 |
| Novig | laliga | 160 | 0.2115 (n=119) | 0.2146 (n=157) | 0.2156 (n=159) | 0.2127 (n=160) | 0.6112 | 119 |
| Novig | ligue1 | 87 | 0.2121 (n=48) | 0.2295 (n=85) | 0.2304 (n=87) | 0.2254 (n=87) | 0.6402 | 48 |
| Novig | mlb | 2938 | 0.2382 (n=582) | 0.2425 (n=2809) | 0.2427 (n=2936) | 0.2429 (n=2938) | 0.6788 | 582 |
| Novig | mls | 299 | 0.2466 (n=244) | 0.2332 (n=297) | 0.2321 (n=299) | 0.2304 (n=299) | 0.6529 | 244 |
| Novig | mma | 122 | 0.2387 (n=101) | 0.2377 (n=117) | 0.2416 (n=122) | 0.2406 (n=122) | 0.6739 | 101 |
| Novig | nba | 423 | 0.2375 (n=87) | 0.2384 (n=380) | 0.2347 (n=420) | 0.2337 (n=423) | 0.6584 | 87 |
| Novig | nfl | 688 | 0.2485 (n=546) | 0.2464 (n=652) | 0.2449 (n=686) | 0.2448 (n=688) | 0.6819 | 546 |
| Novig | nhl | 199 | 0.2494 (n=105) | 0.2512 (n=199) | 0.2508 (n=199) | 0.2511 (n=199) | 0.6954 | 105 |
| Novig | seriea | 141 | 0.2171 (n=86) | 0.2213 (n=139) | 0.2234 (n=140) | 0.2242 (n=141) | 0.6393 | 86 |
| Novig | ucl | 82 | 0.2348 (n=63) | 0.2336 (n=82) | 0.2308 (n=82) | 0.2317 (n=82) | 0.6547 | 63 |

Reliability of the close (all sports, main lines, by venue): bucket = implied probability, hit = how often yes won.

| venue | bucket | n | implied avg | hit rate | gap |
|---|---|---|---|---|---|
| Kalshi | 0.0-0.1 | 49 | 0.024 | 0.000 | -0.024 |
| Kalshi | 0.1-0.2 | 31 | 0.159 | 0.097 | -0.062 |
| Kalshi | 0.2-0.3 | 83 | 0.262 | 0.301 | +0.039 |
| Kalshi | 0.3-0.4 | 220 | 0.352 | 0.323 | -0.029 |
| Kalshi | 0.4-0.5 | 785 | 0.463 | 0.437 | -0.026 |
| Kalshi | 0.5-0.6 | 901 | 0.537 | 0.534 | -0.003 |
| Kalshi | 0.6-0.7 | 253 | 0.646 | 0.668 | +0.022 |
| Kalshi | 0.7-0.8 | 143 | 0.745 | 0.748 | +0.003 |
| Kalshi | 0.8-0.9 | 83 | 0.841 | 0.843 | +0.003 |
| Kalshi | 0.9-1.0 | 107 | 0.955 | 0.963 | +0.008 |
| Novig | 0.1-0.2 | 29 | 0.145 | 0.241 | +0.096 |
| Novig | 0.2-0.3 | 77 | 0.259 | 0.221 | -0.039 |
| Novig | 0.3-0.4 | 429 | 0.363 | 0.336 | -0.027 |
| Novig | 0.4-0.5 | 2418 | 0.462 | 0.460 | -0.002 |
| Novig | 0.5-0.6 | 2511 | 0.536 | 0.532 | -0.004 |
| Novig | 0.6-0.7 | 547 | 0.635 | 0.634 | -0.001 |
| Novig | 0.7-0.8 | 114 | 0.737 | 0.763 | +0.026 |
| Novig | 0.8-0.9 | 35 | 0.826 | 0.800 | -0.026 |

## 2. Structural drift: does one side systematically beat the exchange price?

Buy every yes at the T-24h price (or the close) and hold to settlement, grouped by what yes is. A market with no edge sits near the fee-free break-even of 0%; favorite/dog is defined by the T-24h price. This is the cheapest possible test of market efficiency and the baseline every signal below must beat.

| venue | sport | group | at T-24h: n / ROI / win% | at close: n / ROI / win% | holdout close ROI (n) |
|---|---|---|---|---|---|
| Kalshi | cfb | favorite (p>=.5) | 298 / -0.3% / 0.789 | 309 / +0.5% / 0.786 | -4.2% (63) |
| Kalshi | cfb | underdog (p<.5) | 125 / -34.7% / 0.216 | 131 / -36.6% / 0.206 | +19.3% (37) |
| Kalshi | mls | favorite (p>=.5) | 59 / -3.1% / 0.576 | 59 / -4.0% / 0.576 | -15.2% (21) |
| Kalshi | mls | underdog (p<.5) | 76 / -27.7% / 0.303 | 76 / -29.1% / 0.303 | -25.7% (23) |
| Kalshi | nba | favorite (p>=.5) | 98 / -9.6% / 0.582 | 197 / -14.2% / 0.508 | -0.4% (47) |
| Kalshi | nba | over | 28 / -22.1% / 0.393 | 192 / -4.2% / 0.495 | -4.8% (48) |
| Kalshi | nba | underdog (p<.5) | 72 / +16.9% / 0.486 | 171 / -3.4% / 0.439 | +5.8% (36) |
| Kalshi | nfl | favorite (p>=.5) | 227 / +3.1% / 0.590 | 293 / -0.6% / 0.577 | +4.1% (72) |
| Kalshi | nfl | over | 220 / -2.9% / 0.486 | 237 / -2.4% / 0.494 | -3.2% (59) |
| Kalshi | nfl | underdog (p<.5) | 156 / -6.5% / 0.429 | 183 / -4.4% / 0.432 | -20.2% (46) |
| Kalshi | nhl | favorite (p>=.5) | 180 / +5.2% / 0.622 | 183 / +7.8% / 0.623 | +0.2% (41) |
| Kalshi | nhl | over | 147 / +4.2% / 0.524 | 209 / -3.5% / 0.502 | +9.0% (63) |
| Kalshi | nhl | underdog (p<.5) | 200 / +18.3% / 0.445 | 233 / +9.2% / 0.421 | -1.1% (76) |
| Novig | bundesliga | over | 24 / +32.2% / 0.667 | 42 / +9.7% / 0.548 | -5.4% (10) |
| Novig | cfb | over | 601 / +1.0% / 0.501 | 812 / -1.0% / 0.496 | -12.3% (136) |
| Novig | epl | over | 58 / -10.8% / 0.483 | 69 / -15.7% / 0.464 | -17.9% (20) |
| Novig | laliga | over | 44 / -0.5% / 0.500 | 76 / -1.8% / 0.526 | -22.0% (21) |
| Novig | laliga | underdog (p<.5) | 40 / -4.9% / 0.375 | 48 / +8.7% / 0.417 | -29.8% (15) |
| Novig | ligue1 | over | 13 / -43.4% / 0.308 | 42 / -22.3% / 0.405 | -10.5% (13) |
| Novig | mlb | favorite (p>=.5) | 248 / +0.8% / 0.593 | 1031 / +0.3% / 0.583 | +3.3% (241) |
| Novig | mlb | over | 150 / -12.1% / 0.440 | 1106 / +5.6% / 0.520 | +1.8% (285) |
| Novig | mlb | underdog (p<.5) | 184 / -4.8% / 0.408 | 801 / +3.5% / 0.439 | -0.8% (186) |
| Novig | mls | favorite (p>=.5) | 71 / -12.4% / 0.507 | 75 / -10.5% / 0.520 | -20.0% (18) |
| Novig | mls | over | 89 / +8.0% / 0.551 | 127 / +3.5% / 0.543 | +7.1% (33) |
| Novig | mls | underdog (p<.5) | 84 / +11.3% / 0.429 | 97 / -6.3% / 0.371 | -13.0% (24) |
| Novig | mma | over | 101 / -6.9% / 0.485 | 122 / -5.0% / 0.492 | -22.0% (37) |
| Novig | nba | favorite (p>=.5) | 38 / -15.1% / 0.526 | 158 / -13.7% / 0.513 | -5.4% (40) |
| Novig | nba | over | 19 / +25.9% / 0.632 | 154 / -6.2% / 0.487 | +4.0% (33) |
| Novig | nba | underdog (p<.5) | 30 / -23.6% / 0.333 | 111 / -28.6% / 0.297 | -37.6% (18) |
| Novig | nfl | favorite (p>=.5) | 199 / -16.5% / 0.487 | 243 / -16.0% / 0.490 | -14.6% (47) |
| Novig | nfl | over | 179 / +4.2% / 0.514 | 231 / -4.6% / 0.481 | +3.6% (54) |
| Novig | nfl | underdog (p<.5) | 168 / -10.6% / 0.393 | 214 / -11.8% / 0.388 | -38.0% (55) |
| Novig | nhl | over | 105 / +14.7% / 0.571 | 199 / +1.8% / 0.508 | +8.7% (57) |
| Novig | seriea | over | 33 / -13.1% / 0.455 | 72 / +3.9% / 0.514 | +6.7% (19) |
| Novig | ucl | over | 26 / +29.0% / 0.615 | 41 / +28.0% / 0.610 | +81.5% (9) |

## 3. Momentum vs reversion: does the move from T-6h to the close carry information the close hasn't priced?

Move = close - p(T-6h), in cents. Strategy 'continuation': buy yes at the close when the move was >= +3c, buy no when <= -3c. 'Reversion' is the opposite. The logistic test adds the move to logit(close) and asks whether its coefficient is positive (continuation) or negative (reversion) out of sample.

| venue | sport | n moves >=3c | continuation ROI train / hold (n) | reversion = negative of that | logit coef on move (se) train | holdout logloss: close only vs close+move |
|---|---|---|---|---|---|---|
| Kalshi | cfb | 23 | +19.6% / -30.6% (13/10) | reversion | +0.463 (1.033) per 10c | 0.6120 vs 0.6377 (n=100) |
| Kalshi | mls | 42 | +19.2% / -4.7% (27/15) | reversion | +1.317 (0.810) per 10c | 0.6678 vs 0.6935 (n=44) |
| Kalshi | nba | 170 | +19.7% / +22.9% (132/38) | reversion | +0.357 (0.237) per 10c | 0.6653 vs 0.6690 (n=127) |
| Kalshi | nfl | 83 | +26.9% / -38.9% (67/16) | reversion | +0.739 (0.462) per 10c | 0.6927 vs 0.7046 (n=158) |
| Kalshi | nhl | 25 | -15.3% / +88.9% (19/6) | reversion | +0.843 (0.729) per 10c | 0.6644 vs 0.6615 (n=178) |
| Novig | bundesliga | 18 | -32.0% / +13.0% (16/2) | reversion | -1.462 (1.205) per 10c | 0.7126 vs 0.7133 (n=20) |
| Novig | cfb | 191 | -4.4% / +29.2% (153/38) | reversion | -0.293 (0.355) per 10c | 0.6882 vs 0.6985 (n=129) |
| Novig | epl | 33 | +0.2% / -8.0% (20/13) | reversion | +0.391 (0.945) per 10c | 0.6427 vs 0.6335 (n=39) |
| Novig | laliga | 36 | -2.5% / -8.5% (24/12) | reversion | -0.110 (0.794) per 10c | 0.5847 vs 0.5761 (n=45) |
| Novig | ligue1 | 27 | +19.1% / +26.9% (20/7) | reversion | +1.541 (1.104) per 10c | 0.5929 vs 0.5383 (n=26) |
| Novig | mlb | 286 | +10.8% / -3.8% (205/81) | reversion | -0.089 (0.243) per 10c | 0.6825 vs 0.6835 (n=678) |
| Novig | mls | 65 | +6.8% / +1.0% (49/16) | reversion | +0.401 (0.565) per 10c | 0.6443 vs 0.6357 (n=73) |
| Novig | mma | 35 | -15.3% / -10.1% (26/9) | reversion | -0.213 (0.789) per 10c | 0.6901 vs 0.6755 (n=36) |
| Novig | nba | 105 | +23.0% / +24.7% (83/22) | reversion | +0.391 (0.310) per 10c | 0.6397 vs 0.6397 (n=86) |
| Novig | nfl | 134 | +1.4% / -17.1% (114/20) | reversion | -0.018 (0.254) per 10c | 0.6532 vs 0.6544 (n=147) |
| Novig | nhl | 6 | -20.1% / +76.2% (5/1) | reversion | +0.654 (1.359) per 10c | 0.6935 vs 0.6978 (n=57) |
| Novig | seriea | 28 | -32.3% / -27.0% (23/5) | reversion | -0.622 (0.861) per 10c | 0.5971 vs 0.5703 (n=34) |
| Novig | ucl | 18 | +12.2% / -67.6% (13/5) | reversion | +0.965 (1.106) per 10c | 0.7010 vs 0.6588 (n=18) |

## 4. Late taker flow: follow the money in the last 6h / 2h?

Signed taker dollars (yes buys minus no buys) in the window, as a share of window volume. Strategy: when |flow share| >= 0.3 and window volume >= $500, buy the side the takers bought, at the close. This is the exchange version of 'sharp money', with the advantage that every dollar is real and timestamped.

| venue | sport | lines | window | n | train ROI / win% | holdout ROI / win% (n) | z vs break-even (holdout) |
|---|---|---|---|---|---|---|---|
| Kalshi | cfb | main | 6h | 397 | -14.2% / 0.651 | -3.3% / 0.559 (93) | -0.43 |
| Kalshi | cfb | main | 2h | 397 | -13.4% / 0.638 | -3.8% / 0.548 (93) | -0.38 |
| Kalshi | cfb | all | 6h | 755 | -14.6% / 0.541 | +5.5% / 0.527 (186) | -0.19 |
| Kalshi | cfb | all | 2h | 749 | -15.4% / 0.537 | +6.0% / 0.524 (189) | -0.09 |
| Kalshi | epl | all | 6h | 96 | +10.0% / 0.362 | +3.5% / 0.444 (27) | +0.44 |
| Kalshi | epl | all | 2h | 100 | +10.2% / 0.361 | +4.5% / 0.464 (28) | +0.54 |
| Kalshi | laliga | main | 6h | 48 | +13.7% / 0.588 | -5.3% / 0.571 (14) | -0.10 |
| Kalshi | laliga | main | 2h | 47 | +17.2% / 0.606 | -5.3% / 0.571 (14) | -0.10 |
| Kalshi | laliga | all | 6h | 125 | +1.4% / 0.484 | +18.2% / 0.533 (30) | +1.02 |
| Kalshi | laliga | all | 2h | 121 | +2.2% / 0.484 | +4.5% / 0.464 (28) | +0.63 |
| Kalshi | mls | main | 6h | 121 | -11.8% / 0.470 | -10.6% / 0.474 (38) | -0.69 |
| Kalshi | mls | main | 2h | 122 | -14.1% / 0.458 | -12.9% / 0.462 (39) | -0.85 |
| Kalshi | mls | all | 6h | 247 | +0.5% / 0.417 | -2.5% / 0.444 (72) | -0.30 |
| Kalshi | mls | all | 2h | 239 | -0.1% / 0.427 | -8.2% / 0.456 (68) | -0.51 |
| Kalshi | nba | main | 6h | 424 | -6.0% / 0.511 | +7.7% / 0.573 (103) | +0.81 |
| Kalshi | nba | main | 2h | 434 | -2.4% / 0.527 | +6.6% / 0.569 (102) | +0.74 |
| Kalshi | nba | all | 6h | 1429 | -0.4% / 0.571 | +4.2% / 0.584 (385) | +0.68 |
| Kalshi | nba | all | 2h | 1361 | +2.3% / 0.580 | +4.9% / 0.588 (354) | +1.12 |
| Kalshi | nfl | main | 6h | 534 | +6.1% / 0.582 | -12.3% / 0.485 (132) | -1.52 |
| Kalshi | nfl | main | 2h | 544 | +5.7% / 0.580 | -12.0% / 0.485 (130) | -1.49 |
| Kalshi | nfl | all | 6h | 3717 | +3.3% / 0.581 | -1.9% / 0.564 (1016) | -0.80 |
| Kalshi | nfl | all | 2h | 3579 | +4.0% / 0.569 | -4.6% / 0.550 (981) | -1.21 |
| Kalshi | nhl | main | 6h | 550 | +8.3% / 0.553 | +10.7% / 0.566 (152) | +1.33 |
| Kalshi | nhl | main | 2h | 542 | +10.4% / 0.565 | +8.1% / 0.543 (151) | +0.81 |
| Kalshi | nhl | all | 6h | 987 | +1.1% / 0.538 | +7.6% / 0.595 (296) | +1.71 |
| Kalshi | nhl | all | 2h | 971 | +3.7% / 0.549 | +5.7% / 0.566 (288) | +1.13 |
| Kalshi | seriea | main | 6h | 48 | +11.8% / 0.571 | +13.5% / 0.692 (13) | +0.93 |
| Kalshi | seriea | main | 2h | 47 | +20.1% / 0.618 | +13.5% / 0.692 (13) | +0.93 |
| Kalshi | seriea | all | 6h | 114 | -2.7% / 0.440 | +17.5% / 0.567 (30) | +1.10 |
| Kalshi | seriea | all | 2h | 113 | -1.9% / 0.458 | +13.8% / 0.533 (30) | +0.94 |
| Novig | bundesliga | main | 6h | 64 | +13.2% / 0.596 | +5.0% / 0.588 (17) | +0.14 |
| Novig | bundesliga | main | 2h | 58 | +6.7% / 0.524 | +0.4% / 0.562 (16) | -0.09 |
| Novig | bundesliga | all | 6h | 88 | -4.2% / 0.515 | -6.5% / 0.545 (22) | -0.24 |
| Novig | bundesliga | all | 2h | 82 | -6.5% / 0.484 | -12.5% / 0.500 (20) | -0.56 |
| Novig | cfb | main | 6h | 540 | +6.0% / 0.532 | -2.8% / 0.494 (89) | -0.30 |
| Novig | cfb | main | 2h | 523 | +3.5% / 0.518 | -4.3% / 0.482 (85) | -0.41 |
| Novig | cfb | all | 6h | 1839 | +0.5% / 0.507 | +1.4% / 0.513 (359) | +0.40 |
| Novig | cfb | all | 2h | 1640 | -2.7% / 0.491 | +3.1% / 0.518 (340) | +0.71 |
| Novig | epl | main | 6h | 112 | +6.8% / 0.548 | -8.0% / 0.536 (28) | -0.35 |
| Novig | epl | main | 2h | 110 | +4.4% / 0.541 | +3.0% / 0.600 (25) | +0.27 |
| Novig | epl | all | 6h | 203 | +15.5% / 0.559 | +11.3% / 0.550 (60) | +0.92 |
| Novig | epl | all | 2h | 200 | +4.2% / 0.531 | +18.8% / 0.582 (55) | +1.30 |
| Novig | laliga | main | 6h | 110 | +1.3% / 0.564 | +17.3% / 0.656 (32) | +1.42 |
| Novig | laliga | main | 2h | 108 | +2.0% / 0.562 | +12.4% / 0.629 (35) | +1.31 |
| Novig | laliga | all | 6h | 172 | +14.3% / 0.569 | +9.4% / 0.653 (49) | +1.13 |
| Novig | laliga | all | 2h | 168 | +14.1% / 0.573 | +3.7% / 0.608 (51) | +0.86 |
| Novig | ligue1 | main | 6h | 62 | +7.6% / 0.571 | +3.7% / 0.600 (20) | +0.56 |
| Novig | ligue1 | main | 2h | 60 | -1.3% / 0.524 | +6.2% / 0.611 (18) | +0.69 |
| Novig | ligue1 | all | 6h | 83 | +19.1% / 0.579 | +1.4% / 0.577 (26) | +0.73 |
| Novig | ligue1 | all | 2h | 79 | +16.2% / 0.564 | +3.1% / 0.583 (24) | +0.85 |
| Novig | mlb | main | 6h | 1726 | -1.8% / 0.511 | +2.6% / 0.531 (420) | +0.43 |
| Novig | mlb | main | 2h | 1853 | +0.9% / 0.524 | +0.6% / 0.515 (441) | -0.08 |
| Novig | mlb | all | 6h | 3145 | -1.5% / 0.511 | -5.3% / 0.482 (932) | -1.25 |
| Novig | mlb | all | 2h | 3184 | -2.0% / 0.509 | -2.4% / 0.485 (907) | -0.80 |
| Novig | mls | main | 6h | 207 | +4.1% / 0.540 | +3.3% / 0.561 (57) | +0.57 |
| Novig | mls | main | 2h | 201 | -4.9% / 0.497 | +11.5% / 0.596 (52) | +1.09 |
| Novig | mls | all | 6h | 306 | +3.1% / 0.534 | +7.5% / 0.575 (87) | +0.92 |
| Novig | mls | all | 2h | 291 | -1.3% / 0.507 | +4.0% / 0.575 (80) | +0.95 |
| Novig | mma | main | 6h | 86 | -0.6% / 0.483 | +16.9% / 0.538 (26) | +0.90 |
| Novig | mma | main | 2h | 87 | -4.4% / 0.452 | +15.5% / 0.520 (25) | +0.79 |
| Novig | mma | all | 6h | 92 | +3.2% / 0.515 | +16.9% / 0.538 (26) | +0.90 |
| Novig | mma | all | 2h | 94 | -5.2% / 0.464 | +15.5% / 0.520 (25) | +0.79 |
| Novig | nba | main | 6h | 242 | -6.4% / 0.497 | +2.4% / 0.510 (49) | +0.36 |
| Novig | nba | main | 2h | 247 | +3.4% / 0.545 | +20.3% / 0.596 (47) | +1.45 |
| Novig | nba | all | 6h | 882 | -2.7% / 0.505 | +15.1% / 0.572 (243) | +2.03 |
| Novig | nba | all | 2h | 827 | -0.8% / 0.519 | +12.6% / 0.565 (230) | +1.88 |
| Novig | nfl | main | 6h | 393 | -10.9% / 0.460 | -0.7% / 0.519 (104) | -0.04 |
| Novig | nfl | main | 2h | 413 | -4.8% / 0.486 | +1.2% / 0.510 (100) | +0.31 |
| Novig | nfl | all | 6h | 1597 | -1.7% / 0.496 | +11.6% / 0.534 (459) | +1.60 |
| Novig | nfl | all | 2h | 1570 | -1.2% / 0.496 | +11.8% / 0.523 (453) | +1.60 |
| Novig | nhl | main | 6h | 110 | +9.4% / 0.568 | -26.4% / 0.379 (29) | -1.50 |
| Novig | nhl | main | 2h | 134 | +2.6% / 0.531 | -22.8% / 0.389 (36) | -1.47 |
| Novig | nhl | all | 6h | 230 | +6.2% / 0.584 | -8.6% / 0.493 (69) | -0.75 |
| Novig | nhl | all | 2h | 243 | +3.6% / 0.552 | -8.4% / 0.479 (71) | -0.96 |
| Novig | seriea | main | 6h | 106 | -7.3% / 0.487 | +25.3% / 0.692 (26) | +1.68 |
| Novig | seriea | main | 2h | 106 | -10.9% / 0.469 | +23.7% / 0.680 (25) | +1.64 |
| Novig | seriea | all | 6h | 155 | -5.3% / 0.509 | +26.4% / 0.644 (45) | +1.79 |
| Novig | seriea | all | 2h | 157 | -11.2% / 0.482 | +20.0% / 0.617 (47) | +1.82 |
| Novig | ucl | main | 6h | 59 | +11.3% / 0.614 | +30.2% / 0.600 (15) | +0.83 |
| Novig | ucl | main | 2h | 62 | +9.9% / 0.583 | +39.5% / 0.643 (14) | +1.14 |
| Novig | ucl | all | 6h | 108 | -4.0% / 0.506 | +27.4% / 0.571 (21) | +1.08 |
| Novig | ucl | all | 2h | 115 | -2.3% / 0.516 | +33.8% / 0.600 (20) | +1.36 |

## 5. Big trades: is the largest pre-kickoff trade informed?

The single largest trade in the market (top of the top-5% by size). Direction = side the taker bought. 'Continued' = the close moved further in that direction; ROI = buying that side at the big trade's own price and holding to settlement.

| venue | sport | n | median big trade $ | continued to close | ROI at trade price train / hold (n) | win% hold |
|---|---|---|---|---|---|---|
| Kalshi | cfb | 867 | $649 | 26.0% | -3.2% / -1.5% (199) | 0.523 |
| Kalshi | epl | 117 | $426 | 29.1% | -1.0% / +7.2% (33) | 0.576 |
| Kalshi | laliga | 136 | $376 | 27.2% | -14.3% / +10.2% (37) | 0.649 |
| Kalshi | mls | 295 | $481 | 35.6% | -10.7% / +8.7% (87) | 0.586 |
| Kalshi | nba | 1769 | $741 | 31.0% | +0.1% / +7.9% (467) | 0.612 |
| Kalshi | nfl | 4611 | $1,083 | 26.5% | +3.6% / -0.9% (1244) | 0.585 |
| Kalshi | nhl | 1119 | $723 | 25.3% | -0.1% / +3.4% (336) | 0.577 |
| Kalshi | seriea | 133 | $702 | 30.8% | -16.9% / +8.0% (35) | 0.600 |
| Novig | bundesliga | 115 | $1,539 | 34.8% | -14.6% / +6.5% (28) | 0.607 |
| Novig | cfb | 2820 | $2,664 | 37.2% | +1.5% / +1.1% (534) | 0.515 |
| Novig | epl | 266 | $1,751 | 23.7% | -1.1% / +9.4% (77) | 0.571 |
| Novig | laliga | 246 | $1,521 | 28.5% | +8.8% / +4.3% (69) | 0.594 |
| Novig | ligue1 | 114 | $1,143 | 31.6% | -0.9% / -10.3% (34) | 0.500 |
| Novig | mlb | 5158 | $2,378 | 21.2% | -3.8% / +1.3% (1479) | 0.501 |
| Novig | mls | 437 | $1,500 | 28.4% | -1.6% / +5.0% (120) | 0.558 |
| Novig | mma | 131 | $1,889 | 23.7% | +6.4% / +10.9% (37) | 0.541 |
| Novig | nba | 1408 | $2,046 | 35.2% | -2.7% / +7.5% (396) | 0.535 |
| Novig | nfl | 2458 | $2,833 | 25.8% | -1.2% / +6.3% (651) | 0.513 |
| Novig | nhl | 363 | $1,671 | 21.5% | +3.4% / -7.7% (107) | 0.486 |
| Novig | seriea | 212 | $1,336 | 25.0% | -9.0% / +14.5% (62) | 0.629 |
| Novig | ucl | 159 | $1,543 | 23.9% | -13.4% / +19.3% (35) | 0.571 |

## 6. Who moves first: Kalshi vs Novig on the same market

Hourly two-sided mids (taker spread <= 4c) on markets both exchanges list (same game, market, side, line). Corr(dK_t, dN_t-1) > Corr(dN_t, dK_t-1) means Novig leads. Strategy 'follow the leader': when one venue moved >= 3c in hour t and the other moved < 1c, buy the laggard toward the leader's direction at the laggard's price; graded against the laggard's own close (CLV, in cents) and against the result.

| sport | matched markets | hour-pairs | corr(dK_t, dN_t-1) | corr(dN_t, dK_t-1) | same-hour corr | leader |
|---|---|---|---|---|---|---|
| nba | 115 | 762 | +0.154 | +0.056 | +0.846 | Novig leads |
| nfl | 183 | 2180 | +0.112 | +0.083 | +0.563 | no clear leader |

Follow the leader (laggard priced at its own next hourly print, graded vs laggard close and result):

| leader -> laggard | n | avg CLV (cents, holdout-free: all) | CLV>0 share | ROI at laggard price | win% |
|---|---|---|---|---|---|
| Novig -> Kalshi | 5 | n/a | | | |
| Kalshi -> Novig | 4 | n/a | | | |

## 7. Timing: which hours' moves stick?

For every hourly move of >= 2c in the two-sided mid, did the close end up on the same side of the post-move price (the move 'stuck') or come back? By ET hour of day (moves at least 6h before kickoff only, so the clock is not just distance to kickoff) and by hours-to-kickoff. Sharp moves should stick; public moves should mean-revert. Share > 50% with n in the hundreds is a real timing signal.

| venue | ET hour bucket | n moves | stuck share | avg |move| c |
|---|---|---|---|---|
| Kalshi | 0-5am | 208 | 52.4% | 3.8 |
| Kalshi | 6-9am | 139 | 51.8% | 3.8 |
| Kalshi | 10am-1pm | 301 | 63.1% | 3.9 |
| Kalshi | 2-5pm | 204 | 60.3% | 4.5 |
| Kalshi | 6-9pm | 168 | 56.5% | 3.5 |
| Kalshi | 10pm-12 | 141 | 51.8% | 4.1 |
| Novig | 0-5am | 146 | 52.7% | 3.2 |
| Novig | 6-9am | 215 | 57.2% | 3.2 |
| Novig | 10am-1pm | 425 | 53.9% | 3.2 |
| Novig | 2-5pm | 128 | 62.5% | 3.6 |
| Novig | 6-9pm | 86 | 47.7% | 3.4 |

| venue | hours to kickoff | n moves | stuck share |
|---|---|---|---|
| Kalshi | <1h | 494 | 92.5% |
| Kalshi | 1-3h | 89 | 64.0% |
| Kalshi | 3-6h | 143 | 72.0% |
| Kalshi | 6-12h | 233 | 61.4% |
| Kalshi | 12-24h | 199 | 53.8% |
| Kalshi | 1-3d | 264 | 54.2% |
| Kalshi | 3d+ | 406 | 55.9% |
| Novig | <1h | 802 | 88.3% |
| Novig | 1-3h | 300 | 66.0% |
| Novig | 3-6h | 269 | 61.3% |
| Novig | 6-12h | 488 | 56.6% |
| Novig | 12-24h | 166 | 54.8% |
| Novig | 1-3d | 136 | 57.4% |
| Novig | 3d+ | 167 | 41.9% |

## 8. Does volume make the close sharper?

| venue | sport | volume tercile | n | Brier close | ROI buying favorite at close |
|---|---|---|---|---|---|
| Kalshi | cfb | low (median $12,499) | 147 | 0.0927 | +0.7% |
| Kalshi | cfb | mid (median $52,580) | 146 | 0.1351 | +6.3% |
| Kalshi | cfb | high (median $230,787) | 147 | 0.1882 | -1.9% |
| Kalshi | mls | low (median $11,126) | 45 | 0.2121 | +4.1% |
| Kalshi | mls | mid (median $24,223) | 45 | 0.2380 | +9.6% |
| Kalshi | mls | high (median $91,749) | 45 | 0.2284 | +17.8% |
| Kalshi | nba | low (median $4,630) | 187 | 0.2484 | +4.8% |
| Kalshi | nba | mid (median $17,567) | 186 | 0.2458 | +0.7% |
| Kalshi | nba | high (median $101,214) | 187 | 0.2228 | +2.5% |
| Kalshi | nfl | low (median $11,185) | 238 | 0.2404 | -2.8% |
| Kalshi | nfl | mid (median $79,224) | 237 | 0.2447 | +4.4% |
| Kalshi | nfl | high (median $463,614) | 238 | 0.2390 | -2.9% |
| Kalshi | nhl | low (median $4,695) | 209 | 0.2282 | +4.5% |
| Kalshi | nhl | mid (median $16,959) | 208 | 0.2342 | +0.2% |
| Kalshi | nhl | high (median $53,872) | 208 | 0.2417 | -0.1% |
| Novig | cfb | low (median $5,983) | 272 | 0.2459 | +0.3% |
| Novig | cfb | mid (median $27,976) | 272 | 0.2461 | +4.2% |
| Novig | cfb | high (median $101,790) | 272 | 0.2523 | -8.8% |
| Novig | epl | low (median $9,347) | 47 | 0.2282 | +13.6% |
| Novig | epl | mid (median $25,603) | 46 | 0.2340 | -5.5% |
| Novig | epl | high (median $73,002) | 46 | 0.2238 | +4.6% |
| Novig | laliga | low (median $4,627) | 54 | 0.2486 | +9.8% |
| Novig | laliga | mid (median $14,989) | 53 | 0.1937 | +16.3% |
| Novig | laliga | high (median $41,741) | 53 | 0.1951 | +1.9% |
| Novig | mlb | low (median $5,328) | 980 | 0.2448 | -2.2% |
| Novig | mlb | mid (median $27,707) | 979 | 0.2422 | +3.9% |
| Novig | mlb | high (median $153,859) | 979 | 0.2418 | -1.5% |
| Novig | mls | low (median $3,375) | 100 | 0.2349 | -8.6% |
| Novig | mls | mid (median $9,714) | 99 | 0.2212 | +3.9% |
| Novig | mls | high (median $29,960) | 100 | 0.2350 | +10.8% |
| Novig | mma | low (median $3,650) | 41 | 0.2291 | +0.1% |
| Novig | mma | mid (median $11,193) | 40 | 0.2421 | +3.7% |
| Novig | mma | high (median $32,609) | 41 | 0.2506 | -3.4% |
| Novig | nba | low (median $7,476) | 141 | 0.2404 | -0.1% |
| Novig | nba | mid (median $38,248) | 141 | 0.2455 | +7.1% |
| Novig | nba | high (median $164,503) | 141 | 0.2151 | +8.8% |
| Novig | nfl | low (median $6,700) | 230 | 0.2420 | -5.7% |
| Novig | nfl | mid (median $46,639) | 229 | 0.2498 | -4.3% |
| Novig | nfl | high (median $503,601) | 229 | 0.2427 | +1.6% |
| Novig | nhl | low (median $13,937) | 67 | 0.2539 | -10.5% |
| Novig | nhl | mid (median $29,935) | 66 | 0.2486 | +5.6% |
| Novig | nhl | high (median $67,740) | 66 | 0.2507 | -0.4% |
| Novig | seriea | low (median $4,192) | 47 | 0.2338 | +1.1% |
| Novig | seriea | mid (median $10,629) | 47 | 0.2375 | +10.1% |
| Novig | seriea | high (median $26,513) | 47 | 0.2014 | +13.2% |

## 9. Longshot bias on the exchanges (the one structural effect that is everywhere)

Main lines, close price. z = (wins - sum of implied) / sqrt(sum p(1-p)). Negative gap = yes won less often than its price said.

| venue | price band | n | implied avg | hit rate | gap | z | ROI buying yes at close | ROI buying the other side |
|---|---|---|---|---|---|---|---|---|
| Kalshi | 0.00-0.20 | 80 | 0.076 | 0.037 | -0.039 | -1.35 | -77.0% | +4.4% |
| Kalshi | 0.20-0.35 | 183 | 0.296 | 0.311 | +0.015 | +0.46 | +6.9% | -2.0% |
| Kalshi | 0.35-0.50 | 905 | 0.452 | 0.422 | -0.030 | -1.79 | -7.0% | +5.2% |
| Kalshi | 0.50-0.65 | 1039 | 0.548 | 0.548 | -0.001 | -0.04 | -0.2% | +0.0% |
| Kalshi | 0.65-0.80 | 258 | 0.713 | 0.729 | +0.016 | +0.57 | +2.4% | -4.7% |
| Kalshi | 0.80-1.00 | 190 | 0.905 | 0.911 | +0.006 | +0.27 | +0.5% | -17.5% |
| Novig | 0.20-0.35 | 196 | 0.302 | 0.219 | -0.083 | -2.53 | -25.4% | +12.3% |
| Novig | 0.35-0.50 | 2728 | 0.452 | 0.451 | -0.001 | -0.11 | -0.1% | +0.3% |
| Novig | 0.50-0.65 | 2897 | 0.548 | 0.544 | -0.004 | -0.40 | -0.8% | +0.7% |
| Novig | 0.65-0.80 | 275 | 0.698 | 0.709 | +0.011 | +0.41 | +1.4% | -5.3% |
| Novig | 0.80-1.00 | 44 | 0.846 | 0.841 | -0.005 | -0.09 | -1.0% | -15.0% |

## 10. Reading it

A signal survives only if (a) the holdout ROI is positive and the holdout z is above about 2, (b) train and holdout agree in sign, and (c) the effect is monotone where it should be
(bigger flow / bigger move / bigger trade = bigger edge). Verdicts on this run (first full pull, 2026-10-29; re-run weekly as the tape grows):

**Passes now**
- Nothing. The longshot-bias result in section 9 (Novig 20-35c band, 22% hit on 29.6% implied, n=196, z -2.5) was the best cell of 11 tested (Bonferroni p 0.13), and it does not survive a robustness check run after the report: widening to every main line closing in the band (n=428, including rows whose side label did not parse) gives 28.5% hit on 29.6% implied, i.e. nothing, and the effect decays by month (fade ROI Aug +15.5%, Sep +3.5%, Oct -4.9%). It stays on as a free paper system (xch_homedog_fade) and nothing more.

**Promising, below the bar**
- Late taker flow, Kalshi NHL main lines (section 4): follow the 6h flow, train +8.3% / holdout +10.7% (n=550, holdout z 1.3), consistent across windows and across all-lines (+7.6% holdout). Novig MLB mains agree (+4.8% / +9.5%, n=638). Needs a live trade feed to run forward; the Kalshi trades endpoint can be polled per market.
- Momentum continuation, NBA (section 3): the T-6h to close move is continued, not reverted, on both exchanges (Kalshi +19.7% / +22.9%, Novig +23.0% / +24.7%, n 170 and 105; logit coefficient +0.36 and +0.39 per 10c, each about 1.3 se). Same sign, two venues, small n. NFL is the opposite in holdout (-39% Kalshi, -17% Novig), so this is sport-specific if it is anything. Forward paper test on NBA only.
- Largest trade follow, Kalshi NBA (section 5): buy the side of the biggest pre-kickoff trade at its price: train +0.1%, holdout +7.9% (n=467, 61% win). Novig NBA +7.5% holdout but -2.7% train. Not consistent enough yet.
- Novig leads Kalshi in NBA (section 6): corr(dKalshi_t, dNovig_t-1) = +0.15 vs +0.06 the other way; NFL is a wash. Too few clean laggard setups at hourly resolution to grade a strategy; the 20-minute tick log is the right instrument and move_signals.py (M2) is already wired for it.

**Fails**
- Timing of day (section 7): moves 6h+ before kickoff stick 52-63% of the time on both exchanges, with no hour-of-day bucket separating from the rest beyond noise (n in the low hundreds per bucket). Moves inside 3h stick more, which is mostly distance to the close.
- Volume as a quality signal (section 8): higher-volume markets are not better calibrated in any sport; the ROI differences across terciles are noise.
- Structural over/under or favourite/dog drift at T-24h (section 2): nothing consistent across venues or between train and holdout except the longshot effect above. Novig NFL yes (home) sides are -12% to -16% at the close on 450 markets, which is a home bias worth watching (home sides covering 46-49% this season on Novig prices) but is one season of one sport.
- Kalshi fees: every Kalshi number above is before the taker fee (about 1.75c at 50/50). Only the NHL flow result would survive that haircut as written.

Nothing in this document is a bet recommendation on its own; the survivors go into sharp/systems.py as tagged paper tests and are graded forward on the ledger.
