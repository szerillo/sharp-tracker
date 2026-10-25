# Bet Labs NFL audit — 2026-10-25 (final)

Source: Sports Insights Bet Labs (NFL regular season, 2003–present), queried through the screen data service on the user's own
screens. Bet Labs grades every system at the **closing line** at -110 (breakeven 52.38 %); moneylines at the closing price.

## Method
- Split at 03/01/2021: **train** 08/01/2003–02/28/2021 (~4,600 games), **holdout** 03/01/2021–10/24/2026 (~1,450 games).
- For every numeric filter on a screen (137–197 per bet side), scan every contiguous window of filter values with n ≥ 300 in
  train, keep the window with the best in-sample z (win % vs 52.38 % for spreads/totals; ROI for moneylines), then grade that
  exact window on the untouched holdout.
- For every list filter (day, week, time zone, divisional, streaks, prev-game fav/dog, playoff-last-year…) and the rest-day
  ranges, read every value's record on both halves.
- A rule is reported "alive" only if it is positive on both halves with n ≥ 100 in the holdout, has a plausible mechanism, and
  passes a monotonicity look (adjacent bins move the same way; an isolated spike is noise).
- Reference for what noise looks like: with ~150–200 filters scanned per side, the best in-sample z lands at 2.2–3.7 **every
  time**, and 19–36 of the top-40 training windows go negative on the holdout. Anything that only clears the train half is
  nothing.

## Verdict table

| Market | Scanned | Survivors | Call |
|---|---|---|---|
| FG Under | 139 numeric + situational | wind 10–14 mph | **alive** |
| FG Over | full scan + situational | none (29/40 flip) | dead |
| 1H Under | full scan + situational | wind 10–13; visitor ≥8 days rest; Monday night | alive / lean / lean |
| 1H Over | full scan | none (36/40 flip) | dead |
| Spread Fav (all, home, visitor) | 138 × 3 + situational | none (max z 2.4; 27–29/40 flip) | dead |
| Spread Dog (all, home, visitor) | 138 × 3 + situational | "awful team" family | lean |
| ML Favorite | 137 | none (max z 1.9; 32/40 flip) | dead |
| ML Dog | 137 | none robust (22/40 flip; survivors are stat slivers) | dead |
| 1H Spread Fav | 111 + situational | none (max z 2.9; 26/40 flip) | dead |
| 1H Spread Dog | 111 + situational | blowout bounce (prev ATS margin ≤ −20) | **lean, best version** |
| 1H ML Fav | 110 | none (max z 2.4; 25/40 flip) | dead |
| 1H ML Dog | 110 | awful-team / blowout family again, mixed | lean (same family) |
| SI systems (Pythag, Team ATS, Bad-vs-Good ATS, Fade Covering) | as built | all negative since 2021 | dead |

## 1. The SI systems he was sent
| System | Since 2021 | Verdict |
|---|---|---|
| Pythagorean | **75-92** | dead |
| Team ATS Records | 27-33 (last 3 yrs) | dead |
| Bad ATS vs Good ATS | 20-24 (subset of the above) | dead |
| Fade Covering Teams | 53-32 in 2021–23, **38-50** since | dead |
| NFL Wind (unders) | positive | alive — §2 |
Four of five are the classic Bet Labs failure: tuned on 2003–2020, flat-to-negative out of sample.

## 2. Full-game totals
### Under — wind 10–14 mph (outdoor)
- All years **533-376 (58.6 %)**, 19 of 24 seasons positive; train 384-293 (56.7 %), holdout **149-83 (64.2 %)**.
- By mph, train / holdout under %: 0–9 mph sits at 46–51 / 42–57 (noise around 50); **10: 55/72, 11: 61/61, 12: 50/54, 13:
  59/59, 14: 60/75**; 15–19 mph back to ~50 with small n. A step at 10 mph, not a gradient — books move totals for extreme
  wind and ignore moderate wind.
- Robust to the total's move (works up or down; best when the total moved up 1–2: 112-62). Temperature 46–60 °F best
  (160-82); freezing games 41-42 (cold alone is priced).
