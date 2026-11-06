# Research agenda: where market inefficiencies should be (11/6/2026)

Sean (11/5): "it needs to start with finding market inefficiencies, which have to exist somewhere. And then within those inefficiencies,
finding our best opportunities." Pregame first; in-game later. Every candidate below has a reason it could exist (a mechanism), and every
result goes through the same gate: positive in each season of our data separately, a mechanism, and where Bet Labs can express the
filter (it has first-half lines for NFL, NBA, CFB and CBB going back two decades), the two-window test there.

## Data in hand or arriving tonight
Full-game 2020-26 (all sports, MLB 2026 and the soccer backfill pulling now). Derivatives, one pregame snapshot per game since 2023-05:
NFL and CFB halves and first quarters; NBA halves and quarters with first-half team totals; NHL all three periods, first-period 3-way;
MLB first inning, first three, first five (2-way and 3-way); CBB and WNBA halves; soccer first half, both-teams-to-score, draw-no-bet,
alternate totals; team totals everywhere; tennis first set. Period scores from ESPN for every sport. About 2.8M credits for the set.

## 1. Derived lines (the most likely inefficiency)
Books build first halves, quarters, periods, first five and team totals as near-fixed fractions of the full-game line. Real games do not
split that evenly, and the split depends on things a fixed fraction ignores.
- MLB first five vs full game: the F5 share should depend on starter quality relative to the bullpen. A great starter with a bad bullpen
  should make the F5 under and the late-innings over both live. (Bartolo's pitcher data is the natural partner here.)
- NBA first half vs second half: starters' minutes, bench quality, back-to-backs and blowout risk move the share. The second half cannot
  be bet historically pregame, but full-game line minus first-half line is the market's implied second half, so a "second-half" edge
  can be tested now and acted on through the choice of first half vs full game.
- NFL and CFB first quarter / first half: scripted openings, tempo, and the weather and rest effects already found (the rest and
  Monday-night unders beat the field by 10-20 points in the first half).
- NHL first period: starts are slower and more defensive; does the first-period total track team pace and rest, or just the full total?
- Soccer first half: the first-half share of goals varies by league and by the favourite's style.
Test: for every sport and derivative, actual share of points/goals/runs in the period vs the market's implied share (derivative line /
full line), by team profile and situation. Where a profile's actual share sits outside the market's in every season, that is the angle.

## 2. Cross-market consistency
At the same moment, related markets imply each other. Gaps between them are pricing errors at one of them.
- Team totals vs the full-game total and spread (home team total should be about (total - spread) / 2).
- First-half spread and total vs first-half moneyline; first-period 3-way vs first-period total.
- Both-teams-to-score and draw-no-bet vs the 3-way price and total.
- Tennis first set vs the match price.
Test: compute each implied value from Pinnacle's full-game numbers, compare with every book's derivative, bet the side when the gap is
big, grade on results.

## 3. Soft books vs Pinnacle on derivatives
First pass (NFL at kickoff, `docs/derivatives_2026-11-05.md`): off-number US lines are priced correctly; the one pocket is team totals
at the same number as Pinnacle with a better price (55-36, +17.6%, n 91). Repeat for every sport, then test earlier in the day (below),
when soft books are more likely to be stale.

## 4. Derivative line movement (needs a second snapshot)
Derivatives may lag the full-game market: if the full-game total moves two points in the last hours and a book's first-half total has
not moved, the first half is stale. Requires an earlier snapshot per game (T-6h for NBA/NHL/CBB/MLB, T-24h for NFL/CFB/soccer), about
another 2.8M credits. Pull after the first pass shows which markets are worth it.

## 5. Situations applied to derivatives
The proven full-game situations (wind, rest, prime time, travel, bounce-backs) should concentrate in particular parts of a game: rust
and travel show early, fatigue shows late. Re-test each through the period lines and the implied second half.

## 6. Then team-level metrics
Only after a market inefficiency is located, use metrics to sharpen it: NHL expected goals (MoneyPuck publishes free game-level CSVs),
soccer xG, NBA pace and ratings, MLB Statcast (Bartolo). The metric's job is to explain why the market is wrong in that pocket, not to
build a model of its own.

## Order of work
1. Derived-line share tests (section 1) for every sport as each pull lands.
2. Cross-market consistency (2) and soft books (3) on the same files.
3. Second snapshot (4) for the markets that showed something.
4. Situations on derivatives (5), then metrics (6).
Anything found goes to paper with its reason, grades forward, and only becomes a bet through the methodology's gates.
