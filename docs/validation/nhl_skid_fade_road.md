# NHL road team off a win vs home skid, puck line (nhl_skid_fade_road)

Verdict: **PAPER ONLY** (grid p 0.266; walk-forward +8.0% on 169 (p 0.210); holdout -48.8% on 19)

Live definition: k 3. Price: Pinnacle close on the main NHL spread (puck line). Seasons: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26; holdout 2025-26. Base pool: 7429 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 448, record 231-217, units +31.75, ROI +7.1%. Flags: none. Leakage review: none.

| Season | N | ROI |
|---|---|---|
| 2020-21 | 68 | -2.9% |
| 2021-22 | 112 | +9.3% |
| 2022-23 | 104 | +19.4% |
| 2023-24 | 83 | +5.0% |
| 2024-25 | 81 | -1.3% |
| 2025-26 | 89 | -13.4% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 4 grid variants per shuffle (N >= 30): p = 0.266. Plain single-filter permutation (weaker): p = 0.057.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2022-23 | k 3 | 104 | +19.4% |
| 2023-24 | k 5 | 26 | +6.5% |
| 2024-25 | k 5 | 20 | +4.8% |
| 2025-26 (holdout) | k 5 | 19 | -48.8% |

Out-of-sample before the holdout: +15.2% on 150. Holdout: -48.8% on 19. All walk-forward seasons: +8.0% on 169.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.210 (bar 0.01 with 4 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| k 2 | 850 | +3.4% |
| k 4 | 239 | +5.3% |

Plateau: yes.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| k 5 | 137 | +10.0% |
| k 3 | 448 | +7.1% |
| k 4 | 239 | +5.3% |
| k 2 | 850 | +3.4% |
