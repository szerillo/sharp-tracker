# NFL 1H visitor off 8-30 days under (vrest8_1h)

Verdict: **PAPER ONLY** (grid p 0.398; walk-forward +37.4% on 24 (p 0.020); holdout +37.4% on 24; no plateau)

Live definition: lo 8, hi 30. Price: 1H line 10 min before kickoff: Pinnacle, else US-book median. Seasons: 2023, 2024, 2025; holdout 2025. Base pool: 790 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 79, record 39-38, units -1.31, ROI -1.7%. Flags: N < 100 (thin). Leakage review: none.

| Season | N | ROI |
|---|---|---|
| 2023 | 38 | +6.4% |
| 2024 | 41 | -9.1% |
| 2025 | 36 | +35.6% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 15 grid variants per shuffle (N >= 30): p = 0.398. Plain single-filter permutation (weaker): p = 0.157.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2025 (holdout) | lo 10, hi 30 | 24 | +37.4% |

Out-of-sample before the holdout: n/a on 0. Holdout: +37.4% on 24. All walk-forward seasons: +37.4% on 24.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.020 (bar 0.05 with 1 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| lo 7, hi 30 | 264 | -11.9% |
| lo 9, hi 30 | 53 | +4.0% |
| lo 8, hi 15 | 79 | -1.7% |

Plateau: no.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| lo 10, hi 15 | 51 | +8.0% |
| lo 10, hi 30 | 51 | +8.0% |
| lo 9, hi 15 | 53 | +4.0% |
| lo 9, hi 30 | 53 | +4.0% |
| lo 8, hi 15 | 79 | -1.7% |
| lo 8, hi 30 | 79 | -1.7% |
| lo 10, hi 13 | 32 | -10.5% |
| lo 6, hi 15 | 289 | -11.6% |
| lo 6, hi 30 | 289 | -11.6% |
| lo 7, hi 15 | 264 | -11.9% |
| lo 7, hi 30 | 264 | -11.9% |
| lo 8, hi 13 | 60 | -14.6% |
| lo 6, hi 13 | 270 | -15.2% |
| lo 9, hi 13 | 34 | -15.8% |
| lo 7, hi 13 | 245 | -15.9% |
