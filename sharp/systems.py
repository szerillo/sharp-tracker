#!/usr/bin/env python3
"""Pre-registered systems engine: every tracker run, for each game inside the fire window, evaluate the rules for its sport and the
first time a rule triggers write ONE paper fill at the best bettable price at that moment (BetMGM excluded, Kalshi fee included) with
rule_tag 'paper:<tag>', graded like any fill with CLV vs the ruler. State: data/state/system_fired.json (game x tag, never fires
twice). View: data/state/system_fires.json (games with triggers, fills, per-tag record, rule descriptions in DESC).
Rules and their sources: RULES / DESC below; audits in docs/betlabs_*.md and docs/exchange_signals_audit_2026-10-29.md.
Stacking: one bet per game per market x side. Publication gate per tag: 100 graded fills AND positive CLV."""
import os, sys, json, uuid, sqlite3, datetime as dt, collections, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from sharp import norm as N, fair as F, constants as C, season as SEA, fills as FI

ROOT = os.path.abspath(os.path.join(HERE, '..')); SD = os.path.join(ROOT, 'data', 'state'); DB = os.path.join(SD, 'sharp.sqlite')
FIRED = os.path.join(SD, 'system_fired.json'); VIEW = os.path.join(SD, 'system_fires.json'); WX = os.path.join(ROOT, 'data', 'nfl', 'weather', 'weather.jsonl')
WX_CFB = os.path.join(ROOT, 'data', 'cfb', 'weather', 'weather.jsonl')
NOW = dt.datetime.fromisoformat(os.environ["SYSTEMS_NOW"].replace("Z", "+00:00")) if os.environ.get("SYSTEMS_NOW") else dt.datetime.now(dt.timezone.utc); NOW_S = N.iso(NOW)   # SYSTEMS_NOW replays a past run (debugging)
RULES = {'wind1014': dict(market='total', side='under', stake=1.0), 'wind1014_1h': dict(market='1h_total', side='under', stake=0.5),
         'cfb_wind14': dict(market='total', side='under', stake=1.0, sport='cfb'),
         'vrest8_1h': dict(market='1h_total', side='under', stake=0.5), 'mnf_1h': dict(market='1h_total', side='under', stake=0.5),
         'awfuldog': dict(market='spread', side='dog', stake=0.5), 'bounce15_1h': dict(market='1h_spread', side='dog', stake=0.5),
         # 11/5 Odds API replay of six NFL seasons at Pinnacle closes (sharp/nfl_replay.py, data/research/nfl_replay.json)
         'wind1014_cold': dict(market='total', side='under', stake=0.5), 'awfuldog_deep': dict(market='spread', side='dog', stake=0.5),
         'nfl_home_dog_7510': dict(market='spread', side='dog', stake=0.5), 'nfl_road_dog_7510': dict(market='spread', side='dog', stake=0.5),
         'nfl_fade_fav_bye': dict(market='spread', side='dog', stake=0.5),
         # 11/5 angle miner on the corrected Odds API database (docs/angles_2026-11-05.md): paper, building a forward record
         'nba_ats_hot_home': dict(market='spread', side='home', stake=0.5, sport='nba'), 'nba_bigfav_over': dict(market='total', side='over', stake=0.5, sport='nba'),
         'nhl_loss_streak_over': dict(market='total', side='over', stake=0.5, sport='nhl'),
         'nba_badteams_under': dict(market='total', side='under', stake=0.5, sport='nba'), 'nba_roadtrip_over': dict(market='total', side='over', stake=0.5, sport='nba'),
         'nhl_bounce_home_ml': dict(market='ml', side='home', stake=0.5, sport='nhl'), 'nhl_skid_fade_road': dict(market='spread', side='away', stake=0.5, sport='nhl'),
         'cfb_day_over': dict(market='total', side='over', stake=0.5, sport='cfb'), 'cfb_homefav_7510_under': dict(market='total', side='under', stake=0.5, sport='cfb'),
         'mlb_road_over_under': dict(market='total', side='under', stake=0.5, sport='mlb'),
         # exchange signals (docs/exchange_signals_audit_2026-10-29.md): fired inside T-1.5h, at the exchange that shows the signal
         'xch_homedog_fade': dict(market='ml|spread', side='away', stake=0.5, sport='nfl,nba,cfb,nhl,mlb', venue='Novig'),
         # nba_momentum retired 11/9 (docs/checkpoint_2026-11-09.md): 18-40 on paper, -11.79u, ROI -40.7%, ROI z -3.27 on 58 graded (rule: 50+ graded and z -2 or worse); CLV -1.49 on 58.
         # Bet Labs round 2 leans (docs/betlabs_segments_audit_2026-10-30.md), paper only
         'nhl_pl_fav_gap': dict(market='spread', side='fav', stake=0.5, sport='nhl'), 'nhl_pl_fav_strong_opp': dict(market='spread', side='fav', stake=0.5, sport='nhl'),
         'nhl_pl_dog_bigml': dict(market='spread', side='dog', stake=0.5, sport='nhl'),
         'nba_1h_under_hot_over': dict(market='1h_total', side='under', stake=0.5, sport='nba'),
         # Bet Labs round 3 watch tier (docs/betlabs_account_systems_audit_2026-10-30.md), paper only
         'nhl_early_home_fav_qual': dict(market='ml', side='home', stake=0.5, sport='nhl'), 'nba_under_good_home_over': dict(market='total', side='under', stake=0.5, sport='nba'), 'nba_under_good_home_over_small': dict(market='total', side='under', stake=0.5, sport='nba'),
         'cfb_road_dog_low_total': dict(market='spread', side='away', stake=0.5, sport='cfb'),
         'cbb_bigloss_vs_top5': dict(market='spread', side='team', stake=0.5, sport='cbb'),
         # rescued variants of failed account systems (docs/betlabs_rescue_2026-11-01.md), paper only
         'cfb_hot_over_low_total': dict(market='total', side='over', stake=0.5, sport='cfb'),
         'cfb_road_streak_dog': dict(market='spread', side='away', stake=0.5, sport='cfb'),
         'cbb_under_good_over_drop': dict(market='total', side='under', stake=0.5, sport='cbb')}
