#!/usr/bin/env python3
"""Polymarket sharp accounts, checks 1 and 2 (Sean, 11/2: "test 1+2"). Round 3 (docs/flow_volume_2026-11-02.md) found that accounts
which beat Polymarket's close before September keep beating it after. Two checks before it becomes a signal:

1. Pinnacle: is the edge real, or is it the account's own follow-up orders pushing Polymarket's price? Grade the follower's entry
   against Pinnacle's no-vig close on the same side (moneylines and totals; spreads skipped because the catalog does not say which team
   a Polymarket spread line belongs to). Pinnacle game lines for these sports are only on the tape from 2026-10-29.
2. Kalshi: when a sharp account's bet agrees with a Kalshi 4+ point move (since Kalshi's first two-sided price, as of the follower's
   entry), is it stronger than either alone? Moneylines, NFL / NBA / NHL / CFB / MLB, Kalshi trade history (data/kalshi/history).

Same split and scoring as round 3 (sharp/flow_volume.py): accounts scored on markets that started before 2026-09-01 (mean CLV vs
Polymarket's close of their $100+ pregame fills, 30+ fills on 15+ games); followed after, entering at the two-sided mid 1 or 5
minutes after an account's first $100+ fill on the market. Groups: top 200, the rest of the scored accounts, bottom 200.
Writes data/research/sharp_accounts.json and data/research/poly_wallet_scores.json (the scored list, for the live signal).
Usage: python3 sharp/sharp_accounts.py"""
import os, sys, json, gzip, glob, math, sqlite3, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.exchange_backtest as EB
import sharp.flow_volume as V
from sharp import sports as SP
ZET = __import__('zoneinfo').ZoneInfo('America/New_York')
LAGS = (60, 300); KSPORT = {'nfl': 'KXNFLGAME', 'nba': 'KXNBAGAME', 'nhl': 'KXNHLGAME', 'cfb': 'KXNCAAFGAME', 'mlb': 'KXMLBGAME'}
PIN_FROM = '2026-10-29'


def stat(R, key):
    x = [r[key] for r in R if r.get(key) is not None]
    if not x: return None
    mu = sum(x) / len(x); sd = (sum((v - mu) ** 2 for v in x) / max(1, len(x) - 1)) ** 0.5
    return dict(n=len(x), mean=round(mu * (100 if key == 'roi' else 1), 2), z=round(mu / (sd / math.sqrt(len(x))), 2) if sd and len(x) > 1 else None)


def follows():
    MK = V.poly_markets(); cut_t = MK[int(len(MK) * 2 / 3)][1]
    W = collections.defaultdict(lambda: [0.0, 0, set()]); scored = None; out = []
    for i, (c, st) in enumerate(MK):
        L = V.poly_trades(c, st)
        if not L: continue
        L4 = [x[:4] for x in L]; cl, two = EB.px_at(L4, st); gk = f"{c['event']}|{c['market']}"
        if st < cut_t:
            if cl is None or two != 2: continue
            for t, py, usd, d, w in L:
                if usd < 100 or not w: continue
                x = W[w]; x[0] += 100 * ((cl if d > 0 else 1 - cl) - (py if d > 0 else 1 - py)); x[1] += 1; x[2].add(gk)
            continue
        if scored is None: scored = {w for w, x in W.items() if x[1] >= 30 and len(x[2]) >= 15}
        firsts = {}
        for t, py, usd, d, w in L:
            if usd >= 100 and w in scored and w not in firsts: firsts[w] = (t, d)
        ry = 1 if c['winner'] == c['outcomes'][0] else 0
        for w, (t, d) in firsts.items():
            pr = {}
            for lag in LAGS:
                if t + lag >= st: continue
                px, tw = EB.px_at([x for x in L4 if x[0] <= t + lag], t + lag)
                if px is not None and tw == 2 and 0.05 < (px if d > 0 else 1 - px) < 0.95: pr[lag] = px if d > 0 else 1 - px
            if pr: out.append(dict(w=w, cond=c['cond'], event=c['event'], tag=c['tag'], market=c['market'], line=c.get('line'), outcomes=c['outcomes'],
                                   d=d, t=t, start=st, price=pr, poly_close=None if two != 2 else (cl if d > 0 else 1 - cl), won=ry if d > 0 else 1 - ry))
        if i % 3000 == 0: print(f"[sharp_accounts] {i}/{len(MK)} markets", flush=True)
    score = {w: (x[0] / x[1], x[1], len(x[2])) for w, x in W.items() if x[1] >= 30 and len(x[2]) >= 15}
    return out, score, cut_t


