# Signal and systems study, 2026-11-24

Read only: no rule, tier, gate or paper/live status was changed. Everything here is a recommendation for Sean.

**Judged on realized profit:**
- units and ROI at the prices actually taken
- sample size
- a significance read against break-even at those prices
- stability across sub-periods

CLV is not used for any call. Pre-specified before running: the condition tests in section 2, the tag list, the time splits (1st half to
11/11, 2nd half from 11/12, last 2 weeks from 11/10), the 10% false-discovery bar, and the holdout design.

## Summary

**What holds up**
- **Mechanism and out-of-sample support (the core rule set):**
  - wind1014: walk-forward +28.3% on 104, the only individually significant out-of-sample result
  - cfb_hot_over_low_total: +17.8% on 119
  - nhl_early_home_fav_qual: +9.3% on 222
  - cfb_homefav_7510_under: +8.7% on 180
  - awfuldog: +12.7% on 70
  - nfl_home_dog_7510: +12.4% on 36
  - xch_homedog_fade: live 82-28, +4.4% on 110
  - The derivative curve rules: a real pricing mechanism, though nhl_p3 is losing; see below.
- **The market tags do not hold up as gates.** None of 202 tag and combination tests survives a 10% false-discovery correction
  (Benjamini-Hochberg), and none of the 15 tags that looked significant in the first half holds in the second half.

**What doesn't**
- **8 rules have no stateable mechanism (mined):** wind1014_cold, awfuldog_deep, nba_ats_hot_home, nhl_loss_streak_over,
  nhl_pl_fav_gap, nhl_pl_fav_strong_opp, nhl_pl_dog_bigml, cfb_day_over (already retired). mnf_1h has no Monday-specific one.
- **Kalshi move against (our one hard gate)** was a strong warning early: -32% ROI on 118 positions before 11/12. It has faded to
  -4% on 148 since, not significantly different from rows without it. It is still negative, never positive; it has weakened, not
  flipped.
- **Sharp accounts against** has never been a signal: -4.1% overall vs -3.2% baseline, and 2nd half +1%. Showing it without
  holding (the 11/14 call) is right.
- **Arbitrary conditions tested:**
  - **CFB 2-7pm window:** not a proxy for non-power-conference teams. Afternoon overs win for power home teams too (+9.2%), and
    non-power home teams lose outside the window (-7.1%). Heat doesn't explain it either. The window is strong in-sample (+12.2%
    on 540, every season positive) but was mined on this same data, has no mechanism, and went 11-16 live. It stays retired.
  - **Monday (mnf_1h):** no better per bet than all primetime unders, and neither is significant.
  - **CBB weekday filter:** irrelevant. The rule loses either way (-5.9% on 1,488, z -2.4).

**Recommendations for Sean**
1. **Gates:** keep "Kalshi move against" as a shown warning, not a hard block, or keep the block knowing the evidence has faded.
   Keep "sharp accounts against" display-only. Gate nothing else. Watch one combination: Kalshi move against with big money on our
   side (-47% on 55; -29% in the 2nd half). It is the most persistent negative but not proven.
2. **Rules to paper:**
   - the 7 mined live rules
   - cbb_under_good_over_drop (replay loses)
   - nhl_p3_under_curve (live -34% on 42)
   - nfl_road_dog_7510, nfl_fade_fav_bye, bounce15_1h, cfb_road_streak_dog, nba_under_good_home_over_small (replays failed)
3. **Rules to fold:** wind1014_cold into wind1014, awfuldog_deep into awfuldog.
4. **mnf_1h:** broaden to all primetime unders or put it on paper.

## 1. Mechanism audit (every live and paper rule)

Walk-forward = the 11/18 validation audit, each season bet with the variant fitted on earlier seasons only (docs/validation/SUMMARY.md).
Live = this log (10/30 on), flat 0.25u at the actual prices.

