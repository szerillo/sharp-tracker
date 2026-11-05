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
    'nba': ('basketball_nba', 'h2h,spreads,totals', [(D(2020, 12, 22), D(2021, 7, 21)), (D(2021, 10, 19), D(2022, 6, 17)), (D(2022, 10, 18), D(2023, 6, 13)), (D(2023, 10, 24), D(2024, 6, 20)), (D(2024, 10, 22), D(2025, 6, 25)), (D(2025, 10, 21), D(2026, 6, 25))], [15, 23, 0, 1, 2, 3], False),
    'nhl': ('icehockey_nhl', 'h2h,spreads,totals', [(D(2021, 1, 13), D(2021, 7, 8)), (D(2021, 10, 12), D(2022, 6, 27)), (D(2022, 10, 7), D(2023, 6, 14)), (D(2023, 10, 10), D(2024, 6, 25)), (D(2024, 10, 4), D(2025, 6, 20)), (D(2025, 10, 7), D(2026, 6, 20))], [15, 23, 0, 1, 2, 3], False),
    'cbb': ('basketball_ncaab', 'h2h,spreads,totals', [(D(2020, 11, 25), D(2021, 4, 6)), (D(2021, 11, 9), D(2022, 4, 5)), (D(2022, 11, 7), D(2023, 4, 4)), (D(2023, 11, 6), D(2024, 4, 9)), (D(2024, 11, 4), D(2025, 4, 8)), (D(2025, 11, 3), D(2026, 4, 7))], [15, 23, 0, 1, 2, 3], False),
    'nfl': ('americanfootball_nfl', 'h2h,spreads,totals', [(D(2020, 9, 9), D(2021, 2, 8)), (D(2021, 9, 8), D(2022, 2, 14)), (D(2022, 9, 7), D(2023, 2, 13)), (D(2023, 9, 6), D(2024, 2, 12)), (D(2024, 9, 4), D(2025, 2, 10)), (D(2025, 9, 3), D(2026, 2, 9))], [15, 17, 20, 0, 1], True),
    'cfb': ('americanfootball_ncaaf', 'h2h,spreads,totals', [(D(2020, 9, 3), D(2021, 1, 12)), (D(2021, 8, 26), D(2022, 1, 11)), (D(2022, 8, 25), D(2023, 1, 10)), (D(2023, 8, 24), D(2024, 1, 9)), (D(2024, 8, 24), D(2025, 1, 21)), (D(2025, 8, 23), D(2026, 1, 20))], [15, 16, 19, 23, 0, 3], True),
    'mma': ('mma_mixed_martial_arts', 'h2h,totals', [(D(2022, 1, 1), D(2025, 12, 31))], [22, 2], True),
    # phase 2 (Sean, 11/4: "if credits are left over: MLB, WNBA, futures, whatever else"; no motorsport on the API)
    'mlb': ('baseball_mlb', 'h2h,spreads,totals', [(D(2020, 7, 23), D(2020, 10, 28)), (D(2021, 4, 1), D(2021, 11, 3)), (D(2022, 4, 7), D(2022, 11, 6)), (D(2023, 3, 30), D(2023, 11, 2)), (D(2024, 3, 20), D(2024, 10, 31)), (D(2025, 3, 27), D(2025, 11, 2))], [15, 17, 18, 22, 23, 0, 2], False),
    'wnba': ('basketball_wnba', 'h2h,spreads,totals', [(D(2021, 5, 14), D(2021, 10, 18)), (D(2022, 5, 6), D(2022, 9, 19)), (D(2023, 5, 19), D(2023, 10, 19)), (D(2024, 5, 14), D(2024, 10, 21)), (D(2025, 5, 16), D(2025, 10, 18))], [15, 23, 0, 2, 3], True),
    'cfl': ('americanfootball_cfl', 'h2h,spreads,totals', [(D(2021, 8, 5), D(2021, 12, 13)), (D(2022, 6, 9), D(2022, 11, 21)), (D(2023, 6, 8), D(2023, 11, 20)), (D(2024, 6, 6), D(2024, 11, 18)), (D(2025, 6, 5), D(2025, 11, 17))], [15, 23, 0, 2], True),
    'kbo': ('baseball_kbo', 'h2h,spreads,totals', [(D(2023, 4, 1), D(2023, 11, 15)), (D(2024, 3, 23), D(2024, 11, 1)), (D(2025, 3, 22), D(2025, 11, 1))], [8, 9, 10], True),
    'npb': ('baseball_npb', 'h2h,spreads,totals', [(D(2023, 3, 30), D(2023, 11, 6)), (D(2024, 3, 29), D(2024, 11, 4)), (D(2025, 3, 28), D(2025, 11, 3))], [3, 8, 9, 10], True),
    'boxing': ('boxing_boxing', 'h2h', [(D(2022, 1, 1), D(2025, 12, 31))], [22, 2], True),
    'wncaab': ('basketball_wncaab', 'h2h,spreads,totals', [(D(2021, 11, 9), D(2022, 4, 4)), (D(2022, 11, 7), D(2023, 4, 3)), (D(2023, 11, 6), D(2024, 4, 8)), (D(2024, 11, 4), D(2025, 4, 7)), (D(2025, 11, 3), D(2026, 4, 6))], [15, 23, 0, 1, 2, 3], True),
    'euroleague': ('basketball_euroleague', 'h2h,spreads,totals', [(D(2021, 9, 30), D(2022, 5, 22)), (D(2022, 9, 29), D(2023, 5, 22)), (D(2023, 10, 5), D(2024, 5, 27)), (D(2024, 10, 3), D(2025, 5, 26)), (D(2025, 9, 30), D(2026, 5, 25))], [15, 17, 18, 19, 20], True),
    'milb': ('baseball_milb', 'h2h,spreads,totals', [(D(2021, 5, 4), D(2021, 10, 3)), (D(2022, 4, 5), D(2022, 10, 2)), (D(2023, 3, 31), D(2023, 10, 1)), (D(2024, 3, 29), D(2024, 9, 29)), (D(2025, 3, 28), D(2025, 9, 28))], [15, 22, 23, 0, 2], True),
    'ncaa_baseball': ('baseball_ncaa', 'h2h,spreads,totals', [(D(2022, 2, 18), D(2022, 6, 27)), (D(2023, 2, 17), D(2023, 6, 26)), (D(2024, 2, 16), D(2024, 6, 25)), (D(2025, 2, 14), D(2025, 6, 23))], [15, 17, 19, 22, 0, 2], True),
}
CUPS = {'fa_cup': 'soccer_fa_cup', 'efl_cup': 'soccer_england_efl_cup', 'copa_del_rey': 'soccer_spain_copa_del_rey', 'coppa_italia': 'soccer_italy_coppa_italia', 'dfb_pokal': 'soccer_germany_dfb_pokal',
        'coupe_de_france': 'soccer_france_coupe_de_france', 'club_world_cup': 'soccer_fifa_club_world_cup', 'copa_america': 'soccer_conmebol_copa_america', 'euros_qual': 'soccer_uefa_champs_league_qualification'}
