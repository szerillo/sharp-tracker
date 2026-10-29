#!/usr/bin/env python3
"""Import the user's own executed fills from the exchanges into the ledger, so real bets log themselves (zero typing).
  Novig   GET /v3/portfolio/fills   (NOVIG_KEY_ID / NOVIG_PRIVATE_KEY)   -> decoded with the catalog (market/outcome -> event, market, side, line)
  Kalshi  GET /trade-api/v2/portfolio/fills (KALSHI_KEY_ID / KALSHI_PRIVATE_KEY, Ed25519 or RSA-PSS) -> decoded from the ticker
Raw rows are kept in data/state/exchange_fills.jsonl (append-only, dedup by fill id). Each decodable fill becomes a ledger row
(venue Kalshi/Novig, rule_tag 'real:<exchange>', price = what was actually paid incl. fee) unless the user already logged that bet by
hand within 2 h on the same event x market x side (then the hand row keeps priority). Skips silently without keys."""
import os, sys, json, time, base64, uuid, sqlite3, datetime as dt, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'loggers'))
from sharp import norm as N, fair as F, fills as FI, sports as SP, novig_auth as NA

ROOT = os.path.abspath(os.path.join(HERE, '..')); SD = os.path.join(ROOT, 'data', 'state'); DB = os.path.join(SD, 'sharp.sqlite')
RAW = os.path.join(SD, 'exchange_fills.jsonl'); NOW = dt.datetime.now(dt.timezone.utc); NOW_S = N.iso(NOW)
KAPI = "https://api.elections.kalshi.com/trade-api/v2"


# ----------------------------------------------------------------- Kalshi signed GET ----
def kalshi_get(path, query=''):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding, ed25519
    key = serialization.load_pem_private_key(os.environ['KALSHI_PRIVATE_KEY'].replace('\\n', '\n').encode(), password=None)
    ts = str(int(time.time() * 1000)); msg = (ts + 'GET' + '/trade-api/v2' + path).encode()
    if isinstance(key, ed25519.Ed25519PrivateKey): sig = key.sign(msg)
    else: sig = key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=hashes.SHA256().digest_size), hashes.SHA256())
    hdr = {'KALSHI-ACCESS-KEY': os.environ['KALSHI_KEY_ID'], 'KALSHI-ACCESS-TIMESTAMP': ts, 'KALSHI-ACCESS-SIGNATURE': base64.b64encode(sig).decode(), 'User-Agent': 'sharp-tracker'}
    req = urllib.request.Request(KAPI + path + (('?' + query) if query else ''), headers=hdr)
    with urllib.request.urlopen(req, timeout=40) as r: return json.load(r)


def load_raw():
    out = {}
    if os.path.exists(RAW):
        for l in open(RAW):
            try: r = json.loads(l); out[r['id']] = r
            except Exception: pass
    return out


def pull_kalshi(raw):
    if not (os.environ.get('KALSHI_KEY_ID') and os.environ.get('KALSHI_PRIVATE_KEY')): return 0
    cur = ''; n = 0; min_ts = int((NOW - dt.timedelta(days=14)).timestamp())
    while True:
        x = kalshi_get('/portfolio/fills', f'limit=1000&min_ts={min_ts}' + (f'&cursor={cur}' if cur else ''))
        for f in x.get('fills', []):
            fid = 'kalshi:' + f['fill_id']
            if fid in raw: continue
            side = f.get('outcome_side') or f.get('side'); price = float(f['yes_price_dollars'] if side == 'yes' else f['no_price_dollars'])
            raw[fid] = dict(id=fid, exchange='Kalshi', ticker=f['ticker'], side=side, action=f.get('action'), count=float(f['count_fp']), price=price,
                            fee=float(f.get('fee_cost') or 0), taker=f.get('is_taker'), ts=f['created_time'], imported=NOW_S); n += 1
        cur = x.get('cursor')
        if not cur or not x.get('fills'): break
    return n


def pull_novig(raw):
    if not NA.available(): return 0
    from novig_catalog import load_catalog
    cat = load_catalog(); n = 0; cur = None; since = int((NOW - dt.timedelta(days=14)).timestamp() * 1000)
    while True:
        s, r = NA.request('GET', '/v3/portfolio/fills', f'startsAfter={since}&limit=500' + (f'&after={cur}' if cur else ''))
        if s != 200: print(f'[xfills] novig fills -> {s} {str(r)[:100]}'); break
        for f in r.get('items', []):
            fid = 'novig:' + f['fillId']
            if fid in raw: continue
            m = cat.get(f['marketId']) or {}
            raw[fid] = dict(id=fid, exchange='Novig', market=f['marketId'], outcome=f['outcomeId'], qty=f['qty'], cost=float(f['cost']), fee=float(f.get('fee') or 0),
                            price=round(100 * float(f['cost']) / f['qty'], 4) if f['qty'] else None, taker=f.get('taker'), ts=N.iso(N.parse_ts(f['ts'])),
                            event=m.get('event'), league=m.get('league'), type=m.get('type'), desc=m.get('desc'), strike=m.get('strike'),
                            outcome_name=(m.get('outcomes') or {}).get(f['outcomeId']), start_ts=m.get('start_ts'), imported=NOW_S); n += 1
        cur = r.get('next')
        if not cur: break
    return n


