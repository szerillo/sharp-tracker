#!/usr/bin/env python3
"""Polymarket sharp accounts re-scored at PINNACLE's close instead of Polymarket's own close (Sean, 11/5: "do ... poly too").
Why: the live list ranks accounts by CLV against Polymarket's two-sided close, which the accounts themselves move. Pinnacle's closing
no-vig price is an outside yardstick. Every settled Polymarket game market with a trade file is matched to the Odds API database by
sport, start time and team names; moneylines are scored against Pinnacle's no-vig close, spreads and totals only when Polymarket's line
equals Pinnacle's closing line (then the two Pinnacle prices give the fair price at that number).
Tests: (1) agreement of the two rankings; (2) out of sample (rank on the first two thirds, follow on the last third): following the top 200 by
Pinnacle-CLV vs by Polymarket-CLV, ROI at their fill prices and CLV vs Pinnacle; (3) combinations on the held-out fills: with vs against
Pinnacle's open-to-close move, fills already priced inside Pinnacle's fair at fill time, favourite vs dog, by market and sport.
Writes data/research/poly_pinnacle.json. Usage: python3 sharp/poly_pinnacle.py"""
import os, sys, json, gzip, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.flow_volume as V, sharp.rule_replay as RR
from sharp.sharp_accounts2 import Px
OUT = os.environ.get('POLY_OUT') or os.path.join(ROOT, 'data', 'research', 'poly_pinnacle.json')
TAG = {'nba': 'nba', 'nfl': 'nfl', 'nhl': 'nhl', 'cfb': 'cfb', 'cbb': 'cbb', 'mlb': 'mlb', 'wnba': 'wnba', 'ufc': 'mma'}
MIN_USD = 100.0


def nv(a, b):
    """Two decimal prices -> no-vig probability of the first."""
    if not a or not b: return None
    pa, pb = 1 / a, 1 / b
    return pa / (pa + pb)


RES = {}      # sport -> (sorted residuals actual total - closing total, sorted residuals home margin + closing home spread, pooled with their mirror)
def index():
    """(sport, date) -> [games] from the odds database, with normalised names. Also builds the residual distributions used to price a
    Polymarket line that differs from Pinnacle's closing number."""
    I = collections.defaultdict(list)
    for sp in sorted(set(TAG.values())):
        rt, rs = [], []
        for g in RR.load(sp):
            if g.get('hs') is None: continue
            if g.get('tot_close') is not None: rt.append(g['hs'] + g['as_'] - g['tot_close'])
            if g.get('sp_close') is not None: m = g['hs'] - g['as_'] + g['sp_close']; rs += [m, -m]
            g['_h'] = nz(g['home']); g['_a'] = nz(g['away'])
            for d in (-1, 0, 1): I[(sp, (g['start'] + dt.timedelta(days=d)).date())].append(g)
        RES[sp] = (sorted(rt), sorted(rs))
    return I


def nz(x): return ''.join(ch for ch in (x or '').lower() if ch.isalnum())


def names(c):
    """The two team (or fighter) names of a market: the outcomes for sides, the title ("A vs. B") for totals and yes/no markets."""
    o = c['outcomes']
    if len(o) == 2 and not any(x.lower() in ('over', 'under', 'yes', 'no') for x in o): return nz(o[0]), nz(o[1])
    t = c.get('title') or ''
    if ':' in t.split(' vs')[0]: t = t.split(':', 1)[1]
    t = t.split('(')[0]
    parts = [x.strip() for x in t.replace(' vs. ', ' vs ').split(' vs ')]
    if len(parts) != 2 or not all(parts): return None
    return nz(parts[0]), nz(parts[1])


def match(I, c, st):
    sp = TAG.get(c['tag']); nm = names(c)
    if not sp or not nm: return None
    if c['market'] == 'spread' and set(x.lower() for x in c['outcomes']) == {'yes', 'no'}: return None       # cannot tell which side the line is on
    o0, o1 = nm; t0 = dt.datetime.fromtimestamp(st, dt.timezone.utc)
    best = None
    for g in I.get((sp, t0.date()), []):
        if abs((g['start'] - t0).total_seconds()) > 3 * 3600: continue
        if o0 in g['_a'] and o1 in g['_h']: side0 = 'away'
        elif o0 in g['_h'] and o1 in g['_a']: side0 = 'home'
        else: continue
        if best is None or abs((g['start'] - t0).total_seconds()) < abs((best[0]['start'] - t0).total_seconds()): best = (g, side0)
    return best


