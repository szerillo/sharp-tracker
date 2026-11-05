#!/usr/bin/env python3
"""Matchup styles -> match shape (Sean, 11/4): which combinations of the two players' serve and return profiles make a match go three
sets, run over the games total, produce tiebreaks, or end in a quick two-setter. Tennis Abstract tour + Challenger best-of-3 matches
with a calibrated price; every table is against the baseline of the same match-probability bin, so a style effect is what the two
players' profiles add beyond how lopsided the match is.

Player profiles (trailing 15 tour-level matches with stats): hold rate, break rate achieved on return, ace rate, height.
Outcomes: P(3 sets), mean total games, P(total games >= 22.5), P(a tiebreak in the match), P(set 1 has 10+ games), P(straight sets fav).
Writes data/research/tennis_style.json."""
import os, sys, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.tennis_ta as T
import sharp.tennis_ta2 as T2
OUT = os.path.join(ROOT, 'data', 'research', 'tennis_style.json')


def profiles(M):
    H = collections.defaultdict(lambda: collections.deque(maxlen=15)); B = collections.defaultdict(lambda: collections.deque(maxlen=15)); A = collections.defaultdict(lambda: collections.deque(maxlen=15))
    for m in M:
        for who in ('w', 'l'):
            p = m[who]
            m[f'hold_{who}'] = sum(H[p]) / len(H[p]) if len(H[p]) >= 8 else None
            m[f'brk_{who}'] = sum(B[p]) / len(B[p]) if len(B[p]) >= 8 else None
            m[f'ace_{who}'] = sum(A[p]) / len(A[p]) if len(A[p]) >= 8 else None
        for who, opp in (('w', 'l'), ('l', 'w')):
            sv = m[f'{who}_sv']; osv = m[f'{opp}_sv']
            h = T.hold_rate(sv)
            if h is not None and 0 <= h <= 1: H[m[who]].append(h)
            svpt, fin, fwon, swon, gms, bpf, bps = osv
            if gms:
                b = ((bpf or 0) - (bps or 0)) / gms
                if 0 <= b <= 1: B[m[who]].append(b)


