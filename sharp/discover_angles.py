#!/usr/bin/env python3
"""Discovery search, as pre-registered in docs/validation/DISCOVERY_PLAN.md (fixed seed 20261119). Read-only.
Searches single conditions and pairs from different families on every bet type (Pinnacle close, regular season), charges every candidate
for the whole sport's search (best eligible candidate per shuffle), and walks the search itself forward season by season.
Writes data/research/discovery.json and docs/validation/DISCOVERY.md (with the tracker's paper-log sample sizes).
Usage: python3 sharp/discover_angles.py [sport ...]"""
import os, sys, json, math, itertools, collections, datetime as dt
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.validate_systems as V
SEED = 20261119; N_PERM = 1000; N_WF = 200; MIN_N = 100; TOP_WF = 5
OUTJ = os.path.join(ROOT, 'data', 'research', 'discovery.json'); OUTD = os.path.join(ROOT, 'docs', 'validation', 'DISCOVERY.md')
SPORTS = ['nfl', 'cfb', 'nba', 'nhl']
BIG = {'nfl': 14, 'cfb': 21, 'nba': 15, 'nhl': 3}; MING = {'nfl': 3, 'cfb': 3, 'nba': 8, 'nhl': 8}; MINATS = {'nfl': 4, 'cfb': 4, 'nba': 8}
MOVE_SP = {'nfl': 1, 'cfb': 1, 'nba': 1}; MOVE_TOT = {'nfl': 1, 'cfb': 2, 'nba': 2, 'nhl': 0.5}; MOVE_ML = 0.03
MARKETS = {'nfl': ['sp_home', 'sp_away', 'over', 'under'], 'cfb': ['sp_home', 'sp_away', 'over', 'under'], 'nba': ['sp_home', 'sp_away', 'over', 'under'],
           'nhl': ['ml_home', 'ml_away', 'over', 'under']}
DESC = {'role:fav': 'is the favourite', 'role:dog': 'is the underdog', 'size:low': 'line in the lower third', 'size:mid': 'line in the middle third', 'size:high': 'line in the upper third',
        'move:toward': 'line moved toward it', 'move:against': 'line moved against it', 'move:flat': 'line did not move', 'move:up': 'total rose', 'move:down': 'total fell',
        'rest:b2b': 'on a back-to-back', 'rest:opp_b2b': 'opponent on a back-to-back', 'rest:adv2': '2+ more days of rest than the opponent', 'rest:bye': 'off a bye',
        'rest:opp_bye': 'opponent off a bye', 'rest:short': 'on a short week', 'form:win60': 'win% 60+', 'form:win40': 'win% 40 or less', 'form:opp_win60': 'opponent win% 60+',
        'form:opp_win40': 'opponent win% 40 or less', 'form:lost_big': 'lost its last game big', 'form:won_big': 'won its last game big', 'form:skid3': 'on a 3+ game losing streak',
        'ats:hot': 'ATS 60%+', 'ats:cold': 'ATS 40% or less', 'over:both_hi': 'both teams over 60%+', 'over:both_lo': 'both teams over 40% or less',
        'wx:wind15': 'wind 15+ mph', 'wx:cold': '32 F or colder', 'wx:hot': '85 F or hotter'}
MDESC = {'sp_home': 'home team spread', 'sp_away': 'road team spread', 'ml_home': 'home team moneyline', 'ml_away': 'road team moneyline', 'over': 'over', 'under': 'under'}


def terciles(vals):
    v = np.array([x for x in vals if x is not None], dtype=float); return np.quantile(v, [1 / 3, 2 / 3]) if len(v) >= 30 else None


