#!/usr/bin/env python3
"""NFL, six seasons (2020-2025) of Pinnacle closes from the odds database, graded on results (Sean, 11/5: analysis relative to the
systems in place, what needs recalibrating, and untested ideas).

  A. The live rules replayed where the data allows: wind1014 (outdoor, kickoff-hour wind 10-14 mph from the Open-Meteo archive: full-
     game under), awfuldog (dog with season margin -13 or worse after 2+ games: spread), and the full-game cousins of the 1H rules
     (visitor off 8-30 days: under; Monday night: under; dog off a 15+ ATS loss: spread), since 1H lines are not in the data.
     Each cut comes with its neighbours (other wind bands, the favourite side, no-bounce) so a rule's band can be seen, not assumed.
  B. Market structure, results-first: favourite / dog by band, home / away, key numbers (3, 7) cover and push rates, totals by number,
     open-to-close moves (follow / fade, by size), Pinnacle vs the US books, divisional games, primetime, season phase, byes.
Writes data/research/nfl_replay.json. Weather cache: data/nfl/weather/archive.json (Open-Meteo archive, one call per outdoor game).
Usage: python3 sharp/nfl_replay.py"""
import os, sys, json, math, sqlite3, collections, datetime as dt, zoneinfo, urllib.request, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.rule_replay as RR
OUT = os.path.join(ROOT, 'data', 'research', 'nfl_replay.json'); WXC = os.path.join(ROOT, 'data', 'nfl', 'weather', 'archive.json')
ET = zoneinfo.ZoneInfo('America/New_York')
# outdoor stadiums (home abbreviation -> lat, lon); domes and roofed stadiums left out (ARI ATL DAL DET HOU IND LV LAC LAR MIN NO)
OUTDOOR = {'BAL': (39.278, -76.623), 'BUF': (42.774, -78.787), 'CAR': (35.226, -80.853), 'CHI': (41.862, -87.617), 'CIN': (39.095, -84.516), 'CLE': (41.506, -81.699),
           'DEN': (39.744, -105.020), 'GB': (44.501, -88.062), 'JAX': (30.324, -81.637), 'KC': (39.049, -94.484), 'MIA': (25.958, -80.239), 'NE': (42.091, -71.264),
           'NYG': (40.813, -74.074), 'NYJ': (40.813, -74.074), 'PHI': (39.901, -75.167), 'PIT': (40.447, -80.016), 'SF': (37.403, -121.970), 'SEA': (47.595, -122.332),
           'TB': (27.976, -82.503), 'TEN': (36.166, -86.771), 'WSH': (38.908, -76.864)}
DIV = {'BUF': 'AFCE', 'MIA': 'AFCE', 'NE': 'AFCE', 'NYJ': 'AFCE', 'BAL': 'AFCN', 'CIN': 'AFCN', 'CLE': 'AFCN', 'PIT': 'AFCN', 'HOU': 'AFCS', 'IND': 'AFCS', 'JAX': 'AFCS', 'TEN': 'AFCS',
       'DEN': 'AFCW', 'KC': 'AFCW', 'LV': 'AFCW', 'LAC': 'AFCW', 'DAL': 'NFCE', 'NYG': 'NFCE', 'PHI': 'NFCE', 'WSH': 'NFCE', 'CHI': 'NFCN', 'DET': 'NFCN', 'GB': 'NFCN', 'MIN': 'NFCN',
       'ATL': 'NFCS', 'CAR': 'NFCS', 'NO': 'NFCS', 'TB': 'NFCS', 'ARI': 'NFCW', 'LAR': 'NFCW', 'SF': 'NFCW', 'SEA': 'NFCW'}


def abbr_map():
    T = json.load(open(os.path.join(ROOT, 'data', 'state', 'espn_teams.json')))['nfl']
    import sharp.oddsapi_edge as E
    return {E.norm(t['name']): ab for ab, t in T.items()}


