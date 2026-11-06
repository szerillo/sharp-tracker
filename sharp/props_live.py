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
KEY = os.environ.get('ODDS_API_KEY'); API = 'https://api.the-odds-api.com/v4'
PLAN = {'nba': ('basketball_nba', 'player_threes', 'basketball/nba'), 'nhl': ('icehockey_nhl', 'player_total_saves,player_shots_on_goal', 'hockey/nhl')}
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
                if not 0.15 < h <= float(os.environ.get('PROPS_H', 3)): continue
                d = get(f"{API}/sports/{sk}/events/{e['id']}/odds?apiKey={KEY}&regions=us,eu&markets={markets}&bookmakers=pinnacle,{','.join(BOOKS)}&oddsFormat=decimal")
                if not d: continue
                Q = {}
                for b in d.get('bookmakers') or []:
                    for m in b['markets']:
                        for o in m['outcomes']:
                            if o.get('point') is None or o['name'] not in ('Over', 'Under'): continue
                            Q.setdefault((m['key'], o.get('description'), o['point']), {}).setdefault(b['key'], {})[o['name'].lower()] = o['price']
                for (mk, player, ln), B in Q.items():
                    P = B.get('pinnacle')
                    if not P or 'over' not in P or 'under' not in P: continue
                    fu = (1 / P['under']) / (1 / P['over'] + 1 / P['under'])
                    best = max(((bk, v['under']) for bk, v in B.items() if bk in BOOKS and 'under' in v), key=lambda x: x[1], default=None)
                    if not best or fu * best[1] - 1 < EV_MIN: continue
                    key = f"{e['id']}|{mk}|{player}|{ln}"
                    if key in seen: continue
                    seen.add(key); new += 1
                    rows.append(dict(key=key, sport=sp, odds_id=e['id'], espn=espn_event(sp, e['home_team'], e['away_team'], st), game=f"{e['away_team']} @ {e['home_team']}",
                                     start=e['commence_time'], market=mk, player=player, line=ln, side='under', book=BOOKS[best[0]], price=best[1], fair=round(fu, 4),
                                     ev=round(100 * (fu * best[1] - 1), 1), pin_under=P['under'], flagged=NOW.strftime('%Y-%m-%dT%H:%M:%SZ')))
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
        won = 0.5 if v == r['line'] else 1 if v < r['line'] else 0
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
