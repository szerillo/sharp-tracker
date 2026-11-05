#!/usr/bin/env python3
"""Surface of a live tennis event (Sean, 11/5: the hot favourite only pays when the form came from the same surface and the player is settled).
ESPN gives a tournament name and a venue city, not a surface, so the map comes from Tennis Abstract (2022-25, tour + Challenger): city -> the
surface played there in that month. Fallback: the calendar (clay April to early June, grass mid June to mid July, hard otherwise), which is
right far more often than not at tour level. Build: python3 sharp/tennis_surface.py  ->  data/tennis/surface_map.json"""
import os, sys, csv, gzip, glob, json, re, unicodedata, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
TA = os.path.join(ROOT, 'data', 'tennis', 'ta'); MAP = os.path.join(ROOT, 'data', 'tennis', 'surface_map.json')
SLAM = {'wimbledon': 'Grass', 'roland garros': 'Clay', 'french open': 'Clay', 'australian open': 'Hard', 'us open': 'Hard'}


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z ]', ' ', s).strip()


def build():
    C = collections.defaultdict(collections.Counter)         # city -> Counter((month, surface))
    for f in glob.glob(os.path.join(TA, '*_matches_*.csv.gz')):
        b = os.path.basename(f)
        if 'futures' in b or 'itf' in b or not re.search(r'202[2-5]', b): continue
        for r in csv.DictReader(gzip.open(f, 'rt', errors='replace')):
            s = (r.get('surface') or '').strip(); name = norm(re.sub(r'\d+|Masters|Finals|\bCH\b', '', r.get('tourney_name') or '')).strip()
            if not s or not name or ':' in (r.get('tourney_name') or ''): continue
            try: mo = int(r['tourney_date'][4:6])
            except Exception: continue
            C[name][(mo, s)] += 1
    out = {}
    for city, cnt in C.items():
        bym = collections.defaultdict(collections.Counter)
        for (mo, s), n in cnt.items(): bym[mo][s] += n
        out[city] = {str(mo): c.most_common(1)[0][0] for mo, c in bym.items()}
    json.dump(out, open(MAP, 'w'), separators=(',', ':'), sort_keys=True)
    print(f"[tennis_surface] {len(out)} cities")
    return out


_M = None
def surface(tournament, venue, start):
    """'Hard' | 'Clay' | 'Grass' for an ESPN event. venue 'City, Country'; start ISO."""
    global _M
    if _M is None: _M = json.load(open(MAP)) if os.path.exists(MAP) else build()
    mo = int(start[5:7]) if start else None
    t = norm(tournament)
    for k, v in SLAM.items():
        if k in t: return v
    cands = []
    if venue: cands.append(norm(venue.split(',')[0]))
    cands += [w for w in t.split() if len(w) >= 4]
    for c in cands:
        m = _M.get(c)
        if m:
            if mo and str(mo) in m: return m[str(mo)]
            near = sorted(m.items(), key=lambda kv: abs(int(kv[0]) - (mo or 0)))
            if near and abs(int(near[0][0]) - (mo or 0)) <= 1: return near[0][1]
    if mo in (4, 5) or (mo == 6 and start[8:10] < '08'): return 'Clay'
    if mo == 6 or (mo == 7 and start[8:10] < '15'): return 'Grass'
    return 'Hard'


if __name__ == '__main__':
    build()
