#!/usr/bin/env python3
"""Bulk historical pull from The Odds API (Sean, 11/4, 5M-credit plan): openers and closes for every sport we work, several seasons,
stored COMPACT (one line per game per snapshot: every book's moneyline, spread and total) so the repo stays small. Raw snapshots are
not kept. Resumable: data/oddsapi/compact/_done.json records every (sport, snapshot time) already pulled.

Per sport, per game day, the snapshot slots (UTC) below: a morning line and the hours games start in that sport, so the analysis can
take the last snapshot before each game (the close) and the first (the open). Days with no games are skipped with a 1-credit probe
of the events endpoint where the calendar is irregular (soccer, tennis, MMA, NFL, CFB).

Usage: ODDS_API_KEY=... python3 loggers/oddsapi_bulk.py <plan> [--budget N]
  plans: nba nhl cbb nfl cfb soccer tennis mma   (each covers the seasons listed in PLANS)
Output: data/oddsapi/compact/<sport>.jsonl.gz  rows {t (snapshot), id, sport, key, start, home, away, books: {book: {h2h:[home,away], sp:[home line, home dec, away dec], tot:[line, over dec, under dec]}}}"""
import os, sys, json, gzip, time, datetime as dt, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'data', 'oddsapi', 'compact')
API = "https://api.the-odds-api.com/v4"; KEY = os.environ.get('ODDS_API_KEY')
BOOKS = 'pinnacle,draftkings,fanduel,williamhill_us,betmgm,betonlineag,lowvig,betrivers,bovada,circasports'
D = dt.date
PLANS = {
    # sport: (api key, markets, seasons [(first day, last day)], slots (UTC hours; <12 means next calendar day), probe days first?)
    'nba': ('basketball_nba', 'h2h,spreads,totals', [(D(2021, 10, 19), D(2022, 6, 17)), (D(2022, 10, 18), D(2023, 6, 13)), (D(2023, 10, 24), D(2024, 6, 20)), (D(2024, 10, 22), D(2025, 6, 25)), (D(2025, 10, 21), D(2026, 6, 25))], [15, 23, 0, 1, 2, 3], False),
    'nhl': ('icehockey_nhl', 'h2h,spreads,totals', [(D(2021, 10, 12), D(2022, 6, 27)), (D(2022, 10, 7), D(2023, 6, 14)), (D(2023, 10, 10), D(2024, 6, 25)), (D(2024, 10, 4), D(2025, 6, 20)), (D(2025, 10, 7), D(2026, 6, 20))], [15, 23, 0, 1, 2, 3], False),
    'cbb': ('basketball_ncaab', 'h2h,spreads,totals', [(D(2021, 11, 9), D(2022, 4, 5)), (D(2022, 11, 7), D(2023, 4, 4)), (D(2023, 11, 6), D(2024, 4, 9)), (D(2024, 11, 4), D(2025, 4, 8)), (D(2025, 11, 3), D(2026, 4, 7))], [15, 23, 0, 1, 2, 3], False),
    'nfl': ('americanfootball_nfl', 'h2h,spreads,totals', [(D(2021, 9, 8), D(2022, 2, 14)), (D(2022, 9, 7), D(2023, 2, 13)), (D(2023, 9, 6), D(2024, 2, 12)), (D(2024, 9, 4), D(2025, 2, 10)), (D(2025, 9, 3), D(2026, 2, 9))], [15, 17, 20, 0, 1], True),
    'cfb': ('americanfootball_ncaaf', 'h2h,spreads,totals', [(D(2021, 8, 26), D(2022, 1, 11)), (D(2022, 8, 25), D(2023, 1, 10)), (D(2023, 8, 24), D(2024, 1, 9)), (D(2024, 8, 24), D(2025, 1, 21)), (D(2025, 8, 23), D(2026, 1, 20))], [15, 16, 19, 23, 0, 3], True),
    'mma': ('mma_mixed_martial_arts', 'h2h,totals', [(D(2022, 1, 1), D(2025, 12, 31))], [22, 2], True),
}
SOCCER = {'epl': 'soccer_epl', 'laliga': 'soccer_spain_la_liga', 'seriea': 'soccer_italy_serie_a', 'ucl': 'soccer_uefa_champs_league', 'mls': 'soccer_usa_mls', 'ligamx': 'soccer_mexico_ligamx'}
SOCCER_SEASONS = [(D(2021, 8, 1), D(2022, 6, 5)), (D(2022, 8, 1), D(2023, 6, 12)), (D(2023, 8, 1), D(2024, 6, 5)), (D(2024, 8, 1), D(2025, 6, 5)), (D(2025, 7, 15), D(2026, 6, 5))]
SOCCER_SLOTS = [10, 12, 14, 16, 19, 0, 2]
# tennis: the 2026 windows from oddsapi_tennis.py, shifted a year back for 2024 and 2025 and widened a week each side (the events probe trims)
sys.path.insert(0, HERE)
from oddsapi_tennis import TENNIS as TENNIS_2026


