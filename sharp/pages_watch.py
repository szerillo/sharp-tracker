"""Fail-loud check that GitHub Pages is publishing (Kirk, 11/25: Pages failed every deploy from 20:10Z to 23:30Z while main kept fresh
data). Compares the 'built' time of the live bet_log.json on the site with the one on main. If main is newer and the live copy is more
than 30 minutes old, send one phone alert (ntfy, NTFY_TOPIC) per hour and note it in data/state/pages_watch.json."""
import os, json, urllib.request, datetime as dt
LIVE = 'https://szerillo.github.io/sharp-tracker/data/state/bet_log.json'
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'state', 'pages_watch.json')
def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
def main():
    now = dt.datetime.now(dt.timezone.utc)
    try: st = json.load(open(OUT))
    except Exception: st = {}
    main_built = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'data', 'state', 'bet_log.json')))['built']
    try:
        live_built = json.loads(urllib.request.urlopen(urllib.request.Request(LIVE + f'?t={int(now.timestamp())}', headers={'Cache-Control': 'no-cache'}), timeout=30).read())['built']
    except Exception as e:
        live_built = None
    lag = (ts(main_built) - ts(live_built)).total_seconds() / 60 if live_built else None
    stale = live_built is None or ((now - ts(live_built)).total_seconds() > 30 * 60 and ts(main_built) > ts(live_built))
    st.update(checked=now.strftime('%Y-%m-%dT%H:%M:%SZ'), live_built=live_built, main_built=main_built, lag_min=round(lag) if lag is not None else None, stale=stale)
    if stale and (not st.get('alerted') or (now - ts(st['alerted'])).total_seconds() > 3600):
        msg = (f"Pages is not publishing: the live board's bet log is from {live_built or 'unknown (fetch failed)'}, main has {main_built}. "
               "The board's data still loads from main; check the pages workflow.")
        topic = os.environ.get('NTFY_TOPIC')
        if topic:
            try: urllib.request.urlopen(urllib.request.Request(f'https://ntfy.sh/{topic}', data=msg.encode(), headers={'Title': 'Board not publishing', 'Priority': 'high'}), timeout=15); st['alerted'] = st['checked']
            except Exception as e: print('ntfy failed', e)
        print('ALERT', msg)
    if not stale: st.pop('alerted', None)
    json.dump(st, open(OUT, 'w'), indent=1); print('[pages_watch]', json.dumps(st))
if __name__ == '__main__': main()
