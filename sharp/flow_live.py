#!/usr/bin/env python3
"""Live big-money vs small-money split on upcoming games (watch signal, tier C; backtest: sharp/flow_split.py,
docs/flow_split_2026-10-31.md).

Per upcoming game x market (moneyline, main spread, main total), from every pregame taker fill logged so far:
  size of a fill = risk-equivalent dollars, contracts x min(price, 1 - price): the stake on a dog, the to-win on a favorite
  big   = such dollars in fills of BIG_USD or more, per side   small = in fills of SMALL_USD or less, per side
  big_net = big dollars on the leading side minus the other side; small_net likewise (signed toward the big side)
  divergent = big money and small money on opposite sides with big_net >= DIV_USD (the backtest's best shape)
Sources: Kalshi trades (data/kalshi/trades5, taker side explicit), Polymarket taker trades on game lines (data/polymarket, see
poly_trades) and Novig live trades (data/novig/trades5, see novig_trades; the taker side was verified against Novig's public tape on 11/1).
Writes data/state/flow_live.json."""
import os, sys, json, gzip, glob, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.norm import parse_ts
MOVE_PTS = 4.0; TIGHT = 0.04
STEAM_PTS = 3.0; STEAM_MIN = 60; REV_FRAC = 0.4; REV_FRESH = 30
SHOW_TOTAL = 10000.0; SHOW_BIG = 2500.0   # Today-page floor for big vs small (readability only; stricter cuts were tested and did not help)
BIG_USD = 500.0; SMALL_USD = 50.0; DIV_USD = 1000.0; NOVIG_VERIFIED = True   # 11/1: sharp/novig_verify.py, 1,547 of 1,548 matched trades
OUT = os.path.join(ROOT, 'data', 'state', 'flow_live.json')
PAPER = os.path.join(ROOT, 'data', 'kalshi', 'steam_rev_paper.jsonl'); RESC = os.path.join(ROOT, 'data', 'kalshi', 'steam_rev_results.json')
OTHER = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}
NOW = dt.datetime.now(dt.timezone.utc)


def recent(d, days=8):
    cut = (NOW - dt.timedelta(days=days)).date().isoformat()
    fs = glob.glob(os.path.join(d, '*.jsonl.gz')) + glob.glob(os.path.join(d, '*.jsonl'))     # the Polymarket logger wrote plain .jsonl before 10/31
    return [f for f in sorted(fs) if os.path.basename(f)[:10] >= cut]


LINKS = {}      # event_id -> {'kalshi': {market: url}, 'poly': url, 'an': url}: where the Today page sends you to bet


def kalshi_url(ticker):
    """Kalshi web page for a market ticker: /markets/<series>/x/<event ticker> (the middle slug is free text; checked 11/1; the event ticker is the market ticker minus its last part)."""
    t = ticker.lower(); return f"https://kalshi.com/markets/{t.split('-')[0]}/x/{t.rsplit('-', 1)[0]}"     # event ticker = market ticker minus its outcome suffix


