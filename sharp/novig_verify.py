#!/usr/bin/env python3
"""Which side of a Novig trade is the taker's? Our 5-minute pull (data/novig/trades5, Novig's live API) gives each trade's
market, outcome, price and size but not who took. Novig's public tape (data/novig/tape, published a day or two later) lists
straight taker fills with the taker's outcome and price. Match each 5-minute row to the tape (same market, size within 1 cent,
time within 3 s) and count whether the tape's taker outcome is the row's outcome or the other one.
Usage: python3 sharp/novig_verify.py"""
import os, glob, gzip, json, collections, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def main():
    tape = collections.defaultdict(list); lo = hi = None
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'novig', 'tape', '*.jsonl.gz'))):
        for l in gzip.open(f, 'rt'):
            r = json.loads(l); t = int(dt.datetime.fromisoformat(r['ts'].replace('Z', '+00:00')).timestamp() * 1000)
            tape[r['market']].append((t, r['outcome'], r['price'], r['qty']))
            lo = t if lo is None else min(lo, t); hi = t if hi is None else max(hi, t)
    c = collections.Counter()
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'novig', 'trades5', '*.jsonl.gz'))):
        for l in gzip.open(f, 'rt'):
            r = json.loads(l)
            if not (lo <= r['ts'] <= hi): continue
            c['rows in tape window'] += 1; L = tape.get(r['market_id']); q = r['qty_cents'] / 100
            cands = [x for x in L or [] if abs(x[0] - r['ts']) <= 3000 and abs(x[3] - q) < 0.011]
            if not cands: c['no tape match'] += 1; continue
            same = any(x[1] == r['outcome_id'] for x in cands); opp = any(x[1] != r['outcome_id'] for x in cands)
            k = 'taker = row outcome' if same and not opp else 'taker = the OTHER outcome' if opp and not same else 'ambiguous'
            c[k] += 1
            if r['usd'] >= 500: c[k + ' ($500+)'] += 1
            if k == 'taker = the OTHER outcome': c['  tape price = 1 - row price' if any(abs(x[2] - (1 - r['price'])) < 0.006 for x in cands) else '  tape price other'] += 1
    print(f"[novig_verify] tape {dt.datetime.fromtimestamp(lo / 1000, dt.timezone.utc):%m/%d %H:%M}Z to {dt.datetime.fromtimestamp(hi / 1000, dt.timezone.utc):%m/%d %H:%M}Z")
    for k, v in c.items(): print(f"  {k:36} {v}")


if __name__ == '__main__':
    main()
