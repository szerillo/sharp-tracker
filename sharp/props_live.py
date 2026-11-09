#!/usr/bin/env python3
"""Prop price-gap paper leans, live (11/6; research in docs/props_2026-11-06.md). The backtest found US books pricing some prop UNDERS
better than Pinnacle's no-vig fair at the same line, and those unders winning: NBA threes unders 2453-2198 (+7.9%, 4 of 4 seasons), NHL
goalie-saves unders 99-54 (+24.9%), NHL shots-on-goal unders 1098-1075 (+5.3%).
Live: the Odds API current odds (same source as the backtest) for games starting in the next 3 hours; a lean when FD, Caesars or DK
prices the under 2%+ better than Pinnacle's no-vig fair at the same line. First time per game / player / market / line. Graded on the
ESPN box score after the game. Paper until it has a forward record.
Writes data/state/props_live.json (board) and data/state/props_paper.jsonl (record). Usage: ODDS_API_KEY=... python3 sharp/props_live.py"""
import os, sys, json, re, time, urllib.request, datetime as dt, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.props_test import stat, nm
from sharp.fairprice import check as fair_check   # 11/7: power + proportional Pinnacle fair, the book's own fair, Pinnacle freshness
KEY = os.environ.get('ODDS_API_KEY'); API = 'https://api.the-odds-api.com/v4'
PLAN = {'nba': ('basketball_nba', 'player_threes', 'basketball/nba'), 'nhl': ('icehockey_nhl', 'player_total_saves,player_shots_on_goal', 'hockey/nhl'),
        'nfl': ('americanfootball_nfl', 'player_rush_yds,player_anytime_td', 'football/nfl')}
# 11/8 (docs/nfl_props_2026-11-08.md): NFL rushing-yards OUTLIER book. Pinnacle hangs one line, a bettable book hangs one line 4.5+ yards away,
# and 2+ other books sit within a yard of Pinnacle: bet the side the gap favours at the outlier (its line is lower -> over, higher -> under).
# 2023-26 one snapshot per game: 65-35, +21.9%, 4 of 4 seasons; 2.5-4 yards away was flat (+3.5%). 100 bets, so paper.
OUTLIER = {'nfl': dict(market='player_rush_yds', gap=4.5, agree=2)}
OTHER = 'betrivers,bovada,betonlineag'     # fetched to count agreement with Pinnacle; not bet
# 11/8 (docs/nfl_props_2026-11-08.md, Yes/No props): NFL anytime-touchdown YES where Pinnacle's Yes/No no-vig puts the scorer at 25-50% and
# FD / Caesars / DK pay 2%+ over that fair. 2023-26, one bet per player and game at the best price: 538-1033, +10.4%, every season positive
# (+12 / +7 / +12 / +8); scorers under 25% were -3.1%, so the band is the rule. Paper. NBA double-doubles and NHL anytime goals: nothing.
BINARY = {'nfl': dict(market='player_anytime_td', lo=0.25, hi=0.50, ev=0.02)}
BOOKS = {'fanduel': 'FD', 'williamhill_us': 'Caesars', 'draftkings': 'DK'}
PAPER = os.path.join(ROOT, 'data', 'state', 'props_paper.jsonl'); OUT = os.path.join(ROOT, 'data', 'state', 'props_live.json')
NOW = dt.datetime.now(dt.timezone.utc); EV_MIN = 0.02; STAKE = 0.25


def get(u):
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=30))
        except urllib.error.HTTPError as e:
            if e.code in (401, 404, 422): return None
            time.sleep(2 * (i + 1))
        except Exception: time.sleep(2 * (i + 1))
    return None


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def espn_event(sp, home, away, start):
    try: S = json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json')))
    except Exception: return None
    for k, e in S.items():
        try:
            if abs((ts(e['start'].replace('Z', ':00Z') if len(e['start']) == 17 else e['start']) - start).total_seconds()) > 5400: continue
        except Exception: continue
        if nm((e.get('home_team') or {}).get('displayName')) == nm(home) and nm((e.get('away_team') or {}).get('displayName')) == nm(away): return k
    return None


