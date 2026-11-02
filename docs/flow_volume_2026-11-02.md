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

## Sport-specific sharps vs one cross-sport list (sharp/sport_sharps.py, data/research/sport_sharps.json)

Sean, 11/2: every sport likely has its own sharps; is that sustainable, or does the cream rise across all sports? Two walk-forward
folds: A scored before 2026-03-01 and followed Mar to Aug; B scored before 2026-09-01 and followed since. Groups: GENERAL (cross-sport
top 200), SPORT top 50 (that sport's fills only, 20+ fills on 10+ games), SPECIALIST (sport top 50 not in the general top 200), BOTH
(in both). Entry 5 minutes after the first member fill, CLV vs Polymarket's close.

| Sport, fold | General top 200 | Sport top 50 | Specialist | Both | Sport bottom 50 |
|---|---|---|---|---|---|
| NBA A | +0.85 (1,477) | +0.95 (436) | -0.02 (66) | +1.09 (383) | -0.31 |
| NBA B | +0.90 (518) | +0.84 (38) | | +0.87 (37) | -0.25 |
| NFL B | +0.74 (551) | +0.40 (789) | +0.30 (786) | +1.53 (69) | -0.35 |
| NHL A | +0.82 (420) | +0.91 (415) | +0.71 (288) | +0.89 (286) | -0.68 |
| NHL B | +0.60 (196) | +0.79 (105) | +0.61 (84) | +1.57 (30) | -2.23 (15) |
| Soccer A | +0.75 (334) | +0.68 (310) | +0.98 (51) | +0.65 (309) | -0.22 |
| Soccer B | +1.04 (547) | +1.11 (534) | +1.31 (33) | +1.11 (531) | -0.05 |
| CFB B | +0.50 (638) | +0.59 (538) | +0.59 (538) | | -0.09 |
| WNBA A | +1.19 (327) | +0.64 (266) | +0.51 (241) | +1.81 (26) | |
| WNBA B | +1.40 (110) | +1.03 (149) | +0.81 (109) | +1.44 (106) | -0.34 |
| UFC A | +0.52 (138) | +0.99 (127) | +1.08 (126) | | |
| UFC B | -1.53 (80) | -0.47 (95) | +1.70 (83, z 0.9) | -2.78 (40) | |

Persistence (correlation of an account's train CLV with its test CLV, 10+ fills each side), sport-only score vs cross-sport score:
NBA 0.16 / 0.21 and 0.22 / 0.23; NFL B 0.35 / 0.44; NHL 0.24 / 0.22 and 0.62 / 0.37; soccer 0.45 / 0.44 and 0.37 / 0.46; CFB B 0.35 / 0.49;
WNBA B 0.41 / 0.42; UFC B 0.06 / 0.11.

Read:
1. Skill persists in every team sport, and the cross-sport score predicts an account's future at least as well as the sport-only score
   (higher in 6 of 9 comparisons). The cream does rise across sports: a good account is mostly good everywhere.
2. The best group is BOTH (sport-proven and in the cross-sport top 200): +0.9 to +1.8 pts, the top of every sport except UFC.
3. Specialists (good in one sport only) are positive in most sports but weaker than the general list (NFL +0.30, NHL +0.6-0.7, CFB +0.59;
   NBA about zero). They add coverage, mainly NFL and CFB, at a lower edge.
4. UFC is not sustainable: fold A looked strong (+1.0) and fold B fell apart (persistence 0.06). Keep UFC out.

## Player props (sharp/prop_sharps.py, data/research/prop_sharps.json)

Settled two-way Polymarket prop markets with $2k+ volume: 3,569 (NBA 1,925, UFC 928, NFL 351, MLB 130, WNBA 84, soccer 146), only 160k
taker trades in all. Test from 2026-06-27. Too thin to read: 37 accounts reach 15 prop fills on 8 markets before the cut, and the test
third has 522 markets, of which 320 had any $100+ fill. Following any $100+ prop fill: +0.13 pts CLV (z 0.2). Polymarket's prop board
is not liquid enough for an account signal yet; revisit when NBA and NFL prop volume builds.

## Live changes (11/2)

- The account list (data/state/poly_sharps_list.json) now marks each top-200 account's sports where it is also in that sport's own top 50
  (108 of 200). Such an account flags a game on its own, like a top-50 account.
- Sport specialists (a sport's top 50, not in the cross-sport top 200; 188 accounts, UFC excluded) are followed and their fills logged,
  but they do not flag. Their live record decides later whether they should.

## Specialists as the second account (sharp/specialist_rule.py, data/research/specialist_rule.json)

Scored before 2026-09-01, followed after (62 days), UFC excluded, entry 5 minutes after the trigger, CLV vs Polymarket's close.

| Rule | Markets a day | Games a day | CLV | z | ROI |
|---|---|---|---|---|---|
| R0 live (top 50, or top 200 also in its sport's top 50, or 2+ top 200) | 23.1 | 12.7 | +0.87 | 10.7 | +5.0% |
| R1 = R0 + a specialist can be the second account | 27.8 | 14.7 | +0.82 | 11.7 | +4.0% |
| the flags R1 adds | 5.0 | 4.0 | +0.45 | 4.7 | -1.1% |
| R1b = R1, and a specialist on the other side also blocks | 24.8 | 14.0 | +0.84 | 11.0 | +4.3% |
| R2 = any two of top 200 or specialists | 28.6 | 14.7 | +0.78 | 11.4 | +3.7% |
| the flags R2 adds | 5.8 | 4.1 | +0.35 | 4.0 | -2.1% |

Read: the flags specialists would add are real but carry about half the edge (+0.45 vs +0.87) and no profit at the result. Not turned on.
Note: with the sport-proven tier added today, the live rule now flags about 12-13 games a day (was 8-9) at +0.87 pts.

## Deeper history, four periods (11/2)

The Polymarket history was extended back past Gamma's paging limit (loggers/polymarket_history.py catalog_back): NBA to mid-2024, NHL to
December 2024, the full 2025 MLB season, CFB to September 2025; 3.76M more trades. Older UFC fight markets carry no start time and cannot
be used. sharp/sport_sharps.py rerun with four walk-forward periods (score on everything before the cutoff, follow until the next):
Jul 2025, Nov 2025, Mar 2026, Sep 2026. CLV vs Polymarket's close, entry 5 minutes after the first member bet (n in brackets).

| Sport | Cross-sport top 200, by period | Both lists, by period | Sport bottom 50 |
|---|---|---|---|
| NBA | +1.57 (289), +0.59 (5,012), +0.91 (1,424), +0.96 (496) | +2.51, +0.66, +1.10, +1.28 | +0.29, +0.20, -0.28, -0.25 |
| NFL | +1.08 (360), +0.85 (742), (11), +0.76 (538) | +1.07, +0.98, -, +1.53 | -0.45, -0.35, -, -0.35 |
| NHL | +0.66 (199), +0.56 (1,207), +0.83 (396), +0.60 (178) | +0.71, +0.60, +0.98, +1.77 (11) | -, -0.23, -0.60, -2.23 |
| MLB | +0.64 (952), -, +0.54 (360), +0.89 (115) | +0.49 (895), -, +1.45 (44), +0.47 (36) | -0.22, -, +0.14, - |
| CFB | +0.48 (256), +0.65 (739), -, +0.54 (623) | -, +0.63, -, - | -, -, -, -0.01 |
| Soccer | -, +0.39 (749), +0.69 (359), +1.10 (545) | -, -, +0.59, +1.14 | -, -, -0.21, -0.10 |
| WNBA | +1.43 (121), -, +1.19 (313), +1.39 (108) | +1.32, -, +1.81 (26), +1.43 | -, -, -, -0.34 |
| UFC | -, +0.39 (63), +0.43 (127), -2.69 (78) | -, -, -, -3.48 (39) | |

Persistence (an account's earlier CLV vs its later CLV) is positive in every sport and period with a sample, about 0.2 to 0.5, except UFC
in the latest period (0.06 to 0.12).

Read: over 16 months and four separate periods, the cross-sport top 200 beat Polymarket's close in every team sport in every period with a
sample (the one exception is NFL in Mar-Aug 2026 on 11 bets, the offseason). Accounts in both lists are usually the best. The worst
accounts in each sport stay at or below zero. MLB holds with a full season (+0.5 to +0.9). Specialists remain mixed. UFC stays out.

## Backtest of the watch's Strongest families (sharp/families_backtest.py, data/research/families_backtest.json)

Polymarket game markets, July 2025 to now (488 days), every family rebuilt from the market's own tape as of one hour before the start;
account list rescored walk-forward at each cutoff; price = Polymarket 4+ pt move since its first two-sided price (stand-in for the
Kalshi move; Pinnacle sharp moves and Kalshi bet-backs cannot be rebuilt that far back). Entry at the T-1h mid, CLV vs Polymarket's close.

| Class at T-1h | Markets | A day | CLV | z | ROI |
|---|---|---|---|---|---|
| 3 of 3 | 261 | 0.5 | +0.02 | 0.2 | +0.1% |
| accounts + money | 694 | 1.4 | +0.25 | 4.8 | +5.0% |
| accounts + price | 1,133 | 2.3 | +0.10 | 1.4 | +4.9% |
| Strongest (accounts + 1 or 2 others) | 2,088 | 4.3 | +0.14 | 3.0 | +4.4% (z 2.1) |
| accounts only | 4,016 | 8.2 | +0.13 | 4.7 | +2.4% |
| price + money, no accounts | 129 | 0.3 | -0.22 | -1.2 | -8.3% |
| price only | 1,356 | 2.8 | -0.14 | -2.8 | -3.2% |
| money only | 826 | 1.7 | -0.01 | -0.2 | -2.7% |

Read:
1. By one hour out most of the account edge is already priced (+0.13 here vs +0.87 entering 5 minutes after the account's bet): the value
   is in acting when the account bets, not in a later snapshot.
2. Adding families at T-1h barely helps. Money is the one useful partner (+0.25); a price move adds nothing (+0.10), and 3 of 3 is no
   better than accounts alone (+0.02 on 261).
3. Without accounts, price and money lose (price only -0.14, z -2.8).

## College basketball (11/2)

CBB was missing from every earlier test: 2025-26 college basketball game events on Polymarket carry the 'ncaa-basketball' tag, not
'cbb', so the history pull found none. Added (loggers/polymarket_history.py TAG_ALIAS): 12,550 game markets Nov 2025 to now, 1,458
with $10k+ volume, 572k trades. sharp/sport_sharps.py:
- scored before 2025-11-01, followed Nov 2025 to Feb 2026: cross-sport top 200 +0.39 pts CLV (423, z 3.0); persistence 0.38
- scored before 2026-03-01, followed through March: cross-sport top 200 +0.37 (87, z 1.3); CBB's own top 50 +0.18 (168); both lists +0.43 (67)
Read: the cross-sport sharps carry into CBB, at about half the edge of the other team sports; CBB-only specialists do not add. CBB added
to the live flags with the cross-sport list.
