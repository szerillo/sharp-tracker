#!/usr/bin/env python3
"""Soccer derivatives on the curve (Sean 11/6). Pinnacle's full-game close (1X2 no-vig and the main total) is turned into two
goal rates (independent Poisson, fitted by least squares on home win, away win and the over). Every derivative the books quote 10
minutes before the start that settles on the final score (both teams to score, draw no bet, team totals, alternate totals, asian
quarter lines included) is priced from those rates and compared with the books.
  1. Blend: on Pinnacle's two-sided prices, does the curve add information? logit(result) ~ Pinnacle + curve (decisive outcomes).
  2. Off-curve bets: a book price whose expected value against the curve is 3%+, graded at the price, by market, side, book, season.
Writes data/research/soccer_curve.json. Usage: python3 sharp/soccer_curve.py [path to soccer_full.jsonl.gz]"""
import os, sys, json, math, sqlite3, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
NICE = dict(pinnacle='Pinnacle', draftkings='DK', fanduel='FD', williamhill_us='Caesars', betrivers='BetRivers', betonlineag='BetOnline', lowvig='LowVig', bovada='Bovada', betmgm='BetMGM')
K = 12
LAM = np.arange(0.10, 4.51, 0.02)
PMF = np.array([[math.exp(-l) * l ** k / math.factorial(k) for k in range(K)] for l in LAM])           # [lam, k]
CDF_H = np.cumsum(PMF, axis=1)
# P(home > away) etc. on the grid: sum_k pmf_h[k] * P(away < k)
P_AWAY_LT = np.concatenate([np.zeros((len(LAM), 1)), CDF_H[:, :-1]], axis=1)                            # [lam, k] = P(X < k)
PH = PMF @ P_AWAY_LT.T                       # [lam_h, lam_a]
PA = (PMF @ P_AWAY_LT.T).T
SUMLAM = LAM[:, None] + LAM[None, :]
# goal-difference distribution on the grid: DIFF[i, j, k + K - 1] = P(home - away = k)   (11/6: early snapshots fit on the asian handicap)
DIFF = np.zeros((len(LAM), len(LAM), 2 * K - 1))
for a_ in range(K):
    for b_ in range(K): DIFF[:, :, a_ - b_ + K - 1] += PMF[:, a_][:, None] * PMF[:, b_][None, :]
KS = np.arange(-(K - 1), K)


def ah_ev_grid(line, dec):
    """expected net return of the HOME asian handicap at `line` and decimal `dec`, over the whole grid"""
    halves = [line - 0.25, line + 0.25] if abs(line * 4 - round(line * 4)) < 1e-9 and abs(line * 2 - round(line * 2)) > 1e-9 else [line]
    out = 0
    for h in halves:
        win = DIFF[:, :, KS + h > 0].sum(axis=2); push = DIFF[:, :, KS + h == 0].sum(axis=2)
        out = out + (win * dec + push - 1)
    return out / len(halves)


def ptot_over(mu, line):
    """P(total > line) for Poisson(mu), half lines only"""
    k = int(math.floor(line)); return 1 - sum(math.exp(-mu) * mu ** j / math.factorial(j) for j in range(k + 1))


def settle_probs(dist, line, over=True):
    """dist: probability of each total 0..K-1. Returns (expected net return per unit at decimal d) as a function: f(d)."""
    halves = [line - 0.25, line + 0.25] if abs(line * 4 - round(line * 4)) < 1e-9 and abs(line * 2 - round(line * 2)) > 1e-9 else [line]
    parts = []
    for h in halves:
        if over: win = sum(p for t, p in enumerate(dist) if t > h); push = sum(p for t, p in enumerate(dist) if t == h)
        else: win = sum(p for t, p in enumerate(dist) if t < h); push = sum(p for t, p in enumerate(dist) if t == h)
        parts.append((win, push))
    return lambda d: sum((w * d + pu - 1) for w, pu in parts) / len(parts)


def settle_result(actual, line, over=True):
    """net return multiplier pieces: returns list of (outcome per half) 1 win / 0.5 push / 0 loss"""
    halves = [line - 0.25, line + 0.25] if abs(line * 4 - round(line * 4)) < 1e-9 and abs(line * 2 - round(line * 2)) > 1e-9 else [line]
    out = []
    for h in halves:
        if actual == h: out.append(0.5)
        else: out.append(1 if (actual > h) == over else 0)
    return out