def p_exceed(arr, x):
    """P(residual > x) with half credit on ties, from a sorted residual list."""
    import bisect
    if not arr: return None
    lo = bisect.bisect_left(arr, x); hi = bisect.bisect_right(arr, x)
    return ((len(arr) - hi) + 0.5 * (hi - lo)) / len(arr)


MAX_SHIFT = 3.0
def fair(c, g, side0):
    """Pinnacle's closing fair probability of outcome 0. At Pinnacle's own number the two closing prices give it (no-vig); at a different
    Polymarket line (within 3 points) it is Pinnacle's close shifted along the sport's empirical residual distribution. fair.kind says which."""
    fair.kind = None
    if c['market'] == 'ml':
        p = g.get('p_close')
        if p is None: return None
        return p if side0 == 'home' else 1 - p
    if c['market'] == 'spread':
        if g.get('sp_close') is None or c.get('line') is None: return None
        ln0 = g['sp_close'] if side0 == 'home' else -g['sp_close']            # Pinnacle's closing line for outcome 0
        l0 = float(c['line'])
        if abs(l0 - ln0) <= 1e-9:
            p = nv(g.get('sp_home_dec'), g.get('sp_away_dec'))
            if p is None: return None
            fair.kind = 'exact'; return p if side0 == 'home' else 1 - p
        if abs(l0 - ln0) > MAX_SHIFT: return None
        # outcome 0 covers l0 when margin0 + l0 > 0; margin0 = -ln0 + residual, so covers when residual > ln0 - l0
        p = p_exceed(RES[g['sport']][1], ln0 - l0); fair.kind = 'shifted'; return p
    if c['market'] == 'total':
        if g.get('tot_close') is None or c.get('line') is None: return None
        L = float(c['line'])
        if abs(L - g['tot_close']) <= 1e-9:
            p = nv(g.get('over_dec'), g.get('under_dec'))
            if p is None: return None
            fair.kind = 'exact'
        else:
            if abs(L - g['tot_close']) > MAX_SHIFT: return None
            p = p_exceed(RES[g['sport']][0], L - g['tot_close']); fair.kind = 'shifted'        # P(actual total > L)
        return p if o_is_over(c) else 1 - p
    return None


def o_is_over(c): return 'over' in c['outcomes'][0].lower()


def move(c, g, side0):
    """Pinnacle open -> close move in favour of outcome 0, in no-vig points (ml) or half-points (spread/total). None when no open."""
    if c['market'] == 'ml':
        if g.get('p_open') is None or g.get('p_close') is None: return None
        d = 100 * (g['p_close'] - g['p_open']); return d if side0 == 'home' else -d
    if c['market'] == 'spread':
        if g.get('sp_open') is None or g.get('sp_close') is None: return None
        d = g['sp_open'] - g['sp_close']; return d if side0 == 'home' else -d      # a home -7 that closes -7.5 moved for the home side
    if c['market'] == 'total':
        if g.get('tot_open') is None or g.get('tot_close') is None: return None
        d = g['tot_close'] - g['tot_open']; return d if o_is_over(c) else -d
    return None


