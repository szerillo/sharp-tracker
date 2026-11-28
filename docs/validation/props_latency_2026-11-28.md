# Why props rows reach the board 10 to 50 minutes before the start (11/28/2026)

Asked by Kirk for Sean (td_props_earlier). Research only: no live props logic changed. A draft change is in
`docs/drafts/props_window_2026-11-28.patch` (applies cleanly, not applied; Kirk 11/28: leave it as a draft, Sean decides).

## 1. Why rows are late: a deliberate 1-hour gate, then a slow job and late edges

- **The gate.** `sharp/props_live.py` checks a game only when it starts 9 to 60 minutes from now:
  `if not 0.15 < h <= float(os.environ.get('PROPS_H', 1)): continue`. The comment: "11/7 (Sean): the backtest priced every prop 10-14
  min before tip; flag only inside the last hour (was 3 h)". No workflow sets `PROPS_H`, so it is 1 hour. It is not the odds pull
  schedule and not a lineup or goalie wait.
- **The job.** The props step runs inside `signals.yml` (step "prop price-gap paper leans", skipped on the on-demand fast run), which `pulse.yml` dispatches every 10 minutes. Runs
  take 21 minutes (median of the last 32 successful runs, max 29), and a run that is still going queues the next, so the props check
  actually runs about every 16 minutes (median gap between finishes; max 42). The first check inside the hour lands anywhere from 60 to
  about 44 minutes out.
- **The edge itself.** Most rows were not caught on the first check. From props_paper (92 rows since 11/6): minutes before the start at
  the flag, median 33 (min 9). Barkov and Hutson SOG (11/27) were flagged at 19:46Z, 13 minutes out, and both carry a Pinnacle quote
  time of 19:45Z: Pinnacle moved 15 minutes before puck drop, and before that there was no 2% gap. The same game's Tkachuk and Dvorak
  were flagged 48 minutes out.
- **Board lag.** From the flag to the row being on main: 2 to 3 minutes on every row checked (11/25-11/28).

| Player (11/25-11/28) | Flagged, min before start | On main, min before start |
|---|---|---|
| Jaylen Brown threes | 56 | 53 |
| Toews SOG | 39 (re-logged) | 53 |
| Rice anytime TD | 38 (re-logged) | 51 |
| Melton threes | 37 (re-logged) | 48 |
| Catton SOG | 49 | 46 |
| Tkachuk, Dvorak SOG, Warren TD | 48 | 45 |
| Logan Thompson saves | 46 | 42 |
| Kelce TD | 38 | 35 |
| Reaves threes | 23 | 20 |
| Barkov, Hutson SOG | 13 | 11 |

"Re-logged": the row was on main before its own flag time. It was dropped by the push race fixed on 11/27 (docs/validation/
append_guard_2026-11-27.md) and logged again with a new flag time and price.

## 2. Earlier publishing: where the edge exists earlier (backtests, docs/nfl_props_2026-11-08.md)

| Rule | T-10 | T-60 | T-180 | Read |
|---|---|---|---|---|
| NBA threes unders, EV 4%+ (live rule) | 791 bets, +11.6%, 4/4 | 612, +11.2%, 4/4 | 449, +8.1%, 4/4 | holds 3 hours out |
| NBA threes unders, 2%+ | 2,012, +7.8% | 1,680, +7.6% | 1,239, +8.1%, 4/4 | a standing book shade |
| NHL SOG + saves unders, 2%+ | 843, +6.1% | 779, +6.0%, 2/4 | no data | already weaker at T-60 (goalie news) |
| NFL anytime TD, fair 25-50% | 1,571, +10.4%, 4/4 | | 1,261, +7.0%, 3/4 (2026 -2%) | weaker earlier |
| NFL rushing-yards outlier | 100, +21.9%, 4/4 | | 81, +9.9%, 2/4 | edge is inactives news (~90 min out) |

Live record (props_live.json): 90 graded, 41-49, -0.53u. By rule: threes unders 26 bets 15-11 +15.7%; NHL SOG 39 bets 19-20 +2.2%;
NHL saves 3 bets 2-1; anytime TD 22 bets 5-17 -35.5%. Flag lead inside the hour: 40-60 min out 18 bets +7.7%, 20-40 min 56 bets -3.2%,
9-20 min 11 bets -8.3% (small samples). CLV +1.62 average, 49 of 51 beat the close (information only, not a decision input).

What earlier publishing would do to the record: only NBA threes has evidence for it. Moving threes to a 3-hour window logs each lean at
its first appearance, so prices come from the T-180 to T-60 range, where the backtest pays +8.1% instead of +11.2% to +11.6% per bet,
plus leans whose gap closes before the last hour (these are not logged today). NHL and NFL: no evidence of an earlier edge; keep 1 hour.

## 3. A flag timestamp

Every row already has `flagged` (when the props job found it), plus `pin_ts` and `book_ts` (the quote times), and `start`. Latency =
start minus flagged; board latency is 2-3 minutes after that. The re-logged rows above lost their first flag time; that cannot happen
again since the 11/27 merge fix. The draft adds `last_check`, `last_ev`, `last_price` and `live` (see 5).

## 4. Thompson and Jaylen Brown after their start: not reproduced (resolved 11/28)

On main, from every props_live.json commit 11/25-11/28: Jaylen Brown threes (Heat @ 76ers) first on main 21:16Z, start 22:10Z on the
Odds API and 22:00Z on ESPN (44 minutes before tip); Logan Thompson saves (Flyers @ Capitals) first on main 23:17Z, start 00:00Z on both
(43 minutes before). Both were gone from props_live.json later the same night (after their games started, as designed). The Odds API
lists NBA starts 10 minutes after ESPN's time; NHL and NFL match. Resolved (Kirk, 11/28): his 10-50 minute figure was the
job-side view (first time his job saw the row, up to a poll interval after the flag) against the Novig market's start time, which can
differ from ESPN and the Odds API by about 10 minutes for NBA. The first-on-main numbers above stand; his figure for these two is dropped.

## 5. Recommendation (needs Sean's OK)

1. **NBA threes unders: check from 3 hours before tip** (`WINDOW_H = {'nba': 3, 'nhl': 1, 'nfl': 1}`), same 4%+ strict-EV rule. Backtest
   T-180: 449 bets, +8.1%, 4 of 4 seasons. Cost: The Odds API charges markets x regions per event call, 2 credits for threes; about 7
   extra checks per game at the current cadence, so about 14 credits per NBA game.
2. **Re-check open rows every run** until 9 minutes out: `live: false` when the edge drops under the rule (or the line is gone), `true`
   again if it returns. The auto-placer places only `live: true` rows. The paper record keeps grading the first flag, so it stays
   comparable with the backtest; a `live` split shows what the auto-placer would have done.
3. **NHL and NFL stay at 1 hour.** The Barkov/Hutson miss was a late Pinnacle move (an edge that appeared 13 minutes out), not the
   schedule. Since 11/28 00:xx ET (Kirk) the placer takes a props row while the start is more than 3 minutes away (was 10 until
   11/27) and polls every 2 minutes (was 10), so a row flagged at props_live's 9-minute floor can now be placed; Barkov and Hutson
   would have been, if still priced. No props_live change is needed for this.
4. Optional, independent: move the props step to its own 5-minute workflow (the board's signals run takes 21 minutes). That shortens
   latency for every sport but costs about 3x the credits of the current cadence inside the window.