| Rule | Tier now | Why it should work (one sentence), or "no mechanism" | Arbitrary conditions | Walk-forward out-of-sample (11/18) | Live log ROI (n) | Read |
|---|---|---|---|---|---|---|
| wind1014 | A | Wind of 10-14 mph cuts passing and kicking, and totals only fully adjust for extreme wind. | none (the band is the mechanism) | +28.3% (104), significant | +31.1% (12) | Keep. Mechanism plus the one significant out-of-sample result. |
| wind1014_1h | B | Same wind effect; the first half is closest to the forecast the bet is placed on. | none | +8.4% (25) | +51.8% (9) | Keep. |
| cfb_wind14 | A | Same wind effect at the higher CFB threshold. | none | -4.2% (128) | +20.2% (23) | Keep on mechanism and live 14-9. Walk-forward is -4.2% on our Open-Meteo wind, which is not the wind it fires on. |
| wind1014_cold | C | No mechanism of its own: a temperature split of wind1014 (27-27 in the replay). | cold split | - | - | Fold into wind1014; drop as a rule. |
| cfb_hot_over_low_total | B | Heat wears defences down, and low totals price it least. | non-conference | +17.8% (119) | - | Keep. The replay supports it: total 55 or less +9.2%, above 55 -16.5%; non-conference +18.4% vs conference -16.4%. |
| awfuldog | A | The public and books fade very bad teams, so they are overpriced as underdogs. | none | +12.7% (70) | - | Keep. |
| awfuldog_deep | C | No mechanism of its own: a deeper cut of awfuldog. | arbitrary threshold | - | - | Drop (14-16 in the replay). |
| bounce15_1h | C | The market overreacts to a blowout ATS loss. | first half only (arbitrary) | - | -49.7% (8) | Weak (2-6 live). Paper. |
| nfl_home_dog_7510 | C | Big road favourites draw public money; 7.5-10 brackets the key numbers 7 and 10. | band set by key numbers (a real proxy) | +12.4% (36) | - | Keep (Bet Labs +9.6% on 206; walk-forward +12.4% on 36). |
| nfl_road_dog_7510 | C | Same public bias as the home version, but the replay failed. | band | - | - | Paper. |
| nfl_fade_fav_bye | C | The market overrates rested favourites coming off a bye. | none | - | -49.3% (5) | Paper (70-84 ATS in the replay). |
| vrest8_1h | B | Teams off long rest start slowly (rust), which shows in first halves. | first half (part of the mechanism) | +37.4% (24) | -27.9% (8) | Weak. Walk-forward +37.4% on only 24 bets. Keep at B on the Bet Labs backtest; review at 50 live. |
| mnf_1h | B | No Monday-specific mechanism. "Primetime unders" is the plausible version. | day of week | +24.1% (25) | - | Test showed Monday (+11.0% on 124) no better per bet than all primetime (+6.8% on 339); neither significant. Broaden to primetime or paper. |
| nba_ats_hot_home | C | No mechanism. ATS form usually mean-reverts, which argues the other way. | exactly 2 days rest | +3.2% (74) | +5.8% (20) | Mined. Paper. |
| nba_bigfav_over | C | Mismatches run up the score, and garbage time is played at pace. | none | +2.7% (370) | +6.5% (11) | Keep at C (walk-forward +2.7% on 370; thin). |
| nba_badteams_under | C | Two bad teams make poor offences, and the public bets overs. | win% bands | +3.7% (193) | +28.5% (6) | Keep at C (walk-forward +3.7% on 193; thin). |
| nba_roadtrip_over | C | Fatigue on a long road trip weakens defence. | none | - | +16.7% (10) | Keep at C. |
| nhl_loss_streak_over | C | No mechanism: an over-rate band of 40-60% on a losing streak. | over% band | - | -42.0% (13) | Mined; -42% live. Paper. |
| nhl_bounce_home_ml | C | The market overreacts to a 3+ goal loss. | win% band 50-64% | +3.3% (114) | -41.1% (6) | Keep at C (walk-forward +3.3% on 114). |
| nhl_skid_fade_road | C | Streaks are overweighted (road team off a win vs a home team on a skid). | none | +8.0% (169) | +68.2% (9) | Thin mechanism, +68% on 9 live. Keep at C and watch. |
| nhl_early_home_fav_qual | B | Early-season prices lean on last season, and home favourites with a good opponent are underpriced. | game 24 or earlier (a real proxy: before the market updates) | +9.3% (222) | -10.1% (25) | Keep. Best walk-forward among the NHL rules (+9.3% on 222). |
| nhl_pl_fav_gap | C | No mechanism. | win% gap 22+ | - | - | Mined. Paper. |
| nhl_pl_fav_strong_opp | C | No mechanism. | opponent win% 66+ | - | +5.4% (8) | Mined. Paper. |
| nhl_pl_dog_bigml | C | No mechanism: a price window. | ML +181 to +196 | - | -17.1% (7) | Mined. Paper. |
| nba_1h_under_hot_over | C | Recent overs inflate a team's totals, so fade it early. | first half, 71% cutoff | - | +57.5% (6) | Weak mechanism; 5-1 live. Keep at C. |
| nba_under_good_home_over | A | Totals falling against over-heavy teams means informed under money. | rest windows | -11.6% (65) | +26.5% (14) | Walk-forward -11.6% on 65; live 9-5. Keep, but drop to B or C. Sean said not to retire on history alone. |
| nba_under_good_home_over_small | C | Same as above with a smaller drop. | drop size | - | - | Paper. |
| cfb_homefav_7510_under | C | A home favourite in control runs the clock late: fewer possessions. | spread band | +8.7% (180) | -21.8% (10) | Keep (walk-forward +8.7% on 180). |
| cfb_day_over | retired | No mechanism found. Neither the non-power-conference proxy nor heat explains the afternoon effect (test below). | kickoff window | - | -22.6% (27) | Stays off; see section 2. |
| cfb_road_dog_low_total | retired | Low totals compress margins, so big underdogs cover more often. | total 48 or less | - | -9.9% (30) | Retired 11/23 on a CLV line; to re-decide on profit (section 5). |
| cfb_road_streak_dog | C | Weak: a road-streak team has been underrated. | streak 2-5, total 54 or less | - | +0.5% (9) | Paper. |
| cbb_bigloss_vs_top5 | B | Overreaction to a blowout, plus a motivated underdog against an elite opponent. | none | - | - | Keep (Bet Labs +20.3% on 243). |
| cbb_under_good_over_drop | C | A total falling against over-heavy teams means informed under money. | weekdays only | - | +12.0% (7) | The replay loses with or without the weekday filter (-5.9% on 1,488, z -2.4). Paper. |
| mlb_road_over_under | C | Team over-rates regress; the market overweights them. | over% 60+ | - | - | Mined; out of season. Paper. |
| xch_homedog_fade | C | Late two-sided exchange books on home underdogs carry retail home bias; fade it at the exchange price. | price 20-35c, T-90m | - | +4.4% (110) | Keep. Best live sample (82-28, +4.4%). |
| curve rules (cfb_q1, cfb_tt, cbb_1h, nhl_p1, nhl_p3) | A/C | Derivative lines are set off the full-game number by a fixed ratio; when the curve says the gap is large, the derivative is stale. | gap thresholds | - | - | Real mechanism; nhl_p3 is losing badly (-34% on 42). Paper nhl_p3; keep the rest. |
| tennis_serve_dog | live | Big servers hold serve, so tiebreaks and upsets are likelier than the ML implies. | serve stat cutoff | - | +3.7% (99) | Keep; flat so far (+3.7% on 99). |
| stale_book | paper | A book slow to move after the market can be picked off (latency). | none | - | +2.1% (253) | Real mechanism; break-even so far (+2.1% on 253). Stays paper. |
| sharp flags | paper (soccer live) | Following accounts with a winning history means following informed money. | account cut-offs | - | - | Real in principle; results differ by sport (soccer A +20.5%, NBA B +14.3%, NHL A -40%). |