def kalshi_moves(sched):
    """Kalshi markets whose two-sided mid has moved MOVE_PTS+ points since the first two-sided price we logged (20-minute and 5-minute
    ticks, last 14 days). Backtest (sharp/flow_grid.py --ask): following a 4+ pt move since the open at the ask, 1h to 15m before start,
    +13% on ~500 October games (z 3.4) but about flat in August-September; see docs/flow_split_2026-10-31.md. Watch only."""
    first, last, series = {}, {}, collections.defaultdict(list)
    for sp in sorted({e['sport'] for e in sched.values()}):
        files = []
        for d in ('ticks', 'ticks5'): files += recent(os.path.join(ROOT, 'data', sp, d), days=14)
        for f in files:
            try: fh = gzip.open(f, 'rt'); lines = list(fh)
            except (EOFError, OSError): continue
            for l in lines:
                if '"Kalshi"' not in l: continue
                try: t = json.loads(l)
                except Exception: continue
                if t.get('market') not in ('ml', 'spread', 'total') or t.get('bid') is None or t.get('ask') is None: continue
                e = sched.get(t.get('event_id'))
                if not e or (sp == 'soccer' and t['market'] == 'ml'): continue
                if not (0 < t['ask'] - t['bid'] <= TIGHT): continue
                tk = (t.get('extra') or {}).get('ticker')
                if not tk: continue
                LINKS.setdefault(t['event_id'], {}).setdefault('kalshi', {})[t['market']] = kalshi_url(tk)
                rec = (t['ts'], (t['bid'] + t['ask']) / 2, t['ask'], 1 - t['bid'], t.get('vol') or 0, t['side'], t.get('line'), t['event_id'], t['market'])
                tk = (tk, t['side'])                     # the logger writes a spread/total ticker once per side, mirrored
                if tk not in first or t['ts'] < first[tk][0]: first[tk] = rec
                if tk not in last or t['ts'] > last[tk][0]: last[tk] = rec
                series[tk].append(rec)
    best = {}
    for tk, L in last.items():
        F = first[tk]; ev, mk = L[7], L[8]; e = sched[ev]
        if parse_ts(e['start']) <= NOW or parse_ts(L[0]) < NOW - dt.timedelta(hours=2): continue
        mv = 100 * (L[1] - F[1])
        k = (ev, mk)
        # main line = most traded ticker; for moneylines the two team tickers mirror, so keep the busier one too
        if L[5] not in ('home', 'over'): continue          # one orientation per ticker (home / over), so each market counts once
        if k not in best or L[4] > best[k]['vol']:
            best[k] = dict(vol=L[4], mv=mv, F=F, L=L, tk=tk[0], st=steam_state(sorted(series[tk])))
    out = []; steams = []
    for (ev, mk), b in best.items():
        st = b['st']
        if st:
            e = sched[ev]; L = b['L']; yes = L[5]; up = st['dir'] > 0
            steams.append(dict(sport=e['sport'], league=e.get('league'), event_id=ev, away=e['away'], home=e['home'], start=e['start'], market=mk,
                               ticker=b['tk'], yes_side=yes, line=L[6], steam_side=yes if up else OTHER.get(yes), **{k: v for k, v in st.items() if k != 'dir'},
                               steam_yes=up, rev_side=OTHER.get(yes) if up else yes,
                               rev_cost=round(100 * (L[3] if up else L[2]), 1)))      # the reversal side's ask now (no-ask = 1 - yes bid)
        if abs(b['mv']) < MOVE_PTS: continue
        e = sched[ev]; F, L = b['F'], b['L']; yes = L[5]; toward_yes = b['mv'] > 0
        side = yes if toward_yes else OTHER.get(yes)
        line = L[6]
        if mk == 'spread' and line is not None and side != yes: line = -line
        out.append(dict(sport=e['sport'], league=e.get('league'), event_id=ev, away=e['away'], home=e['home'], away_name=(e.get('away_team') or {}).get('displayName'),
                        home_name=(e.get('home_team') or {}).get('displayName'), start=e['start'], market=mk, side=side, line=line, ticker=b['tk'],
                        open=round(100 * (F[1] if toward_yes else 1 - F[1]), 1), now=round(100 * (L[1] if toward_yes else 1 - L[1]), 1),
                        ask=round(100 * (L[2] if toward_yes else L[3]), 1), move=round(abs(b['mv']), 1), open_ts=F[0], now_ts=L[0],
                        state=(b['st'] or {}).get('state', 'drift'), steam_age_min=(b['st'] or {}).get('age_min')))
    out.sort(key=lambda r: r['start'])
    steams.sort(key=lambda r: r['start'])
    return out, steams


