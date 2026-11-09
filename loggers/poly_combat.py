#!/usr/bin/env python3
"""Polymarket combat sports (UFC / MMA / boxing): every settled two-way fight moneyline and its full public trade tape (Sean, 11/9: "we
only have Polymarket stuff for MMA for a few months; we should have a longer feed of sharp action"). The main history logger
(loggers/polymarket_history.py) only kept fights whose market carried a gameStartTime, which dropped most older UFC cards; here the start
comes from the market's gameStartTime, else its event's startDate (date only, flagged), and the fight is matched to ESPN / Odds API later.
Step 1 catalog: Gamma events for tags ufc, mma, boxing, walked back by end date -> data/polymarket/combat/catalog.jsonl.
Step 2 trades: data-api v2 taker fills per market (volume >= --min-volume) -> data/polymarket/combat/trades/<conditionId>.jsonl.gz.
Usage: python3 loggers/poly_combat.py catalog | trades [--min-volume 500]"""
import os, sys, json, gzip, time, datetime as dt, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import polydata
from polymarket_history import g
OUT = os.path.join(HERE, '..', 'data', 'polymarket', 'combat'); os.makedirs(os.path.join(OUT, 'trades'), exist_ok=True)
G = "https://gamma-api.polymarket.com"
TAGS = ['ufc', 'mma', 'boxing']


def catalog():
    have = set(); n = 0
    with open(os.path.join(OUT, 'catalog.jsonl'), 'w') as f:
        for tag in TAGS:
            mx = dt.date.today().isoformat(); empty = 0; nt = 0
            while empty < 15 and mx > '2021-01-01':
                E = g(f"{G}/events?tag_slug={tag}&closed=true&limit=100&order=startDate&ascending=false&end_date_max={mx}T00:00:00Z")
                if not E: break
                oldest = mx; got = 0
                for e in E:
                    sd = (e.get('startDate') or '')[:10]
                    if sd and sd < oldest: oldest = sd
                    for m in e.get('markets') or []:
                        if m['conditionId'] in have: continue
                        if m.get('sportsMarketType') not in (None, 'moneyline'): continue
                        try: outs = json.loads(m['outcomes']); px = [float(x) for x in json.loads(m.get('outcomePrices') or '[]')]
                        except Exception: continue
                        if len(outs) != 2 or sorted(px) != [0.0, 1.0] or outs in (['Yes', 'No'], ['No', 'Yes']) and 'vs' not in (m.get('question') or ''): continue
                        have.add(m['conditionId']); got += 1; nt += 1
                        st = m.get('gameStartTime') or e.get('endDate') or e.get('startDate')
                        f.write(json.dumps(dict(tag=tag, event=e.get('slug'), market_slug=m.get('slug'), title=m.get('question'), cond=m['conditionId'],
                                                outcomes=outs, winner=outs[px.index(1.0)], start=st, start_exact=bool(m.get('gameStartTime')),
                                                volume=float(m.get('volume') or 0))) + '\n')
                empty = empty + 1 if got == 0 else 0
                if oldest >= mx: oldest = (dt.date.fromisoformat(mx) - dt.timedelta(days=5)).isoformat()
                mx = oldest
            print(f"[poly combat] {tag}: {nt} settled two-way markets, reached {mx}", flush=True); n += nt
    print(f"[poly combat] catalog: {n} markets")


def trades_for(cond):
    p = os.path.join(OUT, 'trades', f'{cond}.jsonl.gz')
    if os.path.exists(p): return 0
    T = polydata.trades(condition=cond, limit=500, max_rows=20000)
    with gzip.open(p, 'wt') as f:
        for t in T: f.write(json.dumps(dict(ts=t['timestamp'], side=t['side'], outcome=t.get('outcome'), price=t['price'], size=t['size'],
                                            wallet=t.get('proxyWallet')), separators=(',', ':')) + '\n')
        if len(T) >= 20000: f.write(json.dumps(dict(truncated=True)) + '\n')
    return len(T)


def trades(min_vol):
    C = [json.loads(l) for l in open(os.path.join(OUT, 'catalog.jsonl'))]
    todo = [c['cond'] for c in C if c['volume'] >= min_vol]
    t0 = time.time(); n = 0
    with cf.ThreadPoolExecutor(6) as ex:
        for i, k in enumerate(ex.map(trades_for, todo)):
            n += k
            if i % 200 == 0: print(f"[poly combat] trades {i}/{len(todo)} markets, {n} trades, {time.time() - t0:.0f}s", flush=True)
    print(f"[poly combat] trades done: {len(todo)} markets, {n} new trades")


if __name__ == '__main__':
    mv = float(sys.argv[sys.argv.index('--min-volume') + 1]) if '--min-volume' in sys.argv else 500.0
    catalog() if sys.argv[1] == 'catalog' else trades(mv)
