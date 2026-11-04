#!/usr/bin/env python3
"""Polymarket settled game markets + their full public trade tape, for backtesting big vs small money on Polymarket (Sean, 11/2).
Step 1 (catalog): every closed game event (slug league-away-home-YYYY-MM-DD) per sport tag from the Gamma API, with each moneyline /
spread / total market: conditionId, outcomes, line, gameStartTime, winner (outcomePrices 1/0), volume ->
data/polymarket/history/catalog.jsonl. Step 2 (trades): every public trade on those markets from data-api.polymarket.com (taker fills:
side BUY/SELL of an outcome, price, size, timestamp, proxyWallet) -> data/polymarket/history/trades/<conditionId>.jsonl.gz.
The wallet column is what makes Polymarket different: every fill has an on-chain account, so a wallet's record can be tested too.
Usage: python3 loggers/polymarket_history.py catalog | trades | catalog_props | trades_props [--min-volume N]"""
import os, sys, re, json, gzip, time, datetime as dt, urllib.request, urllib.error, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import polydata     # Data API v2
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'polymarket', 'history'); os.makedirs(os.path.join(OUT, 'trades'), exist_ok=True)
G = "https://gamma-api.polymarket.com"; D = "https://data-api.polymarket.com"
TAGS = ['nfl', 'nba', 'nhl', 'cfb', 'cbb', 'mlb', 'epl', 'ucl', 'mls', 'laliga', 'bundesliga', 'seriea', 'ligue1', 'ufc', 'wnba']
GAME = re.compile(r'^([a-z0-9]+)-([a-z0-9]+)-([a-z0-9]+)-(\d{4}-\d{2}-\d{2})$')
PROPEV = re.compile(r'^([a-z0-9]+)-([a-z0-9]+)-([a-z0-9]+)-(\d{4}-\d{2}-\d{2})(-player-props)?$')
NOT_PROP = {'moneyline', 'spreads', 'totals', 'first_touchdowns', 'team_first_touchdowns', 'highest_scoring_quarter', 'exact_margin', None}
TAG_ALIAS = {'ncaa-basketball': 'cbb'}     # 2025-26 college basketball game events carry this tag, not 'cbb'
TYPES = {'moneyline': 'ml', 'spreads': 'spread', 'totals': 'total'}


def g(u, tries=5):
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=40))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503): time.sleep(2 * (i + 1)); continue
            return None
        except Exception: time.sleep(2 * (i + 1))
    return None


def catalog():
    seen = set(); n = 0
    with open(os.path.join(OUT, 'catalog.jsonl'), 'w') as f:
        for tag in TAGS:
            off = 0; nt = 0
            while off < 20000:
                E = g(f"{G}/events?tag_slug={tag}&closed=true&limit=100&offset={off}&order=startDate&ascending=false")
                if not E: break
                for e in E:
                    m_ = GAME.match(e.get('slug') or '')
                    if not m_ or e['slug'] in seen: continue
                    seen.add(e['slug'])
                    for m in e.get('markets') or []:
                        mk = TYPES.get(m.get('sportsMarketType'))
                        if not mk: continue
                        try: outs = json.loads(m['outcomes']); px = [float(x) for x in json.loads(m.get('outcomePrices') or '[]')]
                        except Exception: continue
                        if len(outs) != 2 or len(px) != 2 or sorted(px) != [0.0, 1.0]: continue      # settled two-way only (no voids/pushes)
                        f.write(json.dumps(dict(tag=tag, event=e['slug'], title=e.get('title'), date=m_.group(4), market=mk, line=m.get('line'),
                                                cond=m['conditionId'], outcomes=outs, winner=outs[px.index(1.0)], start=m.get('gameStartTime'),
                                                volume=float(m.get('volume') or 0))) + '\n'); n += 1; nt += 1
                off += len(E)
                if len(E) < 100: break
            print(f"[poly hist] {tag}: {nt} settled game markets (scanned {off} events)", flush=True)
    print(f"[poly hist] catalog: {n} markets on {len(seen)} games")


