#!/usr/bin/env python3
"""Settle the paper parlay log (sharp/parlay_live.py): for every logged parlay whose legs should be over, read its Kalshi result and
score the maker (who sold YES at the price paid): profit per $1 of taker stake = (price - result) / price. Split by legs, same game or
not, and by how far the price sat over the product of the legs' mids. Also what the maker's edge "should" have been from the legs
alone (price - fair) so the two can be compared. Writes data/state/parlays_record.json.
Usage: python3 sharp/parlay_grade.py"""
import os, json, time, collections, urllib.request, urllib.error, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
API = 'https://api.elections.kalshi.com/trade-api/v2'
LOG = os.path.join(ROOT, 'data', 'state', 'parlays_paper.jsonl'); RES = os.path.join(ROOT, 'data', 'state', 'parlays_results.json'); OUT = os.path.join(ROOT, 'data', 'state', 'parlays_record.json')
MAX_LOOK = 400


def get(u):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + u, headers={'User-Agent': 'sharp-tracker'}), timeout=30) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 * (i + 1)); continue
            return None
        except Exception: time.sleep(1 + i)
    return None


def main():
    if not os.path.exists(LOG): print('[parlay_grade] no log yet'); return
    R = {}
    for l in open(LOG):
        try: x = json.loads(l); R.setdefault(x['ticker'], x)
        except Exception: pass
    res = json.load(open(RES)) if os.path.exists(RES) else {}
    now = dt.datetime.now(dt.timezone.utc); n = 0
    for tk, x in R.items():
        if tk in res or n >= MAX_LOOK: continue
        if (now - dt.datetime.fromisoformat(x['ts'].replace('Z', '+00:00'))).total_seconds() < 4 * 3600: continue
        m = (get('/markets/' + tk) or {}).get('market') or {}; n += 1; time.sleep(0.12)
        if m.get('result') in ('yes', 'no'): res[tk] = 1 if m['result'] == 'yes' else 0
    json.dump(res, open(RES, 'w'), separators=(',', ':'))
    A = collections.defaultdict(lambda: dict(n=0, stake=0.0, pnl=0.0, exp=0.0, hit=0, days=collections.defaultdict(float)))
    for tk, x in R.items():
        if tk not in res: continue
        mk = x['markup']; band = 'under legs' if mk < 0 else '0-3% over' if mk < .03 else '3-8% over' if mk < .08 else '8%+ over'
        for k in ('all', f"{x['n']} legs", 'same game' if x['same_game'] else 'different games', ('same game' if x['same_game'] else 'different games') + ' | ' + band):
            a = A[k]; c = x['usd'] / x['price']; a['n'] += 1; a['stake'] += x['usd']; a['pnl'] += (x['price'] - res[tk]) * c; a['exp'] += (x['price'] - x['fair']) * c; a['hit'] += res[tk]
            a['days'][x['ts'][:10]] += (x['price'] - res[tk]) * c
    rows = {k: dict(n=a['n'], stake=round(a['stake']), maker_pnl=round(a['pnl']), pct_of_stakes=round(100 * a['pnl'] / a['stake'], 1) if a['stake'] else None,
                    expected_from_legs=round(100 * a['exp'] / a['stake'], 1) if a['stake'] else None, hit=round(100 * a['hit'] / a['n'], 1), days=len(a['days'])) for k, a in sorted(A.items())}
    json.dump(dict(updated=now.strftime('%Y-%m-%dT%H:%M:%SZ'), logged=len(R), settled=len(res), rows=rows), open(OUT, 'w'), indent=0)
    print(f'[parlay_grade] {len(R)} logged, {len(res)} settled; all: {rows.get("all")}')


if __name__ == '__main__': main()