# Evidence per tag: Bet Labs train / holdout record (regular season, closing lines; holdout = 03/2021 on), positive holdout seasons, and a tier:
#   A = holdout z >= 2 with a mechanism (wind family); B = positive both halves, most seasons positive, z 1-2; C = lean (thin or z < 1).
# These are what the screen shows next to a fire. The forward record (W-L, ROI, CLV) is a diagnostic, not a gate: a rule the market does
# not price can keep winning with zero CLV, so nothing here waits for CLV before it is shown as a bet.
EVIDENCE = {'wind1014': dict(tier='A', train='Bet Labs 533-376 all-time (2003-), +13.3%', hold="Bet Labs' own picks since 2020 at Pinnacle's close: 160-101 (+18.6%); Odds API replay on Open-Meteo wind 161-103 (+18.1%). Both sources agree in the NFL", seasons='5 of 6', src='docs/betlabs_nfl_audit_2026-10-25.md'),
            'wind1014_1h': dict(tier='C', train='Bet Labs 404-302 all-time, +9.0%; since 2021 113-90, +5.9%', hold='WC 1H database 2023-26 (Pinnacle 1H line): 55-51, +0.4%, against a -9.6% baseline for every 1H under in the same games; 2023 and 2024 negative. A -> B 11/5; B -> C 11/6 (our own replay is flat, so it cannot hold the same size as rules that replicate)', seasons='1 of 3 (ours)', src='docs/betlabs_nfl_audit_2026-10-25.md'),
            'cfb_wind14': dict(tier='A', train='Bet Labs 555-402 all-time, +12%', hold="Bet Labs' own picks since 2020 graded at Pinnacle's close: 135-96 (+12.3%)", seasons='5 of 6', labs_check='11/5 (docs/cfb_weather_2026-11-05.md): the edge sits in Bet Labs\' wind source; Open-Meteo reanalysis 14+ alone replays 114-102, and its 14+ games Bet Labs did not flag went 66-72. Live rule fires only with MySportsWeather in the blend', src='docs/betlabs_cfb_audit_2026-10-29.md'),
            'vrest8_1h': dict(tier='C', train='454-357 all-time, +7.7%', hold='Odds API full-game cousin 127-93-2 (+11.9%) but 48-49-2 since 2024', seasons='5 of 6', src='docs/betlabs_nfl_audit_2026-10-25.md'),   # 11/5: tier C, the edge is fading
            'mnf_1h': dict(tier='C', train='168-118 all-time, +12.3%', hold='our 1H replay 33-28 (+6.4%) with 2024 at -25.1%; down from B 11/10 (weekly recheck)', seasons='4 of 6', src='docs/betlabs_nfl_audit_2026-10-25.md'),
            # 11/5: the Odds API replay (2020-26, Pinnacle closes, results) re-banded the dog rule: season margin -7 to -13 is 91-75-5 (+5.6%, 5 of 7 seasons),
            # -13 or worse is 14-16 (-11%). The live band moves to -7 to -13 at tier C; the deep band is paper.
            'awfuldog': dict(tier='C', train='Bet Labs (season margin -13 or worse, dog): 2003-Feb 2021 203-133 (+16.8%), since Mar 2021 51-31 (+18.6%); its own picks since 2020 60-40 (+15.1%)', hold='WC 2020-26 with season margins reset each season: 61-50 (+5.5%), 6 of 7 seasons; 3+ games 37-27 (+11.2%). The 11/5 -7 to -13 re-band came from a replay that averaged margins across seasons; that band is +0.7%. C -> B 11/6', seasons='6 of 7', src='docs/systems_test_2026-11-05.md'),
            'awfuldog_deep': dict(tier='P', train='Odds API 2020-26: 14-16, -11%', hold='the old live band', seasons='3 of 6', paper_why='margin -13 or worse was 14-16; waiting on sample', src='data/research/nfl_replay.json'),
            'wind1014_cold': dict(tier='P', train='Odds API 2020-26: wind 10-14 at 35F or colder 27-27', hold='mild weather 133-76, +23.4%', seasons='cold band flat', paper_why='the cold band was 27-27; mild weather carries the wind rule', src='data/research/nfl_replay.json'),
            'nfl_home_dog_7510': dict(tier='C', train='Odds API 2020-26: home dog +7.5 to +10 47-25-1, +23%', hold='all dogs 7.5-10: 135-97-3, +10%, 6 of 7 seasons', seasons='5 of 7', labs_check='Bet Labs: 119-84-2 (+11.2%) all-time, 46-21-1 (+30%) since 2020', alltime='Bet Labs 2003-19: 73-63 (+1.8%); 2020-: 46-21 (+30%); all-time 119-84 (+11.2%). Positive in both eras; stays B', src='data/research/nfl_replay.json'),
            'nfl_road_dog_7510': dict(tier='P', train='Odds API 2020-26: road dog +7.5 to +10 88-72-2', hold='paper, the home version is the bet', seasons='4 of 7', paper_why='the home version carries the edge; road dogs 88-72 only', src='data/research/nfl_replay.json'),
            # 11/5 (Sean): mined angles start at B when they hold every season with a mechanism, C when a season is negative; up to A on a forward record.
            # Selection haircut: these were the best of ~100k tests per sport, so expect about half the backtest ROI going forward.
            'nba_ats_hot_home': dict(tier='C', recheck='11/6 paper grid: 245-173 (+14.3%), 6 of 6; without the rest filter 402-321 (+8.4%, 6 of 6); to C 0.25u (Sean 11/6)', train='WC backtest 2020-23: 203-156 (+10.1%)', hold='2024-26: 108-72 (+17.0%); every season +6% or better', seasons='7 of 7', labs_check='Bet Labs since 8/2020: 261-218 (+4.4%); all-time -1.5%', alltime='Bet Labs 2003-19: 611-629 (-3.8%); 2020-: 261-218 (+4.4%). Since-2020 only; paper 11/5', paper_why='positive only since 2020 (2003-19 -3.8%)', src='docs/angles_2026-11-05.md'),
            'nba_badteams_under': dict(tier='C', recheck='11/6 paper grid: 143-96 (+16.8%), 5 of 6 seasons; every neighbour +6% to +17%; to C 0.25u (Sean 11/6)', train='WC backtest 2020-23: 76-50 (+19%)', hold='2024-26: 77-45 (+22.3%); 153-95 overall, all seasons positive', seasons='7 of 7', labs_check='Bet Labs approximation (visitor 30-45%, home under 40%): 203-175 (+3.0%) since 2020', alltime='Bet Labs approx 2003-19: 771-772 (-2.3%); 2020-: 203-175 (+3.0%). Since-2020 only; paper 11/5', paper_why='positive only since 2020 (2003-19 -2.3%)', src='docs/angles_2026-11-05.md'),
            'nhl_loss_streak_over': dict(tier='P', train='WC backtest 2020-23: 244-202 (+6.0%)', hold='2024-26: 141-88 (+18.7%); 385-290 overall; the one miss -1%', seasons='6 of 7', labs_check='Bet Labs since 8/2020: 391-326 (+4.3%); all-time flat', alltime='Bet Labs 2003-19: 794-826 (-2.3%); 2020-: 391-326 (+4.3%). Since-2020 only; paper 11/5 (Sean: long sample and a reason)', paper_why='positive only since 2020 (2003-19 -2.3%); no mechanism', src='docs/angles_2026-11-05.md'),
            'nhl_bounce_home_ml': dict(tier='C', train='WC backtest 2020-23: 212-136 (+4.9%)', hold='2024-26: 125-61 (+19.9%); 337-197 overall; -6% in 2022-23', seasons='6 of 7', labs_check='Bet Labs since 8/2020: 314-191 (+6.2%)', alltime='Bet Labs 2003-19: 562-398 (-0.7% at the ML); 2020-: 314-191 (+6.2%); all-time +1.7%. Not negative before 2020 but not positive either; tier C 11/5', src='docs/angles_2026-11-05.md'),
            'mlb_road_over_under': dict(tier='P', train='WC backtest 2020-23: 206-151 (+11.1%)', hold='2024-25: 136-95 (+13.6%); 342-246 overall in OUR data, which ends with the 2025 season', seasons='mixed', labs_check='Bet Labs (visitor over% 60+, game 16+, regular season), by season: 2020 21-22, 2021 62-77, 2022 11-5, 2023 66-49, 2024 44-24, 2025 38-35, 2026 69-101 (-21%). The 2026 season, which our tables do not hold, wiped it out', paper_why='Bet Labs 2026 season 69-101 (-21%); 2021 62-77; our 2020-25 sample does not include the collapse', src='docs/angles_2026-11-05.md'),
            'nba_bigfav_over': dict(tier='C', recheck='11/6 paper grid: 351-285 (+6.9%), 5 of 6; 82.5%+ 509-424 (6 of 6); to C 0.25u (Sean 11/6)', train='WC backtest 2020-23: 154-114 (+11.3%)', hold='2024-26: 118-86 (+10.5%); 272-202 overall; flat in 2021-22, -8% road-trip variant in 2022-23', seasons='6 of 7', labs_check='Bet Labs since 8/2020: home fav -650+ 335-300 (+1.0%), visitor fav 59-46; the backtest pair included a filler filter', alltime='Bet Labs 2003-19: 1011-1038 (-3.7%); all-time -2.6%', paper_why='Bet Labs flat at every window; the backtest pair had a filler filter', src='docs/angles_2026-11-05.md'),
            'nba_roadtrip_over': dict(tier='P', train='WC backtest 2020-23: 126-99 (+8%)', hold='2024-26: 64-32 (+28.9%); 190-131 overall; 2023-24 only +2%', seasons='6 of 6', labs_check='Bet Labs: 4th+ road game alone 519-550 (-6.9%) since 2020; the last-meeting split carried the backtest', alltime='Bet Labs 2003-19: 1164-1132 (-1.0%); 2020-: -6.9%; all-time -2.9%', paper_why='Bet Labs -6.9% since 2020 on the road-game filter alone', src='docs/angles_2026-11-05.md'),
            'nhl_skid_fade_road': dict(tier='C', recheck='11/6 paper grid: 286-267 (+7.0%), 5 of 5 full seasons; the visitor-off-a-win filter carries most of it; to C 0.25u (Sean 11/6)', train='WC backtest 2020-23: 132-100 (+19.9%)', hold='2024-26: 64-45 (+20.8%); 196-145 overall at the puck line; 2020-21 -6%', seasons='5 of 6', labs_check='Bet Labs since 8/2020: 284-264 (+5.6%) at the puck line', alltime='Bet Labs 2003-19: 576-623 (-7.1%) at the puck line; 2020-: 284-264 (+5.6%). Since-2020 only; paper 11/5', paper_why='positive only since 2020 (2003-19 -7.1%); no mechanism', src='docs/angles_2026-11-05.md'),
            'cfb_day_over': dict(tier='P', train='2020-23 afternoon (2-7pm ET) kickoffs: 155-112 (+11.7%)', hold='2024-26: 156-109 (+13.1%); noon kickoffs dropped 11/5 (-0.9% / +2.8%)', seasons='7 of 7', labs_check='Bet Labs 2-7pm ET since 8/2020: 301-233-5 (+7.7%), 5 of 7 seasons (2020 -5.6, 2026 -5.6); all-time since 2005 flat (886-853), so a since-2020 angle', alltime='Bet Labs 2005-19 (2-7pm cut): about 585-620; 2020-: 301-233 (+7.7%); all-time 886-853 flat', paper_why='no mechanism for an afternoon-only over; flat before 2020', src='docs/angles_2026-11-05.md'),
            'cfb_homefav_7510_under': dict(tier='C', train='WC backtest 2020-23: 98-74 (+9.7%)', hold='2024-26: 90-56 (+18.2%); 188-130 overall; 2023 -14%', seasons='6 of 7', labs_check='Bet Labs: 611-523 (+4.1%) all-time, 194-138 (+11.4%) since 2020', alltime='Bet Labs 2003-19: 417-385 (+1.1%); 2020-: 194-138 (+11.4%); all-time 611-523 (+4.1%). B -> C 11/6: the 2003-19 era is 802 bets at +1.1%, which is a large enough sample to say the edge did not exist then; the whole edge is 2020 on', src='docs/angles_2026-11-05.md'),
            'nfl_fade_fav_bye': dict(tier='P', train='Odds API 2020-26, favourite off a true bye (12-20 days): 70-84 ATS; the dog +5.4%', hold='our earlier 120-143 counted week 1 as a bye (every team is 12+ days off); corrected 11/5', seasons='mixed', labs_check='Bet Labs (dog vs favourite off 8-30 days, so it also counts long weeks after Thursday games): 2003-19 356-389 (-6.5%), 2020-on 203-188 (-0.4%). Fails the long-window gate; stays paper', paper_why='Bet Labs 2003-19 -6.5%; our replay counted week 1 as a bye; definitions reconciled 11/5, no edge', src='docs/systems_test_2026-11-05.md'),
            'bounce15_1h': dict(tier='P', train='Bet Labs 429-340 all-time, +6.6%; since 2021 117-83, +11.6%', hold='WC 1H database 2023-26: 54-61, -10.5%, every full season negative, no better than all dogs 1H (-10.7%). The two tests disagree: B -> C 11/5; C -> paper 11/6 (our replay is negative in every season and no better than backing every 1H dog)', seasons='0 of 3 (ours)', src='docs/betlabs_nfl_audit_2026-10-25.md'),
            # 11/2 (Sean): the two exchange-audit rules are paper only (tier P): both were below the audit's bar, xch_homedog_fade failed its
            # robustness check and decayed by month, nba_momentum was graded at the close while live fires come earlier; live 12-6 -0.73u and 3-9 -3.15u, both negative CLV
            'xch_homedog_fade': dict(tier='P', train='exchange audit, sparse tape', hold='+12% at the close, n 300', seasons='two months', paper_why='exchange tape only, sparse', src='docs/exchange_signals_audit_2026-10-29.md'),
            'nba_momentum': dict(tier='P', train='exchange audit, sparse tape', hold='continuation +4 to +6 pts', seasons='two months', paper_why='exchange tape only, sparse', src='docs/exchange_signals_audit_2026-10-29.md'),
            'nhl_pl_fav_gap': dict(tier='P', train='Bet Labs 502, +17.4%', hold='corrected replay 2020-26: 79-126 at -1.5, +1.5%; 3 of 7 seasons; Bet Labs own picks 109-138 since 2020', seasons='3 of 7', src='docs/systems_test_2026-11-05.md'),
            'nhl_pl_fav_strong_opp': dict(tier='P', train='Bet Labs 992, +11.9%', hold="corrected replay (regular-season records): 136-222 at -1.5, -0.1% at Pinnacle; the 360 games Bet Labs also picks +3.6%; 2023-24 -36%", seasons='3 of 7', src='docs/systems_test_2026-11-05.md'),
            'nhl_pl_dog_bigml': dict(tier='P', train='Bet Labs 810, +6.0%', hold='Odds API 2020-26: 40-25 at +1.5, +9.9%', seasons='3 of 7', paper_why='4 of 7 seasons negative and 38 of the 65 bets in one season (2022-23); down from C 11/10 (weekly recheck)', src='data/research/rule_replay.json'),
            'nba_1h_under_hot_over': dict(tier='P', train='508, +8.4%', hold='257, +6.1%', labs_check='11/6 (docs/deriv_split_2026-11-06.md): Bet Labs picks 2023-24 on 103-96 (-1.2%) at its own lines, 85-90 (-5.9%) at Pinnacle 1H; data matches Bet Labs game for game. To paper 11/6 (Sean)', seasons='1 of 3 since 2023', src='docs/betlabs_segments_audit_2026-10-30.md'),
            'nhl_early_home_fav_qual': dict(tier='B', train='Bet Labs 1,459, +3.0%', hold='corrected replay 2020-26: 258-139 ML, +9.4% at Pinnacle, +9.3% at the best US book, 6 of 6 full seasons', seasons='6 of 6', src='docs/systems_test_2026-11-05.md'),   # 11/5: the best-replicating rule
            'nba_under_good_home_over_small': dict(tier='P', train='same rule with the total down only 0.5-1.0 from the open', hold='our replay: drop 0.5+ is 215-210 (-1.4%); the games Bet Labs and we disagree on (borderline drop or over%) went 59-83', seasons='n/a', src='docs/deriv_split_2026-11-06.md'),   # 11/6 (Sean): paper below a 1.5 drop
            'nba_under_good_home_over': dict(tier='C', train='Bet Labs 978, +10.9%', hold="Bet Labs' own picks at Pinnacle's close: 392, +7.8%; our replication with real market opens: 215-210-7, -1.3% (the two filter sets still differ on ~90 games)", seasons='3 of 7 (ours)', labs_check="11/6 reconciliation (docs/deriv_split_2026-11-06.md): Bet Labs' own picks at Pinnacle's close 213-174 (+7.4%); our extra borderline games 59-83. Neighbouring thresholds about break-even; total down 1.5+ is the steady part: 171-141 (+6.8%) on our data. From 11/6 the rule fires only on a 1.5+ drop; 0.5-1.0 drops go to paper (nba_under_good_home_over_small)", src='docs/systems_test_2026-11-05.md'),   # 11/5 pm: tier C, the two tests disagree; 11/6 drop 1.5+ only
            'cfb_road_dog_low_total': dict(tier='P', paper_why='2025 -1.0% and 2026 -33.3% (7-14-1): two negative seasons in a row; down from C 11/10 (weekly recheck)', train='Bet Labs 645, +14.9%', hold="corrected replay (conference games): 132-113-10, +4.4%, 5 of 6 full seasons; Bet Labs' own picks 153-117; non-conference version -7.2%", seasons='5 of 6', src='docs/systems_test_2026-11-05.md'),
            'cbb_bigloss_vs_top5': dict(tier='C', train='177, +23.1%', hold='66, +13.0%', seasons='thin (about 12 a season)', src='docs/betlabs_account_systems_audit_2026-10-30.md'),
            'cfb_hot_over_low_total': dict(tier='B', train='Bet Labs 203, +16.4% (to 2021); hold 92, +10.1%', hold='Odds API 2020-26 with NASA POWER kickoff temperature: non-conference 117-71-3 (+19.5%), 6 of 6 seasons; the conference version is 37-38', seasons='6 of 6', labs_check='two independent tests agree; mechanism: heat wears out thinner non-conference defences, low totals price it least; to B 11/5', src='docs/cfb_weather_2026-11-05.md'),
            'cfb_road_streak_dog': dict(tier='P', train='Bet Labs 214, +20.7%', hold='Odds API 2020-26: 212-228-9, -6.4%', seasons='2 of 7', paper_why='Bet Labs uses a bet-volume filter we cannot see; -2% in our replay', src='data/research/rule_replay.json'),   # 11/5: paper
            'cbb_under_good_over_drop': dict(tier='P', train='Bet Labs 949, +7.6%', hold="Bet Labs' own picks +3.5% (3 of the last 4 seasons negative); ours with real opens 495-498-11, -5.0%", seasons='1 of 6 (ours)', paper_why='1 of 6 seasons positive in our replay; Bet Labs 3 of last 4 negative', src='docs/systems_test_2026-11-05.md')}   # 11/5 pm: paper