The audit's other result: grid-aware permutation (each rule tested against the best of its own nearby variants under shuffled outcomes)
passes none of the 16 replayable rules at 5%. That is the multiple-testing caution behind every "keep" above. The walk-forward results
are the evidence that survives it, with wind1014 the only one significant on its own.

## 2. Arbitrary conditions: what removing them does

Replays on the Odds API history (2020 to 2026), Pinnacle closing price, 1 unit per bet. z is against break-even at the price.

**CFB overs, closing total 45-51.5: is the 2-7pm window a proxy for non-power-conference teams?** Non-power home teams are 52% of
afternoon games vs 40% at other times, so the proxy is real, but it does not carry the effect:

| Slice | Bets | Record | Units (1u) | ROI | z | ROI by season |
|---|---|---|---|---|---|---|
| all 45-51.5 overs | 1494 | 788-684 | +45.0 | +3.0% | +1.22 | 2020: +4, 2021: +1, 2022: -7, 2023: +14, 2024: +4, 2025: +2, 2026: +0 |
| 2-7pm ET | 540 | 311-221 | +66.1 | +12.2% | +2.98 | 2020: +15, 2021: +3, 2022: +8, 2023: +19, 2024: +15, 2025: +15, 2026: +5 |
| not 2-7pm | 954 | 477-463 | -21.1 | -2.2% | -0.71 | 2020: -3, 2021: -0, 2022: -17, 2023: +11, 2024: -2, 2025: -4, 2026: -2 |
| G5 home team | 653 | 341-301 | +14.5 | +2.2% | +0.60 | 2020: +8, 2021: +12, 2022: -7, 2023: +13, 2024: +10, 2025: -7, 2026: -7 |
| power home team | 841 | 447-383 | +30.5 | +3.6% | +1.10 | 2020: +2, 2021: -6, 2022: -8, 2023: +15, 2024: +0, 2025: +8, 2026: +6 |
| both G5 | 611 | 322-278 | +20.3 | +3.3% | +0.86 | 2020: +8, 2021: +16, 2022: -7, 2023: +12, 2024: +7, 2025: -2, 2026: -6 |
| G5 home, 2-7pm | 272 | 160-106 | +41.4 | +15.2% | +2.65 | 2020: +24, 2021: +18, 2022: +12, 2023: +17, 2024: +15, 2025: +15, 2026: +10 |
| G5 home, other times | 381 | 181-195 | -26.9 | -7.1% | -1.44 | 2020: -3, 2021: +8, 2022: -23, 2023: +9, 2024: +6, 2025: -18, 2026: -17 |
| power home, 2-7pm | 268 | 151-115 | +24.7 | +9.2% | +1.57 | 2020: +9, 2021: -9, 2022: +3, 2023: +21, 2024: +16, 2025: +16, 2026: -0 |
| power home, other times | 573 | 296-268 | +5.8 | +1.0% | +0.26 | 2020: -4, 2021: -4, 2022: -13, 2023: +12, 2024: -7, 2025: +5, 2026: +10 |

