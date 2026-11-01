#!/usr/bin/env python3
"""Tennis schedule and set-by-set results from ESPN (ATP and WTA tour singles; Challengers and ITF are not on ESPN).

Sean, 11/1: first-set betting is a big tennis market and a place to look for an edge, so every match keeps its per-set games.
Each run reads the ESPN scoreboard for yesterday, today and tomorrow (ET) and writes:
  data/tennis/schedule.json     match_id -> tour, tournament, round, start, players (full names, ESPN ids), status
  data/tennis/results.jsonl     one row per finished match (appended once): sets as [[p1 games, p2 games], ...], winner,
                                first_set_winner, n_sets, total games, retirement / walkover flags
Players are kept in ESPN order (p1, p2); exchange markets are matched to them by surname later (as MMA fighters are).
Usage: python3 loggers/tennis_scores.py [--days-back N]"""
import os, sys, json, time, datetime as dt, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'data', 'tennis'); os.makedirs(OUT, exist_ok=True)
SCHED = os.path.join(OUT, 'schedule.json'); RES = os.path.join(OUT, 'results.jsonl')
ET = __import__('zoneinfo').ZoneInfo('America/New_York')
BACK = int(sys.argv[sys.argv.index('--days-back') + 1]) if '--days-back' in sys.argv else 1


def g(u, tries=4):
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=30))
        except Exception: time.sleep(2 * (i + 1))
    return {}


def matches(tour, day):
    s = g(f"https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard?dates={day.strftime('%Y%m%d')}")
    for ev in s.get('events', []):
        for gp in ev.get('groupings') or []:
            grp = (gp.get('grouping') or {}).get('displayName') or ''
            if 'Singles' not in grp: continue
            for c in gp.get('competitions', []):
                yield ev, grp, c


def parse(tour, ev, grp, c):
    st = (c.get('status') or {}).get('type') or {}
    comps = sorted(c.get('competitors', []), key=lambda x: x.get('order', 0))
    if len(comps) != 2: return None
    pl = []
    for x in comps:
        a = x.get('athlete') or {}
        pl.append(dict(name=a.get('displayName'), short=a.get('shortName'), id=a.get('id') or x.get('id'), winner=bool(x.get('winner')),
                       games=[int(l['value']) for l in x.get('linescores', []) if l.get('value') is not None],
                       tb=[l.get('tiebreak') for l in x.get('linescores', [])]))
    rnd = (c.get('round') or {}).get('displayName') or (c.get('type') or {}).get('text')
    rec = dict(match_id=str(c.get('id')), tour=tour, tournament=ev.get('name'), tournament_id=ev.get('id'), draw=grp, round=rnd, start=c.get('date'),
               status=st.get('name'), detail=st.get('detail') or st.get('shortDetail'), venue=((c.get('venue') or {}).get('fullName')),
               p1=pl[0]['name'], p2=pl[1]['name'], p1_id=pl[0]['id'], p2_id=pl[1]['id'])
    if st.get('completed'):
        sets = [[a, b] for a, b in zip(pl[0]['games'], pl[1]['games'])]
        w = 'p1' if pl[0]['winner'] else ('p2' if pl[1]['winner'] else None)
        det = (rec['detail'] or '').lower()
        rec.update(sets=sets, winner=w, n_sets=len(sets), total_games=sum(a + b for a, b in sets),
                   first_set_winner=('p1' if sets and sets[0][0] > sets[0][1] else ('p2' if sets and sets[0][1] > sets[0][0] else None)),
                   first_set_complete=bool(sets) and max(sets[0]) >= 6 and (abs(sets[0][0] - sets[0][1]) >= 2 or max(sets[0]) == 7),
                   retired='ret' in det or 'retired' in det, walkover='walkover' in det or st.get('name') == 'STATUS_WALKOVER',
                   tiebreaks=[[x, y] for x, y in zip(pl[0]['tb'], pl[1]['tb'])])
    return rec


def main():
    sched = json.load(open(SCHED)) if os.path.exists(SCHED) else {}
    have = set()
    if os.path.exists(RES):
        for l in open(RES): have.add(json.loads(l)['match_id'])
    today = dt.datetime.now(ET).date(); new = 0; seen = 0
    with open(RES, 'a') as fr:
        for d in range(-BACK, 2):
            day = today + dt.timedelta(days=d)
            for tour in ('atp', 'wta'):
                for ev, grp, c in matches(tour, day):
                    r = parse(tour, ev, grp, c)
                    if not r: continue
                    seen += 1
                    sched[r['match_id']] = {k: v for k, v in r.items() if k not in ('sets', 'tiebreaks')}
                    if 'sets' in r and r['match_id'] not in have and not r['walkover']:
                        fr.write(json.dumps(r) + '\n'); have.add(r['match_id']); new += 1
    cut = (today - dt.timedelta(days=21)).isoformat()            # schedule keeps three weeks
    sched = {k: v for k, v in sched.items() if (v.get('start') or '9999') >= cut}
    json.dump(sched, open(SCHED, 'w'), separators=(',', ':'))
    print(f"[tennis] {seen} singles matches seen ({len(sched)} on the schedule), {new} new results")


if __name__ == '__main__':
    main()