# ----------------------------------------------------------------- decode -> ledger rows ----
def decode(conn, r):
    """-> (event_id, market, side, line, participant) or None."""
    if r['exchange'] == 'Kalshi':
        t = r['ticker']; parts = t.split('-')
        if len(parts) < 3: return None
        series, evt, tail = parts[0], parts[1], parts[-1]
        for sp, cfg in SP.SPORTS.items():
            if not series.startswith(cfg['kalshi']): continue
            suf = series[len(cfg['kalshi']):]
            if suf not in SP.KALSHI_GAME: return None
            mkt, per = SP.KALSHI_GAME[suf]; p = SP.kalshi_event(evt)
            if not p: return None
            date, blob = p; teams = SP.Teams(sp); codes = set(teams.codes) | set(SP.CODE_FIX[sp].values())
            sc = SP.split_codes(blob, codes, SP.CODE_FIX[sp])
            if not sc: return None
            a, h = sc
            row = conn.execute("SELECT event_id FROM events WHERE sport=? AND away=? AND home=? AND et_date BETWEEN ? AND ?", (sp, a, h, (date - dt.timedelta(days=1)).isoformat(), (date + dt.timedelta(days=1)).isoformat())).fetchone()
            if not row: return None
            ev = row[0]; yes = r['side'] == 'yes'
            import re
            if mkt == 'ml':
                team = SP.CODE_FIX[sp].get(tail, tail)
                side = ('home' if team == h else 'away') if yes else ('away' if team == h else 'home')
                return ev, per + 'ml', side, None, h if side == 'home' else a
            m = re.match(r'^([A-Z]+)?(\d+)$', tail)
            if not m: return None
            strike = float(m.group(2)) - 0.5
            if mkt == 'total': return ev, per + 'total', 'over' if yes else 'under', strike, None
            team = SP.CODE_FIX[sp].get(m.group(1) or '', m.group(1) or '')
            if mkt == 'spread':
                side_team = 'home' if team == h else 'away'
                if yes: return ev, per + 'spread', side_team, -strike, team
                other = 'away' if side_team == 'home' else 'home'; return ev, per + 'spread', other, strike, a if other == 'away' else h
            if mkt == 'tt': return ev, per + ('tt_home' if team == h else 'tt_away'), 'over' if yes else 'under', strike, team
        return None
    # Novig: decode from the catalog record
    if not r.get('event') or '@' not in r['event'] or not r.get('type'): return None
    lg = (r.get('league') or '').upper(); sp = {'NFL': 'nfl', 'NBA': 'nba', 'NCAAF': 'cfb', 'MLB': 'mlb'}.get(lg)
    if not sp: return None
    aw, hm = [x.strip() for x in r['event'].split('@', 1)]
    if sp == 'mlb': a, h = N.team(aw), N.team(hm)
    else: tm = SP.Teams(sp); a, h = tm.code(aw), tm.code(hm)
    st = N.parse_ts(r['start_ts']) if r.get('start_ts') else N.parse_ts(r['ts'])
    row = conn.execute("SELECT event_id FROM events WHERE sport=? AND away=? AND home=? AND et_date BETWEEN ? AND ?", (sp, a, h, (N.et_date(st) - dt.timedelta(days=1)).isoformat(), (N.et_date(st) + dt.timedelta(days=1)).isoformat())).fetchone()
    if not row: return None
    ev = row[0]; typ = r['type']; name = r.get('outcome_name') or ''; strike = float(r['strike']) if r.get('strike') not in (None, '') else None
    gm = SP.NOVIG_GAME.get(typ) if sp != 'mlb' else {'MONEY': ('ml', ''), 'SPREAD': ('rl', ''), 'TOTAL': ('total', ''), 'TEAM_TOTAL': ('tt', ''), 'MONEY_1H': ('f5_ml', ''), 'TOTAL_1H': ('f5_total', ''), 'SPREAD_1H': ('f5_rl', '')}.get(typ)
    if gm:
        mkt, per = gm; code = (N.team if sp == 'mlb' else SP.Teams(sp).code)
        if mkt in ('ml', 'f5_ml'):
            t = code(name); side = 'home' if t == h else ('away' if t == a else None)
            return (ev, per + mkt, side, None, t) if side else None
        if mkt in ('spread', 'rl', 'f5_rl'):
            import re
            mm = re.match(r'^(.*?)\s+([+-]?\d+\.?\d*)$', name)
            if not mm: return None
            t = code(mm.group(1)); side = 'home' if t == h else ('away' if t == a else None)
            return (ev, per + mkt, side, float(mm.group(2)), t) if side else None
        ou = 'over' if name.lower().startswith('over') else ('under' if name.lower().startswith('under') else None)
        if not ou: return None
        if mkt == 'tt':
            import re
            t = code(re.sub(r'\s+t?\d+\.?\d*$', '', r.get('desc', '')).split('@')[-1].strip())
            return ev, per + ('tt_home' if t == h else 'tt_away'), ou, strike, t
        return ev, per + mkt, ou, strike, None
    stat = (SP.NOVIG_PROPS.get(sp) or {}).get(typ) if sp != 'mlb' else N.STAT_NOVIG.get(typ)
    if not stat: return None
    import re
    desc = r.get('desc', ''); mm = re.match(r'^(.*?)\s+[ou]?\d+\.?\d*(\s+[A-Z_]+)?$', desc); pname = (mm.group(1) if mm else desc).strip()
    ou = 'over' if name.lower().startswith('over') else ('under' if name.lower().startswith('under') else None)
    return (ev, f'prop_{stat}', ou, strike, N.player_key(pname)) if ou else None


