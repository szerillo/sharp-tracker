#!/usr/bin/env python3
"""Novig settled-market history -> catalog (needs NOVIG_KEY_ID / NOVIG_PRIVATE_KEY; silently skips without them).

The public trade tape (data.novig.com, since 2026-08-03) carries only market/outcome ids. Settled markets leave the public
catalog, so until now only markets seen live could be decoded. GET /v3/history/markets returns every settled market with its
description, type, strike, outcomes (ids, names, WIN/LOSS/PUSH) and settlement time; GET /v3/history/events gives the event's
league, sport and start time. This job walks both, newest first, and appends anything not yet in the catalog to
data/novig/catalog/history-YYYY-MM-DD.jsonl.gz in the same record shape novig_catalog.load_catalog() reads. State in
data/novig/_history_state.json keeps the last settledAfter watermark so each run only pulls what is new.

Throttle: history bucket, cost 4 + 1 per 50 rows; a 429 carries Retry-After. Pages of 5000, paced; --all walks back to
2026-08-03 across runs (each run stops at --max-pages and resumes next time)."""
import os, sys, json, gzip, time, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
from sharp import novig_auth as N
from novig_catalog import load_catalog, CDIR

OUT = os.path.join(HERE, '..', 'data', 'novig'); STATE = os.path.join(OUT, '_history_state.json')
TAPE_START = int(dt.datetime(2026, 8, 3, tzinfo=dt.timezone.utc).timestamp() * 1000)


def paged(path, query, max_pages):
    cur = None; pages = 0
    while pages < max_pages:
        q = query + (f'&after={cur}' if cur else '')
        s, r = N.request('GET', path, q, timeout=60)
        if s == 429:
            time.sleep(20); continue
        if s != 200: print(f'[novig history] {path} -> {s} {str(r)[:120]}'); return
        pages += 1
        yield r.get('items', [])
        cur = r.get('next')
        if not cur: return
        time.sleep(2)


def main():
    if not N.available(): print('[novig history] no key in environment; skipped'); return
    args = sys.argv[1:]; max_pages = int(args[args.index('--max-pages') + 1]) if '--max-pages' in args else 6
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    cat = load_catalog(); now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    since = TAPE_START if '--all' in args else st.get('settled_after', TAPE_START)
    events = {}; fresh = []; n_seen = 0; newest = since
    # events first (league / start time), only the pages we need; the market walk fills the rest lazily
    for items in paged('/v3/history/events', 'limit=5000', 2):
        for e in items: events[e['eventId']] = e
    for items in paged('/v3/history/markets', f'settledAfter={since}&limit=5000', max_pages):
        for m in items:
            n_seen += 1; newest = max(newest, m.get('settledTs') or 0)
            if m['marketId'] in cat: continue
            e = events.get(m['eventId']) or {}
            rec = dict(market=m['marketId'], event_id=m['eventId'], event=e.get('description'), league=e.get('league'), sport=e.get('sport'),
                       start_ts=e.get('startsTs'), type=m.get('marketType'), desc=m.get('description'), strike=m.get('strike'),
                       outcomes={o['outcomeId']: o['name'] for o in m.get('outcomes', [])},
                       result={o['outcomeId']: o.get('status') for o in m.get('outcomes', [])}, settled_ts=m.get('settledTs'),
                       first_seen=now, last_seen=now, source='history')
            cat[m['marketId']] = rec; fresh.append(rec)
    if fresh:
        with gzip.open(os.path.join(CDIR, f'history-{now[:10]}.jsonl.gz'), 'at') as f:
            for r in fresh: f.write(json.dumps(r, separators=(',', ':')) + '\n')
    # watermark: only advance when the walk finished (fewer than max_pages full pages) so a cut-off run resumes
    if n_seen < max_pages * 5000: st['settled_after'] = newest
    st['last_run'] = now; st['events_cached'] = len(events); json.dump(st, open(STATE, 'w'))
    print(f'[novig history] {n_seen} settled markets scanned, {len(fresh)} new to catalog ({len(cat)} total); watermark {st.get("settled_after")}')


if __name__ == '__main__':
    main()
