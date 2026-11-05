#!/usr/bin/env python3
"""Tennis Abstract, round 3 (Sean, 11/4: "run all of it, and anything else that could find alpha, match or set-1 markets").
Framework as tennis_ta2: favourite rows (calibrated Elo price p_cal, pooled set-1 curve), tour + Challenger best-of-3 unless stated,
residuals in points (actual - price). Each cut is a structural read; the market test for match-level angles runs through
sharp/tennis_edge.py (slam closes) and for set-1 angles through the live paper log.

  1. Slow starters: per player-season set-1 residual vs match residual; does it persist into the next season? (set-1 input if yes)
  2. Qualifier fatigue: matches already played in the event (qualifying + main draw) before this one.
  3. Previous match in the event: games played, went 3 sets, came from a set down, lost a tiebreak -> next match and its set 1.
  4. Set handicaps by serve profile: P(straight sets) by match-probability bin x hold profile (the -1.5 set price).
  5. Retirements: rate by level, surface, age band; and by match probability (does the dog retire more?).
  6. Lefties by surface and by opponent hand.
  7. Tiebreak skill: per player-season tiebreak win rate beyond hold rate; persistence to the next season.
  8. Altitude events (Bogota, Quito, Madrid, Gstaad, Kitzbuhel, Cali, Medellin, Lima*): hold, tiebreak, set-1 residual.
  9. Seeds: seeded favourite vs unseeded favourite; top-8 seed in round 1.
 10. Home players: favourite playing in home country (ioc vs event country, from the event name).
 11. Serve adjustment by surface for the live set-1 model (refit of SERVE_ADJ).
 12. Bagels and breadsticks: P(6-0 or 6-1 set 1) by match probability (set-1 handicap prices).
Writes data/research/tennis_ta3.json. Usage: python3 sharp/tennis_ta3.py"""
import os, sys, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.tennis_ta as T
import sharp.tennis_ta2 as T2
OUT = os.path.join(ROOT, 'data', 'research', 'tennis_ta3.json')
ALT = ('bogota', 'quito', 'madrid', 'gstaad', 'kitzbuhel', 'cali', 'medellin', 'lima', 'mexico city', 'johannesburg', 'pretoria', 'guadalajara', 'san luis potosi', 'cuenca', 'la paz')
# event name -> country code for the home-player cut (tour-level and Challenger names carry the city)
CITY = {'australian open': 'AUS', 'roland garros': 'FRA', 'wimbledon': 'GBR', 'us open': 'USA', 'indian wells': 'USA', 'miami': 'USA', 'monte carlo': 'MON', 'madrid': 'ESP', 'rome': 'ITA',
        'canada': 'CAN', 'toronto': 'CAN', 'montreal': 'CAN', 'cincinnati': 'USA', 'shanghai': 'CHN', 'paris': 'FRA', 'barcelona': 'ESP', 'hamburg': 'GER', 'halle': 'GER', 'queen': 'GBR',
        'washington': 'USA', 'tokyo': 'JPN', 'beijing': 'CHN', 'vienna': 'AUT', 'basel': 'SUI', 'rotterdam': 'NED', 'dubai': 'UAE', 'acapulco': 'MEX', 'rio': 'BRA', 'buenos aires': 'ARG',
        'santiago': 'CHI', 'doha': 'QAT', 'auckland': 'NZL', 'adelaide': 'AUS', 'brisbane': 'AUS', 'sydney': 'AUS', 'hobart': 'AUS', 'delray': 'USA', 'dallas': 'USA', 'houston': 'USA',
        'atlanta': 'USA', 'newport': 'USA', 'los cabos': 'MEX', 'winston': 'USA', 'san diego': 'USA', 'charleston': 'USA', 'stuttgart': 'GER', 'munich': 'GER', 'berlin': 'GER', 'eastbourne': 'GBR',
        'birmingham': 'GBR', 'nottingham': 'GBR', 'bad homburg': 'GER', 'umag': 'CRO', 'bastad': 'SWE', 'stockholm': 'SWE', 'antwerp': 'BEL', 'brussels': 'BEL', 'marseille': 'FRA', 'lyon': 'FRA',
        'metz': 'FRA', 'montpellier': 'FRA', 'strasbourg': 'FRA', 'geneva': 'SUI', 'gstaad': 'SUI', 'kitzbuhel': 'AUT', 'linz': 'AUT', 'estoril': 'POR', 'marrakech': 'MAR', 'cordoba': 'ARG',
        'bogota': 'COL', 'lima': 'PER', 'sao paulo': 'BRA', 'guadalajara': 'MEX', 'monterrey': 'MEX', 'seoul': 'KOR', 'osaka': 'JPN', 'wuhan': 'CHN', 'zhengzhou': 'CHN', 'ningbo': 'CHN',
        'guangzhou': 'CHN', 'hong kong': 'HKG', 'chennai': 'IND', 'pune': 'IND', 'hua hin': 'THA', 'nanchang': 'CHN', 'tianjin': 'CHN', 'jiangxi': 'CHN', 'prague': 'CZE', 'ostrava': 'CZE',
        'budapest': 'HUN', 'bucharest': 'ROU', 'cluj': 'ROU', 'warsaw': 'POL', 'palermo': 'ITA', 'parma': 'ITA', 'florence': 'ITA', 'naples': 'ITA', 'turin': 'ITA', 'sofia': 'BUL',
        'belgrade': 'SRB', 'moscow': 'RUS', 'st. petersburg': 'RUS', 'istanbul': 'TUR', 'antalya': 'TUR', 'tel aviv': 'ISR', 'astana': 'KAZ', 'nur-sultan': 'KAZ', 'tashkent': 'UZB',
        'kuala lumpur': 'MAS', 'singapore': 'SGP', 'bangkok': 'THA', 'cleveland': 'USA', 'austin': 'USA', 'lexington': 'USA', 'indianapolis': 'USA', 'cincinnati': 'USA', 'new haven': 'USA',
        'stanford': 'USA', 'tenerife': 'ESP', 'valencia': 'ESP', 'mallorca': 'ESP', 'granby': 'CAN', 'vancouver': 'CAN', 'quebec': 'CAN', 'luxembourg': 'LUX', 's-hertogenbosch': 'NED',
        'hertogenbosch': 'NED', 'nuremberg': 'GER', 'lausanne': 'SUI', 'lugano': 'SUI', 'biel': 'SUI', 'bol': 'CRO', 'zagreb': 'CRO', 'bratislava': 'SVK', 'ljubljana': 'SLO', 'portoroz': 'SLO',
        'gdynia': 'POL', 'katowice': 'POL', 'lausanne': 'SUI', 'rabat': 'MAR', 'cairo': 'EGY', 'tunis': 'TUN', 'monastir': 'TUN', 'colombo': 'SRI', 'kobe': 'JPN', 'hiroshima': 'JPN',
        'taipei': 'TPE', 'kaohsiung': 'TPE', 'canberra': 'AUS', 'bendigo': 'AUS', 'traralgon': 'AUS', 'burnie': 'AUS', 'launceston': 'AUS', 'perth': 'AUS', 'melbourne': 'AUS', 'noumea': 'FRA'}


