#!/usr/bin/env python3
"""List item 2 (Sean 11/6): the system-vs-sharp hold rule on all the history we have.
Every system pick from the replays (sharp/rule_replay.py rules, sharp/nfl_replay.py rules and its generic market bets) on games covered
by our Polymarket trade history (8/29/2026 onward) is matched to the Polymarket markets on the same game and market. For each pick: the
pregame dollars that top Polymarket accounts put on the pick's side and against it. Accounts:
  oos  - top 200 by CLV against Pinnacle's no-vig close on markets BEFORE the cut (first two thirds of the window); picks after the cut.
  live - the live sharp list (data/polymarket/_sharp_state.json). It was built with today's data, so it looks ahead; context only.
A pick is 'opposed' when the accounts' net is $500+ against it, 'backed' when $500+ with it, otherwise 'no sharp view'.
Graded at Pinnacle's close (the replays' grade). Writes data/research/sys_vs_poly.json. Usage: python3 sharp/sys_vs_poly.py"""
import os, sys, json, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.rule_replay as RR, sharp.nfl_replay as NR, sharp.poly_pinnacle as PP, sharp.flow_volume as V
OUT = os.path.join(ROOT, 'data', 'research', 'sys_vs_poly.json')
THR = 500.0


class GT(tuple):
    pass


_grade = RR.grade
def grade(g, market, side, line=None):
    r = _grade(g, market, side, line)
    if r is None: return None
    r = GT(r); r.meta = (g, market, side); return r


class DD(collections.defaultdict):
    ALL = []
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        if self.default_factory is list: DD.ALL.append(self)


class C:          # stand-in for the collections module inside the replays, so their hit lists are kept
    defaultdict = DD
    def __getattr__(self, k): return getattr(collections, k)


LIVE_RULES = ('nhl_pl_fav_gap', 'nhl_pl_fav_strong_opp', 'nhl_pl_dog_bigml', 'nhl_early_home_fav_qual', 'nba_under_good_home_over', 'nba_1h_under_hot_over',
              'cbb_under_good_over_drop', 'cfb_road_dog_low_total', 'cfb_road_streak_dog', '(the rule)', '-13 or worse', 'visitor off 8+ days', 'A5 mnf')


def picks():
    RR.grade = grade; RR.collections = C(); NR.collections = C()
    def ro(f, mode='r', *a, **k):              # the replays write their outputs and caches; send writes to /dev/null so nothing is touched
        return open(os.devnull if any(c in mode for c in 'wa') else f, mode, *a, **k)
    RR.open = NR.open = ro
    import builtins
    _p = builtins.print; builtins.print = lambda *a, **k: None
    try:
        RR.main(); NR.main()
    finally:
        builtins.print = _p
    P = []
    for d in DD.ALL:
        for name, hits in d.items():
            if not isinstance(name, str): continue
            for h in hits:
                if not isinstance(h, tuple) or len(h) != 2 or not isinstance(h[1], GT): continue
                g, mk, side = h[1].meta; won, dec = h[1][0], h[1][1]
                live = any(k in name for k in LIVE_RULES) and 'control' not in name and 'did NOT' not in name
                P.append(dict(rule=name, live=live, g=g, mk=mk, side=side, won=won, dec=dec))
    return P


def main():
    P = picks()
    MK = V.poly_markets(); t0 = MK[0][1]; cut = MK[int(len(MK) * 2 / 3)][1]
    P = [p for p in P if p['g']['start'].timestamp() >= t0 - 86400]
    print('replay picks inside the Polymarket window:', len(P), ' live-rule picks:', sum(p['live'] for p in P), flush=True)
    I = PP.index()
    byg = collections.defaultdict(list)          # game id -> [(market, side0, catalog row, start)]
    W = collections.defaultdict(lambda: [0.0, 0])
    for i, (c, st) in enumerate(MK):
        m = PP.match(I, c, st)
        if not m: continue
        g, side0 = m
        byg[g['id']].append((c, st, side0))
        if st < cut:
            fp = PP.fair(c, g, side0)
            if fp is None: continue
            for t, py, usd, d, w in V.poly_trades(c, st):
                if usd < PP.MIN_USD or not w: continue
                price = py if d > 0 else 1 - py; f = fp if d > 0 else 1 - fp
                x = W[w]; x[0] += 100 * (f - price); x[1] += 1
    top = set(sorted([w for w, x in W.items() if x[1] >= 30], key=lambda w: -W[w][0] / W[w][1])[:200])
    live = set(json.load(open(os.path.join(ROOT, 'data', 'polymarket', '_sharp_state.json'))))
    print('scored accounts', len(W), 'top', len(top), 'live list', len(live), flush=True)
    rows = []
    for p in P:
        g = p['g']; M = [x for x in byg.get(g['id'], []) if x[0]['market'] == p['mk']]
        if not M: continue
        net = dict(oos=0.0, live=0.0); vol = 0.0
        for c, st, side0 in M:
            if p['mk'] == 'total': s0 = 'over' if PP.o_is_over(c) else 'under'
            else: s0 = side0
            sign0 = 1 if s0 == p['side'] else -1             # +1 when outcome 0 is the pick's side
            for t, py, usd, d, w in V.poly_trades(c, st):
                vol += usd
                if not w: continue
                if w in top: net['oos'] += usd * d * sign0
                if w in live: net['live'] += usd * d * sign0
        rows.append(dict(rule=p['rule'], live_rule=p['live'], sport=g['sport'], start=g['start'].isoformat(), game=f"{g['away']} @ {g['home']}", mk=p['mk'], side=p['side'],
                         won=p['won'], dec=p['dec'], after_cut=g['start'].timestamp() >= cut, net_oos=round(net['oos']), net_live=round(net['live']), poly_vol=round(vol)))
    print('picks with a Polymarket market:', len(rows), flush=True)

    def view(x):
        return 'opposed' if x <= -THR else 'backed' if x >= THR else 'no sharp view'

    def rec(L):
        w = sum(1 for r in L if r['won'] == 1); l = sum(1 for r in L if r['won'] == 0)
        pl = sum((r['dec'] - 1) if r['won'] == 1 else -1 if r['won'] == 0 else 0 for r in L)
        return dict(n=len(L), w=w, l=l, roi=round(100 * pl / max(1, len(L)), 1))
    R = {}
    for scope, f in (('live rules', lambda r: r['live_rule']), ('generic market bets (nfl_replay B-series and controls)', lambda r: not r['live_rule']), ('all picks', lambda r: True)):
        for acc in ('oos', 'live'):
            L = [r for r in rows if f(r) and (r['after_cut'] or acc == 'live')]
            for v in ('backed', 'no sharp view', 'opposed'):
                S = [r for r in L if view(r['net_' + acc]) == v]
                if S:
                    R[f'{scope} | {acc} accounts | {v}'] = x = rec(S)
                    print(f"{scope:58s} {acc:4s} {v:14s} n={x['n']:4d} {x['w']}-{x['l']} ROI {x['roi']:+.1f}%")
    json.dump(dict(asof=dt.datetime.utcnow().isoformat() + 'Z', window_from=dt.datetime.utcfromtimestamp(t0).date().isoformat(), cut=dt.datetime.utcfromtimestamp(cut).date().isoformat(),
                   threshold_usd=THR, results=R, picks=rows), open(OUT, 'w'), indent=1)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
