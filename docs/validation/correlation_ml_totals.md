# Side and total correlation: is "favorite ML + Over" one position? (td_corr_backtest)

Asked by Sean 11/28/2026. Paper research only; no rule, sizing or board change. Results go below the pre-registration, which was
committed before any outcome was computed.

## Pre-registration (written and committed before looking, 11/28/2026)

**Data.** `data/oddsapi/odds.sqlite` (games + results), Pinnacle closing lines only (`pin_close_home/away` are Pinnacle's de-vigged
closing win probabilities; `pin_close_sp` the home spread; `pin_close_tot` the total). Sports: CFB, NFL, NBA, NHL, CBB. Games starting
2020-01-01 through 2026-11-28 with a final score, both closing ML probabilities, a closing spread and a closing total. Regular season
only (`sharp/rule_replay.regular_season`: ESPN season type 2; blank type counts as regular except the 2020 NHL/NBA bubble). Nothing is
filled from another book; a game missing any Pinnacle close is dropped. Counts by sport are reported. Known gap before looking: NFL
2024-2026 Pinnacle ML closes exist for only about half the games.

**Definitions.**
- Favorite = the side with the higher closing de-vigged probability; exact 0.5 games are dropped from the ML and spread sections.
- ML result: favorite won (overtime and shootouts count, as ML bets settle). Spread result: favorite covered the closing spread; a push
  is dropped from that pair. Over result: final total above the closing total; a push is dropped from that pair.
- Price bands on the favorite's fair closing price: -100 to -200 (p 0.500 to 0.667), -200 to -400 (0.667 to 0.800), -400 and longer
  (0.800+). The dog is the mirror (+100 to +200, +200 to +400, +400+).
- Total size: within each sport, thirds (low, mid, high) of the closing total over the whole sample.
- phi = the Pearson correlation of the two 0/1 results, with a 95% interval (Fisher z, n - 3).

**What phi can and cannot say.** phi is the same number for a pair and for both its complements: phi(favorite ML, Over) =
phi(dog ML, Under). So "dog + Under correlates, favorite + Over only slightly" cannot be a difference in phi. It can be a difference in
lift, which is reported for both:
- lift(Over | favorite wins) = P(Over | favorite wins) - P(Over)
- lift(Under | dog wins) = P(Under | dog wins) - P(Under)
Both equal cov / P(that side wins), so the dog's lift is larger by P(fav wins) / P(dog wins). Both lifts are reported, not chosen
after the fact.

**Outputs.**
1. phi(fav ML win, Over) by sport, by price band, by total third; n, 95% interval, and both lifts.
2. The same for spread: phi(fav covers, Over).
3. Joint rates for the 4 combos (fav+Over, fav+Under, dog+Over, dog+Under) against the independence product, for ML and for spread.
4. Risk of holding two bets: each bet 1 unit at its fair closing price (ML pays 1/p - 1, loses 1; spread and total at even money, +1
   or -1), the variance of the 2-bet P/L against the sum of the two variances (the independent case). Ratio = 1 + 2 cov / (var1 + var2).
5. Control: team total vs game total. A team's implied total = (closing total + favorite margin) / 2 for the favorite, (total -
   margin) / 2 for the dog; result = the team scored over it (exact hit dropped). phi(team over, game over), both teams, per sport.

**Decision rule (set now).** A pair with |phi| >= 0.15 counts as one position when sizing; below that, independent. Applied per sport,
and per price band where the band has 300+ games. If the 95% interval straddles 0.15, it is reported as "borderline" and the point
estimate decides.

**Script.** `sharp/research/corr_ml_totals.py` (committed with the results). Run once; any re-run with changed definitions gets a
dated note here.

## Results (run once, 11/28/2026 7:00 PM ET, `sharp/research/corr_ml_totals.py`; numbers in `data/research/corr_ml_totals.json`)

Answer: at the closing line, the side result and the total result are close to independent in all five sports. No pair reaches the
pre-registered |phi| >= 0.15 in any sport or any band with 300+ games. The control (team total vs game total) comes out at
0.49 to 0.63, so the method does pick up a real correlation where one exists.

### 1 and 2. phi by sport (95% interval), with both lifts

| Sport | Games | ML: phi(fav wins, Over) | Over lift if fav wins | Under lift if dog wins | Spread: phi(fav covers, Over) | Control: phi(fav team over, game Over) |
|---|---|---|---|---|---|---|
| CFB | 4,687 | +0.027 (-0.002, +0.056) | +0.8 pts | +2.2 pts | +0.050 (+0.021, +0.079) | +0.556 |
| NFL | 1,346 | +0.012 (-0.042, +0.066) | +0.4 | +0.9 | -0.037 (-0.092, +0.017) | +0.556 |
| NBA | 7,317 | +0.027 (+0.004, +0.050) | +0.9 | +2.0 | -0.002 (-0.025, +0.021) | +0.618 |
| NHL | 7,698 | -0.004 (-0.027, +0.019) | -0.2 | -0.3 | +0.042 (+0.019, +0.064) | +0.531 |
| CBB | 25,770 | -0.009 (-0.021, +0.003) | -0.3 | -0.7 | -0.019 (-0.031, -0.006) | +0.630 |

