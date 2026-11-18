# CFB hot weather over, total 55 or less (cfb_hot_over_low_total)

Verdict: **PAPER ONLY** (grid p 0.323; walk-forward +17.8% on 119 (p 0.020); holdout +20.7% on 27)

Live definition: T 85, W 10, C 55, nc True. Price: Pinnacle full-game close. Seasons: 2020, 2021, 2022, 2023, 2024, 2025; holdout 2025. Base pool: 3871 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 69, record 43-26, units +13.82, ROI +20.0%. Flags: N < 100 (thin). Leakage review: closing total in the filter (Bet Labs "Closing Total Range"); the bet is graded at the same close, so no extra edge leaks in at the close, but a bet placed earlier sees a different number.

| Season | N | ROI |
|---|---|---|
| 2020 | 0 | n/a |
| 2021 | 17 | +13.2% |
| 2022 | 9 | -14.8% |
| 2023 | 20 | +26.2% |
| 2024 | 23 | +33.3% |
| 2025 | 29 | +19.1% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 72 grid variants per shuffle (N >= 30): p = 0.323. Plain single-filter permutation (weaker): p = 0.038.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022 | T 80, W 8, C 55, nc False | 28 | -3.6% |
| 2023 | T 80, W 8, C 55, nc True | 44 | +26.7% |
| 2024 | T 85, W 8, C 55, nc True | 20 | +24.3% |
| 2025 (holdout) | T 85, W 8, C 55, nc True | 27 | +20.7% |

Out-of-sample before the holdout: +17.0% on 92. Holdout: +20.7% on 27. All walk-forward seasons: +17.8% on 119.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.020 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| T 80, W 10, C 55, nc True | 155 | +14.0% |
| T 90, W 10, C 55, nc True | 34 | +18.8% |
| T 85, W 8, C 55, nc True | 58 | +26.1% |
| T 85, W 12, C 55, nc True | 71 | +16.6% |
| T 85, W 10, C 50, nc True | 29 | +19.2% |
| T 85, W 10, C 60, nc True | 119 | +8.3% |
| T 85, W 10, C 55, nc False | 108 | +7.2% |

Plateau: yes.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| T 85, W 8, C 55, nc True | 58 | +26.1% |
| T 90, W 8, C 55, nc True | 28 | +23.2% |
| T 85, W 10, C 55, nc True | 69 | +20.0% |
| T 85, W 8, C 50, nc True | 24 | +19.9% |
| T 85, W 10, C 50, nc True | 29 | +19.2% |
| T 90, W 10, C 55, nc True | 34 | +18.8% |
| T 80, W 8, C 55, nc True | 136 | +18.5% |
| T 90, W 8, C 55, nc False | 39 | +18.2% |
| T 85, W 12, C 55, nc True | 71 | +16.6% |
| T 80, W 12, C 55, nc True | 163 | +15.5% |
| T 85, W 8, C 55, nc False | 87 | +15.4% |
| T 85, W 12, C 50, nc True | 30 | +15.3% |
| T 85, W 8, C 60, nc True | 97 | +15.0% |
| T 80, W 10, C 55, nc True | 155 | +14.0% |
| T 90, W 8, C 60, nc True | 44 | +13.7% |
| T 90, W 12, C 55, nc True | 36 | +12.2% |
| T 80, W 8, C 55, nc False | 221 | +11.3% |
| T 90, W 10, C 55, nc False | 47 | +10.6% |
| T 80, W 8, C 60, nc True | 222 | +10.2% |
| T 85, W 10, C 50, nc False | 49 | +10.1% |
| T 85, W 8, C 60, nc False | 144 | +9.7% |
| T 85, W 12, C 50, nc False | 51 | +9.5% |
| T 80, W 12, C 55, nc False | 277 | +8.9% |
| T 80, W 8, C 50, nc True | 60 | +8.8% |
| T 80, W 10, C 55, nc False | 262 | +8.5% |
| T 85, W 10, C 60, nc True | 119 | +8.3% |
| T 85, W 8, C 50, nc False | 41 | +8.1% |
| T 80, W 12, C 50, nc True | 73 | +8.0% |
| T 90, W 8, C 60, nc False | 59 | +7.8% |
| T 85, W 10, C 55, nc False | 108 | +7.2% |
| T 80, W 10, C 50, nc True | 70 | +7.1% |
| T 90, W 10, C 60, nc True | 56 | +6.8% |
| T 85, W 12, C 55, nc False | 113 | +5.9% |
| T 90, W 12, C 55, nc False | 51 | +5.8% |
| T 80, W 8, C 60, nc False | 340 | +5.6% |
| T 80, W 12, C 60, nc True | 269 | +5.3% |
| T 80, W 10, C 60, nc True | 255 | +5.0% |
| T 85, W 12, C 60, nc True | 123 | +4.8% |
| T 80, W 12, C 50, nc False | 128 | +3.7% |
| T 80, W 10, C 50, nc False | 121 | +3.3% |
| T 85, W 10, C 60, nc False | 176 | +2.8% |
| T 80, W 12, C 60, nc False | 425 | +2.6% |
| T 80, W 10, C 60, nc False | 399 | +2.5% |
| T 80, W 8, C 999, nc True | 295 | +1.7% |
| T 90, W 8, C 999, nc True | 53 | +1.6% |
| T 85, W 12, C 60, nc False | 184 | +1.6% |
| T 85, W 8, C 999, nc True | 131 | +1.1% |
| T 80, W 8, C 50, nc False | 101 | +1.0% |
| T 90, W 10, C 60, nc False | 73 | +0.5% |
| T 85, W 8, C 999, nc False | 188 | +0.4% |
| T 90, W 12, C 60, nc True | 60 | -0.4% |
| T 90, W 8, C 999, nc False | 70 | -0.9% |
| T 80, W 8, C 999, nc False | 443 | -1.2% |
| T 80, W 12, C 999, nc True | 356 | -1.3% |
| T 80, W 12, C 999, nc False | 553 | -2.5% |
| T 80, W 10, C 999, nc True | 335 | -2.7% |
| T 85, W 10, C 999, nc True | 156 | -2.7% |
| T 90, W 10, C 999, nc True | 68 | -3.7% |
| T 85, W 12, C 999, nc False | 243 | -4.1% |
| T 80, W 10, C 999, nc False | 514 | -4.2% |
| T 90, W 10, C 50, nc True | 14 | -4.3% |
| T 90, W 12, C 999, nc False | 101 | -4.4% |
| T 85, W 12, C 999, nc True | 165 | -4.5% |
| T 90, W 12, C 60, nc False | 79 | -4.7% |
| T 90, W 8, C 50, nc False | 18 | -4.7% |
| T 85, W 10, C 999, nc False | 227 | -5.0% |
| T 90, W 8, C 50, nc True | 12 | -5.1% |
| T 90, W 10, C 999, nc False | 88 | -5.7% |
| T 90, W 12, C 999, nc True | 76 | -6.2% |
| T 90, W 10, C 50, nc False | 21 | -8.8% |
| T 90, W 12, C 50, nc True | 15 | -10.7% |
| T 90, W 12, C 50, nc False | 22 | -12.9% |
