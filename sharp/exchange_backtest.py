"""Exchange-signal backtests on the Novig public tape (since 2026-08-03) and Kalshi's settled sports markets + trade tape.

Builds one feature row per two-outcome market ("yes" = Kalshi ticker outcome; Novig: the first listed outcome) from its pre-kickoff
trades: price at T-24h/6h/1h/close, VWAPs, signed taker flow, big-trade direction, hourly path; result from settlement. Then runs the
pre-registered tests (docs/exchange_signals_audit_*.md) with a chronological train/holdout split per sport.

python3 -m sharp.exchange_backtest build     -> data/state/exchange_features.csv.gz, data/state/exchange_hourly.csv.gz
python3 -m sharp.exchange_backtest report    -> docs/exchange_signals_audit_<date>.md
Prices are probabilities (cost per $1 contract). ROI here is before exchange fees; Kalshi's taker fee (~7% of p(1-p)) is stated in the doc."""
import os, sys, re, json, gzip, glob, math, datetime as dt, collections
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
from sharp import sports as SP
SD = os.path.join(ROOT, 'data', 'state'); HS = os.path.join(SD, 'hist_schedule.json')
FEAT = os.path.join(SD, 'exchange_features.csv.gz'); HOURLY = os.path.join(SD, 'exchange_hourly.csv.gz')
WINDOWS = {'24h': 24 * 3600, '6h': 6 * 3600, '2h': 2 * 3600, '1h': 3600}
SPORT_OF_LEAGUE = {'NFL': 'nfl', 'NBA': 'nba', 'NHL': 'nhl', 'MLB': 'mlb', 'NCAAF': 'cfb', 'EPL': 'epl', 'La Liga': 'laliga', 'Bundesliga': 'bundesliga', 'Serie A': 'seriea',
                   'Ligue 1': 'ligue1', 'MLS': 'mls', 'Champions League': 'ucl', 'UFC': 'mma'}
KSERIES_SPORT = {'KXNFL': 'nfl', 'KXNBA': 'nba', 'KXNHL': 'nhl', 'KXMLB': 'mlb', 'KXNCAAF': 'cfb', 'KXEPL': 'epl', 'KXLALIGA': 'laliga', 'KXBUNDESLIGA': 'bundesliga',
                 'KXSERIEA': 'seriea', 'KXLIGUE1': 'ligue1', 'KXMLS': 'mls', 'KXUCL': 'ucl', 'KXUFC': 'mma'}
MLB_FIX = {'CHW': 'CWS', 'WAS': 'WSH', 'AZ': 'ARI', 'OAK': 'ATH', 'KCR': 'KC', 'SDP': 'SD', 'SFG': 'SF', 'TBR': 'TB'}
GAME_TYPES_NOVIG = {'MONEY': 'ml', 'SPREAD': 'spread', 'TOTAL': 'total', 'MONEYLINE_3_WAY_WIN': 'ml', 'MONEY_1H': '1h_ml', 'SPREAD_1H': '1h_spread', 'TOTAL_1H': '1h_total'}


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


MLB_NAMES = {'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
             'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL', 'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
             'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA', 'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
             'New York Yankees': 'NYY', 'Athletics': 'ATH', 'Oakland Athletics': 'ATH', 'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD',
             'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH'}


class _MLBTeams:
    nick = {k.split()[-1].lower(): v for k, v in MLB_NAMES.items()}
    def code(self, x):
        if not x: return None
        s = str(x).strip()
        if s in MLB_NAMES: return MLB_NAMES[s]
        if s.upper() in MLB_NAMES.values(): return s.upper()
        return self.nick.get(s.lower().split()[-1]) if s.split() else None


# ----------------------------------------------------------------- schedule lookup -----
class Sched:
    def __init__(self):
        self.h = json.load(open(HS)) if os.path.exists(HS) else {}
        self.by = {}
        for sp, games in self.h.items():
            d = collections.defaultdict(list)
            for eid, g in games.items():
                day = dt.datetime.fromtimestamp(ts(g['start']), dt.timezone.utc) - dt.timedelta(hours=4)   # ET date (approx, DST ignored)
                for k in (-1, 0, 1): d[(day.date() + dt.timedelta(days=k), g['away'], g['home'])].append(g)
                d[('name', g['away'], g['home'])].append(g)
            self.by[sp] = d
        self.teams = {sp: SP.Teams(sp) for sp in ('nfl', 'nba', 'nhl')}
        self.teams['mlb'] = _MLBTeams()

    def kalshi(self, sport, date, blob, home_first=False):
        fix = {**SP.CODE_FIX.get(sport, {}), **(MLB_FIX if sport == 'mlb' else {})}
        codes = {g['home'] for g in self.h.get(sport, {}).values()} | {g['away'] for g in self.h.get(sport, {}).values()}
        sp = SP.split_codes(blob, codes, fix)
        if not sp: return None
        a, h = sp
        if home_first: a, h = h, a
        c = self.by.get(sport, {}).get((date, a, h)) or self.by.get(sport, {}).get((date, h, a))
        return c[0] if c else None

    def novig(self, sport, desc, start_ts):
        if not desc or '@' not in desc: return None
        aw, hm = [x.strip() for x in desc.split('@', 1)]
        T = self.teams.get(sport)
        if T:
            a, h = T.code(aw), T.code(hm)
        else:
            a, h = aw, hm
        day = (dt.datetime.fromtimestamp(start_ts / 1000, dt.timezone.utc) - dt.timedelta(hours=4)).date()
        c = self.by.get(sport, {}).get((day, a, h))
        return c[0] if c else None


