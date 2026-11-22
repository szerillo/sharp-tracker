#!/usr/bin/env python3
"""Bet Labs pull, step 2 (11/22): fold a pull saved from sharp/betlabs_pull.js into data/state/betlabs_picks.json, data/betlabs/current_picks.json
and data/state/betlabs_inventory.json, and print ALERTs (new / removed screens, changed filters, screens with no rule) plus picks NEW / GONE / CHANGED
since the last pull on main. Usage: python3 sharp/betlabs_pull_build.py PULL.json   (run from the repo root, before committing)"""
import json, sys, os, collections, datetime as dt, subprocess
R_ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, R_)
from sharp.systems import LABS
N = json.load(open(sys.argv[1]))
try: P = json.load(open(os.path.join(R_, 'data', 'state', 'betlabs_picks.json')))
except Exception: P = {'picks': []}
if not N.get('inv') or not N.get('pulled'): sys.exit('pull file has no screens: not written')
ip = os.path.join(R_, 'data', 'state', 'betlabs_inventory.json'); I = json.load(open(ip))
R = collections.defaultdict(list)
for t, v in LABS.items():
    sid = v[0] if isinstance(v, (list, tuple)) else v
    if sid: R[int(sid)].append(t)
if 'nba_bigfav_over' not in R[1799444]: R[1799444].append('nba_bigfav_over')
for s in N['inv']: s['filters'] = ', '.join(sorted(s['filters'].split('; ')))
inv = {s['id']: s for s in I['screens']}; alerts = []
for s in N['inv']:
    o = inv.get(s['id'])
    if not o:
        alerts.append(f"ALERT: new screen {s['name']}"); I['screens'].append(dict(id=s['id'], name=s['name'], filters=s['filters'], grade=s['grade'], roi=s['roi'], record=s['record'], rule='MISSING', status='MISSING', live='paper'))
        continue
    if o.get('filters') != s['filters']: alerts.append(f"ALERT: filters changed {s['name']}: {o.get('filters')} -> {s['filters']}")
    if not R.get(s['id']): alerts.append(f"ALERT: no rule in LABS for {s['name']}")
    o.update(filters=s['filters'], grade=s['grade'], roi=s['roi'], record=s['record'])
for k in set(inv) - {s['id'] for s in N['inv']}: alerts.append(f"ALERT: screen removed {inv[k]['name']}")
I['built'] = N['pulled']; json.dump(I, open(ip, 'w'), indent=1, ensure_ascii=False)
_t = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).date(); DAYS = (str(_t), str(_t + dt.timedelta(days=1)))
strip = lambda n: n.split(': ', 1)[1] if ': ' in n else n
out = dict(pulled=N['pulled'], source='Bet Labs current system picks (your saved Tested: and Tracked: screens)',
           screens=[dict(id=s['id'], name=strip(s['name']), sport=strip(s['name']).split()[0].lower(), rules=R.get(s['id'], [])) for s in N['inv']], picks=N['picks'])
for f in ('data/state/betlabs_picks.json', 'data/betlabs/current_picks.json'): json.dump(out, open(os.path.join(R_, f), 'w'), indent=1, ensure_ascii=False)
names = {s['id']: strip(s['name']) for s in N['inv']}; sport = {s['id']: strip(s['name']).split()[0] for s in N['inv']}
key = lambda p: (p['sid'], p['date'], p['away'], p['home'], p['play'])
old = {key(p): p for p in P['picks']}; new = {key(p): p for p in N['picks']}
print('\n'.join(alerts) or 'no alerts')
print('picks', len(N['picks']), 'by sport:', dict(collections.Counter(sport[p['sid']] for p in N['picks'])))
print('today + tomorrow by sport:', dict(collections.Counter(sport[p['sid']] for p in N['picks'] if p['date'] in DAYS)))
for k in sorted(set(new) - set(old), key=lambda k: (k[1], names[k[0]])): p = new[k]; print('NEW', p['date'], names[p['sid']], '|', p['away'], '@', p['home'], '|', p['play'], '|', p['info'])
for k in sorted(set(old) - set(new), key=lambda k: (k[1], names.get(k[0], ''))): p = old[k]; print('GONE', p['date'], names.get(p['sid'], p['sid']), '|', p['away'], '@', p['home'], '|', p['play'])
for k in set(new) & set(old):
    if new[k]['info'] != old[k]['info'] and new[k]['date'] in DAYS: print('CHANGED', new[k]['date'], names[k[0]], '|', new[k]['away'], '@', new[k]['home'], '|', new[k]['play'], '|', old[k]['info'], '->', new[k]['info'])
