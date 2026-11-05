#!/usr/bin/env python3
"""Tennis: the market test (Sean, 11/4: "this is a comprehensive database im sure we can find an edge somewhere"). Tennis Abstract has
no prices, so every structural finding in sharp/tennis_ta.py and tennis_ta2.py is tested here against the Pinnacle closing match price
from tennis-data.co.uk (the deuce R package's bundled tables in data/tennis/odds, pulled by .github/workflows/tennis_odds.yml: the
four Grand Slam main draws a year per tour (508 matches a year), 2010-Jan 2023 (joined 2015+), Pinnacle PSW/PSL, Bet365, market max and average, set scores).

Join: odds row -> Tennis Abstract match by tour, surname + first initial of both players, match date inside the event window, and the
set-1 score. Then, for every cut, the real question: does the side the cut points at beat the CLOSE? Reported as
  edge  = actual win rate - Pinnacle no-vig probability (percent; the market residual; +-SE),
  roi   = flat 1u on the cut's side at the Pinnacle close (percent of risk),
  elo   = Elo's view of the same side (calibrated p minus market), to see when Elo and the market disagree.
Match market only: there are no set-1 or games odds in this data. Writes data/research/tennis_edge.json.
Usage: python3 sharp/tennis_edge.py"""
import os, sys, csv, gzip, json, math, re, collections, unicodedata, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.tennis_ta as T
import sharp.tennis_ta2 as T2
import sharp.tennis_ta3 as T3
ODDS = os.path.join(ROOT, 'data', 'tennis', 'odds'); OUT = os.path.join(ROOT, 'data', 'research', 'tennis_edge.json')


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z]', '', s.lower())


def key_odds(name):
    """'Bautista Agut R.' -> ('bautistaagut', 'r'); 'Auger-Aliassime F.' -> ('augeraliassime', 'f'); 'Zverev A.' -> ('zverev', 'a')."""
    name = (name or '').strip()
    m = re.match(r'^(.*?)\s+([A-Z])(?:\.[A-Z]\.?|\.)?(?:\s*[A-Z]\.)*$', name)
    if not m: return (norm(name), '')
    return (norm(m.group(1)), m.group(2).lower())


def key_ta(name):
    """'Roberto Bautista Agut' -> ('bautistaagut', 'r'); 'Felix Auger Aliassime' -> ('augeraliassime', 'f')."""
    parts = (name or '').replace('-', ' ').split()
    if len(parts) < 2: return (norm(name), '')
    return (norm(''.join(parts[1:])), norm(parts[0])[:1])


def odds_sources(tour):
    """Rows from the deuce bundle (csv.gz) plus any tennis-data.co.uk workbooks dropped in as <tour>_<year>.xlsx / .xls."""
    f = os.path.join(ODDS, f'{tour}_odds.csv.gz'); seen = set()
    if os.path.exists(f):
        for r in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8', errors='replace')):
            seen.add((r.get('Date', '')[:10], r.get('Winner'), r.get('Loser'))); yield r
    import glob
    for wb in sorted(glob.glob(os.path.join(ODDS, f'{tour}_*.xls*'))):
        try:
            import pandas as pd
            df = pd.read_excel(wb)
        except Exception as e:
            print('skip', wb, e); continue
        for r in df.to_dict('records'):
            r = {k: ('' if (isinstance(v, float) and math.isnan(v)) else v) for k, v in r.items()}
            r['Date'] = str(r.get('Date', ''))[:10]
            if (r['Date'], r.get('Winner'), r.get('Loser')) in seen: continue
            yield r