def bets(sport, G, W):
    hold = V.HOLDOUT[sport]; tr = [g for g in G if g['season'] < hold]
    cut_sp = terciles([abs(g['sp_close']) for g in tr if g.get('sp_close')]); cut_tot = terciles([g.get('tot_close') for g in tr])
    cut_ml = terciles([max(g['p_close'], 1 - g['p_close']) for g in tr if g.get('p_close') is not None])
    tc = lambda x, c: None if x is None or c is None else ('low' if x <= c[0] else 'mid' if x <= c[1] else 'high')
    rows = []
    for g in G:
        if g['season'] > hold: continue
        for mk in MARKETS[sport]:
            if mk in ('over', 'under'): b = V.tot_bet(g, mk); s = 'home'
            elif mk.startswith('sp'): s = mk[3:]; b = V.sp_bet(g, s)
            else: s = mk[3:]; b = V.ml_bet(g, s)
            if not b: continue
            o = 'away' if s == 'home' else 'home'; C = set()
            # role and size
            if sport == 'nhl':
                p = g.get('p_close')
                if p is not None:
                    ps = p if s == 'home' else 1 - p; C.add('role:fav' if ps > 0.5 else 'role:dog')
                    if mk.startswith('ml'): t = tc(max(p, 1 - p), cut_ml); t and C.add(f'size:{t}')
            else:
                sp = g.get('sp_close')
                if sp:
                    hs = sp if s == 'home' else -sp; C.add('role:fav' if hs < 0 else 'role:dog')
                    if mk.startswith('sp'): t = tc(abs(sp), cut_sp); t and C.add(f'size:{t}')
            if mk in ('over', 'under'):
                t = tc(g.get('tot_close'), cut_tot); t and C.add(f'size:{t}')
                if g.get('tot_open') is not None and g.get('tot_close') is not None:
                    d = g['tot_close'] - g['tot_open']; m = MOVE_TOT[sport]
                    C.add('move:up' if d >= m else 'move:down' if d <= -m else 'move:flat' if abs(d) < m / 2 else '')
            elif mk.startswith('sp') and g.get('sp_open') is not None and g.get('sp_close') is not None:
                d = (g['sp_open'] - g['sp_close']) * (1 if s == 'home' else -1); m = MOVE_SP[sport]
                C.add('move:toward' if d >= m else 'move:against' if d <= -m else 'move:flat' if abs(d) < m / 2 else '')
            elif mk.startswith('ml') and g.get('p_open') is not None and g.get('p_close') is not None:
                d = (g['p_close'] - g['p_open']) * (1 if s == 'home' else -1)
                C.add('move:toward' if d >= MOVE_ML else 'move:against' if d <= -MOVE_ML else 'move:flat' if abs(d) < MOVE_ML / 2 else '')
            # rest
            sd, od = g.get(f'{s}_days'), g.get(f'{o}_days')
            if sport in ('nba', 'nhl'):
                if sd == 1: C.add('rest:b2b')
                if od == 1: C.add('rest:opp_b2b')
                if sd is not None and od is not None and sd - od >= 2: C.add('rest:adv2')
            elif sport == 'nfl':
                if sd is not None and sd >= 13: C.add('rest:bye')
                if od is not None and od >= 13: C.add('rest:opp_bye')
                if sd is not None and sd <= 5: C.add('rest:short')
            # form
            if (g.get(f'{s}_games') or 0) >= MING[sport] and g.get(f'{s}_win_pct') is not None:
                w = g[f'{s}_win_pct']; C.add('form:win60' if w >= 60 else 'form:win40' if w <= 40 else '')
            if (g.get(f'{o}_games') or 0) >= MING[sport] and g.get(f'{o}_win_pct') is not None:
                w = g[f'{o}_win_pct']; C.add('form:opp_win60' if w >= 60 else 'form:opp_win40' if w <= 40 else '')
            lm = g.get(f'{s}_last_margin')
            if lm is not None:
                if lm <= -BIG[sport]: C.add('form:lost_big')
                if lm >= BIG[sport]: C.add('form:won_big')
            if (g.get(f'{s}_loss_streak') or 0) >= 3: C.add('form:skid3')
            # ATS
            if sport in MINATS and (g.get(f'{s}_ats_n') or 0) >= MINATS[sport] and g.get(f'{s}_ats_pct') is not None:
                a = g[f'{s}_ats_pct']; C.add('ats:hot' if a >= 60 else 'ats:cold' if a <= 40 else '')
            # over rate and weather (totals)
            if mk in ('over', 'under') and sport in ('nba', 'nhl'):
                hn, an = g.get('home_over_n') or 0, g.get('away_over_n') or 0; ho, ao = g.get('home_over_pct'), g.get('away_over_pct')
                if hn >= 8 and an >= 8 and ho is not None and ao is not None:
                    if ho >= 0.6 and ao >= 0.6: C.add('over:both_hi')
                    if ho <= 0.4 and ao <= 0.4: C.add('over:both_lo')
            if mk in ('over', 'under') and sport in ('nfl', 'cfb') and not g.get('neutral') and not (sport == 'nfl' and g['home_ab'] in V.ROOF_NFL):
                w = W.get(f"{g['home_ab']}|{g['start']:%Y-%m-%dT%H}")
                if w and w.get('wind') is not None:
                    if round(w['wind']) >= 15: C.add('wx:wind15')
                    if w.get('temp') is not None and w['temp'] <= 32: C.add('wx:cold')
                    if w.get('temp') is not None and w['temp'] >= 85: C.add('wx:hot')
            C.discard('')
            rows.append(dict(mk=mk, won=b[0], dec=b[1], season=g['season'], C=C))
    return rows