# ----------------------------------------------------------------- features -----
def px_at(pre, cut, stale=2 * 3600):
    """Two-sided price estimate at time `cut`: mid of the last yes-buy and the last no-buy (yes-equivalent) if both printed within `stale`
    seconds of each other; otherwise the last trade. Taker fills print at the ask, so a one-sided tape overstates the side being bought."""
    before = [x for x in pre if x[0] <= cut]
    if not before: return None, None
    ly = next((x for x in reversed(before) if x[3] > 0), None); ln = next((x for x in reversed(before) if x[3] < 0), None)
    if ly and ln and abs(ly[0] - ln[0]) <= stale: return round((ly[1] + ln[1]) / 2, 4), 2
    return before[-1][1], 1


def features(trades, start, result):
    """trades: list of (t, p_yes, usd, taker_yes:+1/-1). start: kickoff epoch. -> dict of pre-kickoff features or None."""
    pre = sorted(x for x in trades if x[0] < start)
    if len(pre) < 3: return None
    close, two = px_at(pre, start)
    f = dict(n_trades=len(pre), usd=round(sum(x[2] for x in pre), 2), first_t=pre[0][0], close=close, close_sides=two, close_t=pre[-1][0], last_trade=pre[-1][1], result=result)
    for name, sec in WINDOWS.items():
        cut = start - sec
        f[f'p_{name}'], _ = px_at(pre, cut)
        w = [x for x in pre if x[0] > cut]
        tot = sum(x[2] for x in w)
        f[f'vwap_{name}'] = round(sum(x[1] * x[2] for x in w) / tot, 4) if tot else None
        f[f'usd_{name}'] = round(tot, 2)
        f[f'flow_{name}'] = round(sum(x[2] * x[3] for x in w), 2)                       # signed taker $ (yes buys - no buys)
        f[f'flow_{name}_pct'] = round(f[f'flow_{name}'] / tot, 3) if tot else None
    big = sorted(pre, key=lambda x: -x[2])[:max(1, len(pre) // 20)]                      # top 5% of trades by size
    f['big_usd'] = round(sum(x[2] for x in big), 2); f['big_flow'] = round(sum(x[2] * x[3] for x in big), 2)
    f['big_last_dir'] = big[0][3] if big else 0; f['big_last_p'] = big[0][1]; f['big_last_t'] = big[0][0]
    f['big_last_after'] = round((close or big[0][1]) - big[0][1], 4)
    hp = {}; ly = {}; ln = {}
    for t, p, u, s in pre:
        h = int((t - start) // 3600)
        (ly if s > 0 else ln)[h] = p
    for h in set(ly) | set(ln):                                                           # hourly two-sided mid (yes-buy and no-buy both printed that hour); one-sided hours dropped
        if h in ly and h in ln: hp[h] = (round((ly[h] + ln[h]) / 2, 4), round(ly[h] - ln[h], 4))   # (mid, taker spread = yes ask - yes bid)
    f['hourly'] = hp
    return f


def novig_rows(sched, cat, days):
    out = []; hourly = []
    tape = collections.defaultdict(list)
    for d in days:
        p = os.path.join(ROOT, 'data', 'novig', 'tape', f'{d}.jsonl.gz')
        if not os.path.exists(p): continue
        for l in gzip.open(p, 'rt'):
            r = json.loads(l)
            if r['type'] not in GAME_TYPES_NOVIG: continue
            tape[r['market']].append((ts(r['ts']), r['outcome'], r['price'], r['qty']))
    n_unres = 0
    for mid, L in tape.items():
        m = cat.get(mid)
        if not m or not m.get('result') or not m.get('start_ts') or len(m.get('outcomes') or {}) != 2: n_unres += 1; continue
        sport = SPORT_OF_LEAGUE.get(m.get('league'))
        if not sport: continue
        oids = list(m['outcomes']); yes = oids[0]
        res = m['result'].get(yes)
        if res not in ('WIN', 'LOSS'): continue
        tr = [(t, p if o == yes else round(1 - p, 4), q, 1 if o == yes else -1) for t, o, p, q in L]
        start = m['start_ts'] / 1000
        f = features(tr, start, 1 if res == 'WIN' else 0)
        if not f: continue
        g = sched.novig(sport, m.get('event'), m['start_ts'])
        mtype = GAME_TYPES_NOVIG[m['type']]
        yname = m['outcomes'][yes]
        if mtype.endswith('total'): side = 'over' if yname.lower().startswith('over') else 'under'
        elif mtype.endswith('ml'):
            side = 'home' if (g and sched.teams.get(sport) and sched.teams[sport].code(yname.replace(' MONEYLINE_3_WAY_WIN', '')) == g['home']) else ('away' if g else 'unk')
            if m['type'] == 'MONEYLINE_3_WAY_WIN':
                tm = (m.get('desc') or '').replace(' MONEYLINE_3_WAY_WIN', '').strip(); hm = (m.get('event') or '').split('@')[-1].strip()
                side = 'home' if tm and hm.startswith(tm.split()[0]) else 'away'
        else:
            mm = re.search(r'([+-]\d+\.?\d*)$', yname); side = ('home' if g and sched.teams.get(sport) and sched.teams[sport].code(re.sub(r'\s*[+-]\d+\.?\d*$', '', yname)) == g['home'] else 'unk') if mm else 'unk'
        hp = f.pop('hourly'); strike = None if mtype.endswith('ml') or m.get('strike') in (None, '') else float(m['strike'])
        key = f"{sport}|{g['start'][:10] if g else dt.datetime.fromtimestamp(start, dt.timezone.utc).date()}|{g['away'] if g else '?'}@{g['home'] if g else '?'}|{mtype}|{side}|{strike}"
        out.append(dict(venue='Novig', sport=sport, mtype=mtype, side=side, line=m.get('strike'), market=mid, event=m.get('event'), key=key, start=start,
                        date=dt.datetime.fromtimestamp(start, dt.timezone.utc).date().isoformat(), **f))
        for h, (p, spd) in hp.items(): hourly.append(dict(venue='Novig', key=key, market=mid, h=h, p=p, sp=spd))
    print(f"[exchange_backtest] Novig: {len(out)} markets ({n_unres} tape markets without catalog result/start)")
    return out, hourly


def kalshi_rows(sched):
    out = []; hourly = []
    mk = {}
    mp = os.path.join(ROOT, 'data', 'kalshi', 'history', 'markets.jsonl')
    if not os.path.exists(mp): return out, hourly
    for l in open(mp):
        r = json.loads(l); mk[r['ticker']] = r
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'kalshi', 'history', 'trades', '*.jsonl.gz'))):
        series = os.path.basename(f)[:-9]; pre = next((k for k in KSERIES_SPORT if series.startswith(k)), None)
        if not pre: continue
        sport = KSERIES_SPORT[pre]; suffix = series[len(pre):]
        mtype = {'GAME': 'ml', 'SPREAD': 'spread', 'TOTAL': 'total', '1H': '1h_ml', '1HSPREAD': '1h_spread', '1HTOTAL': '1h_total', 'FIGHT': 'ml'}.get(suffix)
        if not mtype: continue
        by = collections.defaultdict(list)
        try:
          for l in gzip.open(f, 'rt'):
            r = json.loads(l); by[r['ticker']].append((ts(r['ts']), r['yes'], r['n'] * r['yes'] if r['taker'] == 'yes' else r['n'] * (1 - r['yes']), 1 if r['taker'] == 'yes' else -1))
        except (EOFError, OSError, ValueError): pass      # a series still being written by the puller: use what is complete
        for tk, L in by.items():
            m = mk.get(tk)
            if not m or m.get('result') not in ('yes', 'no'): continue
            ev = m['event_ticker'].split('-', 1)[1]; pe = SP.kalshi_event(ev)
            if not pe: continue
            date, blob = pe
            g = sched.kalshi(sport, date, blob, home_first=sport in ('epl', 'laliga', 'bundesliga', 'seriea', 'ligue1', 'mls', 'ucl', 'mma'))
            if not g: continue
            start = ts(g['start'])
            # $ notional for a yes-taker is n*yes, for a no-taker n*(1-yes): both sides' cost
            fx = features([(t, p, u, s) for t, p, u, s in L], start, 1 if m['result'] == 'yes' else 0)
            if not fx: continue
            tail = tk.rsplit('-', 1)[1]; fix = {**SP.CODE_FIX.get(sport, {}), **(MLB_FIX if sport == 'mlb' else {})}
            if mtype.endswith('total'): side = 'over'
            elif mtype.endswith('ml'): side = 'home' if fix.get(tail, tail) == g['home'] else ('away' if fix.get(tail, tail) == g['away'] else 'draw' if tail == 'TIE' else 'unk')
            else:
                tcode = re.sub(r'\d+$', '', tail); side = 'home' if fix.get(tcode, tcode) == g['home'] else 'away'
            hp = fx.pop('hourly'); strike = None if mtype.endswith('ml') or m.get('strike') in (None, '') else float(m['strike'])
            key = f"{sport}|{g['start'][:10]}|{g['away']}@{g['home']}|{mtype}|{side}|{strike}"
            out.append(dict(venue='Kalshi', sport=sport, mtype=mtype, side=side, line=m.get('strike'), market=tk, event=f"{g['away']} @ {g['home']}", key=key, start=start,
                            date=g['start'][:10], **fx))
            for h, (p, spd) in hp.items(): hourly.append(dict(venue='Kalshi', key=key, market=tk, h=h, p=p, sp=spd))
    print(f"[exchange_backtest] Kalshi: {len(out)} markets")
    return out, hourly


