# Research log: what was tested, what it showed, where it lives

Sean 11/10: "Keep an updated log so we know what worked and there aren't redundancies." One line per test, newest work at the top
of each section. Check here before starting a test; add a line when one finishes. A verdict here is a pointer: the numbers and method
are in the linked doc. Where a line says "see doc", the verdict has not been re-read into this log yet.

Verdicts: LIVE (on the board with units), PAPER (logging, 0 units), DEAD (tested, nothing there, do not re-run without new data),
OPEN (running or waiting on data).

## 1. Market making and resting offers

| Date | Test | Result | Verdict | Doc / script |
|---|---|---|---|---|
| 11/10 | Parlay last-price shortcut vs exact trade-by-trade scoring (300 settled two- and three-leg parlays) | Tape volume equals listed volume; stakes agree within 6% ($56,629 vs $53,298); taker was on NO for 10.7% of contracts. The shortcut is not what produced the 16.3% | Shortcut is acceptable; the 16.3% was a run of results | sharp/parlay_price_check.py, data/research/parlay_price_check.json |
| 11/10 | **Parlay verdict** | Makers as a whole break even (-0.8% and -0.3% in two samples, 47 days). Two- and three-leg parlays keep a few percent (3.6% to 6.4% outside the one 16.3% fortnight), matching the roughly 2% markup over the legs on the live log. 6+ legs and 50c+ lose in both samples | PAPER. Not dead, not worth same-game correlation work yet (same-game was $0.5M a sample and flipped sign). Revisit when the live log has 1,000+ settled | this log |
| 11/10 | Parlay price vs its legs, live (two- and three-leg Kalshi parlays off the trade feed) | First 25: parlays with legs in different games traded about 2% over the product of the legs' mids; same-game about 68% over (correlated legs, so not comparable). Conflicts with the 16.3% hold below, so results will decide | PAPER, started 11/10 | sharp/parlay_live.py, sharp/parlay_grade.py, data/state/parlays_record.json |
| 11/10 | Kalshi parlay makers, Sept 25 to Oct 26 (older sample, 584,635 parlays, $50.4M staked; the run was cut off before reaching mid-September) | All -0.3% of stakes. 2 legs +3.6% (z 1.2), 3 legs +5.2% (z 2.3), 4-5 legs +3.2% (z 0.9), 6+ legs -11.2% (z -1.8), priced 50c+ -7.3% (z -4.2), same game -7.1% | The 16.3% on two legs did not repeat. Short parlays: a few percent at most. Long parlays and 50c+ lose in both samples | data/research/kalshi_parlays_older.json |
| 11/10 | Kalshi parlay makers, Oct 27 to Nov 10 (435,098 parlays, $35.7M staked) | All -0.8% of stakes. 2 legs +16.3% (z 3.7), 3 legs +6.4% (z 2.3), 4-5 legs 0.0%, 6+ legs -21.7%, priced 50c+ -5.6% | Two and three legs only; needs the older sample and the live log | docs/maker_playbook.md, sharp/kalshi_parlays.py |
| 11/10 | Novig parlays from the public file | Volume only (118,336 parlays on Oct 26, $2.47M taker stakes); no legs or results, so maker profit cannot be measured | DEAD (data limit) | sharp/novig_maker_history.py (parlay mode) |
| 11/10 | ProphetX quotes vs Pinnacle | Props sit 1.8 to 2.9c under fair (Novig 1.0 to 1.3c). No trade feed found; maker fee unconfirmed (assumed 2% of net profit) | PAPER, quotes pulled every 20 min | loggers/prophetx.py, docs/overnight_2026-11-10.md |
| 11/10 | Paper offers: bid 1c under Pinnacle fair on Novig lines (props 2c, moneylines last hour only), 2c on Kalshi and ProphetX | Logging since 11/10; first fill record due 11/11 | PAPER | sharp/offers_live.py, sharp/offers_grade.py, board "Offers to rest" |
| 11/10 | Novig makers, three months, $744M | +1.9% (z 3.4), positive every month, every market type but soccer; 1c-under bids keep about 0.8c in the last hour | Supports resting on Novig | docs/overnight_2026-11-10.md sections 5, 8 |
| 11/10 | Kalshi makers, two months | -1.4% after the maker fee | DEAD for plain resting on Kalshi game lines | docs/overnight_2026-11-10.md section 1 |
| 11/10 | Kalshi and Novig maker fills vs Pinnacle, 11 days, 1.08M trades | A real maker edge of about 1% of money risked, unhedged; Novig the better venue (no fee). Day-to-day swing is many times the expected profit | Basis for the offer rules; a volume business, not a daily compounding profit | docs/maker_2026-11-10.md, sharp/maker_test.py |
| 11/10 | Rest or take (our own bets: rest a bid instead of taking) | Table on the board | PAPER | sharp/bet_log.py (rest fields) |
| 11/10 | "Rest at the sharps' own price" | Retracted after the follower test | DEAD | sharp/poly_pinnacle.py |
| 11/10 | Cross-venue locks and ladder violations | About 200 episodes in 11 days, 1 to 2c after Kalshi's fee, most last one pull and many are stale quotes | DEAD | sharp/arb_scan.py, data/research/arb_scan.json |

