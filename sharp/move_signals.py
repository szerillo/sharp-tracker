"""Move-based sharp signals on the venue tick log (20-minute snapshots, every venue), pre-registered 2026-10-29. Runs in the tracker job and
writes data/state/move_signals.json; the page shows each test only once its sample gate is met, same as tests.py.

Series: for each settled event x game market x main line x side, the devigged probability per venue per snapshot (books: two-way
multiplicative devig; exchanges: mid). Close = Pinnacle's last pre-kickoff devigged price (Novig's when Pinnacle has no market).

  M1 Pinnacle steam: Pinnacle moves >= 2.0 pts between snapshots. Persistence to close; soft-book follow rate within 1/2/3 snapshots;
     stale-book bet: book still at the old price after the move, taken in Pinnacle's direction -> CLV vs close and result.
  M2 Exchange lead: Novig or Kalshi mid moves >= 2.0 pts while Pinnacle is unchanged -> does Pinnacle follow within 1/2/3 snapshots;
     bet Pinnacle in the exchange's direction -> CLV vs Pinnacle close.
  M3 Juice before line: Pinnacle spread/total number unchanged, price shifted >= 1.5 pts -> direction of the next number change.
  M4 Timing: M1 persistence by ET hour bucket and hours-to-kickoff.
  M5 Limits: M1 persistence by Pinnacle max-risk limit tier at the time of the move.
  M6 Dispersion: soft book vs Pinnacle devigged price gap >= 2.5 pts with no Pinnacle move in the last 2 snapshots (static disagreement) -> CLV; the control for M1.
Gate: 150 settled events per sport (constants.MIN_EVENTS_GAME_LINES) before anything is published; preview numbers are labelled.
"""
import os, sys, json, sqlite3, math, datetime as dt, collections
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp import constants as C
SD = os.path.join(ROOT, 'data', 'state'); DB = os.path.join(SD, 'sharp.sqlite'); OUT = os.path.join(SD, 'move_signals.json')
EXCH = {'Novig', 'Kalshi', 'Polymarket'}; SOFT = {'DK', 'FD', 'Caesars', 'BetRivers', 'Fanatics', 'theScore', 'BetMGM'}
OTHER = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}
MOVE = 0.02; FOLLOW = 0.01; STALE_GAP = 0.025
GATE = 150   # settled events per sport before the move tests are published (preview below that)


