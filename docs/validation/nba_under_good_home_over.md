# NBA under, good home over team, total down (nba_under_good_home_over)

Verdict: **RETIRE** (grid p 0.435; walk-forward -11.6% on 65 (p 0.610); holdout -38.6% on 16; no plateau)

Live definition: d 1.5, o 58. Price: Pinnacle full-game close. Seasons: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26; holdout 2025-26. Base pool: 7103 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 246, record 132-112, units +13.33, ROI +5.4%. Flags: none. Leakage review: open-to-close total move in the filter: only known at the close, where it is graded; a bet placed earlier would not know the full drop.

| Season | N | ROI |
|---|---|---|
| 2020-21 | 49 | +12.1% |
| 2021-22 | 30 | +5.0% |
| 2022-23 | 39 | +8.8% |
| 2023-24 | 58 | +7.5% |
| 2024-25 | 70 | -2.7% |
| 2025-26 | 69 | +14.2% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 25 grid variants per shuffle (N >= 30): p = 0.435. Plain single-filter permutation (weaker): p = 0.040.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022-23 | d 1, o 65 | 15 | +2.9% |
| 2023-24 | d 1, o 65 | 29 | -8.9% |
| 2024-25 | d 3, o 65 | 5 | +16.4% |
| 2025-26 (holdout) | d 3, o 65 | 16 | -38.6% |

Out-of-sample before the holdout: -2.7% on 49. Holdout: -38.6% on 16. All walk-forward seasons: -11.6% on 65.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.610 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| d 1, o 58 | 294 | +1.5% |
| d 2, o 58 | 206 | +1.8% |
| d 1.5, o 55 | 428 | +1.3% |
| d 1.5, o 62 | 133 | +2.1% |

Plateau: no.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| d 3, o 65 | 48 | +9.6% |
| d 1, o 65 | 101 | +5.5% |
| d 1.5, o 58 | 246 | +5.4% |
| d 1.5, o 65 | 83 | +3.5% |
| d 0.5, o 65 | 118 | +2.7% |
| d 1.5, o 62 | 133 | +2.1% |
| d 2, o 58 | 206 | +1.8% |
| d 1, o 58 | 294 | +1.5% |
| d 3, o 62 | 75 | +1.4% |
| d 1.5, o 55 | 428 | +1.3% |
| d 1.5, o 50 | 886 | +1.2% |
| d 1, o 62 | 161 | +0.8% |
| d 3, o 58 | 136 | +0.3% |
| d 2, o 65 | 72 | +0.2% |
| d 1, o 50 | 1048 | +0.2% |
| d 2, o 62 | 115 | -0.6% |
| d 2, o 50 | 740 | -0.7% |
| d 1, o 55 | 508 | -1.2% |
| d 0.5, o 50 | 1217 | -1.9% |
| d 0.5, o 58 | 343 | -2.4% |
| d 2, o 55 | 361 | -2.8% |
| d 0.5, o 62 | 189 | -3.2% |
| d 0.5, o 55 | 586 | -3.5% |
| d 3, o 50 | 490 | -6.0% |
| d 3, o 55 | 243 | -6.2% |
