# Past system conflicts: does the stronger tier win? (11/18)

Built by sharp/conflict_backtest.py from data/state/fills.jsonl. A conflict = two rules' paper fills on opposite sides of one game (moneyline / spread on the other team, any period; or over vs under on the same total). Tiers as on the board today. Flat 1 unit per fill at the filled price. Read-only: the rule stays "both sides untracked" (Sean, 11/18) whatever this shows.

Games with a conflict in the ledger: 28 (25 fully graded; 5 of them with equal tiers on both sides, so no stronger side).

| Policy on the graded conflicts | Fills | W-L | Units (flat 1u) |
|---|---|---|---|
| Stronger tier only (the 11/2 rule) | 20 | 14-6 | +4.61 |
| Weaker tier only | 23 | 9-14 | -9.88 |
| Both sides (no rule) | 53 | 28-25 | -7.61 |
| Cancel both (the 11/18 rule) | 0 | 0-0 | +0.00 |

Sample: 25 graded games. That is far too few to say a stronger tier should override; at roughly -110, telling +5% from zero takes thousands of bets. The 11/18 rule stays as it is, and this file can be re-run as conflicts accumulate.

| Date | Game | Fills (rule, tier, market, side, line, price, result) |
|---|---|---|
| 2026-11-01 | 401892627 | nhl_early_home_fav_qual (B) ml home -122 L; xch_homedog_fade (C) spread away 1.5 -208 W; nhl_pl_fav_strong_opp (P) spread home -1.5 +190 L |
| 2026-11-01 | 401909900 | xch_homedog_fade (C) ml away -326 W; nba_momentum (P) spread home 9.5 -122 L |
| 2026-11-03 | 401892631 | nhl_pl_dog_bigml (P) spread home 1.5 -112 L; xch_homedog_fade (C) ml away -203 W |
| 2026-11-06 | 401909936 | nba_under_good_home_over (C) total under 222.5 -106 W; nba_momentum (P) total over 222.5 -113 L |
| 2026-11-07 | 401862819 | cfb_homefav_7510_under (C) total under 47.5 -110 W; cfb_day_over (P) total over 47.5 -110 L |
| 2026-11-07 | 401892662 | nhl_early_home_fav_qual (B) ml home -122 W; xch_homedog_fade (C) spread away 1.5 -212 W |
| 2026-11-08 | 401873040 | bounce15_1h (P) 1h_spread home 3.5 -110 L; xch_homedog_fade (C) ml away -212 W |
| 2026-11-08 | 401873046 | awfuldog (C) spread home 4.5 -100 L; xch_homedog_fade (C) ml away -208 W |
| 2026-11-08 | 401873042 | awfuldog (C) spread home 7.0 -110 L; xch_homedog_fade (C) ml away -285 W |
| 2026-11-08 | 401892674 | nhl_early_home_fav_qual (B) ml home -133 W; xch_homedog_fade (C) spread away 1.5 -190 L |
| 2026-11-12 | 401892693 | nhl_early_home_fav_qual (B) ml home -133 W; xch_homedog_fade (C) spread away 1.5 -212 L |
| 2026-11-13 | 401892696 | nhl_early_home_fav_qual (B) ml home -117 L; xch_homedog_fade (C) spread away 1.5 -217 W |
| 2026-11-13 | 401892698 | nhl_early_home_fav_qual (B) ml home -105 W; xch_homedog_fade (C) spread away 1.5 -233 W |
| 2026-11-14 | 401858518 | cfb_day_over (P) total over 49.5 -138 L; cfb_homefav_7510_under (C) total under 49.5 -110 W |
| 2026-11-14 | 401858295 | cfb_day_over (P) total over 47.5 -110 L; cfb_wind14 (C) total under 47.5 -104 W |
| 2026-11-14 | 401862828 | cfb_day_over (P) total over 46.5 -110 L; cfb_wind14 (C) total under 48.5 -100 W |
| 2026-11-15 | 401873054 | nfl_home_dog_7510 (C) spread home 7.5 -120 L; xch_homedog_fade (C) ml away -388 W |
| 2026-11-15 | 401892717 | nhl_bounce_home_ml (C) ml home -150 W; xch_homedog_fade (C) spread away 1.5 -199 L |
| 2026-11-15 | 401892711 | nhl_early_home_fav_qual (B) ml home -113 L; xch_homedog_fade (C) spread away 1.5 -203 W |
| 2026-11-15 | 401892716 | nhl_early_home_fav_qual (B) ml home -105 L; xch_homedog_fade (C) spread away 1.5 -239 W |
| 2026-11-16 | 401892722 | nhl_early_home_fav_qual (B) ml home -144 W; xch_homedog_fade (C) spread away 1.5 -212 W |
| 2026-11-17 | 401909997 | nba_roadtrip_over (P) total over 227.5 -110 W; nba_under_good_home_over_small (P) total under 226.5 -106 L |
| 2026-11-18 | 401892730 | nhl_pl_fav_strong_opp (P) spread home -1.5 +178 L; xch_homedog_fade (C) spread away 1.5 -223 W; nhl_early_home_fav_qual (B) ml home -133 L |
| 2026-11-18 | 401892737 | nhl_early_home_fav_qual (B) ml home -138 L; xch_homedog_fade (C) spread away 1.5 -223 W; nhl_bounce_home_ml (C) ml home -138 L |
| 2026-11-18 | 401892734 | nhl_early_home_fav_qual (B) ml home -156 W; xch_homedog_fade (C) spread away 1.5 -212 L |
| 2026-11-19 | 401892741 | nhl_skid_fade_road (C) spread away -1.5 +194 open; nhl_early_home_fav_qual (B) ml home -104 open |
| 2026-11-20 | 401892752 | nhl_skid_fade_road (C) spread away 1.5 -178 open; nhl_bounce_home_ml (C) ml home -186 open |
| 2026-11-20 | 401892753 | nhl_early_home_fav_qual (B) ml home -138 open; nhl_skid_fade_road (C) spread away 1.5 -285 open |