Read: the window adds ROI within both groups. Power home teams go +9.2% in the window vs +1.0% outside it; non-power home teams go
+15.2% vs -7.1%. So the effect is not the conference mix. Heat doesn't explain it either: the 11/5 temperature replay has overs
negative in every temperature band. With no mechanism, a mined window and an 11-16 live record, it stays off.
Power conferences here = the 2024 SEC, Big Ten, Big 12 and ACC, plus Oregon State, Washington State and Notre Dame, for every season.

**NFL full-game unders by slot (the mnf_1h question):**

| Slice | Bets | Record | Units (1u) | ROI | z | ROI by season |
|---|---|---|---|---|---|---|
| all unders | 1662 | 832-806 | -22.2 | -1.3% | -0.56 | 2020: -4, 2021: +5, 2022: +8, 2023: +2, 2024: -12, 2025: -7 |
| Mon | 124 | 70-52 | +13.6 | +11.0% | +1.27 | 2020: +12, 2021: +24, 2022: +13, 2023: +33, 2024: -20, 2025: +5 |
| Thu | 110 | 55-55 | -2.8 | -2.5% | -0.27 | 2020: -16, 2021: +30, 2022: +23, 2023: -39, 2024: -7, 2025: -8 |
| Sun night | 105 | 59-44 | +12.1 | +11.5% | +1.22 | 2020: +18, 2021: -37, 2022: +35, 2023: +41, 2024: +11, 2025: +9 |
| all primetime (Mon/Thu/Sun night) | 339 | 184-151 | +23.0 | +6.8% | +1.29 | 2020: +7, 2021: +4, 2022: +23, 2023: +13, 2024: -7, 2025: +2 |
| Sun day | 1258 | 619-620 | -37.4 | -3.0% | -1.09 | 2020: -5, 2021: +4, 2022: +4, 2023: +1, 2024: -13, 2025: -9 |

