# Pushback on the tiers (board_r10, Sean 11/18)

Built by sharp/validate_pushback.py. Tier rules: [TIER_RULES.md](TIER_RULES.md), version 2, committed before this scoring. Recommendations only: no tier in the tool was changed and nothing is retired.

Bet Labs numbers: data/betlabs/records.json, pulled 2026-11-19 (sharp/betlabs_records.py; the full backtest of each saved screen, refreshed with the Bet Labs pull). Re-scored 11/19 on it: the only tier that moves against the 11/18 scoring is nfl_home_dog_7510, B to C, after its 0-3 start since it was saved (all-time 119-87 now, p 0.071). The board was not changed; tiers stay Sean's call.

## Short answer

Sean is right about the evidence that drove the first verdicts. They rested on our rebuild, which only covers 2020 to 2025 (the Odds API history starts in 2020), uses Pinnacle closes, and uses our own weather and 1H data. His systems were selected on Bet Labs backtests that go back to 2003 and are often 3 to 5 times larger. For his own Bet Labs screens the bigger backtest should be the primary evidence, and the re-tier below uses it.

Two things still hold. First, seven of the live rules were not Bet Labs screens to begin with. They were mined from our 2020-26 data in late October (out of roughly 100,000 tests per sport) and saved as screens afterwards. For those, the 2020-26 record is the sample they were picked on, and Bet Labs' record before 2021 is the real test: for five of the seven, it is negative. Second, where our rebuild could not reproduce a Bet Labs record because it used different data (wind, 1H lines), that is now treated as a weakness in our rebuild, not in the system.

One caution that still applies to the Bet Labs numbers: Sean's saved Tested:/Tracked: screens are the survivors of the screens he built on that same Bet Labs history, so their p-values are in-sample too. That is why Tier A also needs both eras positive and the Mar 2021 on era to stand on its own (p < 0.10).

## 1. Which sample drove each verdict

(a) Bet Labs as reported on the saved screen, at Bet Labs' prices, all years from 2003 (data/betlabs/records.json, pulled 2026-11-19; eras split by season: 2020 and earlier vs 2021 on). (b) Our rebuild: Odds API, Pinnacle close, 2020 to 2025 (NFL 1H 2023 to 2025), in-sample plus the 2025 / 2025-26 holdout. (c) Live paper record from fills.jsonl. "Reproduces" = our rebuild and Bet Labs' Mar 2021 on record are both positive, ours at least half of Bet Labs' ROI; partly = ours positive but smaller.

