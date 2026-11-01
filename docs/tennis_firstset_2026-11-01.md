# Tennis first sets: first look (2026-11-01)

Sean (11/1): first-set betting is a big tennis market and a likely place to find an edge. This is what the data on hand says. All of it
is pregame, ATP and WTA tour singles, results from ESPN set scores (data/tennis/results.jsonl, 7,217 matches since March).

## 1. The match favourite wins set 1 more often than the textbook model says (sharp/tennis_setcurve.py)

**The model.** The usual way to turn a match price into a first-set price treats sets as independent, each won with the same
probability s. In best of 3, that gives match = s^2 (3 - 2s), which is then solved for s.

**The data.** Novig match prices (two-sided mid in the last minute before start, from Novig's public trade tape since 2026-08-03)
matched to ESPN first-set winners: 2,107 matches. For match favourites priced 55% or more:

| Slice | Matches | Set-1 win rate minus model | z |
|---|---|---|---|
| All | 1,798 | +3.3 pts | 3.06 |
| ATP | 768 | +4.6 pts | 2.72 |
| WTA | 1,030 | +2.4 pts | 1.70 |
| First half of dates | 920 | +4.3 pts | 2.82 |
| Second half | 878 | +2.4 pts | 1.51 |
| August / September / October | 613 / 550 / 635 | +3.8 / +4.0 / +2.4 pts | 2.0 / 2.1 / 1.3 |

By match price (favourite's set-1 win rate, realised vs model): 0.575 → 0.597 vs 0.550; 0.725 → 0.714 vs 0.655;
0.775 → 0.742 vs 0.693; 0.874 → 0.832 vs 0.778. The 0.65-0.70 bucket is the one exception (0.596 vs 0.618).

This is a fact about tennis, not yet an edge. It becomes one only where a first-set market prices off the model, or otherwise
under-prices the favourite.

## 2. Do first-set markets price it?

- **Kalshi** (KXATPSETWINNER / KXWTASETWINNER, settled history since 2026-08-25, sharp/tennis_firstset.py).
  - Kalshi's settlement agrees with ESPN's first-set winner on all 927 matched matches.
  - Pregame trading is thin: a median of 14 fills per match, and only 269 matches had a two-sided price 15 minutes out.
  - On those, the set-1 favourite was priced 64.9% and won 68.4%. Backing every set-1 favourite at the mid made +5.3% (z 1.15),
    before Kalshi's fee (about 1.5-2 cents a contract).
  - Big vs small money and late moves on set 1 had almost no qualifying matches (thin pregame tape).
- **Novig first-set moneylines.** Only 235 matches had a pregame mid, and those prices sat close to the model:
  0.552 vs model 0.550; 0.660 vs 0.655; 0.705 vs 0.693.
  - A train/test rule built on them (back whichever side train says is under-priced) went +4.9% on train (n 53) and +6.9% on test (n 28). Too small to mean anything.
- **Pinnacle first-set lines** are now logged every 20 minutes, around the clock (loggers/tennis_lines.py). They will be the main
  check: Pinnacle's match and set-1 moneylines side by side for 100+ matches a day.

## 3. Pre-registered, from today

Rule `tennis_fs_fav`, tier C:

- **Trigger:** the match favourite is priced 55% or more on the match (Pinnacle no-vig match price).
- **Bet:** back the favourite to win set 1 when the best bettable set-1 price (Kalshi ask with fee, Novig ask) is no more than
  the empirical curve minus 1 point. The empirical curve is the model plus 3.3 points, capped at the realised bucket rate.
- **Graded on:** the ESPN first-set winner.
- **Diagnostics:** CLV against Pinnacle's set-1 close.

Checkpoint after 300 graded matches. Before then, also check whether Pinnacle's set-1 price already sits on the empirical curve
rather than the model. If it does, the market prices this and the edge is only at the slower venues.

## 4. Kalshi: first-set price against the same match's match price (added 11/1, once KXATPMATCH / KXWTAMATCH landed)

Bet: the match favourite (55%+ on Kalshi's match market) to win set 1, at Kalshi's set-1 price 15 minutes before the ESPN start.

| Entry | Train | Test |
|---|---|---|
| Mid | n 94, won 85.1% at 67.7%, +26.9% (z 4.5) | n 33, won 78.8% at 66.5%, +20.1% (z 1.8) |
| Ask (a real fill within 30 minutes) | n 47, +29.1% (z 3.4) | n 25, +26.2% (z 2.2) |
| Only when set 1 is under model + 1 pt, ask | n 39, +30.6% | n 16, +40.5% (z 2.8) |

Earlier entries: 1 hour out, n 78, +24.8%; 3 hours out, n 23, +27.7%; 6 hours out, n 17, +4.0%.

Leakage check:
- Kalshi set-1 fills jump at the ESPN start: about 7k fills in the 10 minutes before it, 93k in the first 10 minutes after.
- So the ESPN time marks the real start, and these are pregame prices.

Why it is not a system yet:
1. **Too big to be the same effect.** It is six to eight times the Novig + ESPN gap (+3.3 pts), on a far smaller sample.
2. **The market is nearly empty pregame.** Favourite-side set-1 money traded in the two hours before entry was a median of $29
   (75th percentile $183, 90th $1,290). Most of these prices are a handful of small fills: the number is real but the size is not.
3. **The fee is not in the ROI.** Kalshi's fee (about 1.5-2 cents a contract) is not taken out.

Read: first-set favourites look under-priced at every venue measured (Novig +3.3 pts over the model; Pinnacle carries about a
fifth of that; Kalshi's thin pregame book much more). The live rule (`tennis_fs_fav`) is the test. The size that can actually be
filled at Kalshi and Novig is the constraint to watch, not the edge.

## Still running

The Kalshi ATP Challenger match series is still pulling.

- Section 4 (above) is done.
- Still to do: extend section 1 with Kalshi match prices, and add the Challenger match series once that pull finishes.
