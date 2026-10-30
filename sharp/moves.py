#!/usr/bin/env python3
"""Move tape: who moved first, who followed, who is stuck, and what following was worth. Built from the 5-minute fast tape
(data/<sport>/ticks5: Pinnacle, Novig, Kalshi) plus the 20-minute soft-book tape (data/<sport>/ticks: DK, FD, Caesars, BetRivers,
Fanatics, theScore), Kalshi trades (data/kalshi/trades5), the Novig public trade tape when it is on disk (data/novig/tape, fetched by
novig_tape.py the day after) and graded closes (data/state/closes.jsonl.gz). Scope: docs/sharp_framework_v2_scope.md; tests and
gates: docs/move_tape_prereg_2026-10-30.md.

A move is a change of MOVE (2 cents of devigged probability) or more on the main line of a full-game ML, spread or total at a fast
venue between two of its consecutive observations before kickoff. Moves in the same direction on the same market inside CLUSTER_MIN
minutes are one move; the earliest venue is the origin. For every other venue: the minutes until it followed by FOLLOW (1 cent) in
the same direction, or stuck if it has not. Exchange flow: Kalshi trades (direction-signed dollars) and Novig fills (dollars, unsigned)
in the FLOW_MIN minutes around the origin. Grade: Pinnacle's last pre-kickoff probability on the main line (Novig when Pinnacle has
none) gives CLV in cents for (a) following at the origin venue right after the move and (b) betting each stuck soft book; the
result comes from the graded closes. Novig flow is cached (data/state/moves_novig_flow.json) because the tape is only on disk the
day it is fetched.

Outputs: data/state/moves.json (per sport: tiles, gated at GATE settled events; the newest TAPE_ROWS moves) and
data/state/moves.jsonl.gz (every move, for research). Runs in the tracker job after grade.py and novig_tape.py."""
import os, sys, json, gzip, glob, math, datetime as dt, collections
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp import sports as SP
SD = os.path.join(ROOT, 'data', 'state'); OUT = os.path.join(SD, 'moves.json'); FULL = os.path.join(SD, 'moves.jsonl.gz'); NCACHE = os.path.join(SD, 'moves_novig_flow.json')
FAST = ['Pinnacle', 'Novig', 'Kalshi']; SOFT = ['DK', 'FD', 'Caesars', 'BetRivers', 'Fanatics', 'theScore']
MOVE = 0.02; FOLLOW = 0.01; CLUSTER_MIN = 15; FLOW_MIN = 30; STUCK_MAX_AGE_MIN = 45
GATE = 150; TAPE_ROWS = 150; DAYS = 21
MARKETS = ('ml', 'spread', 'total')
NOW = pd.Timestamp.now(tz='UTC')


def read_jl(files, keep=None):
    rows = []
    for f in files:
        with gzip.open(f, 'rt') as fh:
            for l in fh:
                try: r = json.loads(l)
                except Exception: continue
                if keep is None or keep(r): rows.append(r)
    return rows


def recent(dirp):
    fs = sorted(glob.glob(os.path.join(dirp, '*.jsonl.gz')))
    cut = (NOW - pd.Timedelta(days=DAYS)).strftime('%Y-%m-%d')
    return [f for f in fs if os.path.basename(f)[:10] >= cut]


def prob(r):
    if r.get('bid') is not None and r.get('ask') is not None: return (r['bid'] + r['ask']) / 2
    a = r.get('american')
    if a is None: return None
    return 1 / (1 + a / 100) if a > 0 else 1 / (1 + 100 / -a)


