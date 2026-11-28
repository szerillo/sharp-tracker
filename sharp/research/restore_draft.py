#!/usr/bin/env python3
"""DRAFT ONLY (11/28, td_append_guard follow-up): rebuild the paper rows pushes dropped before the fix, from git history. Nothing here
touches a live log; restoring is Sean's call.

For each paper ledger: every row id seen on main between SINCE and UNTIL that is not on main now, in the latest version main ever had
(so a row that was graded before it was dropped comes back graded). Small ledgers are written to data/research/restore_candidates/
<file>.jsonl; parlays_paper (hundreds of thousands of rows) gets a summary only, the script regenerates its rows on demand (--write-all).
Impact summary: data/research/restore_candidates/summary.json.
Usage: python3 sharp/research/restore_draft.py [SINCE] [UNTIL] [--write-all]"""
import collections
import datetime as dt
import gzip
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); sys.path.insert(0, ROOT)
from sharp import append_merge as M
from sharp.research.row_audit import KEYS

ET = __import__('zoneinfo').ZoneInfo('America/New_York')
OUTD = os.path.join(ROOT, 'data', 'research', 'restore_candidates')
LEDGERS = ['data/state/parlays_paper.jsonl', 'data/kalshi/steam_rev_paper.jsonl', 'data/kalshi/flow_paper.jsonl', 'data/state/stale_paper.jsonl',
           'data/state/sharp_paper.jsonl', 'data/state/curve_paper.jsonl', 'data/state/props_paper.jsonl', 'data/state/sharp_c_paper.jsonl']
BIG = {'data/state/parlays_paper.jsonl'}


def git(*a): return subprocess.run(['git', *a], cwd=ROOT, capture_output=True).stdout


def lines(ref, f):
    b = git('show', f'{ref}:{f}')
    if b[:2] == b'\x1f\x8b': b = gzip.decompress(b)
    return [l for l in b.decode('utf-8', 'replace').split('\n') if l.strip()]


def when(d):
    for k in ('logged', 'flagged', 'ts', 'rev_ts', 'steam_ts', 'start'):
        v = d.get(k)
        if isinstance(v, str) and v[:4] == '2026':
            try: return dt.datetime.fromisoformat(v.replace('Z', '+00:00')).astimezone(ET).date().isoformat()
            except ValueError: pass
        if isinstance(v, (int, float)) and v > 1e9: return dt.datetime.fromtimestamp(v, dt.timezone.utc).astimezone(ET).date().isoformat()
    return None


def rebuild(f, since, until):
    k = M.keyer(KEYS[f])
    now = {k(l) for l in lines('origin/main', f)}
    C = git('log', '--first-parent', 'origin/main', '--reverse', '--format=%H', f'--since={since}', f'--until={until}', '--', f).decode().split()
    lost = {}
    for c in C:                                      # oldest first, so a later (graded) version overwrites an earlier one
        for l in lines(c, f):
            key = k(l)
            if key not in now: lost[key] = l
    return [json.loads(l) for l in lost.values()]


def impact(f, R):
    s = dict(rows=len(R), by_day=dict(sorted(collections.Counter(when(r) for r in R).items(), key=lambda x: str(x[0]))))
    graded = [r for r in R if r.get('won') is not None or r.get('units') is not None]
    s['graded_before_drop'] = len(graded)
    if graded and all(isinstance(r.get('units'), (int, float)) for r in graded):
        s['graded_units'] = round(sum(r['units'] for r in graded), 3)
        s['graded_record'] = f"{sum(1 for r in graded if r.get('won') == 1)}-{sum(1 for r in graded if r.get('won') == 0)}"
    if f.endswith('stale_paper.jsonl'):
        s['checkable'] = sum(1 for r in R if r.get('checkable') and r.get('kind') != 'sb4')
        s['note'] = 'stale_book kill test counts the first 100 graded checkable rows by flag time; restored checkable rows would enter that count'
    if f.endswith('parlays_paper.jsonl'):
        s['legs'] = dict(sorted(collections.Counter(r.get('n') for r in R).items(), key=lambda x: str(x[0])))
        s['same_game'] = sum(1 for r in R if r.get('same_game'))
        s['usd'] = round(sum(r.get('usd') or 0 for r in R), 2)
        s['note'] = 'not graded here: grading needs each parlay\'s Kalshi result (sharp/parlay_grade.py fetches them)'
    if R: s['rules'] = dict(collections.Counter(r.get('rule') for r in R if r.get('rule')))
    return s


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    since = a[0] if a else '2026-11-21T05:00Z'; until = a[1] if len(a) > 1 else '2026-11-28T04:09Z'
    os.makedirs(OUTD, exist_ok=True); out = dict(since=since, until=until, built=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                                                 note='DRAFT: candidate rows only; no live log was changed', ledgers={})
    for f in LEDGERS:
        R = rebuild(f, since, until)
        out['ledgers'][f] = impact(f, R)
        if R and (f not in BIG or '--write-all' in sys.argv):
            with open(os.path.join(OUTD, os.path.basename(f)), 'w') as fh:
                for r in R: fh.write(json.dumps(r) + '\n')
        print(f, json.dumps({x: out['ledgers'][f][x] for x in out['ledgers'][f] if x != 'by_day'}))
    json.dump(out, open(os.path.join(OUTD, 'summary.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
