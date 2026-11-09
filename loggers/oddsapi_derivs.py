#!/usr/bin/env python3
"""Odds API historical derivatives (Sean 11/5: "use the rest of the credits"): per-event pregame snapshot of first-half and team-total
markets, for games already in data/oddsapi/odds.sqlite. Historical period / additional markets exist from 2023-05-03 only.
Cost: 10 credits per market returned per game (one region). Second-half lines are not posted pregame, so 2H cannot be pulled.

Plans (sport: markets):  nfl: spreads_h1,totals_h1,team_totals   nba: totals_h1
Snapshot = start - 10 minutes (the API returns the latest snapshot at or before that time). Raw bookmaker payloads are appended to
data/oddsapi/derivs/<sport>.jsonl.gz, one line per game; reruns skip games already pulled. Stops when credits remaining < --floor.
Usage: ODDS_API_KEY=... python3 loggers/oddsapi_derivs.py nfl nba [--floor 12000] [--newest-first]"""
import os, sys, json, gzip, time, signal, sqlite3, urllib.request, urllib.error, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines as gz_lines
# 11/6: the 30-minute `timeout` SIGTERM killed the process mid-member, leaving a truncated gzip member; the next pass appended after it and
# gzip readers stop at the break. Exit cleanly on SIGTERM so the open member is closed, and read the done set member by member.
signal.signal(signal.SIGTERM, lambda *a: sys.exit(124))
DB = os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'); OUTD = os.path.join(ROOT, 'data', 'oddsapi', 'derivs')
API = 'https://api.the-odds-api.com/v4'; KEY = os.environ.get('ODDS_API_KEY')
BOOKS = 'pinnacle,draftkings,fanduel,williamhill_us,betonlineag,lowvig,betrivers,bovada,circasports,betmgm'
PLAN = {'nfl': 'spreads_h1,totals_h1,team_totals', 'nba': 'totals_h1', 'cfb': 'spreads_h1,totals_h1', 'nhl': 'totals_p1', 'mlb': 'totals_1st_5_innings,spreads_1st_5_innings'}
# 11/5 late (credits topped up to 15M): every period and team market each sport carries, one pregame snapshot per game -> <sport>_full
FULL = {'nfl': 'spreads_h1,totals_h1,h2h_h1,team_totals,totals_q1,spreads_q1,team_totals_h1',
        'nba': 'totals_h1,spreads_h1,h2h_h1,team_totals,totals_q1,spreads_q1,h2h_q1,team_totals_h1',
        'nhl': 'totals_p1,spreads_p1,h2h_p1,h2h_3_way_p1,team_totals,totals_p2,totals_p3',
        'mlb': 'totals_1st_5_innings,spreads_1st_5_innings,h2h_1st_5_innings,h2h_3_way_1st_5_innings,totals_1st_1_innings,totals_1st_3_innings,team_totals',
        'cbb': 'totals_h1,spreads_h1,h2h_h1,team_totals', 'cfb': 'totals_h1,spreads_h1,h2h_h1,team_totals,totals_q1,spreads_q1',
        'wnba': 'totals_h1,spreads_h1,team_totals,totals_q1', 'soccer': 'totals_h1,spreads_h1,h2h_h1,btts,draw_no_bet,team_totals,alternate_totals',
        'tennis': 'h2h_s1'}
# 11/6 (Sean: "props too?"): player props, same snapshot, -> <sport>_props. Markets probed 11/6; CBB/CFB skipped (1-2 markets, no Pinnacle).
PROPS = {'nfl': 'player_pass_yds,player_pass_tds,player_pass_completions,player_pass_attempts,player_pass_interceptions,player_rush_yds,player_rush_attempts,player_receptions,player_reception_yds,player_anytime_td,player_rush_reception_yds,player_pass_rush_yds',
         'nba': 'player_points,player_rebounds,player_assists,player_threes,player_points_rebounds_assists,player_blocks,player_steals,player_points_rebounds,player_points_assists,player_rebounds_assists,player_double_double',
         'nhl': 'player_points,player_goal_scorer_anytime,player_shots_on_goal,player_assists,player_blocked_shots,player_total_saves,player_power_play_points',
         'mlb': 'batter_hits,batter_total_bases,batter_home_runs,batter_rbis,batter_runs_scored,batter_hits_runs_rbis,batter_walks,pitcher_strikeouts,pitcher_hits_allowed,pitcher_walks,pitcher_earned_runs,pitcher_outs,pitcher_record_a_win',
         'wnba': 'player_points,player_rebounds,player_assists,player_threes,player_points_rebounds_assists',
         'soccer': 'player_goal_scorer_anytime,player_first_goal_scorer,player_shots_on_target,player_shots,player_assists'}
