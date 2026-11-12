#!/usr/bin/env python3
"""Paper Novig quoter (Sean 11/12; plan in docs/novig_quoter_plan.md, pass bar in docs/novig_quoter_prereg.md). No orders: every quote
and fill here is hypothetical, replayed against Novig's public trade file.

Rules (fixed for the pre-registered test; change them only with a dated note in the prereg doc):
- Window: the last hour before the start, until 5 minutes before it.
- Fair: Pinnacle no-vig, both sides at the same number, both quotes from one pull (within 60 s) and no older than 10 minutes (our tape
  is 5 and 20 minutes; a live quoter would read Pinnacle in seconds).
- Quote: buy the side at 1c under fair, rounded down to Novig's half cent, $100 at risk, posted 5 s after the reading (latency).
- On each new Pinnacle reading: game spreads are pulled on ANY move; other markets reprice on a 0.5c move and are pulled on a 1c move.
  After a pull the quote comes back only at the next reading that has not moved (for spreads: unchanged).
- A quote is cancelled when no fresh reading arrives within 10 minutes, and at the 5-minute mark.
- After a fill: 2 minutes out, then a new $100 quote.
- Caps (applied in time order across all markets): $300 filled per game, $2,500 filled and unsettled at once.
- Fills come only from real Novig maker trades on the same outcome while our quote is live:
    trade-through: a maker bought our outcome at a price below ours (our better bid would have been hit first) -> fill;
    touch: a maker bought at exactly our price -> fill only if our bid was above Novig's best bid when posted (first in line);
    size = the smaller of our remaining size and the trade's size.
- Graded: edge at fill (the quote's fair), +5 minutes, +30 minutes and the close (Pinnacle no-vig at the start), in cents per contract;
  settled result from the Novig catalog when it has one.

Usage: python3 sharp/novig_paper_quoter.py FIRST LAST [--daily]
  FIRST..LAST are game-start dates (UTC). Trade files FIRST-1 .. LAST+1 are read.
  Writes data/research/novig_paper_quoter_<FIRST>_<LAST>.json (replay) or, with --daily, appends to data/state/novig_quoter_fills.jsonl,
  data/novig/quoter/<day>.jsonl.gz (every quote) and rebuilds data/state/novig_quoter_record.json.
Runs on a GitHub runner (data.novig.com is reachable only there)."""
import os, sys, csv, json, gzip, glob, math, bisect, time, collections, datetime as dt, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
import maker_test as M
from novig_maker_history import fetch_to, BASE

WINDOW, STOP, AGE, PULL, LAT, PAUSE = 3600, 300, 600, 60, 5, 120
SIZE_USD, GAME_CAP, TOTAL_CAP, GAP = 100.0, 300.0, 2500.0, 0.01
REPRICE, PULLMOVE = 0.005, 0.01
SPORTS = ['nba', 'nfl', 'nhl', 'cfb', 'cbb', 'mma', 'soccer']
THREE = ('1h_ml', '1q_ml', '1p_ml')
HEADLINE = ('game spread', 'game total', 'team totals', 'period lines', 'game ml')      # plan v1: props reported, not in the headline
FILLS = os.path.join(ROOT, 'data', 'state', 'novig_quoter_fills.jsonl'); REC = os.path.join(ROOT, 'data', 'state', 'novig_quoter_record.json')
QDIR = os.path.join(ROOT, 'data', 'novig', 'quoter')
LIVE_FROM = '2026-11-13'        # first game day of the pre-registered live paper period (docs/novig_quoter_prereg.md)
UNCAPPED = []                   # replay only: the fills before the caps, for the uncapped summary


