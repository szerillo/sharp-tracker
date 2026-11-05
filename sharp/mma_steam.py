#!/usr/bin/env python3
"""MMA steam favourite (Sean, 11/5: "MMA system should be implemented regarding steam").
Rule (mma_steam_fav, tier C): Pinnacle's no-vig win probability for the favourite is 6+ points above Pinnacle's OPENING number for that
fighter; bet the favourite. Odds API replay 2022-26 (sharp/market_replay.py, 1,457 graded UFC fights): following a 6+ point move at the
close is 161-76 (+7.3%); toward the favourite 136-53 (+6.6%, positive 4 of 5 years); fading those moves -19.7%. Moves under 6 points are
priced by the close.

Open and current prices: The Odds API current-odds endpoint (10 credits a call, every signals run) -> data/mma/oddsapi_live.jsonl; the
open for an event is Pinnacle's first appearance, found once per new event by stepping the historical endpoint back a day at a time
(data/mma/oddsapi_open.json). Without ODDS_API_KEY (local runs) the Pinnacle feed in data/mma/ticks is used for both.
Price for the bet: best US book in the snapshot (no BetMGM) or Kalshi / Novig from our ticks, whichever is cheaper.
Paper log data/mma/steam_paper.jsonl, graded from ESPN (data/mma/schedule.json winner flags, then data/state/hist_schedule.json) ->
data/mma/steam_graded.json. View: data/state/mma_steam.json (rows, record)."""
import os, sys, json, glob, gzip, math, re, unicodedata, datetime as dt, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
MD = os.path.join(ROOT, 'data', 'mma'); LIVE = os.path.join(MD, 'oddsapi_live.jsonl'); OPEN = os.path.join(MD, 'oddsapi_open.json')
PAPER = os.path.join(MD, 'steam_paper.jsonl'); GRADED = os.path.join(MD, 'steam_graded.json'); OUT = os.path.join(ROOT, 'data', 'state', 'mma_steam.json')
KEY = os.environ.get('ODDS_API_KEY'); API = 'https://api.the-odds-api.com/v4'; SPORT = 'mma_mixed_martial_arts'
MOVE = 0.06; US = ('draftkings', 'fanduel', 'williamhill_us', 'betrivers', 'espnbet', 'fanatics'); KFEE = 0.07
NOW = dt.datetime.now(dt.timezone.utc); NOW_S = NOW.strftime('%Y-%m-%dT%H:%M:%SZ')


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z ]', ' ', s).split()


def same(a, b):
    """Fighter names match when the last tokens agree and a first token agrees (Odds API 'Jon Jones' vs ESPN 'Jonathan Jones' fails; rare)."""
    A, B = norm(a), norm(b)
    return bool(A and B) and A[-1] == B[-1] and (A[0] == B[0] or A[0][:3] == B[0][:3])


def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sharp-tracker'}), timeout=30) as r:
            return json.load(r), int(r.headers.get('x-requests-remaining') or 0)
    except Exception as e:
        print(f'[mma_steam] {e}'); return None, None


def nv(h, a):
    if not h or not a: return None
    q = 1 / h + 1 / a; return (1 / h) / q


def implied(am): return 100 / (am + 100) if am > 0 else -am / (-am + 100)


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def pin_row(ev):
    for b in ev.get('bookmakers') or []:
        if b['key'] != 'pinnacle': continue
        for m in b.get('markets') or []:
            if m['key'] == 'h2h':
                p = {x['name']: x.get('price') for x in m['outcomes']}
                if ev['home_team'] in p and ev['away_team'] in p: return p[ev['home_team']], p[ev['away_team']]
    return None


def snapshot():
    """Current Odds API MMA odds -> compact rows (appended to LIVE), returns the events."""
    if not KEY: return None
    d, left = get(f"{API}/sports/{SPORT}/odds?apiKey={KEY}&regions=us,eu&markets=h2h&oddsFormat=decimal")
    if not d: return None
    rows = []
    for ev in d:
        books = {}
        for b in ev.get('bookmakers') or []:
            for m in b.get('markets') or []:
                if m['key'] != 'h2h': continue
                p = {x['name']: x.get('price') for x in m['outcomes']}
                if ev['home_team'] in p and ev['away_team'] in p: books[b['key']] = [p[ev['home_team']], p[ev['away_team']]]
        if books: rows.append(dict(t=NOW_S, id=ev['id'], start=ev['commence_time'], home=ev['home_team'], away=ev['away_team'], books=books))
    os.makedirs(MD, exist_ok=True)
    with open(LIVE, 'a') as f:
        for r in rows: f.write(json.dumps(r, separators=(',', ':')) + '\n')
    print(f"[mma_steam] snapshot: {len(rows)} fights priced, {left} credits left")
    return rows


