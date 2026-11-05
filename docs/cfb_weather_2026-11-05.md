# CFB weather replay, 11/5/2026 (evening)

Sean: "do cfb weather". Script `sharp/cfb_replay.py`; results `data/research/cfb_replay_nasa.json`; weather cache
`data/cfb/weather/archive_nasa.json`; stadium map `data/cfb/weather/_stadiums.json` (137 home teams via ESPN team -> venue -> geocoder,
4 fixed by hand: Baylor, Houston, Ohio State, Miami OH).

## Source
Open-Meteo's archive hit its daily request cap mid-afternoon, so tonight's pass uses NASA POWER (MERRA-2 reanalysis, hourly, no key, no cap),
one call per stadium for 2020-26. Calibrated against Open-Meteo on the 1,090 NFL game-hours we hold from both:
- Temperature: mean difference 0.3F. Trustworthy.
- Wind: correlation 0.77, NASA = 2.6 + 0.67 x Open-Meteo. A NASA 14+ catches only 71 of 121 Open-Meteo 14+ games and adds 67 that were
  not windy. The 50 km grid smooths the wind, so every wind band below is diluted and **the wind results are not a test of cfb_wind14**.
  The Open-Meteo pass runs after the cap resets (00:20 UTC reminder) and replaces the wind section.
4,861 CFB games with a Pinnacle closing total and a result; 4,361 with weather (500 indoor, neutral site or unmapped). Graded at
Pinnacle's closing total price, flat stakes.

## Heat (temperature is reliable here)
| cut | record | ROI | seasons + |
|---|---|---|---|
| over by kickoff temperature, 85F+ | 284-253 | +1.6% | 4/7 |
| 85F+, wind 10 or less: over | 249-212 | +3.7% | 4/6 |
| 85F+, wind 10 or less, total 55 or less: over | 154-109 | +12.5% | 6/6 |
| same, conference game | 37-38 | -5.0% | 3/6 |
| same, **non-conference (the live rule)** | **117-71-3** | **+19.5%** | **6/6** |
| 85F+, wind 10 or less, total 55.5+: over | 95-103 | -8.0% | 3/6 |
| every other temperature band, over | negative | -2 to -5% | |
| freezing (under 32F): under | 40-40 | -3.5% | |
Verdict: `cfb_hot_over_low_total` holds on an independent database with the same shape Bet Labs found (203 games +16.4% through 2021,
92 +10.1% after), 6 of 6 seasons, and the two nearest cuts (conference games, higher totals) are negative, so the rule's edges are real
edges rather than a wide plateau. Mechanism: early-season heat against thinner non-conference rosters; low totals are where the market
prices it least. **Tier C -> B** (0.5u). Fires August-September only by construction (85F+).

## Wind, first pass on NASA (diluted; read for shape only, not level)
- Under by band: 0-5 -6.8%, 6-9 -6.7%, 10-13 +2.4% (5/7), 14-17 -3.7%, 18-21 +6.5% (5/7), 22+ 22-10 (+31.6%).
- cfb_wind14 as the rule (14+): 206-182-4, +1.9%, 5 of 7 seasons. Cold (under 45F) and windy 27-10; mild and windy 179-172.
- Totals 60+ in the wind: 43-27 (+18.6%). Rain in the wind: 13-19.
Shape matches the NFL replay (wind helps unders, more wind helps more, cold helps) but the level is unreadable until the finer source runs.
cfb_wind14 stays tier A on its Bet Labs record (555-402 all-time, positive on both halves, 5 of 6 seasons); no change tonight.

## Afternoon-over question (Sean: is it temperature?)
Not answerable from this pass: the afternoon-over cut was dropped to paper earlier tonight for having no mechanism, and the temperature
bands above show no over edge between 45F and 84F in any slot. If it were heat, the 85F+ band would be the whole effect, and the 2-7pm
slot is positive in October and November too. It stays paper.

## Next
Open-Meteo pass for wind (then wind and temperature bands as miner features for CFB); MLB weather when we circle back.

## Open-Meteo pass (after the quota reset, 23:00 UTC) and the Bet Labs pick list
Open-Meteo archive (ERA5, ~9 km), same 4,361 games. Heat: non-conference hot rule 88-55 (+18.4%), 5 of 6 seasons; conference 22-29;
totals 55.5+ 82-106. Tier B confirmed.
Wind, straight replay: 14+ under **114-102-2 (+1.3%)**, 4 of 7 seasons; 10-13 311-305; 18-21 15-14; 22+ 5-0. The rule does not replay on
reanalysis wind. So the question became whether the rule or the wind source is wrong. Bet Labs' own picks for screen 1783043 since
8/2020 (271 picks, 235 matched to our database, `data/research/betlabs/cfb_wind14_1783043.txt`):
- Their picks graded at Pinnacle's closing total and price: **135-96 (+12.3%)**. The rule is real on their wind.
- Their wind reads 16.0 mph on average where Open-Meteo's 3-hour average reads 14.3; only 54% of their 14+ picks are 14+ in Open-Meteo.
- Their picks that Open-Meteo also puts at 14+: 68-53 (+8.0%). Their picks Open-Meteo puts at 11-13.9: 46-32 (+13.4%); under 11: 19-5.
- Our Open-Meteo 14+ games that are on their list: 48-30 (+18.0%). Our Open-Meteo 14+ games they did NOT flag: **66-72 (-8.2%)**.
Reading: the edge lives in Bet Labs' wind source (station observations at the venue, by the look of it), not in a reanalysis grid. A
reanalysis 14+ that the venue reading does not confirm is not a windy game. This matches what the live tool already does for NFL
(average of Open-Meteo and MySportsWeather, which sat on Bet Labs' number on the 11/1 games), and it changes one thing for CFB: the
live rule now fires only when MySportsWeather is in the blend; Open-Meteo alone is a flag ("one source at 14+"), not a bet.
`cfb_wind14` stays tier A on Bet Labs' record; the backtest line on the board now cites their picks at our close (135-96).
The miner's CFB wind feature is therefore a weak proxy; wind angles from it (calm + low total over) are not trusted.

## The same check for the NFL rule (why the NFL replay worked and the CFB one did not)
Bet Labs' picks for NFL wind 10-14 under since 2020 (270, 263 matched, `data/research/betlabs/nfl_wind1014_1772775.txt`): graded at
Pinnacle's close **160-101 (+18.6%)**. Their wind averages 11.6 mph on those games, Open-Meteo's 11.8; 67% of their picks are in the
10-14 band by Open-Meteo too, and the rule holds in every Open-Meteo bucket of their picks (in band 98-61, below 10 25-13, above 14 25-18).
NFL stadiums sit where a 9 km reanalysis cell reads the venue well; CFB venues do not (their wind read 1.7 mph above Open-Meteo and only
half of their 14+ games were 14+ in it). So: NFL fires on the Open-Meteo / MySportsWeather average as before; CFB fires only when
MySportsWeather (a point forecast at the stadium) is in the blend.
