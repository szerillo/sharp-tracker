#!/usr/bin/env python3
"""Formats docs/validation/DISCOVERY.md from data/research/discovery.json (sharp/discover_angles.py) and data/state/fills.jsonl. No new
tests here: it ranks the candidates the search produced and adds the paper-log sample-size math (80% power, one-sided 5%)."""
import os, sys, json, math, collections, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, ROOT)
from sharp.discover_angles import describe, pct
D = json.load(open(os.path.join(ROOT, 'data', 'research', 'discovery.json')))
FILLS = [json.loads(l) for l in open(os.path.join(ROOT, 'data', 'state', 'fills.jsonl')) if l.strip()]
OUT = os.path.join(ROOT, 'docs', 'validation', 'DISCOVERY.md')
SD = 0.95                                     # per-bet profit sd at about -110 (the audit's walk-forward bets ran 0.80 to 1.06)
need = lambda e: math.ceil(((1.645 + 0.842) * SD / e) ** 2)
L = ['# Discovery search (board_r10 follow-up)', '',
     f"Built {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC by sharp/discover_report.py from sharp/discover_angles.py (seed 20261119). Plan: "
     "[DISCOVERY_PLAN.md](DISCOVERY_PLAN.md), registered before the search ran. Read-only: nothing was added to the board.", '',
     '## Bottom line', '']
tot_c = sum(r['n_cands'] for r in D.values()); tot_e = sum(r['n_elig'] for r in D.values())
best = sorted([c for r in D.values() for c in r['cands']], key=lambda c: c['p_search'])
L += [f"The search tried {tot_c:,} candidate angles across NFL, CFB, NBA and NHL. {tot_e:,} of them had 100+ bets in the training seasons. **None survives the "
      f"search-adjusted test** (the best search p is {best[0]['p_search']:.3f}). The reason is the size of the search: when the outcomes are shuffled, the best "
      "angle in each sport still shows a median ROI of +17% to +19% (table below). Any real angle would have to beat that to stand out.", '',
      "The stronger evidence is the walk-forward of the search itself. Each season, the procedure takes the top 5 angles found on earlier seasons (plain p < 0.05) "
      "and bets them blind the next season. That is how a newly found angle would actually be used. It does not make money in any sport beyond what chance allows:", '',
      '| Sport | Candidates (eligible) | Best ROI on shuffled data, median / 95th pct | Walk-forward of the search: ROI on N | p | Seasons |', '|---|---|---|---|---|---|']
for sp, r in D.items():
    L.append(f"| {sp.upper()} | {r['n_cands']} ({r['n_elig']}) | {pct(r['best_null']['median'])} / {pct(r['best_null']['p95'])} | {pct(r['wf_roi'])} on {r['wf_n']} | {r['wf_p']:.3f} | {', '.join(r['wf_seasons'])} |")
L += ['', 'In plain terms: mining the price and results history for new single or two-condition angles turns up angles that look strong in-sample (+15% to +20% '
      'on 100+ bets). They do about as well as a random pick in the following season. These markets (Pinnacle closes in the major US sports) are hard to beat on '
      'records, rest, form, ATS, line size, line move and weather alone. The results that held up in the audit (the wind under, the NHL early-season favourite) '
      'came from specific ideas that were tested, not from a broad search.', '',
      '## Candidates worth a look anyway', '',
      'The 10 lowest search-adjusted p-values overall, plus the top 3 per sport by plain p. None passes; they are listed so Sean can decide whether any is worth a paper '
      'tag to build a forward record. Holdout = the last complete season, never used to choose. WF picked = seasons in which the walk-forward of the search chose this angle.', '',
      '| Angle | Training N | Training ROI | Plain p | Search p | Holdout ROI (N) | WF picked |', '|---|---|---|---|---|---|---|']
seen = set(); short = best[:10]
for sp, r in D.items(): short += sorted(r['cands'], key=lambda c: (c['p_plain'], -c['roi']))[:3]
for c in short:
    k = (c['sport'], c['mk'], tuple(c['cond']))
    if k in seen: continue
    seen.add(k); wp = '; '.join(f"{w['season']} {pct(w['roi'])}/{w['n']}" for w in c['wf_picked']) or 'never'
    L.append(f"| {describe(c)} | {c['n']} | {pct(c['roi'])} | {c['p_plain']:.3f} | {c['p_search']:.3f} | {pct(c['hold_roi'])} ({c['hold_n']}) | {wp} |")
held = [c for c in best if c['hold_n'] >= 20 and (c['hold_roi'] or 0) > 0 and c['p_plain'] < 0.05]
L += ['', f"Of the {sum(1 for c in best if c['p_plain'] < 0.05)} eligible angles with plain p < 0.05 in training, {len(held)} were also positive in the holdout on 20+ bets. "
      f"Chance alone would put about half of them there.", '']
# paper logs
live = collections.defaultdict(lambda: dict(n=0, units=0.0, first=None, last=None))
for f in FILLS:
    if f.get('void_at') or f.get('result') not in ('W', 'L', 'P'): continue
    t = f['rule_tag'].split(':', 1)[-1]; x = live[t]; x['n'] += 1; x['units'] += f['pnl_units']
    x['first'] = min(x['first'] or f['ts_utc'], f['ts_utc']); x['last'] = max(x['last'] or f['ts_utc'], f['ts_utc'])
now = dt.datetime.now(dt.timezone.utc)
L += ['## The tracker\'s paper logs: when are they big enough?', '',
      f"The paper logs are too young to mine: {sum(x['n'] for x in live.values())} graded fills across {len(live)} rules since late October. To tell a real edge from zero "
      f"with 80% confidence (one-sided 5% test) at about -110 takes about **{need(0.10):,} bets for a +10% edge** and **{need(0.05):,} for +5%**. "
      "The table projects each rule's current pace (graded fills per week since its first fill) forward. Most rules need a season or more, and football rules "
      "only fill on game days, so their pace stops when the season ends.", '',
      '| Rule | Graded fills | Units | Fills per week | Weeks to 558 (+10% edge) |', '|---|---|---|---|---|']
for t, x in sorted(live.items(), key=lambda z: -z[1]['n']):
    wk = max(1.0, (now - dt.datetime.fromisoformat(x['first'].replace('Z', '+00:00'))).days / 7); pace = x['n'] / wk
    left = max(0, need(0.10) - x['n']); L.append(f"| {t} | {x['n']} | {x['units']:+.1f} | {pace:.1f} | {math.ceil(left / pace) if pace else 'n/a'} |")
L += ['', '## What is not searched, and why', '',
      '- CBB: no ESPN schedule history in the repo, so no records, rest or form. It could be added by backfilling the CBB schedule; line-only angles in CBB were not searched.',
      '- Bet Labs history: the repo holds pick lists for 5 screens only, not a game-level Bet Labs database, so there is nothing to mine beyond the systems already audited.',
      '- First-half, period and team-total markets: line history is too short (NFL 1H from 2023, CFB curves from 2023) for a training set plus a holdout.', '']
open(OUT, 'w').write('\n'.join(L) + '\n'); print(OUT)
