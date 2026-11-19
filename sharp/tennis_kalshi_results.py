#!/usr/bin/env python3
"""Kalshi match-winner settlements for tennis (11/19): grades the x: matches (Challenger / ITF events ESPN does not carry), which were
never graded before. Series: KXATPCHALLENGERMATCH, KXWTACHALLENGERMATCH, KXATPMATCH, KXWTAMATCH. One row per Kalshi event (two player
markets): the winner is the player whose market settled yes; a scalar settlement (walkover or no ball played) or anything other than
exactly one yes gives no result. Writes data/tennis/kalshi_match_results.json, merged with what is already there (incremental: only
markets closed since the last build, less a day, are fetched).
Usage: python3 sharp/tennis_kalshi_results.py [--since YYYY-MM-DD]"""
import os, sys, re, json, time, unicodedata, datetime as dt, urllib.request, urllib.error
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT = os.path.join(ROOT, 'data', 'tennis', 'kalshi_match_results.json')
KAPI = 'https://api.elections.kalshi.com/trade-api/v2'
SERIES = ('KXATPCHALLENGERMATCH', 'KXWTACHALLENGERMATCH', 'KXATPMATCH', 'KXWTAMATCH')
FIRST = '2026-10-25'          # the tennis paper logs start in late October


def get(u, tries=4):
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=30))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(3 * (i + 1)); continue
            time.sleep(1 + i)
        except Exception: time.sleep(1 + i)
    return None


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return [t for t in re.sub(r'[^a-z\s-]', ' ', s).replace('-', ' ').split() if t]


def same_player(a, b):
    """Same rule as loggers/tennis_lines.py: same surname (first initials agree when both have one), or for reversed name order a shared
    token of 4+ letters that is one side's surname."""
    ta, tb = norm(a), norm(b)
    if not ta or not tb: return False
    if ta[-1] == tb[-1]:
        fa, fb = ta[:-1], tb[:-1]
        return not fa or not fb or fa[0][0] == fb[0][0]
    return (ta[-1] in tb and len(ta[-1]) >= 4) or (tb[-1] in ta and len(tb[-1]) >= 4)


def build(since=None):
    D = json.load(open(OUT)) if os.path.exists(OUT) else {'events': {}}
    E = D.get('events', {})
    start = since or (D.get('built', FIRST + 'T00:00:00Z')[:10])
    t0 = int((dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc) - dt.timedelta(days=1)).timestamp())
    got = 0
    for s in SERIES:
        cur = ''
        for _ in range(200):
            r = get(f"{KAPI}/markets?series_ticker={s}&status=settled&limit=1000&min_close_ts={t0}" + (f"&cursor={cur}" if cur else ''))
            if r is None: print(f'[kalshi results] {s}: fetch failed, keeping what is stored'); break
            for m in r.get('markets', []):
                ev = E.setdefault(m['event_ticker'], dict(series=s, time=m.get('occurrence_datetime') or m.get('close_time'), players={}))
                ev['players'][m.get('yes_sub_title') or m['ticker']] = m.get('result'); got += 1
            cur = r.get('cursor') or ''
            if not cur or not r.get('markets'): break
    for ev in E.values():
        yes = [p for p, res in ev['players'].items() if res == 'yes']
        ev['winner'] = yes[0] if len(yes) == 1 and len(ev['players']) == 2 and all(v in ('yes', 'no') for v in ev['players'].values()) else None
    D = dict(built=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), source='Kalshi settled markets: ' + ', '.join(SERIES), events=E)
    os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(D, open(OUT, 'w'), separators=(',', ':'), sort_keys=True)
    print(f"[kalshi results] {got} markets read; {len(E)} events stored, {sum(1 for e in E.values() if e['winner'])} with a winner")
    return D


def load():
    return (json.load(open(OUT)) if os.path.exists(OUT) else {}).get('events', {})


def winner_side(home, away, start, K, hours=48):
    """home / away player names and the scheduled start of a paper row. -> 'p1' (home won), 'p2' (away won) or None. Both players must
    match one Kalshi event settled within `hours` of the start."""
    if not home or not away or not start: return None
    s_ = start if re.search(r'T\d\d:\d\d:\d\d', start) else start.replace('Z', ':00Z')
    st = dt.datetime.fromisoformat(s_.replace('Z', '+00:00'))
    for k in K.values():
        if not k.get('winner') or len(k['players']) != 2: continue
        try: kt = dt.datetime.fromisoformat(k['time'].replace('Z', '+00:00'))
        except Exception: continue
        if abs((kt - st).total_seconds()) > hours * 3600: continue
        n1, n2 = list(k['players'])
        if (same_player(n1, home) and same_player(n2, away)) or (same_player(n1, away) and same_player(n2, home)):
            return 'p1' if same_player(k['winner'], home) else 'p2'
    return None


if __name__ == '__main__':
    a = sys.argv[1:]
    build(a[a.index('--since') + 1] if '--since' in a else None)
