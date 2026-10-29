#!/usr/bin/env python3
"""Build data/sharp/dashboard.json for sharp_dashboard.html.

Sections: board (upcoming games: every market x side with the prior-weighted fair, the venue ladder and the best bettable price),
props (same, per player x stat x line), venues (Tests A-D, gated), ledger (fills), health (log cadence per venue per day), constants.
"""
import os, sys, json, sqlite3, datetime as dt, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from sharp import constants as C, norm as N, fair as F, tests as T
from sharp import sports as SP

ROOT = os.path.abspath(os.path.join(HERE, '..')); SD = os.path.join(ROOT, 'data', 'state'); DB = os.path.join(SD, 'sharp.sqlite')
NOW = dt.datetime.now(dt.timezone.utc); NOW_S = N.iso(NOW)
GAME_ORDER = ['ml', 'rl', 'total', 'tt_away', 'tt_home', 'f5_ml', 'f5_rl', 'f5_total', 'f5_tt_away', 'f5_tt_home', 'rfi']
ORDER_SPORT = {'mlb': GAME_ORDER}
for _sp, _cfg in SP.SPORTS.items():
    ORDER_SPORT[_sp] = [pre + m for pre in [''] + [SP.PERIODS[p] for p in _cfg['periods'] if p != 'full'] for m in ('ml', 'spread', 'total', 'tt_away', 'tt_home')]
BOARD_HOURS = {'mlb': 40, 'nba': 40, 'nhl': 40, 'nfl': 8 * 24, 'cfb': 8 * 24}   # how far ahead the board shows games (NFL/CFB lines are up all week)
KEY_SPREAD = {'mlb': 1.5, 'nfl': 3, 'cfb': 3, 'nba': 3, 'nhl': 1.5}
MIN_VENUES_FOR_EDGE = {'game': 3, 'prop': 2}   # fair shown only when at least this many ruler venues quote the cell (Fable 10/14; props 2 on 10/29: Kalshi+Novig+Pinnacle are the prop venues)


def r4(x): return None if x is None else round(x, 4)


def cell(eq, market, line, side, part, ts):
    fr = eq.fair(market, line, side, ts, part)
    ladder = []
    for v, d in sorted(fr['detail'].items(), key=lambda kv: (kv[1]['p'] is None, -(kv[1]['p'] or 0))):
        q = eq.latest(v, market, line, side, ts, 90, part)
        ladder.append(dict(venue=v, p=r4(d['p']), why=d['why'] if d['p'] is None else None, w=round(fr['weights'].get(v, 0), 3),
                           american=q[10] if q else None, bid=r4(q[6]) if q else None, ask=r4(q[7]) if q else None, limit=q[11] if q else None,
                           age_min=round((N.parse_ts(ts) - N.parse_ts(q[0])).total_seconds() / 60) if q else None,
                           flags=q[9] if q else None))
    best = F.best_price(eq, market, line, side, ts, part)
    for b in best:
        for k in ('implied', 'cost', 'bid', 'ask'): b[k] = r4(b[k])
    fair = fr['fair'] if fr['n'] >= MIN_VENUES_FOR_EDGE['prop' if market.startswith('prop_') else 'game'] else None
    edge = (fair - best[0]['cost']) if (fair is not None and best) else None
    # reference quotes: AN consensus public %, AN open
    cons = eq.latest('AN_Consensus', market, line, side, ts, 10 ** 6, part); opn = eq.latest('AN_Open', market, line, side, ts, 10 ** 6, part)
    return dict(market=market, line=line, side=side, participant=part, player=eq.names.get(part) if part else None,
                fair=r4(fair), fair_n=fr['n'], fair_status=fr['status'], fair_american=N.prob_to_american(fair) if fair else None,
                best=best[:4], edge_pts=(round(100 * edge, 2) if edge is not None else None), ladder=ladder,
                open_american=opn[10] if opn else None, open_p=r4(N.implied_from_american(opn[10])) if opn else None, public=None)


def public_pct(conn, ev, market, side):
    r = conn.execute("SELECT extra FROM ticks WHERE event_id=? AND venue='AN_Consensus' AND market=? AND side=? AND extra IS NOT NULL ORDER BY ts_utc DESC LIMIT 1",
                     (ev, market, side)).fetchone()
    return json.loads(r[0]) if r else None


