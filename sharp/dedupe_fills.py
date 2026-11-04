#!/usr/bin/env python3
"""Remove duplicate bets from the records (Sean, 11/4: "make sure we don't have duplicates tracking in there for record keeping").

  data/state/fills.jsonl     one live fill per rule per game x market: a later fill of the same rule on the same game and market is
                             voided ("duplicate of <first fill>"), so it never counts twice. Different rules on the same bet are kept
                             (the bet log notes that it flagged for more than one reason).
  data/tennis/fs_paper.jsonl one set-1 pick per match: the same two players within 6 hours under a second match id (a Pinnacle-made id
                             before ESPN lists the match, then ESPN's) is dropped, keeping the first pick.
Idempotent; run before the bet log. Usage: python3 sharp/dedupe_fills.py"""
import os, sys, json, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp import fills as FI


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def main():
    rows = FI.load(); first = {}; n = 0
    for r in sorted(rows, key=lambda r: r['ts_utc']):
        if r.get('result') == 'void' or not str(r.get('rule_tag', '')).startswith('paper:'): continue
        k = (r['event_id'], r['rule_tag'], r['market'])
        if k not in first: first[k] = r['fill_id']; continue
        r['result'] = 'void'; r['pnl_units'] = 0.0; r['note'] = (r.get('note') or '') + f" | VOID: duplicate of {first[k]}"; n += 1
    if n: FI.save(rows)
    tp = os.path.join(ROOT, 'data', 'tennis', 'fs_paper.jsonl'); m = 0
    if os.path.exists(tp):
        P = [json.loads(l) for l in open(tp) if l.strip()]; keep = []
        for p in sorted(P, key=lambda p: p['ts']):
            if any({q.get('fav_name'), q.get('opp_name')} == {p.get('fav_name'), p.get('opp_name')} and abs((ts(q['start']) - ts(p['start'])).total_seconds()) <= 6 * 3600 for q in keep):
                m += 1; continue
            keep.append(p)
        if m:
            with open(tp, 'w') as f:
                for p in keep: f.write(json.dumps(p) + '\n')
    print(f"[dedupe] voided {n} duplicate system fills, dropped {m} duplicate tennis picks")


if __name__ == '__main__':
    main()
