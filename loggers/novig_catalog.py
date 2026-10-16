#!/usr/bin/env python3
"""Novig catalog snapshot, every league: market id -> event, description, type, strike, outcome ids + names, start.
The public trade tape at data.novig.com carries only ids, and settled markets leave the public catalog, so this file is what makes
the tape readable later. Append-only: data/novig/catalog/YYYY-MM-DD.jsonl.gz holds the markets first seen that day (one line each, immutable).
Run with the price log (every 20 min); one pass over the whole open catalog is ~20-40 pages."""
import json, os, time, datetime as dt, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'data', 'novig'); os.makedirs(OUT, exist_ok=True)
CDIR = os.path.join(OUT, 'catalog'); os.makedirs(CDIR, exist_ok=True); A = "https://api.novig.com/v3/public"
import gzip, glob


def load_catalog():
    """marketId -> record, from every daily gz (markets keyed by the day first seen; immutable once written)."""
    cat = {}
    for f in sorted(glob.glob(os.path.join(CDIR, '*.jsonl.gz'))):
        with gzip.open(f, 'rt') as fh:
            for l in fh:
                r = json.loads(l); cat[r.pop('market')] = r
    return cat


def g(u):
    for i in range(6):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=40))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(3 * (i + 1)); continue
            return {}
        except Exception: time.sleep(1.5 * (i + 1))
    return {}


def main():
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    cat = load_catalog(); fresh = []
    events = {}; cur = None
    for _ in range(40):                                    # hard cap: a repeating cursor would otherwise loop forever
        x = g(f"{A}/catalog/events?limit=500" + (f"&next={cur}" if cur else ''))
        before = len(events)
        for e in x.get('items', []): events[e['eventId']] = e
        cur = x.get('next')
        if not cur or len(events) == before: break
    import concurrent.futures as cf
    def mk(e):
        out, cur, seen = [], None, set()
        for _ in range(20):
            x = g(f"{A}/catalog/markets?event={e['eventId']}&limit=2000" + (f"&next={cur}" if cur else ''))
            new = [m for m in x.get('items', []) if m['marketId'] not in seen]
            out += new; seen.update(m['marketId'] for m in new); cur = x.get('next')
            if not cur or not new: break
        return e, out
    n_new = n_mk = 0
    with cf.ThreadPoolExecutor(4) as ex:
        for e, items in ex.map(mk, list(events.values())):
            for m in items:
                n_mk += 1
                rec = dict(event_id=e['eventId'], event=e.get('description'), league=e.get('league'), sport=e.get('sport'), start_ts=m.get('startsTs') or e.get('startsTs'),
                           type=m.get('marketType'), desc=m.get('description'), strike=m.get('strike'), outcomes={o['outcomeId']: o['name'] for o in m.get('outcomes', [])},
                           last_seen=now)
                if m['marketId'] in cat: continue                      # immutable once written; ids never change meaning
                rec['first_seen'] = now; n_new += 1; cat[m['marketId']] = rec; fresh.append(dict(market=m['marketId'], **rec))
    if fresh:
        with gzip.open(os.path.join(CDIR, now[:10] + '.jsonl.gz'), 'at') as f:
            for r in fresh: f.write(json.dumps(r, separators=(',', ':')) + '\n')
    print(f"[novig catalog] {len(events)} events, {n_mk} open markets, {n_new} new; {len(cat)} in catalog")


if __name__ == '__main__':
    main()
