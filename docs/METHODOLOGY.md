# Action Winners Circle: methodology (as of 11/10/2026)

The standing process for the sharp tracker (szerillo/sharp-tracker). This is the document of record; dated docs under `docs/` hold the
tests behind each line. Updated when a rule or gate changes, with the date. Every test and its verdict is listed in
`docs/RESEARCH_LOG.md`; the project overview is `docs/HANDOFF.md`.

## Changes on 11/10
- Tiers (weekly recheck, docs/weekly_recheck_2026-11-10.md): cfb_wind14 A -> C, mnf_1h B -> C, cfb_road_dog_low_total C -> paper,
  nhl_pl_dog_bigml C -> paper. Section 1a.
- Polymarket sharp flags: paper (0 units) for flags logged from 2026-11-10 10:00 UTC. Section 4.
- New: resting offers and market making, paper only (section 8), and the parlay verdict (section 8c).
- New paper rules: stale_book_sb4 (section 6b), women's college basketball dogs +7 to +10 and following a 1+ point spread move
  (section 8d).
- Sean's instruction for everything on paper: give it 1-2 months of tracking before retiring it, including the rules a test said to
  stop spending time on.
- Correction: the 11/6 tier review below said nfl_home_dog_7510 was held at B; the 11/6 evening recheck (docs/tier_recheck_2026-11-06.md)
  moved it to C, and C is what the code uses.

## 1. Sizing and tiers
- Unit $500. Tier A and B systems 0.5u; tier C leans 0.25u (including NBA threes unders at a 2%+ price gap to Pinnacle, and CBB
  first-half totals off the full-game curve, 11/6); CFB first-quarter unders off the curve are tier A (0.5u; Sean's call 11/6 on 3
  seasons, 2023-25, every one +10% or better); tennis settled hot favourite is tier B (0.5u); MMA steam tier C. Paper (P) rows are
  logged and graded at 0 units. Sunday staking cap 0.25u.
- Tier A: a Bet Labs rule with a long positive history (2003-on), positive on both Bet Labs halves and 5+ of 6 recent seasons, and a
  stated reason (weather). Tier B: positive in Bet Labs' 2003-19 window AND in 2020-26 at Pinnacle's close, every season positive, plus
  a reason. Tier C: a rule whose two tests disagree, one losing season, or an edge only at its exact thresholds. P: everything else, with
  the reason shown on the board (`paper_why`).
- Sharp signals: paper since 11/10 (section 4). The grades below still label each flag: Grade A (a sport-proven account, or sharps plus
  big money), Grade B (two top-200 accounts, or one top-50), C (accounts plus a market move, no flag).
- "To win" when laying juice (the board also shows what that risks), "to risk" on plus money.
- Promotion is on forward record only: a paper rule needs 50+ graded fires, positive, plus the long-window and reason gates, to become
  a bet; C to B needs the same forward evidence; B to A needs a full season.
- Demotion never happens on CLV alone and promotion never on CLV alone. CLV is diagnostic; ROI across a holdout decides (11/5).
- Tier changes are recommended by the weekly recheck (Tuesdays) and the Monday checkpoint; the checkpoint rules are fixed in
  docs/checkpoint_rules_2026-11-02.md.

## 1a. Tiers on 11/10 (sharp/systems.py EVIDENCE is the source)
| Tier | Rules |
|---|---|
| A | wind1014 (NFL under, wind 10-14 mph); CFB first-quarter unders off the curve |
| B | nhl_early_home_fav_qual; cfb_hot_over_low_total; tennis settled hot favourite |
| C | wind1014_1h, cfb_wind14, vrest8_1h, mnf_1h, awfuldog (-7 to -13), nfl_home_dog_7510, cfb_homefav_7510_under, nba_ats_hot_home, nba_badteams_under, nba_bigfav_over, nba_under_good_home_over, nhl_bounce_home_ml, nhl_skid_fade_road, cbb_bigloss_vs_top5; NBA threes unders at a 2%+ gap; CBB first-half totals off the curve; MMA steam |
| P | everything else in systems.py, the sharp flags, and the paper logs in sections 6b and 8 |

## 2. Data of record
- Odds API history 2020-26 (`data/oddsapi/odds.sqlite`, rebuilt from `data/oddsapi/compact/`): full-game moneyline, spread and total for
  18 sports. Market open = first snapshot where two or more books post the number (06:00 and 12:00 UTC snapshots added for
  NBA/NHL/CBB/CFB/MLB); Pinnacle close and prices; results from ESPN (regular season, OT, conference, neutral flags). Team records from
  the complete ESPN schedule (preseason excluded). Snapshots oriented to the first-seen home/away.
