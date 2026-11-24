# Wind systems backtest: Bet Labs vs pregame NBM vs observed (2020-26)

Read-only research for Sean (via Kirk, 11/24). No rule changed.

**Question:** which weather source should trigger the wind bets, judged on what was actually knowable before the game.

**Method:**
- Profit at Pinnacle's closing total and closing under price, flat 1u to risk.
- p = the one-sided chance of a result this good at break-even.
- The two winners (Bet Labs in CFB, p 0.003; NBM in the NFL, p 0.0007) survive a Bonferroni correction for the 8 source-by-rule tests.

## Summary

**NFL (wind1014, 10-14 mph full-game under), 1,014 outdoor regular-season games:**
- Bet Labs' list: **+21.9% on 233** (p 0.0003).
- The reconstructed pregame NBM forecast: **+18.6% on 274** (p 0.0007).
- Observed ERA5 reanalysis: +19.0% on 243.
- Observed airport stations (ASOS): +9.9% on 229.
- The rule works on any reasonable wind number, including one that was fully knowable 6-12 hours before kickoff. So in the NFL a
  MySportsWeather-style fallback is supported.

**CFB (cfb_wind14, 14+ mph full-game under), 4,251 games:**
- Bet Labs' list: **+17.8% on 212** (p 0.003).
- Every other source is flat:
  - NBM pregame: +2.5% on 244.
  - ERA5: +2.8% on 211.
  - ASOS: +0.6% on 319.
- The whole edge sits in the games only Bet Labs flags:
  - On Bet Labs but not NBM: **+32% on 81** (p 0.001).
  - On NBM but not Bet Labs: -5.0% on 113.
- A MySportsWeather or NBM fallback for CFB is **not** supported. A CFB game that only the fallback flags should be a flag, not a bet.

**Is Bet Labs' weather observed (look-ahead) or a pregame forecast? The evidence says pregame forecast:**
1. **Its record matches its own pregame lists.** For the 11/21-11/23 games we hold several pregame pulls of Sean's screens, and the wind
   value in Bet Labs' final record equals the last pregame pull in 8 of 8 games, including two that moved 10 to 11 mph between pulls.
   One CFB game (Arizona @ Kansas State) was on a pregame list at 14 mph, then dropped out before kickoff and is not in the record.
   Bet Labs keeps updating the forecast up to the game and freezes it. It does not overwrite it with what was measured.
2. **Its number is not closer to the observations than to the forecast.**
   - On its own NFL picks, the typical gap to the pregame NBM is 1.8 mph and to ERA5 1.75 mph, almost the same. To the airport station
     it is 2.3 mph, further away. An observed record would sit closest to the observations.
   - In CFB, Bet Labs reads about 1.6-1.8 mph windier than both the forecast and ERA5, consistent with a different forecast vendor,
     not a measurement.
3. **Caveat:** this check covers recent games only. Whether Bet Labs used the same pregame method in 2003-19 cannot be verified from
   here, so the older seasons of its backtest carry that uncertainty.

**Recommendation:**
- Keep the Bet Labs pull as the trigger (in place since 4:45 PM today). It is a pregame number and the only one that carries the CFB edge.
- **NFL:** the MySportsWeather (NBM-based) fallback is fine as a bet when no pull is fresh (NBM +18.6% on 274).
- **CFB:** the fallback should be **flag-only**. A CFB wind game that only MySportsWeather has at 14+ is not a bet; at most it waits for
  the next Bet Labs pull. That would be a small code change, and it needs Sean's OK.

## What was built

| Source | What it is | Coverage |
|---|---|---|
| Bet Labs | the games each saved screen lists, with Bet Labs' own wind. NFL Wind 10-14 Under (1772775) and CFB Wind 14 Plus Under (1783043); both screens filter only wind and regular season, so an outdoor game not listed is outside Bet Labs' band | picks from 2020 matched to our games: NFL 242 of 278, CFB 216 of 278 (the rest are neutral sites, missing lines, or name mismatches) |
| NBM pregame | the National Blend of Models from NOAA's archive (AWS noaa-nbm-grib2-pds, from May 2020). For each game: the 6-hourly cycle issued 6-12 hours before kickoff, 10 m wind for the kickoff hour and the next two (averaged), at the grid point nearest the stadium (2.5 km grid). 4,165 cycle-hour fields fetched, 116 missing (early-2020 gaps; the cycle 6 hours earlier is used when it exists) | 1,014 NFL and 4,251 CFB games |
| Observed ERA5 | the Open-Meteo historical archive (ERA5 reanalysis), 3-hour mean from kickoff at the stadium, from our existing archive | same games |
| Observed ASOS | the nearest airport station's routine hourly METAR wind (Iowa Environmental Mesonet), mean of the kickoff hour and the next two; median 6.5 km from the stadium | 864 NFL and 3,973 CFB games |

**Limits:**
- MySportsWeather itself cannot be rebuilt. Kevin Roth's manual adjustments are not archived, so NBM is the closest proxy for what it
  would have shown.