# 11/5 (Sean: "as accurate a database as possible"): the Bet Labs reconciliation showed our first snapshot is the morning of the game for
# the daily sports (lines post overnight after the previous night's games), so "open to close" was a same-day move. These plans add the
# overnight and midday snapshots (06, 09, 12, 18, 21 UTC) for the same seasons; odds_db folds plan 'nba2' into sport 'nba'.
# Credits: 449k left on 11/5 after the main backfill, so two extra slots (06 and 12 UTC, ~30 credits each) for the five core sports (~300k).
for _sp in ('nba', 'nhl', 'cbb', 'mlb', 'cfb', 'wnba', 'wncaab', 'euroleague'):
    _k, _m, _seasons, _slots, _probe = PLANS[_sp]
    PLANS[_sp + '2'] = (_k, _m, _seasons, [6, 12], _probe)

SOCCER3 = {'ligue1': 'soccer_france_ligue_one', 'eredivisie': 'soccer_netherlands_eredivisie', 'portugal': 'soccer_portugal_primeira_liga', 'efl_champ': 'soccer_efl_champ',
           'libertadores': 'soccer_conmebol_copa_libertadores', 'brazil': 'soccer_brazil_campeonato', 'argentina': 'soccer_argentina_primera_division', 'turkey': 'soccer_turkey_super_league'}
