# Bet Labs vs the Odds API database: game-by-game reconciliation, 11/5/2026

Question (Sean): why did our Odds API replay disagree with Bet Labs' 03/2021-on holdouts on rules we had already audited there?
Method: pull each system's actual pick list from the Bet Labs screen (Past System Picks, 2020-26), match every pick to our database by
date and teams, and compare the line, the price, the result and whether our filter logic would have fired. Pick lists saved under
`data/research/betlabs/` (NBA under and NHL strong-opp game by game; the others as per-season records).

## What Bet Labs grades at
Real juice, not a flat -110: the pick lists carry the payout per win (NBA unders pay 87 to 104 per 100; puck lines pay +85 to +231).
The earlier audit note that Bet Labs "grades at -110" was wrong.

## NBA under, good home over team, rest, total down (1789285)
- 445 picks since 2020; 392 matched to our database with a Pinnacle closing total and a result.
- Line: Pinnacle's close vs Bet Labs' line: mean +0.08, median 0; same W/L/P result on 379 of 392. The lines agree.
- Price: same games graded at Pinnacle's close and price: **+7.8%** (Bet Labs' own grading +6.4%). By season: 2020-21 +4.9, 2021-22 +9.8,
  2022-23 +10.0, 2023-24 +6.7, 2024-25 +11.0, 2025-26 +1.1, 2026-27 (8 games) +70. Positive 6 of 7.
- Filter: our replay logic fires on only 243 of their 392 picks. 117 fail our "total down 0.5+" because OUR open is Pinnacle's first
  posted number in the bulk pulls, which for NBA is the snapshot the morning of the game, not the true opener. Bet Labs' change is
  measured from the real open. 46 fail our home over%, mostly early-season count differences.
- Verdict: the rule is real at our prices. Our replay's -0.5% was testing a different set of games. **Back to tier B.** Lesson: every
  "open to close" feature in the replays and the angle miner is a same-day move, not an open-to-close move, until the opens are re-pulled.

## NHL puck line favourite vs opponent winning 66%+ (1784155)
- 445 picks since 2020; 405 matched; result agrees on 405 of 405.
- Price: Bet Labs' own grading +10.4%; same picks at Pinnacle's closing puck-line price **+7.4%**. Pinnacle's puck line pays about 3 points
  of ROI less than the price Bet Labs records.
- Filter: ours fires on 344 of 405. The misses are win% definition: Bet Labs' win% excludes overtime/shootout losses (W/(W+L)); ours
  counted them as losses, so opponents at 63-65% by our count were 66-71% by theirs. The 319 games both pick: Pinnacle price -1.1%,
  Bet Labs grading +5.6%. The 46 we miss: +22% by Bet Labs' grading.
- Verdict: positive at our prices but carried by the price and by the fringe games; 2023-24 -22%, 2025-26 -4%. **Tier C.** Live rule
  should use regulation win% (exclude OTL) to match.

## CFB conference road dog 7+, total 48 or less (1789286)
- Bet Labs' own picks 2020-26: 153-117, positive 6 of 7 seasons (2020 +14.8, 2021 +21.4, 2022 +9.3, 2023 +8.5, 2024 +3.0, 2025 +4.5,
  2026 -4.7 on 20 games).
- Our replay had no conference flag (420 games vs their 270) and came out flat. The live rule has the flag. **Back to tier B.**

## CBB under, good over teams, total down (1792184)
- Bet Labs' own picks 2020-26: 309-262, about +3.5%; 2022-23 -2.1, 2023-24 -6.0, 2024-25 -1.5, 2025-26 +13.7. Same open-line issue in
  our replay. Thin and mixed either way. **Tier C.**

## CFB conference road streak dog (1792198) and NHL fav win% gap 22+ (1784154)
- Road streak dog: 49-41 since 2020 (2023 -30%, 2024 -13%); Bet Labs also filters on a heavy-bet day we cannot see. Stays paper.
- Fav gap: 109-138 since 2020 at plus money, ROI positive 5 of 7 seasons but swinging -21 to +68. Stays tier C.

## What this means for the rest of today's work
1. Bet Labs' pick lists, graded at Pinnacle's close, are the right independent test of a Bet Labs rule. Our replay re-implements the
   filters and gets them subtly wrong (opens, OTL, conference). Use the pick lists.
2. Totals lines agree between the two sources; puck-line prices are ~3 points richer at Bet Labs than at Pinnacle's close.
3. Our bulk pulls' "open" is a morning number. Any move-based result in `market_replay`, `nfl_replay` (B6) and the angle miner's
   `sp_move` / `tot_move` features measures same-day movement only. True opens need an earlier snapshot per game (one extra historical
   call per game day, ~10 credits each); worth doing for NBA, NFL and CFB before trusting any move angle.
