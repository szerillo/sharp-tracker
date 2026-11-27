# Board changes and decisions, 11/25 to 11/27/2026

A dated record of what changed on the board and in the tools in these three days, with the commit for each. Tier and rule changes are marked with who approved them. Everything else is a tool, data, test or display change, with no tier or rule effect.

## Sean's decisions (approved, applied)

| Date | Decision | Commit | Record |
|---|---|---|---|
| 11/25 | Re-score all 32 saved Tested:/Tracked: Bet Labs screens on TIER_RULES v2, as written. Eight rules move to real money at 0.25u for games from 11/26 00:30Z: bounce15_1h B, nhl_pl_fav_gap A, nhl_pl_fav_strong_opp A, nhl_pl_dog_bigml A, nba_1h_under_hot_over B, cfb_road_dog_low_total B, cbb_under_good_over_drop B, cfb_road_streak_dog B. | 6d92515c34 | docs/validation/PUSHBACK.md section 5; TIER_RULES.md Changes |
| 11/25 | vrest8_1h and mnf_1h count SoFi as open, matching Bet Labs' Dome Closed flag. | 6d92515c34 | TIER_RULES.md Changes |
| 11/26 | nba_under_good_home_over_small and wind1014_cold stay tier A. | (no code change) | docs/validation/betlabs_mismatch_2026-11-26.md |
| 11/27 | cbb_under_good_over_drop bets only games on a fresh Bet Labs pull. Our own reading of the filters shows as a `cbb_labs_gap` flag and is never bet. Tier B, 0.25u. | 4786af8313 | TIER_RULES.md Changes; docs/drafts/cbb_labs_gate_2026-11-27.md |

## Rule-scope fixes to match the saved screens (no tier change)

- **11/27, regular season only:** every saved screen filters to the regular season, so the live rules built from them skip preseason and playoff games (`systems.regular_season`). Commit ddc8c8ac0a.
- **11/27, neutral sites:** a Bet Labs listing matches with home and visitor swapped. Fresno State v South Alabama was missed on 11/27. This applies to the list-driven totals screens (wind and CBB). Commit 65eda4cdaa. The CFB road-streak rule (`labs_list`, a spread veto) does not swap yet; changing that touches a real-money rule's gate, so it is Sean's call.

## Data and replay fixes

| Fix | Effect | Commit |
|---|---|---|
| tennis_watch.json crashed on void rows from 11/24 10:16Z. | File rebuilt; stale-file alert added for tennis_watch and props_live. | 93d0ff89e1 |
| PUSHBACK section 5 replay records were doubled (season rows plus the all-seasons row). | Records corrected; reader `rule_replay.summary_record()` with a test. | 99d4ab58ca, ddc8c8ac0a |
| 2020 NHL/NBA bubble games (no season type) were counted in 2020-21 records. | Our 2020-21 NHL opponent win % now matches Bet Labs on all 392 matched games, up from 345. | ddc8c8ac0a, de8cc37565 |
| Utah's ESPN abbreviation flips between seasons (UTAH / UTA). | 191 Utah games get results on the next results rebuild. | ddc8c8ac0a |
| `rule_replay.grade()` priced the wrong side of the puck line at near pick'ems, and gave off-number lines a made-up 1.91. | Only the posted line is priced. nhl_pl_fav_strong_opp replay goes from -0.6% to +5.3% on 349; nhl_pl_fav_gap from +8.8% to +18.9% on 196. | a116c1f2dc |
| Made-up fallback prices in cfb_replay (1.909) and nba_under_reconcile (1.95). | Removed. They were never used on the current database, and a lint test now blocks them. | 0e2bf152c3 |

## Tools, tests, display

- **11/27, CI:** `.github/workflows/tests.yml` runs `tests/` on every code push, with a phone alert on failure. Commit f78456f646.
- **11/27, no-fill reason:** `system_fires.json` games now carry `no_fill[tag]`, the reason a triggered rule didn't fill. Example: Liberty @ St. Thomas, where only Pinnacle quoted the total. Commit 43673f2702.
- **11/27, list matching audit:** the board audit warns when a listing on a list-bet screen (wind, CBB under) isn't on the board. The Bet Labs tab matches neutral-site swaps and drops definition notes that no longer apply. Commit 0735543f2e.
- **11/27, record column:** shows the 11/27 replay for the six rules it covers (text only). Commits 6dba2acc73 and a116c1f2dc.

## Open for Sean

- CFB road-streak rule: match Bet Labs listings with home and visitor swapped at neutral sites (veto only)?
- 12/8: re-read the Kalshi cancel rule. About 15 new rows are expected by then, too few to decide on.
- stale_book kill test: 35 of 100 checkable rows graded (10-25, -38%).
