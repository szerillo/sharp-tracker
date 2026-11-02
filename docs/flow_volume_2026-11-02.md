# Big vs small money, round 3: bigger fills, busier markets, Polymarket, and sharp accounts (2026-11-02)

Sean, 11/2: "Can we test Polymarket? Did you try filtering by bigger trades or more volume?" Script: sharp/flow_volume.py. Results: data/research/flow_volume.json.
Polymarket history: loggers/polymarket_history.py (29,959 settled game markets with $10k+ volume, 2024-08 to 2026-11, 22.5M taker trades; kept out of git).

## Pre-registered read (written in the script before results)

Each venue's games split by start time: first two thirds = train, last third = holdout. A version passes only with train n >= 100 and
z >= 2, then holdout n >= 50 and ROI > 0. Luck gives about 2.5% of versions a train z >= 2. Entry = two-sided mid at the entry time, no fee.

## Grid: 120 versions per venue

Entry T-6h / T-1h / T-15m; big cut $500 / $1k / $2.5k / $5k / $10k (single fills, risk-equivalent); DIV (big vs small) or BIG (big alone);
market volume before entry any / $25k+ / $100k+ / $500k+.

| Venue | Holdout from | Train finds (luck about 3) | Passed holdout |
|---|---|---|---|
| Kalshi | 2026-10-19 | 0 | 0 |
| Novig | 2026-10-04 | 0 | 0 |
| Polymarket | 2026-09-01 | 0 | 0 |

- Whales ($5k / $10k fills): flat to negative everywhere.
- Busy markets: Novig $100k+ markets looked +15-16% on train and went -3% in holdout; Polymarket $100k+ markets went -9% to -12% in holdout.
- Still a lean, nothing more: Kalshi $500+ vs small money at T-15m on $25k+ markets, +10.5% (n 184) train, +14.6% (n 81) holdout, z about 1.3 each.
- CLV about zero throughout: the price does not follow big fills.

## Sharp accounts on Polymarket (the one that works)

Every Polymarket fill carries its account (proxy wallet). Each account was scored on train (games before 2026-09-01) by the mean CLV of
its pregame fills of $100+ (fill price vs the side's two-sided mid at the start), minimum 30 fills on 15+ games: 3,687 accounts scored.
Holdout: follow a group's first $100+ fill per game x market, entering at the two-sided mid 1 / 5 / 15 / 60 minutes after it (not
their price). Graded on the result and on CLV vs Polymarket's own pregame close.

| Group | Lag | Bets | CLV pts | CLV z | ROI | ROI z |
|---|---|---|---|---|---|---|
| Top 50 | 1m | 169 | +1.57 | 3.8 | +0.3% | 0.0 |
| Top 50 | 5m | 170 | +1.06 | 2.7 | -3.0% | -0.4 |
| Top 200 | 1m | 3,679 | +0.80 | 11.1 | +3.2% | 1.6 |
| Top 200 | 5m | 3,693 | +0.64 | 8.9 | +1.7% | 0.9 |
| Top 200 | 15m | 3,552 | +0.50 | 6.5 | +0.8% | 0.4 |
| Top 200 | 60m | 3,121 | +0.39 | 4.5 | +1.6% | 0.8 |
| Top 1,000 | 1m | 5,439 | +0.70 | 11.6 | +3.7% | 2.3 |
| Top 1,000 | 5m | 5,388 | +0.59 | 9.8 | +2.5% | 1.5 |
| Bottom 200 | 5m | 327 | -0.20 | -0.6 | -5.3% | -1.0 |

Top 200 at 5 minutes, by sport: CLV positive in every sport but UFC (NFL +0.62, NBA +0.63, CFB +0.54, NHL +0.54, MLB +0.72, EPL +1.07,
UCL +1.25, Bundesliga +0.97, MLS +0.90, WNBA +1.00; UFC -1.53 on 86).

Read:
1. Account skill persists. Accounts that beat the close before September keep beating it after, in every major sport, and the edge
   decays the longer a follower waits (1m > 5m > 15m > 60m). The worst accounts stay at or below zero.
2. ROI is positive but not yet significant except top 1,000 at 1 minute (z 2.3). CLV is the stronger test at these sample sizes.
3. Caveats before betting it:
   - CLV is against Polymarket's own close. Part of it could be the account's own follow-up orders pushing the price, not information.
     Check against Pinnacle's close where we have it (our Pinnacle log covers October onward).
   - The account list must be rebuilt on a rolling basis; accounts change behaviour.
   - A follower needs to see the fill within minutes: the live Polymarket logger runs every 5 minutes (it now keeps the account).

Next: live paper test. Score accounts on all history to date, flag a top-200 account's $100+ pregame fill on the Today page as a
"Sharp account" signal (price family), log it with the price 5 minutes later, grade on CLV vs Pinnacle and on the result.
