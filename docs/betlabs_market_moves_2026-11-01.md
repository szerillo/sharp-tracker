# Do line moves overcorrect? Every game in Bet Labs, open to close (2026-11-01)

Sean's question: when a line moves from open to close, does the close overshoot (so the side the money pushed away from is the
value), is the move right but short (so following still pays at the close), or do the books just win both sides?

Method. Blank Bet Labs screens per sport and market (regular season, full game; "Scratch: Market Move Study ..." 1789367-1789377).
For each game, the side the line moved toward ("follow") and the side it moved away from ("fade"), bucketed by the size of the
open-to-close change (Spread / O/U Change Open to Close in points, Moneyline Change in cents). Graded at the closing price, vig
included, so -4.5% is "the books won". Train 08/2003-02/2021, holdout 03/2021-10/2026. Raw buckets:
data/research/betlabs_market_moves_2026-11-01.txt. Script: sharp/betlabs_moves.js (screen helpers) + the summary in this doc.

## All moves

| Market | Follow, train | Fade, train | Follow, holdout | Fade, holdout | Read |
|---|---|---|---|---|---|
| NFL spread | 3,448 -2.1% | -2.3% | 1,305 -6.8% | -1.6% | books win; no direction |
| NFL total | 3,886 -5.1% | +0.1% | 1,351 -1.9% | -6.8% | flips between periods |
| CFB spread | 10,192 -3.8% | -1.6% | 3,631 -3.9% | -4.9% | books win |
| CFB total | 9,966 -0.6% | -5.2% | 3,670 -3.6% | -5.5% | fade worse, both lose |
| NBA spread | 15,193 -2.9% | -1.8% | 5,864 -3.7% | -4.6% | books win |
| NBA total | 17,239 -0.2% | -4.5% | 6,297 -1.2% | -7.2% | close under-reacts; fade loses most |
| NHL ML | 17,374 -2.4% | -1.7% | 6,667 -1.8% | -7.3% | flat before 2021, fade bad since |
| CBB spread | 46,754 -2.7% | -2.9% | 15,761 -3.8% | -5.1% | books win |
| CBB total | 43,621 -2.3% | -4.9% | 17,697 -3.0% | -6.1% | close under-reacts, both lose |
| MLB ML | 36,238 -1.4% | -2.3% | 12,834 -4.4% | -2.6% | books win |
| MLB total | 14,679 -1.4% | -3.3% | 7,414 +0.1% | -7.9% | close under-reacts (half-run moves) |

## Big moves only (2.5+ points, 35+ cents on ML)

| Market | Follow, train | Fade, train | Follow, holdout | Fade, holdout |
|---|---|---|---|---|
| NBA total | 6,103 -0.3% | -4.5% | 3,453 -0.1% | -8.4% |
| NHL ML | 688 +2.3% | -2.9% | 1,253 +2.5% | -12.2% |
| CBB total | 15,373 -2.2% | -5.1% | 5,973 -3.4% | -5.7% |
| NFL total | 740 -2.0% | -3.0% | 613 +1.0% | -10.1% |
| NFL spread | 651 +0.2% | -4.5% | 681 -4.5% | -4.2% |
| CFB total | 3,706 +0.3% | -5.9% | 1,540 -7.5% | -1.7% |
| NBA spread | 1,738 -1.9% | -2.7% | 1,841 -1.2% | -7.2% |
| MLB ML | 1,842 +1.1% | -4.1% | 1,241 -5.6% | -3.1% |

## What this says

1. No market overcorrects. Fading the move at the close does not win anywhere on both periods; the best fade numbers are
   single-period noise (NFL totals before 2021, CFB totals since).
2. Sides are efficient: NFL, CFB, NBA, CBB spreads and MLB moneylines lose about the vig on both sides of every move size.
   The books won.
3. Totals and NHL moneylines under-react: the side the line moved toward runs near break-even at the close and the side it moved
   away from loses 5 to 12%. The move is right and did not go all the way. Betting with it at the close is close to free, betting
   against it is the worst bet in the table. Practical rule: never take the other side of a big NBA / CBB total move or a 35-cent
   NHL moneyline move because it "went too far".
4. The one positive cell on both periods: NHL moneyline moves of 35+ cents, following at the close, +2.3% (688) and +2.5%
   (1,253). Thin (holdout z about 0.8), plausibly goalie news the close has not finished pricing. Watch list, not a rule.
5. NBA spread moves of 3.5-4.5 toward the dog (a favourite's star out) covered +13.5% (69) and +10.8% (99). Thin; watch list.
6. Bet Labs has open and close only. "Moved, overshot, and got bet back" needs the path, which the move tape (since 10/30) keeps
   (p0 -> p1 -> close per move); it is graded there as games settle.