def get(u):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=60) as r:
                return json.load(r), int(r.headers.get('x-requests-last') or 0), int(r.headers.get('x-requests-remaining') or 0)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(5 * (i + 1)); continue
            if e.code in (404, 422): return None, 0, None
            time.sleep(2 + i)
        except Exception: time.sleep(2 + i)
    return None, 0, None


def compact(sport, key, d):
    t = d.get('timestamp'); rows = []
    for g in d.get('data') or []:
        B = {}
        for b in g.get('bookmakers') or []:
            e = {}
            for m in b.get('markets') or []:
                o = m.get('outcomes') or []
                if m['key'] == 'h2h':
                    p = {x['name']: x.get('price') for x in o}
                    if g['home_team'] in p and g['away_team'] in p: e['h2h'] = [p[g['home_team']], p[g['away_team']]] + ([p['Draw']] if 'Draw' in p else [])
                elif m['key'] == 'spreads':
                    h = next((x for x in o if x['name'] == g['home_team']), None); a = next((x for x in o if x['name'] == g['away_team']), None)
                    if h and a and h.get('point') is not None: e['sp'] = [h['point'], h.get('price'), a.get('price')]
                elif m['key'] == 'totals':
                    ov = next((x for x in o if x['name'] == 'Over'), None); un = next((x for x in o if x['name'] == 'Under'), None)
                    if ov and un and ov.get('point') is not None: e['tot'] = [ov['point'], ov.get('price'), un.get('price')]
            if e: B[b['key']] = e
        if B: rows.append(dict(t=t, id=g['id'], sport=sport, key=key, start=g['commence_time'], home=g['home_team'], away=g['away_team'], books=B))
    return rows


