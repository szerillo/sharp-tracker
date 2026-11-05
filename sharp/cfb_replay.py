#!/usr/bin/env python3
"""CFB weather replay on the Odds API database (Sean, 11/5: "do cfb weather").
Every non-neutral 2020-26 CFB game with a Pinnacle closing total gets kickoff-hour weather at the home stadium from the Open-Meteo
archive (same method as sharp/nfl_replay.py: average of the kickoff hour and the next two, mph and F). Stadium coordinates come from the
ESPN team -> venue chain (data/cfb/weather/_venues.json first, then the Open-Meteo geocoder on the venue city); indoor venues are skipped.
Replays the two live weather rules by season and shows their neighbours:
  cfb_wind14 (outdoor, wind 14+: under) and cfb_hot_over_low_total (85F+, wind <= 10, total <= 55, non-conference: over).
Writes data/research/cfb_replay.json and caches weather in data/cfb/weather/archive.json, stadiums in data/cfb/weather/_stadiums.json.
Usage: python3 sharp/cfb_replay.py [--fetch-only]"""
import os, sys, json, time, sqlite3, collections, urllib.request, urllib.parse, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.rule_replay as RR
DB = os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'); WXD = os.path.join(ROOT, 'data', 'cfb', 'weather')
WXC = os.path.join(WXD, 'archive.json'); STAD = os.path.join(WXD, '_stadiums.json'); VEN = os.path.join(WXD, '_venues.json')
OUT = os.path.join(ROOT, 'data', 'research', 'cfb_replay.json')
UA = {'User-Agent': 'sharp-tracker-replay'}


def get(u, timeout=30):
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout))
        except Exception: time.sleep(2)
    return None