Read: the Monday filter is not special. All primetime unders (+6.8% on 339) give nearly three times the sample for a lower ROI, and
none of the slots is significant. Day games lose (-3.0% on 1,258). If a primetime-under mechanism is accepted (night games, slower
pace), the rule should be "primetime", not "Monday".

**CBB under (over-heavy teams, total down 0.5+): does the weekday filter matter?**

| Slice | Bets | Record | Units (1u) | ROI | z | ROI by season |
|---|---|---|---|---|---|---|
| no day filter | 1488 | 727-746 | -87.6 | -5.9% | -2.40 | 2020: +1, 2021: -1, 2022: -20, 2023: -6, 2024: -7, 2025: +4, 2026: -30 |
| Mon-Fri (live rule) | 829 | 406-415 | -46.9 | -5.7% | -1.72 | 2020: +23, 2021: -0, 2022: -10, 2023: -9, 2024: -14, 2025: -4, 2026: -17 |
| Sat-Sun | 659 | 321-331 | -40.7 | -6.2% | -1.67 | 2020: -26, 2021: -2, 2022: -34, 2023: -2, 2024: +0, 2025: +14, 2026: -67 |

Read: the day filter changes nothing, and the rule itself loses on 1,488 bets (z -2.4). Recommend paper.

## 3. Market tags and signals

Each game-side position counts once (several rules on one game share one outcome). Tags are the union over the rows on that position.
1,537 graded positions, 10/30 to 11/23, flat 0.25u at the logged price. "ROI vs rows without" is the gap to every other position, with
a 2,000-shuffle permutation p.

| Tag (rows carrying it) | Positions | Units | ROI | z vs break-even | ROI vs rows without (pts) | Permutation p | 1st half (to 11/11) | 2nd half (11/12 on) | Last 2 weeks |
|---|---|---|---|---|---|---|---|---|---|
| ALL positions (baseline) | 1537 | -17.50 | -3.2% | -1.40 | - | - | 335-381, -11% | 441-368, +4% | 508-437, +2% |
| Kalshi move against | 266 | -13.32 | -15.9% | -2.65 | -15.0 | 0.0125 | 37-81, -32% | 72-71, -4% | 81-81, -4% |
| Kalshi move with | 340 | +6.52 | +5.5% | +1.12 | 11.0 | 0.039 | 75-77, -4% | 108-79, +14% | 117-96, +10% |
| sharp accts against | 374 | -5.31 | -4.1% | -0.86 | -1.2 | 0.8266 | 91-107, -8% | 88-82, +1% | 105-100, -0% |
| sharp accts with | 226 | -8.11 | -10.4% | -1.73 | -8.5 | 0.1774 | 57-71, -9% | 46-52, -12% | 60-60, -6% |
| big money with | 248 | -12.80 | -16.7% | -2.65 | -15.7 | 0.0065 | 35-75, -34% | 66-72, -5% | 76-81, -2% |
| big money against | 228 | +7.40 | +8.7% | +1.52 | 14.0 | 0.0245 | 48-42, +3% | 79-56, +12% | 86-68, +8% |
| bet back with | 235 | -4.42 | -5.5% | -0.90 | -2.8 | 0.6412 | 45-74, -24% | 69-47, +12% | 77-58, +9% |
| bet back against | 216 | -0.35 | -0.5% | -0.08 | 3.0 | 0.6392 | 39-55, -16% | 64-55, +12% | 74-65, +11% |
| sharp move with | 136 | +1.42 | +3.1% | +0.38 | 6.8 | 0.3833 | 34-38, -8% | 34-30, +16% | 42-36, +16% |
| sharp move against | 104 | -1.19 | -3.2% | -0.36 | -0.1 | 0.991 | 27-33, -10% | 23-20, +6% | 30-23, +10% |
| sharp flag also | 130 | -6.21 | -15.3% | -1.79 | -13.1 | 0.1004 | 27-39, -15% | 28-36, -16% | 32-39, -13% |
| sharp flag against | 126 | -1.92 | -4.0% | -0.53 | -1.0 | 0.903 | 34-35, -1% | 30-27, -8% | 35-29, -3% |
| system also | 41 | -1.12 | -8.5% | -0.58 | -5.5 | 0.6672 | 9-6, +15% | 11-15, -21% | 13-15, -14% |
| system against | 91 | -7.00 | -21.4% | -2.29 | -19.4 | 0.0455 | 10-19, -29% | 25-37, -18% | 25-42, -24% |
| middle | 46 | +0.76 | +4.3% | +0.34 | 7.7 | 0.5617 | 12-8, +16% | 13-13, -5% | 13-13, -5% |
| no signal against | 764 | -8.78 | -3.0% | -0.98 | 0.4 | 0.94 | 189-185, -9% | 217-172, +3% | 255-208, +1% |
| any signal against | 773 | -8.72 | -3.4% | -1.01 | -0.4 | 0.943 | 146-196, -13% | 224-196, +4% | 253-229, +3% |

