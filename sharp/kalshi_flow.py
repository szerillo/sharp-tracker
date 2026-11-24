#!/usr/bin/env python3
"""Kalshi late taker flow, NHL (paper lean). From docs/exchange_signals_audit_2026-10-29.md section 4: on Kalshi NHL main lines, when the
signed taker dollars in the last 6 hours before the start are 30%+ of the window's volume (and the window has $500+), the side the takers
bought won at the close: train +8.3% / holdout +10.7% (n 152, z 1.3), the one exchange-flow result that survived the taker fee. Sean 11/5:
build the live version and let it grade forward. Tier P (paper) until it has a forward record.

Reads the Kalshi trade tape data/kalshi/trades5/*.jsonl.gz (loggers/fast.py --trades, every 5 minutes), NHL game markets. For each
upcoming NHL game inside the final 90 minutes: per market (ml, spread, total) the main strike is the most-traded line; flow share =
(taker yes dollars - taker no dollars) / window dollars over the last 6h. Flags |share| >= 0.30 with $500+; the side is the one the takers
bought. Paper log data/kalshi/flow_paper.jsonl (price = last trade on the tape for that side), graded from data/state/hist_schedule.json.
Writes data/state/kalshi_flow.json. Usage: python3 sharp/kalshi_flow.py"""
import os, sys, json, gzip, glob, time, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
TR = os.path.join(ROOT, 'data', 'kalshi', 'trades5'); OUT = os.path.join(ROOT, 'data', 'state', 'kalshi_flow.json')
PAPER = os.path.join(ROOT, 'data', 'kalshi', 'flow_paper.jsonl'); HIST = os.path.join(ROOT, 'data', 'state', 'hist_schedule.json')
SPORT = 'nhl'; WINDOW_H = 6; SHARE = 0.30; MIN_USD = 500.0; FIRE_MIN = 90        # flag inside the last 90 minutes (the backtest bet at the close)
NOW = time.time()


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def _sched():
    out = {}
    for f in (os.path.join(ROOT, 'data', SPORT, 'schedule.json'),):
        try:
            d = json.load(open(f)); out.update(d if isinstance(d, dict) else {str(g.get('event_id') or g.get('id')): g for g in d})
        except Exception: pass
    try:
        for k, v in (json.load(open(HIST)).get(SPORT) or {}).items(): out.setdefault(str(k), v)
    except Exception: pass
    return out
SCH = _sched()


def load_trades(days=2):
    files = sorted(glob.glob(os.path.join(TR, '*.jsonl.gz')))[-days:]
    out = []
    for f in files:
        try:
            for l in gzip.open(f, 'rt'):
                if f'"sport":"{SPORT}"' not in l: continue
                r = json.loads(l)
                if r.get('market') not in ('ml', 'spread', 'total') or not r.get('event_id'): continue
                if not r.get('start'):
                    sch = SCH.get(str(r['event_id'])); r['start'] = (sch or {}).get('start') or (sch or {}).get('start_utc') or (sch or {}).get('date')
                    if not r['start']: continue
                out.append(r)
        except (EOFError, OSError): pass
    return out


def other(side): return {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}.get(side)
def ticker_yes(t, default):
    import re
    m = re.match(r'KXNHL\w+-\d\d[A-Z]{3}\d\d([A-Z]+)-([A-Z]+?)(\d*)$', t or '')
    if not m: return default
    return 'away' if m.group(1).startswith(m.group(2)) else 'home' if m.group(1).endswith(m.group(2)) else default


# 11/24 (Kirk, docs/cancel_and_sharp_signal_2026-11-24.md section 4): the paper price is the last trade on the tape. On 178 rows with a
# quote it matched the executable cost closely (median gap 0, mean +0.2c), but each logged row now also carries the executable Kalshi cost
# at the log time (the ticker's YES ask, or 1 - YES bid for its NO side, from the newest 20-minute tick file) and that cost plus the taker
# fee, so a promotion read can use the price that could actually be bought.
_QUOTES = {}
def kalshi_quote(ticker):
    if not _QUOTES:
        fs = sorted(glob.glob(os.path.join(ROOT, 'data', SPORT, 'ticks', '*.jsonl.gz')))[-1:]
        for f in fs:
            try:
                for l in gzip.open(f, 'rt'):
                    if '"Kalshi"' not in l: continue
                    r = json.loads(l); t = (r.get('extra') or {}).get('ticker')
                    if t and (r.get('extra') or {}).get('yes') == r.get('side') and r.get('bid') is not None and r.get('ask') is not None: _QUOTES[t] = (r['ts'], r['bid'], r['ask'])
            except (EOFError, OSError): pass
        _QUOTES.setdefault('_loaded', None)
    return _QUOTES.get(ticker)


