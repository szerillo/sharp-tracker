#!/usr/bin/env python3
"""Tennis match-winner flow tests on Kalshi's settled history (KXATPMATCH / KXWTAMATCH), the same tests run on the team sports
(docs/flow_split_2026-10-31.md): big vs small money, and following the price move since the first two-sided price, both at the ask.

Start time = the ESPN result (surname + date); trades after it are in play and dropped. One row per match (the first player's market;
the other is its mirror). Train = first two thirds of dates, test = the last third. Flat 1u, no Kalshi fee (about 1.5-2c a contract).
Usage: python3 sharp/tennis_flow.py"""
import os, sys, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp import tennis_firstset as T


def build():
    M = T.load_markets(); TR = {}
    for s in T.MATCH: TR.update(T.load_trades(s))
    S = T.espn_starts()
    ev = collections.defaultdict(dict)
    for tk, m in M.items():
        if m['series'] in T.MATCH: ev[m['event_ticker'].split('-')[1]][tk] = m
    rows = []; miss = collections.Counter()
    for code, d in ev.items():
        if len(d) != 2: miss['not a pair'] += 1; continue
        names = {tk: m.get('sub') or '' for tk, m in d.items()}; a, b = [T.sur(n) for n in names.values()]
        cd = T.code_date(code); hit = None
        for dd in ((cd + dt.timedelta(days=k)).isoformat() for k in (0, -1, 1)) if cd else []:
            hit = S.get((dd, a, b))
            if hit: break
        if not hit: miss['no ESPN start'] += 1; continue
        start, _, rec = hit
        if rec.get('walkover'): continue
        tk, m = next(iter(d.items()))
        if m.get('result') not in ('yes', 'no'): continue
        pre = [x for x in TR.get(tk, []) if x[0] < start]
        if len(pre) < 5: miss['thin'] += 1; continue
        rows.append(dict(code=code, start=start, won=1 if m['result'] == 'yes' else 0, set1=pre, match=[], tour='atp' if m['series'].startswith('KXATP') else 'wta'))
    return rows, miss


def main():
    rows, miss = build(); rows.sort(key=lambda r: r['start'])
    print(f"[tennis_flow] {len(rows)} Kalshi match markets with an ESPN start and 5+ pregame fills; skipped {dict(miss)}")
    if len(rows) < 60: return
    cut = rows[int(len(rows) * 2 / 3)]['start']; split = lambda r: 'train' if r['start'] < cut else 'test'
    out = {}
    for en_name, en in (('T-1h', 3600), ('T-15m', 900)):
        for th in (250, 500, 1000):
            B = {'train': [], 'test': []}
            for r in rows:
                E = r['start'] - en; pre = [x for x in r['set1'] if x[0] < E]
                bn = sum(u * d for _, _, u, d in pre if u >= th); sn = sum(u * d for _, _, u, d in pre if u <= 50)
                if abs(bn) < th or sn == 0 or (bn > 0) == (sn > 0): continue
                B[split(r)].append(T.bet(r, 1 if bn > 0 else -1, E, 'ask'))
            out[f'bigsmall {en_name} ${th}'] = {k: T.stats(v) for k, v in B.items()}
        for mv in (3, 5):
            for kind in ('follow', 'fade'):
                B = {'train': [], 'test': []}
                for r in rows:
                    E = r['start'] - en; p1 = T.price(r['set1'], E)
                    first = r.get('_first', 'x')
                    if first == 'x':
                        first = None; ly = ln = None
                        for x in r['set1']:          # first moment a yes-buy and a no-buy printed within 2h: mid of the two
                            if x[3] > 0: ly = x
                            else: ln = x
                            if ly and ln and abs(ly[0] - ln[0]) <= 7200: first = (ly[1] + ln[1]) / 2; break
                        r['_first'] = first
                    if p1 is None or first is None or abs(100 * (p1 - first)) < mv: continue
                    d = (1 if p1 > first else -1) * (1 if kind == 'follow' else -1)
                    B[split(r)].append(T.bet(r, d, E, 'ask'))
                out[f'move {kind} {mv}+ pts since open, {en_name}'] = {k: T.stats(v) for k, v in B.items()}
    for k, v in out.items(): print(f"  {k:40} train {v['train']}  TEST {v['test']}")
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'tennis_flow.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
