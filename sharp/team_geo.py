#!/usr/bin/env python3
"""Home-venue coordinates and UTC offset (standard time, hours) per team, by ESPN abbreviation, for the travel / body-clock features in
the angle miner (Sean 11/5: 'travel/time zones'). ESPN site API team list -> core API team -> venue address -> Open-Meteo geocoder city
(falls back to a state centroid). CFB reuses data/cfb/weather/_stadiums.json. Writes data/state/team_geo.json {sport: {ab: {lat, lon, tz}}}.
Usage: python3 sharp/team_geo.py"""
import os, sys, json, time, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, 'data', 'state', 'team_geo.json'); UA = {'User-Agent': 'sharp-tracker-geo'}
LG = {'nba': 'basketball/nba', 'nhl': 'hockey/nhl', 'nfl': 'football/nfl', 'mlb': 'baseball/mlb', 'wnba': 'basketball/wnba', 'cbb': 'basketball/mens-college-basketball', 'cfb': 'football/college-football'}
# standard-time UTC offsets by state (the few split states take their larger part); DST shifts every zone equally so differences hold
TZ = {'CT': -5, 'DC': -5, 'DE': -5, 'FL': -5, 'GA': -5, 'IN': -5, 'KY': -5, 'MA': -5, 'MD': -5, 'ME': -5, 'MI': -5, 'NC': -5, 'NH': -5, 'NJ': -5, 'NY': -5, 'OH': -5, 'PA': -5, 'RI': -5, 'SC': -5, 'VA': -5, 'VT': -5, 'WV': -5,
      'AL': -6, 'AR': -6, 'IA': -6, 'IL': -6, 'KS': -6, 'LA': -6, 'MN': -6, 'MO': -6, 'MS': -6, 'ND': -6, 'NE': -6, 'OK': -6, 'SD': -6, 'TN': -6, 'TX': -6, 'WI': -6,
      'AZ': -7, 'CO': -7, 'ID': -7, 'MT': -7, 'NM': -7, 'UT': -7, 'WY': -7, 'CA': -8, 'NV': -8, 'OR': -8, 'WA': -8, 'AK': -9, 'HI': -10,
      'ON': -5, 'QC': -5, 'MB': -6, 'AB': -7, 'BC': -8}


def get(u, timeout=30):
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout))
        except Exception: time.sleep(1.5)
    return None


def tz_from_lon(lon): return round(lon / 15)


def build(sport):
    out = {}
    if sport == 'cfb':
        S = json.load(open(os.path.join(ROOT, 'data', 'cfb', 'weather', '_stadiums.json')))
        for ab, s in S.items():
            if s.get('lat'): out[ab] = dict(lat=s['lat'], lon=s['lon'], tz=TZ.get(s.get('state') or '', tz_from_lon(s['lon'])), city=s.get('city'))
        return out
    teams = []; page = 1
    while True:
        d = get(f"https://site.api.espn.com/apis/site/v2/sports/{LG[sport]}/teams?limit=1000&page={page}")
        L = (((d or {}).get('sports') or [{}])[0].get('leagues') or [{}])[0].get('teams') or []
        teams += [t['team'] for t in L]
        if len(L) < 1000: break
        page += 1
    for t in teams:
        ab = t.get('abbreviation'); tid = t.get('id')
        if not ab or not tid: continue
        c = get(f"https://sports.core.api.espn.com/v2/sports/{LG[sport].split('/')[0]}/leagues/{LG[sport].split('/')[1]}/teams/{tid}?lang=en")
        v = (c or {}).get('venue') or {}; ad = v.get('address') or {}; city, state = ad.get('city'), ad.get('state')
        lat = lon = None
        if city:
            g = get(f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=10")
            hits = (g or {}).get('results') or []
            best = [h for h in hits if h.get('country_code') in ('US', 'CA')]
            if state: best = [h for h in best if (h.get('admin1') or '').startswith(state) or STATE_NAME.get(state) == h.get('admin1')] or best
            if best: lat, lon = best[0]['latitude'], best[0]['longitude']
        if lat is None: continue
        out[ab] = dict(lat=lat, lon=lon, tz=TZ.get(state or '', tz_from_lon(lon)), city=city, state=state, venue=v.get('fullName'), indoor=bool(v.get('indoor')))
        time.sleep(0.15)
    return out


STATE_NAME = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
              'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts',
              'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
              'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
              'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
              'ON': 'Ontario', 'QC': 'Quebec', 'MB': 'Manitoba', 'AB': 'Alberta', 'BC': 'British Columbia'}


def main():
    G = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for sp in sys.argv[1:] or ['nba', 'nhl', 'nfl', 'mlb', 'wnba', 'cfb', 'cbb']:
        if sp in G and len(G[sp]) > 10 and '--refresh' not in sys.argv: continue
        G[sp] = build(sp); print(sp, len(G[sp]), 'teams', flush=True)
        json.dump(G, open(OUT, 'w'), indent=0)
    json.dump(G, open(OUT, 'w'), indent=0)


if __name__ == '__main__':
    main()
