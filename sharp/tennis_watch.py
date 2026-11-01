#!/usr/bin/env python3
"""Live watch list for the pre-registered tennis first-set rule tennis_fs_fav (docs/tennis_firstset_2026-11-01.md), and its paper log.

For every upcoming tennis match in the latest tick snapshots (data/tennis/ticks + ticks5):
  match favourite = Pinnacle's no-vig match price (falls back to the Kalshi / Novig match mid when Pinnacle has no line)
  fair set-1 price for the favourite = independent-sets model + 3.3 points (the Novig + ESPN gap), never above the match price
  best bettable set-1 price = the lowest cost of the favourite's set 1 at Kalshi (ask + taker fee) or Novig (ask); Pinnacle's set-1
  no-vig price is shown as the sharp reference, not as a place to bet
A match is flagged when the favourite is 55%+ on the match and fair minus cost is 1 point or more. The first time a match is
flagged it is written to data/tennis/fs_paper.jsonl (price, venue, Pinnacle set-1 reference) and graded later from the ESPN result.
Writes data/state/tennis_watch.json. Usage: python3 sharp/tennis_watch.py"""
import os, sys, json, gzip, glob, math, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
TD = os.path.join(ROOT, 'data', 'tennis'); OUT = os.path.join(ROOT, 'data', 'state', 'tennis_watch.json'); PAPER = os.path.join(TD, 'fs_paper.jsonl')
NOW = dt.datetime.now(dt.timezone.utc); GAP = 0.033; MIN_FAV = 0.55; MIN_EDGE = 0.01; KFEE = 0.07; STALE_MIN = 45


def s_from_match(p):
    lo, hi = 0.0, 1.0
    for _ in range(50):
        m = (lo + hi) / 2
        if m * m * (3 - 2 * m) < p: lo = m
        else: hi = m
    return (lo + hi) / 2


def implied(a): return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def latest():
    """(event, market, venue, side) -> latest tick within STALE_MIN."""
    L = {}
    for d in ('ticks', 'ticks5'):
        for f in sorted(glob.glob(os.path.join(TD, d, '*.jsonl.gz')))[-2:]:
            try:
                for l in gzip.open(f, 'rt'):
                    r = json.loads(l)
                    if r['market'] not in ('ml', '1s_ml'): continue
                    k = (r['event_id'], r['market'], r['venue'], r['side'])
                    if k not in L or r['ts'] > L[k]['ts']: L[k] = r
            except (EOFError, OSError): pass
    return {k: v for k, v in L.items() if (NOW - ts(v['ts'])).total_seconds() <= STALE_MIN * 60}


def novig_pin_p(L, ev, mk, side):
    h, a = L.get((ev, mk, 'Pinnacle', 'home')), L.get((ev, mk, 'Pinnacle', 'away'))
    if h and a and h.get('american') and a.get('american'):
        ph, pa = implied(h['american']), implied(a['american']); p = ph / (ph + pa)
        return p if side == 'home' else 1 - p
    return None


def mid(L, ev, mk, venue, side):
    r = L.get((ev, mk, venue, side))
    if r and r.get('bid') and r.get('ask') and r['ask'] - r['bid'] <= 0.06: return (r['bid'] + r['ask']) / 2
    return None


def main():
    E = json.load(open(os.path.join(TD, 'events.json'))) if os.path.exists(os.path.join(TD, 'events.json')) else {}
    L = latest(); evs = {k[0] for k in L}
    paper = {}
    if os.path.exists(PAPER):
        for l in open(PAPER): r = json.loads(l); paper[r['event_id']] = r
    rows = []; new = []
    for ev in evs:
        e = E.get(ev)
        if not e or ts(e['start']) <= NOW: continue
        pm = novig_pin_p(L, ev, 'ml', 'home'); src = 'Pinnacle'
        if pm is None:
            pm = mid(L, ev, 'ml', 'Kalshi', 'home') or mid(L, ev, 'ml', 'Novig', 'home'); src = 'exchange mid'
        if pm is None: continue
        fav = 'home' if pm >= 0.5 else 'away'; pf = pm if fav == 'home' else 1 - pm
        model = s_from_match(pf); fair = min(model + GAP, pf)
        cands = []
        for v in ('Kalshi', 'Novig'):
            r = L.get((ev, '1s_ml', v, fav))
            if not r or not r.get('ask') or 'oneside' in (r.get('flags') or []): continue
            cost = r['ask'] + (math.ceil(KFEE * r['ask'] * (1 - r['ask']) * 100) / 100 if v == 'Kalshi' else 0)
            cands.append(dict(venue=v, ask=r['ask'], cost=round(cost, 4), ticker=(r.get('extra') or {}).get('ticker')))
        best = min(cands, key=lambda c: c['cost']) if cands else None
        pin1 = novig_pin_p(L, ev, '1s_ml', fav)
        name = (e.get('home_team') if fav == 'home' else e.get('away_team') or {}).get('displayName') if e else None
        opp = (e.get('away_team') if fav == 'home' else e.get('home_team') or {}).get('displayName') if e else None
        row = dict(event_id=ev, start=e['start'], tour=e.get('tour'), tournament=e.get('tournament'), fav=fav, fav_name=name, opp_name=opp,
                   match_p=round(pf, 4), match_src=src, model=round(model, 4), fair=round(fair, 4), pin_set1=round(pin1, 4) if pin1 else None,
                   best=best, edge=round(fair - best['cost'], 4) if best else None)
        row['flag'] = bool(best and pf >= MIN_FAV and row['edge'] >= MIN_EDGE)
        rows.append(row)
        if row['flag'] and ev not in paper:
            rec = dict(event_id=ev, ts=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), start=e['start'], fav=fav, fav_name=name, opp_name=opp, match_p=row['match_p'],
                       fair=row['fair'], venue=best['venue'], price=best['cost'], pin_set1=row['pin_set1'], rule='tennis_fs_fav')
            new.append(rec); paper[ev] = rec
    if new:
        with open(PAPER, 'a') as f:
            for r in new: f.write(json.dumps(r) + '\n')
    # grade paper entries from ESPN (ESPN ids only; x: matches stay ungraded until a Kalshi/Novig settlement path is added)
    res = {}
    rp = os.path.join(TD, 'results.jsonl')
    if os.path.exists(rp):
        for l in open(rp): r = json.loads(l); res[r['match_id']] = r
    graded = []
    for ev, p in paper.items():
        r = res.get(ev)
        if not r or not r.get('first_set_complete') or not r.get('first_set_winner'): continue
        won = (r['first_set_winner'] == 'p1') == (p['fav'] == 'home')
        graded.append(dict(p, won=won, pnl=round((1 - p['price']) / p['price'] if won else -1.0, 3)))
    rows.sort(key=lambda r: (not r['flag'], r['start']))
    rec = dict(n=len(graded), won=sum(g['won'] for g in graded), units=round(sum(g['pnl'] for g in graded), 2)) if graded else dict(n=0)
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), gap=GAP, min_fav=MIN_FAV, min_edge=MIN_EDGE, record=rec, recent=sorted(graded, key=lambda g: g['start'])[-25:],
                   rows=rows), open(OUT, 'w'), separators=(',', ':'))
    print(f"[tennis watch] {len(rows)} upcoming matches priced, {sum(r['flag'] for r in rows)} flagged, {len(new)} new paper entries; record {rec}")


if __name__ == '__main__':
    main()
