#!/usr/bin/env python3
"""Snapshot of every sharp-money watch signal per game x market, frozen at the start, so "the signals agree" vs "they conflict"
(a steam and a bet-back, big money one way and a move the other) can be graded later (Sean, 11/1: conflicting rows on the
Today page; does either side carry signal, or do they cancel?).

Same signal definitions as the Today page (index.html renderToday):
  move   notable move in the last 6 hours (Pinnacle origin, or $1k+ Kalshi fills with it)       moves.json
  big    big vs small divergent, above the display floor                                          flow_live.json rows
  kmove  Kalshi 4+ pts since its first price, with its steam state                                flow_live.json moves
  back   steam that gave back 40% (the reversal side)                                             flow_live.json steam
Each tracker run overwrites the pregame snapshot (data/state/signal_snap.json); the first run after the start appends the last
pregame snapshot to data/research/signal_log.jsonl and drops it from the snapshot file. Grading (agree / conflict / single, by kind,
against results and the close) is a later script once there are enough games.
Lines are logged as the home number for spreads and the total for totals (sharp/signal_grade.py grades them).
Each signal keeps `first`, the first run it was seen on that side (shown on the Today page as "first seen"). When a snapshot is
frozen, each signal gets Pinnacle's devigged price on its side and line at `first` (p_first) and at the start (p_close), from the
tick database built earlier in the same tracker run: clv = p_close - p_first, in points, the main test for top-down signals.
Usage: python3 sharp/signal_log.py"""
import os, sys, json, sqlite3, datetime as dt
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
ST = os.path.join(ROOT, 'data', 'state'); SNAP = os.path.join(ST, 'signal_snap.json'); LOG = os.path.join(ROOT, 'data', 'research', 'signal_log.jsonl')
NOW = dt.datetime.now(dt.timezone.utc)


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def load(name):
    try: return json.load(open(os.path.join(ST, name)))
    except Exception: return {}


def pinnacle_clv(rows):
    """Pinnacle devigged price on each signal's side at first sight and at the start (None when Pinnacle has no quote on that line)."""
    try:
        from sharp import constants as C, fair as F, sports as SP
        conn = sqlite3.connect(os.environ.get('SHARP_DB') or os.path.join(ST, 'sharp.sqlite'))
    except Exception as e:
        print(f"[signal_log] no tick database for CLV ({e})"); return
    for v in rows:
        try: eq = F.EventQuotes(conn, v['event_id'])
        except Exception: continue
        mk = v['market']; start = ts(v['start']).strftime('%Y-%m-%dT%H:%M:%SZ')
        try: meth = C.DEVIG_METHOD[(v['sport'], SP.market_class(mk))]['value']
        except Exception: meth = 'power'
        for kind, sg in v['signals'].items():
            ln = sg.get('line')
            if mk == 'spread' and ln is not None and sg['side'] == 'away': ln = -ln          # the tick database keeps each side's own number
            if mk == 'ml': ln = None
            first = sg.get('first') or v.get('ts')
            part = (eq.event[4] if sg['side'] == 'home' else eq.event[3]) if mk in ('ml', 'spread') and eq.event and sg['side'] in ('home', 'away') else None   # team markets are keyed by team
            p1 = eq.venue_prob('Pinnacle', mk, ln, sg['side'], first, meth, part)[0] if first else None
            p2 = eq.venue_prob('Pinnacle', mk, ln, sg['side'], start, meth, part, max_age=180)[0]
            sg['p_first'] = round(p1, 4) if p1 is not None else None; sg['p_close'] = round(p2, 4) if p2 is not None else None
            sg['clv'] = round(100 * (p2 - p1), 2) if p1 is not None and p2 is not None else None


def main():
    if '--reclv' in sys.argv:                   # one-off: add CLV to log rows frozen before it was recorded
        rows = [json.loads(l) for l in open(LOG) if l.strip()]
        todo = [v for v in rows if any('clv' not in sg for sg in v['signals'].values())]
        pinnacle_clv(todo)
        with open(LOG, 'w') as f:
            for v in rows: f.write(json.dumps(v) + '\n')
        print(f"[signal_log] CLV added to {len(todo)} logged snapshots"); return
    MV, FL = load('moves.json'), load('flow_live.json')
    cur = {}
    def add(kind, ev, market, side, start, sport, line=None, **extra):
        if not ev or not start or ts(start) <= NOW: return
        k = f"{ev}|{market}"
        r = cur.setdefault(k, dict(event_id=ev, market=market, start=start, sport=sport, signals={}))
        r['signals'][kind] = dict(side=side, line=line, **extra)
    for sp, v in (MV.get('sports') or {}).items():
        for m in v.get('tape') or []:
            k_ = m.get('kalshi') or {}
            if m.get('started') or (NOW - ts(m['ts'])).total_seconds() > 6 * 3600: continue
            if not (m.get('origin') == 'Pinnacle' or (k_.get('big_n') and (k_.get('big_net') or 0) > 0)): continue
            add('move', m.get('event_id'), m['market'], m['side'], m['start'], sp, m.get('line'), origin=m.get('origin'), pts=m.get('size_pts'), p1=m.get('p1'))
    for r in FL.get('rows') or []:
        if r.get('divergent') and r.get('show') is not False:
            add('big', r['event_id'], r['market'], r['big_side'], r['start'], r['sport'], r.get('line'), big_net=r.get('big_net'), small_net=r.get('small_net'))
    for r in FL.get('moves') or []:
        ln = r.get('line')
        if r['market'] == 'spread' and ln is not None and r['side'] == 'away': ln = -ln      # flow_live gives the side's own number; log the home number
        add('kmove', r['event_id'], r['market'], r['side'], r['start'], r['sport'], ln, state=r.get('state'), now=r.get('now'), ask=r.get('ask'))
    for r in (FL.get('steam') or {}).get('rows') or []:
        if r.get('state') == 'reversed':
            add('back', r['event_id'], r['market'], r['rev_side'], r['start'], r['sport'], r.get('line'), cost=r.get('rev_cost'), ticker=r.get('ticker'))
    for r in cur.values():
        sides = {s['side'] for s in r['signals'].values()}
        r['agree'] = len(sides) == 1; r['ts'] = NOW.strftime('%Y-%m-%dT%H:%M:%SZ')
    old = json.load(open(SNAP)) if os.path.exists(SNAP) else {}
    now_s = NOW.strftime('%Y-%m-%dT%H:%M:%SZ')
    for k, r in cur.items():                     # first seen: carried while the signal stays on the same side
        for kind, sg in r['signals'].items():
            o = ((old.get(k) or {}).get('signals') or {}).get(kind) or {}
            sg['first'] = o.get('first') if o.get('side') == sg['side'] and o.get('first') else now_s
    frozen = [v for k, v in old.items() if ts(v['start']) <= NOW]
    pinnacle_clv(frozen)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a') as f:                   # always exists, so the workflow's git add never fails on it
        for v in frozen: f.write(json.dumps(v) + '\n')
    keep = {k: v for k, v in old.items() if ts(v['start']) > NOW}
    keep.update(cur)          # the latest pregame view wins; markets whose signals faded keep their last snapshot until the start
    json.dump(keep, open(SNAP, 'w'), separators=(',', ':'))
    print(f"[signal_log] {len(cur)} game x markets with signals now ({sum(not v['agree'] for v in cur.values())} conflicting); {len(frozen)} frozen to the log")


if __name__ == '__main__':
    main()