def main_line(eq, market, part=None):
    """The 'main' line for a totals-type market: the line with the most venues, ties to the one nearest 50%."""
    cands = [(k[1], len(v)) for k, v in eq.keys.items() if k[0] == market and k[2] == part and k[1] is not None]
    if not cands: return []
    mx = max(n for _, n in cands)
    return sorted({l for l, n in cands if n == mx})


def board(conn, sport='mlb'):
    out = []; order = ORDER_SPORT[sport]; mclass = N.MARKET_CLASS if sport == 'mlb' else SP.market_class
    for ev, et_date, start, away, home, status in conn.execute("SELECT event_id, et_date, start_utc, away, home, status FROM events WHERE sport=? ORDER BY start_utc", (sport,)).fetchall():
        st = N.parse_ts(start)
        if st < NOW - dt.timedelta(hours=1) or st > NOW + dt.timedelta(hours=BOARD_HOURS[sport]): continue
        eq = F.EventQuotes(conn, ev); ts = NOW_S
        last_tick = max((L[-1][0] for L in eq.idx.values()), default=None)
        if last_tick and (NOW - N.parse_ts(last_tick)).total_seconds() > C.STALE_BOOK_MIN['value'] * 60:
            ts = last_tick   # the log is stale (job not running): price the board at the last observation and say so
        g = dict(event_id=ev, et_date=et_date, start_utc=start, away=away, home=home, status=status, priced_at=ts,
                 stale_min=round((NOW - N.parse_ts(ts)).total_seconds() / 60), minutes_to_start=round((st - N.parse_ts(ts)).total_seconds() / 60), markets=[])
        for m in order:
            if m.endswith('ml'):
                for side, part in (('away', away), ('home', home)):
                    c = cell(eq, m, None, side, part, ts)
                    if c['ladder']: c['public'] = public_pct(conn, ev, m, side); g['markets'].append(c)
            elif m.endswith('rl') or m.endswith('spread'):
                keyline = (1.5 if m == 'rl' else 0.5) if sport == 'mlb' else KEY_SPREAD[sport]
                nv = {k[1]: len(v) for k, v in eq.keys.items() if k[0] == m and k[1] is not None and k[2] == home}   # home-side lines -> venues quoting
                lines = sorted(nv, key=lambda l: (-nv[l], abs(abs(l) - keyline)))   # the most-quoted line first (the market's main number), then nearest the key
                for line in lines[:2]:
                    for side, part in (('away', away), ('home', home)):
                        c = cell(eq, m, line if side == 'home' else -line, side, part, ts)
                        if c['ladder']: c['public'] = public_pct(conn, ev, m, side); g['markets'].append(c)
            else:
                part = home if m.endswith('home') else (away if m.endswith('away') else None)
                for line in main_line(eq, m, part)[:1] if m != 'rfi' else [0.5]:
                    for side in ('over', 'under'):
                        c = cell(eq, m, line, side, part, ts)
                        if c['ladder']: c['public'] = public_pct(conn, ev, m, side) if m in ('total',) else None; g['markets'].append(c)
        # Pinnacle limit growth (first post vs now) per market
        g['pinnacle_limits'] = {}
        for (v, m, l, s, p), L in eq.idx.items():
            if v == 'Pinnacle' and mclass(m) == 'game' and L[0][11]:
                g['pinnacle_limits'][m] = dict(first=L[0][11], now=L[-1][11], first_ts=L[0][0])
        # props: every player x stat x line with 2+ venues; keep the main line per player-stat (most venues)
        props = []
        groups = collections.defaultdict(list)
        for (m, l, p), vs in eq.keys.items():
            if m.startswith('prop_') and p: groups[(m, p)].append((l, len(vs)))
        for (m, p), ls in groups.items():
            ls.sort(key=lambda x: (-x[1], x[0]))
            for l, nv in ls[:2]:
                if nv < 2: continue
                for side in ('over', 'under'):
                    c = cell(eq, m, l, side, p, ts)
                    if c['ladder']: c['stat'] = m[5:]; props.append(c)
        props.sort(key=lambda c: -(c['edge_pts'] if c['edge_pts'] is not None else -99))
        g['props'] = props
        out.append(g)
    return out