**Kalshi move against:** -32% before 11/12, -4% from 11/12 on, -4% over the last two weeks. It was a warning sign. It is still on the
losing side but no longer separates from the baseline (2nd half gap -9 pts, p 0.25). It has not flipped.

**Sharp accounts against:** -4.1% overall, a gap of -1 pt to the rest (p 0.83), +1% in the 2nd half. No signal at any point.

By sport (only cells with 15+ positions):

| Tag by sport | Positions | Units | ROI | z vs break-even | ROI vs rows without (pts) | Permutation p | 1st half (to 11/11) | 2nd half (11/12 on) | Last 2 weeks |
|---|---|---|---|---|---|---|---|---|---|
| Kalshi move against | cbb | 37 | -0.52 | -5.5% | -0.32 | -18.1 | 0.3513 | 4-8, -18% | 12-13, +0% | 13-16, -4% |
| Kalshi move against | cfb | 69 | -3.03 | -13.9% | -1.27 | -13.1 | 0.3293 | 8-21, -41% | 23-17, +4% | 25-19, +3% |
| Kalshi move against | nba | 84 | -3.76 | -14.0% | -1.25 | -9.1 | 0.4038 | 15-32, -30% | 19-18, +2% | 25-23, +4% |
| Kalshi move against | nfl | 31 | -2.02 | -19.1% | -1.12 | -19.5 | 0.2964 | 7-8, -6% | 6-10, -32% | 6-10, -32% |
| Kalshi move against | nhl | 40 | -3.73 | -27.1% | -2.04 | -23.6 | 0.1109 | 3-9, -51% | 10-13, -17% | 10-13, -17% |
| sharp accts against | cfb | 33 | +0.91 | +9.2% | +0.56 | 14.5 | 0.4133 | 5-7, -5% | 13-8, +16% | 14-9, +15% |
| sharp accts against | nba | 220 | -7.66 | -9.9% | -1.59 | -8.5 | 0.3798 | 55-71, -12% | 43-51, -6% | 55-62, -4% |
| sharp accts against | nfl | 46 | -3.54 | -22.0% | -1.54 | -31.2 | 0.068 | 12-16, -12% | 6-12, -38% | 6-12, -38% |
| sharp accts against | nhl | 63 | +2.90 | +12.3% | +1.19 | 26.5 | 0.035 | 13-11, -3% | 23-10, +23% | 27-16, +13% |

Two-tag combinations:

