# NBA weak home team vs weak visitor under (nba_badteams_under)

Verdict: **PAPER ONLY** (grid p 0.669; walk-forward +3.7% on 193 (p 0.150); holdout +3.6% on 72; no plateau)

Live definition: h 40, vlo 30, vhi 45. Price: Pinnacle full-game close. Seasons: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26; holdout 2025-26. Base pool: 7103 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 308, record 160-146, units +6.65, ROI +2.2%. Flags: none. Leakage review: none.

| Season | N | ROI |
|---|---|---|
| 2020-21 | 72 | +0.7% |
| 2021-22 | 64 | +6.2% |
| 2022-23 | 44 | +1.9% |
| 2023-24 | 54 | -2.7% |
| 2024-25 | 74 | +3.9% |
| 2025-26 | 67 | +10.0% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 36 grid variants per shuffle (N >= 30): p = 0.669. Plain single-filter permutation (weaker): p = 0.121.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022-23 | h 30, vlo 25, vhi 45 | 35 | +0.2% |
| 2023-24 | h 40, vlo 25, vhi 40 | 45 | +12.7% |
| 2024-25 | h 35, vlo 25, vhi 40 | 41 | -2.9% |
| 2025-26 (holdout) | h 35, vlo 25, vhi 45 | 72 | +3.6% |

Out-of-sample before the holdout: +3.8% on 121. Holdout: +3.6% on 72. All walk-forward seasons: +3.7% on 193.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.150 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| h 35, vlo 30, vhi 45 | 215 | +4.3% |
| h 45, vlo 30, vhi 45 | 399 | +0.1% |
| h 40, vlo 25, vhi 45 | 382 | +5.0% |
| h 40, vlo 35, vhi 45 | 249 | -0.4% |
| h 40, vlo 30, vhi 40 | 165 | -0.9% |
| h 40, vlo 30, vhi 50 | 506 | +1.6% |

Plateau: no.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| h 35, vlo 25, vhi 45 | 266 | +6.8% |
| h 30, vlo 25, vhi 45 | 194 | +6.6% |
| h 35, vlo 25, vhi 40 | 164 | +5.1% |
| h 40, vlo 25, vhi 45 | 382 | +5.0% |
| h 40, vlo 25, vhi 40 | 239 | +4.6% |
| h 35, vlo 30, vhi 45 | 215 | +4.3% |
| h 30, vlo 30, vhi 45 | 160 | +4.1% |
| h 30, vlo 25, vhi 40 | 116 | +3.8% |
| h 35, vlo 35, vhi 45 | 173 | +3.6% |
| h 40, vlo 25, vhi 50 | 580 | +3.6% |
| h 35, vlo 25, vhi 50 | 417 | +3.3% |
| h 30, vlo 25, vhi 50 | 307 | +2.5% |
| h 40, vlo 30, vhi 45 | 308 | +2.2% |
| h 30, vlo 35, vhi 45 | 131 | +1.7% |
| h 40, vlo 30, vhi 50 | 506 | +1.6% |
| h 35, vlo 30, vhi 50 | 366 | +1.4% |
| h 45, vlo 25, vhi 45 | 506 | +1.1% |
| h 45, vlo 25, vhi 50 | 787 | +0.7% |
| h 45, vlo 25, vhi 40 | 323 | +0.7% |
| h 35, vlo 35, vhi 50 | 324 | +0.7% |
| h 30, vlo 30, vhi 50 | 273 | +0.5% |
| h 45, vlo 30, vhi 45 | 399 | +0.1% |
| h 40, vlo 35, vhi 50 | 447 | +0.1% |
| h 45, vlo 30, vhi 50 | 680 | +0.1% |
| h 45, vlo 35, vhi 50 | 606 | -0.2% |
| h 45, vlo 35, vhi 45 | 325 | -0.3% |
| h 40, vlo 35, vhi 45 | 249 | -0.4% |
| h 35, vlo 30, vhi 40 | 113 | -0.4% |
| h 40, vlo 30, vhi 40 | 165 | -0.9% |
| h 30, vlo 35, vhi 50 | 244 | -1.2% |
| h 45, vlo 30, vhi 40 | 216 | -1.3% |
| h 30, vlo 30, vhi 40 | 82 | -2.2% |
| h 45, vlo 35, vhi 40 | 142 | -3.0% |
| h 35, vlo 35, vhi 40 | 71 | -4.9% |
| h 40, vlo 35, vhi 40 | 106 | -8.6% |
| h 30, vlo 35, vhi 40 | 53 | -11.6% |
