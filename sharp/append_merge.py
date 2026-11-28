#!/usr/bin/env python3
"""Git merge driver for the row logs (*.jsonl, *.jsonl.gz under data/): never drop a row on a rebase. (td_append_guard, Sean OK 11/27)

Why: every data job commits, then loops `git pull --rebase -X theirs` until the push lands. When two jobs touched the same log, git's
own merge resolves the overlap by taking ONE side's hunk (for a .jsonl) or ONE side's whole file (a .jsonl.gz is binary to git), so the
rows the other job had just written were silently lost. P1 found it on 11/27: prices_fast CBB rows stamped 14:23 UTC were gone
(on 11/27 alone, 8 pushes dropped 14,634 CBB tape rows).

What this does: a row-level three-way merge. %O is the common ancestor, %A and %B the two sides (in a rebase %A is main as it now
stands and %B is the job's own commit being replayed; the rule is symmetric). Each row is identified by a key:
  * ledgers that jobs rewrite in place (grading, settled flags) use their own id (KEYS below), so a graded row replaces the ungraded one
    instead of being duplicated;
  * everything else is a pure append log and the whole line is the key (a multiset: the same line written twice by one job stays twice).
For every key: unchanged on one side -> take the other side's version (that includes a row one side deleted on purpose, e.g. a dedupe);
changed on both sides -> field merge, A's fields overlaid with B's non-empty fields. A row added on either side is ALWAYS kept.
Order: A's rows in A's order, then B's new rows in B's order (append logs stay append-ordered). A .jsonl.gz is decompressed (all gzip
members), merged, and written back as one gzip member.

Wired up in two places: .gitattributes (`merge=rowlog` on the logs) and each workflow's commit step
(`git config merge.rowlog.driver "python3 sharp/append_merge.py %O %A %B %P"`). Without the config line git falls back to its old
behaviour, so a workflow that is missing it is no worse than before. Tested in tests/test_append_merge.py with two real git writers.
Usage (git calls it): append_merge.py ANCESTOR CURRENT OTHER [PATH]; writes the result into CURRENT, exits 0 (non-zero = conflict)."""
import gzip
import json
import sys
from collections import Counter

# ledgers rewritten in place by their jobs -> the row id those jobs dedupe on (checked unique on main 11/27)
KEYS = {
    'data/state/fills.jsonl': ('fill_id',),                         # sharp/fills.py
    'data/state/sharp_paper.jsonl': ('cond', 'side'),               # sharp/sharp_live.py
    'data/kalshi/flow_paper.jsonl': ('event_id', 'market', 'line'), # sharp/kalshi_flow.py (re-grades spread rows every run)
    'data/state/stale_paper.jsonl': ('key',),                       # sharp/stale_live.py
    'data/state/props_paper.jsonl': ('key',),                       # sharp/props_live.py
    'data/state/curve_paper.jsonl': ('key',),                       # sharp/curve_live.py
    'data/state/wncaab_paper.jsonl': ('key',),                      # loggers/wncaab_live.py
    'data/state/sharp_c_paper.jsonl': ('key',),                     # sharp/sharp_c_log.py
    'data/state/novig_quoter_fills.jsonl': ('id',),                 # sharp/novig_paper_quoter.py
    'data/state/exchange_fills.jsonl': ('id',),                     # sharp/exchange_fills.py
    'data/state/placed.jsonl': ('id',),
    'data/experts/picks.jsonl': ('id',),                            # loggers/expert_picks.py
    'data/tennis/hot_paper.jsonl': ('event_id',),                   # sharp/tennis_watch.py (settled backfill)
    'data/tennis/fs_paper.jsonl': ('event_id', 'rule'),             # sharp/dedupe_fills.py
}
GZ = b'\x1f\x8b'


def read(path):
    try: raw = open(path, 'rb').read()
    except FileNotFoundError: return [], False
    gz = raw[:2] == GZ
    if gz: raw = gzip.decompress(raw)
    return [l for l in raw.decode('utf-8').split('\n') if l.strip()], gz