- Our only true MySportsWeather sample is 10/29 on (docs/wind_source_2026-11-24.md).
- The first-half screen (wind1014_1h) is not in the three-way test: we have no first-half scores for 2020-22. Its record rests on Bet
  Labs' own first-half results.

## Results by source (same games)

| Rule | Source | n | Record | Units | ROI | p |
|---|---|---|---|---|---|---|
| wind1014 (NFL) | Bet Labs | 233 | 146-85 | +51.1 | **+21.9%** | 0.0003 |
| | NBM pregame | 274 | 167-105 | +51.1 | **+18.6%** | 0.0007 |
| | Observed ERA5 | 243 | 148-93 | +46.1 | +19.0% | 0.001 |
| | Observed ASOS | 229 | 128-98 | +22.8 | +9.9% | 0.06 |
| cfb_wind14 (CFB) | Bet Labs | 212 | 129-81 | +37.8 | **+17.8%** | 0.003 |
| | NBM pregame | 244 | 129-112 | +6.2 | +2.5% | 0.34 |
| | Observed ERA5 | 211 | 112-97 | +5.9 | +2.8% | 0.34 |
| | Observed ASOS | 319 | 166-150 | +2.0 | +0.6% | 0.45 |

**By season (ROI, n):**

| Rule / source | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| NFL Bet Labs | -3.6% (22) | +16.4% (45) | +40.5% (55) | +32.2% (33) | -1.2% (39) | +43.9% (22) | +14.0% (17) |
| NFL NBM pregame | +16.9% (25) | +11.8% (47) | +47.3% (46) | +23.0% (59) | -13.8% (47) | +30.9% (33) | +13.1% (17) |
| CFB Bet Labs | +49.0% (26) | +24.1% (45) | +5.8% (48) | +2.8% (29) | -23.1% (25) | +41.4% (27) | +43.5% (12) |
| CFB NBM pregame | +8.1% (16) | -3.7% (29) | +7.1% (42) | -4.1% (58) | -13.5% (39) | +19.7% (32) | +15.5% (28) |

## Agreement, and ROI where the sources disagree

| Rule | Pair (A vs B) | Games | Same call | Plays both flag | Both | A only | B only |
|---|---|---|---|---|---|---|---|
| NFL | Bet Labs vs NBM pregame | 1,014 | 82% | 47% | +26.9% (163) | +10.3% (70) | +6.5% (111) |
| NFL | Bet Labs vs ERA5 | 1,014 | 83% | 48% | +21.9% (154) | +21.9% (79) | +13.9% (89) |
| NFL | Bet Labs vs ASOS | 864 | 78% | 38% | +23.2% (118) | +21.9% (82) | -4.1% (111) |
| NFL | NBM pregame vs ERA5 | 1,014 | 82% | 48% | +25.6% (168) | +7.6% (106) | +4.1% (75) |
| CFB | Bet Labs vs NBM pregame | 4,251 | 95% | 40% | +9.0% (131) | **+32.0% (81)** | -5.0% (113) |
| CFB | Bet Labs vs ERA5 | 4,251 | 96% | 45% | +15.2% (131) | +22.0% (81) | -17.6% (80) |
| CFB | Bet Labs vs ASOS | 3,973 | 94% | 35% | +16.2% (133) | +13.1% (58) | -10.5% (186) |
| CFB | NBM pregame vs ERA5 | 4,251 | 95% | 39% | -0.5% (128) | +5.9% (116) | +7.8% (83) |

"Same call" is high mostly because both sources say "no play" on calm games. The share of plays both flag is the real agreement: under
half.

## Is Bet Labs' weather knowable pregame?

| Check | Result |
|---|---|
| Final record vs Bet Labs' own pregame pulls (11/21-11/23) | wind value identical in 8 of 8 games; one game dropped before kickoff is absent from the record; values updated up to the game (10 to 11) |
| Gap on its NFL picks: to pregame NBM / ERA5 / airport station | 1.80 / 1.75 / 2.29 mph (bias -0.2 / -0.3 / -1.0) |
| Gap on its CFB picks: to pregame NBM / ERA5 / airport station | 2.62 / 2.44 / 3.22 mph (Bet Labs about 1.6-1.8 mph windier than NBM and ERA5) |
| Correlation of its number with NBM / ERA5 / ASOS (NFL) | 0.50 / 0.57 / 0.48 |

**Verdict:**
- Bet Labs records its latest pregame forecast, so its backtests are not look-ahead on observed wind, as far as the recent games show.
- That forecast is not the NBM: in CFB it runs windier and picks different games, and those games carry the result.
- Mechanism (one sentence): a forecast that flags a windy game the market's usual weather feeds do not price as windy gets the under at
  a number that has not moved; games every source sees as windy are already priced.
- The same mechanism explains why the shared NFL plays still win: NFL wind is rarer, and the 10-14 band is mild enough that the
  market prices it less.

## Files

- `data/research/wind_three_way_2020_26.json`: every table above.
- `data/research/wind_three_way_games.json`: one row per game, with all four winds, the line, the price and the result.
- `sharp/research/wind_nbm_pull.py`, `wind_asos_pull.py`, `wind_three_way.py`: the scripts (they were run from a scratch folder holding
  the weather archives and the odds database).
