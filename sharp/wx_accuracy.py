"""Weekly wind-forecast check (Sean, 11/8): which forecast is closer to what happened, Open-Meteo or MySportsWeather, and the blend the
wind rule uses? Run by weekly.yml; writes data/research/wx_accuracy.json (and prints the table).
Games: outdoor NFL + CFB games with both forecasts logged (MySportsWeather from 10/29), kickoff already past.
Forecasts: each source at T-24h (nearest 18-30h) and latest before kickoff; the blend the wind rule uses (their average).
Actual: NASA POWER hourly 10 m wind (MERRA-2 reanalysis), mean of the kickoff hour and the next 3 (game window), m/s -> mph.
Second actual for NFL through 11/2: the Open-Meteo archive (ERA5) already in data/nfl/weather/archive.json (wind_kick).
Graded by mean absolute error, bias (forecast minus actual), and agreement on the rule's 10-14 mph band."""
import json, sys, os, time, collections, datetime as dt, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data', 'research', 'wx_cache'); os.makedirs(D, exist_ok=True)
P = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
NOW = dt.datetime.now(dt.timezone.utc)

games = {}
for sp in ('nfl', 'cfb'):
    for l in open(os.path.join(ROOT, 'data', sp, 'weather', 'weather.jsonl')):
        try: r = json.loads(l)
        except Exception: continue
        if r.get('indoor') or r.get('wind_mph') is None: continue
        k = (sp, str(r['espn_id'])); ko = P(r['kickoff_utc'])
        if ko > NOW - dt.timedelta(hours=4) or ko < P('2026-10-29T00:00:00Z'): continue
        g = games.setdefault(k, dict(sp=sp, ko=ko, lat=r['lat'], lon=r['lon'], home=r['home'], away=r['away'], om=[], msw=[]))
        g['om'].append((r['hours_to_kickoff'], r['wind_mph_kick'] if r.get('wind_mph_kick') is not None else r['wind_mph']))
    for l in open(os.path.join(ROOT, 'data', sp, 'weather', 'msw.jsonl')):
        try: r = json.loads(l)
        except Exception: continue
        k = (sp, str(r.get('event_id')))
        if k not in games or r.get('wind_mph') is None: continue
        h = (games[k]['ko'] - P(r['ts'])).total_seconds() / 3600
        games[k]['msw'].append((h, r['wind_mph']))

def pick(L, mode):
    pre = [x for x in L if x[0] > 0]
    if not pre: return None
    if mode == 't24':
        t = [x for x in pre if 18 <= x[0] <= 30]
        return min(t, key=lambda x: abs(x[0] - 24))[1] if t else None
    return min(pre, key=lambda x: x[0])[1]

G = [g for g in games.values() if g['om'] and g['msw']]
print(f'{len(G)} outdoor games with both forecasts ({sum(g["sp"] == "nfl" for g in G)} NFL, {sum(g["sp"] == "cfb" for g in G)} CFB)')

ARCH = json.load(open(os.path.join(ROOT, 'data', 'nfl', 'weather', 'archive.json')))

# ASOS airport stations (Iowa Environmental Mesonet): measured 10 m wind, hourly METARs. Nearest station within 25 km of the stadium.
import math
ST_CACHE = f'{D}/asos_stations.json'
try: ST = json.load(open(ST_CACHE))
except Exception:
    ST = []
    for stt in ('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC').split():
        try:
            gj = json.load(urllib.request.urlopen(f'https://mesonet.agron.iastate.edu/geojson/network/{stt}_ASOS.geojson', timeout=60))
            ST += [(f['properties']['sid'], f['geometry']['coordinates'][1], f['geometry']['coordinates'][0]) for f in gj['features']]
        except Exception as e: print('stations', stt, e)
    json.dump(ST, open(ST_CACHE, 'w'))
def km(a, b, c, d):
    r = math.pi / 180; x = (d - b) * r * math.cos((a + c) / 2 * r); y = (c - a) * r; return 6371 * math.hypot(x, y)
