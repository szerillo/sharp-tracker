# What should cancel a system play, and where the signal in the sharp flags is (2026-11-24)

Read-only research for Sean. No rule, tier, hold or size was changed. The only code change is a research log (section 3) that
collects the sample these questions need.

**How results are judged:**
- Profit at the prices actually taken: flat 1u (favourite to win 1u, plus money risk 1u), so ROI is units per unit risked.
- Significance against break-even at those prices.
- With vs without a signal: a permutation test on the ROI gap.
- Benjamini-Hochberg at 10% across every slice in a table, so a slice has to survive the number of slices tried.
- Holdout: first half (games before 11/12) vs second half. History (2020-26 or 2024-26) and the forward log are read separately,
  so one can confirm the other.
- CLV is not used for any call.

**Sources:**
- Forward bet log (`data/state/bet_log.json`), games from 10/30 to 11/24 2 PM ET.
  - 1,575 system positions. One position per game, market and side, at the first flag. Sources: systems, curve, props, tennis, MMA
    and paper rules.
  - 435 graded sharp flags.
- Kalshi move size and timing: the day reviews (`data/research/day_review_*.json`), first tight price to the price at the signal.
  Matched for 209 of 224 positions with a Kalshi move against.
- Odds API history 2020-26: 3,680 replayed system picks (`sharp/rule_replay.py` rules, controls dropped), graded at Pinnacle's close.
  Split by how the number moved from open to close.
- Polymarket history 2024-26:
  - `sys_vs_poly.json`: system picks vs net sharp-account money, with accounts scored before 6/11/2026 (out of sample) and as scored
    today.
  - `opp_timing.json`: 12,045 first fills by a current top-200 account. These accounts were chosen on this same history, so it is
    in-sample and optimistic. It is used to find slices; the forward log tests them.
- Not usable:
  - **Bet Labs 2003-19.** It has no Kalshi, Polymarket or money-split data for those years. A line-movement test of Sean's systems
    there would need new screens in his account, which this work does not do.
  - **"Expert against".** No capper picks are logged in this repo, so it cannot be tested.

**"Core" means:** the system positions without the rules that are themselves market-driven: stale_book, kalshi_nhl_flow,
xch_homedog_fade and nba_momentum. Those rules react to the same price moves the tags measure, so they are mechanically tied to
them; 91 of the 224 Kalshi-against positions are theirs.

## Summary

**Goal 1, cancel signals:**
- **One cancel candidate is real enough to act on: Kalshi move against with big money on our side.**
  - All plays: 6-27, -56% (n 33). Core: 1-12, -85% (n 13).
  - Negative in both halves, and it survives the 10% false-discovery bar.
  - This is the third read in a row where it shows up (signal study 11/24: -47% on 55).
- **Kalshi move against on its own is the strongest single warning:**
  - All plays: -18% vs +1% without (n 224, p 0.001, survives the bar).
  - Core: -24% vs -2% (n 97, p 0.017). Live core plays: -24% vs +5% (n 52, p 0.03).
  - Both halves are negative: -44% then -10% in core. It has faded but not flipped.
  - The size of the move matters the wrong way for a simple story. Moves of 4-5.5 points carry the loss (-22% core). Moves of 6+
    points are +8% (n 17, too few).
  - On history, the opposite pattern shows. Pinnacle numbers that moved against a system pick from open to close did better at the
    close (+5.5% vs -2.3%, n 682, p 0.07). Kalshi moves are not Pinnacle moves, and the history grades at the moved price, but it
    means there is no long-run case that "the market moved against you" should cancel by itself.
- **Everything else is show-only or ignore:**
  - Sharp accounts against: +0.4% vs -1.7% (n 303). History with out-of-sample accounts shows no effect either.
  - Sharp flags against: grade A +4.8% on 27, grade B -6.4% on 12.
  - Big money against: +9% (it leans the other way).
  - Bet back against: flat.
  - Sharp move against: -4% on 81.
  - Two or more signals against: -7% on 290, not significant.
