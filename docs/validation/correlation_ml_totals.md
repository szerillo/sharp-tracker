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