def frame(rows, venues):
    """ticks -> one row per (event, venue, market, home_line, ts) with p = devigged probability of the home / over side."""
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows); df = df[df['venue'].isin(venues) & df['market'].isin(MARKETS)]
    if df.empty: return df
    if 'flags' in df: df = df[~df['flags'].astype(str).str.contains('threeway')]
    df['p_raw'] = [prob(r) for r in df.to_dict('records')]; df = df[df['p_raw'].notna()]
    df['line'] = pd.to_numeric(df.get('line'), errors='coerce').fillna(0.0)
    df['home_line'] = np.where((df['market'] == 'spread') & (df['side'] == 'away'), -df['line'], df['line'])
    df['ts'] = pd.to_datetime(df['ts'], utc=True, format='ISO8601')
    key = ['event_id', 'venue', 'market', 'home_line', 'ts']
    exch = df['venue'].isin(['Novig', 'Kalshi', 'Polymarket'])
    tot = df.groupby(key)['p_raw'].transform('sum'); n = df.groupby(key)['p_raw'].transform('count')
    df['p'] = np.where(exch, df['p_raw'], np.where(n == 2, df['p_raw'] / tot, np.nan))
    df = df[df['p'].notna() & df['side'].isin(['home', 'over'])].copy()
    if 'limit' not in df: df['limit'] = np.nan
    if 'extra' not in df: df['extra'] = None
    return df[['event_id', 'venue', 'market', 'home_line', 'ts', 'p', 'limit', 'extra']].drop_duplicates(key).sort_values('ts')


def load_sport(sport):
    sd = os.path.join(ROOT, 'data', sport)
    sched = json.load(open(os.path.join(sd, 'schedule.json'))) if os.path.exists(os.path.join(sd, 'schedule.json')) else {}
    fdir = 'ticks' if os.environ.get('MOVES_TEST_20MIN') else 'ticks5'
    fast = frame(read_jl(recent(os.path.join(sd, fdir)), keep=lambda r: r['venue'] in FAST and r['market'] in MARKETS), FAST)
    soft = frame(read_jl(recent(os.path.join(sd, 'ticks')), keep=lambda r: r['venue'] in SOFT and r['market'] in MARKETS), SOFT)
    return sched, fast, soft


def load_closes():
    p = os.path.join(SD, 'closes.jsonl.gz')
    if not os.path.exists(p): return {}
    out = {}
    for r in read_jl([p]):
        if r.get('outcome') is None or r['market'] not in MARKETS: continue
        out[(r['event_id'], r['market'], float(r['line'] or 0), r['side'])] = (r['outcome'], r.get('push'))
    return out


