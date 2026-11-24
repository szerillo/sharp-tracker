"""Pregame NBM (National Blend of Models) 10 m wind at every outdoor NFL / CFB stadium in our 2020-26 game list, from the NOAA archive on
AWS (noaa-nbm-grib2-pds). For each game: the NBM cycle issued 6-12 hours before kickoff (the 6-hourly cycle at or before kickoff - 6 h),
forecast hours for the kickoff hour and the next two (averaged later, like Bet Labs' "avg wind" and our archive). Only the WIND:10 m
message is fetched (HTTP range from the .idx), decoded in memory, and the value at the grid point nearest each stadium kept.
Output: nbm_cache.json {"YYYYmmddHH|fh": {"nfl:BUF": m/s, ...}}; a missing cycle falls back to the one 6 hours earlier."""
import json, os, sys, time, datetime as dt, urllib.request, concurrent.futures as cf
import numpy as np, pygrib
B = 'https://noaa-nbm-grib2-pds.s3.amazonaws.com'
OUT = 'nbm_cache.json'
OUTDOOR = {'BAL': (39.278, -76.623), 'BUF': (42.774, -78.787), 'CAR': (35.226, -80.853), 'CHI': (41.862, -87.617), 'CIN': (39.095, -84.516), 'CLE': (41.506, -81.699),
           'DEN': (39.744, -105.020), 'GB': (44.501, -88.062), 'JAX': (30.324, -81.637), 'KC': (39.049, -94.484), 'MIA': (25.958, -80.239), 'NE': (42.091, -71.264),
           'NYG': (40.813, -74.074), 'NYJ': (40.813, -74.074), 'PHI': (39.901, -75.167), 'PIT': (40.447, -80.016), 'SF': (37.403, -121.970), 'SEA': (47.595, -122.332),
           'TB': (27.976, -82.503), 'TEN': (36.166, -86.771), 'WSH': (38.908, -76.864)}
PTS = {f'nfl:{k}': v for k, v in OUTDOOR.items()}
for k, v in json.load(open('stad_cfb.json')).items():
    if v.get('lat') is not None and not v.get('indoor'): PTS[f'cfb:{k}'] = (v['lat'], v['lon'])
NAMES = list(PTS); LAT = np.array([PTS[k][0] for k in NAMES]); LON = np.array([PTS[k][1] for k in NAMES])
def get(u, rng=None, tries=4):
    for i in range(tries):
        try:
            rq = urllib.request.Request(u, headers={'Range': f'bytes={rng[0]}-{rng[1]}'} if rng else {})
            with urllib.request.urlopen(rq, timeout=60) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404): return None
            time.sleep(1 + 2 * i)
        except Exception: time.sleep(1 + 2 * i)
    return None
def fetch(run, fh):
    """bytes of the WIND:10 m deterministic message, or None."""
    f = f"{B}/blend.{run:%Y%m%d}/{run:%H}/core/blend.t{run:%H}z.core.f{fh:03d}.co.grib2"
    idx = get(f + '.idx')
    if not idx: return None
    L = idx.decode().splitlines()
    for i, l in enumerate(L):
        p = l.split(':')
        if len(p) > 4 and p[3] == 'WIND' and p[4] == '10 m above ground' and (len(p) < 7 or p[6].strip() == ''):
            a = int(p[1]); b = int(L[i + 1].split(':')[1]) - 1 if i + 1 < len(L) else ''
            return get(f, (a, b))
    return None
GRID = {}
def extract(buf):
    g = pygrib.fromstring(buf); v = g.values; key = (v.shape, round(float(g['latitudeOfFirstGridPointInDegrees']), 3), round(float(g['longitudeOfFirstGridPointInDegrees']), 3))
    if key not in GRID:
        la, lo = g.latlons(); lo = np.where(lo > 180, lo - 360, lo); idx = []
        for y, x in zip(LAT, LON):
            d = (la - y) ** 2 + ((lo - x) * np.cos(np.radians(y))) ** 2; idx.append(np.unravel_index(np.argmin(d), d.shape))
        GRID[key] = idx
    vv = np.ma.filled(v, np.nan) if np.ma.isMaskedArray(v) else v
    return {n: (None if np.isnan(vv[i]) else round(float(vv[i]), 2)) for n, i in zip(NAMES, GRID[key])}
def job(run, fh):
    for back in (0, 6, 12):
        r = run - dt.timedelta(hours=back); buf = fetch(r, fh + back)
        if buf: return f"{run:%Y%m%d%H}|{fh}", dict(used=f"{r:%Y%m%d%H}|{fh + back}", vals=buf)
    return f"{run:%Y%m%d%H}|{fh}", None
if __name__ == '__main__':
    combos = set()
    for s in ('nfl', 'cfb'):
        for k in json.load(open(f'arch_{s}.json')):
            ab, t = k.split('|'); kick = dt.datetime.strptime(t, '%Y-%m-%dT%H')
            run = kick - dt.timedelta(hours=6); run = run.replace(hour=run.hour // 6 * 6)
            for h in range(3): combos.add((run, int((kick - run).total_seconds() // 3600) + h))
    C = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = sorted(c for c in combos if f"{c[0]:%Y%m%d%H}|{c[1]}" not in C)
    print('combos', len(combos), 'todo', len(todo), flush=True)
    t0 = time.time(); done = 0
    with cf.ThreadPoolExecutor(12) as ex:
      for b0 in range(0, len(todo), 48):           # batches, so downloaded buffers never pile up in memory
        futs = [ex.submit(job, r, f) for r, f in todo[b0:b0 + 48]]
        for fu in cf.as_completed(futs):
              k, res = fu.result(); done += 1
              if res is None: C[k] = None
              else:
                  try: C[k] = dict(used=res['used'], v=extract(res['vals']))
                  except Exception as e: C[k] = dict(err=str(e)[:80])
              if done % 100 == 0:
                  json.dump(C, open(OUT, 'w')); print(done, 'of', len(todo), round(time.time() - t0), 's', flush=True)
    json.dump(C, open(OUT, 'w')); print('done', len(C), 'missing', sum(1 for v in C.values() if not v or 'v' not in v))
