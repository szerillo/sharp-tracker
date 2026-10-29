#!/usr/bin/env python3
"""Kalshi settled sports markets + their full public trade tape, for the exchange-signal backtests (no key needed).

  data/kalshi/history/markets.jsonl          one row per settled market: ticker, event_ticker, series, result, strike, open/close/expiration, volume
  data/kalshi/history/trades/<series>.jsonl.gz  every trade: ticker, created_time, yes_price, count (contracts, $1 each), taker_side, block flag
  data/kalshi/history/_state.json            tickers whose trades are already on disk (resume)

Usage: python3 loggers/kalshi_history.py [--series KXNFLGAME,KXNBATOTAL] [--max-pages 12]
Paced (~3 req/s, backoff on 429); the raw pull is not committed (gitignored), the derived tables are."""
import os, sys, json, gzip, time, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'data', 'kalshi', 'history')
os.makedirs(os.path.join(OUT, 'trades'), exist_ok=True)
API = 'https://api.elections.kalshi.com/trade-api/v2'
SERIES = (['KXNFLGAME', 'KXNFLSPREAD', 'KXNFLTOTAL', 'KXNFL1H', 'KXNFL1HSPREAD', 'KXNFL1HTOTAL',
           'KXNBAGAME', 'KXNBASPREAD', 'KXNBATOTAL', 'KXNBA1H', 'KXNBA1HSPREAD', 'KXNBA1HTOTAL',
           'KXNHLGAME', 'KXNHLSPREAD', 'KXNHLTOTAL', 'KXNCAAFGAME', 'KXNCAAFSPREAD', 'KXNCAAFTOTAL',
           'KXMLBGAME', 'KXMLBTOTAL', 'KXMLBSPREAD']
          + [f'KX{l}{m}' for l in ('EPL', 'LALIGA', 'BUNDESLIGA', 'SERIEA', 'LIGUE1', 'MLS', 'UCL') for m in ('GAME', 'TOTAL', 'SPREAD')] + ['KXUFCFIGHT'])
ARGS = sys.argv[1:]
if '--series' in ARGS: SERIES = ARGS[ARGS.index('--series') + 1].split(',')
MAX_PAGES = int(ARGS[ARGS.index('--max-pages') + 1]) if '--max-pages' in ARGS else 12
STATE = os.path.join(OUT, '_state.json'); st = json.load(open(STATE)) if os.path.exists(STATE) else {'done': []}
done = set(st['done']); T_LAST = [0.0]


def g(u, tries=8):
    for i in range(tries):
        dtm = time.time() - T_LAST[0]
        if dtm < 0.5: time.sleep(0.5 - dtm)
        T_LAST[0] = time.time()
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker backtest'}), timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(1.0 * (i + 1)); continue
            if e.code == 404: return {}
            time.sleep(2 * (i + 1))
        except Exception: time.sleep(2 * (i + 1))
    return {}


def settled(series):
    cur = ''
    while True:
        x = g(f"{API}/markets?series_ticker={series}&status=settled&limit=1000" + (f"&cursor={cur}" if cur else ''))
        for m in x.get('markets', []): yield m
        cur = x.get('cursor')
        if not cur or not x.get('markets'): break


def trades(ticker, max_ts=None):
    cur = ''; pages = 0
    while pages < MAX_PAGES:
        x = g(f"{API}/markets/trades?ticker={ticker}&limit=1000" + (f"&max_ts={int(max_ts)}" if max_ts else '') + (f"&cursor={cur}" if cur else ''))
        for t in x.get('trades', []): yield t
        cur = x.get('cursor'); pages += 1
        if not cur or not x.get('trades'): break


def kickoffs():
    """event_ticker date+codes -> kickoff epoch from data/state/hist_schedule.json (pre-kickoff trades only; trading continues in-game on Kalshi)."""
    sys.path.insert(0, os.path.join(HERE, '..'))
    from sharp import sports as SP, exchange_backtest as XB
    sched = XB.Sched(); cache = {}
    def lookup(series, event_ticker):
        if event_ticker in cache: return cache[event_ticker]
        pre = next((k for k in XB.KSERIES_SPORT if series.startswith(k)), None); sport = XB.KSERIES_SPORT.get(pre)
        pe = SP.kalshi_event(event_ticker.split('-', 1)[1]) if sport else None
        g_ = sched.kalshi(sport, pe[0], pe[1], home_first=sport in ('epl', 'laliga', 'bundesliga', 'seriea', 'ligue1', 'mls', 'ucl', 'mma')) if pe else None
        cache[event_ticker] = XB.ts(g_['start']) if g_ else None
        return cache[event_ticker]
    return lookup


def main():
    ko = kickoffs()
    mk_path = os.path.join(OUT, 'markets.jsonl'); seen_m = set()
    if os.path.exists(mk_path):
        for l in open(mk_path): seen_m.add(json.loads(l)['ticker'])
    for series in SERIES:
        n_m = n_t = 0; t0 = time.time()
        with open(mk_path, 'a') as fm, gzip.open(os.path.join(OUT, 'trades', f'{series}.jsonl.gz'), 'at') as ft:
            for m in settled(series):
                tk = m['ticker']
                if tk not in seen_m:
                    fm.write(json.dumps(dict(ticker=tk, event_ticker=m.get('event_ticker'), series=series, result=m.get('result'), strike=m.get('floor_strike'),
                                             open_time=m.get('open_time'), close_time=m.get('close_time'), expiration=m.get('expiration_time'), expected_exp=m.get('expected_expiration_time'),
                                             volume=m.get('volume_fp') or m.get('volume'), title=m.get('title'), sub=m.get('yes_sub_title'), status=m.get('status'))) + '\n')
                    seen_m.add(tk); n_m += 1
                if tk in done or float(m.get('volume_fp') or m.get('volume') or 0) <= 0: continue
                for t in trades(tk, ko(series, m.get('event_ticker') or '')):
                    ft.write(json.dumps(dict(ticker=tk, ts=t['created_time'], yes=float(t['yes_price_dollars']), n=float(t['count_fp']), taker=t.get('taker_side'), block=t.get('is_block_trade'))) + '\n'); n_t += 1
                done.add(tk); st['done'] = sorted(done); json.dump(st, open(STATE, 'w'))
        print(f"[kalshi history] {series}: {n_m} new settled markets, {n_t} trades in {round(time.time() - t0)}s", flush=True)


if __name__ == '__main__':
    main()