_WX = None
def weather(ab, start):
    """Kickoff-hour wind (mph), gust, temperature, precipitation at the home stadium from the Open-Meteo archive, cached."""
    global _WX
    if _WX is None: _WX = json.load(open(WXC)) if os.path.exists(WXC) else {}
    C = _WX
    k = f"{ab}|{start:%Y-%m-%dT%H}"
    if k in C: return C[k]
    lat, lon = OUTDOOR[ab]; d = start.strftime('%Y-%m-%d')
    u = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={d}&end_date={d}&hourly=wind_speed_10m,wind_gusts_10m,temperature_2m,precipitation&wind_speed_unit=mph&temperature_unit=fahrenheit&timezone=UTC"
    out = None
    for i in range(3):
        try:
            x = json.load(urllib.request.urlopen(u, timeout=30)); h = x['hourly']; i_ = h['time'].index(start.strftime('%Y-%m-%dT%H:00'))
            # average of the kickoff hour and the next two (the game), like a forecast "at kickoff" would read
            w = [v for v in h['wind_speed_10m'][i_:i_ + 3] if v is not None]
            out = dict(wind=round(sum(w) / len(w), 1) if w else None, wind_kick=h['wind_speed_10m'][i_], gust=h['wind_gusts_10m'][i_], temp=h['temperature_2m'][i_], precip=sum(v or 0 for v in h['precipitation'][i_:i_ + 3]))
            break
        except Exception as e: time.sleep(2)
    C[k] = out; weather.dirty = getattr(weather, 'dirty', 0) + 1
    if weather.dirty % 25 == 0: os.makedirs(os.path.dirname(WXC), exist_ok=True); json.dump(C, open(WXC, 'w'))
    time.sleep(0.1)
    return out