def run_sport(sport, rng):
    G = V.load(sport); W = V.wx_map(sport) if sport in ('nfl', 'cfb') else {}
    R = bets(sport, G, W); hold = V.HOLDOUT[sport]
    seasons = sorted({r['season'] for r in R}); train = [s for s in seasons if s < hold]
    M = {}
    for mk in MARKETS[sport]:
        rr = [r for r in R if r['mk'] == mk]
        if not rr: continue
        conds = sorted(set().union(*[r['C'] for r in rr]))
        cands = [(c,) for c in conds] + [tuple(p) for p in itertools.combinations(conds, 2) if p[0].split(':')[0] != p[1].split(':')[0]]
        X = np.array([[all(c in r['C'] for c in cd) for r in rr] for cd in cands], dtype=np.float32)
        sea = np.array([r['season'] for r in rr]); won = np.array([r['won'] for r in rr], float); dec = np.array([r['dec'] for r in rr], float)
        M[mk] = dict(cands=cands, X=X, sea=sea, won=won, dec=dec, sid=V.strata(sea, dec))
    print(f'[discover] {sport}: {len(G)} games, {sum(len(m["cands"]) for m in M.values())} candidates', flush=True)

    def evaluate(mask_seasons, shuf=None):
        """ROI and N for every candidate on the given seasons, per market. shuf: dict mk -> shuffled won."""
        out = {}
        for mk, m in M.items():
            w = shuf[mk] if shuf else m['won']; pr = V.profit(w, m['dec']).astype(np.float32)
            sel = np.isin(m['sea'], mask_seasons).astype(np.float32)
            n = m['X'] @ sel; tot = m['X'] @ (pr * sel)
            out[mk] = (np.where(n > 0, tot / np.maximum(n, 1), np.nan), n)
        return out

    def shuffled(only=None):
        return {mk: V.shuffle(m['won'], m['sid'], rng, only=None if only is None else np.isin(m['sea'], only)) for mk, m in M.items()}

    # training-season search with plain and search-adjusted p
    real = evaluate(train)
    elig = {mk: (real[mk][1] >= MIN_N) for mk in M}
    plain = {mk: np.zeros(len(M[mk]['cands'])) for mk in M}; best = []
    for _ in range(N_PERM):
        S = evaluate(train, shuffled())
        b = -9
        for mk in M:
            r, n = S[mk]; plain[mk] += (r >= real[mk][0]) & elig[mk]
            v = r[elig[mk]]; v = v[~np.isnan(v)]
            if len(v): b = max(b, float(v.max()))
        best.append(b)
    best = np.array(best); hol = evaluate([hold])
    C = []
    for mk, m in M.items():
        for i, cd in enumerate(m['cands']):
            if not elig[mk][i]: continue
            r = float(real[mk][0][i])
            C.append(dict(sport=sport, mk=mk, cond=list(cd), n=int(real[mk][1][i]), roi=r, p_plain=float(plain[mk][i] / N_PERM), p_search=float((best >= r).mean()),
                          hold_roi=None if np.isnan(hol[mk][0][i]) else float(hol[mk][0][i]), hold_n=int(hol[mk][1][i]), wf_picked=[]))
    # walk-forward of the search itself
    idx = {(c['mk'], tuple(c['cond'])): c for c in C}; WF = []
    for t in range(2, len(seasons)):
        Y = seasons[t]; prev = seasons[:t]; rp = evaluate(prev); el = {mk: rp[mk][1] >= MIN_N for mk in M}
        pc = {mk: np.zeros(len(M[mk]['cands'])) for mk in M}
        for _ in range(N_WF):
            S = evaluate(prev, shuffled(prev))
            for mk in M: pc[mk] += S[mk][0] >= rp[mk][0]
        pool = [(float(rp[mk][0][i]), mk, i) for mk in M for i in range(len(M[mk]['cands'])) if el[mk][i] and pc[mk][i] / N_WF < 0.05]
        picks = sorted(pool, reverse=True)[:TOP_WF]; ry = evaluate([Y])
        for r0, mk, i in picks:
            ro, n = ry[mk]; key = (mk, M[mk]['cands'][i])
            WF.append(dict(season=Y, holdout=Y == hold, mk=mk, cond=list(M[mk]['cands'][i]), train_roi=r0, roi=None if np.isnan(ro[i]) else float(ro[i]), n=int(n[i])))
            if key in idx: idx[key]['wf_picked'].append(dict(season=Y, roi=WF[-1]['roi'], n=WF[-1]['n']))
    def pooled(ev):
        u = sum((w['roi'] or 0) * w['n'] for w in ev); n = sum(w['n'] for w in ev); return (u / n if n else None), n
    wf_roi, wf_n = pooled(WF)
    # permutation of the walk-forward seasons, picks fixed
    wfs = sorted({w['season'] for w in WF}); cnt = 0
    for _ in range(N_WF):
        S = shuffled(wfs); tot = 0.0; n = 0
        for Y in wfs:
            ev = evaluate([Y], S)
            for w in WF:
                if w['season'] != Y: continue
                i = M[w['mk']]['cands'].index(tuple(w['cond'])); r, nn = ev[w['mk']][0][i], ev[w['mk']][1][i]
                if nn: tot += r * nn; n += nn
        cnt += (tot / n if n else -9) >= (wf_roi if wf_roi is not None else 9)
    return dict(sport=sport, n_games=len(G), n_cands=sum(len(m['cands']) for m in M.values()), n_elig=len(C), train=train, holdout=hold,
                best_null=dict(median=float(np.median(best)), p95=float(np.quantile(best, 0.95))), cands=C, wf=WF, wf_roi=wf_roi, wf_n=wf_n,
                wf_p=float(cnt / N_WF), wf_seasons=wfs)


