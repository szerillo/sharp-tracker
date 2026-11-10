# Handoff: Action Winners Circle (sharp tracker), as of 11/10/2026 evening

One place to pick this project up from. Detail lives in the linked files; this page says what exists, what is live, and what only
existed in chat. Companion pages: docs/METHODOLOGY.md (standing process), docs/RESEARCH_LOG.md (every test and its verdict),
docs/maker_playbook.md (resting offers and parlays).

## 1. What it is

- Repo: github.com/szerillo/sharp-tracker. Site: https://szerillo.github.io/sharp-tracker (GitHub Pages, single index.html).
- It logs prices across venues, prices each market against Pinnacle's no-vig number, fires pre-registered betting rules, flags sharp
  Polymarket accounts, lists paper offers to rest on exchanges, and grades everything in a bet log.
- Nothing in the repo places a bet or an order. Sean places bets himself. BetMGM is logged but never bettable.

## 2. Architecture

- loggers/: price and tape pullers. lines.py (20-minute prices, all venues), fast.py (5-minute move tape, exchange fills),
  prophetx.py (ProphetX quotes), oddsapi_*.py (Odds API history, props, derivatives), tennis and boxing helpers.
- sharp/: analysis and the live engines. systems.py (rules and tiers, EVIDENCE table), bet_log.py (the ledger, sizing, HOLD rule,
  rest fields), sharp_live.py (Polymarket sharp flags), stale_live.py (stale books, sb4), props_live.py (prop price gaps),
  curve_live.py (derivative curve leans), offers_live.py / offers_grade.py (paper offers), parlay_live.py / parlay_grade.py (paper
  parlay log), plus one script per research test.
- data/: per-sport ticks and trades, data/state (board inputs, paper logs, bet_log.json), data/research (test outputs),
  data/oddsapi (history; odds.sqlite is rebuilt, not committed).
- docs/: dated research notes, METHODOLOGY.md, RESEARCH_LOG.md, this file.

## 3. Data sources

| Source | What | Access |
|---|---|---|
| Pinnacle (guest API) | The fair-price anchor, with limits | public |
| Kalshi | Quotes, full trade tape, settled markets, parlays | public API; reachable from the analysis container |
| Novig | Quotes, public trade file (data.novig.com) | public file is reachable only from GitHub runners; signed API needs NOVIG_KEY_ID / NOVIG_PRIVATE_KEY |
| Polymarket | Fills by account (the sharp list) | public |
| ProphetX | Quotes via partner API | PROPHETX_KEY / PROPHETX_SECRET secrets; no trade feed found |
| DK, FD, Caesars, BetRivers, Fanatics, theScore | 20-minute quotes | via Action Network feed |
| The Odds API | History 2020-26 (18 sports), derivatives from 2023-05, props 2023-26 | ODDS_API_KEY; about 2,986,777 credits left, floor was 3M, Sean later said credits may be used |
| ESPN | Results, box scores, period scores | public |
| Bet Labs (Sports Insights) | System audits, 2003 on | Sean's account, through his Chrome |
| Tennis Abstract, Open-Meteo, MySportsWeather, NASA POWER | Tennis results, weather | public |

Secrets are set by Sean in GitHub only. Never paste keys into files, commits or chat. A ProphetX key was pasted in chat on 11/10;
it was not used or stored and should be regenerated.

## 4. Scheduled jobs (GitHub Actions, 29 workflows)

GitHub's own cron is unreliable, so pulse.yml (cron 7,37 each hour) is the scheduler: it dispatches prices.yml, signals.yml, moves.yml
and prophetx.yml on their slots, and tracker.yml hourly at :40 from 9 AM to 9 PM ET.

