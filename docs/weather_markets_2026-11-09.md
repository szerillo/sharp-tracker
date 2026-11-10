# Kalshi daily high-temperature markets: can we beat them? (11/9)

Sean: "can we use our weather modeling to beat weather models or prediction markets?"

## Data
- Kalshi: every settled bracket for NYC, Chicago, Miami, Austin, Los Angeles, Denver and Washington, Sep 3 to Nov 9 2026 (2,856 brackets,
  476 city-days; the public API only reaches back about 68 days), with every trade from 36 hours before the day
  (loggers/kalshi_weather.py). These are large markets: about 12 million contracts traded in NYC and 30 million in Los Angeles over the period.
- Settlement: the NWS daily climate report (CLI) high at each city's station, day in local standard time. IEM's copy of the CLI, and every
  ASOS report (hourly and 5-minute) from IEM.
- Forecasts: IEM's archive of the National Blend of Models (NBS, the blend the NWS forecasts are built from), four runs a day, each with
  a forecast high (txn) and its standard deviation (xnd), fall 2025 and fall 2026.
- Bartolo (mlb-tracker, read only): its forecasting side is the NWS hourly forecast at each park plus an accuracy log (2.1 F error at
  first pitch against 3.5 F for BallparkPal). The useful part here is the method, a forecast with a measured error, applied to the daily
  high at the settlement station; the run-scoring model does not carry over.

## 1. Is the market calibrated? (last trade before each clock time, 2,500-2,600 brackets each; fees not included)

| Price band | 8 AM: priced / won | 11 AM | 2 PM | 5 PM |
|---|---|---|---|---|
| 0-5c | 1.7% / 0.5% | 1.6% / 0.6% | 1.2% / 0.1% | 1.1% / 0.1% |
| 5-15c | 8.7% / 8.7% | 8.8% / 8.2% | 8.6% / 9.4% | 7.9% / 7.7% |
| 15-30c | 21.7% / 18.7% | 21.9% / 20.5% | 21.2% / 15.4% | |
| 30-50c | 39.0% / 36.1% | 38.6% / 37.1% | 38.3% / 44.3% | |
| 50-70c | 58.6% / 64.4% | 59.1% / 59.1% | 60.8% / 55.6% | |
| 70-85c | 74.8% / 75.6% | 75.2% / 81.5% | 76.7% / 81.4% | |
| 95-100c | | | 98.0% / 98.3% | 98.6% / 99.8% |

Close to calibrated at every time. The only steady pattern is the usual one: 1-5c longshots win less than priced, so selling them pays
about 1% before fees. No band misses by a consistent amount across the day.

## 2. Brackets already settled by the observations ("sure things")
The CLI high was at least the highest ASOS report on 509 of 510 city-days, so once a reading is above a bracket, that bracket cannot win.
The 5-minute reports are whole degrees C converted to F and can read 1 F above the CLI, so a 1 F margin is needed: with none, 2.6% of
the "dead" brackets still settled yes; with 1 F, 19,163 of 19,163 settled as the readings said.

| (1 F margin) | Trades | Price | Profit available at settlement |
|---|---|---|---|
| Dead brackets, 'yes' at 1c | 18,994 | 1c | $44,680 on 4.47M contracts |
| Dead brackets, 'yes' at 2-15c | 169 | 2-15c | $180 |
| Already-won brackets, 'yes' at 99c | 992 | 99c | $875 |

The market already knows. Almost every trade on a settled bracket is at the 1c floor, so the riskless side earns 1% on money tied up until
the CLI posts (hours to overnight). Across all seven cities that is about $650 a day of 1% scalps, already being taken. Not alpha.

## 3. National Blend of Models against the market
Bias and spread per station fitted on fall 2025 (the NBM's own spread is too narrow: actual errors run 1.2 to 1.9 times it), then each
2026 run priced every bracket and was compared with the Kalshi price 2.5 hours after the run (the run's publication lag).

| | Brier score: model / market (lower is better) | Bets where the model was 5+ / 10+ / 15+ points better | ROI after fee |
|---|---|---|---|
| Day before | 0.137 / 0.108 (4,659 bracket-runs) | 2,661 / 1,877 / 1,255 | -9.0% / -10.3% / -14.8% |
| Same day | 0.138 / 0.100 (7,521) | 4,094 / 3,000 / 2,145 | -11.3% / -12.2% / -12.9% |

The market is clearly better than the public forecast, and the more the model disagrees, the more it loses.

## Read
- These markets are efficient against public information: calibrated through the day, the observation-settled outcomes priced at the floor,
  and better than the National Blend once its own bias and spread are corrected.
- What is left is speed: the hourly NBM, the HRRR and the 5-minute ASOS feed update faster than the archive used here, and the traders
  use them. An edge, if any, would be in reacting to a new run or reading before the market does. That needs a live feed and orders placed
  by Sean; a backtest on this archive cannot show it.
- Not recommended as a betting market for us. The puller can run on a schedule to build a longer history if this is revisited.
