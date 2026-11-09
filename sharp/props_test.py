#!/usr/bin/env python3
"""Player props, first pass (Sean 11/5-6: "props too"). One pregame snapshot per game (10 minutes before the start, every book) from
data/oddsapi/derivs/<sport>_props.jsonl.gz, graded on ESPN box scores (data/boxscores/<sport>.jsonl.gz).
  A. Over / under at Pinnacle's own price, per market (is there a standing under or over lean?).
  B. Soft books vs Pinnacle at the same line: a book price 2%+ better than Pinnacle's no-vig fair.
  C. Line gaps: a book's line differs from Pinnacle's on the same player and market; bet the side the gap favours at that book.
  D. Off the main line: Pinnacle's no-vig on a line vs the book's alternate price.
Players who did not play (no box line) are void. Writes data/research/props_<sport>.json. Usage: python3 sharp/props_test.py nba [path]"""
import os, sys, json, re, sqlite3, collections, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
NICE = dict(pinnacle='Pinnacle', draftkings='DK', fanduel='FD', williamhill_us='Caesars', betrivers='BetRivers', betonlineag='BetOnline', lowvig='LowVig', circasports='Circa', bovada='Bovada', betmgm='BetMGM')


def num(v):
    try: return float(str(v).split('-')[0].split('/')[0])
    except Exception: return None