def match_game(F, sched_by, codes_by):
    """Polymarket event slug league-away-home-date -> hist_schedule game (ESPN codes), by ET date +-1 and code match."""
    _, a, h, day = F['event'].split('-', 3)[0], *F['event'].split('-')[1:3], F['event'][-10:]
    sp = F['tag']; c = sched_by.get(sp)
    if not c: return None
    def fit(x, code): x, code = x.upper(), code.upper(); return x == code or code.startswith(x) or x.startswith(code)
    d0 = dt.date.fromisoformat(day); hits = []
    for k in (0, -1, 1):
        for eid, g in c.get(d0 + dt.timedelta(days=k), []):
            if fit(a, g['away']) and fit(h, g['home']): hits.append((eid, g))
        if hits: break
    if not hits:                                     # CFB codes differ a lot (oregst vs ORST): same kickoff minute and the same first letter for both teams
        st = F.get('start') if isinstance(F.get('start'), (int, float)) else (dt.datetime.fromisoformat(F['start'].replace(' ', 'T').replace('+00', '+00:00')).timestamp() if F.get('start') else None)
        for k in (0, -1, 1):
            for eid, g in c.get(d0 + dt.timedelta(days=k), []):
                if st and abs(EB.ts(g['start']) - st) < 60 and a[:1].upper() == g['away'][:1] and h[:1].upper() == g['home'][:1]: hits.append((eid, g))
    return hits[0] if len(hits) == 1 else None


