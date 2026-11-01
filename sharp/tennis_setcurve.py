#!/usr/bin/env python3
"""Fair first-set price from the match price, and whether first-set markets price it right (Novig, Aug 3 onward).

1. Every settled Novig ATP/WTA MONEY market with a two-sided pregame mid in the hour before start, matched to its ESPN result
   (surname + date) for the first-set winner: how often the match favourite wins set 1, by match price. Compared with the
   independent-sets model (best of 3: match = s^2 (3 - 2s), solved for s).
2. Novig FIRST_SET_MONEYLINE markets with a pregame mid, paired with the same match's MONEY mid: the market's set-1 price for the
   match favourite vs the realised curve (train on the first two thirds of dates, grade the last third).
Prices are two-sided mids from taker fills (exchange_backtest.px_at); flat 1u at the mid, no fee. Usage: python3 sharp/tennis_setcurve.py"""
import os, sys, json, gzip, glob, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
import sharp.exchange_backtest as EB
from sharp.tennis_firstset import sur, ts
from novig_catalog import CDIR


def s_from_match(p):
    lo, hi = 0.0, 1.0
    for _ in range(50):
        m = (lo + hi) / 2
        if m * m * (3 - 2 * m) < p: lo = m
        else: hi = m
    return (lo + hi) / 2