# 11/6: --early N pulls the same markets N minutes before the start instead of 10 (does an off-curve edge exist when the live rules fire?)
EARLY = int(sys.argv[sys.argv.index('--early') + 1]) if '--early' in sys.argv else None
CURVE = {'cbb': 'totals,spreads,totals_h1', 'cfb': 'totals,spreads,totals_q1,team_totals', 'nhl': 'totals,spreads,totals_p3,spreads_p1'}
# 11/6: the other quarters and the second half (books post them pregame; the CFB first-quarter edge suggests they are derived too)
QUARTERS = {'nfl': 'totals,spreads,totals_q2,totals_q3,totals_q4,spreads_q2,spreads_q3,spreads_q4,totals_h2,spreads_h2',
            'cfb': 'totals,spreads,totals_q2,totals_q3,totals_q4,spreads_q2,spreads_q3,spreads_q4,totals_h2,spreads_h2',
            'nba': 'totals,spreads,totals_q2,totals_q3,totals_q4,spreads_q2,spreads_q3,spreads_q4,totals_h2,spreads_h2',
            'wnba': 'totals,spreads,totals_q2,totals_q3,totals_q4,totals_h2',
            'cbb': 'totals,spreads,totals_h2,spreads_h2'}
if '--quarters' in sys.argv: PLAN = QUARTERS
if '--curve' in sys.argv: PLAN = CURVE
if '--full' in sys.argv: PLAN = FULL
if '--props' in sys.argv: PLAN = PROPS
# 11/8: --markets a,b pulls only those markets (an early props snapshot for the rules that fire, without paying for every prop market)
if '--markets' in sys.argv: PLAN = {k: sys.argv[sys.argv.index('--markets') + 1] for k in PLAN}
SINCE = '2023-05-03'


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def recent(G, now):
    """11/8: the exported game list ends when it was exported (NFL: 2026-02-08), so this season's games were never pulled. Add every game
    since then from the historical events list, one call per sport key per day at 12:00Z (1 credit each)."""
    keys = sorted({g[1] for g in G})
    if not G or len(keys) > 3: return G
    have = {g[0] for g in G}; last = max(g[2] for g in G)
    d = dt.datetime.fromisoformat(last[:10] + 'T12:00:00+00:00'); end = dt.datetime.fromisoformat(now.replace('Z', '+00:00'))
    if (end - d).days < 2: return G
    add = 0
    while d < end:
        for k in keys:
            j, cost, rem, st = get(f"{API}/historical/sports/{k}/events?apiKey={KEY}&date={d.strftime('%Y-%m-%dT%H:%M:%SZ')}")
            for e in ((j or {}).get('data') or []):
                if e['id'] in have or not (last < e['commence_time'] < now): continue
                have.add(e['id']); G.append((e['id'], k, e['commence_time'], e['home_team'], e['away_team'])); add += 1
        d += dt.timedelta(days=1)
    print(f'[derivs] added {add} games after {last[:10]} from the events list', flush=True)
    return G


def get(url):
    """(json, cost, remaining, status). status: 'ok', 'none' (404/422: the event has no snapshot), or 'fail' (do not record)."""
    for i in range(8):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sharp-tracker'}), timeout=60)
            return json.load(r), int(r.headers.get('x-requests-last') or 0), int(r.headers.get('x-requests-remaining') or 0), 'ok'
        except urllib.error.HTTPError as e:
            if e.code in (404, 422): return None, 0, None, 'none'
            if e.code == 401: raise SystemExit('[derivs] 401: key rejected or out of credits')
            time.sleep(min(60, 2 ** i) if e.code == 429 else 3 * (i + 1))
        except Exception:
            time.sleep(3 * (i + 1))
    return None, 0, None, 'fail'