- Derivatives (`data/oddsapi/derivs/`, from 2023-05 only, when the Odds API started keeping them): first halves, quarters, periods and
  team totals for NFL, NBA, CFB, CBB, NHL, MLB, WNBA, soccer and tennis, at one or more set times before the start. Second-half lines are
  never posted pregame, so 2H history does not exist.
- Player props 2023-26 (`data/oddsapi/derivs/*_props*.jsonl.gz`): NBA, NFL, NHL, MLB, WNBA and soccer, mostly 10 minutes before the
  start, with 60-minute, 3-hour and 6-hour snapshots for some markets. Graded on ESPN box scores (`data/boxscores`).
- Exchanges: the Novig public trade file (every fill since 2026-08-03, both sides), the Kalshi trade tape and settled markets (back about
  60-70 days for parlays), Polymarket fills by account. ProphetX quotes since 11/10 (no trade feed).
- Live: the tracker's own tape (Pinnacle, DK, FD, Caesars, BetRivers, Fanatics, theScore, Kalshi, Novig, Polymarket, ProphetX) at 5 and
  20 minute cadence; weather from Open-Meteo forecasts and MySportsWeather. Women's college basketball spreads from The Odds API
  directly (section 8d); the main feed does not carry that sport.
- Not in the history: Pinnacle in women's college basketball (it does not quote it); Challenger tennis prices.

## 3. Testing standard for a rule
0. The two-window test (Sean, 11/5): a rule must have held over Bet Labs' full history (2003 on) AND since March 2021, with a logical reason
   it should keep working. Both windows are pulled live for every rule (`data/research/betlabs_windows.json`) and shown on the board.
   Anything positive only since 2020-21, or without a reason (the afternoon CFB over), is paper at best.
1. Bet Labs rule: pull Bet Labs' own pick list for the screen and grade it at Pinnacle's closing line and price (our replay of their
   filter is the second test, not the first; replays get opens, OT and conference subtly wrong).
2. Any rule: 2003-19 window in Bet Labs must not be negative; 2020-26 at Pinnacle's close positive; 5+ of 7 seasons positive;
   train (to 2023) and test (2024-26) both positive for mined angles; a stated mechanism before it is a bet at any tier.
3. Miner (`sharp/angle_miner.py`): singles, pairs and triples over team form, rest, streaks, line and total bands, pace, conference,
   neutral, altitude, travel/body clock, CFB weather; filler-value combinations excluded; z and consistency bars. Everything it finds
   starts as paper until (2) is met; most of what it finds is a since-2020 pattern and fails the long window.
4. Weather: NFL wind from Open-Meteo agrees with Bet Labs' venue wind (their picks 160-101 at our close); CFB does not (reanalysis
   flat, their picks 135-96), so the CFB rule fires only with MySportsWeather in the blend. Bets fire inside 30h of kickoff; 48h
   triggers are listed in the open as "Coming".
5. Every system has a Bet Labs tracking screen ("Tracked: ...") and the tracker grades every fire at the price it flagged, with CLV
   against Pinnacle's close.
6. Neighbours (11/6): a rule is also graded one notch either side of each threshold. An edge that exists only at the exact thresholds,
   with neighbours near break-even, is at most tier C.
7. Every test script is saved in the repo and its result is logged in docs/RESEARCH_LOG.md (11/10). A result that cannot be rebuilt
   from a saved script is treated as unconfirmed (the 11/9 women's basketball move-follow cell is the example: section 8d).

## 4. Sharp money (Polymarket accounts)
- Paper since 2026-11-10 10:00 UTC (`SHARP_PAPER_FROM` in sharp/bet_log.py; sharp_live.py sizes new flags at 0). The flags are still
  logged, graded and shown. Why: the live record had reached 72-94, -18.9% at the 11/9 checkpoint, and the 11/10 tests found the list
  is real at the accounts' own prices (+0.74 CLV) but cannot be followed at the price we get after they move it
  (docs/sharp_flags_2026-11-09.md, docs/overnight_2026-11-10.md). Keep logging for 1-2 months per Sean before deciding more.
- Accounts ranked by CLV against Polymarket's close (top 200; sport-proven = also in that sport's top 50). Selection by CLV, evaluation
  by ROI: ranking by past ROI loses (-15% out of sample, 11/5); ranking by Pinnacle CLV is worse than the live method.
