#!/usr/bin/env python3
"""Market tests on The Odds API closes (Sean, 11/4: "backtest everything we couldn't before: tennis, MMA, CBB and all other sports; test
as many theories as you like"). Every snapshot in data/oddsapi is folded into one row per game: the last snapshot before the start
(the close; for tennis and MMA the last one before the match, hours earlier at worst), Pinnacle's no-vig probabilities, lines and
prices, and the best US-book price per side. Results from ESPN (data/state/hist_schedule.json for team sports and MMA,
data/tennis/results.jsonl for tennis). Then, per sport, the theories that need only a close and a result:

  1. Calibration and bias: favourite-longshot (by Pinnacle probability band), home / away, over / under, by book.
  2. Pinnacle vs the US books: when DK / FD / Caesars / BetMGM price a side above Pinnacle's no-vig number by x%, flat ROI betting
     it at that book (the +EV / off-market angle, measured per sport and market, so the ruler knows where it is real).
  3. Spreads and totals: by line size and key numbers (NFL / CFB 3 and 7, NBA 1-2 points off round numbers), push rates.
  4. Tennis: the Tennis Abstract features (Elo, form, serve profile, layoff, surface switch, first match, h2h) against TOUR-level
     closes, the test the slam bundle could not run; the hot-favourite and serve-profile paper angles at tour level.
  5. MMA: favourite-longshot, rounds-total bias, Pinnacle vs books; the price bands where dogs pay.
  6. CBB: the two tier-C rules' ingredients (over rates, drops) need season logs; here: bias, key numbers, Pinnacle vs books, and
     a conference-vs-non-conference / weekday split of the totals bias.
Writes data/research/oddsapi_edge.json and prints the tables. Usage: python3 sharp/oddsapi_edge.py [sport ...]"""
import os, sys, json, gzip, glob, math, re, collections, datetime as dt, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
OA = os.path.join(ROOT, 'data', 'oddsapi'); OUT = os.path.join(ROOT, 'data', 'research', 'oddsapi_edge.json')
US = ('draftkings', 'fanduel', 'williamhill_us', 'betmgm')
KEYS = {'nfl': (3, 7), 'cfb': (3, 7)}


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def norm(s): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower())


def load_sport(sport):
    """-> {game key: {home, away, start, snaps: [(snap_time, bookmakers)]}} from every snapshot file of the sport (tennis: all keys)."""
    files = sorted(glob.glob(os.path.join(OA, sport, '*.json.gz')) + glob.glob(os.path.join(OA, sport, '*', '*.json.gz')))
    G = {}
    for f in files:
        try: d = json.load(gzip.open(f, 'rt'))
        except Exception: continue
        t = d.get('timestamp')
        if not t: continue
        for g in d.get('data') or []:
            k = g['id']; G.setdefault(k, dict(home=g['home_team'], away=g['away_team'], start=g['commence_time'], snaps=[], key=os.path.basename(os.path.dirname(f)) if sport == 'tennis' else sport))
            G[k]['snaps'].append((t, g.get('bookmakers') or []))
    return G


