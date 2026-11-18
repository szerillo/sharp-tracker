# NHL early-season home fav vs quality opponent ML (nhl_early_home_fav_qual)

Verdict: **PAPER ONLY** (grid p 0.087; walk-forward +9.3% on 222 (p 0.015); holdout +17.9% on 65)

Live definition: G 24, w 51. Price: Pinnacle full-game close. Seasons: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26; holdout 2025-26. Base pool: 7264 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 328, record 215-113, units +33.26, ROI +10.1%. Flags: none. Leakage review: closing moneyline decides favourite (graded at the same close).

| Season | N | ROI |
|---|---|---|
| 2020-21 | 26 | +27.3% |
| 2021-22 | 94 | +14.2% |
| 2022-23 | 86 | +2.3% |
| 2023-24 | 57 | +10.5% |
| 2024-25 | 65 | +7.3% |
| 2025-26 | 81 | +15.5% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 25 grid variants per shuffle (N >= 30): p = 0.087. Plain single-filter permutation (weaker): p = 0.012.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022-23 | G 20, w 55 | 70 | +6.2% |
| 2023-24 | G 20, w 55 | 43 | +3.1% |
| 2024-25 | G 20, w 55 | 44 | +7.5% |
| 2025-26 (holdout) | G 24, w 55 | 65 | +17.9% |

Out-of-sample before the holdout: +5.7% on 157. Holdout: +17.9% on 65. All walk-forward seasons: +9.3% on 222.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.015 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| G 20, w 51 | 267 | +8.2% |
| G 28, w 51 | 394 | +7.4% |
| G 24, w 50 | 449 | +4.9% |
| G 24, w 53 | 313 | +9.4% |

Plateau: yes.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| G 24, w 55 | 286 | +10.4% |
| G 20, w 55 | 238 | +10.4% |
| G 24, w 51 | 328 | +10.1% |
| G 24, w 53 | 313 | +9.4% |
| G 16, w 55 | 185 | +9.0% |
| G 20, w 53 | 260 | +8.7% |
| G 20, w 51 | 267 | +8.2% |
| G 28, w 55 | 330 | +8.0% |
| G 16, w 53 | 204 | +7.8% |
| G 28, w 53 | 366 | +7.5% |
| G 16, w 51 | 206 | +7.4% |
| G 28, w 51 | 394 | +7.4% |
| G 32, w 53 | 422 | +6.9% |
| G 32, w 51 | 456 | +6.9% |
| G 32, w 55 | 379 | +6.7% |
| G 24, w 48 | 452 | +5.3% |
| G 24, w 50 | 449 | +4.9% |
| G 20, w 48 | 376 | +4.4% |
| G 20, w 50 | 376 | +4.4% |
| G 32, w 48 | 618 | +4.2% |
| G 16, w 48 | 301 | +4.2% |
| G 16, w 50 | 301 | +4.2% |
| G 32, w 50 | 594 | +3.8% |
| G 28, w 48 | 539 | +3.5% |
| G 28, w 50 | 527 | +3.2% |