| Job | Cadence | Does |
|---|---|---|
| prices.yml | 20 min, 10 AM to 2 AM ET | price log, all venues |
| prices_fast.yml | 5 min | move tape, exchange fills |
| signals.yml | 10 min | sharp board, stale books, props leans, curve leans, paper offers and grade, paper parlay sample and grade |
| moves.yml | 10 min | market move tape |
| prophetx.yml | 20 min (via pulse) | ProphetX quotes |
| tracker.yml | hourly :40 (via pulse) | fold, grade, export bet_log. Do NOT dispatch off schedule: it logs system fills |
| oddsapi.yml | daily 4:23 AM ET | yesterday's closes |
| novig_tape.yml | daily | Novig public trade file |
| daily_review.yml | daily 10:41 AM ET | yesterday's signals by family |
| weekly.yml | Mondays | scoreboard, wind accuracy |
| tennis_*.yml, poly_rescore.yml | weekly / monthly | tennis data, monthly sharp-list rescore |
| pages.yml | on push | publish the site |

All workflows pull with `git pull ... -X theirs --no-tags origin main` (a plain pull fetched a backup branch with full history and
took 11.5 minutes a run).

## 5. Betting rules and tiers (live on the board with units)

Unit $500. Tier A and B 0.5u, tier C 0.25u, paper 0u. Sunday staking cap 0.25u. Full evidence per rule: EVIDENCE in sharp/systems.py
and docs/tier_recheck_2026-11-06.md, docs/weekly_recheck_2026-11-10.md.

