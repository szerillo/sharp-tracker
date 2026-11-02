#!/usr/bin/env python3
"""Rebuild the Today page's sharp-money watch for past games, as it would have read 1 hour before each start, and grade it
(Sean, 11/1: "how many sharp money bets over the last 2 days would have fallen under Strongest?").

At T = start - 1h, per game x market (main line):
  PRICE  sharp move: notable move on the move tape (Pinnacle origin, or $1k+ Kalshi fills with it) with ts in [T-6h, T]
         Kalshi move: Kalshi two-sided mid moved 4+ pts from its first tight print to T (state from flow_live.steam_state)
         bet back:    a 3+ pt / 60-min Kalshi steam that gave back 40% by T (reversal side)
  MONEY  big vs small: Kalshi + Polymarket taker fills before T, risk-equivalent, $500+ net $1,000+ one way with small
         money ($50 and under) the other way, above the display floor ($10k traded, $2.5k big net)
Strongest = price (one side) and money agree, or any signal on a system bet (system_fired.json) for that market.
A Kalshi move that gave back is folded into its bet-back row (same story), as on the page.
Graded at the line (results.jsonl); Kalshi ask at T reported for moneylines. Writes data/research/strongest_backfill.json.
Usage: python3 sharp/strongest_backfill.py [days back, default 2]"""
import os, sys, json, gzip, glob, bisect, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp import flow_live as FL
from sharp.norm import parse_ts
OTHER = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 2
NOW = dt.datetime.now(dt.timezone.utc); SINCE = NOW - dt.timedelta(days=DAYS)