def catalog_back(tags=None):
    """Older settled game markets the newest-first listing cannot reach (Gamma stops paging around 2,100 events per tag): walk each tag
    backwards by end date (end_date_max = the oldest start seen so far) until a window holds no game events, and append markets not
    already in catalog.jsonl."""
    have = set()
    for l in open(os.path.join(OUT, 'catalog.jsonl')): have.add(json.loads(l)['cond'])
    n = 0
    with open(os.path.join(OUT, 'catalog.jsonl'), 'a') as f:
        for tag in (tags or TAGS):
            mx = None; empty = 0; nt = 0
            for l in open(os.path.join(OUT, 'catalog.jsonl')):
                r = json.loads(l)
                if r['tag'] == tag and (mx is None or r['date'] < mx): mx = r['date']
            mx = mx or '2026-11-02'
            while empty < 60 and mx > '2023-06-01':          # props / novelty events fill whole windows; keep walking
                E = g(f"{G}/events?tag_slug={tag}&closed=true&limit=100&order=startDate&ascending=false&end_date_max={mx}T00:00:00Z")
                if not E: break
                got = 0; oldest = mx
                for e in E:
                    m_ = GAME.match(e.get('slug') or ''); sd = (e.get('startDate') or '')[:10]
                    if sd and sd < oldest: oldest = sd
                    if not m_: continue
                    got += 1
                    for m in e.get('markets') or []:
                        mk = TYPES.get(m.get('sportsMarketType'))
                        if not mk or m['conditionId'] in have: continue
                        try: outs = json.loads(m['outcomes']); px = [float(x) for x in json.loads(m.get('outcomePrices') or '[]')]
                        except Exception: continue
                        if len(outs) != 2 or len(px) != 2 or sorted(px) != [0.0, 1.0]: continue
                        have.add(m['conditionId'])
                        f.write(json.dumps(dict(tag=TAG_ALIAS.get(tag, tag), event=e['slug'], title=e.get('title'), date=m_.group(4), market=mk, line=m.get('line'),
                                                cond=m['conditionId'], outcomes=outs, winner=outs[px.index(1.0)], start=m.get('gameStartTime'),
                                                volume=float(m.get('volume') or 0))) + '\n'); n += 1; nt += 1
                empty = empty + 1 if got == 0 else 0
                if oldest >= mx: oldest = (dt.date.fromisoformat(mx) - dt.timedelta(days=3)).isoformat()   # no progress: step back
                mx = oldest
            print(f"[poly hist] back {tag}: {nt} older markets, reached {mx}", flush=True)
    print(f"[poly hist] back: {n} older markets added")


def catalog_ufc_cards(out_name='catalog_ufc_old.jsonl'):
    """Older UFC markets live on card-level events ('ufc-320-ankalaev-vs-pereira-2', one moneyline market per fight), which the
    league-a-h-date pattern misses. Walk the ufc tag back by end date and keep settled two-way moneyline fight markets with a
    gameStartTime that are not already in catalog.jsonl -> catalog_ufc_old.jsonl (merge by hand after checking)."""
    have = set(json.loads(l)['cond'] for l in open(os.path.join(OUT, 'catalog.jsonl')))
    mx = '2026-11-02'; n = 0; empty = 0
    with open(os.path.join(OUT, out_name), 'w') as f:
        while empty < 20 and mx > '2023-01-01':
            E = g(f"{G}/events?tag_slug=ufc&closed=true&limit=100&order=startDate&ascending=false&end_date_max={mx}T00:00:00Z")
            if not E: break
            oldest = mx; got = 0
            for e in E:
                sd = (e.get('startDate') or '')[:10]
                if sd and sd < oldest: oldest = sd
                if not (e.get('slug') or '').startswith('ufc'): continue
                for m in e.get('markets') or []:
                    if m.get('sportsMarketType') != 'moneyline' or m['conditionId'] in have or not m.get('gameStartTime'): continue
                    try: outs = json.loads(m['outcomes']); px = [float(x) for x in json.loads(m.get('outcomePrices') or '[]')]
                    except Exception: continue
                    if len(outs) != 2 or sorted(px) != [0.0, 1.0]: continue
                    have.add(m['conditionId']); got += 1; n += 1
                    f.write(json.dumps(dict(tag='ufc', event=m.get('slug') or e['slug'], title=m.get('question'), date=m['gameStartTime'][:10], market='ml', line=None,
                                            cond=m['conditionId'], outcomes=outs, winner=outs[px.index(1.0)], start=m['gameStartTime'],
                                            volume=float(m.get('volume') or 0))) + '\n')
            empty = empty + 1 if got == 0 else 0
            if oldest >= mx: oldest = (dt.date.fromisoformat(mx) - dt.timedelta(days=3)).isoformat()
            mx = oldest
    print(f"[poly hist] ufc cards: {n} older fight markets, reached {mx}")


