# NHL bounce home ML off a 3+ goal loss (nhl_bounce_home_ml)

Verdict: **PAPER ONLY** (grid p 0.424; walk-forward +3.2% on 116 (p 0.220); holdout +54.9% on 14)

Live definition: lo 50, hi 64, m 3. Price: Pinnacle full-game close. Seasons: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26; holdout 2025-26. Base pool: 7428 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 385, record 239-146, units +22.27, ROI +5.8%. Flags: none. Leakage review: none.

| Season | N | ROI |
|---|---|---|
| 2020-21 | 29 | +6.8% |
| 2021-22 | 92 | +20.6% |
| 2022-23 | 89 | -17.4% |
| 2023-24 | 97 | +8.0% |
| 2024-25 | 78 | +11.7% |
| 2025-26 | 101 | +10.9% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 27 grid variants per shuffle (N >= 30): p = 0.424. Plain single-filter permutation (weaker): p = 0.030.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022-23 | lo 45, hi 60, m 4 | 40 | -21.0% |
| 2023-24 | lo 45, hi 60, m 4 | 46 | +1.9% |
| 2024-25 | lo 55, hi 60, m 4 | 16 | +21.8% |
| 2025-26 (holdout) | lo 55, hi 60, m 4 | 14 | +54.9% |

Out-of-sample before the holdout: -3.9% on 102. Holdout: +54.9% on 14. All walk-forward seasons: +3.2% on 116.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.220 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| lo 45, hi 64, m 3 | 512 | +3.7% |
| lo 55, hi 64, m 3 | 212 | +10.0% |
| lo 50, hi 60, m 3 | 309 | +6.2% |
| lo 50, hi 70, m 3 | 434 | +5.9% |
| lo 50, hi 64, m 2 | 583 | +5.1% |
| lo 50, hi 64, m 4 | 164 | +4.4% |

Plateau: yes.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| lo 55, hi 60, m 4 | 60 | +16.2% |
| lo 55, hi 60, m 3 | 136 | +13.4% |
| lo 45, hi 60, m 4 | 191 | +11.1% |
| lo 55, hi 64, m 3 | 212 | +10.0% |
| lo 55, hi 60, m 2 | 205 | +9.6% |
| lo 55, hi 70, m 3 | 261 | +9.4% |
| lo 50, hi 60, m 4 | 137 | +8.3% |
| lo 45, hi 64, m 4 | 218 | +7.8% |
| lo 55, hi 64, m 2 | 314 | +6.5% |
| lo 45, hi 70, m 4 | 235 | +6.5% |
| lo 55, hi 64, m 4 | 87 | +6.3% |
| lo 50, hi 60, m 3 | 309 | +6.2% |
| lo 50, hi 60, m 2 | 474 | +6.0% |
| lo 50, hi 70, m 3 | 434 | +5.9% |
| lo 50, hi 64, m 3 | 385 | +5.8% |
| lo 55, hi 70, m 2 | 393 | +5.2% |
| lo 50, hi 64, m 2 | 583 | +5.1% |
| lo 50, hi 70, m 2 | 662 | +4.4% |
| lo 50, hi 64, m 4 | 164 | +4.4% |
| lo 45, hi 70, m 3 | 561 | +4.0% |
| lo 45, hi 64, m 3 | 512 | +3.7% |
| lo 45, hi 60, m 3 | 436 | +3.7% |
| lo 45, hi 60, m 2 | 675 | +3.6% |
| lo 55, hi 70, m 4 | 104 | +3.5% |
| lo 45, hi 64, m 2 | 784 | +3.2% |
| lo 50, hi 70, m 4 | 181 | +3.0% |
| lo 45, hi 70, m 2 | 863 | +2.9% |