def main():
    raw = load_raw(); n_k = n_n = 0
    try: n_k = pull_kalshi(raw)
    except Exception as e: print(f'[xfills] kalshi: {type(e).__name__} {str(e)[:120]}')
    try: n_n = pull_novig(raw)
    except Exception as e: print(f'[xfills] novig: {type(e).__name__} {str(e)[:120]}')
    with open(RAW, 'w') as f:
        for r in raw.values(): f.write(json.dumps(r) + '\n')
    conn = sqlite3.connect(DB); rows = FI.load(); have = {r.get('exchange_fill_id') for r in rows if r.get('exchange_fill_id')}; added = 0; undecoded = 0
    for r in raw.values():
        if r['id'] in have: continue
        # buys only for Kalshi (a sell closes a position; ignore for the ledger), Novig fills are all opens from our side
        if r['exchange'] == 'Kalshi' and r.get('action') == 'sell': continue
        d = decode(conn, r)
        if not d: undecoded += 1; continue
        ev, market, side, line, part = d
        e = conn.execute("SELECT start_utc, away, home FROM events WHERE event_id=?", (ev,)).fetchone()
        start = e[0]; ts = r['ts']
        dup = [x for x in rows if x['event_id'] == ev and x['market'] == market and x['side'] == side and (x.get('line') == line) and not str(x.get('rule_tag', '')).startswith(('paper:', 'real:'))
               and abs((N.parse_ts(x['ts_utc']) - N.parse_ts(ts)).total_seconds()) < 7200]
        if dup: dup[0]['exchange_fill_id'] = r['id']; continue
        if r['exchange'] == 'Kalshi':
            cost = r['price'] + (r['fee'] / r['count'] if r['count'] else 0); stake_usd = r['count'] * r['price']
        else:
            cost = (r['price'] or 0) / 100; stake_usd = r['cost']
        if not cost or cost <= 0 or cost >= 1: continue
        eq = F.EventQuotes(conn, ev); fr = eq.fair(market, line, side, ts, part)
        row = dict(fill_id=uuid.uuid4().hex[:12], ts_utc=N.iso(N.parse_ts(ts)), event_id=ev, market=market, mclass=('prop' if market.startswith('prop_') else 'game'), participant=part,
                   player_name=None, line=line, side=side, venue=r['exchange'], price_american=N.prob_to_american(cost), price_decimal=round(1 / cost, 4), implied=round(cost, 5),
                   stake=round(stake_usd / 100, 3), rule_tag=f"real:{r['exchange'].lower()}", fair_at_fill=round(fr['fair'], 5) if fr['fair'] is not None else None,
                   fair_at_fill_status=fr['status'], fair_at_fill_detail={k: (round(v['p'], 4) if v['p'] is not None else v['why']) for k, v in fr['detail'].items()},
                   fair_weights={k: round(v, 3) for k, v in fr['weights'].items()}, late=int(N.parse_ts(start) <= N.parse_ts(ts)), note=f"auto-import {r['id']}; stake in units of $100",
                   start_utc=start, exchange_fill_id=r['id'])
        rows.append(row); added += 1
    FI.save(rows); conn.close()
    print(f"[xfills] pulled kalshi {n_k} novig {n_n}; {added} new ledger rows, {undecoded} undecoded (futures/parlays/unknown markets), {len(raw)} raw on file")


if __name__ == '__main__':
    main()
