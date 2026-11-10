#!/usr/bin/env python3
"""Parlay prices against their legs, live, paper only (Sean 11/10: "think offering parlays even more lucrative"; two-week test in
docs/maker_playbook.md: makers kept 16.3% of stakes on two-leg parlays, 6.4% on three legs, lost on 6+). Each run takes the newest
parlay trades off Kalshi's public trade feed (about 45 parlay trades a second, so a run is a sample), keeps two- and three-leg
parlays where the taker bought YES, and for each one reads the legs' own Kalshi markets at that moment. Logged: the price the taker
paid, the product of the legs' mid prices (the no-correlation fair price), the product of the legs' asks (what buying each leg alone
would cost in probability terms), and the markup = price / product of mids - 1. Parlays whose legs share a game are flagged (their
legs are correlated, so the product is not a fair price there).
Appends to data/state/parlays_paper.jsonl; sharp/parlay_grade.py settles them. Nothing is placed.
Usage: python3 sharp/parlay_live.py [max_parlays]"""
import os, sys, json, time, urllib.request, urllib.error, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
API = 'https://api.elections.kalshi.com/trade-api/v2'; OUT = os.path.join(ROOT, 'data', 'state', 'parlays_paper.jsonl')
MAXN = int(sys.argv[1]) if len(sys.argv) > 1 else 60; PAGES = 3; MIN_USD = 5.0


def get(u):
    for i in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + u, headers={'User-Agent': 'sharp-tracker'}), timeout=30) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 * (i + 1)); continue
            return None
        except Exception: time.sleep(1 + i)
    return None


def f(x):
    try: return float(x)
    except Exception: return None


def main():
    seen = set()
    if os.path.exists(OUT):
        for l in open(OUT):
            try: seen.add(json.loads(l)['ticker'])
            except Exception: pass
    T = {}; cur = ''
    for _ in range(PAGES):
        d = get('/markets/trades?limit=1000' + (f'&cursor={cur}' if cur else ''))
        if not d: break
        for t in d.get('trades') or []:
            if not t.get('ticker', '').startswith('KXMVE') or t.get('taker_side') != 'yes' or t['ticker'] in seen: continue
            p = f(t.get('yes_price_dollars')); c = f(t.get('count_fp'))
            if p is None or not c or not 0.03 <= p <= 0.97 or p * c < MIN_USD: continue
            x = T.setdefault(t['ticker'], dict(ticker=t['ticker'], ts=t['created_time'][:19] + 'Z', usd=0.0, c=0.0))
            x['usd'] += p * c; x['c'] += c
        cur = d.get('cursor')
        if not cur: break
        time.sleep(0.3)
    rows = []; legq = {}; looked = 0
    for x in sorted(T.values(), key=lambda z: -z['usd']):
        if len(rows) >= MAXN or looked >= MAXN * 4: break
        looked += 1
        m = (get('/markets/' + x['ticker']) or {}).get('market') or {}
        legs = m.get('mve_selected_legs') or []
        if not 2 <= len(legs) <= 3: time.sleep(0.15); continue
        mid = ask = 1.0; ok = True; L = []
        for l in legs:
            tk = l.get('market_ticker')
            if tk not in legq:
                q = (get('/markets/' + tk) or {}).get('market') or {}; time.sleep(0.15)
                legq[tk] = (f(q.get('yes_bid_dollars')), f(q.get('yes_ask_dollars')), q.get('status'))
            b, a, st = legq[tk]
            if b is None or a is None or not (0 < b < a < 1) or a - b > 0.06 or st not in ('active', 'open'): ok = False; break
            yes = l.get('side') == 'yes'
            lm = (b + a) / 2 if yes else 1 - (b + a) / 2; la = a if yes else 1 - b
            mid *= lm; ask *= la; L.append([tk, l.get('side'), round(lm, 4)])
        if not ok: continue
        price = x['usd'] / x['c']; games = len({l.get('event_ticker', '').split('-', 1)[-1] for l in legs})
        rows.append(dict(ticker=x['ticker'], ts=x['ts'], price=round(price, 4), usd=round(x['usd'], 2), legs=L, n=len(legs), same_game=games < len(legs),
                         fair=round(mid, 4), legs_ask=round(ask, 4), markup=round(price / mid - 1, 4), close=m.get('close_time')))
    if rows:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, 'a') as fh:
            for r in rows: fh.write(json.dumps(r, separators=(',', ':')) + '\n')
    ind = [r for r in rows if not r['same_game']]
    w = sum(r['usd'] for r in ind)
    print(f"[parlay_live] {len(T)} parlay tickers in the sample, {looked} looked up, {len(rows)} logged ({len(ind)} with legs in different games); "
          f"stake-weighted markup over the legs' mids {round(100 * sum(r['markup'] * r['usd'] for r in ind) / w, 1) if w else None}%")


if __name__ == '__main__': main()