def load(conn, sport):
    q = """SELECT t.ts_utc, t.event_id, t.start_utc, t.market, t.line, t.side, t.venue, t.implied, t.mid, t."limit", t.flags
           FROM ticks t WHERE t.sport=? AND t.mclass='game' AND t.market IN ('ml','spread','total') AND t.ts_utc < t.start_utc"""
    df = pd.read_sql_query(q, conn, params=(sport,))
    if df.empty: return df
    df['p_raw'] = np.where(df['venue'].isin(EXCH), df['mid'], df['implied'])
    df = df[df['p_raw'].notna() & ~df['flags'].fillna('').str.contains('threeway')]
    # snapshot grid: round to 20 minutes
    df['snap'] = (pd.to_datetime(df['ts_utc']).astype('int64') // 10**9 // 1200) * 1200
    # devig books two-way per (event, venue, market, line, snap)
    df['line_key'] = df['line'].fillna(0.0)
    df['home_line'] = np.where(df['side'].isin(['home', 'over']), df['line_key'], -df['line_key'])   # pair spreads by the home-side number
    df.loc[df['market'] == 'total', 'home_line'] = df.loc[df['market'] == 'total', 'line_key']
    key = ['event_id', 'venue', 'market', 'home_line', 'snap']
    tot = df.groupby(key)['p_raw'].transform('sum'); n = df.groupby(key)['p_raw'].transform('count')
    df['p'] = np.where(df['venue'].isin(EXCH), df['p_raw'], np.where(n == 2, df['p_raw'] / tot, np.nan))
    df = df[df['p'].notna()].drop_duplicates(key + ['side'])
    return df


def main_lines(df):
    """the most-quoted home-side number per event x market (venue-snapshots quoting it)"""
    c = df[df['venue'] == 'Pinnacle'].groupby(['event_id', 'market', 'home_line']).size().reset_index(name='n')
    c = c.sort_values('n', ascending=False).drop_duplicates(['event_id', 'market'])
    return df.merge(c[['event_id', 'market', 'home_line']], on=['event_id', 'market', 'home_line'])


def results(conn, sport):
    r = pd.read_sql_query("SELECT event_id, venue, market, line, side, outcome, p_close FROM closes WHERE outcome IS NOT NULL", conn)
    return r


def run_sport(conn, sport):
    df = load(conn, sport)
    out = dict(sport=sport, events=0, gate=GATE, published=False, tests={})
    if df.empty: return out
    df = main_lines(df)
    res = results(conn, sport)
    if res.empty: return out
    # Pinnacle close per event/market/side (fallback Novig)
    pin = df[df['venue'] == 'Pinnacle'].sort_values('snap').groupby(['event_id', 'market', 'side']).tail(1)[['event_id', 'market', 'side', 'p']].rename(columns={'p': 'close'})
    nov = df[df['venue'] == 'Novig'].sort_values('snap').groupby(['event_id', 'market', 'side']).tail(1)[['event_id', 'market', 'side', 'p']].rename(columns={'p': 'close_n'})
    close = pin.merge(nov, on=['event_id', 'market', 'side'], how='outer'); close['close'] = close['close'].fillna(close['close_n'])
    oc = res.groupby(['event_id', 'market', 'side'])['outcome'].first().reset_index()
    close = close.merge(oc, on=['event_id', 'market', 'side'], how='inner')
    settled = set(close['event_id']); df = df[df['event_id'].isin(settled)]
    out['events'] = len(settled)
    if not len(df): return out
    piv = df.pivot_table(index=['event_id', 'market', 'side', 'snap'], columns='venue', values='p').reset_index().sort_values(['event_id', 'market', 'side', 'snap'])
    lim = df[df['venue'] == 'Pinnacle'].set_index(['event_id', 'market', 'side', 'snap'])['limit']
    piv = piv.merge(close, on=['event_id', 'market', 'side'], how='inner')
    g = piv.groupby(['event_id', 'market', 'side'])
    venues = [v for v in piv.columns if v in SOFT | EXCH | {'Pinnacle'}]
    for v in venues: piv[f'd_{v}'] = g[v].diff()
    for v in venues:
        for k in (1, 2, 3): piv[f'f{k}_{v}'] = g[v].shift(-k) - piv[v]       # forward change over the next k snapshots
    T = out['tests']

    def clv_rows(rows, venue_col, direction_col):
        """bet `venue_col` at its price in `direction` (+1 toward yes side of this row). returns clv (close - price) and roi."""
        p = rows[venue_col].values; d = rows[direction_col].values; cl = rows['close'].values; oc_ = rows['outcome'].values
        price = np.where(d > 0, p, 1 - p); fair = np.where(d > 0, cl, 1 - cl); won = np.where(d > 0, oc_, 1 - oc_)
        roi = np.where(won == 1, (1 - price) / price, -1.0)
        return fair - price, roi, won

    # M1 Pinnacle steam
    if 'Pinnacle' in piv:
        m = piv[piv['d_Pinnacle'].abs() >= MOVE].copy(); m['dir'] = np.sign(m['d_Pinnacle'])
        if len(m):
            pers = ((m['close'] - m['Pinnacle']) * m['dir'] >= 0).mean()
            fol = {}
            for k in (1, 2, 3):
                cols = [f'f{k}_{v}' for v in venues if v in SOFT and f'f{k}_{v}' in m]
                if cols: fol[k] = float(np.nanmean([((m[c] * m['dir']) >= FOLLOW).mean() for c in cols]))
            stale = []
            for v in venues:
                if v not in SOFT or f'd_{v}' not in m: continue
                s = m[(m[f'd_{v}'].abs() < 0.005) & m[v].notna()]
                if len(s):
                    clv, roi, won = clv_rows(s, v, 'dir'); stale.append(pd.DataFrame(dict(venue=v, clv=clv, roi=roi, won=won)))
            st = pd.concat(stale) if stale else pd.DataFrame(columns=['venue', 'clv', 'roi', 'won'])
            T['M1_pinnacle_steam'] = dict(n_moves=int(len(m)), events=int(m['event_id'].nunique()), persistence_to_close=round(float(pers), 3), soft_follow_within=fol,
                                          stale_book_bets=int(len(st)), stale_clv_pts=round(100 * float(st['clv'].mean()), 2) if len(st) else None,
                                          stale_roi=round(float(st['roi'].mean()), 4) if len(st) else None, stale_win=round(float(st['won'].mean()), 3) if len(st) else None,
                                          by_book={v: dict(n=int(len(x)), clv_pts=round(100 * float(x['clv'].mean()), 2), roi=round(float(x['roi'].mean()), 4)) for v, x in st.groupby('venue')} if len(st) else {})
            # M4 timing
            m['et_hour'] = ((m['snap'] - 4 * 3600) % 86400 // 3600).astype(int)
            m['ttk_h'] = (pd.to_datetime(m['start_utc'] if 'start_utc' in m else None).astype('int64') // 10**9 - m['snap']) / 3600 if 'start_utc' in m else np.nan
            b = pd.cut(m['et_hour'], [-1, 5, 9, 13, 17, 21, 24], labels=['0-5am', '6-9am', '10am-1pm', '2-5pm', '6-9pm', '10pm-12'])
            T['M4_timing'] = {str(k): dict(n=int(len(x)), persistence=round(float(((x['close'] - x['Pinnacle']) * x['dir'] >= 0).mean()), 3)) for k, x in m.groupby(b, observed=True) if len(x)}
            # M5 limits
            ml = m.join(lim.rename('lim'), on=['event_id', 'market', 'side', 'snap'])
            if ml['lim'].notna().any():
                q = pd.qcut(ml['lim'].rank(method='first'), min(3, ml['lim'].notna().sum()), labels=False, duplicates='drop') if ml['lim'].notna().sum() >= 3 else None
                if q is not None:
                    T['M5_limit_tier'] = {f"tier{int(k)} (median ${x['lim'].median():,.0f})": dict(n=int(len(x)), persistence=round(float(((x['close'] - x['Pinnacle']) * x['dir'] >= 0).mean()), 3)) for k, x in ml.groupby(q) if len(x)}
    # M2 exchange lead
    for ex in ('Novig', 'Kalshi'):
        if ex not in piv or 'Pinnacle' not in piv: continue
        m = piv[(piv[f'd_{ex}'].abs() >= MOVE) & (piv['d_Pinnacle'].abs() < 0.005) & piv['Pinnacle'].notna()].copy(); m['dir'] = np.sign(m[f'd_{ex}'])
        if not len(m): continue
        fol = {k: round(float(((m[f'f{k}_Pinnacle'] * m['dir']) >= FOLLOW).mean()), 3) for k in (1, 2, 3) if f'f{k}_Pinnacle' in m}
        clv, roi, won = clv_rows(m, 'Pinnacle', 'dir')
        T[f'M2_{ex.lower()}_leads'] = dict(n_moves=int(len(m)), events=int(m['event_id'].nunique()), pinnacle_follows_within=fol, bet_pinnacle_clv_pts=round(100 * float(np.nanmean(clv)), 2),
                                           roi=round(float(np.nanmean(roi)), 4), win=round(float(np.nanmean(won)), 3))
    # M6 static dispersion control
    if 'Pinnacle' in piv:
        rows = []
        for v in venues:
            if v not in SOFT or v not in piv: continue
            s = piv[(piv[v] - piv['Pinnacle'] <= -STALE_GAP) & (piv['d_Pinnacle'].abs() < 0.005) & (g['d_Pinnacle'].shift(1).abs() < 0.005)].copy()   # book cheaper than Pinnacle, Pinnacle quiet
            if len(s):
                s['dir'] = 1; clv, roi, won = clv_rows(s, v, 'dir'); rows.append(pd.DataFrame(dict(venue=v, clv=clv, roi=roi, won=won)))
        if rows:
            st = pd.concat(rows)
            T['M6_static_dispersion_control'] = dict(n=int(len(st)), clv_pts=round(100 * float(st['clv'].mean()), 2), roi=round(float(st['roi'].mean()), 4), win=round(float(st['won'].mean()), 3))
    out['published'] = out['events'] >= GATE
    return out


def main():
    conn = sqlite3.connect(DB)
    sports = [r[0] for r in conn.execute("SELECT DISTINCT sport FROM ticks WHERE sport != 'mlb'")]
    res = dict(built=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), move_pts=MOVE * 100, follow_pts=FOLLOW * 100, sports={})
    for sp in sports:
        try: res['sports'][sp] = run_sport(conn, sp)
        except Exception as e: res['sports'][sp] = dict(sport=sp, error=f'{type(e).__name__}: {e}')
    json.dump(res, open(OUT, 'w'), indent=1, default=str)
    for sp, r in res['sports'].items(): print(f"[move_signals] {sp}: {r.get('events', 0)} settled events, {len(r.get('tests', {}))} tests computed, published={r.get('published')}{' ERROR ' + r['error'] if r.get('error') else ''}")


if __name__ == '__main__':
    main()
