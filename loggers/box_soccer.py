#!/usr/bin/env python3
"""ESPN soccer player stats (goals, assists, shots, shots on target, appearances) for grading soccer props, every soccer game in
odds.sqlite since 2023-05 with an ESPN id. data/boxscores/soccer.jsonl.gz, resumable. Usage: python3 loggers/box_soccer.py [--max-s 550]"""
import os, sys, json, gzip, time, signal, sqlite3, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
signal.signal(signal.SIGTERM, lambda *a: sys.exit(124))
LG = {'soccer_epl': 'eng.1', 'soccer_france_ligue_one': 'fra.1', 'soccer_germany_bundesliga': 'ger.1', 'soccer_spain_la_liga': 'esp.1', 'soccer_italy_serie_a': 'ita.1', 'soccer_usa_mls': 'usa.1', 'soccer_uefa_champs_league': 'uefa.champions'}


def main():
    max_s = float(sys.argv[sys.argv.index('--max-s') + 1]) if '--max-s' in sys.argv else 1e9; t0 = time.time()
    path = os.path.join(ROOT, 'data', 'boxscores', 'soccer.jsonl.gz'); done = set()
    if os.path.exists(path):
        for l in lines(path):
            try: done.add(json.loads(l)['event_id'])
            except Exception: pass
    c = sqlite3.connect(os.path.join(ROOT, 'data', 'oddsapi', 'odds.sqlite'))
    todo = [(k, str(e)) for k, e in c.execute("SELECT g.key, r.espn_id FROM games g JOIN results r USING(game_id) WHERE g.sport='soccer' AND g.start>='2023-05-03' AND r.espn_id IS NOT NULL") if str(e) not in done and k in LG]
    print(f'[box soccer] {len(done)} done, {len(todo)} to pull', flush=True); n = 0
    with gzip.open(path, 'at') as f:
        for k, ev in todo:
            if time.time() - t0 > max_s: break
            d = None
            for i in range(3):
                try: d = json.load(urllib.request.urlopen(urllib.request.Request(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{LG[k]}/summary?event={ev}", headers={'User-Agent': 'sharp-tracker'}), timeout=30)); break
                except Exception: time.sleep(2)
            if d is None: continue
            P = {}
            for team in d.get('rosters') or []:
                ab = (team.get('team') or {}).get('abbreviation')
                for p in team.get('roster') or []:
                    nm = (p.get('athlete') or {}).get('displayName')
                    if nm: P[nm] = dict(team=ab, starter=p.get('starter'), **{s['name']: s.get('value') for s in p.get('stats') or []})
            f.write(json.dumps(dict(event_id=ev, players=P), separators=(',', ':')) + '\n'); n += 1
            time.sleep(0.05)
    print(f'[box soccer] wrote {n}', flush=True)


if __name__ == '__main__':
    main()
