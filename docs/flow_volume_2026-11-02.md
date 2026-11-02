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

## Checks 1 and 2 (sharp/sharp_accounts.py, data/research/sharp_accounts.json)

Same scoring and split. First follow per group x market, entry 1 or 5 minutes after the account's first $100+ fill.

**1. Against Pinnacle's no-vig close** (moneylines and totals, games from 2026-10-29 when Pinnacle game lines start on our tape;
746 follows in the window, 231 graded: 187 no schedule match, 328 no Pinnacle quote on that line):

| Group | Lag | n | CLV vs Pinnacle | z | CLV vs Polymarket | ROI |
|---|---|---|---|---|---|---|
| Top 200 | 1m | 93 | +1.26 | 4.1 | +1.10 | +12.1% (z 1.1) |
| Top 200 | 5m | 92 | +1.11 | 3.7 | +0.90 | +6.6% (z 0.6) |
| Rest of scored | 5m | 126 | +0.01 | 0.0 | -0.06 | -0.2% |
| Bottom 200 | 5m | 8 | +0.67 | | | |

Read: the top accounts beat Pinnacle's close by as much as Polymarket's, so it is not their own orders moving Polymarket's price.
Thin (four days of Pinnacle), but z 3.7 with the rest of the accounts at exactly zero.

**2. With a Kalshi 4+ point move** (moneylines, NFL / NBA / NHL / CFB / MLB, Kalshi move from its first two-sided price to the follower's
entry, CLV vs Polymarket's close):

| Top 200, 5m | n | CLV | ROI |
|---|---|---|---|
| Kalshi moved 4+ the same way | 44 | +1.10 (z 1.5) | +17.2% |
| Kalshi under 4 | 166 | +0.99 (z 4.1) | -1.5% |
| Kalshi moved 4+ the other way | 57 | +0.24 (z 0.3) | 0.0% |

Read: an agreeing Kalshi move adds little to CLV; an opposing one cuts most of it. Use Kalshi as a veto, not a booster. Small samples.

## Round 2 cuts (sharp/sharp_accounts2.py, data/research/sharp_accounts2.json)

Sean, 11/2: bigger orders isolated, head-to-head, multiple positions, other angles. Holdout only (Sep 1 on), accounts ranked on train,
entry 5 minutes after the triggering fill, CLV vs Polymarket's close. These cuts were chosen after round 1, so read them as
descriptive, not as new pre-registered tests.

| Cut | n | CLV | z | ROI |
|---|---|---|---|---|
| A fill $100-500 (top 200) | 2,483 | +0.75 | 8.0 | +2.5% |
| A fill $500-2k | 2,021 | +0.62 | 7.0 | +5.5% (z 2.1) |
| A fill $2k-10k | 1,339 | +0.58 | 5.3 | -1.2% |
| A fill $10k+ | 331 | +0.74 | 2.4 | +2.8% |
| B rank 1-50 | 170 | +1.06 | 2.7 | -3.0% |
| B rank 51-200 | 3,181 | +0.64 | 8.5 | +2.2% |
| B rank 201-1000 | 3,598 | +0.53 | 7.0 | +4.3% (z 2.1) |
| B rank 1001+ | 3,295 | +0.19 | 2.4 | +2.3% |
| C first top-200 account in | 3,180 | +0.66 | 8.7 | +2.2% |
| C joins a top-200 already on that side | 1,448 | +0.81 | 7.7 | +0.6% |
| C another top-200 already on the other side | 1,759 | +0.56 | 5.0 | +3.2% |
| D head-to-head at T-15m: side with more top-200 $ | 1,512 | -0.03 | -0.5 | +2.0% |
| D head-to-head at T-15m: best-ranked account's side | 1,512 | -0.01 | -0.2 | -1.8% |
| E account's 1st fill | 6,387 | +0.67 | 12.2 | +2.1% |
| E 2nd fill, same side (adding) | 2,564 | +0.68 | 8.5 | +2.1% |
| E flip (already bet the other side) | 1,162 | +0.41 | 3.2 | -0.3% |
| F net top-200 $5k+, entered at T-1h | 707 | +0.44 | 2.8 | +1.9% |
| F net top-200 $1k+, entered at T-15m | 2,206 | +0.10 | 3.2 | +1.3% |
| G first top-200 fill 24h+ out | 540 | +1.04 | 4.1 | +3.5% |
| G 6-24h | 1,162 | +0.63 | 5.0 | +2.1% |
| G 1-6h | 807 | +0.71 | 4.3 | +1.0% |
| G under 1h | 671 | +0.36 | 6.7 | +2.9% |
| H moneyline | 1,125 | +0.92 | 6.0 | +8.4% (z 1.9) |
| H spread | 1,110 | +0.49 | 5.0 | -3.0% |
| H total | 945 | +0.53 | 4.0 | +0.9% |
| H followed side under 40c (dog) | 471 | +0.83 | 3.4 | +15.2% (z 1.6) |
| H 40-60c | 2,214 | +0.69 | 8.7 | +0.5% |
| H over 60c (fav) | 495 | +0.37 | 1.6 | -2.6% |

By sport (first top-200 fill): positive CLV everywhere but UFC (-1.52 on 66). Soccer and WNBA highest (+1.0 to +1.2), NFL / CFB / NBA
+0.6, NHL +0.5.

Read:
1. Size does not matter: a $100-500 fill from a top account carries as much as a $10k one. The account is the signal, not the bet size.
2. Rank matters, monotonically (top 50 > 51-200 > 201-1000 > the rest).
3. Two top accounts on the same side is the best case (+0.81). Head-to-head is weaker at the moment of the bet (+0.56), and once both
   sides have top money by 15 minutes out, nothing is left on either side (D about 0).
4. Adding to a position is as good as the first bet; a flip is weaker.
5. Speed matters: the same accounts' net position entered at T-1h or T-15m keeps only +0.1 to +0.4. Earlier bets (24h+) carry the most.
6. Moneylines and dogs carry the most; favorites the least. UFC is excluded.

## Follow the sharps, fade the squares (sharp/sharp_square.py, data/research/sharp_square.json)

Sean, 11/2: combine following sharps with fading bad bettors. Squares defined three ways on train (bottom 500 by ROI, bottom 500 by
CLV, both negative). Holdout, entry 5 minutes after the trigger, CLV vs Polymarket's close.

| Signal | n | CLV | z | ROI |
|---|---|---|---|---|
| Follow a sharp (top 200 by CLV) | 2,503 | +0.73 | 8.6 | +2.5% |
| Fade a square: bottom 500 by ROI | 1,203 | -0.25 | -1.9 | +3.7% (z 1.2) |
| Fade a square: bottom 500 by CLV | 986 | +0.18 | 1.3 | +0.4% |
| Fade a square: ROI and CLV both negative | 1,262 | -0.17 | -1.4 | -2.2% |
| Sharp on X and square on the other side (best version) | 613 | +0.46 | 2.7 | -2.1% |
| Sharp and square on the same side (bet the sharp side, best version) | 649 | +0.61 | 3.0 | -1.7% |

Read: fading squares does not work at the price a follower gets. Accounts with the worst past ROI are not picking the wrong side going
forward (fading them loses CLV); their past losses were mostly price (longshots, buying after the move) and luck, which a fade at the
next price does not capture. Adding a square on the other side does not improve a sharp bet (it triggers later, so it is worse), and
a square on the same side does not spoil one. Keep the signal to following sharps.
