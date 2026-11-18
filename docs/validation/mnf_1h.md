# NFL 1H Monday night under (mnf_1h)

Verdict: **PAPER ONLY** (grid p 0.534; walk-forward +24.1% on 25 (p 0.090); holdout +24.1% on 25; no plateau)

Live definition: d mon. Price: 1H line 10 min before kickoff: Pinnacle, else US-book median. Seasons: 2023, 2024, 2025; holdout 2025. Base pool: 790 bets of this market.

## Gate 1: in-sample (all seasons before the holdout)

N 29, record 12-15, units -3.57, ROI -12.3%. Flags: N < 100 (thin). Leakage review: none.

| Season | N | ROI |
|---|---|---|
| 2023 | 16 | +7.8% |
| 2024 | 13 | -37.1% |
| 2025 | 12 | +45.5% |

## Gate 2: permutation (1,000 shuffles within season x price decile)

Best of 4 grid variants per shuffle (N >= 30): p = 0.534. Plain single-filter permutation (weaker): p = 0.508.

## Gate 3: walk-forward (fit on earlier seasons, bet the next blind)

| Season | Variant fitted | N | ROI |
|---|---|---|---|
| 2025 (holdout) | d mon_thu | 25 | +24.1% |

Out-of-sample before the holdout: n/a on 0. Holdout: +24.1% on 25. All walk-forward seasons: +24.1% on 25.

## Gate 4: walk-forward permutation (200 shuffles of the walk-forward seasons)

p = 0.090 (bar 0.05 with 1 walk-forward season(s)).

## Plateau (grid neighbours of the live definition, in-sample)

| Variant | N | ROI |
|---|---|---|
| d mon_thu | 54 | -8.6% |

Plateau: no.

## Whole grid (in-sample)

| Variant | N | ROI |
|---|---|---|
| d sun_night | 19 | +3.2% |
| d thu | 25 | -4.2% |
| d mon_thu | 54 | -8.6% |
| d mon | 29 | -12.3% |
