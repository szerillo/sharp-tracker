# Does the market move with our systems? Open-to-close line movement on every kept rule (2026-10-30)

Bet Labs carries opening and closing numbers, so for each system's games we can ask where the line went between open and close.
Field: O/U Change Open to Close (totals), Spread Change Open to Close (sides, from the bet team's perspective), Moneyline Change
Open to Close (ML). "Toward" = the market moved toward the system's side (total down for an under; the dog's number shrinking
for a dog; the favorite's ML shortening). ROI is at the close. Holdout = 03/2021 to now. Pulled with the scanner on the saved screens.

| System | Games (holdout) | Mean move, holdout | Toward / against / flat (holdout) | ROI when toward | ROI when against | Read |
|---|---|---|---|---|---|---|
| NFL wind 10-14 under (1772775) | 904 (233) | -1.8 pts | 69 / 27 / 4 | +19.9% (n 161) | +29.4% (n 62) | market moves with us 7 games in 10, under still wins either way: edge at open and at close |
| NFL Wind parent (766902) | 909 (225) | -2.1 | 72 / 22 / 6 | +13.6% | +25.8% (n 50) | same |
| CFB wind 14+ under (1783043) | 949 (227) | -1.9 | 69 / 22 / 9 | +4.4% (n 157) | +19.5% (n 51) | same; the close has absorbed more of it in CFB since 2021 |
| CFB Windy Unders parent (766921) | 1,028 (233) | -1.8 | 71 / 19 / 10 | +14.5% | +3.9% | same |
| NFL 1H wind 10-13 under (769171) | 698 (201) | +0.1 | 46 / 28 / 26 | +27.1% (n 92) | -18.9% (n 56) | 1H totals barely move; the edge is in the games where the 1H total did drop |
| NFL 1H visitor off 8-30 under (1772962) | 809 (223) | 0.0 | 35 / 26 / 39 | +28.6% (n 78) | +10.0% (n 58) | same shape |
| NFL 1H MNF under (1772963) | 287 (78) | +0.1 | 38 / 33 / 29 | +24.0% (n 30) | +0.9% (n 26) | same shape, thin |
| NFL awful-team dog (1772776) | 418 (82) | +2.7 pts against | 20 / 76 / 4 | -3.4% (n 16) | +26.8% (n 62) | the market keeps fading the awful team all week (the dog gets 2.7 more points by close) and the dog covers anyway: a CLV-negative winner |
| NFL 1H bounce dog (1772929) | 766 (198) | +0.5 against | 28 / 42 / 30 | +14.3% (n 55) | +2.0% (n 84) | mostly flat; edge in the games that moved toward the dog |
| CFB road dog low total (766923) | 883 (238) | +0.7 against | 38 / 50 / 12 | -3.4% (n 91) | +17.6% (n 118) | same as the awful dog: the number grows and the dog still covers |
| NBA under on good home over team (766963) | 2,943 unfiltered (863) | +0.9 | 41 / 53 / 6 | +5.3% (n 353) | -7.4% (n 461) | the saved screen IS the "total dropped 0.5+" subset: it is a follow-the-move under, and the unfollowed games lose |
| NHL early-season home favorite ML (766996) | 1,919 (460) | -6.9 cents | 60 / 36 / 4 | +5.3% (n 278) | +11.1% (n 166) | favorite shortens 6 games in 10; wins either way |
| NHL puck-line rules | | | 87% flat | | | the puck line does not move; the ML change is the right field and was not pulled |

## What this says

1. The wind family is priced by the market and still wins: the total drops about two points from open to close in windy games,
   and the under covers at the close whether or not it moved. Betting at open captures roughly 2 points of CLV on top. This is
   the only family where "positive CLV" and "positive results" both hold, which is why it is tier A.
2. Two rules win against the move: the NFL awful-team dog and the CFB conference road dog with a low total. The market keeps
   pushing the number away from them all week and they cover anyway (+27% and +18% on the holdout in exactly those games). A
   CLV gate would have retired both; results are the only test that applies to them.
3. The NFL first-half unders are flat on movement with the edge concentrated in the games whose 1H total did move down. For
   those three rules a late check of the 1H number against its open is worth adding as a condition (not done yet; it would be a
   new rule and needs its own audit).
4. The NBA "good home over team under" is a follow-the-move rule by construction (its own filter is "total down 0.5 to 9"); the
   tracker's version requires the drop from AN_Open, so it is reproduced correctly.

## Change made

Publication no longer waits for positive CLV. Every fire is shown as a flagged bet with its evidence tier (A: holdout z >= 2
and a mechanism; B: positive on both halves and most seasons; C: lean) and the forward W-L, ROI and CLV shown as diagnostics.
