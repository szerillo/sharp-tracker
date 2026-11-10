#!/usr/bin/env python3
"""Odds history database (Sean, 11/5: "build a database with it that can be referenced here"). Rebuilt from the stored Odds API pulls in
seconds, so the compact files in the repo are the only thing that has to be kept:

  data/oddsapi/compact/<plan>.jsonl.gz      bulk backfill (oddsapi_bulk.py), one line per game per snapshot, every book
  data/oddsapi/<sport>/*.json.gz            the first raw pulls (oddsapi_hist.py, this season) and data/oddsapi/tennis|mma (oddsapi_tennis.py, 2026)

Tables (data/oddsapi/odds.sqlite, gitignored):
  quotes(sport, key, game_id, t, book, ml_home, ml_away, ml_draw, sp_line, sp_home, sp_away, tot_line, tot_over, tot_under)   decimal odds
  games(game_id, sport, key, start, home, away, n_snaps, open_t, close_t, close_h,       close = last snapshot before the start
        pin_open_home, pin_close_home, pin_close_away, pin_close_draw (no-vig), pin_open_sp, pin_close_sp, pin_open_tot, pin_close_tot,
        best_home, best_home_book, best_away, best_away_book (best US decimal at the close))
  results(game_id, home_score, away_score, winner)          filled by sharp/odds_db.py --results (team sports from hist_schedule.json)
Usage: python3 sharp/odds_db.py   |   sqlite3 data/oddsapi/odds.sqlite "select ..." """
import os, sys, json, gzip, glob, sqlite3, collections, datetime as dt, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
OA = os.path.join(ROOT, 'data', 'oddsapi'); DB = os.path.join(OA, 'odds.sqlite')
US = ('draftkings', 'fanduel', 'williamhill_us', 'betmgm', 'betrivers', 'espnbet', 'fanatics')
SPORT_OF_PLAN = {'soccer': 'soccer', 'soccer2': 'soccer', 'soccer3': 'soccer', 'cups': 'soccer', 'futures': None}


def raw_rows():
    """The first raw pulls, converted to the compact shape."""
    from loggers.oddsapi_bulk import compact
    for f in sorted(glob.glob(os.path.join(OA, '*', '*.json.gz')) + glob.glob(os.path.join(OA, '*', '*', '*.json.gz'))):
        if '/compact/' in f or '/props/' in f: continue
        parts = os.path.relpath(f, OA).split(os.sep); sport = parts[0]; key = parts[1] if len(parts) == 3 else sport
        try: d = json.load(gzip.open(f, 'rt'))
        except Exception: continue
        if not isinstance(d, dict) or not d.get('timestamp'): continue
        for r in compact(sport, key, d): yield r


def compact_rows(plans=None):
    for f in sorted(glob.glob(os.path.join(OA, 'compact', '*.jsonl.gz'))):
        plan = os.path.basename(f).split('.')[0]
        if plan == 'futures' or (plans and plan not in plans): continue
        try:
            with gzip.open(f, 'rt') as fh:
                for l in fh:
                    try: r = json.loads(l)
                    except Exception: continue
                    r['sport'] = SPORT_OF_PLAN.get(plan, plan.rstrip('0123456789')); yield r
        except (EOFError, OSError): pass       # a file still being written: the complete lines are in


def nv(a, b, c=None):
    if not a or not b: return None
    q = [1 / a, 1 / b] + ([1 / c] if c else []); s = sum(q)
    return [x / s for x in q]


def flip(B):
    out = {}
    for bk, e in B.items():
        f = {}
        if e.get('h2h'): h = e['h2h']; f['h2h'] = [h[1], h[0]] + h[2:]
        if e.get('sp'): sp = e['sp']; f['sp'] = [-sp[0] if sp[0] is not None else None, sp[2], sp[1]]
        if e.get('tot'): f['tot'] = e['tot']
        out[bk] = f
    return out


