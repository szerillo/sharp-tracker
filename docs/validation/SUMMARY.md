# Systems validation audit (board_r10): summary

Built 2026-11-18 18:22 UTC by sharp/validate_summary.py from data/research/validation.json. Plan: [VALIDATION_PLAN.md](VALIDATION_PLAN.md) (registered before any result). Read-only: verdicts are recommendations; no tier or live/paper status was changed.

## Plain-language read

**Which systems to trust with real money: none yet.** Under the bar set before any result was run, none of the 16 systems that can be replayed earns KEEP, and none earns WATCH. Fourteen come out PAPER ONLY and two come out RETIRE. Six more can't be judged on the data we have.

Why: on the actual results, most of these systems look good. Nine of the 16 beat the plain single-filter shuffle test (p at or below about 0.05). But each one was picked from a range of nearby versions: different wind bands, spread ranges, win% cutoffs. If you shuffle the outcomes and search that same range, the best version often looks just as good as the live system does on real data. That's the gate 2 test, and no system cleared p < 0.05. The closest was nhl_early_home_fav_qual at 0.087. With 16 systems tested, chance alone would let about 1 through, and 0 got through.

These are not all dead. Several kept winning when bet blind, and those are the ones worth tracking:

- **wind1014 (NFL wind under, tier A now).** Bet blind with the band fitted on earlier seasons, it went +28.3% on 104 bets (2022 to 2025), and that result is significant on its own (p < 0.005). Every walk-forward fit picked the 11 to 14 mph band. The plateau around 10 to 14 holds: all four neighbours are positive. The problem is that the in-sample edge doesn't beat the search test (p 0.314), and the test uses archive wind, not MySportsWeather. It's the strongest candidate to keep as a lead. Moving it from tier A to a smaller size is Sean's call.
- **cfb_homefav_7510_under (CFB under).** Blind: +8.7% on 180 (p 0.015, which misses the 0.01 bar for 2+ seasons). The plateau holds. The middle of the plateau is the live 7.5 to 10 range.
- **nhl_early_home_fav_qual (NHL, tier B now).** Closest to passing the search test (p 0.087). Blind: +9.3% on 222 (p 0.015). The plateau holds.
- **cfb_hot_over_low_total (CFB over, tier B now).** Blind: +17.8% on 119 (p 0.02). But it has only 69 in-sample bets, and the live filter uses the closing total.

Recommend retiring two. **cfb_wind14:** +0.1% in-sample and -4.2% on 128 blind bets. **nba_under_good_home_over:** -11.6% on 65 blind bets and -38.6% in the 2025-26 holdout. Retirements need Sean's OK. Nothing has been changed.

What would change a verdict: one more season of blind results. The walk-forward permutation (gate 4) is the test that matters most for the leads above, and wind1014 already clears it.

## Ranked table