def main():
    sched = {}
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'cbb', 'soccer'):
        p = os.path.join(ROOT, 'data', sp, 'schedule.json')
        if os.path.exists(p):
            for k, v in json.load(open(p)).items(): sched[k] = dict(v, sport=sp)
    games = {ev: e for ev, e in sched.items() if SINCE <= parse_ts(e['start']) <= NOW - dt.timedelta(hours=3)}
    T = {ev: parse_ts(e['start']) - dt.timedelta(hours=1) for ev, e in games.items()}
    res = {}
    for l in open(os.path.join(ROOT, 'data', 'state', 'results.jsonl')):
        try: r = json.loads(l)
        except Exception: continue
        if r.get('status') == 'final' and r.get('home_score') is not None: res[r['event_id']] = (r['home_score'], r['away_score'])
    # ---- money: Kalshi trades5 + Polymarket, before T
    agg = collections.defaultdict(lambda: dict(sides=collections.defaultdict(lambda: dict(big=0.0, small=0.0, all=0.0, n=0, n_big=0)), venues=set(), last=None))
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'kalshi', 'trades5', '*.jsonl.gz'))):
        try:
            for l in gzip.open(f, 'rt'):
                t = json.loads(l); ev = t.get('event_id')
                if ev not in games or t.get('market') not in ('ml', 'spread', 'total') or not t.get('yes_side'): continue
                if games[ev]['sport'] == 'soccer' and t['market'] == 'ml': continue
                if parse_ts(t['ts']) >= T[ev]: continue
                yes = t['taker_side'] == 'yes'; side = t['yes_side'] if yes else OTHER.get(t['yes_side'])
                if not side: continue
                yp = t['yes_price']; usd = t['count'] * min(yp, 1 - yp)
                line = None if t['market'] == 'ml' else (t['line'] if side in ('home', 'over') or t['market'] == 'total' else -t['line'])
                a = agg[(ev, t['market'], line)]; s = a['sides'][side]
                s['all'] += usd; s['n'] += 1
                if usd >= FL.BIG_USD: s['big'] += usd; s['n_big'] += 1
                if usd <= FL.SMALL_USD: s['small'] += usd
        except (EOFError, OSError): pass
    FL.NOW = NOW; npoly = FL.poly_trades(games, agg, cut=T)       # Polymarket taker fills before T, same buckets as Kalshi
    print(f"[strongest backfill] {npoly} Polymarket trades before T-1h added")
    money = {}
    best = {}
    for (ev, mk, line), a in agg.items():
        tot = sum(s['all'] for s in a['sides'].values())
        if (ev, mk) not in best or tot > best[(ev, mk)][1]: best[(ev, mk)] = (line, tot, a)
    for (ev, mk), (line, tot, a) in best.items():
        names = ('over', 'under') if mk == 'total' else ('home', 'away'); sd = a['sides']
        s1, s2 = sd.get(names[0], dict(big=0, small=0)), sd.get(names[1], dict(big=0, small=0))
        lead = names[0] if s1['big'] >= s2['big'] else names[1]; lo = OTHER[lead]
        bn = sd.get(lead, {}).get('big', 0) - sd.get(lo, {}).get('big', 0); sn = sd.get(lead, {}).get('small', 0) - sd.get(lo, {}).get('small', 0)
        if bn >= FL.DIV_USD and sn < 0 and tot >= FL.SHOW_TOTAL and bn >= FL.SHOW_BIG:
            money[(ev, mk)] = dict(side=lead, line=line, big_net=round(bn), small_net=round(sn), total=round(tot))
    # ---- price: move tape (notable, ts in [T-6h, T])
    price = collections.defaultdict(list)
    for l in gzip.open(os.path.join(ROOT, 'data', 'state', 'moves.jsonl.gz'), 'rt'):
        m = json.loads(l); ev = m['event_id']
        if ev not in games: continue
        k_ = m.get('kalshi') or {}
        if not (m['origin'] == 'Pinnacle' or (k_.get('big_n') and (k_.get('big_net') or 0) > 0)): continue
        ts = parse_ts(m['ts'])
        if not (T[ev] - dt.timedelta(hours=6) <= ts <= T[ev]): continue
        price[(ev, m['market'])].append(dict(kind='move', side=m['side'], line=m['line']))
    # ---- price: Kalshi movers and bet-backs from the tick tape, as of T
    series = collections.defaultdict(list)
    for sp in {e['sport'] for e in games.values()}:
        for d in ('ticks', 'ticks5'):
            for f in sorted(glob.glob(os.path.join(ROOT, 'data', sp, d, '*.jsonl.gz'))):
                try:
                    for l in gzip.open(f, 'rt'):
                        if '"Kalshi"' not in l: continue
                        t = json.loads(l); ev = t.get('event_id')
                        if ev not in games or t.get('market') not in ('ml', 'spread', 'total') or t.get('bid') is None or t.get('ask') is None: continue
                        if games[ev]['sport'] == 'soccer' and t['market'] == 'ml': continue
                        if not (0 < t['ask'] - t['bid'] <= FL.TIGHT) or t['side'] not in ('home', 'over'): continue
                        if parse_ts(t['ts']) > T[ev]: continue
                        tk = (t.get('extra') or {}).get('ticker')
                        if tk: series[(ev, t['market'], tk)].append((t['ts'], (t['bid'] + t['ask']) / 2, t['ask'], 1 - t['bid'], t.get('vol') or 0, t['side'], t.get('line')))
                except (EOFError, OSError): pass
    main_tk = {}
    for (ev, mk, tk), S in series.items():
        S.sort(); v = S[-1][4]
        if (ev, mk) not in main_tk or v > main_tk[(ev, mk)][1]: main_tk[(ev, mk)] = (tk, v)
    for (ev, mk), (tk, _) in main_tk.items():
        S = series[(ev, mk, tk)]
        if len(S) < 3: continue
        FL.NOW = T[ev]; st = FL.steam_state(S)
        yes = S[-1][5]; mv = 100 * (S[-1][1] - S[0][1])
        line = S[-1][6]
        if abs(mv) >= FL.MOVE_PTS:
            side = yes if mv > 0 else OTHER[yes]
            price[(ev, mk)].append(dict(kind='kmove', side=side, line=line, state=(st or {}).get('state', 'drift'), ask=round(100 * (S[-1][2] if mv > 0 else S[-1][3]), 1)))
        if st and st['state'] == 'reversed':
            rev = OTHER[yes] if st['dir'] > 0 else yes
            price[(ev, mk)].append(dict(kind='back', side=rev, line=line, ask=round(100 * (S[-1][3] if st['dir'] > 0 else S[-1][2]), 1)))
    # ---- system bets on file
    sysb = collections.defaultdict(list)
    fired = json.load(open(os.path.join(ROOT, 'data', 'state', 'system_fired.json')))
    for k, f in fired.items():
        if f.get('fill_id') and not f.get('void'): sysb[(k.split(':')[0], f['market'].replace('1h_', ''))].append(f['side'])
    # ---- classify, grade
    rows = []
    for key in set(price) | set(money):
        ev, mk = key; e = games[ev]
        P = price.get(key, []); backs = [x for x in P if x['kind'] == 'back']
        P = [x for x in P if not (x['kind'] == 'kmove' and x.get('state') == 'reversed' and backs)]
        ps = {x['side'] for x in P}; mo = money.get(key)
        sides = ps | ({mo['side']} if mo else set())
        if len(sides) != 1: cls = 'mixed'
        elif P and mo: cls = 'strongest'
        else: cls = 'single'
        side = next(iter(sides)) if len(sides) == 1 else None
        on_sys = side is not None and side in sysb.get(key, [])
        if on_sys and cls == 'single': cls = 'strongest (system bet)'
        line = (mo or {}).get('line') if mo else None
        if line is None and P:
            x = P[0]; line = x.get('line')        # tick-tape lines are already the home number for spreads (series uses home-side ticks)
        g = None; sc = res.get(ev)
        if sc and side:
            hs, as_ = sc
            if mk == 'ml': g = 'P' if hs == as_ else ('W' if (hs > as_) == (side == 'home') else 'L')
            elif mk == 'total' and line is not None: t_ = hs + as_; g = 'P' if t_ == line else ('W' if (t_ > line) == (side == 'over') else 'L')
            elif mk == 'spread' and line is not None: m_ = hs - as_ + line; g = 'P' if m_ == 0 else ('W' if (m_ > 0) == (side == 'home') else 'L')
        rows.append(dict(event_id=ev, sport=e['sport'], game=f"{e['away']}@{e['home']}", start=e['start'], market=mk, cls=cls, side=side, line=line,
                         price=[x['kind'] + ('/' + x['state'] if x.get('state') else '') for x in P], money=mo, ask=next((x.get('ask') for x in P if x.get('ask')), None), result=g))
    rows.sort(key=lambda r: r['start'])
    by = collections.Counter(r['cls'] for r in rows)
    print(f"[strongest backfill] {len(games)} games started {SINCE:%m/%d %H:%M}Z to now-3h; {len(rows)} game x markets with a watch signal at T-1h: {dict(by)}")
    for r in rows:
        if r['cls'].startswith('strongest'):
            print(f"  {r['start'][5:16]} {r['sport']:6} {r['game']:12} {r['market']:6} {r['side']:5} line {r['line']}  price {r['price']} money {r['money'] and r['money']['big_net']}  ask {r['ask']}  -> {r['result']}")
    rec = collections.defaultdict(collections.Counter)
    for r in rows:
        if r['result']: rec[r['cls']][r['result']] += 1
    print('  graded:', {k: dict(v) for k, v in rec.items()})
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), days=DAYS, games=len(games), counts=dict(by), graded={k: dict(v) for k, v in rec.items()}, rows=rows),
              open(os.path.join(ROOT, 'data', 'research', 'strongest_backfill.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
