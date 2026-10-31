#!/usr/bin/env python3
"""MySportsWeather (Kevin Roth, NWS/NBM data) as a second kickoff-weather source: python3 loggers/msw_weather.py --sport nfl|cfb|mlb
Parses the public list pages (NFL: in-page match sections; NCAAF/MLB: one page per game) into data/<sport>/weather/msw.jsonl:
  ts, date, kickoff_et, away, home, venue, temp_f, wind_mph (at kickoff), gust_mph, wind_dir, rain_pct, hourly [{h, precip, temp, wind, gust, dir}],
  event_id (ESPN, matched through data/<sport>/schedule.json by team codes + date).
Read-only; the site has no API, so this is plain HTML parsing of server-rendered pages and may need updating if the markup changes."""
import os, sys, re, json, time, html, datetime as dt, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
from sharp.norm import iso, et_date, parse_ts

ARGS = sys.argv[1:]; SPORT = ARGS[ARGS.index('--sport') + 1] if '--sport' in ARGS else 'nfl'
PATH = {'nfl': '/nfl', 'cfb': '/ncaaf', 'mlb': '/mlb'}[SPORT]; BASE = 'https://mysportsweather.com'
OUT = os.path.join(HERE, '..', 'data', SPORT, 'weather'); os.makedirs(OUT, exist_ok=True)
NOW = dt.datetime.now(dt.timezone.utc); TS = iso(NOW); T0 = time.time(); BUDGET = 240
FIX = {'nfl': {'JAC': 'JAX', 'LA': 'LAR', 'WAS': 'WSH'}, 'cfb': {}, 'mlb': {'CHW': 'CWS', 'WAS': 'WSH', 'AZ': 'ARI', 'OAK': 'ATH'}}[SPORT]


def get(path):
    if time.time() - T0 > BUDGET: return ''
    try: return urllib.request.urlopen(urllib.request.Request(BASE + path, headers={'User-Agent': 'Mozilla/5.0 (sharp-tracker weather cross-check)'}), timeout=25).read().decode(errors='replace')
    except Exception: return ''


def text(seg):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', seg, flags=re.S); t = re.sub(r'<[^>]+>', ' ', t)
    return html.unescape(re.sub(r'\s+', ' ', t)).strip()


def parse_block(t):
    """'... 51° At kickoff 0% Rain 6 mph Wind 7 PM 8 PM ... Precip 0% ... Temp 53° ... Wind 7 mph ... Gusts 16 mph ... Wind dir WNW ...'
    or the game-page form '79 °F At kickoff 14 mph wind E · Gusts 25 89% Rain chance'."""
    r = {}
    m = re.search(r'(-?\d+)\s*°\s*F?\s*At kickoff', t); r['temp_f'] = float(m.group(1)) if m else None
    m = re.search(r'At kickoff.*?(\d+)\s*mph', t); r['wind_mph'] = float(m.group(1)) if m else None
    m = re.search(r'At kickoff.*?Gusts\s*(\d+)', t); r['gust_mph'] = float(m.group(1)) if m else None
    m = re.search(r'At kickoff.*?mph wind ([NESW]{1,3})', t); r['wind_dir'] = m.group(1) if m else None
    m = re.search(r'(\d+)%\s*Rain', t); r['rain_pct'] = float(m.group(1)) if m else None
    hours = re.findall(r'\b(\d{1,2} [AP]M)\b', t.split('Precip')[0][-120:]) if 'Precip' in t else []
    def row(label, unit=''):
        mm = re.search(label + r'((?:\s*-?\d+' + unit + r')+)', t); return [float(x) for x in re.findall(r'-?\d+', mm.group(1))] if mm else []
    pr, tp, wd, gs = row('Precip', '%'), row('Temp', '°'), row(r'Wind(?! dir)', ' mph'), row('Gusts', ' mph')
    dm = re.search(r'Wind dir((?:\s+[NESW]{1,3})+)', t); dirs = dm.group(1).split() if dm else []
    r['hourly'] = [dict(h=hours[i] if i < len(hours) else None, precip=pr[i] if i < len(pr) else None, temp=tp[i] if i < len(tp) else None, wind=wd[i] if i < len(wd) else None,
                        gust=gs[i] if i < len(gs) else None, dir=dirs[i] if i < len(dirs) else None) for i in range(max(len(hours), len(wd)))]
    if r['wind_mph'] is None and wd: r['wind_mph'] = wd[min(1, len(wd) - 1)]
    if r['gust_mph'] is None and gs: r['gust_mph'] = gs[min(1, len(gs) - 1)]
    if r['wind_dir'] is None and dirs: r['wind_dir'] = dirs[min(1, len(dirs) - 1)]
    m = re.search(r'Kickoff\s*·?\s*(\d{1,2}:\d\d [AP]M ET)', t) or re.search(r'First pitch\s*·?\s*(\d{1,2}:\d\d [AP]M ET)', t); r['kickoff_et'] = m.group(1) if m else None
    m = re.search(r'at .*? ((?:[A-Z][\w.&\' -]+?)(?: Stadium| Field| Park| Dome| Coliseum| Bowl| Center| Arena)[^·]*?) ·', t); r['venue'] = m.group(1).strip() if m else None
    return r


