# CFB home fav 7.5 to 10 under (cfb_homefav_7510_under)

Verdict: **PAPER ONLY** (grid p 0.127; walk-forward +8.7% on 180 (p 0.015); holdout +35.8% on 37)

Live definition: lo 7.5, hi 10. Price: Pinnacle full-game close. Seasons: 2020, 2021, 2022, 2023, 2024, 2025; holdout 2025. Base pool: 4154 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 212, record 121-89, units +22.87, ROI +10.8%. Flags: none. Leakage review: closing spread in the filter (graded at the same close).

| Season | N | ROI |
|---|---|---|
| 2020 | 21 | +37.9% |
| 2021 | 36 | +14.9% |
| 2022 | 56 | +24.0% |
| 2023 | 49 | -13.5% |
| 2024 | 50 | +5.5% |
| 2025 | 54 | +18.1% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 30 grid variants per shuffle (N >= 30): p = 0.127. Plain single-filter permutation (weaker): p = 0.007.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022 | lo 8, hi 10 | 44 | +14.2% |
| 2023 | lo 7.5, hi 10 | 49 | -13.5% |
| 2024 | lo 7.5, hi 10 | 50 | +5.5% |
| 2025 (holdout) | lo 8, hi 10 | 37 | +35.8% |

Out-of-sample before the holdout: +1.7% on 143. Holdout: +35.8% on 37. All walk-forward seasons: +8.7% on 180.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.015 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| lo 7, hi 10 | 281 | +6.1% |
| lo 8, hi 10 | 147 | +12.0% |
| lo 7.5, hi 9.5 | 165 | +6.6% |
| lo 7.5, hi 10.5 | 257 | +3.3% |

Plateau: yes.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| lo 8, hi 10 | 147 | +12.0% |
| lo 7.5, hi 10 | 212 | +10.8% |
| lo 7.5, hi 9.5 | 165 | +6.6% |
| lo 7, hi 10 | 281 | +6.1% |
| lo 6.5, hi 10 | 362 | +6.0% |
| lo 8, hi 9.5 | 100 | +5.7% |
| lo 6, hi 10 | 401 | +3.6% |
| lo 7.5, hi 10.5 | 257 | +3.3% |
| lo 6.5, hi 9.5 | 315 | +3.2% |
| lo 7.5, hi 9 | 127 | +2.3% |
| lo 7, hi 9.5 | 234 | +2.3% |
| lo 7.5, hi 11 | 286 | +2.1% |
| lo 6.5, hi 10.5 | 407 | +1.8% |
| lo 8, hi 10.5 | 192 | +1.6% |
| lo 6.5, hi 11 | 436 | +1.2% |
| lo 7, hi 10.5 | 326 | +0.8% |
| lo 6, hi 9.5 | 354 | +0.8% |
| lo 6.5, hi 9 | 277 | +0.7% |
| lo 8, hi 11 | 221 | +0.3% |
| lo 7, hi 11 | 355 | +0.1% |
| lo 6, hi 10.5 | 446 | +0.0% |
| lo 6, hi 11 | 475 | -0.5% |
| lo 7, hi 9 | 196 | -1.4% |
| lo 6.5, hi 14 | 638 | -1.4% |
| lo 7.5, hi 14 | 488 | -1.7% |
| lo 6, hi 9 | 316 | -1.7% |
| lo 6, hi 14 | 677 | -2.4% |
| lo 7, hi 14 | 557 | -2.5% |
| lo 8, hi 14 | 423 | -3.1% |
| lo 8, hi 9 | 62 | -3.8% |
