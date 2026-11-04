#!/usr/bin/env python3
"""Tennis Abstract research (Sean, 11/4): sharpen the tennis models with Jeff Sackmann's match database (data/tennis/ta, pulled by
.github/workflows/tennis_data.yml). No prices in this data, so everything here is about structure and skill, not market edge:

  1. Elo (overall and per surface, blended), chronological, 2015 on: calibration of the pre-match win probability.
  2. First set vs match: P(favourite wins set 1) by match-probability bin, observed against the independent-sets model the live rule
     uses, by tour, surface, best-of and level. Comeback structure: P(win match | won set 1) and P(win match | lost set 1), which
     lets the live rule turn a market match price into a fair set-1 price without assuming independent sets.
  3. First-set tiebreak rate and first-set games by surface and tour (for set-1 totals later).
  4. Serve profile (tour-level matches carry serve stats): do two big holders make set 1 closer than the match price says?
  5. Surface fit: when the surface Elo favourite and the overall Elo favourite disagree, who wins. Form: last-10 record on top of Elo.
  6. Rank-points favourite vs Elo favourite: who wins when they disagree (rank is the public's number; Elo is closer to the market).
Train = 2015-2022, holdout = 2023-2026 wherever a fit is used to predict. Writes data/research/tennis_ta.json and prints the tables.
Usage: python3 sharp/tennis_ta.py"""
import os, sys, re, csv, gzip, json, math, glob, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
TA = os.path.join(ROOT, 'data', 'tennis', 'ta'); OUT = os.path.join(ROOT, 'data', 'research', 'tennis_ta.json')
HOLD = 20230101
SET_RE = re.compile(r'^(\d+)-(\d+)(?:\((\d+)\))?$')


def load():
    M = []
    for f in sorted(glob.glob(os.path.join(TA, '*_matches_*.csv.gz'))):
        b = os.path.basename(f); tour = b[:3]
        level = 'futures' if 'futures' in b else 'qual_chall' if 'qual_chall' in b else 'qual_itf' if 'qual_itf' in b else 'tour'
        for r in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8', errors='replace')):
            sc = (r.get('score') or '').strip()
            if not sc or 'W/O' in sc or 'DEF' in sc or 'Walkover' in sc: continue
            toks = sc.replace('RET', '').split()
            if not toks: continue
            m1 = SET_RE.match(toks[0])
            if not m1: continue
            a, b_ = int(m1.group(1)), int(m1.group(2)); hi, lo = max(a, b_), min(a, b_)
            if hi < 6 or (hi - lo < 2 and hi < 7) or hi > 7 and lo < hi - 2: continue       # set 1 not completed (retirement mid-set)
            try: d = int(r['tourney_date'])
            except Exception: continue
            try: bo = int(r.get('best_of') or 3)
            except Exception: bo = 3
            def num(x):
                try: return float(x)
                except Exception: return None
            M.append(dict(tour=tour, level=level if level != 'tour' else (r.get('tourney_level') or 'A'), surface=(r.get('surface') or '').strip() or 'Unknown', date=d, bo=bo,
                          w=r['winner_id'], l=r['loser_id'], wn=r.get('winner_name'), ln=r.get('loser_name'), s1_winner_won=a > b_, s1_tb=hi == 7 and lo == 6, s1_games=a + b_,
                          wpts=num(r.get('winner_rank_points')), lpts=num(r.get('loser_rank_points')), wrank=num(r.get('winner_rank')), lrank=num(r.get('loser_rank')),
                          w_sv=(num(r.get('w_svpt')), num(r.get('w_1stIn')), num(r.get('w_1stWon')), num(r.get('w_2ndWon')), num(r.get('w_SvGms')), num(r.get('w_bpFaced')), num(r.get('w_bpSaved'))),
                          l_sv=(num(r.get('l_svpt')), num(r.get('l_1stIn')), num(r.get('l_1stWon')), num(r.get('l_2ndWon')), num(r.get('l_SvGms')), num(r.get('l_bpFaced')), num(r.get('l_bpSaved'))),
                          rnd=r.get('round'), num=int(r.get('match_num') or 0)))
    M.sort(key=lambda m: (m['date'], m['tour'], m['num']))
    return M


