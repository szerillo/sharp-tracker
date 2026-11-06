# Stale US books vs Pinnacle on our own tape, 11/6/2026

Script `sharp/stale_books.py`, results `data/research/stale_books.json`. Tape: our 20-minute snapshots 10/29-11/6 (NBA, NHL, NFL, CFB,
CBB), Pinnacle plus DK, FD, Caesars, BetRivers, Fanatics, theScore and Kalshi (at the ask plus fee). At every snapshot, Pinnacle's no-vig
fair for each side (moneyline; spreads and totals at Pinnacle's number) against every book at the same number; the first time a
(game, market, side, book) offers 2%+ expected value is the bet. Graded at the book's price.

## Result
- 256 opportunities in 8 days (124 distinct game-market-sides). Flat ROI -7.8% (75-181), but these are mostly moneyline dogs (mean price
  5.0). Against Pinnacle's CLOSING fair the prices were still +3.3% EV on average, and results matched the close exactly: 42 wins vs 42.1
  expected (one bet per game). The negative ROI is longshot variance, not a broken signal.
- The book lagging a Pinnacle move toward the side: 71 bets, +15.8% ROI, +4.0% EV at the close, 30 wins vs 26.4 expected. The book simply
  disagreeing with Pinnacle (no move): -13.0% ROI, still +3.9% EV at the close.
- By book, after a Pinnacle move: FD 5-4, Caesars 5-3, DK 3-5 (small); theScore and Fanatics offer the most stale prices overall.
- Edges of 7%+ at the bet: +12.6% ROI, +6.6% EV at close. Most opportunities are 6h+ before the start (189 of 256).

## Reading
Price edges against Pinnacle's fair are real expected value (they survive to the close) and this is the most durable edge available:
it does not depend on a pattern repeating. Two cautions: most of the volume is long-priced moneylines, so the swings are large, and
books limit accounts that take these prices. Next: run it live as a paper lean (book lagging a Pinnacle move, edge 2%+, price under 3.0)
and grade forward; widen to the 5-minute tape for Pinnacle and Kalshi, where the move timing is sharper.
