#!/usr/bin/env python3
"""NFL kickoff weather forecasts for the pre-registered wind tests (docs/betlabs_nfl_audit_2026-10-25.md §7).

Every run: ESPN public scoreboard for the current week (schedule, venue, indoor flag) -> Open-Meteo hourly forecast at the kickoff
hour for every OUTDOOR game inside 7 days -> one row per game per run in data/nfl/weather/weather.jsonl:
  ts, espn_id, kickoff_utc, hours_to_kickoff, away, home, venue, city, lat/lon, wind_mph (10 m sustained), gust_mph, temp_f, precip_mm, forecast_model.
The tracker reads the row whose hours_to_kickoff is nearest 24 (tolerance in constants) as the T-24h forecast; the trigger is
10 <= wind_mph <= 14. Bet Labs' historical wind is the observed game-time wind, so the forward test is on *forecast* wind — a
weaker signal by construction, which is the point of running it forward before trusting it.

Open-Meteo is free, no key, archive + forecast; wind_speed_unit=mph requested explicitly. Venue coordinates come from the
Open-Meteo geocoder on the venue city/state and are cached in data/nfl/weather/_venues.json (indoor venues are logged once and skipped).
"""
import json, os, time, datetime as dt, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', '..', 'data', 'nfl', 'weather'); os.makedirs(OUT, exist_ok=True)
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
OM = "https://api.open-meteo.com/v1/forecast"; GEO = "https://geocoding-api.open-meteo.com/v1/search"
VEN = os.path.join(OUT, '_venues.json'); HORIZON_H = 7 * 24
# Home stadium coordinates by ESPN team abbreviation (2026 season). Used first; the geocoder is the fallback for neutral sites
# (London, Munich, Mexico City, Madrid...). Indoor/retractable comes from ESPN's venue.indoor flag, not from this table.
STADIUM = {'ARI': (33.5276, -112.2626), 'ATL': (33.7554, -84.4010), 'BAL': (39.2780, -76.6227), 'BUF': (42.7738, -78.7870), 'CAR': (35.2258, -80.8528),
           'CHI': (41.8623, -87.6167), 'CIN': (39.0954, -84.5160), 'CLE': (41.5061, -81.6995), 'DAL': (32.7473, -97.0945), 'DEN': (39.7439, -105.0201),
           'DET': (42.3400, -83.0456), 'GB': (44.5013, -88.0622), 'HOU': (29.6847, -95.4107), 'IND': (39.7601, -86.1639), 'JAX': (30.3239, -81.6373),
           'KC': (39.0489, -94.4839), 'LV': (36.0909, -115.1833), 'LAC': (33.9535, -118.3392), 'LAR': (33.9535, -118.3392), 'MIA': (25.9580, -80.2389),
           'MIN': (44.9736, -93.2575), 'NE': (42.0909, -71.2643), 'NO': (29.9511, -90.0812), 'NYG': (40.8135, -74.0745), 'NYJ': (40.8135, -74.0745),
           'PHI': (39.9008, -75.1675), 'PIT': (40.4468, -80.0158), 'SF': (37.4030, -121.9700), 'SEA': (47.5952, -122.3316), 'TB': (27.9759, -82.5033),
           'TEN': (36.1665, -86.7713), 'WSH': (38.9076, -76.8645), 'WAS': (38.9076, -76.8645)}


def g(u, timeout=15):
    for i in range(2):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=timeout))
        except Exception: time.sleep(2 * (i + 1))
    return {}


def venue_coords(cache, v, home):
    """ESPN gives venue name + city/state, not coordinates: use the home stadium table, else geocode once per venue and cache."""
    key = str(v.get('id') or v.get('fullName'))
    if key in cache: return cache[key]
    addr = v.get('address') or {}; q = ', '.join(x for x in (addr.get('city'), addr.get('state')) if x)
    lat, lon = STADIUM.get(home, (None, None))
    is_home_park = home in STADIUM and (addr.get('country') in (None, 'USA', 'US') and (addr.get('state') or '') != '')
    if not is_home_park or lat is None:
        r = (g(f"{GEO}?name={urllib.parse.quote(addr.get('city') or '')}&count=10&language=en&format=json") or {}).get('results') or []
        hit = next((x for x in r if (x.get('admin1') or '').lower().startswith((addr.get('state') or '').lower()[:4])), r[0] if r else None)
        if hit: lat, lon = hit.get('latitude'), hit.get('longitude')
    cache[key] = dict(name=v.get('fullName'), city=q, indoor=bool(v.get('indoor')), lat=lat, lon=lon, source='table' if is_home_park else 'geocoder')
    return cache[key]


def main():
    now = dt.datetime.now(dt.timezone.utc); ts = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    cache = json.load(open(VEN)) if os.path.exists(VEN) else {}
    rows = []
    for ev in (g(ESPN) or {}).get('events', []):
        try: ko = dt.datetime.fromisoformat(ev['date'].replace('Z', '+00:00'))
        except Exception: continue
        h = (ko - now).total_seconds() / 3600
        if not (-1 <= h <= HORIZON_H): continue
        comp = ev['competitions'][0]; v = comp.get('venue') or {}
        teams = {c['homeAway']: c['team']['abbreviation'] for c in comp['competitors']}
        vc = venue_coords(cache, v, teams.get('home'))
        row = dict(ts=ts, espn_id=ev['id'], kickoff_utc=ko.strftime('%Y-%m-%dT%H:%M:%SZ'), hours_to_kickoff=round(h, 2), away=teams.get('away'), home=teams.get('home'),
                   venue=vc['name'], city=vc['city'], indoor=vc['indoor'], lat=vc['lat'], lon=vc['lon'])
        if vc['indoor'] or vc['lat'] is None: rows.append(row); continue
        day = ko.strftime('%Y-%m-%d')
        f = g(f"{OM}?latitude={vc['lat']}&longitude={vc['lon']}&hourly=wind_speed_10m,wind_gusts_10m,temperature_2m,precipitation&wind_speed_unit=mph"
              f"&temperature_unit=fahrenheit&timezone=UTC&start_date={day}&end_date={day}") or {}
        hr = (f.get('hourly') or {}); times = hr.get('time') or []
        want = ko.replace(minute=0, second=0).strftime('%Y-%m-%dT%H:00')          # hour containing kickoff; +1h would be the second-quarter hour
        if want in times:
            i = times.index(want); j = min(i + 1, len(times) - 1)
            ws = [hr['wind_speed_10m'][i], hr['wind_speed_10m'][j]]
            row.update(wind_mph=round(sum(x for x in ws if x is not None) / max(1, sum(1 for x in ws if x is not None)), 1), wind_mph_kick=hr['wind_speed_10m'][i],
                       gust_mph=hr['wind_gusts_10m'][i], temp_f=hr['temperature_2m'][i], precip_mm=hr['precipitation'][i], forecast_model='open-meteo best_match')
        rows.append(row)
    with open(os.path.join(OUT, 'weather.jsonl'), 'a') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    json.dump(cache, open(VEN, 'w'), indent=0)
    trig = [r for r in rows if r.get('wind_mph') is not None and 10 <= r['wind_mph'] <= 14 and 18 <= r['hours_to_kickoff'] <= 30]
    print(f"[nfl weather] {len(rows)} games, {sum(1 for r in rows if r.get('wind_mph') is not None)} forecast; T-24h wind 10-14 triggers: "
          + ', '.join(f"{r['away']}@{r['home']} {r['wind_mph']}mph" for r in trig))


if __name__ == '__main__':
    main()
