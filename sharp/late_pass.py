#!/usr/bin/env python3
"""Late pass (Sean, 11/4: "aren't there systems that lock within 90 minutes of a start time?"). The systems engine runs three times a
day on the full price database; the two exchange rules (xch_homedog_fade, nba_momentum) only fire inside T-90 minutes, so on that
schedule they only ever saw games starting 6 to 7 PM. This runs every 20 minutes from signals.yml on a small database of the games
starting in the next 2.5 hours (sharp/build_db.py with BUILD_SOON_H), fires the late rules, and refreshes the Price / Bet to columns
for every fill on those games. It edits data/state/system_fired.json and system_fires.json in place (only the games it looked at;
nothing else on the board moves) and only writes when something changed.
Usage: BUILD_DB=data/state/soon.sqlite BUILD_SOON_H=2.5 python3 sharp/build_db.py && python3 sharp/late_pass.py"""
import os, sys, json, sqlite3, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp import systems as S
from sharp import norm as N

DB = os.environ.get('BUILD_DB') or os.path.join(ROOT, 'data', 'state', 'soon.sqlite')


def main():
    if not os.path.exists(DB): print('[late] no soon database; nothing to do'); return
    conn = sqlite3.connect(DB)
    evs = conn.execute("SELECT event_id, sport, start_utc, away, home FROM events").fetchall()
    if not evs: print('[late] no games starting soon'); return
    fired = json.load(open(S.FIRED)) if os.path.exists(S.FIRED) else {}
    view = json.load(open(S.VIEW)) if os.path.exists(S.VIEW) else {}
    before = json.dumps(fired, sort_keys=True)
    games = {g['event_id']: g for g in view.get('games', [])}
    fires_now, new_games = [], []
    S.late_rules(conn, fired, fires_now, new_games)
    for g in new_games:                      # a game the board did not have yet (its only trigger is a late rule)
        if g['event_id'] in games:
            G = games[g['event_id']]; G['triggers'].update(g['triggers'])
            have = {f.get('fill_id') for f in G.get('fills', [])}
            G['fills'].extend(f for f in g['fills'] if f.get('fill_id') not in have)
        else:
            r_ = S.sched_rec(g['sport'], g['event_id']); g['away_name'] = (r_.get('away_team') or {}).get('displayName') or g['away']; g['home_name'] = (r_.get('home_team') or {}).get('displayName') or g['home']
            g['league'] = r_.get('league'); games[g['event_id']] = g; view.setdefault('games', []).append(g)
    changed = json.dumps(fired, sort_keys=True) != before
    # refresh Price / Bet to on every fill of the games starting soon
    soon = {e[0] for e in evs}
    for g in view.get('games', []):
        if g['event_id'] not in soon: continue
        snap = json.dumps(g.get('fills'), sort_keys=True, default=str)
        g['hours_to_kickoff'] = round((N.parse_ts(g['start_utc']) - S.NOW).total_seconds() / 3600, 1)
        S.refresh_fills(conn, g)
        if json.dumps(g.get('fills'), sort_keys=True, default=str) != snap: changed = True
    if not changed: print(f"[late] {len(evs)} games inside the window, nothing new"); return
    json.dump(fired, open(S.FIRED, 'w'), indent=0)
    view['late_pass'] = S.NOW_S
    json.dump(view, open(S.VIEW, 'w'), default=str, separators=(',', ':'))
    print(f"[late] {len(evs)} games inside the window; {len(fires_now)} new paper fills: {[f'{f['game']} {f['tag']} {f['market']} {f['side']}' for f in fires_now]}")


if __name__ == '__main__':
    main()
