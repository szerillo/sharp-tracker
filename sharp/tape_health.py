#!/usr/bin/env python3
"""Missed-run check for the 5-minute tape (Sean, 11/1). GitHub can drop scheduled runs, and a gap in the tape is a gap in the move
tape, the steam states and the CLV marks. Collects every distinct run time in the 5-minute tape (data/*/ticks5, all sports and venues)
for the last 24 hours and lists each gap longer than 20 minutes (the tape runs every 5 minutes 10 AM-2 AM ET and every 10 overnight).
Writes data/state/tape_health.json; the Today page shows a banner when the tape is 30+ minutes stale or had a 30+ minute gap in the
last 6 hours. Usage: python3 sharp/tape_health.py"""
import os, glob, gzip, json, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
NOW = dt.datetime.now(dt.timezone.utc); SINCE = NOW - dt.timedelta(hours=24)


def main():
    days = {(NOW - dt.timedelta(days=i)).date().isoformat() for i in (0, 1)}
    runs = set()
    for f in glob.glob(os.path.join(ROOT, 'data', '*', 'ticks5', '*.jsonl.gz')):
        if os.path.basename(f)[:10] not in days: continue
        try:
            for l in gzip.open(f, 'rt'):
                i = l.find('"ts":"')
                if i < 0: continue
                t = l[i + 6:i + 22]                                   # to the minute
                if t >= SINCE.strftime('%Y-%m-%dT%H:%M'): runs.add(t)
        except (EOFError, OSError): pass
    T = sorted(dt.datetime.fromisoformat(t + ':00+00:00') for t in runs)
    gaps = []
    pts = [SINCE] + T + [NOW]
    for a, b in zip(pts, pts[1:]):
        m = (b - a).total_seconds() / 60
        if m > 20: gaps.append(dict(start=a.strftime('%Y-%m-%dT%H:%M:%SZ'), end=b.strftime('%Y-%m-%dT%H:%M:%SZ'), minutes=round(m)))
    last = T[-1].strftime('%Y-%m-%dT%H:%M:%SZ') if T else None
    stale = round((NOW - T[-1]).total_seconds() / 60) if T else None
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), runs_24h=len(T), last=last, stale_min=stale, gaps=gaps),
              open(os.path.join(ROOT, 'data', 'state', 'tape_health.json'), 'w'), indent=1)
    print(f"[tape_health] {len(T)} tape runs in 24h, last {stale} min ago; gaps over 20 min: " + (', '.join(f"{g['start'][5:16]}Z {g['minutes']}m" for g in gaps) or 'none'))


if __name__ == '__main__':
    main()