def main():
    G = RR.load('nfl'); RR.profiles(G)
    A = abbr_map()
    for g in G:
        g['hab'] = A.get(__import__('sharp.oddsapi_edge', fromlist=['norm']).norm(g['home'])); g['aab'] = A.get(__import__('sharp.oddsapi_edge', fromlist=['norm']).norm(g['away']))
    G = [g for g in G if g['hs'] is not None and g['close_h'] is not None and g['close_h'] <= 8 and g['hab'] and g['aab'] and g['hab'] not in ('AFC', 'NFC')]
    print(f"NFL games with a close and a result: {len(G)} ({min(g['start'] for g in G):%Y-%m-%d} to {max(g['start'] for g in G):%Y-%m-%d})")
    # season margins and last ATS margin per team (what awfuldog / bounce need), from scores and closing spreads
    hist = collections.defaultdict(list)
    for g in G:
        for side, team in (('home', g['hab']), ('away', g['aab'])):
            L = hist[team]; g[f'{side}_margin_avg'] = sum(x['margin'] for x in L) / len(L) if L else None; g[f'{side}_n'] = len(L)
            g[f'{side}_last_ats'] = L[-1]['ats'] if L else None
            g[f'{side}_bye'] = (g['start'].astimezone(ET).date() - L[-1]['start'].astimezone(ET).date()).days >= 12 if L else False
        if g['sp_close'] is not None:
            hist[g['hab']].append(dict(start=g['start'], margin=g['hs'] - g['as_'], ats=(g['hs'] - g['as_']) + g['sp_close']))
            hist[g['aab']].append(dict(start=g['start'], margin=g['as_'] - g['hs'], ats=(g['as_'] - g['hs']) - g['sp_close']))
    # weather for outdoor games
    nwx = 0
    for g in G:
        if g['hab'] in OUTDOOR:
            g['wx'] = weather(g['hab'], g['start']); nwx += bool(g['wx'])
    os.makedirs(os.path.dirname(WXC), exist_ok=True); json.dump(_WX or {}, open(WXC, 'w'))
    print(f"weather pulled for {nwx} outdoor games")
    R = {}
    def rec(name, hits):
        by = collections.defaultdict(lambda: dict(n=0, w=0, l=0, p=0, pnl=0.0, lm=[]))
        for g, gr in hits:
            won, dec, best, clv, lm = gr
            for t in (by[RR.season_of('nfl', g['start'])], by['all']):
                t['n'] += 1; t['w'] += won == 1; t['l'] += won == 0; t['p'] += won == 0.5; t['pnl'] += (dec - 1) if won == 1 else -1 if won == 0 else 0
                if lm is not None: t['lm'].append(lm)
        R[name] = {k: dict(n=v['n'], record=f"{v['w']}-{v['l']}" + (f"-{v['p']}" if v['p'] else ''), win_pct=round(v['w'] / max(v['w'] + v['l'], 1), 3), roi=round(100 * v['pnl'] / v['n'], 1), number_moved_for=round(sum(v['lm']) / len(v['lm']), 2) if v['lm'] else None) for k, v in sorted(by.items())}
    H = collections.defaultdict(list)
    for g in G:
        wx = g.get('wx'); w = round(wx['wind']) if wx and wx.get('wind') is not None else None
        fav = 'home' if (g['sp_close'] or 0) < 0 else 'away'; dog = 'away' if fav == 'home' else 'home'
        et = g['start'].astimezone(ET); dow = et.strftime('%A'); hour = et.hour
        # ---- A. rules
        if w is not None:
            band = 'wind 0-5' if w <= 5 else 'wind 6-9' if w <= 9 else 'wind 10-14 (the rule)' if w <= 14 else 'wind 15-19' if w <= 19 else 'wind 20+'
            gr = RR.grade(g, 'total', 'under')
            if gr: H[f'A1 wind1014 and its neighbours: UNDER by kickoff wind (Open-Meteo archive, 3h avg) | {band}'].append((g, gr))
            if 10 <= w <= 14:
                H['A1b wind 10-14 under, by temperature'].append((g, gr)) if False else None
                k2 = 'cold (under 40F)' if wx['temp'] is not None and wx['temp'] < 40 else 'mild'
                H[f'A1c wind 10-14 under | {k2}'].append((g, gr))
                gr2 = RR.grade(g, 'total', 'under')
                H[f"A1d wind 10-14 under | total {'44 or under' if g['tot_close'] <= 44 else '44.5-48' if g['tot_close'] <= 48 else '48.5+'}"].append((g, gr2))
        dm = g[f'{dog}_margin_avg']; dn = g[f'{dog}_n']
        if dm is not None and dn >= 2:
            gr = RR.grade(g, 'spread', dog)
            if gr: H[f"A2 awfuldog and neighbours: DOG ATS by its season margin | {'-13 or worse (the rule)' if dm <= -13 else '-7 to -13' if dm <= -7 else '-7 to 0' if dm < 0 else 'positive'}"].append((g, gr))
        la = g[f'{dog}_last_ats']
        if la is not None:
            gr = RR.grade(g, 'spread', dog)
            if gr: H[f"A3 bounce (full game): DOG ATS by its previous ATS margin | {'lost ATS by 15+ (the 1H rule)' if la <= -15 else 'lost ATS by 7-15' if la <= -7 else 'lost by 0-7' if la < 0 else 'covered'}"].append((g, gr))
        va = g['away_bye']
        gr = RR.grade(g, 'total', 'under')
        if gr:
            H[f"A4 vrest8 (full game): UNDER when the visitor is off a bye | {'visitor off 8+ days' if va else 'normal week'}"].append((g, gr))
            if dow == 'Monday': H['A5 mnf (full game): Monday night UNDER'].append((g, gr))
            if dow == 'Thursday': H['A5b Thursday night UNDER'].append((g, gr))
            if dow == 'Sunday' and hour >= 20: H['A5c Sunday night UNDER'].append((g, gr))
        # ---- B. market structure
        pf = max(g['p_close'], 1 - g['p_close']) if g['p_close'] is not None else None
        if pf is not None:
            grf = RR.grade(g, 'ml', 'home' if g['p_close'] >= .5 else 'away'); grd = RR.grade(g, 'ml', 'away' if g['p_close'] >= .5 else 'home')
            if grf: H[f"B1 moneyline favourite by Pinnacle band | {math.floor(pf * 10) / 10:.1f}"].append((g, grf))
            if grd: H[f"B1b moneyline dog by band | {math.floor(pf * 10) / 10:.1f}"].append((g, grd))
        if g['sp_close'] is not None:
            s = abs(g['sp_close']); k = f"{s:.1f}" if s in (3, 7) else '1-2.5' if s < 3 else '3.5-6.5' if s < 7 else '7.5-10' if s <= 10 else '10.5+'
            grh = RR.grade(g, 'spread', 'home'); gra = RR.grade(g, 'spread', 'away'); grF = RR.grade(g, 'spread', fav); grD = RR.grade(g, 'spread', dog)
            if grh: H[f"B2 home ATS by spread size | {'home fav' if g['sp_close'] < 0 else 'home dog'} {k}"].append((g, grh))
            if grD: H[f"B2b DOG ATS by spread size | {k}"].append((g, grD))
            if g.get('sp_open') is not None and grF and grD:
                mv = g['sp_close'] - g['sp_open']      # negative = moved toward the home side
                side_moved = 'home' if mv < 0 else 'away' if mv > 0 else None
                if side_moved:
                    grm = RR.grade(g, 'spread', side_moved); grx = RR.grade(g, 'spread', 'away' if side_moved == 'home' else 'home')
                    sz = '0.5' if abs(mv) <= .5 else '1-1.5' if abs(mv) <= 1.5 else '2+'
                    if grm: H[f"B3 FOLLOW the open-to-close spread move (bet the side the number moved toward, at the close) | moved {sz}"].append((g, grm))
                    if grx: H[f"B3b FADE the move (take the side the number moved against, at the close) | moved {sz}"].append((g, grx))
                    H[f"B3c follow the move, crossed a key number | {'crossed 3 or 7' if (min(abs(g['sp_open']), abs(g['sp_close'])) <= 3 <= max(abs(g['sp_open']), abs(g['sp_close'])) or min(abs(g['sp_open']), abs(g['sp_close'])) <= 7 <= max(abs(g['sp_open']), abs(g['sp_close']))) and abs(g['sp_open']) != abs(g['sp_close']) else 'no key number'}"].append((g, grm)) if grm else None
            if DIV.get(g['hab']) and DIV.get(g['hab']) == DIV.get(g['aab']) and grD: H['B4 divisional game: DOG ATS'].append((g, grD))
            if grD and (dow in ('Monday', 'Thursday') or (dow == 'Sunday' and hour >= 20)): H['B4b primetime: DOG ATS'].append((g, grD))
            wk = (g['start'].astimezone(ET).date() - dt.date(g['start'].year if g['start'].month >= 8 else g['start'].year - 1, 9, 1)).days // 7 + 1
            if grD: H[f"B4c DOG ATS by season phase | {'weeks 1-4' if wk <= 4 else 'weeks 5-12' if wk <= 12 else 'weeks 13+'}"].append((g, grD))
            if grD and g[f'{dog}_bye']: H['B4d dog off a bye: DOG ATS'].append((g, grD))
            if grF and g[f'{fav}_bye']: H['B4e favourite off a bye: FAV ATS'].append((g, grF))
        if g['tot_close'] is not None:
            gro = RR.grade(g, 'total', 'over'); gru = RR.grade(g, 'total', 'under')
            if gru: H[f"B5 UNDER by closing total | {'40 or under' if g['tot_close'] <= 40 else '40.5-44' if g['tot_close'] <= 44 else '44.5-48' if g['tot_close'] <= 48 else '48.5-52' if g['tot_close'] <= 52 else '52.5+'}"].append((g, gru))
            if g.get('tot_open') is not None and gro and gru:
                mv = g['tot_close'] - g['tot_open']
                if mv > 0: H[f"B6 total moved UP open-to-close: follow (OVER) | {'0.5-1' if mv <= 1 else '1.5+'}"].append((g, gro)); H[f"B6b total moved UP: fade (UNDER) | {'0.5-1' if mv <= 1 else '1.5+'}"].append((g, gru))
                elif mv < 0: H[f"B6c total moved DOWN: follow (UNDER) | {'0.5-1' if -mv <= 1 else '1.5+'}"].append((g, gru)); H[f"B6d total moved DOWN: fade (OVER) | {'0.5-1' if -mv <= 1 else '1.5+'}"].append((g, gro))
    for k, v in sorted(H.items()): rec(k, v)
    json.dump(R, open(OUT, 'w'), indent=1)
    for k, v in R.items():
        a = v.get('all', {}); print(f"  {k:100} n={a.get('n', 0):5} {a.get('record', ''):12} win {a.get('win_pct', 0):.3f} ROI {a.get('roi', 0):+6.1f}")


if __name__ == '__main__':
    main()