def opens(rows):
    """Pinnacle's first posted no-vig for each event. New events: step the historical endpoint back a day at a time (10 credits each) until
    the event is absent or 28 days back; the earliest snapshot that has Pinnacle on it is the open."""
    O = json.load(open(OPEN)) if os.path.exists(OPEN) else {}
    new = [r for r in rows if r['id'] not in O and 'pinnacle' in r['books']]
    if new and KEY:
        need = {r['id'] for r in new}; found = {}
        for back in range(1, 29):
            when = (NOW - dt.timedelta(days=back)).strftime('%Y-%m-%dT%H:00:00Z')
            d, left = get(f"{API}/historical/sports/{SPORT}/odds?apiKey={KEY}&regions=us,eu&markets=h2h&oddsFormat=decimal&date={when}")
            if not d or not d.get('data'): break
            listed = 0
            for ev in d['data']:
                if ev['id'] not in need: continue
                listed += 1; pr = pin_row(ev)
                if pr: found[ev['id']] = dict(t=d.get('timestamp') or when, home=ev['home_team'], away=ev['away_team'], dec=pr, p_home=nv(*pr), src='Odds API history')   # earlier snapshots overwrite: the earliest wins
            if not listed: break        # none of the new fights was listed that far back: everything found so far is the open
        for r in new:
            if r['id'] in found: O[r['id']] = found[r['id']]
            else:
                pr = r['books']['pinnacle']; O[r['id']] = dict(t=r['t'], home=r['home'], away=r['away'], dec=pr, p_home=nv(*pr), src='first seen live')
        print(f"[mma_steam] opens for {len(new)} new fights ({sum(1 for r in new if O[r['id']]['src'] != 'first seen live')} from history)")
    elif new:
        for r in new:
            pr = r['books']['pinnacle']; O[r['id']] = dict(t=r['t'], home=r['home'], away=r['away'], dec=pr, p_home=nv(*pr), src='first seen live')
    json.dump(O, open(OPEN, 'w'), separators=(',', ':'))
    return O


def ticks_latest():
    """Our own feed (data/mma/ticks): latest Pinnacle / Kalshi / Novig ML per ESPN event + side, and Pinnacle's first-seen no-vig."""
    L = {}; first = {}
    for f in sorted(glob.glob(os.path.join(MD, 'ticks', '*.jsonl.gz')))[-14:]:
        try:
            for l in gzip.open(f, 'rt'):
                r = json.loads(l)
                if r['market'] != 'ml': continue
                k = (r['event_id'], r['venue'], r['side'])
                if k not in L or r['ts'] > L[k]['ts']: L[k] = r
                if r['venue'] == 'Pinnacle':
                    fk = (r['event_id'], r['side'])
                    if fk not in first or r['ts'] < first[fk]['ts']: first[fk] = r
        except (EOFError, OSError): pass
    return L, first


