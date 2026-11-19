# Bet Labs records (Sean's saved backtests)

Started 11/19/2026 so audits use Sean's actual Bet Labs backtests instead of rebuilding them. Read only on Bet Labs: nothing in the account is
changed.

## Files

- `records.json`: the latest pull. Per saved Tested:/Tracked: screen (the ones in `data/state/betlabs_inventory.json`):
  - `name`, `sport`, `grade`, `filters` (each filter as Bet Labs words it), `bet_type`, `line_type`, `fade`
  - `all_time`: W, L, P, units, ROI, z, N, first and last game date, as Bet Labs shows on the screen
  - `since_saved`: the date the screen was created and Bet Labs' record since then (`from_picks` is the same count rebuilt from the
    past-picks list, as a cross-check)
  - `this_season`: Bet Labs' current-season record
  - `seasons`: per-season splits computed from Bet Labs' own past-picks list for the screen, `[W, L, P, units, ROI %]`. Football seasons
    by year (August start), NBA / NHL / CBB as `YYYY-YY` (August start), MLB by calendar year.
  - `rules`: the tool rule(s) the screen backs (`sharp/systems.py` LABS)
- `records_history.jsonl`: one line per pull, appended, never overwritten. Each line has the summary numbers per screen; the full
  per-season splits and filters are repeated only when they changed since the previous pull, so a Bet Labs data revision shows up.

Units are Bet Labs' $100 units divided by 100, and ROI = units / (W + L + P), as Bet Labs computes it. Prices are Bet Labs' own lines,
not Pinnacle's close. Per-game picks are not stored: about 39,000 rows across the screens, too large to move out of the browser on every
pull. The past-picks list stays on each screen in Bet Labs.

## How it is refreshed

With the Bet Labs pull (Sean's Chrome, signed in): open any Bet Labs screen page, run `sharp/betlabs_records.js` in the page with the
inventory's screen ids, read `window._BLREC` out (render it into the page and read the page text; it is about 40 KB), save it as
`betlabs_in.json` and run `python3 sharp/betlabs_records.py betlabs_in.json`. Commit `data/betlabs/records.json` and
`data/betlabs/records_history.jsonl`.

## Who uses it

`docs/validation/TIER_RULES.md` (version 2) takes the Bet Labs record from here as the primary evidence, and
`sharp/validate_pushback.py` re-scores the tiers from it.