def build():
    from novig_catalog import load_catalog
    sched = Sched(); cat = load_catalog()
    days = sorted(os.path.basename(p)[:-9] for p in glob.glob(os.path.join(ROOT, 'data', 'novig', 'tape', '*.jsonl.gz')))
    n_rows, n_h = novig_rows(sched, cat, days)
    k_rows, k_h = kalshi_rows(sched)
    df = pd.DataFrame(n_rows + k_rows); hh = pd.DataFrame(n_h + k_h)
    df.to_csv(FEAT, index=False); hh.to_csv(HOURLY, index=False)
    print(f"[exchange_backtest] {len(df)} market rows, {len(hh)} hourly points -> {FEAT}")
    return df


# ----------------------------------------------------------------- tests -----
def roi_yes(p, won):
    """Return per $1 risked buying yes at price p: win -> (1-p)/p, lose -> -1."""
    return np.where(won == 1, (1 - p) / p, -1.0)


def z(hits, n, p0=0.5):
    return (hits - n * p0) / math.sqrt(n * p0 * (1 - p0)) if n else 0.0


def split(df):
    """chronological 70/30 per sport+venue."""
    df = df.copy(); df['hold'] = False
    for (sp, v), g in df.groupby(['sport', 'venue']):
        cut = g['date'].quantile(0.7, interpolation='lower') if len(g) else None
        if cut is not None: df.loc[g.index[g['date'] > cut], 'hold'] = True
    return df