OB_CACHE = f'{D}/asos_obs.json'
try: OB = json.load(open(OB_CACHE))
except Exception: OB = {}
def asos(g):
    near = min(ST, key=lambda s: km(g['lat'], g['lon'], s[1], s[2])) if ST else None
    if not near or km(g['lat'], g['lon'], near[1], near[2]) > 25: return None
    sid = near[0]; d0 = g['ko'] - dt.timedelta(hours=1); d1 = g['ko'] + dt.timedelta(hours=5)
    key = f"{sid}|{g['ko'].isoformat()}"
    if key not in OB:
        u = (f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station={sid}&data=sknt&year1={d0.year}&month1={d0.month}&day1={d0.day}"
             f"&hour1={d0.hour}&year2={d1.year}&month2={d1.month}&day2={d1.day}&hour2={d1.hour}&tz=Etc/UTC&format=onlycomma&latlon=no&missing=M&report_type=3")
        try:
            txt = urllib.request.urlopen(u, timeout=60).read().decode()
            OB[key] = [l.split(',')[1:3] for l in txt.splitlines()[1:] if l and ',M' not in l]
        except Exception as e: OB[key] = None
        json.dump(OB, open(OB_CACHE, 'w')); time.sleep(0.3)
    rows = OB.get(key) or []
    v = [float(k) * 1.15078 for t, k in rows if g['ko'] <= dt.datetime.fromisoformat(t + ':00+00:00') <= g['ko'] + dt.timedelta(hours=3, minutes=59)]
    return sum(v) / len(v) if len(v) >= 2 else None

def nasa(g):
    S = NC.get(f'{round(g["lat"], 3)},{round(g["lon"], 3)}') or {}
    v = []
    for i in range(4):
        t = (g['ko'].replace(minute=0, second=0) + dt.timedelta(hours=i)).strftime('%Y%m%d%H')
        x = S.get(t)
        if x is not None and x > -900: v.append(x * 2.23694)
    return sum(v) / len(v) if len(v) >= 2 else None

def era5(g):
    if g['sp'] != 'nfl': return None
    k = f"{g['home']}|{g['ko'].strftime('%Y-%m-%dT%H')}"
    return (ARCH.get(k) or {}).get('wind_kick')

def band(x): return x is not None and 10 <= round(x) <= 14

OUTJ = {}
for label, truth in (('ASOS airport stations (measured)', asos), ('Open-Meteo archive (ERA5), NFL', era5)):
    rows = []
    for g in G:
        a = truth(g)
        if a is None: continue
        f = dict(om24=pick(g['om'], 't24'), omL=pick(g['om'], 'latest'), msw24=pick(g['msw'], 't24'), mswL=pick(g['msw'], 'latest'))
        f['blend24'] = (f['om24'] + f['mswL']) / 2 if f['om24'] is not None and f['mswL'] is not None else None   # the rule before 11/8
        f['blendL'] = (f['omL'] + f['mswL']) / 2 if f['omL'] is not None and f['mswL'] is not None else None      # the rule from 11/8
        rows.append((g, a, f))
    print(f'\n== actual = {label}: {len(rows)} games')
    if not rows: continue
    print(f"{'forecast':38} {'games':>5} {'MAE mph':>8} {'bias':>6} {'band agree':>11}")
    names = dict(om24='Open-Meteo at T-24h', omL='Open-Meteo latest', msw24='MySportsWeather at T-24h', mswL='MySportsWeather latest',
                 blend24='rule before 11/8 (OM T-24h + MSW latest)', blendL='rule now (OM latest + MSW latest)')
    for k, nmz in names.items():
        L = [(f[k], a) for g, a, f in rows if f[k] is not None]
        if not L: continue
        mae = sum(abs(x - a) for x, a in L) / len(L); bias = sum(x - a for x, a in L) / len(L)
        agree = sum(band(x) == band(a) for x, a in L) / len(L)
        print(f'{nmz:38} {len(L):5} {mae:8.2f} {bias:+6.2f} {100 * agree:10.0f}%')
        OUTJ.setdefault(label, {})[k] = dict(games=len(L), mae=round(mae, 2), bias=round(bias, 2), band_agree=round(agree, 3))
    windy = [(g, a, f) for g, a, f in rows if a >= 10 or any((f[k] or 0) >= 10 for k in ('omL', 'mswL'))]
    print(f'  games where the actual or either latest forecast was 10+ mph: {len(windy)}')
    for k in ('omL', 'mswL', 'blendL'):
        L = [(f[k], a) for g, a, f in windy if f[k] is not None]
        if L: print(f"    {names[k]:36} MAE {sum(abs(x - a) for x, a in L) / len(L):.2f}  bias {sum(x - a for x, a in L) / len(L):+.2f}")
json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), results=OUTJ), open(os.path.join(ROOT, 'data', 'research', 'wx_accuracy.json'), 'w'), indent=1)