## 2. Sharp accounts and order flow

| Date | Test | Result | Verdict | Doc / script |
|---|---|---|---|---|
| 11/10 | Polymarket sharp list at its own price vs following it | Real at their price (+0.74 CLV), not followable at ours | Flags PAPER from 11/10 10:00 UTC (0 units), keep logging 1-2 months per Sean | docs/overnight_2026-11-10.md, docs/review_2026-11-10.md |
| 11/10 | Fade moves the sharps did not follow | About break-even once the mover's price is used (first read of +15% was a bug) | DEAD | sharp/unfollowed_fade.py |
| 11/10 | Opening moves, open lead, open momentum | Nothing | DEAD | sharp/open_lead.py, sharp/open_momentum.py |
| 11/9 | Sharp flags: what the live losses are made of | 72-94, -18.9%; spreads and totals carry it; not a follower-price problem | Led to paper-only | docs/sharp_flags_2026-11-09.md |
| 11/9 | Pushback timing (when opposition arrives, when to lock in) | Held from the start: 76-128, -32.4%. A Kalshi move against: 6-11, -35.2% on the tracker, and about -20% to -30% ROI at every horizon in Kalshi history. Sharp accounts or big money against did not hurt (small n) | HOLD rule kept as is; a Kalshi move against is the signal that matters | docs/pushback_2026-11-09.md |
| 11/9 | Combat sports sharp feed (UFC, boxing on Polymarket, 1,524 fights) | No edge in boxing; MMA multi-year backtests showed nothing new | DEAD (boxing); MMA steam stays tier C | docs/combat_sharps_2026-11-09.md |
| 11/9 | CLV audit | Sharp A "standout" was a soccer three-way devig bug; fixed, no measurable edge | Fixed | docs/clv_2026-11-09.md |
| 11/8 | Heavy one-way big money as opposition | Following it is flat to negative on both venues; biggest late Novig money loses (-18.4%, one cell of 48) | DEAD as a signal either way | docs/flow_big_oneway_2026-11-08.md |
| 11/6 | System bets vs Polymarket sharp opposition | Noise at n=139 | DEAD until more data | docs/list_items_2026-11-06.md |
| 11/5 | Polymarket accounts re-scored at Pinnacle's close | Top 200 by Polymarket CLV: +6.8% held out (z about 5.5). Ranking by Pinnacle CLV is no better; ranking by past ROI is -15.2%. Fills inside Pinnacle's fair +9.3% | Keep the live ranking method | docs/poly_pinnacle_2026-11-05.md |
| 11/2 | Big vs small money round 3 (bigger fills, busier markets, Polymarket) | Busy-market versions failed holdout (Novig $100k+ -3%, Polymarket -9% to -12%). One lean left: Kalshi $500+ vs small money at T-15m on $25k+ markets (+14.6% holdout, n 81, z 1.3). Account skill on Polymarket persists | DEAD except the Kalshi lean (watch); source of the sharp-account work | docs/flow_volume_2026-11-02.md |
| 10/31 | Big vs small money on Kalshi and Novig | Most of the first edge was the favorite effect; calibrated, nothing clears z 2 | Watch only, no fills | docs/flow_split_2026-10-31.md |
| 10/30 | Does big money on Novig win? | Positions are not public; only fill size testable. Big takers are negative by about the spread in every sport; UFC $5k+ fills +18.2% on 133 fills (z 1.3) | DEAD (UFC top bucket too small to act on) | docs/novig_big_money_2026-10-30.md |
| 10/29 | Exchange signal audit (Novig tape, Kalshi tape): calibration by time, favorite/dog drift | Baseline tables for every later exchange test; no standalone rule came from it | Reference | docs/exchange_signals_audit_2026-10-29.md |

## 3. Stale books, price gaps, line shopping