def fold(g):
    """The last snapshot before the start -> one row: pinnacle no-vig p_home, spread line/prices, total line/prices, best US prices."""
    st = ts(g['start']); pre = [(t, b) for t, b in g['snaps'] if ts(t) < st]
    if not pre: return None
    t, books = max(pre, key=lambda x: x[0])
    row = dict(home=g['home'], away=g['away'], start=g['start'], snap=t, hours_before=round((st - ts(t)).total_seconds() / 3600, 1), key=g.get('key'))
    B = {b['key']: {m['key']: m['outcomes'] for m in b.get('markets') or []} for b in books}
    def h2h(bk):
        o = B.get(bk, {}).get('h2h')
        if not o: return None
        p = {x['name']: 1 / x['price'] for x in o if x.get('price')}
        if g['home'] not in p or g['away'] not in p: return None
        return dict(home=p[g['home']], away=p[g['away']], nv_home=p[g['home']] / (p[g['home']] + p[g['away']]), dec_home=1 / p[g['home']], dec_away=1 / p[g['away']])
    pin = h2h('pinnacle')
    if pin: row.update(p_home=round(pin['nv_home'], 4), pin_dec_home=round(pin['dec_home'], 3), pin_dec_away=round(pin['dec_away'], 3), vig=round(pin['home'] + pin['away'] - 1, 4))
    best = {'home': None, 'away': None}
    for bk in US:
        x = h2h(bk)
        if not x: continue
        for s in ('home', 'away'):
            if best[s] is None or x[f'dec_{s}'] > best[s][0]: best[s] = (x[f'dec_{s}'], bk)
    row['best_home'], row['best_away'] = best['home'], best['away']
    for mk, nm in (('spreads', 'spread'), ('totals', 'total')):
        o = B.get('pinnacle', {}).get(mk)
        if o:
            if nm == 'spread':
                h = next((x for x in o if x['name'] == g['home']), None); a = next((x for x in o if x['name'] == g['away']), None)
                if h and a and h.get('point') is not None: row.update(spread_home=h['point'], spread_home_dec=h['price'], spread_away_dec=a['price'])
            else:
                ov = next((x for x in o if x['name'] == 'Over'), None); un = next((x for x in o if x['name'] == 'Under'), None)
                if ov and un and ov.get('point') is not None: row.update(total=ov['point'], over_dec=ov['price'], under_dec=un['price'])
        bl = {}
        for bk in US:
            o2 = B.get(bk, {}).get(mk)
            if not o2: continue
            for x in o2:
                if x.get('point') is None or not x.get('price'): continue
                side = 'home' if x['name'] == g['home'] else 'away' if x['name'] == g['away'] else x['name'].lower()
                cur = bl.get((side, x['point']))
                if cur is None or x['price'] > cur[0]: bl[(side, x['point'])] = (x['price'], bk)
        row[f'{nm}_books'] = {f"{s}|{pt}": v for (s, pt), v in bl.items()}
    return row


def results_team(sport):
    H = json.load(open(os.path.join(ROOT, 'data', 'state', 'hist_schedule.json'))).get(sport, {})
    # ESPN abbreviations <-> Odds API full names, from the cached ESPN team lists (data/state/espn_teams.json)
    try: T = json.load(open(os.path.join(ROOT, 'data', 'state', 'espn_teams.json'))).get(sport, {})
    except Exception: T = {}
    names = {ab: t.get('name') for ab, t in T.items() if t.get('name')}
    alt = {}
    for ab, t in T.items():
        for k in (t.get('name'), (t.get('loc') or '') + ' ' + (t.get('nick') or ''), t.get('short')):
            if k: alt[norm(k)] = ab
    return H, names, alt


def main(sports):
    R = {}
    for sport in sports:
        G = load_sport(sport)
        rows = [r for r in (fold(g) for g in G.values()) if r]
        print(f"\n#### {sport}: {len(G)} games in snapshots, {len(rows)} with a pre-start snapshot (median {sorted(r['hours_before'] for r in rows)[len(rows) // 2] if rows else '-'}h before)")
        if sport in ('tennis',): res = results_tennis(rows)
        elif sport == 'mma': res = results_mma(rows)
        else: res = results_games(sport, rows)
        print(f"     joined to results: {res}")
        R[sport] = tests(sport, rows)
        if sport == 'tennis': R['tennis_ta'] = tennis_ta(rows)
    json.dump(R, open(OUT, 'w'), indent=1, default=str)


def results_games(sport, rows):
    H, names, alt = results_team(sport)
    full2abbr = {norm(v): k for k, v in names.items()}; full2abbr.update(alt)
    def ab(name):
        n = norm(name)
        if n in full2abbr: return full2abbr[n]
        # Odds API sometimes drops or adds a word (e.g. 'St.' vs 'State', 'Hawai'i'): longest ESPN name contained in it, or containing it
        best = None
        for k, v in full2abbr.items():
            if len(k) >= 6 and (k in n or n in k) and (best is None or len(k) > len(best[0])): best = (k, v)
        return best[1] if best else None
    byday = collections.defaultdict(list)
    for ev, h in H.items():
        if h.get('hs') is None: continue
        byday[h['start'][:10]].append(h)
    n = 0
    for r in rows:
        d = r['start'][:10]; cands = byday.get(d, []) + byday.get((ts(r['start']) + dt.timedelta(days=1)).strftime('%Y-%m-%d'), []) + byday.get((ts(r['start']) - dt.timedelta(days=1)).strftime('%Y-%m-%d'), [])
        hn, an = norm(r['home']), norm(r['away'])
        hit = None
        ha, aa = ab(r['home']), ab(r['away'])
        for h in cands:
            if ha and aa and h['home'] == ha and h['away'] == aa and abs((ts(h['start']) - ts(r['start'])).total_seconds()) < 6 * 3600: hit = h; break
        if hit: r['hs'], r['as'] = hit['hs'], hit['as_']; n += 1
    return f"{n}/{len(rows)}"


