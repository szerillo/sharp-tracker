"""Season-to-date team game logs for the registry sports (systems engine inputs): per game the score, margin, DraftKings closing spread
and total from ESPN's summary pickcenter, ATS margin, days of rest. Cached in data/<sport>/season.json; completed games never refetched.
Usage: python3 -m sharp.season nfl   (the tracker job runs it for every registry sport)."""
import os, sys, json, time, urllib.request, datetime as dt, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from sharp import sports as SP
from sharp.norm import parse_ts, et_date

ROOT = os.path.abspath(os.path.join(HERE, '..'))
SEASON_START = {'nfl': dt.date(2026, 9, 1), 'nba': dt.date(2026, 10, 15), 'cfb': dt.date(2026, 8, 20)}


def g(u, tries=3):
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40))
        except Exception: time.sleep(1.5 * (i + 1))
    return {}


def path(sport): return os.path.join(ROOT, 'data', sport, 'season.json')


def load(sport):
    p = path(sport)
    return json.load(open(p)) if os.path.exists(p) else {'games': {}, 'fetched': None}


def refresh(sport):
    cfg = SP.SPORTS[sport]; st = load(sport); games = st['games']; today = et_date(dt.datetime.now(dt.timezone.utc))
    day = max(SEASON_START[sport], today - dt.timedelta(days=120)); n_new = 0
    while day <= today:
        x = g(f"https://site.api.espn.com/apis/site/v2/sports/{cfg['espn']}/scoreboard?dates={day.strftime('%Y%m%d')}" + ('&groups=80&limit=400' if sport == 'cfb' else ''))
        for ev in x.get('events', []):
            if ev['id'] in games and games[ev['id']].get('final'): continue
            c = ev['competitions'][0]; stt = (c.get('status') or {}).get('type') or {}
            if not stt.get('completed'): continue
            t = {x_['homeAway']: x_ for x_ in c['competitors']}
            rec = dict(event_id=ev['id'], start=ev['date'], week=(ev.get('week') or {}).get('number'), away=t['away']['team'].get('abbreviation'), home=t['home']['team'].get('abbreviation'),
                       away_score=float(t['away'].get('score') or 0), home_score=float(t['home'].get('score') or 0), final=True, neutral=c.get('neutralSite'))
            ls = {k: [float(q.get('value') or 0) for q in (v.get('linescores') or [])] for k, v in t.items()}
            if ls.get('home') and len(ls['home']) >= 2: rec['h1_home'] = ls['home'][0] + ls['home'][1]; rec['h1_away'] = ls['away'][0] + ls['away'][1]
            s = g(f"https://site.api.espn.com/apis/site/v2/sports/{cfg['espn']}/summary?event={ev['id']}")
            pc = (s.get('pickcenter') or [{}])[0]
            if pc.get('spread') is not None:
                # ESPN spread is the favourite's number; details 'PIT -3' says who. Store as the HOME line.
                det = pc.get('details') or ''; fav = det.split(' ')[0] if det else None
                sp = abs(float(pc['spread'])); rec['home_spread'] = -sp if fav == rec['home'] else (sp if fav == rec['away'] else None)
                rec['total'] = pc.get('overUnder'); rec['line_src'] = (pc.get('provider') or {}).get('name')
            games[ev['id']] = rec; n_new += 1
        day += dt.timedelta(days=1)
    st['fetched'] = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    os.makedirs(os.path.dirname(path(sport)), exist_ok=True); json.dump(st, open(path(sport), 'w'), separators=(',', ':'))
    print(f"[season {sport}] {len(games)} completed games on file, {n_new} new")
    return st


def team_logs(sport):
    """team -> list of games (chronological) with margin, spread (team perspective), ats margin, rest days."""
    st = load(sport); logs = collections.defaultdict(list)
    for gm in sorted(st['games'].values(), key=lambda r: r['start']):
        for side in ('home', 'away'):
            team = gm[side]; opp = gm['away' if side == 'home' else 'home']
            pf = gm['home_score'] if side == 'home' else gm['away_score']; pa = gm['away_score'] if side == 'home' else gm['home_score']
            hs = gm.get('home_spread'); spread = None if hs is None else (hs if side == 'home' else -hs)
            margin = pf - pa; ats = None if spread is None else margin + spread
            logs[team].append(dict(event_id=gm['event_id'], start=gm['start'], opp=opp, side=side, pf=pf, pa=pa, margin=margin, spread=spread, ats_margin=ats, week=gm.get('week')))
    for team, L in logs.items():
        for i, gm in enumerate(L):
            gm['rest_days'] = None if i == 0 else round((parse_ts(gm['start']) - parse_ts(L[i - 1]['start'])).total_seconds() / 86400)
    return logs


def profile(sport, team, before_utc):
    """Season-to-date numbers for `team` as of a kickoff time: games played, avg margin, last game's ATS margin and date."""
    L = [gm for gm in team_logs(sport).get(team, []) if parse_ts(gm['start']) < before_utc]
    if not L: return dict(games=0)
    last = L[-1]
    return dict(games=len(L), margin_avg=sum(gm['margin'] for gm in L) / len(L), last_ats_margin=last.get('ats_margin'), last_margin=last['margin'],
                last_start=last['start'], days_since_last=(before_utc - parse_ts(last['start'])).total_seconds() / 86400,
                wins=sum(1 for gm in L if gm['margin'] > 0), losses=sum(1 for gm in L if gm['margin'] < 0))


if __name__ == '__main__':
    for sp in (sys.argv[1:] or ['nfl']): refresh(sp)