- Flag: first fill by a sport-proven account, or two top-200 accounts on a side, with no top-200 account on the other side yet.
  Grade A = sport-proven account or big money behind it; B = any other flag; C = accounts plus money or price, no flag. NBA single-account
  flags are watch only.
- A flag a sharp later opposes stays a signal (hold): 12,051 first fills, opposed later +4.1% vs never opposed +3.5%; opposition arrives
  at every hour before the start, so there is no window to wait for (11/5). Accounts on both sides before any flag: no flag. Kalshi
  4-point move against a moneyline flag: dropped.
- Annotations on every flag: priced inside / above the Pinnacle-based fair (held out +9.3% vs +3.8%); market moved toward or against the
  side before the flag; "also flagged by a system"; sharps with / against.
- Market-only signals (Kalshi price moves, bet backs, big money, sharp moves) are watch only: 392 graded, none positive at any meaningful z.
  Kalshi NHL late taker flow (30%+ one way on $500+ in the last 6h) is a paper lean. Novig and Kalshi have no account-level flow;
  Novig's leaderboard is in-app only.
- Sharp flags no longer hold a system bet (11/14). A sharp flag with a system on the other side is itself held. Each sharp flag is graded
  on its own record, with nothing dropped for an opposite flag (11/14).

## 5. Record keeping
- Every record reads the same way everywhere: label, W-L, win %, ROI. Labels: "WC backtest <years>" (our database at Pinnacle's close),
  "Bet Labs 2003-26", "Bet Labs since 2021", "Tracker" (our flagged prices). Sharp rows show that sport's sharp record, not the overall one.
- Never both sides of one market: a later bet on the other side of the SAME market stays on the tracker with no units and a note on what
  it conflicted with; the earlier bet counts. A spread on one side with the moneyline on the other is a middle (or reverse middle): both
  count, and both rows are labelled. The tracker has a filter for conflicts and middles (Sean, 11/6).
- The tracker is organised sport first, then Systems / Sharp / Paper rules, then that sport's rules or grades.
- Rest or take (11/10): each bet also records what a resting bid at a better price would have done (`rest`, `rest_filled` in
  bet_log.json); the board's "Rest or take" table compares the two. Paper.

## 6. Board rules
- Filter: All / Sharp / Systems on Today and Upcoming.
- Order: Sharp signals, System bets (coming weather fires in the open), Leans (rules firing on 4+ games grouped), Paper rules
  (collapsed), plus an Offers to rest section (section 8). In-progress games stay four hours, listed below the upcoming ones in each section.
- Hold rule (Sean, 11/14; replaces the 11/7 "no signal against" rule): a system or lean is held only when a stronger rule is on the
  other side, or Kalshi moved against it (29-67 across systems and paper by 11/14). Sharp accounts, sharp flags, bet back, big money
  and sharp move against are shown and graded, not held; each is re-checked at 30 bets against. Sharp flags still need nothing against
  them. Paper rules never count as opposition. One bet shows in one place.
- Bet tracker (11/14): bets are graded at 1 unit flat (favorites to win 1u, plus money risks 1u). Bets view defaults to "Bet per the
  board"; "Held" shows what the board held. Conflict and middle notes carry the gap between the two flags, with a within-an-hour filter.
- Cross-annotation: a bet both a system and a sharp signal land on shows the badge in both sections and in the tracker
  ("Flagged by a system AND a sharp signal").
- BetMGM never bettable. No duplicate bets on one market; stacked fires on the same side are one bet.
- Trusted experts shown for cross-checks: CFB Stuckey, Collin Wilson, Duck; NFL Dabbundo, Anderson, Giffen.
- Tracker filters: window, category, bet type (ML / spread / over / under / 1H), rule (systems and paper rules separately), sharps on the
  other side, sport.

## 6b. Execution findings (11/6, updated 11/10)
- Line shopping: the best of DK, FD, Caesars and BetRivers is worth +1.0% ROI over one book on every rule replayed 2020-26 (n 30,748),
  and lands within 0.4% of Pinnacle's closing price. Shop all four on every bet. Novig is the best taker price on 73% of sides, at -0.5%
  EV against Pinnacle's fair (docs/derivatives_round2_2026-11-06.md).
- Stale books: the original lean (a US book 2%+ better than Pinnacle's no-vig fair at the same number) went 20-43 forward to 11/10; the
  weekly recheck recommends retiring it, and it stays on paper under Sean's 1-2 month tracking instruction. stale_book_sb4 (paper,
  11/10): a FanDuel, Caesars or DraftKings moneyline 4%+ over Pinnacle's no-vig fair (sharp/stale_live.py).
- Sharp flag timing: flags 6h+ out precede most of Pinnacle's move; flags after Pinnacle already moved a point for the side are chasing
  (n 73, small).
- Pushback (11/9, docs/pushback_2026-11-09.md): a late Kalshi move against a side costs it about 20-30% ROI at every horizon in Kalshi
  history; the hold rule stays as it is.
- Replays key team histories by season (a cross-season bug was found and fixed in the NFL replays 11/6; awfuldog now 50-37-1, +10.2%).

## 7. Open items
- First fill record on the paper offers (data/state/offers_record.json) and ProphetX matched volume: read 11/11 9:00 AM.
- Parlay log: revisit at 1,000+ settled parlays (data/state/parlays_record.json).
- Women's college basketball paper rules: first fires this week (section 8d).
- NBA 1H under rule once the NBA 1H pull finishes; MLB first five and MLB 2026 rules.
- Weather fire window 30h vs 48h: re-ask at 50 games of our forecast ladder.
- Tennis Challenger settled rule and set-1 vs Kalshi once the Kalshi tape has prices.
- CBB mining once the sharp accounts bet it (2003-19 gate from the start).
- Sean's calls are listed in docs/HANDOFF.md section 7.

## 8. Resting offers and market making (11/10, paper only)
Sean (11/10): look at serving as a market maker on Kalshi and Novig at good prices, and at scanning for soft markets to offer into.
Nothing in the repo places an order; every offer is a paper row. Tests: docs/maker_2026-11-10.md, docs/overnight_2026-11-10.md sections
1, 5 and 8, docs/maker_playbook.md.
- Evidence. Novig makers earned +1.9% on $744M over three months (z 3.4), positive every month and in every market type but soccer. A
  bid 1c under Pinnacle's fair keeps about 0.8c in the last hour in every market type. Kalshi makers lost 1.4% after the maker fee over
  two months. ProphetX props sit 1.8 to 2.9c under fair (Novig 1.0 to 1.3c). The edge is about 1% of money risked and the positions
  are not hedged, so the day-to-day swing is many times the expected profit.
- Offer rules (sharp/offers_live.py, every 10 minutes). Rest a bid where Pinnacle quotes both sides at the same number and our bid
  would be first in line:
  - Novig: 1c under the no-vig fair on spreads, totals, team totals and period lines; props 2c (1c in the last hour); moneylines 1c,
    last hour only.
  - Kalshi and ProphetX: 2c under fair.
  - Left out: period moneylines, soccer moneylines (three-way), games more than 24 hours out or inside 10 minutes, fair prices outside
    8-92%. Venue and Pinnacle quotes must be within 15 minutes of each other and 45 minutes of the run.
  - Fees: Kalshi maker 0.0175 x p x (1 - p) on game lines; Novig none pregame; ProphetX assumed 2% of a market's net profit (Sean to
    confirm).