| System | Origin | (a) Bet Labs all-time | (a) seasons to 2020 | (a) seasons 2021 on | (b) Our rebuild in-sample | (b) Holdout | (b) Data | (c) Live | Reproduces |
|---|---|---|---|---|---|---|---|---|---|
| wind1014 | Sean's Bet Labs screen | 537-380, +13.1% (p 0.000) | 384-293, +10.1% | 153-87, +21.8% | 211 bets, +14.7% (2020 to 2024) | 22, +57.0% | Open-Meteo archive wind, not Bet Labs' wind | 8-4, +3.6u | yes |
| wind1014_1h | Sean's Bet Labs screen | 407-303, +9.2% (p 0.005) | 291-212, +11.9% | 116-91, +6.6% | 82 bets, -8.9% (2023 to 2024) | 25, +8.4% | Open-Meteo wind and a Pinnacle or US-book 1H line from 2023 only | 7-2, +2.3u | no |
| cfb_wind14 | Sean's Bet Labs screen | 557-403, +12.2% (p 0.000) | 423-307, +12.6% | 134-96, +10.9% | 186 bets, +0.1% (2020 to 2024) | 4, +92.7% | Open-Meteo archive wind, not Bet Labs' wind | 13-3, +9.9u | partly |
| cfb_hot_over_low_total | Sean's Bet Labs screen | 175-120, +14.2% (p 0.005) | 122-81, +15.9% | 53-39, +10.1% | 69 bets, +20.0% (2020 to 2024) | 27, +20.7% | Open-Meteo archive temperature and wind, not Bet Labs' weather | none | yes |
| awfuldog | Sean's Bet Labs screen | 254-164, +17.2% (p 0.000) | 203-133, +16.8% | 51-31, +18.6% | 62 bets, +6.7% (2020 to 2024) | 29, +12.0% | Pinnacle full-game close | 0-4, -2.0u | partly |
| nfl_home_dog_7510 | mined from our 2020-26 data, screen saved 10/28 to 11/3 | 119-87, +9.6% (p 0.071) | 83-67, +4.9% | 36-20, +22.1% | 57 bets, +21.3% (2020 to 2024) | 6, +25.2% | Pinnacle full-game close | 0-4, -2.0u | yes |
| vrest8_1h | Sean's Bet Labs screen | 459-364, +6.8% (p 0.020) | 319-271, +4.5% | 140-93, +14.5% | 79 bets, -1.7% (2023 to 2024) | 24, +37.4% | Pinnacle or US-book 1H line from 2023 only | 3-5, -1.0u | no |
| mnf_1h | Sean's Bet Labs screen | 169-120, +10.7% (p 0.026) | 122-87, +11.4% | 47-33, +12.6% | 29 bets, -12.3% (2023 to 2024) | 25, +24.1% | Pinnacle or US-book 1H line from 2023 only | none | no |
| cfb_homefav_7510_under | mined from our 2020-26 data, screen saved 10/28 to 11/3 | 618-528, +4.1% (p 0.075) | 436-395, +2.0% | 181-134, +9.5% | 212 bets, +10.8% (2020 to 2024) | 37, +35.8% | Pinnacle full-game close | 4-6, -1.1u | yes |
| nba_bigfav_over | mined from our 2020-26 data, screen saved 10/28 to 11/3 | 1349-1343, -2.7% (p 0.925) | 1045-1068, -3.5% | 304-275, +0.4% | 446 bets, +8.2% (2020-21 to 2024-25) | 136, +10.1% | Pinnacle full-game close | 5-4, +0.4u | yes |
| nba_badteams_under | mined from our 2020-26 data, screen saved 10/28 to 11/3 | 978-950, -1.2% (p 0.706) | 808-807, -2.2% | 170-143, +3.8% | 308 bets, +2.2% (2020-21 to 2024-25) | 72, +3.6% | Pinnacle full-game close | 3-1, +0.7u | yes |
| nba_ats_hot_home | mined from our 2020-26 data, screen saved 10/28 to 11/3 | 880-854, -1.5% (p 0.740) | 644-665, -4.0% | 236-189, +6.1% | 432 bets, +11.1% (2020-21 to 2024-25) | 12, -1.8% | Pinnacle full-game close | 9-6, +1.0u | yes |
| nba_under_good_home_over | Sean's Bet Labs screen | 755-581, +9.7% (p 0.000) | 575-439, +10.6% | 181-142, +7.1% | 246 bets, +5.4% (2020-21 to 2024-25) | 16, -38.6% | the tool's 1.5-point total drop (the screen starts at 0.5) | 9-4, +2.3u | yes |
| nhl_early_home_fav_qual | Sean's Bet Labs screen | 1184-763, +3.7% (p 0.025) | 880-591, +3.0% | 305-172, +6.0% | 328 bets, +10.1% (2020-21 to 2024-25) | 65, +17.9% | Pinnacle full-game close | 12-10, -1.0u | yes |
| nhl_bounce_home_ml | mined from our 2020-26 data, screen saved 10/28 to 11/3 | 878-593, +1.5% (p 0.245) | 580-410, -0.4% | 298-183, +5.4% | 387 bets, +7.9% (2020-21 to 2024-25) | 13, +52.0% | Pinnacle full-game close | 2-4, -1.3u | yes |
| nhl_skid_fade_road | mined from our 2020-26 data, screen saved 10/28 to 11/3 | 864-889, -3.0% (p 0.899) | 607-660, -6.6% | 257-230, +6.3% | 447 bets, +7.2% (2020-21 to 2024-25) | 19, -48.8% | Pinnacle close on the main NHL spread (puck line) | 6-1, +3.5u | yes |
| cbb_bigloss_vs_top5 | Sean's Bet Labs screen | 151-92, +20.3% (p 0.000) | 113-65, +23.4% | 38-27, +11.8% | not rebuilt | | AP ranks not in our data | none | n/a |

