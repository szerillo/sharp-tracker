#!/usr/bin/env python3
"""Merge the shared bet logs with what is on origin/main before a job commits (11/7).
The tracker job and the signals job both write data/state/fills.jsonl and data/state/system_fired.json. Each used to commit its own
copy whole, so whichever finished second erased the other's new bets (11/6: a Georgia Southern under and an exchange fill vanished
this way). Run after `git fetch origin main`: every record on either side is kept, keyed by fill id / fire key. When both sides have the
same record, the more advanced one wins (graded beats ungraded, void beats live), else this job's copy.
Usage: python3 sharp/merge_state.py [ref]   (default origin/main)"""
import json, subprocess, sys, os

REF = sys.argv[1] if len(sys.argv) > 1 else 'origin/main'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def remote(path):
    r = subprocess.run(['git', 'show', f'{REF}:{path}'], capture_output=True, text=True, cwd=ROOT)
    return r.stdout if r.returncode == 0 else None


def rank(rec):
    return (1 if rec.get('void') or rec.get('result') == 'void' else 0) + (2 if rec.get('result') not in (None, 'void') else 0)


def merge_fills(path='data/state/fills.jsonl'):
    full = os.path.join(ROOT, path); txt = remote(path)
    if txt is None or not os.path.exists(full): return
    def parse(t):
        out = {}
        for l in t.splitlines():
            if not l.strip(): continue
            try: r = json.loads(l)
            except Exception: continue
            out[r.get('fill_id') or json.dumps(r, sort_keys=True)] = r
        return out
    L, R = parse(open(full).read()), parse(txt)
    added = [k for k in R if k not in L]
    for k, r in R.items():
        if k not in L or rank(r) > rank(L[k]): L[k] = r
    rows = sorted(L.values(), key=lambda r: (r.get('ts_utc') or '', r.get('fill_id') or ''))
    open(full, 'w').write(''.join(json.dumps(r) + '\n' for r in rows))
    print(f'[merge_state] {path}: {len(rows)} fills, {len(added)} kept from main that this job did not have')


def merge_fired(path='data/state/system_fired.json'):
    full = os.path.join(ROOT, path); txt = remote(path)
    if txt is None or not os.path.exists(full): return
    try: R = json.loads(txt); L = json.load(open(full))
    except Exception as e:
        print(f'[merge_state] {path}: not merged ({e})'); return
    added = [k for k in R if k not in L]
    for k, r in R.items():
        if k not in L or (isinstance(r, dict) and isinstance(L[k], dict) and rank(r) > rank(L[k])): L[k] = r
    json.dump(L, open(full, 'w'), indent=0)
    print(f'[merge_state] {path}: {len(L)} fires, {len(added)} kept from main that this job did not have')


if __name__ == '__main__':
    merge_fills(); merge_fired()
