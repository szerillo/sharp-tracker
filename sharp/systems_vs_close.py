#!/usr/bin/env python3
"""Our systems against Pinnacle's close from The Odds API (Sean, 11/4: "test our own systems"). Two things:

  A. Every paper fill in the ledger (data/state/fills.jsonl) gets Pinnacle's closing no-vig price on its side from the closest Odds
     API snapshot before the start (data/oddsapi/<sport>), at the same number when the line matches, with the closing number noted
     when it does not. Per rule: fills, record, units, mean close CLV, how often the number moved for / against. This is the
     market's verdict on each rule as it fired, independent of our own tape (which only starts 10/29).
  B. Replays of the rules that can be stated from odds alone, on every game in the snapshots (this season): NHL dog +1.5 when the dog
     moneyline is +181 to +196 (nhl_pl_dog_bigml) and the two exchange rules' pricing cousins are not replayable (they need the
     exchange tape). More replays need the season logs lined up with the snapshots (next).
Writes data/research/systems_vs_close.json. Usage: python3 sharp/systems_vs_close.py"""
import os, sys, json, re, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.oddsapi_edge as E
OUT = os.path.join(ROOT, 'data', 'research', 'systems_vs_close.json')


def main():
    F = [json.loads(l) for l in open(os.path.join(ROOT, 'data', 'state', 'fills.jsonl'))]
    S = [f for f in F if str(f.get('rule_tag', '')).startswith('paper:') and f.get('mclass', 'game') == 'game' and f.get('result') != 'void']
    sched = {}
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'cbb'):
        try: sched.update({k: dict(v, sport=sp) for k, v in json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json'))).items()})
        except Exception: pass
    H = json.load(open(os.path.join(ROOT, 'data', 'state', 'hist_schedule.json')))
    for sp, G in H.items():
        for k, v in G.items(): sched.setdefault(k, dict(v, sport=sp, away_team={'abbreviation': v.get('away')}, home_team={'abbreviation': v.get('home')}))
    teams = json.load(open(os.path.join(ROOT, 'data', 'state', 'espn_teams.json')))
    closes = {}
    for sp in ('nba', 'nhl', 'nfl', 'cfb', 'cbb'):
        G = E.load_sport(sp); rows = [r for r in (E.fold(g) for g in G.values()) if r]
        T = teams.get(sp, {}); byname = {E.norm(t['name']): ab for ab, t in T.items() if t.get('name')}
        for r in rows:
            if r['hours_before'] > 6: continue
            ha, aa = byname.get(E.norm(r['home'])), byname.get(E.norm(r['away']))
            if not ha or not aa:
                for k, ab in byname.items():
                    if len(k) >= 6 and (k in E.norm(r['home'])): ha = ha or ab
                    if len(k) >= 6 and (k in E.norm(r['away'])): aa = aa or ab
            if ha and aa: closes[(sp, aa, ha, r['start'][:10])] = r
    out = []; per = collections.defaultdict(lambda: dict(n=0, graded=0, w=0, l=0, units=0.0, clv=[], line_for=0, line_against=0, same=0))
    for f in S:
        e = sched.get(f['event_id'])
        if not e: continue
        sp = e['sport']; aw = (e.get('away_team') or {}).get('abbreviation') or e.get('away'); hm = (e.get('home_team') or {}).get('abbreviation') or e.get('home')
        d = f['start_utc'][:10]
        c = closes.get((sp, aw, hm, d)) or closes.get((sp, aw, hm, (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat())) or closes.get((sp, aw, hm, (dt.date.fromisoformat(d) - dt.timedelta(days=1)).isoformat()))
        tag = f['rule_tag'][6:]; base = re.sub(r'^(1h|1q|1p)_', '', f['market'])
        rec = dict(tag=tag, event=f"{aw} @ {hm}", start=f['start_utc'], market=f['market'], side=f['side'], line=f.get('line'), price=f['implied'], venue=f['venue'], result=f.get('result'), pnl=f.get('pnl_units'))
        p = per[tag]; p['n'] += 1
        if f.get('result') in ('W', 'L', 'P'):
            p['graded'] += 1; p['w'] += f['result'] == 'W'; p['l'] += f['result'] == 'L'; p['units'] += f.get('pnl_units') or 0
        if c and f['market'] == base:            # full-game markets only: the snapshots carry no first-half lines
            if base == 'ml' and c.get('p_home') is not None:
                q = c['p_home'] if f['side'] == 'home' else 1 - c['p_home']; rec['close_nv'] = round(q, 4); rec['clv'] = round(100 * (q - f['implied']), 2)
            elif base == 'spread' and c.get('spread_home') is not None:
                cl = c['spread_home'] if f['side'] == 'home' else -c['spread_home']; dec = c['spread_home_dec'] if f['side'] == 'home' else c['spread_away_dec']
                oth = c['spread_away_dec'] if f['side'] == 'home' else c['spread_home_dec']; q = (1 / dec) / (1 / dec + 1 / oth)
                rec['close_line'] = cl; rec['close_nv'] = round(q, 4); rec['line_move'] = round(cl - float(f.get('line') or 0), 1)
                if f.get('line') is not None and abs(cl - float(f['line'])) < 1e-9: rec['clv'] = round(100 * (q - f['implied']), 2); p['same'] += 1
                elif f.get('line') is not None: p['line_for' if cl < float(f['line']) else 'line_against'] += 1     # a lower number than taken = the market moved toward us? (for a spread, taking +6.5 that closes +5.5 is value: close < taken)
            elif base == 'total' and c.get('total') is not None:
                cl = c['total']; dec = c['over_dec'] if f['side'] == 'over' else c['under_dec']; oth = c['under_dec'] if f['side'] == 'over' else c['over_dec']; q = (1 / dec) / (1 / dec + 1 / oth)
                rec['close_line'] = cl; rec['close_nv'] = round(q, 4)
                if f.get('line') is not None and abs(cl - float(f['line'])) < 1e-9: rec['clv'] = round(100 * (q - f['implied']), 2); p['same'] += 1
                elif f.get('line') is not None:
                    good = (cl < float(f['line'])) if f['side'] == 'under' else (cl > float(f['line']))
                    p['line_for' if good else 'line_against'] += 1
        if rec.get('clv') is not None: p['clv'].append(rec['clv'])
        out.append(rec)
    summ = {k: dict(n=v['n'], graded=v['graded'], record=f"{v['w']}-{v['l']}", units=round(v['units'], 2), clv_close=round(sum(v['clv']) / len(v['clv']), 2) if v['clv'] else None, clv_n=len(v['clv']),
                    number_moved_for=v['line_for'], number_moved_against=v['line_against'], same_number=v['same']) for k, v in sorted(per.items())}
    # B. replay: NHL dog +1.5 when the dog ML is +181 to +196 at the close (Pinnacle), bet the puck line at Pinnacle's price
    G = E.load_sport('nhl'); rows = [r for r in (E.fold(g) for g in G.values()) if r and r['hours_before'] <= 6]
    E.results_games('nhl', rows)
    rp = dict(n=0, w=0, l=0, p=0, pnl=0.0)
    for r in rows:
        if r.get('hs') is None or r.get('p_home') is None or r.get('spread_home') is None: continue
        dog = 'away' if r['p_home'] >= .5 else 'home'; dec = r['pin_dec_away'] if dog == 'away' else r['pin_dec_home']; am = (dec - 1) * 100
        if not (181 <= am <= 196): continue
        line = -r['spread_home'] if dog == 'away' else r['spread_home']
        if abs(line) != 1.5: continue
        margin = (r['as'] - r['hs'] if dog == 'away' else r['hs'] - r['as']) + 1.5; pdec = r['spread_away_dec'] if dog == 'away' else r['spread_home_dec']
        rp['n'] += 1
        if margin > 0: rp['w'] += 1; rp['pnl'] += pdec - 1
        elif margin < 0: rp['l'] += 1; rp['pnl'] -= 1
        else: rp['p'] += 1
    summ['_replay_nhl_pl_dog_bigml_this_season'] = dict(rp, roi=round(100 * rp['pnl'] / rp['n'], 1) if rp['n'] else None)
    json.dump(dict(fills=out, summary=summ), open(OUT, 'w'), indent=1)
    for k, v in summ.items(): print(f"  {k:30} {v}")


if __name__ == '__main__':
    main()
