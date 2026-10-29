# sharp-tracker roadmap — written 2026-10-29

Goal: a stand-alone site (GitHub Pages) that logs prices across venues, prices every market against an exchange-anchored
ruler, fires the pre-registered systems automatically, grades everything, and needs nothing typed by hand except real
fills. Sports in order: NFL (running), NBA, CFB; later soccer, tennis. MMA excluded (separate model).

## 0. Manual steps — the only ones (≈ 5 minutes, one time)
1. GitHub → New repository → owner `szerillo`, name `sharp-tracker`, **empty** (no README), public (Pages is free on public).
2. Claude app → GitHub connector → add `szerillo/sharp-tracker` to the repositories Claude can access.
3. Optional, unlocks the Novig history decode: paper.novig.com → Profile → Settings → Novig API → Create Key → paste the key
   id + .pem into the chat (stored as an Actions secret, never in the repo).
4. Optional, if paying for an odds screen: the API key for whichever aggregator (OddsAPI / OpticOdds / Unabated) → same.
Everything below is automated from there. The session is bound to the repos it is given, so step 1–2 cannot be done from here.

## 1. Ship what exists (day 0 after step 2)
- Push the 10 local commits; enable Pages (`gh api repos/szerillo/sharp-tracker/pages`), Actions schedules go live:
  `prices.yml` every 20 min (venues + Polymarket + Novig catalog + NFL weather), `tracker.yml` at :10 (tape, build, results,
  grade, weights, export). First dashboard build same day.
- Add secrets (Novig key, odds-API key) as they arrive; loggers detect presence and switch on.

## 2. Sport registry (week 1)
One config per sport (`sharp/sports/<sport>.py`) with: Pinnacle league id, Kalshi series prefixes, Novig league name,
Polymarket tag, Action Network scoreboard slug, ESPN results slug, season calendar, market set, weather yes/no, canonical
team codes. The MLB-specific loggers become `loggers/<venue>.py --sport X`.
| Sport | Pinnacle | Kalshi | Polymarket | AN / ESPN | Weather |
|---|---|---|---|---|---|
| NFL | 889 | KXNFL* | nfl | nfl | yes (outdoor) |
| NBA | 487 | KXNBA* | nba | nba | no |
| CFB | 880 | KXNCAAF* | cfb (futures only today) | ncaaf | yes |
Markets: ML, spread, total, team totals, 1H/1Q (where quoted), player props (NBA first — Kalshi/Novig/Pinnacle all quote them).
Results: ESPN scoreboard (final scores, half scores for 1H grading) — no key.

## 3. Systems engine (week 1–2) — zero manual input
`sharp/systems.py`: each rule is code with its trigger inputs and outlet market.
| tag | trigger | outlet | stake |
|---|---|---|---|
| wind1014 | outdoor, Open-Meteo T-24h sustained 10–14 mph | FG under | 1.0 |
| wind1014_1h | same | 1H under | 0.5 |
| vrest8_1h | visitor off ≥ 8 days | 1H under | 0.5 |
| mnf_1h | Monday night | 1H under | 0.5 |
| awfuldog | dog, season margin avg ≤ −13, game ≥ 2 | FG spread | 0.5 |
| bounce15_1h | dog, previous game ATS margin ≤ −15 | 1H spread | 0.5 |
| sharp10 | dog, money % − ticket % ≥ 10 (AN consensus) | confirmation flag only | — |
Stacking rule: one bet per game; if awfuldog and bounce15_1h both fire, take the 1H spread.
Every fire is written to the ledger as a **paper fill at the best bettable price at trigger time** (BetMGM excluded), graded
automatically with CLV vs the exchange ruler. Publication gate per tag: 100 graded fills and positive CLV. The dashboard
shows "fires today" with the price, the fair, and the edge — that is the thing to look at each morning.

## 4. Real fills with minimal typing (week 2)
- A Google Sheet `sharp-fills` (one row: date, sport, game, market, side, line, price, stake, venue, tag). The tracker reads
  it every run and grades it; nothing else to do. Alternative: `fill.yml` workflow_dispatch form (already exists).
- A phone-friendly page on the site that posts a row to the sheet is possible later; the sheet is the minimum.

## 5. Site (week 2–3)
Pages site, one page per sport plus an overview, same spirit as the Bartolo tracker but built around decisions:
Board (every market × side: best price, ruler fair, edge, venue ladder with liquidity flags) · Systems (fires today, each
tag's forward record vs its gate) · Ledger (paper + real, CLV, ROI by tag/venue/market) · Venue tests A–F (gated) ·
Log health (cadence per venue). Mobile layout. Data published as gzipped JSON per sport so pages load fast.

## 6. Weekly automation (week 3)
- Monday 9 am ET scheduled task: grades the week, writes the forward-test scoreboard and the "fires this week" preview, posts
  it to the chat (and optionally a Claude Doc). Nothing to request.
- Consensus cross-check: the one semi-manual item. A `cards` tab in the same sheet (capper, sport, pick, number); the
  tracker compares each pick to live best prices and the ruler and marks worth / not worth at current numbers.

## 7. Research queue (as data allows)
- CFB wind transfer test on Bet Labs (pinned this week).
- NBA: Bet Labs audit of the usual suspects (rest/B2B, travel, line move, public) with the same train/holdout method before
  any NBA system goes live.
- Novig 73-day tape decode once the key exists (Test F: big taker prints vs close).
- Test E/F steam-chasing on our own tape (the Bet Labs steam field is dead).
- Ridge weight fit when gates open (1500 games / 3000 pairs).

## 8. Storage
data/ is 384 MB locally. Rule going in: raw ticks partitioned by sport/day and gzipped on write; sqlite and derived files
gitignored; a monthly job moves raw months older than 90 days into a GitHub Release asset so the working tree stays small.
