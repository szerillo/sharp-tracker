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

## 5. Novig makers on the whole public tape, every market type (sharp/novig_maker_history.py)
**The strongest result of the night.** Novig publishes every trade with both sides marked (taker and maker). This is every pregame maker
fill on a settled two-outcome market from Aug 3 to Nov 6: 8.48 million fills on 7,604 events, $744M put up by makers, $7.75M a day.
Settled results, no fee (Novig charges none pregame), z clustered by event.

| | Maker money per day | Settled ROI | vs Novig's close |
|---|---|---|---|
| **Every maker fill** | $7.75M | **+1.90% (z 3.4)** | +0.21c |
| August / September / October | | +1.55% / +1.80% / +2.15% (each z 2.0+) | |
| Moneylines | $2.38M | +2.75% (z 2.3) | +0.16c |
| Spreads | $1.72M | +2.80% (z 2.4) | +0.18c |
| Totals | $1.45M | +0.32% | +0.16c |
| Player and other props | $1.91M | +1.56% (z 3.3) | +0.34c |
| Team totals | $38k | +3.70% (z 2.0) | +0.70c |
| First-half spreads | $40k | +8.30% (z 2.3) | +0.85c |
| First-half totals | $54k | +3.50% | +0.62c |
| Soccer three-way moneylines | $115k | -6.38% (z -1.9) | +0.01c |

By league and market (settled ROI): NFL moneyline +8.3% (z 2.1), NFL spread +6.2% (z 2.0), NFL first-half spread +17.9%; MLB spread
+4.6% (z 2.4), MLB team total +6.8% (z 2.6), MLB props +1.4% (z 2.7); NHL props +3.9% (z 3.0); NBA props +3.0% (z 2.5); UFC props +9.1%
(z 2.8); tennis props +6.1% (z 2.2). Losing: NBA moneyline -5.6% (z -1.8, the same sign as the 11-day test), soccer spreads -8.4%, UFC
moneyline -3.0%. By size: every size is positive, including $10k+ fills (+11.0%, z 2.2, on $34M). By time: last hour +2.2%, 1 to 6
hours +2.4%, 24 hours out +0.9%.

Props by type (settled ROI, $ of maker money a day): MLB pitcher strikeouts +2.4% (z 2.6, $205k), MLB home runs +0.8% ($203k), MLB
first-inning total +2.1% ($146k); NFL first touchdown +1.1% (z 1.9, $166k), receptions +1.4% ($90k), receiving yards +1.0% ($89k),
passing yards -3.9%; NBA threes +6.8% (z 2.2, $28k), points-rebounds-assists +7.1% (z 2.0), assists +4.2%, points +0.8% ($51k),
rebounds -0.2%. By league, game lines only: NFL +5.6% (z 2.4), MLB +2.2%, college football +1.2%, NHL +1.9%, tennis +1.2%, NBA -3.5%
(z -2.1, October only), soccer -5.5% (z -2.2).

Read:
- On Novig the resting side has made about 1.9% of the money it put up, in each of the three months, across game lines and props.
  That is about $147,000 a day earned by makers as a group, and it is the mirror of what takers there lose. On Kalshi over the same
  months the makers lost 1.4% after the fee (section 1).
- **This changes how to use Novig.** Every bet we take there pays about 2% to someone resting. The same bet rested instead earns it.
  It is the long-sample confirmation of the rest-or-take pattern in our own log.
- The thin, wide markets (team totals, first-half lines) pay makers more per dollar (+3.7% to +8.3%) but only $40-55k a day trades in
  each. Props are the size: $1.9M a day at +1.6%.
- Not tested here: how much of this a new, small maker would get (queue position), and who the makers are. It is an average over all
  resting orders, including Novig's own liquidity providers, who are faster than we are.

## 6. The sharp list on the last 60 days, scored at Pinnacle's close (sharp/poly_pinnacle.py, POLY_CUT=2026-09-10)
The Polymarket trade history was re-pulled (51,555 markets, 23.5 million fills). Accounts ranked on everything before Sep 10 (30+ fills on
15+ games), then followed from Sep 10 to Nov 9 **at their own fill prices**.

| Followed Sep 10 to Nov 9 | Fills | Accounts | ROI | CLV vs Pinnacle's close |
|---|---|---|---|---|
| Top 200 by Polymarket CLV (the live method) | 9,489 | 57 | +6.7% | **+0.39** |
| Top 200 by Pinnacle CLV | 10,653 | 46 | +5.7% | +0.34 |
| In both top 200s | 8,461 | 30 | +7.9% | +0.41 |
| Top 200 by past ROI | 728 | 36 | -10.1% | -0.23 |
| Every qualified account | 64,056 | 604 | -1.7% | -0.03 |
| Bottom 200 by Pinnacle CLV | 570 | 30 | -0.8% | -1.06 |