def results_mma(rows):
    H = json.load(open(os.path.join(ROOT, 'data', 'state', 'hist_schedule.json'))).get('mma', {})
    idx = {}
    for k, h in H.items():
        if h.get('final') and h.get('winner'): idx[(norm(h['p1']), norm(h['p2']))] = h; idx[(norm(h['p2']), norm(h['p1']))] = h
    n = 0
    for r in rows:
        h = idx.get((norm(r['home']), norm(r['away'])))
        if not h: continue
        w = norm(h['winner']); r['winner'] = 'home' if w == norm(r['home']) else 'away' if w == norm(r['away']) else None
        if r['winner']: n += 1
    return f"{n}/{len(rows)}"


def results_tennis(rows):
    L = [json.loads(l) for l in open(os.path.join(ROOT, 'data', 'tennis', 'results.jsonl'))]
    idx = collections.defaultdict(list)
    for m in L:
        if m.get('status') != 'STATUS_FINAL' or not m.get('winner'): continue
        idx[(norm(m['p1']), norm(m['p2']))].append(m); idx[(norm(m['p2']), norm(m['p1']))].append(m)
    n = 0
    for r in rows:
        ms = idx.get((norm(r['home']), norm(r['away']))) or []
        ms = [m for m in ms if abs((ts(m['start']) - ts(r['start'])).total_seconds()) < 36 * 3600]
        if not ms: continue
        m = ms[0]; wn = norm(m['p1'] if m['winner'] == 'p1' else m['p2'])
        r['winner'] = 'home' if wn == norm(r['home']) else 'away' if wn == norm(r['away']) else None
        r['sets'] = m.get('sets'); r['first_set_winner'] = m.get('first_set_winner'); r['p1'] = m['p1']; r['retired'] = m.get('retired')
        if r['winner']: n += 1
    return f"{n}/{len(rows)}"


def se(p, n): return round(100 * math.sqrt(max(p * (1 - p), 1e-9) / n), 1) if n else None