def catalog_props(min_vol=2000.0):
    """Settled two-way player-prop markets (any sportsMarketType that is not a game line or a many-way novelty) on game and
    '-player-props' events -> data/polymarket/history/catalog_props.jsonl (same fields as catalog.jsonl plus the stat type)."""
    n = 0
    with open(os.path.join(OUT, 'catalog_props.jsonl'), 'w') as f:
        for tag in TAGS:
            off = 0; nt = 0
            while off < 20000:
                E = g(f"{G}/events?tag_slug={tag}&closed=true&limit=100&offset={off}&order=startDate&ascending=false")
                if not E: break
                for e in E:
                    m_ = PROPEV.match(e.get('slug') or '')
                    if not m_: continue
                    for m in e.get('markets') or []:
                        t = m.get('sportsMarketType')
                        if t in NOT_PROP or t.startswith(('first_half', 'second_half', 'q1', 'q2', 'q3', 'q4', 'team_')) or float(m.get('volume') or 0) < min_vol: continue
                        try: outs = json.loads(m['outcomes']); px = [float(x) for x in json.loads(m.get('outcomePrices') or '[]')]
                        except Exception: continue
                        if len(outs) != 2 or sorted(px) != [0.0, 1.0] or not m.get('gameStartTime'): continue
                        f.write(json.dumps(dict(tag=tag, event=e['slug'], title=e.get('title'), date=m_.group(4), market='prop', stat=t, q=m.get('question'), line=m.get('line'),
                                                cond=m['conditionId'], outcomes=outs, winner=outs[px.index(1.0)], start=m.get('gameStartTime'),
                                                volume=float(m.get('volume') or 0))) + '\n'); n += 1; nt += 1
                off += len(E)
                if len(E) < 100: break
            print(f"[poly hist] props {tag}: {nt} settled prop markets", flush=True)
    print(f"[poly hist] props catalog: {n} markets")


def trades_for(cond):
    p = os.path.join(OUT, 'trades', f'{cond}.jsonl.gz')
    if os.path.exists(p): return 0
    T = polydata.trades(condition=cond, limit=500, max_rows=10000)       # v2 cursor paging; very busy markets are truncated at 10k (flagged)
    rows = [dict(ts=t['timestamp'], side=t['side'], outcome=t.get('outcome'), price=t['price'], size=t['size'], wallet=t.get('proxyWallet')) for t in T]
    off = len(rows)
    with gzip.open(p, 'wt') as f:
        for r in rows: f.write(json.dumps(r, separators=(',', ':')) + '\n')
        if off >= 10000: f.write(json.dumps(dict(truncated=True)) + '\n')
    return len(rows)


def trades(min_vol, cat='catalog.jsonl'):
    C = [json.loads(l) for l in open(os.path.join(OUT, cat))]
    todo = [c['cond'] for c in C if c['volume'] >= min_vol]
    t0 = time.time(); n = 0
    with cf.ThreadPoolExecutor(8) as ex:
        for i, k in enumerate(ex.map(trades_for, todo)):
            n += k
            if i % 500 == 0: print(f"[poly hist] trades {i}/{len(todo)} markets, {n} trades, {time.time() - t0:.0f}s", flush=True)
    print(f"[poly hist] trades done: {len(todo)} markets, {n} new trades")


if __name__ == '__main__':
    mv = float(sys.argv[sys.argv.index('--min-volume') + 1]) if '--min-volume' in sys.argv else 1000.0
    if sys.argv[1] == 'catalog': catalog()
    elif sys.argv[1] == 'catalog_props': catalog_props()
    elif sys.argv[1] == 'catalog_ufc': catalog_ufc_cards()
    elif sys.argv[1] == 'catalog_back': catalog_back([t for t in sys.argv[2:] if not t.startswith('--')] or None)
    elif sys.argv[1] == 'trades_props': trades(mv, 'catalog_props.jsonl')
    else: trades(mv)
