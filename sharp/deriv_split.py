#!/usr/bin/env python3
"""Full-game systems split into derivatives (Sean, 11/6: "any way we can split a full game system into a derivative, I'd be interested
in seeing whether it's profitable").
For every replayable full-game rule, the games it fires on (same filters as sharp/rule_replay.py, from the odds database) are graded on
the same side of each derivative Pinnacle priced about 10 minutes before the start (data/oddsapi/derivs/<sport>_full.jsonl.gz, mid-2023 on):
first half, first quarter, second half where priced, team totals; and for side rules, the game total too. Each is set against the same
market on every game in the window (the baseline: what blind betting that side costs, about -2 to -4% at Pinnacle).
Graded on ESPN period scores (data/state/linescores.json), flat 1 unit at Pinnacle's price, by season.
Writes data/research/deriv_split.json. Usage: python3 sharp/deriv_split.py [nba cfb ...]"""
import os, sys, json, sqlite3, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.rule_replay as RR
from sharp.gzlines import lines
from sharp.deriv_curve import PER, season
ET = RR.ET


def days_off(g, side): return (g['start'].astimezone(ET).date() - g[f'{side}_last'].astimezone(ET).date()).days if g.get(f'{side}_last') else None


# rule -> (sport, predicate on a profiled odds-database game, full-game market, side ('under'/'over'/'home'/'away'/'dog'/'fav'))
def _nba_under_good_home_over(g):
    ho, ao = days_off(g, 'home'), days_off(g, 'away')
    return g['home_over_n'] >= 1 and int(100 * (g['home_over_pct'] or 0)) >= 58 and ho is not None and ao is not None and 1 <= ho <= 2 and 1 <= ao <= 3 and g['tot_open'] is not None and g['tot_close'] is not None and g['tot_open'] - g['tot_close'] >= 0.5
def _nba_1h_hot_over(g): return g['away_over_n'] >= 1 and int(100 * (g['away_over_pct'] or 0)) >= 71
def _cfb_road_dog_low_total(g): return g.get('conf') and g['sp_close'] is not None and g['tot_close'] is not None and g['sp_close'] <= -7 and g['tot_close'] <= 48
def _cfb_homefav_7510_under(g): return g['sp_close'] is not None and -10 <= g['sp_close'] <= -7.5 and not g.get('neutral')
def _cfb_road_streak_dog(g): return g['sp_close'] is not None and g['tot_close'] is not None and g['sp_close'] < 0 and g['tot_close'] <= 54 and 2 <= (g.get('away_road_streak') or 0) + 1 <= 5
def _nhl_early_home_fav(g):
    return g['p_close'] is not None and g['p_close'] >= .5 and g['home_games'] + 1 <= 24 and (g.get('away_win_pct') or 0) >= 51
RULES = {
    'nba_under_good_home_over': ('nba', _nba_under_good_home_over, 'total', 'under'),
    'nba_1h_under_hot_over (full-game filter)': ('nba', _nba_1h_hot_over, 'total', 'under'),
    'cfb_road_dog_low_total': ('cfb', _cfb_road_dog_low_total, 'spread', 'away'),
    'cfb_homefav_7510_under': ('cfb', _cfb_homefav_7510_under, 'total', 'under'),
    'cfb_road_streak_dog': ('cfb', _cfb_road_streak_dog, 'spread', 'away'),
    'nhl_early_home_fav_qual': ('nhl', _nhl_early_home_fav, 'ml', 'home'),
}