def tests(sport, rows):
    R = {}
    CLOSE_H = 6 if sport not in ('tennis', 'mma') else 16
    graded = [r for r in rows if r.get('p_home') is not None and (r.get('winner') or r.get('hs') is not None) and r['hours_before'] <= CLOSE_H]
    for r in graded:
        if r.get('winner') is None: r['winner'] = 'home' if r['hs'] > r['as'] else 'away' if r['as'] > r['hs'] else 'push'
    def table(name, keyf, sidef, rows_, min_n=25):
        T = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0, 0])
        for r in rows_:
            k = keyf(r); s = sidef(r)
            if k is None or s is None or r['winner'] == 'push': continue
            q = r['p_home'] if s == 'home' else 1 - r['p_home']; dec = r['pin_dec_home'] if s == 'home' else r['pin_dec_away']
            bb = r.get(f'best_{s}'); won = r['winner'] == s
            t = T[k]; t[0] += 1; t[1] += won; t[2] += q; t[3] += (dec - 1) if won else -1
            if bb: t[4] += (bb[0] - 1) if won else -1; t[5] += 1
        out = {}
        for k, (n, w, q, pnl, pnlb, nb) in sorted(T.items(), key=lambda kv: str(kv[0])):
            if n < min_n: continue
            out[str(k)] = dict(n=n, win=round(w / n, 3), pin_nv=round(q / n, 3), edge=round(100 * (w / n - q / n), 1), se=se(q / n, n), roi_pin=round(100 * pnl / n, 1), roi_best_us=round(100 * pnlb / nb, 1) if nb else None)
        R[name] = out
    band = lambda p: f"{math.floor(p * 10) / 10:.1f}"
    fav = lambda r: 'home' if r['p_home'] >= .5 else 'away'; dog = lambda r: 'away' if r['p_home'] >= .5 else 'home'
    pf = lambda r: max(r['p_home'], 1 - r['p_home'])
    table('1a favourite by Pinnacle no-vig band (bet fav)', lambda r: band(pf(r)), fav, graded)
    table('1b dog by band (bet dog)', lambda r: band(pf(r)), dog, graded)
    if sport not in ('tennis', 'mma'):
        table('1c home / away (bet home)', lambda r: 'home', lambda r: 'home', graded)
        table('1d home dog / away dog (bet dog)', lambda r: 'home dog' if r['p_home'] < .5 else 'away dog', dog, graded)
    # 2. Pinnacle vs the US books
    def off(r, s):
        bb = r.get(f'best_{s}')
        if not bb: return None
        q = r['p_home'] if s == 'home' else 1 - r['p_home']
        return 100 * (q - 1 / bb[0])          # Pinnacle no-vig minus the book's implied: positive = the book is paying more than fair
    for s_name, sf in (('fav', fav), ('dog', dog)):
        table(f'2 US book price vs Pinnacle no-vig, bet the {s_name} at the best US book', lambda r, sf=sf: (lambda o: None if o is None else ('book pays 1%+ over fair' if o >= 1 else 'book 0-1% over fair' if o >= 0 else 'book 0-1% under fair' if o >= -1 else 'book 1-2% under fair' if o >= -2 else 'book 2-3% under fair' if o >= -3 else 'book 3%+ under fair'))(off(r, sf(r))), sf, graded)
    # 3. spreads and totals (team sports)
    if sport not in ('tennis', 'mma'):
        SP = [r for r in graded if r.get('spread_home') is not None and r.get('hs') is not None]
        T = collections.defaultdict(lambda: [0, 0, 0, 0])
        for r in SP:
            m = (r['hs'] - r['as']) + r['spread_home']; k = f"home {'fav' if r['spread_home'] < 0 else 'dog'} {abs(r['spread_home']):.1f}" if abs(r['spread_home']) in KEYS.get(sport, ()) else f"home {'fav' if r['spread_home'] < 0 else 'dog'} {'1-3' if abs(r['spread_home']) <= 3 else '3.5-7' if abs(r['spread_home']) <= 7 else '7.5-14' if abs(r['spread_home']) <= 14 else '14+'}"
            t = T[k]; t[0] += 1; t[1] += m > 0; t[2] += m < 0; t[3] += m == 0
        R['3a home ATS by spread band (Pinnacle close)'] = {k: dict(n=n, home_cover=round(w / (w + l), 3) if w + l else None, push=round(p / n, 3)) for k, (n, w, l, p) in sorted(T.items()) if n >= 25}
        TO = [r for r in graded if r.get('total') is not None and r.get('hs') is not None]
        T = collections.defaultdict(lambda: [0, 0, 0, 0, 0.0])
        for r in TO:
            tt = r['hs'] + r['as']; k = f"total {'low' if r['total'] < sorted(x['total'] for x in TO)[len(TO) // 3] else 'high' if r['total'] > sorted(x['total'] for x in TO)[2 * len(TO) // 3] else 'mid'}"
            t = T[k]; t[0] += 1; t[1] += tt > r['total']; t[2] += tt < r['total']; t[3] += tt == r['total']; t[4] += (1 / r['over_dec']) / (1 / r['over_dec'] + 1 / r['under_dec'])
            t = T['all']; t[0] += 1; t[1] += tt > r['total']; t[2] += tt < r['total']; t[3] += tt == r['total']; t[4] += (1 / r['over_dec']) / (1 / r['over_dec'] + 1 / r['under_dec'])
        R['3b over rate by total band (Pinnacle close) vs Pinnacle no-vig over'] = {k: dict(n=n, over=round(o / (o + u), 3) if o + u else None, pin_over=round(q / n, 3), push=round(p / n, 3)) for k, (n, o, u, p, q) in sorted(T.items()) if n >= 25}
        # the US books' totals vs Pinnacle's line: when a book's number is 0.5+ off Pinnacle's, bet toward Pinnacle at that book
        T = collections.defaultdict(lambda: [0, 0, 0.0])
        for r in TO:
            for k2, (dec, bk) in (r.get('total_books') or {}).items():
                side, pt = k2.split('|'); pt = float(pt)
                if side == 'over' and pt <= r['total'] - 0.5: won = r['hs'] + r['as'] > pt; push = r['hs'] + r['as'] == pt
                elif side == 'under' and pt >= r['total'] + 0.5: won = r['hs'] + r['as'] < pt; push = r['hs'] + r['as'] == pt
                else: continue
                if push: continue
                t = T[f"{side} at a book {abs(pt - r['total']):.1f}+ better than Pinnacle"]; t[0] += 1; t[1] += won; t[2] += (dec - 1) if won else -1
        R['3c totals: book number 0.5+ better than Pinnacle close, bet toward Pinnacle'] = {k: dict(n=n, win=round(w / n, 3), roi=round(100 * pnl / n, 1)) for k, (n, w, pnl) in sorted(T.items()) if n >= 30}
    R['_n'] = dict(rows=len(rows), graded=len(graded), pin=sum(1 for r in rows if r.get('p_home') is not None))
    for k, v in R.items():
        if k.startswith('_'): continue
        print(f"\n== {k}")
        for kk, vv in v.items(): print(f"  {kk:48} {vv}")
    return R


