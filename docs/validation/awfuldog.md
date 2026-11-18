# NFL awful-team dog ATS (awfuldog)

Verdict: **PAPER ONLY** (grid p 0.459; walk-forward +12.7% on 70 (p 0.100); holdout +12.0% on 29)

Live definition: m -13. Price: Pinnacle full-game close. Seasons: 2020, 2021, 2022, 2023, 2024, 2025; holdout 2025. Base pool: 1594 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 62, record 34-27, units +4.18, ROI +6.7%. Flags: N < 100 (thin). Leakage review: none.

| Season | N | ROI |
|---|---|---|
| 2020 | 16 | -4.9% |
| 2021 | 21 | +9.4% |
| 2022 | 1 | +103.0% |
| 2023 | 12 | +2.8% |
| 2024 | 12 | +13.5% |
| 2025 | 15 | +27.3% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 6 grid variants per shuffle (N >= 30): p = 0.459. Plain single-filter permutation (weaker): p = 0.245.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022 | m -13 | 1 | +103.0% |
| 2023 | m -11 | 22 | +4.3% |
| 2024 | m -11 | 18 | +19.1% |
| 2025 (holdout) | m -11 | 29 | +12.0% |

Out-of-sample before the holdout: +13.2% on 41. Holdout: +12.0% on 29. All walk-forward seasons: +12.7% on 70.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.100 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| m -15 | 36 | +4.8% |
| m -11 | 102 | +8.5% |

Plateau: yes.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| m -17 | 15 | +23.9% |
| m -11 | 102 | +8.5% |
| m -13 | 62 | +6.7% |
| m -15 | 36 | +4.8% |
| m -9 | 195 | +2.7% |
| m -7 | 322 | -2.2% |
