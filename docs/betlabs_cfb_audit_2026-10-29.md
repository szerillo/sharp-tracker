# Bet Labs CFB audit — 2026-10-29

Same method as the NFL and NBA audits: Bet Labs NCAAF regular season 2003–present at closing lines, train 08/01/2003–02/28/2021
vs holdout 03/01/2021–10/29/2026, best contiguous window per numeric filter (n ≥ 500 train) graded on the holdout, situational
values read directly. Temporary screens built with "Build" (NCAAF × bet type × Game); the totals screen was kept and converted
into the saved system below, the spread and moneyline screens were deleted.

| Market | Scanned | Survivors | Call |
|---|---|---|---|
| Totals — Under | 65 numeric | **wind ≥ 14 mph** (#2 of 65, both halves 58.1 %) | **alive** |
| Totals — Over | 65 numeric | home laying 32.5+ → over (lean) | lean |
| Spread — Favorite | 124 numeric | none (32/40 flip) | dead |
| Spread — Dog | 124 numeric | none (29/40 flip; survivors are stat slivers) | dead |
| Moneyline — Favorite | 123 (ROI-ranked) | none (31/40 flip, max z 1.7) | dead |
| Moneyline — Dog | 123 (ROI-ranked) | none (32/40 flip; "win % 54–60" is a cherry-pick: the 50s bin is +4 % train / −16 % holdout) | dead |

## 1. Wind transfers, with a higher threshold
Under by observed wind, train / holdout: 0–9 mph 49.7 % / 49.8 % (n 9,038 / 3,214); **10–12 mph 52 % / 50 %** (the NFL band
does nothing in CFB); 13 mph 54 / 58; 14 mph 57 / 62; 15 mph 61 / 55; 17 mph 59 / 65; 19+ small but ≥ 59.
- Aggregate **≥ 14 mph: 422-304 (58.1 %) train, 132-95 (58.1 %) holdout**; all years 555-402 (58.0 %), ROI +12.2 %.
- 13–19 mph: 482-379 (56.0 %) / 177-133 (57.1 %).
- Unlike the NFL, the effect does not die at 15+: CFB totals are set with less precision and far more games are played in
  open-air, high-wind venues, so the market under-adjusts further up the scale. Threshold set at 14 (the scanner's own pick).
Saved as **Tested: CFB Wind 14 Plus Under** (ScreenId 1783043: Under, avg wind 14–99, regular season): 555-402-12.
Forward test in sharp-tracker: `cfb_wind14` — outdoor CFB, Open-Meteo kickoff forecast ≥ 14 mph sustained at T-24h → FG under, 1u.
Same caveat as the NFL rule: Bet Labs wind is observed, the tracker fires on a forecast.

## 2. Over: big home favourites
Home laying 32.5–45 → over: 354-257 (57.9 %) train, 73-57 (56.2 %) holdout. By bin the −45 and −35/−40 bins are 54–64 % in
training and the holdout lumps −35 and −30 at 60 %, but the −30 bin is 48 % in training, so the edge is choppy at the margin.
Lean only (≈130 holdout games); not added to the tracker yet.
Public-over-follow (under dollars ≤ 15 %, i.e. ≥ 85 % of money on the over → over) is 56.1 % / 55.7 % — the opposite of a
contrarian signal and consistent with the NFL finding that money % carries a little information. Not promoted.

## 3. Sides
Nothing on spreads or moneylines survives on either side. The dog "survivors" are narrow stat windows (rush-yard and
pass-yard-allowed slivers) that read as noise, and no situational family was needed to say so.

## 4. Screens
- Tested: CFB Wind 14 Plus Under — ScreenId 1783043 (kept).
- Audit CFB Spread Game / Audit CFB ML Game (temp) — deleted.