| # | System | Sport | N | ROI | Permutation p (grid) | p (single filter, weaker) | Walk-forward OOS ROI (N) | Holdout ROI (N) | Plateau | Verdict | Reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [nhl_early_home_fav_qual](nhl_early_home_fav_qual.md) | NHL | 328 | +10.1% | 0.087 | 0.012 | +9.3% (222) | +17.9% (65) | yes | PAPER ONLY | edge is within what searching 25 variants finds by luck (grid p 0.087); walk-forward +9.3% on 222 |
| 2 | [cfb_homefav_7510_under](cfb_homefav_7510_under.md) | CFB | 212 | +10.8% | 0.127 | 0.007 | +8.7% (180) | +35.8% (37) | yes | PAPER ONLY | edge is within what searching 30 variants finds by luck (grid p 0.127); walk-forward +8.7% on 180 |
| 3 | [nba_bigfav_over](nba_bigfav_over.md) | NBA | 446 | +8.2% | 0.176 | 0.018 | +2.7% (370) | +10.1% (136) | yes | PAPER ONLY | edge is within what searching 7 variants finds by luck (grid p 0.176); walk-forward +2.7% on 370 |
| 4 | [nfl_home_dog_7510](nfl_home_dog_7510.md) | NFL | 57 | +21.3% | 0.234 | 0.053 | +12.4% (36) | +25.2% (6) | yes | PAPER ONLY | edge is within what searching 30 variants finds by luck (grid p 0.234); walk-forward +12.4% on 36 |
| 5 | [nhl_skid_fade_road](nhl_skid_fade_road.md) | NHL | 447 | +7.2% | 0.262 | 0.050 | +8.0% (169) | -48.8% (19) | yes | PAPER ONLY | edge is within what searching 4 variants finds by luck (grid p 0.262); walk-forward +8.0% on 169 |
| 6 | [nhl_bounce_home_ml](nhl_bounce_home_ml.md) | NHL | 387 | +7.9% | 0.267 | 0.012 | +3.3% (114) | +52.0% (13) | yes | PAPER ONLY | edge is within what searching 27 variants finds by luck (grid p 0.267); walk-forward +3.3% on 114 |
| 7 | [nba_ats_hot_home](nba_ats_hot_home.md) | NBA | 432 | +11.1% | 0.301 | 0.000 | +3.2% (74) | -1.8% (12) | no | PAPER ONLY | edge is within what searching 12 variants finds by luck (grid p 0.301); walk-forward +3.2% on 74 |
| 8 | [wind1014](wind1014.md) | NFL | 211 | +14.7% | 0.314 | 0.056 | +28.3% (104) | +57.0% (22) | yes | PAPER ONLY | edge is within what searching 29 variants finds by luck (grid p 0.314); walk-forward +28.3% on 104, itself significant (p 0.000) |
| 9 | [cfb_hot_over_low_total](cfb_hot_over_low_total.md) | CFB | 69 | +20.0% | 0.323 | 0.038 | +17.8% (119) | +20.7% (27) | yes | PAPER ONLY | edge is within what searching 72 variants finds by luck (grid p 0.323); walk-forward +17.8% on 119 |
| 10 | [vrest8_1h](vrest8_1h.md) | NFL | 79 | -1.7% | 0.398 | 0.157 | +37.4% (24) | +37.4% (24) | no | PAPER ONLY | edge is within what searching 15 variants finds by luck (grid p 0.398); walk-forward +37.4% on 24, itself significant (p 0.020) |
| 11 | [awfuldog](awfuldog.md) | NFL | 62 | +6.7% | 0.459 | 0.245 | +12.7% (70) | +12.0% (29) | yes | PAPER ONLY | edge is within what searching 6 variants finds by luck (grid p 0.459); walk-forward +12.7% on 70 |
| 12 | [mnf_1h](mnf_1h.md) | NFL | 29 | -12.3% | 0.534 | 0.508 | +24.1% (25) | +24.1% (25) | no | PAPER ONLY | edge is within what searching 4 variants finds by luck (grid p 0.534); walk-forward +24.1% on 25 |
| 13 | [nba_badteams_under](nba_badteams_under.md) | NBA | 308 | +2.2% | 0.669 | 0.121 | +3.7% (193) | +3.6% (72) | no | PAPER ONLY | edge is within what searching 36 variants finds by luck (grid p 0.669); walk-forward +3.7% on 193 |
| 14 | [wind1014_1h](wind1014_1h.md) | NFL | 82 | -8.9% | 0.842 | 0.381 | +8.4% (25) | +8.4% (25) | no | PAPER ONLY | edge is within what searching 29 variants finds by luck (grid p 0.842); walk-forward +8.4% on 25 |
| 15 | [nba_under_good_home_over](nba_under_good_home_over.md) | NBA | 246 | +5.4% | 0.435 | 0.040 | -11.6% (65) | -38.6% (16) | no | RETIRE | no edge beyond search luck (grid p 0.435) and walk-forward -11.6% on 65 |
| 16 | [cfb_wind14](cfb_wind14.md) | CFB | 186 | +0.1% | 0.705 | 0.306 | -4.2% (128) | +92.7% (4) | no | RETIRE | no edge beyond search luck (grid p 0.705) and walk-forward -4.2% on 128 |
| - | cbb_bigloss_vs_top5 | CBB spread | - | - | - | - | - | - | - | INSUFFICIENT DATA | needs AP top-5 rankings at game time; not in the data |
| - | xch_homedog_fade | exchange tape | - | - | - | - | - | - | - | INSUFFICIENT DATA | built on exchange order flow (2025-26 only); no multi-season history to permute or walk forward |
| - | cfb_q1_under_curve | CFB 1Q total | - | - | - | - | - | - | - | INSUFFICIENT DATA | derivative curve lines exist only from 2023; one in-sample season before the holdout |
| - | cfb_tt_under_curve | CFB team total | - | - | - | - | - | - | - | INSUFFICIENT DATA | derivative curve lines exist only from 2023; one in-sample season before the holdout |
| - | cbb_1h_total_curve | CBB 1H total | - | - | - | - | - | - | - | INSUFFICIENT DATA | no CBB derivative (1H) line history in the repo |
| - | nhl_p1_spread_curve | NHL 1P spread | - | - | - | - | - | - | - | INSUFFICIENT DATA | no NHL period line history in the repo |

N and ROI are in-sample (2020 to the season before the holdout), flat 1 unit at the price stated in each report. Walk-forward OOS covers every season from the third on, holdout included, each bet with the variant fitted on earlier seasons only.

## Multiple testing

16 systems and 360 grid variants were tested. Gate 2 already corrects for each system's own grid (best variant per shuffle). Across systems, about 0.8 of 16 would pass gate 2 at p < 0.05 by luck alone; 0 did. With a Bonferroni bar across systems (0.05 / 16 = 0.0031), 0 pass.

## Limits

- Wind: the gates test Open-Meteo archive wind, not MySportsWeather (no history before 10/29/2026) or Bet Labs' own wind. A bet placed on a forecast sees a different number.
- NFL first-half lines exist from 2023-05 only, so the 1H rules have 3 seasons (2023 to 2025): one walk-forward season before the holdout.
- Filters that use the closing number (spread, total, moneyline, open-to-close move) are graded at that same close; a bet placed earlier sees a different number, so the live edge can be smaller.
- 2026 football and the 2026-27 NBA/NHL seasons are partial and are left out of every gate.

