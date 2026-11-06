# First-half history on the Winners Circle database, 11/5/2026

Sean: "have we run stuff for derivatives like team totals and 1H / 2H splits since using our odds api database?" Not until tonight.

## What was pulled (`loggers/oddsapi_derivs.py`, `data/oddsapi/derivs/`)
Odds API historical event odds, one snapshot 10-14 minutes before kickoff per game. Period and team-total history exists only from
2023-05-03. Second-half lines are not posted before the game, so 2H cannot be pulled historically.
- NFL (1,207 games, about 25k credits): 1H spread, 1H total, team totals. Pinnacle quoted the 1H total on 817 of 820 graded games.
- NBA (4,173 games, newest first, 1H total only, about 10 credits a game): running; stops at a 12k credit floor.
Half-time scores from ESPN linescores (`sharp/linescores.py`, `data/state/linescores.json`): NFL 961, NBA 4,119 games; every NFL
linescore adds up to the final score.

## Baseline first: the era ran over
In the 820 NFL games with a 1H line (Sep 2023 to Feb 2026) first halves landed 1.18 points over Pinnacle's 1H total on average; 1H overs
won 52.2%, unders 45.1%. Full games ran the same way (1.26 over the close). Every 1H under in this window: 370-428, **-9.6%**. A 1H under
rule has to be read against that.

## The four NFL first-half rules (`sharp/nfl_1h_replay.py`, `data/research/nfl_1h_replay.json`, at Pinnacle's 1H price)
| rule | the rule's games | its neighbours | Bet Labs since 2021 | change |
|---|---|---|---|---|
| wind1014_1h (wind 10-13, 1H under) | 55-51, +0.4% (2023 -15%, 2024 -10%, 2025 +44%) | calm 0-5 mph -19.3%; 6-9 -3.7% | 113-90, +5.9% | A -> **B** |
| vrest8_1h (visitor off 8-30 days) | 100-87, +4.4% (3 of 4 seasons flat or better) | visitor on a normal week -16.2% | 139-88, +16.7% | stays C |
| mnf_1h (Monday night) | 33-28, +6.4% (2024 -25%) | Sunday night -2.1%, Thursday -22.6%, other slots -10.5% | 47-32, +14.0% | stays B |
| bounce15_1h (dog off a 15+ ATS loss, 1H spread) | 54-61, -10.5%, every full season negative | dogs off a 7-14 loss -5.3%; all other dogs -10.7% | 117-83, +11.6% | B -> **C** |
Reading: against the baseline the weather, rest and Monday-night unders all beat the field by 10-20 points, which is the mechanism
(fewer possessions, rust, the prime-time under) showing up; none clears zero by much on its own in an over-heavy era. The wind rule's
full-game version (161-103, +18.1%) stays tier A; its first-half version drops to B. The bounce rule shows nothing in our 1H data and
goes to C because the two tests disagree.

## Next
NBA 1H under rule once the NBA pull finishes; NFL team totals as miner features (wind and rest by team); CFB 1H and MLB first five
when credits allow.
