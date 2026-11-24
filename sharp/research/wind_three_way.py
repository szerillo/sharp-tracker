"""Wind systems three ways on the same 2020-26 games: Bet Labs' weather (its pick lists), the reconstructed PREGAME NBM forecast
(cycle issued 6-12 h before kickoff, kickoff hour + next two, at the stadium grid point), and OBSERVED weather (ERA5 reanalysis from the
Open-Meteo archive, 3-hour mean from kickoff; and the nearest airport ASOS station, mean of the routine hourly reports in the same 3 hours).
Graded: the full-game under at Pinnacle's closing total and closing under price, flat 1u to risk (favourite: to win 1u)."""
import json, math, sqlite3, datetime as dt, collections, random, sys
random.seed(11)
MPH = 2.23694; KT = 1.15078
NBM = json.load(open('nbm_cache.json')); AS = json.load(open('asos_cache.json')) if True else {}; AM = json.load(open('asos_map.json'))
ARCH = {s: json.load(open(f'arch_{s}.json')) for s in ('nfl', 'cfb')}
BL26 = json.load(open('../wt/blw2026.json'))
def nm(x): return ''.join(c for c in (x or '').lower().replace('los angeles', 'la').replace('international', 'intl').replace('state', 'st') if c.isalnum() or c == ' ').split()
def same(a, b):
    x, y = nm(a), nm(b)
    if not x or not y or x[0] != y[0]: return False
    n = min(len(x), len(y)); L = x if len(x) >= len(y) else y
    return x[:n] == y[:n] and (len(L) == n or L[n] not in ('st', 'tech', 'a', 'am', 'intl', 'southern', 'northern'))
def bl_list(sp):
    L = []
    for l in open(f'bl_{sp}.txt'):
        p = l.strip().split('|')
        if len(p) < 6: continue
        m, d, y = map(int, p[0].split('/')); L.append((dt.date(2000 + y, m, d), p[1], p[2], float(p[5])))
    sid = '1772775' if sp == 'nfl' else '1783043'
    have = {(a, b, c) for a, b, c, _ in L}
    for r in BL26[sid]:
        k = (dt.date.fromisoformat(r[0]), r[1], r[2])
        if k not in have: L.append((k[0], r[1], r[2], float(r[3])))
    return L
c = sqlite3.connect('../bl/data/oddsapi/odds.sqlite')
def close_under(gid, ct):
    q = c.execute("SELECT tot_line, tot_over, tot_under FROM quotes WHERE game_id=? AND book='pinnacle' AND t=?", (gid, ct)).fetchone()
    return q
def regular(sp, d):
    if sp == 'nfl': return not (d.month == 1 and d.day >= 12) and d.month not in (2, 3, 4, 5, 6, 7)
    return not ((d.month == 12 and d.day >= 14) or d.month == 1)