- Caveat: Bet Labs wind is **observed** game-time wind. We can only bet on a **forecast**, which is weaker by construction.
### Under — everything else: nothing
139 numeric filters: top-40 train windows 19/40 negative on holdout. Rest, bye, travel, week, primetime, divisional, previous
margin, streaks, public-money and line-move bands all 47–54 % on both halves.
### Over: nothing
Full scan 29/40 flip negative; no weather, dome, pace, public, line-move or situational family produces an over edge at the close.
Overs are efficiently priced in this data set — tested, not assumed.

## 3. First-half totals
### Under
- **Wind 10–13 mph → 1H Under**: train 291-212 (57.9 %), holdout 112-88 (56.0 %); 10–14 all years 448-342, holdout 132-94
  (58.4 %). Same mechanism, thinner market, second outlet when the full-game number is already bet.
- **Visitor off ≥ 8 days (bye / long week) → 1H Under**: train 319-271 (54.1 %), holdout **135-86 (61.1 %)**; 8–10 days all
  years 286-219 (56.6 %). Home off ≥ 8 days: train 273-240, holdout 127-92 (58.0 %). Home on 4–6 days rest is the opposite
  (train 45.0 %) — don't play under on short-rest home teams. Lean: the train half is only 54 %.
- **Monday night → 1H Under**: train 122-87 (58.4 %), holdout 46-31 (59.7 %); Thursday 51/50 %, Sunday 51/51 %. One
  standalone game with public over money and slow starts is a plausible story; n = 286. Lean.
- 1H Under overall since 2021: 532-485 (52.3 %) — no market-wide drift. Under dollars ≥ 70 %: 55.9 % holdout but 38-38
  pre-2021 — not promoted. Closing-total bins alternate above/below 50 — noise.
### Over: nothing (36/40 flip).

## 4. Spreads
Six full scans (Fav/Dog × all/home/visitor) plus situational families on both sides.
- **Favorites**: nothing anywhere. Max in-sample z 2.0–3.1, 27–29/40 flip negative. Rest days 46–57 % scattered with no
  pattern; no streak, week, day, time-zone or divisional cell clears 55 % on both halves.
- **Dogs — the "awful team" family (lean)**: dogs whose season numbers are terrible cover more than the market expects.
  Season margin avg ≤ −13: train 236-166 (58.7 %), holdout 57-33 (63 %); Pythagorean win % < 20: 244-165 (59.7 %) / 42-32
  (57 %); win % ≤ 12: 54 % / 61 %; season ATS margin ≤ −7 (visitor dogs): 63 % / 58 %. Caveat: season averages are extreme
  early, so most of the sample is weeks 2–4 (a team blown out in its first games). Training stays positive from game 5 on
  (124-73), holdout from game 5 on is 11-12. Mechanism (overreaction to blowouts) is real but the bettable sample is small —
  track as a lean, half stake.
- **Dog buy-low downgraded to noise**: dog on a 3-game losing streak is 58 %/58 %, but −2 games is 48 %/45 % and −4 is 45 %/52 %
  — an isolated spike. Dog after a 22+ point loss (83-63) is flat across adjacent margin bins in training.
- Big home dogs (+7 to +14.5): 54 % train / 62 % holdout (n 100) — old lean, weak train half, not promoted.
- Public money / ticket % / line move at close: nothing. Fading 76 %+ ticket favourites → dog 53.3 %, inside noise.

## 5. Moneylines (ranked by ROI, not win %)
- Favorites: every band negative; best in-sample window z 1.9; 32/40 flip. Dead.
- Dogs: 22/40 flip; the "both-positive" list is narrow stat slivers (opp sack % 2.9–3.0, defensive yards 355–366…). Dog after a
  blowout ATS loss is flat in training by margin bin. By game number, no pattern. Dead.

## 5b. First-half sides (screens 1772929 spread, 1772928 ML — opened 10/25 04:20)
- **1H spread favorites**: nothing. Max in-sample z 2.9, 26/40 flip; no situational cell clears 55 % on both halves.
- **1H spread dogs — blowout bounce (the cleanest version of the family)**: dog whose previous game ATS margin was −20 or worse
  → 1H cover. By 5-point bin, train / holdout cover %: −30: 61/–, −25: 57/61, −20: 53/62, −15: 52/42, −10: 49/50, −5: 49/45,
  0: 51/48. Aggregate ≤ −20: train 254-203 (55.6 %), holdout **94-58 (61.8 %)**. Gradient in training, consistent in holdout,
  same direction as the full-game spread (dog after a 22+ loss 83-63) and 1H ML dog (prev ATS margin −22..−15: +18 % / +12 %
  ROI). Favorites after a blowout show nothing (50/51 %) — the bounce is a dog phenomenon, i.e. the market over-shades the
  team that just got embarrassed. Still a lean: ~450 training games, 150 holdout.
