#!/usr/bin/env python3
"""Research agenda section 1 (derived lines): books set first halves / first quarters / first periods as near-fixed shares of the full
game. Does the actual share depend on things a fixed share ignores? Per game: Pinnacle's derivative total (median of the books when
Pinnacle has none) and full-game total at the same snapshot (10 minutes before the start, data/oddsapi/derivs/<sport>_full.jsonl.gz),
period points from ESPN linescores. Bets graded flat at the price on the derivative over / under, split by the market's implied share,
the full total, the favourite's size and season. Writes data/research/deriv_share_<sport>.json. Usage: python3 sharp/deriv_share.py nfl"""
import os, sys, json, sqlite3, statistics, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
PER = {'nfl': [('totals_h1', 2), ('totals_q1', 1)], 'cfb': [('totals_h1', 2), ('totals_q1', 1)], 'wnba': [('totals_h1', 2), ('totals_q1', 1)],
       'nba': [('totals_h1', 2), ('totals_q1', 1)], 'nhl': [('totals_p1', 1)], 'cbb': [('totals_h1', 1)]}


def main_total(outs):
    G = collections.defaultdict(dict)
    for o in outs: G[o.get('point')][o['name']] = o['price']
    best = None
    for ln, d in G.items():
        if 'Over' in d and 'Under' in d:
            sc = abs(d['Over'] - d['Under'])
            if best is None or sc < best[0]: best = (sc, ln, d['Over'], d['Under'])
    return best[1:] if best else None


def main_spread(outs, home):
    for o in outs:
        if o['name'] == home and o.get('point') is not None: return o['point']
    return None


def main():
    sp = sys.argv[1]; path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'data', 'oddsapi', 'derivs', f'{sp}_full.jsonl.gz')
    LS = json.load(open(os.path.join(ROOT, 'data', 'state', 'linescores.json'))).get(sp, {})
    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    RES = {r[0]: r[1:] for r in conn.execute("SELECT game_id, espn_id, home_score, away_score FROM results")}
    rows = []
    for l in lines(path):
        try: d = json.loads(l)
        except Exception: continue
        if d['game_id'] not in RES or not d.get('bookmakers'): continue
        eid, hs, as_ = RES[d['game_id']]; ls = LS.get(str(eid))
        if hs is None or not ls: continue
        B = {b['key']: {m['key']: m['outcomes'] for m in b['markets']} for b in d['bookmakers']}
        full = None; sp_line = None
        q = conn.execute("SELECT pin_close_tot, pin_close_sp FROM games WHERE game_id=?", (d['game_id'],)).fetchone()
        if q: full, sp_line = q
        if not full: continue
        for mk, nper in PER.get(sp, []):
            src = B.get('pinnacle', {}).get(mk)
            mt = main_total(src) if src else None
            if not mt:
                c = [main_total(B[b][mk]) for b in B if mk in B[b]]; c = [x for x in c if x]
                if not c: continue
                ln = statistics.median(x[0] for x in c); c = [x for x in c if x[0] == ln]
                if not c: continue
                mt = c[0]
            ln, po, pu = mt
            if ln is None or len(ls['h']) < nper or len(ls['a']) < nper: continue
            pts = sum(ls['h'][:nper]) + sum(ls['a'][:nper])
            rows.append(dict(mk=mk, season=d['start'][:4] if sp in ('nfl', 'cfb', 'wnba') else (d['start'][:4] if d['start'][5:7] >= '08' else str(int(d['start'][:4]) - 1)),
                             share=ln / full, full=full, fav=abs(sp_line) if sp_line is not None else None, line=ln, po=po, pu=pu, pts=pts, act_share=pts / max(1, hs + as_)))
    R = {}
    for mk, _ in PER.get(sp, []):
        L = [r for r in rows if r['mk'] == mk]
        if len(L) < 50: continue
        sh = sorted(r['share'] for r in L); q1, q2 = sh[len(sh) // 3], sh[2 * len(sh) // 3]
        fu = sorted(r['full'] for r in L); f1, f2 = fu[len(fu) // 3], fu[2 * len(fu) // 3]
        fv = sorted(r['fav'] for r in L if r['fav'] is not None); v1, v2 = (fv[len(fv) // 3], fv[2 * len(fv) // 3]) if fv else (0, 0)
        def band(r):
            yield 'all'
            yield 'implied share ' + ('low' if r['share'] < q1 else 'mid' if r['share'] < q2 else 'high')
            yield 'full total ' + ('low' if r['full'] < f1 else 'mid' if r['full'] < f2 else 'high')
            if r['fav'] is not None: yield 'favourite ' + ('small' if r['fav'] < v1 else 'mid' if r['fav'] < v2 else 'big')
        H = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0]))
        for r in L:
            for b in band(r):
                for side in ('over', 'under'):
                    pr = r['po'] if side == 'over' else r['pu']
                    won = 0.5 if r['pts'] == r['line'] else 1 if (r['pts'] > r['line']) == (side == 'over') else 0
                    for s in (r['season'], 'all'):
                        x = H[f'{b} | {side}'][s]; x[0] += won == 1; x[1] += won == 0; x[2] += (pr - 1) if won == 1 else -1 if won == 0 else 0; x[3] += r['act_share']; x[4] += r['share']
        out = {}
        for k, S in H.items():
            a = S['all']; n = a[0] + a[1]
            seas = {s: f"{v[0]}-{v[1]} {100 * v[2] / max(1, v[0] + v[1]):+.0f}%" for s, v in sorted(S.items()) if s != 'all'}
            pos = sum(1 for s, v in S.items() if s != 'all' and v[0] + v[1] >= 15 and v[2] > 0); tot = sum(1 for s, v in S.items() if s != 'all' and v[0] + v[1] >= 15)
            out[k] = dict(record=f"{a[0]}-{a[1]}", roi=round(100 * a[2] / max(1, n), 1), actual_share=round(a[3] / max(1, n + 0), 3), implied_share=round(a[4] / max(1, n), 3), seasons=seas, positive=f'{pos}/{tot}')
            if a[2] / max(1, n) > 0.03 and n >= 60: print(f"{sp} {mk:10s} {k:34s} {out[k]['record']:>9s} {out[k]['roi']:+5.1f}%  seasons+ {out[k]['positive']}  implied {out[k]['implied_share']} actual {out[k]['actual_share']}")
        R[mk] = dict(n=len(L), cuts=dict(share=[q1, q2], full=[f1, f2], fav=[v1, v2]), results=out)
        a = out.get('all | under'); print(f"{sp} {mk}: n {len(L)}, all unders {a['record']} {a['roi']:+.1f}%, implied share {a['implied_share']} vs actual {a['actual_share']}")
    json.dump(R, open(os.path.join(ROOT, 'data', 'research', f'deriv_share_{sp}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
