#!/usr/bin/env python3
"""Polymarket sports markets (public, no key): Gamma catalog + CLOB order books + public trade tape.
One snapshot per run for every game-tagged market starting within 36 hours -> data/polymarket/YYYY-MM-DD.jsonl.gz, one row per market:
  event slug/title, league, gameStartTime, question, sportsMarketType (moneyline / spreads / totals / nrfi / <prop stat>), line, outcomes,
  per outcome: best bid / ask, resting dollars within 3c of best on each side (bid side = shares x price), last trade,
  and taker trades since the last run (price, size, side, outcome) from data-api.polymarket.com.
Game lines only in MLB today (moneyline, nrfi); NFL/NBA carry spreads, totals and player props. Matched to a game by the slug's
team codes + gameStartTime in build_db (Polymarket slugs read away-home: mlb-cle-tb-2026-10-19 = CLE @ TB).
Also keeps data/polymarket/_markets.json (conditionId -> market metadata) so the public trade tape stays decodable."""
import json, os, gzip, time, datetime as dt, urllib.request, concurrent.futures as cf
import polydata                      # Data API v2 (v1 retired 11/2)

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'data', 'polymarket'); os.makedirs(OUT, exist_ok=True)
G = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"; DATA = "https://data-api.polymarket.com"
TAGS = ['mlb', 'nfl', 'nba', 'nhl', 'cfb', 'cbb', 'epl', 'ucl', 'mls', 'ufc', 'atp', 'wta']
TAG_SLUG = {'cbb': 'ncaa-basketball'}
BOOKS = {}
LINES_ONLY = {'NBA', 'NHL', 'CFB', 'CBB'}
LINE_TYPES = {'moneyline', 'spreads', 'totals', 'first_half_moneyline', 'first_half_spreads', 'first_half_totals', 'team_totals'}
HORIZON_H = 36; STATE = os.path.join(OUT, '_last_trade.json'); META = os.path.join(OUT, '_markets.json')


T0 = time.time(); BUDGET_S = float(os.environ.get('POLY_BUDGET_S', 360))


def g(u):
    for i in range(3):
        if time.time() - T0 > BUDGET_S: return None          # run budget: a throttling endpoint cannot stall the job
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=20))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 * (i + 1)); continue
            return None
        except Exception: time.sleep(1.0 * (i + 1))
    return None


def depth3(levels, best, bid_side):
    """resting dollars within 3c of best. bids: size x price; asks: size x (1-price) is the counterparty's stake; keep shares x price for both
    so the number reads as 'dollars it takes to clear within 3c' on the bid side and 'dollars offered' on the ask side."""
    out = 0.0
    for l in levels:
        p, s = float(l['price']), float(l['size'])
        if (bid_side and p >= best - 0.03) or (not bid_side and p <= best + 0.03): out += s * p
    return round(out, 2)


def snap_market(args):
    e, m, last_ts = args
    try: toks = json.loads(m.get('clobTokenIds') or '[]'); outs = json.loads(m.get('outcomes') or '[]'); px = json.loads(m.get('outcomePrices') or '[]')
    except Exception: return None
    if len(toks) != len(outs) or not toks: return None
    sides = {}
    for tok, name, p in zip(toks, outs, px + [None] * len(toks)):
        b = BOOKS.get(tok)
        if b is None: b = g(f"{CLOB}/book?token_id={tok}") or {}
        bids = sorted(b.get('bids') or [], key=lambda l: -float(l['price'])); asks = sorted(b.get('asks') or [], key=lambda l: float(l['price']))
        bb = float(bids[0]['price']) if bids else None; ba = float(asks[0]['price']) if asks else None
        sides[name] = dict(token=tok, mid_gamma=float(p) if p not in (None, '') else None, bid=bb, ask=ba,
                           bid_qty=float(bids[0]['size']) if bids else None, ask_qty=float(asks[0]['size']) if asks else None,
                           bid_depth3=depth3(bids, bb, True) if bb is not None else None, ask_depth3=depth3(asks, ba, False) if ba is not None else None,
                           last=float(b['last_trade_price']) if b.get('last_trade_price') not in (None, '') else None)
    cid = m.get('conditionId'); new = []
    tr = polydata.trades(condition=cid, limit=200) if cid else []
    lt = last_ts.get(cid, 0)
    for t in tr:
        if t.get('timestamp', 0) > lt: new.append(dict(ts=t['timestamp'], side=t.get('side'), outcome=t.get('outcome'), p=t.get('price'), size=t.get('size'), w=t.get('proxyWallet')))
    return dict(event=e.get('slug'), title=e.get('title'), league=e.get('_league'), market=m.get('id'), cond=cid, q=m.get('question'), type=m.get('sportsMarketType'),
                line=m.get('line'), start=m.get('gameStartTime') or e.get('startDate'), vol=float(m.get('volume') or 0), liq=float(m.get('liquidity') or 0),
                sides=sides, new_trades=new, last_ts=max([t.get('timestamp', 0) for t in tr] + [lt]))