def main():
    sports = sys.argv[1:] or sorted({v[0] for v in RULES.values()})
    out = {}
    LSall = json.load(open(os.path.join(ROOT, 'data', 'state', 'linescores.json')))
    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    ESPN = {r[0]: r[1] for r in conn.execute("SELECT game_id, espn_id FROM results")}
    for sp in sports:
        LS = LSall.get(sp, {})
        G = RR.load(sp); RR.profiles(G); GI = {g['id']: g for g in G}
        # derivative prices at Pinnacle (last snapshot of the 10-minute pull)
        D = {}
        for l in lines(os.path.join(ROOT, 'data', 'oddsapi', 'derivs', f'{sp}_full.jsonl.gz')):
            try: d = json.loads(l)
            except Exception: continue
            P = next((b for b in d.get('bookmakers') or [] if b['key'] == 'pinnacle'), None)
            if P: D[d['game_id']] = (d, P)
        print(f'{sp}: {len(G)} games, {len(D)} with Pinnacle derivatives', flush=True)

        def period(g, per):
            ls = LS.get(str(ESPN.get(g['id'])))
            if not ls or per not in PER[sp]: return None
            i0, n = PER[sp][per]
            if len(ls['h']) < i0 + n or len(ls['a']) < i0 + n: return None
            return sum(ls['h'][i0:i0 + n]), sum(ls['a'][i0:i0 + n])

        def bets(g, kind, side):
            """every derivative bet on this side of this game: [(label, won 1/0/.5, decimal)]"""
            if g['id'] not in D or g['hs'] is None: return []
            d, P = D[g['id']]; R = []
            for m in P['markets']:
                k = m['key']; O = m['outcomes']
                for per in PER[sp]:
                    if k == f'totals_{per}' and kind == 'total':
                        sc = period(g, per)
                        if not sc: continue
                        for o in O:
                            if o['name'].lower() != side: continue
                            t = sc[0] + sc[1]; won = .5 if t == o['point'] else int((t < o['point']) == (side == 'under'))
                            R.append((f'{per} {side}', won, o['price']))
                    if k == f'spreads_{per}' and kind in ('spread', 'ml'):
                        sc = period(g, per)
                        if not sc: continue
                        team = d['home'] if side == 'home' else d['away']
                        for o in O:
                            if o['name'] != team: continue
                            mg = (sc[0] - sc[1]) if side == 'home' else (sc[1] - sc[0]); v = mg + o['point']
                            R.append((f'{per} {side} spread', .5 if v == 0 else int(v > 0), o['price']))
                    if k == f'totals_{per}' and kind in ('spread', 'ml'):       # side rules: the period total too, both ways
                        sc = period(g, per)
                        if not sc: continue
                        for o in O:
                            t = sc[0] + sc[1]; u = o['name'].lower()
                            R.append((f'{per} {u}', .5 if t == o['point'] else int((t < o['point']) == (u == 'under')), o['price']))
                if k == 'team_totals' and kind == 'total':
                    for o in O:
                        if o['name'].lower() != side: continue
                        who = 'home' if o.get('description') == d['home'] else 'away' if o.get('description') == d['away'] else None
                        if not who: continue
                        pts = g['hs'] if who == 'home' else g['as_']
                        R.append((f'{who} team total {side}', .5 if pts == o['point'] else int((pts < o['point']) == (side == 'under')), o['price']))
            return R

        for rule, (rsp, pred, kind, side) in RULES.items():
            if rsp != sp: continue
            fired = [g for g in G if g['hs'] is not None and g.get('close_h') is not None and g['close_h'] <= 6 and pred(g)]
            fired_d = [g for g in fired if g['id'] in D]
            H = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0.0]))
            B = collections.defaultdict(lambda: [0, 0, 0.0])
            for g in fired_d:
                for lab, won, dec in bets(g, kind, side):
                    for s in (season(sp, g['start'].isoformat()), 'all'):
                        x = H[lab][s]; x[0] += won == 1; x[1] += won == 0; x[2] += (dec - 1) if won == 1 else -1 if won == 0 else 0
            # the full-game bet itself on the same games (the system as it is, same window)
            for g in fired_d:
                gr = RR.grade(g, kind, side)
                if not gr: continue
                won, dec = gr[0], gr[1]
                for s in (season(sp, g['start'].isoformat()), 'all'):
                    x = H['full game (the rule)'][s]; x[0] += won == 1; x[1] += won == 0; x[2] += (dec - 1) if won == 1 else -1 if won == 0 else 0
            # baseline: the same derivative side on every game with derivatives
            for g in G:
                if g['id'] not in D or g['hs'] is None: continue
                for lab, won, dec in bets(g, kind, side):
                    x = B[lab]; x[0] += won == 1; x[1] += won == 0; x[2] += (dec - 1) if won == 1 else -1 if won == 0 else 0
            res = {}
            print(f'\n{rule}: fires on {len(fired)} games, {len(fired_d)} with derivative prices (mid-2023 on)')
            for lab in sorted(H, key=lambda z: (z != 'full game (the rule)', z)):
                a = H[lab]['all']; n = a[0] + a[1]
                if n < 15: continue
                by = {s: dict(w=v[0], l=v[1], roi=round(100 * v[2] / max(1, v[0] + v[1]), 1)) for s, v in sorted(H[lab].items()) if s != 'all'}
                b = B.get(lab)
                res[lab] = dict(w=a[0], l=a[1], roi=round(100 * a[2] / n, 1), seasons=by, baseline=dict(n=b[0] + b[1], roi=round(100 * b[2] / max(1, b[0] + b[1]), 1)) if b else None)
                pos = sum(1 for v in by.values() if v['roi'] > 0 and v['w'] + v['l'] >= 5)
                print(f"  {lab:32s} {a[0]}-{a[1]} {100 * a[2] / n:+6.1f}%  seasons +: {pos}/{len(by)}  ({', '.join(f'{s} {v['roi']:+.0f}% n{v['w'] + v['l']}' for s, v in by.items())})"
                      + (f"   | every game: {res[lab]['baseline']['roi']:+.1f}% n{res[lab]['baseline']['n']}" if b else ''))
            out[rule] = dict(sport=sp, fired=len(fired), with_derivs=len(fired_d), splits=res)
    p = os.path.join(ROOT, 'data', 'research', 'deriv_split.json')
    old = json.load(open(p)) if os.path.exists(p) else {}
    old.update(out); json.dump(old, open(p, 'w'), indent=1)


if __name__ == '__main__':
    main()