def cards(page):
    out = []
    for c in re.findall(r'<a href="([^"]+)" class="cheat-card[^"]*"([^>]*)>(.*?)</a>', page, flags=re.S):
        href, attrs, seg = c; ab = re.findall(r'cheat-card__abbr[^"]*">([A-Z0-9&]+)<', seg); date = re.search(r'cheat-card__date">(\d+/\d+)<', seg); tm = re.search(r'cheat-card__time">([^<]+)<', seg)
        if len(ab) != 2: continue
        ko = re.search(r'data-sort-kickoff="([^"]+)"', attrs); d = None
        if ko: d = et_date(parse_ts(ko.group(1)))
        elif date:
            mo, dd = date.group(1).split('/'); d = dt.date(NOW.year + (1 if int(mo) < NOW.month - 6 else 0), int(mo), int(dd))
        extra = {k: float(v) for k, v in re.findall(r'data-sort-(wind|total|movement|rain)="([-\d.]+)"', attrs)}
        out.append(dict(href=href, away=FIX.get(ab[0], ab[0]), home=FIX.get(ab[1], ab[1]), date=d.isoformat() if d else None, time=tm.group(1) if tm else None, card=extra or None))
    return out


def main():
    page = get(PATH); rows = []
    sched = json.load(open(os.path.join(HERE, '..', 'data', SPORT, 'schedule.json'))) if os.path.exists(os.path.join(HERE, '..', 'data', SPORT, 'schedule.json')) else {}
    byk = {}
    for eid, e in sched.items():
        if e.get('away') and e.get('home'): byk[(et_date(parse_ts(e['start'])).isoformat(), e['away'], e['home'])] = eid
    for c in cards(page):
        if c['href'].startswith('#'):
            m = re.search(r'id="%s"(.*?)(?=<section|id="match-|</main>)' % re.escape(c['href'][1:]), page, flags=re.S); t = text(m.group(0)) if m else ''
        else:
            t = text(get(c['href']))
        if not t: continue
        r = parse_block(t); r.update(ts=TS, source='mysportsweather', **{k: c[k] for k in ('away', 'home', 'date', 'time')})
        if c.get('card'):
            r['card'] = c['card']
            if r.get('wind_mph') is None and c['card'].get('wind') is not None: r['wind_mph'] = c['card']['wind']
        r['event_id'] = byk.get((c['date'], c['away'], c['home']))
        if not r['event_id'] and c['date']:      # abbreviation drift (AF vs AFA, MRSH vs MAR): same date, one side exact, other side shares a prefix
            cands = [(k, v) for k, v in byk.items() if k[0] == c['date'] and ((k[1] == c['away'] and (k[2][:2] == c['home'][:2] or c['home'][:2] == k[2][:2])) or (k[2] == c['home'] and k[1][:2] == c['away'][:2]))]
            if not cands:    # a team plays once a day: one side exact on the date is enough (UA vs ARIZ, NW vs NU, IND vs IU, UW vs WASH ...)
                cands = [(k, v) for k, v in byk.items() if k[0] == c['date'] and (k[1] == c['away'] or k[2] == c['home'])]
            if len(cands) == 1: r['event_id'] = cands[0][1]; r['match'] = 'fuzzy'
        rows.append(r)
    with open(os.path.join(OUT, 'msw.jsonl'), 'a') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    n_m = sum(1 for r in rows if r.get('event_id')); n_w = sum(1 for r in rows if r.get('wind_mph') is not None)
    print(f"[msw {SPORT}] {len(rows)} games, {n_w} with kickoff wind, {n_m} matched to ESPN; " + ', '.join(f"{r['away']}@{r['home']} {r['wind_mph']}mph" for r in rows if (r.get('wind_mph') or 0) >= 10))


if __name__ == '__main__':
    main()