G = []
for sp in ('nfl', 'cfb'):
    BLL = bl_list(sp); used = set()
    rows = c.execute("""SELECT g.game_id, g.start, g.home, g.away, g.close_t, g.pin_close_tot, r.home_score, r.away_score, r.home_ab, r.neutral FROM games g JOIN results r USING(game_id)
                        WHERE g.sport=? AND g.start>='2020-08-01'""", (sp,)).fetchall()
    for gid, start, home, away, ct, tot, hs, as_, hab, neu in rows:
        if hs is None or tot is None or not hab or neu: continue
        st = dt.datetime.fromisoformat(start.replace('Z', '+00:00')); key = f"{hab}|{st:%Y-%m-%dT%H}"
        A = ARCH[sp].get(key)
        if A is None: continue        # not an outdoor game in our weather archive (domes and roofed stadiums are left out there)
        et = (st - dt.timedelta(hours=5)).date()
        if not regular(sp, et): continue
        pt = f"{sp}:{hab}"
        # NBM pregame
        kick = st.replace(minute=0, second=0, tzinfo=None); run = kick - dt.timedelta(hours=6); run = run.replace(hour=run.hour // 6 * 6)
        vals = []
        for h in range(3):
            e = NBM.get(f"{run:%Y%m%d%H}|{int((kick - run).total_seconds() // 3600) + h}")
            if e and 'v' in e and e['v'].get(pt) is not None: vals.append(e['v'][pt])
        nbm = round(MPH * sum(vals) / len(vals), 1) if vals else None
        # ASOS
        stn = (AM.get(pt) or [None])[0]; H = AS.get(stn) or {}
        ob = [H.get((kick + dt.timedelta(hours=h)).strftime('%Y-%m-%dT%H')) for h in range(3)]; ob = [x for x in ob if x is not None]
        asos = round(KT * sum(ob) / len(ob), 1) if ob else None
        bl = next((b for b in BLL if abs((b[0] - et).days) <= 1 and same(b[1], away) and same(b[2], home)), None)
        if bl: used.add(bl)
        q = close_under(gid, ct)
        if not q or q[0] is None or q[2] is None: continue
        ln, pu = q[0], q[2]; tt = hs + as_
        won = 0.5 if tt == ln else (1 if tt < ln else 0)
        G.append(dict(sp=sp, gid=gid, start=start, game=f"{away} @ {home}", season=et.year if et.month >= 8 else et.year - 1, nbm=nbm, era5=A.get('wind'), asos=asos,
                      bl=bl is not None, bl_wind=bl[3] if bl else None, line=ln, price=pu, won=won, asos_km=(AM.get(pt) or [None, None])[1]))
    print(sp, 'games', sum(1 for g in G if g['sp'] == sp), 'Bet Labs picks matched', len(used), 'of', len([b for b in BLL if b[0] >= dt.date(2020, 8, 1)]))
json.dump(G, open('games3.json', 'w'))
def dec(p): return p if p > 1.01 else None
def U(g):
    d = g['price']
    if g['won'] == 0.5: return 0.0, 1.0, 0.0
    return ((d - 1) if g['won'] == 1 else -1.0), 1.0, ((d - 1) ** 2 / d + (1 - 1 / d))
def phi(z): return 0.5 * (1 + math.erf(z / math.sqrt(2)))
def rec(rs):
    if not rs: return dict(n=0)
    u = sum(U(g)[0] for g in rs); v = sum(U(g)[2] for g in rs); z = u / math.sqrt(v) if v else 0
    return dict(n=len(rs), w=sum(g['won'] == 1 for g in rs), l=sum(g['won'] == 0 for g in rs), u=round(u, 2), roi=round(100 * u / len(rs), 1), p=round(1 - phi(z), 4))
OUT = {}
for rule, sp, inband in (('wind1014', 'nfl', lambda w: w is not None and 10 <= round(w) <= 14), ('cfb_wind14', 'cfb', lambda w: w is not None and round(w) >= 14)):
    R = [g for g in G if g['sp'] == sp]
    full = [g for g in R if g['nbm'] is not None and g['era5'] is not None]       # games every source covers (ASOS reported separately)
    src = {'Bet Labs': lambda g: g['bl'], 'NBM pregame': lambda g: inband(g['nbm']), 'Observed ERA5': lambda g: inband(g['era5']), 'Observed ASOS': lambda g: inband(g['asos'])}
    res = dict(games=len(full), by_source={k: rec([g for g in full if f(g)]) for k, f in src.items()})
    res['by_source_by_season'] = {k: {s: rec([g for g in full if f(g) and g['season'] == s]) for s in sorted({g['season'] for g in full})} for k, f in src.items()}
    pairs = {}
    for a, b in (('Bet Labs', 'NBM pregame'), ('Bet Labs', 'Observed ERA5'), ('Bet Labs', 'Observed ASOS'), ('NBM pregame', 'Observed ERA5'), ('NBM pregame', 'Observed ASOS')):
        fa, fb = src[a], src[b]; F = [g for g in full if (b != 'Observed ASOS' or g['asos'] is not None) and (a != 'Observed ASOS' or g['asos'] is not None)]
        both = [g for g in F if fa(g) and fb(g)]; ao = [g for g in F if fa(g) and not fb(g)]; bo = [g for g in F if fb(g) and not fa(g)]
        pairs[f"{a} vs {b}"] = dict(games=len(F), agree_pct=round(100 * sum(fa(g) == fb(g) for g in F) / max(1, len(F)), 1),
                                    plays_overlap_pct=round(100 * len(both) / max(1, len(both) + len(ao) + len(bo)), 1), both=rec(both), only_a=rec(ao), only_b=rec(bo))
    res['pairs'] = pairs
    # Q2: is Bet Labs' wind a forecast or an observation? On its own picks, how close is its number to each source.
    P = [g for g in full if g['bl'] and g['bl_wind'] is not None]
    def err(key, rs):
        x = [(g['bl_wind'] - g[key]) for g in rs if g.get(key) is not None]
        if not x: return None
        return dict(n=len(x), mae=round(sum(abs(v) for v in x) / len(x), 2), bias=round(sum(x) / len(x), 2),
                    in_band=round(100 * sum(1 for g in rs if g.get(key) is not None and inband(g[key])) / len(x), 1))
    res['bl_number_vs'] = {k: err(k, P) for k in ('nbm', 'era5', 'asos')}
    # correlation of Bet Labs' number with each source
    def corr(key):
        x = [(g['bl_wind'], g[key]) for g in P if g.get(key) is not None]
        if len(x) < 5: return None
        ma = sum(a for a, _ in x) / len(x); mb = sum(b for _, b in x) / len(x)
        cov = sum((a - ma) * (b - mb) for a, b in x); va = sum((a - ma) ** 2 for a, _ in x); vb = sum((b - mb) ** 2 for _, b in x)
        return round(cov / math.sqrt(va * vb), 3) if va and vb else None
    res['bl_corr'] = {k: corr(k) for k in ('nbm', 'era5', 'asos')}
    OUT[rule] = res
    print('\n==', rule, 'games', len(full))
    for k, v in res['by_source'].items(): print(f"  {k:15s} {v}")
    for k, v in pairs.items(): print(f"  {k:32s} agree {v['agree_pct']}% overlap {v['plays_overlap_pct']}% | both {v['both'].get('n')} {v['both'].get('roi')} | only A {v['only_a'].get('n')} {v['only_a'].get('roi')} | only B {v['only_b'].get('n')} {v['only_b'].get('roi')}")
    print('  Bet Labs number vs:', res['bl_number_vs'], 'corr', res['bl_corr'])
json.dump(OUT, open('three.json', 'w'), indent=1)
