# Odds API replay, 11/5/2026: every rule re-graded on 2020-26 Pinnacle closes

Data: The Odds API history (`data/oddsapi/compact/*.jsonl.gz`, 1.93M snapshot rows, 116,915 games, 18 sports), folded into
`data/oddsapi/odds.sqlite` by `sharp/odds_db.py` (rebuild ~2 min). Results: ESPN (`data/state/hist_schedule.json`) for team sports and
MMA, Tennis Abstract for tennis. Everything is graded on RESULTS at the Pinnacle close, flat stakes; CLV is computed but is not the score.

Two data fixes made today that change earlier numbers: (1) the Odds API sometimes swaps home/away between snapshots of one event (MMA
especially); snapshots are now oriented to the first one seen; (2) team season profiles (record, over %, rest) now reset each season.
Scripts: `sharp/rule_replay.py` (our rules), `sharp/nfl_replay.py` (NFL + weather), `sharp/market_replay.py` (generic market tests,
all sports), `sharp/tennis_form.py` and `sharp/tennis_market.py` (tennis). Output JSON in `data/research/`.

## Our rules, re-graded

| rule | replay | seasons + | verdict |
|---|---|---|---|
| wind1014 (NFL under, wind 10-14) | 160-103-3, +17.8% | 6 of 7 | keep, tier A. Mild weather 133-76 (+23%); 35F or colder 27-27 -> cold games are paper (`wind1014_cold`). Total <= 44 inside the band 90-50 |
| awfuldog | margin -7 to -13: 91-75-5, +5.6%; -13 or worse (the old live band): 14-16, -11% | 5 of 7 | re-banded to -7..-13, tier C; deep band paper |
| bounce15 (full-game cousin) | 124-102-5, +6.0% | 5 of 7 | keep (1H not in the data) |
| vrest8 (full-game cousin) | 127-93-2, +11.9%, but 48-49-2 since 2024 | 5 of 7 | tier C |
| mnf under | 71-56-2, +8.1%; SNF 60-46-2 +10.2%; TNF 59-57 | 5 of 7 | keep |
| nhl_early_home_fav_qual | 269-155 ML, +7.1% (+6.9% best US) | 6 of 7 | keep, tier B: the best-replicating rule |
| nhl_pl_fav_gap | 94-131 at -1.5, +12.0% ROI (plus money) | 5 of 7 | tier C: two seasons carry it |
| nhl_pl_fav_strong_opp | 141-238 at -1.5, -1.6% | 3 of 7 | paper |
| nhl_pl_dog_bigml | 46-32 at +1.5, +5.0% | 4 of 7 | tier C |
| nba_under_good_home_over | 200-188-4, +0.5% (control without the drop -5.4%) | 3 of 7 | paper |
| nba_1h_under_hot_over (full-game cousin) | 131-129-4, -1.9% | - | 1H line not in the data; cousin shows nothing. Left at tier B per Sean, flagged |
| cbb_under_good_over_drop | 422-418-7, -4.1% (only 2020-21 positive) | 1 of 6 | paper |
| cfb_road_dog_low_total (no conference flag) | 210-197-13, -0.1%; 11-29 in 2026 | 4 of 7 | paper |
| cfb_road_streak_dog | 212-228-9, -6.4% | 2 of 7 | paper |
| tennis hot favourite (tour) | all: +1.9% vs close, -0.6% ROI; SETTLED: 142-31, about +9% ROI, positive every year | 5 of 5 | tier C only when settled (same surface previous event, 4+ of last 10 on it, 8-27 days rest, first match); rest paper |

## New rules from the replay

- `nfl_home_dog_7510` (tier C): home dog +7.5 to +10 at the close, 47-25-1 (+23%); all dogs in the band 136-97-3 (+10.3%, 6 of 7).
  Road version paper. The band does nothing in NBA, CBB, CFB (negative) or WNBA: NFL-specific.
- `nfl_fade_fav_bye` (paper): favourite off a bye is 120-143-7 ATS (-9.9%); take the dog.
- NFL totals: follow a 0.5-1 point move (down -> under 50-33, up -> over 34-26); fade a 1.5+ up move (under 23-11). CFB agrees on the
  small up move (over 430-358, +4.8%, 6 of 7); NBA only on large up moves (+4.8%, 5 of 6). Not a rule yet; feeds the sharp-action weighting.

## What the market does and does not price (all sports)

- Closing spreads and moneylines are efficient in every band tested in NBA, NHL, CBB, CFB; the only persistent bands are NFL dogs 7.5-10
  and NFL road dogs at exactly +3 (71-57-9, +7.9%). CBB and NBA home dogs of 10.5-14 lose (-8 to -10%).
- Following or fading the open-to-close spread move at the close is 50/50 everywhere. But the side the market moves toward, taken at its
  OPENING price, wins in every sport (NBA large moves +22%, NHL medium +11.7%, CFB medium +5.8%, MMA large +19.7%). The edge is in being
  early on the sharp side, which is what the sharp tracker is for; it is gone by the close.
- MMA is the exception: a 6+ point move toward the favourite is still worth following at the close (136-53, +6.6%, 4 of 5 years); fading
  large MMA moves is -19.7%. Candidate rule once the MMA open is tracked live.
- A US book lagging Pinnacle by half a point is not a free edge: the stale number loses at the stale book's price (alt-line juice), and
  Pinnacle's side at Pinnacle's price is break-even.
- Rest: back-to-back teams lose on the moneyline in NBA (-6%) and NHL (-12%) but that is priced; rested (3+) vs b2b ATS in NBA +5.7% (4 of 5).
- Tennis: no band, surface, format or move angle beats the close; US books beat Pinnacle's fair by 2%+ in 0.6% of matches. The settled hot
  favourite is the one thing the close misses, and it does not depend on the market moving (flat market: 104-20).
- WNBA early-season dogs ATS 66-43-4 (+16%, 3 of 3) and dogs 10.5+ (+6%): small samples, paper candidates.

## Still to do
Soccer plans (La Liga, Bundesliga, Eredivisie, EFL Cup partial; Serie A, UCL, MLS, Liga MX, the rest not started) are re-running on
GitHub; MLB/WNBA/WNCAAB results backfill is running; props puller not yet run; EPL team map misses relegated clubs (1,142 of 2,232 joined).
