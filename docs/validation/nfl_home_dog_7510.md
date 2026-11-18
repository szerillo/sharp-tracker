# NFL home dog 7.5 to 10 (nfl_home_dog_7510)

Verdict: **PAPER ONLY** (grid p 0.234; walk-forward +12.4% on 36 (p 0.230); holdout +25.2% on 6)

Live definition: lo 7.5, hi 10. Price: Pinnacle full-game close. Seasons: 2020, 2021, 2022, 2023, 2024, 2025; holdout 2025. Base pool: 641 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 57, record 36-20, units +12.12, ROI +21.3%. Flags: N < 100 (thin). Leakage review: closing spread in the filter (graded at the same close).

| Season | N | ROI |
|---|---|---|
| 2020 | 16 | +31.1% |
| 2021 | 12 | -3.8% |
| 2022 | 13 | +15.8% |
| 2023 | 9 | +13.7% |
| 2024 | 7 | +61.6% |
| 2025 | 16 | +29.6% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 30 grid variants per shuffle (N >= 30): p = 0.234. Plain single-filter permutation (weaker): p = 0.053.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022 | lo 7.5, hi 11 | 14 | +20.9% |
| 2023 | lo 8, hi 14 | 14 | -13.1% |
| 2024 | lo 8, hi 11 | 2 | +92.5% |
| 2025 (holdout) | lo 8, hi 10 | 6 | +25.2% |

Out-of-sample before the holdout: +9.8% on 30. Holdout: +25.2% on 6. All walk-forward seasons: +12.4% on 36.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.230 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| lo 7, hi 10 | 84 | +13.2% |
| lo 8, hi 10 | 30 | +23.9% |
| lo 7.5, hi 9.5 | 46 | +19.7% |
| lo 7.5, hi 10.5 | 60 | +18.3% |

Plateau: yes.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| lo 8, hi 10 | 30 | +23.9% |
| lo 8, hi 9.5 | 19 | +21.7% |
| lo 8, hi 11 | 40 | +21.3% |
| lo 7.5, hi 10 | 57 | +21.3% |
| lo 7.5, hi 11 | 67 | +20.1% |
| lo 7.5, hi 9.5 | 46 | +19.7% |
| lo 7.5, hi 10.5 | 60 | +18.3% |
| lo 8, hi 10.5 | 33 | +18.3% |
| lo 6.5, hi 10 | 114 | +17.4% |
| lo 7.5, hi 9 | 42 | +17.3% |
| lo 6.5, hi 11 | 124 | +17.1% |
| lo 6.5, hi 9.5 | 103 | +16.3% |
| lo 6.5, hi 10.5 | 117 | +16.0% |
| lo 8, hi 9 | 15 | +15.5% |
| lo 7.5, hi 14 | 84 | +15.2% |
| lo 6.5, hi 9 | 99 | +15.1% |
| lo 6.5, hi 14 | 141 | +14.5% |
| lo 8, hi 14 | 57 | +13.7% |
| lo 7, hi 11 | 94 | +13.2% |
| lo 7, hi 10 | 84 | +13.2% |
| lo 7, hi 10.5 | 87 | +11.4% |
| lo 7, hi 9.5 | 73 | +11.0% |
| lo 7, hi 14 | 111 | +10.5% |
| lo 7, hi 9 | 69 | +9.0% |
| lo 6, hi 11 | 145 | +9.0% |
| lo 6, hi 10 | 135 | +8.6% |
| lo 6, hi 10.5 | 138 | +7.6% |
| lo 6, hi 14 | 162 | +7.6% |
| lo 6, hi 9.5 | 124 | +6.9% |
| lo 6, hi 9 | 120 | +5.6% |
