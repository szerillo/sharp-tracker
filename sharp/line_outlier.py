"""Outlier book on spreads and totals (Sean 11/9, list item 3; the game-line version of the props outlier test).
Odds API history (data/oddsapi/compact/<plan>.jsonl.gz, 2020-26, every book, many snapshots per game). In each snapshot inside the window
before the start: Pinnacle's spread (home number) and total; a book hanging a different number. 'Outlier' = 2+ other books (BetMGM and the
offshore books count toward agreement, never as the bet) on Pinnacle's exact number, so the odd one out is the book. The bet is the side
the gap favours at the book (more points / the lower total for the over / the higher total for the under), at the book's own number and
price. First qualifying snapshot per game, market, side and book; then one bet per game, market and side (largest gap, then best price).
Graded on ESPN finals (data/state/hist_schedule.json via sharp/odds_db.results). Also split by whether Pinnacle had just moved to its
number (the book is lagging a move) and, for the NFL, whether the gap crosses 3 or 7.
Usage: python3 sharp/line_outlier.py <compact dir> <sport plans, e.g. nfl or nba,nba2> [window hours, default 3] [out.json]"""
import os, sys, json, gzip, math, sqlite3, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.odds_db as ODB
SRC, PLANS = sys.argv[1], sys.argv[2].split(',')
WIN = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
BET = {'draftkings': 'DK', 'fanduel': 'FD', 'williamhill_us': 'Caesars', 'betrivers': 'BetRivers', 'fanatics': 'Fanatics', 'espnbet': 'theScore'}
OFF = {'betonlineag': 'BetOnline', 'bovada': 'Bovada', 'lowvig': 'LowVig'}
P = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))

snaps = collections.defaultdict(list); games = {}
for plan in PLANS:
    for l in gzip.open(os.path.join(SRC, f'{plan}.jsonl.gz'), 'rt'):
        try: d = json.loads(l)
        except Exception: continue
        h = (P(d['start']) - P(d['t'])).total_seconds() / 3600
        if not 0 < h <= max(WIN, 3): continue
        b = {k: (v.get('sp'), v.get('tot')) for k, v in d['books'].items() if v.get('sp') or v.get('tot')}
        if 'pinnacle' not in b: continue
        snaps[d['id']].append((d['t'], h, b)); games[d['id']] = (d['sport'], d['key'], d['start'], d['home'], d['away'])
print(f'[line_outlier] {"+".join(PLANS)}: {len(games)} games with a Pinnacle quote inside {WIN:g}h', flush=True)

conn = sqlite3.connect(':memory:')
conn.executescript("""CREATE TABLE games(game_id TEXT PRIMARY KEY, sport TEXT, key TEXT, start TEXT, home TEXT, away TEXT);
  CREATE TABLE results(game_id TEXT PRIMARY KEY, home_score REAL, away_score REAL, winner TEXT, src TEXT, ot INT, conf INT, neutral INT, home_ab TEXT, away_ab TEXT, espn_id TEXT);""")
conn.executemany("INSERT INTO games VALUES (?,?,?,?,?,?)", [(g, *v) for g, v in games.items()])
_p = print; print = lambda *a, **k: None
try: ODB.results(conn)
finally: print = _p
RES = {g: (h, a) for g, h, a in conn.execute("SELECT game_id, home_score, away_score FROM results")}
print(f'[line_outlier] finals matched for {sum(1 for g in games if g in RES)} of {len(games)}', flush=True)

rows = []
for gid, S in snaps.items():
    if gid not in RES: continue
    hs, as_ = RES[gid]; S.sort(key=lambda x: (x[0], -x[1])); seen = set(); prev_pin = {}
    sport = games[gid][0]
    for t, h, B in S:
        pin = B['pinnacle']
        for mi, mk in ((0, 'spread'), (1, 'total')):
            q = pin[mi]
            if not q: continue
            pl = q[0]; moved = prev_pin.get(mk) is not None and prev_pin[mk] != pl; pmove = (pl - prev_pin[mk]) if moved else 0
            prev_pin[mk] = pl
            if h > WIN: continue
            for bk, name in BET.items():
                bq = (B.get(bk) or (None, None))[mi]
                if not bq or bq[0] == pl: continue
                bl = bq[0]; gap = abs(bl - pl)
                agree = sum(1 for k2, v2 in B.items() if k2 not in (bk, 'pinnacle') and v2[mi] and v2[mi][0] == pl)
                near = sum(1 for k2, v2 in B.items() if k2 not in (bk, 'pinnacle') and v2[mi] and abs(v2[mi][0] - pl) <= 0.5)
                if mk == 'spread':
                    side = 'home' if bl > pl else 'away'; pr = bq[1] if side == 'home' else bq[2]
                    m = (hs - as_) + bl if side == 'home' else (as_ - hs) - bl      # cover margin at the book's number
                    lagging = moved and ((pmove < 0 and side == 'home') or (pmove > 0 and side == 'away'))   # Pinnacle moved toward the side's opponent: book stale
                    crosses = sport == 'nfl' and bl * pl > 0 and any(min(abs(bl), abs(pl)) <= k <= max(abs(bl), abs(pl)) for k in (3, 7))
                else:
                    side = 'over' if bl < pl else 'under'; pr = bq[1] if side == 'over' else bq[2]
                    tot = hs + as_; m = (tot - bl) if side == 'over' else (bl - tot)
                    lagging = moved and ((pmove > 0 and side == 'over') or (pmove < 0 and side == 'under'))
                    crosses = False
                if not pr or pr <= 1: continue
                key = (gid, mk, side, bk)
                if key in seen: continue
                seen.add(key)
                rows.append(dict(gid=gid, mk=mk, side=side, book=name, gap=gap, agree=agree, near=near, pr=pr, won=None if m == 0 else m > 0, h=h,
                                 season=games[gid][2][:4], lag=lagging, moved=moved, crosses=crosses, pl=pl, bl=bl))