Our rebuild is less than a third the size of the Bet Labs sample for 16 of 17 systems (wind1014, wind1014_1h, cfb_wind14, cfb_hot_over_low_total, awfuldog, nfl_home_dog_7510, vrest8_1h, mnf_1h, cfb_homefav_7510_under, nba_bigfav_over, nba_badteams_under, nba_ats_hot_home, nba_under_good_home_over, nhl_early_home_fav_qual, nhl_bounce_home_ml, nhl_skid_fade_road), because the Odds API history starts in 2020 and Bet Labs goes back to 2003. Bet Labs' records are at its own prices, not Pinnacle's close.

Our rebuild did not reproduce (or only partly reproduced, under half the ROI) Bet Labs' Mar 2021 on record for: wind1014_1h (no; Open-Meteo wind and a Pinnacle or US-book 1H line from 2023 only), cfb_wind14 (partly; Open-Meteo archive wind, not Bet Labs' wind), awfuldog (partly; same kind of data), vrest8_1h (no; Pinnacle or US-book 1H line from 2023 only), mnf_1h (no; Pinnacle or US-book 1H line from 2023 only). Where the data differs, it may be our rebuild, not the system, that is weak.

## 2. Did the live record drive any downgrade?

No. The first audit's verdicts did not use it at all. The first tiering (FOLLOWUP.md) blended it in. Re-running that tiering on history alone gives the same tier for every system: the live record moved some probabilities (nhl_early_home_fav_qual 0.96 to 0.93, cfb_homefav_7510_under 0.89 to 0.85, cfb_wind14 0.31 to 0.66) but crossed no tier line. In version 2 below it is not used at all, except as a tiebreak, and no tiebreak was needed.

## 3. The search penalty: how many variants were assumed

The variant counts were my guess, not a record of what Sean or Bet Labs tried. For each rule I built a grid of nearby versions (6 to 75 per rule: wind bands, spread ranges, win% cutoffs) and charged the system for the best of them. Bet Labs does not save the variants tried before a screen is saved, and Sean's saved Tested:/Tracked: screens hold one version per rule (two for nba_bigfav_over, the home and visitor sides of the same rule). So, as Kirk asked, version 2 drops the search penalty and uses the plain single-filter test plus the full Bet Labs record. The search penalty did matter for the seven mined rules: for those the search was real and larger than my grids (about 100,000 tests per sport), which is why their pre-2021 Bet Labs record is the test that counts.

## 4. Re-tier (full backtest primary)