def brier(p, y): return float(np.mean((p - y) ** 2))
def logloss(p, y):
    p = np.clip(p, 1e-4, 1 - 1e-4); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def logit_fit(X, y, iters=50, l2=1e-3):
    """tiny Newton logistic regression; X includes intercept column. returns beta, se"""
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        pz = 1 / (1 + np.exp(-X @ b)); W = pz * (1 - pz)
        H = X.T @ (X * W[:, None]) + l2 * np.eye(X.shape[1]); gr = X.T @ (y - pz) - l2 * b
        step = np.linalg.solve(H, gr); b = b + step
        if np.abs(step).max() < 1e-8: break
    pz = 1 / (1 + np.exp(-X @ b)); W = pz * (1 - pz); H = X.T @ (X * W[:, None]) + l2 * np.eye(X.shape[1])
    return b, np.sqrt(np.diag(np.linalg.inv(H)))


def fmt_roi(r): return f"{100 * r:+.1f}%"


def report():
    df = pd.read_csv(FEAT); hh = pd.read_csv(HOURLY); hh = hh[hh['sp'].abs() <= 0.04]     # hourly mids only where the taker spread was within 4c (a price, not a guess)
    df = df[df['side'] != 'unk'].copy(); df['date'] = df['date'].astype(str)
    df['main'] = df.groupby(['venue', 'sport', 'event', 'date', 'mtype'])['usd'].transform('max') == df['usd']     # the most-traded strike per game x market
    n_all = len(df)
    df = df[(df['usd'] >= 2000) & (df['n_trades'] >= 10) & df['close'].notna()].copy()                              # liquidity floor: thin alt lines print at the ask, not at a price
    df = split(df); df['won'] = df['result'].astype(int)
    hh = hh.merge(df.loc[df['main'], ['venue', 'market']].drop_duplicates(), on=['venue', 'market'])      # hourly paths: liquid main lines only (one market per series)
    today = dt.date.today().isoformat(); L = []
    P = L.append
    P(f"# Exchange signal audit, {today}\n")
    P("Novig public tape (every taker fill since 2026-08-03) and Kalshi settled sports markets with their full trade tape, aligned to ESPN kickoff times. "
      "One row per two-outcome market; 'yes' is the Kalshi ticker outcome or Novig's first listed outcome. Pre-kickoff trades only. "
      "Train = first 70% of each sport x venue by date, holdout = last 30%. ROI is per $1 risked at the exchange price, before fees "
      "(Kalshi taker fee is about 7% of p(1-p) per contract, 1.75c at 50/50; Novig charges no fee on taker fills today). Nothing here was tuned on the holdout.\n")
    P(f"Liquidity floor: markets with >= $2,000 and >= 10 pre-kickoff trades ({len(df)} of {n_all} markets). Prices are two-sided mids where the last yes-buy and no-buy printed within 2h of each other (close_sides = 2), else the last print. "
      f"'Main' = the most-traded strike per game and market type; alt lines are kept but flagged.\n")
    P("## 0. Sample\n")
    P("| venue | sport | markets | main lines | two-sided close | with T-24h price | with T-6h | $ pre-kickoff |\n|---|---|---|---|---|---|---|---|")
    for (v, sp), g in df.groupby(['venue', 'sport']):
        P(f"| {v} | {sp} | {len(g)} | {int(g['main'].sum())} | {int((g['close_sides'] == 2).sum())} | {g['p_24h'].notna().sum()} | {g['p_6h'].notna().sum()} | ${g['usd'].sum():,.0f} |")

    # T1 calibration
    P("\n## 1. How good is the exchange price, and when? (calibration)\n")
    P("Brier score and log loss of the last trade before T-24h, T-6h, T-1h and the final pre-kickoff trade, against the result. Lower is better; 0.25 Brier = coin flip. "
      "If the close is sharper than T-6h the market learns something in the last hours; the size of that gap is the ceiling for any timing edge.\n")
    dm = df[df['main']]
    P("Main lines only (one market per game x type), so the games are the sample, not the alt strikes.\n")
    P("| venue | sport | n(close) | Brier 24h | Brier 6h | Brier 1h | Brier close | logloss close | n(24h) |\n|---|---|---|---|---|---|---|---|---|")
    for (v, sp), g in dm.groupby(['venue', 'sport']):
        if len(g) < 40: continue
        row = [v, sp, len(g)]
        for c in ('p_24h', 'p_6h', 'p_1h', 'close'):
            gg = g[g[c].notna()]; row.append(f"{brier(gg[c].values, gg['won'].values):.4f} (n={len(gg)})" if len(gg) >= 30 else 'n/a')
        gg = g[g['close'].notna()]; row.append(f"{logloss(gg['close'].values, gg['won'].values):.4f}"); row.append(int(g['p_24h'].notna().sum()))
        P('| ' + ' | '.join(str(x) for x in row) + ' |')
    P("\nReliability of the close (all sports, main lines, by venue): bucket = implied probability, hit = how often yes won.\n")
    P("| venue | bucket | n | implied avg | hit rate | gap |\n|---|---|---|---|---|---|")
    for v, g in dm.groupby('venue'):
        g = g[g['close'].notna()]; b = (g['close'] * 10).clip(0, 9).astype(int)
        for k, gg in g.groupby(b):
            if len(gg) < 25: continue
            P(f"| {v} | {k / 10:.1f}-{(k + 1) / 10:.1f} | {len(gg)} | {gg['close'].mean():.3f} | {gg['won'].mean():.3f} | {gg['won'].mean() - gg['close'].mean():+.3f} |")

    # T7 drift / structural
    P("\n## 2. Structural drift: does one side systematically beat the exchange price?\n")
    P("Buy every yes at the T-24h price (or the close) and hold to settlement, grouped by what yes is. A market with no edge sits near the fee-free break-even of 0%; "
      "favorite/dog is defined by the T-24h price. This is the cheapest possible test of market efficiency and the baseline every signal below must beat.\n")
    P("| venue | sport | group | at T-24h: n / ROI / win% | at close: n / ROI / win% | holdout close ROI (n) |\n|---|---|---|---|---|---|")
    df['grp'] = np.where(df['mtype'].str.endswith('total'), np.where(df['side'] == 'over', 'over', 'under'),
                         np.where(df['p_24h'].fillna(df['close']) >= 0.5, 'favorite (p>=.5)', 'underdog (p<.5)'))
    for (v, sp, grp), g in df[df['main']].groupby(['venue', 'sport', 'grp']):
        if len(g) < 40: continue
        a = g[g['p_24h'].notna()]; r24 = roi_yes(a['p_24h'].values, a['won'].values) if len(a) else np.array([])
        rc = roi_yes(g['close'].values, g['won'].values); h = g[g['hold']]; rh = roi_yes(h['close'].values, h['won'].values) if len(h) else np.array([])
        P(f"| {v} | {sp} | {grp} | {len(a)} / {fmt_roi(r24.mean()) if len(a) else 'n/a'} / {a['won'].mean():.3f} | {len(g)} / {fmt_roi(rc.mean())} / {g['won'].mean():.3f} | {fmt_roi(rh.mean()) if len(h) else 'n/a'} ({len(h)}) |")

    # T2 momentum
    P("\n## 3. Momentum vs reversion: does the move from T-6h to the close carry information the close hasn't priced?\n")
    P("Move = close - p(T-6h), in cents. Strategy 'continuation': buy yes at the close when the move was >= +3c, buy no when <= -3c. 'Reversion' is the opposite. "
      "The logistic test adds the move to logit(close) and asks whether its coefficient is positive (continuation) or negative (reversion) out of sample.\n")
    P("| venue | sport | n moves >=3c | continuation ROI train / hold (n) | reversion = negative of that | logit coef on move (se) train | holdout logloss: close only vs close+move |\n|---|---|---|---|---|---|---|")
    for (v, sp), g in df[df['main']].groupby(['venue', 'sport']):
        g = g[g['p_6h'].notna() & g['close'].notna()].copy()
        if len(g) < 60: continue
        g['mv'] = g['close'] - g['p_6h']
        def cont(gg):
            up = gg[gg['mv'] >= 0.03]; dn = gg[gg['mv'] <= -0.03]
            r = np.concatenate([roi_yes(up['close'].values, up['won'].values), roi_yes(1 - dn['close'].values, 1 - dn['won'].values)])
            return r, len(up) + len(dn)
        rt, nt = cont(g[~g['hold']]); rh, nh = cont(g[g['hold']])
        tr, ho = g[~g['hold']], g[g['hold']]
        X = np.column_stack([np.ones(len(tr)), np.log(tr['close'].clip(0.02, 0.98) / (1 - tr['close'].clip(0.02, 0.98))), tr['mv'] * 10])
        b, se = logit_fit(X, tr['won'].values)
        Xh = np.column_stack([np.ones(len(ho)), np.log(ho['close'].clip(0.02, 0.98) / (1 - ho['close'].clip(0.02, 0.98))), ho['mv'] * 10])
        ll_close = logloss(ho['close'].values, ho['won'].values) if len(ho) else float('nan')
        ll_mv = logloss(1 / (1 + np.exp(-(Xh @ b))), ho['won'].values) if len(ho) else float('nan')
        P(f"| {v} | {sp} | {nt + nh} | {fmt_roi(rt.mean()) if nt else 'n/a'} / {fmt_roi(rh.mean()) if nh else 'n/a'} ({nt}/{nh}) | reversion | {b[2]:+.3f} ({se[2]:.3f}) per 10c | {ll_close:.4f} vs {ll_mv:.4f} (n={len(ho)}) |")

    # T3 flow
    P("\n## 4. Late taker flow: follow the money in the last 6h / 2h?\n")
    P("Signed taker dollars (yes buys minus no buys) in the window, as a share of window volume. Strategy: when |flow share| >= 0.3 and window volume >= $500, buy the side the takers bought, at the close. "
      "This is the exchange version of 'sharp money', with the advantage that every dollar is real and timestamped.\n")
    P("| venue | sport | lines | window | n | train ROI / win% | holdout ROI / win% (n) | z vs break-even (holdout) |\n|---|---|---|---|---|---|---|---|")
    for (v, sp), g0 in df.groupby(['venue', 'sport']):
      for lines_lab, g in (('main', g0[g0['main']]), ('all', g0)):
        for w in ('6h', '2h'):
            gg = g[(g[f'usd_{w}'] >= 500) & g[f'flow_{w}_pct'].notna() & (g[f'flow_{w}_pct'].abs() >= 0.3) & g['close'].notna()]
            if len(gg) < 40: continue
            def strat(x):
                buy_yes = x[f'flow_{w}_pct'] > 0
                p = np.where(buy_yes, x['close'], 1 - x['close']); won = np.where(buy_yes, x['won'], 1 - x['won'])
                return roi_yes(p, won), won, p
            rt, wt, _ = strat(gg[~gg['hold']]); rh, wh, ph = strat(gg[gg['hold']])
            # z: compare realised wins to implied (sum p) on holdout
            zz = (wh.sum() - ph.sum()) / math.sqrt((ph * (1 - ph)).sum()) if len(ph) else 0
            P(f"| {v} | {sp} | {lines_lab} | {w} | {len(gg)} | {fmt_roi(rt.mean()) if len(rt) else 'n/a'} / {wt.mean():.3f} | {fmt_roi(rh.mean()) if len(rh) else 'n/a'} / {wh.mean() if len(wh) else float('nan'):.3f} ({len(rh)}) | {zz:+.2f} |")

    # T4 big trades
    P("\n## 5. Big trades: is the largest pre-kickoff trade informed?\n")
    P("The single largest trade in the market (top of the top-5% by size). Direction = side the taker bought. 'Continued' = the close moved further in that direction; "
      "ROI = buying that side at the big trade's own price and holding to settlement.\n")
    P("| venue | sport | n | median big trade $ | continued to close | ROI at trade price train / hold (n) | win% hold |\n|---|---|---|---|---|---|---|")
    for (v, sp), g in df.groupby(['venue', 'sport']):
        g = g[g['big_last_dir'] != 0]
        if len(g) < 60: continue
        d = g['big_last_dir']; cont_ = ((g['close'] - g['big_last_p']) * d > 0.005).mean()
        p = np.where(d > 0, g['big_last_p'], 1 - g['big_last_p']); won = np.where(d > 0, g['won'], 1 - g['won'])
        r = roi_yes(p, won); tr = ~g['hold'].values; ho = g['hold'].values
        bigusd = (g['big_usd'] / np.maximum(1, g['n_trades'] // 20)).median()
        P(f"| {v} | {sp} | {len(g)} | ${bigusd:,.0f} | {cont_:.1%} | {fmt_roi(r[tr].mean())} / {fmt_roi(r[ho].mean()) if ho.sum() else 'n/a'} ({ho.sum()}) | {won[ho].mean() if ho.sum() else float('nan'):.3f} |")

    # T5 lead/lag
    P("\n## 6. Who moves first: Kalshi vs Novig on the same market\n")
    P("Hourly two-sided mids (taker spread <= 4c) on markets both exchanges list (same game, market, side, line). Corr(dK_t, dN_t-1) > Corr(dN_t, dK_t-1) means Novig leads. "
      "Strategy 'follow the leader': when one venue moved >= 3c in hour t and the other moved < 1c, buy the laggard toward the leader's direction at the laggard's price; "
      "graded against the laggard's own close (CLV, in cents) and against the result.\n")
    both = hh.groupby('key')['venue'].nunique(); keys = both[both == 2].index
    hb = hh[hh['key'].isin(keys)].pivot_table(index=['key', 'h'], columns='venue', values='p').dropna().reset_index().sort_values(['key', 'h'])
    if len(hb) > 200:
        hb['dK'] = hb.groupby('key')['Kalshi'].diff(); hb['dN'] = hb.groupby('key')['Novig'].diff()
        hb['dK_prev'] = hb.groupby('key')['dK'].shift(1); hb['dN_prev'] = hb.groupby('key')['dN'].shift(1)
        hb['sport'] = hb['key'].str.split('|').str[0]
        P("| sport | matched markets | hour-pairs | corr(dK_t, dN_t-1) | corr(dN_t, dK_t-1) | same-hour corr | leader |\n|---|---|---|---|---|---|---|")
        for sp, g in hb.groupby('sport'):
            gg = g.dropna(subset=['dK', 'dN', 'dK_prev', 'dN_prev'])
            if len(gg) < 100: continue
            c1 = gg['dK'].corr(gg['dN_prev']); c2 = gg['dN'].corr(gg['dK_prev']); c0 = gg['dK'].corr(gg['dN'])
            P(f"| {sp} | {g['key'].nunique()} | {len(gg)} | {c1:+.3f} | {c2:+.3f} | {c0:+.3f} | {'Novig leads' if c1 > c2 + 0.03 else 'Kalshi leads' if c2 > c1 + 0.03 else 'no clear leader'} |")
        # follow-the-leader strategy
        close = df.set_index(['venue', 'key'])[['close', 'won']]
        P("\nFollow the leader (laggard priced at its own next hourly print, graded vs laggard close and result):\n")
        P("| leader -> laggard | n | avg CLV (cents, holdout-free: all) | CLV>0 share | ROI at laggard price | win% |\n|---|---|---|---|---|---|")
        for lead, lag in (('Novig', 'Kalshi'), ('Kalshi', 'Novig')):
            dl, dg = ('dN', 'dK') if lead == 'Novig' else ('dK', 'dN')
            s = hb[(hb[dl].abs() >= 0.03) & (hb[dg].abs() < 0.01)].copy()
            rows_ = []
            for _, r in s.iterrows():
                try: c = close.loc[(lag, r['key'])]
                except KeyError: continue
                direction = 1 if r[dl] > 0 else -1; p_lag = r[lag]
                p = p_lag if direction > 0 else 1 - p_lag; clv = (c['close'] - p_lag) * direction; won = c['won'] if direction > 0 else 1 - c['won']
                rows_.append((clv, roi_yes(np.array([p]), np.array([won]))[0], won))
            if len(rows_) < 30: P(f"| {lead} -> {lag} | {len(rows_)} | n/a | | | |"); continue
            a = np.array(rows_)
            P(f"| {lead} -> {lag} | {len(a)} | {100 * a[:, 0].mean():+.2f} | {(a[:, 0] > 0).mean():.1%} | {fmt_roi(a[:, 1].mean())} | {a[:, 2].mean():.3f} |")
    else:
        P("Not enough overlapping markets yet (Kalshi pull still running or sports not yet aligned).")

    # T6 timing
    P("\n## 7. Timing: which hours' moves stick?\n")
    P("For every hourly move of >= 2c in the two-sided mid, did the close end up on the same side of the post-move price (the move 'stuck') or come back? "
      "By ET hour of day (moves at least 6h before kickoff only, so the clock is not just distance to kickoff) and by hours-to-kickoff. "
      "Sharp moves should stick; public moves should mean-revert. Share > 50% with n in the hundreds is a real timing signal.\n")
    hh2 = hh.merge(df[['venue', 'market', 'start', 'close', 'sport']], on=['venue', 'market'], how='inner').sort_values(['venue', 'market', 'h'])
    hh2['dp'] = hh2.groupby(['venue', 'market'])['p'].diff()
    hh2 = hh2[hh2['dp'].abs() >= 0.02].copy()
    hh2['stuck'] = (hh2['close'] - hh2['p']) * np.sign(hh2['dp']) >= 0
    hh2['t'] = hh2['start'] + (hh2['h'] + 1) * 3600
    hh2['et_hour'] = ((hh2['t'] - 4 * 3600) % 86400 // 3600).astype(int)
    hh2['ttk'] = (-hh2['h'] - 1)
    P("| venue | ET hour bucket | n moves | stuck share | avg |move| c |\n|---|---|---|---|---|")
    for v, g in hh2[hh2['ttk'] >= 6].groupby('venue'):
        b = pd.cut(g['et_hour'], [-1, 5, 9, 13, 17, 21, 24], labels=['0-5am', '6-9am', '10am-1pm', '2-5pm', '6-9pm', '10pm-12'])
        for k, gg in g.groupby(b, observed=True):
            if len(gg) < 80: continue
            P(f"| {v} | {k} | {len(gg)} | {gg['stuck'].mean():.1%} | {100 * gg['dp'].abs().mean():.1f} |")
    P("\n| venue | hours to kickoff | n moves | stuck share |\n|---|---|---|---|")
    for v, g in hh2.groupby('venue'):
        b = pd.cut(g['ttk'], [-1, 1, 3, 6, 12, 24, 72, 10000], labels=['<1h', '1-3h', '3-6h', '6-12h', '12-24h', '1-3d', '3d+'])
        for k, gg in g.groupby(b, observed=True):
            if len(gg) < 80: continue
            P(f"| {v} | {k} | {len(gg)} | {gg['stuck'].mean():.1%} |")

    # T8 volume conditioning
    P("\n## 8. Does volume make the close sharper?\n")
    P("| venue | sport | volume tercile | n | Brier close | ROI buying favorite at close |\n|---|---|---|---|---|---|")
    for (v, sp), g in df[df['main']].groupby(['venue', 'sport']):
        if len(g) < 90: continue
        q = pd.qcut(g['usd'].rank(method='first'), 3, labels=['low', 'mid', 'high'])
        for k, gg in g.groupby(q, observed=True):
            fav = gg['close'] >= 0.5; p = np.where(fav, gg['close'], 1 - gg['close']); won = np.where(fav, gg['won'], 1 - gg['won'])
            P(f"| {v} | {sp} | {k} (median ${gg['usd'].median():,.0f}) | {len(gg)} | {brier(gg['close'].values, gg['won'].values):.4f} | {fmt_roi(roi_yes(p, won).mean())} |")

    P("\n## 9. Longshot bias on the exchanges (the one structural effect that is everywhere)\n")
    P("Main lines, close price. z = (wins - sum of implied) / sqrt(sum p(1-p)). Negative gap = yes won less often than its price said.\n")
    P("| venue | price band | n | implied avg | hit rate | gap | z | ROI buying yes at close | ROI buying the other side |\n|---|---|---|---|---|---|---|---|---|")
    for v, g in dm.groupby('venue'):
        for lo, hi in ((0.0, 0.2), (0.2, 0.35), (0.35, 0.5), (0.5, 0.65), (0.65, 0.8), (0.8, 1.0)):
            gg = g[(g['close'] >= lo) & (g['close'] < hi)]
            if len(gg) < 40: continue
            p = gg['close'].values; y = gg['won'].values; zz = (y.sum() - p.sum()) / math.sqrt((p * (1 - p)).sum())
            P(f"| {v} | {lo:.2f}-{hi:.2f} | {len(gg)} | {p.mean():.3f} | {y.mean():.3f} | {y.mean() - p.mean():+.3f} | {zz:+.2f} | {fmt_roi(roi_yes(p, y).mean())} | {fmt_roi(roi_yes(1 - p, 1 - y).mean())} |")
    P("\n## 10. Reading it\n")
    P("""A signal survives only if (a) the holdout ROI is positive and the holdout z is above about 2, (b) train and holdout agree in sign, and (c) the effect is monotone where it should be
(bigger flow / bigger move / bigger trade = bigger edge). Verdicts on this run (first full pull, 2026-10-29; re-run weekly as the tape grows):

**Passes now**
- Longshot bias on Novig, 20-35c band (section 9): yes outcomes priced 0.30 won 22% (n=196, z -2.5); the other side of those markets returned +12% at the close. On Novig the yes side is the home side, so this is specifically home dogs priced 20-35c being too expensive, with away favourites at 65-80c too cheap. Kalshi shows the same shape, weaker (35-50c band -3 pts, z -1.8; sub-20c -3.9 pts). Goes forward as a paper system: buy the away favourite on Novig when the home side is two-sided at 20-35c inside T-1h.

**Promising, below the bar**
- Late taker flow, Kalshi NHL main lines (section 4): follow the 6h flow, train +8.3% / holdout +10.7% (n=550, holdout z 1.3), consistent across windows and across all-lines (+7.6% holdout). Novig MLB mains agree (+4.8% / +9.5%, n=638). Needs a live trade feed to run forward; the Kalshi trades endpoint can be polled per market.
- Momentum continuation, NBA (section 3): the T-6h to close move is continued, not reverted, on both exchanges (Kalshi +19.7% / +22.9%, Novig +23.0% / +24.7%, n 170 and 105; logit coefficient +0.36 and +0.39 per 10c, each about 1.3 se). Same sign, two venues, small n. NFL is the opposite in holdout (-39% Kalshi, -17% Novig), so this is sport-specific if it is anything. Forward paper test on NBA only.
- Largest trade follow, Kalshi NBA (section 5): buy the side of the biggest pre-kickoff trade at its price: train +0.1%, holdout +7.9% (n=467, 61% win). Novig NBA +7.5% holdout but -2.7% train. Not consistent enough yet.
- Novig leads Kalshi in NBA (section 6): corr(dKalshi_t, dNovig_t-1) = +0.15 vs +0.06 the other way; NFL is a wash. Too few clean laggard setups at hourly resolution to grade a strategy; the 20-minute tick log is the right instrument and move_signals.py (M2) is already wired for it.

**Fails**
- Timing of day (section 7): moves 6h+ before kickoff stick 52-63% of the time on both exchanges, with no hour-of-day bucket separating from the rest beyond noise (n in the low hundreds per bucket). Moves inside 3h stick more, which is mostly distance to the close.
- Volume as a quality signal (section 8): higher-volume markets are not better calibrated in any sport; the ROI differences across terciles are noise.
- Structural over/under or favourite/dog drift at T-24h (section 2): nothing consistent across venues or between train and holdout except the longshot effect above. Novig NFL yes (home) sides are -12% to -16% at the close on 450 markets, which is a home bias worth watching (home sides covering 46-49% this season on Novig prices) but is one season of one sport.
- Kalshi fees: every Kalshi number above is before the taker fee (about 1.75c at 50/50). Only the NHL flow result would survive that haircut as written.

Nothing in this document is a bet recommendation on its own; the survivors go into sharp/systems.py as tagged paper tests and are graded forward on the ledger.
""")
    out = os.path.join(ROOT, 'docs', f'exchange_signals_audit_{today}.md')
    open(out, 'w').write('\n'.join(L)); print(f"[exchange_backtest] wrote {out}")
    return out


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'build'
    if cmd == 'build': build()
    elif cmd == 'report': report()
    else: build(); report()