- Season ATS margin avg ≤ −8 on 1H spread dogs: 59.4 % / 58.5 % — the same "awful team" family as §4.
- **1H ML**: favorites dead (25/40 flip). Dogs 28/40 flip; survivors are the blowout/awful-team family (season ATS margin ≤ −8:
  +24.8 % / +11.6 % ROI) but season-margin itself flips negative (−2.2 %) — treat as the same lean, express it on the 1H spread.
- 1H situational (rest, bye, day, week, time zone, divisional, streaks) on both sides: nothing.
- The "3-game skid" and "Week 10" cells that pop on 1H dogs are isolated spikes (adjacent bins flat) — noise.

## 5c. Market-flow families: steam, RLM, public/sharp money, line moves (scratch screens, deleted afterwards)
- **Steam chasing: cannot be tested in Bet Labs.** The Steam Moves field is populated for ~340 training games and only **14
  games since 2021** — the feed is dead. Training alone: dog with 1 steam move 157-130 (54.7 %), dog when the *favourite*
  steamed 152-135 (53 %) — both sides "positive", which is what a stale, inconsistently-tagged field looks like. Steam /
  move-chasing goes to the forward tracker (Pinnacle limit growth, Novig/Kalshi/Polymarket tape, Test E/F), not to history.
- **Sharp-vs-square money on spreads: small, stable.** Dog when spread money % − ticket % ≥ +10: all years **394-340 (53.7 %)**,
  train 155-134 (53.6 %), holdout 239-206 (53.7 %). Mirror image on favourites (money ≥ 10 below tickets): 46.3 % / 46.3 %.
  ≈ +2.5 % ROI at −110: real, consistent, thin. Stricter cut (≥ +15) is weaker (51–52 %), so it is not a "bigger divergence,
  bigger edge" effect. Use as a confirmation input, not a stand-alone system.
- **Reverse line movement on dogs**: unpopular dog (≤ 35 % tickets) with the line moving toward it: 48–56 % train, 44–50 %
  holdout. Nothing. Line moving *against* the unpopular dog: 54 % / 49–55 %. Nothing.
- **Fade heavy public favourites** (≥ 65 % tickets): favourite covers 48–51 % both halves overall; by line move, no bin is
  consistent. The "fade 76 %+" cell is 53.3 % for the dog — inside noise (reported earlier).
- Ticket % alone, dollars % alone, bets z-score (how heavily bet the game is), juice: all 49–53 % in every bin on both halves,
  both sides.
- **Totals money flow**: Over/Under ticket %, under dollars %, O/U money-vs-ticket diff, open→close total move, juice — no bin
  agrees across halves. Under dollars ≥ 70 % is 94-53 (64 %) in holdout but 26-29 in training (noted before, not promoted).
  Totals steam: same dead field.
- Betting-% fields exist only from ~2005/06 and come from SI's own book panel, so the "sharp money" lean rests on one data
  vendor's definition of money %.

## 5d. Do the dog leans stack? (A = awful team, season margin ≤ −13; B = bounce, prev ATS margin ≤ −15)
Full-game spread, dogs (train / holdout cover %):
| Cell | Train | Holdout |
|---|---|---|
| A | 203-133 (60.4) | 51-31 (62.2) |
| B | 324-276 (54.0) | 112-80 (58.3) |
| A ∧ B | 80-47 (63.0) | 22-13 (62.9) |
| A only | 123-86 (58.9) | 29-18 (61.7) |
| B only | 244-229 (**51.6**) | 90-67 (57.3) |
First-half spread, dogs: A 185-133 (58.2) / **42-42 (50.0)**; B 312-258 (54.7) / 117-80 (59.4); A∧B 74-44 (62.7) / 20-16;
B only 238-214 (52.7) / 97-64 (60.2).
- About a quarter of awful-team games are also bounce games. On full-game spreads the bounce's training edge is mostly those
  overlap games (B-only 51.6 %); on 1H spreads the bounce stands alone in holdout (60.2 %) while awful-team dies (50.0 %).