| Two-tag combination (40+ positions; 12 lowest p) | Positions | Units | ROI | z vs break-even | ROI vs rows without (pts) | Permutation p | 1st half (to 11/11) | 2nd half (11/12 on) | Last 2 weeks |
|---|---|---|---|---|---|---|---|---|---|
| Kalshi move against + big money with | 55 | -8.01 | -47.4% | -3.32 | -45.7 | 0.0015 | 5-27, -66% | 8-15, -29% | 10-18, -25% |
| any signal against + big money with | 176 | -12.28 | -22.0% | -2.93 | -21.0 | 0.0025 | 25-63, -40% | 41-47, -7% | 48-54, -4% |
| Kalshi move against + any signal against | 266 | -13.32 | -15.9% | -2.65 | -15.0 | 0.0095 | 37-81, -32% | 72-71, -4% | 81-81, -4% |
| Kalshi move with + big money against | 64 | +5.90 | +23.2% | +2.17 | 27.6 | 0.016 | 22-8, +29% | 19-15, +18% | 22-20, +12% |
| Kalshi move with + no signal against | 125 | +6.35 | +15.4% | +1.90 | 20.0 | 0.0175 | 25-21, +4% | 52-27, +23% | 55-29, +23% |
| bet back with + sharp accts with | 80 | -7.06 | -26.8% | -2.54 | -24.8 | 0.018 | 16-35, -34% | 13-16, -15% | 16-19, -13% |
| Kalshi move with + big money with | 87 | -6.36 | -23.2% | -2.22 | -21.1 | 0.0245 | 13-30, -37% | 19-25, -12% | 20-30, -16% |
| any signal against + big money against | 228 | +7.40 | +8.7% | +1.52 | 14.0 | 0.0245 | 48-42, +3% | 79-56, +12% | 86-68, +8% |
| sharp accts against + sharp flag also | 74 | -5.19 | -22.8% | -1.94 | -20.5 | 0.0385 | 17-29, -20% | 10-18, -27% | 12-20, -24% |
| any signal against + sharp flag also | 99 | -6.31 | -20.0% | -2.04 | -17.8 | 0.0415 | 19-34, -22% | 19-27, -17% | 23-29, -13% |
| any signal against + system against | 91 | -7.00 | -21.4% | -2.29 | -19.4 | 0.046 | 10-19, -29% | 25-37, -18% | 25-42, -24% |
| bet back with + sharp flag against | 45 | -4.80 | -28.4% | -2.23 | -26.1 | 0.0485 | 9-18, -29% | 8-10, -27% | 8-11, -30% |

## 4. Multiple comparisons

- **Benjamini-Hochberg at a 10% false-discovery rate:** 202 tests (18 tags, by sport and by source, and 2-tag combinations with 40+
  positions). Survivors on the ROI gap to other rows: 0 of 198. Survivors on the break-even test: 0 of 202.
- **Holdout:** every tag, tag-by-sport or combination with a gap at p 0.05 or less in the 1st half (15 of them) was carried forward and
  tested only on the 2nd half, in the same direction, with a Bonferroni bar across the 15. None holds:

| Found in the 1st half (lift p 0.05 or less) | 1st half n | 1st half lift | 2nd half n | 2nd half lift | 2nd half p | Same direction | 2nd half record |
|---|---|---|---|---|---|---|---|
| Kalshi move against + big money with | 32 | -56.5 | 23 | -33.5 | 0.076 | yes | 8-15, -28.9% |
| bet back with + big money with | 42 | -46.6 | 35 | +18.8 | 0.210 | no | 22-13, +21.6% |
| big money with | 110 | -25.8 | 138 | -9.7 | 0.226 | yes | 66-72, -4.7% |
| any signal against + big money with | 88 | -31.8 | 88 | -11.8 | 0.226 | yes | 41-47, -7.0% |
| Kalshi move against + any signal against | 118 | -24.7 | 148 | -9.1 | 0.248 | yes | 72-71, -4.0% |
| Kalshi move against | 118 | -24.7 | 148 | -9.1 | 0.251 | yes | 72-71, -4.0% |
| big money with + sharp accts with | 44 | -28.1 | 23 | +19.2 | 0.288 | no | 15-8, +22.3% |
| big money with + sharp flag also | 27 | -44.2 | 17 | +21.0 | 0.332 | no | 11-6, +24.2% |
| Kalshi move with + big money against | 30 | +42.0 | 34 | +14.6 | 0.339 | yes | 19-15, +17.5% |
| big money against + sharp flag against | 27 | +33.9 | 15 | -18.6 | 0.410 | no | 8-7, -14.6% |
| Kalshi move against + bet back with | 30 | -35.9 | 45 | -7.8 | 0.559 | yes | 23-22, -3.7% |
| big money with | nba | 55 | -30.3 | 43 | -4.5 | 0.736 | yes | 21-22, -0.7% |
| big money with + sharp accts against | 68 | -21.8 | 41 | +2.4 | 0.871 | no | 22-19, +5.9% |
| any signal against + bet back with | 94 | -21.3 | 89 | +0.9 | 0.929 | no | 48-41, +4.4% |
| bet back with | nfl | 24 | -35.9 | 17 | -1.4 | 0.944 | yes | 9-8, +2.2% |