def steam_state(S):
    """S = time-sorted (ts, mid, ...) for one ticker side. The steam_timing.py definitions (docs/steam_timing_2026-11-01.md):
    steam = the first time the mid moved STEAM_PTS+ inside STEAM_MIN minutes; it has REVERSED once the mid gives back REV_FRAC of
    that move from the steam price. state: fresh (under 60 min old, not reversed: waiting beat chasing), held (60+ min, not reversed:
    fading it lost 15-25%), reversed (the bet-back candidate, paper-tracked as steam_rev). None when no steam."""
    if len(S) < 3: return None
    T = [parse_ts(x[0]) for x in S]; M = [x[1] for x in S]
    for i in range(len(S)):
        j = i - 1                                             # the last tick at least STEAM_MIN before tick i
        while j >= 0 and (T[i] - T[j]).total_seconds() < STEAM_MIN * 60: j -= 1
        if j < 0: continue
        k = j
        while k >= 0 and (T[i] - T[k]).total_seconds() <= STEAM_MIN * 60 + 1800: k -= 1   # not a stale gap: the earlier tick within 30 min of the window
        if (T[i] - T[j]).total_seconds() > STEAM_MIN * 60 + 1800: continue
        mv = 100 * (M[i] - M[j])
        if abs(mv) >= STEAM_PTS:
            d = 1 if mv > 0 else -1; lvl = M[i] - d * REV_FRAC * abs(M[i] - M[j]); rev_ts = None
            for q in range(i + 1, len(S)):
                if (M[q] - lvl) * d <= 0: rev_ts = S[q][0]; break
            age = (NOW - T[i]).total_seconds() / 60
            state = 'reversed' if rev_ts else ('held' if age >= 60 else 'fresh')
            return dict(dir=d, state=state, steam_ts=S[i][0], steam_from=round(100 * M[j], 1), steam_to=round(100 * M[i], 1), now_mid=round(100 * M[-1], 1),
                        rev_level=round(100 * lvl, 1), rev_ts=rev_ts, age_min=round(age))
    return None


def steam_paper(steams):
    """Pre-registered paper rule steam_rev (11/1): a Kalshi steam (STEAM_PTS+ in STEAM_MIN min) that gives back REV_FRAC of its move
    before the start -> the reversal side at its ask, logged on the first run within REV_FRESH minutes of the give-back, 5+ minutes
    before the start (the 20-minute tracker cadence; older reversals are listed but not logged).
    Graded on Kalshi's settlement. Backtest: +5.5% / +6.4% (3+ pts), +9.0% / +11.5% (5+ pts), train / October, z about 1."""
    import urllib.request
    have = {}
    if os.path.exists(PAPER):
        for l in open(PAPER): r = json.loads(l); have[(r['ticker'], r['steam_ts'])] = r
    new = []
    for s in steams:
        if s['state'] != 'reversed' or (s['ticker'], s['steam_ts']) in have: continue
        if (parse_ts(s['start']) - NOW).total_seconds() < 300 or not (2 < s['rev_cost'] < 98): continue
        if (NOW - parse_ts(s['rev_ts'])).total_seconds() > REV_FRESH * 60: continue      # the backtest entered at the give-back; older reversals are shown, not logged
        rec = dict(rule='steam_rev', ts=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), **{k: s[k] for k in ('sport', 'league', 'event_id', 'away', 'home', 'start', 'market', 'ticker',
                   'line', 'steam_ts', 'steam_from', 'steam_to', 'rev_level', 'rev_ts', 'rev_side', 'steam_side')}, bet_yes=not s['steam_yes'], price=s['rev_cost'])
        new.append(rec); have[(s['ticker'], s['steam_ts'])] = rec
    with open(PAPER, 'a') as f:                      # always exists, so the workflow's git add never fails on it
        for r in new: f.write(json.dumps(r) + '\n')
    graded = []; asked = 0
    cache = json.load(open(RESC)) if os.path.exists(RESC) else {}
    for r in have.values():
        if parse_ts(r['start']) > NOW - dt.timedelta(hours=3): continue
        res = cache.get(r['ticker'])
        if res is None and asked < 60:
            asked += 1
            try:
                m = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.elections.kalshi.com/trade-api/v2/markets/{r['ticker']}", headers={'User-Agent': 'sharp-tracker'}), timeout=20)).get('market') or {}
                if m.get('result') in ('yes', 'no'): res = cache[r['ticker']] = m['result']
            except Exception: pass
        if res not in ('yes', 'no'): continue
        won = (res == 'yes') == r['bet_yes']; p = r['price'] / 100
        graded.append(dict(r, won=won, pnl=round((1 - p) / p if won else -1.0, 3)))
    json.dump(cache, open(RESC, 'w'))
    rec = dict(n=len(graded), won=sum(g['won'] for g in graded), units=round(sum(g['pnl'] for g in graded), 2)) if graded else dict(n=0)
    return dict(record=rec, recent=sorted(graded, key=lambda g: g['start'])[-20:], new=len(new))