def keyer(fields):
    def k(line):
        if fields:
            try:
                d = json.loads(line)
                if isinstance(d, dict) and all(f in d for f in fields): return ('id',) + tuple(json.dumps(d[f], sort_keys=True) for f in fields)
            except ValueError: pass
        return ('line', line)
    return k


def index(lines, k):
    """key -> list of lines (a list, so an append log's repeated identical lines are counted, not collapsed)"""
    out = {}
    for l in lines: out.setdefault(k(l), []).append(l)
    return out


def field_merge(a, b):
    try:
        da, db = json.loads(a), json.loads(b)
        if isinstance(da, dict) and isinstance(db, dict):
            da.update({f: v for f, v in db.items() if v is not None}); return json.dumps(da)
    except ValueError: pass
    return b


def merge(O, A, B, fields=None):
    """Row-level three-way merge of three lists of lines. Returns the merged list."""
    k = keyer(fields)
    if not fields:                                   # pure append log: multiset of whole lines
        cO, cA, cB = Counter(O), Counter(A), Counter(B)
        out = []
        # copies of each line in the result: base, plus what each side added, minus what either side deleted (a + b - o)
        want = {l: max(0, cA[l] + cB[l] - cO[l]) for l in set(cA) | set(cB)}
        for l in A:                                  # A's order first
            if want.get(l, 0) > 0: out.append(l); want[l] -= 1
        for l in B:                                  # then B's new rows in B's order
            if want.get(l, 0) > 0: out.append(l); want[l] -= 1
        return out
    iO, iA, iB = index(O, k), index(A, k), index(B, k)
    out, done = [], set()
    def pick(key):
        o, a, b = iO.get(key), iA.get(key), iB.get(key)
        if a is None and b is None: return []
        if a is None: return [] if b == o else b     # A deleted an unchanged row: respect it; B changed or added it: keep
        if b is None: return [] if a == o else a
        if a == b or b == o: return a
        if a == o: return b
        if len(a) == 1 and len(b) == 1: return [field_merge(a[0], b[0])]
        return a + [x for x in b if x not in a]      # duplicate ids on both sides (should not happen): keep every distinct row
    for l in A + B:
        key = k(l)
        if key in done: continue
        done.add(key); out.extend(pick(key))
    return out


def check(O, A, B, res, fields=None):
    """Rows one side added (a key the base lacks, or more copies of an append-log line than the base) that are missing from the result."""
    k = keyer(fields); cO, cR = Counter(O), Counter(res); kO = {k(l) for l in O}; kR = {k(l) for l in res}
    lost = []
    for side in (A, B):
        cS = Counter(side)
        for l, n in cS.items():
            key = k(l)
            if key[0] == 'id':
                if key not in kO and key not in kR: lost.append(l)
            elif n > cO[l] and cR[l] < n - cO[l]: lost.append(l)
    return lost


def main(argv):
    o_path, a_path, b_path = argv[1:4]; path = (argv[4] if len(argv) > 4 else '').replace('\\', '/')
    O, _ = read(o_path); A, gza = read(a_path); B, gzb = read(b_path)
    fields = KEYS.get(path)
    res = merge(O, A, B, fields)
    body = ('\n'.join(res) + '\n' if res else '').encode('utf-8')
    if gza or gzb or path.endswith('.gz'): body = gzip.compress(body, mtime=0)
    open(a_path, 'wb').write(body)
    lost = check(O, A, B, res, fields)
    if lost:                                         # a row one side added is missing: refuse, git leaves the conflict and the push loop retries
        print(f'[append_merge] {path}: {len(lost)} added rows would be lost; leaving the conflict', file=sys.stderr); return 1
    print(f'[append_merge] {path or a_path}: base {len(O)}, current {len(A)}, other {len(B)} -> {len(res)} rows', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
