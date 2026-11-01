# Steam timing on the Kalshi path: chase, wait, or fade? (2026-11-01)

Follow-up to docs/betlabs_market_moves_2026-11-01.md (closes under-react in totals and NHL ML, so where is the value along the
way?). Script: sharp/steam_timing.py; full cells in data/research/steam_timing.json.

Data: every settled Kalshi game market with 20+ pregame fills (plus the Novig public tape where it has them), one market per
game x type (ladders: the strike closing nearest 50c). Steam = the first time the two-sided mid moved M points (3 / 5 / 8) inside
W minutes (15 / 60), at least 30 minutes before the start. Entries at the ask: at once, +5m, +15m, +60m, T-15m, and on a dip (the
first time the move gives back 40%). Each graded following the steam and fading it. Train = before Oct 1, test = October.

## What the path does after steam

| Steam | Events (train / test) | Mid drift, event to close | Gave back 2+ pts from the peak |
|---|---|---|---|
| 3+ pts in 15 min | 734 / 713 | -0.35 / -0.25 | 43% / 47% |
| 5+ pts in 15 min | 282 / 295 | -0.66 / -1.38 | 50% / 57% |
| 8+ pts in 15 min | 118 / 133 | -1.36 / -2.49 | 49% / 62% |
| 5+ pts in 60 min | 337 / 351 | -0.85 / -1.31 | 50% / 53% |

On Kalshi a fast move peaks early and partly comes back: about half of them give back 2+ points before the close, and the
average close is below the price at the steam point. "Overshot and got bet back" is real on the exchange path.

## Entry timing (pooled, all sports and markets)

| Steam | Entry | Follow, train | Follow, test | Fade, train | Fade, test |
|---|---|---|---|---|---|
| 3+ in 15 min | at once | -5.5% (CLV -1.4) | +1.3% (-1.5) | -0.4% | -6.7% |
| 3+ in 15 min | T-15m | -3.6% (CLV -0.6) | +5.3% (-0.5) | +3.1% | -4.5% |
| 5+ in 60 min | at once | -4.9% (CLV -2.3) | -2.3% (-2.9) | -5.5% | +1.8% |
| 5+ in 60 min | +60m | +6.2% | -3.3% | **-24.6%** (z -2.8) | **-15.3%** (z -1.9) |
| 3+ in 60 min | dip (40% given back) | -10.3% | -2.6% | **+5.5%** (n 296) | **+6.4%** (n 326) |
| 5+ in 60 min | dip | -12.6% | -7.0% | **+9.0%** (n 122) | **+11.5%** (n 138) |

## What this says

1. Chasing exchange steam at once is the worst follow entry: you pay the top of the move plus the spread (CLV -1.4 to -4.6).
   Waiting until just before the start costs much less (CLV about -0.5) but still does not win on both periods.
2. A move that holds for an hour is real: fading it loses 15-25% on both periods. That is the firmest result here, and it is
   a "don't".
3. The bet-back case: once a steam has given back 40%, the reversal side won on both periods (+5.5% / +6.4% for 3+ point moves,
   +9.0% / +11.5% for 5+). Holdout z about 1 and CLV slightly negative, so it is a candidate, not a rule: paper-track it forward.
4. By sport the cells are too thin to read (most under 30); the pooled numbers are the result.
5. Kalshi steam is measured on Kalshi's own mid, so some of it is a thin book being walked and refilled. The next step (the
   5-minute tape: Pinnacle moves vs when Novig / Kalshi / FanDuel / Caesars follow) separates real information from that.