# futures: one snapshot a week (Tuesday 15:00 UTC) 2021-2026; outright markets cost 10 a snapshot
FUTURES = {'nba_champ': 'basketball_nba_championship_winner', 'nfl_sb': 'americanfootball_nfl_super_bowl_winner', 'nhl_cup': 'icehockey_nhl_championship_winner',
           'mlb_ws': 'baseball_mlb_world_series_winner', 'cbb_champ': 'basketball_ncaab_championship_winner', 'cfb_champ': 'americanfootball_ncaaf_championship_winner',
           'world_cup': 'soccer_fifa_world_cup_winner', 'masters': 'golf_masters_tournament_winner', 'pga': 'golf_pga_championship_winner', 'open': 'golf_the_open_championship_winner', 'us_open_golf': 'golf_us_open_winner'}
SOCCER = {'epl': 'soccer_epl', 'laliga': 'soccer_spain_la_liga', 'seriea': 'soccer_italy_serie_a', 'ucl': 'soccer_uefa_champs_league', 'mls': 'soccer_usa_mls', 'ligamx': 'soccer_mexico_ligamx'}
SOCCER2 = {'europa': 'soccer_uefa_europa_league', 'bundesliga': 'soccer_germany_bundesliga', 'worldcup': 'soccer_fifa_world_cup'}   # 11/4: added; own plan and file so it can run beside the first
SOCCER_SEASONS = [(D(2020, 9, 1), D(2021, 6, 5)), (D(2021, 8, 1), D(2022, 6, 5)), (D(2022, 8, 1), D(2023, 6, 12)), (D(2023, 8, 1), D(2024, 6, 5)), (D(2024, 8, 1), D(2025, 6, 5)), (D(2025, 7, 15), D(2026, 6, 5))]
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
    elif plan in ('soccer', 'soccer2', 'soccer3', 'cups'):
        for lg, key in (SOCCER if plan == 'soccer' else SOCCER2 if plan == 'soccer2' else SOCCER3 if plan == 'soccer3' else CUPS).items():
            for a, b in ([(D(2022, 11, 18), D(2022, 12, 20))] if lg == 'worldcup' else SOCCER_SEASONS):
                day = a
                while day <= b:
                    w0 = dt.datetime.combine(day, dt.time(10, 0), dt.timezone.utc)
                    if f"{plan}|{key}|{w0:%Y-%m-%dT%H%M}" not in R.done:
                        ev = R.probe(key, w0)
                        if not ev:
                            for w in slot_times(day, SOCCER_SLOTS): R.done.add(f"{plan}|{key}|{w:%Y-%m-%dT%H%M}")
                            day += dt.timedelta(days=1); continue
                    for w in slot_times(day, SOCCER_SLOTS):
                        if not R.snap(plan, key, 'h2h,spreads,totals', w): R.save_done(); print(f'[bulk {plan}] budget reached'); return
                    day += dt.timedelta(days=1)
            R.save_done(); print(f"[bulk {plan}] {lg} done, {R.spent} credits", flush=True)
    elif plan == 'futures':
        for name, key in FUTURES.items():
            day = D(2021, 6, 1)
            while day <= D(2026, 11, 3):
                if day.weekday() == 1:
                    w = dt.datetime.combine(day, dt.time(15, 0), dt.timezone.utc); k = f"futures|{key}|{w:%Y-%m-%dT%H%M}"
                    if k not in R.done:
                        d, used, left = get(f"{API}/historical/sports/{key}/odds/?apiKey={KEY}&bookmakers={BOOKS}&markets=outrights&oddsFormat=decimal&date={w:%Y-%m-%dT%H:%M:%SZ}")
                        R.spent += used; R.left = left; R.done.add(k)
                        if d and d.get('data'):
                            with gzip.open(os.path.join(OUT, 'futures.jsonl.gz'), 'at') as fh:
                                for g in d['data']:
                                    B = {b['key']: {o['name']: o.get('price') for m in b.get('markets') or [] for o in m.get('outcomes') or []} for b in g.get('bookmakers') or []}
                                    fh.write(json.dumps(dict(t=d.get('timestamp'), id=g['id'], sport='futures', key=key, name=name, start=g.get('commence_time'), title=g.get('home_team') or g.get('sport_title'), books=B), separators=(',', ':')) + '\n')
                            R.n += 1
                        time.sleep(0.4)
                        if R.spent + 20 > R.budget: R.save_done(); print('[bulk futures] budget reached'); return
                day += dt.timedelta(days=1)
            R.save_done(); print(f"[bulk futures] {name} done, {R.spent} credits", flush=True)
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
