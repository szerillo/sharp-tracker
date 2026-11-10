#!/usr/bin/env python3
"""Which paper offers would have filled (docs/maker_2026-11-10.md: "share of fills and out-of-sample CLV are measured" before any money).
For every offer in data/state/offers_paper.jsonl (sharp/offers_live.py: a resting bid 2c under Pinnacle's fair on a Kalshi or Novig side):
  filled = a trade printed on that market after the offer was logged and before the start in which the resting side was ours at our
           price or lower (a taker willing to sell at or under our bid; we would have been first in line at a better bid).
           Novig: the tape's outcome and price are the resting order's. Kalshi: a 'no' taker at yes price p sold yes at p (and the mirror).
  close  = Pinnacle's no-vig fair for the side at the same line, last quote in the hour before the start (data/<sport>/ticks).
Reads data/kalshi/trades5, trades5_soft and data/novig/trades5, trades5_soft. Writes data/state/offers_record.json for the board.
Usage: python3 sharp/offers_grade.py"""
import os, sys, json, gzip, glob, bisect, collections, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
PAPER = os.path.join(ROOT, 'data', 'state', 'offers_paper.jsonl'); OUT = os.path.join(ROOT, 'data', 'state', 'offers_record.json')
NOW = dt.datetime.now(dt.timezone.utc)
LIFE, OUR_USD = 3600, 100.0
OTH = dict(home='away', away='home', over='under', under='over')
def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp() if isinstance(s, str) else s / 1000.0
def imp(a): return 100.0 / (a + 100.0) if a > 0 else -a / (-a + 100.0)
def totlike(m): return 'total' in m or m.startswith('prop_') or 'tt_' in m