POLY_LEAGUES = {'NFL': 'nfl', 'NBA': 'nba', 'NHL': 'nhl', 'CFB': 'cfb', 'CBB': 'cbb', 'NCAAF': 'cfb', 'NCAAB': 'cbb'}   # Polymarket game lines (only NFL lists them today)
POLY_TYPES = {'moneyline': 'ml', 'spreads': 'spread', 'totals': 'total'}


def poly_trades(sched, agg, cut=None):
    """Polymarket taker trades on game lines (logged by loggers/polymarket.py from data-api.polymarket.com, which returns taker fills:
    BUY outcome X = a bet on X, SELL outcome X = a bet against X), added to the same per-market buckets as Kalshi, risk-equivalent size.
    Matched to our schedule by start time and team names. Pregame only; each trade counted once across snapshots.
    cut: optional {event_id: datetime} to count only trades before that time (sharp/strongest_backfill.py rebuilds the watch at T-1h)."""
    idx = collections.defaultdict(list)
    for ev, e in sched.items(): idx[(e['sport'], e['start'][:16])].append(ev)
    def name_side(e, nm):
        nm = (nm or '').lower().strip()
        for side in ('home', 'away'):
            t = e.get(side + '_team') or {}
            full = (t.get('displayName') or '').lower(); short = (t.get('shortDisplayName') or t.get('name') or '').lower()
            if nm and (full.endswith(nm) or nm == short or nm == full or nm == (e.get(side) or '').lower()): return side
        return None
    seen = set(); n = 0; root = os.path.join(ROOT, 'data', 'polymarket')
    for f in recent(root):
        try: fh = gzip.open(f, 'rt') if f.endswith('.gz') else open(f); lines = fh
        except OSError: continue
        try:
            for l in lines:
                if '"new_trades": [{' not in l or not any(f'"type": "{t}"' in l for t in POLY_TYPES): continue
                r = json.loads(l); sp = POLY_LEAGUES.get(r.get('league')); mk = POLY_TYPES.get(r.get('type'))
                if not sp or not mk or not r.get('start'): continue
                st = r['start'].replace(' ', 'T')[:16]
                cands = idx.get((sp, st)) or []
                sides = list((r.get('sides') or {}).keys())
                ev = None
                for c in cands:
                    e = sched[c]
                    if mk == 'total':
                        teams = [x.strip() for x in (r.get('title') or '').split(' vs. ')]
                        if len(teams) == 2 and {name_side(e, teams[0]), name_side(e, teams[1])} == {'home', 'away'}: ev = c; break
                    elif len(sides) == 2 and {name_side(e, sides[0]), name_side(e, sides[1])} == {'home', 'away'}: ev = c; break
                if not ev: continue
                e = sched[ev]; start_ts = parse_ts(e['start'])
                if r.get('event'): LINKS.setdefault(ev, {})['poly'] = f"https://polymarket.us/event/{r['event']}"
                for t in r['new_trades']:
                    k = (r.get('cond'), t.get('ts'), t.get('side'), t.get('outcome'), t.get('size'), t.get('p'))
                    if k in seen: continue
                    seen.add(k)
                    tt = dt.datetime.fromtimestamp(int(t['ts']), dt.timezone.utc)
                    if tt >= ((cut or {}).get(ev) or start_ts): continue
                    p = float(t['p']); usd = float(t['size']) * min(p, 1 - p)
                    if mk == 'total':
                        o = (t.get('outcome') or '').lower(); bet = o if t['side'] == 'BUY' else OTHER.get(o)
                        if bet not in ('over', 'under'): continue
                        line = r.get('line')
                    else:
                        os_ = name_side(e, t.get('outcome'))
                        if not os_: continue
                        bet = os_ if t['side'] == 'BUY' else OTHER[os_]
                        line = None
                        if mk == 'spread':
                            first = name_side(e, sides[0]); L = r.get('line')
                            if L is None or not first: continue
                            line = L if first == 'home' else -L          # home number, as for Kalshi
                    a = agg[(ev, mk, line)]; s_ = a['sides'][bet]
                    s_['all'] += usd; s_['n'] += 1
                    if usd >= BIG_USD: s_['big'] += usd; s_['n_big'] += 1
                    if usd <= SMALL_USD: s_['small'] += usd
                    a['venues'].add('Polymarket'); a['last'] = max(a['last'] or '', tt.strftime('%Y-%m-%dT%H:%M:%SZ')); n += 1
        except (EOFError, OSError): pass
    return n