# nhl_over_busy_goalie retired 10/30: positive in 2 of 7 seasons and the goalie-saves field thins to a handful of games after 2023.
DESC = {'wind1014': 'NFL outdoor, wind 10-14 mph (average of the latest Open-Meteo and MySportsWeather forecasts, whole mph): full-game under', 'wind1014_1h': 'same wind, 10-13 mph: first-half under',
        'cfb_wind14': 'CFB outdoor, wind 14+ mph (same two-source average): full-game under', 'vrest8_1h': 'NFL visitor off 8-30 days: first-half under', 'mnf_1h': 'Monday night: first-half under',
        'awfuldog': 'NFL dog whose season point margin is -13 or worse (1+ games): full-game spread (Bet Labs definition; restored 11/6)', 'bounce15_1h': 'NFL dog whose last game lost ATS by 15+: first-half spread',
        'awfuldog_deep': 'NFL dog with a season margin worse than -13: full-game spread (paper; 14-16 in the six-season replay)',
        'wind1014_cold': 'NFL outdoor, wind 10-14 mph but 35F or colder: full-game under (paper; the cold band was 27-27 in the replay, mild weather carries the rule)',
        'nfl_home_dog_7510': 'NFL home dog of +7.5 to +10 at the close: home spread', 'nfl_road_dog_7510': 'NFL road dog of +7.5 to +10: road spread (paper)',
        'nfl_fade_fav_bye': 'NFL favourite coming off a bye (8+ days): take the dog on the spread (paper)',
        'nba_ats_hot_home': 'NBA home team covering 60%+ of its spreads this season (8+ games) on exactly 2 days rest: home spread (mined 11/5)',
        'nba_bigfav_over': 'NBA favourite at 85%+ no-vig on the moneyline: over (mined 11/5; blowouts run up)',
        'nhl_loss_streak_over': 'NHL home team on a 3+ game losing streak with a season over rate of 40-60%: over (mined 11/5)',
        'nba_badteams_under': 'NBA visitor with a season margin of -2 to -7 at a home team winning under 40% at home (8+ games each): under (mined 11/5)',
        'nba_roadtrip_over': 'NBA visitor on its 4th+ straight road game that won the last meeting with this opponent: over (mined 11/5)',
        'nhl_bounce_home_ml': 'NHL home team off a loss by 3+ goals with a 50-64% record (8+ games): home moneyline (mined 11/5)',
        'nhl_skid_fade_road': 'NHL road team off a win against a home team that has lost 3+ straight: road puck line (mined 11/5)',
        'cfb_day_over': 'CFB game kicking off 2-7pm ET with a total of 45-51.5: over (mined 11/5; noon kickoffs dropped. PAPER until a mechanism is shown: Sean 11/5, a time slot is not a reason for overs. Tomorrow\'s CFB weather replay tests the temperature story)',
        'cfb_homefav_7510_under': 'CFB home favourite of 7.5 to 10: under (mined 11/5)',
        'mlb_road_over_under': 'MLB road team whose games have gone over 60%+ this season (15+ games): under (mined 11/5; fires in season)',
        'xch_homedog_fade': 'Novig home side two-sided at 20-35c inside T-90m: take the road side on Novig', 'nba_momentum': 'NBA exchange mid moved 3c+ since T-6h: continuation at that exchange',
        'nhl_pl_fav_gap': "NHL favorite -1.5 when the OPPONENT's win% is 22+ points higher than the favorite's (market rates the favorite above its record)", 'nhl_pl_fav_strong_opp': 'NHL favorite -1.5 when the opponent wins 66%+',
        'nhl_pl_dog_bigml': 'NHL dog +1.5 when the dog ML is +181 to +196', 'nba_1h_under_hot_over': 'NBA 1H under when the visitor has gone over 71%+ of the time',
        'nhl_early_home_fav_qual': 'NHL home favorite, game 24 or earlier, vs an opponent winning 51%+: moneyline', 'nba_under_good_home_over': 'NBA under: home team over 58%+, home 1-2 days off, visitor 1-3, total down 1.5+ from open (11/6: was 0.5+)', 'nba_under_good_home_over_small': 'Same NBA under spot with the total down only 0.5-1.0 from open: paper (11/6)',
        'cfb_road_dog_low_total': 'CFB conference game, road dog of 7+ with a total of 48 or less: road spread',
        'cbb_bigloss_vs_top5': 'CBB regular-season conference game: unranked team off a 14-45 point loss vs a top-5 opponent: that team on the spread',
        'cfb_hot_over_low_total': 'CFB non-conference game, 85F+ and wind 10 mph or less, total 55 or lower: over (heat wears defences down; low totals price it least)',
        'cfb_road_streak_dog': 'CFB conference road dog on its 2nd-5th straight road game, total 54 or lower: road spread (Bet Labs also requires a heavy-bet day, which we cannot see)',
        'cbb_under_good_over_drop': 'CBB weekday game, home team over 50%+ and visitor over 59%+ this season (3+ games each), total down 0.5+ from open: under'}
# Bet Labs screen per rule (every rule Bet Labs can express has a "Tested:" screen in the account, aligned 11/1). Exchange and tennis rules
# use data Bet Labs does not have, so they have none.
LABS = {'wind1014': (1772775, 'Tested: NFL Wind 10-14 Under'), 'wind1014_1h': (769171, 'Tested: NFL 1H Wind 10-13 Under'),
        'vrest8_1h': (1772962, 'Tested: NFL 1H Visitor Off 8 to 30 Days Under'), 'mnf_1h': (1772963, 'Tested: NFL 1H Monday Night Under'),
        'awfuldog': (1772776, 'Tested: NFL Awful-Team Dog ATS'), 'bounce15_1h': (1772929, 'Tested: NFL 1H Blowout Bounce Dog ATS'),
        'cfb_wind14': (1783043, 'Tested: CFB Wind 14 Plus Under'), 'cfb_road_dog_low_total': (1789286, 'Tested: CFB Conf Road Dog 7 Plus Total 48 or Less'),
        'nhl_pl_fav_gap': (1784154, 'Tested: NHL Puck Line Fav Win Pct Gap 22 Plus'), 'nhl_pl_fav_strong_opp': (1784155, 'Tested: NHL Puck Line Fav vs Opp Win Pct 66 Plus'),
        'nhl_pl_dog_bigml': (1784156, 'Tested: NHL Puck Line Dog Open ML 181 to 196'), 'nhl_early_home_fav_qual': (1789284, 'Tested: NHL Early Season Home Fav vs Quality Opp ML'),
        'nba_1h_under_hot_over': (1784158, 'Tested: NBA 1H Under Visitor Over Pct 71 Plus'), 'nba_under_good_home_over': (1789285, 'Tested: NBA Under Good Home Over Team Rest Total Down'),
        'cbb_bigloss_vs_top5': (1789287, 'Tested: CBB Unranked Off 14 Plus Loss vs Top 5 Conf'),
        'cfb_hot_over_low_total': (1792204, 'Tested: CFB Hot Weather Over Total 55 or Less'), 'cfb_road_streak_dog': (1792198, 'Tested: CFB Conf Road Streak Dog Total 54 or Less'),
        'cbb_under_good_over_drop': (1792184, 'Tested: CBB Under Good Over Teams Total Down'),
        # 11/5 (Sean): every added system has a Bet Labs screen for tracking; 'Tracked:' screens, built from the data service
        'nhl_loss_streak_over': (1799428, 'Tracked: NHL Home Lost 3 Straight Over'), 'nhl_bounce_home_ml': (1799430, 'Tracked: NHL Bounce Home Off 3 Plus Goal Loss ML'),
        'nhl_skid_fade_road': (1799431, 'Tested: NHL Road Off Win vs Home Lost 3 Plus PL'), 'nba_ats_hot_home': (1799432, 'Tested: NBA Home ATS 60 Pct Rest 2 Days'),
        'nfl_home_dog_7510': (1799433, 'Tracked: NFL Home Dog 7.5 to 10 ATS'), 'nfl_road_dog_7510': (1799434, 'Tracked: NFL Road Dog 7.5 to 10 ATS'),
        'nfl_fade_fav_bye': (1799435, 'Tracked: NFL Dog vs Favorite Off Bye ATS'), 'nba_bigfav_over': (1799443, 'Tested: NBA Big Home Fav 85 Pct Over (visitor: 1799444)'),
        'nba_roadtrip_over': (1799438, 'Tracked: NBA Visitor 4th Plus Straight Road Game Over'), 'nba_badteams_under': (1799442, 'Tested: NBA Weak Visitor at Home Team Under 40 Pct Under (approx)'),
        'cfb_day_over': (1799439, 'Tracked: CFB Afternoon Game 2-7pm ET Total 45 to 51.5 Over'), 'cfb_homefav_7510_under': (1799440, 'Tracked: CFB Home Fav 7.5 to 10 Under'),
        'mlb_road_over_under': (1799441, 'Tracked: MLB Visitor Over 60 Pct Under')}
LATE_H = (0.1, 1.5)   # exchange rules fire in the last 90 minutes (the audit priced them at the close)
WINDOW_H = tuple(float(x) for x in os.environ.get('SYSTEMS_WINDOW', '1,30').split(','))   # 11/7 (Sean): fire up to 60 min before the start (was 2 h)
# 11/4 (Sean: "why do CFB / NFL systems need to be inside 30 hours to fire?"): only the weather rules do, because the forecast they fire on
# is only reliable inside about a day. Every other rule bets as soon as it triggers and a book has a price (the trigger is a schedule /
# record / line fact that is already true days out), up to a week ahead.
WEATHER = {'wind1014', 'wind1014_1h', 'wind1014_cold', 'cfb_wind14', 'cfb_hot_over_low_total', 'wind_msw_only'}
EARLY_H = 7 * 24
def max_h(tag): return WINDOW_H[1] if tag in WEATHER else EARLY_H
VIEW_H = 8 * 24          # how far ahead a trigger is shown (Bet Labs lists current picks days ahead)


def msw_latest(sport, event_id):
    """Latest MySportsWeather reading for the game (cross-check source; NWS/NBM data)."""
    p = os.path.join(ROOT, 'data', sport, 'weather', 'msw.jsonl'); last = None
    if os.path.exists(p):
        for l in open(p):
            try: r = json.loads(l)
            except Exception: continue
            if r.get('event_id') == event_id and r.get('wind_mph') is not None: last = r
    return last