def main():
    M = T.load(); T.elo_run(M); profiles(M); T2.annotate(M)
    rows = T.fav_rows(M)
    cal = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for r in rows: c = cal[T.grp(r)][T.binp(r['p'])]; c[0] += 1; c[1] += r['fav_won']
    for r in rows:
        c = cal[T.grp(r)].get(T.binp(r['p'])); r['p_cal'] = c[1] / c[0] if c and c[0] >= 100 else None
    rows = [r for r in rows if r.get('p_cal') is not None and r['bo'] == 3 and T.grp(r) in ('atp_tour', 'atp_chall', 'wta_tour') and r.get('score')]
    for r in rows:
        st = T2.sets_of(r['score']); r['sets'] = st; r['n_sets'] = len(st); r['games'] = sum(a + b for a, b in st); r['tb'] = any(max(a, b) == 7 and min(a, b) == 6 for a, b in st)
        r['ret'] = 'RET' in r['score']
    rows = [r for r in rows if not r['ret'] and r['n_sets'] >= 2]
    fav = lambda r, k: r[k + ('_w' if r['fav_won'] else '_l')]; dog = lambda r, k: r[k + ('_l' if r['fav_won'] else '_w')]
    pb = lambda r: f"p{T.binp(r['p_cal']):.2f}"
    # baseline by tour x price bin
    def stats(rs):
        n = len(rs)
        return dict(n=n, three_sets=round(sum(r['n_sets'] == 3 for r in rs) / n, 3), games=round(sum(r['games'] for r in rs) / n, 2), over_22_5=round(sum(r['games'] >= 23 for r in rs) / n, 3),
                    tiebreak=round(sum(r['tb'] for r in rs) / n, 3), set1_10plus=round(sum(r['s1_games'] >= 10 for r in rs) / n, 3), fav_straight=round(sum(r['fav_won'] and r['n_sets'] == 2 for r in rs) / n, 3))
    B = collections.defaultdict(list)
    for r in rows: B[(r['tour'], pb(r))].append(r)
    base = {k: stats(v) for k, v in B.items() if len(v) >= 300}
    R = {'baseline by tour x price': {f"{k[0]} {k[1]}": v for k, v in sorted(base.items())}}

    def cut(name, keyf, min_n=400):
        G = collections.defaultdict(list)
        for r in rows:
            k = keyf(r)
            if k is None or (r['tour'], pb(r)) not in base: continue
            G[k].append(r)
        out = {}
        for k, rs in sorted(G.items(), key=lambda kv: str(kv[0])):
            if len(rs) < min_n: continue
            s = stats(rs); bl = {f: sum(base[(r['tour'], pb(r))][f] for r in rs) / len(rs) for f in ('three_sets', 'games', 'over_22_5', 'tiebreak', 'set1_10plus', 'fav_straight')}
            out[str(k)] = dict(n=s['n'], **{f: s[f] for f in s if f != 'n'}, **{f'd_{f}': round(s[f] - bl[f], 3) for f in bl})
        R[name] = out
    hb = lambda h: None if h is None else ('85%+' if h >= .85 else '78-85%' if h >= .78 else '70-78%' if h >= .70 else 'under 70%')
    cut('1 combined hold rate (both players\' trailing hold, average)', lambda r: None if fav(r, 'hold') is None or dog(r, 'hold') is None else f"{r['tour']} avg hold {hb((fav(r, 'hold') + dog(r, 'hold')) / 2)}")
    cut('2 serve profile gap', lambda r: None if fav(r, 'hold') is None or dog(r, 'hold') is None else ('dog holds 3%+ more' if dog(r, 'hold') - fav(r, 'hold') >= .03 else 'fav holds 3%+ more' if fav(r, 'hold') - dog(r, 'hold') >= .03 else 'similar'))
    cut('3 both big servers (85%+) vs both breakable (under 75%)', lambda r: None if fav(r, 'hold') is None or dog(r, 'hold') is None else (f"{r['tour']} both 85%+" if min(fav(r, 'hold'), dog(r, 'hold')) >= .85 else f"{r['tour']} both under 75%" if max(fav(r, 'hold'), dog(r, 'hold')) < .75 else None), 200)
    rb = lambda b: None if b is None else ('returns well (breaks 30%+)' if b >= .30 else 'breaks 20-30%' if b >= .20 else 'weak return (under 20%)')
    cut('4 return quality (trailing break rate achieved), both players', lambda r: None if fav(r, 'brk') is None or dog(r, 'brk') is None else f"fav {rb(fav(r, 'brk'))} / dog {rb(dog(r, 'brk'))}")
    cut('5 serve-vs-return: big server (85%+) against a strong returner (30%+)', lambda r: None if fav(r, 'hold') is None or dog(r, 'brk') is None or dog(r, 'hold') is None or fav(r, 'brk') is None else ('fav big server vs dog strong returner' if fav(r, 'hold') >= .85 and dog(r, 'brk') >= .30 else 'dog big server vs fav strong returner' if dog(r, 'hold') >= .85 and fav(r, 'brk') >= .30 else 'big server vs weak returner' if (fav(r, 'hold') >= .85 and dog(r, 'brk') < .20) or (dog(r, 'hold') >= .85 and fav(r, 'brk') < .20) else None), 200)
    cut('6 surface x combined hold', lambda r: None if fav(r, 'hold') is None or dog(r, 'hold') is None else f"{r['surface']} avg hold {hb((fav(r, 'hold') + dog(r, 'hold')) / 2)}")
    cut('7 lefty in the match', lambda r: 'lefty vs righty' if {r['w_hand'], r['l_hand']} == {'L', 'R'} else 'both right' if r['w_hand'] == 'R' and r['l_hand'] == 'R' else None)
    cut('8 age: both 30+ vs both under 23', lambda r: None if not r.get('w_age') or not r.get('l_age') else ('both 30+' if min(r['w_age'], r['l_age']) >= 30 else 'both under 23' if max(r['w_age'], r['l_age']) < 23 else None), 300)
    cut('9 head-to-head history: 3+ prior meetings', lambda r: '3+ prior meetings' if r['w_h2h'] + r['l_h2h'] >= 3 else 'first meeting' if r['w_h2h'] + r['l_h2h'] == 0 else None)
    cut('10 round', lambda r: r.get('rnd') if r.get('rnd') in ('F', 'SF', 'QF', 'R16', 'R32', 'R64', 'R128') else None)
    cut('11 both players in their first match of the event vs both have played', lambda r: 'both first match' if r['w_first'] and r['l_first'] else 'both have played' if not r['w_first'] and not r['l_first'] else None)
    json.dump(R, open(OUT, 'w'), indent=1)
    for k, v in R.items():
        print(f"\n== {k}")
        for kk, vv in v.items(): print(f"  {kk:52} " + ' '.join(f"{a}={b}" for a, b in vv.items()))


if __name__ == '__main__':
    main()