def event_country(tname):
    t = (tname or '').lower()
    for k, v in CITY.items():
        if k in t: return v
    return None


def fatigue(M):
    """Per-player event history: matches already played in this event and the previous match's shape (games, sets, tiebreaks, comeback, retirement)."""
    played = collections.defaultdict(int); prev = {}
    for m in M:
        tid = m.get('tid')
        if not tid: continue
        st = T2.sets_of(m.get('score') or '')
        for who in ('w', 'l'):
            m[f'{who}_played'] = played[(tid, m[who])]; m[f'{who}_prev'] = prev.get((tid, m[who]))
        info = dict(games=sum(a + b for a, b in st), sets=len(st), tb=sum(1 for a, b in st if max(a, b) == 7 and min(a, b) == 6), ret='RET' in (m.get('score') or ''))
        for who in ('w', 'l'):
            played[(tid, m[who])] += 1
            lost_tb = any((a < b if who == 'w' else a > b) and max(a, b) == 7 and min(a, b) == 6 for a, b in st)
            came_back = who == 'w' and st and st[0][0] < st[0][1]
            prev[(tid, m[who])] = dict(info, won=(who == 'w'), lost_tb=lost_tb, came_back=came_back)


def main():
    M = T.load(); T.elo_run(M); T.serve_profiles(M); T2.annotate(M)
    fatigue(M)
    rows = T.fav_rows(M)
    cal = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for r in rows: c = cal[T.grp(r)][T.binp(r['p'])]; c[0] += 1; c[1] += r['fav_won']
    for r in rows:
        c = cal[T.grp(r)].get(T.binp(r['p'])); r['p_cal'] = c[1] / c[0] if c and c[0] >= 100 else None
    rows = [r for r in rows if r.get('p_cal') is not None and r.get('tid')]
    bo3 = [r for r in rows if r['bo'] == 3 and T.grp(r) in ('atp_tour', 'atp_chall', 'wta_tour')]
    pooled = T.curve(bo3)
    for r in rows: r['s1c'] = T.interp(pooled, r['p_cal']) if r['bo'] == 3 else None
    R = {}
    fav = lambda r, k: r[('w_' if r['fav_won'] else 'l_') + k]
    dog = lambda r, k: r[('l_' if r['fav_won'] else 'w_') + k]
    favk = lambda r, k: r[k + ('_w' if r['fav_won'] else '_l')]
    dogk = lambda r, k: r[k + ('_l' if r['fav_won'] else '_w')]

    def cut(name, rows_, keyf, min_n=300):
        Tt = collections.defaultdict(lambda: [0, 0, 0.0, 0, 0.0])
        for r in rows_:
            k = keyf(r)
            if k is None or r['s1c'] is None: continue
            t = Tt[k]; t[0] += 1; t[1] += r['fav_won']; t[2] += r['p_cal']; t[3] += r['fav_s1']; t[4] += r['s1c']
        R[name] = {str(k): dict(n=n, fav_won=round(w / n, 3), price=round(p / n, 3), match_resid=round(100 * (w / n - p / n), 1), set1=round(s / n, 3), set1_resid=round(100 * (s / n - sc / n), 1))
                   for k, (n, w, p, s, sc) in sorted(Tt.items(), key=lambda kv: str(kv[0])) if n >= min_n}

    # 1. slow starters: per player-season set-1 residual (as favourite or dog) and persistence
    PS = collections.defaultdict(lambda: [0, 0.0, 0.0])        # (player, year) -> n, sum(set1 won - curve), sum(match won - price)
    for r in bo3:
        y = r['date'] // 10000
        for who, won_s1, won_m, pr, cv in ((r['w'], r['s1_winner_won'], True, r['p_cal'] if r['fav_won'] else 1 - r['p_cal'], r['s1c'] if r['fav_won'] else 1 - r['s1c']),
                                           (r['l'], not r['s1_winner_won'], False, 1 - r['p_cal'] if r['fav_won'] else r['p_cal'], 1 - r['s1c'] if r['fav_won'] else r['s1c'])):
            t = PS[(who, y)]; t[0] += 1; t[1] += won_s1 - cv; t[2] += won_m - pr
    pairs = []
    for (pl, y), (n, s1, mt) in PS.items():
        nxt = PS.get((pl, y + 1))
        if n >= 25 and nxt and nxt[0] >= 25: pairs.append((s1 / n - mt / n, nxt[1] / nxt[0] - nxt[2] / nxt[0], s1 / n, nxt[1] / nxt[0]))
    def corr(xs, ys):
        n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
        sx = math.sqrt(sum((x - mx) ** 2 for x in xs) / n); sy = math.sqrt(sum((y - my) ** 2 for y in ys) / n)
        return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n / (sx * sy) if sx and sy else None
    q = sorted(pairs); k = len(q) // 5
    R['1 slow starters: set-1 residual beyond match residual, persistence to next season (player-seasons with 25+ matches both years)'] = dict(
        n_pairs=len(pairs), corr_set1_beyond_match=round(corr([a for a, b, c, d in pairs], [b for a, b, c, d in pairs]), 3), corr_raw_set1_resid=round(corr([c for a, b, c, d in pairs], [d for a, b, c, d in pairs]), 3),
        quintiles={f"q{i + 1} (this season {100 * sum(x[0] for x in q[i * k:(i + 1) * k]) / k:+.1f})": round(100 * sum(x[1] for x in q[i * k:(i + 1) * k]) / k, 2) for i in range(5)} if k else {})
    # 2. qualifier fatigue: matches already played in this event
    cut('2 matches already played in the event (favourite)', bo3, lambda r: f"fav played {min(fav(r, 'played'), 4)}{'+' if fav(r, 'played') >= 4 else ''}, dog played {min(dog(r, 'played'), 4)}{'+' if dog(r, 'played') >= 4 else ''}", 400)
    cut('2b favourite has played 3+ more matches than the dog in this event (qualifier)', bo3, lambda r: 'fav 3+ more' if fav(r, 'played') - dog(r, 'played') >= 3 else 'dog 3+ more' if dog(r, 'played') - fav(r, 'played') >= 3 else None, 200)
    # 3. previous match in the event
    pv = lambda r, side: (fav if side == 'fav' else dog)(r, 'prev')
    cut('3 previous match games (favourite), both have a previous match', [r for r in bo3 if fav(r, 'prev') and dog(r, 'prev')],
        lambda r: f"fav prev {'3 sets' if pv(r, 'fav')['sets'] >= 3 else '2 sets'} / dog prev {'3 sets' if pv(r, 'dog')['sets'] >= 3 else '2 sets'}")
    cut('3b previous match long (28+ games) vs short (under 20)', [r for r in bo3 if fav(r, 'prev') and dog(r, 'prev')],
        lambda r: ('fav long, dog short' if pv(r, 'fav')['games'] >= 28 and pv(r, 'dog')['games'] < 20 else 'dog long, fav short' if pv(r, 'dog')['games'] >= 28 and pv(r, 'fav')['games'] < 20 else None), 200)
    cut('3c came from a set down in the previous match', [r for r in bo3 if fav(r, 'prev') and dog(r, 'prev')],
        lambda r: ('fav came back' if pv(r, 'fav')['came_back'] and not pv(r, 'dog')['came_back'] else 'dog came back' if pv(r, 'dog')['came_back'] and not pv(r, 'fav')['came_back'] else 'neither' if not pv(r, 'fav')['came_back'] else None))
    cut('3d previous opponent retired (walk-through)', [r for r in bo3 if fav(r, 'prev') and dog(r, 'prev')],
        lambda r: ('fav had a retirement' if pv(r, 'fav')['ret'] and not pv(r, 'dog')['ret'] else 'dog had a retirement' if pv(r, 'dog')['ret'] and not pv(r, 'fav')['ret'] else None), 150)
    # 4. set handicaps by serve profile
    S = collections.defaultdict(lambda: [0, 0, 0])
    for r in bo3:
        st = T2.sets_of(r.get('score') or '')
        if len(st) < 2 or favk(r, 'hold') is None or dogk(r, 'hold') is None: continue
        prof = 'dog bigger server' if dogk(r, 'hold') - favk(r, 'hold') >= .03 else 'fav bigger server' if favk(r, 'hold') - dogk(r, 'hold') >= .03 else 'similar'
        t = S[(f"p {T.binp(r['p_cal']):.2f}", prof)]; t[0] += 1; t[1] += r['fav_won'] and len(st) == 2; t[2] += r['fav_won']
    R['4 straight sets by match probability x serve profile (the -1.5 set price)'] = {f"{k[0]} {k[1]}": dict(n=n, straight_sets=round(ss / n, 3), fav_won=round(w / n, 3)) for k, (n, ss, w) in sorted(S.items()) if n >= 400}
    # 5. retirements
    RT = collections.defaultdict(lambda: [0, 0, 0])      # n, retirements, dog retired
    for r in rows:
        sc = r.get('score') or ''
        ret = 'RET' in sc
        age_f = fav(r, 'age'); k1 = (T.grp(r), r['surface'])
        t = RT[k1]; t[0] += 1; t[1] += ret; t[2] += ret and not r['fav_won'] is False and not r['fav_won']   # the retiring player is the loser; dog retired when fav won
        if age_f:
            t = RT[('fav age', '33+' if age_f >= 33 else 'under 21' if age_f < 21 else '21-32')]; t[0] += 1; t[1] += ret
        t = RT[('match price', f"{T.binp(r['p_cal']):.2f}")]; t[0] += 1; t[1] += ret; t[2] += ret and r['fav_won']
    R['5 retirements (share of matches with a completed set 1)'] = {f"{k[0]} / {k[1]}": dict(n=n, ret=round(rt / n, 4), dog_retired_share=round(dr / rt, 3) if rt and k[0] == 'match price' else None) for k, (n, rt, dr) in sorted(RT.items()) if n >= 1000 and k[1] not in ('Unknown', 'Carpet')}
    # 6. lefties by surface
    hand_k = lambda r: 'fav lefty' if fav(r, 'hand') == 'L' and dog(r, 'hand') == 'R' else 'dog lefty' if dog(r, 'hand') == 'L' and fav(r, 'hand') == 'R' else 'both lefty' if fav(r, 'hand') == 'L' and dog(r, 'hand') == 'L' else None
    cut('6 lefty vs righty by surface', bo3, lambda r: f"{r['surface']}: {hand_k(r)}" if hand_k(r) else None, 200)
    # 7. tiebreak skill persistence
    TB = collections.defaultdict(lambda: [0, 0])
    for m in M:
        y = m['date'] // 10000
        for a, b in T2.sets_of(m.get('score') or ''):
            if max(a, b) == 7 and min(a, b) == 6:
                TB[(m['w'], y)][0] += 1; TB[(m['w'], y)][1] += a > b
                TB[(m['l'], y)][0] += 1; TB[(m['l'], y)][1] += b > a
    tp = [(w / n, TB[(pl, y + 1)][1] / TB[(pl, y + 1)][0]) for (pl, y), (n, w) in TB.items() if n >= 12 and TB.get((pl, y + 1), [0, 0])[0] >= 12]
    q = sorted(tp); k = len(q) // 4
    R['7 tiebreak win rate persistence (player-seasons with 12+ tiebreaks both years)'] = dict(n_pairs=len(tp), corr=round(corr([a for a, b in tp], [b for a, b in tp]), 3),
        quartiles={f"q{i + 1} (this season {100 * sum(x[0] for x in q[i * k:(i + 1) * k]) / k:.1f}%)": round(100 * sum(x[1] for x in q[i * k:(i + 1) * k]) / k, 1) for i in range(4)} if k else {})
    # 8. altitude
    alt = lambda r: any(a in (r.get('tname') or '').lower() for a in ALT)
    A = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])
    for r in bo3:
        k = ('altitude' if alt(r) else 'sea level', r['tour'], r['surface'])
        t = A[k]; t[0] += 1; t[1] += r['s1_tb']; t[2] += r['s1_games']
        hf, ho = favk(r, 'hold'), dogk(r, 'hold')
        if hf is not None and ho is not None: t[3] += (hf + ho) / 2
    R['8 altitude events: set-1 tiebreak and games'] = {' / '.join(k): dict(n=n, set1_tiebreak=round(tb / n, 3), set1_games=round(g / n, 2)) for k, (n, tb, g, h) in sorted(A.items()) if n >= 300}
    cut('8b altitude: favourite residuals', bo3, lambda r: f"{'altitude' if alt(r) else 'sea level'} {r['surface']}", 300)
    cut('8c altitude: big server dog at altitude', [r for r in bo3 if favk(r, 'hold') is not None and dogk(r, 'hold') is not None],
        lambda r: f"{'altitude' if alt(r) else 'sea level'}: " + ('dog bigger server' if dogk(r, 'hold') - favk(r, 'hold') >= .03 else 'fav bigger server' if favk(r, 'hold') - dogk(r, 'hold') >= .03 else 'similar'), 150)
    # 9. seeds
    seed = lambda x: int(x) if x and str(x).isdigit() else None
    cut('9 seeds', bo3, lambda r: ('fav seeded, dog not' if seed(fav(r, 'seed')) and not seed(dog(r, 'seed')) else 'dog seeded, fav not' if seed(dog(r, 'seed')) and not seed(fav(r, 'seed')) else 'both seeded' if seed(fav(r, 'seed')) else 'neither seeded'))
    cut('9b top-4 seed in its first match', bo3, lambda r: 'fav is a top-4 seed, first match' if (seed(fav(r, 'seed')) or 99) <= 4 and fav(r, 'first') else None, 300)
    # 10. home players
    def home(r, who):
        c = event_country(r.get('tname'))
        return c is not None and (fav if who == 'fav' else dog)(r, 'ioc') == c
    cut('10 home player (event country from the event name)', bo3, lambda r: ('fav at home, dog not' if home(r, 'fav') and not home(r, 'dog') else 'dog at home, fav not' if home(r, 'dog') and not home(r, 'fav') else 'both at home' if home(r, 'fav') else 'neither') if event_country(r.get('tname')) else None)
    cut('10b home player by tour', bo3, lambda r: f"{r['tour']}: " + ('fav at home' if home(r, 'fav') and not home(r, 'dog') else 'dog at home' if home(r, 'dog') and not home(r, 'fav') else 'neither') if event_country(r.get('tname')) and not (home(r, 'fav') and home(r, 'dog')) else None)
    # 11. serve adjustment by surface (refit for the live model, same definition as tennis_ta.mapping)
    cut('11 serve profile by surface (SERVE_ADJ refit; set1_resid is the adjustment)', [r for r in bo3 if favk(r, 'hold') is not None and dogk(r, 'hold') is not None],
        lambda r: f"{r['surface']}: " + ('dog' if dogk(r, 'hold') - favk(r, 'hold') >= .03 else 'fav' if favk(r, 'hold') - dogk(r, 'hold') >= .03 else 'similar'), 500)
    # 12. bagels and breadsticks in set 1
    B = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in bo3:
        st = T2.sets_of(r.get('score') or '')
        if not st: continue
        a, b = st[0] if r['fav_won'] else (st[0][1], st[0][0])
        t = B[(r['tour'], f"p {T.binp(r['p_cal']):.2f}")]; t[0] += 1; t[1] += (a == 6 and b <= 1); t[2] += (a == 6 and b <= 2); t[3] += (b == 6 and a <= 2)
    R['12 set 1 by 6-0/6-1 (fav), 6-0 to 6-2 (fav), 6-0 to 6-2 (dog), by tour and match probability'] = {f"{k[0]} {k[1]}": dict(n=n, fav_60_61=round(x / n, 3), fav_by_4plus=round(y / n, 3), dog_by_4plus=round(z / n, 3)) for k, (n, x, y, z) in sorted(B.items()) if n >= 1000}
    json.dump(R, open(OUT, 'w'), indent=1)
    for k, v in R.items():
        print(f"\n== {k}")
        if isinstance(v, dict) and v and isinstance(next(iter(v.values())), dict):
            for kk, vv in v.items(): print(f"  {kk:58} {vv}")
        else: print(' ', json.dumps(v))


if __name__ == '__main__':
    main()