def dd(L):
    g = {}
    for r in L:
        k = (r['gid'], r['mk'], r['side'])
        if k not in g or (r['gap'], r['pr']) > (g[k]['gap'], g[k]['pr']): g[k] = r
    return list(g.values())
def stats(L):
    L = [r for r in L if r['won'] is not None]
    if not L: return None
    n = len(L); w = sum(r['won'] for r in L); pnl = sum((r['pr'] - 1) if r['won'] else -1 for r in L); be = sum(1 / r['pr'] for r in L) / n
    s = collections.defaultdict(lambda: [0, 0.0])
    for r in L: s[r['season']][0] += 1; s[r['season']][1] += (r['pr'] - 1) if r['won'] else -1
    return dict(n=n, w=w, l=n - w, roi=round(100 * pnl / n, 1), z=round((w / n - be) / math.sqrt(be * (1 - be) / n), 2),
                pos=sum(1 for v in s.values() if v[1] > 0), ns=len(s), seasons={k: round(100 * v[1] / v[0], 1) for k, v in sorted(s.items())})
OUT = {}
def rep(label, L, key=None):
    s = stats(L)
    if key: OUT[key] = s
    if not s or s['n'] < 30: return
    print(f"{label:60} n={s['n']:5} {s['w']}-{s['l']:<5} ROI {s['roi']:+6.1f}%  z {s['z']:+5.2f}  seasons+ {s['pos']}/{s['ns']}  " + ' '.join(f"{k[2:]}:{v:+.0f}%" for k, v in s['seasons'].items()))
for mk in ('spread', 'total'):
    R = [r for r in rows if r['mk'] == mk]
    print(f'--- {mk} (window {WIN:g}h before the start)')
    for lo, hi, lab in ((0.5, 0.5, '0.5'), (1, 1, '1'), (1.5, 1.5, '1.5'), (2, 2.5, '2-2.5'), (3, 99, '3+')):
        G = [r for r in R if lo <= r['gap'] <= hi]
        rep(f'  gap {lab}: outlier (2+ others on Pinnacle\'s number)', dd([r for r in G if r['agree'] >= 2]), f'{mk}|{lab}|outlier')
        rep(f'  gap {lab}: others split / Pinnacle odd', dd([r for r in G if r['agree'] < 2]), f'{mk}|{lab}|not')
    for lab, f in (('1+', lambda r: r['gap'] >= 1), ('1.5+', lambda r: r['gap'] >= 1.5)):
        O = [r for r in R if f(r) and r['agree'] >= 2]
        rep(f'  gap {lab} outlier', dd(O), f'{mk}|{lab}|outlier all')
        rep(f'    ... 4+ others on Pinnacle\'s number', dd([r for r in O if r['agree'] >= 4]), f'{mk}|{lab}|outlier 4+')
        rep(f'    ... Pinnacle just moved to its number (book lagging)', dd([r for r in O if r['lag']]), f'{mk}|{lab}|lagging')
        rep(f'    ... no Pinnacle move', dd([r for r in O if not r['moved']]), f'{mk}|{lab}|no move')
        for s_ in (('home', 'away') if mk == 'spread' else ('over', 'under')): rep(f'    ... {s_}', dd([r for r in O if r['side'] == s_]), f'{mk}|{lab}|{s_}')
        rep(f'    ... inside 1 hour', dd([r for r in O if r['h'] <= 1]), f'{mk}|{lab}|1h')
        if mk == 'spread': rep(f'    ... NFL gap crossing 3 or 7', dd([r for r in O if r['crosses']]), f'{mk}|{lab}|key')
        for bk in sorted({r['book'] for r in O}): rep(f'    ... at {bk}', dd([r for r in O if r['book'] == bk]), f'{mk}|{lab}|{bk}')
if len(sys.argv) > 4: json.dump(OUT, open(sys.argv[4], 'w'), indent=1)