def main():
    cat = {}
    for f in sorted(glob.glob(os.path.join(CDIR, '*.jsonl.gz'))):
        for l in gzip.open(f, 'rt'):
            if '"ATP"' not in l and '"WTA"' not in l: continue
            v = json.loads(l)
            if v.get('league') in ('ATP', 'WTA') and v.get('type') in ('MONEY', 'FIRST_SET_MONEYLINE') and v.get('start_ts') and len(v.get('outcomes') or {}) == 2:
                cat[v['market']] = v
    tape = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'novig', 'tape', '*.jsonl.gz'))):
        for l in gzip.open(f, 'rt'):
            i = l.find('"market": "'); mid = l[i + 11:i + 47] if i >= 0 else None
            if mid not in cat: continue
            r = json.loads(l); o0 = list(cat[mid]['outcomes'])[0]; y = r['outcome'] == o0
            tape[mid].append((ts(r['ts']), r['price'] if y else 1 - r['price'], r['price'] * r['qty'], 1 if y else -1))
    E = {}
    for l in open(os.path.join(ROOT, 'data', 'tennis', 'results.jsonl')):
        r = json.loads(l)
        for d in (0, -1, 1):
            day = (dt.date.fromisoformat(r['start'][:10]) + dt.timedelta(days=d)).isoformat()
            E.setdefault((day, sur(r['p1']), sur(r['p2'])), r); E.setdefault((day, sur(r['p2']), sur(r['p1'])), r)
    by_ev = collections.defaultdict(dict)
    for mid, v in cat.items(): by_ev[v.get('event') or mid][v['type']] = (mid, v)
    rows = []; miss = collections.Counter()
    for evk, d in by_ev.items():
        if 'MONEY' not in d: continue
        mid, v = d['MONEY']; st = v['start_ts'] / 1000; outs = list(v['outcomes'])
        names = [v['outcomes'][o] if isinstance(v['outcomes'], dict) else o for o in outs]
        L = sorted(x for x in tape.get(mid, []) if st - 3600 <= x[0] < st)
        p, two = EB.px_at(sorted(x for x in tape.get(mid, []) if x[0] < st), st - 60)
        if p is None or two != 2: miss['no match mid'] += 1; continue
        day = dt.datetime.fromtimestamp(st, dt.timezone.utc).date().isoformat()
        nm = [str(x) for x in names]
        e = E.get((day, sur(nm[0]), sur(nm[1])))
        if not e: miss['no ESPN result'] += 1; continue
        if not e.get('first_set_complete') or not e.get('first_set_winner'): miss['set 1 not complete'] += 1; continue
        o0_is_p1 = sur(nm[0]) == sur(e['p1'])
        fs0 = 1 if (e['first_set_winner'] == 'p1') == o0_is_p1 else 0          # outcome 0 won set 1
        rec = dict(start=st, pm=p, fs0=fs0, tour=v['league'])
        if 'FIRST_SET_MONEYLINE' in d:
            mid2, v2 = d['FIRST_SET_MONEYLINE']; o2 = list(v2['outcomes'])
            ps, two2 = EB.px_at(sorted(x for x in tape.get(mid2, []) if x[0] < st), st - 60)
            if ps is not None and two2 == 2:
                same = sur(str(v2['outcomes'][o2[0]] if isinstance(v2['outcomes'], dict) else o2[0])) == sur(nm[0])
                rec['ps'] = ps if same else 1 - ps
        rows.append(rec)
    print(f"[setcurve] {len(rows)} Novig tennis matches with a pregame match mid and an ESPN first-set result; skipped {dict(miss)}; {sum('ps' in r for r in rows)} also have a first-set mid")
    print("\n1. Match favourite's first-set win rate by match price (all matches), vs the independent-sets model")
    B = collections.defaultdict(list)
    for r in rows:
        fav = r['pm'] >= 0.5; pm = r['pm'] if fav else 1 - r['pm']; won = r['fs0'] if fav else 1 - r['fs0']
        B[min(int((pm - 0.5) / 0.05), 9)].append((pm, won, r.get('ps') if fav else (1 - r['ps'] if 'ps' in r else None)))
    curve = {}
    for b in sorted(B):
        L = B[b]; pm = sum(x for x, _, _ in L) / len(L); w = sum(y for _, y, _ in L) / len(L); se = math.sqrt(w * (1 - w) / len(L))
        ps = [z for _, _, z in L if z is not None]
        curve[b] = w
        print(f"  match {0.5 + 0.05 * b:.2f}-{0.55 + 0.05 * b:.2f}: n {len(L):>5}  match {pm:.3f}  set-1 won {w:.3f} (+/-{se:.3f})  model {s_from_match(pm):.3f}"
              + (f"  | set-1 market (n {len(ps)}) {sum(ps) / len(ps):.3f}" if ps else ''))
    print("\n2. Where Novig quoted both: set-1 market price vs the realised curve (train on the first 2/3 of dates, grade the last 1/3)")
    P = sorted([r for r in rows if 'ps' in r], key=lambda r: r['start'])
    if len(P) < 60: print('  too few'); return rows
    cut = P[int(len(P) * 2 / 3)]['start']
    tr = collections.defaultdict(list)
    for r in P:
        if r['start'] >= cut: continue
        fav = r['pm'] >= 0.5; pm = r['pm'] if fav else 1 - r['pm']
        tr[min(int((pm - 0.5) / 0.1), 4)].append(((r['ps'] if fav else 1 - r['ps']), r['fs0'] if fav else 1 - r['fs0']))
    gap = {b: sum(w for _, w in L) / len(L) - sum(p for p, _ in L) / len(L) for b, L in tr.items() if len(L) >= 30}
    print('  train gap (set-1 won minus set-1 priced, favourite) by match-price bucket:', {f"{0.5 + 0.1 * b:.1f}": round(g, 3) for b, g in gap.items()})
    for split in ('train', 'test'):
        res = []
        for r in P:
            if (r['start'] < cut) != (split == 'train'): continue
            fav = r['pm'] >= 0.5; pm = r['pm'] if fav else 1 - r['pm']; b = min(int((pm - 0.5) / 0.1), 4)
            if b not in gap or abs(gap[b]) < 0.02: continue
            back_fav = gap[b] > 0; pf = r['ps'] if fav else 1 - r['ps']; wf = r['fs0'] if fav else 1 - r['fs0']
            price = pf if back_fav else 1 - pf; won = wf if back_fav else 1 - wf
            if 0.03 < price < 0.97: res.append((1 - price) / price if won else -1.0)
        if res:
            mu = sum(res) / len(res); sd = (sum((x - mu) ** 2 for x in res) / max(1, len(res) - 1)) ** 0.5
            print(f"  {split}: n {len(res)}  ROI {100 * mu:+.1f}%  z {mu / (sd / math.sqrt(len(res))):.2f}")
    json.dump(dict(curve={f"{0.5 + 0.05 * b:.2f}": w for b, w in curve.items()}, n=len(rows)), open(os.path.join(ROOT, 'data', 'research', 'tennis_setcurve.json'), 'w'), indent=1)
    return rows


if __name__ == '__main__':
    main()
