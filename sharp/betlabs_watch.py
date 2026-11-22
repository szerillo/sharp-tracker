#!/usr/bin/env python3
"""Missed Bet Labs pull alert (11/22, Kirk: the Fri 5 PM pull failed with Chrome busy and nobody knew). The pull runs from Claude scheduled
tasks in Sean's signed-in Chrome on this schedule (ET): 6:55 AM daily, 11:15 AM Sat/Sun, 2:55 PM Sat/Sun, 5:25 PM daily. Run from signals.yml
(about every 10 minutes): if a slot passed more than 35 minutes ago and data/state/betlabs_picks.json was not pulled at or after the slot
(5-minute grace before it), send one phone alert per slot (ntfy, NTFY_TOPIC) and note it in data/state/betlabs_watch.json."""
import os, json, urllib.request, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); SD = os.path.join(ROOT, 'data', 'state')
SLOTS = [((6, 55), None), ((11, 15), {5, 6}), ((14, 55), {5, 6}), ((17, 25), None)]      # weekday(): Sat 5, Sun 6
LATE_MIN = 35


def et_now():
    u = dt.datetime.now(dt.timezone.utc); y = u.year
    # US Eastern: DST from the 2nd Sunday of March 07:00Z to the 1st Sunday of November 06:00Z
    def nth_sun(m, n): d = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc); return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))
    dst = nth_sun(3, 2) + dt.timedelta(hours=7) <= u < nth_sun(11, 1) + dt.timedelta(hours=6)
    return u, dt.timezone(dt.timedelta(hours=-4 if dst else -5))


def main():
    u, tz = et_now(); now = u.astimezone(tz)
    try: pulled = dt.datetime.fromisoformat(json.load(open(os.path.join(SD, 'betlabs_picks.json')))['pulled'].replace('Z', '+00:00'))
    except Exception: pulled = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
    wp = os.path.join(SD, 'betlabs_watch.json')
    try: W = json.load(open(wp))
    except Exception: W = {}
    due = None
    for d in (0, 1):
        day = (now - dt.timedelta(days=d)).date()
        for (h, m), days in SLOTS:
            t = dt.datetime(day.year, day.month, day.day, h, m, tzinfo=tz)
            if days and t.weekday() not in days: continue
            if t + dt.timedelta(minutes=LATE_MIN) <= now and (due is None or t > due): due = t
    if due is None: return
    key = due.strftime('%Y-%m-%dT%H:%M')
    ok = pulled >= due - dt.timedelta(minutes=5)
    W['last_check'] = u.strftime('%Y-%m-%dT%H:%M:%SZ'); W['last_slot'] = key; W['last_pull'] = pulled.strftime('%Y-%m-%dT%H:%M:%SZ'); W['ok'] = ok
    if not ok and W.get('alerted') != key:
        msg = f"The {due.strftime('%a %-I:%M %p')} ET Bet Labs pull did not land (last pull {pulled.astimezone(tz).strftime('%a %-I:%M %p')} ET). The board's Bet Labs matches are stale; ask Claude to run the Bet Labs pull (needs Chrome open and signed in)."
        topic = os.environ.get('NTFY_TOPIC')
        if topic:
            try: urllib.request.urlopen(urllib.request.Request(f'https://ntfy.sh/{topic}', data=msg.encode(), headers={'Title': 'Bet Labs pull missed', 'Priority': 'high'}), timeout=15)
            except Exception as e: print('[betlabs watch] alert failed', e)
        W['alerted'] = key; print('[betlabs watch] ALERT', msg)
    else: print(f"[betlabs watch] slot {key}: {'pulled' if ok else 'missed, already alerted'} (last pull {W['last_pull']})")
    json.dump(W, open(wp, 'w'), indent=1)


if __name__ == '__main__':
    main()
