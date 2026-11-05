"""Historic game list with start times and final scores from ESPN, for aligning exchange trade tapes to kickoff.
python3 -m sharp.hist_schedule 2026-08-01 2026-10-29  -> data/state/hist_schedule.json {sport: {event_id: {start, away, home, hs, as, date}}}
Sports: nfl, nba, nhl, cfb, mlb, soccer leagues. Team codes are ESPN abbreviations (the canonical codes in sharp/sports.py)."""
import os, sys, json, time, urllib.request, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'data', 'state', 'hist_schedule.json')
PATHS = {'nfl': 'football/nfl', 'nba': 'basketball/nba', 'nhl': 'hockey/nhl', 'cfb': 'football/college-football', 'mlb': 'baseball/mlb',
         'cbb': 'basketball/mens-college-basketball', 'mma': 'mma/ufc', 'epl': 'soccer/eng.1', 'laliga': 'soccer/esp.1', 'bundesliga': 'soccer/ger.1', 'seriea': 'soccer/ita.1', 'ligue1': 'soccer/fra.1', 'mls': 'soccer/usa.1', 'ucl': 'soccer/uefa.champions', 'ligamx': 'soccer/mex.1', 'wnba': 'basketball/wnba', 'wncaab': 'basketball/womens-college-basketball'}


def g(u, tries=4):
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60))
        except Exception: time.sleep(2 * (i + 1))
    return {}


def main(d0, d1, only=None):
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for sp, path in PATHS.items():
        if only and sp not in only: continue
        out.setdefault(sp, {}); day = d0
        while day <= d1:
            end = day
            x = g(f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={day:%Y%m%d}" + ('&groups=80&limit=400' if sp == 'cfb' else '&groups=50&limit=500' if sp in ('cbb', 'wncaab') else ''))
            for ev in x.get('events', []):
                if sp == 'mma':          # a card: one event, many fights (competitions); each fight is its own row keyed by the fight id
                    for c in ev.get('competitions', []):
                        cc = c.get('competitors') or []
                        if len(cc) != 2: continue
                        stt = (c.get('status') or {}).get('type') or {}
                        out[sp][c['id']] = dict(start=c.get('date') or ev['date'], card=ev.get('name'), p1=(cc[0].get('athlete') or {}).get('displayName'), p2=(cc[1].get('athlete') or {}).get('displayName'),
                                                winner=((cc[0].get('athlete') or {}).get('displayName') if cc[0].get('winner') else (cc[1].get('athlete') or {}).get('displayName') if cc[1].get('winner') else None),
                                                final=bool(stt.get('completed')), status=stt.get('name'), result=(c.get('status') or {}).get('result') and (c['status']['result'].get('displayName')), rounds=((c.get('status') or {}).get('period')))
                    continue
                c = ev['competitions'][0]; t = {k['homeAway']: k for k in c['competitors']}
                if 'home' not in t or 'away' not in t: continue
                stt = (c.get('status') or {}).get('type') or {}
                det = (stt.get('detail') or stt.get('shortDetail') or '')
                out[sp][ev['id']] = dict(start=ev['date'], away=t['away']['team'].get('abbreviation'), home=t['home']['team'].get('abbreviation'),
                                         hs=float(t['home'].get('score') or 0) if stt.get('completed') else None, as_=float(t['away'].get('score') or 0) if stt.get('completed') else None,
                                         final=bool(stt.get('completed')), status=stt.get('name'),
                                         # 11/5: overtime / shootout flag (Bet Labs' NHL win% excludes OT losses), conference game and neutral site (CFB / CBB filters)
                                         ot=('OT' in det or 'SO' in det) or None, conf=c.get('conferenceCompetition'), neutral=c.get('neutralSite') or None)
            day = end + dt.timedelta(days=1)
        print(f"[hist_schedule] {sp}: {len(out[sp])} games", flush=True)
        json.dump(out, open(OUT, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(dt.date.fromisoformat(a[0]) if a else dt.date(2026, 8, 1), dt.date.fromisoformat(a[1]) if len(a) > 1 else dt.date.today(), only=set(a[2].split(',')) if len(a) > 2 else None)