ML n is a little below games (ML ties and total pushes dropped). "Lift" = how many points the second bet's win rate rises when the
first one wins. Sean's direction is right where there is any effect at all (CFB, NBA): the dog-and-Under lift is about 2.3 times the
favorite-and-Over lift, as the pre-registration said it must be (same phi, divided by the smaller dog win rate). But it is about 2
points, not a stacked position. In NHL and CBB it is zero or slightly the other way.

By favorite price band (phi, n):

| Sport | ML -100 to -200 | ML -200 to -400 | ML -400+ | Spread -100 to -200 | Spread -200 to -400 | Spread -400+ |
|---|---|---|---|---|---|---|
| CFB | +0.021 (1,641) | +0.026 (1,388) | +0.032 (1,602) | +0.017 (1,599) | +0.010 (1,355) | **+0.118** (1,573), interval to +0.166 |
| NFL | +0.005 (747) | +0.027 (453) | +0.015 (121, under 300) | -0.051 (725) | -0.033 (445) | +0.044 (117, under 300) |
| NBA | +0.010 (3,594) | +0.033 (2,346) | +0.031 (1,293) | +0.000 (3,530) | -0.001 (2,304) | -0.011 (1,276) |
| NHL | -0.010 (5,954) | +0.022 (1,315) | -0.017 (42, under 300) | +0.029 (5,954) | +0.092 (1,315) | +0.193 (42, under 300) |
| CBB | -0.014 (11,512) | -0.022 (7,526) | +0.005 (6,422) | -0.017 (11,289) | -0.036 (7,392) | -0.002 (6,312) |

By total third, the largest is CFB spread in low totals (under 50): +0.086 (1,471), and NHL spread at a 5.5 total: +0.096 (1,895).
Every ML cell by total third is within +/-0.042.

The biggest real effect is big favorites laying points: CFB -400+ spread +0.118 (a heavy favorite that covers a big number tends to put up
points). That falls under the threshold; its interval reaches +0.166, which makes it "borderline", and by the pre-registered rule the
point estimate decides, so it counts as independent. NHL -400+ spread is +0.193, but on 42 games, which is under the 300-game floor.

### 3. Joint win rates (observed vs the independence product)

| Sport | fav ML + Over | fav ML + Under | dog ML + Over | dog ML + Under |
|---|---|---|---|---|
| CFB | 36.8% vs 36.2% | 36.3% vs 36.9% | 12.7% vs 13.3% | 14.2% vs 13.6% |
| NFL | 32.5% vs 32.2% | 34.1% vs 34.4% | 15.9% vs 16.2% | 17.6% vs 17.3% |
| NBA | 35.2% vs 34.6% | 33.0% vs 33.7% | 15.5% vs 16.1% | 16.3% vs 15.7% |
| NHL | 30.7% vs 30.8% | 30.6% vs 30.5% | 19.6% vs 19.5% | 19.2% vs 19.3% |
| CBB | 35.7% vs 35.9% | 35.6% vs 35.4% | 14.7% vs 14.5% | 14.1% vs 14.3% |

Spread: every combo is within 1.2 points of the product (largest: CFB favorite covers + Over 25.9% vs 24.6%; NHL puck-line favorite
covers + Over 20.8% vs 19.7%).

### 4. Risk of holding two bets

Variance of the 2-bet P/L over the independent case (1 unit each at the fair closing price; 1.00 = independent, 2.00 = one bet doubled):

| Sport | fav ML + Over | dog ML + Under | fav ML + Under | dog ML + Over | fav spread + Over | dog spread + Under |
|---|---|---|---|---|---|---|
| CFB | 1.022 | 1.014 | 0.978 | 0.986 | 1.050 | 1.050 |
| NFL | 1.000 | 1.009 | 1.000 | 0.991 | 0.963 | 0.963 |
| NBA | 1.015 | 1.021 | 0.985 | 0.979 | 0.998 | 0.998 |
| NHL | 0.996 | 0.998 | 1.004 | 1.002 | 1.042 | 1.042 |
| CBB | 0.988 | 0.994 | 1.012 | 1.006 | 0.981 | 0.981 |

The worst case anywhere with 300+ games is CFB -400+ favorite spread + Over at about 1.12 (phi +0.118). Holding a side and a total in the
same game adds at most about 5% to the variance of the two bets in any sport overall. Counting them as one position would treat
them as 100% more.

### 5. The rule for Kirk

- **Side (ML or spread) + same-game total: independent.** Size each on its own, in all five sports and all price bands. No measured
  pair reaches |phi| 0.15 (largest with 300+ games: CFB big-favorite spread + Over, +0.118). This holds for both directions: fav +
  Over and dog + Under are the same phi.
- **Team total + same-game total, same direction: one position** (phi +0.49 to +0.63, every sport). A team Under plus a game Under
  counts as one bet when sizing. Opposite directions (team Over + game Under) partly offset.
- **Not measured here:** team total vs side (for example JXST team total Under + DEL -2.5) was not in the pre-registration, so it gets
  no rule from this test. It needs its own pre-registered run.

### Limits

- Closing lines only. A bet placed earlier at a different number is a different pair; the result says the close prices the
  side-total link, not that an early bet has none.
- NFL is the thinnest sample (1,346 games; Pinnacle ML closes for about half of 2024-2026), and its intervals are about +/-0.055.
- Regular season only. Pushes and ties are dropped from each pair.
- Measured on results, not P/L at actual prices; the variance ratios use fair closing prices.
