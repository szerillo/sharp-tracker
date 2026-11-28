#!/usr/bin/env python3
"""11/27 (td_append_guard follow-up): phone alert if a push drops rows from a paper ledger.

sharp/append_merge.py keeps a rebase from dropping rows. This is the alarm behind it: every board audit (signals.yml, about every
10 minutes) reads each ledger as it stands on main, compares its row ids with the ids it had at the main commit the previous
audit saw (data/state/ledger_watch.json holds just that commit), and reports any id that vanished. Rows only ever get added or graded in place, so a missing
id means a push dropped it. Legitimate removals: data/tennis/fs_paper.jsonl (sharp/dedupe_fills.py drops duplicate tennis picks) is
not watched; system fills are voided, never removed, so fills.jsonl is watched.
check() -> {file: n_dropped}; sharp/audit.py shows it as a warning on the banner and the phone alert fires when it first appears."""
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, ROOT)
from sharp import append_merge as M

WATCH = {f: k for f, k in M.KEYS.items() if f != 'data/tennis/fs_paper.jsonl'}
WATCH.update({'data/state/sys_sharp_tags.jsonl': ('key',), 'data/kalshi/steam_rev_paper.jsonl': ('ticker', 'steam_ts')})
SNAP = os.path.join(ROOT, 'data', 'state', 'ledger_watch.json')




def ids_on_main(f, fields, ref='origin/main'):
    r = subprocess.run(['git', 'show', f'{ref}:{f}'], cwd=ROOT, capture_output=True)
    if r.returncode: return None                     # not on main (yet), or not fetchable
    k = M.keyer(fields)
    return {k(l) for l in r.stdout.decode('utf-8', 'replace').split('\n') if l.strip()}


def git(*a): return subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True)


def check(fetch=True, ref='origin/main', snap=SNAP):
    if fetch: git('fetch', '-q', 'origin', 'main')
    cur = git('rev-parse', ref).stdout.strip()
    try: prev = json.load(open(snap)).get('main')
    except Exception: prev = None
    dropped = {}
    if prev and prev != cur:
        if git('cat-file', '-e', prev + '^{commit}').returncode:          # shallow CI checkout: fetch that one commit (trees only)
            git('fetch', '-q', '--depth=1', '--filter=blob:none', 'origin', prev)
        for f, fields in WATCH.items():
            old, new = ids_on_main(f, fields, prev), ids_on_main(f, fields, ref)
            if old is None or new is None: continue
            if old - new: dropped[f] = len(old - new)
    json.dump(dict(main=cur, checked=prev, dropped=dropped), open(snap, 'w'))
    return dropped


if __name__ == '__main__':
    print(check())