def weather_t24(event_id, path=None):
    """The latest pre-kickoff forecast row for this game (11/8, Sean: the wind should update. It was the row nearest 24h before kickoff,
    so a forecast that rose or fell on game day never changed the call). Open-Meteo is logged about every 20 minutes."""
    rows = []; path = path or WX
    if os.path.exists(path):
        for l in open(path):
            try: r = json.loads(l)
            except Exception: continue
            if r.get('espn_id') == event_id and r.get('wind_mph') is not None: rows.append(r)
    if not rows: return None
    pre = [r for r in rows if r['hours_to_kickoff'] > 0]
    return min(pre, key=lambda r: r['hours_to_kickoff']) if pre else rows[-1]


def blend_wind(wx, msw, need_both=False):
    """Wind the rules fire on: the average of the latest Open-Meteo and MySportsWeather forecasts when both exist, else whichever exists.
    Bet Labs' own wind sits between the two (11/1: LAC@LAR 14 vs 12.7 / 15, NE@MIA 10 vs 10.2 / 13, IND@JAX 11 vs 9.4 / 15, ATL@TB 11 vs
    8.9 / 12; the average matched all four in-band calls and the out-of-band KC@DEN). Returns (mph or None, label)."""
    o = wx.get('wind_mph') if wx and not wx.get('indoor') else None
    m = msw.get('wind_mph') if msw else None
    if o is not None and m is not None: return (o + m) / 2, f"avg {((o + m) / 2):.1f} mph (Open-Meteo {o} at T-{wx['hours_to_kickoff']:.0f}h, MySportsWeather {m})"
    if o is not None and need_both: return None, f"Open-Meteo {o} mph alone (MySportsWeather n/a): flag only. 11/5 CFB replay: Open-Meteo 14+ games Bet Labs' wind did not confirm went 66-72"
    if o is not None: return o, f"Open-Meteo {o} mph at T-{wx['hours_to_kickoff']:.0f}h (MySportsWeather n/a)"
    if m is not None and not (wx or {}).get('indoor'): return m, f"MySportsWeather {m} mph (Open-Meteo n/a)"
    return None, 'no forecast'


def prev_scheduled(sport, team, st):
    """(start, event_id) of the team's last scheduled game before st, played or not (postponed games skipped), from the ESPN schedule."""
    sched_rec(sport, ''); best = None
    for k, g in (SCHED_CACHE.get(sport) or {}).items():
        if team not in (g.get('away'), g.get('home')) or 'POSTPONED' in str(g.get('status') or '') or 'CANCELED' in str(g.get('status') or ''): continue
        t = N.parse_ts(g['start'])
        if t < st and (best is None or t > best[0]): best = (t, k)
    return best


def main_line(eq, market, home):
    """(line_home, n_books) of the line the most sportsbooks are hanging right now (each book's latest quote; opener and exchanges
    excluded). Spreads: home-side line; totals: the line."""
    nv = collections.Counter()
    for src in (eq.current, eq.keys):              # books' latest lines first; every line ever quoted only if no book has one
        for (m, l, p), vs in src.items():
            if m != market or l is None: continue
            if market.endswith('spread') and p != home: continue
            nv[l] += len(vs)
        if nv: break
    if not nv: return None, 0
    l = max(nv, key=lambda k: (nv[k], -abs(k))); return l, nv[l]


def take(conn, eq, fired, fires_now, game, ev, start, away, home, tag, market, line, side, part, stake, why):
    """One paper fill per game per tag; appends to the game view either way."""
    key = f"{ev}:{tag}"; game['triggers'][tag] = why
    if key in fired and not fired[key].get('void'): game['fills'].append(fired[key]); return
    if line is None: return
    row = paper_fill(conn, eq, ev, start, market, line, side, part, tag, stake, why)
    if not row: return
    rec_ = dict(tag=tag, fill_id=row['fill_id'], ts=NOW_S, market=market, side=side, line=line, venue=row['venue'], price=row['price_american'],
                fair=row['fair_at_fill'], edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why)
    fired[key] = rec_; game['fills'].append(rec_); fires_now.append(dict(game=f"{away}@{home}", **rec_))


def road_streak(sport, team, before):
    """Consecutive away games (this one included) for `team` going into a road game at `before`, from the season log."""
    L = [g for g in SEA.team_logs(sport).get(team, []) if N.parse_ts(g['start']) < before]
    k = 1
    for g in reversed(L):
        if g['side'] != 'away': break
        k += 1
    return k, len(L)


def open_line(conn, ev, market):
    """The opening number for a total: AN_Open's first line, else the earliest line any book quoted."""
    r = conn.execute("SELECT line FROM ticks WHERE event_id=? AND market=? AND venue='AN_Open' AND line IS NOT NULL ORDER BY ts_utc LIMIT 1", (ev, market)).fetchone()
    if not r: r = conn.execute("SELECT line FROM ticks WHERE event_id=? AND market=? AND line IS NOT NULL AND venue NOT IN ('Kalshi','Novig','Polymarket') ORDER BY ts_utc LIMIT 1", (ev, market)).fetchone()
    return r[0] if r else None


def open_ml(conn, ev, side):
    """Opening American moneyline for a side: AN_Open first, else the earliest book quote."""
    r = conn.execute("SELECT price_american FROM ticks WHERE event_id=? AND market='ml' AND side=? AND venue='AN_Open' AND price_american IS NOT NULL ORDER BY ts_utc LIMIT 1", (ev, side)).fetchone()
    if not r: r = conn.execute("SELECT price_american FROM ticks WHERE event_id=? AND market='ml' AND side=? AND price_american IS NOT NULL AND venue NOT IN ('Kalshi','Novig','Polymarket') ORDER BY ts_utc LIMIT 1", (ev, side)).fetchone()
    return r[0] if r else None


# 11/5 (Sean): structured backtest numbers for the record column. WC backtest = the Winners Circle database (Odds API 2020-26) at
# Pinnacle's closing price; 'cousin' marks a full-game stand-in for a first-half rule (1H history pull under way). Bet Labs windows come
# from data/research/betlabs_windows.json (all years, to Feb 2021, Mar 2021 on).
WC = {
    'wind1014': ('2020-26', 161, 103, 18.1, None), 'cfb_wind14': ('2020-26', 135, 96, 12.3, "Bet Labs' picks at Pinnacle's close"),
    'vrest8_1h': ('2023-26', 100, 87, 4.4, '1H at Pinnacle; all 1H unders -9.6%'), 'mnf_1h': ('2023-26', 33, 28, 6.4, '1H at Pinnacle; all 1H unders -9.6%'), 'bounce15_1h': ('2023-26', 54, 61, -10.5, '1H at Pinnacle'),
    'wind1014_1h': ('2023-26', 55, 51, 0.4, '1H at Pinnacle; all 1H unders -9.6%'),
    'awfuldog': ('2020-26', 61, 50, 5.5, 'season margins reset each season'), 'wind1014_cold': ('2020-26', 27, 27, None, None),
    'nfl_home_dog_7510': ('2020-26', 47, 25, 23.0, None), 'nfl_road_dog_7510': ('2020-26', 88, 72, None, None), 'nfl_fade_fav_bye': ('2020-26', 84, 70, 5.4, None),
    'nba_ats_hot_home': ('2020-26', 311, 228, 12.4, None), 'nba_badteams_under': ('2020-26', 153, 95, 20.6, None), 'nhl_loss_streak_over': ('2020-26', 385, 290, 10.3, None),
    'nhl_bounce_home_ml': ('2020-26', 337, 197, 10.1, None), 'mlb_road_over_under': ('2020-25', 342, 246, 12.1, None), 'nba_bigfav_over': ('2020-26', 272, 202, 10.9, None),
    'nba_roadtrip_over': ('2020-26', 190, 131, 14.2, None), 'nhl_skid_fade_road': ('2020-26', 196, 145, 20.2, None), 'cfb_day_over': ('2020-26', 311, 221, 12.4, None),
    'cfb_homefav_7510_under': ('2020-26', 188, 130, 13.6, None), 'nhl_pl_fav_gap': ('2020-26', 79, 126, 1.5, None), 'nhl_pl_fav_strong_opp': ('2020-26', 136, 222, -0.1, None),
    'nhl_pl_dog_bigml': ('2020-26', 46, 32, 5.0, None), 'nhl_early_home_fav_qual': ('2020-26', 258, 139, 9.4, None), 'nba_under_good_home_over': ('2020-26', 215, 210, -1.3, None),
    'cfb_road_dog_low_total': ('2020-26', 132, 113, 4.4, None), 'cfb_hot_over_low_total': ('2020-26', 88, 55, 18.4, None), 'cfb_road_streak_dog': ('2020-26', 212, 228, -6.4, None),
    'cbb_under_good_over_drop': ('2020-26', 495, 498, -5.0, None), 'mma_steam_fav': ('2022-26', 136, 53, 6.6, None)}
try: LABW = json.load(open(os.path.join(ROOT, 'data', 'research', 'betlabs_windows.json')))['rules']
except Exception: LABW = {}


_FILLS_BY_ID = None
def fill_header(ev, f):
    """(sport, start_utc, away, home) for a fill whose event is no longer in the events table: start from fills.jsonl, names from the
    complete ESPN schedule (data/state/hist_schedule.json + espn_teams.json)."""
    global _FILLS_BY_ID
    if _FILLS_BY_ID is None:
        _FILLS_BY_ID = {}
        try:
            for l in open(os.path.join(SD, 'fills.jsonl')):
                r = json.loads(l); _FILLS_BY_ID[r['fill_id']] = r
        except Exception: pass
    fr = _FILLS_BY_ID.get(f.get('fill_id')) or {}
    start = fr.get('start_utc')
    if not start: return None
    try: H = json.load(open(os.path.join(SD, 'hist_schedule.json'))); T = json.load(open(os.path.join(SD, 'espn_teams.json')))
    except Exception: H, T = {}, {}
    for sp, games in H.items():
        g = games.get(str(ev))
        if g:
            nm = lambda ab: (T.get(sp, {}).get(ab) or {}).get('name') or ab
            return (sp, start, nm(g.get('away')), nm(g.get('home')))
    sp = (f.get('tag') or '').split('_')[0]
    return (sp if sp in ('nba', 'nhl', 'cfb', 'nfl', 'cbb', 'mlb', 'wnba') else 'nfl', start, fr.get('participant') or '?', '?')


def sched_rec(sport, ev):
    p = os.path.join(ROOT, 'data', sport, 'schedule.json'); s = SCHED_CACHE.get(sport)
    if s is None: s = SCHED_CACHE[sport] = json.load(open(p)) if os.path.exists(p) else {}
    return s.get(ev) or {}


SCHED_CACHE = {}


def public(conn, ev, market, side):
    r = conn.execute("SELECT extra FROM ticks WHERE event_id=? AND venue='AN_Consensus' AND market=? AND side=? AND extra IS NOT NULL ORDER BY ts_utc DESC LIMIT 1", (ev, market, side)).fetchone()
    return json.loads(r[0]) if r else {}


LEAN_TAGS = {'nhl_pl_fav_gap', 'nhl_pl_fav_strong_opp', 'nhl_pl_dog_bigml', 'nba_1h_under_hot_over', 'nhl_early_home_fav_qual', 'nba_under_good_home_over', 'nba_under_good_home_over_small', 'nba_ats_hot_home', 'nba_bigfav_over', 'nhl_loss_streak_over', 'nba_badteams_under', 'nba_roadtrip_over', 'nhl_bounce_home_ml', 'nhl_skid_fade_road'}


CFB_LINE_TAGS = {'cfb_road_dog_low_total', 'cfb_road_streak_dog', 'cfb_day_over', 'cfb_homefav_7510_under', 'cfb_hot_over_low_total'}   # rules defined on the closing line


