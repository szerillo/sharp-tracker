# List items 2-5, 11/6/2026

## 2. System bets vs Polymarket sharp opposition (`sharp/sys_vs_poly.py`, `data/research/sys_vs_poly.json`)
Every replay pick (rule_replay and nfl_replay rules plus the generic NFL market bets) on games with Polymarket trade history
(6/2024 onward) was matched to the Polymarket market on the same game and market. Opposition = $500+ net from top accounts against
the pick, backed = $500+ with it.
- Honest test (accounts ranked only on markets before 6/11/2026, picks after): live rules backed 15-18 (-12.5%), no sharp view 31-31
  (+6.9%), opposed 16-23 (-20.1%). Backed did nearly as badly as opposed, so this is noise at n=139, not a sharp signal.
- With today's live sharp list over the whole window (looks ahead, context only): backed +1.7% (n 249), no view -14.7% (n 64),
  opposed +7.4% (n 209). Generic bets: opposed +0.3% vs backed -6.9% (n 2,600 each).
- Reading: no evidence that sharp opposition predicts a system bet losing. The hold rule is kept because it is the board's standing
  rule (no bets against the sharps), but it does not earn ROI on this evidence. It costs little either way.

## 3. Line shopping (`sharp/line_shop.py`, `data/research/line_shop.json`)
Every replay pick 2020-26 graded at the closing snapshot on each book's own number and price (n 30,748 bets priced everywhere).
- Best of DK, FD, Caesars, BetRivers vs DraftKings alone: +1.0 cents per $1 risked (+1.0% ROI). Best of four vs Pinnacle's close:
  -0.35%, so four US accounts get you almost exactly the Pinnacle closing price.
- Live rules: Pinnacle +1.6%, DK alone +0.9%, best of four +2.2%, best of seven (with offshore) +2.6%.
- Examples: wind 10-14 under +18.1 / +15.7 / +16.7; vrest8 +13.7 / +11.9 / +12.6; cfb_road_streak_dog -1.1 / -1.9 / +0.2.
- Reading: shopping four books is worth about one point of ROI on everything we bet; for thin-edge rules it is the difference between
  break-even and a small profit.

## 4. Sharp flags vs the opening number (`sharp/flag_move.py`, `data/research/flag_move.json`)
Moneyline flags since 9/1 matched to Pinnacle's snapshots (n 73, small). Pinnacle moved +1.16 points toward the flagged side open to
close on average; +0.45 had happened before the flag, +0.71 after (61% after).
- Flags 6h+ before the start: most of the move is still to come (69-84% after). Flags inside 6h: only 18% after; the market already
  has it.
- Flags where Pinnacle had NOT yet moved: 95% of the move came after, 36-25, +8.7%. Flags after Pinnacle had already moved a point
  toward the side: 6-6, -6.3% (chasing).
- Reading: early flags that lead Pinnacle are the information; late flags and flags that follow a Pinnacle move are not. Candidate grade
  input once n is larger: "Pinnacle already moved for the side" as a downgrade.

## 5. Audit for the cross-season stats bug
`sharp/nfl_replay.py` and `sharp/nfl_1h_replay.py` kept team histories by team only, so season margins ran across seasons, the last-game
ATS margin in week 1 came from last season, and every week-1 game read as "off a bye". Both now key by (team, season).
- awfuldog (-13 or worse): was 14-16 (-11.3%) under the bug, now 50-37-1 (+10.2%, n 88). Confirms restoring it at tier B.
- vrest8 under (visitor off a bye): was 132-93 (+13.7%), now 75-55 (+11.7%, n 132): the week-1 games were padding it; still holds.
- bounce full game (lost ATS by 15+): +5.5% -> +4.3%. 1H bounce15: 52-59. Favourite off a bye ATS: -11.9%.
- Checked clean: rule_replay (records reset each season from the ESPN schedule), cfb_replay (weather only), systems.py live CBB (current
  season schedule only).
