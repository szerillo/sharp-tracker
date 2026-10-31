#!/usr/bin/env python3
"""Big money vs small money on the exchanges (Sean, 10/31): the exchange version of "money % vs ticket %", built from real fill sizes.

For every settled two-outcome game market on Kalshi (data/kalshi/history) and Novig (data/novig/tape + catalog), pregame taker fills only:
  big_net(T)   = net taker dollars at or above a size threshold (250 / 500 / 1000), signed toward the yes side, before time T
  small_net(T) = net taker dollars at or below $50, same sign convention
Fill size = risk-equivalent dollars, contracts x min(p, 1-p) (stake on the dog side, to-win on the favorite side), so heavy favorites
are not inflated by having to lay a big price (Sean, 10/31). The first run (stake dollars) is kept in data/state/flow_split_stake.json.
Signals, evaluated at an entry time T (T-6h, T-1h, T-15m):
  DIV  big money and small money on opposite sides, |big_net| >= threshold  -> bet the big side
  BIG  big money net on one side by >= threshold, small money ignored      -> bet the big side
One bet per game x market type (the strongest |big_net| across tickers / strikes). Entry price = two-sided mid at T (last yes-buy and
last no-buy within 2h; taker fills print at the ask so a one-sided tape is skipped). Graded on the result (flat 1u ROI at the entry
mid, no fee) and on CLV = the same side's mid at kickoff minus the entry mid, in points.
Writes data/state/flow_split.json and prints the table. Usage: python3 sharp/flow_split.py"""
import os, sys, json, gzip, glob, math, re, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
import sharp.exchange_backtest as EB
from sharp import sports as SP
from novig_catalog import CDIR

SMALL = 50.0; THRESH = (250.0, 500.0, 1000.0); ENTRIES = {'T-6h': 6 * 3600, 'T-1h': 3600, 'T-15m': 900}
NOVIG_TYPES = {'MONEY': 'ml', 'SPREAD': 'spread', 'TOTAL': 'total'}
NOVIG_LEAGUES = {'NFL': 'nfl', 'NBA': 'nba', 'NHL': 'nhl', 'MLB': 'mlb', 'NCAAF': 'cfb', 'UFC': 'mma', 'WNBA': 'wnba', 'NCAAB': 'cbb'}


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def market_rows():
    """-> list of (venue, sport, mtype, game_key, start, result_yes, trades[(t, p_yes, usd, dir)])"""
    out = []
    # Kalshi: reuse the backtest's market/event resolution
    mk = {}
    for l in open(os.path.join(ROOT, 'data', 'kalshi', 'history', 'markets.jsonl')):
        r = json.loads(l); mk[r['ticker']] = r
    sched = EB.Sched()
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'kalshi', 'history', 'trades', '*.jsonl.gz'))):
        series = os.path.basename(f)[:-9]; pre = next((k for k in EB.KSERIES_SPORT if series.startswith(k)), None)
        if not pre: continue
        sport = EB.KSERIES_SPORT[pre]; mtype = {'GAME': 'ml', 'SPREAD': 'spread', 'TOTAL': 'total', 'FIGHT': 'ml'}.get(series[len(pre):])
        if not mtype: continue
        by = collections.defaultdict(list)
        try:
            for l in gzip.open(f, 'rt'):
                r = json.loads(l); y = r['taker'] == 'yes'
                by[r['ticker']].append((ts(r['ts']), r['yes'], r['n'] * min(r['yes'], 1 - r['yes']), 1 if y else -1))
        except (EOFError, OSError, ValueError): pass
        for tk, L in by.items():
            m = mk.get(tk)
            if not m or m.get('result') not in ('yes', 'no') or tk.endswith('-TIE'): continue
            pe = SP.kalshi_event(m['event_ticker'].split('-', 1)[1])
            if not pe: continue
            g = sched.kalshi(sport, pe[0], pe[1], home_first=sport in ('epl', 'laliga', 'bundesliga', 'seriea', 'ligue1', 'mls', 'ucl', 'mma'))
            if not g: continue
            out.append(('Kalshi', sport, mtype, f"{sport}|{g['start'][:10]}|{g['away']}@{g['home']}|{mtype}", ts(g['start']), 1 if m['result'] == 'yes' else 0, L))
    # Novig: slim catalog (two-outcome game markets in the leagues above)
    cat = {}
    for f in sorted(glob.glob(os.path.join(CDIR, '*.jsonl.gz'))):
        for l in gzip.open(f, 'rt'):
            if '"result"' not in l: continue
            v = json.loads(l)
            if v.get('league') not in NOVIG_LEAGUES or v.get('type') not in NOVIG_TYPES or not v.get('start_ts') or len(v.get('outcomes') or {}) != 2: continue
            o = list(v['outcomes']); res = v['result'].get(o[0])
            if res not in ('WIN', 'LOSS'): continue
            cat[v['market']] = (NOVIG_LEAGUES[v['league']], NOVIG_TYPES[v['type']], v['start_ts'] / 1000, o[0], 1 if res == 'WIN' else 0, v.get('event') or v['market'])
    tape = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'novig', 'tape', '*.jsonl.gz'))):
        for l in gzip.open(f, 'rt'):
            i = l.find('"market": "'); mid = l[i + 11:i + 47] if i >= 0 else None
            if mid not in cat: continue
            r = json.loads(l); sp, mt, st, yes, res, ev = cat[mid]
            y = r['outcome'] == yes; p = r['price'] if y else round(1 - r['price'], 4)
            tape[mid].append((ts(r['ts']), p, r['qty'] * min(r['price'], 1 - r['price']), 1 if y else -1))      # risk-equivalent size
    for mid, L in tape.items():
        sp, mt, st, yes, res, ev = cat[mid]
        out.append(('Novig', sp, mt, f"{sp}|{ev}|{mt}", st, res, L))
    return out