def void_fill(fired, key, why):
    """Mark a flagged bet void (not graded, no P&L) and keep the record of why."""
    rec = fired[key]; rec['void'] = True; rec['void_why'] = why; rec['void_at'] = NOW_S     # void_at: the merge keeps the later record
    if rec.get('fill_id'):
        rows = FI.load()
        for r in rows:
            if r['fill_id'] == rec['fill_id'] and r.get('result') is None:
                r['result'] = 'void'; r['pnl_units'] = 0.0; r['void_at'] = NOW_S; r['note'] = (r.get('note') or '') + f' | VOID: {why}'
        FI.save(rows)
    print(f"[systems] voided {key}: {why}")


def paper_fill(conn, eq, ev, start, market, line, side, part, tag, stake, note, venue=None, min_h=None):
    ttk = (N.parse_ts(start) - NOW).total_seconds() / 3600
    if ttk < (WINDOW_H[0] if min_h is None else min_h): return None      # inside the last hours a new trigger is shown, not filled
    if ttk > max_h(tag): return None      # weather rules: shown as an upcoming trigger, filled inside 30h; everything else fills when it triggers
    # one bet per rule per game (11/4): the fills ledger is the record, so a lost or voided state entry can never fire the same rule twice
    if any(r['event_id'] == ev and r.get('rule_tag') == f'paper:{tag}' and r.get('market') == market and r.get('result') != 'void' for r in FI.load()): return None
    best = F.best_price(eq, market, line, side, NOW_S, part)
    if venue: best = [b for b in best if b['venue'] == venue]
    if not best: return None
    b = best[0]; fr = eq.fair(market, line, side, NOW_S, part)
    imp = b['cost']; price = N.prob_to_american(imp)
    # 11/7: a main spread / total never prices past -150 / +150 at a book; days out the only quote can be a thin exchange order (Novig 75c
    # on a CFB total a week ahead, Kalshi 98c). Refuse those and fill later at a real price. Puck lines / run lines (+-1.5) are exempt.
    puck = market == 'spread' and line is not None and abs(line) == 1.5
    if market in ('spread', 'total', '1h_spread', '1h_total') and not puck and not (0.40 <= imp <= 0.60): return None
    if fr.get('fair') is not None and imp - fr['fair'] > 0.08 and not puck: return None
    row = dict(fill_id=uuid.uuid4().hex[:12], ts_utc=NOW_S, event_id=ev, start_utc=start, market=market, mclass='game', participant=part, player_name=None,
               line=line, side=side, venue=b['venue'], price_american=price, price_decimal=round(1 / imp, 4), implied=round(imp, 5), stake=stake,
               rule_tag=f'paper:{tag}', fair_at_fill=round(fr['fair'], 5) if fr['fair'] is not None else None, fair_at_fill_status=fr['status'],
               fair_at_fill_detail={k: (round(v['p'], 4) if v['p'] is not None else v['why']) for k, v in fr['detail'].items()},
               fair_weights={k: round(v, 3) for k, v in fr['weights'].items()}, late=0, note=note + (' | backfill: replayed after a missed run' if os.environ.get('SYSTEMS_BACKFILL') else ''), paper=1, **({'backfill': 1} if os.environ.get('SYSTEMS_BACKFILL') else {}))
    rows = FI.load(); rows.append(row); FI.save(rows)
    return row


# Fills written under a rule definition later found to be wrong are voided, graded or not, so they never count in that rule's record.
# nhl_pl_fav_gap ran backwards (favorite better than opponent) until the 10/31 fix; every fill before it is void.
RETRO_VOID = {'nhl_pl_fav_gap': ('2026-10-31T08:00:00Z', "fired under the reversed definition (favorite's win% above the opponent's); Bet Labs' rule is the opposite")}


# single fills voided after an input definition changed (event_id, tag) -> why
RETRO_VOID_EV = {('401873032', 'wind1014_1h'): "filled 10/31 on Open-Meteo alone (12.7 mph); on the Open-Meteo/MySportsWeather average (13.8 -> 14) it is outside the "
                                                "1H 10-13 band, and Bet Labs (14 mph) does not list it"}


def retro_void(fired):
    rows = FI.load(); ch = 0
    for r in rows:
        t = (r.get('rule_tag') or '').replace('paper:', '')
        if (r.get('event_id'), t) in RETRO_VOID_EV and r.get('result') != 'void':
            r['result'] = 'void'; r['pnl_units'] = 0.0; r['note'] = (r.get('note') or '') + ' | VOID: ' + RETRO_VOID_EV[(r['event_id'], t)]; ch += 1
        if t in RETRO_VOID and r['ts_utc'] < RETRO_VOID[t][0] and r.get('result') != 'void':
            r['result'] = 'void'; r['pnl_units'] = 0.0; r['note'] = (r.get('note') or '') + ' | VOID: ' + RETRO_VOID[t][1]; ch += 1
    if ch: FI.save(rows)
    for k, rec in fired.items():
        t = k.split(':')[1] if ':' in k else ''
        if (k.split(':')[0], t) in RETRO_VOID_EV and not rec.get('void'): rec['void'] = True; rec['void_why'] = RETRO_VOID_EV[(k.split(':')[0], t)]
        if t in RETRO_VOID and (rec.get('ts') or '') < RETRO_VOID[t][0] and not rec.get('void'):
            rec['void'] = True; rec['void_why'] = RETRO_VOID[t][1]
    if ch: print(f"[systems] retro-voided {ch} fills")


ALT_TOL = 0.02     # an alternate line is still the bet while its value (fair - cost) is within 2% of the value at the flagged number


def alt_lines(eq, f, part):
    """Sean, 11/2: where can a system bet still be placed once its number moves? For the flagged line and up to 2 points either way (half
    steps), the best bettable price and the ruler fair at that line now. value = fair - cost; 'loss' = flagged value - value at that line,
    in probability. bet_to = the furthest line in the worse direction whose loss is within ALT_TOL (or the flagged line itself)."""
    L0 = float(f['line']); side = f['side']
    worse = -1 if side in ('under', 'home', 'away') else 1          # under / a spread side: lower lines are worse; over: higher is worse
    try: fair0 = float(f.get('fair')) if f.get('fair') is not None else None
    except (TypeError, ValueError): fair0 = None
    p0 = N.implied_from_american(f['price']) if f.get('price') is not None else None
    if fair0 is None or p0 is None: return [], None
    v0 = fair0 - p0; out = []
    for k in range(-4, 5):
        L = round(L0 + worse * 0.5 * k, 1)
        try: b = F.best_price(eq, f['market'], L, side, NOW_S, part)
        except Exception: b = []
        if not b: continue
        try: fr = eq.fair(f['market'], L, side, NOW_S, part).get('fair')
        except Exception: fr = None
        c = b[0]['cost']; v = (fr - c) if fr is not None else None
        out.append(dict(line=L, steps=k, venue=b[0]['venue'], price=N.prob_to_american(c), cost=round(c, 4), fair=round(fr, 4) if fr is not None else None,
                        loss=round(v0 - v, 4) if v is not None else None))
    ok = [x for x in out if x['loss'] is not None and x['loss'] <= ALT_TOL and x['steps'] >= 0]
    return out, (max(ok, key=lambda x: x['steps']) if ok else None)


