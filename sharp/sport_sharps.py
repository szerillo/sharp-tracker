#!/usr/bin/env python3
"""Sport-specific Polymarket sharps vs one cross-sport list, and whether either holds up over time (Sean, 11/2: "every sport has
sport-specific sharps; the question is whether that is sustainable over time, or whether the cream rises to the top across all sports").

Two walk-forward folds on the settled game-line history (data/polymarket/history, moneyline / spread / total, $10k+ volume):
  fold A: score on games before 2026-03-01, follow on 2026-03-01 to 2026-08-31
  fold B: score on games before 2026-09-01, follow on 2026-09-01 on   (the split round 3 used)
Scores (train): mean CLV vs Polymarket's two-sided close of $100+ (risk-equivalent) pregame fills.
  GENERAL   top 200 across all sports (30+ fills on 15+ games), as live
  SPORT     top 50 / top 100 within one sport, from that sport's fills only (20+ fills on 10+ games in that sport)
  SPECIALIST  in the sport's top 50 but not in the general top 200 (the sport-only sharps)
  BOTH      in the sport's top 50 and the general top 200
  SPORT BOTTOM 50  (check: should be at or below zero)
Each group is followed on that sport's test markets: first $100+ fill by a member per market, entry at the two-sided mid 5 minutes
later, graded on CLV vs Polymarket's close and on the result.
Persistence: for accounts with 10+ qualifying fills in both train and test in a sport, the correlation between train CLV and test CLV
(per account), for the sport score and the cross-sport score; higher = skill that lasts.
Sports: nfl, nba, nhl, cfb, mlb, wnba, soccer (epl + ucl + mls + bundesliga), ufc.
Writes data/research/sport_sharps.json. Usage: python3 sharp/sport_sharps.py"""
import os, sys, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V
from sharp.sharp_accounts2 import Px
SPORT = {'epl': 'soccer', 'ucl': 'soccer', 'mls': 'soccer', 'bundesliga': 'soccer'}
FOLDS = {'A': ('2026-03-01', '2026-09-01'), 'B': ('2026-09-01', '2099-01-01')}
LAG = 300


def ts(d): return dt.datetime.fromisoformat(d + 'T00:00:00+00:00').timestamp()


def stat(R):
    n = len(R)
    if n < 10: return dict(n=n)
    def zz(x):
        m = sum(x) / len(x); s = (sum((v - m) ** 2 for v in x) / max(1, len(x) - 1)) ** .5
        return round(m, 3), round(m / (s / math.sqrt(len(x))), 2) if s else None
    c, cz = zz([r[0] for r in R]); r_, rz = zz([r[1] for r in R])
    return dict(n=n, clv=round(c, 2), clv_z=cz, roi=round(100 * r_, 1), roi_z=rz)


def corr(pairs):
    if len(pairs) < 10: return dict(n=len(pairs))
    xs, ys = zip(*pairs); mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxy = sum((a - mx) * (b - my) for a, b in pairs); sx = math.sqrt(sum((a - mx) ** 2 for a in xs)); sy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return dict(n=len(pairs), r=round(sxy / (sx * sy), 3) if sx and sy else None)


