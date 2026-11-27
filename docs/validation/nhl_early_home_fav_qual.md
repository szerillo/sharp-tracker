# NHL early-season home fav vs quality opponent ML (nhl_early_home_fav_qual)

Verdict: **PAPER ONLY** (grid p 0.128; walk-forward +7.4% on 214 (p 0.020); holdout +18.2% on 51)

Live definition: G 24, w 51. Price: Pinnacle full-game close. Seasons: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26; holdout 2025-26. Base pool: 7428 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 363, record 233-130, units +30.21, ROI +8.3%. Flags: none. Leakage review: closing moneyline decides favourite (graded at the same close).

| Season | N | ROI |
|---|---|---|
| 2020-21 | 55 | +12.0% |
| 2021-22 | 94 | +14.2% |
| 2022-23 | 86 | +2.3% |
| 2023-24 | 57 | +10.5% |
| 2024-25 | 71 | +3.1% |
| 2025-26 | 88 | +10.2% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 25 grid variants per shuffle (N >= 30): p = 0.128. Plain single-filter permutation (weaker): p = 0.029.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022-23 | G 20, w 55 | 70 | +6.2% |
| 2023-24 | G 20, w 55 | 43 | +3.1% |
| 2024-25 | G 20, w 55 | 50 | +1.5% |
| 2025-26 (holdout) | G 16, w 55 | 51 | +18.2% |

Out-of-sample before the holdout: +4.0% on 163. Holdout: +18.2% on 51. All walk-forward seasons: +7.4% on 214.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.020 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| G 20, w 51 | 297 | +7.3% |
| G 28, w 51 | 428 | +5.4% |
| G 24, w 50 | 494 | +4.6% |
| G 24, w 53 | 353 | +8.5% |

Plateau: yes.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| G 16, w 55 | 210 | +9.3% |
| G 24, w 55 | 327 | +8.9% |
| G 20, w 55 | 269 | +8.6% |
| G 16, w 53 | 230 | +8.6% |
| G 24, w 53 | 353 | +8.5% |
| G 24, w 51 | 363 | +8.3% |
| G 16, w 51 | 232 | +8.3% |
| G 20, w 53 | 291 | +7.9% |
| G 20, w 51 | 297 | +7.3% |
| G 28, w 55 | 371 | +6.4% |
| G 28, w 53 | 405 | +6.2% |
| G 32, w 53 | 468 | +5.8% |
| G 16, w 48 | 341 | +5.6% |
| G 16, w 50 | 341 | +5.6% |
| G 28, w 51 | 428 | +5.4% |
| G 32, w 51 | 498 | +5.3% |
| G 32, w 55 | 424 | +5.2% |
| G 20, w 48 | 418 | +4.6% |
| G 20, w 50 | 418 | +4.6% |
| G 24, w 50 | 494 | +4.6% |
| G 24, w 48 | 497 | +4.5% |
| G 32, w 48 | 669 | +4.1% |
| G 32, w 50 | 645 | +3.7% |
| G 28, w 48 | 582 | +3.0% |
| G 28, w 50 | 569 | +2.9% |