def build(plans=None, since=None):
    """Streaming: one pass over the compact files, quotes inserted as they come (unique on game, time, book), and per game only the first and
    last pre-start snapshot kept in memory (the 11/5 full backfill is ~2 GB of snapshots; the old all-in-memory build was OOM-killed)."""
    t0 = time.time()
    sys.path.insert(0, os.path.join(ROOT, 'loggers'))
    inc = plans is not None          # 11/6: --add PLAN[,PLAN] --since DATE appends new games to the existing database (a full rebuild needs ~4 GB free)
    if os.path.exists(DB) and not inc: os.remove(DB)
    conn = sqlite3.connect(DB)
    have = {r[0] for r in conn.execute("SELECT game_id FROM games")} if inc else set()
    if not inc: conn.executescript("""
      PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
      CREATE TABLE quotes(sport TEXT, key TEXT, game_id TEXT, t TEXT, book TEXT, ml_home REAL, ml_away REAL, ml_draw REAL, sp_line REAL, sp_home REAL, sp_away REAL, tot_line REAL, tot_over REAL, tot_under REAL);
      CREATE UNIQUE INDEX q_uni ON quotes(game_id, t, book);
      CREATE TABLE games(game_id TEXT PRIMARY KEY, sport TEXT, key TEXT, start TEXT, home TEXT, away TEXT, n_snaps INT, open_t TEXT, close_t TEXT, close_h REAL,
        pin_open_home REAL, pin_close_home REAL, pin_close_away REAL, pin_close_draw REAL, pin_open_sp REAL, pin_close_sp REAL, pin_open_tot REAL, pin_close_tot REAL,
        best_home REAL, best_home_book TEXT, best_away REAL, best_away_book TEXT, mkt_open_sp REAL, mkt_open_tot REAL, mkt_open_t TEXT);
      CREATE TABLE results(game_id TEXT PRIMARY KEY, home_score REAL, away_score REAL, winner TEXT, src TEXT, ot INT, conf INT, neutral INT, home_ab TEXT, away_ab TEXT, espn_id TEXT);""")
    G = {}; Q = []; n = 0
    import itertools
    def keep(b):          # the part of a snapshot the games table needs
        return {k: v for k, v in b.items() if k == 'pinnacle' or k in US}
    for r in (compact_rows(plans) if inc else itertools.chain(compact_rows(), raw_rows())):
        t = r['t']
        if not t: continue
        if inc and (r['id'] in have or (since and r['start'] < since)): continue
        n += 1
        g = G.get(r['id'])
        if g is None: g = G[r['id']] = dict(sport=r['sport'], key=r.get('key'), start=r['start'], home=r['home'], away=r['away'], n=0, ot=None, ob=None, ct=None, cb=None)
        elif r['home'] != g['home']:
            # the Odds API sometimes swaps home/away between snapshots of the same event (MMA, Amosov-Magny 12/2025): orient every snapshot to
            # the first one seen so the quotes and the games row agree
            if r['home'] == g['away']: r['books'] = flip(r['books'])
            else: continue
        if t < g['start']:
            g['n'] += 1
            if g['ot'] is None or t < g['ot']: g['ot'], g['ob'] = t, keep(r['books'])
            if g['ct'] is None or t > g['ct']: g['ct'], g['cb'] = t, keep(r['books'])
            # Pinnacle's first posted number per market (its totals and spreads often appear after the first snapshot: NBA totals are in
            # only 15% of first snapshots), so the "open" for each market is the earliest snapshot that has it
            pb = r['books'].get('pinnacle') or {}
            for mk in ('h2h', 'sp', 'tot'):
                if pb.get(mk) and (g.get('o_' + mk) is None or t < g['o_' + mk][0]): g['o_' + mk] = (t, pb[mk])
            # market open (11/5, Bet Labs reconciliation): the first snapshot where 2+ books have the number; Pinnacle posts NBA / CBB totals
            # ~6h after DraftKings / FanDuel, so its first number is not the opener Bet Labs measures moves from. Median line across books.
            for mk in ('sp', 'tot'):
                ls = sorted(e[mk][0] for e in r['books'].values() if e.get(mk) and e[mk][0] is not None)
                if len(ls) >= 2 and (g.get('m_' + mk) is None or t < g['m_' + mk][0]): g['m_' + mk] = (t, ls[len(ls) // 2])
        for bk, e in r['books'].items():
            ml = e.get('h2h') or [None, None]; sp = e.get('sp') or [None, None, None]; tt = e.get('tot') or [None, None, None]
            Q.append((r['sport'], r.get('key'), r['id'], t, bk, ml[0], ml[1], ml[2] if len(ml) > 2 else None, sp[0], sp[1], sp[2], tt[0], tt[1], tt[2]))
        if len(Q) > 200000: conn.executemany("INSERT OR IGNORE INTO quotes VALUES (" + ','.join('?' * 14) + ")", Q); Q = []; conn.commit()
    if Q: conn.executemany("INSERT OR IGNORE INTO quotes VALUES (" + ','.join('?' * 14) + ")", Q)
    rows = []
    for gid, g in G.items():
        if g['ot'] is None: continue
        st = dt.datetime.fromisoformat(g['start'].replace('Z', '+00:00'))
        ot, ob, ct, cb = g['ot'], g['ob'], g['ct'], g['cb']
        def pin(b, f):
            return (b.get('pinnacle') or {}).get(f)
        po, pc = (g.get('o_h2h') or (None, None))[1], pin(cb, 'h2h')
        nvo = nv(*(po or [None, None])[:3]) if po else None; nvc = nv(*(pc or [None, None])[:3]) if pc else None
        best = {}
        for bk in US:
            e = (cb.get(bk) or {}).get('h2h')
            if not e: continue
            for i, s in ((0, 'home'), (1, 'away')):
                if e[i] and (s not in best or e[i] > best[s][0]): best[s] = (e[i], bk)
        sp_o, sp_c = (g.get('o_sp') or (None, None))[1], pin(cb, 'sp'); to_o, to_c = (g.get('o_tot') or (None, None))[1], pin(cb, 'tot')
        rows.append((gid, g['sport'], g['key'], g['start'], g['home'], g['away'], g['n'], ot, ct, round((st - dt.datetime.fromisoformat(ct.replace('Z', '+00:00'))).total_seconds() / 3600, 2),
                     nvo[0] if nvo else None, nvc[0] if nvc else None, nvc[1] if nvc else None, nvc[2] if nvc and len(nvc) > 2 else None,
                     sp_o[0] if sp_o else None, sp_c[0] if sp_c else None, to_o[0] if to_o else None, to_c[0] if to_c else None,
                     *(best.get('home') or (None, None)), *(best.get('away') or (None, None)),
                     (g.get('m_sp') or (None, None))[1], (g.get('m_tot') or (None, None))[1], (g.get('m_tot') or g.get('m_sp') or (None, None))[0]))
    conn.executemany("INSERT OR REPLACE INTO games VALUES (" + ','.join('?' * 25) + ")", rows)
    conn.execute("CREATE INDEX IF NOT EXISTS q_game ON quotes(game_id, t)"); conn.execute("CREATE INDEX IF NOT EXISTS g_sport ON games(sport, start)")
    conn.commit()
    print(f"[odds_db] {n} snapshot rows, {len(rows)} games, by sport: {dict(collections.Counter(r[1] for r in rows))} in {time.time() - t0:.0f}s", flush=True)
    results(conn)
    conn.close()


SOCCER_KEYS = {'soccer_epl': 'epl', 'soccer_spain_la_liga': 'laliga', 'soccer_germany_bundesliga': 'bundesliga', 'soccer_italy_serie_a': 'seriea', 'soccer_france_ligue_one': 'ligue1',
               'soccer_usa_mls': 'mls', 'soccer_uefa_champs_league': 'ucl', 'soccer_mexico_ligamx': 'ligamx'}


def results(conn):
    """Team sports from data/state/hist_schedule.json (ESPN), matched by date and team names (data/state/espn_teams.json); soccer leagues by
    Odds API key; MMA by the two fighters' names (hist_schedule has one row per fight)."""
    import sharp.oddsapi_edge as E
    H = json.load(open(os.path.join(ROOT, 'data', 'state', 'hist_schedule.json')))
    teams = json.load(open(os.path.join(ROOT, 'data', 'state', 'espn_teams.json'))) if os.path.exists(os.path.join(ROOT, 'data', 'state', 'espn_teams.json')) else {}
    out = []
    jobs = [(sp, sp, "SELECT game_id, home, away, start FROM games WHERE sport=?", (sp,)) for sp in ('nba', 'nhl', 'nfl', 'cfb', 'cbb', 'mlb', 'wnba', 'wncaab')]
    jobs += [(hk, hk, "SELECT game_id, home, away, start FROM games WHERE key=?", (ok,)) for ok, hk in SOCCER_KEYS.items()]
    for sport, hkey, sql, arg in jobs:
        T = teams.get(sport, {}); alt = {}
        for ab, t in T.items():
            for k in (t.get('name'), (t.get('loc') or '') + ' ' + (t.get('nick') or ''), t.get('short')):
                if k: alt[E.norm(k)] = ab
        def ab(name):
            n = E.norm(name)
            if n in alt: return alt[n]
            best = None
            for k, v in alt.items():
                if len(k) >= 6 and (k in n or n in k) and (best is None or len(k) > len(best[0])): best = (k, v)
            return best[1] if best else None
        idx = collections.defaultdict(list)
        for eid, h in (H.get(hkey) or {}).items():
            if h.get('hs') is None: continue
            idx[(h['home'], h['away'])].append(dict(h, eid=eid))
        k0 = len(out)
        for gid, home, away, start in conn.execute(sql, arg):
            ha, aa = ab(home), ab(away)
            if not ha or not aa: continue
            st = dt.datetime.fromisoformat(start.replace('Z', '+00:00'))
            for h in idx.get((ha, aa), []):
                if abs((dt.datetime.fromisoformat(h['start'].replace('Z', '+00:00')) - st).total_seconds()) < 6 * 3600:
                    out.append((gid, h['hs'], h['as_'], 'home' if h['hs'] > h['as_'] else 'away' if h['as_'] > h['hs'] else 'draw', 'espn',
                                1 if h.get('ot') else 0, None if h.get('conf') is None else int(bool(h['conf'])), 1 if h.get('neutral') else 0, ha, aa, h.get('eid'))); break
        print(f"[odds_db] results {hkey}: {len(out) - k0}", flush=True)
    # MMA: fighter names, fight within 2 days
    idx = collections.defaultdict(list)
    for h in (H.get('mma') or {}).values():
        if not h.get('winner') or not h.get('p1') or not h.get('p2'): continue
        idx[frozenset((E.norm(h['p1']), E.norm(h['p2'])))].append(h)
    k0 = len(out)
    for gid, home, away, start in conn.execute("SELECT game_id, home, away, start FROM games WHERE sport='mma'"):
        st = dt.datetime.fromisoformat(start.replace('Z', '+00:00'))
        for h in idx.get(frozenset((E.norm(home), E.norm(away))), []):
            if abs((dt.datetime.fromisoformat(h['start'].replace('Z', '+00:00')) - st).total_seconds()) < 48 * 3600:
                w = E.norm(h['winner']); nh, na = E.norm(home), E.norm(away)
                side = 'home' if w == nh else 'away' if w == na else ('home' if (w in nh or nh in w) and not (w in na or na in w) else 'away' if (w in na or na in w) else None)
                if side: out.append((gid, 1.0 if side == 'home' else 0.0, 1.0 if side == 'away' else 0.0, side, 'espn', 0, None, 0, None, None, None))
                break
    print(f"[odds_db] results mma: {len(out) - k0}", flush=True)
    conn.executemany("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?,?,?,?,?,?)", out); conn.commit()
    print(f"[odds_db] results joined: {len(out)}")


if __name__ == '__main__':
    if '--results' in sys.argv:
        c = sqlite3.connect(DB)
        cols = [r[1] for r in c.execute("PRAGMA table_info(results)")]
        for col in ('ot', 'conf', 'neutral', 'home_ab', 'away_ab', 'espn_id'):
            if col not in cols: c.execute(f"ALTER TABLE results ADD COLUMN {col} {'TEXT' if col.endswith(('_ab', '_id')) else 'INT'}")
        results(c); c.close()
    elif '--add' in sys.argv:
        build(plans=sys.argv[sys.argv.index('--add') + 1].split(','), since=sys.argv[sys.argv.index('--since') + 1] if '--since' in sys.argv else None)
    else: build()
