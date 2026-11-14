# Feed redundancy audit, 11/14/2026

Written after the Bet Labs pull went in (9, 11, 2, 5, 7 ET through Sean's Chrome). Question: which jobs does the pull make redundant?

| Feed or job | Verdict | Why |
|---|---|---|
| Bet Labs picks pull (scheduled task "Bet Labs picks refresh") | KEEP (new) | Says which games qualify on Sean's 32 Tested:/Tracked: screens (110 picks at 9 AM) and alerts on new or changed systems. It carries no prices, openers, scores or closes. |
| Price tapes (prices, prices_fast, Odds API, Novig, Kalshi, ProphetX) | KEEP | Prices, opening lines, closes and CLV come only from these. |
| Scores and grading (box_scores, tracker grade) | KEEP | Bet Labs does not grade our fills. |
| sharp/season.py (team logs, records, streaks) | MERGE | Stays the engine: replays, the weekly re-check and the rules with no Bet Labs screen. Bet Labs is the check on it (Bet Labs tab gap view). |
| Open-Meteo forecasts (loggers/nfl/weather.py for NFL and CFB) | RETIRE candidate (not retired) | Wind now fires on MySportsWeather; Open-Meteo is only the fallback when MySportsWeather has no reading. Dome detection moved off its indoor flag to the ESPN schedule plus a fixed roofed-stadium list (sharp/systems.py roofed(), 11/14). Retire only on Sean's OK; first check how often the fallback is used. |
| experts.yml (Action Network expert picks) | KEEP, rescheduled | GitHub's runners get Action's bot-check page, so a GitHub schedule cannot work. Two scheduled tasks now read the profiles in Sean's Chrome: daily 8:47 AM, and 9:53 AM and 5:53 PM ET on Sat, Sun, Mon and Thu (about 2 hours before the first kickoff), handing them to loggers/expert_picks.py --from-json. |

## Rules with no Bet Labs screen

| Rule | Tier | Source | Should Sean save a screen? |
|---|---|---|---|
| xch_homedog_fade | C (live since 11/14) | Novig exchange tape (home side two-sided at 20-35c inside 90 minutes) | No: Bet Labs has no exchange data. |
| wind1014_cold | P | NFL replay on Open-Meteo archive: wind 10-14 at 35F or colder, 27-27 | Yes, optional: Bet Labs can express it (Avg Wind Speed 10-14, Avg Temperature at or below 35, under). |
| awfuldog_deep | P | NFL replay: season margin worse than -13, 14-16 | No: it sits inside the Tested awfuldog screen (margin -40 to -13); a second screen would duplicate it. |
| nba_under_good_home_over_small | P | The 1789285 screen split by drop size (0.5 to 1.0) | No: screen 1789285 already covers it; the split is ours. |

The 11/14 audit called these four "live"; only xch_homedog_fade is live (tier C). The other three are paper.