| Date | Test | Result | Verdict | Doc / script |
|---|---|---|---|---|
| 11/10 | Sportsbook moneyline 4%+ over Pinnacle fair (FD, Caesars, DK) | Gaps hold | PAPER as stale_book_sb4 | sharp/stale_live.py, docs/overnight_2026-11-10.md |
| 11/9 | Outlier books (one book off, 2+ agree with Pinnacle), all props and game lines | Props lose 2-7% everywhere except two extreme cells: NFL rushing yards 4.5-7 yds off (54-28, +24.1%, 4 of 4 seasons) and NBA points unders 15%+ off (111-54, +18.7%). Game lines, about 100,000 games: nothing | DEAD in general; the two extreme cells are at most paper (rare, losing neighbours) | docs/outlier_books_2026-11-09.md |
| 11/9 | Game total moved, props did not | No edge in the 3-hour or 6-hour window; stale props lose about the vig | DEAD | docs/stale_total_props_2026-11-09.md |
| 11/8 | NFL player props, 12 markets, 10 min before kickoff | Almost nothing | DEAD at 10 minutes | docs/nfl_props_2026-11-08.md |
| 11/7 | Props price-gap thresholds and devig | NBA threes unders: 2%+ gap +7.8%, 4%+ +11.6%, 4 of 4 seasons | LIVE, tier C | docs/props_grid_2026-11-07.md, sharp/props_live.py |
| 11/6 | Player props first pass | NBA threes unders at a 2%+ gap: 2453-2198, +7.9%, every season | Source of the rule above | docs/props_2026-11-06.md |
| 11/6 | Stale US books on our tape | 256 spots in 8 days, flat ROI -7.8% (mostly moneyline dogs); see doc | Original stale lean stays PAPER | docs/stale_books_2026-11-06.md |
| 11/6 | Line shopping across venues | Novig best price on 73% of sides, -0.5% EV vs Pinnacle fair; books -4.4%; Kalshi -4.8% after fee | Take on Novig first | docs/derivatives_round2_2026-11-06.md |
| 11/1 | Do your books lag Pinnacle? | DK and FD follow about half of Pinnacle moves in 15 min; exchange lag is not buyable | DEAD as a chase | docs/catchup_2026-11-01.md |

## 4. Systems, derivatives, weather

