#!/usr/bin/env python3
"""Live big-money vs small-money split on upcoming games (watch signal, tier C; backtest: sharp/flow_split.py,
docs/flow_split_2026-10-31.md).

Per upcoming game x market (moneyline, main spread, main total), from every pregame taker fill logged so far:
  size of a fill = risk-equivalent dollars, contracts x min(price, 1 - price): the stake on a dog, the to-win on a favorite
  big   = such dollars in fills of BIG_USD or more, per side   small = in fills of SMALL_USD or less, per side
  big_net = big dollars on the leading side minus the other side; small_net likewise (signed toward the big side)
  divergent = big money and small money on opposite sides with big_net >= DIV_USD (the backtest's best shape)
Sources: Kalshi trades (data/kalshi/trades5, taker side explicit). Novig live trades (data/novig/trades5) are logged but only used
once NOVIG_VERIFIED is set: the API does not say whether a trade's outcome is the taker's, so it is checked against the next-day
public tape (which labels taker/maker) first.
Writes data/state/flow_live.json."""
import os, sys, json, gzip, glob, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.norm import parse_ts
BIG_USD = 500.0; SMALL_USD = 50.0; DIV_USD = 1000.0; NOVIG_VERIFIED = False
OUT = os.path.join(ROOT, 'data', 'state', 'flow_live.json')
OTHER = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}
NOW = dt.datetime.now(dt.timezone.utc)


def recent(d, days=8):
    cut = (NOW - dt.timedelta(days=days)).date().isoformat()
    return [f for f in sorted(glob.glob(os.path.join(d, '*.jsonl.gz'))) if os.path.basename(f)[:10] >= cut]


def main():
    sched = {}
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'soccer', 'mma'):
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
            line = None if t['market'] == 'ml' else (t['line'] if side in ('home', 'over') or t['market'] == 'total' else -t['line'])   # home / over number
            k = (t['event_id'], t['market'], line); a = agg[k]; s = a['sides'][side]
            s['all'] += usd; s['n'] += 1
            if usd >= BIG_USD: s['big'] += usd; s['n_big'] += 1
            if usd <= SMALL_USD: s['small'] += usd
            a['venues'].add('Kalshi'); a['last'] = max(a['last'] or '', t['ts'])
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
        rows.append(dict(sport=e['sport'], event_id=ev, away=e['away'], home=e['home'], away_name=(e.get('away_team') or {}).get('displayName'), home_name=(e.get('home_team') or {}).get('displayName'),
                         start=e['start'], market=mk, line=line, big_side=lead, big_net=round(big_net), small_net=round(small_net), big_fills=L_.get('n_big', 0) + O_.get('n_big', 0),
                         total=round(tot), fills=s1['n'] + s2['n'], divergent=bool(big_net >= DIV_USD and small_net < 0), venues=sorted(a['venues']), last=a['last'],
                         sides={k: {kk: round(vv) for kk, vv in v.items()} for k, v in sides.items()}))
    rows.sort(key=lambda r: (-int(r['divergent']), -r['big_net']))
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), big_usd=BIG_USD, small_usd=SMALL_USD, div_usd=DIV_USD, novig_included=NOVIG_VERIFIED, rows=rows),
              open(OUT, 'w'), separators=(',', ':'))
    print(f"[flow_live] {len(rows)} upcoming game markets with Kalshi flow; {sum(r['divergent'] for r in rows)} divergent (big >= ${DIV_USD:,.0f} one way, small money the other)")


if __name__ == '__main__':
    main()