- **Opposing systems:** -16% vs 0% (n 89, p 0.10); core -44% on 19. Consistent with the current cancel rule; keep it.

**Goal 2, sharp flags:**
- **Forward, there is no slice that survives the multiple-comparison bar:** 0 of 97 slices. All 435 flags: -1.0%.
- **Consistent in both halves, but each is too small to call:**
  - Soccer sharp A: +20.5% on 54, +20% in both halves.
  - Inside it, "team to win: Yes" carries the result: +61% on 19. The "No (draw or loss)" side is -18% on 16, and soccer totals are
    -13% on 19.
  - Sharp B in all sports: +14.7% on 92 (+9% then +20%). NBA B: +11.6% on 53.
- **Consistently negative:**
  - NHL sharp A: -40% on 37 (p 0.011; -79% then -28%).
  - NBA single-account (watch) flags: -23% on 44.
  - Flags 12-48 hours before the start: -20% on 114, mostly the first half.
- **History does not back soccer:**
  - On 805 soccer first fills (2025-26), at the sharps' own price and with in-sample accounts: +0.2%. EPL +0.2% on 301, UCL -4% on 221.
  - The forward soccer edge has no long-run support yet. It may be real but recent (thin soccer markets on Polymarket), or it may
    be luck.
- **History's strongest slices are not confirmed forward:**
  - NBA (+5.3% on 5,646; moneylines +6%, totals +7%) and fills 1-3 hours before the start (+8.9% on 1,502) both survive the bar in
    both periods of history.
  - Forward, NBA flags are -1.3% on 158 and 1-3 hour flags -0.3% on 80.
  - The history is in-sample on the accounts and at the sharps' own fill price, so this gap is what a follower should expect.

## 1. Goal 1: what should cancel a system play

### Forward, every candidate (with vs without the signal)

Gap = ROI with the signal minus ROI without, in points. p = permutation test on the gap. * = survives Benjamini-Hochberg at 10%
across all 127 tests (signal x scope x sport). Halves = the gap in games before 11/12 / from 11/12.

| Signal against the play | Scope | n | Record | ROI with | ROI without | Gap | p | Halves |
|---|---|---|---|---|---|---|---|---|
| Kalshi move against | all plays | 224 | 91-128 | -18.4% | +1.1% | -19.5 | 0.001* | -31 / -14 |
| Kalshi move against | core | 97 | 36-56 | -24.0% | -2.0% | -22.0 | 0.017 | -44 / -10 |
| Kalshi against + big money with | all plays | 33 | 6-27 | -56.4% | -0.3% | -56.1 | 0.001* | -64 / -48 |
| Kalshi against + big money with | core | 13 | 1-12 | -84.8% | -3.1% | -81.7 | 0.001* | -63 / -101 |
| Kalshi against, no other signal against | all plays | 86 | 32-52 | -27.6% | 0.0% | -27.6 | 0.004* | -43 / -17 |
| Kalshi against, no other signal against | core | 38 | 14-22 | -26.5% | -3.2% | -23.3 | 0.11 | -67 / +6 |
| Kalshi against + sharp accounts with | all plays | 68 | 28-40 | -20.0% | -0.6% | -19.4 | 0.07 | -31 / -12 |
| Kalshi against + big money against | all plays | 58 | 28-30 | -4.3% | -1.2% | -3.1 | 0.77 | +7 / -10 |
| Kalshi against, move 4-5.5 pts | core | 69 | 28-40 | -22.0% | -2.8% | -19.3 | 0.08 | -21 / -19 |
| Kalshi against, move 6+ pts | all plays | 17 | 9-7 | +8.4% | -1.4% | +9.8 | 0.64 | +3 / +18 |
| Kalshi against, first seen 6h+ before start | core | 54 | 23-31 | -20.4% | -3.1% | -17.3 | 0.15 | -12 / -21 |
| Kalshi against, first seen under 6h before start | core | 23 | 9-12 | -15.7% | -3.8% | -11.9 | 0.50 | -7 / -15 |
| Kalshi against, already there when the system fired | core | 41 | 17-23 | -20.3% | -3.4% | -16.9 | 0.21 | -23 / -10 |
| Kalshi against, arrived after the system fired | core | 36 | 15-20 | -17.7% | -3.6% | -14.2 | 0.32 | +13 / -28 |
| Big money against | all plays | 232 | 130-99 | +9.2% | -3.0% | +12.3 | 0.05 | +21 / +7 |
| Bet back against | all plays | 165 | 83-79 | -1.3% | -1.3% | 0.0 | 1.00 | -6 / +4 |
| Sharp move against | all plays | 81 | 38-42 | -4.3% | -1.2% | -3.1 | 0.76 | -1 / -4 |
| Sharp accounts against | all plays | 303 | 159-138 | +0.4% | -1.7% | +2.2 | 0.70 | +6 / 0 |
| Sharp flag against, any | all plays | 121 | 66-55 | +0.7% | -1.5% | +2.2 | 0.78 | +8 / -2 |
| Sharp flag against, grade A | all plays | 27 | 18-9 | +4.8% | -1.5% | +6.2 | 0.71 | +42 / -6 |
| Sharp flag against, grade B | all plays | 12 | 6-6 | -6.4% | -1.3% | -5.1 | 0.83 | n/a / -3 |
| Opposing system | all plays | 89 | 38-51 | -15.7% | -0.4% | -15.2 | 0.10 | -3 / -22 |
| Opposing system | core | 19 | 5-14 | -43.7% | -3.2% | -40.5 | 0.05 | n/a / -40 |
| Two or more different signals against | all plays | 290 | 137-148 | -7.3% | -0.1% | -7.2 | 0.19 | -9 / -7 |
| Any signal against | all plays | 701 | 356-334 | -0.2% | -2.1% | +2.0 | 0.66 | +5 / -1 |

