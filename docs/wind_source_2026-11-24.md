# Wind source: Bet Labs pull first, MySportsWeather as fallback (2026-11-24)

**Decision (Sean, 11/24 4:40 PM).** The wind rules fire on Sean's saved Bet Labs weather screens, because those screens carry the proven
backtests:
- wind1014: NFL Wind 10-14 Under (1772775)
- wind1014_1h: NFL 1H Wind 10-13 Under (769171)
- cfb_wind14: CFB Wind 14 Plus Under (1783043)

**How it works in the code (`sharp/systems.py` labs_pick, WIND_SCREENS):**
- **A game fires** when the latest Bet Labs pull lists it on the screen.
- **Fallback:** MySportsWeather (with Open-Meteo behind it) is used only when no pull is under 16 hours old. The pulls run at 7:00 AM
  and 5:30 PM ET daily, plus 11:15 AM and 3:00 PM on weekends.
- **Cross-check:** the MySportsWeather wind is shown on every wind row. A game MySportsWeather has in the band but Bet Labs does not list
  is a flag only, not a bet.
- **WAIT rule:** unchanged. A wind bet shows WAIT until 12 hours before kickoff, and lapses if a later pull drops the game.
- **Cold split:** wind1014_cold (35F or colder, paper) still uses Open-Meteo's temperature.

## The holiday games (Bet Labs pull Tue 11/24 6:57 AM ET; the next pull is 5:30 PM ET)

| Game | Bet Labs | MySportsWeather (latest) | What fires |
|---|---|---|---|
| KC @ BUF, Thu 8:20 PM ET | NFL Wind 10-14 Under: listed, wind 14. NFL 1H Wind 10-13: not listed (14 is over 13) | 10 mph, gusts 26, 37F | wind1014 full-game under (WAIT until 8:20 AM Thu). No 1H play. If Open-Meteo puts it at 35F or colder it logs as wind1014_cold, which is paper. |
| DEN @ PIT, Fri 3:00 PM ET | Both screens list it, wind 12 | 20-21 mph | wind1014 full-game under and wind1014_1h first-half under (WAIT until 3:00 AM Fri). Under the old MySportsWeather-only rule this game did not fire. |
| LV @ CLE, Sun | Both screens list it, wind 13 | | Both, once inside the window. |

## Backtest: MySportsWeather vs Bet Labs weather

**Data.**
- MySportsWeather readings start 10/29/2026, so the overlap is this season only: 36 outdoor NFL games and 236 outdoor CFB games from
  10/29 to 11/23 with a reading before kickoff.
- MySportsWeather side: the last reading before kickoff, whole mph.
- Bet Labs side: the games each screen's own past-picks list shows (read-only pull 11/24, `data/research/betlabs_wind_picks_2026.json`).
- Grading: the full-game under at Pinnacle's closing total (Odds API) at -110. First halves use Bet Labs' own result.
- Output: `data/research/wind_betlabs_vs_msw_2026.json`.

| Screen | Games | Same call | Both say play | Bet Labs only | MySportsWeather only | Both | Bet Labs only | MySportsWeather only |
|---|---|---|---|---|---|---|---|---|
| NFL wind 10-14 (full game) | 36 | 78% | 5 of 13 plays | 4 | 4 | 3-2 (+15%) | 2-2 (-5%) | 1-3 (-52%) |
| NFL 1H wind 10-13 | 36 | 83% | 5 of 11 plays | 3 | 3 | 4-1 | 0-3 | no 1H scores |
| CFB wind 14+ | 236 | 94% | 7 of 22 plays | 0 | 15 | 3-4 (-18%) | none | 11-4 (+40%) |

**Reading:**
- **The two sources rarely agree on which games to play.**
  - NFL: they agreed on 5 of 13 play calls.
  - CFB: on 7 of 22. MySportsWeather reads stiffer CFB wind; every CFB game Bet Labs listed in this window MySportsWeather also had at
    14+.
- **The ROI where they disagree is tiny and mixed:**
  - NFL: MySportsWeather-only plays went 1-3.
  - CFB: MySportsWeather-only plays went 11-4. Nine of those 15 were on 11/14, a single windy Saturday, so it is one weather day, not
    15 independent results.
  - Four weeks cannot rank the sources.
- **The long record favours Bet Labs' wind.**
  - The 11/5 CFB study (docs/cfb_weather_2026-11-05.md) used 2020-26 games. Games our Open-Meteo reanalysis put at 14+ that Bet Labs did
    NOT list went **66-72 (-8.2%)**. Bet Labs' own 14+ picks went **135-96 (+12.3%)** at Pinnacle's close.
  - The rule is real on Bet Labs' wind, not on a second source's.
  - MySportsWeather has no multi-season history of its own to test.
- **Fallback decision supported by this:**
  - Bet Labs first.
  - MySportsWeather only when no pull is under 16 hours old.
  - A MySportsWeather-only game is a flag, not a bet.
  - Re-run this comparison at the end of the NFL regular season, when the overlap is about 70 NFL and 400+ CFB games.

**Caveats:**
- **Forecast vs observed.** Bet Labs' past-pick wind may be the observed or final-forecast number, while its live list is a forecast.
  The live pull (forecast) is what the rule now follows.
- **Timing.** The MySportsWeather readings used here are the last before kickoff (mostly under an hour out), so they are as late and as
  good as MySportsWeather gets.
