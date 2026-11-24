# Weekly checkpoint: decision rules (written 2026-11-02, before reading this week's numbers)

These rules decide what happens to each paper rule and signal at the Monday checkpoints. They are written before the first
checkpoint's numbers are read, and change only by a dated edit here, never during a read.

## Systems (bottom-up rules: Bet Labs and our own)

The market does not price these, so CLV is a diagnostic, not the verdict.
- **Retire** at 25+ graded bets if ROI is negative AND mean CLV is 2.0+ pts worse than the close (losing and paying a bad number), or at
  50+ graded bets if the ROI z-score is -2 or worse.
- **Review** (keep, flag on the page) at 15+ graded bets with ROI below -15% and CLV worse than -1.5.
- Nothing is promoted on tracker results before 100 graded bets.

## Top-down signals (steam_rev, Kalshi movers, big vs small, sharp moves, Polymarket sharp accounts)

CLV is the main test.
- **Retire** at 50+ graded if mean CLV is at or below zero with z of -1 or worse.
- **Promote** (from watch to a sized paper bet) at 150+ graded with CLV z of 2 or better and ROI not below -5%.
- Polymarket sharp accounts: graded on CLV vs Polymarket's close and, where we have it, Pinnacle's; first read at 150 graded flags.

Amended 2026-11-02 (Sean): watch signals that are not bet are not retired at this stage; they keep logging and stay on the
page until a bigger sample (300+ settled) or Sean decides. The retire rule above applies to signals that are bet or paper-bet.

## Tennis first-set favourites (tier C)

First read at 300 graded matches (set in the methodology doc); retire early only at 100+ with ROI z of -2 or worse.

## Always

- One week of results is never a reason to retire or promote, except under the rules above.
- Each checkpoint writes what was read, what changed and why, in the methodology doc's change log.

## Amended 2026-11-24 (Sean, via Kirk): profit only. CLV never decides

This amendment replaces every CLV test above for systems, signals that are bet or paper-bet, and sharp flags. CLV stays in the tables as
information only. The tests are realized profit: units and ROI at the prices actually taken, sample size, the chance of the result at
break-even (binomial or bootstrap at the price-implied win probability, after any fee), and stability across halves of the sample.

- **Retire:** at 50+ graded, a 5% or smaller chance of a result this bad at break-even AND ROI negative in both halves; or at 25+ graded,
  a 1% or smaller chance. For a rule picked on a Bet Labs backtest, also require the live 90% ROI range to sit entirely below the
  backtest's ROI (a small live sample does not overrule a large backtest without that).
- **Review** (flag on the page, no change): at 15+ graded, a 10% or smaller chance of a result this bad at break-even.
- **Promote, paper to live (tier C, 0.25u unless Sean sizes it):** at 100+ graded, a 10% or smaller chance of a result this good at
  break-even after fees, AND ROI positive in both halves.
- **Promote, watch to sized paper:** at 150+ graded, the same test.
- **Sharp flags (replaces the 11/10 "until they beat Pinnacle's close"):** a sport x grade slice goes live only on the promote line above.
- **Tennis first-set favourites:** first read at 300; retire early only at 100+ with a 5% or smaller chance of a result this bad.
- **Unchanged:** one week is never enough on its own; each checkpoint writes what it read and why; no rule or status change without Sean.

Re-decided under these lines on 11/24 (docs/decisions_2026-11-24.md): the 11/23 retirements of cfb_road_dog_low_total and steam_rev and
the 11/23 promotion of Kalshi 4+ movers to sized paper are undone, since none meets the profit retire or promote bar.