def main():
    T = load_trades(); paper = [json.loads(l) for l in open(PAPER)] if os.path.exists(PAPER) else []
    logged = {(p['event_id'], p['market'], p['line']) for p in paper}
    G = collections.defaultdict(list)
    for r in T: G[(r['event_id'], r['market'], r.get('line'), r['start'])].append(r)
    # main strike per event x market = most traded line (dollars) in the whole tape we hold
    vol = collections.defaultdict(float)
    for k, L in G.items():
        for r in L: vol[k] += r['count'] * (r['yes_price'] if r['taker_side'] == 'yes' else 1 - r['yes_price'])
    main_k = {}
    for k, v in vol.items():
        mk = (k[0], k[1])
        if mk not in main_k or v > vol[main_k[mk]]: main_k[mk] = k
    rows = []
    for mk, k in main_k.items():
        ev, market, line, start = k; st = ts(start.replace('Z', '+00:00') if 'Z' in start else start)
        L = [r for r in G[k] if st - WINDOW_H * 3600 <= ts(r['ts']) < st]
        if not L: continue
        # Kalshi lists two tickers per game market (one per team); a taker buying YES on the -NYI ticker and a taker buying NO on the -CAR
        # ticker are both money on the Islanders. Reduce every trade to dollars on a side (home/away, over/under).
        ref = 'over' if market == 'total' else 'home'; usd = {ref: 0.0, other(ref): 0.0}
        for r in L:
            ys = r.get('yes_side') or ref; bought = ys if r['taker_side'] == 'yes' else other(ys); cost = r['yes_price'] if r['taker_side'] == 'yes' else 1 - r['yes_price']
            if bought in usd: usd[bought] += r['count'] * cost
        tot = usd[ref] + usd[other(ref)]
        if tot <= 0: continue
        share = (usd[ref] - usd[other(ref)]) / tot; yes_side = ref
        side = ref if share > 0 else other(ref); last = sorted(L, key=lambda r: r['ts'])[-1]
        p_side = last['yes_price'] if (last.get('yes_side') or ref) == side else 1 - last['yes_price']
        mins = (st - NOW) / 60
        flag = abs(share) >= SHARE and tot >= MIN_USD and 0 < mins <= FIRE_MIN
        sch = SCH.get(str(ev)) or {}; nm = lambda k: ((sch.get(k + '_team') or {}).get('displayName')) or sch.get(k) or k
        bet = (nm(side) + (' moneyline' if market == 'ml' else f" {line:+g}" if line is not None else '')) if market != 'total' else f"{side.capitalize()} {line}"
        row = dict(event_id=ev, market=market, line=line, start=start, side=side, yes_side=yes_side, home=nm('home'), away=nm('away'), game=f"{nm('away')} @ {nm('home')}", bet=bet, share=round(share, 3), usd=round(tot), trades=len(L), price=round(p_side, 3),
                   mins_to_start=round(mins), flag=flag, ticker=last['ticker'], window_h=WINDOW_H)
        rows.append(row)
        if flag and (ev, market, line) not in logged:
            q = kalshi_quote(row['ticker']); ex = {}
            if q:
                c_ = q[2] if side == ticker_yes(row['ticker'], last.get('yes_side') or ref) else round(1 - q[1], 4)   # the ticker's own YES side
                ex = dict(ask=c_, ask_fee=round(c_ + 0.07 * c_ * (1 - c_), 4), quote_ts=q[0])
            paper.append(dict(row, rule='kalshi_nhl_flow', logged=dt.datetime.fromtimestamp(NOW, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), venue='Kalshi', **ex)); logged.add((ev, market, line))
    # grade from the ESPN schedule (hist_schedule.json carries finals with scores)
    H = (json.load(open(HIST)) if os.path.exists(HIST) else {}).get(SPORT, {})
    for p in paper:
        # 11/24: spread rows are re-graded every run (the 11/24 fix below changed 10 of them); everything else grades once
        if p.get('won') is not None and p['market'] != 'spread': continue
        h = H.get(str(p['event_id']))
        if not h or not h.get('final') or h.get('hs') is None: continue
        hs, as_ = h['hs'], h['as_']; m, ln, sd = p['market'], p.get('line'), p['side']
        if m == 'ml': won = 1 if (hs > as_) == (sd == 'home') else 0
        elif m == 'spread':
            # the tape line is the handicap of the TICKER's YES team (Kalshi puck lines sit at +-1.5); the no side gets the mirror.
            # 11/24 fix: the YES team comes from the ticker (KXNHLSPREAD-26NOV14WPGCHI-WPG2: away WPG -1.5), not the stored yes_side, which
            # is always 'home'; tickers whose YES team was the visitor were graded as if the line were the home team's (10 rows wrong).
            hc = (ln if ln is not None else 0) * (1 if sd == ticker_yes(p.get('ticker'), p.get('yes_side') or sd) else -1)
            mg = (hs - as_ if sd == 'home' else as_ - hs) + hc
            won = 1 if mg > 0 else 0 if mg < 0 else 0.5
        else:
            t = hs + as_; won = 0.5 if t == ln else (1 if (t > ln) == (sd == 'over') else 0)
        p['won'] = won; p['final'] = f"{int(as_)}-{int(hs)}"
        p['units'] = round(0 if won == 0.5 else (0.25 * (1 - p['price']) / p['price'] if won == 1 else -0.25), 3)   # 0.25u to risk at the tape price, before the Kalshi fee
    os.makedirs(os.path.dirname(PAPER), exist_ok=True)
    with open(PAPER, 'w') as f:
        for p in paper: f.write(json.dumps(p) + '\n')
    G_ = [p for p in paper if p.get('won') is not None]
    rec = dict(n=len(G_), won=sum(1 for p in G_ if p['won'] == 1), units=round(sum(p['units'] for p in G_), 2))
    rows.sort(key=lambda r: (not r['flag'], r['start']))
    json.dump(dict(built=dt.datetime.fromtimestamp(NOW, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), sport=SPORT, rule='kalshi_nhl_flow', tier='P', share=SHARE, min_usd=MIN_USD,
                   window_h=WINDOW_H, fire_min=FIRE_MIN, rows=[r for r in rows if ts(r['start']) > NOW - 3 * 3600], record=rec, n_flagged=sum(1 for r in rows if r['flag'])), open(OUT, 'w'), indent=0)
    print(f"[kalshi_flow] {len(rows)} NHL main markets with 6h tape, {sum(1 for r in rows if r['flag'])} flagged, paper {rec}")


if __name__ == '__main__':
    main()
