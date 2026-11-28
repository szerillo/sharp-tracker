# First weekend Bet Labs pulls, Sat 11/28/2026

Checked 3:10 PM ET from the scheduled-task run records, main's commit history and the signals board audit. Read only on Bet Labs.

## The pulls

| Scheduled task | Fired (ET) | Finished | Commits on main | Pulled (UTC) | Screens | Picks | Today | Duplicates | Errors |
|---|---|---|---|---|---|---|---|---|---|
| Bet Labs pull 6:55 AM daily | 6:55 | succeeded | 8bf9400fd7 | 11:59:35 | 32 | 70 | 23 | 0 | none |
| Bet Labs pull 11:15 AM Sat/Sun (first run) | 11:15:26 | 11:20:14, succeeded | d4485bc9a1, then 32880d3c3c | 16:18:04, then 16:19:12 | 32 | 73 | 24 | 0 | none |
| Bet Labs pull 2:55 PM Sat/Sun (first run) | 2:55:52 | 3:01:55, succeeded | e5a1215097, then 4f8e6810ec | 19:59:34, then 19:59:47 | 32 | 72 | 25 | 0 | none |

Both weekend tasks fired on time and their rows landed. Each window has two pull commits about a minute apart. The second commit in each
pair changes only the pull time stamps (3 lines, same picks), so no row was dropped or duplicated. At 2:55 PM the second pull came from
the "Bet Labs pull 6:55 AM daily" task, which fired at 2:55:18 PM (its last run: fired 19:55:18Z, succeeded). A daily 6:55 AM task
firing at 2:55 PM is not on its schedule; it looks like a manual "run now" (the on-demand refresh), and a 2:53 AM pull (f8ec7e312a)
also landed outside any schedule. Kirk: was either fired by your jobs? Harmless either way: identical picks, a newer time stamp.

Each pull dispatches a board rebuild; at 2:59 PM both of those dispatches were cancelled (20:01:12Z and 20:01:34Z) because a newer run
was already queued (signals keeps one queued run and drops older ones). That newer run started after the pull, so the board picked the
pull up. Expected.

## Two board issues found while checking (fixed on a branch, not merged)

1. **False warning on the board audit:** "1 of today's list-bet listings not on the board: cfb_wind14 UCF @ Colorado (matched a tool
   game, but the rule did not trigger)". Not a missed bet: cfb_wind14 logged UCF @ Colorado on 11/27 at 23:02Z (under 48.5, Bet Labs
   wind 17 mph) and the board shows it untracked because the paper rule cfb_day_over sits on the other side (Sean's 11/18 conflict
   rule). The game kicked off at 2 PM ET; the check ran after kickoff, when triggers clear. Fix: `sharp/labs_match.py` no longer warns
   on a list game whose rule already logged a row (or was left untracked by a conflict) or whose game has started. With the fix, today's
   check is clean. Test added.
2. **signals.yml committed a stale copy of sharp_accounts.json:** the step "read the latest system-bet files from main" checks
   sharp_accounts.json and sharp_paper.jsonl out of main, which also stages them. signals never writes either file, but its
   start-of-run copy (about 15 minutes old by the commit) was committed and won the rebase: at 19:41Z signals pushed a copy built
   19:20Z over prices_fast's 19:36Z build (same at 19:22Z and 19:00Z). The board audit also read that old copy: "sharp signals
   (5-minute job) last built 38 min ago (allowed 20)" at 19:57Z, while main had a 19:51Z build. Fix: unstage both files before
   signals commits, and read main's newest sharp_accounts.json just before the bet tracker and audit. sharp_paper.jsonl rows were
   protected by the 11/27 row merge, but a stale copy could still overlay newer field values, so it is unstaged too.

Branch `fix/signals-stale-copies-1128` (a98b884a27): tests 43/43 pass on the branch (tests.yml run 46185013695). Not merged: it changes
the board's main job, so it waits for a go-ahead.

## Still armed

- "Append guard next-day row audit": enabled, one run at 11:20 PM ET today (2026-11-29T04:20Z), into this session.
- Next weekend pulls: Sun 11/29 11:15 AM and 2:55 PM ET (enabled).
