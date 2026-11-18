# NBA hot home team ATS, 2 days rest (nba_ats_hot_home)

Verdict: **PAPER ONLY** (grid p 0.301; walk-forward +3.2% on 74 (p 0.325); holdout -1.8% on 12; no plateau)

Live definition: a 60, r 2. Price: Pinnacle full-game close. Seasons: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26; holdout 2025-26. Base pool: 7108 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 432, record 240-180, units +48.12, ROI +11.1%. Flags: none. Leakage review: none.

| Season | N | ROI |
|---|---|---|
| 2020-21 | 73 | -5.6% |
| 2021-22 | 114 | +18.0% |
| 2022-23 | 66 | +3.7% |
| 2023-24 | 81 | +14.4% |
| 2024-25 | 98 | +17.9% |
| 2025-26 | 76 | -3.7% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 12 grid variants per shuffle (N >= 30): p = 0.301. Plain single-filter permutation (weaker): p = 0.000.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022-23 | a 60, r 3 | 23 | -31.7% |
| 2023-24 | a 70, r 2 | 24 | +38.0% |
| 2024-25 | a 70, r 2 | 15 | +5.1% |
| 2025-26 (holdout) | a 70, r 2 | 12 | -1.8% |

Out-of-sample before the holdout: +4.2% on 62. Holdout: -1.8% on 12. All walk-forward seasons: +3.2% on 74.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.325 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| a 55, r 2 | 901 | +4.9% |
| a 65, r 2 | 176 | +18.2% |
| a 60, r 1 | 117 | -9.2% |
| a 60, r 3 | 117 | -0.8% |

Plateau: no.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| a 70, r 2 | 74 | +25.2% |
| a 65, r 2 | 176 | +18.2% |
| a 70, r 1 | 21 | +12.7% |
| a 60, r 2 | 432 | +11.1% |
| a 55, r 2 | 901 | +4.9% |
| a 70, r 3 | 24 | +1.4% |
| a 65, r 1 | 51 | -0.0% |
| a 55, r 3 | 202 | -0.4% |
| a 60, r 3 | 117 | -0.8% |
| a 60, r 1 | 117 | -9.2% |
| a 55, r 1 | 226 | -16.2% |
| a 65, r 3 | 55 | -16.6% |
