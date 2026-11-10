#!/usr/bin/env python3
"""Novig makers on the whole public tape, every market type (overnight 11/10; docs/maker_2026-11-10.md had 11 days of game lines).
data.novig.com/reporting/trade-data/<date>/trades.csv has one row per side of every trade (side = TAKER or MAKER) since 2026-08-03.
For every pregame STRAIGHT MAKER row on a settled market in our catalog (data/novig/catalog: start, result, type, league): the maker's
price (cost / qty), the settled result, and the market's close (last pregame taker prices on the two outcomes, a mid when both printed in
the last 2 hours). Novig charges no pregame fee. Summed by market type, league, time to the start, fill size and price; settled z is
clustered by event. Also the maker dollars per day by market type (how much there is to fill).
Runs on a GitHub runner (data.novig.com is not reachable from the analysis container).
Usage: python3 sharp/novig_maker_history.py [first_day] [last_day]  -> data/research/novig_maker_history.json"""
import os, sys, csv, json, gzip, time, collections, datetime as dt, urllib.request, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
from novig_catalog import load_catalog
BASE = "https://data.novig.com/reporting/trade-data"
D0 = sys.argv[1] if len(sys.argv) > 1 else '2026-08-03'; D1 = sys.argv[2] if len(sys.argv) > 2 else (dt.date.today() - dt.timedelta(days=1)).isoformat()
T0 = time.time(); MAXS = float(os.environ.get('MAX_SECONDS', 19000))
SOCCER = {'MLS', 'EPL', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1', 'Champions League', 'UCL', 'Liga MX', 'Europa League'}


def tgroup(t):
    t = t or ''
    per = ''
    for suf, lab in (('_1H', '1st half '), ('_1Q', '1st quarter '), ('_1P', '1st period '), ('_F5', 'first 5 ')):
        if t.endswith(suf): per = lab; t = t[:-len(suf)]
    base = {'MONEY': 'moneyline', 'MONEYLINE_3_WAY_WIN': 'moneyline (3-way)', 'SPREAD': 'spread', 'TOTAL': 'total', 'TEAM_TOTAL': 'team total'}.get(t)
    return (per + base) if base else 'player and other props'


def lgroup(l): return 'soccer' if l in SOCCER else 'tennis' if l in ('ATP', 'WTA') else (l or '?')


def fetch_to(u, path):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=600) as r, open(path, 'wb') as f:
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    f.write(b)
            return True
        except Exception as e:
            if getattr(e, 'code', 0) == 404: return False
            time.sleep(5 * (i + 1))
    return False


