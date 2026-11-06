#!/usr/bin/env python3
"""MLB first five vs full game with Bartolo's pregame inputs (Sean 11/6). Bartolo's archive (szerillo/mlb-tracker data/archive/<date>/
pregame_inputs.json, read only) gives each side's starter runs allowed (spRA), bullpen runs allowed (bpRA) and expected starter innings
(shrunkIpgs). From those, each team's expected share of its runs in the first five innings:
    share = (min(ip, 5) * spRA_opp + max(0, 5 - ip) * bpRA_opp) / (ip * spRA_opp + (9 - ip) * bpRA_opp)     (ip = the opposing starter's)
and the game's first-five share = runs-weighted average of both teams' shares. The market's own first-five share is Pinnacle's F5 total /
full total at the same snapshot. Tests: (1) logistic on the F5 over/under result with Pinnacle's no-vig and the share difference; (2)
bets when Bartolo's share differs from the market's by 2+ / 3+ points, at Pinnacle's price and at the best of FD/Caesars/DK.
Usage: python3 sharp/mlb_f5_bartolo.py <dir with pi_YYYY-MM-DD.json> <mlb derivatives file>"""
import os, sys, json, glob, math, sqlite3, collections, datetime as dt
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
from zoneinfo import ZoneInfo
ET = ZoneInfo('America/New_York'); US = ('fanduel', 'williamhill_us', 'draftkings')


def share(ip, sp, bp):
    ip = max(1.0, min(8.0, ip)); full = ip * sp + (9 - ip) * bp
    return (min(ip, 5) * sp + max(0, 5 - ip) * bp) / full if full > 0 else None


def main():
    BI = {}
    for f in glob.glob(os.path.join(sys.argv[1], 'pi_*.json')):
        try: d = json.load(open(f))
        except Exception: continue
        for g in (d.get('games') or {}).values():
            try:
                c = g['model']['components']; a, h = c['away']['staff'], c['home']['staff']
                # home runs come off the AWAY staff; away runs off the HOME staff
                sh_home = share(a['shrunkIpgs'], a['spRA'], a['bpRA']); sh_away = share(h['shrunkIpgs'], h['spRA'], h['bpRA'])
                rh, ra = g['model']['home_runs'], g['model']['away_runs']
                BI[(g['game_date'], g['home'], g['away'])] = dict(share=(rh * sh_home + ra * sh_away) / (rh + ra), total=g['model']['total'])
            except Exception: continue
    print('Bartolo games with inputs:', len(BI))
    c = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    RES = {r[0]: r[1:] for r in c.execute("SELECT game_id, espn_id, home_score, away_score FROM results")}
    FULL = {r[0]: r[1:] for r in c.execute("SELECT game_id, pin_close_tot FROM games WHERE sport='mlb'")}
    LS = json.load(open(os.path.join(ROOT, 'data', 'state', 'linescores.json'))).get('mlb', {})
    X, Y, rows = [], [], []
    for l in lines(sys.argv[2]):
        try: d = json.loads(l)
        except Exception: continue
        if d['start'] < '2026' or d['game_id'] not in RES: continue
        day = dt.datetime.fromisoformat(d['start'].replace('Z', '+00:00')).astimezone(ET).date().isoformat()
        b = BI.get((day, d['home'], d['away']))
        eid, hs, as_ = RES[d['game_id']]; ls = LS.get(str(eid))
        if not b or hs is None or not ls or len(ls['h']) < 5 or len(ls['a']) < 5: continue
        B = {x['key']: {m['key']: m['outcomes'] for m in x['markets']} for x in d['bookmakers']}
        pin = B.get('pinnacle') or {}
        T = next((o['point'] for o in pin.get('totals', []) if o['name'] == 'Over'), None) or FULL.get(d['game_id'], (None,))[0]
        f5 = {}
        for o in pin.get('totals_1st_5_innings', []): f5.setdefault(o.get('point'), {})[o['name'].lower()] = o['price']
        f5 = {k: v for k, v in f5.items() if k is not None and 'over' in v and 'under' in v}
        if not T or not f5: continue
        ln, pr = min(f5.items(), key=lambda kv: abs(kv[1]['over'] - kv[1]['under']))
        v = sum(x or 0 for x in ls['h'][:5]) + sum(x or 0 for x in ls['a'][:5])
        if v == ln: continue
        q = (1 / pr['over']) / (1 / pr['over'] + 1 / pr['under']); mshare = ln / T; diff = b['share'] - mshare
        y = 1 if v > ln else 0
        X.append([1, math.log(q / (1 - q)), diff * 10]); Y.append(y)
        us = {s: max([o['price'] for bk in US for o in (B.get(bk) or {}).get('totals_1st_5_innings', []) if o['name'].lower() == s and o.get('point') == ln] or [0]) for s in ('over', 'under')}
        rows.append(dict(diff=diff, y=y, po=pr['over'], pu=pr['under'], uo=us['over'], uu=us['under'], month=day[:7]))
    print('games tested:', len(Y))
    if len(Y) < 100: return
    Xa, Ya = np.array(X), np.array(Y, dtype=float); w = np.zeros(3)
    for _ in range(30):
        p = 1 / (1 + np.exp(-Xa @ w)); H = Xa.T @ (Xa * (p * (1 - p))[:, None]) + 1e-6 * np.eye(3); w += np.linalg.solve(H, Xa.T @ (Ya - p))
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    print(f'blend: Pinnacle {w[1]:+.2f}, Bartolo F5 share minus market share (per 10 pts) {w[2]:+.2f} (z {w[2] / se[2]:+.2f})')
    Hh = collections.defaultdict(lambda: [0, 0, 0.0])
    for r in rows:
        for thr in (0.02, 0.03):
            if abs(r['diff']) < thr: continue
            side = 'over' if r['diff'] > 0 else 'under'; won = r['y'] == (1 if side == 'over' else 0)
            for k, pr in ((f'gap {int(thr * 100)}+ pts | {side} | Pinnacle', r['po'] if side == 'over' else r['pu']), (f'gap {int(thr * 100)}+ pts | {side} | best US', r['uo'] if side == 'over' else r['uu'])):
                if not pr: continue
                x = Hh[k]; x[0] += won; x[1] += not won; x[2] += (pr - 1) if won else -1
            x = Hh[f'gap {int(thr * 100)}+ pts | {side} | {r["month"]}']; pr = r['po'] if side == 'over' else r['pu']; x[0] += won; x[1] += not won; x[2] += (pr - 1) if won else -1
    for k, (a, b_, u) in sorted(Hh.items()): print(f'   {k:40s} {a}-{b_} {100 * u / max(1, a + b_):+.1f}%')


if __name__ == '__main__':
    main()
