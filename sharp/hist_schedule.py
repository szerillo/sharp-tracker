"""Historic game list with start times and final scores from ESPN, for aligning exchange trade tapes to kickoff.
python3 -m sharp.hist_schedule 2026-08-01 2026-10-29  -> data/state/hist_schedule.json {sport: {event_id: {start, away, home, hs, as, date}}}
Sports: nfl, nba, nhl, cfb, mlb, soccer leagues. Team codes are ESPN abbreviations (the canonical codes in sharp/sports.py)."""
import os, sys, json, time, urllib.request, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'data', 'state', 'hist_schedule.json')
PATHS = {'nfl': 'football/nfl', 'nba': 'basketball/nba', 'nhl': 'hockey/nhl', 'cfb': 'football/college-football', 'mlb': 'baseball/mlb',
         'epl': 'soccer/eng.1', 'laliga': 'soccer/esp.1', 'bundesliga': 'soccer/ger.1', 'seriea': 'soccer/ita.1', 'ligue1': 'soccer/fra.1', 'mls': 'soccer/usa.1', 'ucl': 'soccer/uefa.champions'}


def g(u, tries=4):
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60))
        except Exception: time.sleep(2 * (i + 1))
    return {}


def main(d0, d1):
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for sp, path in PATHS.items():
        out.setdefault(sp, {}); day = d0
        while day <= d1:
            end = day
            x = g(f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={day:%Y%m%d}" + ('&groups=80&limit=400' if sp == 'cfb' else ''))
            for ev in x.get('events', []):
                c = ev['competitions'][0]; t = {k['homeAway']: k for k in c['competitors']}
                if 'home' not in t or 'away' not in t: continue
                stt = (c.get('status') or {}).get('type') or {}
                out[sp][ev['id']] = dict(start=ev['date'], away=t['away']['team'].get('abbreviation'), home=t['home']['team'].get('abbreviation'),
                                         hs=float(t['home'].get('score') or 0) if stt.get('completed') else None, as_=float(t['away'].get('score') or 0) if stt.get('completed') else None,
                                         final=bool(stt.get('completed')), status=stt.get('name'))
            day = end + dt.timedelta(days=1)
        print(f"[hist_schedule] {sp}: {len(out[sp])} games", flush=True)
        json.dump(out, open(OUT, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(dt.date.fromisoformat(a[0]) if a else dt.date(2026, 8, 1), dt.date.fromisoformat(a[1]) if len(a) > 1 else dt.date.today())