def main():
    if not os.path.exists(PAPER): print('[offers_grade] no offers logged yet'); return
    O = []
    for l in open(PAPER):
        try: O.append(json.loads(l))
        except Exception: pass
    days = sorted({o['logged'][:10] for o in O} | {o['start'][:10] for o in O})
    # trades: Novig by (market_id, side), Kalshi by ticker
    NV = collections.defaultdict(list); KA = collections.defaultdict(list); polled = set()
    for sub in ('trades5', 'trades5_soft'):
        for d in days:
            p = os.path.join(ROOT, 'data', 'novig', sub, f'{d}.jsonl.gz')
            if os.path.exists(p):
                for l in lines(p):
                    try: t = json.loads(l)
                    except Exception: continue
                    polled.add(t.get('market_id'))
                    if t.get('side_if_taker'): NV[(t['market_id'], t['side_if_taker'])].append((ts(t['ts']), float(t['price']), float(t.get('usd') or 0)))
            p = os.path.join(ROOT, 'data', 'kalshi', sub, f'{d}.jsonl.gz')
            if os.path.exists(p):
                for l in lines(p):
                    try: t = json.loads(l)
                    except Exception: continue
                    KA[t['ticker']].append((ts(t['ts']), float(t['yes_price']), float(t.get('count') or 0), t.get('taker_side')))
    # Pinnacle closes per sport, only for the offers' games
    need = collections.defaultdict(set)
    for o in O: need[o['sport']].add(o['event_id'])
    PIN = collections.defaultdict(lambda: ([], []))
    for sp, evs in need.items():
        for d in days:
            p = os.path.join(ROOT, 'data', sp, 'ticks', f'{d}.jsonl.gz')
            if not os.path.exists(p): continue
            for l in lines(p):
                if '"Pinnacle"' not in l: continue
                try: x = json.loads(l)
                except Exception: continue
                if str(x.get('event_id')) not in evs or x.get('american') is None: continue
                m = x['market']; k = (str(x['event_id']), m, x.get('side'), x.get('line'), x.get('participant') if m.startswith('prop_') else None)
                PIN[k][0].append(ts(x['ts'])); PIN[k][1].append(imp(x['american']))
    for k, (T, P) in PIN.items():
        o_ = sorted(range(len(T)), key=T.__getitem__); PIN[k] = ([T[i] for i in o_], [P[i] for i in o_])
    def last(k, t, age):
        v = PIN.get(k)
        if not v: return None
        i = bisect.bisect_right(v[0], t) - 1
        return v[1][i] if i >= 0 and t - v[0][i] <= age else None
    rows = []
    for o in O:
        st = ts(o['start']); t0 = ts(o['logged']); started = st <= NOW.timestamp()
        fills = []; watched = False
        if o['venue'] == 'Novig' and o.get('market_id'):
            watched = o['market_id'] in polled
            fills = [(t, p, u) for t, p, u in NV.get((o['market_id'], o['side']), []) if t0 < t < st and p <= o['offer'] + 1e-9]
        elif o['venue'] == 'Kalshi' and o.get('ticker'):
            watched = o['ticker'] in KA
            ours_yes = (o['yes'] == o['side']) if o.get('yes') else o['side'] in ('over', 'home')
            for t, yp, c, tk in KA.get(o['ticker'], []):
                if not t0 < t < st: continue
                q = yp if tk == 'no' else 1 - yp; side_yes = tk == 'no'          # the resting side bought yes when the taker sold it
                if side_yes == ours_yes and q <= o['offer'] + 1e-9: fills.append((t, q, q * c))
        m = o['market']; pk = (o['key'].split('|')[-1] or None) if m.startswith('prop_') else None          # the participant key the ticks use
        key = (o['event_id'], m, o['side'], o.get('line'), pk)
        a = last(key, st, 3600); b = last((o['event_id'], m, OTH[o['side']], o.get('line') if (o.get('line') is None or totlike(m)) else -o['line'], pk), st, 3600)
        close = a / (a + b) if a and b else None
        # 11/10: the headline counts a fill only inside the order's life (LIFE after it was logged: the scan reprices each cycle, so an
        # old bid would have been moved), and at most OUR_USD of it (our size, not the whole print). filled_any = any time before the start.
        any_ = bool(fills); fills = [f for f in fills if f[0] <= t0 + LIFE]
        rows.append(dict(key=o['key'], venue=o['venue'], sport=o['sport'], market=m, started=started, watched=watched, filled=bool(fills), filled_any=any_, fill_usd=round(min(OUR_USD, sum(f[2] for f in fills))),
                         first_fill_min=round((fills[0][0] - t0) / 60) if fills else None, offer=o['offer'], fair=o['fair'], close=round(close, 4) if close else None,
                         clv=round(100 * (close - o['offer']), 2) if close else None))
    def summ(L):
        L = [r for r in L if r['started'] and r['watched']]
        F = [r for r in L if r['filled']]; N = [r for r in L if not r['filled']]
        cv = lambda X: (round(sum(r['clv'] for r in X if r['clv'] is not None) / max(1, sum(1 for r in X if r['clv'] is not None)), 2), sum(1 for r in X if r['clv'] is not None))
        return dict(offers=len(L), filled=len(F), filled_any=sum(1 for r in L if r['filled_any']), fill_rate=round(len(F) / len(L), 3) if L else None, usd_per_fill=round(sum(r['fill_usd'] for r in F) / len(F)) if F else None,
                    clv_filled=cv(F)[0] if F else None, clv_filled_n=cv(F)[1], clv_unfilled=cv(N)[0] if N else None, clv_unfilled_n=cv(N)[1])
    grp = lambda m: 'props' if m.startswith('prop_') else 'team totals' if 'tt_' in m else 'period lines' if m[:2] in ('1h', '1q', '1p') else 'game lines'
    rec = dict(updated=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), logged=len(O), not_started=sum(1 for r in rows if not r['started']), unwatched=sum(1 for r in rows if r['started'] and not r['watched']),
               all=summ(rows), by={f"{v} {g}": summ([r for r in rows if r['venue'] == v and grp(r['market']) == g]) for v in ('Novig', 'Kalshi') for g in ('props', 'team totals', 'period lines', 'game lines')})
    rec['by'] = {k: v for k, v in rec['by'].items() if v['offers']}
    # ProphetX has no trade tape; each quote row carries the market's matched total (extra.filled), so the rise between pulls is what traded
    try:
        PX = collections.defaultdict(dict)
        for f in glob.glob(os.path.join(ROOT, 'data', '*', 'ticks_px', '2026-*.jsonl.gz')):
            sp = f.split(os.sep)[-3]; day = os.path.basename(f)[:10]
            for l in lines(f):
                try: x = json.loads(l)
                except Exception: continue
                fl = (x.get('extra') or {}).get('filled')
                if fl is None: continue
                k = (sp, grp(x['market']), day, (x['extra'].get('px_event'), x['extra'].get('market_id')))
                a = PX[k]; a['lo'] = min(a.get('lo', fl), fl); a['hi'] = max(a.get('hi', fl), fl)
        agg = collections.defaultdict(lambda: [0, 0, 0.0, set()])
        for (sp, g_, day, mk), a in PX.items():
            z = agg[(sp, g_)]; z[0] += 1; z[1] += 1 if a['hi'] > a['lo'] else 0; z[2] += a['hi'] - a['lo']; z[3].add(day)
        rec['prophetx_flow'] = [dict(sport=k[0], group=k[1], markets=v[0], traded=v[1], matched=round(v[2]), days=len(v[3]), per_day=round(v[2] / max(1, len(v[3])))) for k, v in sorted(agg.items(), key=lambda kv: -kv[1][2])]
    except Exception as e: print('[offers_grade] prophetx flow failed:', e)
    json.dump(rec, open(OUT, 'w'), separators=(',', ':'))
    print(f"[offers_grade] {len(O)} offers logged; started and watched {rec['all']['offers']}, filled {rec['all']['filled']} ({rec['all']['fill_rate']}); CLV filled {rec['all']['clv_filled']} on {rec['all']['clv_filled_n']}, unfilled {rec['all']['clv_unfilled']} on {rec['all']['clv_unfilled_n']}; not watched {rec['unwatched']}")


if __name__ == '__main__': main()