def main():
    F, score, cut_t = follows()
    ranked = sorted(score, key=lambda w: -score[w][0]); top = set(ranked[:200]); bot = set(ranked[-200:])
    grp = lambda w: 'top200' if w in top else ('bottom200' if w in bot else 'rest')
    json.dump(dict(train_cut=dt.datetime.fromtimestamp(cut_t, dt.timezone.utc).strftime('%Y-%m-%d'), n=len(score),
                   wallets=[dict(w=w, clv=round(score[w][0], 2), fills=score[w][1], games=score[w][2]) for w in ranked]),
              open(os.path.join(ROOT, 'data', 'research', 'poly_wallet_scores.json'), 'w'))
    # first follow per group x market (the earliest qualifying account in that group)
    first = {}
    for f in sorted(F, key=lambda f: f['t']):
        k = (grp(f['w']), f['cond'])
        if k not in first: first[k] = f
    print(f"[sharp_accounts] {len(F)} account follows on holdout markets; {len(first)} group x market firsts")
    # ---- schedule (ESPN codes, results)
    HS = json.load(open(os.path.join(ROOT, 'data', 'state', 'hist_schedule.json')))
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'soccer'):                 # recent games (schedule.json) for the Pinnacle window
        p = os.path.join(ROOT, 'data', sp, 'schedule.json')
        if os.path.exists(p):
            for eid, g in json.load(open(p)).items():
                tags = [sp] if sp != 'soccer' else ['epl', 'ucl', 'mls', 'bundesliga']
                for tg in tags: HS.setdefault(tg, {}).setdefault(eid, dict(start=g['start'], away=g['away'], home=g['home']))
    sched_by = {}
    for sp, games in HS.items():
        d = collections.defaultdict(list)
        for eid, g in games.items():
            d[EB.dt.datetime.fromtimestamp(EB.ts(g['start']), dt.timezone.utc).astimezone(ZET).date()].append((eid, g))
        sched_by[sp] = d
    # ---- 1. Pinnacle close (ml, total), games from PIN_FROM
    conn = sqlite3.connect(os.environ.get('SHARP_DB') or '/tmp/claude-0/mini.sqlite')
    from sharp import fair as FR, constants as C
    eqc = {}; pin = collections.defaultdict(list); nm = collections.Counter()
    for (g_, cond), f in first.items():
        if f['market'] not in ('ml', 'total') or dt.datetime.fromtimestamp(f['start'], dt.timezone.utc).strftime('%Y-%m-%d') < PIN_FROM: continue
        nm['in window'] += 1
        m = match_game(f, sched_by, None)
        if not m: nm['no game match'] += 1; continue
        eid, g = m
        if eid not in eqc: eqc[eid] = FR.EventQuotes(conn, eid)
        eq = eqc[eid]
        if not eq.event: nm['no Pinnacle'] += 1; continue
        o = f['outcomes'][0] if f['d'] > 0 else f['outcomes'][1]
        if f['market'] == 'total':
            side = o.lower(); line = f['line']; part = None
            if side not in ('over', 'under') or line is None: nm['bad total'] += 1; continue
        else:
            side = 'away' if f['d'] > 0 else 'home'; line = None; part = eq.event[3] if side == 'away' else eq.event[4]   # outcomes read away, home
        sport = eq.sport; meth = 'power'
        start = dt.datetime.fromtimestamp(f['start'], dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        pc = eq.venue_prob('Pinnacle', f['market'], line, side, start, meth, part, max_age=240)[0]
        if pc is None: nm['no Pinnacle quote'] += 1; continue
        nm['graded'] += 1
        for lag, price in f['price'].items():
            pin[(g_, lag)].append(dict(pin_clv=100 * (pc - price), poly_clv=None if f['poly_close'] is None else 100 * (f['poly_close'] - price),
                                       roi=(1 - price) / price if f['won'] else -1.0, sport=f['tag'], market=f['market']))
    res = dict(pinnacle=dict(match=dict(nm), cells={}), kalshi={})
    for (g_, lag), R in sorted(pin.items()):
        res['pinnacle']['cells'][f'{g_}_lag{lag // 60}m'] = dict(pin_clv=stat(R, 'pin_clv'), poly_clv=stat(R, 'poly_clv'), roi=stat(R, 'roi'))
    # ---- 2. Kalshi 4+ move agreement (ml), from Kalshi trade history
    mk = {}
    for l in open(os.path.join(ROOT, 'data', 'kalshi', 'history', 'markets.jsonl')):
        r = json.loads(l); mk[r['ticker']] = r
    sch = EB.Sched(); K = {}                                          # (sport, eid) -> {'home': trades yes=home}
    hs_ids = {sp: {(g['start'], g['away'], g['home']): eid for eid, g in games.items()} for sp, games in sch.h.items()}
    for sp, series in KSPORT.items():
        f_ = os.path.join(ROOT, 'data', 'kalshi', 'history', 'trades', f'{series}.jsonl.gz')
        if not os.path.exists(f_): continue
        by = collections.defaultdict(list)
        for l in gzip.open(f_, 'rt'):
            r = json.loads(l)
            if r['ts'] < '2026-08-25': continue
            by[r['ticker']].append((EB.ts(r['ts']), r['yes'], r['n'] * min(r['yes'], 1 - r['yes']), 1 if r['taker'] == 'yes' else -1))
        for tk, L in by.items():
            m = mk.get(tk)
            if not m or tk.endswith('-TIE'): continue
            pe = SP.kalshi_event(m['event_ticker'].split('-', 1)[1])
            if not pe: continue
            g = sch.kalshi(sp, pe[0], pe[1])
            if not g: continue
            eid = hs_ids[sp].get((g['start'], g['away'], g['home']))
            team = tk.rsplit('-', 1)[1]; fix = {**SP.CODE_FIX.get(sp, {}), **(EB.MLB_FIX if sp == 'mlb' else {})}; team = fix.get(team, team)
            side = 'home' if team == g['home'] else ('away' if team == g['away'] else None)
            if not side or not eid: continue
            if side == 'home': K[(sp, eid)] = sorted(L)
            elif (sp, eid) not in K: K[(sp, eid)] = sorted((t, 1 - p, u, -d) for t, p, u, d in L)
    kal = collections.defaultdict(list); km = collections.Counter()
    for (g_, cond), f in first.items():
        if f['market'] != 'ml' or f['tag'] not in KSPORT: continue
        m = match_game(f, sched_by, None)
        if not m: km['no game match'] += 1; continue
        eid, g = m; L = K.get((f['tag'], eid))
        if not L: km['no Kalshi'] += 1; continue
        side_home = f['d'] < 0                                              # outcomes read away, home: d>0 = away
        for lag, price in f['price'].items():
            E = f['t'] + lag; pre = [x for x in L if x[0] <= E]
            p0 = None
            for j in range(len(pre)):                                       # first two-sided price
                q, two = EB.px_at(pre[:j + 1], pre[j][0])
                if two == 2: p0 = q; break
            pe_, two_e = EB.px_at(pre, E) if pre else (None, None)
            if p0 is None or pe_ is None or two_e != 2: km['no Kalshi two-sided'] += 1; continue
            mv = 100 * (pe_ - p0) * (1 if side_home else -1)              # toward the followed side
            cls = 'kalshi agrees (4+)' if mv >= 4 else ('kalshi against (4+)' if mv <= -4 else 'kalshi under 4')
            kal[(g_, lag, cls)].append(dict(poly_clv=None if f['poly_close'] is None else 100 * (f['poly_close'] - price), roi=(1 - price) / price if f['won'] else -1.0))
            km['graded'] += 1
    res['kalshi']['match'] = dict(km)
    for (g_, lag, cls), R in sorted(kal.items()):
        res['kalshi'][f'{g_}_lag{lag // 60}m | {cls}'] = dict(poly_clv=stat(R, 'poly_clv'), roi=stat(R, 'roi'))
    json.dump(res, open(os.path.join(ROOT, 'data', 'research', 'sharp_accounts.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