- Grading (sharp/offers_grade.py): whether the offer would have filled inside an hour at $100, and how filled and unfilled offers
  closed against Pinnacle. Board section "Offers to rest".
- What has to be true before money goes in: a positive fill record over weeks, and a quoter on Sean's own keys that reprices and pulls
  quotes when Pinnacle moves. Sean's decision.

### 8b. Rest or take
For each board bet, whether resting a bid at a better price would have filled before the start (section 5). Paper.

### 8c. Parlays (11/10)
Kalshi lists every parlay as a public settled market with its legs, so the makers can be scored (sharp/kalshi_parlays.py). Over two
samples (Sept 25 to Oct 26 and Oct 27 to Nov 10, 47 days, about 1.0M parlays) makers as a whole broke even (-0.3% and -0.8% of taker
stakes). Two- and three-leg parlays kept them 3.6% to 6.4% of stakes, outside one fortnight when two legs kept 16.3%. Parlays of 6+
legs and parlays priced 50c and up lost in both samples. A trade-by-trade check on 300 parlays (sharp/parlay_price_check.py) confirmed
the last-price shortcut. Verdict: paper. sharp/parlay_live.py logs two- and three-leg parlay prices against the product of their legs'
prices every 10 minutes; sharp/parlay_grade.py settles them. Novig publishes parlay volume but not legs or results, so its parlay makers
cannot be scored.