def main():
    if not KEY: raise SystemExit('ODDS_API_KEY not set')
    floor = int(arg('--floor', '12000')); sports = [a for a in sys.argv[1:] if a in PLAN]; suffix = '_full' if '--full' in sys.argv else '_props' if '--props' in sys.argv else '_curve' if '--curve' in sys.argv else '_quarters' if '--quarters' in sys.argv else ''
    if EARLY:      # 11/6: an early snapshot also carries the full-game total and spread of that moment (the curve is built from them)
        suffix = f'_early{EARLY}' if suffix == '_full' else suffix + f'_t{EARLY}m'
        if '--full' in sys.argv: PLAN.update({k: 'totals,spreads,' + v for k, v in PLAN.items() if not v.startswith('totals,spreads')})
    os.makedirs(OUTD, exist_ok=True); conn = sqlite3.connect(DB) if os.path.exists(DB) else None
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    for sp in sports:
        path = os.path.join(OUTD, f'{sp}{suffix}.jsonl.gz'); done = set()
        if os.path.exists(path):
            for l in gz_lines(path):
                try: done.add(json.loads(l)['game_id'])
                except Exception: pass
        order = 'DESC' if '--newest-first' in sys.argv else 'ASC'
        if conn is not None:
            G = conn.execute(f"SELECT game_id, key, start, home, away FROM games WHERE sport=? AND start>=? AND start<? AND key LIKE '%\\_%' ESCAPE '\\' ORDER BY start {order}", (sp, SINCE, now)).fetchall()   # Odds API ids only (live-logger rows carry ESPN ids)
        else:      # GitHub runners have no odds.sqlite: the exported list data/oddsapi/derivs/_games.json.gz
            G = [(g['game_id'], g['key'], g['start'], g['home'], g['away']) for g in json.load(gzip.open(os.path.join(OUTD, '_games.json.gz'), 'rt')) if g['sport'] == sp and SINCE <= g['start'] < now]
            G = recent(G, now)
            G.sort(key=lambda x: x[2], reverse=(order == 'DESC'))
        todo = [g for g in G if g[0] not in done]
        print(f'[derivs] {sp}: {len(G)} games since {SINCE}, {len(done)} done, {len(todo)} to pull ({PLAN[sp]})', flush=True)
        n = spent = fails = 0; left = None
        with gzip.open(path, 'at') as out:
            for gid, key, start, home, away in todo:
                when = (dt.datetime.fromisoformat(start.replace('Z', '+00:00')) - dt.timedelta(minutes=EARLY or 10)).strftime('%Y-%m-%dT%H:%M:%SZ')
                d, cost, rem, status = get(f"{API}/historical/sports/{key}/events/{gid}/odds?apiKey={KEY}&bookmakers={BOOKS}&markets={PLAN[sp]}&oddsFormat=decimal&date={when}")
                spent += cost; left = rem if rem is not None else left
                if status == 'fail': fails += 1; continue          # not recorded, so a rerun retries it
                e = (d or {}).get('data') or {}
                out.write(json.dumps(dict(game_id=gid, sport=sp, start=start, home=home, away=away, snap=(d or {}).get('timestamp'), asked=when,
                                          markets=PLAN[sp], status=status, bookmakers=e.get('bookmakers') or [])) + '\n')
                n += 1
                if n % 100 == 0: out.flush(); print(f'[derivs] {sp}: {n}/{len(todo)} pulled, {fails} failed (will retry), {spent} credits this run, {left} left', flush=True)
                if left is not None and left < floor: print(f'[derivs] stopping at the {floor} floor ({left} left)', flush=True); return
                time.sleep(0.4)
        print(f'[derivs] {sp}: finished {n} games, {spent} credits, {left} left', flush=True)


if __name__ == '__main__':
    main()