def load_odds():
    rows = []
    for tour in ('atp', 'wta'):
        for r in odds_sources(tour):
            def num(x):
                try: return float(x)
                except Exception: return None
            psw, psl = num(r.get('PSW')), num(r.get('PSL'))
            r['_src'] = 'pin' if psw else 'b365'
            if (not psw or not psl) and num(r.get('B365W')) and num(r.get('B365L')): psw, psl = num(r.get('B365W')), num(r.get('B365L'))   # 2000-2003 and WTA 2009 have no Pinnacle column
            if not psw or not psl or psw < 1.001 or psl < 1.001: continue
            try: d = dt.datetime.strptime(r['Date'][:10], '%Y-%m-%d').date()
            except Exception: continue
            rows.append(dict(tour=tour, date=d, tourney=r.get('Tournament'), surface=r.get('Surface'), rnd=r.get('Round'), bo=int(float(r.get('Best.of') or 3)),
                             wk=key_odds(r.get('Winner')), lk=key_odds(r.get('Loser')), wname=r.get('Winner'), lname=r.get('Loser'),
                             w1=num(r.get('W1')), l1=num(r.get('L1')), psw=psw, psl=psl, b365w=num(r.get('B365W')), b365l=num(r.get('B365L')),
                             maxw=num(r.get('MaxW')), maxl=num(r.get('MaxL')), avgw=num(r.get('AvgW')), avgl=num(r.get('AvgL')), comment=r.get('Comment')))
    return rows


