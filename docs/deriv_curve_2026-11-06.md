# Derivatives on the curve (11/6/2026)

Sean: assume markets are efficient; look for spots where derivative prices sit off the curve implied by the full-game numbers, the
way the tennis first-set work did. Script `sharp/deriv_curve.py`, results `data/research/deriv_curve_<sport>.json`.

## Method
For each game, every derivative outcome (first-half / first-quarter / period totals and spreads, period moneylines, team totals, every
line offered, Pinnacle and the US books, 10 minutes before the start) is priced from Pinnacle's FULL-GAME close alone: the outcome among
past games with a similar full-game total and spread, scaled to this game's numbers, leave-one-season-out. Then two questions:
1. Does that curve price add anything to Pinnacle's own derivative price? Logistic blend on Pinnacle's two-sided lines:
   logit(result) ~ Pinnacle + curve. A curve weight reliably above zero means the derivative is mispriced relative to the full game.
2. Graded bets where a book is 3%+ better than the curve price.

## Result: derivatives are on the curve almost everywhere
- Pinnacle's derivative prices beat the curve on log loss in every market of every sport (NFL, NBA, NHL, CFB, CBB, WNBA). The books
  know more about how a game splits than the full-game number does, so the books' prices off our curve are mostly our curve's error:
  "3%+ better than the curve" bets lose 3-7% everywhere.
- Curve weight in the blend is indistinguishable from zero (|z| under 1.6) in 27 of 28 markets.
- The one exception: **CFB team totals** (curve weight +0.40, z +3.0, n 4,340; Pinnacle's own weight only +0.42). Betting the side the
  curve prefers when it disagrees with Pinnacle's no-vig team total by 5+ points: 844-756, +3.6% at Pinnacle's own price (n 1,600;
  2023 +7.0%, 2024 +5.7%, 2025 -0.3%). Gap 8+: unders 194-154 (+7.7%).
- NFL team totals point the same way (curve weight +0.35, z +1.6): gap 8+ points 165-119, +14.3% (n 284; 2023 +19%, 2024 +32%,
  2025 flat), almost all overs.

## Reading
Mechanism for the football exception: team totals are derived from the spread and total, but football team scoring is lumpy (3s and
7s, key totals at 17, 20, 24, 27), so a derived team total can sit off the real distribution in a way a points-share model does not.
Every other derivative tracks the full game as well as the full game itself is priced. Next:
- Paper: CFB and NFL team totals where the curve disagrees with Pinnacle by 5+ (CFB) / 8+ (NFL) points, best price at the US books.
- A better curve before calling anything else efficient: more seasons (ESPN period scores back to 2020 for the curve history only),
  and key-number aware scoring distributions for football.
- The earlier-snapshot pull (research agenda section 4): derivatives may sit off the curve hours before the start and be fixed by kickoff.

## Update (11/6, 3am): curve history back to 2020
ESPN period scores pulled back to 2020 for NFL, CFB and WNBA, so the curve uses every past season (NFL 1,781 games, CFB 4,861).
- NFL team totals: the curve signal disappears (curve weight -0.19, z -0.7). The +14% from the 2023-25-only curve was noise.
- CFB team totals hold (curve weight +0.45, z +2.6). With the better curve, the edge is in UNDERS: Pinnacle team-total unders where the
  curve is 5+ points lower: 210-176, +7.3% (2023 +10.6%, 2024 +15.4%, 2025 -4.5%); team totals 27.5+ 121-92, +13.1%.
- CFB first-quarter totals: curve 5+ points lower than Pinnacle: unders 222-171, +6.2%, every season positive (+11.0, +6.8, +0.9).
- Paper candidates: CFB Q1 total under and CFB team total under when off the curve. Live needs the curve computed per game on our tape.

## Soccer on the curve (`sharp/soccer_curve.py`, `data/research/soccer_curve.json`)
Pinnacle's full-game close (1X2 no-vig and the main total, asian lines settled properly) fitted to two Poisson goal rates per game; both
teams to score, draw no bet, team totals and alternate totals priced from those rates (2,305 games, 2023-26).
- The curve ties Pinnacle on log loss in every market (BTTS 0.6794 vs 0.6784, team totals 0.6751 vs 0.6751, alternate totals 0.6393 vs
  0.6395). Blend weights +0.2 to +0.6, z under 1.6. Soccer derivatives are on the curve.
- Draw no bet off the curve loses 27%: plain Poisson under-counts draws, the known flaw; nothing to bet there.
- The one pocket: alternate-total UNDERS priced 6%+ above the curve: n 343, +18.0% (2023 +1.1%, 2024 +38.0%, 2025 +14.5%), positive at
  every line from 1.5 to 3.5 and at Pinnacle itself (n 207, +15.2%). Correlated rows (several books on one game) and long prices, so
  smaller than it looks. Paper candidate; recheck when the 2026-27 soccer backfill lands.

## CBB with the full pull (11/6, 4:30am)
15,754 games. Unlike the other sports, the curve adds real information to Pinnacle's CBB derivatives: first-half totals (curve weight
+0.61, z +4.9), first-half spreads (z +3.4), team totals (z +3.0).
- First-half totals where the curve disagrees with Pinnacle's no-vig by 7+ points: 313-231, +9.7% at Pinnacle's price, every season
  positive (+14.9, +11.3, +2.7); mostly unders (227-161, +11.6%). At 4+ points: +1.5%.