**What survives as real signal: nothing yet.** The strongest candidate is "Kalshi move against + big money with". It is negative in
both halves (-66%, then -29% on 23) and has a plausible mechanism: retail-sized money on our side while the exchange price moves
against us means informed flow on the other side. It does not clear the bar yet. "Big money with" alone (-34% then -5%) and
"Kalshi move against" alone have faded.

Limits: 25 days of tagged data. The tags overlap (any signal against includes Kalshi move against). Positions on the same game day
are correlated. A month more data doubles the holdout.

## 5. Recommendations

**Gates:**
1. **Kalshi move against:** the evidence no longer supports a hard block on its own. Options: (a) make it a shown warning, as the
   sharp tags are; (b) keep the block on the early evidence and re-read at the next checkpoint. It has never been a positive sign.
2. **Sharp accounts, bet back, big money, sharp move, middle, sharp flag also/against:** display only. None separates from the baseline
   after correction.
3. **Conflict rule (opposite-side systems cancel):** not testable here, because cancelled rows are not graded. It stays as Sean set it.
4. **Watch list, not a gate:** Kalshi move against + big money with.

**A short rule set Sean could present** (each with a one-sentence reason, a long backtest and out-of-sample support):
- **Weather:** wind1014 and wind1014_1h (NFL wind 10-14 mph), cfb_wind14, cfb_hot_over_low_total (CFB heat, low total,
  non-conference).
- **Market overreaction:** awfuldog (NFL dogs with a terrible margin), nfl_home_dog_7510 (home dogs across the 7 to 10 key numbers),
  cbb_bigloss_vs_top5, nhl_bounce_home_ml.
- **Game script:** cfb_homefav_7510_under (big home favourites run the clock).
- **Stale early-season prices:** nhl_early_home_fav_qual.
- **Market microstructure:** xch_homedog_fade (late retail home bias on exchanges), the derivative curve rules except nhl_p3 (lines set
  off the full game by a fixed ratio), stale_book (paper; latency).
- **Informed money:** soccer sharp flags (live).

**Out of the presentation set** (paper, pending Sean):
- the 7 mined live rules (nba_ats_hot_home, nhl_loss_streak_over, nhl_pl_fav_gap, nhl_pl_fav_strong_opp, nhl_pl_dog_bigml, plus
  wind1014_cold and awfuldog_deep folded into their parents)
- cbb_under_good_over_drop
- nhl_p3_under_curve
- the rules whose own replay failed: nfl_road_dog_7510, nfl_fade_fav_bye, bounce15_1h, cfb_road_streak_dog,
  nba_under_good_home_over_small
- mnf_1h (until it is broadened to primetime)

**Open items for Sean:**
- the wind source (MySportsWeather alone vs the two-source average)
- the four 11/23 checkpoint calls that rested on CLV (docs/weekly_review_2026-11-23.md, section 5)
- profit-based checkpoint lines (same doc, section 6)

**Note on the wind description:** the wind rules' text in sharp/systems.py says "average of the latest Open-Meteo and MySportsWeather
forecasts", but the code fires on MySportsWeather alone (Open-Meteo only as a fallback), per Sean's 11/14 call. One of the two should
change once he decides the wind source.

Files: the replay script and outputs are not committed (data/oddsapi/odds.sqlite is rebuilt locally by sharp/odds_db.py); the numbers
above are the record.
