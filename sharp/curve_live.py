#!/usr/bin/env python3
"""Derivatives off the curve, live (Sean 11/6: "build that then upgrade them from paper"). Research: docs/deriv_curve_2026-11-06.md.
For games starting in the next 3 hours: the Odds API current odds (the backtest's own source) for the full game and the derivative;
Pinnacle's full-game total and spread give the curve (past games with a similar total and spread, scaled to this game's numbers, from
data/research/curve_pool_<sport>.json.gz, the same method as sharp/deriv_curve.py); the derivative's curve probability is compared with
Pinnacle's no-vig on the same line. A bet when they differ by the rule's gap, on the side the curve prefers, at the best of FD / Caesars /
DK / Pinnacle-matching price at that line.
Rules:
  cbb_1h_total_curve   CBB first-half total, gap 7+ points, either side (backtest 313-231, +9.7%, 3 of 3 seasons). Tier C, 0.25u.
  cfb_q1_under_curve   CFB first-quarter total UNDER, gap 5+ points (at kickoff 242-176, +8.8%; 2 hours out 296-189, +15.0%, every season). Tier A (Sean, 11/6), 0.5u.
  cfb_tt_under_curve   CFB team-total UNDER, gap 5+ points (backtest 210-176, +7.3%; 2025 -4.5%). Tier C 0.25u from 11/6 (Sean).
Writes data/state/curve_live.json (board) and data/state/curve_paper.jsonl (every fire, graded on ESPN period scores).
Usage: ODDS_API_KEY=... python3 sharp/curve_live.py"""
import os, sys, json, gzip, bisect, re, time, urllib.request, urllib.error, unicodedata, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.fairprice import check as fair_check   # 11/7: Pinnacle freshness + the book's own fair next to Pinnacle's
KEY = os.environ.get('ODDS_API_KEY'); API = 'https://api.the-odds-api.com/v4'
NOW = dt.datetime.fromisoformat(os.environ['CURVE_NOW']) if os.environ.get('CURVE_NOW') else dt.datetime.now(dt.timezone.utc)
HORIZON_H = float(os.environ.get('CURVE_H', 3))
BOOKS = {'fanduel': 'FD', 'williamhill_us': 'Caesars', 'draftkings': 'DK'}
RULES = {
    'cbb_1h_total_curve': dict(sport='cbb', key='basketball_ncaab', mk='totals_h1', per=(0, 1), gap=0.07, sides=('over', 'under'), tier='C', stake=0.25),
    'cfb_q1_under_curve': dict(sport='cfb', key='americanfootball_ncaaf', mk='totals_q1', per=(0, 1), gap=0.05, sides=('under',), tier='A', stake=0.5),    # 11/6: B after the T-2h test (296-189, +15.0%; every season +10 to +19); A on Sean's call
    # 11/6 paper: NHL period markets off the curve at kickoff (validate at 6 hours before the start when that pull lands)
    'nhl_p1_spread_curve': dict(sport='nhl', key='icehockey_nhl', mk='spreads_p1', per=(0, 1), gap=0.07, sides=('home', 'away'), kind='spread', tier='C', stake=0.25),
    # 11/6 9am: B after the 6-hours-before test: 243-185, +13.3%, every season (+19.7 / +5.3 / +17.9); kickoff 241-194, +10.9%
    'nhl_p3_under_curve': dict(sport='nhl', key='icehockey_nhl', mk='totals_p3', per=(2, 1), gap=0.07, sides=('under',), tier='B', stake=0.5),
    'cfb_tt_under_curve': dict(sport='cfb', key='americanfootball_ncaaf', mk='team_totals', per=None, gap=0.05, sides=('under',), tier='C', stake=0.25),
}
PAPER = os.path.join(ROOT, 'data', 'state', 'curve_paper.jsonl'); OUT = os.path.join(ROOT, 'data', 'state', 'curve_live.json')
QPER = {'cbb': 2, 'cfb': 4}


def nm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower(); return re.sub(r'[^a-z]', '', s)


def get(u):
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=30))
        except urllib.error.HTTPError as e:
            if e.code in (401, 404, 422): return None
            time.sleep(2 * (i + 1))
        except Exception: time.sleep(2 * (i + 1))
    return None


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


_POOL = {}
def pool(sp):
    if sp not in _POOL:
        P = json.load(gzip.open(os.path.join(ROOT, 'data', 'research', f'curve_pool_{sp}.json.gz'), 'rt'))
        Tm = sum(p[1] for p in P) / len(P)
        _POOL[sp] = (P, (sum((p[1] - Tm) ** 2 for p in P) / len(P)) ** .5 or 1, (sum(p[2] ** 2 for p in P) / len(P)) ** .5 or 1)
    return _POOL[sp]


