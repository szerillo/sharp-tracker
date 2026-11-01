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
Usage: python3 sharp/signal_log.py"""
import os, sys, json, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
ST = os.path.join(ROOT, 'data', 'state'); SNAP = os.path.join(ST, 'signal_snap.json'); LOG = os.path.join(ROOT, 'data', 'research', 'signal_log.jsonl')
NOW = dt.datetime.now(dt.timezone.utc)


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def load(name):
    try: return json.load(open(os.path.join(ST, name)))
    except Exception: return {}


def main():
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
        add('kmove', r['event_id'], r['market'], r['side'], r['start'], r['sport'], r.get('line'), state=r.get('state'), now=r.get('now'), ask=r.get('ask'))
    for r in (FL.get('steam') or {}).get('rows') or []:
        if r.get('state') == 'reversed':
            add('back', r['event_id'], r['market'], r['rev_side'], r['start'], r['sport'], r.get('line'), cost=r.get('rev_cost'), ticker=r.get('ticker'))
    for r in cur.values():
        sides = {s['side'] for s in r['signals'].values()}
        r['agree'] = len(sides) == 1; r['ts'] = NOW.strftime('%Y-%m-%dT%H:%M:%SZ')
    old = json.load(open(SNAP)) if os.path.exists(SNAP) else {}
    frozen = [v for k, v in old.items() if ts(v['start']) <= NOW]
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a') as f:                   # always exists, so the workflow's git add never fails on it
        for v in frozen: f.write(json.dumps(v) + '\n')
    keep = {k: v for k, v in old.items() if ts(v['start']) > NOW}
    keep.update(cur)          # the latest pregame view wins; markets whose signals faded keep their last snapshot until the start
    json.dump(keep, open(SNAP, 'w'), separators=(',', ':'))
    print(f"[signal_log] {len(cur)} game x markets with signals now ({sum(not v['agree'] for v in cur.values())} conflicting); {len(frozen)} frozen to the log")


if __name__ == '__main__':
    main()
