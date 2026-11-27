# Draft: cbb_under_good_over_drop bets only games on Bet Labs' list (NOT applied)

Kirk, 11/27 (td_replay_fixes), from docs/validation/betlabs_mismatch_2026-11-26.md: Bet Labs' own picks for screen 1792184 return +4.0% at Pinnacle's close (502 games, 2020-26). The tool computes the filters itself, and its version picks mostly other games: 474 games at -6.0%, with only 172 of them on Bet Labs' list.

The patch is `docs/drafts/cbb_labs_gate_2026-11-27.patch`, against sharp/systems.py at the commit that adds it. Apply it with `git apply docs/drafts/cbb_labs_gate_2026-11-27.patch`.

What it does:
- **Fresh Bet Labs pull lists the game** (same 16-hour freshness as the wind rules; pulls run at 7:00 AM and 5:30 PM daily plus weekend afternoons): the rule fires at the current total, under, even if our own reading of the filters disagrees. The row shows Bet Labs' numbers and ours.
- **Fresh pull does not list it:** no bet. If our own filters pass, the game shows a `cbb_labs_gap` flag on the board.
- **No fresh pull:** no bet. Our reading is shown as the same flag.
- Weekday and regular-season checks stay. Sizing, tier and the hold rules are unchanged.

How this differs from cfb_road_streak_dog: the CFB rule fires on our own trigger and is only vetoed by a fresh list that doesn't include the game, so with no fresh pull it still bets. This draft is stricter, because here our own trigger is the losing version. A softer CFB-style form would be: keep our trigger, add `if labs_list(1792184, ...) is False: continue`. That keeps the 172 shared games and drops the 302 non-list games, but misses the roughly 350 Bet Labs games our filters don't reach.

`tests/test_replay_fixes.py` checks that the patch applies to the current systems.py and compiles, and that it is not applied.
