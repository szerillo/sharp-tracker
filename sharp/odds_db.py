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
        if not d.get('timestamp'): continue
        for r in compact(sport, key, d): yield r


def compact_rows():
    for f in sorted(glob.glob(os.path.join(OA, 'compact', '*.jsonl.gz'))):
        plan = os.path.basename(f).split('.')[0]
        if plan == 'futures': continue
        try:
            with gzip.open(f, 'rt') as fh:
                for l in fh:
                    try: r = json.loads(l)
                    except Exception: continue
                    r['sport'] = SPORT_OF_PLAN.get(plan, plan); yield r
        except (EOFError, OSError): pass       # a file still being written: the complete lines are in


def nv(a, b, c=None):
    if not a or not b: return None
    q = [1 / a, 1 / b] + ([1 / c] if c else []); s = sum(q)
    return [x / s for x in q]


def build():
    """Streaming: one pass over the compact files, quotes inserted as they come (unique on game, time, book), and per game only the first and
    last pre-start snapshot kept in memory (the 11/5 full backfill is ~2 GB of snapshots; the old all-in-memory build was OOM-killed)."""
    t0 = time.time()
    sys.path.insert(0, os.path.join(ROOT, 'loggers'))
    if os.path.exists(DB): os.remove(DB)
    conn = sqlite3.connect(DB)
    conn.executescript("""
      PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
      CREATE TABLE quotes(sport TEXT, key TEXT, game_id TEXT, t TEXT, book TEXT, ml_home REAL, ml_away REAL, ml_draw REAL, sp_line REAL, sp_home REAL, sp_away REAL, tot_line REAL, tot_over REAL, tot_under REAL);
      CREATE UNIQUE INDEX q_uni ON quotes(game_id, t, book);
      CREATE TABLE games(game_id TEXT PRIMARY KEY, sport TEXT, key TEXT, start TEXT, home TEXT, away TEXT, n_snaps INT, open_t TEXT, close_t TEXT, close_h REAL,
        pin_open_home REAL, pin_close_home REAL, pin_close_away REAL, pin_close_draw REAL, pin_open_sp REAL, pin_close_sp REAL, pin_open_tot REAL, pin_close_tot REAL,
        best_home REAL, best_home_book TEXT, best_away REAL, best_away_book TEXT);
      CREATE TABLE results(game_id TEXT PRIMARY KEY, home_score REAL, away_score REAL, winner TEXT, src TEXT);""")
    G = {}; Q = []; n = 0
    import itertools
    def keep(b):          # the part of a snapshot the games table needs
        return {k: v for k, v in b.items() if k == 'pinnacle' or k in US}
    for r in itertools.chain(compact_rows(), raw_rows()):
        t = r['t']
        if not t: continue
        n += 1
        g = G.get(r['id'])
        if g is None: g = G[r['id']] = dict(sport=r['sport'], key=r.get('key'), start=r['start'], home=r['home'], away=r['away'], n=0, ot=None, ob=None, ct=None, cb=None)
        if t < g['start']:
            g['n'] += 1
            if g['ot'] is None or t < g['ot']: g['ot'], g['ob'] = t, keep(r['books'])
            if g['ct'] is None or t > g['ct']: g['ct'], g['cb'] = t, keep(r['books'])
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
        po, pc = pin(ob, 'h2h'), pin(cb, 'h2h')
        nvo = nv(*(po or [None, None])[:3]) if po else None; nvc = nv(*(pc or [None, None])[:3]) if pc else None
        best = {}
        for bk in US:
            e = (cb.get(bk) or {}).get('h2h')
            if not e: continue
            for i, s in ((0, 'home'), (1, 'away')):
                if e[i] and (s not in best or e[i] > best[s][0]): best[s] = (e[i], bk)
        sp_o, sp_c = pin(ob, 'sp'), pin(cb, 'sp'); to_o, to_c = pin(ob, 'tot'), pin(cb, 'tot')
        rows.append((gid, g['sport'], g['key'], g['start'], g['home'], g['away'], g['n'], ot, ct, round((st - dt.datetime.fromisoformat(ct.replace('Z', '+00:00'))).total_seconds() / 3600, 2),
                     nvo[0] if nvo else None, nvc[0] if nvc else None, nvc[1] if nvc else None, nvc[2] if nvc and len(nvc) > 2 else None,
                     sp_o[0] if sp_o else None, sp_c[0] if sp_c else None, to_o[0] if to_o else None, to_c[0] if to_c else None,
                     *(best.get('home') or (None, None)), *(best.get('away') or (None, None))))
    conn.executemany("INSERT OR REPLACE INTO games VALUES (" + ','.join('?' * 22) + ")", rows)
    conn.execute("CREATE INDEX q_game ON quotes(game_id, t)"); conn.execute("CREATE INDEX g_sport ON games(sport, start)")
    conn.commit()
    print(f"[odds_db] {n} snapshot rows, {len(rows)} games, by sport: {dict(collections.Counter(r[1] for r in rows))} in {time.time() - t0:.0f}s", flush=True)
    results(conn)
    conn.close()


def results(conn):
    """Team sports from data/state/hist_schedule.json (ESPN), matched by date and team names (data/state/espn_teams.json)."""
    import sharp.oddsapi_edge as E
    H = json.load(open(os.path.join(ROOT, 'data', 'state', 'hist_schedule.json')))
    teams = json.load(open(os.path.join(ROOT, 'data', 'state', 'espn_teams.json'))) if os.path.exists(os.path.join(ROOT, 'data', 'state', 'espn_teams.json')) else {}
    out = []
    for sport in ('nba', 'nhl', 'nfl', 'cfb', 'cbb', 'mlb', 'wnba'):
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
        for h in (H.get(sport) or {}).values():
            if h.get('hs') is None: continue
            idx[(h['home'], h['away'])].append(h)
        for gid, home, away, start in conn.execute("SELECT game_id, home, away, start FROM games WHERE sport=?", (sport,)):
            ha, aa = ab(home), ab(away)
            if not ha or not aa: continue
            st = dt.datetime.fromisoformat(start.replace('Z', '+00:00'))
            for h in idx.get((ha, aa), []):
                if abs((dt.datetime.fromisoformat(h['start'].replace('Z', '+00:00')) - st).total_seconds()) < 6 * 3600:
                    out.append((gid, h['hs'], h['as_'], 'home' if h['hs'] > h['as_'] else 'away' if h['as_'] > h['hs'] else 'draw', 'espn')); break
    conn.executemany("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)", out); conn.commit()
    print(f"[odds_db] results joined: {len(out)}")


if __name__ == '__main__':
    build()