def novig_trades(sched, agg, cut=None):
    """Novig live trades (data/novig/trades5, loggers/fast.py). Each row's outcome is the MAKER's side: checked against Novig's public
    taker tape (sharp/novig_verify.py, 11/1: the taker took the other outcome on 1,547 of 1,548 matched trades, $500+ 29 of 29, at
    1 - the row's price). So the bet is the other side at 1 - price; size is risk-equivalent like Kalshi: contracts x min(p, 1-p).
    Lines are the home number (spreads) or the total, as the Kalshi buckets. Pregame only; each trade counted once."""
    seen = set(); n = 0
    for f in recent(os.path.join(ROOT, 'data', 'novig', 'trades5')):
        try:
            for l in gzip.open(f, 'rt'):
                try: t = json.loads(l)
                except Exception: continue
                ev = t.get('event_id'); e = sched.get(ev); mk = t.get('market')
                if not e or mk not in ('ml', 'spread', 'total') or t.get('trade_id') in seen: continue
                if e['sport'] == 'soccer' and mk == 'ml': continue
                seen.add(t.get('trade_id'))
                tt = dt.datetime.fromtimestamp(int(t['ts']) / 1000, dt.timezone.utc)
                if tt >= ((cut or {}).get(ev) or parse_ts(e['start'])): continue
                side = OTHER.get(t.get('side_if_taker'))
                if not side: continue
                p = float(t['price']); usd = t['qty_cents'] / 100 * min(p, 1 - p)
                line = None if mk == 'ml' else t.get('line')
                a = agg[(ev, mk, line)]; s_ = a['sides'][side]
                s_['all'] += usd; s_['n'] += 1
                if usd >= BIG_USD: s_['big'] += usd; s_['n_big'] += 1
                if usd <= SMALL_USD: s_['small'] += usd
                a['venues'].add('Novig'); a['last'] = max(a['last'] or '', tt.strftime('%Y-%m-%dT%H:%M:%SZ')); n += 1
        except (EOFError, OSError): pass
    return n