def health(conn):
    rows = [dict(zip(('et_date', 'venue', 'mclass', 'n_ticks', 'n_events', 'first_ts', 'last_ts'), r)) for r in conn.execute("SELECT * FROM log_health ORDER BY 1,2,3")]
    # snapshots per game per venue (how many distinct observation times) -> the cadence check
    cad = [dict(venue=r[0], mclass=r[1], games=r[2], snaps_per_game=round(r[3], 1)) for r in conn.execute("""
        SELECT venue, mclass, COUNT(DISTINCT event_id), AVG(n) FROM (
          SELECT venue, mclass, event_id, COUNT(DISTINCT substr(ts_utc,1,16)) n FROM ticks GROUP BY 1,2,3) GROUP BY 1,2""")]
    unmatched = {}
    return dict(by_day=rows, cadence=cad, feed_lag={v: c['value'] for v, c in C.FEED_LAG_S.items()},
                note="expected ~40 snapshots per game-day at the 20-minute job cadence (10 AM to midnight ET); far fewer means the job is not landing")


def ledger(conn):
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM fills ORDER BY ts_utc DESC")]
    for r in rows:
        r['clv_fill_pts'] = round(100 * (r['fair_at_fill'] - r['implied']), 2) if r.get('fair_at_fill') is not None and not r['late'] else None
        r['clv_close_pts'] = round(100 * (r['fair_at_close'] - r['implied']), 2) if r.get('fair_at_close') is not None and not r['late'] else None
        try: r['fair_at_fill_detail'] = json.loads(r['fair_at_fill_detail'] or 'null')
        except Exception: pass
    graded = [r for r in rows if r.get('result') in ('W', 'L', 'P')]
    summ = collections.defaultdict(lambda: dict(n=0, units=0.0, pnl=0.0, clv=[], w=0, l=0, p=0))
    for r in graded:
        for key in (('all', 'all'), ('venue', r['venue']), ('market', r['market']), ('side', r['side']), ('tag', r['rule_tag']), ('mclass', r['mclass'])):
            s = summ[f"{key[0]}:{key[1]}"]; s['n'] += 1; s['units'] += r['stake']; s['pnl'] += r['pnl_units'] or 0
            s[{'W': 'w', 'L': 'l', 'P': 'p'}[r['result']]] += 1
            if r['clv_close_pts'] is not None: s['clv'].append(r['clv_close_pts'])
    for s in summ.values():
        s['clv_avg'] = round(sum(s['clv']) / len(s['clv']), 2) if s['clv'] else None; s['n_clv'] = len(s['clv']); del s['clv']
        s['pnl'] = round(s['pnl'], 3); s['roi'] = round(100 * s['pnl'] / s['units'], 1) if s['units'] else None
    conn.row_factory = None
    return dict(fills=rows, summary=dict(summ))


def strip(x):   # drop null fields to keep the committed files small
    if isinstance(x, dict): return {k: strip(v) for k, v in x.items() if v is not None}
    if isinstance(x, list): return [strip(v) for v in x]
    return x