def main():
    conn = sqlite3.connect(DB)
    fired = json.load(open(FIRED)) if os.path.exists(FIRED) else {}
    # the fills ledger is the record (11/4): a bet in the ledger that the state file lost (an older checkout's commit overwrote it) is
    # restored here, so it stays on the board instead of vanishing (the duplicate guard in paper_fill would not refire it)
    have = {v.get('fill_id') for v in fired.values() if isinstance(v, dict)}
    # 11/10: a state entry that points at a fill the ledger voided as a duplicate is re-pointed at the live fill of the same bet (the board
    # showed the voided copy of SJSU @ AFA and the audit reported the live one as missing)
    dead = {r['fill_id'] for r in FI.load() if r.get('result') == 'void'}
    for r in FI.load():
        if not str(r.get('rule_tag', '')).startswith('paper:') or r['fill_id'] in have or r.get('result') == 'void' or r.get('mclass', 'game') != 'game': continue
        if N.parse_ts(r['start_utc']) < NOW - dt.timedelta(hours=6): continue
        tag = r['rule_tag'][6:]; key = f"{r['event_id']}:{tag}" + (f":{r['market']}" if tag in ('xch_homedog_fade', 'nba_momentum') else '')
        if key in fired and fired[key].get('fill_id') and not fired[key].get('void') and fired[key]['fill_id'] not in dead: continue
        fired[key] = dict(tag=tag, fill_id=r['fill_id'], ts=r['ts_utc'], market=r['market'], side=r['side'], line=r.get('line'), venue=r['venue'], price=r['price_american'],
                          fair=r.get('fair_at_fill'), edge_pts=(round(100 * (r['fair_at_fill'] - r['implied']), 2) if r.get('fair_at_fill') is not None else None),
                          why=(r.get('note') or '').split(' | ')[0], restored=True)
    retro_void(fired)
    fires_now = []; view_games = []
    for ev, start, away, home in conn.execute("SELECT event_id, start_utc, away, home FROM events WHERE sport='nfl' ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (0 < ttk <= VIEW_H): continue      # triggers visible up to a week out (like Bet Labs); fills only inside WINDOW_H (paper_fill checks)
        eq = F.EventQuotes(conn, ev); trig = {}
        wx = weather_t24(ev)
        pv = SEA.profile('nfl', away, st); ph = SEA.profile('nfl', home, st)
        sp_line, sp_n = main_line(eq, 'spread', home)       # home line
        dog = None
        if sp_line is not None and sp_line != 0: dog = 'home' if sp_line > 0 else 'away'
        et_dow = st.astimezone(N.ET).strftime('%A')
        v_prev = prev_scheduled('nfl', away, st); h_prev = prev_scheduled('nfl', home, st)
        # a team with a game still to play before this one: its record / last result are not final yet, so result-based rules wait
        pending = {t for t, pg in ((away, v_prev), (home, h_prev)) if pg and pg[0] > NOW}
        # --- rules
        msw = msw_latest('nfl', ev)
        wv, wlab = blend_wind(wx, msw)
        wr = round(wv) if wv is not None else None     # Bet Labs' wind is whole mph (checked on its 2026 picks 10/31)
        if wr is not None and 10 <= wr <= 14:
            cold = wx is not None and wx.get('temp_f') is not None and wx['temp_f'] <= 35      # 11/5 replay: the cold band is 27-27, mild weather 133-76
            trig['wind1014_cold' if cold else 'wind1014'] = wlab + (f", gust {wx.get('gust_mph')}, {wx.get('temp_f')}F" if wx else '')
            if wr <= 13: trig['wind1014_1h'] = trig['wind1014_cold' if cold else 'wind1014']      # the tested first-half screen is 10-13 mph, not 10-14
        elif wr is not None and any(x is not None and 10 <= round(x) <= 14 for x in ((wx or {}).get('wind_mph'), (msw or {}).get('wind_mph'))):
            trig['wind_msw_only'] = (f"one source in the 10-14 band but the average is {wv:.1f} mph ({wlab}); flag only" if wv is not None
                                     else f"one source in the 10-14 band ({wlab}); flag only")
        # visitor's previous game: the later of its last completed game (season log) and its last scheduled game before this one (the schedule
        # file only keeps a rolling window, the season log only has finished games); calendar days, as Bet Labs counts
        cand = [t for t in (v_prev[0] if v_prev else None, N.parse_ts(pv['last_start']) if pv.get('last_start') else None) if t is not None and t < st]
        vdays = (N.et_date(st) - N.et_date(max(cand))).days if cand else None
        if vdays is not None and 8 <= vdays <= 30:
            trig['vrest8_1h'] = f"{away} off {vdays} days"
        if et_dow == 'Monday': trig['mnf_1h'] = 'Monday night'
        if dog and (away if dog == 'away' else home) not in pending:
            dp = pv if dog == 'away' else ph; dteam = away if dog == 'away' else home
            if dp.get('games', 0) >= 1 and dp.get('margin_avg') is not None and dp['margin_avg'] <= -13:     # 11/6: back to Bet Labs' -13 or worse (the 11/5 re-band came from a replay bug)
                trig['awfuldog'] = f"{dteam} season margin {dp['margin_avg']:+.1f} over {dp['games']} games, dog {('+' if sp_line > 0 else '')}{sp_line if dog == 'home' else -sp_line}"
            dl = sp_line if dog == 'home' else -sp_line
            if 7.5 <= dl <= 10: trig['nfl_home_dog_7510' if dog == 'home' else 'nfl_road_dog_7510'] = f"{dteam} +{dl:g} at home" if dog == 'home' else f"{dteam} +{dl:g} on the road"
            # favourite off a bye: the dog on the spread (paper)
            fteam = home if dog == 'away' else away; f_prev = h_prev if dog == 'away' else v_prev; fp = ph if dog == 'away' else pv
            fc = [t for t in (f_prev[0] if f_prev else None, N.parse_ts(fp['last_start']) if fp.get('last_start') else None) if t is not None and t < st]
            fdays = (N.et_date(st) - N.et_date(max(fc))).days if fc else None
            if fdays is not None and 8 <= fdays <= 30 and fteam not in pending: trig['nfl_fade_fav_bye'] = f"{fteam} (favourite) off {fdays} days: dog {dteam}"
            if dp.get('last_ats_margin') is not None and dp['last_ats_margin'] <= -15:
                trig['bounce15_1h'] = f"{dteam} previous game ATS margin {dp['last_ats_margin']:+.1f}"
        if 'awfuldog' in trig and 'bounce15_1h' in trig: trig['awfuldog'] += ' (skipped: bounce15_1h takes the game)'; skip_awful = True
        else: skip_awful = False
        game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=sp_line, dog=dog, triggers=trig,
                    wind=wx and dict(mph=wx['wind_mph'], gust=wx.get('gust_mph'), temp_f=wx.get('temp_f'), at_h=wx['hours_to_kickoff'],
                                     msw=msw and dict(mph=msw['wind_mph'], gust=msw.get('gust_mph'), dir=msw.get('wind_dir'), rain=msw.get('rain_pct'))), fills=[])
        taken = {(f['market'], f['side']) for k, f in fired.items() if k.startswith(ev + ':') and f.get('fill_id') and not f.get('void')}   # one bet per game per market x side (a voided fill does not block)
        for tag in [t for t in ('wind1014', 'wind1014_1h', 'vrest8_1h', 'mnf_1h', 'awfuldog', 'bounce15_1h', 'nfl_home_dog_7510', 'wind1014_cold', 'awfuldog_deep', 'nfl_road_dog_7510', 'nfl_fade_fav_bye') if t in trig]:   # priority order
            why = trig[tag]
            if tag == 'awfuldog' and skip_awful: continue
            key = f"{ev}:{tag}"
            if key in fired and fired[key].get('stacked') and (fired[key]['market'], fired[key]['side']) not in taken:
                del fired[key]                    # the bet it was stacked on is gone (voided): this rule gets its own fill now
            if key in fired: game['fills'].append(fired[key]); continue
            r = RULES[tag]; market = r['market']
            if r['side'] == 'dog':
                side = dog; part = away if dog == 'away' else home
                line = (sp_line if dog == 'home' else -sp_line) if market == 'spread' else None
                if market == '1h_spread':
                    hl, hn = main_line(eq, '1h_spread', home)
                    if hl is None: continue
                    line = hl if dog == 'home' else -hl
            else:
                side = r['side']; part = None; line, n = main_line(eq, market, home)
                if line is None: continue
            if (market, side) in taken:
                fired[key] = dict(tag=tag, stacked=True, market=market, side=side, why=why + ' (same bet already taken by a higher-priority rule)'); game['fills'].append(fired[key]); continue
            row = paper_fill(conn, eq, ev, start, market, line, side, part, tag, r['stake'], why)
            if not row: continue
            taken.add((market, side))
            rec = dict(tag=tag, fill_id=row['fill_id'], ts=NOW_S, market=market, side=side, line=line, venue=row['venue'], price=row['price_american'],
                       fair=row['fair_at_fill'], edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why)
            fired[key] = rec; game['fills'].append(rec); fires_now.append(dict(game=f"{away}@{home}", **rec))
        # a bet already flagged whose trigger has since lapsed (e.g. the wind forecast moved out of range): keep it on the board,
        # marked, so a bet placed on it does not silently disappear; it stays in the ledger and is graded either way
        lapsed = [dict(f, lapsed=True) for k, f in fired.items() if k.startswith(ev + ':') and f.get('fill_id') and not f.get('void')
                  and k.split(':', 1)[1] not in trig]
        game['fills'] += lapsed
        if trig or lapsed: view_games.append(game)
    # CFB: wind >= 14 mph -> under (docs/betlabs_cfb_audit_2026-10-29.md). Only rule audited for CFB.
    for ev, start, away, home in conn.execute("SELECT event_id, start_utc, away, home FROM events WHERE sport='cfb' ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (0 < ttk <= VIEW_H): continue      # triggers visible up to a week out (like Bet Labs); fills only inside WINDOW_H (paper_fill checks)
        wx = weather_t24(ev, WX_CFB); msw = msw_latest('cfb', ev)
        wv, wlab = blend_wind(wx, msw, need_both=True)      # 11/5: CFB needs the MySportsWeather reading; Open-Meteo alone does not carry the rule
        windy = wv is not None and round(wv) >= 14
        msw_only = (not windy) and any(x is not None and round(x) >= 14 for x in ((wx or {}).get('wind_mph'), (msw or {}).get('wind_mph')))   # one source (or Open-Meteo alone) at 14+: flag, no bet
        eq = F.EventQuotes(conn, ev)
        sp_line, _n = main_line(eq, 'spread', home); tl, _n2 = main_line(eq, 'total', None); rec_s = sched_rec('cfb', ev)
        rdlt = sp_line is not None and sp_line <= -7 and tl is not None and tl <= 48 and rec_s.get('conf')
        temp = (wx or {}).get('temp_f')
        hot = (not rec_s.get('conf')) and temp is not None and temp >= 85 and wv is not None and round(wv) <= 10 and tl is not None and tl <= 55
        rs = None
        if rec_s.get('conf') and sp_line is not None and sp_line < 0 and tl is not None and tl <= 54:
            k_, n_ = road_streak('cfb', away, st)
            if n_ >= 1 and 2 <= k_ <= 5: rs = k_
        dayover = tl is not None and 45 <= tl <= 51.5 and 14 <= st.astimezone(N.ET).hour < 19     # 11/5 (Sean, cut the noise): noon kickoffs were -0.9% / +2.8% train / test; 2-7pm ET +11.7% / +13.1%, 7 of 7 seasons
        hf_under = sp_line is not None and -10 <= sp_line <= -7.5 and tl is not None
        # 11/7 (Sean's Bet Labs comparison): a logged CFB bet whose rule no longer holds on the current line before kickoff (the spread left
        # the band, the total moved past the cap) is voided, as the NBA / NHL leans already are. Only when both lines are known now.
        if sp_line is not None and tl is not None and ttk > 0:
            now_cfb = {t for t, ok in (('cfb_road_dog_low_total', rdlt), ('cfb_road_streak_dog', rs), ('cfb_day_over', dayover), ('cfb_homefav_7510_under', hf_under), ('cfb_hot_over_low_total', hot)) if ok}
            for key_ in [k for k in fired if k.startswith(ev + ':') and k.split(':')[1] in CFB_LINE_TAGS and k.split(':')[1] not in now_cfb and not fired[k].get('void')]:
                void_fill(fired, key_, f"rule no longer holds on the current line: home spread {sp_line}, total {tl} ({NOW_S})")
        if not windy and not rdlt and not msw_only and not hot and not rs and not dayover and not hf_under: continue
        game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=sp_line, dog=('away' if sp_line and sp_line < 0 else None), triggers={},
                    wind=(dict(mph=wx['wind_mph'], gust=wx.get('gust_mph'), temp_f=wx.get('temp_f'), at_h=wx['hours_to_kickoff']) if wx else None), fills=[], sport='cfb')
        if rdlt:
            why2 = f"conference game, {away} +{-sp_line} on the road, total {tl}"; game['triggers']['cfb_road_dog_low_total'] = why2; key2 = f"{ev}:cfb_road_dog_low_total"
            if key2 in fired and not fired[key2].get('void'): game['fills'].append(fired[key2])
            else:
                row = paper_fill(conn, eq, ev, start, 'spread', -sp_line, 'away', away, 'cfb_road_dog_low_total', 0.5, why2)
                if row:
                    rec_ = dict(tag='cfb_road_dog_low_total', fill_id=row['fill_id'], ts=NOW_S, market='spread', side='away', line=-sp_line, venue=row['venue'], price=row['price_american'],
                                fair=row['fair_at_fill'], edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why2)
                    fired[key2] = rec_; game['fills'].append(rec_); fires_now.append(dict(game=f"{away}@{home}", **rec_))
        if hot:
            take(conn, eq, fired, fires_now, game, ev, start, away, home, 'cfb_hot_over_low_total', 'total', tl, 'over', None, 0.5,
                 f"non-conference, forecast {temp:.0f}F, wind {wlab}, total {tl}")
        if rs:
            take(conn, eq, fired, fires_now, game, ev, start, away, home, 'cfb_road_streak_dog', 'spread', -sp_line, 'away', away, 0.5,
                 f"conference game, {away} on road game {rs} in a row, +{-sp_line}, total {tl}")
        if dayover and not windy:        # 11/5 mined angle; a windy under takes the game first
            take(conn, eq, fired, fires_now, game, ev, start, away, home, 'cfb_day_over', 'total', tl, 'over', None, 0.5, f"{st.astimezone(N.ET):%-I:%M %p} ET kickoff, total {tl}: over (mined angle)")
        if hf_under:
            take(conn, eq, fired, fires_now, game, ev, start, away, home, 'cfb_homefav_7510_under', 'total', tl, 'under', None, 0.5, f"home favourite {home} {sp_line}, total {tl}: under (mined angle)")
        if msw_only: game['triggers']['wind_msw_only'] = (f"one source at 14+ mph but the average is {wv:.1f} mph ({wlab}); flag only" if wv is not None
                                                          else f"one source at 14+ mph ({wlab}); the rule needs both sources, so flag only")   # 11/7 crash: only one source in
        if not windy: view_games.append(game); continue
        why = wlab + (f", gust {wx.get('gust_mph')}, {wx.get('temp_f')}F" if wx else '')
        game['triggers']['cfb_wind14'] = why
        key = f"{ev}:cfb_wind14"
        if key in fired: game['fills'].append(fired[key])
        else:
            line, n = main_line(eq, 'total', home)
            if line is not None:
                row = paper_fill(conn, eq, ev, start, 'total', line, 'under', None, 'cfb_wind14', 1.0, why)
                if row:
                    rec_ = dict(tag='cfb_wind14', fill_id=row['fill_id'], ts=NOW_S, market='total', side='under', line=line, venue=row['venue'], price=row['price_american'],
                                fair=row['fair_at_fill'], edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why)
                    fired[key] = rec_; game['fills'].append(rec_); fires_now.append(dict(game=f"{away}@{home}", **rec_))
        view_games.append(game)
    # NHL and NBA leans from the segment audit: one fill per game per tag, inside the normal window.
    for ev, sport, start, away, home in conn.execute("SELECT event_id, sport, start_utc, away, home FROM events WHERE sport IN ('nhl','nba') ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (0 < ttk <= VIEW_H): continue      # triggers visible up to a week out (like Bet Labs); fills only inside WINDOW_H (paper_fill checks)
        ph, pa = SEA.profile(sport, home, st, opp=away), SEA.profile(sport, away, st, opp=home)
        if ph.get('games', 0) < 1 or pa.get('games', 0) < 1: continue      # Bet Labs applies no minimum (its picks start in a team's 2nd game); 8 was ours
        eq = F.EventQuotes(conn, ev); ml_h = eq.fair('ml', None, 'home', NOW_S, home); ml_a = eq.fair('ml', None, 'away', NOW_S, away)
        p_home = ml_h.get('fair') if ml_h else None
        if p_home is None: continue
        fav, dog = (home, away) if p_home >= 0.5 else (away, home); pf, pd = (ph, pa) if fav == home else (pa, ph); fav_side = 'home' if fav == home else 'away'
        trig = {}
        if sport == 'nhl':
            # Bet Labs definitions (checked against its past picks 10/31): Win % = wins / games played (OT and shootout losses are losses),
            # each team's value truncated to a whole percent; "Win % Difference" = OPPONENT's win% minus the team's. So this rule backs a
            # favorite whose opponent has the much better record (the market rates the favorite above its record), not the reverse.
            wf, wd = int(100 * pf['win_pct']), int(100 * pd['win_pct']); rec_ = lambda p_: f"{p_['wins']}-{p_['games'] - p_['wins']}"
            if wd - wf >= 22: trig['nhl_pl_fav_gap'] = ('spread', fav_side, f"favorite {fav} is {wf}% ({rec_(pf)}) but opponent {dog} is {wd}% ({rec_(pd)}): opponent's win% higher by {wd - wf} pts")
            if wd >= 66: trig['nhl_pl_fav_strong_opp'] = ('spread', fav_side, f"opponent {dog} wins {wd}% ({rec_(pd)}); favorite {fav} -1.5 against a strong team")
            dog_side = 'away' if fav_side == 'home' else 'home'; am = open_ml(conn, ev, dog_side)     # Bet Labs filters on the OPENING moneyline
            if am is not None and 181 <= am <= 196: trig['nhl_pl_dog_bigml'] = ('spread', dog_side, f"{dog} opened +{am:.0f} on the moneyline: +1.5 on a big dog")
            if fav == home and ph['games'] + 1 <= 24 and int(100 * pd['win_pct']) >= 51:
                trig['nhl_early_home_fav_qual'] = ('ml', 'home', f"home favorite, game {ph['games'] + 1} of the season, opponent {away} wins {int(100 * pd['win_pct'])}% ({pd['wins']}-{pd['games'] - pd['wins']})")
            mined_ok = ph['games'] >= 3 and pa['games'] >= 3          # 11/5: the miner's own minimum (3 games for record features); the Bet Labs rules keep their own definitions
            if mined_ok and ph.get('loss_streak', 0) >= 3 and ph.get('over_pct') is not None and 0.40 <= ph['over_pct'] < 0.60:
                trig['nhl_loss_streak_over'] = ('total', 'over', f"home {home} has lost {ph['loss_streak']} straight, season over rate {100 * ph['over_pct']:.0f}%: over (mined angle)")
            if mined_ok and ph.get('last_margin') is not None and ph['last_margin'] <= -3 and 0.50 <= ph['win_pct'] < 0.65:
                trig['nhl_bounce_home_ml'] = ('ml', 'home', f"home {home} lost its last game by {-ph['last_margin']:.0f}, record {ph['wins']}-{ph['games'] - ph['wins']} ({100 * ph['win_pct']:.0f}%): home moneyline (mined angle)")
            if mined_ok and pa.get('last_margin') is not None and pa['last_margin'] > 0 and ph.get('loss_streak', 0) >= 3:
                trig['nhl_skid_fade_road'] = ('spread', 'away', f"{away} off a win, home {home} has lost {ph['loss_streak']} straight: road puck line (mined angle)")
        else:
            if int(100 * (pa.get('over_pct') or 0)) >= 71: trig['nba_1h_under_hot_over'] = ('1h_total', 'under', f"visitor {away} over rate {100 * pa['over_pct']:.0f}% this season; 1H under (regression lean)")
            # mined paper angles (11/5): ATS-hot home team on 2 days rest; big favourite over
            h_off0 = (N.et_date(st) - N.et_date(N.parse_ts(ph['last_start']))).days if ph.get('last_start') else None
            mined_ok = ph['games'] >= 3 and pa['games'] >= 3          # 11/5: the miner's own minimum (3 games); ATS% still needs 8 spreads
            if mined_ok and ph.get('ats_n', 0) >= 8 and ph.get('ats_pct') is not None and ph['ats_pct'] >= 0.60 and h_off0 == 2:
                trig['nba_ats_hot_home'] = ('spread', 'home', f"home {home} covers {100 * ph['ats_pct']:.0f}% of spreads this season ({ph['ats_n']} games), 2 days rest: home spread (mined angle)")
            if mined_ok and max(p_home, 1 - p_home) >= 0.85:
                trig['nba_bigfav_over'] = ('total', 'over', f"{fav} is {100 * max(p_home, 1 - p_home):.0f}% on the moneyline: over (mined angle)")
            if mined_ok and pa.get('margin_avg') is not None and -7 <= pa['margin_avg'] < -2 and ph.get('home_pct') is not None and ph['home_pct'] < 0.40:
                trig['nba_badteams_under'] = ('total', 'under', f"visitor {away} season margin {pa['margin_avg']:+.1f}, home {home} wins {100 * ph['home_pct']:.0f}% at home: under (mined angle)")
            if mined_ok and pa.get('road_streak', 0) >= 4 and pa.get('last_vs') is not None and pa['last_vs'] > 0:
                trig['nba_roadtrip_over'] = ('total', 'over', f"{away} on road game {pa['road_streak']} in a row and won the last meeting by {pa['last_vs']:.0f}: over (mined angle)")
            # Bet Labs "days between games" = calendar-day gap (back-to-back = 1); checked on its 2026 picks 10/31
            h_off = (N.et_date(st) - N.et_date(N.parse_ts(ph['last_start']))).days if ph.get('last_start') else None
            a_off = (N.et_date(st) - N.et_date(N.parse_ts(pa['last_start']))).days if pa.get('last_start') else None
            if int(100 * (ph.get('over_pct') or 0)) >= 58 and h_off is not None and a_off is not None and 1 <= h_off <= 2 and 1 <= a_off <= 3:
                tl, _n = main_line(eq, 'total', None); op = open_line(conn, ev, 'total')
                if tl is not None and op is not None and op - tl >= 0.5:
                    trig['nba_under_good_home_over' if op - tl >= 1.5 else 'nba_under_good_home_over_small'] = ('total', 'under', f"home {home} over rate {int(100 * ph['over_pct'])}%, days since last game: home {h_off}, visitor {a_off}; total {op} -> {tl}")
        # A fired bet whose trigger no longer holds on corrected inputs (e.g. a late-arriving result changed a record) is voided before kickoff.
        for key_ in [k for k in fired if k.startswith(ev + ':') and k.split(':')[1] in LEAN_TAGS and k.split(':')[1] not in trig and not fired[k].get('void')]:
            void_fill(fired, key_, f"trigger no longer holds on current season records ({NOW_S})")
        if not trig: continue
        game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=None, dog=dog, triggers={k: v[2] for k, v in trig.items()}, fills=[], sport=sport)
        for tag, (market, side, why) in trig.items():
            key = f"{ev}:{tag}"
            if key in fired and not fired[key].get('void'): game['fills'].append(fired[key]); continue
            line = None; part = None
            if market == 'spread' and sport == 'nhl':
                line = -1.5 if side == fav_side else 1.5; part = home if side == 'home' else away
            elif market == 'spread':
                hl, _n = main_line(eq, 'spread', home)
                if hl is None: continue
                line = hl if side == 'home' else -hl; part = home if side == 'home' else away
            elif market == 'ml':
                part = home if side == 'home' else away      # moneyline: no number, the team is the participant
            else:
                line, _n = main_line(eq, market, None)
                if line is None: continue
            row = paper_fill(conn, eq, ev, start, market, line, side, part, tag, 0.5, why)
            if not row: continue
            rec_ = dict(tag=tag, fill_id=row['fill_id'], ts=NOW_S, market=market, side=side, line=line, venue=row['venue'], price=row['price_american'], fair=row['fair_at_fill'],
                        edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why)
            fired[key] = rec_; game['fills'].append(rec_); fires_now.append(dict(game=f"{away}@{home}", **rec_))
        view_games.append(game)
    # CBB: Teams Off Big Loss vs Ranked Opponent (Bet Labs PRO 766983, read from the screen 11/1): previous game margin -45 to -14, opponent
    # AP rank 1-5, team unranked, conference game, regular season. Previous game = the team's last completed game in our ESPN schedule log
    # (scores from the schedule or results.jsonl), so a team's first logged game of the season never fires.
    sched_rec('cbb', ''); cbb = SCHED_CACHE.get('cbb') or {}
    res_ = {}
    rp = os.path.join(SD, 'results.jsonl')
    if os.path.exists(rp):
        for l in open(rp):
            try: r_ = json.loads(l)
            except Exception: continue
            if r_.get('status') == 'final' and r_.get('home_score') is not None: res_[r_['event_id']] = (r_['home_score'], r_['away_score'])
    hist = collections.defaultdict(list)          # ESPN team id -> [(start, margin)]
    for k, g in (cbb or {}).items():
        hs = as_ = None
        if k in res_: hs, as_ = res_[k]
        elif g.get('completed') and (g.get('home_team') or {}).get('score') not in (None, '') and (g.get('away_team') or {}).get('score') not in (None, ''):
            hs, as_ = float(g['home_team']['score']), float(g['away_team']['score'])
        if hs is None: continue
        if (g.get('home_team') or {}).get('id'): hist[g['home_team']['id']].append((g['start'], hs - as_))
        if (g.get('away_team') or {}).get('id'): hist[g['away_team']['id']].append((g['start'], as_ - hs))
    for ev, start, away, home in conn.execute("SELECT event_id, start_utc, away, home FROM events WHERE sport='cbb' ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (0 < ttk <= VIEW_H): continue
        g = (cbb or {}).get(ev) or {}
        if not g.get('conf') or g.get('season_type') not in (2, None): continue
        trig = None
        for side, me, op in (('home', g.get('home_team') or {}, g.get('away_team') or {}), ('away', g.get('away_team') or {}, g.get('home_team') or {})):
            if me.get('rank') or not op.get('rank') or op['rank'] > 5: continue
            prev = [x for x in hist.get(me.get('id'), []) if x[0] < start]
            if not prev: continue
            m = max(prev)[1]
            if -45 <= m <= -14:
                trig = (side, f"{me.get('displayName')} (unranked) lost its last game by {abs(m):.0f}; opponent {op.get('displayName')} is ranked #{op['rank']}; conference game")
        key = f"{ev}:cbb_bigloss_vs_top5"
        if not trig:
            if key in fired and not fired[key].get('void'): void_fill(fired, key, f"trigger no longer holds ({NOW_S})")
            continue
        side, why = trig
        game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=None, dog=None, triggers={'cbb_bigloss_vs_top5': why}, fills=[], sport='cbb')
        if key in fired and not fired[key].get('void'): game['fills'].append(fired[key])
        else:
            eq = F.EventQuotes(conn, ev); hl, _n = main_line(eq, 'spread', home)
            if hl is not None:
                line = hl if side == 'home' else -hl; part = home if side == 'home' else away
                row = paper_fill(conn, eq, ev, start, 'spread', line, side, part, 'cbb_bigloss_vs_top5', 0.5, why)
                if row:
                    rec_ = dict(tag='cbb_bigloss_vs_top5', fill_id=row['fill_id'], ts=NOW_S, market='spread', side=side, line=line, venue=row['venue'], price=row['price_american'],
                                fair=row['fair_at_fill'], edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why)
                    fired[key] = rec_; game['fills'].append(rec_); fires_now.append(dict(game=f"{away}@{home}", **rec_))
        view_games.append(game)
    # CBB under with two over-heavy teams once the total has dropped (rescued 766981 variant)
    for ev, start, away, home in conn.execute("SELECT event_id, start_utc, away, home FROM events WHERE sport='cbb' ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (0 < ttk <= VIEW_H): continue
        g = (cbb or {}).get(ev) or {}
        if g.get('season_type') not in (2, None) or st.astimezone(N.ET).weekday() > 4: continue      # Monday-Friday, regular season
        ph, pa = SEA.profile('cbb', home, st), SEA.profile('cbb', away, st)
        if ph.get('games', 0) < 3 or pa.get('games', 0) < 3 or ph.get('over_pct') is None or pa.get('over_pct') is None: continue
        if not (ph['over_pct'] >= 0.50 and pa['over_pct'] >= 0.59): continue
        eq = F.EventQuotes(conn, ev); tl, _n = main_line(eq, 'total', None); op = open_line(conn, ev, 'total')
        if tl is None or op is None or op - tl < 0.5: continue
        game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=None, dog=None, triggers={}, fills=[], sport='cbb')
        take(conn, eq, fired, fires_now, game, ev, start, away, home, 'cbb_under_good_over_drop', 'total', tl, 'under', None, 0.5,
             f"home {home} over {100 * ph['over_pct']:.0f}% ({ph['games']} games), visitor {away} over {100 * pa['over_pct']:.0f}% ({pa['games']}); total {op} -> {tl}")
        view_games.append(game)
    late_rules(conn, fired, fires_now, view_games)
    json.dump(fired, open(FIRED, 'w'), indent=0)
    # per-tag forward record from the ledger
    rec = collections.defaultdict(lambda: dict(n=0, graded=0, w=0, l=0, p=0, pnl=0.0, clv=[], gate=100))
    for f in FI.load():
        t = (f.get('rule_tag') or '')
        if not t.startswith('paper:'): continue
        s = rec[t[6:]]; s['n'] += 1
        if f.get('result') in ('W', 'L', 'P'):
            s['graded'] += 1; s[{'W': 'w', 'L': 'l', 'P': 'p'}[f['result']]] += 1; s['pnl'] += f.get('pnl_units') or 0
            if f.get('fair_at_close') is not None: s['clv'].append(100 * (f['fair_at_close'] - f['implied']))
    for s in rec.values():
        s['clv_avg'] = round(sum(s['clv']) / len(s['clv']), 2) if s['clv'] else None; s['n_clv'] = len(s['clv']); del s['clv']; s['pnl'] = round(s['pnl'], 3)
        s['published'] = bool(s['graded'] >= s['gate'] and (s['clv_avg'] or 0) > 0)
    # a placed bet stays on the board until its game starts (Sean, 11/4: the NBA unders vanished twice). A rule that is re-checked and
    # no longer holds voids its fill explicitly above; anything else that fired and is not void is shown, even if this run did not
    # re-evaluate its trigger (missing season data, the open line outside the 4-day price window, a skipped sport loop).
    shown = {f.get('fill_id') for g in view_games for f in g.get('fills', [])}
    byev = {g['event_id']: g for g in view_games}
    for k, f in fired.items():
        if not isinstance(f, dict) or not f.get('fill_id') or f.get('void') or f.get('stacked') or f['fill_id'] in shown: continue
        ev_ = k.split(':')[0]
        row = conn.execute("SELECT sport, start_utc, away, home FROM events WHERE event_id=?", (ev_,)).fetchone()
        if not row: row = fill_header(ev_, f)        # 11/5 late: the events table drops games once they start (the schedule logger prunes them); fall back to the fill + ESPN schedule
        if not row or N.parse_ts(row[1]) <= NOW - dt.timedelta(hours=4): continue      # 11/5 (Sean): placed bets stay on the board 4h into the game, shown as In progress
        g = byev.get(ev_)
        if g is None:
            g = dict(event_id=ev_, away=row[2], home=row[3], start_utc=row[1], hours_to_kickoff=round((N.parse_ts(row[1]) - NOW).total_seconds() / 3600, 1),
                     spread_home=None, dog=None, triggers={}, fills=[], sport=row[0]); view_games.append(g); byev[ev_] = g
        # 11/7: a weather bet that reaches this catch-all was not re-fired by its own loop, so its forecast no longer meets the rule
        # (Navy: average 13.4 mph). Show it as lapsed, not as a live play.
        if f['tag'] in WEATHER and N.parse_ts(row[1]) > NOW:
            g['fills'].append(dict(f, lapsed=True)); g['triggers'][f['tag']] = 'the latest forecast no longer meets the wind rule (see the wind reading on this game)'
        else:
            g['fills'].append(f); g['triggers'].setdefault(f['tag'], f.get('why') or '')
    for g in view_games:
        r_ = sched_rec(g.get('sport', 'nfl'), g['event_id']); g['away_name'] = (r_.get('away_team') or {}).get('displayName') or g['away']; g['home_name'] = (r_.get('home_team') or {}).get('displayName') or g['home']
        g.setdefault('sport', 'nfl'); g['league'] = sched_rec(g['sport'], g['event_id']).get('league')
        g['hours_to_kickoff'] = round((N.parse_ts(g['start_utc']) - NOW).total_seconds() / 3600, 1)
        fired_tags = {f['tag'] for f in g.get('fills', [])}
        if g['hours_to_kickoff'] < WINDOW_H[0]:      # inside the last hours a trigger without a fill cannot become a bet any more: keep it visible, labelled
            g['late'] = [t for t in g['triggers'] if t not in fired_tags and not t.startswith(('xch_', 'nba_momentum'))]
        g['fills'] = [f for f in g.get('fills', []) if not f.get('void')]
        refresh_fills(conn, g)
    view_games = [g for g in view_games if g['triggers'] or any(f.get('fill_id') for f in g.get('fills', []))]      # a lapsed bet keeps its game on the board
    json.dump(dict(built=NOW_S, window_h=WINDOW_H, rules={k: dict(v, tag=k, max_h=max_h(k), desc=DESC.get(k, ''), evidence=EVIDENCE.get(k), labs=(dict(id=LABS[k][0], name=LABS[k][1]) if k in LABS else None), wc=(dict(zip(('years', 'w', 'l', 'roi', 'note'), WC[k])) if k in WC else None), labsw=LABW.get(k)) for k, v in RULES.items()}, games=view_games, fired_now=fires_now, record=dict(rec)),
              open(VIEW, 'w'), default=str, separators=(',', ':'))
    print(f"[systems] {len(view_games)} games with triggers (shown up to {VIEW_H}h out, filled {WINDOW_H[0]}-{WINDOW_H[1]}h); {len(fires_now)} new paper fills; tags on file {dict((k, v['n']) for k, v in rec.items())}")
    conn.close()


