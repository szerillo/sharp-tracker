# signals.yml: where the time goes (11/28/2026)

Research only, no change. Last 8 successful runs (11/28 early morning ET), from the GitHub run and step timestamps.

- From dispatch to finish: queued 0.8 to 9.3 minutes (median about 5) behind the previous run, then 13.3 to 20.7 minutes running
  (median about 15). pulse.yml dispatches every 10 minutes, so a run is always waiting and the board rebuilds about every 16 minutes.
- Steps that take 0.2 minutes or more (median, max):

| Step | Median | Max |
|---|---|---|
| exchange money split, tape check, tennis, MMA steam and the late pass (parallel) | 3.7 | 4.9 |
| checkout (sparse, blob-less) | 3.5 | 5.8 |
| offers to rest (Kalshi and Novig paper) | 3.1 | 4.1 |
| bet tracker | 2.4 | 3.0 |
| parlay prices against their legs (paper) | 1.4 | 2.5 |
| stale-book paper lean | 0.5 | 0.6 |
| commit | 0.4 | 0.8 |

The props step itself takes under 0.2 minutes and runs about 12 minutes into each run, after offers and parlays.

## Options (none applied; the first two change no rule and no output, only when steps run)

1. Move the three paper-only research steps that do not feed the board's bets (offers 3.1, parlays 1.4, women's college basketball) to
   their own workflow. The board run would drop to about 10 minutes and rebuild about every 10 minutes, as pulse intends; props and the
   system bets would be checked more often. Their files are row logs, which the 11/27 merge driver already protects from the second
   writer.
2. Run props and the bet tracker before offers and parlays: each props check would land about 5 minutes sooner after dispatch (the
   interval between checks stays the same unless option 1 is done too).
3. Checkout (3.5 minutes, measured 11/28): the fetch takes under a second (`--filter=blob:none --depth=1`); the time is
   `git checkout` downloading the contents of every file the sparse pattern keeps (everything but data/oddsapi): 1,746 files,
   about 3.5 GB per run (GitHub tree sizes, 11/28). The largest: cfb ticks 302 MB, cbb ticks 217 MB, nfl ticks 208 MB, tennis
   poly_hist 197 MB, cfb ticks_px 177 MB, tennis kalshi_hist 154 MB, cbb ticks_px 151 MB, cfb weather 150 MB, cbb ticks5 146 MB, novig
   catalog 139 MB. Most of it is history the board run never reads, but a static read of the 24 scripts the job runs is not reliable
   enough to cut by (paths are built at run time, and build_db and the near and late passes read tapes by date).
   Proposed, not applied: (a) one instrumented signals run with a Python audit hook (`sys.addaudithook`, through `sitecustomize` on
   PYTHONPATH) that writes every data file the job opens to a list, read only, nothing else changed; (b) then check out code and state
   only, and add the files on that list (with today's and yesterday's day files by date) through `git sparse-checkout add`, so only
   those are downloaded. Expected saving: most of the 3.5 minutes; it changes no rule and no output, but it changes which files the
   board's main job can see, so it should be tested on a dispatched copy of the job before it replaces the checkout.