| Rule | Tier | Evidence |
|---|---|---|
| wind1014 (NFL under, wind 10-14 mph) | A | Bet Labs 533-376 all-time; replay 161-103 (+18.1%), 6 of 7 seasons |
| CFB first-quarter unders off the curve | A | 2023-25 every season +10% or better (Sean's call 11/6); live start 4-7 |
| nhl_early_home_fav_qual | B | 269-155 ML, +7.1%, 6 of 7 seasons |
| cfb_hot_over_low_total | B | 117-71-3 (+19.5%), 6 of 6 seasons |
| Tennis settled hot favourite | B | 142-31, about +9%, positive every year |
| wind1014_1h, cfb_wind14, vrest8_1h, mnf_1h, awfuldog (-7 to -13), nfl_home_dog_7510, cfb_homefav_7510_under, nba_ats_hot_home, nba_badteams_under, nba_bigfav_over, nba_under_good_home_over, nhl_bounce_home_ml, nhl_skid_fade_road, cbb_bigloss_vs_top5 | C | two tests disagree, or one losing season; see EVIDENCE |
| NBA threes unders at a 2%+ price gap to Pinnacle | C | +7.8%, 4 of 4 seasons |
| CBB first-half totals off the curve; MMA steam | C | docs/deriv_curve_2026-11-06.md; docs/wncaab_mma_2026-11-09.md |
| Everything else in systems.py | paper | reason shown on the board |

Board rules (standing, from Sean):
- Bet systems, leans and sharp action only with NO signal against. Any signal against = HOLD (greyed, graded, no units). Paper rules
  never count as opposition. One bet shows in one place.
- Trusted experts shown for cross-check: CFB Stuckey, Collin Wilson, Duck; NFL Dabbundo, Anderson, Giffen.
- Promotion on forward record only; never promote or demote on CLV alone.
- Weekly checkpoint rules are fixed in docs/checkpoint_rules_2026-11-02.md.

## 6. Live vs paper vs dead (summary; the log has every line)

- Live with units: the tiered systems above, NBA threes unders, curve leans, tennis settled favourite.
- Paper, logging for 1-2 months at Sean's request (do not retire early): Polymarket sharp flags (0 units since 11/10 10:00 UTC),
  Kalshi offers, the original stale-book lean, stale_book_sb4 (book moneyline 4%+ over Pinnacle fair), nba_momentum, paper offers on
  Novig / Kalshi / ProphetX, rest-or-take, the parlay log, tennis first-set favourite, steam reversal.
- Dead (do not re-run without new data): boxing, ties, locks and ladders, opening moves, fading unfollowed moves, fading line moves,
  big-vs-small money, heavy one-way money, stale props after a total move, outlier books in general, team metrics on full-game
  closes, Kalshi weather markets, plain resting on Kalshi game lines (-1.4% after the fee), rescuing failed Bet Labs systems.

Key findings behind the current direction:
- Novig pays the resting side: makers +1.9% on $744M over three months; a bid 1c under Pinnacle fair keeps about 0.8c in the last hour.
- The sharp list is real at its own price (+0.74 CLV) and not followable at ours.
- Parlays: Kalshi parlay makers break even overall; two and three legs keep a few percent; 6+ legs and 50c+ lose. Paper only.
- Novig is the best taker price on 73% of sides (-0.5% EV vs Pinnacle fair).

## 7. Open items

1. First fill record on the paper offers (data/state/offers_record.json). At 6:38 PM ET 11/10: 8 offers graded, 5 filled inside an
   hour, too few to read. ProphetX matched volume, first day: CFB game lines $154,812, NBA $135,676, CBB $107,749, NHL $34,540, NBA
   props $30,105.
2. Parlay log: 85 logged, none settled yet (data/state/parlays_record.json). Revisit at 1,000+ settled.
3. Unmapped ProphetX prop types; no ProphetX trade feed.
4. WNCAAB cells (dogs +7 to +10, move-follow) are not logged on paper yet.
5. docs/METHODOLOGY.md is dated 11/6 and predates the maker work and the 11/10 tier changes; it needs a refresh.
6. METHODOLOGY section 7 items still open (NBA 1H under, weather fire window, tennis Challenger rule, CBB mining).

Sean's calls (not decided by Claude):
- ProphetX maker fee (assumed 2% of net profit per market) and regenerating the ProphetX key.
- Whether to run a real quoter on Novig (needs his keys and him running it).
- cfb_wind14: C (set 11/10) or B if Bet Labs' picks count.
- The 8 system fills logged at 6:49 AM on 11/10 by an off-schedule tracker run: kept; void or keep.
- Retiring nba_momentum (18-40) and the original stale_book lean (20-43), which the weekly recheck recommends and his 1-2 month
  tracking instruction overrides for now.

## 8. Things that only existed in the chat

- Working rules: no em dashes; data-strict (never estimate a number); percents not points; $500 unit; link every deliverable; the
  MLB trade ledger and the mlb-tracker repo are off limits (read-only); Sean's email is private.
- Deletes only when the data is certainly already committed to GitHub.
- The Claude session proxy cannot push tags or create refs; data.novig.com and Wikipedia are reachable only from GitHub runners.
- Push helper used in the session (not in the repo): fetch, reset to origin/main, copy the changed files, commit, push, retry.
- Novig tape: outcome and price are the resting order's. moves.jsonl.gz: p1 is the home/over price. Soccer moneylines need a
  three-way devig. Kalshi maker fee 0.0175 x p x (1-p) on game lines; Novig no pregame fee; ProphetX 2% of net profit per market.
- Kalshi parlay history only reaches back about 60 to 70 days; the series filter does not work with the parlay listing, so history
  is sampled by settle-time window.

## 9. Scheduled Claude tasks and chats for this project

| Task | When | Keep? |
|---|---|---|
| Weekly sharp tracker checkpoint | Mondays 12:31 PM ET | Keep (writes docs/checkpoint_<date>.md) |
| Sharp tracker weekly rule re-check | Tuesdays 4:43 AM ET | Keep (writes docs/weekly_recheck_<date>.md; recommends, changes nothing) |
| Read first paper-offer fill record | one time, 11/11 9:00 AM ET, in the main sharp-tracker chat | Closes itself after it runs |

Not this project (leave alone): the Ledger tasks (Front Office Ledger), Weekly X scorecard, Front Office Ledger weekly winter check,
and the disabled mlb-tracker tasks.

Chats: the main sharp-tracker session (the one that wrote this file) holds the full history; once this file and the research log are
in the repo it can be closed after the 11/11 check-in runs. Each weekly task run opens its own short chat ("Weekly sharp tracker
checkpoint", "Sharp tracker weekly rule re-check"); those can be closed once their doc is pushed. No other "Sharp tracker" side
chats could be listed from inside this session, so any others should be checked by title before closing: if their last message
links a pushed doc or commit, they are safe to close.
