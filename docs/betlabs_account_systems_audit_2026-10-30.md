# Bet Labs audit, round 3: the 136 systems already in the account (2026-10-30)

Every system in the account that this project did not build (your own older ones plus the Bet Labs PRO set that comes
pre-loaded) graded the same way as rounds 1 and 2: record under a train window (08/01/2003 to 02/28/2021) and under the
holdout (03/01/2021 to 10/30/2026), by adding a temporary date filter to each screen and removing it afterwards. No screen was
changed. Raw table: data/betlabs/account_systems_audit_2026-10-30.psv (train and holdout W-L-P and dollars at $100 a unit).

The PRO systems were published before 2021, so for them the holdout is a true out-of-sample test. Your own systems built after
2021 have no train record and only a live one; those are listed separately.

## Result

82 systems have enough data on both sides (train n >= 100, holdout n >= 50). 48 are negative on the holdout. 34 are positive on
both; ranked by holdout ROI z, only two clear z 2:

| System | Market | Train | Holdout | z |
|---|---|---|---|---|
| NFL Wind (766902) | NFL O/U | 686, +10.2% | 225, +17.0% | 2.3 |
| Windy Unders (PRO) (766921) | NCAAF O/U | 805, +12.9% | 233, +15.5% | 2.2 |

These are the parents of the two wind systems already kept as "Tested:" (NFL Wind 10-14 Under; CFB Wind 14 Plus Under). The
account audit therefore confirms the earlier finding and adds nothing new at the system bar.

Next tier (positive both halves, holdout z 1 to 1.5; watch, not bet):

| System | Market | Train | Holdout | z | Note |
|---|---|---|---|---|---|
| At Home, Quality Opponent, Early Season (PRO) (766996) | NHL ML | 1,459, +3.0% | 463, +7.2% | 1.4 | early-season home ML vs good opponent |
| Bet Against Public After Bad Game (PRO) (766869) | NFL spread | 248, +18.2% | 54, +16.9% | 1.1 | n 54; public-money family, which has failed every other test here |
| Unders on Good Home Over Team (PRO) (766963) | NBA O/U | 978, +10.9% | 344, +6.4% | 1.1 | same regression-to-the-mean shape as the nba_1h_under_hot_over lean |
| Road Dogs Low Totals (PRO) (766923) | NCAAF spread | 645, +14.9% | 238, +7.3% | 1.0 | |
| High Seed Faves Off a Loss as Fave (1461278) | NCAAB ML | 164, +7.5% | 58, +14.2% | 1.0 | tournament only, thin |
| Teams Off Big Loss vs Ranked Opponent (PRO) (766983) | NCAAB spread | 177, +23.1% | 66, +13.0% | 1.0 | thin |

Everything else positive on both halves is +0 to +5% on the holdout with z under 1: the usual shrinkage of a published system.

## Notable fails on the holdout (train strongly positive, holdout clearly negative)

Under Streak (MLB, -5.0k on 1,400), Under with Good Over Teams (NCAAB, -4.4k on 983), Dog Against the Public off of Big Win (MLB,
-4.7k on 650), Non-Public Road Dog (MLB, -3.7k on 1,564), Tickets vs Money NHL Dogs (-3.0k on 767), Road Dogs Off ATS Loss (NBA,
-2.6k on 682), Pythagorean Point Differential (NFL, -2.8k on 171), Well Rested Visiting Faves (NHL, -2.3k on 484), Weather: Wind
Blowing In (MLB, -2.7k on 846). Every contrarian / public-money system in the account is flat or negative since 2021.

## Your post-2021 systems (no train window)

MLB F5 (6179-6181, -734 units: a whole-population screen, not a system), MLB F5 Spread, MLB Totals and MLB Totals - copy (same),
Umpire (1200-1194, flat), NCAA 1H / NCAA 1H ML (flat), NCAA Tourney Ball (61-34-1, +21.8 units on 95: tournament totals, worth a
proper filter-by-filter scan before March), Wild Card Under (22-7-3, +12.9 units, n 32).

## What changes

Nothing is added to the tracker from this round. The two wind parents are already covered. The NHL early-season home ML and the NBA
"good home over team under" screens are recorded here as watch items with the pinned Bet Labs queue (ROADMAP §9) and could be
scanned filter by filter in the same way as rounds 1 and 2 if wanted.