class Run:
    def __init__(self, budget, plan):
        os.makedirs(OUT, exist_ok=True); self.DONE = os.path.join(OUT, f'_done_{plan}.json')
        self.done = set(json.load(open(self.DONE))) if os.path.exists(self.DONE) else set(); self.budget = budget; self.spent = 0; self.left = None; self.n = 0; self.t0 = time.time()

    def save_done(self):
        tmp = self.DONE + '.tmp'; json.dump(sorted(self.done), open(tmp, 'w')); os.replace(tmp, self.DONE)

    def snap(self, sport, key, markets, when):
        k = f"{sport}|{key}|{when:%Y-%m-%dT%H%M}"
        if k in self.done: return True
        if self.spent + 40 > self.budget: return False
        d, used, left = get(f"{API}/historical/sports/{key}/odds/?apiKey={KEY}&bookmakers={BOOKS}&markets={markets}&oddsFormat=decimal&date={when:%Y-%m-%dT%H:%M:%SZ}")
        self.spent += used; self.left = left
        if d is None: self.done.add(k); return True
        rows = compact(sport, key, d)
        with gzip.open(os.path.join(OUT, f'{sport}.jsonl.gz'), 'at') as fh:
            for r in rows: fh.write(json.dumps(r, separators=(',', ':')) + '\n')
        self.done.add(k); self.n += 1
        if self.n % 25 == 0: self.save_done(); print(f"[bulk {sport}] {when:%Y-%m-%d %H}Z {len(rows)} games | {self.n} snapshots, {self.spent} credits, {left} left, {time.time() - self.t0:.0f}s", flush=True)
        time.sleep(0.4)
        return True

    def probe(self, key, when):
        """1 credit: are there games starting in the next 14h? (irregular calendars)"""
        d, used, left = get(f"{API}/historical/sports/{key}/events?apiKey={KEY}&date={when:%Y-%m-%dT%H:%M:%SZ}"); self.spent += used
        return [e for e in (d or {}).get('data') or [] if when <= dt.datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00')) <= when + dt.timedelta(hours=14)]


def slot_times(day, slots):
    return [dt.datetime.combine(day + dt.timedelta(days=1 if h < 12 else 0), dt.time(h, 0), dt.timezone.utc) for h in slots]


def run_plan(plan, budget):
    R = Run(budget, plan)
    if plan in PLANS:
        key, markets, seasons, slots, probe = PLANS[plan]
        for a, b in seasons:
            day = a
            while day <= b:
                if probe:
                    # one probe at the day's first slot; skip the whole day when nothing starts in the next 24h
                    w0 = slot_times(day, slots)[0]
                    if f"{plan}|{key}|{w0:%Y-%m-%dT%H%M}" not in R.done:
                        ev = R.probe(key, w0 - dt.timedelta(hours=1))
                        ev2 = [] if ev else R.probe(key, w0 + dt.timedelta(hours=8))
                        if not ev and not ev2:
                            for w in slot_times(day, slots): R.done.add(f"{plan}|{key}|{w:%Y-%m-%dT%H%M}")
                            day += dt.timedelta(days=1); continue
                for w in slot_times(day, slots):
                    if not R.snap(plan, key, markets, w): R.save_done(); print(f"[bulk {plan}] budget reached"); return
                day += dt.timedelta(days=1)
    elif plan == 'soccer':
        for lg, key in SOCCER.items():
            for a, b in SOCCER_SEASONS:
                day = a
                while day <= b:
                    w0 = dt.datetime.combine(day, dt.time(10, 0), dt.timezone.utc)
                    if f"soccer|{key}|{w0:%Y-%m-%dT%H%M}" not in R.done:
                        ev = R.probe(key, w0)
                        if not ev:
                            for w in slot_times(day, SOCCER_SLOTS): R.done.add(f"soccer|{key}|{w:%Y-%m-%dT%H%M}")
                            day += dt.timedelta(days=1); continue
                    for w in slot_times(day, SOCCER_SLOTS):
                        if not R.snap('soccer', key, 'h2h,spreads,totals', w): R.save_done(); print('[bulk soccer] budget reached'); return
                    day += dt.timedelta(days=1)
            R.save_done(); print(f"[bulk soccer] {lg} done, {R.spent} credits", flush=True)
    elif plan == 'tennis':
        for key, (a, b) in TENNIS_2026.items():
            for yrs in (4, 3, 2, 1):
                d0 = D.fromisoformat(a).replace(year=D.fromisoformat(a).year - yrs) - dt.timedelta(days=7); d1 = D.fromisoformat(b).replace(year=D.fromisoformat(b).year - yrs) + dt.timedelta(days=7)
                day = d0
                while day <= d1:
                    for h in (12, 22):
                        w = dt.datetime.combine(day, dt.time(h, 0), dt.timezone.utc); k = f"tennis|{key}|{w:%Y-%m-%dT%H%M}"
                        if k in R.done: continue
                        if not R.probe(key, w): R.done.add(k); continue
                        if not R.snap('tennis', key, 'h2h', w): R.save_done(); print('[bulk tennis] budget reached'); return
                    day += dt.timedelta(days=1)
            R.save_done()
    R.save_done(); print(f"[bulk {plan}] done: {R.n} snapshots, {R.spent} credits, {R.left} left")


if __name__ == '__main__':
    plan = sys.argv[1]; budget = int(sys.argv[sys.argv.index('--budget') + 1]) if '--budget' in sys.argv else 600000
    run_plan(plan, budget)