def stat(sp, mk, p):
    """the box-score value a prop market settles on, or None"""
    g = lambda *ks: next((num(p[k]) for k in ks if k in p and num(p[k]) is not None), None)
    if sp in ('nba', 'wnba'):
        pts, reb, ast = g('points'), g('rebounds'), g('assists')
        three = num(str(p.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted', '')).split('-')[0]) if 'threePointFieldGoalsMade-threePointFieldGoalsAttempted' in p else None
        M = {'player_points': pts, 'player_rebounds': reb, 'player_assists': ast, 'player_threes': three, 'player_blocks': g('blocks'), 'player_steals': g('steals')}
        if mk in M: return M[mk]
        if None in (pts, reb, ast): return None
        return {'player_points_rebounds_assists': pts + reb + ast, 'player_points_rebounds': pts + reb, 'player_points_assists': pts + ast, 'player_rebounds_assists': reb + ast}.get(mk)
    if sp == 'nhl':
        M = {'player_points': None, 'player_shots_on_goal': g('forwards.shotsTotal', 'defenses.shotsTotal'), 'player_assists': g('forwards.assists', 'defenses.assists'),
             'player_blocked_shots': g('forwards.blockedShots', 'defenses.blockedShots'), 'player_total_saves': g('goalies.saves')}
        if mk == 'player_points':
            gl, a = g('forwards.goals', 'defenses.goals'), g('forwards.assists', 'defenses.assists')
            return None if gl is None or a is None else gl + a
        return M.get(mk)
    if sp == 'mlb':      # ESPN MLB box: batters carry atBats, pitchers carry innings ('fullInnings.partInnings'); no doubles/triples, so no total bases
        pit = 'fullInnings.partInnings' in p; bat = 'atBats' in p
        if mk.startswith('pitcher_'):
            if not pit: return None
            if mk == 'pitcher_outs':
                w, _, f = str(p['fullInnings.partInnings']).partition('.'); return 3 * int(w or 0) + int(f or 0)
            return {'pitcher_strikeouts': g('strikeouts'), 'pitcher_hits_allowed': g('hits'), 'pitcher_walks': g('walks'), 'pitcher_earned_runs': g('earnedRuns')}.get(mk)
        if not bat or pit: return None
        h, r_, rbi = g('hits'), g('runs'), g('RBIs')
        if mk == 'batter_hits_runs_rbis': return None if None in (h, r_, rbi) else h + r_ + rbi
        return {'batter_hits': h, 'batter_home_runs': g('homeRuns'), 'batter_rbis': rbi, 'batter_runs_scored': r_, 'batter_walks': g('walks')}.get(mk)
    if sp == 'soccer':
        if not p.get('appearances'): return None          # did not play: void
        return {'player_goal_scorer_anytime': g('totalGoals'), 'player_shots_on_target': g('shotsOnTarget'), 'player_shots': g('totalShots'), 'player_assists': g('goalAssists')}.get(mk)
    if sp == 'nfl':
        cmp_ = str(p.get('passing.completions/passingAttempts', '')).split('/')
        M = {'player_pass_yds': g('passing.passingYards'), 'player_pass_tds': g('passing.passingTouchdowns'), 'player_pass_interceptions': g('passing.interceptions'),
             'player_pass_completions': num(cmp_[0]) if len(cmp_) == 2 else None, 'player_pass_attempts': num(cmp_[1]) if len(cmp_) == 2 else None,
             'player_rush_yds': g('rushing.rushingYards'), 'player_rush_attempts': g('rushing.rushingAttempts'), 'player_receptions': g('receiving.receptions'),
             'player_reception_yds': g('receiving.receivingYards')}
        if mk in M: return M[mk]
        if mk == 'player_anytime_td':      # 11/8: rushing + receiving touchdowns (passing TDs do not count)
            rt, ct = g('rushing.rushingTouchdowns'), g('receiving.receivingTouchdowns')
            return None if rt is None and ct is None else (rt or 0) + (ct or 0)
        ry, rcy = g('rushing.rushingYards'), g('receiving.receivingYards')
        if mk == 'player_rush_reception_yds': return (ry or 0) + (rcy or 0) if (ry is not None or rcy is not None) else None
        if mk == 'player_pass_rush_yds':
            py = g('passing.passingYards'); return None if py is None else py + (ry or 0)
    return None


def nm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return re.sub(r'[^a-z]', '', s)


def toks(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return [t for t in re.findall(r'[a-z]+', s) if t not in ('jr', 'sr', 'ii', 'iii', 'iv', 'de', 'da', 'van', 'der', 'dos', 'del')]


def fuzzy(box, name):
    """Vendor names carry full legal names ('Martin Zubimendi Ibanez'); ESPN uses the common one. Match when every ESPN token is in the
    vendor name, or surname + first initial match; only when exactly one player fits."""
    if not name: return None
    vt = toks(name)
    if not vt: return None
    c = [v for v in box.values() if toks(v.get('_name')) and set(toks(v['_name'])) <= set(vt)]
    if len(c) == 1: return c[0]
    c = [v for v in box.values() if toks(v.get('_name')) and toks(v['_name'])[-1] in vt and toks(v['_name'])[0][0] == vt[0][0]]
    return c[0] if len(c) == 1 else None


def main():
    sp = sys.argv[1]; path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'data', 'oddsapi', 'derivs', f'{sp}_props.jsonl.gz')
    dbp = os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'); ESPN = {}
    if os.path.exists(dbp):
        conn = sqlite3.connect(dbp); ESPN = {r[0]: str(r[1]) for r in conn.execute("SELECT game_id, espn_id FROM results WHERE espn_id IS NOT NULL")}
    BOX = {}; BYDAY = collections.defaultdict(list)      # 11/8: without odds.sqlite, match the box score by start time (within 1h) and 3+ player names
    import datetime as _dt
    _ts = lambda t: _dt.datetime.fromisoformat(t.replace('Z', '+00:00') if len(t) > 17 else t.replace('Z', ':00+00:00'))
    for l in lines(os.path.join(ROOT, 'data', 'boxscores', f'{sp}.jsonl.gz')):
        try: d = json.loads(l)
        except Exception: continue
        BOX[str(d['event_id'])] = {nm(k): dict(v, _name=k) for k, v in d['players'].items()}
        BYDAY[d['start'][:10]].append((BOX[str(d['event_id'])], _ts(d['start'])))
    def find_box(d):
        st = _ts(d['start']); best = None
        names = {nm(o.get('description')) for b in d.get('bookmakers') or [] for m in b['markets'] for o in m['outcomes'] if o.get('description')}
        for day in {st.date().isoformat(), (st - _dt.timedelta(days=1)).date().isoformat(), (st + _dt.timedelta(days=1)).date().isoformat()}:
            for box, bst in BYDAY.get(day, []):
                if abs((bst - st).total_seconds()) > 3600: continue
                hit = sum(1 for n in names if n in box)
                if hit >= 3 and (best is None or hit > best[0]): best = (hit, box)
        return best[1] if best else None
    H = collections.defaultdict(list); nb = collections.Counter()
    for l in lines(path):
        try: d = json.loads(l)
        except Exception: continue
        box = BOX.get(ESPN.get(d['game_id'], '')) or find_box(d)
        if not box or not d.get('bookmakers'): nb['no box'] += 1; continue
        season = d['start'][:4]
        Q = collections.defaultdict(dict); desc = {}          # (market, player) -> book -> {(side, line): price}
        for b in d['bookmakers']:
            for m in b['markets']:
                for o in m['outcomes']:
                    if m['key'] == 'player_goal_scorer_anytime' and o['name'] in ('Yes', 'No'):       # anytime scorer = over / under 0.5 goals
                        o = dict(o, name='Over' if o['name'] == 'Yes' else 'Under', point=0.5)
                    if o.get('point') is None or o['name'] not in ('Over', 'Under'): continue
                    desc[(m['key'], nm(o.get('description')))] = o.get('description')
                    Q[(m['key'], nm(o.get('description')))][b['key']] = Q[(m['key'], nm(o.get('description')))].get(b['key'], {})
                    Q[(m['key'], nm(o.get('description')))][b['key']][(o['name'].lower(), o['point'])] = o['price']
        for (mk, pl), books in Q.items():
            p = box.get(pl)
            if p is None: p = fuzzy(box, desc.get((mk, pl)))
            if p is None: nb['player not in box'] += 1; continue
            v = stat(sp, mk, p)
            if v is None: nb['no stat ' + mk] += 1; continue
            res = lambda side, ln: 0.5 if v == ln else 1 if (v > ln) == (side == 'over') else 0
            P = books.get('pinnacle')
            if not P: continue
            pin_lines = sorted({ln for (s, ln) in P if ('over', ln) in P and ('under', ln) in P})
            for ln in pin_lines:
                po, pu = P[('over', ln)], P[('under', ln)]; fo = (1 / po) / (1 / po + 1 / pu)
                for side, pr in (('over', po), ('under', pu)):
                    H[f'A {mk} | Pinnacle {side}'].append((res(side, ln), pr, 'Pinnacle', season))
                    H[f'A all markets | Pinnacle {side}'].append((res(side, ln), pr, 'Pinnacle', season))
                for bk, B in books.items():
                    if bk in ('pinnacle', 'betmgm'): continue
                    for side, f in (('over', fo), ('under', 1 - fo)):
                        pr = B.get((side, ln))
                        if pr and f * pr - 1 >= 0.02:
                            for k_ in (f'B {mk} | price gap', 'B all markets | price gap', f'B {mk} | price gap {side}', f'B all markets | price gap {side}', f"B {mk} | price gap EV {'2-4%' if f * pr < 1.04 else '4%+'}"): H[k_].append((res(side, ln), pr, NICE.get(bk, bk), season))
            if len(pin_lines) == 1:
                ln0 = pin_lines[0]
                for bk, B in books.items():
                    if bk in ('pinnacle', 'betmgm'): continue
                    bl = sorted({ln for (s, ln) in B if ('over', ln) in B and ('under', ln) in B})
                    if len(bl) != 1 or bl[0] == ln0: continue
                    side = 'over' if bl[0] < ln0 else 'under'; gap = abs(bl[0] - ln0)
                    k = 'C line gap ' + ('0.5-1' if gap <= 1 else '1.5-4' if gap <= 4 else '4.5+')
                    H[f'{k} | {mk}'].append((res(side, bl[0]), B[(side, bl[0])], NICE.get(bk, bk), season)); H[f'{k} | all markets'].append((res(side, bl[0]), B[(side, bl[0])], NICE.get(bk, bk), season))
    R = {}
    for k in sorted(H):
        L = H[k]; w = sum(1 for x in L if x[0] == 1); l = sum(1 for x in L if x[0] == 0)
        pl = sum((x[1] - 1) if x[0] == 1 else -1 if x[0] == 0 else 0 for x in L)
        bys = collections.defaultdict(lambda: [0, 0, 0.0]); byb = collections.defaultdict(lambda: [0, 0, 0.0])
        for r_, pr, bk, se in L:
            for D_, key in ((bys, se), (byb, bk)):
                x = D_[key]; x[0] += r_ == 1; x[1] += r_ == 0; x[2] += (pr - 1) if r_ == 1 else -1 if r_ == 0 else 0
        R[k] = dict(w=w, l=l, roi=round(100 * pl / max(1, w + l), 1), seasons={s: f'{a}-{b} {100 * u / max(1, a + b):+.1f}%' for s, (a, b, u) in sorted(bys.items())},
                    books={s: f'{a}-{b} {100 * u / max(1, a + b):+.1f}%' for s, (a, b, u) in sorted(byb.items(), key=lambda x: -(x[1][0] + x[1][1]))[:6]})
        if w + l >= 100: print(f"{k:52s} {w}-{l}  {R[k]['roi']:+.1f}%   {' '.join(f'{s}:{v.split()[-1]}' for s, v in R[k]['seasons'].items())}")
    print(dict(nb.most_common(8)))
    json.dump(R, open(os.path.join(ROOT, 'data', 'research', f'props_{sp}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