def main():
    rows = []
    if os.path.exists(PAPER):
        for l in open(PAPER):
            try: rows.append(json.loads(l))
            except Exception: pass
    seen = {r['key'] for r in rows}; new = 0
    if KEY:
        for sp, (sk, markets, _) in PLAN.items():
            evs = get(f"{API}/sports/{sk}/events?apiKey={KEY}") or []
            for e in evs:
                st = ts(e['commence_time']); h = (st - NOW).total_seconds() / 3600
                # 11/7 (Sean): the backtest priced every prop 10-14 min before tip; flag only inside the last hour (was 3 h)
                if not 0.15 < h <= float(os.environ.get('PROPS_H', 1)): continue
                d = get(f"{API}/sports/{sk}/events/{e['id']}/odds?apiKey={KEY}&regions=us,eu&markets={markets}&bookmakers=pinnacle,{','.join(BOOKS)}{',' + OTHER if sp in OUTLIER else ''}&oddsFormat=decimal")
                if not d: continue
                if sp in OUTLIER:
                    o_ = OUTLIER[sp]; L = {}       # player -> book -> {line: (over, under, ts)}
                    for b in d.get('bookmakers') or []:
                        for m in b['markets']:
                            if m['key'] != o_['market']: continue
                            for o in m['outcomes']:
                                if o.get('point') is None or o['name'] not in ('Over', 'Under'): continue
                                q_ = L.setdefault(o.get('description'), {}).setdefault(b['key'], {}).setdefault(o['point'], {})
                                q_[o['name'].lower()] = o['price']; q_['ts'] = m.get('last_update') or b.get('last_update')
                    for player, books in L.items():
                        P = books.get('pinnacle') or {}
                        pl = [ln for ln, v in P.items() if 'over' in v and 'under' in v]
                        if len(pl) != 1: continue
                        ln0 = pl[0]
                        for bk, name in BOOKS.items():
                            bl = [ln for ln, v in (books.get(bk) or {}).items() if 'over' in v and 'under' in v]
                            if len(bl) != 1 or abs(bl[0] - ln0) < o_['gap']: continue
                            agree = sum(1 for k2, B2 in books.items() if k2 not in (bk, 'pinnacle') and any(abs(ln - ln0) <= 1 for ln in B2))
                            if agree < o_['agree']: print(f'[props_live] skip {player} rush {bl[0]} at {name}: Pinnacle {ln0} but only {agree} other books near it'); continue
                            side = 'over' if bl[0] < ln0 else 'under'; v = books[bk][bl[0]]; price = v[side]
                            key = f"{e['id']}|{o_['market']}|{player}|{bl[0]}|{side}"
                            if key in seen: continue
                            seen.add(key); new += 1
                            rows.append(dict(key=key, sport=sp, odds_id=e['id'], espn=espn_event(sp, e['home_team'], e['away_team'], st), game=f"{e['away_team']} @ {e['home_team']}",
                                             start=e['commence_time'], market=o_['market'], player=player, line=bl[0], side=side, book=name, price=price, rule='outlier book',
                                             pin_line=ln0, gap=round(abs(bl[0] - ln0), 1), agree=agree, pin_over=P[ln0]['over'], pin_under=P[ln0]['under'],
                                             pin_ts=P[ln0].get('ts'), book_ts=v.get('ts'), flagged=NOW.strftime('%Y-%m-%dT%H:%M:%SZ')))
                    if sp in BINARY:
                        b_ = BINARY[sp]; Y = {}      # player -> book -> {'Yes': price, 'No': price, 'ts': ..}
                        for b in d.get('bookmakers') or []:
                            for m in b['markets']:
                                if m['key'] != b_['market']: continue
                                for o in m['outcomes']:
                                    if o['name'] not in ('Yes', 'No'): continue
                                    q_ = Y.setdefault(o.get('description'), {}).setdefault(b['key'], {}); q_[o['name']] = o['price']; q_['ts'] = m.get('last_update') or b.get('last_update')
                        for player, books in Y.items():
                            P = books.get('pinnacle') or {}
                            if 'Yes' not in P or 'No' not in P: continue
                            fy = (1 / P['Yes']) / (1 / P['Yes'] + 1 / P['No'])
                            if not b_['lo'] <= fy < b_['hi']: continue
                            best = max(((bk, v['Yes']) for bk, v in books.items() if bk in BOOKS and 'Yes' in v), key=lambda x: x[1], default=None)
                            if not best or fy * best[1] - 1 < b_['ev']: continue
                            key = f"{e['id']}|{b_['market']}|{player}|yes"
                            if key in seen: continue
                            fc = fair_check(P['Yes'], P['No'], best[1], None, None, P.get('ts'), books[best[0]].get('ts'), NOW, max_age=5)
                            if not fc['fresh']: print(f"[props_live] skip {player} anytime TD {BOOKS[best[0]]}: {fc['stale_why']}"); continue
                            seen.add(key); new += 1
                            rows.append(dict(key=key, sport=sp, odds_id=e['id'], espn=espn_event(sp, e['home_team'], e['away_team'], st), game=f"{e['away_team']} @ {e['home_team']}",
                                             start=e['commence_time'], market=b_['market'], player=player, line=0.5, side='over', book=BOOKS[best[0]], price=best[1], rule='anytime td',
                                             fair=round(fy, 4), fair_power=fc['pin_fair_power'], ev=round(100 * (fy * best[1] - 1), 1), ev_strict=fc['ev_strict'], pin_yes=P['Yes'], pin_no=P['No'],
                                             pin_ts=P.get('ts'), book_ts=books[best[0]].get('ts'), flagged=NOW.strftime('%Y-%m-%dT%H:%M:%SZ')))
                    continue
                Q = {}
                for b in d.get('bookmakers') or []:
                    for m in b['markets']:
                        for o in m['outcomes']:
                            if o.get('point') is None or o['name'] not in ('Over', 'Under'): continue
                            q_ = Q.setdefault((m['key'], o.get('description'), o['point']), {}).setdefault(b['key'], {})
                            q_[o['name'].lower()] = o['price']; q_['ts'] = m.get('last_update') or b.get('last_update')
                for (mk, player, ln), B in Q.items():
                    P = B.get('pinnacle')
                    if not P or 'over' not in P or 'under' not in P: continue
                    fu = (1 / P['under']) / (1 / P['over'] + 1 / P['under'])
                    best = max(((bk, v['under']) for bk, v in B.items() if bk in BOOKS and 'under' in v), key=lambda x: x[1], default=None)
                    if not best or fu * best[1] - 1 < EV_MIN: continue
                    key = f"{e['id']}|{mk}|{player}|{ln}"
                    if key in seen: continue
                    bv = B[best[0]]
                    # 11/7 backtest (props grid, 2023-26): a Pinnacle quote 5+ min old lost (NBA 14-19, NHL 7-9); NBA threes only when the book's
                    # own no-vig is 4+ points below Pinnacle's; replaced 11/8 by EV 4%+, see below. NHL keeps the 2% rule.
                    fc = fair_check(P['under'], P['over'], best[1], bv.get('under'), bv.get('over'), P.get('ts'), bv.get('ts'), NOW, max_age=5)
                    if not fc['ok']:
                        print(f"[props_live] skip {player} {mk} u{ln} {BOOKS[best[0]]} {best[1]}: {fc['stale_why'] or 'no edge on the power-devig fair'} ({fc['ev_strict']}%)"); continue
                    # 11/8 (docs/nfl_props_2026-11-08.md, Sean): the 4-point fair-gap filter was fit to the 10-minute snapshot and flipped at the
                    # 60-minute window the feed now uses (2-4 points was +13.3% there). EV 4%+ on the stricter Pinnacle fair holds at both windows
                    # (+11.6% at T-10, +11.2% at T-60, every season positive), so threes use that instead.
                    if mk == 'player_threes' and fc['ev_strict'] < 4:
                        print(f"[props_live] skip {player} threes u{ln} {BOOKS[best[0]]} {best[1]}: only {fc['ev_strict']}% EV on the strict fair (threes need 4%)"); continue
                    seen.add(key); new += 1
                    rows.append(dict(key=key, sport=sp, odds_id=e['id'], espn=espn_event(sp, e['home_team'], e['away_team'], st), game=f"{e['away_team']} @ {e['home_team']}",
                                     start=e['commence_time'], market=mk, player=player, line=ln, side='under', book=BOOKS[best[0]], price=best[1], fair=round(fu, 4),
                                     ev=round(100 * (fu * best[1] - 1), 1), pin_under=P['under'], pin_over=P['over'], book_over=bv.get('over'),
                                     fair_power=fc['pin_fair_power'], book_fair=fc['book_fair'], fair_gap=fc['fair_gap'], ev_strict=fc['ev_strict'],
                                     pin_ts=P.get('ts'), book_ts=bv.get('ts'), flagged=NOW.strftime('%Y-%m-%dT%H:%M:%SZ')))
    # grade on the ESPN box score
    box = {}
    for r in rows:
        if r.get('won') is not None or not r.get('espn') or ts(r['start']) > NOW - dt.timedelta(hours=3.5): continue
        k = (r['sport'], r['espn'])
        if k not in box:
            d = get(f"https://site.api.espn.com/apis/site/v2/sports/{PLAN[r['sport']][2]}/summary?event={r['espn']}")
            done_ = ((((d or {}).get('header') or {}).get('competitions') or [{}])[0].get('status') or {}).get('type', {}).get('completed')
            if not done_: box[k] = None; continue
            from loggers.box_scores import parse
            box[k] = {nm(n): v for n, v in parse(d).items()}
        B = box[k]
        if B is None: continue
        p = B.get(nm(r['player']))
        if p is None: r['won'] = 'void'; r['units'] = 0.0; continue
        v = stat(r['sport'], r['market'], p)
        if v is None: continue
        won = 0.5 if v == r['line'] else 1 if (v < r['line']) == (r.get('side', 'under') == 'under') else 0
        r['won'] = won; r['actual'] = v; r['units'] = round(STAKE * ((r['price'] - 1) if won == 1 else -1 if won == 0 else 0), 3)
    with open(PAPER, 'w') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    g = [r for r in rows if r.get('won') in (0, 0.5, 1)]
    rec = dict(n=len(g), won=sum(1 for r in g if r['won'] == 1), lost=sum(1 for r in g if r['won'] == 0), units=round(sum(r['units'] for r in g), 2))
    open_ = [r for r in rows if r.get('won') is None and ts(r['start']) > NOW - dt.timedelta(hours=4)]
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), record=rec, rows=open_), open(OUT, 'w'), indent=1)
    print(f'[props_live] {new} new, {len(open_)} open, record {rec}')


if __name__ == '__main__':
    main()
