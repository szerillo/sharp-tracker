# NHL bounce home ML off a 3+ goal loss (nhl_bounce_home_ml)

Verdict: **PAPER ONLY** (grid p 0.267; walk-forward +3.3% on 114 (p 0.175); holdout +52.0% on 13)

Live definition: lo 50, hi 64, m 3. Price: Pinnacle full-game close. Seasons: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26; holdout 2025-26. Base pool: 7264 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 387, record 245-142, units +30.72, ROI +7.9%. Flags: none. Leakage review: none.

| Season | N | ROI |
|---|---|---|
| 2020-21 | 35 | +23.0% |
| 2021-22 | 92 | +20.6% |
| 2022-23 | 89 | -17.4% |
| 2023-24 | 97 | +8.0% |
| 2024-25 | 74 | +15.6% |
| 2025-26 | 94 | +12.1% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 27 grid variants per shuffle (N >= 30): p = 0.267. Plain single-filter permutation (weaker): p = 0.012.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022-23 | lo 45, hi 60, m 4 | 40 | -21.0% |
| 2023-24 | lo 45, hi 60, m 4 | 46 | +1.9% |
| 2024-25 | lo 55, hi 60, m 4 | 15 | +29.9% |
| 2025-26 (holdout) | lo 55, hi 60, m 4 | 13 | +52.0% |

Out-of-sample before the holdout: -3.0% on 101. Holdout: +52.0% on 13. All walk-forward seasons: +3.3% on 114.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.175 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| lo 45, hi 64, m 3 | 526 | +6.4% |
| lo 55, hi 64, m 3 | 210 | +14.2% |
| lo 50, hi 60, m 3 | 314 | +7.7% |
| lo 50, hi 70, m 3 | 431 | +7.2% |
| lo 50, hi 64, m 2 | 587 | +5.7% |
| lo 50, hi 64, m 4 | 162 | +6.9% |

Plateau: yes.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| lo 55, hi 60, m 4 | 61 | +19.4% |
| lo 55, hi 60, m 3 | 137 | +17.1% |
| lo 55, hi 64, m 3 | 210 | +14.2% |
| lo 45, hi 60, m 4 | 199 | +12.6% |
| lo 55, hi 60, m 2 | 213 | +12.0% |
| lo 55, hi 70, m 3 | 254 | +11.8% |
| lo 55, hi 64, m 4 | 86 | +11.7% |
| lo 45, hi 64, m 4 | 224 | +10.4% |
| lo 50, hi 60, m 4 | 137 | +9.5% |
| lo 45, hi 70, m 4 | 240 | +8.6% |
| lo 55, hi 64, m 2 | 317 | +8.4% |
| lo 50, hi 64, m 3 | 387 | +7.9% |
| lo 50, hi 60, m 3 | 314 | +7.7% |
| lo 55, hi 70, m 4 | 102 | +7.4% |
| lo 50, hi 70, m 3 | 431 | +7.2% |
| lo 50, hi 64, m 4 | 162 | +6.9% |
| lo 50, hi 60, m 2 | 483 | +6.7% |
| lo 55, hi 70, m 2 | 388 | +6.5% |
| lo 45, hi 64, m 3 | 526 | +6.4% |
| lo 45, hi 60, m 3 | 453 | +5.9% |
| lo 45, hi 70, m 3 | 570 | +5.9% |
| lo 50, hi 64, m 2 | 587 | +5.7% |
| lo 50, hi 70, m 2 | 658 | +4.9% |
| lo 50, hi 70, m 4 | 178 | +4.9% |
| lo 45, hi 60, m 2 | 701 | +4.7% |
| lo 45, hi 64, m 2 | 805 | +4.2% |
| lo 45, hi 70, m 2 | 876 | +3.7% |