def join(M, O):
    """Index TA matches by (tour, winner key, loser key); accept the odds row when its date falls in [tourney_date, +21d] and set 1 agrees."""
    idx = collections.defaultdict(list)
    for m in M:
        if m['level'] in ('qual_itf', 'futures'): continue
        idx[(m['tour'], key_ta(m['wn']), key_ta(m['ln']))].append(m)
    out = []; miss = collections.Counter()
    for o in O:
        cands = idx.get((o['tour'], o['wk'], o['lk']), [])
        best = None
        for m in cands:
            td = dt.date(m['date'] // 10000, m['date'] // 100 % 100, m['date'] % 100)
            gap = (o['date'] - td).days
            if not (-2 <= gap <= 21): continue
            if o['w1'] is not None and o['l1'] is not None and m.get('score'):
                st = T2.sets_of(m['score'])
                if st and (st[0][0], st[0][1]) != (int(o['w1']), int(o['l1'])): continue
            if best is None or abs(gap) < abs((o['date'] - dt.date(best['date'] // 10000, best['date'] // 100 % 100, best['date'] % 100)).days): best = m
        if best is None: miss['no match' if not cands else 'date/score'] += 1; continue
        out.append((o, best))
    return out, miss


def se(p, n): return math.sqrt(max(p * (1 - p), 1e-9) / n) * 100 if n else None


def records():
    M = T.load(); T.elo_run(M); T.serve_profiles(M); T2.annotate(M); T3.fatigue(M)
    rows = T.fav_rows(M)
    cal = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for r in rows: c = cal[T.grp(r)][T.binp(r['p'])]; c[0] += 1; c[1] += r['fav_won']
    for r in rows:
        c = cal[T.grp(r)].get(T.binp(r['p'])); r['p_cal'] = c[1] / c[0] if c and c[0] >= 100 else None
    byid = {(r['date'], r['w'], r['l']): r for r in rows}
    O = load_odds(); print(f"odds rows with a Pinnacle price: {len(O)}")
    J, miss = join([r for r in rows], O); print(f"joined to Tennis Abstract: {len(J)}  unmatched: {dict(miss)}")
    # one record per joined match, from the market favourite's side
    R = []
    for o, m in J:
        qw, ql = 1 / o['psw'], 1 / o['psl']; pw = qw / (qw + ql)            # Pinnacle no-vig P(winner)
        fav_is_w = pw >= 0.5
        mkt = pw if fav_is_w else 1 - pw                                       # market fav probability
        fav_won = fav_is_w                                                     # the market favourite won iff the winner was the favourite
        price_fav = o['psw'] if fav_is_w else o['psl']; price_dog = o['psl'] if fav_is_w else o['psw']
        # Elo: m is the Elo-favourite row; translate to the market favourite's side
        elo_mkt_fav = m['p_cal'] if (m['fav_won'] == fav_is_w) else (1 - m['p_cal'] if m['p_cal'] is not None else None)
        side = lambda k: m[('w_' if fav_is_w else 'l_') + k]                   # market fav's TA fields
        oside = lambda k: m[('l_' if fav_is_w else 'w_') + k]
        R.append(dict(tour=o['tour'], year=o['date'].year, surface=m['surface'], bo=m['bo'], level=T.grp(m), rnd=m.get('rnd'), mkt=mkt, fav_won=fav_won,
                      price_fav=price_fav, price_dog=price_dog, elo=elo_mkt_fav, hold=o['date'].year >= 2023 or False,
                      fav_form=m['form_w'] if fav_is_w else m['form_l'], dog_form=m['form_l'] if fav_is_w else m['form_w'],
                      fav_first=side('first'), dog_first=oside('first'), fav_layoff=side('layoff'), dog_layoff=oside('layoff'),
                      fav_switch=side('switch'), dog_switch=oside('switch'), fav_h2h=side('h2h'), dog_h2h=oside('h2h'),
                      fav_entry=side('entry'), dog_entry=oside('entry'), fav_hand=side('hand'), dog_hand=oside('hand'),
                      fav_prev=m.get('w_prev' if fav_is_w else 'l_prev'), dog_prev=m.get('l_prev' if fav_is_w else 'w_prev'), fav_played=m.get('w_played' if fav_is_w else 'l_played'), dog_played=m.get('l_played' if fav_is_w else 'w_played'),
                      fav_hold=(m.get('hold_w') if fav_is_w else m.get('hold_l')), dog_hold=(m.get('hold_l') if fav_is_w else m.get('hold_w')),
                      b365_fav=(o['b365w'] if fav_is_w else o['b365l']), b365_dog=(o['b365l'] if fav_is_w else o['b365w']),
                      max_fav=(o['maxw'] if fav_is_w else o['maxl']), max_dog=(o['maxl'] if fav_is_w else o['maxw'])))
    print(f"records: {len(R)}  years {min(r['year'] for r in R)}-{max(r['year'] for r in R)}")
    return R, O, J, miss


def main():
    R, O, J, miss = records()
    res = {'n_odds': len(O), 'n_joined': len(J), 'unmatched': dict(miss)}

    def cut(name, keyf, sidef, rows_=R, min_n=60):
        """keyf -> bucket label or None; sidef(r) -> 'fav' or 'dog' (the side the cut says to bet)."""
        Tt = collections.defaultdict(lambda: dict(n=0, won=0, q=0.0, pnl=0.0, elo=0.0, n_elo=0, pnl_max=0.0, n_max=0))
        for r in rows_:
            k = keyf(r)
            if k is None: continue
            s = sidef(r); t = Tt[k]
            win = r['fav_won'] if s == 'fav' else not r['fav_won']
            q = r['mkt'] if s == 'fav' else 1 - r['mkt']
            price = r['price_fav'] if s == 'fav' else r['price_dog']
            t['n'] += 1; t['won'] += win; t['q'] += q; t['pnl'] += (price - 1) if win else -1
            if r['elo'] is not None: t['elo'] += (r['elo'] if s == 'fav' else 1 - r['elo']) - q; t['n_elo'] += 1
            mx = r['max_fav'] if s == 'fav' else r['max_dog']
            if mx: t['pnl_max'] += (mx - 1) if win else -1; t['n_max'] += 1
        out = {}
        for k, t in sorted(Tt.items(), key=lambda kv: str(kv[0])):
            if t['n'] < min_n: continue
            wr = t['won'] / t['n']; q = t['q'] / t['n']
            out[str(k)] = dict(n=t['n'], side=sidef(next(r for r in rows_ if keyf(r) == k)), win_rate=round(wr, 3), market=round(q, 3), edge=round(100 * (wr - q), 1), se=round(se(q, t['n']), 1),
                               roi=round(100 * t['pnl'] / t['n'], 1), roi_best_price=round(100 * t['pnl_max'] / t['n_max'], 1) if t['n_max'] else None,
                               elo_vs_market=round(100 * t['elo'] / t['n_elo'], 1) if t['n_elo'] else None)
        res[name] = out
    fav, dog = (lambda r: 'fav'), (lambda r: 'dog')
    # 0. the market itself: favourite-longshot bias by price bucket (bet the favourite)
    cut('0 market calibration by Pinnacle favourite probability (bet fav)', lambda r: f"{math.floor(r['mkt'] * 20) / 20:.2f}", fav)
    cut('0b by tour (bet fav)', lambda r: r['tour'], fav)
    cut('0c by level (bet fav)', lambda r: r['level'], fav)
    # 1. Elo vs the market
    E = [r for r in R if r['elo'] is not None]
    def elo_edge(r):
        d = r['elo'] - r['mkt']
        return d
    cut('1 Elo disagrees with the close: bet the side Elo likes, by Elo-market gap', lambda r: ('Elo likes fav by 8%+' if elo_edge(r) >= .08 else 'Elo likes fav 4-8%' if elo_edge(r) >= .04 else 'Elo likes dog 4-8%' if elo_edge(r) <= -.04 and elo_edge(r) > -.08 else 'Elo likes dog by 8%+' if elo_edge(r) <= -.08 else 'within 4%'),
        lambda r: 'fav' if elo_edge(r) > 0 else 'dog', E)
    cut('1b same, holdout 2021-2023', lambda r: ('Elo likes fav by 5%+' if elo_edge(r) >= .05 else 'Elo likes dog by 5%+' if elo_edge(r) <= -.05 else 'within 5%'), lambda r: 'fav' if elo_edge(r) > 0 else 'dog', [r for r in E if r['year'] >= 2021], min_n=40)
    cut('1c Elo picks the other player (Elo dog is the market fav): bet Elo favourite', lambda r: 'Elo favourite is the market dog' if r['elo'] < 0.5 else None, dog, E)
    # 2. form
    F = [r for r in R if r['fav_form'] is not None and r['dog_form'] is not None]
    cut('2 form (last 10), bet the hotter side', lambda r: ('fav hotter by 30%+' if r['fav_form'] - r['dog_form'] >= .3 else 'dog hotter by 30%+' if r['dog_form'] - r['fav_form'] >= .3 else 'dog hotter 10-30%' if r['dog_form'] - r['fav_form'] >= .1 else 'fav hotter 10-30%' if r['fav_form'] - r['dog_form'] >= .1 else 'similar'),
        lambda r: 'fav' if r['fav_form'] >= r['dog_form'] else 'dog', F)
    hot = lambda r: r['fav_form'] - r['dog_form'] >= .3
    cut('2b favourite hotter by 30%+, by year (bet fav)', lambda r: str(r['year']) if hot(r) else None, fav, F, min_n=40)
    cut('2c favourite hotter by 30%+, by tour and price (bet fav)', lambda r: f"{r['tour']} {'fav under 70%' if r['mkt'] < .7 else 'fav 70-85%' if r['mkt'] < .85 else 'fav 85%+'}" if hot(r) else None, fav, F, min_n=40)
    cut('2d favourite hotter by 30%+ and Elo agrees with the market within 5% (bet fav)', lambda r: 'hot fav, Elo agrees' if hot(r) and r['elo'] is not None and abs(r['elo'] - r['mkt']) < .05 else 'hot fav, Elo likes the dog 5%+' if hot(r) and r['elo'] is not None and r['elo'] - r['mkt'] <= -.05 else None, fav, F, min_n=40)
    # 3. rust, layoffs, surface switches (tour + Challenger)
    cut('3 first match of the event (bet the side that has already played)', lambda r: ('fav first match, dog has played' if r['fav_first'] and not r['dog_first'] else 'dog first match, fav has played' if r['dog_first'] and not r['fav_first'] else 'both first match' if r['fav_first'] else 'both have played'),
        lambda r: 'dog' if (r['fav_first'] and not r['dog_first']) else 'fav')
    FB = [r for r in R if r['fav_first'] and r['dog_first'] and r['fav_layoff'] is not None and r['dog_layoff'] is not None]
    cut('4 layoff 28+ days, both in their first match (bet the rested side\'s opponent)', lambda r: ('fav off 28+ days' if r['fav_layoff'] and not r['dog_layoff'] else 'dog off 28+ days' if r['dog_layoff'] and not r['fav_layoff'] else 'both off 28+' if r['fav_layoff'] else 'neither'),
        lambda r: 'dog' if (r['fav_layoff'] and not r['dog_layoff']) else 'fav', FB, min_n=40)
    cut('5 surface switch, both in their first match (bet the side that did not switch)', lambda r: ('fav switched, dog did not' if r['fav_switch'] and not r['dog_switch'] else 'dog switched, fav did not' if r['dog_switch'] and not r['fav_switch'] else 'both switched' if r['fav_switch'] else 'neither'),
        lambda r: 'dog' if (r['fav_switch'] and not r['dog_switch']) else 'fav', [r for r in R if r['fav_first'] and r['dog_first']], min_n=40)
    cut('5b surface switch, all matches', lambda r: ('fav switched, dog did not' if r['fav_switch'] and not r['dog_switch'] else 'dog switched, fav did not' if r['dog_switch'] and not r['fav_switch'] else None),
        lambda r: 'dog' if (r['fav_switch'] and not r['dog_switch']) else 'fav', min_n=40)
    # 6. head-to-head, entries, hands
    cut('6 head-to-head (bet the h2h leader)', lambda r: ('dog leads h2h' if r['dog_h2h'] > r['fav_h2h'] else 'fav leads h2h' if r['fav_h2h'] > r['dog_h2h'] else 'no edge / level'), lambda r: 'dog' if r['dog_h2h'] > r['fav_h2h'] else 'fav')
    cut('6b dog leads h2h by 2+ (bet dog)', lambda r: 'dog leads by 2+' if r['dog_h2h'] - r['fav_h2h'] >= 2 else None, dog, min_n=30)
    cut('7 entry (bet dog)', lambda r: ('dog is a lucky loser' if r['dog_entry'] == 'LL' else 'dog is a qualifier' if r['dog_entry'] == 'Q' else 'dog is a wild card' if r['dog_entry'] == 'WC' else 'fav is a qualifier' if r['fav_entry'] == 'Q' else 'fav is a wild card' if r['fav_entry'] == 'WC' else None), dog, min_n=30)
    cut('8 lefties (bet the lefty)', lambda r: ('fav lefty vs righty' if r['fav_hand'] == 'L' and r['dog_hand'] == 'R' else 'dog lefty vs righty' if r['dog_hand'] == 'L' and r['fav_hand'] == 'R' else None), lambda r: 'fav' if r['fav_hand'] == 'L' else 'dog', min_n=40)
    # 9. serve profiles (match market; the set-1 effect cannot be priced here)
    H = [r for r in R if r['fav_hold'] is not None and r['dog_hold'] is not None]
    cut('9 serve profile (bet the bigger server)', lambda r: ('dog holds 3%+ more' if r['dog_hold'] - r['fav_hold'] >= .03 else 'fav holds 3%+ more' if r['fav_hold'] - r['dog_hold'] >= .03 else 'similar'), lambda r: 'dog' if r['dog_hold'] > r['fav_hold'] else 'fav', H, min_n=40)
    # 9b. fatigue from the previous match in the event (round 3 of the research: -5.8 match / -4.4 set 1 for a favourite off a long match vs a dog off a short one)
    PV = [r for r in R if r['fav_prev'] and r['dog_prev']]
    cut('9b previous match: long (28+ games) vs short (under 20); bet the fresher side', lambda r: ('fav long, dog short' if r['fav_prev']['games'] >= 28 and r['dog_prev']['games'] < 20 else 'dog long, fav short' if r['dog_prev']['games'] >= 28 and r['fav_prev']['games'] < 20 else None),
        lambda r: 'dog' if r['fav_prev']['games'] >= 28 and r['dog_prev']['games'] < 20 else 'fav', PV, min_n=40)
    cut('9c previous match: sets played; bet the fresher side', lambda r: f"fav {min(r['fav_prev']['sets'], 4)} sets / dog {min(r['dog_prev']['sets'], 4)} sets" if r['fav_prev']['sets'] != r['dog_prev']['sets'] else None,
        lambda r: 'dog' if r['fav_prev']['sets'] > r['dog_prev']['sets'] else 'fav', PV, min_n=40)
    cut('9d previous match: came from a set down; bet the other side', lambda r: ('fav came back, dog did not' if r['fav_prev']['came_back'] and not r['dog_prev']['came_back'] else 'dog came back, fav did not' if r['dog_prev']['came_back'] and not r['fav_prev']['came_back'] else None),
        lambda r: 'dog' if r['fav_prev']['came_back'] else 'fav', PV, min_n=40)
    cut('9e previous match: 5 sets (slams); bet the other side', lambda r: ('fav went 5, dog did not' if r['fav_prev']['sets'] == 5 and r['dog_prev']['sets'] <= 3 else 'dog went 5, fav did not' if r['dog_prev']['sets'] == 5 and r['fav_prev']['sets'] <= 3 else None),
        lambda r: 'dog' if r['fav_prev']['sets'] == 5 else 'fav', PV, min_n=40)
    # 10. rounds and best-of
    cut('10 round (bet fav)', lambda r: r['rnd'] if r['rnd'] in ('F', 'SF', 'QF', 'R16', 'R32', 'R64', 'R128') else None, fav)
    cut('10b best-of-5 vs 3 (bet fav)', lambda r: f"bo{r['bo']}", fav)
    # 11. Pinnacle vs the field: the market max vs Pinnacle (is there price to be had?)
    cut('11 shop: Pinnacle close vs best price in the market (bet fav)', lambda r: 'fav' , fav)
    json.dump(res, open(OUT, 'w'), indent=1)
    for k, v in res.items():
        if not isinstance(v, dict) or not v or not isinstance(next(iter(v.values())), dict): continue
        print(f"\n== {k}")
        for kk, vv in v.items(): print(f"  {kk:40} n={vv['n']:5} bet {vv['side']:3} win {vv['win_rate']:.3f} mkt {vv['market']:.3f} edge {vv['edge']:+5.1f} ±{vv['se']:.1f}  roi {vv['roi']:+5.1f}  best-price roi {vv['roi_best_price']}  elo-vs-mkt {vv['elo_vs_market']}")



def scan():
    """Sean, 11/4: results irrespective of CLV. Every simple angle (tour x round x surface x favourite price band, plus the feature cuts)
    scored by flat ROI at the Pinnacle close, at Bet365 and at the market's best price, with the number of positive years out of the
    years it covers. Reported: angles with n >= 150 and ROI > 0 at the close in at least 5 of the years. Many angles are tried, so
    anything here is a candidate for the live paper test, not a system."""
    R, O, J, miss = records()
    years = sorted({r['year'] for r in R})
    def pr(r, side, book):
        if side == 'fav': return r['price_fav'] if book == 'pin' else r['b365_fav'] if book == 'b365' else r['max_fav']
        return r['price_dog'] if book == 'pin' else r['b365_dog'] if book == 'b365' else r['max_dog']
    def roi(rows_, side, book):
        n = 0; pnl = 0.0
        for r in rows_:
            p = pr(r, side, book)
            if not p: continue
            win = r['fav_won'] if side == 'fav' else not r['fav_won']
            n += 1; pnl += (p - 1) if win else -1
        return (100 * pnl / n, n) if n else (None, 0)
    band = lambda r: 'fav 50-60' if r['mkt'] < .6 else 'fav 60-70' if r['mkt'] < .7 else 'fav 70-80' if r['mkt'] < .8 else 'fav 80-90' if r['mkt'] < .9 else 'fav 90+'
    rnd = lambda r: {'R128': 'R1', 'R64': 'R2', 'R32': 'R3', 'R16': 'R4'}.get(r['rnd'], 'QF+' if r['rnd'] in ('QF', 'SF', 'F') else None)
    dims = dict(tour=lambda r: r['tour'], round=rnd, surface=lambda r: r['surface'], band=band,
                form=lambda r: None if r['fav_form'] is None or r['dog_form'] is None else ('fav hot 30+' if r['fav_form'] - r['dog_form'] >= .3 else 'dog hot 30+' if r['dog_form'] - r['fav_form'] >= .3 else 'even form'),
                first=lambda r: 'fav first, dog played' if r['fav_first'] and not r['dog_first'] else 'dog first, fav played' if r['dog_first'] and not r['fav_first'] else 'both first' if r['fav_first'] else 'both played',
                h2h=lambda r: 'dog leads h2h' if r['dog_h2h'] > r['fav_h2h'] else 'fav leads h2h' if r['fav_h2h'] > r['dog_h2h'] else 'no h2h edge',
                entry=lambda r: 'dog Q/LL' if r['dog_entry'] in ('Q', 'LL') else 'dog WC' if r['dog_entry'] == 'WC' else 'dog direct',
                serve=lambda r: None if r['fav_hold'] is None or r['dog_hold'] is None else ('dog bigger server' if r['dog_hold'] - r['fav_hold'] >= .03 else 'fav bigger server' if r['fav_hold'] - r['dog_hold'] >= .03 else 'similar serve'),
                hand=lambda r: 'lefty dog' if r['dog_hand'] == 'L' and r['fav_hand'] == 'R' else 'lefty fav' if r['fav_hand'] == 'L' and r['dog_hand'] == 'R' else 'righties')
    import itertools
    names = list(dims); combos = [()] + [(a,) for a in names] + list(itertools.combinations(names, 2)) + [c for c in itertools.combinations(names, 3) if 'band' in c or 'tour' in c]
    out = []
    for combo in combos:
        groups = collections.defaultdict(list)
        for r in R:
            k = tuple(dims[d](r) for d in combo)
            if any(x is None for x in k): continue
            groups[k].append(r)
        for k, rows_ in groups.items():
            if len(rows_) < 150: continue
            for side in ('fav', 'dog'):
                rp, n = roi(rows_, side, 'pin')
                if rp is None or rp <= 0: continue
                ys = [roi([r for r in rows_ if r['year'] == y], side, 'pin') for y in years]
                pos = sum(1 for v, nn in ys if nn >= 10 and v is not None and v > 0); cov = sum(1 for v, nn in ys if nn >= 10)
                if pos < 5 or pos / max(cov, 1) < 0.7: continue
                rb, _ = roi(rows_, side, 'b365'); rm, _ = roi(rows_, side, 'max')
                wr = sum((r['fav_won'] if side == 'fav' else not r['fav_won']) for r in rows_) / len(rows_)
                q = sum((r['mkt'] if side == 'fav' else 1 - r['mkt']) for r in rows_) / len(rows_)
                out.append(dict(angle=' / '.join(f"{d}={v}" for d, v in zip(combo, k)) or 'everything', side=side, n=n, win=round(wr, 3), market=round(q, 3), edge=round(100 * (wr - q), 1), se=round(se(q, n), 1),
                                roi_pin=round(rp, 1), roi_b365=round(rb, 1) if rb is not None else None, roi_best=round(rm, 1) if rm is not None else None, pos_years=f"{pos}/{cov}", dims=len(combo)))
    out.sort(key=lambda x: (-x['roi_pin'] / (1 + x['dims']), ))
    json.dump(dict(years=years, n=len(R), angles=out), open(os.path.join(ROOT, 'data', 'research', 'tennis_scan.json'), 'w'), indent=1)
    print(f"\n{len(out)} angles with ROI > 0 at the Pinnacle close in 70%+ of years (n >= 150). Top by ROI, simplest first:")
    for x in sorted(out, key=lambda x: (x['dims'], -x['roi_pin']))[:60]:
        print(f"  {x['angle']:70} bet {x['side']:3} n={x['n']:5} win {x['win']:.3f} mkt {x['market']:.3f} edge {x['edge']:+5.1f}±{x['se']:.1f} roi pin {x['roi_pin']:+5.1f} b365 {x['roi_b365']} best {x['roi_best']} years {x['pos_years']}")


if __name__ == '__main__':
    main() if '--scan' not in sys.argv else scan()