Grade C sharp rows against a system play: too few to test (under 10).

**By sport, the only other slices under p 0.05:**
- Sharp flag against NHL plays: +47% on 34, survives the bar. It mirrors NHL sharp flags losing (section 2): systems those flags
  oppose win.
- Kalshi against NHL plays: -23% on 63, p 0.013.
- Sharp accounts against NHL plays: +23% on 107, p 0.008.
- Bet back against CFB plays: +45% on 18.
- Opposing system in CFB: 1-9.

All are small, sport-specific, and three of them point the "wrong" way for a cancel rule.

### History (no Kalshi or exchange tape before October 2026)

- **Market moved against the play, Odds API 2020-26, Pinnacle close:**
  - Number moved against the pick: +5.5% on 682, vs -2.3% when it moved for it or stayed (p 0.07).
  - By era: +9.9% in 2020-23, +3.5% in 2023-26.
  - Same direction in CFB, NBA and NHL, and in every rule with 10+ picks each way.
  - Mechanism: a move against means the pick is taken at a better number at the close. The forward log grades at the system's own
    (earlier) price, so the two measure different things. The history says a market move against is not by itself a reason to
    cancel.
- **Sharp accounts on Polymarket vs system picks, 2024-26 (`sys_vs_poly.json`):**
  - Live rules, with accounts scored before 6/11/2026 and games after it: opposed -20% on 41, none +7% on 63, backed -13% on 35. No
    pattern, and not significant (p 0.30).
  - All 1,851 picks: opposed -3.0%, backed -4.4%, none +1.0%.
  - With accounts as scored today (in-sample): opposed +0.9% vs backed -6.1%, the opposite of a cancel signal.

### Verdict per signal

