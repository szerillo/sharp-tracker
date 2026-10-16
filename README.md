# Sharp tracker

Multi-sport sharp-price tracker: a price-history log, venue tests, a fitted ruler and a graded bet ledger. MLB is the first feed; the schema is sport-agnostic.

In-house build of SHARP_TRACKER_BUILD_SPEC_2026-10-14 §1–§12: a price-history view plus a grading engine, no projection anywhere in the ruler.
Order of work is strict: **log → test → weight → bet**. Nothing here produces a bet on its own.

## What runs

| step | file | writes |
|---|---|---|
| fold the append-only logs into `events` + `ticks` | `sharp/build_db.py` | `data/state/sharp.sqlite` (derived, gitignored), `schedule_cache.json`, `kalshi_markets.json` |
| results + box scores from statsapi | `sharp/results.py` | `data/state/results.jsonl` |
| closing-line table (open, close, T-24h/6h/1h, outcome) | `sharp/grade.py` | table `closes`, `data/state/closes.jsonl` (gitignored) |
| bet ledger | `sharp/fills.py` | `data/state/fills.jsonl` |
| Tests A–D, opener (gated) | `sharp/tests.py` | nothing; read by export |
| ruler weights (gated ridge fit) | `sharp/weights_fit.py` | `data/state/weights_fitted.json` |
| dashboard data | `sharp/export.py` | `data/state/dashboard.json` → `index.html` |

Workflows: `prices.yml` logs every venue every 20 min; `tracker.yml` runs the grading chain every 20 min (offset :10); `fill.yml` logs a fill from the Actions UI.
Dashboard: `index.html` on GitHub Pages (Settings → Pages → deploy from `main`, root) reads `data/state/dashboard.json`.

Local: `python3 sharp/build_db.py && python3 sharp/results.py && python3 sharp/grade.py && python3 -m sharp.fills grade && python3 sharp/weights_fit.py && python3 sharp/export.py`,
then open `index.html` from a local server (`python3 -m http.server`) or the Pages site. `SHARP_OFFLINE=1` skips every network call.

## Loggers (`loggers/mlb/`, carried over from mlb-tracker and repathed)

| log | venue(s) | class |
|---|---|---|
| `data/mlb/game_lines/pinnacle_log.jsonl` | Pinnacle (with max-risk limits) | game |
| `data/mlb/game_lines/an_log.jsonl` | DK, FD, Caesars, BetRivers, Fanatics, theScore; AN_Consensus (public %), AN_Open (reference only) | game |
| `data/mlb/game_lines/kalshi_log.jsonl` | Kalshi (bid/ask/last/vol per rung; F5 tie rung kept as `draw`) | game |
| `data/mlb/kalshi_oblog/*.jsonl` | Kalshi prop order books | prop |
| `data/mlb/novig_log/*.jsonl` | Novig (best resting bid per outcome; ask = 1 − other side's bid) | game + prop |
| `data/mlb/an_props_log/*.jsonl` | DK, FD, Caesars, BetRivers, Fanatics, theScore, BetMGM | prop |
| `data/mlb/pinnacle_props/pinnacle_props.jsonl` | Pinnacle props (with limits); matched to a game via the exchanges' player→game map | prop |

Canonical event id = statsapi gamePk, matched by participants + ET date (+ nearest start for doubleheaders), never by name string.
Every tick stores both sides as rows. Exchanges store bid/ask/mid; `implied` is the ask (cost to take). Flags: `open` (first row per venue×market×line×side),
`wide` (ask − bid > 0.04, excluded from the ruler), `oneside` (no complement quote), `pulled` (venue stopped quoting 60+ min before the others), `threeway`.

## Novig public exchange data (`loggers/novig_catalog.py`, `loggers/novig_tape.py`)

Novig publishes every executed trade and every market's daily OHLC as static CSVs at `data.novig.com/reporting/trade-data/` (since 2026-08-03,
no auth, ~180k straight taker fills and ~$35M notional a day across every league). The files carry only market/outcome ids, and settled markets
leave the public catalog, so `novig_catalog.py` snapshots the whole open catalog every 20 minutes into `data/novig/catalog/` (ids → event,
description, strike, outcome names) and `novig_tape.py` turns each day's tape into `data/novig/daily/<date>.jsonl.gz`: per market-outcome-day
fills, volume, vwap, OHLC, big-print (≥$1k) vwap, and the T-24h/6h/1h window vwaps where the market is decoded. Raw tape and market census
files are re-downloadable and not committed. Markets that settled before the catalog log began decode only through `/v3/history/markets`,
which needs a (free) Novig API key.

## The ruler

An exchange quote is a price only when it is two-sided, inside 4¢, has at least $500 resting within 3¢ of best **on each side**, and is not alone:
a quote more than 5 pts from the book median needs two other venues within 3 pts or it is flagged `outlier` and left out (Sean 10/15: one big make
order on Novig is not a fair — Chuba Hubbard over 67.5 at -2400 with $2.4k vs $61 on the other side; the market was -112 to -125). Excluded quotes
stay in the log and show on the ladder with the reason (`wide 41c`, `thin $61`, `outlier +31pts`); their weight goes to the venues that passed.
`tests/test_ruler_rules.py` pins those cases.

`fair.py`: per venue, devig (power by default; proportional and Shin implemented, chosen by calibration at 2,000 events) or the exchange mid when the
spread is ≤ 4¢; weighted average with the prior vector from `constants.py` (the thread's hand-set weights, renormalised, every venue capped at 60%).
Books older than 45 min and exchange quotes older than 45 min do not enter. A fair is shown on the board only with ≥3 ruler venues.
Every fair carries `status` = `prior` until `weights_fit.py` passes its gate (1,500 settled games for game lines, 20,000 settled prop rows) and writes a fitted vector.

Best bettable price excludes BetMGM and adds Kalshi's taker fee to the ask; Novig charges no pregame fee.

## Tests (pre-registered, gated)

A accuracy (Brier + deciles) · B speed (gap closure at 24h/6h/1h, with the reaction-speed control; the feed-lag control waits on measured lags) ·
C head-to-head edge conversion on props (3,000 pairs per venue) · D the over tax (and C split by side) · opener test. Steam test: not yet (needs a tick-level pass).
Below the gate the export carries the sample count only. `python3 sharp/tests.py --preview` prints below-gate numbers locally, labelled PREVIEW.

## Fills

`python3 -m sharp.fills add --game MIL@LAD --market ml --side home --venue FD --price -174 --stake 1 --tag "rule:…"`. The fair at fill is computed from the
DB at that moment; a row written after first pitch is tagged `late` and excluded from CLV. "Discussed" and "would have" are not fills.

## Cadence

Every logger runs alone in `prices.yml` on its own concurrency group with no sleeps, so a snapshot should land every 20 minutes. The Log health tab
shows snapshots per game per venue; ~40 per game-day is the target, and the history carried over from mlb-tracker (Oct 6–14) averaged 3–6.

## Constants

`sharp/constants.py`. Every entry has `status` (rule / prior / fitted) and a `source`. An entry without one is a bug. The dashboard's Constants tab lists them.

## Not yet done (spec items deferred)

Feed-lag measurement per venue (spec §2, weekly spot check); devig method calibration harness (§5, needs 2,000 settled events); steam-chasing test (§6);
limit-growth test (§6; the raw material is in `pinnacle_first.json` and the ticks); Circa, ProphetX, Polymarket feeds; other sports (the schema is sport-agnostic:
`sport`/`league` columns, `events` keyed by any id); folding Bartolo's older `clv_archive` into `fills` (those rows are model calls, not fills, so they stay out by rule).
