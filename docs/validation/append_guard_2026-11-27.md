# Append guard: no job drops rows on a rebase (11/27/2026)

Approved by Sean 11/27 (td_append_guard). Tool and workflow change only; no rule, tier or record change.

## The bug

Every data job commits, then loops `git pull --rebase -X theirs` until its push lands. When another push touched the same row log in
between, git resolved the overlap by keeping one side: one hunk for a `.jsonl`, the whole file for a `.jsonl.gz` (binary to git).
The rows the other push had just written were gone, with no error.

Why it happened so often in prices fast: a run queued behind the previous one checks out the commit it was triggered on, not main as it
stands when it starts. Its CBB and trades jobs then appended to stale copies of the logs, and the rebase let those stale copies win.

On 11/27 (05:00Z to 05:00Z), from `sharp/research/row_audit.py` on main's history:

| File | Pushes | Pushes that dropped rows | Rows dropped | Added rows still missing at the end |
|---|---|---|---|---|
| data/cbb/ticks5/2026-11-27.jsonl.gz | 161 | 8 | 14,634 | (tape) |
| data/state/sharp_paper.jsonl | 80 | 14 | 26 | 4 |
| data/kalshi/flow_paper.jsonl | 27 | 13 | 21 | 6 |
| data/state/sys_sharp_tags.jsonl | 11 | 6 | 9 | 6 |
| data/state/stale_paper.jsonl | 33 | 4 | 4 | 4 |
| data/state/fills.jsonl | 30 | 0 | 0 | 0 |

Example: the 14:23Z CBB rows (2,061) were pushed at 14:23:12Z and dropped by the 14:30:14Z push.

## The fix

- `sharp/append_merge.py`: a git merge driver that merges row logs row by row (three-way). A row either side added is always kept.
  Ledgers that jobs rewrite in place (grading) are matched on their own id (`KEYS`), so a graded row replaces its ungraded copy. A
  `.jsonl.gz` is decompressed, merged and recompressed. If an added row would still be missing, the driver refuses and the push loop
  retries.
- `.gitattributes`: `data/**/*.jsonl` and `data/**/*.jsonl.gz` use it (`merge=rowlog`).
- All 25 workflows that pull and push (tracker.yml included) set `git config merge.rowlog.driver ...` in their commit step. `-X theirs`
  stays for the JSON state files, which are snapshots, not logs.
- prices_fast checks out `main` (not the trigger commit), so queued runs start from current data.
- Replayed on the real 11/27 14:30Z collision: 90,144 rows out, every row from both pushes kept, including the 2,061 at 14:23Z, in 1.1s.

## Tests

`tests/test_append_merge.py`: two writers in real git clones push through the workflows' own loop. Without the driver rows are lost
(control, reproduces the bug); with it every row from both writers survives, for a `.jsonl.gz` tape and two paper ledgers. Also: rule
tests, and a check that every pushing workflow configures the driver.

## Not done (Sean's call)

Rows already dropped are still in git history. Restoring the ledger rows (sharp_paper 4, flow_paper 6, sys_sharp_tags 6,
stale_paper 4) would change paper records, including the stale_book kill test count, so it waits for Sean.