def load_kalshi_trades(sport):
    rows = read_jl(recent(os.path.join(ROOT, 'data', 'kalshi', 'trades5')), keep=lambda r: r.get('sport') == sport and r.get('market') in MARKETS)
    if not rows: return pd.DataFrame()
    t = pd.DataFrame(rows); t['ts'] = pd.to_datetime(t['ts'], utc=True, format='ISO8601')
    bought = np.where(t['taker_side'] == 'yes', t['yes_side'], t['yes_side'].map({'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}))
    t['dir'] = np.where(pd.Series(bought).isin(['home', 'over']), 1, -1)
    t['usd'] = t['count'] * np.where(t['taker_side'] == 'yes', t['yes_price'], 1 - t['yes_price'])
    t['home_line'] = np.where((t['market'] == 'spread') & (t['yes_side'] == 'away'), -t['line'].fillna(0), t['line'].fillna(0))
    return t


def novig_tape(days):
    fs = [os.path.join(ROOT, 'data', 'novig', 'tape', f'{d}.jsonl.gz') for d in days]
    fs = [f for f in fs if os.path.exists(f)]
    if not fs: return pd.DataFrame()
    rows = read_jl(fs)
    if not rows: return pd.DataFrame()
    t = pd.DataFrame(rows); t['ts'] = pd.to_datetime(t['ts'], utc=True, format='ISO8601'); t['usd'] = t['price'] * t['qty'] if 'qty' in t else 0
    return t


def detect(fast, soft, sched, closes, ktr, ntape, ncache, sport):
    moves = []
    if fast.empty: return moves
    main = fast[fast['venue'] == 'Pinnacle'].groupby(['event_id', 'market', 'home_line']).size().reset_index(name='n')
    if main.empty: main = fast.groupby(['event_id', 'market', 'home_line']).size().reset_index(name='n')
    main = main.sort_values('n', ascending=False).drop_duplicates(['event_id', 'market'])
    allv = pd.concat([fast, soft]) if not soft.empty else fast
    allv = allv.merge(main[['event_id', 'market', 'home_line']], on=['event_id', 'market', 'home_line'])
    for (ev, mkt, hl), g in allv.groupby(['event_id', 'market', 'home_line']):
        e = sched.get(ev)
        if not e: continue
        start = pd.Timestamp(e['start']); start = start.tz_localize('UTC') if start.tzinfo is None else start.tz_convert('UTC')
        g = g[g['ts'] < start]
        if g.empty: continue
        series = {v: x.sort_values('ts') for v, x in g.groupby('venue')}
        raw = []
        for v in FAST:
            s = series.get(v)
            if s is None or len(s) < 2: continue
            p = s['p'].values; ts = list(s['ts']); lim = s['limit'].values
            for i in range(1, len(p)):
                d = p[i] - p[i - 1]
                if abs(d) >= MOVE: raw.append(dict(venue=v, ts=ts[i], p0=float(p[i - 1]), p1=float(p[i]), dir=int(np.sign(d)), limit=(None if pd.isna(lim[i]) else float(lim[i]))))
        if not raw: continue
        raw.sort(key=lambda r: r['ts']); clusters = []
        for r in raw:
            c = next((c for c in clusters if c['dir'] == r['dir'] and (r['ts'] - c['ts']).total_seconds() <= CLUSTER_MIN * 60 and r['venue'] not in c['members']), None)
            if c: c['members'][r['venue']] = round((r['ts'] - c['ts']).total_seconds() / 60, 1)
            else: clusters.append(dict(**r, members={}))
        pin = series.get('Pinnacle'); nov = series.get('Novig')
        close_s = pin if pin is not None and len(pin) else nov
        close = float(close_s['p'].values[-1]) if close_s is not None and len(close_s) else None
        settled = (ev, mkt, float(hl), 'home' if mkt != 'total' else 'over') in closes
        started = NOW >= start
        for c in clusters:
            t0 = c['ts']; d = c['dir']
            # Pinnacle limit at the move
            lim = c['limit']
            if lim is None and pin is not None:
                pre = pin[pin['ts'] <= t0]
                if len(pre) and not pd.isna(pre['limit'].values[-1]): lim = float(pre['limit'].values[-1])
            # followers and stuck books
            fol = {}; stuck = {}; stuck_clv = []
            for v, s in series.items():
                if v == c['venue'] or v in c['members']: continue
                pre = s[s['ts'] <= t0]
                if not len(pre): fol[v] = None; continue
                p0 = float(pre['p'].values[-1]); post = s[s['ts'] > t0]
                hit = post[(post['p'] - p0) * d >= FOLLOW]
                if len(hit): fol[v] = round((hit['ts'].iloc[0] - t0).total_seconds() / 60, 1)
                else:
                    fol[v] = None
                    last = post if len(post) else pre; last_ts = last['ts'].iloc[-1]; age = (NOW - last_ts).total_seconds() / 60
                    if v in SOFT:
                        if not started and age <= STUCK_MAX_AGE_MIN: stuck[v] = round(float(last['p'].values[-1]), 4)
                        if close is not None and settled: stuck_clv.append(100 * (close - p0) * d)
            followed = [v for v in fol if fol[v] is not None]
            soft_seen = [v for v in fol if v in SOFT]; soft_fol = [v for v in soft_seen if fol[v] is not None]
            # exchange flow
            kflow = None
            if not ktr.empty:
                w = ktr[(ktr['event_id'] == ev) & (ktr['market'] == mkt) & (ktr['home_line'] == hl) & (ktr['ts'] >= t0 - pd.Timedelta(minutes=FLOW_MIN)) & (ktr['ts'] <= t0 + pd.Timedelta(minutes=FLOW_MIN))]
                if len(w): kflow = dict(usd=round(float(w['usd'].sum())), net=round(float((w['usd'] * w['dir'] * d).sum())), n=int(len(w)), big=round(float(w['usd'].max())))
            mid = f"{ev}:{mkt}:{hl}:{t0.strftime('%Y%m%dT%H%M')}:{d}"
            nflow = ncache.get(mid)
            if nflow is None and not ntape.empty and nov is not None:
                mids = {(x or {}).get('market_id') for x in nov['extra'].values if isinstance(x, dict)} - {None}
                if mids:
                    w = ntape[ntape['market'].isin(mids) & (ntape['ts'] >= t0 - pd.Timedelta(minutes=FLOW_MIN)) & (ntape['ts'] <= t0 + pd.Timedelta(minutes=FLOW_MIN))]
                    nflow = dict(usd=round(float(w['usd'].sum())), n=int(len(w)), big=round(float(w['usd'].max())) if len(w) else 0); ncache[mid] = nflow
            clv = 100 * (close - c['p1']) * d if close is not None and settled else None
            side = ('home' if d > 0 else 'away') if mkt != 'total' else ('over' if d > 0 else 'under')
            line = (hl if side in ('home', 'over') else -hl) if mkt == 'spread' else hl
            oc = closes.get((ev, mkt, float(line), side)) if settled else None
            moves.append(dict(id=mid, sport=sport, event_id=ev, away=e.get('away'), home=e.get('home'), start=start.strftime('%Y-%m-%dT%H:%MZ'), market=mkt, line=float(hl) if mkt != 'ml' else None,
                              ts=t0.strftime('%Y-%m-%dT%H:%MZ'), ttk_h=round((start - t0).total_seconds() / 3600, 2), origin=c['venue'], dir=d, side=side,
                              p0=round(c['p0'], 4), p1=round(c['p1'], 4), size_pts=round(100 * (c['p1'] - c['p0']) * d, 1), limit=lim, with_=c['members'],
                              followed=fol, soft_follow_rate=(round(len(soft_fol) / len(soft_seen), 2) if soft_seen else None), stuck=stuck,
                              kalshi=kflow, novig=nflow, close=(round(close, 4) if close is not None else None), settled=settled, started=bool(started),
                              clv_pts=(round(clv, 1) if clv is not None else None), stuck_clv_pts=(round(float(np.mean(stuck_clv)), 1) if stuck_clv else None),
                              outcome=(oc[0] if oc else None), push=(oc[1] if oc else None)))
    return moves


def tiles(moves):
    s = [m for m in moves if m['settled'] and m['clv_pts'] is not None]
    def agg(L):
        if not L: return None
        clv = [m['clv_pts'] for m in L]; w = [m['outcome'] for m in L if m['outcome'] is not None and not m.get('push')]
        fr = [m['soft_follow_rate'] for m in L if m['soft_follow_rate'] is not None]
        return dict(n=len(L), clv_pts=round(float(np.mean(clv)), 2), persist=round(float(np.mean([c >= 0 for c in clv])), 3), win=(round(float(np.mean(w)), 3) if w else None),
                    soft_follow=(round(float(np.mean(fr)), 3) if fr else None), stuck_clv_pts=(round(float(np.mean([m['stuck_clv_pts'] for m in L if m['stuck_clv_pts'] is not None])), 2) if any(m['stuck_clv_pts'] is not None for m in L) else None))
    T = dict(by_origin={v: agg([m for m in s if m['origin'] == v]) for v in FAST})
    pin = [m for m in s if m['origin'] == 'Pinnacle' and m['limit']]
    if len(pin) >= 30:
        lims = sorted(m['limit'] for m in pin); q1, q2 = lims[len(lims) // 3], lims[2 * len(lims) // 3]
        T['by_limit_tier'] = {f'low (<{q1:,.0f})': agg([m for m in pin if m['limit'] < q1]), f'mid': agg([m for m in pin if q1 <= m['limit'] < q2]), f'high (>={q2:,.0f})': agg([m for m in pin if m['limit'] >= q2])}
    def kb(m):
        k = m.get('kalshi')
        if not k: return 'no trades'
        return 'against' if k['net'] < -500 else ('<$1k with' if k['net'] < 1000 else ('$1k-5k with' if k['net'] < 5000 else '$5k+ with'))
    T['by_kalshi_flow'] = {b: agg([m for m in s if kb(m) == b]) for b in ('no trades', 'against', '<$1k with', '$1k-5k with', '$5k+ with')}
    def tb(m):
        h = m['ttk_h']; return '>24h' if h > 24 else ('6-24h' if h > 6 else ('1-6h' if h > 1 else '<1h'))
    T['by_time_to_kickoff'] = {b: agg([m for m in s if tb(m) == b]) for b in ('>24h', '6-24h', '1-6h', '<1h')}
    T['by_market'] = {k: agg([m for m in s if m['market'] == k]) for k in MARKETS}
    T['exchange_lead_no_pinnacle'] = agg([m for m in s if m['origin'] in ('Novig', 'Kalshi') and m['followed'].get('Pinnacle') is None])
    T['exchange_lead_pinnacle_followed'] = agg([m for m in s if m['origin'] in ('Novig', 'Kalshi') and m['followed'].get('Pinnacle') is not None])
    return {k: v for k, v in T.items() if v}


def main():
    closes = load_closes(); ncache = json.load(open(NCACHE)) if os.path.exists(NCACHE) else {}
    days = [(NOW - pd.Timedelta(days=i)).strftime('%Y-%m-%d') for i in range(0, 4)]; ntape = novig_tape(days)
    res = dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), move_pts=MOVE * 100, follow_pts=FOLLOW * 100, cluster_min=CLUSTER_MIN, flow_min=FLOW_MIN, gate=GATE, sports={})
    prev = collections.defaultdict(list)     # settled moves from earlier runs survive the raw-tick roll-off
    if os.path.exists(FULL):
        for m in read_jl([FULL]):
            if m.get('settled'): prev[m['sport']].append(m)
    allm = []
    for sport in SP.SPORTS:
        if sport == 'mlb': continue
        try:
            sched, fast, soft = load_sport(sport)
            if fast.empty and not prev.get(sport): res['sports'][sport] = dict(events=0, settled=0, moves=0, published=False); continue
            moves = detect(fast, soft, sched, closes, load_kalshi_trades(sport), ntape, ncache, sport)
            ids = {m['id'] for m in moves}; moves += [m for m in prev.get(sport, []) if m['id'] not in ids]
            moves.sort(key=lambda m: m['ts'], reverse=True); allm.extend(moves)
            settled_ev = len({m['event_id'] for m in moves if m['settled']}); fast_ev = int(fast['event_id'].nunique()) if not fast.empty else 0
            res['sports'][sport] = dict(events=fast_ev, settled=settled_ev, moves=len(moves), live=sum(1 for m in moves if not m['started']), published=settled_ev >= GATE,
                                        tiles=tiles(moves), tape=moves[:TAPE_ROWS])
            print(f"[moves] {sport}: {fast_ev} events on the fast tape, {len(moves)} moves, {settled_ev} settled events, published={settled_ev >= GATE}")
        except Exception as e:
            res['sports'][sport] = dict(error=f'{type(e).__name__}: {e}'); print(f"[moves] {sport}: ERROR {type(e).__name__}: {e}")
    json.dump(res, open(OUT, 'w'), separators=(',', ':'), default=str)
    with gzip.open(FULL, 'wt') as f:
        for m in allm: f.write(json.dumps(m, separators=(',', ':'), default=str) + '\n')
    json.dump(ncache, open(NCACHE, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
