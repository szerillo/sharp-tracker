# Rescue tests for failed Bet Labs systems: results (2026-11-01)

Variants pre-registered in docs/betlabs_rescue_prereg_2026-11-01.md (committed before any results were pulled). Each variant was
run on a scratch copy of the system's screen ("Scratch: Rescue <id> ..."; the originals were not touched), at Bet Labs closing
lines, train 08/2003-02/2021 vs holdout 03/2021-now. ROI per $100 risked. 20 systems, 33 variants.

## The bar, corrected

The pre-registration said "about 3-5 passes expected on luck". That was wrong: every system was chosen for a strong train record,
so a variant is almost always positive on train, and with no edge left its holdout is positive about 45% of the time (the vig).
About 14-15 of 33 would pass "both positive" by luck alone. Only 5 did, so the decay these systems showed is real, and a pass needs
more than a positive sign: a holdout of 75+ bets and a holdout ROI clearly above zero.

## Results

| System | Variant | Train | Holdout | Read |
|---|---|---|---|---|
| 766922 CFB Weather Overs (hot, calm, non-conf) | A: total 55 or lower | 203, +16.4% | **92, +10.1%** | **candidate** (holdout z about 1.0) |
| 766924 CFB Road Streak (conf, 2-5 road games) | A: team is the dog | 214, +20.7% | **85, +5.3%** | **candidate, weak**; overlaps cfb_road_dog_low_total |
| | B: spread 14 or less | 310, +17.4% | 110, +0.6% | flat |
| 766981 CBB Under with Good Over Teams | A: total fell 0.5+ | 949, +7.6% | **497, +1.9%** | **weak** (holdout z about 0.4) |
| | B: closing total 145+ | 1,080, +7.5% | 622, -5.9% | dead |
| 766997 NHL Tickets vs Money Dogs | A: ML moved toward the dog | 229, +19.1% | 291, +0.3% | flat |
| 766927 CFB Bet Against Public w/ Line Move | A: team is the dog | 245, +10.7% | 32, +7.7% | thin |
| | B: conference game | 229, +14.9% | 44, +13.1% | thin; recheck as it grows |
| 766870 NFL Team ATS Records | B: spread 7 or less | 176, +18.0% | 59, +0.3% | thin, flat |
| | A: team is the dog | 235, +19.8% | 61, -5.9% | dead |
| 766974 CBB Contrarian Saturdays | A: line moved to the team | 148, +7.1% | 38, +0.9% | thin, flat |
| | B: team is the dog | 343, +11.8% | 65, -2.7% | dead |
| 766971 CBB Neutral Court Unders | A: total fell 0.5+ | 170, +21.6% | 113, -0.1% | dead |
| | B: team game number 5 or less | 537, +12.6% | 256, -3.6% | dead |
| 766970 CBB Top 15 Home Teams | A: spread 15 or less | 139, +3.8% | 24, +11.6% | thin |
| 766962 NBA RLM Unders | A: total fell 1.5+ | 174, +7.8% | 193, -4.5% | dead |
| | B: money minus tickets 10+ | 146, +11.1% | 176, -7.2% | dead |
| 766961 NBA Road Dogs Off ATS Loss | A: spread 4 to 10 | 1,048, +4.3% | 338, -2.8% | dead |
| | B: previous ATS loss 7+ | 967, +4.8% | 391, -4.3% | dead |
| 853058 NHL Well-Rested Vis Fav PL | A: opponent on 0-1 days rest | 89, +6.4% | 39, +1.3% | thin |
| 766995 NHL Well-Rested Vis Fav ML | A: opponent on 0-1 days rest | 89, +10.2% | 39, +0.9% | thin |
| | B: ML -170 or longer | 710, +12.6% | 292, -8.9% | dead |
| 825756 NFL Bad ATS vs Good ATS | A: week 9+ | 138, +21.8% | 31, -7.5% | dead |
| | B: team is the dog | 171, +25.9% | 45, -6.6% | dead |
| 774066 NFL Over After Both Went Under | A: total 44 or lower | 127, +15.4% | 53, -16.5% | dead |
| 822611 NFL Pythagorean | A: week 6+ | 285, +9.3% | 146, -16.4% | dead |
| | B: team is the favourite | 168, +4.1% | 92, -18.9% | dead |
| 772518 NFL Early Season Upsets | A: ML moved toward the dog | 111, +29.4% | 35, -7.4% | dead |
| 766866 NFL Road Trips w/ Line Move | A: team is the dog | 101, +21.7% | 13, +17.7% | too thin to read |
| 1331115 CFB Scoring Streak Fade | A: spread 14 or less | 313, +21.5% | 93, -11.7% | dead |
| | B: conference game | 291, +21.3% | 75, -5.7% | dead |
| 764707 CFB Small Visiting Dog | A: conference game | 1,059, +6.3% | 517, -5.8% | dead |
| | B: ML moved toward the dog | 734, +7.2% | 314, -8.2% | dead |

(Train counts can differ from the screen's own record when the variant's field is blank for some games, or when the variant's
field is also one of the screen's filters; the holdout read uses the same field, so the comparison is like for like.)

## What this says

1. Logic does not rescue most of these. 28 of 33 variants were flat or losing after 2021, fewer passes than luck alone would
   produce: the market has absorbed these angles, not just the specific cut points.
2. Two candidates, for paper tracking only:
   - CFB hot-weather overs (85F+, wind 10 or less, non-conference) with a total of 55 or lower: +10.1% on 92 since 2021. The reason
     holds (heat wears defences down late; the market prices the heat less on low totals). Season-bound: August-September.
   - CFB conference road dogs on their 2nd-5th straight road game, total 54 or lower, heavy-bet day: +5.3% on 85. Weak, and it
     overlaps the live cfb_road_dog_low_total rule (conference road dog of 7+, total 48 or lower); most of its value is probably that rule.
3. One weak lean: CBB unders with two over-heavy teams once the total has dropped (+1.9% on 497). The same shape as the live
   NBA rule (good home over team, total down); not strong enough alone.
4. Two thin positives to recheck as the holdout grows: CFB bet-against-public with line move in conference games (44 bets,
   +13.1%), CBB top-15 home teams with a spread of 15 or less (24 bets).
5. Not tested this round: MLB systems (spring), and the postseason / preseason screens.
