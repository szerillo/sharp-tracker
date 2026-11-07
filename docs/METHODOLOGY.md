# Action Winners Circle: methodology (as of 11/6/2026)

The standing process for the sharp tracker (szerillo/sharp-tracker). This is the document of record; dated docs under `docs/` hold the
tests behind each line. Updated when a rule or gate changes, with the date.

## 1. Sizing and tiers
- Unit $500. Tier A and B systems and sharp flags 0.5u; tier C leans 0.25u (including NBA threes unders at a 2%+ price gap to Pinnacle, and CBB first-half totals off the full-game curve, 11/6); CFB first-quarter unders off the curve are tier A (0.5u; Sean's call 11/6 on 3 seasons, 2023-25, every one +10% or better); tennis settled hot favourite is tier B (0.5u); MMA steam
  tier C. Paper (P) rows are logged and graded at 0 units.
- Tier A: a Bet Labs rule with a long positive history (2003-on), positive on both Bet Labs halves and 5+ of 6 recent seasons, and a
  stated reason (weather). Tier B: positive in Bet Labs' 2003-19 window AND in 2020-26 at Pinnacle's close, plus a reason. Tier C: a
  rule whose two tests disagree, or positive only at Bet Labs' price. P: everything else, with the reason shown on the board
  (`paper_why`).
- Sharp signals: Grade A (a sport-proven account, or sharps plus big money) 0.5u, soccer A 0.25u; Grade B (two top-200 accounts, or one
  top-50) and C (accounts plus a market move, no flag) 0.25u. The board prints the reason next to the grade.
- "To win" when laying juice (the board also shows what that risks), "to risk" on plus money.
- Promotion is on forward record only: a paper rule needs 50+ graded fires, positive, plus the long-window and reason gates, to become
  a bet; C to B needs the same forward evidence; B to A needs a full season.
- Demotion never happens on CLV alone and promotion never on CLV alone. CLV is diagnostic; ROI across a holdout decides (11/5).

## 2. Data of record
- Odds API history 2020-26 (`data/oddsapi/odds.sqlite`): full-game moneyline, spread and total only (no derivatives). Market open =
  first snapshot where two or more books post the number (06:00 and 12:00 UTC snapshots added for NBA/NHL/CBB/CFB/MLB); Pinnacle
  close and prices; results from ESPN (regular season, OT, conference, neutral flags). Team records from the complete ESPN schedule
  (preseason excluded). Snapshots oriented to the first-seen home/away.
- Live: the tracker's own tape (Pinnacle, DK, FD, Caesars, BetRivers, Fanatics, theScore, Kalshi, Novig, Polymarket) at 5 and 20 minute
  cadence; weather from Open-Meteo forecasts and MySportsWeather; Polymarket fills by account.
- Derivatives (`data/oddsapi/derivs/`, from 2023-05 only): NFL 1H spread, 1H total and team totals; NBA 1H total. Half-time scores from
  ESPN linescores. Second-half lines are never posted pregame, so 2H history does not exist.
- Not in the history: props; soccer beyond a few leagues; MLB 2026; Challenger tennis prices (Kalshi tape re-pull in progress).

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

## 4. Sharp money (Polymarket accounts)
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

## 5. Record keeping
- Every record reads the same way everywhere: label, W-L, win %, ROI. Labels: "WC backtest <years>" (our database at Pinnacle's close),
  "Bet Labs 2003-26", "Bet Labs since 2021", "Tracker" (our flagged prices). Sharp rows show that sport's sharp record, not the overall one.
- Never both sides of one market: a later bet on the other side of the SAME market stays on the tracker with no units and a note on what
  it conflicted with; the earlier bet counts. A spread on one side with the moneyline on the other is a middle (or reverse middle): both
  count, and both rows are labelled. The tracker has a filter for conflicts and middles (Sean, 11/6).
- The tracker is organised sport first, then Systems / Sharp / Paper rules, then that sport's rules or grades.

## 6. Board rules
- Filter: All / Sharp / Systems on Today and Upcoming.
- Order: Sharp signals, System bets (coming weather fires in the open), Leans (rules firing on 4+ games grouped), Paper rules
  (collapsed). In-progress games stay four hours, listed below the upcoming ones in each section.
- No bet against the Polymarket sharps: a system bet or lean with sharps on the other side at the flag is held (greyed, no units,
  Held note) and still graded. Full-history test (11/6, docs/list_items_2026-11-06.md): opposition does not predict a system bet losing
  (honest test backed -12.5%, no view +6.9%, opposed -20.1% on n 139; with today's list opposed +7.4% vs backed +1.7% on n 458). The
  rule stays as the board's standing rule; it does not earn ROI on this evidence.
- Cross-annotation: a bet both a system and a sharp signal land on shows the badge in both sections and in the tracker
  ("Flagged by a system AND a sharp signal").
- BetMGM never bettable. No duplicate bets on one market; stacked fires on the same side are one bet.
- Tracker filters: window, category, bet type (ML / spread / over / under / 1H), rule (systems and paper rules separately), sharps on the
  other side, sport.

## 6b. Execution findings (11/6)
- Line shopping: the best of DK, FD, Caesars and BetRivers is worth +1.0% ROI over one book on every rule replayed 2020-26 (n 30,748),
  and lands within 0.4% of Pinnacle's closing price. Shop all four on every bet.
- Stale books: a US book 2%+ better than Pinnacle's no-vig fair at the same number holds +3-4% EV at the close; the cleanest slice is a book
  lagging a Pinnacle move (+15.8%, n 71, small). Paper until it grades forward.
- Sharp flag timing: flags 6h+ out precede most of Pinnacle's move; flags after Pinnacle already moved a point for the side are chasing
  (n 73, small).
- Replays key team histories by season (a cross-season bug was found and fixed in the NFL replays 11/6; awfuldog now 50-37-1, +10.2%).

## 7. Open items
- NBA 1H under rule once the NBA 1H pull finishes; CFB 1H, MLB first five, MLB 2026 and soccer when credits are added.
- Weather fire window 30h vs 48h: re-ask at 50 games of our forecast ladder.
- Tennis Challenger settled rule and set-1 vs Kalshi once the Kalshi tape has prices.
- CBB mining once the sharp accounts bet it (2003-19 gate from the start).

## Tier review, 11/6

Rule used: a rule keeps tier B only if our own replay at Pinnacle's close is positive, and only if the edge is not confined to one era when the older era has enough bets to tell (several hundred).
- wind1014_1h: B -> C. Bet Labs +9.0% all-time, but our 1H replay is 55-51 (+0.4%).
- bounce15_1h: C -> paper. Our replay is 54-61 (-10.5%), negative every season, no better than all 1H dogs.
- cfb_homefav_7510_under: B -> C. 2003-19 is 417-385 (+1.1%) on 802 bets; the edge is 2020 on only.
- Held: nfl_home_dog_7510 at B (its 2003-19 sample is only 136 bets, too small to say either way); nhl_early_home_fav_qual at B (6 of 6 seasons in our replay); nba_under_good_home_over and nhl_bounce_home_ml at C.
- Forward tracker records (2-5 bets per rule) are too small to move any tier.
Sizing stays flat by tier. Tier A and B are both 0.5u, so an A label carries no extra stake today.

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