def main():
    now = dt.datetime.now(dt.timezone.utc); et = now.astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))
    last = json.load(open(STATE)) if os.path.exists(STATE) else {}
    meta = json.load(open(META)) if os.path.exists(META) else {}
    todo = []
    # 11/6: ordering by startDate (when the event was CREATED) returned the 100 newest events, two weeks out, so NBA/NHL/CFB/CBB games
    # inside 36h never made it in (only EPL did). Order by endDate from 4h ago and page until past the horizon. CBB games carry the
    # 'ncaa-basketball' tag ('cbb' is futures only).
    emin = (now - dt.timedelta(hours=4)).strftime('%Y-%m-%dT%H:%M:%SZ'); emax = now + dt.timedelta(hours=HORIZON_H + 12)
    for tag in TAGS:
        evs = []
        for off in range(0, 2000, 100):
            page = g(f"{G}/events?tag_slug={TAG_SLUG.get(tag, tag)}&active=true&closed=false&limit=100&offset={off}&order=endDate&ascending=true&end_date_min={emin}") or []
            evs += page
            try: last_end = dt.datetime.fromisoformat((page[-1].get('endDate') or '').replace('Z', '+00:00')) if page else None
            except Exception: last_end = None
            if len(page) < 100 or (last_end and last_end > emax): break
        for e in evs:
            e['_league'] = tag.upper()
            for m in e.get('markets', []):
                if not m.get('sportsMarketType') or not m.get('gameStartTime'): continue
                try: gst = dt.datetime.fromisoformat(m['gameStartTime'].replace(' ', 'T').replace('+00', '+00:00'))
                except Exception: continue
                if not (-3 <= (gst - now).total_seconds() / 3600 <= HORIZON_H): continue
                if e['_league'] in LINES_ONLY and m.get('sportsMarketType') not in LINE_TYPES: continue      # 11/6: game lines only for the newly added leagues (CFB alone has ~4,000 novelty markets)
                todo.append((e, m, last))
                meta[m.get('conditionId')] = dict(event=e.get('slug'), title=e.get('title'), league=e['_league'], q=m.get('question'), type=m.get('sportsMarketType'),
                                                  line=m.get('line'), outcomes=json.loads(m.get('outcomes') or '[]'), tokens=json.loads(m.get('clobTokenIds') or '[]'),
                                                  start=m.get('gameStartTime'))
    # 11/6: books in batches of 100 (POST /books) instead of one GET per outcome; the added leagues took a run from 84s to ~400s
    toks = [t for e, m, _ in todo for t in (json.loads(m.get('clobTokenIds') or '[]') if isinstance(m.get('clobTokenIds'), str) else (m.get('clobTokenIds') or []))]
    def batch(chunk):
        for i in range(3):
            try:
                req = urllib.request.Request(f"{CLOB}/books", data=json.dumps([{'token_id': t} for t in chunk]).encode(), headers={'Content-Type': 'application/json', 'User-Agent': 'sharp-tracker'})
                return json.load(urllib.request.urlopen(req, timeout=40))
            except Exception: time.sleep(2 * (i + 1))
        return []
    with cf.ThreadPoolExecutor(4) as ex:
        for res in ex.map(batch, [toks[i:i + 100] for i in range(0, len(toks), 100)]):
            for b in res or []: BOOKS[b.get('asset_id')] = b
    with cf.ThreadPoolExecutor(6) as ex: rows = [r for r in ex.map(snap_market, todo) if r]
    ts = int(now.timestamp())
    # gzip (appended members): the plain .jsonl hit GitHub's 100 MB file limit on a Saturday (2026-10-31, 114k rows) and the push failed
    with gzip.open(os.path.join(OUT, f"{et.date().isoformat()}.jsonl.gz"), 'at') as f:
        for r in rows: f.write(json.dumps({'ts': ts, **{k: v for k, v in r.items() if k != 'last_ts'}}) + '\n')
    last.update({r['cond']: r['last_ts'] for r in rows}); json.dump(last, open(STATE, 'w'))
    json.dump(meta, open(META, 'w'), separators=(',', ':'))
    import collections
    print(f"[polymarket] {len(rows)} of {len(todo)} markets in {round(time.time() - T0)}s, {sum(len(r['new_trades']) for r in rows)} new trades; " + str(dict(collections.Counter(r['league'] for r in rows))))


if __name__ == '__main__':
    main()
