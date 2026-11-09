#!/usr/bin/env python3
"""Kalshi daily high-temperature markets: settled brackets and their full trade tape (Sean, 11/9: "can we use our weather modeling to beat
weather models or prediction markets?"). Public API, no key. The settled listing only reaches back about 68 days, so run it on a schedule
to build history. Writes data/research/wx_kalshi/<SERIES>.markets.json and trades/<ticker>.jsonl.gz (ts, yes price, count, taker side).
Settlement (each market's rules): the NWS daily climate report (CLI) max for the city's station.
Usage: python3 loggers/kalshi_weather.py [SERIES,SERIES ...]"""
import os, sys, json, gzip, time, datetime as dt, urllib.request, urllib.error, concurrent.futures as cf
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT = os.path.join(ROOT, 'data', 'research', 'wx_kalshi'); os.makedirs(os.path.join(OUT, 'trades'), exist_ok=True)
API = 'https://api.elections.kalshi.com/trade-api/v2'
SERIES = (sys.argv[1].split(',') if len(sys.argv) > 1 else
          ['KXHIGHNY', 'KXHIGHCHI', 'KXHIGHMIA', 'KXHIGHAUS', 'KXHIGHLAX', 'KXHIGHDEN', 'KXHIGHTDC'])


def get(u):
    for i in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=40) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(3 * (i + 1)); continue
            return None
        except Exception: time.sleep(2 + i)
    return None


def main():
    for s in SERIES:
        M = []; cur = ''
        while True:
            d = get(f'{API}/markets?series_ticker={s}&status=settled&limit=1000' + (f'&cursor={cur}' if cur else ''))
            if not d: break
            M += d.get('markets') or []; cur = d.get('cursor')
            if not cur: break
            time.sleep(0.5)
        json.dump(dict(series=s, markets=M), open(os.path.join(OUT, f'{s}.markets.json'), 'w'))
        def one(m):
            p = os.path.join(OUT, 'trades', m['ticker'] + '.jsonl.gz')
            if os.path.exists(p): return 0
            # 11/9: only trades from 36 hours before the market's day (the calibration starts the evening before); cuts the paging
            try: d0 = dt.datetime.strptime(m['event_ticker'].split('-')[1], '%y%b%d').replace(tzinfo=dt.timezone.utc)
            except Exception: d0 = None
            mn = f"&min_ts={int((d0 - dt.timedelta(hours=36)).timestamp())}" if d0 else ''
            T = []; cur = ''
            while True:
                d = get(f"{API}/markets/trades?ticker={m['ticker']}&limit=1000{mn}" + (f'&cursor={cur}' if cur else ''))
                time.sleep(0.4)
                if not d: break
                for t in d.get('trades') or []:
                    T.append(dict(ts=t['created_time'], yes=float(t.get('yes_price_dollars') or t.get('yes_price', 0) / 100),
                                  n=float(t.get('count_fp') or t.get('count') or 0), taker=t.get('taker_side')))
                cur = d.get('cursor')
                if not cur: break
            with gzip.open(p, 'wt') as f:
                for t in T: f.write(json.dumps(t, separators=(',', ':')) + '\n')
            return 1
        with cf.ThreadPoolExecutor(4) as ex: n = sum(ex.map(one, M))
        print(f'[kalshi_weather] {s}: {len(M)} settled brackets, {n} trade tapes pulled', flush=True)


if __name__ == '__main__': main()
