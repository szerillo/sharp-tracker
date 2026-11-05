#!/usr/bin/env python3
"""Tennis market history from the exchanges (Sean, 11/4: find alpha in tennis markets, match or set 1 or totals; and did the Polymarket
sharp accounts make money on tennis?). Two sources, both public, both resumable (files are append-only and conditions / tickers already
on file are skipped), run on GitHub's runner by .github/workflows/tennis_history.yml:

  kalshi   every SETTLED market in the tennis series (match winner, set winner, total games, total sets, set spread, tiebreak, set
           sweep, Challenger match) with its result, and the full trade tape per market (price, size, time) -> the close is the last
           trade before the match. data/tennis/kalshi_hist/markets.jsonl.gz and trades.jsonl.gz. Kalshi keeps settled markets for
           about two months, so this grows the history from here on.
  poly     every CLOSED Polymarket tennis event (Gamma tag 'tennis'), its markets (match winner, set winners, totals, spreads, exact
           score ...) with outcome prices (the result) and start time, plus the taker-fill tape per market from the Data API
           (wallet, side, price, size, time) -> close, and which wallets were on which side. data/tennis/poly_hist/events.jsonl.gz
           and trades.jsonl.gz (match winner, set-1 winner and total-sets markets with volume; the rest have none).
Usage: python3 loggers/tennis_history.py [kalshi|poly] [--months N]"""
import os, sys, json, gzip, time, datetime as dt, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, HERE)
KH = os.path.join(ROOT, 'data', 'tennis', 'kalshi_hist'); PH = os.path.join(ROOT, 'data', 'tennis', 'poly_hist')
K = "https://api.elections.kalshi.com/trade-api/v2"; G = "https://gamma-api.polymarket.com"
K_SERIES = ['KXATPMATCH', 'KXWTAMATCH', 'KXATPCHALLENGERMATCH', 'KXATPSETWINNER', 'KXWTASETWINNER', 'KXATPGTOTAL', 'KXWTAGTOTAL', 'KXATPGAMETOTAL',
            'KXATPTOTALSETS', 'KXATPSSPREAD', 'KXATPTIEBREAK', 'KXATPSETSWEEP', 'KXATPEXACTMATCH', 'KXWTAEXACTMATCH']
MONTHS = int(sys.argv[sys.argv.index('--months') + 1]) if '--months' in sys.argv else 14
T0 = time.time(); BUDGET = float(os.environ.get('HIST_BUDGET_S') or 4.5 * 3600)


def g(u, tries=6):
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=40))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(min(60, 3 * 2 ** i)); continue
            if e.code in (404, 422): return None
            time.sleep(2 + i)
        except Exception: time.sleep(2 + i)
    return None


def have(path, key):
    s = set()
    if os.path.exists(path):
        with gzip.open(path, 'rt') as fh:
            for l in fh:
                try: s.add(json.loads(l)[key])
                except Exception: pass
    return s


def append(path, rows):
    if not rows: return
    with gzip.open(path, 'at') as fh:
        for r in rows: fh.write(json.dumps(r, separators=(',', ':')) + '\n')


def trade_row(ticker, x):
    """Kalshi moved trade prices to *_price_dollars strings and counts to count_fp (the old fields come back null): read both."""
    f = lambda *ks: next((float(x[k]) for k in ks if x.get(k) is not None), None)
    return dict(ticker=ticker, ts=x.get('created_time'), yes=f('yes_price_dollars', 'yes_price'), no=f('no_price_dollars', 'no_price'), n=f('count_fp', 'count'), side=x.get('taker_side'))


def priceless(path):
    """Tickers whose stored tape has rows but no prices (pulled before the field rename, 11/5): re-pulled by --repair, budget permitting."""
    bad, good = set(), set()
    if not os.path.exists(path): return bad
    with gzip.open(path, 'rt') as fh:
        for l in fh:
            try: r = json.loads(l)
            except Exception: continue
            if r.get('empty'): continue
            (good if r.get('yes') is not None else bad).add(r['ticker'])
    return bad - good


