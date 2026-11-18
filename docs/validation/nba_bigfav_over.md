# NBA big favourite over (nba_bigfav_over)

Verdict: **PAPER ONLY** (grid p 0.176; walk-forward +2.7% on 370 (p 0.200); holdout +10.1% on 136)

Live definition: t 0.855. Price: Pinnacle full-game close. Seasons: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26; holdout 2025-26. Base pool: 7103 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 446, record 246-194, units +36.71, ROI +8.2%. Flags: none. Leakage review: closing moneyline in the filter (graded at the same close).

| Season | N | ROI |
|---|---|---|
| 2020-21 | 62 | +19.4% |
| 2021-22 | 102 | +9.5% |
| 2022-23 | 48 | -7.2% |
| 2023-24 | 105 | +15.2% |
| 2024-25 | 129 | +1.9% |
| 2025-26 | 136 | +10.1% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 7 grid variants per shuffle (N >= 30): p = 0.176. Plain single-filter permutation (weaker): p = 0.018.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022-23 | t 0.855 | 48 | -7.2% |
| 2023-24 | t 0.88 | 57 | -4.9% |
| 2024-25 | t 0.855 | 129 | +1.9% |
| 2025-26 (holdout) | t 0.855 | 136 | +10.1% |

Out-of-sample before the holdout: -1.6% on 234. Holdout: +10.1% on 136. All walk-forward seasons: +2.7% on 370.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.200 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| t 0.82 | 775 | +4.6% |
| t 0.88 | 230 | +6.7% |

Plateau: yes.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| t 0.855 | 446 | +8.2% |
| t 0.88 | 230 | +6.7% |
| t 0.82 | 775 | +4.6% |
| t 0.8 | 998 | +4.1% |
| t 0.78 | 1215 | +3.9% |
| t 0.75 | 1586 | +2.9% |
| t 0.9 | 114 | -3.3% |