| Signal against | Call | Evidence | Mechanism (one sentence) |
|---|---|---|---|
| Kalshi move against + big money on our side | **Cancel (recommend to Sean)** | -56% on 33 (core -85% on 13); both halves; survives the bar; third read in a row | Big money is with us yet the informed exchange price walked away, so the money on our side is being faded by better-informed traders. |
| Kalshi move against (alone) | **Downsize (recommend half size) and keep the warning; re-read 12/8** | -18% all, -24% core; both halves negative but fading; history of Pinnacle moves points the other way | Kalshi game-day moves may carry late news (injuries, lineups) the system's pre-game inputs do not see. |
| Opposing system | **Cancel (keep the current rule)** | -16% on 89, core -44% on 19 | Two rules on opposite sides means neither rule's condition is the deciding fact for this game. |
| Sharp move against | Show-only | -4% on 81; history: no effect | A line move alone is already priced into the number we take. |
| Sharp accounts against | Ignore (show) | +0.4% on 303; history out of sample: none | Polymarket sharps beat the close, but systems target things the close misses, so the two are not opposed. |
| Sharp flag against, grade A / B / C | Show-only | A +5% on 27, B -6% on 12, C too few | Same as sharp accounts; NHL flags are themselves losing. |
| Big money against | Ignore | +9% on 232 | Big tickets against a system are often public or square money. |
| Bet back against | Ignore | Flat on 165 | A Kalshi give-back is the market correcting a steam, not information against the system. |
| Two or more signals against | Show-only | -7% on 290, not significant | Counting signals adds noise from weak ones. |
| Expert against | Cannot test | No capper picks are logged | n/a |

### Power: how many more plays each needs

To confirm a gap, the "with" group needs about (2.8 x sd / gap)^2 plays, with sd about 1.0u per play at these prices (80% power,
5% two-sided).

| Signal (core) | n now | New per week (core) | More plays to confirm the gap seen | More plays to rule a 10-pt gap in or out | Weeks at the current rate |
|---|---|---|---|---|---|
| Kalshi move against | 97 | about 27 | about 50 | about 700 | 2 / 26 |
| Kalshi against + big money with | 13 | about 4 | already past it | about 780 | 0 / 200 |
| Opposing system | 19 | about 5 | about 25 | about 770 | 5 / 150 |
| Sharp accounts against | 112 | about 31 | n/a (no gap) | about 680 | 22 |
| Sharp flag against, grade A | 16 | about 4 | about 110 | about 770 | 28 / 190 |
| Big money against | 86 | about 24 | about 630 | about 700 | 26 / 29 |

