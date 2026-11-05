#!/usr/bin/env python3
"""Tennis and MMA historical snapshots from The Odds API (Sean, 11/4: backtest tennis and MMA against real closes). The API lists tennis
per event (Masters, 500s, slams; no 250s), so this walks each event's window a day at a time: a 1-credit events probe first, then the
10-credit odds snapshot (moneyline, Pinnacle + US books) only on days with matches listed. Two snapshots a day (12:00Z for the
European day session and the US morning line, 22:00Z for US evening sessions); the analysis takes the last one before each match.
MMA: one card a week, snapshots Saturday 22:00Z and Sunday 02:00Z (prelims / main card), moneyline + rounds total.
Files: data/oddsapi/tennis/<key>/<ts>.json.gz, data/oddsapi/mma/<ts>.json.gz. Key in ODDS_API_KEY.
Usage: ODDS_API_KEY=... python3 loggers/oddsapi_tennis.py tennis|mma [--budget 3000]"""
import os, sys, json, gzip, time, datetime as dt, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'data', 'oddsapi'); API = "https://api.the-odds-api.com/v4"; KEY = os.environ.get('ODDS_API_KEY')
BOOKS = 'pinnacle,draftkings,fanduel,williamhill_us,betmgm,betonlineag,lowvig'
# 2026 windows (Tennis Abstract tourney dates through June; the ATP / WTA calendar after): key -> (first day, last day)
TENNIS = {
    'tennis_atp_aus_open_singles': ('2026-01-18', '2026-02-01'), 'tennis_wta_aus_open_singles': ('2026-01-18', '2026-02-01'),
    'tennis_atp_qatar_open': ('2026-02-16', '2026-02-22'), 'tennis_wta_qatar_open': ('2026-02-08', '2026-02-15'),
    'tennis_atp_dubai': ('2026-02-23', '2026-03-01'), 'tennis_wta_dubai': ('2026-02-15', '2026-02-22'),
    'tennis_atp_indian_wells': ('2026-03-04', '2026-03-16'), 'tennis_wta_indian_wells': ('2026-03-04', '2026-03-16'),
    'tennis_atp_miami_open': ('2026-03-18', '2026-03-30'), 'tennis_wta_miami_open': ('2026-03-17', '2026-03-29'),
    'tennis_wta_charleston_open': ('2026-03-30', '2026-04-06'), 'tennis_atp_monte_carlo_masters': ('2026-04-05', '2026-04-13'),
    'tennis_atp_barcelona_open': ('2026-04-13', '2026-04-20'), 'tennis_atp_munich': ('2026-04-13', '2026-04-20'), 'tennis_wta_stuttgart_open': ('2026-04-13', '2026-04-20'),
    'tennis_atp_madrid_open': ('2026-04-22', '2026-05-04'), 'tennis_wta_madrid_open': ('2026-04-21', '2026-05-03'),
    'tennis_atp_italian_open': ('2026-05-06', '2026-05-18'), 'tennis_wta_italian_open': ('2026-05-05', '2026-05-17'),
    'tennis_atp_hamburg_open': ('2026-05-17', '2026-05-24'), 'tennis_atp_french_open': ('2026-05-24', '2026-06-08'), 'tennis_wta_french_open': ('2026-05-24', '2026-06-07'),
    'tennis_atp_halle_open': ('2026-06-15', '2026-06-22'), 'tennis_atp_queens_club_champ': ('2026-06-15', '2026-06-22'), 'tennis_wta_german_open': ('2026-06-15', '2026-06-22'),
    'tennis_wta_bad_homburg_open': ('2026-06-21', '2026-06-28'), 'tennis_atp_wimbledon': ('2026-06-29', '2026-07-13'), 'tennis_wta_wimbledon': ('2026-06-29', '2026-07-12'),
    'tennis_atp_washington_open': ('2026-07-27', '2026-08-03'), 'tennis_wta_washington_open': ('2026-07-27', '2026-08-03'),
    'tennis_atp_canadian_open': ('2026-07-25', '2026-08-08'), 'tennis_wta_canadian_open': ('2026-07-25', '2026-08-08'),
    'tennis_atp_cincinnati_open': ('2026-08-06', '2026-08-18'), 'tennis_wta_cincinnati_open': ('2026-08-06', '2026-08-18'),
    'tennis_atp_us_open': ('2026-08-24', '2026-09-14'), 'tennis_wta_us_open': ('2026-08-24', '2026-09-13'),
    'tennis_wta_guadalajara_open': ('2026-09-07', '2026-09-14'), 'tennis_atp_japan_open': ('2026-09-23', '2026-09-30'), 'tennis_atp_china_open': ('2026-09-23', '2026-10-06'),
    'tennis_wta_china_open': ('2026-09-23', '2026-10-06'), 'tennis_atp_shanghai_masters': ('2026-10-01', '2026-10-13'),
    'tennis_atp_vienna_open': ('2026-10-19', '2026-10-26'), 'tennis_atp_swiss_indoors': ('2026-10-19', '2026-10-26'), 'tennis_atp_paris_masters': ('2026-10-26', '2026-11-02'),
}


