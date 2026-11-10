# Overnight tests, 11/10 (5 AM to 11 AM ET)

Sean: "run anything else that you have ever possibly wanted to run overnight." No Odds API credits were used. Each section: what was
tested, the result, and what it means for the board.

## Bottom line
1. **Novig pays the resting side; Kalshi does not.** Novig's makers earned 1.9% on $744M over three months, positive every month and
   in every market type but soccer (section 5). Against Pinnacle at the moment of the fill, a bid 1c under fair keeps about 0.8c in
   every market type in the last hour, and 2 to 3c bids keep more everywhere except moneylines (section 8). Kalshi's makers lost 1.4%
   after the maker fee over the same months (section 1).
2. **The sharp list is real and cannot be followed.** The top accounts beat Pinnacle's close by 0.74 at their own price in the last
   60 days, buying at about the mid. A follower who crosses the spread 5 minutes later is between -0.44 and +0.06 depending on the
   spread, which is where the live flags sit (+0.06); a bid rested at their price fills on the three quarters of flags that are worth
   nothing; no filter at 5 minutes finds the quarter that runs (section 6). Flags stay on paper.
3. **Price gaps against Pinnacle hold on moneylines at sportsbooks, not on numbers and not on exchanges.** A US book's moneyline 4%+
   over Pinnacle's fair has paid at the open and later; a spread or total half a point better than Pinnacle's loses the juice. The
   live stale-book lean has been firing on the two cases history does not support (section 2).
4. **Nothing in locks, ladders or tie prices** (sections 3 and 4).

Decisions for Sean: (a) the stale-book lean to sportsbooks only at a 4%+ gap; (b) the weekly recheck's tier moves
(docs/weekly_recheck_2026-11-10.md); (c) whether to set Novig keys so a paper quoter can become a real one. Nothing was changed on
those. Fixed overnight: the board check's "1 missing" (cfb_road_dog_low_total, SJSU @ AFA) was the board pointing at a duplicate fill the
ledger had already voided; sharp/systems.py now re-points to the live fill. One bet, counted once, as before.

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

Checked: in Novig's file the two sides of a trade carry different outcomes and their costs add up to the payout (66,960 of 66,960 trades
on Oct 20), so a MAKER row is the resting side's own position and price.

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
| Taking 1 minute later (mid + 1c), same flags | 1,285 | -0.22 (z -2.3) | +1.9% |
| Taking 5 minutes later (mid + 1c) | 1,354 | **-0.44** (z -4.6) | -0.5% |
| Taking 30 minutes later (mid + 1c) | 1,354 | -0.61 (z -6.7) | -0.9% |

The cost to cross is the whole story. One minute after their fill the mid is still at their price (CLV at the mid +0.78): they are
buying at about the middle of the market, and a follower has to pay the spread to get in. With 1c to cross the follower is at -0.2 to
-0.6; with half a cent (a 1c-wide market) it is about +0.3 at one minute and +0.06 at five, **which is exactly what the live Sharp A
flags show (+0.06)**. The live record is not bad luck on a working signal; it is the signal after the cost of entry.

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
- **Which flags run cannot be told at 5 minutes.** For a taker at 5 minutes, CLV is negative in every split tried: by how far the
  price had already moved (fell 1c+: +0.25 on 49; within 1c: -0.38 on 1,120; up 1 to 2c: -0.78; up 2c+: -1.45), one account (-0.43) or
  two or more (-0.65), money in the first 5 minutes (under $1k -0.29, $1k to $10k -0.57, $10k+ -1.04), time to the start (24h+ -0.15,
  6 to 24h -0.52, 1 to 6h -0.59, last hour -0.67), and every sport (NFL -0.17 to NBA -0.66). More accounts and more money mean a
  bigger move before a follower gets there, not a better bet.
- So the sharp list, as a follow signal, has no entry that captures it in these 60 days: not taking late, not resting, not filtering.
  What is left is speed (seconds, which needs an order sent by machine). Flags stay on paper.
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

## 8. Novig makers against Pinnacle at the moment of each fill, every market type (sharp/novig_maker_select.py)
Section 5 is three months of settled results. This is the selective version: every Novig maker fill from Oct 30 to Nov 9 on a market in
our ticks (3.2 million fills; 1.03 million where Pinnacle quoted the same line at that moment), priced against Pinnacle's no-vig fair at
the fill and at the close. These are real fills, with size, props and team totals included.

**Every maker fill** (cents per contract at the close; maker money per day): game moneylines +0.06c ($3.79M), spreads +0.16c ($1.78M),
totals +0.41c ($957k), period lines +0.83c ($67k), team totals +0.87c ($45k), player props +0.06c ($1.26M).

**A bid resting under Pinnacle's fair, paid at our bid** (kept at the close; money filled per day at that level or better; whole pool):

| Market | 1c under | 2c under | 3c under |
|---|---|---|---|
| Game moneylines | +0.17c on $558k a day | -0.18c | -0.87c |
| Game spreads | **+0.84c** on $411k ($5,600 a day) | +1.79c on $107k | +2.94c on $41k |
| Game totals | **+0.71c** on $335k ($3,800) | +1.50c on $135k | +2.04c on $35k |
| Period lines | +0.89c on $34k | +1.81c on $17k | +2.64c on $7k |
| Team totals | +0.60c on $23k | +1.47c on $14k | +2.11c on $7k |
| Player props | +0.14c on $455k | +0.70c on $266k ($3,800) | **+1.31c** on $150k ($3,900) |

**By time (1c under).** Last hour: moneylines +0.86c, spreads +0.87c, totals +0.79c, props +0.66c, team totals +0.93c, period lines
+0.95c: about 0.8c in every market type, on about $745k a day in total. Earlier than that it depends on the market: spreads and totals
hold (+0.4 to +1.4c), moneylines do not (6 to 24 hours out -0.70c), props do not at 1c (6 to 24 hours -0.19c, more than a day -0.74c)
but do at 2c and 3c (+0.5 and +1.0c).

Read:
- On Novig a patient bid is paid for in every market type, and outside moneylines asking for more gets more: fills 2c and 3c under
  fair keep about two thirds of the gap. (On Kalshi a 3c fill lost 2c.) Moneylines are the exception: the people who sell a moneyline
  2c under Pinnacle know something.
- Sizes are real but not large. The whole last-hour pool is about $15,000 a day of expected value for everyone resting 1c under fair
  on Novig. Team totals and period lines are the richest per dollar and the thinnest ($20-35k a day filled at 1c under).
- Spreads and totals outside the last hour are scored only when Pinnacle still has that line at the close (a third to two thirds of
  the money), so those rows flatter; the last-hour rows are nearly complete and are the ones to trust.
- What it supports for the paper quoter: Novig only; spreads, totals, team totals, period lines at 1 to 2c under fair at any time
  inside a day; props at 2c or more, or 1c in the last hour; moneylines only in the last hour.