The observed gaps are almost surely too large (the winner's curse): the first-half Kalshi gap was -44 and the second -10. Planning
on the 10-point column is the honest version. At 0.25u, ruling a 10-point gap in or out on Kalshi alone takes about six months.

## 2. Goal 2: where the signal in the sharp flags is

### Forward (435 flags, 10/30 to 11/24, true out of sample): every slice with n 10+

No slice survives Benjamini-Hochberg at 10% (0 of 97). p = break-even test.

| Slice | n | Units | ROI | p | 1st half / 2nd half |
|---|---|---|---|---|---|
| All flags | 435 | -5.99 | -1.0% | 0.83 | -11.0% / +7.2% |
| Soccer, all | 57 | +12.32 | +16.5% | 0.27 | +14.9% / +20.7% |
| Soccer sharp A | 54 | +13.88 | +20.5% | 0.20 | +20.4% / +20.7% |
| Soccer, team to win: Yes | 19 | +15.69 | +60.8% | 0.05 | +66.8% / +42.8% |
| Soccer, team not to win (draw or loss) | 16 | -4.02 | -18.4% | 0.46 | -28.8% / +22.5% |
| Soccer totals | 19 | -2.97 | -12.9% | 0.56 | -17.0% / -7.5% |
| Soccer EPL | 26 | +13.29 | +40.9% | 0.09 | +43.9% / +38.1% |
| Soccer UCL | 16 | +5.42 | +23.1% | 0.39 | +23.1% / - |
| Sharp A, all sports | 271 | -21.15 | -6.3% | 0.33 | -15.4% / +2.1% |
| Sharp B, all sports | 92 | +21.75 | +14.7% | 0.11 | +8.7% / +19.5% |
| Sharp C | 28 | +9.31 | +27.4% | 0.12 | n/a / +29.1% |
| NBA sharp B | 53 | +9.15 | +11.6% | 0.36 | +3.6% / +22.1% |
| NBA sharp A | 52 | +1.08 | +1.5% | 0.91 | -14.7% / +12.5% |
| NBA single-account (watch) | 44 | -15.91 | -22.9% | 0.09 | -27.6% / -17.5% |
| NHL sharp A | 37 | -17.88 | -40.3% | 0.011 | -79.4% / -27.7% |
| NFL sharp A | 43 | -6.50 | -12.0% | 0.53 | -47.6% / +37.1% |
| CFB sharp A | 74 | -7.83 | -9.3% | 0.40 | -13.2% / -6.8% |
| CFB sharp B | 11 | +12.87 | +49.5% | 0.03 | +108.9% / +36.9% |
| Flag type: proven (top-200 and sport top-50) | 194 | -19.43 | -8.4% | 0.29 | -14.5% / -2.6% |
| Flag type: 2+ top-200 accounts | 120 | +12.41 | +7.1% | 0.40 | -5.9% / +19.1% |
| Flag type: one top-50 account | 93 | -8.28 | -5.5% | 0.55 | -11.9% / -0.2% |
| Accounts on the flag: 1 | 315 | -18.40 | -4.4% | 0.44 | -13.4% / +2.6% |
| Accounts on the flag: 2 | 96 | +13.05 | +9.2% | 0.33 | -7.1% / +24.8% |
| Accounts on the flag: 3+ | 24 | -0.64 | -2.0% | 0.92 | 0.0% / -3.7% |
| Best account rank 1-20 | 53 | +10.07 | +12.2% | 0.31 | +20.3% / +7.8% |
| Best account rank 21-50 | 98 | -3.45 | -2.2% | 0.81 | -17.6% / +14.1% |
| Best account rank 51-100 | 87 | -4.58 | -4.0% | 0.68 | +1.5% / -8.7% |
| Best account rank 101-200 | 169 | -17.34 | -8.7% | 0.32 | -21.7% / +4.5% |
| Flag under 1h before start | 54 | +0.44 | +0.6% | 0.96 | +14.9% / -9.6% |
| Flag 1-3h before | 80 | -0.31 | -0.3% | 0.98 | -5.4% / +4.4% |
| Flag 3-12h before | 163 | +19.31 | +9.0% | 0.24 | -3.6% / +17.5% |
| Flag 12-48h before | 114 | -32.39 | -19.6% | 0.04 | -39.1% / +1.3% |
| Flag 48h+ before | 24 | +6.95 | +17.7% | 0.29 | +31.4% / +7.4% |
| Moneyline / spread / total (non-soccer) | 150 / 123 / 127 | | -2.2% / -2.5% / -5.8% | 0.5-0.8 | |
| Price: dog under 35c / 35-50c / fav 50-65c / 65c+ | 54 / 86 / 249 / 46 | | -6.2% / -0.9% / -3.4% / +5.7% | 0.5-0.9 | |
| Market had moved with / against / flat before the flag | 161 / 107 / 75 | | +2.7% / +0.4% / +9.0% | 0.5-1.0 | |
| A sharp later took the other side: no / yes | 268 / 167 | | -1.5% / -0.2% | 0.8-1.0 | |
| Kalshi move against the flag: no / yes | 344 / 91 | | +1.3% / -10.8% | 0.8 / 0.35 | |
| Market kept moving the flag's way after it / moved back (known only afterwards) | 181 / 207 | | +4.4% / -4.0% | | |

### History (12,045 first fills by current top-200 accounts, June 2024 to Nov 2026; in-sample accounts, the sharps' own price)

All fills: +3.0% (z 3.4). Six of 57 slices survive the 10% bar:
- NBA +5.3% on 5,646
- NBA moneylines +6.0% on 1,872
- NBA totals +7.3% on 1,975
- all moneylines +3.5%
- fills 1-3 hours before the start +8.9% on 1,502
- fills never opposed by another sharp +2.9%

Each is positive in both periods. Soccer is +0.2% on 805:
- Bundesliga +9.3% on 188
- EPL +0.2% on 301
- UCL -4.2% on 221
- MLS -8.4% on 95
- Soccer 3-12 hours before the start: -9%
- Soccer 1-3 hours before: +10% on 106

### Soccer sharp A: why +20%, and does it hold?

- **What carries it:**
  - The "team to win: Yes" market: 15-4, +61%.
  - The EPL: 18-8, +41%.
  - Single proven accounts (the top-200 account that is also in soccer's top 50): +26% on 52.
  - Flags on the "not to win" side and on totals lose.
- **Timing:** no clear pattern. 12-48 hours before the start was -20% then +155% on 17; 1-3 hours +21% on 13.
- **Out of sample:**
  - History does not confirm it. EPL first fills were +0.2% on 301, and the history cannot split Yes from No (the file only stores the
    market type).
  - The forward result is 54 flags with p 0.20. It is a lead, not a finding.
- **Mechanism, if real:** Polymarket soccer markets are thin and recent. A soccer-specialist account backing a team to win is more
  informative than in liquid US markets. "Not to win" bets are often hedges, which would explain why the No side does not carry it.
- **What would decide it:** about 150 more soccer A flags split by Yes / No and by league. At about 15 a week, that is roughly 10 weeks.

### Real / noise / undecided

| | Slices | Why |
|---|---|---|
| **Real (act on it)** | None yet | No forward slice survives the bar, and history's best slices (NBA, 1-3h) do not repeat forward. |
| **Lean negative (paper only, consider excluding from any future live slice)** | NHL sharp A (-40% on 37, both halves); NBA single-account flags (-23% on 44); flags 12-48h before the start (-20% on 114) | Each is negative in both halves or large and negative, but none survives the bar. |
| **Lean positive, keep tracking** | Soccer sharp A, mainly the Yes side and the EPL; sharp B in all sports (+15% on 92); NBA B (live test at 0.10u since today); 2-account flags (+9% on 96) | Positive in both halves, each under 100 graded. |
| **Noise** | Account rank bands, price bands, market type outside soccer, whether a sharp later opposed, whether the market had moved before the flag | Flat in both data sets. |

**Data needed to decide the rest:**
1. **Account rank at the time of each historical fill** (walk-forward scoring). This would make history out of sample and tell us
   whether "proven" and "top 20" accounts really are better.
2. **The Yes / No side and the follower's fill price in the history file.** Today it stores only the sharps' price and the market type.
3. **About 100 more forward flags each** for soccer A, sharp B and NBA B.
4. **A Bet Labs line-move split of Sean's systems for 2003-19** (cancel question). It needs new screens in his account, so it waits
   for his OK.

## 3. Tracker set-up so the sample accumulates cleanly

From today, every signals build writes `data/state/against_panel.json`. Research only: nothing on the board reads it.

- **Rows:** one per system position, covering systems, curve, props, tennis, MMA and paper rules (sharp flags and watch signals are
  not system plays).
- **Signals against, each with:**
  - kind (Kalshi move, big money, bet back, sharp move, sharp flag and its grade, sharp C, opposing system)
  - first-seen time and hours before the start
  - whether it was there before the system fired
  - its price
  - the Kalshi move size in points
- **Signals with it:** the same fields.
- **Both sides paper-graded:**
  - The play at its own price.
  - The other side at the opposing signal's price in the same market, or 1 minus the price.
  - Flat 1u.
- **The board's own call:** every row also carries board_status (bet / held / pass / dropped / wait / paper), so held plays are
  graded too.

The 12/8 re-read of the Kalshi warning should run from this panel: the cancel table above on games from 11/24 19:00Z, core and
all plays, by move size and timing.

## Method notes

- Forward positions: graded, not excluded, priced 2-98c, games before 2026-11-24 19:00Z; conflicting-systems pairs are left out.
- Sharp flags are graded one by one at the logged Polymarket ask (the 11/14 rule).
- History picks are graded at Pinnacle's close at flat 1u to risk. Polymarket fills are graded at the sharps' own price.
- Scripts are in the session scratch directory: `cs/a.py` (forward cancel tests), `cs/b.py` + `cs/d.py` (history), `cs/c.py`
  (sharp flags). Outputs: `goal1_fwd.json`, `goal2.json`, `hist_picks.json`.