def fold(MK, cut, end):
    cut, end = ts(cut), ts(end)
    G = collections.defaultdict(lambda: [0.0, 0, set()])                         # all-sport train
    S = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0, set()]))   # sport -> wallet train
    T = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0]))           # sport -> wallet test CLV (persistence)
    cand = None; tests = collections.defaultdict(list)
    for i, (c, st) in enumerate(MK):
        if st >= end: break
        sp = SPORT.get(c['tag'], c['tag'])
        L = V.poly_trades(c, st)
        if len(L) < 5: continue
        L4 = [x[:4] for x in L]; P = Px(L4); cl = P.at(st)
        if cl is None: continue
        if st < cut:
            for t, py, usd, d, w in L:
                if usd < 100 or not w: continue
                v = 100 * ((cl if d > 0 else 1 - cl) - (py if d > 0 else 1 - py))
                g = G[w]; g[0] += v; g[1] += 1; g[2].add(c['cond'])
                s = S[sp][w]; s[0] += v; s[1] += 1; s[2].add(c['cond'])
            continue
        if cand is None:
            cand = {w for w, x in G.items() if x[1] >= 30 and len(x[2]) >= 15}
            for sp_, W in S.items(): cand |= {w for w, x in W.items() if x[1] >= 20 and len(x[2]) >= 10}
        ry = 1 if c['winner'] == c['outcomes'][0] else 0; first = {}
        for t, py, usd, d, w in L:
            if usd < 100 or not w: continue
            if w in cand:
                tt = T[sp][w]; tt[0] += 100 * ((cl if d > 0 else 1 - cl) - (py if d > 0 else 1 - py)); tt[1] += 1
                if w not in first: first[w] = (t, d)
        ent = {}
        for w, (t, d) in first.items():
            if t + LAG >= st: continue
            px = P.at(t + LAG)
            if px is None: continue
            price = px if d > 0 else 1 - px
            if 0.05 < price < 0.95: ent[w] = (t, d, price)
        if ent: tests[sp].append((ry, cl, ent))
        if i % 5000 == 0: print(f"[sport_sharps] {i}/{len(MK)}", flush=True)
    gen = sorted([w for w, x in G.items() if x[1] >= 30 and len(x[2]) >= 15], key=lambda w: -G[w][0] / G[w][1]); gen200 = set(gen[:200])
    out = {}
    for sp, markets in tests.items():
        W = S.get(sp, {}); ranked = sorted([w for w, x in W.items() if x[1] >= 20 and len(x[2]) >= 10], key=lambda w: -W[w][0] / W[w][1])
        top50, top100 = set(ranked[:50]), set(ranked[:100])
        groups = {'GENERAL top 200': gen200, 'SPORT top 50': top50, 'SPORT top 100': top100, 'SPECIALIST (sport top 50, not general)': top50 - gen200,
                  'BOTH (sport top 50 and general)': top50 & gen200, 'SPORT bottom 50': set(ranked[-50:]) if len(ranked) >= 150 else set()}
        res = dict(scored_in_sport=len(ranked), test_markets=len(markets), overlap_sport50_general200=len(top50 & gen200), groups={})
        for name, grp in groups.items():
            R = []
            for ry, cl, ent in markets:
                h = sorted(v for w, v in ent.items() if w in grp)
                if not h: continue
                t, d, price = h[0]; won = ry if d > 0 else 1 - ry
                R.append((100 * ((cl if d > 0 else 1 - cl) - price), (1 - price) / price if won else -1.0))
            res['groups'][name] = dict(stat(R), members=len(grp))
        # persistence: train CLV vs test CLV per account (10+ fills each side)
        Tt = T.get(sp, {})
        res['persistence_sport_score'] = corr([(W[w][0] / W[w][1], Tt[w][0] / Tt[w][1]) for w in W if W[w][1] >= 10 and Tt.get(w, [0, 0])[1] >= 10])
        res['persistence_general_score'] = corr([(G[w][0] / G[w][1], Tt[w][0] / Tt[w][1]) for w in G if G[w][1] >= 10 and Tt.get(w, [0, 0])[1] >= 10])
        out[sp] = res
    return out


def main():
    MK = V.poly_markets(); res = {}
    for name, (cut, end) in FOLDS.items():
        print(f"[sport_sharps] fold {name}: train before {cut}, test {cut} to {end}", flush=True)
        res[name] = dict(train_before=cut, test_until=end, sports=fold(MK, cut, end))
        json.dump(res, open(os.path.join(ROOT, 'data', 'research', 'sport_sharps.json'), 'w'), indent=1)
    for f, r in res.items():
        print(f"\n== fold {f} (train before {r['train_before']})")
        for sp, x in sorted(r['sports'].items()):
            print(f"  {sp}: {x['test_markets']} test markets, {x['scored_in_sport']} scored in sport, overlap {x['overlap_sport50_general200']}; persistence sport r {x['persistence_sport_score'].get('r')} (n {x['persistence_sport_score']['n']}), general r {x['persistence_general_score'].get('r')}")
            for g, v in x['groups'].items():
                if v.get('n', 0) >= 10: print(f"     {g:42} n {v['n']:4}  CLV {v['clv']:+.2f} (z {v['clv_z']})  ROI {v['roi']:+.1f}% (z {v['roi_z']})  members {v['members']}")


if __name__ == '__main__':
    main()