def pnl(pieces, d):
    return sum((d - 1) if x == 1 else 0 if x == 0.5 else -1 for x in pieces) / len(pieces)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'oddsapi', 'derivs', 'soccer_full.jsonl.gz')
    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    RES = {r[0]: r[1:] for r in conn.execute("SELECT game_id, home_score, away_score FROM results WHERE home_score IS NOT NULL")}
    CLOSE = {}
    for gid, ct in conn.execute("SELECT game_id, close_t FROM games WHERE sport='soccer'"):
        q = conn.execute("SELECT ml_home, ml_away, ml_draw, tot_line, tot_over, tot_under FROM quotes WHERE game_id=? AND t=? AND book='pinnacle'", (gid, ct)).fetchone()
        if q and all(q[:3]) and q[3] is not None and q[4] and q[5]: CLOSE[gid] = q       # any total line: quarter and whole lines fitted on settlement (11/6)
    bets = []; CAL = []; n = 0; fitbad = 0
    for l in lines(path):
        try: d = json.loads(l)
        except Exception: continue
        gid = d['game_id']
        if gid not in RES or (gid not in CLOSE and not os.environ.get('SOCCER_SNAP')) or not d.get('bookmakers'): continue
        hs, as_ = RES[gid]; SNAP = None
        if os.environ.get('SOCCER_SNAP'):       # fit on THIS snapshot's Pinnacle asian handicap and total (no 1X2 in the early pulls)
            pz = next((b for b in d['bookmakers'] if b['key'] == 'pinnacle'), None); mz = {m['key']: m['outcomes'] for m in (pz or {}).get('markets', [])}
            sh = {o['name']: o for o in mz.get('spreads', [])}; st_ = {o['name']: o for o in mz.get('totals', [])}
            if d['home'] not in sh or d['away'] not in sh or 'Over' not in st_ or 'Under' not in st_: continue
            ho, ao = sh[d['home']], sh[d['away']]; qa_h = (1 / ho['price']) / (1 / ho['price'] + 1 / ao['price'])
            tl = st_['Over']['point']; qo = (1 / st_['Over']['price']) / (1 / st_['Over']['price'] + 1 / st_['Under']['price'])
            mus = np.round(SUMLAM, 2); EVO = {}
            for m in np.unique(mus):
                dist = [math.exp(-m) * m ** t / math.factorial(t) for t in range(2 * K)]; EVO[m] = settle_probs(dist, tl, True)(1 / qo)
            SNAP = (ah_ev_grid(ho['point'], 1 / qa_h) / 2) ** 2 + (np.vectorize(lambda m: EVO[m])(mus) / 2) ** 2
            mh = ma = md = 2.0; to = tu = 1.9
        else:
            if gid not in CLOSE: continue
            mh, ma, md, tl, to, tu = CLOSE[gid]
        s = 1 / mh + 1 / ma + 1 / md; qh, qa = (1 / mh) / s, (1 / ma) / s; qo = (1 / to) / (1 / to + 1 / tu)
        mus = np.round(SUMLAM, 2); EVO = {}
        for m in np.unique(mus):
            dist = [math.exp(-m) * m ** t / math.factorial(t) for t in range(2 * K)]
            EVO[m] = settle_probs(dist, tl, True)(1 / qo)          # the over's expected return at Pinnacle's no-vig price: zero on the curve
        PO = np.vectorize(lambda m: EVO[m])(mus)
        loss = (PH - qh) ** 2 + (PA - qa) ** 2 + (PO / 2) ** 2
        if SNAP is not None:
            loss = SNAP
        i, j = np.unravel_index(np.argmin(loss), loss.shape)
        if loss[i, j] > 0.002: fitbad += 1; continue
        lh, la = LAM[i], LAM[j]; ph_, pa_ = PMF[i], PMF[j]; n += 1
        joint = np.outer(ph_, pa_)
        tot = [sum(joint[a, b] for a in range(K) for b in range(K) if a + b == t) for t in range(2 * K)]
        season = d['start'][:4] if d['start'][5:7] >= '07' else str(int(d['start'][:4]) - 1)
        p_btts = float((1 - ph_[0]) * (1 - pa_[0])); p_hw = float(PH[i, j]); p_aw = float(PA[i, j])
        pin = {}
        for b in d['bookmakers']:
            bk = b['key']
            if bk == 'betmgm': continue
            for m in b['markets']:
                mk = m['key']
                for o in m['outcomes']:
                    price = o['price']; rec = None
                    if mk == 'btts':
                        yes = o['name'] == 'Yes'; pw = p_btts if yes else 1 - p_btts; won = 1 if ((hs > 0 and as_ > 0) == yes) else 0
                        ev = pw * price - 1; rec = dict(mk=mk, side='yes' if yes else 'no', line=None, pw=pw, pieces=[won], ev=ev)
                    elif mk == 'draw_no_bet':
                        home = o['name'] == d['home']
                        if not home and o['name'] != d['away']: continue
                        pw = p_hw if home else p_aw; pdr = 1 - p_hw - p_aw
                        ev = pw * price + pdr - 1; won = 0.5 if hs == as_ else 1 if (hs > as_) == home else 0
                        rec = dict(mk=mk, side='home' if home else 'away', line=None, pw=pw / max(1e-9, 1 - pdr), pieces=[won], ev=ev)
                    elif mk in ('alternate_totals', 'team_totals') and o.get('point') is not None and o['name'] in ('Over', 'Under'):
                        over = o['name'] == 'Over'
                        if mk == 'team_totals':
                            team = 'home' if o.get('description') == d['home'] else 'away' if o.get('description') == d['away'] else None
                            if not team: continue
                            dist = list(ph_ if team == 'home' else pa_); act = hs if team == 'home' else as_; side = f'{team} {o["name"].lower()}'
                        else: dist = tot; act = hs + as_; side = o['name'].lower(); team = None
                        f = settle_probs(dist, o['point'], over); ev = f(price); pieces = settle_result(act, o['point'], over)
                        half = abs(o['point'] * 2 - round(o['point'] * 2)) < 1e-9 and o['point'] % 1
                        pw = (sum(p for t, p in enumerate(dist) if (t > o['point']) == over)) if half else None
                        rec = dict(mk=mk, side=side, line=o['point'], pw=pw, pieces=pieces, ev=ev, team=team)
                    if not rec: continue
                    rec.update(book=NICE.get(bk, bk), price=price, season=season, g=gid, lam=(round(float(lh), 2), round(float(la), 2)))
                    if bk == 'pinnacle': pin[(mk, rec['side'], rec['line'])] = rec
                    if rec['ev'] >= 0.03: bets.append(rec)
        # calibration pairs on Pinnacle (half lines / BTTS / DNB without a draw)
        OPP = {'yes': 'no', 'home': 'away', 'over': 'under', 'home over': 'home under', 'away over': 'away under'}
        for (mk, side, ln), r in pin.items():
            if side not in OPP or r['pw'] is None: continue
            o2 = pin.get((mk, OPP[side], ln))
            if not o2 or r['pieces'] == [0.5]: continue
            q = (1 / r['price']) / (1 / r['price'] + 1 / o2['price'])
            CAL.append((mk, min(max(q, .02), .98), min(max(r['pw'], .02), .98), r['pieces'][0]))
    print(f'soccer: {n} games fitted ({fitbad} poor fits skipped), {len(bets)} off-curve quotes', flush=True)
    lg = lambda p: math.log(p / (1 - p)); R = dict(games=n, blend={}, bets={})
    for mk in sorted({c[0] for c in CAL}):
        Rw = [c for c in CAL if c[0] == mk]
        if len(Rw) < 300: continue
        X = np.array([[1.0, lg(q), lg(p)] for _, q, p, _ in Rw]); Y = np.array([y for *_, y in Rw], dtype=float); w = np.zeros(3)
        for _ in range(25):
            p_ = 1 / (1 + np.exp(-X @ w)); H = X.T @ (X * (p_ * (1 - p_))[:, None]) + 1e-6 * np.eye(3); w += np.linalg.solve(H, X.T @ (Y - p_))
        se = np.sqrt(np.diag(np.linalg.inv(H)))
        ll_c = -np.mean([y * math.log(p) + (1 - y) * math.log(1 - p) for _, _, p, y in Rw]); ll_q = -np.mean([y * math.log(q) + (1 - y) * math.log(1 - q) for _, q, _, y in Rw])
        R['blend'][mk] = dict(n=len(Rw), w_pin=round(float(w[1]), 2), w_curve=round(float(w[2]), 2), z_curve=round(float(w[2] / se[2]), 2), ll_curve=round(ll_c, 4), ll_pin=round(ll_q, 4))
        print(f"   blend {mk:18s} n={len(Rw):6d}  Pinnacle {w[1]:+.2f}  curve {w[2]:+.2f} (z {w[2] / se[2]:+.2f})  log loss curve {ll_c:.4f} Pinnacle {ll_q:.4f}")
    G = collections.defaultdict(list)
    for b in bets:
        sd = b['side'].split()[-1]
        if b['mk'] == 'alternate_totals' and sd == 'under' and b['ev'] >= .06:
            G[f"ALT UNDER 6%+ | season {b['season']}"].append(b); G[f"ALT UNDER 6%+ | line {b['line']}"].append(b); G[f"ALT UNDER 6%+ | book {b['book']}"].append(b)
        for k in ('all', f"{b['mk']}", f"{b['mk']} | {sd}", f"{b['mk']} | {sd} | book {b['book']}", f"{b['mk']} | {sd} | season {b['season']}", f"{b['mk']} | {sd} | edge {'3-6%' if b['ev'] < .06 else '6%+'}"):
            G[k].append(b)
    for k in sorted(G, key=lambda k: (k.count('|'), k)):
        L = G[k]; w = sum(1 for b in L if b['pieces'] == [1] or (len(b['pieces']) == 2 and sum(b['pieces']) >= 1.5)); pl = sum(pnl(b['pieces'], b['price']) for b in L)
        R['bets'][k] = dict(n=len(L), roi=round(100 * pl / len(L), 1), ev=round(100 * sum(b['ev'] for b in L) / len(L), 1))
        if (len(L) >= 80 and (k.count('|') <= 1 or R['bets'][k]['roi'] > 3)) or (k.startswith('ALT') and len(L) >= 20): print(f"   {k:48s} n={len(L):6d} ROI {R['bets'][k]['roi']:+.1f}%  curve EV {R['bets'][k]['ev']:+.1f}%")
    json.dump(R, open(os.path.join(ROOT, 'data', 'research', 'soccer_curve' + ('_snap' if os.environ.get('SOCCER_SNAP') else '') + '.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
