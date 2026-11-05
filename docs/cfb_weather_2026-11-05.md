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

## Wind (diluted; read for shape only, not level)
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