| Date | Test | Result | Verdict | Doc / script |
|---|---|---|---|---|
| 11/10 | Weekly rule recheck | Recommended: cfb_road_dog_low_total to paper, mnf_1h to C, cfb_wind14 to C, nhl_pl_dog_bigml to paper (all applied 11/10); retire nba_momentum (18-40) and stale_book (20-43) paper rules (not applied: Sean wants 1-2 months of tracking) | Applied except the two retirements | docs/weekly_recheck_2026-11-10.md |
| 11/10 | Ties, locks, ladders | Nothing | DEAD | docs/overnight_2026-11-10.md |
| 11/9 | Curve leans retest after going live | Judged on results, not CLV; early live record poor (NHL 3rd-period unders 0-8) | Keep tracking | docs/curve_retest_2026-11-09.md |
| 11/9 | Kalshi daily high-temperature markets | Calibrated through the day and better than the National Blend; what is left is speed | DEAD for us | docs/weather_markets_2026-11-09.md |
| 11/10 | Women's college basketball spread cells rebuilt (sharp/wncaab_replay.py; the 11/9 script was not saved) and put on paper | Dogs +7 to +10: 53-38-1, +11.4%, both seasons positive, matches 11/9 exactly. Follow a 1+ point move: 76-57-1, +9.6%, 2025-26 -3.7u; the 11/9 figure (75-44, +20.7%) could not be reproduced (checked one-snapshot games, pricing off the median, in-game snapshots, listed start vs ESPN tip: only 20 games list a late start and none moved a close). Live logic matched the replay's side and number on 76 of 80 historical picks (the other 4 had none of Sean's books on the median); ESPN grading matched on all 76 | PAPER from 11/10 as wncaab_dog_7_10 and wncaab_move_follow; the rebuild is the definition of record | loggers/wncaab_live.py, data/research/wncaab_replay.json, METHODOLOGY section 8d |
| 11/9 | Women's college basketball, MMA market tests | WNCAAB (no Pinnacle, 2 seasons): unders -7.9%; dogs +7 to +10 53-38 (+11.4%); following a line move is the strongest cell. MMA: following a 6+ point Pinnacle move at the close +7.3%, but the same side at its opening price +19.7% (the money is made before the move) | WNCAAB cells on paper 11/10 (row above); MMA steam stays tier C | docs/wncaab_mma_2026-11-09.md |
| 11/6 | Tier recheck of every system and paper angle | Tiers set | see doc | docs/tier_recheck_2026-11-06.md |
| 11/6 | Derivatives on the full-game curve | CFB first-quarter unders tier A, CBB first-half totals tier C | LIVE | docs/deriv_curve_2026-11-06.md |
| 11/6 | Full-game systems split into derivatives; NBA under reconciliation; threshold grid | NBA under rule works only at its exact thresholds (fragile); grid verdicts ROBUST / FRAGILE / NO EDGE per rule | Tiers set from it (see tier recheck) | docs/deriv_split_2026-11-06.md |
| 11/6 | Team metrics on top of the market (CBB tempo, NHL xG, NFL EPA) | The closing full-game markets already contain them (EPA adds nothing, z -0.9) | DEAD for full-game closes; possible use inside derivative rules | docs/metrics_2026-11-06.md |
| 11/5 | Odds API replay of every rule, 2020-26 Pinnacle closes | wind1014 +17.8% (6 of 7 seasons), nhl_early_home_fav_qual +7.1% (6 of 7); several rules to paper | Tiers set from it | docs/odds_api_replay_2026-11-05.md, docs/systems_test_2026-11-05.md |
| 11/5 | Angle miner (train through 2023, test 2024 on) | Candidates for paper only | PAPER | docs/angles_2026-11-05.md |
| 11/5 | CFB weather replay | cfb_hot_over_low_total to tier B (117-71-3, 6 of 6 seasons) | LIVE | docs/cfb_weather_2026-11-05.md |
| 11/5 | First-half and team-total history | Weather, rest and Monday-night unders beat the first-half baseline by 10-20 points | Feeds the 1H rule tiers | docs/derivatives_2026-11-05.md |
| 11/5 | Bet Labs vs Odds API reconciliation | Bet Labs grades at real juice; see doc | Explains the disagreements | docs/betlabs_reconciliation_2026-11-05.md |
| 11/4 | Tennis Abstract models | Structure only, no prices; settled hot favourite is tier B | LIVE (tier B) | docs/tennis_ta_2026-11-04.md |
| 11/1 | Tennis first sets | Favourite wins set 1 more than the textbook model says; first-set favourites look under-priced at every venue measured | PAPER (tennis_fs_fav) | docs/tennis_firstset_2026-11-01.md |
| 11/1 | Do line moves overcorrect? Steam timing on Kalshi | Bet Labs open to close, every sport: the books win both sides; fading a move is the worse side (NBA totals fade -7.2%, NHL ML fade -7.3% in holdout). Closes under-react a little in totals | DEAD as a fade; never fade a move | docs/betlabs_market_moves_2026-11-01.md, docs/steam_timing_2026-11-01.md |
| 11/1 | Rescue variants for failed Bet Labs systems (20 systems, 33 variants) | Bar corrected: about 14-15 of 33 pass on luck; only 5 passed, so the decay is real | DEAD: logic does not rescue the failed systems | docs/betlabs_rescue_2026-11-01.md |
| 10/25 to 10/30 | Bet Labs audits: NFL, NBA, CFB, NHL, NCAAB, segments, 136 account systems, line moves | Source of the systems on the board | see docs | docs/betlabs_*.md |

## 5. Odds API data on hand (check before spending credits)

- Game lines 2020-26, 18 sports, 116,915 games: data/oddsapi/compact, folded into data/oddsapi/odds.sqlite. Includes tennis, soccer, MMA, boxing, WNCAAB.
- Derivatives (first half, quarters, periods, team totals), one pregame snapshot per game from 2023-05: loggers/oddsapi_derivs.py.
- Player props, 2023-26: NBA (points, rebounds, assists, threes, PRA), NFL (12 markets), NHL (shots, saves, points, goalscorer), plus MLB, WNBA, soccer results files in data/research/props_*.json.
- Not pulled: props at more than one or two times before the start (only 10 min, 60 min and 3 h snapshots exist); second-half lines (not posted pregame).

## 6. Process changes

| Date | Change |
|---|---|
| 11/10 | docs/METHODOLOGY.md refreshed (was dated 11/6): new "Changes on 11/10" list; tier table (1a); 11/10 tier review (cfb_wind14 A to C, mnf_1h B to C, cfb_road_dog_low_total and nhl_pl_dog_bigml to paper); sharp flags on paper from 11/10 10:00 UTC; data of record now lists derivatives for nine sports, props 2023-26, exchange tapes and ProphetX; new section 8 (resting offers, rest or take, parlays, women's college basketball); testing standard adds the neighbour rule and "every test script saved in the repo"; corrected the 11/6 note that nfl_home_dog_7510 was held at B (it went to C later that day) |
| 11/10 | Push helper adds the session attribution lines to every commit from here on |

## 7. Corrections worth remembering

- Novig tape: outcome and price are the resting order's. Maker side was reversed once in maker_test (fixed 11/10).
- moves.jsonl.gz: p1 is the home/over price, not the mover's.
- Soccer moneylines need a three-way devig.
- One day of parlays (11/10, makers +21.1%) was not representative; 15 days came to -0.8%.
- Do not dispatch tracker.yml off schedule (it logs system fills).
- A test whose script was not saved cannot be checked later (the 11/9 women's basketball move cell). Save every test script in sharp/.
- nfl_home_dog_7510 is tier C in sharp/systems.py, but its EVIDENCE text still says "stays B" (left from before the 11/6 recheck). Text only; not changed, since it is in the live rules file.