def late_rules(conn, fired, fires_now, view_games):
    """Exchange rules that fire inside the last 90 minutes (LATE_H). Also run by sharp/late_pass.py every 20 minutes (Sean, 11/4: the
    3-a-day systems run only saw games starting 6 to 7 PM in that window)."""
    # Exchange rules, inside T-1.5h. One fill per game per rule; stacking across rules allowed only on different market x side.
    def xmid(eq, venue, market, line, side, part, ts):
        q = eq.latest(venue, market, line, side, ts, 90, part)
        if not q or q[6] is None or q[7] is None or (q[7] - q[6]) > 0.04: return None
        return (q[6] + q[7]) / 2
    for ev, sport, start, away, home in conn.execute("SELECT event_id, sport, start_utc, away, home FROM events WHERE sport IN ('nfl','nba','cfb','nhl','mlb') ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (LATE_H[0] <= ttk <= LATE_H[1]): continue
        eq = F.EventQuotes(conn, ev); game = None
        def fire(tag, market, line, side, part, venue, why, stake=0.5):
            nonlocal game
            key = f"{ev}:{tag}:{market}"
            if key in fired: return
            row = paper_fill(conn, eq, ev, start, market, line, side, part, tag, stake, why, venue=venue, min_h=LATE_H[0])
            if not row: return
            rec_ = dict(tag=tag, fill_id=row['fill_id'], ts=NOW_S, market=market, side=side, line=line, venue=row['venue'], price=row['price_american'], fair=row['fair_at_fill'],
                        edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why)
            fired[key] = rec_; fires_now.append(dict(game=f"{away}@{home}", **rec_))
            if game is None:
                game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=None, dog=None, triggers={}, fills=[], sport=sport); view_games.append(game)
            game['triggers'][tag] = why; game['fills'].append(rec_)
        # xch_homedog_fade: Novig home side two-sided at 20-35c -> buy the away side on Novig (section 9 of the audit: +12% at the close, z -2.5 on the home side)
        for market in ('ml', 'spread'):
            line = None
            if market == 'spread':
                line, _n = main_line(eq, 'spread', home)
                if line is None: continue
            ph = xmid(eq, 'Novig', market, line, 'home', home, NOW_S)
            if ph is not None and 0.20 <= ph <= 0.35:
                fire('xch_homedog_fade', market, (-line if line is not None else None), 'away', away, 'Novig', f"Novig home side mid {ph:.3f} inside T-{ttk:.1f}h; audit band 20-35c")
                break
        # nba_momentum: exchange two-sided mid moved >= 3c since T-6h -> continuation at that exchange
        if sport == 'nba' and 'nba_momentum' in RULES:   # retired 11/9: out of RULES, so it no longer fires
            t6 = N.iso(st - dt.timedelta(hours=6))
            for market in ('ml', 'spread', 'total'):
                line = None; part_h, part_a = home, away
                if market == 'spread': line, _n = main_line(eq, 'spread', home)
                elif market == 'total': line, _n = main_line(eq, 'total', None); part_h = part_a = None
                if market != 'ml' and line is None: continue
                side_h = 'home' if market != 'total' else 'over'
                for venue in ('Novig', 'Kalshi'):
                    p_now = xmid(eq, venue, market, line, side_h, part_h, NOW_S); p_6 = xmid(eq, venue, market, line, side_h, part_h, t6)
                    if p_now is None or p_6 is None or abs(p_now - p_6) < 0.03: continue
                    up = p_now > p_6
                    side = side_h if up else ('away' if market != 'total' else 'under'); part = (part_h if up else part_a) if market != 'total' else None
                    fire('nba_momentum', market, (line if (up or market == 'total') else -line) if line is not None else None, side, part, venue,
                         f"{venue} {market} mid {p_6:.3f} at T-6h -> {p_now:.3f} now ({100 * (p_now - p_6):+.1f}c); continuation (audit section 3, NBA only)")
                    break


