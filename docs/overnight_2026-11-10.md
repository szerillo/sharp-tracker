# Overnight tests, 11/10 (5 AM to 11 AM ET)

Sean: "run anything else that you have ever possibly wanted to run overnight." No Odds API credits were used. Each section: what was
tested, the result, and what it means for the board.

## 1. Kalshi makers on the full settled tape (sharp/maker_history.py)
The 11/10 maker test had 11 days. This is every pregame trade on Kalshi's settled game markets from Aug 24 to Oct 29: 6.95 million
fills, 1,276 games (NFL, college football, NBA, NHL, soccer; MLB tickers did not match the schedule and are left out), $607M put up by
makers. Scored against Kalshi's own close (no Pinnacle in this history) and on results. Maker fee applied to every row.

| | Risked | vs Kalshi's close | After the maker fee | Settled, after fee |
|---|---|---|---|---|
| Every maker fill | $607M | +0.10c (z 3.1) | **-0.27c** | -1.36% (z -1.2) |
| Last hour, fills under $1k | $144M | +0.44c (z 12.6) | **+0.06c** | -2.03% |
| Fills under $100 | $109M | +0.40c | +0.03c | -0.40% |
| Fills of $10k+ | $113M | -0.49c (z -4.4) | -0.86c | +0.83% |
| More than 24 hours out | $59M | -0.73c (z -4.1) | -1.07c | +0.76% |
| Last hour | $286M | +0.33c (z 9.5) | -0.06c | -1.60% |

Read: over three months the picture is the same shape as the 11-day test and smaller. Makers on Kalshi earn about a tenth of a cent
before the fee and lose a quarter of a cent after it. The best slice (small fills in the last hour) is break-even after the fee. Large
fills and early fills are the informed ones. **Quoting Kalshi passively is not a business at retail fees.** What survives from the
11-day test is only the selective version (a bid 1c under Pinnacle's fair, +0.45c after fee), which this history cannot check because it
has no Pinnacle price at the time of each fill. Novig, with no fee, remains the venue.

## 2. The open: who leads, and price gaps against Pinnacle (sharp/open_lead.py)
Odds API history 2020-26, 69,549 games with results. The open = a game's first snapshot with Pinnacle and 2+ US books.

**Spreads and totals: Pinnacle's opening number is no better than the US books'.** Taking a bettable US book's number that is half a
point better than Pinnacle's at the open: 25,526 spread bets, -3.0% (z -5.0), 0 of 7 seasons positive; 30,224 total bets, -2.6%
(z -4.8). A full point better: -1.8% and -3.2%. The same later in the week: negative in every time bucket. When the two disagree at the
open each moves about halfway to the other. So a number that is off Pinnacle's is not a bet, at the open or later. (This is why the
line-outlier scan found nothing.)

**Moneylines: a US price above Pinnacle's fair is worth what it says.** Best price at FD, Caesars, BetRivers or DK, price +200 or shorter:

| First time the gap shows | EV 2%+ | EV 4%+ | EV 7%+ |
|---|---|---|---|
| At the open | 1,991 bets, +5.2% (z 1.9), 5 of 7 seasons; EV at Pinnacle's close +5.7% | 533, +8.8% (z 1.6), close +7.5% | 107, -10.2% |
| Later, 6+ hours out | 1,178, about 0% | 219, +8.3% | 58, -11.1% |
| Later, inside 6 hours | 2,075, +0.2% | 640, +5.4% (z 1.2) | 238, +13.0% (z 1.75) |

**The live stale-book lean, checked against history.** Its condition is a price gap right after Pinnacle moved 1+ point toward the side.
In history, at a US book: gap 2%+ -2.7% on 1,575 (2 of 7 seasons), gap 4%+ **+12.5% on 415 (z 2.2, 6 of 7 seasons)**, gap 7%+ +14.4% on
147. Live it is 20-43 (-32.5%), and 47 of the 63 were on Novig, 10 on Polymarket, 6 at a sportsbook; 53 of 63 had a gap under 4%.
The live rule is firing on the two things history does not support: gaps of 2-4%, and exchange quotes. A cheap exchange ask after a
Pinnacle move is someone informed selling, not a stale book.

Proposed (not changed; a rule change is Sean's call): stale-book lean = sportsbooks only (FD, Caesars, BetRivers, DK), gap 4%+. The
exchange version stops.

## 3. Locks and ladder violations on our tape (sharp/arb_scan.py)
Every pregame pull of Kalshi, Novig and Polymarket game markets and team totals, Oct 30 to Nov 10 (2.1 million market pulls).
- **Kalshi ladders: no violations.** Not once was an easier spread or total line offered under the bid of a harder one after fees.
- **Cross-venue locks are rare and small.** About 200 episodes in 11 days across all sports, typically 1 to 2 cents after Kalshi's fee
  (Novig + Polymarket NHL moneylines 43 episodes at 0.5c; Kalshi + Novig NBA spreads 28 at 2c; Kalshi + Polymarket NBA moneylines 8 at
  4c). Most last one pull, and the two quotes are up to 3 minutes apart, so many are a stale quote and not a real lock. One college
  football team total showed a 40c "lock" on 247 pulls: a line mismatch on one game, not money.
- Read: nothing to build. The exchanges are consistent with each other at our pull speed.

## 4. Tie prices on Kalshi's half, quarter and period moneylines
Kalshi lists the tie as its own contract. Last tight quote in the 6 hours before the start against the tie rate in our linescores:

| Market | Games | Kalshi tie bid / ask | History |
|---|---|---|---|
| NFL first half | 28 | 7.8c / 8.9c | 7.2% of 1,799 |
| NFL first quarter | 28 | 20.5c / 21.6c | 20.7% |
| College football first half | 91 | 6.6c / 7.8c | 6.3% of 6,007 |
| NBA first half | 83 | 2.9c / 4.3c | 3.2% of 4,119 |
| NBA first quarter | 82 | 3.4c / 5.8c | 4.8% |
| College basketball first half | 55 | 1.6c / 3.9c | 3.5% of 18,923 |
| NHL first period | 72 | 31.8c / 33.3c | 34.3% of 4,455 |

Read: priced right. The history rate sits inside or within a cent of the quote everywhere, and the fee is larger than any gap. The
closest thing to a bet is the NHL first-period tie at the ask (33.3c against 34.3%), which the 1.6c fee erases. No edge in ties.
