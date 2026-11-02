#!/usr/bin/env python3
"""One-off (11/2): attach the best Novig / Kalshi / FD / Caesars / DK price at the moment each existing sharp-account paper flag was
logged, read from the tracker board committed just before that moment (git history of data/state/dashboard_<sport>.json). New flags get
this live in sharp/sharp_live.py. Usage: python3 sharp/paper_venue_backfill.py"""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.sharp_live as SL
meta = json.load(open(SL.META)); P = [json.loads(l) for l in open(SL.PAPER)]
cache = {}
def board_at(sp, ts):
    k = (sp, ts)
    if k not in cache:
        f = f'data/state/dashboard_{sp}.json'
        h = subprocess.run(['git', '-C', ROOT, 'log', '-1', f'--before={ts}', '--format=%H', '--', f], capture_output=True, text=True).stdout.strip()
        try: cache[k] = json.loads(subprocess.run(['git', '-C', ROOT, 'show', f'{h}:{f}'], capture_output=True, text=True).stdout) if h else {}
        except Exception: cache[k] = {}
    return cache[k]
n = 0
for p in P:
    if p.get('venues') is not None: continue
    m = meta.get(p['cond']) or {}
    row = dict(title=m.get('title') or '', start=p['start'], side=p['side'], mtype=p['mtype'], bet=p['bet'])
    SL.map_rows([row])
    if not row.get('event_id'): continue
    p['event_id'] = row['event_id']; p['venues'] = SL.venue_prices(row, board_at(row['sport'], p['logged']))
    n += p['venues'] is not None
    print(p['bet'], '|', p['logged'], '|', p['venues'] and p['venues']['q'])
with open(SL.PAPER, 'w') as f:
    for p in P: f.write(json.dumps(p) + '\n')
print(f'[backfill] venue prices on {n} of {len(P)} paper flags')
