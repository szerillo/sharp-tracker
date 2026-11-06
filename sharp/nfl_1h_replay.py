#!/usr/bin/env python3
"""NFL first-half rules on the Winners Circle database (Sean 11/5: test the derivatives now that we have them).
1H lines: data/oddsapi/derivs/nfl.jsonl.gz (Odds API historical, snapshot 10 minutes before kickoff, 2023-05 on): Pinnacle's 1H total and
1H spread with prices, falling back to the median of the US books when Pinnacle has no quote. 1H scores: ESPN linescores
(data/state/linescores.json via sharp/linescores.py). Weather, rest and last-game ATS margin as in sharp/nfl_replay.py.
Rules: wind1014_1h (wind 10-13: 1H under), vrest8_1h (visitor off 8-30 days, week 1 excluded: 1H under), mnf_1h (Monday night: 1H under),
bounce15_1h (dog whose last game lost ATS by 15+: 1H spread). Graded flat at the price. Writes data/research/nfl_1h_replay.json.
Usage: python3 sharp/nfl_1h_replay.py"""
import os, sys, json, gzip, sqlite3, statistics as st, collections, datetime as dt
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.rule_replay as RR, sharp.nfl_replay as NR, sharp.oddsapi_edge as E
ET = ZoneInfo('America/New_York'); OUT = os.path.join(ROOT, 'data', 'research', 'nfl_1h_replay.json')


def lines(game):
    """(tot_line, over_dec, under_dec, home_sp_line, home_sp_dec, away_sp_dec, src) at the snapshot."""
    B = {b['key']: {m['key']: m['outcomes'] for m in b['markets']} for b in game['bookmakers']}
    def tot(o):
        ov = next((x for x in o if x['name'] == 'Over'), None); un = next((x for x in o if x['name'] == 'Under'), None)
        return (ov['point'], ov['price'], un['price']) if ov and un and ov.get('point') == un.get('point') else None
    def spr(o):
        h = next((x for x in o if x['name'] == game['home']), None); a = next((x for x in o if x['name'] == game['away']), None)
        return (h['point'], h['price'], a['price']) if h and a else None
    out = {}
    for mk, fn in (('totals_h1', tot), ('spreads_h1', spr)):
        P = B.get('pinnacle', {}).get(mk)
        v = fn(P) if P else None
        if v: out[mk] = v + ('pinnacle',); continue
        vals = [fn(b[mk]) for k, b in B.items() if mk in b and k != 'bovada']
        vals = [x for x in vals if x]
        if vals:
            ln = st.median(x[0] for x in vals); same = [x for x in vals if x[0] == ln] or vals
            out[mk] = (ln, st.mean(x[1] for x in same), st.mean(x[2] for x in same), 'books')
    return out