def main():
    conn = sqlite3.connect(DB)
    tests = T.run_all(preview=False)
    wf = json.load(open(F.WEIGHTS_FILE)) if os.path.exists(F.WEIGHTS_FILE) else {}
    ledg = ledger(conn); hlth = health(conn); consts = C.dump()
    sysv = json.load(open(os.path.join(SD, 'system_fires.json'))) if os.path.exists(os.path.join(SD, 'system_fires.json')) else None
    sports = [r[0] for r in conn.execute("SELECT DISTINCT sport FROM events")] or ['mlb']
    index = dict(built=NOW_S, sports=[], spec='SHARP_TRACKER_BUILD_SPEC_2026-10-14.md')
    for sp in sorted(sports, key=lambda s: ['nfl', 'nba', 'nhl', 'cfb', 'mlb'].index(s) if s in ('nfl', 'nba', 'nhl', 'cfb', 'mlb') else 9):
        nev = conn.execute("SELECT COUNT(*) FROM events WHERE sport=?", (sp,)).fetchone()[0]
        nset = conn.execute("SELECT COUNT(*) FROM results r JOIN events e ON e.event_id=r.event_id WHERE r.status='final' AND e.sport=?", (sp,)).fetchone()[0]
        nt = conn.execute("SELECT COUNT(*) FROM ticks WHERE sport=?", (sp,)).fetchone()[0]
        out = dict(built=NOW_S, sport=sp, label=SP.SPORTS[sp]['label'] if sp in SP.SPORTS else 'MLB',
                   counts=dict(events=nev, settled=nset, ticks=nt,
                               prop_rows_settled=conn.execute("SELECT COUNT(*) FROM closes c JOIN events e ON e.event_id=c.event_id WHERE c.mclass='prop' AND c.outcome IS NOT NULL AND e.sport=?", (sp,)).fetchone()[0]),
                   weights=dict(game=F.weights_for(sp, 'game')[0], game_status=F.weights_for(sp, 'game')[1],
                                prop=F.weights_for(sp, 'prop')[0], prop_status=F.weights_for(sp, 'prop')[1], fit_file=wf),
                   board=board(conn, sp), venues=tests, ledger=ledg, health=hlth, constants=consts, systems=(sysv if sp == 'nfl' else None),
                   spec='SHARP_TRACKER_BUILD_SPEC_2026-10-14.md')
        fn = os.path.join(SD, f'dashboard_{sp}.json'); json.dump(strip(out), open(fn, 'w'), default=str, separators=(',', ':'))
        index['sports'].append(dict(sport=sp, label=out['label'], file=f'data/state/dashboard_{sp}.json', games=len(out['board']), ticks=nt, events=nev, settled=nset))
        print(f"[export] {fn.split('/')[-1]}: {len(out['board'])} games on the board, {sum(len(g['props']) for g in out['board'])} prop cells, {os.path.getsize(fn) // 1024} KB")
    # cross-sport edge list: every priced cell (game + prop) in one small file, best-first, for the Edges screen
    edges = []
    for spx in index['sports']:
        d = json.load(open(os.path.join(SD, f"dashboard_{spx['sport']}.json")))
        for gm in d['board']:
            for c in gm['markets'] + gm.get('props', []):
                if c.get('fair') is None or not c.get('best'): continue
                b = c['best'][0]; b2 = c['best'][1] if len(c['best']) > 1 else None
                lad = {l['venue']: l.get('p') for l in c.get('ladder', []) if l.get('p') is not None}
                edges.append(dict(sport=spx['sport'], event_id=gm['event_id'], game=f"{gm['away']}@{gm['home']}", start_utc=gm['start_utc'], ttk_h=round(gm['minutes_to_start'] / 60, 1),
                                  stale_min=gm['stale_min'], market=c['market'], mclass='prop' if c['market'].startswith('prop_') else 'game', side=c['side'], line=c.get('line'),
                                  participant=c.get('participant'), player=c.get('player'), stat=c.get('stat'), fair=c['fair'], fair_n=c['fair_n'], fair_status=c.get('fair_status'),
                                  venue=b['venue'], price=b.get('cost_american') or b.get('american'), cost=b['cost'], limit=b.get('limit'), flags=b.get('flags'),
                                  venue2=b2 and b2['venue'], price2=b2 and (b2.get('cost_american') or b2.get('american')), edge_pts=c['edge_pts'], ladder=lad,
                                  public=c.get('public'), open_american=c.get('open_american')))
    edges.sort(key=lambda e: -(e['edge_pts'] if e['edge_pts'] is not None else -99))
    json.dump(strip(dict(built=NOW_S, n=len(edges), edges=edges)), open(os.path.join(SD, 'edges.json'), 'w'), default=str, separators=(',', ':'))
    print(f"[export] edges.json: {len(edges)} priced cells across {len(index['sports'])} sports, {os.path.getsize(os.path.join(SD, 'edges.json')) // 1024} KB; top: "
          + ', '.join(f"{e['sport']} {e['game']} {e['market']} {e['side']} {e['edge_pts']:+.1f}" for e in edges[:3]))
    # dashboard.json stays the first sport's full file (back-compat for the page) with the index attached
    first = json.load(open(os.path.join(SD, f"dashboard_{index['sports'][0]['sport']}.json"))); first['index'] = index
    json.dump(first, open(os.path.join(SD, 'dashboard.json'), 'w'), default=str, separators=(',', ':'))
    conn.close()


if __name__ == '__main__':
    main()