def main():
    cat = load_catalog(); print(f'catalog: {len(cat)} markets', flush=True)
    PNL = collections.defaultdict(lambda: collections.defaultdict(float))     # key -> event -> settled pnl
    AGG = collections.defaultdict(lambda: [0, 0.0, 0.0])                       # key -> fills, contracts, cost
    DAY = collections.defaultdict(lambda: collections.defaultdict(float))      # type group -> day -> cost
    CL = collections.defaultdict(lambda: [0.0, 0.0])                           # (market, outcome, clv key) -> qty, cost
    LAST = {}                                                                  # (market, outcome) -> (t, price) last pregame taker print
    seen = collections.Counter(); days = []
    d = dt.date.fromisoformat(D0); end = dt.date.fromisoformat(D1)
    tmp = os.path.join(tempfile.gettempdir(), 'novig_trades.csv')
    while d <= end and time.time() - T0 < MAXS:
        ds = d.isoformat(); d += dt.timedelta(days=1)
        if not fetch_to(f"{BASE}/{ds}/trades.csv", tmp): print(f'{ds}: no file', flush=True); continue
        n = 0
        if os.environ.get('DEBUG_ROWS'):       # check of the file's shape: both sides of the same trades, and whether their costs add to the payout
            with open(tmp, newline='') as fh:
                rd = csv.DictReader(fh); print(rd.fieldnames); by = collections.defaultdict(list)
                for i, r in enumerate(rd):
                    if r.get('tradeType') == 'STRAIGHT': by[r.get('tradeId') or r.get('id') or (r['marketId'], r['timestamp'], r['qty'])].append(r)
                    if i > 400000: break
                k2 = [v for v in by.values() if len(v) == 2 and {x['side'] for x in v} == {'TAKER', 'MAKER'}]
                print('trades with both sides:', len(k2), 'of', len(by))
                same = sum(1 for v in k2 if v[0]['outcomeId'] == v[1]['outcomeId']); print('same outcome on both sides:', same, 'different:', len(k2) - same)
                tot = [(float(v[0]['cost']) + float(v[1]['cost'])) / float(v[0]['qty']) for v in k2 if float(v[0]['qty']) > 0 and v[0]['qty'] == v[1]['qty']]
                tot.sort(); print('(taker cost + maker cost) / qty: median', tot[len(tot) // 2] if tot else None, 'p10', tot[len(tot) // 10] if tot else None, 'p90', tot[9 * len(tot) // 10] if tot else None, 'n', len(tot))
                for v in k2[:4]: print(json.dumps(v)[:900])
            return
        with open(tmp, newline='') as fh:
            for r in csv.DictReader(fh):
                if r.get('tradeType') != 'STRAIGHT': continue
                m = cat.get(r['marketId'])
                if not m or not m.get('start_ts'): seen['not in catalog'] += 1; continue
                try: qty = float(r['qty']); cost = float(r['cost']); t = dt.datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')).timestamp()
                except Exception: continue
                st = m['start_ts'] / 1000
                if qty <= 0 or t >= st: continue
                q = cost / qty
                if not 0.02 <= q <= 0.98: continue
                oid = r['outcomeId']
                if r['side'] == 'TAKER':
                    LAST[(r['marketId'], oid)] = (t, q); continue
                if r['side'] != 'MAKER': continue
                res = (m.get('result') or {}).get(oid)
                if res not in ('WIN', 'LOSS') or len(m.get('outcomes') or {}) != 2: seen['no win/loss result'] += 1; continue
                won = 1.0 if res == 'WIN' else 0.0; tg = tgroup(m.get('type')); lg = lgroup(m.get('league')); h = (st - t) / 3600; ev = m.get('event_id') or r['marketId']
                tb = '24h+' if h >= 24 else '6-24h' if h >= 6 else '1-6h' if h >= 1 else 'last hour'
                sb = 'under $100' if cost < 100 else '$100-1k' if cost < 1000 else '$1k-10k' if cost < 1e4 else '$10k+'
                pb = 'under 25c' if q < .25 else '25-40c' if q < .4 else '40-60c' if q < .6 else '60-75c' if q < .75 else '75c+'
                pnl = (won - q) * qty; n += 1
                for key in (('all',), ('type', tg), ('league type', lg, tg), ('time', tb), ('size', sb), ('price', pb), ('type time', tg, tb), ('type size', tg, sb), ('month', ds[:7]),
                            ('type price', tg, pb), ('prop', lg, m.get('type') or '?') if tg == 'player and other props' else ('league', lg), ('league month', lg, ds[:7])):
                    PNL[key][ev] += pnl; a = AGG[key]; a[0] += 1; a[1] += qty; a[2] += cost
                for ck in (('all',), ('type', tg), ('time', tb), ('size', sb), ('type time', tg, tb)):
                    c_ = CL[(r['marketId'], oid, ck)]; c_[0] += qty; c_[1] += cost
                DAY[tg][ds] += cost
        days.append(ds); print(f'{ds}: {n} pregame maker fills ({round(time.time() - T0)}s)', flush=True)
    # close per market outcome: a mid when both outcomes printed inside the last 2 hours before the start
    CLV = collections.defaultdict(lambda: [0.0, 0.0])
    for (mid, oid, ck), (qty, cost) in CL.items():
        m = cat[mid]; st = m['start_ts'] / 1000; oth = next((o for o in m['outcomes'] if o != oid), None)
        a = LAST.get((mid, oid)); b = LAST.get((mid, oth))
        if not a or not b or st - a[0] > 7200 or st - b[0] > 7200: continue
        close = (a[1] + (1 - b[1])) / 2
        if abs(a[1] - (1 - b[1])) > 0.06: continue
        x = CLV[ck]; x[0] += close * qty - cost; x[1] += qty
    rows = {}
    for key, evs in PNL.items():
        n, qty, cost = AGG[key]; tot = sum(evs.values()); se = sum(v * v for v in evs.values()) ** 0.5
        cv = CLV.get(key)
        rows[' | '.join(key)] = dict(fills=n, events=len(evs), risk=round(cost), risk_per_day=round(cost / max(1, len(days))), roi=round(100 * tot / cost, 2) if cost else None,
                                     roi_z=round(tot / se, 2) if se else None, pnl=round(tot), clv=round(100 * cv[0] / cv[1], 2) if cv and cv[1] else None,
                                     clv_share=round(cv[1] / qty, 2) if cv and qty else None)
    out = dict(days=[days[0] if days else None, days[-1] if days else None, len(days)], seen=dict(seen), rows=rows,
               per_day={tg: round(sum(v.values()) / max(1, len(days))) for tg, v in DAY.items()})
    os.makedirs(os.path.join(ROOT, 'data', 'research'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'novig_maker_history.json'), 'w'), indent=0)
    print(out['days'], dict(seen))
    for k in sorted(rows):
        r = rows[k]
        if r['fills'] >= 200: print(f"{k:<58} fills {r['fills']:>8} events {r['events']:>6} risk ${r['risk']:>12,} (${r['risk_per_day']:>9,}/day) | settled ROI {str(r['roi']):>7}% (z {r['roi_z']}) | vs close {str(r['clv']):>6}c on {r['clv_share']}")


if __name__ == '__main__': main()