def main():
    D = {}
    for l in gzip.open(os.path.join(ROOT, 'data', 'oddsapi', 'derivs', 'nfl.jsonl.gz'), 'rt'):
        r = json.loads(l)
        if r['bookmakers']: D[r['game_id']] = r
    LS = json.load(open(os.path.join(ROOT, 'data', 'state', 'linescores.json'))).get('nfl', {})
    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    ESPN = dict(conn.execute("SELECT game_id, espn_id FROM results WHERE espn_id IS NOT NULL").fetchall())
    G = RR.load('nfl'); A = NR.abbr_map()
    for g in G: g['hab'] = A.get(E.norm(g['home'])); g['aab'] = A.get(E.norm(g['away']))
    G = [g for g in G if g['hs'] is not None and g['hab'] and g['aab'] and g['hab'] not in ('AFC', 'NFC')]
    G.sort(key=lambda g: g['start']); hist = collections.defaultdict(list)
    for g in G:          # rest days and last-game ATS margin from the full history (2020 on), before this game
        sn = RR.season_of('nfl', g['start'] - dt.timedelta(days=60))      # 11/6 audit: per season (week 1 read last season's final game and 200+ days of rest)
        for side, team in (('home', g['hab']), ('away', g['aab'])):
            L = hist[(team, sn)]
            g[f'{side}_days'] = (g['start'].astimezone(ET).date() - L[-1]['start'].astimezone(ET).date()).days if L else None
            g[f'{side}_last_ats'] = L[-1]['ats'] if L else None
        if g.get('sp_close') is not None:
            hist[(g['hab'], sn)].append(dict(start=g['start'], ats=(g['hs'] - g['as_']) + g['sp_close']))
            hist[(g['aab'], sn)].append(dict(start=g['start'], ats=(g['as_'] - g['hs']) - g['sp_close']))
    rows = []
    for g in G:
        d = D.get(g['id']); ls = LS.get(str(ESPN.get(g['id'])))
        if not d or not ls or len(ls.get('h', [])) < 2: continue
        L = lines(d)
        h1, a1 = sum(ls['h'][:2]), sum(ls['a'][:2]); g['h1'] = (h1, a1); g['L'] = L
        g['wx'] = NR.weather(g['hab'], g['start']) if g['hab'] in NR.OUTDOOR else None
        rows.append(g)
    print(f'NFL games with a 1H line and 1H score: {len(rows)} ({rows[0]["start"]:%Y-%m-%d} to {rows[-1]["start"]:%Y-%m-%d})')

    def g_tot(g, side):
        t = g['L'].get('totals_h1')
        if not t: return None
        pts = sum(g['h1']); ln, ov, un = t[0], t[1], t[2]
        won = 0.5 if pts == ln else 1 if (pts < ln) == (side == 'under') else 0
        return won, (un if side == 'under' else ov)

    def g_sp(g, side):
        s = g['L'].get('spreads_h1')
        if not s: return None
        ln_h, ph, pa = s[0], s[1], s[2]; m = g['h1'][0] - g['h1'][1]
        cov = m + ln_h if side == 'home' else -m - ln_h
        return (0.5 if cov == 0 else 1 if cov > 0 else 0), (ph if side == 'home' else pa)

    H = collections.defaultdict(list)
    for g in rows:
        et = g['start'].astimezone(ET); season = RR.season_of('nfl', g['start'])
        u = g_tot(g, 'under')
        if u: H['all games: 1H under (baseline)'].append((season, u))
        wx = g.get('wx'); w = round(wx['wind']) if wx and wx.get('wind') is not None else None
        if w is not None and u:
            band = '0-5' if w <= 5 else '6-9' if w <= 9 else '10-13 (the rule)' if w <= 13 else '14' if w == 14 else '15+'
            H[f'wind1014_1h | wind {band}: 1H under'].append((season, u))
        vd = g.get('away_days')
        if vd is not None and u: H[f"vrest8_1h | visitor {'off 8-30 days (the rule)' if 8 <= vd <= 30 else 'normal week' if vd < 8 else 'week 1 / 31+'}: 1H under"].append((season, u))
        if u: H[f"mnf_1h | {'Monday night (the rule)' if et.strftime('%A') == 'Monday' and et.hour >= 18 else 'Sunday night' if et.strftime('%A') == 'Sunday' and et.hour >= 19 else 'Thursday night' if et.strftime('%A') == 'Thursday' else 'other slots'}: 1H under"].append((season, u))
        sp = g['L'].get('spreads_h1')
        if g.get('sp_close') is not None:
            dog = 'away' if g['sp_close'] < 0 else 'home' if g['sp_close'] > 0 else None
            la = g.get(f'{dog}_last_ats') if dog else None
            if dog and la is not None:
                r = g_sp(g, dog)
                if r: H[f"bounce15_1h | dog's last game ATS {'lost by 15+ (the rule)' if la <= -15 else 'lost by 7-14' if la <= -7 else 'other'}: dog 1H spread"].append((season, r))
    R = {}
    for k in sorted(H):
        L = H[k]; w = sum(1 for _, (x, _) in L if x == 1); l = sum(1 for _, (x, _) in L if x == 0)
        pl = sum((p - 1) if x == 1 else -1 if x == 0 else 0 for _, (x, p) in L)
        by = collections.defaultdict(lambda: [0, 0, 0.0])
        for s, (x, p) in L:
            b = by[s]; b[0] += x == 1; b[1] += x == 0; b[2] += (p - 1) if x == 1 else -1 if x == 0 else 0
        R[k] = dict(w=w, l=l, n=len(L), roi=round(100 * pl / max(1, w + l), 1), seasons={s: f'{a}-{b_} {100 * c / max(1, a + b_):+.1f}%' for s, (a, b_, c) in sorted(by.items())})
        print(f"{k:70s} {w}-{l}  {R[k]['roi']:+.1f}%   {' | '.join(f'{s}: {v}' for s, v in R[k]['seasons'].items())}")
    json.dump(dict(games=len(rows), results=R), open(OUT, 'w'), indent=1); print('wrote', OUT)


if __name__ == '__main__':
    main()