def describe(c):
    who = 'the total' if c['mk'] in ('over', 'under') else 'the team'
    tot = c['mk'] in ('over', 'under'); parts = []
    for x in c['cond']:
        d = DESC.get(x, x)
        if tot and x.split(':')[0] in ('role', 'rest', 'form', 'ats'):
            d = d.replace('opponent', 'the visitor') if 'opp' in x else 'the home team ' + d.replace('is the', 'is the')
            d = d.replace('the home team on', 'the home team is on').replace('the home team is the', 'the home team is the').replace('the home team win%', "the home team's win% is").replace('the home team lost', 'the home team lost').replace('the home team ATS', "the home team's ATS is")
        parts.append(d)
    return f"{c['sport'].upper()} {MDESC[c['mk']]}, when " + ' and '.join(parts)


def main():
    want = sys.argv[1:] or SPORTS; out = json.load(open(OUTJ)) if os.path.exists(OUTJ) else {}
    for sp in want:
        res = run_sport(sp, np.random.default_rng(SEED + sum(map(ord, sp))))
        out[sp] = res; json.dump(out, open(OUTJ, 'w'), default=str)
        top = sorted(res['cands'], key=lambda c: c['p_search'])[:3]
        print(f"[discover] {sp}: eligible {res['n_elig']}/{res['n_cands']}, null best median {pct(res['best_null']['median'])} p95 {pct(res['best_null']['p95'])}, "
              f"walk-forward {pct(res['wf_roi'])} on {res['wf_n']} (p {res['wf_p']:.3f}); best: " + '; '.join(f"{describe(c)} {pct(c['roi'])}/{c['n']} ps {c['p_search']:.3f}" for c in top), flush=True)


def pct(x): return 'n/a' if x is None else f"{100 * x:+.1f}%"


if __name__ == '__main__': main()