def tot(m): return 'total' in m or m.startswith('prop_') or 'tt_' in m
def grp(m): return 'player props' if m.startswith('prop_') else 'team totals' if 'tt_' in m else 'period lines' if m[:3] in ('1h_', '1q_', '1p_') else 'game ' + m
def iso(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def load_tape(d0, d1):
    """Pinnacle series and Novig best bids per key, Novig ids per key, start times; only games starting in [d0, d1]."""
    lo = dt.datetime.fromisoformat(d0 + 'T00:00:00+00:00').timestamp(); hi = dt.datetime.fromisoformat(d1 + 'T00:00:00+00:00').timestamp() + 86400
    start = {}; pin = collections.defaultdict(lambda: ([], [])); nvb = collections.defaultdict(lambda: ([], [])); K2NV = {}; KSP = {}
    days = set()
    x = dt.date.fromisoformat(d0) - dt.timedelta(days=2)
    while x <= dt.date.fromisoformat(d1) + dt.timedelta(days=1): days.add(x.isoformat()); x += dt.timedelta(days=1)
    for sp in SPORTS:
        p = os.path.join(ROOT, 'data', sp, 'schedule.json')
        if not os.path.exists(p): continue
        d = json.load(open(p)); ev = d if isinstance(d, list) else (d.get('events') if isinstance(d.get('events'), list) else list(d.values()))
        for e in ev:
            if isinstance(e, dict) and e.get('event_id') and e.get('start'):
                try: s = M.ts_(e['start'] if len(e['start']) > 17 else e['start'].replace('Z', ':00Z'))
                except Exception: continue
                if lo <= s < hi: start[str(e['event_id'])] = s
        for sub in ('ticks', 'ticks5'):
            for f in sorted(glob.glob(os.path.join(ROOT, 'data', sp, sub, '2026-*.jsonl.gz'))):
                if os.path.basename(f)[:10] not in days: continue
                try:
                    for l in gzip.open(f, 'rt'):
                        isp = '"venue":"Pinnacle"' in l
                        if not isp and '"venue":"Novig"' not in l: continue
                        try: x_ = json.loads(l)
                        except Exception: continue
                        ev_ = str(x_.get('event_id'))
                        if ev_ not in start: continue
                        m = x_.get('market') or ''
                        if m in THREE or (sp == 'soccer' and m == 'ml') or x_.get('side') not in M.OTH: continue
                        k = (ev_, m, x_['side'], x_.get('line'), x_.get('participant') if m.startswith('prop_') else None)
                        t = M.ts_(x_['ts'])
                        if isp:
                            if x_.get('american') is not None: pin[k][0].append(t); pin[k][1].append(M.imp(x_['american']))
                        else:
                            e_ = x_.get('extra') or {}
                            if e_.get('market_id') and e_.get('outcome_id'): K2NV[k] = (e_['market_id'], e_['outcome_id']); KSP[k] = sp
                            if x_.get('bid') is not None: nvb[k][0].append(t); nvb[k][1].append(float(x_['bid']))
                except Exception as ex: print('skip', f, ex, flush=True)
    for D in (pin, nvb):
        for k, (T, P) in D.items():
            o = sorted(range(len(T)), key=T.__getitem__); D[k] = ([T[i] for i in o], [P[i] for i in o])
    return start, pin, nvb, K2NV, KSP


def load_trades(d0, d1, want):
    """Novig STRAIGHT maker trades on the outcomes we quote: (marketId, outcomeId) -> sorted [(t, price, qty)]."""
    out = collections.defaultdict(list); tmp = os.path.join(tempfile.gettempdir(), 'novig_trades.csv'); files = []
    x = dt.date.fromisoformat(d0) - dt.timedelta(days=1)
    while x <= dt.date.fromisoformat(d1) + dt.timedelta(days=1):
        ds = x.isoformat(); x += dt.timedelta(days=1)
        if not fetch_to(f"{BASE}/{ds}/trades.csv", tmp): print(f'{ds}: no trade file', flush=True); continue
        files.append(ds); n = 0
        with open(tmp, newline='') as fh:
            for r in csv.DictReader(fh):
                if r.get('side') != 'MAKER' or r.get('tradeType') != 'STRAIGHT': continue
                key = (r['marketId'], r['outcomeId'])
                if key not in want: continue
                try: qty = float(r['qty']); cost = float(r['cost']); t = M.ts_(r['timestamp'])
                except Exception: continue
                if qty > 0: out[key].append((t, cost / qty, qty)); n += 1
        print(f'{ds}: {n} maker trades on quoted outcomes', flush=True)
    for k in out: out[k].sort()
    return out, files


def last_t(S, k, t, age):
    v = S.get(k)
    if not v: return None
    i = bisect.bisect_right(v[0], t) - 1
    return (v[0][i], v[1][i]) if i >= 0 and t - v[0][i] <= age else None


def other(k):
    ev, m, side, line, pk = k
    return (ev, m, M.OTH[side], line if (line is None or tot(m)) else -line, pk)


def fair_fresh(pin, k, t):
    a = last_t(pin, k, t, AGE); b = last_t(pin, other(k), t, AGE)
    if not (a and b) or abs(a[0] - b[0]) > PULL: return None
    return a[1] / (a[1] + b[1]), max(a[0], b[0])


def fair_loose(pin, k, t, age):
    a = last_t(pin, k, t, age); b = last_t(pin, other(k), t, age)
    return a[1] / (a[1] + b[1]) if a and b else None


def price(f): return math.floor((f - GAP) * 200 + 1e-9) / 200.0


def fair_next(pin, k, t, st, within=900):
    """Fair at the first fresh Pinnacle reading strictly after t (both sides one pull), within 15 minutes and before the start.
    11/12: our tape updates every 5-20 minutes, so a fixed +5 minute mark mostly reuses the fill's own reading; this is the first new
    information after the fill."""
    v = pin.get(k)
    if not v: return None
    i = bisect.bisect_right(v[0], t)
    while i < len(v[0]) and v[0][i] <= min(t + within, st):
        r = fair_fresh(pin, k, v[0][i])
        if r: return r[0]
        i += 1
    return None


def simulate(k, st, pin, nvb, trades):
    """One market side over its last-hour window. Returns (quotes, fills)."""
    g = grp(k[1]); spreadlike = (g == 'game spread')
    t0, t1 = st - WINDOW, st - STOP
    reads = sorted(set(t for kk in (k, other(k)) for t in (pin.get(kk, ([], []))[0]) if t0 - AGE <= t <= t1))
    ev = [(t, 0, None) for t in reads] + [(t, 1, (q, c)) for (t, q, c) in trades if t0 <= t <= t1]
    ev.sort(key=lambda e: (e[0], e[1]))
    quotes, fills = [], []
    q = None; f_cur = None; out_until_stable = False; last_f = None; pause_until = 0.0; last_read = None
    def post(t, f):
        nb = last_t(nvb, k, t, 1800)
        b = price(f)
        if not 0.02 <= b <= 0.98: return None
        return dict(post=t + LAT, b=b, f=f, rem=SIZE_USD / b, first=bool(nb and b > nb[1] + 1e-4), filled=0.0, end=None, why=None)
    def close(t, why):
        nonlocal q
        if q: q['end'] = t; q['why'] = why; quotes.append(q); q = None
    for t, typ, payload in ev:
        if q and last_read is not None and t > last_read + AGE: close(last_read + AGE, 'stale')
        if typ == 0:
            r = fair_fresh(pin, k, t)
            if r is None:
                if q: close(t, 'no fresh fair')
                continue
            f, _ = r; last_read = t
            if t < t0: last_f = f; continue
            moved = None if last_f is None else abs(f - last_f)
            if q:
                d = abs(f - q['f'])
                if (spreadlike and d > 1e-9) or (not spreadlike and d >= PULLMOVE): close(t, 'pulled on move'); out_until_stable = True
                elif not spreadlike and d >= REPRICE: close(t, 'repriced'); q = post(t, f)
            else:
                stable = moved is not None and (moved <= 1e-9 if spreadlike else moved < REPRICE)
                if out_until_stable and not stable: pass
                elif t >= pause_until and t + LAT < t1:
                    out_until_stable = False; q = post(t, f)
            last_f = f
        elif q and t >= q['post']:
            px, c = payload
            through = px < q['b'] - 1e-4; touch = abs(px - q['b']) <= 1e-4 and q['first']      # prices are cost / qty, so a small tolerance
            if not (through or touch): continue
            n = min(q['rem'], c)
            if n <= 0: continue
            q['rem'] -= n; q['filled'] += n
            r_ = fair_fresh(pin, k, t)
            fills.append(dict(t=t, b=q['b'], c=n, f=r_[0] if r_ else q['f'], how='through' if through else 'touch'))
            if q['rem'] <= 1e-9: close(t, 'filled'); pause_until = t + PAUSE
    if q and last_read is not None and last_read + AGE < t1: close(last_read + AGE, 'stale')
    if q: close(t1, 'window end')
    return quotes, fills


def run(d0, d1):
    T0 = time.time()
    start, pin, nvb, K2NV, KSP = load_tape(d0, d1)
    print(f'tape: {len(start)} games, {len(pin)} Pinnacle series, {len(K2NV)} Novig outcomes mapped ({round(time.time() - T0)}s)', flush=True)
    want = {v: k for k, v in K2NV.items()}
    trades, files = load_trades(d0, d1, set(want))
    from novig_catalog import load_catalog
    cat = load_catalog()
    Q, F = [], []
    for k, nv in K2NV.items():
        st = start.get(k[0])
        if st is None or k not in pin or other(k) not in pin: continue
        qs, fs = simulate(k, st, pin, nvb, trades.get(nv, []))
        g = grp(k[1]); sp = KSP[k]
        for x in qs: Q.append(dict(key='|'.join(map(str, k)), sport=sp, group=g, start=iso(st), post=iso(x['post']), end=iso(x['end']), b=x['b'], fair=round(x['f'], 4), first=x['first'], why=x['why'], filled=round(x['filled'], 2)))
        res = ((cat.get(nv[0]) or {}).get('result') or {}).get(nv[1])
        for x in fs:
            f5 = fair_loose(pin, k, x['t'] + 300, 1800) if x['t'] + 300 < st else None
            f30 = fair_loose(pin, k, x['t'] + 1800, 1800) if x['t'] + 1800 < st else None
            fc = fair_loose(pin, k, st, 3600); fn = fair_next(pin, k, x['t'], st)
            F.append(dict(id=f"{'|'.join(map(str, k))}|{round(x['t'])}", key='|'.join(map(str, k)), event=k[0], sport=sp, group=g, market_id=nv[0], outcome_id=nv[1],
                          start=iso(st), t=iso(x['t']), day=iso(st)[:10], b=x['b'], c=round(x['c'], 2), risk=round(x['b'] * x['c'], 2), how=x['how'],
                          e_fill=round(x['f'] - x['b'], 4), e_next=round(fn - x['b'], 4) if fn is not None else None, e5=round(f5 - x['b'], 4) if f5 is not None else None, e30=round(f30 - x['b'], 4) if f30 is not None else None,
                          e_close=round(fc - x['b'], 4) if fc is not None else None, won=(1 if res == 'WIN' else 0 if res == 'LOSS' else None)))
    F.sort(key=lambda r: r['t'])
    global UNCAPPED; UNCAPPED = [dict(r) for r in F]          # before the caps trim anything
    # caps, in time order across all markets
    game = collections.defaultdict(float); openr = []; kept = []; dropped = 0
    for r in F:
        t = M.ts_(r['t']); openr = [(e, a) for e, a in openr if e > t]
        room = min(GAME_CAP - game[r['event']], TOTAL_CAP - sum(a for _, a in openr))
        if room <= 0.01: dropped += 1; continue
        if r['risk'] > room: r['c'] = round(room / r['b'], 2); r['risk'] = round(room, 2); r['capped'] = True
        game[r['event']] += r['risk']; openr.append((M.ts_(r['start']) + 4 * 3600, r['risk'])); kept.append(r)
    print(f'{len(Q)} quotes, {len(F)} fills, {dropped} dropped by the caps ({round(time.time() - T0)}s)', flush=True)
    return Q, kept, dict(games=len(start), series=len(pin), mapped=len(K2NV), trade_files=files, dropped_by_caps=dropped)


def summarize(Q, F, ndays):
    def acc(rows, qrows):
        c = sum(r['c'] for r in rows)
        def w(f):
            xs = [(r[f], r['c']) for r in rows if r.get(f) is not None]; cc = sum(b for _, b in xs)
            return (round(100 * sum(a * b for a, b in xs) / cc, 2), round(cc / c, 2) if c else None) if cc else (None, 0)
        g = collections.defaultdict(lambda: [0.0, 0.0])
        for r in rows:
            if r.get('e_close') is not None: g[r['event']][0] += r['e_close'] * r['c']; g[r['event']][1] += r['c']
        ms = [a / b for a, b in g.values() if b > 0]; z = lo90 = None
        if len(ms) > 5:
            mu = sum(ms) / len(ms); sd = (sum((x - mu) ** 2 for x in ms) / (len(ms) - 1)) ** 0.5
            if sd > 0: se = sd / len(ms) ** 0.5; z = round(mu / se, 2); lo90 = round(100 * (mu - 1.645 * se), 2)
        st = [r for r in rows if r.get('won') is not None]
        pnl = sum((r['won'] - r['b']) * r['c'] for r in st); risk = sum(r['risk'] for r in st)
        exp_close = sum(r['e_close'] * r['c'] for r in rows if r.get('e_close') is not None)
        nq = len(qrows); nqf = sum(1 for x in qrows if x['filled'] > 0)
        sides = {x['key'] for x in qrows}; sides_f = {r['key'] for r in rows}
        return dict(quotes=nq, quotes_filled=nqf, fill_rate=round(nqf / nq, 3) if nq else None,
                    sides_quoted=len(sides), sides_filled=len(sides_f & sides), side_fill_rate=round(len(sides_f & sides) / len(sides), 3) if sides else None,
                    fills=len(rows), contracts=round(c),
                    dollars_filled=round(sum(r['risk'] for r in rows)), avg_fill_usd=round(sum(r['risk'] for r in rows) / len(rows), 2) if rows else None,
                    through_share=round(sum(1 for r in rows if r['how'] == 'through') / len(rows), 2) if rows else None,
                    games=len(g), edge_at_fill=w('e_fill')[0], next_reading=w('e_next')[0], next_reading_share=w('e_next')[1], plus5=w('e5')[0], plus30=w('e30')[0], plus30_share=w('e30')[1], close=w('e_close')[0],
                    close_z_by_game=z, close_lo90=lo90, usd_day_at_close=round(exp_close / max(1, ndays), 2),
                    settled_fills=len(st), settled_pnl=round(pnl, 2), settled_roi=round(100 * pnl / risk, 2) if risk else None,
                    settled_expected=round(sum(r['e_close'] * r['c'] for r in st if r.get('e_close') is not None), 2))
    out = {'all (headline groups)': acc([r for r in F if r['group'] in HEADLINE], [x for x in Q if x['group'] in HEADLINE])}
    for gname in sorted({r['group'] for r in F} | {x['group'] for x in Q}):
        out[gname] = acc([r for r in F if r['group'] == gname], [x for x in Q if x['group'] == gname])
    whys = collections.Counter(x['why'] for x in Q)
    return dict(rows=out, quote_ends=dict(whys), days=ndays)


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    d1 = a[1] if len(a) > 1 else (dt.date.today() - dt.timedelta(days=2)).isoformat(); d0 = a[0] if a else d1
    daily = '--daily' in sys.argv
    Q, F, info = run(d0, d1)
    ndays = (dt.date.fromisoformat(d1) - dt.date.fromisoformat(d0)).days + 1
    if not daily:
        out = dict(first=d0, last=d1, rules=dict(window_s=WINDOW, stop_s=STOP, fair_age_s=AGE, same_pull_s=PULL, latency_s=LAT, pause_s=PAUSE, size_usd=SIZE_USD,
                                                    game_cap=GAME_CAP, total_cap=TOTAL_CAP, gap=GAP, reprice=REPRICE, pull=PULLMOVE, spreads='pulled on any move'),
                   info=info, **summarize(Q, F, ndays), uncapped=summarize(Q, UNCAPPED, ndays)['rows'], sample_fills=F[:50])
        p = os.path.join(ROOT, 'data', 'research', f'novig_paper_quoter_{d0}_{d1}.json'); json.dump(out, open(p, 'w'), indent=0)
        print(json.dumps(out['rows'], indent=0)); return
    # daily live-paper mode: log every quote, append new fills, regrade settled results on all fills, rebuild the record
    os.makedirs(QDIR, exist_ok=True)
    with gzip.open(os.path.join(QDIR, f'{d0}.jsonl.gz' if d0 == d1 else f'{d0}_{d1}.jsonl.gz'), 'wt') as fh:
        for x in Q: fh.write(json.dumps(x, separators=(',', ':')) + '\n')
    old = {}
    if os.path.exists(FILLS):
        for l in open(FILLS):
            try: r = json.loads(l); old[r['id']] = r
            except Exception: pass
    for r in F: old.setdefault(r['id'], r)
    from novig_catalog import load_catalog
    cat = load_catalog()
    for r in old.values():
        if r.get('won') is None:
            res = ((cat.get(r['market_id']) or {}).get('result') or {}).get(r['outcome_id'])
            if res in ('WIN', 'LOSS'): r['won'] = 1 if res == 'WIN' else 0
    with open(FILLS + '.tmp', 'w') as fh:
        for r in sorted(old.values(), key=lambda r: r['t']): fh.write(json.dumps(r, separators=(',', ':')) + '\n')
    os.replace(FILLS + '.tmp', FILLS)
    allF = [r for r in old.values() if r['day'] >= LIVE_FROM]
    allQ = []
    for f in sorted(glob.glob(os.path.join(QDIR, '*.jsonl.gz'))):
        for l in gzip.open(f, 'rt'):
            x = json.loads(l)
            if x['start'][:10] >= LIVE_FROM: allQ.append(x)
    days = sorted({r['day'] for r in allF} | {x['start'][:10] for x in allQ})
    rec = dict(updated=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), live_from=LIVE_FROM, game_days=days, last_run=dict(first=d0, last=d1, **info),
               **summarize(allQ, allF, max(1, len(days))))
    json.dump(rec, open(REC, 'w'), indent=0)
    print(f"[quoter] {d0}..{d1}: {len(Q)} quotes, {len(F)} fills; live record: {rec['rows'].get('all (headline groups)')}")


if __name__ == '__main__': main()