- First-half spreads and team totals: the information is there but it does not survive the price (about -1% to +2%).
- The same shape as CFB (first-quarter and team-total unders off the curve): derived period totals that sit above what the full game
  implies go under. Paper candidate; going live needs the curve computed per game from our tape.

## Live (11/6, 5am): `sharp/curve_live.py`, tier C
Runs in the 20-minute signals job. For games inside 3 hours: the Odds API's current odds (the backtest's source), Pinnacle's full-game
total and spread, the curve from `data/research/curve_pool_<sport>.json.gz` (every past game with period scores), Pinnacle's no-vig on
the derivative line. The live code replayed on the backtest data (leave-one-season-out pools) reproduces the result:
- **cbb_1h_total_curve** (gap 7+, either side): 323-238, +9.8% at Pinnacle; 2023 +14.2, 2024 +10.7, 2025 +4.1. At the best of
  FD/Caesars/DK when they hang the same line: 162-133, +3.5% (Pinnacle on the same bets +5.3%). **Tier C, 0.25u.**
- **cfb_q1_under_curve** (gap 5+, unders): 242-176, +8.8%; 2023 +14.6, 2024 +9.3, 2025 +3.0. At FD/Caesars/DK: 170-102, +18.4%.
  **Tier C, 0.25u.**
- **cfb_tt_under_curve** (gap 5+, unders): stays paper (2025 -4.5%).
- CFB first-half totals are not a rule: off the curve they were +1.2% at a 5-point gap and 2024 was -7.6%.

## MLB (partial pull, 11/6 5am: 2,246 games of 7,111)
First five innings (total, run line, moneyline), first inning, first three and team totals priced from the full-game total and run line:
on the curve everywhere (curve weight z between -1.4 and +0.4; every off-curve slice -4% to -9%). As expected: the first five depends on
the starters and the market prices them; the full-game number alone cannot see that. The MLB test that matters is the first five vs
the full game WITH starter and bullpen quality (Bartolo's pitcher data), not the curve alone.

## 2 hours before the start (11/6, 6am): CFB first-quarter unders promoted to tier B
Same markets pulled 2 hours before every start (`*_curve_t120m`), the curve built from THAT snapshot's Pinnacle full-game total and
spread, graded on period scores:
- **cfb_q1_under_curve: 296-189, +15.0% at Pinnacle; 213-124, +19.8% at the best of FD/Caesars/DK; 2023 +16.5, 2024 +18.7, 2025
  +10.0.** Stronger than at kickoff (+8.8%): the first-quarter line is softer early. **Tier B, 0.5u** (System bets on the board).
- cfb_tt_under_curve: 198-180, +2.5% (2023 -1.0, 2025 -2.0). Stays paper.
- cbb_1h_total_curve: Pinnacle rarely has a CBB first-half line 2 hours out (19 fires in the 2,080 games pulled so far, 12-7). Rescore
  when the CBB pull finishes; stays tier C.

## Scan of every sport's derivatives off the curve (11/6, 7am)
Every market, both gap bands (4-7 and 7+ points), each side, at Pinnacle's price and the best of FD/Caesars/DK. Many slices, three
seasons each, so a pocket counts only with a mechanism and every season positive. Sanity check on the CFB rule: ALL CFB first-quarter
unders at Pinnacle 2 hours out are 1157-1054, -1.6% (the vig); the curve picks out the profitable ones, it is not a blanket under lean.
New candidates (paper in `sharp/curve_live.py`, waiting for the 6-hour-before pull to confirm):
- **NHL first-period puck line (spreads_p1), gap 7+:** 161-107, +10.2% at Pinnacle, +10.4% at FD/Caesars/DK (2023 +3.8, 2024 +19.4,
  2025 +2.8 on 31). Curve weight z +2.4.
- **NHL third-period total UNDER, gap 7+:** 241-194, +10.9%, every season positive (+17.3, +4.7, +10.3). Few US books hang third-period
  totals pregame, so where to bet it is the open question.
Not pockets: NBA first-quarter spreads (2025 -5.8%), NFL first-quarter spreads (+5.7%, small), CBB first-half spreads (-1% / +3.6%),
NHL second-period totals (curve says over, loses), CFB first-quarter spreads (-0.7%).
