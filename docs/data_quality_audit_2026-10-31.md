# Data-quality audit: tracker rules vs Bet Labs' own picks (2026-10-31)

Method: every saved Bet Labs system the tracker runs lists its past picks with the filter values Bet Labs computed. For each rule
the 2026-season picks were pulled and compared game by game with the tracker's inputs for the same games.

## Fixed

| Area | Problem | Effect | Fix |
|---|---|---|---|
| NHL season logs | Logs started 10/05; the season opened 9/30 | every team missing 3-4 games; every NHL win% wrong | scan from 9/20, keep ESPN season type 2/3; all 32 NHL, 30 NBA, 32 NFL teams now match ESPN standings |
| NBA season logs | Preseason games counted | NBA over% and records wrong | same fix |
| nhl_pl_fav_gap | Direction backwards: Bet Labs' Win % Difference is opponent minus team | fired on the opposite games; 4 bets voided | rule now backs a favorite whose opponent's win% is 22+ higher |
| NHL win% | Bet Labs: wins / games played (OT losses are losses), truncated to whole % | small threshold differences | tracker truncates the same way |
| NBA/NHL minimum games | Tracker skipped teams with < 8 games; Bet Labs has no minimum | early-season NHL rule (games 1-24) blind for 8 games; NBA 1H rule missed its early picks | minimum 1 game |
| NBA rest days | Bet Labs counts the calendar-day gap (back-to-back = 1); tracker subtracted 1 | wrong rest window on nba_under_good_home_over | calendar-day gap, home 1-2, visitor 1-3 |
| NHL big-dog puck line | Tracker used the current fair price; Bet Labs filters the opening moneyline | wrong games | opening ML from AN_Open (earliest book quote fallback) |
| NFL awful-team dog | Tracker required 2+ games; Bet Labs has none | missed 4 of Bet Labs' 8 2026 picks (all week 2) | minimum 1 game |
| NFL visitor rest | Tracker measured hours between kickoffs (8 days could read 7.99) | missed Dallas @ Philadelphia, Giants @ Rams | calendar days, 8-30 as on the screen |
| NFL wind | Bet Labs records whole mph; 1H screen is 10-13 mph, not 10-14 | 10-mph games reading 9.7-9.8 missed; 1H under fired at 14 mph | round to whole mph; 1H rule 10-13 |
| Venue coordinates | Geocoder fell back to the first city-name match | Ole Miss forecast for Oxford, England; Penn State for University Park, Iowa; Kansas State for Manhattan, New York; Stade de France for Reunion island | strict country + state match, no fallback; 4 venues corrected; 69 wrong-city forecast rows dropped |

## Checked and matching

- NFL season margin average (awful dog) and previous-game ATS margin (bounce): match Bet Labs to the half point (DK close vs Bet
  Labs' close differs by 0.5 on 3 of 12 games).
- NBA over% (visitor and home): matches exactly once preseason is excluded.
- NHL opponent win% and game number (early-season and 66%+ rules): match.
- NFL Monday night and dome/outdoor: match.
- Wind scale: Open-Meteo's recorded 10 m wind at kickoff averages 0.6 mph below Bet Labs' value on its 12 checkable 2026 picks; same
  scale. The forward rule uses a T-24h forecast, which adds forecast error on top; nothing to fix, but expect the forward hit rate
  on the wind band to be noisier than the backtest.
- CFB conference road dog: the saved screen's extra filters (conference, opposing team, game number, season) are inactive; the
  tracker's conference / visitor / spread 7+ / total 48 or less matches.

## Not yet checkable

- CFB wind: forecasts only logged from 10/25, after Bet Labs' last CFB wind pick; recheck after next week.
- Exchange-audit rules (xch_homedog_fade, nba_momentum): no Bet Labs counterpart; they rest on the 10/29 exchange audit, which
  ran on sparse tape and should be rerun on the dense 5-minute tape before being trusted.