def curve(sp, T, S, kind, per, team=None):
    """sorted curve values of the outcome (total points over the period, or a team's points) for a game with full total T and home spread S"""
    P, Tsd, Ssd = pool(sp)
    nb = sorted(P, key=lambda x: ((x[1] - T) / Tsd) ** 2 + ((x[2] - S) / Ssd) ** 2)[:max(150, len(P) // 12)]
    vals = []
    for season, Tx, Sx, hs, as_, lh, la in nb:
        if kind == 'total':
            i0, n = per
            if len(lh) < i0 + n or len(la) < i0 + n: continue
            vals.append((sum(lh[i0:i0 + n]) + sum(la[i0:i0 + n])) * T / Tx)
        elif kind == 'spread':              # home margin over the period, shifted by the full-game spread difference scaled to the period
            i0, n = per
            if len(lh) < i0 + n or len(la) < i0 + n: continue
            frac = n / {'nba': 4, 'nfl': 4, 'cfb': 4, 'wnba': 4, 'cbb': 2, 'nhl': 3, 'mlb': 9}.get(sp, 4)
            vals.append((sum(lh[i0:i0 + n]) - sum(la[i0:i0 + n])) + (Sx - S) * frac)
        else:
            imp_g = T / 2 + (-S if team == 'home' else S) / 2; imp_x = Tx / 2 + (-Sx if team == 'home' else Sx) / 2
            if imp_x <= 0 or imp_g <= 0: continue
            vals.append((hs if team == 'home' else as_) * imp_g / imp_x)
    return sorted(vals)


def probs(vals, line, side):
    lo = bisect.bisect_left(vals, line); hi = bisect.bisect_right(vals, line); n = len(vals)
    over = (n - hi) / n; push = (hi - lo) / n; under = lo / n
    w = over if side == 'over' else under
    return w / max(1e-9, 1 - push)


def espn_event(sp, home, away, start):
    try: S = json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json')))
    except Exception: return None
    best = None
    for k, e in S.items():
        try: d = abs((ts(e['start'].replace('Z', ':00Z') if len(e['start']) == 17 else e['start']) - start).total_seconds())
        except Exception: continue
        if d > 5400: continue
        hn, an = nm((e.get('home_team') or {}).get('displayName')), nm((e.get('away_team') or {}).get('displayName'))
        if (hn == nm(home) and an == nm(away)) or (hn and an and (hn in nm(home) or nm(home) in hn) and (an in nm(away) or nm(away) in an)):
            if best is None or d < best[0]: best = (d, k)
    return best[1] if best else None


def main():
    rows = []
    if os.path.exists(PAPER):
        for l in open(PAPER):
            try: rows.append(json.loads(l))
            except Exception: pass
    seen = {r['key'] for r in rows}; new = 0
    if KEY:
        for sk in sorted({r['key'] for r in RULES.values()}):
            rules = {k: r for k, r in RULES.items() if r['key'] == sk}; sp = list(rules.values())[0]['sport']
            mks = ','.join(['totals', 'spreads'] + sorted({r['mk'] for r in rules.values()}))
            for e in get(f"{API}/sports/{sk}/events?apiKey={KEY}") or []:
                st = ts(e['commence_time']); h = (st - NOW).total_seconds() / 3600
                if not 0.15 < h <= HORIZON_H: continue
                d = get(f"{API}/sports/{sk}/events/{e['id']}/odds?apiKey={KEY}&regions=us,eu&markets={mks}&bookmakers=pinnacle,{','.join(BOOKS)}&oddsFormat=decimal")
                if not d: continue
                B = {b['key']: {m['key']: m['outcomes'] for m in b['markets']} for b in d.get('bookmakers') or []}
                # 11/7: each book's quote time per market (Pinnacle freshness check in sharp/fairprice.py)
                TS = {(b['key'], m['key']): m.get('last_update') or b.get('last_update') for b in d.get('bookmakers') or [] for m in b['markets']}
                NICE = {v: k for k, v in BOOKS.items()}
                pin = B.get('pinnacle') or {}
                T = next((o['point'] for o in pin.get('totals', []) if o['name'] == 'Over'), None)
                S = next((o['point'] for o in pin.get('spreads', []) if o['name'] == e['home_team']), None)
                if T is None or S is None: continue
                for tag, R in rules.items():
                    outs = pin.get(R['mk']) or []
                    if R.get('kind') == 'spread':       # period spread: P(home covers) from the curve of period margins
                        P2 = {o['name']: o for o in outs if o.get('point') is not None}
                        ho, ao = P2.get(e['home_team']), P2.get(e['away_team'])
                        if not ho or not ao or ho['point'] != -ao['point']: continue
                        vals = curve(sp, T, S, 'spread', R['per'])
                        if len(vals) < 100: continue
                        ln = ho['point']; lo = bisect.bisect_left(vals, -ln); hi = bisect.bisect_right(vals, -ln); N_ = len(vals)
                        ph = ((N_ - hi) / N_) / max(1e-9, 1 - (hi - lo) / N_); qh = (1 / ho['price']) / (1 / ho['price'] + 1 / ao['price'])
                        for side, pc, q, pp_ in (('home', ph, qh, ho['price']), ('away', 1 - ph, 1 - qh, ao['price'])):
                            if side not in R['sides'] or pc - q < R['gap']: continue
                            nm_ = e['home_team'] if side == 'home' else e['away_team']; sl = ln if side == 'home' else -ln
                            us = [(nice, o['price']) for bk, nice in BOOKS.items() for o in (B.get(bk) or {}).get(R['mk'], []) if o['name'] == nm_ and o.get('point') == sl]
                            book, price = max(us, key=lambda c: c[1]) if us else (None, None)
                            key = f"{tag}|{e['id']}||{side}"
                            if key in seen: continue
                            fc = None
                            if book:
                                oth = e['away_team'] if side == 'home' else e['home_team']
                                bo = next((o['price'] for o in (B.get(NICE[book]) or {}).get(R['mk'], []) if o['name'] == oth and o.get('point') == -sl), None)
                                fc = fair_check(pp_, ao['price'] if side == 'home' else ho['price'], price, price, bo, TS.get(('pinnacle', R['mk'])), TS.get((NICE[book], R['mk'])), NOW)
                                if not fc['fresh']: print(f"[curve_live] skip {tag} {e['id']} {side}: {fc['stale_why']}"); continue
                                fc['ev_curve'] = round(100 * ((pc if R.get('kind') != 'spread' else (ph if side == 'home' else 1 - ph)) * price - 1), 1)   # the rule's edge is the curve's, not Pinnacle's
                            seen.add(key); new += 1
                            rows.append(dict(key=key, rule=tag, tier=R['tier'] if book else 'P', stake=R['stake'] if book else 0.0, sport=sp, odds_id=e['id'], espn=espn_event(sp, e['home_team'], e['away_team'], st),
                                             game=f"{e['away_team']} @ {e['home_team']}", start=e['commence_time'], market=R['mk'], team=None, team_name=nm_, side=side, line=sl,
                                             curve=round(pc, 3), pin_fair=round(q, 3), gap=round(100 * (pc - q), 1), full_total=T, full_spread=S,
                                             pin_price=pp_, book=book, price=price, **({k: fc[k] for k in ('pin_fair_power', 'book_fair', 'fair_gap', 'ev_curve')} if fc else {}),
                                             flagged=NOW.strftime('%Y-%m-%dT%H:%M:%SZ')))
                        continue
                    groups = {}
                    for o in outs:
                        if o['name'] not in ('Over', 'Under') or o.get('point') is None: continue
                        team = None
                        if R['mk'] == 'team_totals':
                            team = 'home' if o.get('description') == e['home_team'] else 'away' if o.get('description') == e['away_team'] else None
                            if not team: continue
                        groups.setdefault((team, o['point']), {})[o['name'].lower()] = o['price']
                    for (team, ln), pr in groups.items():
                        if 'over' not in pr or 'under' not in pr: continue
                        vals = curve(sp, T, S, 'team' if team else 'total', R['per'], team)
                        if len(vals) < 100: continue
                        for side in R['sides']:
                            q = (1 / pr[side]) / (1 / pr['over'] + 1 / pr['under']); pc = probs(vals, ln, side)
                            if pc - q < R['gap']: continue
                            # best bettable price at Pinnacle's line
                            cand = [('Pinnacle line', pr[side])]
                            for bk, nice in BOOKS.items():
                                for o in (B.get(bk) or {}).get(R['mk'], []):
                                    if o['name'].lower() == side and o.get('point') == ln and (not team or o.get('description') == (e['home_team'] if team == 'home' else e['away_team'])): cand.append((nice, o['price']))
                            us = [c for c in cand if c[0] != 'Pinnacle line']
                            book, price = max(us, key=lambda c: c[1]) if us else (None, None)
                            key = f"{tag}|{e['id']}|{team or ''}|{side}"
                            if key in seen: continue
                            fc = None
                            if book:
                                oside = 'under' if side == 'over' else 'over'
                                bo = next((o['price'] for o in (B.get(NICE[book]) or {}).get(R['mk'], []) if o['name'].lower() == oside and o.get('point') == ln and (not team or o.get('description') == (e['home_team'] if team == 'home' else e['away_team']))), None)
                                fc = fair_check(pr[side], pr[oside], price, price, bo, TS.get(('pinnacle', R['mk'])), TS.get((NICE[book], R['mk'])), NOW)
                                if not fc['fresh']: print(f"[curve_live] skip {tag} {e['id']} {team or ''} {side}: {fc['stale_why']}"); continue
                                fc['ev_curve'] = round(100 * ((pc if R.get('kind') != 'spread' else (ph if side == 'home' else 1 - ph)) * price - 1), 1)   # the rule's edge is the curve's, not Pinnacle's
                            seen.add(key); new += 1
                            rows.append(dict(key=key, rule=tag, tier=R['tier'] if book else 'P', stake=R['stake'] if book else 0.0, sport=sp, odds_id=e['id'], espn=espn_event(sp, e['home_team'], e['away_team'], st),      # no FD/Caesars/DK price at the line: paper
                                             game=f"{e['away_team']} @ {e['home_team']}", start=e['commence_time'], market=R['mk'], team=team,
                                             team_name=(e['home_team'] if team == 'home' else e['away_team']) if team else None, side=side, line=ln,
                                             curve=round(pc, 3), pin_fair=round(q, 3), gap=round(100 * (pc - q), 1), full_total=T, full_spread=S,
                                             pin_price=pr[side], book=book, price=price, **({k: fc[k] for k in ('pin_fair_power', 'book_fair', 'fair_gap', 'ev_curve')} if fc else {}),
                                             flagged=NOW.strftime('%Y-%m-%dT%H:%M:%SZ')))
    # 11/9 (Sean, list item 2): closing line value. These derivative markets are not on our tick tape, so the bet tracker has no close for
    # them. In the last run before the start (inside 12 minutes), one Pinnacle-only call per game for the flagged markets. Stored per row:
    #   close_line   Pinnacle's closing number for our side (period spread: our team's points; totals: the line nearest ours)
    #   close_fair   Pinnacle's closing no-vig probability for our side at OUR number (when it still hangs it)
    #   clv          100 x (close_fair - 1/price paid)   beat_fair  close_fair minus Pinnacle's no-vig fair when flagged
    #   line_value   points Pinnacle's close moved past our number in our favour
    if KEY:
        due = {}
        for r in rows:
            if r.get('close_ts') or r.get('won') is not None or r.get('rule') not in RULES: continue
            m_ = (ts(r['start']) - NOW).total_seconds() / 60
            if 0 < m_ <= 12: due.setdefault((RULES[r['rule']]['key'], r['odds_id']), []).append(r)
        for (sk, oid), Rr in due.items():
            mks = ','.join(sorted({r['market'] for r in Rr}))
            d = get(f"{API}/sports/{sk}/events/{oid}/odds?apiKey={KEY}&regions=eu&markets={mks}&bookmakers=pinnacle&oddsFormat=decimal")
            pin = {m['key']: m['outcomes'] for b in (d or {}).get('bookmakers') or [] if b['key'] == 'pinnacle' for m in b['markets']}
            for r in Rr:
                r['close_ts'] = NOW.strftime('%Y-%m-%dT%H:%M:%SZ'); outs = pin.get(r['market']) or []
                if not outs: r['close_note'] = 'Pinnacle off the market at the close'; continue
                if RULES[r['rule']].get('kind') == 'spread':
                    mine = [o for o in outs if o['name'] == r['team_name'] and o.get('point') is not None]
                    if mine: r['close_line'] = mine[0]['point']; r['line_value'] = round(r['line'] - r['close_line'], 1)
                    a = next((o for o in mine if o['point'] == r['line']), None)
                    b_ = next((o for o in outs if o['name'] != r['team_name'] and o.get('point') == -r['line']), None)
                    if a and b_: r['close_fair'] = round((1 / a['price']) / (1 / a['price'] + 1 / b_['price']), 4)
                else:
                    want = (lambda o: o.get('description') == r['team_name']) if r.get('team') else (lambda o: True)
                    G = {}
                    for o in outs:
                        if o['name'] in ('Over', 'Under') and o.get('point') is not None and want(o): G.setdefault(o['point'], {})[o['name'].lower()] = o['price']
                    two = [ln for ln, v in G.items() if 'over' in v and 'under' in v]
                    if two:
                        r['close_line'] = min(two, key=lambda x: abs(x - r['line']))
                        r['line_value'] = round((r['close_line'] - r['line']) if r['side'] == 'over' else (r['line'] - r['close_line']), 1)
                    v = G.get(r['line']) or {}
                    if 'over' in v and 'under' in v:
                        fo = (1 / v['over']) / (1 / v['over'] + 1 / v['under']); r['close_fair'] = round(fo if r['side'] == 'over' else 1 - fo, 4)
                if r.get('close_fair') is not None:
                    pr = r.get('price') or r.get('pin_price')
                    if pr: r['clv'] = round(100 * (r['close_fair'] - 1 / pr), 2)
                    if r.get('pin_fair') is not None: r['beat_fair'] = round(100 * (r['close_fair'] - r['pin_fair']), 2)
            print(f"[curve_live] close check {sk} {oid}: {len(Rr)} leans, markets {mks}")
    # grade on ESPN period scores (schedule.json linescores) or the final
    S_ = {}
    for r in rows:
        if r.get('won') is not None or not r.get('espn'): continue
        sp = r['sport']
        if sp not in S_:
            try: S_[sp] = json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json')))
            except Exception: S_[sp] = {}
        e = S_[sp].get(r['espn'])
        if not e or not e.get('completed'): continue
        R = RULES[r['rule']]
        if R.get('kind') == 'spread':
            ls = e.get('linescores') or {}; i0, n = R['per']; lh, la = ls.get('home') or [], ls.get('away') or []
            if len(lh) < i0 + n or len(la) < i0 + n: continue
            m = sum(lh[i0:i0 + n]) - sum(la[i0:i0 + n]); c = (m if r['side'] == 'home' else -m) + r['line']
            won = 0.5 if c == 0 else 1 if c > 0 else 0; pr = r['price'] or r['pin_price']
            r['won'] = won; r['actual'] = m; r['units'] = round((r['stake'] or 0.25) * ((pr - 1) if won == 1 else -1 if won == 0 else 0), 3); continue
        try:
            if R['per'] is None:
                v = float((e['home_team'] if r['team'] == 'home' else e['away_team'])['score'])
            else:
                ls = e.get('linescores') or {}; i0, n = R['per']
                lh, la = ls.get('home') or [], ls.get('away') or []
                if len(lh) < i0 + n or len(la) < i0 + n: continue
                v = sum(lh[i0:i0 + n]) + sum(la[i0:i0 + n])
        except Exception: continue
        won = 0.5 if v == r['line'] else 1 if (v > r['line']) == (r['side'] == 'over') else 0
        pr = r['price'] or r['pin_price']
        r['won'] = won; r['actual'] = v; r['units'] = round((r['stake'] or 0.25) * ((pr - 1) if won == 1 else -1 if won == 0 else 0), 3)
    with open(PAPER, 'w') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    rec = {}
    for tag in RULES:
        g = [r for r in rows if r['rule'] == tag and r.get('won') is not None]
        rec[tag] = dict(n=len(g), won=sum(1 for r in g if r['won'] == 1), lost=sum(1 for r in g if r['won'] == 0), units=round(sum(r['units'] for r in g), 2))
        c_ = [r for r in rows if r['rule'] == tag and r.get('clv') is not None]
        if c_: rec[tag]['clv'] = dict(n=len(c_), avg=round(sum(r['clv'] for r in c_) / len(c_), 2), beat=sum(1 for r in c_ if r['clv'] > 0))
        l_ = [r for r in rows if r['rule'] == tag and r.get('line_value') is not None]
        if l_: rec[tag]['line_value'] = dict(n=len(l_), avg=round(sum(r['line_value'] for r in l_) / len(l_), 2), better=sum(1 for r in l_ if r['line_value'] > 0), worse=sum(1 for r in l_ if r['line_value'] < 0))
    open_ = [r for r in rows if r.get('won') is None and ts(r['start']) > NOW - dt.timedelta(hours=4)]
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), record=rec, rows=open_), open(OUT, 'w'), indent=1)
    print(f'[curve_live] {new} new, {len(open_)} open, record {rec}')


if __name__ == '__main__':
    main()
