# Tennis schedule reconciliation

Scheduled starts are estimates, not proof of live play. The existing feeds now supply fresh status observations: ESPN scoreboard status for covered matches; Pinnacle `isLive`/pending; Novig OPEN_PREGAME. Kalshi expiration/occurrence timestamps are not used as exact starts or evidence of pregame.

The registry keeps a stable fixture id across revised times and overnight delays. It records original_start, latest start, source-specific observations, schedule_checked_at and bounded start_revisions. Fresh explicit live/suspended evidence overrides a book still quoting pregame; confirmed final/cancelled is sticky. Unknown/stale timing blocks new quotes/actions rather than assuming pregame. Current schedule sources expire for pregame authorization after one hour.

The board retains recently flagged unstarted fixtures through missing price snapshots, labels expired estimates Awaiting start, and puts stale timing in a visible schedule-confirmation section with HOLD rather than BET. Today/Later filters still apply. Ungraded ledger starts reconcile from the registry; flag timestamps and historical grades remain unchanged.

No paid feed added. Flashscore/Sofascore integration is not required for these fixes and is not claimed validated.

Validation: `python3 -m unittest discover -s tests -p 'test_tennis_timing.py' -v`. Covers delayed matches, stale evidence, conflicting live/pregame sources, terminal status, revised times, overnight identity, ungraded ledger reconciliation, and blocking potentially live quote ingestion.
