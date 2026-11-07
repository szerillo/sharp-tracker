# Props price-gap rules: thresholds, devig and Pinnacle freshness (11/7)

Sean, 11/7: would a higher edge cutoff, a tighter Pinnacle check or a window closer to tip raise ROI?
Script: `sharp/props_grid.py <nba|nhl> [props file]`. Odds API prop snapshots (every price taken 10 to 14 minutes before the start),
graded on ESPN box scores, flat 1u at the best FD / Caesars / DK under price, pushes void. Seasons 2023 to 2026.

## NBA threes unders (base: book 2%+ over Pinnacle's proportional no-vig)

| Filter | Bets | ROI | Seasons + |
|---|---|---|---|
| 2%+ (old rule) | 2,012 | +7.8% | 4/4 |
| 3%+ | 1,274 | +8.8% | 4/4 |
| 4%+ | 791 | +11.6% | 4/4 |
| power-devig 3%+ | 1,421 | +10.6% | 4/4 |
| book's own no-vig 4+ pts below Pinnacle's (new rule) | 1,655 | +9.8% | 4/4 |
| book's own no-vig only 2-4 pts below | 357 | -1.7% | 2/4 |
| Pinnacle quote 5-20 min old | 33 | -13.3% | 1/4 |

## NHL saves and shots unders

| Filter | Bets | ROI |
|---|---|---|
| 2%+ (kept) | 843 | +6.1% |
| 3%+ | 469 | +4.4% |
| 4%+ | 266 | +4.4% |
| fair gap 4+ pts | 627 | +6.9% (fewer units) |
| Pinnacle quote 5-20 min old | 16 | -8.9% |

## Changes (sharp/props_live.py, sharp/fairprice.py)
- NBA threes: the book's two-way no-vig must sit 4+ points below Pinnacle's no-vig (and the old 2% edge still applies).
- NHL: unchanged, 2%.
- Every prop: Pinnacle's quote at most 5 minutes old, and an edge on the stricter of the proportional and power no-vig.
- Flag window: the last hour before the start (was 3 hours). The backtest only knows prices 10 to 14 minutes out; an hour is a judgment
  call (most prop prices barely move in the last hour), so these flags keep grading as their own record.