def main():
    sched = json.load(open(os.path.join(MD, 'schedule.json'))) if os.path.exists(os.path.join(MD, 'schedule.json')) else {}
    L, first = ticks_latest()
    rows = snapshot()
    O = opens(rows) if rows else (json.load(open(OPEN)) if os.path.exists(OPEN) else {})
    paper = {}
    if os.path.exists(PAPER):
        for l in open(PAPER): r = json.loads(l); paper[r['key']] = r
    out = []; new = []
    def espn_match(home, away):
        for ev, e in sched.items():
            hn = (e.get('home_team') or {}).get('displayName'); an = (e.get('away_team') or {}).get('displayName')
            if (same(home, hn) and same(away, an)) or (same(home, an) and same(away, hn)): return ev, e, same(home, hn)
        return None, None, None
    cands = []
    if rows:
        for r in rows:
            if 'pinnacle' not in r['books'] or ts(r['start']) <= NOW: continue
            o = O.get(r['id']); cur = nv(*r['books']['pinnacle'])
            if not o or cur is None or o.get('p_home') is None: continue
            # orient the open to this snapshot's home (the Odds API swaps sides between snapshots sometimes)
            op = o['p_home'] if o['home'] == r['home'] else 1 - o['p_home'] if o['home'] == r['away'] else None
            if op is None: continue
            fav = 'home' if cur >= .5 else 'away'; pf = cur if fav == 'home' else 1 - cur; of = op if fav == 'home' else 1 - op
            best = None
            for bk in US:
                e = r['books'].get(bk)
                if e and e[0 if fav == 'home' else 1]:
                    c = 1 / e[0 if fav == 'home' else 1]
                    if best is None or c < best['cost']: best = dict(venue=bk, cost=round(c, 4))
            cands.append(dict(key=r['id'], start=r['start'], fav_name=r['home'] if fav == 'home' else r['away'], dog_name=r['away'] if fav == 'home' else r['home'], fav=fav,
                              open_p=round(of, 4), cur_p=round(pf, 4), move=round(pf - of, 4), open_ts=o['t'], open_src=o.get('src'), best=best, src='Odds API'))
    else:
        # no key: our Pinnacle ticks (open = first tick we logged, which is only the true open for fights posted after logging began)
        evs = {k[0] for k in first}
        for ev in evs:
            e = sched.get(ev)
            if not e or ts(e['start']) <= NOW: continue
            h, a = L.get((ev, 'Pinnacle', 'home')), L.get((ev, 'Pinnacle', 'away')); fh, fa = first.get((ev, 'home')), first.get((ev, 'away'))
            if not (h and a and fh and fa and h.get('american') and a.get('american') and fh.get('american') and fa.get('american')): continue
            ph, pa = implied(h['american']), implied(a['american']); cur = ph / (ph + pa)
            oh, oa = implied(fh['american']), implied(fa['american']); op = oh / (oh + oa)
            fav = 'home' if cur >= .5 else 'away'; pf = cur if fav == 'home' else 1 - cur; of = op if fav == 'home' else 1 - op
            cands.append(dict(key=ev, start=e['start'], fav_name=(e.get('home_team') if fav == 'home' else e.get('away_team') or {}).get('displayName'), dog_name=(e.get('away_team') if fav == 'home' else e.get('home_team') or {}).get('displayName'),
                              fav=fav, open_p=round(of, 4), cur_p=round(pf, 4), move=round(pf - of, 4), open_ts=fh['ts'], open_src='first Pinnacle tick', best=None, src='ticks', espn=ev))
    for c in cands:
        ev = c.get('espn')
        if not ev:
            ev, e, aligned = espn_match(c['fav_name'], c['dog_name'])
        if ev:
            e = sched.get(ev) or {}
            side = 'home' if same(c['fav_name'], (e.get('home_team') or {}).get('displayName')) else 'away'
            for v in ('Kalshi', 'Novig'):
                r = L.get((ev, v, side))
                if r and r.get('ask') and 'oneside' not in (r.get('flags') or []):
                    cost = round(r['ask'] + (math.ceil(KFEE * r['ask'] * (1 - r['ask']) * 100) / 100 if v == 'Kalshi' else 0), 4)
                    if c['best'] is None or cost < c['best']['cost']: c['best'] = dict(venue=v, cost=cost)
            c['espn'] = ev; c['espn_side'] = side
        c['flag'] = bool(c['move'] >= MOVE and c['best'] and c['cur_p'] <= .92)
        if c['key'] in paper: c['logged'] = dict(ts=paper[c['key']]['ts'], venue=paper[c['key']]['venue'], price=paper[c['key']]['price'])
        elif c['flag']:
            rec = dict(key=c['key'], ts=NOW_S, start=c['start'], fav_name=c['fav_name'], dog_name=c['dog_name'], open_p=c['open_p'], cur_p=c['cur_p'], move=c['move'], venue=c['best']['venue'], price=c['best']['cost'],
                       rule='mma_steam_fav', espn=c.get('espn'), espn_side=c.get('espn_side'))
            new.append(rec); paper[c['key']] = rec; c['logged'] = dict(ts=rec['ts'], venue=rec['venue'], price=rec['price'])
        out.append(c)
    if new:
        with open(PAPER, 'a') as f:
            for r in new: f.write(json.dumps(r) + '\n')
    # grade: ESPN winner flags on the schedule, then hist_schedule
    H = {}
    hp = os.path.join(ROOT, 'data', 'state', 'hist_schedule.json')
    if os.path.exists(hp):
        try: H = json.load(open(hp)).get('mma') or {}
        except Exception: H = {}
    graded = []
    for p in paper.values():
        if ts(p['start']) > NOW: continue
        won = None; e = sched.get(p.get('espn') or '')
        if e:
            ht, at = e.get('home_team') or {}, e.get('away_team') or {}
            if ht.get('winner') or at.get('winner'): won = bool((ht if p.get('espn_side') == 'home' else at).get('winner'))
        if won is None:
            for h in H.values():
                if h.get('winner') and ((same(h.get('p1'), p['fav_name']) and same(h.get('p2'), p['dog_name'])) or (same(h.get('p2'), p['fav_name']) and same(h.get('p1'), p['dog_name']))):
                    won = same(h['winner'], p['fav_name']); break
        if won is None: continue
        graded.append(dict(p, won=won, pnl=round((1 - p['price']) / p['price'] if won else -1.0, 3)))
    json.dump(graded, open(GRADED, 'w'), separators=(',', ':'))
    rec = dict(n=len(graded), won=sum(1 for g in graded if g['won']), units=round(sum(0.25 * g['pnl'] for g in graded), 2))
    out.sort(key=lambda c: c['start'])
    json.dump(dict(built=NOW_S, move=MOVE, src='Odds API' if rows else 'ticks', rows=out, record=rec, n_flagged=sum(1 for c in out if c['flag'])), open(OUT, 'w'), separators=(',', ':'))
    print(f"[mma_steam] {len(out)} upcoming fights, {sum(1 for c in out if c['flag'])} flagged, {len(new)} new paper; record {rec}")


if __name__ == '__main__':
    main()