def refresh_fills(conn, g):
    """Current best price, ladder and bet-to number for each live fill on a game (board columns Price / Bet to)."""
    g['fills'] = [f for f in g.get('fills', []) if not f.get('void')]
    live = [f for f in g.get('fills', []) if f.get('fill_id') and not f.get('stacked')]
    if live:
        eq = F.EventQuotes(conn, g['event_id'])
        for f in live:
            part = None if f['market'].endswith('total') else (g['home'] if f['side'] == 'home' else g['away'])
            try: best = F.best_price(eq, f['market'], f['line'], f['side'], NOW_S, part)
            except Exception: best = []
            f['now'] = dict(venue=best[0]['venue'], price=N.prob_to_american(best[0]['cost'])) if best else None
            if f['market'] != 'ml' and not f['market'].endswith('_ml') and f.get('line') is not None and not (g.get('sport') in ('nhl', 'mlb') and f['market'].endswith('spread')):   # puck / run lines: a different number is a different bet
                f['ladder'], f['bet_to'] = alt_lines(eq, f, part)
                if not best and f['bet_to']:               # the flagged number is gone but a nearby one keeps the value (Sean, 11/2: Celtics Under 217 -> 216.5)
                    x = f['bet_to']; f['now'] = dict(venue=x['venue'], price=x['price'], line=x['line'], alt=True)



if __name__ == '__main__':
    main()