def kalshi():
    os.makedirs(KH, exist_ok=True)
    MP, TP = os.path.join(KH, 'markets.jsonl.gz'), os.path.join(KH, 'trades.jsonl.gz')
    seen_m, seen_t = have(MP, 'ticker'), have(TP, 'ticker')
    n_new_m = n_new_t = 0
    if '--repair' in sys.argv:
        bad = sorted(priceless(TP)); print(f"[kalshi] {len(bad)} tapes without prices to re-pull", flush=True); fixed = 0
        for tk in bad:
            if time.time() - T0 > BUDGET: break
            t = g(f"{K}/markets/trades?ticker={tk}&limit=1000"); rows = [trade_row(tk, x) for x in (t or {}).get('trades') or []]
            if rows and rows[0].get('yes') is not None: append(TP, rows); fixed += 1
            time.sleep(0.15)
        print(f"[kalshi] repaired {fixed} tapes ({time.time() - T0:.0f}s)")
    for s in K_SERIES:
        cur = None; pages = 0
        while True:
            d = g(f"{K}/markets?series_ticker={s}&status=settled&limit=1000" + (f"&cursor={cur}" if cur else ''))
            if not d: break
            ms = d.get('markets') or []; pages += 1
            new = [dict(m, series=s) for m in ms if m['ticker'] not in seen_m]
            append(MP, new); seen_m.update(m['ticker'] for m in new); n_new_m += len(new)
            # trades for every settled market we have no tape for yet (one page of 1000 is the whole tape for nearly all tennis markets)
            for m in ms:
                if m['ticker'] in seen_t or time.time() - T0 > BUDGET: continue
                t = g(f"{K}/markets/trades?ticker={m['ticker']}&limit=1000")
                rows = [trade_row(m['ticker'], x) for x in (t or {}).get('trades') or []]
                append(TP, rows if rows else [dict(ticker=m['ticker'], ts=None, empty=True)]); seen_t.add(m['ticker']); n_new_t += 1
                time.sleep(0.15)
            cur = d.get('cursor')
            if not cur or not ms or pages >= 50: break
        print(f"[kalshi] {s}: {len([1 for _ in ms])} on last page, markets on file {len(seen_m)}, tapes {len(seen_t)}  ({time.time() - T0:.0f}s)")
    print(f"[kalshi] new markets {n_new_m}, new tapes {n_new_t}")


def poly():
    import polydata
    os.makedirs(PH, exist_ok=True)
    EP, TP = os.path.join(PH, 'events.jsonl.gz'), os.path.join(PH, 'trades.jsonl.gz')
    seen_e, seen_c = have(EP, 'slug'), have(TP, 'cond')
    n_new_e = n_new_t = 0
    end = dt.datetime.now(dt.timezone.utc); start = end - dt.timedelta(days=30 * MONTHS)
    # month windows (the offset parameter stops around 2,000, so page by end date)
    w0 = start
    while w0 < end:
        w1 = min(end, w0 + dt.timedelta(days=14)); off = 0
        while True:
            E = g(f"{G}/events?tag_slug=tennis&closed=true&limit=100&offset={off}&end_date_min={w0.strftime('%Y-%m-%dT%H:%M:%SZ')}&end_date_max={w1.strftime('%Y-%m-%dT%H:%M:%SZ')}&order=endDate&ascending=true")
            if not E: break
            for e in E:
                slug = e.get('slug') or ''
                if slug in seen_e: continue
                # singles match events only: 'X vs Y' titles; tournament winners, doubles, props and futures are skipped
                title = e.get('title') or ''
                if ' vs' not in title.lower() or 'doubles' in slug or 'doubles' in title.lower(): continue
                ms = []
                for m in e.get('markets') or []:
                    ms.append(dict(cond=m.get('conditionId'), q=m.get('question'), slug=m.get('slug'), line=m.get('line'), stype=m.get('sportsMarketType'), start=m.get('gameStartTime'),
                                   outcomes=m.get('outcomes'), prices=m.get('outcomePrices'), tokens=m.get('clobTokenIds'), vol=m.get('volume'), closed=m.get('closed'), end=m.get('endDate')))
                rec = dict(slug=slug, title=title, start=e.get('startDate'), end=e.get('endDate'), vol=e.get('volume'), markets=ms)
                append(EP, [rec]); seen_e.add(slug); n_new_e += 1
                # tapes: the match-winner market (question == title) and set-1 / total markets
                for m in ms:
                    q = (m['q'] or '').lower()
                    try: vol = float(m['vol'] or 0)
                    except Exception: vol = 0
                    want = m['q'] == title or q.startswith('set 1 winner') or 'total sets' in q
                    if not want or vol <= 0 or not m['cond'] or m['cond'] in seen_c or time.time() - T0 > BUDGET: continue
                    try: rows = polydata.trades(condition=m['cond'], limit=100, max_rows=3000)
                    except Exception: rows = []
                    out = [dict(cond=m['cond'], ts=r.get('timestamp'), w=r.get('proxyWallet'), side=r.get('side'), outcome=r.get('outcome'), price=r.get('price'), size=r.get('size')) for r in rows or []]
                    append(TP, out if out else [dict(cond=m['cond'], ts=None, empty=True)]); seen_c.add(m['cond']); n_new_t += 1
                    time.sleep(0.1)
            if len(E) < 100: break
            off += 100
        print(f"[poly] through {w1.date()}: events on file {len(seen_e)}, tapes {len(seen_c)}  ({time.time() - T0:.0f}s)")
        w0 = w1
        if time.time() - T0 > BUDGET: print('[poly] time budget reached; resumes next run'); break
    print(f"[poly] new events {n_new_e}, new tapes {n_new_t}")


if __name__ == '__main__':
    what = [a for a in sys.argv[1:] if not a.startswith('--') and a in ('kalshi', 'poly')] or ['kalshi', 'poly']
    for w in what: (kalshi if w == 'kalshi' else poly)()
