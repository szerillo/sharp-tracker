"""Observed station wind (ASOS / METAR, Iowa Environmental Mesonet) at the airport nearest each outdoor stadium, 2020-08 to 2026-11,
routine hourly reports, knots. Output asos_cache.json {station: {"YYYY-mm-ddTHH": knots}} and asos_map.json {point: [station, km]}."""
import json, math, os, time, subprocess, urllib.request, csv, io
from wind_nbm_pull import PTS
ST = json.loads(subprocess.run("git -C ../pushclone show origin/main:data/research/wx_cache/asos_stations.json", shell=True, capture_output=True).stdout)
def km(a, b, c, d): return 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(c - a) / 2) ** 2 + math.cos(math.radians(a)) * math.cos(math.radians(c)) * math.sin(math.radians(d - b) / 2) ** 2))
M = {}
for p, (la, lo) in PTS.items():
    s = min(ST, key=lambda x: km(la, lo, x[1], x[2])); M[p] = [s[0], round(km(la, lo, s[1], s[2]), 1)]
json.dump(M, open('asos_map.json', 'w'), indent=0)
C = json.load(open('asos_cache.json')) if os.path.exists('asos_cache.json') else {}
need = sorted({v[0] for v in M.values()} - set(C))
print('stations', len({v[0] for v in M.values()}), 'to fetch', len(need), 'median km', sorted(v[1] for v in M.values())[len(M) // 2], flush=True)
for i, s in enumerate(need):
    u = ("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=" + s + "&data=sknt&year1=2020&month1=8&day1=1&year2=2026&month2=11&day2=24"
         "&tz=Etc/UTC&format=onlycomma&latlon=no&missing=empty&trace=empty&report_type=3")
    for t in range(4):
        try:
            txt = urllib.request.urlopen(u, timeout=180).read().decode(); break
        except Exception as e:
            txt = None; time.sleep(5 + 10 * t)
    H = {}
    if txt:
        for r in csv.DictReader(io.StringIO(txt)):
            if r.get('sknt'):
                k = r['valid'][:13].replace(' ', 'T'); H.setdefault(k, []).append(float(r['sknt']))
    C[s] = {k: round(sum(v) / len(v), 1) for k, v in H.items()}
    if i % 5 == 0: json.dump(C, open('asos_cache.json', 'w')); print(i, s, len(C[s]), flush=True)
    time.sleep(1)
json.dump(C, open('asos_cache.json', 'w')); print('done', len(C))
