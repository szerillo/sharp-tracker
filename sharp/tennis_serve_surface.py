#!/usr/bin/env python3
"""Tennis Abstract: hold, break and serve rates by surface, tour and level (Sean, 11/4), plus whether a SURFACE-specific hold rate
reads set 1 better than the overall trailing hold rate used in the live set-1 model. Writes data/research/tennis_serve_surface.json."""
import os, sys, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.tennis_ta as T
OUT = os.path.join(ROOT, 'data', 'research', 'tennis_serve_surface.json')


def main():
    M = T.load(); T.elo_run(M)
    R = {}
    # 1. match-level serve rates by tour x level-group x surface (tour-level matches carry serve stats)
    A = collections.defaultdict(lambda: collections.Counter())
    for m in M:
        for sv in (m['w_sv'], m['l_sv']):
            svpt, fin, fwon, swon, gms, bpf, bps = sv
            if not svpt or not gms or fin is None or fwon is None or swon is None: continue
            k = (m['tour'], 'slam' if m['bo'] == 5 else T.grp(m).split('_', 1)[1], m['surface'])
            c = A[k]; c['n'] += 1; c['svpt'] += svpt; c['fin'] += fin; c['fwon'] += fwon; c['swon'] += swon; c['gms'] += gms; c['bpf'] += bpf or 0; c['bps'] += bps or 0
            c['s1_tb'] += m['s1_tb']; c['s1_games'] += m['s1_games']
    R['serve by surface'] = {}
    for k, c in sorted(A.items()):
        if c['n'] < 2000 or k[2] in ('Unknown', 'Carpet'): continue
        R['serve by surface'][' / '.join(k)] = dict(player_matches=c['n'], hold=round(1 - (c['bpf'] - c['bps']) / c['gms'], 3), break_per_ret_game=round((c['bpf'] - c['bps']) / c['gms'], 3),
                                                   first_in=round(c['fin'] / c['svpt'], 3), first_won=round(c['fwon'] / c['fin'], 3), second_won=round(c['swon'] / (c['svpt'] - c['fin']), 3),
                                                   serve_pts_won=round((c['fwon'] + c['swon']) / c['svpt'], 3), bp_saved=round(c['bps'] / c['bpf'], 3) if c['bpf'] else None,
                                                   set1_tiebreak=round(c['s1_tb'] / c['n'], 3), set1_games=round(c['s1_games'] / c['n'], 2))
    # 2. surface-specific trailing hold vs overall trailing hold as a set-1 reader (favourite rows, bo3, tour + Challenger)
    H = collections.defaultdict(lambda: collections.deque(maxlen=15)); HS = collections.defaultdict(lambda: collections.deque(maxlen=15))
    for m in M:
        for who in ('w', 'l'):
            m[f'hold_{who}'] = sum(H[m[who]]) / len(H[m[who]]) if len(H[m[who]]) >= 8 else None
            m[f'holds_{who}'] = sum(HS[(m[who], m['surface'])]) / len(HS[(m[who], m['surface'])]) if len(HS[(m[who], m['surface'])]) >= 8 else None
        for who in ('w', 'l'):
            h = T.hold_rate(m[f'{who}_sv'])
            if h is not None and 0 <= h <= 1: H[m[who]].append(h); HS[(m[who], m['surface'])].append(h)
    rows = T.fav_rows(M)
    cal = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for r in rows: c = cal[T.grp(r)][T.binp(r['p'])]; c[0] += 1; c[1] += r['fav_won']
    for r in rows:
        c = cal[T.grp(r)].get(T.binp(r['p'])); r['p_cal'] = c[1] / c[0] if c and c[0] >= 100 else None
    rows = [r for r in rows if r['p_cal'] is not None and r['bo'] == 3 and T.grp(r) in ('atp_tour', 'atp_chall', 'wta_tour')]
    pooled = T.curve(rows)
    for r in rows: r['s1c'] = T.interp(pooled, r['p_cal'])
    def cut(name, keyf, rows_, min_n=500):
        Tt = collections.defaultdict(lambda: [0, 0, 0.0, 0, 0.0])
        for r in rows_:
            k = keyf(r)
            if k is None: continue
            t = Tt[k]; t[0] += 1; t[1] += r['fav_won']; t[2] += r['p_cal']; t[3] += r['fav_s1']; t[4] += r['s1c']
        R[name] = {str(k): dict(n=n, match_resid=round(100 * (w / n - p / n), 1), set1_resid=round(100 * (s / n - sc / n), 1)) for k, (n, w, p, s, sc) in sorted(Tt.items()) if n >= min_n}
    fav = lambda r, k: r[k + ('_w' if r['fav_won'] else '_l')]; dog = lambda r, k: r[k + ('_l' if r['fav_won'] else '_w')]
    prof = lambda hf, ho: None if hf is None or ho is None else ('dog bigger server' if ho - hf >= .03 else 'fav bigger server' if hf - ho >= .03 else 'similar')
    cut('A overall trailing hold (live model input)', lambda r: prof(fav(r, 'hold'), dog(r, 'hold')), rows)
    cut('B surface-specific trailing hold', lambda r: prof(fav(r, 'holds'), dog(r, 'holds')), rows)
    cut('C both known: overall says X, surface says Y', lambda r: None if prof(fav(r, 'hold'), dog(r, 'hold')) is None or prof(fav(r, 'holds'), dog(r, 'holds')) is None else f"overall {prof(fav(r, 'hold'), dog(r, 'hold'))} | surface {prof(fav(r, 'holds'), dog(r, 'holds'))}", rows, 300)
    cut('D overall hold profile by surface', lambda r: None if prof(fav(r, 'hold'), dog(r, 'hold')) is None else f"{r['surface']}: {prof(fav(r, 'hold'), dog(r, 'hold'))}", rows)
    # 3. break-rate matchup: both players hold a lot (serve-dominant match) vs both break a lot -> set-1 tiebreak rate and games
    Q = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows:
        hf, ho = fav(r, 'hold'), dog(r, 'hold')
        if hf is None or ho is None: continue
        avg = (hf + ho) / 2; k = f"{r['surface']}: avg hold {'85%+' if avg >= .85 else '78-85%' if avg >= .78 else 'under 78%'}"
        t = Q[k]; t[0] += 1; t[1] += r['s1_tb']; t[2] += r['s1_games']
    R['E set-1 tiebreak and games by combined hold rate'] = {k: dict(n=n, set1_tiebreak=round(tb / n, 3), set1_games=round(g / n, 2)) for k, (n, tb, g) in sorted(Q.items()) if n >= 500}
    json.dump(R, open(OUT, 'w'), indent=1)
    for k, v in R.items():
        print(f"\n== {k}")
        for kk, vv in v.items(): print(f"  {kk:60} {vv}")


if __name__ == '__main__':
    main()
