#!/usr/bin/env python3
"""MLB player props + first-inning (RFI) at Pinnacle (public guest API used by pinnacle.com; read-only, with max-risk limits).
One snapshot per run -> data/mlb/pinnacle_props/pinnacle_props.jsonl. Each row carries the parent matchup (away/home/start) so the
tracker can match the prop to a game without a player->team lookup."""
import json, os, time, datetime as dt, urllib.request, collections, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', '..', 'data', 'mlb', 'pinnacle_props'); os.makedirs(OUT, exist_ok=True)
PA = "https://guest.api.arcadia.pinnacle.com/0.1"
PSTAT = {'Total Strikeouts': 'K', 'Total Pitching Outs': 'OUTS', 'Total Hits Allowed': 'HA', 'Total Earned Runs': 'ER', 'Total Walks Allowed': 'BB',
         'Total Bases': 'TB', 'Total Home Runs': 'HR', 'Total Hits': 'H', 'Total Runs Batted In': 'RBI', 'Total Runs': 'R', 'Total Hits + Runs + RBIs': 'HRR'}
TEAM_AB = {'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
           'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL', 'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
           'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA', 'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
           'New York Yankees': 'NYY', 'Athletics': 'ATH', 'Oakland Athletics': 'ATH', 'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD',
           'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH'}
nz = lambda s: unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower().replace('.', '').replace(' jr', '').replace("'", '').strip()


def g(u):
    for i in range(6):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40))
        except urllib.error.HTTPError as e:
            if e.code == 404: return {}
            time.sleep(1.5 * (i + 1))
        except Exception: time.sleep(1.5 * (i + 1))
    return {}


def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    pm = g(f"{PA}/leagues/246/matchups?brandId=0") or []; pk = g(f"{PA}/leagues/246/markets/straight") or []
    km = collections.defaultdict(list)
    for k in pk: km[k['matchupId']].append(k)
    games = {}
    for m in pm:
        if m.get('type') == 'matchup' and len(m.get('participants', [])) == 2 and 'Runs' not in m['participants'][0]['name']:
            al = {p.get('alignment'): p['name'] for p in m['participants']}
            games[m['id']] = dict(away=TEAM_AB.get(al.get('away')), home=TEAM_AB.get(al.get('home')), start=m['startTime'])
    rows = []
    for m in pm:
        if m.get('type') == 'special' and (m.get('special') or {}).get('category') == 'Player Props':
            d = m['special']['description']; key = next((k for k in PSTAT if d.endswith(k)), None)
            if not key: continue
            stat = PSTAT[key]; nm = nz(d[:-len(key)].strip()); side = {p['id']: p['name'].lower() for p in m['participants']}
            par = games.get((m.get('parent') or {}).get('id')) or {}
            for k in km[m['id']]:
                pr = {side.get(x['participantId']): x for x in k['prices']}
                if 'over' in pr and 'under' in pr:
                    lim = next((l['amount'] for l in k.get('limits') or [] if l['type'] == 'maxRiskStake'), None)
                    rows.append(dict(ts=now, name=nm, stat=stat, line=pr['over']['points'], over=pr['over']['price'], under=pr['under']['price'], limit=lim,
                                     start=par.get('start') or m.get('startTime'), parent=(m.get('parent') or {}).get('id'), away=par.get('away'), home=par.get('home')))
        elif m['id'] in games:
            for k in km[m['id']]:
                if k['key'] == 's;3;ou;0.5':      # first inning total 0.5 = YRFI/NRFI
                    pr = {x['designation']: x['price'] for x in k['prices']}
                    lim = next((l['amount'] for l in k.get('limits') or [] if l['type'] == 'maxRiskStake'), None)
                    rows.append(dict(ts=now, name=None, stat='RFI', line=0.5, over=pr['over'], under=pr['under'], limit=lim, start=m['startTime'], parent=m['id'], **{k2: games[m['id']][k2] for k2 in ('away', 'home')}))
    with open(os.path.join(OUT, 'pinnacle_props.jsonl'), 'a') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    print(f"[pinnacle props] {len(rows)} rows, {len(games)} games")


if __name__ == '__main__':
    main()