def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=60) as r:
                return json.load(r), int(r.headers.get('x-requests-last') or 0), int(r.headers.get('x-requests-remaining') or 0)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(5 * (i + 1)); continue
            if e.code in (404, 422): return None, 0, None
            time.sleep(2)
        except Exception: time.sleep(2)
    return None, 0, None


def snap(path, sport_key, when, markets):
    if os.path.exists(path): return 0, None
    d, used, left = get(f"{API}/historical/sports/{sport_key}/odds/?apiKey={KEY}&bookmakers={BOOKS}&markets={markets}&oddsFormat=decimal&date={when:%Y-%m-%dT%H:%M:%SZ}")
    if d is None: return used, left
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, 'wt') as fh: json.dump(d, fh, separators=(',', ':'))
    print(f"[oddsapi] {sport_key} {when:%Y-%m-%d %H:%M}Z: {len(d.get('data') or [])} matches, cost {used}, left {left}", flush=True)
    return used, left


def tennis(budget):
    spent = 0
    for key, (a, b) in TENNIS.items():
        d = dt.date.fromisoformat(a); end = dt.date.fromisoformat(b)
        while d <= end:
            for h in (12, 22):
                when = dt.datetime.combine(d, dt.time(h, 0), dt.timezone.utc)
                p = os.path.join(OUT, 'tennis', key, when.strftime('%Y-%m-%dT%H%M') + '.json.gz')
                if os.path.exists(p): continue
                if spent + 11 > budget: print(f"[oddsapi] budget reached at {spent}"); return
                ev, u1, _ = get(f"{API}/historical/sports/{key}/events?apiKey={KEY}&date={when:%Y-%m-%dT%H:%M:%SZ}"); spent += u1
                # only matches starting in the next 14 hours are worth a snapshot (the next one covers the rest)
                soon = [e for e in (ev or {}).get('data') or [] if when <= dt.datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00')) <= when + dt.timedelta(hours=14)]
                if not soon:
                    with gzip.open(p, 'wt') as fh: json.dump(dict(timestamp=None, data=[]), fh)   # remember the empty day
                    continue
                u, _ = snap(p, key, when, 'h2h'); spent += u
                time.sleep(0.2)
            d += dt.timedelta(days=1)
    print(f"[oddsapi] tennis done, {spent} credits")


def mma(budget):
    spent = 0; d = dt.date(2026, 1, 3)
    while d <= dt.date(2026, 11, 1):
        if d.weekday() == 5:
            for when in (dt.datetime.combine(d, dt.time(22, 0), dt.timezone.utc), dt.datetime.combine(d + dt.timedelta(days=1), dt.time(2, 0), dt.timezone.utc)):
                p = os.path.join(OUT, 'mma', when.strftime('%Y-%m-%dT%H%M') + '.json.gz')
                if spent + 20 > budget: print(f"[oddsapi] budget reached at {spent}"); return
                u, _ = snap(p, 'mma_mixed_martial_arts', when, 'h2h,totals'); spent += u
        d += dt.timedelta(days=1)
    print(f"[oddsapi] mma done, {spent} credits")


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'tennis'
    budget = int(sys.argv[sys.argv.index('--budget') + 1]) if '--budget' in sys.argv else 3000
    (tennis if what == 'tennis' else mma)(budget)