| System | Before (follow-up) | After (v2) | Bet Labs all-time p | Mar 2021 on p | Why, in one sentence each |
|---|---|---|---|---|---|
| wind1014 | B | **A** | 0.0000 | 0.000 | Meets every Tier A bar on the full Bet Labs backtest. Our rebuild used Open-Meteo archive wind, not Bet Labs' wind. |
| wind1014_1h | C | **B** | 0.0046 | 0.157 | Reduced size because the Mar 2021 on era (116-91, +6.6%) is not significant on its own (p 0.16). Our rebuild used Open-Meteo wind and a Pinnacle or US-book 1H line from 2023 only. |
| cfb_wind14 | C | **A** | 0.0000 | 0.039 | Meets every Tier A bar on the full Bet Labs backtest. Flag, no move: our blind walk-forward was -4.2% on 128 bets. Our rebuild used Open-Meteo archive wind, not Bet Labs' wind. |
| cfb_hot_over_low_total | B | **B** | 0.0050 | 0.153 | Reduced size because only 295 all-time bets and the Mar 2021 on era (53-39, +10.1%) is not significant on its own (p 0.15). Our rebuild used Open-Meteo archive temperature and wind, not Bet Labs' weather. |
| awfuldog | C | **A** | 0.0001 | 0.034 | Meets every Tier A bar on the full Bet Labs backtest. |
| nfl_home_dog_7510 | C | **C** | 0.0707 | 0.035 | Bet Labs' all-time record (119-87, +9.6%) is not strong enough to rule out luck (p 0.071). |
| vrest8_1h | C | **B** | 0.0201 | 0.009 | Reduced size because all-time p 0.020, above 0.01. Flag, no move: the tool's live filter differs from this saved screen (11/18 inventory). Our rebuild used Pinnacle or US-book 1H line from 2023 only. |
| mnf_1h | C | **B** | 0.0256 | 0.116 | Reduced size because only 289 all-time bets and all-time p 0.026, above 0.01 and the Mar 2021 on era (47-33, +12.6%) is not significant on its own (p 0.12). Flag, no move: the tool's live filter differs from this saved screen (11/18 inventory). Our rebuild used Pinnacle or US-book 1H line from 2023 only. |
| cfb_homefav_7510_under | C | **C** | 0.0746 | 0.037 | Bet Labs' all-time record (618-528, +4.1%) is not strong enough to rule out luck (p 0.075). |
| nba_bigfav_over | C | **C** | 0.9255 | 0.460 | Bet Labs' own record before 2021 is 1045-1068, -3.5%: the edge exists only from 2020 on, which is the same window it was found in. Flag, no move: the tool's live filter differs from this saved screen (11/18 inventory). |
| nba_badteams_under | C | **C** | 0.7058 | 0.240 | Bet Labs' own record before 2021 is 808-807, -2.2%: the edge exists only from 2020 on, which is the same window it was found in. Flag, no move: the tool's live filter differs from this saved screen (11/18 inventory). |
| nba_ats_hot_home | C | **C** | 0.7401 | 0.093 | Bet Labs' own record before 2021 is 644-665, -4.0%: the edge exists only from 2020 on, which is the same window it was found in. Flag, no move: the tool's live filter differs from this saved screen (11/18 inventory). |
| nba_under_good_home_over | C | **A** | 0.0001 | 0.089 | Meets every Tier A bar on the full Bet Labs backtest. Flag, no move: our blind walk-forward was -11.6% on 65 bets. Our rebuild used the tool's 1.5-point total drop (the screen starts at 0.5). |
| nhl_early_home_fav_qual | B | **B** | 0.0249 | 0.050 | Reduced size because all-time p 0.025, above 0.01. |
| nhl_bounce_home_ml | C | **C** | 0.2452 | 0.076 | Bet Labs' own record before 2021 is 580-410, -0.4%: the edge exists only from 2020 on, which is the same window it was found in. Flag, no move: the tool's live filter differs from this saved screen (11/18 inventory). |
| nhl_skid_fade_road | C | **C** | 0.8991 | 0.083 | Bet Labs' own record before 2021 is 607-660, -6.6%: the edge exists only from 2020 on, which is the same window it was found in. Flag, no move: the tool's live filter differs from this saved screen (11/18 inventory). |
| cbb_bigloss_vs_top5 | C | **B** | 0.0004 | 0.156 | Reduced size because only 243 all-time bets and the Mar 2021 on era (38-27, +11.8%) is not significant on its own (p 0.16). |

Not in this table: xch_homedog_fade and the four curve rules (no Bet Labs screen and no multi-season replay; they stay where Sean has them).

