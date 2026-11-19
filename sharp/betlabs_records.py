#!/usr/bin/env python3
"""Stores the full Bet Labs backtest record of each saved Tested:/Tracked: screen (Sean, 11/19). Read only on Bet Labs.

Input: the JSON built in a signed-in Bet Labs page by sharp/betlabs_records.js (window._BLREC), saved to a file.
Output:
  data/betlabs/records.json          the latest pull, with pulled_at, per screen: name, sport, grade, filters as Bet Labs words them,
                                     all-time record (W-L-P, units, ROI, z, N, first and last game), since the screen was saved,
                                     the current season, per-season splits, and the tool rule(s) it maps to (sharp/systems.py LABS)
  data/betlabs/records_history.jsonl one line per pull: the summary numbers per screen, plus the full per-season splits only when they
                                     changed since the previous pull (so a Bet Labs data revision is visible). Nothing is overwritten.
Units are Bet Labs' $100 units / 100; ROI = units / (W + L + P), as Bet Labs computes it; prices are Bet Labs' own (its consensus lines).
Usage: python3 sharp/betlabs_records.py betlabs_in.json"""
import os, sys, json, hashlib
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, ROOT)
D = os.path.join(ROOT, 'data', 'betlabs'); OUT = os.path.join(D, 'records.json'); HIST = os.path.join(D, 'records_history.jsonl')
INV = os.path.join(ROOT, 'data', 'state', 'betlabs_inventory.json')
EXTRA_RULES = {1799444: ['nba_bigfav_over']}          # the visitor-side screen of the same tool rule


def h(x): return hashlib.sha1(json.dumps(x, sort_keys=True).encode()).hexdigest()[:12]


def rules_by_screen():
    from sharp.systems import LABS
    R = {}
    for tag, v in LABS.items():
        sid = v[0] if isinstance(v, (tuple, list)) else v
        if sid: R.setdefault(int(sid), []).append(tag)
    for sid, tags in EXTRA_RULES.items(): R.setdefault(sid, []).extend(t for t in tags if t not in R.get(sid, []))
    return R


def main(path):
    new = json.load(open(path))
    if new.get('errors'): print('[betlabs records] page errors:', new['errors'])
    inv = {int(s['id']) for s in json.load(open(INV))['screens']} if os.path.exists(INV) else set()
    R = rules_by_screen()
    screens = {}
    for sid, s in new['screens'].items():
        s = dict(s); s['rules'] = R.get(int(sid), []); s['in_inventory'] = int(sid) in inv
        screens[str(sid)] = s
    missing = sorted(inv - {int(k) for k in screens})
    os.makedirs(D, exist_ok=True)
    prev = {}
    if os.path.exists(HIST):
        for l in open(HIST):
            try: r = json.loads(l)
            except Exception: continue
            for k, v in r.get('screens', {}).items(): prev[k] = v.get('seasons_hash')
    line = dict(pulled_at=new['pulled_at'], screens={})
    for k, s in screens.items():
        e = dict(all_time=s['all_time'], since_saved=s['since_saved'], this_season=s['this_season'], grade=s.get('grade'),
                 filters_hash=h(s['filters']), seasons_hash=h(s['seasons']))
        if prev.get(k) != e['seasons_hash']: e['seasons'] = s['seasons']; e['filters'] = s['filters']
        line['screens'][k] = e
    with open(HIST, 'a') as f: f.write(json.dumps(line, separators=(',', ':')) + '\n')
    out = dict(pulled_at=new['pulled_at'], source='Bet Labs (sportsinsights.actionnetwork.com/betlabs), Sean\'s saved Tested:/Tracked: screens, read only',
               units='Bet Labs $100 units / 100; ROI = units / (W + L + P); prices are Bet Labs\' own lines',
               seasons_note='per-season splits are computed from Bet Labs\' own past-picks list for the screen; football by season year (Aug start), '
                            'NBA/NHL/CBB as YYYY-YY (Aug start), MLB by calendar year. Columns: W, L, P, units, ROI %.',
               missing_from_pull=missing, screens=dict(sorted(screens.items())))
    json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)
    print(f"[betlabs records] {len(screens)} screens stored ({sum(1 for s in screens.values() if s['rules'])} mapped to tool rules); "
          f"missing from this pull: {missing or 'none'}; history lines: {sum(1 for _ in open(HIST))}")


if __name__ == '__main__':
    main(sys.argv[1])