- The A∧B cell is 35 holdout games — not enough to justify a bigger stake when both fire. Rule for the tracker: **when both
  trigger, it is one bet, not two** (full-game spread for A, 1H spread for B; if the same game fires both, take the 1H spread
  and skip the FG, since A's 1H record is flat).
- Sharp-money (C, money % − ticket % ≥ 10) could only be tested on the ~30 % of games with betting-% data; A∧C 18-7 / 18-8 and
  B∧C 28-26 / 44-28 are too small to say anything.

## 5e. Referees (Official field, Under side)
18 referees with ≥ 30 games since 2021. Their 2015–20 under rate does not predict 2021+: Vinovich 61 → 52 %, Rogers 26 → 50,
Boger 36 → 56, Hussey 56 → 51, Allen 55 → 50. Only Hochuli (54 → 60) and Hill (63 → 57) are above 50 % in both windows —
roughly the 4–5 of 18 chance predicts. No referee system; the Official field is not a usable totals input.

## 6. Bet Labs systems created 10/25 (all prefixed "Tested:" = built here, not a Bet Labs/SI system)
| Screen | Name | Filters | Record (all years) |
|---|---|---|---|
| 1772775 | Tested: NFL Wind 10-14 Under | Under; avg wind 10–14 | 533-376 (58.6 %), ROI +13.3 % |
| 769171 | Tested: NFL 1H Wind 10-13 Under | 1H Under; avg wind 10–13; dome closed N | 403-300 (57.3 %), +10.4 % |
| 1772962 | Tested: NFL 1H Visitor Off 8 to 30 Days Under | 1H Under; visitor days between games 8–30; dome closed N | 454-357 (56.0 %), +7.7 % |
| 1772963 | Tested: NFL 1H Monday Night Under | 1H Under; day of week Monday; dome closed N | 168-118 (58.7 %), +12.3 % |
| 1772776 | Tested: NFL Awful-Team Dog ATS | Dog; season margin avg −40 to −13 | 254-164 (60.8 %), +17.2 %; train 203-133 / holdout 51-31 |
| 1772929 | Tested: NFL 1H Blowout Bounce Dog ATS | 1H Dog; previous game ATS margin −60 to −15 | 429-338 (55.9 %), +7.5 %; train 312-258 / holdout 117-80 |
Correction to §5b: the bounce cutoff is **≤ −15**, not ≤ −20 (a binning slip: 5-point floor bins labelled "−20" ran −20 to −16).
Screen-level split for ≤ −15: train 312-258 (54.7 %), holdout 117-80 (59.4 %). No system was created on the ML screens
(1457234, 1772928): nothing on either moneyline side cleared the bar.

## 6b. Screens touched (state as left)
- Totals 1772775: Under + date filter (reset to full range) + wind filter (set to 0–99 = no restriction; delete when done).
- Spread 1772776: Favorite/Dog filter (left on **Favorite**) + date filter (full range). Season-margin and Home/Visitor filters
  were added and deleted.
- ML 1457234: Season filter removed earlier; Favorite/Dog (left on Favorite); Game Month filter present but inactive; date
  filter added (left on holdout dates — reset or delete).
- 1H totals 769171: Corrente filter removed; date filter added (full range).
- 1H ML 1772928 and 1H Spread 1772929 (new): date filter (full range) + Favorite/Dog filter added to each (both left on
  Favorite for 1H ML, Favorite for 1H spread after the situational pass).

## 7. Pre-registered forward tests in sharp-tracker (graded on real fills, not Bet Labs history)
| rule_tag | Trigger | Bet | Stake |
|---|---|---|---|
| `wind1014` | outdoor NFL, Open-Meteo forecast at T-24h sustained 10–14 mph (loggers/nfl/weather.py) | FG Under, best price | 1u |
| `wind1014_1h` | same | 1H Under | 0.5u |
| `vrest8_1h` | visitor off ≥ 8 days | 1H Under | 0.5u |
| `mnf_1h` | Monday night | 1H Under | 0.5u |
| `awfuldog` | dog, season margin avg ≤ −13 or Pythag < 20 %, after ≥ 2 games | Spread | 0.5u |
| `bounce20_1h` | dog whose previous game ATS margin was ≤ −20 | 1H spread (FG spread secondary) | 0.5u |
Publication gate per tag: 100 graded fills AND positive CLV vs the exchange ruler. Until then each is a hypothesis.