def tennis_ta(rows):
    """The Tennis Abstract feature test against TOUR-level closes (sharp/tennis_edge.py's cuts, fed Odds API rows instead of the slam bundle).
    An Odds API row becomes a tennis-data-style row: winner / loser from the ESPN result, Pinnacle decimal prices, the set-1 score."""
    import sharp.tennis_edge as TE
    O = []
    for r in rows:
        if not r.get('winner') or r.get('p_home') is None or r['hours_before'] > 16 or r.get('retired'): continue
        w, l = (r['home'], r['away']) if r['winner'] == 'home' else (r['away'], r['home'])
        psw, psl = (r['pin_dec_home'], r['pin_dec_away']) if r['winner'] == 'home' else (r['pin_dec_away'], r['pin_dec_home'])
        st = r.get('sets') or []
        s1 = st[0] if st else None
        # ESPN sets are [p1 games, p2 games]; p1 is the ESPN first-listed player
        w_is_p1 = norm(r.get('p1') or '') == norm(w)
        w1, l1 = ((s1[0], s1[1]) if w_is_p1 else (s1[1], s1[0])) if s1 else (None, None)
        tour = 'wta' if '_wta_' in (r.get('key') or '') else 'atp'
        bo = 5 if tour == 'atp' and any(x in (r.get('key') or '') for x in ('aus_open', 'french_open', 'wimbledon', 'us_open')) else 3
        O.append(dict(tour=tour, date=ts(r['start']).date(), tourney=r.get('key'), surface=None, rnd=None, bo=bo, wk=TE.key_odds(last_initial(w)), lk=TE.key_odds(last_initial(l)),
                      wname=w, lname=l, w1=w1, l1=l1, psw=psw, psl=psl, b365w=None, b365l=None,
                      maxw=(r['best_home'][0] if r['winner'] == 'home' else r['best_away'][0]) if r.get('best_home') and r.get('best_away') else None,
                      maxl=(r['best_away'][0] if r['winner'] == 'home' else r['best_home'][0]) if r.get('best_home') and r.get('best_away') else None, avgw=None, avgl=None, comment=''))
    print(f"\n#### tennis x Tennis Abstract: {len(O)} tour-level matches with a Pinnacle price and a result")
    if len(O) < 50: return {}
    TE.main(O, out=os.path.join(ROOT, 'data', 'research', 'tennis_edge_tour.json'))
    return json.load(open(os.path.join(ROOT, 'data', 'research', 'tennis_edge_tour.json')))


def last_initial(name):
    """'Carlos Alcaraz' -> 'Alcaraz C.' (the tennis-data name shape tennis_edge keys on)."""
    p = (name or '').replace('-', ' ').split()
    return f"{' '.join(p[1:])} {p[0][0]}." if len(p) >= 2 else name


if __name__ == '__main__':
    main(sys.argv[1:] or ['nba', 'nhl', 'nfl', 'cfb', 'cbb', 'mma', 'tennis'])
