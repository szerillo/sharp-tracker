#!/usr/bin/env python3
"""Near pass (11/22, Sean via Kirk: "the board must be current when he uses it"). The full tracker (price database + systems engine) runs
hourly and takes about 35 minutes, so on Sun 11/22 system_fires.json lagged the 10-minute signals job by up to two hours: lapsed wind bets
stayed live and NO @ CHI never re-checked its wind before kickoff. This runs the WHOLE systems engine, every rule, on the small database of
games starting inside the next BUILD_SOON_H hours (12 by default; sharp/build_db.py with BUILD_SOON_H), on every signals run, so every
trigger near kickoff (wind from the latest forecast included) fires, re-fires or lapses within about 15 minutes. Games further out keep the
hourly tracker build.
system_fires.json: games inside the window are replaced by this run's; every other game is kept as the tracker left it. 'built' stays the
tracker's full-build time (the commit guards in signals.yml / keep_newer_fires.py compare it); this run's time goes in 'near_built'.
Usage: BUILD_DB=data/state/soon.sqlite BUILD_SOON_H=12 python3 sharp/build_db.py && python3 sharp/near_pass.py"""
import os, sys, json, sqlite3, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp import systems as S

DB = os.environ.get('BUILD_DB') or os.path.join(ROOT, 'data', 'state', 'soon.sqlite')


def main():
    t0 = time.time()
    if not os.path.exists(DB): print('[near] no soon database; nothing to do'); return
    c = sqlite3.connect(DB); soon = {r[0] for r in c.execute("SELECT event_id FROM events")}; c.close()
    if not soon: print('[near] no games inside the window'); return
    real = S.VIEW
    old = json.load(open(real)) if os.path.exists(real) else {}
    S.DB, S.VIEW = DB, real + '.near'
    try: S.main()
    finally: S.VIEW = real
    new = json.load(open(real + '.near')); os.remove(real + '.near')
    keep = [g for g in old.get('games', []) if g.get('event_id') not in soon]
    got = [g for g in new.get('games', []) if g.get('event_id') in soon]
    out = dict(old) if old else dict(new)
    out.update(games=keep + got, near_built=new['built'], near_window_h=float(os.environ.get('BUILD_SOON_H') or 12), near_games=len(got),
               rules=new.get('rules', out.get('rules')), record=new.get('record', out.get('record')))
    out.setdefault('built', new['built'])
    json.dump(out, open(real, 'w'), default=str, separators=(',', ':'))
    print(f"[near] {len(soon)} games inside {out['near_window_h']:g}h; {len(got)} on the board from this run, {len(keep)} kept from the tracker build; {time.time() - t0:.0f}s")


if __name__ == '__main__':
    main()