Inside the live method's top 200: fills already priced under Pinnacle's fair +7.6% (CLV +2.30) against +5.5% (CLV -1.96) for fills over
it; with Pinnacle's move +9.7% (CLV +1.23), against it +2.9% (-0.52); moneylines, spreads and totals about equal (+6.1 / +6.2 / +7.3%);
6+ hours out +7.8% (CLV +0.61), last hour +3.8% (-0.07). By sport: CFB +9.6%, NFL +5.6%, NBA +4.1%, NHL +16.8% (442 fills).

Read:
- **The list is not broken.** On the most recent 60 days the same accounts still beat Pinnacle's close by 0.4 points and made 6.7% at
  the prices they got. Ranking by ROI still does not work, and the two CLV rankings still agree.
- **Our flags are not getting the accounts' price.** Live, Sharp A is +0.06 against Pinnacle where the accounts themselves are +0.39,
  and the live record (45-69) is well below what their own fills returned. The gap between their fill and our entry is most of the edge.
  That fits everything else tonight: the value is in the price they rested or took early, not in the price left afterwards.
- What to do with it: see the follower test below. Their price is not ours to get, by taking or by resting.

**What a follower gets.** A flag = the first fill by a top-200 account on a game, market and side (2,127 flags, Sep 10 to Nov 9).

| Entry | Flags | CLV vs Pinnacle's close | ROI |
|---|---|---|---|
| At the account's own price | 2,127 | **+0.74** (z 9.8) | +2.6% |
| Taking 5 minutes later (mid + 1c), same flags | 1,354 | **-0.44** (z -4.6) | -0.5% |
| Taking 30 minutes later | 1,354 | -0.61 (z -6.7) | -0.9% |

**Resting a bid at the account's price.** Did the market trade back to their price 5+ minutes later?

| | Flags | At their price: CLV, ROI | |
|---|---|---|---|
| Came back (the bid fills) | 1,579 (74%) | +0.18, **-2.7%** | what a resting follower gets |
| Never came back (no fill) | 548 (26%) | +2.36, **+18.0%** (z 3.8) | all of the edge; taking these 5 minutes later was +0.50 CLV, +9.8% (z 1.6) on 315 |

Read:
- The accounts' edge is real and it is in about a quarter of their bets: the ones the market never comes back on. A bid rested at their
  price fills on the other three quarters, which are worth nothing. A taker 5 minutes later pays more than the whole edge.
- **This goes against resting on sharp flags.** In our own log, sharp flags whose price came back did better (+9.5% on 33 against
  -21.7% on 72). On 2,127 flags from the full tape it is the other way round. The log split was small-sample noise for sharps. The
  board still shows a rest price on sharp flags and the forward table will keep counting, but the evidence now says a sharp flag that
  comes back to you is the weak kind.
- So the sharp list, as a follow signal, has no entry that captures it in these 60 days: not taking late, not resting. What is left
  to test is speed (entering within seconds of the fill) and knowing in advance which quarter runs. Flags stay on paper.
- Polymarket's public feed does not separate resting fills from taking fills (the taker-only switch returns the same rows), so ranking
  wallets by their resting fills is not possible from this data.

## 7. Smaller checks
- **Does CLV predict results in our own log?** 1,448 graded rows with a Pinnacle close: the slope of (won minus price) on CLV is 0.22
  per point, where an efficient market gives about 1. With this sample the error on that slope is about 0.5, so it says nothing either
  way. CLV stays the yardstick for sharps; the rest-or-take forward test is what will settle the pattern in section 2 of the review.
- **Systems at the price we get**: not rerun. sharp/rule_replay.py already grades every replayable rule at Pinnacle's close and at the best
  US book, with the open-to-close move (pushback doc, 11/9).
- **A scheduled weekly recheck also ran overnight** (docs/weekly_recheck_2026-11-10.md). Its recommendations (cfb_road_dog_low_total and
  nhl_pl_dog_bigml down to paper, mnf_1h and cfb_wind14 down to C, nba_momentum and stale_book retired or reworked) are Sean's calls.

## Built overnight
- sharp/offers_grade.py: marks which paper offers would have filled (a trade on the tape after the offer where someone sold at or under
  our bid) and how filled and unfilled offers closed against Pinnacle. The 5-minute trade job now also polls every Novig market with an
  open offer, props included. The board's offers section shows the record once offers have started.
- Trade tape for team totals, props and period lines (data/kalshi/trades5_soft, data/novig/trades5_soft) is landing.
