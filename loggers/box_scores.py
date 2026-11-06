#!/usr/bin/env python3
"""Player box scores from ESPN game summaries (free), for grading player props (data/oddsapi/derivs/<sport>_props.jsonl.gz).
Every final in data/state/hist_schedule.json since 2023-05-03 for the sport. One line per game in data/boxscores/<sport>.jsonl.gz:
{event_id, start, home, away, players: {display name: {team, <stat key>: value, ...}}}. Resumable; closes the gzip member on SIGTERM.
Usage: python3 loggers/box_scores.py nba [--max-s 1700]"""
import os, sys, json, gzip, time, signal, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
signal.signal(signal.SIGTERM, lambda *a: sys.exit(124))
LG = {'nfl': 'football/nfl', 'nba': 'basketball/nba', 'nhl': 'hockey/nhl', 'wnba': 'basketball/wnba', 'mlb': 'baseball/mlb'}
OUT = os.path.join(ROOT, 'data', 'boxscores')


def get(u):
    for i in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=30))
        except Exception: time.sleep(2 * (i + 1))
    return None


def parse(d):
    P = {}
    for team in (d.get('boxscore') or {}).get('players') or []:
        ab = (team.get('team') or {}).get('abbreviation')
        for cat in team.get('statistics') or []:
            keys = cat.get('keys') or cat.get('labels') or []; pre = (cat.get('name') or '')
            for a in cat.get('athletes') or []:
                nm = (a.get('athlete') or {}).get('displayName')
                if not nm or not a.get('stats'): continue
                x = P.setdefault(nm, {'team': ab})
                for k, v in zip(keys, a['stats']): x[(pre + '.' if pre and pre not in ('', 'statistics') else '') + k] = v
    return P


def main():
    sp = sys.argv[1]; max_s = float(sys.argv[sys.argv.index('--max-s') + 1]) if '--max-s' in sys.argv else 1e9; t0 = time.time()
    os.makedirs(OUT, exist_ok=True); path = os.path.join(OUT, f'{sp}.jsonl.gz'); done = set()
    if os.path.exists(path):
        for l in lines(path):
            try: done.add(json.loads(l)['event_id'])
            except Exception: pass
    H = json.load(open(os.path.join(ROOT, 'data', 'state', 'hist_schedule.json'))).get(sp, {})
    todo = sorted((v['start'], k) for k, v in H.items() if v.get('start', '') >= '2023-05-03' and v.get('hs') is not None and k not in done)
    print(f'[box] {sp}: {len(done)} done, {len(todo)} to pull', flush=True); n = 0
    with gzip.open(path, 'at') as f:
        for st, ev in reversed(todo):
            if time.time() - t0 > max_s: break
            d = get(f"https://site.api.espn.com/apis/site/v2/sports/{LG[sp]}/summary?event={ev}")
            if d is None: continue
            P = parse(d); h = H[ev]
            f.write(json.dumps(dict(event_id=ev, start=st, home=h.get('home'), away=h.get('away'), players=P), separators=(',', ':')) + '\n'); n += 1
            if n % 200 == 0: print(f'[box] {sp}: {n}', flush=True)
            time.sleep(0.05)
    print(f'[box] {sp}: wrote {n}', flush=True)


if __name__ == '__main__':
    main()
