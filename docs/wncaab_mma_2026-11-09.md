# Women's college basketball and MMA: market tests (11/9)

## Women's college basketball
Odds API history (data/oddsapi/compact/wncaab.jsonl.gz): 1,434 games, November 2024 to April 2026, mostly the bigger games. **No Pinnacle
quotes at all**, only BetRivers, DK, FD, Caesars, BetOnline and LowVig, which is why the 11/5 market replay (anchored on Pinnacle's close)
came back empty for this sport. Results from ESPN (data/state/hist_schedule.json): 922 games graded with 3+ books at the close.

The line here is the median across the books (BetMGM left out); "open" is the median at the first snapshot. Bets at the best price at the
median line. Two seasons only.

| Test | Bets | Record | ROI | z | 2024-25 / 2025-26 |
|---|---|---|---|---|---|
| **Spread moved 1+ point open to close: follow at the close** | 119 | 75-44 | **+20.7%** | +2.37 | +7.9u / +16.7u |
| Same: fade | 119 | 44-75 | -28.9% | -3.29 | |
| Total moved 1+ point: follow | 111 | 63-48 | +7.7% | +0.87 | +3.0u / +5.6u |
| Total moved 1+ point: fade | 111 | 48-63 | -17.8% | -1.95 | |
| **Unders, all games** | 799 | 385-414 | **-7.9%** | -2.35 | -23.1u / -39.8u |
| Unders by closing-total quintile | 159-200 each | | -0.3% to -13.1% | | every quintile negative |
| Dogs +7 to +10 | 91 | 53-38 | +11.4% | +1.14 | +0.6u / +9.8u |
| Other dog bands, home teams | 96-759 | | -0.7% to -6.1% | | |

Read: the closing number does not fully catch up to the information behind a move in this market (a thin one, with no Pinnacle to set
it). The move-follow result is the strongest single cell found tonight outside the props: 119 bets, both seasons positive, and the fade
loses by more than the vig, which is what a real signal looks like. Moves of 2+ points have only 25-30 bets.
Overs: unders lose in every total band in both seasons, so the books shade the women's totals low.

Both are leads, not rules: two seasons, about a sixth of the games, and the "open" is our first snapshot rather than the true opener.
**Next:** the live price feed does not carry women's college basketball. Adding it (US books only, the same snapshots as the men's) would
let both run as paper rules this season. Cost is in the price feed's Odds API calls; to be sized before it is switched on.

## MMA (from the 11/5 market replay, data/research/market_replay.json; 2022-26, Pinnacle anchored)
- **Following a large Pinnacle moneyline move (6+ points open to close), at the close:** 237 fights, 161-76, +7.3%, but positive in only
  2 of 5 years (2022 +18.5%, 2024 +15.9%; 2023, 2025 and 2026 flat). Toward the favourite: 189 fights, +6.6%, 4 of 5 years positive.
- **The same side at its opening price:** 119 fights, 76-43, +19.7%. The money is made before the move, not after it.
- **Underdogs against 70-89% favourites** lose 20-45%: the long dogs are overpriced.
- Read: the MMA close is about right (beating it by 8-9 points of CLV still only breaks even at the close). The edge is in getting the
  side before the move, which is what a sharp-action read is for. That is the thread to pull for MMA: how early the BetMMA steam and the
  Polymarket accounts get to the side that Pinnacle later moves toward (data/state/mma_steam.json is the live feed).