### 8d. Women's college basketball (11/10, paper)
Odds API history 2024-26 (US books only; Pinnacle does not quote this sport), rebuilt in sharp/wncaab_replay.py; line = the median
spread across books (BetMGM out), open = the first snapshot, close = the last snapshot before the start, 3+ books at the close.
- wncaab_dog_7_10: the closing dog is +7 to +10. 53-38-1, +11.4%, both seasons positive. Matches the 11/9 test exactly.
- wncaab_move_follow: the median spread moved 1+ point open to close; take the side it moved toward. The rebuild gives 76-57-1, +9.6%,
  with 2024-25 +16.5u and 2025-26 -3.7u. The 11/9 doc reported 75-44, +20.7% with both seasons positive; that version was not saved and
  could not be reproduced (checked: games with one snapshot, pricing off the median number, in-game snapshots, and the Odds API start
  against ESPN's tip). The rebuild is the definition of record.
- Live: loggers/wncaab_live.py in the signals job pulls The Odds API (spreads, eight US books, 1 credit a pull, at most every 18
  minutes, stops under 2,950,000 credits). A game's first pull is its open; a rule fires once, on the first pull inside the last 40
  minutes before the start, priced at the best of Sean's books on the median number. Graded from ESPN finals.
  data/state/wncaab_paper.jsonl, data/state/wncaab_record.json; on the board and tracker as paper rows.
- Both are two-season leads on about a sixth of the games. Paper until they meet the promotion gates in section 1.

## Tier review, 11/6

Rule used: a rule keeps tier B only if our own replay at Pinnacle's close is positive, and only if the edge is not confined to one era when the older era has enough bets to tell (several hundred).
- wind1014_1h: B -> C. Bet Labs +9.0% all-time, but our 1H replay is 55-51 (+0.4%).
- bounce15_1h: C -> paper. Our replay is 54-61 (-10.5%), negative every season, no better than all 1H dogs.
- cfb_homefav_7510_under: B -> C. 2003-19 is 417-385 (+1.1%) on 802 bets; the edge is 2020 on only.
- Held at this review: nfl_home_dog_7510 at B (its 2003-19 sample is only 136 bets, too small to say either way); nhl_early_home_fav_qual at B (6 of 6 seasons in our replay); nba_under_good_home_over and nhl_bounce_home_ml at C. (Later on 11/6 the full recheck moved nfl_home_dog_7510, cfb_road_dog_low_total and awfuldog to C: robust, but each has a losing season.)
- Forward tracker records (2-5 bets per rule) are too small to move any tier.
Sizing stays flat by tier. Tier A and B are both 0.5u, so an A label carries no extra stake today.

## Tier review, 11/10 (docs/weekly_recheck_2026-11-10.md; applied by Claude on Sean's "fulfill all open tasks")
- cfb_wind14: A -> C. Our own wind replay 206-182 (+1.9%) with 2024 -32.7% and 2026 -9.9%; the edge sits in Bet Labs' wind source.
  B if Sean counts the Bet Labs picks (his call).
- mnf_1h: B -> C. Bet Labs 4 of 6 seasons; our 1H replay 33-28 (+6.4%) has 2024 at -25.1%.
- cfb_road_dog_low_total: C -> paper. 2025 -1.0% and 2026 -33.3% (7-14-1).
- nhl_pl_dog_bigml: C -> paper. 40-25 (+9.9%) but 4 of 7 seasons negative and 38 of 65 bets in 2022-23.
- Not applied: retiring nba_momentum (18-40) and the original stale_book lean (20-43). Sean wants 1-2 months of tracking first.

## Sizing rule: no signal against (11/7)

Sean: "we want systems & leans without a signal against it. And sharp action without signals against it."
- A system bet or lean with any signal on the other side is held: shown greyed with the reason, graded in the tracker, no size. Signals are
  Polymarket sharp accounts, big money, a Kalshi move, a bet back, or a sharp move on the same game and market family (totals with totals;
  spread and moneyline together), first seen before the start.
- A sharp flag is held the same way: market signals against already sent it to "Sharp flags with a signal against them"; sharp accounts on
  the other side now hold it too (previously held but still sized, per the 11/5 test on account opposition alone).
- Evidence so far (forward tracker, 11/7): systems and leans with any signal against 5-7 (-10.6%) vs none 37-26 (+4.0%); sharp flags fully
  unopposed 6-5 (-5.9%) vs opposed 12-21; a Kalshi move against went 7-26 across systems, paper rules and sharp flags. Small samples: the
  tracker's tag filter keeps scoring both sides of the rule, so it can be loosened if the held group starts winning.
- Full-history test (11/6, docs/list_items_2026-11-06.md): opposition does not predict a system bet losing (honest test backed -12.5%,
  no view +6.9%, opposed -20.1% on n 139). The rule stays as the board's standing rule; it does not earn ROI on this evidence.
