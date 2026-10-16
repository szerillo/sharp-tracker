#!/usr/bin/env python3
"""Novig public exchange data (data.novig.com/reporting/trade-data): every executed trade and every market's daily OHLC, all leagues,
static CSVs since 2026-08-03, no auth. Raw files are immutable and ~140 MB/day, so they are NOT committed; this script keeps:

  data/novig/tape/<date>.jsonl.gz    STRAIGHT taker fills, one row per trade: ts, market, outcome, price (cost/qty), qty, league, type
  data/novig/daily/<date>.jsonl.gz   per market per day: n, volume, vwap, open/close/high/low, first/last ts, and vwap in the T-24h/6h/1h
                                     windows before start when the market is in catalog.json (decoded with desc/outcome names)
  data/novig/markets/<date>.csv.gz   Novig's own per-market daily census (OHLC, open interest, status) as published

Usage: python3 loggers/novig_tape.py [--all | --days N | YYYY-MM-DD ...]   (default: the last 3 published days not yet on disk)
"""
import sys, os, io, csv, gzip, json, time, datetime as dt, urllib.request, collections

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'data', 'novig')
for d in ('tape', 'daily', 'markets'): os.makedirs(os.path.join(OUT, d), exist_ok=True)
BASE = "https://data.novig.com/reporting/trade-data"
sys.path.insert(0, HERE); from novig_catalog import load_catalog
BIG_USD = 1000.0


def fetch(u):
    for i in range(4):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=300).read()
        except Exception as e:
            if getattr(e, 'code', 0) == 404: return None
            time.sleep(3 * (i + 1))
    return None


def summarise(date, rows, cat):
    """rows: decoded taker fills. -> per-market daily rows."""
    by = collections.defaultdict(list)
    for r in rows: by[(r['market'], r['outcome'])].append(r)
    out = []
    for (mid, oid), L in by.items():
        L.sort(key=lambda r: r['ts']); m = cat.get(mid) or {}
        q = sum(r['qty'] for r in L); cost = sum(r['price'] * r['qty'] for r in L)
        rec = dict(date=date, market=mid, outcome=oid, league=L[0]['league'], type=L[0]['type'], n=len(L), qty=round(q, 2), vwap=round(cost / q, 4) if q else None,
                   open=L[0]['price'], close=L[-1]['price'], high=max(r['price'] for r in L), low=min(r['price'] for r in L), first_ts=L[0]['ts'], last_ts=L[-1]['ts'],
                   big_n=sum(1 for r in L if r['qty'] >= BIG_USD), big_qty=round(sum(r['qty'] for r in L if r['qty'] >= BIG_USD), 2),
                   big_vwap=(round(sum(r['price'] * r['qty'] for r in L if r['qty'] >= BIG_USD) / sum(r['qty'] for r in L if r['qty'] >= BIG_USD), 4)
                             if any(r['qty'] >= BIG_USD for r in L) else None))
        if m:
            rec.update(event=m.get('event'), desc=m.get('desc'), strike=m.get('strike'), name=(m.get('outcomes') or {}).get(oid), start_ts=m.get('start_ts'))
            if m.get('start_ts'):
                st = m['start_ts'] / 1000
                for name, mins in (('24h', 1440), ('6h', 360), ('1h', 60)):
                    w = [r for r in L if st - mins * 60 <= r['t'] < st - (mins * 60 - 3600 if mins > 60 else 0)]   # the hour ending at T-mins (T-1h: last hour)
                    if w: rec[f'vwap_{name}'] = round(sum(r['price'] * r['qty'] for r in w) / sum(r['qty'] for r in w), 4); rec[f'qty_{name}'] = round(sum(r['qty'] for r in w), 2)
                pre = [r for r in L if r['t'] < st]
                rec['pregame_qty'] = round(sum(r['qty'] for r in pre), 2); rec['pregame_close'] = pre[-1]['price'] if pre else None
        out.append(rec)
    return out


def one_day(date, cat, force=False):
    tp = os.path.join(OUT, 'tape', f'{date}.jsonl.gz'); dp = os.path.join(OUT, 'daily', f'{date}.jsonl.gz'); mp = os.path.join(OUT, 'markets', f'{date}.csv.gz')
    if os.path.exists(dp) and not force: return None
    raw = fetch(f"{BASE}/{date}/trades.csv")
    if raw is None: print(f"[tape] {date}: no trades file"); return None
    rows = []
    for r in csv.DictReader(io.StringIO(raw.decode())):
        if r['side'] != 'TAKER' or r['tradeType'] != 'STRAIGHT': continue
        qty = float(r['qty']); cost = float(r['cost'])
        if qty <= 0: continue
        t = dt.datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')).timestamp()
        rows.append(dict(ts=r['timestamp'], t=t, market=r['marketId'], outcome=r['outcomeId'], price=round(cost / qty, 4), qty=round(qty, 2), league=r['league'], type=r['marketType']))
    with gzip.open(tp, 'wt') as f:
        for r in rows: f.write(json.dumps({k: v for k, v in r.items() if k != 't'}) + '\n')
    daily = summarise(date, rows, cat)
    with gzip.open(dp, 'wt') as f:
        for r in daily: f.write(json.dumps(r, separators=(',', ':')) + '\n')
    mk = fetch(f"{BASE}/{date}/markets.csv")
    if mk: open(mp, 'wb').write(gzip.compress(mk))
    dec = sum(1 for r in daily if r.get('desc'))
    print(f"[tape] {date}: {len(rows)} straight taker fills, {len(daily)} market-outcome-days ({dec} decoded), ${sum(r['qty'] for r in rows):,.0f} notional")
    return len(rows)


def main():
    idx = json.loads(fetch(f"{BASE}/index.json") or '{}'); dates = idx.get('dates', [])
    cat = load_catalog()
    args = sys.argv[1:]
    if '--all' in args: todo = dates
    elif '--days' in args: todo = dates[-int(args[args.index('--days') + 1]):]
    elif args: todo = [a for a in args if a in dates]
    else: todo = dates[-3:]
    for d in todo: one_day(d, cat, force='--force' in args)


if __name__ == '__main__':
    main()
