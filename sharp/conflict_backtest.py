#!/usr/bin/env python3
"""Past system conflicts (Sean, 11/18): every game where two rules' paper fills took opposite sides (a team side: moneyline / spread, any
period; or over vs under on the same total), graded. Question: would letting the stronger tier override have beaten cancelling both?
Read-only. Data: data/state/fills.jsonl (graded fills; voids excluded unless voided for this conflict rule), tiers as on the board now
(data/state/system_fires.json). Flat 1 unit per side at the filled price. Writes docs/conflict_backtest_2026-11-18.md."""
import os, sys, re, json, collections, itertools
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); SD = os.path.join(ROOT, 'data', 'state')
OUT = os.path.join(ROOT, 'docs', 'conflict_backtest_2026-11-18.md')
TIER = {k: (v.get('evidence') or {}).get('tier') for k, v in json.load(open(os.path.join(SD, 'system_fires.json')))['rules'].items()}
RANK = {'A': 3, 'B': 2, 'C': 1, 'P': 0}
OPPO = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}
fam = lambda m: 'side' if re.sub(r'^(1h|1q|1p)_', '', m or '') in ('ml', 'spread') else f'total:{m}' if re.sub(r'^(1h|1q|1p)_', '', m or '') == 'total' else None
F = []
for l in open(os.path.join(SD, 'fills.jsonl')):
    r = json.loads(l)
    if not str(r.get('rule_tag', '')).startswith('paper:') or r.get('mclass', 'game') != 'game': continue
    if r.get('result') == 'void' and 'systems conflict' not in (r.get('note') or ''): continue
    F.append(r)
flat = lambda r: (r['price_decimal'] - 1) if r.get('result') == 'W' else -1.0 if r.get('result') == 'L' else 0.0
by = collections.defaultdict(list)
for r in F: by[r['event_id']].append(r)
pairs = []
for ev, L in by.items():
    for a, b in itertools.combinations(L, 2):
        if a['rule_tag'] == b['rule_tag'] or not fam(a['market']) or fam(a['market']) != fam(b['market']) or OPPO.get(a['side']) != b['side']: continue
        pairs.append((ev, a, b))
games = {}
for ev, a, b in pairs:
    g = games.setdefault(ev, {'fills': {}})
    for x in (a, b): g['fills'][x['fill_id']] = x
rows = []
for ev, g in games.items():
    L = list(g['fills'].values()); graded = all(x.get('result') in ('W', 'L', 'P') for x in L)
    tiers = {x['fill_id']: TIER.get(x['rule_tag'][6:], 'P') or 'P' for x in L}
    sides = collections.defaultdict(list)
    for x in L: sides[(x['side'], x['market'])].append(x)
    top = max(RANK.get(tiers[x['fill_id']], 0) for x in L)
    strong = [x for x in L if RANK.get(tiers[x['fill_id']], 0) == top]
    tie = len({OPPO.get(x['side']) == y['side'] for x in strong for y in strong if x is not y} - {False}) > 0
    rows.append(dict(ev=ev, start=L[0]['start_utc'][:10], graded=graded, tie=tie, objs=L, fills=[(x['rule_tag'][6:], tiers[x['fill_id']], x['market'], x['side'], x.get('line'), x['price_american'], x.get('result')) for x in L],
                     strong=None if tie else [x for x in strong], weak=None if tie else [x for x in L if x not in strong]))
G = [r for r in rows if r['graded']]
rec = lambda X: (sum(1 for x in X if x.get('result') == 'W'), sum(1 for x in X if x.get('result') == 'L'), round(sum(flat(x) for x in X), 2), len(X))
S = [x for r in G if not r['tie'] for x in r['strong']]; W_ = [x for r in G if not r['tie'] for x in r['weak']]
allf = [x for r in G for x in r['objs']]
sw, sl, su, sn = rec(S); ww, wl, wu, wn = rec(W_); aw, al, au, an = rec(allf)
L = ['# Past system conflicts: does the stronger tier win? (11/18)', '',
     'Built by sharp/conflict_backtest.py from data/state/fills.jsonl. A conflict = two rules\' paper fills on opposite sides of one game (moneyline / '
     'spread on the other team, any period; or over vs under on the same total). Tiers as on the board today. Flat 1 unit per fill at the filled price. '
     'Read-only: the rule stays "both sides untracked" (Sean, 11/18) whatever this shows.', '',
     f"Games with a conflict in the ledger: {len(rows)} ({len(G)} fully graded; {sum(1 for r in G if r['tie'])} of them with equal tiers on both sides, so no stronger side).", '',
     '| Policy on the graded conflicts | Fills | W-L | Units (flat 1u) |', '|---|---|---|---|',
     f"| Stronger tier only (the 11/2 rule) | {sn} | {sw}-{sl} | {su:+.2f} |",
     f"| Weaker tier only | {wn} | {ww}-{wl} | {wu:+.2f} |",
     f"| Both sides (no rule) | {an} | {aw}-{al} | {au:+.2f} |",
     '| Cancel both (the 11/18 rule) | 0 | 0-0 | +0.00 |', '',
     f"Sample: {len(G)} graded games. That is far too few to say a stronger tier should override; at roughly -110, telling +5% from zero takes thousands of bets. "
     "The 11/18 rule stays as it is, and this file can be re-run as conflicts accumulate.", '',
     '| Date | Game | Fills (rule, tier, market, side, line, price, result) |', '|---|---|---|']
for r in sorted(rows, key=lambda r: r['start']):
    L.append(f"| {r['start']} | {r['ev']} | " + '; '.join(f"{t} ({ti}) {m} {sd}{'' if ln is None else ' ' + str(ln)} {pr:+d} {res or 'open'}" for t, ti, m, sd, ln, pr, res in r['fills']) + ' |')
open(OUT, 'w').write('\n'.join(L) + '\n'); print(OUT, len(rows), 'conflict games', len(G), 'graded', (sw, sl, su), (ww, wl, wu), (aw, al, au))
