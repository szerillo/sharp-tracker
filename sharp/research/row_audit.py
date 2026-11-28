#!/usr/bin/env python3
"""td_append_guard (11/27): did any push drop rows from a row log? Walks main's commits in a window, file by file.

For each commit that touched a log: rows the parent had that the commit no longer has (lost), and rows it added. Then each writer's
check: every row a commit added is still in the file at the end of the window (or it was replaced by a newer version of the same ledger
id, for the rewritten ledgers in sharp/append_merge.KEYS). Writers are told apart by the commit subject ('fast', 'signals', 'moves', ...).
A ledger that grades in place loses old versions of a row by design; for those, only a lost ID counts.
Usage: python3 sharp/research/row_audit.py SINCE [UNTIL] [FILE ...]   (default files: the logs prices_fast and the trades job write)
Writes docs/validation/row_audit_<since date>.json and prints a summary."""
import collections
import gzip
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); sys.path.insert(0, ROOT)
from sharp import append_merge as M

DEFAULT = ['data/state/sharp_paper.jsonl', 'data/kalshi/flow_paper.jsonl', 'data/state/sys_sharp_tags.jsonl',
           'data/polymarket/sharp_fills.jsonl', 'data/state/fills.jsonl']


def git(*a): return subprocess.run(['git', *a], cwd=ROOT, capture_output=True).stdout


def rows(c, f):
    b = git('show', f'{c}:{f}')
    if b[:2] == b'\x1f\x8b':
        try: b = gzip.decompress(b)
        except Exception: return []
    return [l for l in b.decode('utf-8', 'replace').split('\n') if l.strip()]


def audit(f, since, until):
    C = [l.split(' ', 2) for l in git('log', '--first-parent', 'origin/main', '--reverse', '--format=%H %ad %s', '--date=format:%m-%dT%H:%MZ',
                                       f'--since={since}', f'--until={until}', '--', f).decode().splitlines()]
    k = M.keyer(M.KEYS.get(f)); keyed = f in M.KEYS
    losses, added_by = [], []
    for h, when, subj in C:
        cur, par = rows(h, f), rows(h + '^', f)
        if keyed:
            lost = {k(l) for l in par} - {k(l) for l in cur}; add = {k(l) for l in cur} - {k(l) for l in par}
            nl, na = len(lost), len(add)
        else:
            cc, cp = collections.Counter(cur), collections.Counter(par)
            add = cc - cp; nl, na = sum((cp - cc).values()), sum(add.values())
        if nl: losses.append(dict(commit=h[:10], at=when, writer=subj.split()[0], lost=nl, added=na, before=len(par), after=len(cur)))
        added_by.append((h[:10], when, subj.split()[0], add))
    end = rows('origin/main', f) if not C else rows(C[-1][0], f)
    endk = collections.Counter(k(l) for l in end) if keyed else collections.Counter(end)
    missing = collections.Counter()
    for h, when, w, add in added_by:
        if keyed: missing[w] += sum(1 for x in add if x not in endk)
        else: missing[w] += sum(max(0, n - endk[l]) for l, n in add.items())
    return dict(file=f, commits=len(C), rows_start=len(rows(C[0][0] + '^', f)) if C else None, rows_end=len(end),
                pushes_that_dropped_rows=losses, rows_lost=sum(x['lost'] for x in losses),
                writers=dict(collections.Counter(w for _, _, w, _ in added_by)), added_rows_missing_at_end=dict(missing))


def main():
    a = sys.argv[1:]
    since = a[0]; until = a[1] if len(a) > 1 and not a[1].startswith('data/') else 'now'
    files = [x for x in a[1:] if x.startswith('data/')] or DEFAULT
    out = [audit(f, since, until) for f in files]
    for r in out:
        print(f"{r['file']}: {r['commits']} pushes, rows {r['rows_start']} -> {r['rows_end']}, "
              f"pushes that dropped rows {len(r['pushes_that_dropped_rows'])} ({r['rows_lost']} rows), "
              f"added rows missing at end {sum(r['added_rows_missing_at_end'].values())}")
        for x in r['pushes_that_dropped_rows'][:10]: print('   ', x)
    p = os.path.join(ROOT, 'docs', 'validation', f'row_audit_{since[:10]}.json')
    json.dump(dict(since=since, until=until, files=out), open(p, 'w'), indent=1)
    print('wrote', os.path.relpath(p, ROOT))


if __name__ == '__main__':
    main()
