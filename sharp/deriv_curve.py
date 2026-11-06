#!/usr/bin/env python3
"""Derivatives on the curve (Sean 11/6: "on the curve relative to full game numbers ... like we did with first set tennis").
For every game, the fair price of each derivative outcome (first-half / first-quarter / first-period totals and spreads, period
moneylines, team totals) implied by Pinnacle's FULL-GAME close, estimated from history: the outcome among past games with a similar
full-game total and spread, scaled to this game's numbers, leave-one-season-out (a game is never priced with its own season).
Then every quoted derivative price (Pinnacle and the US books, every line offered, 10 minutes before the start) is compared with that
curve price.
  1. Calibration: does the curve predict outcomes better than Pinnacle's own derivative price (log loss on the same outcomes)?
  2. Off-curve bets: a book price 3%+ better than the curve price, graded flat at the price, by sport, market, book, edge and season.
Data: data/oddsapi/derivs/<sport>_full.jsonl.gz, odds.sqlite (full-game close, results), data/state/linescores.json.
Writes data/research/deriv_curve_<sport>.json. Usage: python3 sharp/deriv_curve.py nba [path]"""
import os, sys, json, math, bisect, sqlite3, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
NICE = dict(pinnacle='Pinnacle', draftkings='DK', fanduel='FD', williamhill_us='Caesars', betrivers='BetRivers', betonlineag='BetOnline', lowvig='LowVig',
            circasports='Circa', bovada='Bovada', betmgm='BetMGM')
# periods counted by each market: (first period index, number of periods) in the ESPN linescore
PER = {'nba': dict(h1=(0, 2), q1=(0, 1)), 'nfl': dict(h1=(0, 2), q1=(0, 1)), 'cfb': dict(h1=(0, 2), q1=(0, 1)), 'wnba': dict(h1=(0, 2), q1=(0, 1)),
       'cbb': dict(h1=(0, 1)), 'nhl': dict(p1=(0, 1), p2=(1, 1), p3=(2, 1)),
       'mlb': {'1st_5_innings': (0, 5), '1st_1_innings': (0, 1), '1st_3_innings': (0, 3)}}
EV_MIN = 0.03


def season(sp, s):
    y, m = int(s[:4]), int(s[5:7])
    if sp == 'mlb': return str(y)
    return str(y) if sp in ('nfl', 'cfb', 'wnba') and m >= 3 else str(y - 1) if sp in ('nfl', 'cfb') else (str(y) if m >= 8 else str(y - 1))


def parse_mk(k):
    """market key -> (kind, period) e.g. totals_h1 -> ('total', 'h1'); team_totals -> ('team', None); h2h_p1 -> ('ml', 'p1')"""
    if k == 'team_totals': return 'team', None
    for pre, kind in (('team_totals_', 'team'), ('totals_', 'total'), ('spreads_', 'spread'), ('h2h_3_way_', None), ('h2h_', 'ml')):
        if k.startswith(pre): return kind, k[len(pre):]
    return None, None


