# NBA under reconciliation and full-game systems split into derivatives (11/6)

Scripts: `sharp/nba_under_reconcile.py`, `sharp/deriv_split.py` (writes `data/research/deriv_split.json`).

## nba_under_good_home_over: why Bet Labs and our replay disagree

Bet Labs export (system 1789285, 445 picks, 2019-20 on) joined game by game to the odds database (405 matched; the 40 unmatched are 2019-20, before our data):
- Bet Labs as exported, at its own prices: 236-202, +3.6%. The +9.6% headline is the 2003-26 total; since 2019 it is +3.6%.
- Bet Labs' own picks graded at Pinnacle's close: 213-174, +7.4%. Scores match on every game. Lines are within half a point on 294 of 405.
- Our replay: 432 picks, 215-210, -1.4%. Of those, 290 are also Bet Labs picks (156-127, +7.6%), and 142 are ours only (59-83, -19.2%).
- Bet Labs picks our filter misses: 115 (57-47, +7.0%). Reasons: our opening total shows no 0.5+ drop (59), our home over% under 58 (45), no close inside 6 hours (16).
- Rest days match exactly (Bet Labs rest = our days off). Over% matches on 227 of 405, with ours usually 1-5 points lower.

So the data is not off: the same games grade the same. The two filters disagree on the borderline games (home over% 58-61, and whether the total dropped half a point from the open, which depends on whose opener). The 142 borderline games we add went 59-83.

Robustness grid on our data (ROI at Pinnacle's close; every game with the same rest and a 0.5 drop is -3.2% on 2,646):

| home over% | drop 0.5+ | 1.0+ | 1.5+ | 2.0+ |
|---|---|---|---|---|
| 54+ | -2.2% (788) | -0.2% | +2.0% | -0.2% |
| 56+ | -2.6% (608) | -1.1% | +1.9% | -0.5% |
| 58+ | -1.4% (432) | +2.0% | +6.8% (315) | +5.2% |
| 60+ | -1.9% (345) | +1.6% | +5.0% | +3.5% |
| 62+ | -4.8% (240) | -1.3% | +1.1% | -0.3% |
| 65+ | -3.7% (151) | +0.1% | -1.4% | -4.3% |

Reading: Bet Labs' exact game list is profitable, but moving a threshold a notch either way takes it to about break-even. The best neighbourhood is a bigger drop (1.5+), +5-7%. That pattern (one exact definition works, its neighbours don't) is what an over-fitted screen looks like. Recommendation: paper, or keep tier C only on games with a drop of 1.5 points or more.

## Full-game systems split into derivatives

Pinnacle derivative prices about 10 minutes before the start (mid-2023 to 2025-26, three seasons), graded on ESPN period scores. "Every game" = the same bet on every game in the window.

| rule | full game (same games) | best split | other splits |
|---|---|---|---|
| nba_under_good_home_over | 126-122, -1.1% | home team total under +3.1% (2/3 seasons) | 1H under -1.9%, 1Q under +2.9% (1/3), away TT under -13.9% |
| nba_1h_under_hot_over (visitor over 71%+) | 81-82, -3.3% | away TT under +8.9% (2/3) | **1H under 77-85, -7.8%, 0 of 3 seasons** |
| cfb_road_dog_low_total (TCU) | 70-62, +2.9% | 1Q road spread +6.9% (2/3) | 1H road spread -1.1%, 1H under -11.6% (0/3), 1H over +2.6% |
| cfb_homefav_7510_under | 81-61, +9.8% (3/3) | home TT under +6.1% (2/3) | 1H under -1.7%, 1Q under -1.2%, away TT under +3.2% |
| cfb_road_streak_dog | 104-113, -7.2% | 1H over +4.5% (2/3) | 1H road spread -7.7%, 1H under -13.7% |

No split clears the bar (every season positive, 100+ bets). The derivatives follow the full game: where the full-game rule works, its splits are weaker; where it does not, the splits do not rescue it. Splitting is not a source of extra edge.

The flag: `nba_1h_under_hot_over` (tier C, sized 0.5u by Sean) is the 1H under itself, and on real Pinnacle 1H lines it is 77-85, -7.8%, negative every season. Bet Labs' visitor over% may be defined differently, so this needs the same game-by-game reconciliation before the next fire.
