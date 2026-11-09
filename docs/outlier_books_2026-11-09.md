# Outlier books: every prop market and every game line (11/9)

The question: the NFL rushing-yards result (docs/nfl_props_2026-11-08.md) says that when one book hangs a number well off Pinnacle's while
2+ other books sit on Pinnacle's, betting the side the gap favours at the odd book wins. Is that a general edge (a stale book) or one
mined bucket? Tested on everything we have that Pinnacle quotes.

Definitions used throughout. Outlier = Pinnacle hangs one number, the book hangs a different one, and 2+ other books agree with Pinnacle
(props: within a step; game lines: Pinnacle's exact number). The control is the same gap when the other books do not agree (Pinnacle is
the odd one). Bet the side the gap favours at the book's own number and price. One bet per game (or player), market and side. BetMGM never
bet. Pushes void. z is against the breakeven implied by the prices.

## Props (sharp/prop_outlier.py; snapshot 10 minutes before the start, graded on ESPN box scores)

**Small gaps lose in every sport, outlier or not.** A book half a point or a point off Pinnacle (1-4 yards in NFL yardage markets) loses
2-7% in every market, every sport, and the loss is the same whether or not the other books agree with Pinnacle. That is ordinary
disagreement and the vig.

| Sport, cut | Bets | Record | ROI | z | Seasons + |
|---|---|---|---|---|---|
| NBA, every market, gap 1 (outlier) | 20,033 | 11082-8951 | -3.6% | -6.0 | 0/4 |
| NHL, every market, gap 1 (outlier) | 6,524 | 4062-2462 | -4.6% | -5.1 | 0/4 |
| MLB, every market, gap 1 (outlier) | 2,596 | 1547-1049 | -2.0% | -1.2 | 0/3 |
| NFL, every market, gap 1-2.5 yds (outlier) | 11,147 | 5744-5403 | -2.6% | -3.0 | 1/4 |
| NFL, every market, gap 4.5-7 yds (outlier) | 631 | 351-280 | +5.1% | +1.3 | 3/4 |

**The edge is only at the extreme gap, in two markets.**

| Market | Cut | Bets | Record | ROI | z | Seasons + |
|---|---|---|---|---|---|---|
| NFL rushing yards | outlier, 4.5-7 yds | 82 | 54-28 | +24.1% | +2.3 | 4/4 |
| (neighbour) | outlier, 3-4 yds | 720 | 397-323 | +4.2% | +1.2 | 3/4 |
| NBA points under | outlier book 15%+ above Pinnacle's line | 165 | 111-54 | +18.7% | +2.7 | 3/4 (2026 -3%) |
| (neighbour) | 11-15% above | 985 | 511-474 | -6.5% | -2.3 | 0/4 |
| (control) | Pinnacle the odd one, 15%+, under | 196 | 107-89 | -1.5% | | 1/4 |
| NBA points over | outlier book 15%+ below | 101 | 56-45 | -0.2% | | 2/4 |

The NBA points unders are real games (144 of 145 played 10+ minutes; DNPs are not in the box and void): mostly bench and role players on
5-15 point lines where the book is 2-3 points above Pinnacle, i.e. a minutes or role change that Pinnacle and the market priced and one
book did not. Rebounds, assists and threes show nothing at any relative gap (unders about flat, overs -6% to -9%).

Read: the mechanism exists but only fires on news-sized gaps, and those are rare. A single threshold with a losing neighbour is at most
tier C, and the NBA one has a negative 2026. NFL rushing yards stays paper (live since 11/8). NBA points unders at 15%+ goes on the watch
list, not the board: it would need the points market added to the live props pull (about 10 credits per game per run).

## Game lines (sharp/line_outlier.py; Odds API history 2020-26, every snapshot inside 3 hours of the start)

About 100,000 games across six sports. Nothing.

| Sport | Spread, gap 0.5 outlier | Spread, gap 1+ outlier | Total, gap 0.5 outlier | Total, gap 1+ outlier |
|---|---|---|---|---|
| NFL (1,642 games) | 964 bets, -6.0%, 2/7 | 95, +0.9%, 3/7 | 1,106, -3.8%, 2/7 | 97, -10.4%, 4/7 |
| CFB (4,297) | 3,007, -4.9%, 0/7 | 573, -1.2%, 4/7 | 3,063, -2.6%, 3/7 | 749, -6.6%, 0/7 |
| CBB (19,483) | 14,924, -2.7%, 1/7 | 2,480, -1.0%, 2/7 | 12,092, -2.7%, 1/7 | 5,301, -3.7%, 1/7 |
| NBA (7,158) | 6,363, -1.9%, 2/7 | 476, -1.0%, 2/6 | 6,936, -3.4%, 0/7 | 1,881, -1.7%, 3/7 |
| NHL (6,920) | puck lines, n/a | 393, -6.3%, 2/6 | 3,590, -2.7%, 0/6 | |
| WNBA (657) | 542, +0.3%, 2/3 | 45, +21.4% (small) | 515, -4.2%, 0/3 | 143, +1.1%, 1/3 |

Splits by Pinnacle having just moved (book lagging), 4+ books agreeing, inside 1 hour, side and book were all run (data/research/outlier/
lines_<sport>.txt). The handful of positive slices are single books or single sides, about what chance gives across roughly 300 cuts:
NBA totals gap 1.5+ inside 1 hour 78-45 (+19.5%, 123 bets), CBB spreads at DK gap 1+ 290-219 (+6.7%, 7/7 seasons), WNBA totals unders
gap 1+ 35-17. None has a neighbour that agrees. The 24-hour window (NFL, CFB, NBA) is the same: half-point outliers lose in every sport.

Why the game lines are dead and props are not: game lines get the full attention of every book's trading desk, so a number off the
market is a deliberate shade (and is priced to lose), not a stale quote. Prop desks are thinner, and a stale prop after news is the only
place a real outlier survives. The price-lag version on game lines (same number, better price right after Pinnacle moves) is the
stale-book lean already live (sharp/stale_live.py); the snapshot spacing in this history is too coarse to retest it here.

## Files
- sharp/prop_outlier.py, sharp/line_outlier.py
- data/research/outlier/: props_<sport>.txt / .json, lines_<sport>.txt / .json (3-hour window), lines24_<sport>.txt (24-hour window)
