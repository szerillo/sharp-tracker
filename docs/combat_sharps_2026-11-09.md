# Combat sports: a longer Polymarket sharp feed, scored against Pinnacle (11/9)

Sean: "we only have Polymarket stuff for MMA for a few months; we should have a longer feed of sharp action."

## The feed
loggers/poly_combat.py: every settled two-way fight moneyline on Polymarket under the ufc, mma and boxing tags, and its full public trade
tape. 1,524 fights (UFC 1,206 from April 2024; boxing 312 from December 2023), 1,153 with $2k+ volume, 763,528 trades (one market capped at
20,000). The 11/2 history pull kept only fights whose market had an exact start time, which dropped most older UFC cards; this one takes
the date from the card and matches each fight to the Odds API by both surnames and a start within 2 days. The market's resolution is the
result. Kept locally (data/polymarket/combat, 21 MB); rebuild with `python3 loggers/poly_combat.py catalog` then `trades`.

## UFC (sharp/combat_sharps.py; 721 fights matched to Pinnacle, 36,143 wallets)
Pinnacle: the Odds API history (2022-25) plus the 2026 fight-night snapshots. Per wallet and fight, CLV = Pinnacle's no-vig close for the
fighter minus the price the wallet paid. Walk-forward: rank wallets (8+ fights, $2k+) by the t-stat of their CLV on fights before a cutoff,
follow the top 50 after it at their first fill ($100+) plus 1 point of follower cost.

| | Bets | Record | ROI | CLV vs Pinnacle close | Pinnacle moved toward the side after the fill |
|---|---|---|---|---|---|
| Every wallet, first fill per fight and side | 27,082 | 14785-12297 | -2.0% | -3.07 | -0.46 |
| First fills of $1k+ | 4,941 | 2790-2151 | -3.3% | -3.70 | -0.71 |
| Top 50, followed Jul-Dec 2025 (181 ranked) | 153 | 68-85 | -2.9% | **+2.02** | +0.54 |
| Bottom 50, same period | 216 | 124-92 | -7.8% | -4.61 | -1.36 |
| Top 50, followed Jan-May 2026 (420 ranked) | 86 | 40-46 | +4.1% | **+1.40** | +3.70 |
| Bottom 50 | 105 | 65-40 | +3.7% | -3.69 | -1.61 |
| Top 50, followed Jun-Nov 2026 (658 ranked) | 142 | 65-77 | -6.4% | **-1.25** | +0.75 |
| Bottom 50 | 124 | 80-44 | +7.5% | -2.61 | -0.61 |

(The first period, ranked on fights before 2025, had only 21 qualifying wallets, so its top and bottom were the same group; left out.)

Read:
- Polymarket's UFC crowd overpays by about 3 points against Pinnacle, and its big fills are no better than its small ones.
- The ranking does separate wallets: the top 50 beat the bottom 50 against Pinnacle's close by 6.6, 5.1 and 1.4 points, and Pinnacle moved
  toward the top group's side after they bet in all three periods (the bottom group's side moved away every time). So there are UFC bettors
  on Polymarket who are early.
- But the top group's own edge is too small and too unstable to follow: +2.0, +1.4, then -1.3 points, and results that lose in two of
  three periods. That matches the 11/2 finding (UFC skill does not carry from one period to the next well enough), now on two years and a
  sharper yardstick.
- Not a bet. Possible use: a top-wallet fill as a reason to hold a UFC position against it (a pushback signal), which the three-period
  gap supports better than following does. To be checked against the live MMA steam rule before anything changes.

## Boxing
Pinnacle for 2026 boxing pulled for the Polymarket fight dates (loggers/oddsapi_lines_at.py --markets h2h; 6 hours and 10 minutes out, 76
calls, 760 credits). Only 66 of Polymarket's 312 boxing fights have a Pinnacle price (Pinnacle does not hang most of the small Zuffa and
undercard fights Polymarket lists), and almost no wallet has bet 8+ of them, so there is no one to rank: 3,254 wallets, 2 that qualify.

| | Bets | Record | ROI | CLV vs Pinnacle close | Pinnacle moved toward the side after |
|---|---|---|---|---|---|
| Every wallet, first fill per fight and side | 888 | 629-259 | +4.0% | -2.21 | +0.03 |
| First fills of $1k+ | 159 | 123-36 | +1.3% | -2.16 | +0.02 |

Read: Polymarket's boxing money is mostly on favourites (629-259) and pays about 2 points over Pinnacle; Pinnacle does not move after it.
No sharp signal to be had from Polymarket in boxing.

### Boxing odds: Pinnacle against the US books, 2023-26 (sharp/boxing_test.py)
Results from the Wikipedia record tables (loggers/boxing_results.py): 2,320 fights with odds, 917 settled, 838 graded (540 with a
Pinnacle quote). The other 1,395 have no Wikipedia page for either fighter, mostly undercards.

**The full set is biased.** An unknown fighter usually gets a Wikipedia page only after he wins, so when only one fighter has a page,
upsets by unknowns are over-represented. On all 838 fights, Pinnacle's 55-70% favourites won only 51.7% (n 120) and the best US price
on dogs 7%+ over Pinnacle's fair returned +63% (65 bets, z 2.6). On the 207 fights where both fighters have a page, both go away:

| (both fighters have a page) | Bets | Record | ROI | z |
|---|---|---|---|---|
| Pinnacle 55-70% favourites: priced / won | 44 | | 62.3% / 63.6% | |
| Best US book 0%+ over Pinnacle's fair | 55 | 21-34 | +11.9% | +0.48 |
| Best US book 2%+ over Pinnacle's fair | 35 | 9-26 | +5.4% | -0.24 |
| Follow a Pinnacle move of 2+ pts at the best US book | 71 | 52-19 | +14.8% | +0.70 |
| Dogs +150 to +300 / +300 or longer | 46 / 127 | 11-35 / 13-114 | -28.0% / -31.2% | -1.23 / -1.33 |

Read: Pinnacle is calibrated on boxing, and nothing beats it: shopping the US books against Pinnacle, following Pinnacle's moves (the
lagging-book version lost even on the biased full set: 53 bets, -3.2%), and every price band. Longshots lose the usual amount. The clean sample is small, and widening it
would need a results source for undercard fights (BoxRec is not reachable). Not recommended.
