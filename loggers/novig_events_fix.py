#!/usr/bin/env python3
"""Fill league / sport / start_ts / event description on history catalog records whose event was not in the events cache.
Walks GET /v3/history/events with settledAfter from the tape start (the bare endpoint only returns a recent window), then rewrites the
history-*.jsonl.gz catalog files in place. Needs the Novig key; run from the backfill workflow."""
import os, sys, json, gzip, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
from sharp import novig_auth as N
from novig_history import paged, TAPE_START
from novig_catalog import CDIR

EV = os.path.join(HERE, '..', 'data', 'novig', 'events_history.jsonl.gz')


def main():
    if not N.available(): print('[novig events] no key; skipped'); return
    events = {}
    if os.path.exists(EV):
        for l in gzip.open(EV, 'rt'): e = json.loads(l); events[e['eventId']] = e
    n0 = len(events)
    for since in (TAPE_START, TAPE_START - 40 * 86400000):
        for items in paged('/v3/history/events', f'settledAfter={since}&limit=5000', 200):
            for e in items: events[e['eventId']] = e
        if len(events) > n0: break
    with gzip.open(EV, 'wt') as f:
        for e in events.values(): f.write(json.dumps(e, separators=(',', ':')) + '\n')
    print(f'[novig events] {len(events)} events on file ({len(events) - n0} new)')
    fixed = 0; missing = 0
    for p in sorted(glob.glob(os.path.join(CDIR, 'history-*.jsonl.gz'))):
        rows = [json.loads(l) for l in gzip.open(p, 'rt')]; ch = False
        for r in rows:
            if r.get('start_ts'): continue
            e = events.get(r['event_id'])
            if not e: missing += 1; continue
            r.update(event=e.get('description'), league=e.get('league'), sport=e.get('sport'), start_ts=e.get('startsTs')); fixed += 1; ch = True
        if ch:
            with gzip.open(p, 'wt') as f:
                for r in rows: f.write(json.dumps(r, separators=(',', ':')) + '\n')
    print(f'[novig events] {fixed} catalog records filled, {missing} still without an event')


if __name__ == '__main__':
    main()