def kfac(n): return 250.0 / ((n + 5) ** 0.4)       # FiveThirtyEight-style: new players move fast


def elo_run(M):
    """Chronological Elo per tour: overall and per surface; each match gets the pre-match probabilities. Lower-level matches update
    with a smaller K (they say less about tour-level strength)."""
    E = collections.defaultdict(lambda: 1500.0); ES = collections.defaultdict(lambda: 1500.0); N = collections.Counter(); NS = collections.Counter()
    last = {}; form = collections.defaultdict(lambda: collections.deque(maxlen=10))
    for m in M:
        w, l, s = m['w'], m['l'], m['surface']
        ew, el = E[w], E[l]; sw, sl = ES[(w, s)], ES[(l, s)]
        p_all = 1 / (1 + 10 ** ((el - ew) / 400)); p_surf = 1 / (1 + 10 ** ((sl - sw) / 400))
        m['p_w'] = p_all; m['p_w_surf'] = p_surf; m['p_w_blend'] = 1 / (1 + 10 ** ((((el + sl) / 2) - ((ew + sw) / 2)) / 400))
        m['n_w'], m['n_l'] = N[w], N[l]; m['ns_w'], m['ns_l'] = NS[(w, s)], NS[(l, s)]
        m['form_w'] = sum(form[w]) / len(form[w]) if form[w] else None; m['form_l'] = sum(form[l]) / len(form[l]) if form[l] else None
        m['rest_w'] = (dt.date(m['date'] // 10000, m['date'] // 100 % 100, m['date'] % 100) - last[w]).days if w in last else None
        m['rest_l'] = (dt.date(m['date'] // 10000, m['date'] // 100 % 100, m['date'] % 100) - last[l]).days if l in last else None
        scale = 1.0 if m['level'] in ('G', 'M', 'A', 'D', 'F', 'P', 'PM', 'I', 'O', 'T1', 'T2', 'T3', 'T4') else 0.6 if m['level'] == 'qual_chall' else 0.4
        kw, kl = kfac(N[w]) * scale, kfac(N[l]) * scale
        E[w] += kw * (1 - p_all); E[l] -= kl * (1 - p_all)
        ksw, ksl = kfac(NS[(w, s)]) * scale, kfac(NS[(l, s)]) * scale
        ES[(w, s)] += ksw * (1 - p_surf); ES[(l, s)] -= ksl * (1 - p_surf)
        N[w] += 1; N[l] += 1; NS[(w, s)] += 1; NS[(l, s)] += 1
        form[w].append(1); form[l].append(0)
        last[w] = last[l] = dt.date(m['date'] // 10000, m['date'] // 100 % 100, m['date'] % 100)
    return E, ES


def indep(p, bo=3):
    """Independent-sets model: set-win s such that P(match) = p. Best of 3: s^2(3-2s); best of 5: s^3(10-15s+6s^2)."""
    f = (lambda s: s * s * (3 - 2 * s)) if bo == 3 else (lambda s: s ** 3 * (10 - 15 * s + 6 * s * s))
    lo, hi = 0.0, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        if f(m) < p: lo = m
        else: hi = m
    return (lo + hi) / 2


def binp(p): return min(0.95, max(0.5, math.floor(p * 20) / 20))


def fav_rows(M, pkey='p_w_blend', min_n=10):
    """Rows from the favourite's side: (p_fav, fav won match, fav won set 1, ...). Only matches where both players have some history."""
    out = []
    for m in M:
        if m['n_w'] < min_n or m['n_l'] < min_n: continue
        p = m[pkey]
        if p >= 0.5: out.append(dict(m, p=p, fav_won=True, fav_s1=m['s1_winner_won']))
        else: out.append(dict(m, p=1 - p, fav_won=False, fav_s1=not m['s1_winner_won']))
    return out


def table(rows, keyf, name):
    T = collections.defaultdict(lambda: [0, 0, 0, 0.0, 0.0])       # n, fav won match, fav won s1, sum p, sum indep s
    for r in rows:
        t = T[keyf(r)]; t[0] += 1; t[1] += r['fav_won']; t[2] += r['fav_s1']; t[3] += r['p']; t[4] += indep(r['p'], r['bo'])
    out = {}
    for k, (n, fw, fs, sp, si) in sorted(T.items(), key=lambda kv: str(kv[0])):
        if n < 30: continue
        out[str(k)] = dict(n=n, p_mean=round(sp / n, 3), match=round(fw / n, 3), set1=round(fs / n, 3), indep=round(si / n, 3), set1_minus_indep=round(100 * (fs / n - si / n), 1))
    return out


def comeback(rows):
    """P(fav wins match | fav won set 1) = a, P(fav wins match | fav lost set 1) = b, by p bin and best-of."""
    T = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        t = T[(r['bo'], binp(r['p']))]
        if r['fav_s1']: t[0] += 1; t[1] += r['fav_won']
        else: t[2] += 1; t[3] += r['fav_won']
    out = {}
    for (bo, b), (n1, w1, n0, w0) in sorted(T.items()):
        if n1 + n0 < 100: continue
        out[f"bo{bo} p{b:.2f}"] = dict(n=n1 + n0, a=round(w1 / n1, 3) if n1 else None, b=round(w0 / n0, 3) if n0 else None, set1=round(n1 / (n1 + n0), 3))
    return out


def hold_rate(sv):
    svpt, fin, fwon, swon, gms, bpf, bps = sv
    if not svpt or not gms: return None
    return 1 - ((bpf or 0) - (bps or 0)) / gms           # breaks lost per service game


def serve_profiles(M):
    """Trailing hold rate per player from the last 15 tour-level matches with stats (before this match)."""
    H = collections.defaultdict(lambda: collections.deque(maxlen=15))
    for m in M:
        hw, hl = (sum(H[m['w']]) / len(H[m['w']]) if len(H[m['w']]) >= 8 else None), (sum(H[m['l']]) / len(H[m['l']]) if len(H[m['l']]) >= 8 else None)
        m['hold_w'], m['hold_l'] = hw, hl
        for who, sv in (('w', m['w_sv']), ('l', m['l_sv'])):
            h = hold_rate(sv)
            if h is not None and 0 <= h <= 1: H[m[who]].append(h)


def logloss(rows, key):
    L = [-(math.log(r[key]) if r['fav_won'] else math.log(1 - r[key])) for r in rows if 0 < r[key] < 1]
    return round(sum(L) / len(L), 4) if L else None


def main():
    M = load(); print(f"[tennis_ta] {len(M)} matches with a completed first set, {M[0]['date']} to {M[-1]['date']}", flush=True)
    elo_run(M); serve_profiles(M)
    R = dict(matches=len(M), through=M[-1]['date'])
    rows = fav_rows(M); R['rows_with_history'] = len(rows)
    # 1. calibration (holdout)
    hold = [r for r in rows if r['date'] >= HOLD]; train = [r for r in rows if r['date'] < HOLD]
    R['calibration_holdout'] = {f"{b:.2f}": dict(n=n, pred=round(sp / n, 3), won=round(fw / n, 3)) for b, (n, fw, sp) in sorted(
        collections.Counter() and {k: v for k, v in collections.defaultdict(lambda: [0, 0, 0.0]).items()}.items())}  # placeholder replaced below
    C = collections.defaultdict(lambda: [0, 0, 0.0])
    for r in hold: t = C[binp(r['p'])]; t[0] += 1; t[1] += r['fav_won']; t[2] += r['p']
    R['calibration_holdout'] = {f"{b:.2f}": dict(n=n, pred=round(sp / n, 3), won=round(fw / n, 3)) for b, (n, fw, sp) in sorted(C.items())}
    R['logloss_holdout'] = dict(elo_overall=logloss(hold, 'p_w') if False else None)
    # log loss by model, favourite-side (recompute from the winner side to avoid the fav flip)
    def ll(key):
        L = []
        for m in M:
            if m['date'] < HOLD or m['n_w'] < 10 or m['n_l'] < 10: continue
            p = m[key]
            if 0 < p < 1: L.append(-math.log(p))
        return round(sum(L) / len(L), 4)
    R['logloss_holdout'] = dict(elo_overall=ll('p_w'), elo_surface=ll('p_w_surf'), elo_blend=ll('p_w_blend'))
    # 2. set 1 vs match
    R['set1_by_p'] = table(rows, lambda r: f"{binp(r['p']):.2f}", 'p')
    R['set1_by_p_tour'] = table(rows, lambda r: f"{r['tour']} {binp(r['p']):.2f}", 'tour')
    R['set1_by_p_bo'] = table(rows, lambda r: f"bo{r['bo']} {binp(r['p']):.2f}", 'bo')
    R['set1_by_surface'] = table([r for r in rows if r['bo'] == 3], lambda r: f"{r['surface']}", 'surface')
    R['set1_by_surface_p'] = table([r for r in rows if r['bo'] == 3], lambda r: f"{r['surface']} {binp(r['p']):.2f}", 'surface_p')
    R['set1_by_level'] = table([r for r in rows if r['bo'] == 3], lambda r: f"{r['tour']} {r['level']}", 'level')
    R['comeback'] = comeback(rows)
    # 3. tiebreaks and games
    T = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows: t = T[(r['tour'], r['surface'])]; t[0] += 1; t[1] += r['s1_tb']; t[2] += r['s1_games']
    R['set1_tiebreak_games'] = {f"{k[0]} {k[1]}": dict(n=n, tiebreak=round(tb / n, 3), games=round(g / n, 2)) for k, (n, tb, g) in sorted(T.items()) if n >= 200}
    # 4. serve profile: set-1 result vs p, split by the two players' hold rates (tour level, both known)
    S = [r for r in rows if r.get('hold_w') is not None and r.get('hold_l') is not None]
    for r in S: r['hold_sum'] = r['hold_w'] + r['hold_l']; r['hold_fav'] = r['hold_w'] if r['fav_won'] else r['hold_l']; r['hold_dog'] = r['hold_l'] if r['fav_won'] else r['hold_w']
    if S:
        qs = sorted(r['hold_sum'] for r in S); cuts = (qs[len(qs) // 3], qs[2 * len(qs) // 3])
        terc = lambda r: 'both big servers' if r['hold_sum'] >= cuts[1] else 'both returners' if r['hold_sum'] < cuts[0] else 'middle'
        R['set1_by_serve_profile'] = table(S, lambda r: f"{terc(r)} {binp(r['p']):.2f}", 'serve')
        R['set1_by_serve_profile_all'] = table(S, terc, 'serve_all')
        R['serve_profile_cuts'] = dict(low=round(cuts[0], 3), high=round(cuts[1], 3), n=len(S))
        # dog with the bigger hold rate: does set 1 go his way more often than p says?
        R['set1_dog_bigger_server'] = table(S, lambda r: 'dog holds more' if r['hold_dog'] > r['hold_fav'] + 0.03 else 'fav holds more' if r['hold_fav'] > r['hold_dog'] + 0.03 else 'similar', 'dogserve')
    # 5. surface fit: surface favourite vs overall favourite disagree (holdout, both with 10+ surface matches)
    D = collections.defaultdict(lambda: [0, 0])
    for m in M:
        if m['date'] < HOLD or m['ns_w'] < 10 or m['ns_l'] < 10 or m['n_w'] < 20 or m['n_l'] < 20: continue
        if (m['p_w'] >= 0.5) == (m['p_w_surf'] >= 0.5): continue
        surf_fav_won = m['p_w_surf'] >= 0.5
        gap = abs(m['p_w_surf'] - m['p_w'])
        for k in ('all', m['surface'], m['tour'], 'gap 10%+' if gap >= 0.10 else 'gap <10%'):
            D[k][0] += 1; D[k][1] += surf_fav_won
    R['surface_fav_vs_overall_fav_disagree_holdout'] = {k: dict(n=n, surface_fav_won=round(w / n, 3)) for k, (n, w) in sorted(D.items()) if n >= 50}
    # form on top of Elo (holdout): logistic-free check by bins of form difference
    F = collections.defaultdict(lambda: [0, 0, 0.0])
    for m in M:
        if m['date'] < HOLD or m['form_w'] is None or m['form_l'] is None or m['n_w'] < 20 or m['n_l'] < 20: continue
        fd = m['form_w'] - m['form_l']; k = 'winner form better by 30%+' if fd >= 0.3 else 'loser form better by 30%+' if fd <= -0.3 else 'similar'
        t = F[k]; t[0] += 1; t[2] += m['p_w_blend']
    # form from the favourite's side
    F = collections.defaultdict(lambda: [0, 0, 0.0])
    for r in hold:
        if r['form_w'] is None or r['form_l'] is None or r['n_w'] < 20 or r['n_l'] < 20: continue
        ff, fd_ = (r['form_w'], r['form_l']) if r['fav_won'] else (r['form_l'], r['form_w'])
        k = 'fav hotter (last 10 +30%)' if ff - fd_ >= 0.3 else 'dog hotter (last 10 +30%)' if fd_ - ff >= 0.3 else 'similar form'
        t = F[k]; t[0] += 1; t[1] += r['fav_won']; t[2] += r['p']
    R['form_on_top_of_elo_holdout'] = {k: dict(n=n, elo_pred=round(sp / n, 3), fav_won=round(w / n, 3), diff=round(100 * (w / n - sp / n), 1)) for k, (n, w, sp) in F.items()}
    # rest days
    Rr = collections.defaultdict(lambda: [0, 0, 0.0])
    for r in hold:
        if r['rest_w'] is None or r['rest_l'] is None: continue
        rf, rd = (r['rest_w'], r['rest_l']) if r['fav_won'] else (r['rest_l'], r['rest_w'])
        k = 'fav on 1 day rest, dog 2+' if rf <= 1 < rd else 'dog on 1 day rest, fav 2+' if rd <= 1 < rf else 'same'
        t = Rr[k]; t[0] += 1; t[1] += r['fav_won']; t[2] += r['p']
    R['rest_holdout'] = {k: dict(n=n, elo_pred=round(sp / n, 3), fav_won=round(w / n, 3), diff=round(100 * (w / n - sp / n), 1)) for k, (n, w, sp) in Rr.items()}
    # 6. rank-points favourite vs Elo favourite
    G = collections.defaultdict(lambda: [0, 0])
    for m in M:
        if m['date'] < HOLD or m['wpts'] is None or m['lpts'] is None or m['n_w'] < 20 or m['n_l'] < 20: continue
        rank_fav_w = m['wpts'] > m['lpts']; elo_fav_w = m['p_w_blend'] >= 0.5
        if rank_fav_w == elo_fav_w: continue
        for k in ('all', m['tour'], m['level'] if m['level'] in ('qual_chall', 'qual_itf', 'futures') else 'tour'):
            G[k][0] += 1; G[k][1] += elo_fav_w
    R['elo_fav_vs_rank_fav_disagree_holdout'] = {k: dict(n=n, elo_fav_won=round(w / n, 3)) for k, (n, w) in sorted(G.items()) if n >= 50}
    json.dump(R, open(OUT, 'w'), indent=1)
    for k in ('logloss_holdout', 'calibration_holdout', 'set1_by_p', 'set1_by_p_tour', 'set1_by_p_bo', 'set1_by_surface', 'set1_by_level', 'comeback', 'set1_tiebreak_games',
              'set1_by_serve_profile_all', 'set1_dog_bigger_server', 'surface_fav_vs_overall_fav_disagree_holdout', 'form_on_top_of_elo_holdout', 'rest_holdout', 'elo_fav_vs_rank_fav_disagree_holdout'):
        print(f"\n== {k}")
        v = R.get(k) or {}
        for kk, vv in (v.items() if isinstance(v, dict) else []): print(f"  {kk:34} {vv}")


if __name__ == '__main__' and '--map' not in sys.argv:
    main()


# ---------------------------------------------------------------- the live mapping: fair set-1 from a calibrated match price ----
LEVEL_GROUP = {'qual_chall': 'chall', 'futures': 'itf', 'qual_itf': 'itf'}


def grp(m): return f"{m['tour']}_{LEVEL_GROUP.get(m['level'], 'tour')}" + ('_bo5' if m['bo'] == 5 else '')


def curve(rows, step=0.025):
    """[(observed match rate, observed set-1 rate, n)] per Elo-probability bin: x is the calibrated match probability."""
    T = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows:
        b = min(0.975, max(0.5, math.floor(r['p'] / step) * step)); t = T[b]; t[0] += 1; t[1] += r['fav_won']; t[2] += r['fav_s1']
    pts = [(round(fw / n, 4), round(fs / n, 4), n) for b, (n, fw, fs) in sorted(T.items()) if n >= 400]
    out = []
    for x, y, n in pts:                      # keep x increasing (merge a bin that falls back)
        if out and x <= out[-1][0]: out[-1] = (round((out[-1][0] * out[-1][2] + x * n) / (out[-1][2] + n), 4), round((out[-1][1] * out[-1][2] + y * n) / (out[-1][2] + n), 4), out[-1][2] + n)
        else: out.append((x, y, n))
    return out


def interp(cv, x):
    if not cv: return None
    if x <= cv[0][0]: return cv[0][1] + (x - cv[0][0]) * (cv[0][1] - 0.5) / max(1e-6, cv[0][0] - 0.5)
    for (x0, y0, _), (x1, y1, _) in zip(cv, cv[1:]):
        if x0 <= x <= x1: return y0 + (y1 - y0) * (x - x0) / max(1e-9, x1 - x0)
    return cv[-1][1]


def mapping(M):
    rows = fav_rows(M); out = dict(groups={}, stability={}, serve_residual={}, surface_residual={}, offsets={})
    # the pooled curve (all levels, best-of-3) carries the shape to 0.95; each group gets an offset = its mean residual against it
    # calibrated match probability per row: the group's own calibration (Elo bin -> observed match rate)
    cal = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for r in rows: c = cal[grp(r)][binp(r['p'])]; c[0] += 1; c[1] += r['fav_won']
    for r in rows:
        c = cal[grp(r)].get(binp(r['p'])); r['p_cal'] = c[1] / c[0] if c and c[0] >= 100 else None
    pooled = curve([r for r in rows if r['bo'] == 3]); out['pooled'] = pooled
    for g in sorted({grp(r) for r in rows}):
        rs = [r for r in rows if grp(r) == g]
        if len(rs) < 3000: continue
        cv = curve(rs); out['groups'][g] = cv
        if not g.endswith('bo5'):
            res = [r['fav_s1'] - interp(pooled, r['p_cal']) for r in rs if r.get('p_cal') is not None]
            out['offsets'][g] = round(sum(res) / len(res), 4) if res else 0.0
        tr, ho = curve([r for r in rs if r['date'] < HOLD]), curve([r for r in rs if r['date'] >= HOLD])
        # holdout residual vs the train curve at a few match probabilities
        out['stability'][g] = {f"{x:.2f}": dict(train=round(interp(tr, x), 3) if tr else None, holdout=round(interp(ho, x), 3) if ho else None,
                                                indep=round(indep(x, 5 if g.endswith('bo5') else 3), 3)) for x in (0.6, 0.7, 0.8, 0.9)}
    # residuals vs the group curve: serve profile and surface (how much to move the fair set-1 price)
    def resid(rs, keyf, store):
        T = collections.defaultdict(lambda: [0, 0.0, 0.0])
        for r in rs:
            cv = out['groups'].get(grp(r))
            if not cv: continue
            base = interp(cv, r['p_cal']) if r.get('p_cal') is not None else None
            if base is None: continue
            t = T[keyf(r)]; t[0] += 1; t[1] += r['fav_s1']; t[2] += base
        for k, (n, s, b) in sorted(T.items()):
            if n >= 500: store[k] = dict(n=n, set1=round(s / n, 3), curve=round(b / n, 3), residual=round(100 * (s / n - b / n), 1))
    S = [r for r in rows if r.get('hold_w') is not None and r.get('hold_l') is not None]
    for r in S: r['hold_fav'] = r['hold_w'] if r['fav_won'] else r['hold_l']; r['hold_dog'] = r['hold_l'] if r['fav_won'] else r['hold_w']
    resid(S, lambda r: 'dog holds 3%+ more' if r['hold_dog'] > r['hold_fav'] + 0.03 else 'fav holds 3%+ more' if r['hold_fav'] > r['hold_dog'] + 0.03 else 'similar hold rates', out['serve_residual'])
    resid(S, lambda r: f"both hold {'85%+' if min(r['hold_fav'], r['hold_dog']) >= 0.85 else 'under 75%' if max(r['hold_fav'], r['hold_dog']) < 0.75 else 'mixed'}", out['serve_residual'])
    resid(rows, lambda r: f"{r['tour']} {r['surface']}", out['surface_residual'])
    return out


def profiles(M):
    """Per player: trailing hold rate (last 15 tour-level matches with stats), overall and surface Elo, matches, last seen. Keyed by name."""
    E, ES = elo_run(M)
    last = {}; name = {}; nm = collections.Counter()
    H = collections.defaultdict(lambda: collections.deque(maxlen=15))
    for m in M:
        for who, sv in (('w', m['w_sv']), ('l', m['l_sv'])):
            h = hold_rate(sv)
            if h is not None and 0 <= h <= 1: H[m[who]].append(h)
        name[m['w']] = m['wn']; name[m['l']] = m['ln']; last[m['w']] = last[m['l']] = m['date']; nm[m['w']] += 1; nm[m['l']] += 1
    out = {}
    for pid, n in nm.items():
        if n < 10 or not name.get(pid): continue
        surf = {s: round(ES[(pid, s)]) for s in ('Hard', 'Clay', 'Grass') if (pid, s) in ES}
        out[name[pid]] = dict(elo=round(E[pid]), surface_elo=surf, hold=round(sum(H[pid]) / len(H[pid]), 3) if len(H[pid]) >= 8 else None, hold_n=len(H[pid]), matches=n, last=last[pid])
    return out


if __name__ == '__main__' and '--map' in sys.argv:
    M = load(); elo_run(M); serve_profiles(M)
    out = mapping(M)
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'tennis_set1_map.json'), 'w'), indent=1)
    P = profiles(M); json.dump(P, open(os.path.join(ROOT, 'data', 'state', 'tennis_profiles.json'), 'w'), separators=(',', ':'))
    print(f"[tennis_ta] set-1 mapping for {list(out['groups'])}; {len(P)} player profiles")
    for g, st in out['stability'].items(): print(' ', g, st)
    for k in ('serve_residual', 'surface_residual'):
        print(f"\n== {k}")
        for kk, v in out[k].items(): print(f"  {kk:30} {v}")
