#!/usr/bin/env python3
"""Running per-account record for the Polymarket sharp list, so the list can be rebuilt on GitHub without the 22M-trade history.

data/research/poly_agg.json.gz holds, per account: CLV sum (points vs Polymarket's two-sided close), fill count, game count and ROI sum,
over $100+ (risk-equivalent) pregame fills on settled game moneylines / spreads / totals with $10k+ volume (UFC excluded), plus the
condition ids already counted and the last start date covered. Each market is counted once, so adding a month never double counts.
  --init     build it from the local history pull (loggers/polymarket_history.py catalog + trades)
  --update   fetch settled game markets that started after the last covered date (Gamma, newest first), pull their public trades,
             add them; then write data/state/poly_sharps_list.json (top 200 by mean CLV, 30+ fills on 15+ games), same method as
             sharp/poly_rescore.py. Run monthly by .github/workflows/poly_rescore.yml.
Usage: python3 sharp/poly_agg.py --init | --update"""
import os, sys, json, gzip, time, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
import sharp.flow_volume as V
from sharp.sharp_accounts2 import Px
AGG = os.path.join(ROOT, 'data', 'research', 'poly_agg.json.gz'); LIST = os.path.join(ROOT, 'data', 'state', 'poly_sharps_list.json')
MIN_VOL = 10000.0


def add_market(A, c, st, L):
    """L: sorted [(t, p_yes, usd, dir, wallet)] pregame. Adds the market's $100+ fills to A['w'] once."""
    if c['cond'] in A['done'] or len(L) < 5: return
    P = Px([x[:4] for x in L]); cl = P.at(st)
    A['done'][c['cond']] = 1
    if cl is None: return
    ry = 1 if c['winner'] == c['outcomes'][0] else 0; seen = set()
    for t, py, usd, d, w in L:
        if usd < 100 or not w: continue
        price = py if d > 0 else 1 - py; won = ry if d > 0 else 1 - ry
        x = A['w'].setdefault(w, [0.0, 0, 0, 0.0])
        x[0] += 100 * ((cl if d > 0 else 1 - cl) - price); x[1] += 1; x[3] += (1 - price) / price if won else -1.0
        if w not in seen: x[2] += 1; seen.add(w)
    A['through'] = max(A.get('through') or '', dt.datetime.fromtimestamp(st, dt.timezone.utc).strftime('%Y-%m-%d'))


def write_list(A):
    W = A['w']; sc = {w: x for w, x in W.items() if x[1] >= 30 and x[2] >= 15}
    ranked = sorted(sc, key=lambda w: -sc[w][0] / sc[w][1])
    out = dict(built=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), history_through=A.get('through'), scored=len(sc),
               method='mean CLV vs Polymarket close of $100+ pregame fills, 30+ fills on 15+ games, top 200 (sharp/poly_agg.py)',
               accounts=[dict(w=w, rank=i + 1, clv=round(sc[w][0] / sc[w][1], 2), roi=round(100 * sc[w][3] / sc[w][1], 1), fills=sc[w][1], games=sc[w][2])
                         for i, w in enumerate(ranked[:200])])
    json.dump(out, open(LIST, 'w'), indent=0)
    print(f"[poly_agg] list: {len(sc)} accounts scored through {A.get('through')}, top 200 (CLV floor {out['accounts'][-1]['clv'] if out['accounts'] else None})")


def save(A):
    with gzip.open(AGG, 'wt') as f: json.dump({k: ({w: [round(x[0], 3), x[1], x[2], round(x[3], 3)] for w, x in v.items()} if k == 'w' else v) for k, v in A.items()}, f, separators=(',', ':'))


def init():
    A = dict(w={}, done={}, through=None)
    for i, (c, st) in enumerate(V.poly_markets()):
        if c['tag'] == 'ufc' or c['volume'] < MIN_VOL: continue
        add_market(A, c, st, V.poly_trades(c, st))
        if i % 5000 == 0: print(f"[poly_agg] {i}", flush=True)
    save(A); write_list(A)


def update():
    import polymarket_history as PH
    A = json.load(gzip.open(AGG, 'rt')); since = A.get('through') or '2026-11-01'
    T0 = time.time(); n = 0; cutoff = time.time() - 6 * 3600          # settled: started 6h+ ago
    for tag in [t for t in PH.TAGS if t != 'ufc']:
        off = 0; stop = False
        while not stop and off < 20000:
            E = PH.g(f"{PH.G}/events?tag_slug={tag}&closed=true&limit=100&offset={off}&order=startDate&ascending=false")
            if not E: break
            for e in E:
                m_ = PH.GAME.match(e.get('slug') or '')
                if not m_: continue
                if m_.group(4) < since: stop = True; break           # newest first: everything older is already counted
                for m in e.get('markets') or []:
                    mk = PH.TYPES.get(m.get('sportsMarketType'))
                    if not mk or m['conditionId'] in A['done'] or float(m.get('volume') or 0) < MIN_VOL or not m.get('gameStartTime'): continue
                    try: outs = json.loads(m['outcomes']); px = [float(x) for x in json.loads(m.get('outcomePrices') or '[]')]
                    except Exception: continue
                    if len(outs) != 2 or sorted(px) != [0.0, 1.0]: continue
                    st = dt.datetime.fromisoformat(m['gameStartTime'].replace(' ', 'T').replace('+00', '+00:00')).timestamp()
                    if st > cutoff: continue
                    c = dict(tag=tag, cond=m['conditionId'], outcomes=outs, winner=outs[px.index(1.0)], start=m['gameStartTime'], volume=float(m.get('volume') or 0))
                    PH.trades_for(c['cond']); L = V.poly_trades(c, st); add_market(A, c, st, L); n += 1
                    try: os.remove(os.path.join(V.PH, 'trades', f"{c['cond']}.jsonl.gz"))
                    except OSError: pass
            off += len(E)
            if len(E) < 100: break
        print(f"[poly_agg] {tag}: {n} markets added so far, {time.time() - T0:.0f}s", flush=True)
    save(A); write_list(A)


if __name__ == '__main__':
    init() if '--init' in sys.argv else update()