def main():
    sp = sys.argv[1]; path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'data', 'oddsapi', 'derivs', f'{sp}_full.jsonl.gz')
    LS = json.load(open(os.path.join(ROOT, 'data', 'state', 'linescores.json'))).get(sp, {})
    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    RES = {r[0]: r[1:] for r in conn.execute("SELECT game_id, espn_id, home_score, away_score FROM results")}
    FULL = {r[0]: r[1:] for r in conn.execute("SELECT game_id, pin_close_tot, pin_close_sp FROM games WHERE sport=?", (sp,))}
    G = []
    for l in lines(path):
        try: d = json.loads(l)
        except Exception: continue
        if not d.get('bookmakers') or d['game_id'] not in RES or d['game_id'] not in FULL: continue
        eid, hs, as_ = RES[d['game_id']]; T, S = FULL[d['game_id']]
        ls = LS.get(str(eid))
        if hs is None or T is None or S is None or not ls: continue
        G.append(dict(id=d['game_id'], season=season(sp, d['start']), home=d['home'], away=d['away'], T=T, S=S, hs=hs, as_=as_, ls=ls, books=d['bookmakers']))
    # 11/6: the curve's history is every game with a full-game close and period scores (back to 2020 where ESPN period scores were pulled),
    # not only the games with derivative prices; a game is still never priced with its own season
    POOL = []
    for gid, start, T, S, eid, hs, as_ in conn.execute("SELECT g.game_id, g.start, g.pin_close_tot, g.pin_close_sp, r.espn_id, r.home_score, r.away_score FROM games g JOIN results r USING(game_id) WHERE g.sport=? AND g.pin_close_tot IS NOT NULL AND g.pin_close_sp IS NOT NULL AND r.home_score IS NOT NULL", (sp,)):
        ls = LS.get(str(eid))
        if ls: POOL.append(dict(id=gid, season=season(sp, start), T=T, S=S, hs=hs, as_=as_, ls=ls))
    print(f'{sp}: {len(G)} games with derivatives, full-game close, scores and period lines; curve history {len(POOL)} games', flush=True)

    def outcome_val(g, kind, per, team=None):
        """the realised quantity: total points / home margin / team points over the period (per None = full game)"""
        if per is None: h, a = g['hs'], g['as_']
        else:
            if per not in PER.get(sp, {}): return None
            i0, n = PER[sp][per]
            if len(g['ls']['h']) < i0 + n or len(g['ls']['a']) < i0 + n: return None
            h, a = sum(g['ls']['h'][i0:i0 + n]), sum(g['ls']['a'][i0:i0 + n])
        if kind == 'total': return h + a
        if kind in ('spread', 'ml'): return h - a
        if kind == 'team': return h if team == 'home' else a
        return None

    # neighbours: past games (other seasons) with a similar full-game total and spread; the outcome scaled to this game's numbers
    seasons = sorted({g['season'] for g in G})
    Tsd = (sum((g['T'] - sum(x['T'] for x in G) / len(G)) ** 2 for g in G) / len(G)) ** .5 or 1
    Ssd = (sum(g['S'] ** 2 for g in G) / len(G)) ** .5 or 1
    cache = {}

    def curve(g, kind, per, team=None):
        key = (g['id'], kind, per, team)
        if key in cache: return cache[key]
        tr = [x for x in POOL if x['season'] != g['season']]
        tr.sort(key=lambda x: ((x['T'] - g['T']) / Tsd) ** 2 + ((x['S'] - g['S']) / Ssd) ** 2)
        nb = tr[:max(150, len(tr) // 12)]
        vals = []
        for x in nb:
            v = outcome_val(x, kind, per, team)
            if v is None: continue
            if kind == 'total': v = v * g['T'] / x['T']
            elif kind == 'team':
                imp_g = g['T'] / 2 + (-g['S'] if team == 'home' else g['S']) / 2; imp_x = x['T'] / 2 + (-x['S'] if team == 'home' else x['S']) / 2
                if imp_x <= 0 or imp_g <= 0: continue
                v = v * imp_g / imp_x
            elif kind in ('spread', 'ml'):
                frac = 1.0 if per is None else (PER[sp][per][1] / (4 if sp in ('nba', 'nfl', 'cfb', 'wnba') else 2 if sp == 'cbb' else 9 if sp == 'mlb' else 3))
                v = v + (x['S'] - g['S']) * frac          # shift the period margin by the difference in full-game spread, scaled to the period
            vals.append(v)
        vals.sort(); cache[key] = vals
        return vals

    def p_gt(vals, x):
        lo = bisect.bisect_left(vals, x); hi = bisect.bisect_right(vals, x); n = len(vals)
        return ((n - hi) + 0.5 * (hi - lo)) / n if n else None

    def p_push(vals, x):
        lo = bisect.bisect_left(vals, x); hi = bisect.bisect_right(vals, x); return (hi - lo) / len(vals) if vals else 0

    CALROWS = []; DUMP = []
    bets = []; cal = collections.defaultdict(lambda: [0, 0.0, 0.0])      # (market) -> [n, logloss curve, logloss pinnacle]
    for gi, g in enumerate(G):
        if gi % 500 == 0: print(f'  {gi}/{len(G)}', flush=True)
        pin = {}
        for b in g['books']:
            for m in b['markets']:
                kind, per = parse_mk(m['key'])
                if kind is None: continue
                for o in m['outcomes']:
                    # the side: over/under (total, team), home/away (spread, ml); team totals name the team in 'description'
                    nm = o['name']; pt = o.get('point'); team = None
                    if kind in ('total', 'team'):
                        if nm not in ('Over', 'Under') or pt is None: continue
                        if kind == 'team':
                            desc = o.get('description'); team = 'home' if desc == g['home'] else 'away' if desc == g['away'] else None
                            if not team: continue
                        side = nm.lower()
                    else:
                        side = 'home' if nm == g['home'] else 'away' if nm == g['away'] else None
                        if not side: continue
                        if kind == 'spread' and pt is None: continue
                    actual = outcome_val(g, kind, per, team)
                    if actual is None: continue
                    vals = curve(g, kind, per, team)
                    if len(vals) < 100: continue
                    # curve probabilities of win / push for this outcome
                    if kind in ('total', 'team'):
                        pw = p_gt(vals, pt) if side == 'over' else 1 - p_gt(vals, pt) - p_push(vals, pt); pp = p_push(vals, pt)
                        won = 0.5 if actual == pt else 1 if (actual > pt) == (side == 'over') else 0
                    elif kind == 'spread':
                        thr = -pt if side == 'home' else pt               # home covers when margin > -pt; away covers when margin < pt
                        if side == 'home': pw = p_gt(vals, thr); pp = p_push(vals, thr)
                        else: pp = p_push(vals, thr); pw = 1 - p_gt(vals, thr) - pp
                        m_ = actual if side == 'home' else -actual; c = m_ + pt; won = 0.5 if c == 0 else 1 if c > 0 else 0
                    else:       # period moneyline, two-way: a tie is a push
                        pp = p_push(vals, 0); pw = p_gt(vals, 0) if side == 'home' else 1 - p_gt(vals, 0) - pp
                        won = 0.5 if actual == 0 else 1 if (actual > 0) == (side == 'home') else 0
                    price = o['price']
                    if pw is None or price <= 1: continue
                    ev = pw * price + pp - 1                     # push returns the stake
                    mk = m['key']
                    rec = dict(sport=sp, mk=mk, book=NICE.get(b['key'], b['key']), side=side, line=pt, price=price, pw=pw, pp=pp, ev=ev, won=won, season=g['season'], g=g['id'])
                    if b['key'] == 'pinnacle': pin[(mk, side, pt, team)] = (price, rec)
                    if ev >= EV_MIN and b['key'] != 'betmgm': bets.append(rec)
        # calibration on Pinnacle's two-sided lines: curve vs Pinnacle's no-vig price, decisive outcomes only
        done = set()
        for (mk, side, pt, team), (price, rec) in pin.items():
            opp = {'over': 'under', 'under': 'over', 'home': 'away', 'away': 'home'}[side]
            opt = pt if mk.startswith(('totals', 'team')) else (-pt if pt is not None else None)
            o2 = pin.get((mk, opp, opt, team))
            if not o2 or (mk, pt, team) in done or rec['won'] == 0.5: continue
            done.add((mk, pt, team)); done.add((mk, opt, team))
            q = (1 / price) / (1 / price + 1 / o2[0])
            pc = rec['pw'] / max(1e-9, 1 - rec['pp'])          # curve win probability given no push
            pc = min(max(pc, 0.02), 0.98); q = min(max(q, 0.02), 0.98); y = rec['won']
            CALROWS.append((mk, q, pc, y)); DUMP.append(dict(mk=mk, q=q, pc=pc, y=y, side=rec['side'], line=rec['line'], price=price, oprice=o2[0], season=rec['season'], team=team)); x = cal[mk]; x[0] += 1; x[1] += -(y * math.log(pc) + (1 - y) * math.log(1 - pc)); x[2] += -(y * math.log(q) + (1 - y) * math.log(1 - q))

    def rec_(L):
        w = sum(1 for b in L if b['won'] == 1); l = sum(1 for b in L if b['won'] == 0)
        pl = sum((b['price'] - 1) if b['won'] == 1 else -1 if b['won'] == 0 else 0 for b in L)
        return dict(n=len(L), w=w, l=l, roi=round(100 * pl / max(1, w + l), 1), ev=round(100 * sum(b['ev'] for b in L) / max(1, len(L)), 1))
    R = dict(games=len(G), calibration={k: dict(n=v[0], logloss_curve=round(v[1] / v[0], 4), logloss_pinnacle=round(v[2] / v[0], 4)) for k, v in cal.items() if v[0]})
    # does the curve add anything to Pinnacle's own price? logit(y) ~ a + b*logit(pinnacle) + c*logit(curve), per market (Newton steps)
    import numpy as np
    lg = lambda p: math.log(p / (1 - p))
    R['blend'] = {}
    for mk in sorted({r[0] for r in CALROWS}):
        Rw = [r for r in CALROWS if r[0] == mk]
        if len(Rw) < 300: continue
        X = np.array([[1.0, lg(q), lg(pc)] for _, q, pc, _ in Rw]); Y = np.array([y for *_, y in Rw], dtype=float); w = np.zeros(3)
        for _ in range(25):
            p_ = 1 / (1 + np.exp(-X @ w)); H = X.T @ (X * (p_ * (1 - p_))[:, None]) + 1e-6 * np.eye(3); w += np.linalg.solve(H, X.T @ (Y - p_))
        se = np.sqrt(np.diag(np.linalg.inv(H)))
        R['blend'][mk] = dict(n=len(Rw), b_pinnacle=round(float(w[1]), 3), c_curve=round(float(w[2]), 3), z_curve=round(float(w[2] / se[2]), 2))
        print(f"   blend {mk:16s} n={len(Rw):5d}  Pinnacle weight {w[1]:+.2f}  curve weight {w[2]:+.2f} (z {w[2] / se[2]:+.2f})")
    print('calibration on Pinnacle two-sided lines (lower is better):')
    for k, v in sorted(R['calibration'].items()): print(f"   {k:18s} n={v['n']:5d}  curve {v['logloss_curve']}  Pinnacle {v['logloss_pinnacle']}  {'CURVE BETTER' if v['logloss_curve'] < v['logloss_pinnacle'] else ''}")
    groups = collections.defaultdict(list)
    for b in bets:
        groups['all'].append(b); groups['market ' + b['mk']].append(b); groups['book ' + b['book']].append(b)
        groups['edge ' + ('3-6%' if b['ev'] < .06 else '6-10%' if b['ev'] < .10 else '10%+')].append(b)
        groups[f"market {b['mk']} | book {b['book']}"].append(b)
        groups[f"market {b['mk']} | season {b['season']}"].append(b)
        groups['main-ish price (1.70-2.30)' if 1.7 <= b['price'] <= 2.3 else 'longer price'].append(b)
    R['bets'] = {k: rec_(v) for k, v in groups.items()}
    print('off-curve bets (book price 3%+ better than the curve):')
    for k in sorted(R['bets'], key=lambda k: (k.count('|'), k)):
        v = R['bets'][k]
        if v['w'] + v['l'] >= 40 and (k.count('|') == 0 or v['roi'] > 3): print(f"   {k:46s} {v['w']}-{v['l']} ROI {v['roi']:+.1f}%  curve EV {v['ev']:+.1f}%")
    json.dump(R, open(os.path.join(ROOT, 'data', 'research', f'deriv_curve_{sp}.json'), 'w'), indent=1)
    if os.environ.get('CURVE_DUMP'): json.dump(DUMP, open(os.environ['CURVE_DUMP'], 'w'))


if __name__ == '__main__':
    main()