def stadiums(abs_):
    """ESPN abbreviation -> dict(venue_id, name, city, state, indoor, lat, lon). Cached."""
    S = json.load(open(STAD)) if os.path.exists(STAD) else {}
    V = json.load(open(VEN)) if os.path.exists(VEN) else {}
    for ab in abs_:
        if ab in S: continue
        t = get(f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{ab}")
        tid = t and t.get('team', {}).get('id')
        c = tid and get(f"https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/teams/{tid}?lang=en")
        v = (c or {}).get('venue') or {}
        row = dict(venue_id=v.get('id'), name=v.get('fullName'), city=(v.get('address') or {}).get('city'), state=(v.get('address') or {}).get('state'),
                   indoor=bool(v.get('indoor')), lat=None, lon=None)
        kv = V.get(str(v.get('id')))
        if kv and kv.get('lat'): row['lat'], row['lon'], row['src'] = kv['lat'], kv['lon'], 'live venues file'
        elif row['city'] and not row['indoor']:
            q = urllib.parse.quote(row['city']); g = get(f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=10&country=US")
            hits = (g or {}).get('results') or []
            best = [h for h in hits if h.get('admin1_id') and h.get('admin1', '')[:2].upper() == (row['state'] or '')[:2].upper()] or hits
            best = [h for h in hits if STATE.get(h.get('admin1')) == row['state']] or best
            if best: row['lat'], row['lon'], row['src'] = best[0]['latitude'], best[0]['longitude'], 'geocoder'
        S[ab] = row; json.dump(S, open(STAD, 'w'), indent=1); time.sleep(0.2)
    return S


STATE = {'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL',
         'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME',
         'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
         'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
         'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
         'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC'}

_WX = None
def _wx_load():
    global _WX
    if _WX is None: _WX = json.load(open(WXC)) if os.path.exists(WXC) else {}
    return _WX


def fetch_stadium(key, lat, lon, starts):
    """One Open-Meteo archive call per stadium covering every game date (the per-game version hit the 429 rate limit); keeps only the
    kickoff hours in the cache: {stadium|hour: dict(wind 3h avg, wind_kick, gust, temp, precip 3h)}."""
    C = _wx_load(); need = [s for s in starts if f"{key}|{s:%Y-%m-%dT%H}" not in C]
    if not need: return
    d0 = min(need).strftime('%Y-%m-%d'); d1 = (max(need) + dt.timedelta(days=1)).strftime('%Y-%m-%d')
    u = (f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={d0}&end_date={d1}"
         f"&hourly=wind_speed_10m,wind_gusts_10m,temperature_2m,precipitation&wind_speed_unit=mph&temperature_unit=fahrenheit&timezone=UTC")
    x = None
    for i in range(6):
        x = get(u, timeout=120)
        if x and 'hourly' in x: break
        time.sleep(10 * (i + 1))
    if not x or 'hourly' not in x: print('  no archive for', key, flush=True); return
    h = x['hourly']; idx = {t: i for i, t in enumerate(h['time'])}
    for s in need:
        k = f"{key}|{s:%Y-%m-%dT%H}"; i_ = idx.get(s.strftime('%Y-%m-%dT%H:00'))
        if i_ is None: C[k] = None; continue
        w = [v for v in h['wind_speed_10m'][i_:i_ + 3] if v is not None]
        C[k] = dict(wind=round(sum(w) / len(w), 1) if w else None, wind_kick=h['wind_speed_10m'][i_], gust=h['wind_gusts_10m'][i_], temp=h['temperature_2m'][i_],
                    precip=round(sum(v or 0 for v in h['precipitation'][i_:i_ + 3]), 2))
    save_wx(); time.sleep(1.0)


def weather(key, start):
    return _wx_load().get(f"{key}|{start:%Y-%m-%dT%H}")


def save_wx():
    if _WX is not None: os.makedirs(WXD, exist_ok=True); json.dump(_WX, open(WXC, 'w'))


def attach(G):
    """Add g['wx'] (or None for indoor / neutral / unknown) to every game. Returns the stadium map."""
    S = stadiums(sorted({g['home_ab'] for g in G if g.get('home_ab')}))
    byteam = collections.defaultdict(list)
    for g in G:
        g['wx'] = None; s = S.get(g.get('home_ab') or '')
        if g.get('neutral') or not s or s['indoor'] or not s.get('lat'): continue
        byteam[g['home_ab']].append(g['start'])
    for n_, (ab, starts) in enumerate(sorted(byteam.items())):
        fetch_stadium(ab, S[ab]['lat'], S[ab]['lon'], starts)
        if n_ % 10 == 0: print('  stadiums fetched', n_ + 1, '/', len(byteam), flush=True)
    for g in G:
        s = S.get(g.get('home_ab') or '')
        if g.get('neutral') or not s or s['indoor'] or not s.get('lat'): continue
        g['wx'] = weather(g['home_ab'], g['start'])
    save_wx(); return S


def rec(rows):
    """Flat stakes at Pinnacle's closing price for the side taken (over_dec/under_dec); -110 when the price is missing."""
    w = sum(1 for _, gr, _ in rows if gr == 1); l = sum(1 for _, gr, _ in rows if gr == -1); p = len(rows) - w - l
    pl = sum((d - 1) if gr == 1 else -1 if gr == -1 else 0 for _, gr, d in rows)
    return dict(n=len(rows), w=w, l=l, p=p, roi=round(pl / (w + l) * 100, 1) if w + l else 0.0)


def by_season(rows):
    S = collections.defaultdict(list)
    for g, gr, d in rows: S[RR.season_of('cfb', g['start'])].append((g, gr, d))
    return {s: rec(v) for s, v in sorted(S.items())}


def main():
    G = [g for g in RR.load('cfb') if g.get('tot_close') is not None and g.get('hs') is not None]
    print('cfb games with a closing total and a result:', len(G), flush=True)
    S = attach(G)
    have = [g for g in G if g['wx'] and g['wx'].get('wind') is not None]
    print('with weather:', len(have), 'indoor/neutral/unknown:', len(G) - len(have), flush=True)
    if '--fetch-only' in sys.argv: return
    H = collections.defaultdict(list)
    for g in have:
        wx = g['wx']; w = round(wx['wind']); t = wx['temp']; tot = g['tot_close']; pts = g['hs'] + g['as_']
        un = 1 if pts < tot else -1 if pts > tot else 0; ov = -un; U = (g, un, g.get('under_dec') or 1.909); O = (g, ov, g.get('over_dec') or 1.909)
        band = '0-5' if w <= 5 else '6-9' if w <= 9 else '10-13' if w <= 13 else '14-17 (rule)' if w <= 17 else '18-21 (rule)' if w <= 21 else '22+ (rule)'
        H[f'W1 under by kickoff wind band | {band}'].append(U)
        if w >= 14:
            H['W2 cfb_wind14: wind 14+ under'].append(U)
            H[f"W2a wind14 under | total {'under 50' if tot < 50 else '50-59.5' if tot < 60 else '60+'}"].append(U)
            H[f"W2b wind14 under | {'conference' if g.get('conf') else 'non-conference'}"].append(U)
            H[f"W2c wind14 under | {'cold (under 45F)' if t is not None and t < 45 else 'mild'}"].append(U)
            H[f"W2d wind14 under | {'rain (0.05in+ over 3h)' if (wx.get('precip') or 0) >= 0.05 else 'dry'}"].append(U)
            H[f"W2e wind14 under | gust {'25+' if (wx.get('gust') or 0) >= 25 else 'under 25'}"].append(U)
        if 10 <= w <= 13: H['W3 wind 10-13 under (the NFL band, in CFB)'].append(U)
        if t is not None:
            tb = 'under 32' if t < 32 else '32-44' if t < 45 else '45-59' if t < 60 else '60-74' if t < 75 else '75-84' if t < 85 else '85+'
            H[f'T1 over by kickoff temperature | {tb}'].append(O)
            if t >= 85 and w <= 10:
                H['T2 hot (85F+), wind <= 10: over'].append(O)
                if tot <= 55:
                    H['T3 hot, wind <= 10, total <= 55: over'].append(O)
                    H[f"T4 cfb_hot_over_low_total | {'non-conference (rule)' if not g.get('conf') else 'conference'}"].append(O)
                else: H['T3b hot, wind <= 10, total 55.5+: over'].append(O)
            if t < 32: H['T5 freezing (under 32F): under'].append(U)
        if (wx.get('precip') or 0) >= 0.1: H['P1 rain 0.1in+ over the game: under'].append(U)
    R = {}
    for k in sorted(H):
        r = rec(H[k]); r['seasons'] = by_season(H[k]); r['pos_seasons'] = sum(1 for s in r['seasons'].values() if s['roi'] > 0 and s['n'] >= 5)
        R[k] = r; print(f"{k:70s} {r['w']}-{r['l']}-{r['p']}  {r['roi']:+.1f}%  seasons+ {r['pos_seasons']}/{sum(1 for s in r['seasons'].values() if s['n'] >= 5)}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(dict(asof=dt.datetime.utcnow().isoformat() + 'Z', games=len(G), with_weather=len(have), stadiums=len(S), indoor=[a for a, s in S.items() if s['indoor']],
                   no_coords=[a for a, s in S.items() if not s['indoor'] and not s.get('lat')], results=R), open(OUT, 'w'), indent=1)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
