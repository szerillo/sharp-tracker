#!/usr/bin/env python3
"""Grade the paper offers (sharp/offers_live.py) from Novig's public trade file, so no Novig offer is ungradeable (Sean 11/12: 5,290 of
the logged offers could not be graded from our own tape, which only follows some markets).

A Novig offer (buy the side at `offer`, logged at `logged`) is filled by any Novig maker trade on the same market and outcome at or under
the offer price, between `logged` and the earlier of logged + 1 hour and the start, up to $100 at risk. Trades under the offer are
trade-throughs; trades at exactly the offer count too, because offers_live only logs a bid that improves Novig's best bid (first in line).
Close edge = Pinnacle no-vig at the start minus the offer (cents).
Not gradeable here, and said so in the record: Novig offers logged without market/outcome ids; Kalshi offers (most were logged without a
Kalshi ticker, and resting on Kalshi already tested negative after its fee); ProphetX offers (ProphetX publishes no trade feed).
Writes data/state/offers_public_grades.json (per offer, cached once the game has started and the files are in) and
data/state/offers_record_public.json. Runs on a GitHub runner (data.novig.com). Usage: python3 sharp/offers_grade_public.py"""
import os, sys, json, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
import maker_test as M
import novig_paper_quoter as Q
LOG = os.path.join(ROOT, 'data', 'state', 'offers_paper.jsonl'); G = os.path.join(ROOT, 'data', 'state', 'offers_public_grades.json')
OUT = os.path.join(ROOT, 'data', 'state', 'offers_record_public.json')
LIFE, USD = 3600, 100.0


def main():
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    O = []
    for l in open(LOG):
        try: O.append(json.loads(l))
        except Exception: pass
    graded = json.load(open(G)) if os.path.exists(G) else {}
    why = collections.Counter(); todo = []
    for r in O:
        st = M.ts_(r['start'])
        if st > now: why['not started'] += 1; continue
        if r['venue'] == 'Kalshi': why['Kalshi: not graded (no ticker on most; resting on Kalshi tested negative)'] += 1; continue
        if r['venue'] == 'ProphetX': why['ProphetX: no public trade feed'] += 1; continue
        if not (r.get('market_id') and r.get('outcome_id')): why['Novig: logged without market/outcome ids'] += 1; continue
        if r['key'] in graded: why['Novig: graded'] += 1; continue
        if now - st < 36 * 3600: why['Novig: waiting for the trade file'] += 1; continue      # the day's file publishes after midnight ET
        todo.append(r)
    if todo:
        d0 = min(r['start'][:10] for r in todo); d1 = max(r['start'][:10] for r in todo)
        start, pin, nvb, K2NV, KSP = Q.load_tape(d0, d1)
        want = {(r['market_id'], r['outcome_id']) for r in todo}
        trades, files = Q.load_trades(d0, d1, want)
        for r in todo:
            st = M.ts_(r['start']); t0 = M.ts_(r['logged']); t1 = min(t0 + LIFE, st); b = float(r['offer'])
            rem = USD / b; c = 0.0; first_t = None; how = None
            for (t, px, qty) in trades.get((r['market_id'], r['outcome_id']), []):
                if t < t0 or t > t1 or px > b + 1e-4: continue
                n = min(rem, qty); rem -= n; c += n
                if first_t is None: first_t = t; how = 'through' if px < b - 1e-4 else 'touch'
                if rem <= 1e-9: break
            p = r['key'].split('|'); line = float(p[4]) if p[4] not in ('', 'None') else None
            k = (p[1], p[2], p[3], line, p[5] if len(p) > 5 and p[5] else None)
            fc = Q.fair_loose(pin, k, st, 3600)
            graded[r['key']] = dict(group=Q.grp(r['market']), sport=r['sport'], offer=b, filled=c > 0, contracts=round(c, 2), usd=round(c * b, 2),
                                    first_fill=Q.iso(first_t) if first_t else None, how=how, e_close=round(fc - b, 4) if fc is not None else None,
                                    start=r['start'], files=bool(files))
        json.dump(graded, open(G, 'w'), separators=(',', ':'))
        why['Novig: graded'] += len(todo)
    def agg(rows):
        f = [x for x in rows if x['filled']]; u = [x for x in rows if not x['filled']]
        m = lambda L: round(100 * sum(x['e_close'] for x in L if x['e_close'] is not None) / max(1, sum(1 for x in L if x['e_close'] is not None)), 2) if any(x['e_close'] is not None for x in L) else None
        return dict(graded=len(rows), filled=len(f), fill_rate=round(len(f) / len(rows), 3) if rows else None, usd_filled=round(sum(x['usd'] for x in f)),
                    avg_fill_usd=round(sum(x['usd'] for x in f) / len(f), 2) if f else None, close_edge_filled=m(f), close_edge_unfilled=m(u))
    V = list(graded.values())
    rec = dict(updated=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), logged=len(O), status=dict(why), all=agg(V),
               groups={g: agg([x for x in V if x['group'] == g]) for g in sorted({x['group'] for x in V})})
    json.dump(rec, open(OUT, 'w'), indent=0)
    print(f"[offers public] {dict(why)}; all: {rec['all']}")


if __name__ == '__main__': main()