def evaluate(rows):
    res = {}
    for venue in ('Kalshi', 'Novig'):
        for entry, sec in ENTRIES.items():
            for th in THRESH:
                for kind in ('DIV', 'BIG'):
                    best = {}
                    for v, sp, mt, gk, start, ry, L in rows:
                        if v != venue: continue
                        E = start - sec; pre = sorted(x for x in L if x[0] < E)
                        if len(pre) < 5: continue
                        bn = sum(u * d for t, p, u, d in pre if u >= th); sn = sum(u * d for t, p, u, d in pre if u <= SMALL)
                        if abs(bn) < th: continue
                        if kind == 'DIV' and (sn == 0 or (bn > 0) == (sn > 0)): continue
                        px, two = EB.px_at(pre, E)
                        if px is None or two != 2: continue
                        allpre = sorted(x for x in L if x[0] < start); cl, two_c = EB.px_at(allpre, start)
                        d = 1 if bn > 0 else -1; price = px if d > 0 else 1 - px
                        if not (0.03 < price < 0.97): continue
                        won = ry if d > 0 else 1 - ry
                        clv = None if cl is None or two_c != 2 else 100 * ((cl if d > 0 else 1 - cl) - price)
                        rec = dict(sport=sp, mtype=mt, price=price, won=won, roi=(1 - price) / price if won else -1.0, clv=clv, big=abs(bn))
                        if gk not in best or rec['big'] > best[gk]['big']: best[gk] = rec
                    B = list(best.values())
                    if not B: continue
                    roi = [b['roi'] for b in B]; mu = sum(roi) / len(roi); sd = (sum((x - mu) ** 2 for x in roi) / max(1, len(roi) - 1)) ** 0.5
                    cl = [b['clv'] for b in B if b['clv'] is not None]
                    by_sport = collections.defaultdict(list)
                    for b in B: by_sport[b['sport']].append(b)
                    res[f"{venue}|{entry}|{int(th)}|{kind}"] = dict(n=len(B), win=round(sum(b['won'] for b in B) / len(B), 3), implied=round(sum(b['price'] for b in B) / len(B), 3),
                                                                     roi=round(100 * mu, 2), z=round(mu / (sd / math.sqrt(len(B))), 2) if len(B) > 2 and sd > 0 else None,
                                                                     clv=round(sum(cl) / len(cl), 2) if cl else None, clv_n=len(cl),
                                                                     by_sport={k: dict(n=len(x), roi=round(100 * sum(y['roi'] for y in x) / len(x), 1)) for k, x in sorted(by_sport.items(), key=lambda kv: -len(kv[1]))})
    return res


def main():
    rows = market_rows(); print(f"[flow_split] {len(rows)} settled markets ({sum(1 for r in rows if r[0] == 'Kalshi')} Kalshi, {sum(1 for r in rows if r[0] == 'Novig')} Novig)", flush=True)
    res = evaluate(rows)
    json.dump(res, open(os.path.join(ROOT, 'data', 'state', 'flow_split.json'), 'w'), indent=1)
    print(f"{'venue':7} {'entry':6} {'size':>5} {'kind':4} {'games':>6} {'win':>6} {'impl':>6} {'ROI':>7} {'z':>6} {'CLV pts':>8}  by sport")
    for k, r in res.items():
        v, e, th, kind = k.split('|')
        bs = ', '.join(f"{s} {x['n']}/{x['roi']:+.0f}%" for s, x in list(r['by_sport'].items())[:5])
        print(f"{v:7} {e:6} {th:>5} {kind:4} {r['n']:>6} {r['win']:>6} {r['implied']:>6} {r['roi']:>+6.1f}% {str(r['z']):>6} {str(r['clv']):>8}  {bs}")


if __name__ == '__main__':
    main()
