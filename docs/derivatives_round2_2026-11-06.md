# Derivatives, round 2 (11/6/2026): line shopping venues, derived shares, soft books in every sport

## Line shopping across every venue Sean bets (`sharp/venue_shop.py`, `data/research/venue_shop.json`)
Our own tape, 10/27-11/6, main lines about an hour before the start, cost to take each side against Pinnacle's no-vig fair (1,008 sides):
- Novig is the best price on 73% of sides (76% of moneylines, 68% of spreads, 76% of totals), at -0.5% EV against Pinnacle's fair
  (+0.1% on moneylines). FD, Caesars and DK sit at -4.4% to -4.5%; Kalshi at -4.8% after the taker fee.
- Same sides priced everywhere: best of all venues -1.0%, best exchange -1.4%, Novig alone -0.5% of the time it is there, best of the
  three books -3.4%, DK alone -4.4%.
- Polymarket had no game-line history on our tape (see fixes below), so it is not in these numbers yet.

Fixes made while doing this:
- Novig had been missing from the tape and the board since 11/4 ~09:00 UTC: the signed API key returns 401. The logger now falls back
  to Novig's public API (its URL join had been wrong, so the fallback never worked). Novig is back on the next price run. A new Novig
  API key would restore the signed path, which avoids the public API's rate limits.
- Polymarket game lines were only logged for EPL and NFL: the snapshot query returned the 100 most recently created events, two weeks
  out. Fixed (ordered by end date, paged, CBB under its real tag), and Polymarket NFL/NBA/NHL/CFB/CBB/WNBA game lines now go on the
  price tape every 20 minutes, so the board's best price includes them.

## Derived-line shares (`sharp/deriv_share.py`, `data/research/deriv_share_<sport>.json`)
Pinnacle's first-half / first-quarter / first-period total vs the full-game total 10 minutes before the start, against period scores.
- The market's implied share matches the actual share closely in NBA (0.510 vs 0.509 halves, 0.258 vs 0.257 quarters), CFB (0.526 vs
  0.533), WNBA (0.511 vs 0.513). First-half and first-quarter totals are priced as well as the full game.
- NFL first halves ran over 2023-25 (implied 0.508, actual 0.525; unders -9.7%). Biggest with big favourites (1H over +11.2%) and high
  totals (+6.7%, 3 of 3 seasons), but three seasons and one era: paper at most.
- Nothing passes the bar yet (3 seasons of data per sport; the gate needs a mechanism and every season positive).

## Soft books vs Pinnacle on derivatives, every sport (`sharp/deriv_soft.py`)
At kickoff, off-number US lines lose 2-9% in every sport and market (NFL, CFB, WNBA, NBA, NHL, CBB). The one NFL pocket from 11/5
(team totals at Pinnacle's number with a better price: 55-36, +17.6%) does not replicate: CFB 50-47 (-0.2%), NBA 29-29 (-1.5%), CBB 87-91
(-3.7%). Retired as noise. The derivative markets are efficient at the close; the remaining derivative test is the earlier snapshot
(research agenda section 4), when books are slower.

## Exchange and book derivatives vs Pinnacle on our tape (11/6, 6am; `sharp/exch_deriv.py`)
9 days of our 20-minute tape, last 12 hours before the start, every derivative line Pinnacle hangs (halves, quarters, periods, team
totals); a venue 2%+ better than Pinnacle's no-vig at the same line, first time per game / market / side / venue. 166 bets.
- The prices are real value: +2.0% EV against Pinnacle's last pregame fair (they hold to the close); results 77-89 vs 82.3 expected.
  Too few to grade a ROI (-3.9%).
- Novig supplies most of them (109; +2.0% EV at the close), then FD (31), DK (16), Kalshi (6).
- Stale derivatives (Pinnacle's full game moved toward the side in the previous 20-45 minutes): only 15 cases, 7-8. Nothing to read yet.
- 4%+ edges: 12-8, +5.3% EV at the close.
Keeps collecting on the tape; rerun weekly. The earlier-snapshot pulls (NBA/NHL 6 hours, NFL 24 hours before the start) were dispatched
11/6 to test the same question over three seasons.