def main():
    sched = {}
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'cbb', 'soccer', 'mma'):
        p = os.path.join(ROOT, 'data', sp, 'schedule.json')
        if os.path.exists(p):
            for k, v in json.load(open(p)).items(): sched[k] = dict(v, sport=sp)
    agg = collections.defaultdict(lambda: dict(sides=collections.defaultdict(lambda: dict(big=0.0, small=0.0, all=0.0, n=0, n_big=0)), venues=set(), last=None))
    for f in recent(os.path.join(ROOT, 'data', 'kalshi', 'trades5')):
        for l in gzip.open(f, 'rt'):
            try: t = json.loads(l)
            except Exception: continue
            e = sched.get(t.get('event_id'))
            if not e or t.get('market') not in ('ml', 'spread', 'total') or not t.get('yes_side'): continue
            if e['sport'] == 'soccer' and t['market'] == 'ml': continue      # three-way: a 'no' on one team is not a bet on the other
            if parse_ts(t['ts']) >= parse_ts(e['start']): continue      # pregame only
            yes = t['taker_side'] == 'yes'; side = t['yes_side'] if yes else OTHER.get(t['yes_side'])
            if not side: continue
            # size = risk-equivalent dollars: the stake on the cheaper side, the to-win on the dearer side (count x min(p, 1-p)), so a
            # $9,000 bet on a -900 favorite (to win $1,000) counts the same as $1,000 on the +900 dog; at -110 it is about the stake
            yp = t['yes_price']; usd = t['count'] * min(yp, 1 - yp)
            line = None if t['market'] == 'ml' else (t['line'] if t['market'] == 'total' or t['yes_side'] == 'home' else -t['line'])   # home number: Kalshi's line is the YES team's own number (fixed 11/1: was flipped by the bet side, which split no-takers onto the wrong line)
            k = (t['event_id'], t['market'], line); a = agg[k]; s = a['sides'][side]
            s['all'] += usd; s['n'] += 1
            if usd >= BIG_USD: s['big'] += usd; s['n_big'] += 1
            if usd <= SMALL_USD: s['small'] += usd
            a['venues'].add('Kalshi'); a['last'] = max(a['last'] or '', t['ts'])
    n_poly = poly_trades(sched, agg)
    n_novig = novig_trades(sched, agg) if NOVIG_VERIFIED else 0
    # main line per game x market = the line with the most dollars
    best = {}
    for (ev, mk, line), a in agg.items():
        tot = sum(s['all'] for s in a['sides'].values())
        if (ev, mk) not in best or tot > best[(ev, mk)][1]: best[(ev, mk)] = (line, tot, a)
    rows = []
    for (ev, mk), (line, tot, a) in best.items():
        e = sched[ev]
        if parse_ts(e['start']) <= NOW: continue
        sides = a['sides']; names = ('over', 'under') if mk == 'total' else ('home', 'away')
        s1, s2 = sides.get(names[0], dict(big=0, small=0, all=0, n=0, n_big=0)), sides.get(names[1], dict(big=0, small=0, all=0, n=0, n_big=0))
        lead = names[0] if s1['big'] >= s2['big'] else names[1]; lo = names[1] if lead == names[0] else names[0]
        L_, O_ = sides.get(lead, {}), sides.get(lo, {})
        big_net = (L_.get('big', 0) - O_.get('big', 0)); small_net = (L_.get('small', 0) - O_.get('small', 0))
        rows.append(dict(sport=e['sport'], league=e.get('league'), event_id=ev, away=e['away'], home=e['home'], away_name=(e.get('away_team') or {}).get('displayName'), home_name=(e.get('home_team') or {}).get('displayName'),
                         start=e['start'], market=mk, line=line, big_side=lead, big_net=round(big_net), small_net=round(small_net), big_fills=L_.get('n_big', 0) + O_.get('n_big', 0),
                         total=round(tot), fills=s1['n'] + s2['n'], divergent=bool(big_net >= DIV_USD and small_net < 0), show=bool(tot >= SHOW_TOTAL and big_net >= SHOW_BIG), venues=sorted(a['venues']), last=a['last'],
                         sides={k: {kk: round(vv) for kk, vv in v.items()} for k, v in sides.items()}))
    rows.sort(key=lambda r: (-int(r['divergent']), -r['big_net']))
    moves, steams = kalshi_moves(sched)
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'cbb', 'soccer', 'mma'):          # Action Network game pages (loggers/lines.py)
        try:
            for ev, u in json.load(open(os.path.join(ROOT, 'data', sp, 'an_links.json'))).items():
                if ev in sched and parse_ts(sched[ev]['start']) > NOW: LINKS.setdefault(ev, {})['an'] = u
        except Exception: pass
    links = {ev: v for ev, v in LINKS.items() if ev in sched and parse_ts(sched[ev]['start']) > NOW}
    sp = steam_paper(steams)
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), big_usd=BIG_USD, small_usd=SMALL_USD, div_usd=DIV_USD, novig_included=NOVIG_VERIFIED, rows=rows,
                   show_total=SHOW_TOTAL, show_big=SHOW_BIG, move_pts=MOVE_PTS, moves=moves, links=links,
                   steam=dict(pts=STEAM_PTS, minutes=STEAM_MIN, rev_frac=REV_FRAC, rows=steams, **sp)),
              open(OUT, 'w'), separators=(',', ':'))
    print(f"[flow_live] steam: {len(steams)} upcoming markets with a {STEAM_PTS}+ pt / {STEAM_MIN}-min move ({collections.Counter(x['state'] for x in steams)}); steam_rev paper {sp['new']} new, record {sp['record']}")
    print(f"[flow_live] {len(moves)} upcoming Kalshi markets moved {MOVE_PTS}+ pts since their first two-sided price")
    print(f"[flow_live] {n_poly} Polymarket and {n_novig} Novig pregame taker trades added")
    print(f"[flow_live] {len(rows)} upcoming game markets with exchange flow; {sum(r['divergent'] for r in rows)} divergent (big >= ${DIV_USD:,.0f} one way, small money the other)")


if __name__ == '__main__':
    main()