def main():
    I = index(); MK = V.poly_markets(); cut = MK[int(len(MK) * 2 / 3)][1]
    if os.environ.get('POLY_CUT'): cut = dt.datetime.fromisoformat(os.environ['POLY_CUT']).replace(tzinfo=dt.timezone.utc).timestamp()     # 11/10: rank before this date, follow after it
    print('polymarket markets with trades:', len(MK), 'cut', dt.datetime.utcfromtimestamp(cut).date(), flush=True)
    W = collections.defaultdict(lambda: dict(pin=0.0, poly=0.0, n=0, games=set(), roi=0.0, n_poly=0))
    F = []; stats = collections.Counter()
    for i, (c, st) in enumerate(MK):
        if i % 5000 == 0: print(i, dict(stats), flush=True)
        m = match(I, c, st)
        if not m: stats['unmatched ' + c['tag']] += 1; continue
        g, side0 = m; fp = fair(c, g, side0)
        if fp is None: stats['no pinnacle price ' + c['market']] += 1; continue
        stats['scored ' + c['market'] + ' ' + (fair.kind or '')] += 1
        L = V.poly_trades(c, st)
        if len(L) < 5: continue
        P = Px([x[:4] for x in L]); cl = P.at(st); ry = 1 if c['winner'] == c['outcomes'][0] else 0; mv = move(c, g, side0)
        for t, py, usd, d, w in L:
            if usd < MIN_USD or not w: continue
            price = py if d > 0 else 1 - py; fair_side = fp if d > 0 else 1 - fp; won = ry if d > 0 else 1 - ry
            clv_pin = 100 * (fair_side - price); clv_poly = 100 * (((cl if d > 0 else 1 - cl) - price)) if cl is not None else None
            roi = ((1 - price) / price if won else -1.0)
            if st < cut:
                x = W[w]; x['pin'] += clv_pin; x['n'] += 1; x['games'].add(g['id']); x['roi'] += roi
                if clv_poly is not None: x['poly'] += clv_poly; x['n_poly'] += 1
            else:
                F.append(dict(w=w, clv_pin=clv_pin, clv_poly=clv_poly, roi=roi, price=price, fair=fair_side, mv=(mv if d > 0 else -mv) if mv is not None else None,
                              mkt=c['market'], sport=c['tag'], fav=fair_side >= 0.5, inside=price < fair_side, t_to=st - t, kind=fair.kind))
    print('markets', dict(stats), 'train accounts', len(W), 'test fills', len(F), flush=True)
    sc = {w: x for w, x in W.items() if x['n'] >= 30 and len(x['games']) >= 15 and x['n_poly'] >= 30}
    for x in sc.values(): x['pin_m'] = x['pin'] / x['n']; x['poly_m'] = x['poly'] / x['n_poly']; x['roi_m'] = x['roi'] / x['n']
    by_pin = sorted(sc, key=lambda w: -sc[w]['pin_m']); by_poly = sorted(sc, key=lambda w: -sc[w]['poly_m'])
    # (1) agreement
    rk_pin = {w: i for i, w in enumerate(by_pin)}; rk_poly = {w: i for i, w in enumerate(by_poly)}; n = len(sc)
    rho = 1 - 6 * sum((rk_pin[w] - rk_poly[w]) ** 2 for w in sc) / (n * (n * n - 1)) if n > 2 else None
    top_pin, top_poly = set(by_pin[:200]), set(by_poly[:200])
    agree = dict(accounts_scored=n, spearman=round(rho, 3) if rho is not None else None, top200_overlap=len(top_pin & top_poly),
                 mean_pin_clv_all=round(sum(x['pin_m'] for x in sc.values()) / n, 2) if n else None,
                 mean_poly_clv_all=round(sum(x['poly_m'] for x in sc.values()) / n, 2) if n else None)

    def follow(S, label, fills=None):
        S = set(S); R = [f for f in (fills if fills is not None else F) if f['w'] in S]
        if not R: return dict(label=label, n=0)
        roi = sum(f['roi'] for f in R) / len(R) * 100; clv = sum(f['clv_pin'] for f in R) / len(R)
        wins = sum(1 for f in R if f['roi'] > 0)
        return dict(label=label, n=len(R), accounts=len({f['w'] for f in R}), roi=round(roi, 1), clv_pin=round(clv, 2), win_rate=round(wins / len(R) * 100, 1),
                     clv_poly=round(sum(f['clv_poly'] for f in R if f['clv_poly'] is not None) / max(1, sum(1 for f in R if f['clv_poly'] is not None)), 2))
    by_roi = sorted(sc, key=lambda w: -sc[w]['roi_m']); top_roi = set(by_roi[:200])
    W_tot = {w: x for w, x in W.items() if x['n'] >= 30 and len(x['games']) >= 15}       # totals-inclusive pool, no Polymarket-close requirement
    oos = [follow(by_pin[:200], 'top 200 by Pinnacle CLV'), follow(by_poly[:200], 'top 200 by Polymarket CLV'), follow(top_pin & top_poly, 'in both top 200s'),
           follow(by_roi[:200], 'top 200 by past ROI at fill (Sean 11/5: ROI decides)'), follow(top_roi & top_poly, 'in ROI top 200 and Polymarket-CLV top 200'),
           follow(top_roi - top_poly, 'ROI top 200 only'), follow(by_roi[:50], 'top 50 by past ROI'),
           follow(top_pin - top_poly, 'Pinnacle top 200 only'), follow(top_poly - top_pin, 'Polymarket top 200 only'), follow(by_pin[:50], 'top 50 by Pinnacle CLV'),
           follow(by_poly[:50], 'top 50 by Polymarket CLV'), follow(sc, 'every qualified account (baseline)'), follow(by_pin[-200:], 'bottom 200 by Pinnacle CLV (fade?)')]
    # (3) combinations on the held-out fills of the Polymarket top 200 (the live list's method) and of the Pinnacle top 200
    combos = {}
    for name, S in (('poly_top200', top_poly), ('pin_top200', top_pin), ('roi_top200', top_roi)):
        R = [f for f in F if f['w'] in S]; C = {}
        C['with the Pinnacle move'] = follow(S, 'with', [f for f in R if f['mv'] is not None and f['mv'] > 0])
        C['against the Pinnacle move'] = follow(S, 'against', [f for f in R if f['mv'] is not None and f['mv'] < 0])
        C['no move'] = follow(S, 'flat', [f for f in R if f['mv'] is not None and f['mv'] == 0])
        C['fill already inside Pinnacle fair (price < fair)'] = follow(S, 'inside', [f for f in R if f['inside']])
        C['fill outside Pinnacle fair (price >= fair)'] = follow(S, 'outside', [f for f in R if not f['inside']])
        C['favourite side (fair >= 50%)'] = follow(S, 'fav', [f for f in R if f['fav']])
        C['dog side'] = follow(S, 'dog', [f for f in R if not f['fav']])
        C['inside fair AND with the move'] = follow(S, 'both', [f for f in R if f['inside'] and f['mv'] is not None and f['mv'] > 0])
        C['outside fair AND against the move'] = follow(S, 'neither', [f for f in R if not f['inside'] and f['mv'] is not None and f['mv'] < 0])
        for mk in ('ml', 'spread', 'total'): C[f'market {mk}'] = follow(S, mk, [f for f in R if f['mkt'] == mk])
        for kd in ('exact', 'shifted'): C[f'priced at Pinnacle number: {kd}'] = follow(S, kd, [f for f in R if f['kind'] == kd])
        for spt in sorted({f['sport'] for f in R}): C[f'sport {spt}'] = follow(S, spt, [f for f in R if f['sport'] == spt])
        for spt in ('nba', 'nfl', 'cfb', 'nhl'):
            C[f'{spt} totals'] = follow(S, spt, [f for f in R if f['sport'] == spt and f['mkt'] == 'total']); C[f'{spt} sides (ml+spread)'] = follow(S, spt, [f for f in R if f['sport'] == spt and f['mkt'] != 'total'])
            C[f'{spt} sides WITH the Pinnacle move'] = follow(S, spt, [f for f in R if f['sport'] == spt and f['mkt'] != 'total' and f['mv'] is not None and f['mv'] > 0])
            C[f'{spt} sides AGAINST the move'] = follow(S, spt, [f for f in R if f['sport'] == spt and f['mkt'] != 'total' and f['mv'] is not None and f['mv'] < 0])
        C['inside the last hour'] = follow(S, 'late', [f for f in R if f['t_to'] <= 3600]); C['earlier than 6h out'] = follow(S, 'early', [f for f in R if f['t_to'] > 6 * 3600])
        combos[name] = C
    res = dict(asof=dt.datetime.utcnow().isoformat() + 'Z', markets=dict(stats), cut=dt.datetime.utcfromtimestamp(cut).isoformat() + 'Z', agreement=agree, out_of_sample=oos,
               combinations=combos, top20_pinnacle=[dict(w=w, pin_clv=round(sc[w]['pin_m'], 2), poly_clv=round(sc[w]['poly_m'], 2), fills=sc[w]['n'], roi=round(sc[w]['roi_m'] * 100, 1),
                                                         poly_rank=rk_poly[w] + 1) for w in by_pin[:20]])
    os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(res, open(OUT, 'w'), indent=1)
    print(json.dumps(agree)); [print(o) for o in oos]
    for name, C in combos.items():
        print('==', name)
        for k, v in C.items(): print(f"  {k:55s} n={v.get('n',0):5d} roi={v.get('roi')} clv_pin={v.get('clv_pin')}")
    print('wrote', OUT)


if __name__ == '__main__':
    main()
