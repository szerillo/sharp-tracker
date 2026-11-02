# Rescue tests for failed Bet Labs systems: pre-registered variants (2026-11-01)

Sean, 11/1: for systems that had a real edge and then failed, try slightly different parameters "without sacrificing logic or
reasoning. Don't add stuff just to make it profitable. Add stuff because it would make sense, and it turns out it would be profitable."

Written after reading each screen's filters and before pulling any results for the variants. Source list: the 10/30 account audit
(data/betlabs/account_systems_audit_2026-10-30.psv), systems with 150+ train bets, +4% or better train ROI and a flat or losing
holdout. In-season sports only this round (CBB, NBA, NHL, NFL, CFB); MLB in the spring. Skipped: postseason / preseason / one game a
year screens (766986 NCAA tournament, 766865 NFL preseason, 1106820 NHL playoffs, 766920 opening game), 766972 (holdout 51 bets) and
766926 (it is the kept cfb_road_dog_low_total rule's parent).

Rules of the test:
- Each variant adds one condition (two at most), with a stated reason the original edge should live there.
- Cut points are natural (key numbers, half a point of movement, rest days, season halves), not windows tuned on the data.
- Train 08/2003-02/2021, holdout 03/2021-now, read once. A variant passes only if both are positive, the holdout has 75+ bets,
  and the reason still reads as sound. With about 30 variants, 3-5 passing on luck alone is expected, so a pass is a candidate
  for paper tracking, not a rule.

| Screen | What it is | Variant | Reason |
|---|---|---|---|
| 766971 Neutral Court Unders | Nov, neutral court, total 145+, under, public on the over | A: total fell 0.5+ from open | the market agrees; totals under-react (market-moves study) |
| | | B: team game number 5 or less | the earliest tournaments: new rotations, unfamiliar arenas |
| 766981 CBB Under with Good Over Teams | both teams over-heavy, weekday, under | A: total fell 0.5+ from open | the NBA version of this rule only works with the drop |
| | | B: closing total 145+ | the over-team premium is largest in high totals |
| 766974 CBB Contrarian Saturdays | conf game, team on an ATS losing streak, heavy-bet day | A: line moved toward the team 0.5+ | sharp money confirming the contrarian side |
| | | B: team is the dog | buy-low is a dog angle; favourites on a slide are still overpriced |
| 766970 CBB Top 15 Home Teams | non-conf, ranked home team off a home win | A: spread 15 or less | huge non-conf spreads are garbage-time noise |
| 766962 NBA RLM Unders | division game, public on the over, total fell | A: total fell 1.5+ | a bigger reverse move is a stronger signal |
| | | B: money% minus ticket% 10+ | the money really is on the under |
| 766961 NBA Road Dogs Off ATS Loss | visiting dog off an ATS loss, opponent off an ATS win | A: spread 4 to 10 | real dogs, not pick'ems, not blowouts |
| | | B: previous ATS loss by 7+ | a bigger overreaction to fade |
| 853058 / 766995 NHL Well-Rested Visiting Favs (PL / ML) | visiting fav off 3-4 days, opponent missed playoffs | A: opponent on 0-1 days rest | the rest gap is the mechanism |
| | | B: moneyline -170 or longer (ML screen only) | moderate favourites, not chalk |
| 766997 NHL Tickets vs Money Dogs | dog with money% 15-30 above tickets | A: moneyline moved toward the dog | the money moved the price |
| 825756 NFL Bad ATS vs Good ATS | weeks 6-17, team ATS 30% or worse vs 60%+ | A: week 9 or later | ATS records mean more with more games |
| | | B: team is the dog | buy-low is a dog angle |
| 766870 NFL Team ATS Records | weeks 6-17, team ATS 30% or worse vs 51%+ | A: team is the dog | same |
| | | B: spread 7 or less | inside a converted score |
| 774066 NFL Over After Both Went Under | weeks 2-4, both teams' last games under | A: total 44 or lower | the market overcorrects most on already-low totals |
| 822611 NFL Pythagorean | team winning 51-81% with a Pythagorean below .500 | A: week 6 or later | point differential needs games |
| | | B: team is the favourite | an overrated team is priced as a favourite |
| 772518 NFL Early Season Upsets | weeks 1-5 division dog of 5.5 or less, ML | A: line moved toward the dog | money confirms |
| 766866 NFL Road Trips with Line Move | 2nd-3rd straight road game, off a loss, line moved to them | A: team is the dog | a road team off a loss is a buy-low dog |
| 766924 CFB Road Streak | conf, 2-5 straight road games, heavy-bet day, total 54 or lower | A: team is the dog | same |
| | | B: spread 14 or less | |
| 1331115 CFB Scoring Streak Fade | home favourite on a low-scoring streak | A: spread 14 or less | |
| | | B: conference game | familiarity, fewer mismatches |
| 766927 CFB Bet Against Public with Line Move | home team, 10-35% of spread bets, line moved to them | A: team is the dog | |
| | | B: conference game | |
| 766922 CFB Weather Overs | hot (85F+), calm (wind 10 or less), non-conf, over | A: total 55 or lower | heat tires defences; high totals already priced |
| 764707 CFB Small Visiting Dog (ML) | visiting dog of 4 or less | A: conference game | |
| | | B: line moved toward the dog | |

Results: docs/betlabs_rescue_2026-11-01.md.
