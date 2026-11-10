#!/usr/bin/env python3
"""Boxing results from Wikipedia professional-record tables (Sean 11/9: is boxing beatable? ESPN has no boxing).
For every fight in data/oddsapi/compact/boxing.jsonl.gz: find each fighter's Wikipedia page (title, then a 'NAME boxer' search; a page
counts only if it has a professional boxing record), find the row whose opponent surname appears and whose date is within a day of the
fight, and read Win / Loss / Draw / NC from that row. Either fighter's page settles it; when both have the row they must agree.
Output data/boxing/results.json: {odds_api_id: {"winner": "home"|"away"|"draw"|"nc", "src": page, "date": ...}}. Resumable (page cache
in data/boxing/wiki_cache.json.gz). Runs on a GitHub runner (Wikipedia is not reachable from the analysis container).
Usage: python3 loggers/boxing_results.py [max_minutes]"""
import os, sys, json, gzip, re, time, unicodedata, datetime as dt, urllib.request, urllib.parse
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.join(ROOT, 'data', 'oddsapi', 'compact', 'boxing.jsonl.gz')
OUT = os.path.join(ROOT, 'data', 'boxing', 'results.json')
CACHE = os.path.join(ROOT, 'data', 'boxing', 'wiki_cache.json.gz')
UA = 'sharp-tracker research bot (github.com/szerillo/sharp-tracker)'
API = 'https://en.wikipedia.org/w/api.php'
MAXMIN = float(sys.argv[1]) if len(sys.argv) > 1 else 100


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z ]', ' ', s)


def api(params):
    q = API + '?' + urllib.parse.urlencode(dict(params, format='json', formatversion=2))
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers={'User-Agent': UA}), timeout=30) as r: return json.load(r)
        except Exception: time.sleep(2 + 3 * i)
    return None


def wikitext(title):
    d = api(dict(action='parse', page=title, prop='wikitext', redirects=1))
    return ((d or {}).get('parse') or {}).get('wikitext') or ''


def is_boxer(t): return 'professional boxing record' in t.lower() or 'boxing record' in t.lower()


def page_for(name, cache):
    if name in cache: return cache[name]
    t = wikitext(name); title = name
    if not is_boxer(t):
        s = api(dict(action='query', list='search', srsearch=f'{name} boxer', srlimit=3)) or {}
        t = ''; title = None
        for hit in ((s.get('query') or {}).get('search') or []):
            x = wikitext(hit['title'])
            # the page must be about this fighter: his surname in the title
            if is_boxer(x) and norm(name).split()[-1] in norm(hit['title']): t, title = x, hit['title']; break
    # keep only the record section to keep the cache small
    i = t.lower().find('boxing record')
    cache[name] = (title, t[i:i + 120000] if i >= 0 else '')
    time.sleep(0.15)
    return cache[name]


MON = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']


def date_keys(d):
    out = set()
    for k in (-1, 0, 1):
        x = d + dt.timedelta(days=k); m = MON[x.month - 1]
        out |= {f'{m} {x.day} {x.year}', f'{x.day} {m} {x.year}', f'{x.year}|{x.month:02d}|{x.day:02d}', f'{x.year}|{x.month}|{x.day}',
                f'{x.year}-{x.month:02d}-{x.day:02d}'}
    return out


def row_norm(r):
    r = r.lower(); r = re.sub(r'(january|february|march|april|june|july|august|september|october|november|december)', lambda m: m.group(1)[:3], r)
    r = r.replace('sept', 'sep'); r = re.sub(r'[,\.]', ' ', r); r = re.sub(r'\s+', ' ', r)
    return r


def find(text, opp, d):
    sur = norm(opp).split()
    if not sur: return None
    sur = sur[-1]; keys = date_keys(d)
    for row in re.split(r'\n\|-', text):
        rn = row_norm(row)
        if sur not in norm(row): continue
        if not any(k in rn for k in keys): continue
        m = re.search(r'\b(win|loss|draw|nc|no contest)\b', rn)
        if m: return {'win': 'W', 'loss': 'L', 'draw': 'D', 'nc': 'NC', 'no contest': 'NC'}[m.group(1)]
    return None


def save_cache(cache):
    # 11/9: a snapshot (the page threads keep adding while this runs), written to a temp file and closed before it replaces the old one
    tmp = CACHE + '.tmp'
    with gzip.open(tmp, 'wt') as f: json.dump(dict(cache), f)
    os.replace(tmp, CACHE)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fights = {}
    for l in gzip.open(SRC, 'rt'):
        try: x = json.loads(l)
        except Exception: continue
        fights[x['id']] = (x['home'], x['away'], x['start'])
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    cache = {}
    if os.path.exists(CACHE):
        try: cache = json.load(gzip.open(CACHE, 'rt'))
        except Exception as e: print(f'[boxing_results] cache unreadable ({e}), starting fresh', flush=True)
    t0 = time.time(); n = 0
    todo = [k for k in fights if k not in res and dt.datetime.fromisoformat(fights[k][2].replace('Z', '+00:00')) < dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)]
    print(f'[boxing_results] {len(fights)} fights, {len(res)} done, {len(todo)} to look up', flush=True)
    # 11/9: one page at a time managed about 2 fights a minute; fetch every fighter's page first, 8 at a time
    import concurrent.futures as cf
    names = sorted({x for k in todo for x in fights[k][:2]} - set(cache))
    print(f'[boxing_results] fetching {len(names)} fighter pages', flush=True)
    with cf.ThreadPoolExecutor(8) as ex:
        for i, _ in enumerate(ex.map(lambda nm_: page_for(nm_, cache), names)):
            if i % 250 == 0: print(f'[boxing_results] pages {i}/{len(names)}', flush=True); save_cache(cache)
            if (time.time() - t0) / 60 > MAXMIN: break
    for k in todo:
        if (time.time() - t0) / 60 > MAXMIN: break
        h, a, s = fights[k]; d = dt.datetime.fromisoformat(s.replace('Z', '+00:00')).date()
        ph, th = page_for(h, cache); pa, ta = page_for(a, cache)
        rh = find(th, a, d) if th else None; ra = find(ta, h, d) if ta else None
        flip = {'W': 'L', 'L': 'W', 'D': 'D', 'NC': 'NC'}
        if rh and ra and rh != flip[ra]: res[k] = {'winner': 'conflict', 'home': rh, 'away': ra}; continue
        r = rh or (flip[ra] if ra else None)
        if r: res[k] = {'winner': {'W': 'home', 'L': 'away', 'D': 'draw', 'NC': 'nc'}[r], 'src': ph if rh else pa, 'date': s[:10]}
        else: res[k] = {'winner': None, 'pages': [bool(th), bool(ta)]}
        n += 1
        if n % 100 == 0:
            print(f'[boxing_results] {n} looked up, {sum(1 for v in res.values() if v.get("winner") in ("home", "away", "draw", "nc"))} settled', flush=True)
            json.dump(res, open(OUT, 'w')); save_cache(cache)
    json.dump(res, open(OUT, 'w')); save_cache(cache)
    c = {}
    for v in res.values(): c[str(v.get('winner'))] = c.get(str(v.get('winner')), 0) + 1
    print(f'[boxing_results] done: {len(res)} fights, {c}')


if __name__ == '__main__': main()
