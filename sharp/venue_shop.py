#!/usr/bin/env python3
"""Line shopping across the venues Sean bets (Sean 11/6: "needs to include Novig and Kalshi and Polymarket too"). Our own tape
(data/<sport>/ticks), every game's main lines (Pinnacle's number) at about one hour before the start: each venue's cost to take the side
(books at their price, Novig at 1 - the other side's best bid, Kalshi at the ask plus the taker fee, Polymarket at the ask) against
Pinnacle's no-vig fair. Expected value per venue, how often each venue is the best, and what best-of-all adds over best-of-books and over
one book. Writes data/research/venue_shop.json. Usage: python3 sharp/venue_shop.py [days]"""
import os, sys, json, gzip, glob, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
V = ('Novig', 'Kalshi', 'Polymarket', 'FD', 'Caesars', 'DK')
BOOKS = ('FD', 'Caesars', 'DK')
OPP = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def cost(r):
    if r.get('american') is not None:
        a = r['american']; return 1 / (1 + (a / 100 if a > 0 else 100 / -a))
    a = r.get('ask')
    if a is None or not 0.02 < a < 0.98: return None
    if r['venue'] == 'Kalshi': a = a + math.ceil(0.07 * a * (1 - a) * 100) / 100
    return a


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime('%Y-%m-%d')
    out = []
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'cbb'):
        try: sched = json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json')))
        except Exception: continue
        R = collections.defaultdict(list); WIN = {}
        for k, e in sched.items():
            try: s0 = ts(e['start'].replace('Z', ':00Z') if len(e['start']) == 17 else e['start'])
            except Exception: continue
            WIN[k] = ((s0 - dt.timedelta(minutes=105)).strftime('%Y-%m-%dT%H:%M:%S'), (s0 - dt.timedelta(minutes=60)).strftime('%Y-%m-%dT%H:%M:%S'))
        for f in sorted(glob.glob(os.path.join(ROOT, 'data', sp, 'ticks', '*.jsonl.gz'))):
            if os.path.basename(f)[:10] < since: continue
            try:
                for l in gzip.open(f, 'rt'):
                    if '"ml"' not in l and '"spread"' not in l and '"total"' not in l: continue
                    r = json.loads(l); w = WIN.get(r.get('event_id'))
                    if not w or not (w[0] <= r['ts'][:19] <= w[1]): continue
                    if r.get('market') in ('ml', 'spread', 'total') and (r['venue'] in V or r['venue'] == 'Pinnacle'): R[r['event_id']].append(r)
            except (EOFError, OSError): pass
        for ev, L in R.items():
            e = sched.get(ev)
            if not e: continue
            st = ts(e['start'].replace('Z', ':00Z') if len(e['start']) == 17 else e['start']); T = st - dt.timedelta(minutes=60)
            W = [r for r in L if T - dt.timedelta(minutes=45) <= ts(r['ts']) <= T]       # quotes in the 45 minutes before T-60
            last = {}
            for r in sorted(W, key=lambda r: r['ts']): last[(r['venue'], r['market'], r.get('line'), r['side'])] = r
            for mk in ('ml', 'spread', 'total'):
                P = {k[3]: (k[2], v) for k, v in last.items() if k[0] == 'Pinnacle' and k[1] == mk}
                if mk == 'ml': P = {s: (None, v) for s, (_, v) in P.items()}
                for side in (('home', 'away') if mk != 'total' else ('over', 'under')):
                    if side not in P or OPP[side] not in P: continue
                    ln, pr = P[side]; lo, po = P[OPP[side]]
                    if mk == 'spread' and (ln is None or lo != -ln): continue
                    if mk == 'total' and (ln is None or lo != ln): continue
                    ca, cb = cost(pr), cost(po)
                    if not ca or not cb: continue
                    fair = (ca) / (ca + cb)
                    row = dict(sport=sp, mk=mk, fair=fair)
                    for v in V:
                        r = last.get((v, mk, ln if mk != 'ml' else None, side))
                        c = cost(r) if r else None
                        if c: row[v] = fair / c - 1           # expected value per $1 at that venue
                    if sum(1 for v in V if v in row) >= 2: out.append(row)
    print('sides priced at 2+ venues:', len(out))
    def m(L): return round(100 * sum(L) / len(L), 2) if L else None
    res = dict(n=len(out))
    res['ev_by_venue'] = {v: dict(n=sum(1 for r in out if v in r), ev=m([r[v] for r in out if v in r])) for v in V}
    best = collections.Counter(max((v for v in V if v in r), key=lambda v: r[v]) for r in out)
    res['best_venue_share'] = {v: round(100 * best[v] / len(out), 1) for v in V}
    both = [r for r in out if any(b in r for b in BOOKS) and any(v in r for v in ('Novig', 'Kalshi', 'Polymarket'))]
    res['same_sides'] = dict(n=len(both), best_of_all=m([max(r[v] for v in V if v in r) for r in both]),
                             best_of_books=m([max(r[b] for b in BOOKS if b in r) for r in both]),
                             novig_only=m([r['Novig'] for r in both if 'Novig' in r]), dk_only=m([r['DK'] for r in both if 'DK' in r]),
                             best_exchange=m([max(r[v] for v in ('Novig', 'Kalshi', 'Polymarket') if v in r) for r in both]))
    for mk in ('ml', 'spread', 'total'):
        L = [r for r in out if r['mk'] == mk]; bb = collections.Counter(max((v for v in V if v in r), key=lambda v: r[v]) for r in L)
        res[f'best_venue_share {mk}'] = {v: round(100 * bb[v] / max(1, len(L)), 1) for v in V}
        res[f'ev_by_venue {mk}'] = {v: m([r[v] for r in L if v in r]) for v in V}
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(ROOT, 'data', 'research', 'venue_shop.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
