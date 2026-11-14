# Bet Labs inventory (Tested:/Tracked: systems), 11/14/2026

Source: Sean's Bet Labs account, all 171 saved systems listed by Bet Labs itself; 32 start with Tested: (23) or Tracked: (9). Every one maps to a rule in sharp/systems.py. Tiers were not changed (live = tier A/B/C, paper = P). Filters are as Bet Labs shows them; every screen is regular season.

| Bet Labs system | Sport | Bet | Filters | Grade / ROI | Record | Rule | Live/paper | Status | Note |
|---|---|---|---|---|---|---|---|---|---|
| Tested: NBA Big Visitor Fav 85 Pct Over (1799444) | NBA | total over | Home ML +650 or longer | D / -5.5% | 113-118 | nba_bigfav_over | live (C) | DIFFERENT FILTERS | fixed: -650/+650 (85.5% no-vig), no games minimum |
| Tested: NBA Big Home Fav 85 Pct Over (1799443) | NBA | total over | Home ML -650 or shorter | D / -2.7% | 1347-1342 | nba_bigfav_over | live (C) | DIFFERENT FILTERS | fixed: was 85% no-vig and a 3-game minimum |
| Tested: NBA Weak Visitor at Home Team Under 40 Pct Under (approx) (1799442) | NBA | total under | Home game 9-82, home win 0-40%, visitor win 30-45% | D / -1.1% | 978-949 | nba_badteams_under | live (C) | DIFFERENT FILTERS | fixed: was visitor margin -7 to -2 and home win% at home |
| Tracked: MLB Visitor Over 60 Pct Under (1799441) | MLB | total under | Visitor game 16-162, visitor over 60-100% | D / -2.2% | 1287-1273 | mlb_road_over_under | paper (P) | MISSING | added: had a rule entry but no firing code; fires in season |
| Tracked: CFB Home Fav 7.5 to 10 Under (1799440) | CFB | total under | Home spread -10 to -7.5 | A / +4.0% | 614-527 | cfb_homefav_7510_under | live (C) | MATCHES |  |
| Tracked: CFB Afternoon Game 2-7pm ET Total 45 to 51.5 Over (1799439) | CFB | total over | Kickoff 14:00-18:59 ET, total 45-51.5 | D / -1.7% | 889-858 | cfb_day_over | paper (P) | MATCHES |  |
| Tracked: NBA Visitor 4th Plus Straight Road Game Over (1799438) | NBA | total over | Visitor's previous game road streak 3-30 | D / -2.9% | 1688-1686 | nba_roadtrip_over | paper (P) | DIFFERENT FILTERS | fixed: dropped the last-meeting filter, streak 3+ before this game |
| Tracked: NFL Dog vs Favorite Off Bye ATS (1799435) | NFL | spread dog | Opponent off 8-30 days, dog | D / -4.6% | 560-581 | nfl_fade_fav_bye | paper (P) | MATCHES |  |
| Tracked: NFL Road Dog 7.5 to 10 ATS (1799434) | NFL | spread dog | Spread 7.5-10, dog, visitor | D / -3.5% | 311-306 | nfl_road_dog_7510 | paper (P) | MATCHES |  |
| Tracked: NFL Home Dog 7.5 to 10 ATS (1799433) | NFL | spread dog | Spread 7.5-10, dog, home | A / +10.7% | 119-85 | nfl_home_dog_7510 | live (C) | MATCHES |  |
| Tested: NBA Home ATS 60 Pct Rest 2 Days (1799432) | NBA | spread home | Game 9-82, 2 days between, ATS 60-100%, home | D / -1.4% | 879-852 | nba_ats_hot_home | live (C) | DIFFERENT FILTERS | fixed: games played 8+ (was 8 spreads), whole-percent ATS |
| Tested: NHL Road Off Win vs Home Lost 3 Plus PL (1799431) | NHL | puck line visitor | Opp losing streak 3-12, previous margin +1 to +20, visitor | D / -3.1% | 861-887 | nhl_skid_fade_road | live (C) | DIFFERENT FILTERS | fixed: ranges capped like Bet Labs, no 3-game minimum |
| Tracked: NHL Bounce Home Off 3 Plus Goal Loss ML (1799430) | NHL | ML home | Win 50-64%, previous margin -20 to -3, home | B / +1.5% | 876-591 | nhl_bounce_home_ml | live (C) | DIFFERENT FILTERS | fixed: whole-percent win 50-64, margin floor -20, no 3-game minimum |
| Tracked: NHL Home Lost 3 Straight Over (1799428) | NHL | total over | Home over 40-59%, home recent win 0% | D / -0.4% | 1186-1155 | nhl_loss_streak_over | paper (P) | DIFFERENT FILTERS | fixed: no 3-game minimum |
| Tested: CFB Hot Weather Over Total 55 or Less (1792204) | CFB | total over | Total 0-55, wind 0-10, non-conf, 85-106F | A / +14.2% | 175-120 | cfb_hot_over_low_total | live (B) | MATCHES | wind from MySportsWeather by design |
| Tested: CFB Conf Road Streak Dog Total 54 or Less (1792198) | CFB | spread dog | Dog, total 0-54, road streak 2-5, bets vs daily avg 1.01+, conf | A / +15.9% | 179-121 | cfb_road_streak_dog | paper (P) | DIFFERENT FILTERS | fixed: the bet-count filter is taken from the Bet Labs list while the snapshot is fresh |
| Tested: CBB Under Good Over Teams Total Down (1792184) | CBB | total under | Total down 0.5+, Mon-Fri, home over 50%+, visitor over 59%+, home OU streak 0-3 | D / +5.4% | 797-661 | cbb_under_good_over_drop | paper (P) | DIFFERENT FILTERS | fixed: home OU streak added; Sean's 6-game minimum kept |
| Tested: CBB Unranked Off 14 Plus Loss vs Top 5 Conf (1789287) | CBB | spread | Conf, unranked, opp top 5, previous margin -45 to -14 | A / +20.3% | 151-92 | cbb_bigloss_vs_top5 | live (C) | MATCHES |  |
| Tested: CFB Conf Road Dog 7 Plus Total 48 or Less (1789286) | CFB | spread visitor | Conf, spread 7+, visitor, total 0-48 | A / +12.4% | 520-373 | cfb_road_dog_low_total | paper (P) | MATCHES |  |
| Tested: NBA Under Good Home Over Team Rest Total Down (1789285) | NBA | total under | Total down 0.5-9, visitor 1-3 days, home 1-2 days, home over 58%+ | A / +9.7% | 754-580 | nba_under_good_home_over | live (C) | MATCHES | split by the size of the drop: 1.5+ live, 0.5-1.0 paper (nba_under_good_home_over_small) |
| Tested: NHL Early Season Home Fav vs Quality Opp ML (1789284) | NHL | ML home | Home fav, opp win 51%+, game 1-24 | A / +3.8% | 1177-756 | nhl_early_home_fav_qual | live (B) | MATCHES |  |
| Tested: NBA 1H Under Visitor Over Pct 71 Plus (1784158) | NBA | 1H total under | Visitor over 71%+ | A / +7.9% | 431-340 | nba_1h_under_hot_over | paper (P) | MATCHES |  |
| Tested: NHL Puck Line Dog Open ML 181 to 196 (1784156) | NHL | puck line dog | Open ML +181 to +196, dog | A / +6.1% | 709-417 | nhl_pl_dog_bigml | paper (P) | MATCHES |  |
| Tested: NHL Puck Line Fav vs Opp Win Pct 66 Plus (1784155) | NHL | puck line fav | Opp win 66%+, fav | A / +11.9% | 552-851 | nhl_pl_fav_strong_opp | paper (P) | MATCHES |  |
| Tested: NHL Puck Line Fav Win Pct Gap 22 Plus (1784154) | NHL | puck line fav | Win% difference 22+, fav | A / +14.4% | 342-496 | nhl_pl_fav_gap | paper (P) | MATCHES |  |
| Tested: CFB Wind 14 Plus Under (1783043) | CFB | total under | Wind 14-99 | A / +12.2% | 555-402 | cfb_wind14 | live (C) | MATCHES | wind from MySportsWeather by design |
| Tested: NFL 1H Monday Night Under (1772963) | NFL | 1H total under | Monday, dome closed N | A / +11.1% | 169-119 | mnf_1h | live (C) | DIFFERENT FILTERS | fixed: roofed games excluded |
| Tested: NFL 1H Visitor Off 8 to 30 Days Under (1772962) | NFL | 1H total under | Visitor 8-30 days between, dome closed N | A / +7.2% | 459-361 | vrest8_1h | live (C) | DIFFERENT FILTERS | fixed: roofed games excluded |
| Tested: NFL 1H Blowout Bounce Dog ATS (1772929) | NFL | 1H spread dog | Previous ATS margin -60 to -15, dog | A / +6.5% | 430-342 | bounce15_1h | paper (P) | MATCHES |  |
| Tested: NFL Awful-Team Dog ATS (1772776) | NFL | spread dog | Season margin -40 to -13, dog | A / +17.2% | 254-164 | awfuldog | live (C) | MATCHES |  |
| Tested: NFL Wind 10-14 Under (1772775) | NFL | total under | Wind 10-14 | A / +13.2% | 536-379 | wind1014 | live (A) | MATCHES | wind from MySportsWeather by design |
| Tested: NFL 1H Wind 10-13 Under (769171) | NFL | 1H total under | Wind 10-13, dome closed N | A / +9.2% | 406-302 | wind1014_1h | live (C) | MATCHES | wind from MySportsWeather by design |
