# Bet Labs audit, round 2: NHL, NCAAB, and the 1H / 2H segments of NFL, NBA, CFB (2026-10-30)

Same method as the first three audits (docs/betlabs_nfl_audit_2026-10-25.md): Bet Labs regular-season data 2003 to present at
closing lines, train 08/01/2003 to 02/28/2021, holdout 03/01/2021 to 10/30/2026. For every filter on a screen the scanner
(sharp/betlabs_scan.js, injected into the Bet Labs screen page) pulls the per-value record under each date range; the best
contiguous window per numeric filter in train (n >= 500, or 300 for NFL segments) is graded on the untouched holdout, with the
top-40 training windows' holdout flip count as the noise reference. List filters are read value by value. NHL and all moneyline
screens are ranked by ROI z (puck-line and NHL-total juice is not -110); spreads and totals elsewhere by win% z against 52.38%.
Raw per-screen output is in data/betlabs/scans_2026-10-30.txt. Screens were built with "Build" as "Audit: ..." and deleted after.

## Verdict table

| Screen | Side | Filters | Best in-sample (train) | Same window on holdout | Call |
|---|---|---|---|---|---|
| NHL totals | Under | 328 | O/U juice -125 and heavier, z 5.7 | 756 games, -14.4% | dead |
| NHL totals | Over | 327 | Total bets band, z 2.3 | -6.5% | dead; one lean (below) |
| NHL moneyline | Dog | 337 | ML +198 to +227, +12.5% | 462 games, -11.0% | dead |
| NHL moneyline | Favorite | 343 | Open ML -109 to -105, +10.6% | -5.9% | dead |
| NHL puck line | Dog +1.5 | 353 | Pythag win% 33-40, +4.2% | -3.7% | dead; one lean |
| NHL puck line | Favorite -1.5 | 361 | Game number 71-73, +19.3% | -14.7% | dead; two leans (below) |
| NBA 1H totals | Under / Over | 399 | z 2.6 / 2.9 | flip 40/40 both | dead |
| NBA 1H spread | Dog / Fav | 388 / 387 | z 3.1 / 2.8 | flip 40/40 both | dead |
| NBA 2H totals | Under / Over | 398 | z 3.3 (era drift) / Warriors-only | flip | dead |
| NBA 2H spread | Dog / Fav | 403 | off-efficiency z 3.5 / def 3P% z 2.2 | flip 38-40/40 | dead |
| CFB 1H totals | Under / Over | 133 | wind 15-25, z 2.5 / z 2.4 | +1.0% on 155 / -10.9% | dead |
| CFB 1H spread | Dog / Fav | 221 / 222 | team-stat windows z 2.4 / 2.9 | 40/40 flips on odds filters | dead |
| CFB 2H totals | Under / Over | 150 | home up 31+ at half, +14.6% / z 2.1 | 0% since 2021 / -6.8% | dead |
| CFB full game, situational lists only | Dog / Fav | 108 / 107 | ATS streak -2, z 1.2 / z 0.3 | +1.1% / 0% | dead |
| NFL 2H totals | Under / Over | 126 | redzone-eff windows z 3.2 / z 2.0 | +1.4% on 218 / -4.4% | dead |
| NFL 2H spread | Dog / Fav | 202 | yards-per-point z 3.1 / rush-yards z 3.1 | -5.1% / -3.9% | dead |
| NFL 2H moneyline | Dog / Fav | 195 | z 2.5 / rush-yards z 3.6 | thin (n 106-170) / -0.8% | dead |
| NCAAB totals | Under / Over | 391 | visitor FT 81.5-87, +20.7%, z 4.7 / z 2.7 | -2.4% on 305 / sliver | dead |
| NCAAB spread | Dog / Fav | 489 / 495 | season ATS margin, z 2.6 / opp def 3P%, z 3.6 | -2.5% on 1,311 / -2.1% | dead |

Thirty-six screen-sides, zero systems. The noise reference held everywhere: with 150 to 500 filters per side the best in-sample
z lands between 2.1 and 5.7 every time, and 30 to 40 of the top-40 windows go negative on the holdout.

## What the segments taught

1. Halftime-state rules were real and are gone. "Home up 31+ at half, 2H under" in CFB was 60.6% (+14.6%) through 2020 and
   52.6% since; NBA "game 11+ under pace at half, 2H under" went from +8.1% to +0.3%; NFL "favorite up 17-29 at half, 2H
   favorite" went from +10% to -11%. Second-half markets now price garbage time and pace correctly.
2. The NFL wind under does not transfer to CFB first halves (train +10.8%, holdout +1.0% on 155), and nothing in CFB or NBA
   first halves beats noise. The NFL 1H unders from the first audit remain the only 1H rules with support.
3. Big samples do not rescue the method: NCAAB has 76k totals and 78k spreads on file, the in-sample z reaches 4.7, and the
   holdout still flips. More data finds more noise, not more edge.
4. Season team-stat windows (rush yards, fumble %, redzone efficiency) dominate the "alive" lists in CFB and NFL segments with
   0/40 flips and thin holdouts. That is the signature of a stat computed on the full season (including games after the bet),
   not a point-in-time number. They are excluded from systems unless the field is confirmed season-to-date.
5. Era drift is a real failure mode in NBA: offensive-points and efficiency windows that were extreme pre-2021 are now the
   league average, so the "window" selects a different population on the holdout.

## Leans (not systems): forward-test candidates

Each is positive on both halves with a low flip count but fails the n >= 300 holdout bar or the mechanism test. They go into
the tracker as paper tags, graded on real closes, and nothing else.

| Tag | Rule | Train | Holdout | Flips | Why it might be real |
|---|---|---|---|---|---|
| nhl_pl_fav_gap | NHL favorite -1.5 (plus money) when favorite win% minus opponent win% is 22+ pts | 502, +17.4% | 196, +14.6% | 0/40 | Puck-line favorites at plus money are a longshot-bias product; strong-vs-weak is where blowouts live |
| nhl_pl_fav_strong_opp | NHL favorite -1.5 when the opponent's win% is 66%+ | 992, +11.9% | 405, +12.8% | 3/40 | Same family; two strong teams, the favorite's -1.5 is priced off the ML not the margin distribution |
| nhl_pl_dog_bigml | NHL dog +1.5 when the opening ML is +181 to +196 | 810, +6.0% | 310, +7.4% | 11/40 | Big dogs keep games close; the +1.5 price does not fully credit it |
| nhl_over_busy_goalie | NHL over when the home goalie's season saves/game is 31.1+ (tracker proxy: home shots against 34+/game) | 934, +7.0% | 322, +6.0% | 0/40 | A goalie facing 31+ shots a night sits behind a defense that leaks; total is set on goals, not shots |
| nba_1h_under_hot_over | NBA 1H under when the visitor's games have gone over 71%+ of the time | 508, +8.4% | 257, +6.1% | 6/40 | Regression to the mean on a team's over rate; the same shape appears in CFB 1H (+5.1 / +5.3) |

The two puck-line favorite rules overlap little (strong vs weak, strong vs strong) and should be tracked as one family:
"NHL puck-line favorites are underpriced when the moneyline is short". Combined they fire roughly 2 to 4 times a night.

## Screens

All "Audit: ..." screens created for this round were deleted after the scan; the "Tested:" systems from the first round are
unchanged. No new "Tested:" screens were created, because nothing met the bar. The leans live in sharp/systems.py as paper tags.
