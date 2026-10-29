# Bet Labs NBA audit — 2026-10-29

Same method as the NFL audit (docs/betlabs_nfl_audit_2026-10-25.md): Bet Labs NBA regular season 2003–present, closing lines,
train 08/01/2003–02/28/2021 vs holdout 03/01/2021–10/29/2026, best contiguous window per numeric filter (n ≥ 500 in train, the
NBA has ~2,400 games a season) graded on the untouched holdout, plus every list/situational value. Screens were built with the
Bet Labs "Build" dialog (NBA × bet type × Game) as temporary audit screens and deleted afterwards. Filters whose holdout rows came
back identical to training (some "(NEW)" fields ignore the date filter) were discarded.

| Market | Scanned | Survivors | Call |
|---|---|---|---|
| Totals — Under | 77 numeric + 272 situational cells | none (34/40 flip) | dead |
| Totals — Over | same | none (one 1.5-pt previous-spread sliver) | dead |
| Spread — Favorite | 99 numeric + 160 situational | none (33/40 flip; survivors are 1-pt slivers) | dead |
| Spread — Dog | same | none (23/40 flip; ATS-streak −5 sliver) | dead |
| Moneyline — Favorite | 97 numeric (ROI-ranked) | none (max z 1.6) | dead |
| Moneyline — Dog | 97 numeric (ROI-ranked) | isolated bin only (§4) | dead |

## 1. Totals
Under: top-40 training windows 34/40 below breakeven on holdout; best in-sample z 2.5 (that is noise at 77 filters). Over: 23/40
flip, the only two-sided survivor is "home previous-game spread 11–12.5" (124-98 holdout) — a 1.5-point sliver with no mechanism.
Situational (day, month, time zones, travel, B2B, streaks, division, coach): nothing on either side; the three under "hits" are a
single opening-spread value, one coach and one team.

## 2. Spreads
Favorites: max in-sample z 2.3, 33/40 flip. Dogs: 23/40 flip; "team ATS % 10–32" (the classic bad-ATS-team dog) is 57.3 % train
but **50.8 % holdout**. Rest is fully priced: team days-between-games 1/2/3/4 → 49–52 % on both halves for both sides; opponent rest
the same. The Back-2-Back field has no holdout data and is flat (50–52 %) in training anyway.

## 3. Moneylines
Favorites: nothing (best in-sample z 1.6; the two "both-positive" items are a single win-% value and a 1.5-pt spread sliver).
Dogs: 30/40 flip. The one thing that looked like a system — dog after a 13–20 point loss, +9.6 % ROI train (1,402) and +8.8 %
holdout (561) — is a single 5-point bin: the −25 bin is −0.9 % / −6.1 %, the −15 bin −4.1 % / −13.3 %, the −30 bin +0.3 % / −7.2 %.
No gradient, so it is not the NFL blowout-bounce transferring; it is one bin out of fourteen landing positive twice. Watch-list
only (re-check next summer with another season of holdout), no system.

## 4. What this means for the tracker
No NBA system goes live. The NBA page carries the board, props and the ruler only; the Systems tab says so. NBA edges come from
price discrepancies (best price vs the exchange ruler), not from situational rules — which is what the Edges screen is for.
