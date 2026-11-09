#!/usr/bin/env python3
"""Board and tracker audit (Sean, 11/4: "how do we stop this from happening / ensure data quality of the board and the tracker").

Runs after every signals and tracker job and checks the published data against the records, so a problem shows on the board (red
banner) and on the phone (ntfy, when NTFY_TOPIC is set) the run it happens, instead of being noticed by eye hours later.

  freshness      each board file's build time vs how often its job runs (inside the 10 AM to 2 AM ET window)
  sharp feed     the newest Polymarket sharp fill is recent (the Data API v1 retirement stopped it silently for a day on 11/2)
  open bets      every open system bet in the fills ledger is on the board (the NBA unders vanished twice on 11/4)
  tennis picks   every open set-1 pick in the paper log is on the tennis watch
  duplicates     one live fill per rule per game x market; one tennis pick per match
  bet tracker    every flagged bet in the three records is in the bet tracker
Writes data/state/audit.json: {built, ok, checks: [{name, ok, level, detail}]}. Alerts only when a check newly fails.
Usage: python3 sharp/audit.py"""
import os, sys, json, datetime as dt, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
SD = os.path.join(ROOT, 'data', 'state'); OUT = os.path.join(SD, 'audit.json')
NOW = dt.datetime.now(dt.timezone.utc); ET = __import__('zoneinfo').ZoneInfo('America/New_York')
ACTIVE = NOW.astimezone(ET).hour >= 10 or NOW.astimezone(ET).hour < 2


def ts(s):
    if not s: return None
    return dt.datetime.fromisoformat(str(s).replace('Z', '+00:00').replace(' ', 'T'))


def load(p, default=None):
    try: return json.load(open(os.path.join(ROOT, p)))
    except Exception: return default


def jl(p):
    try: return [json.loads(l) for l in open(os.path.join(ROOT, p)) if l.strip()]
    except Exception: return []


def main():
    C = []
    def check(name, ok, detail, level='error'): C.append(dict(name=name, ok=bool(ok), level=level, detail=detail))
    # ---- freshness (minutes allowed since the last build, while the jobs run)
    if ACTIVE:
        for f, key, mins, what in (('data/state/sharp_accounts.json', 'built', 20, 'sharp signals (5-minute job)'),
                                   ('data/state/flow_live.json', 'built', 60, 'big money / Kalshi moves (20-minute job)'),
                                   ('data/state/tennis_watch.json', 'built', 60, 'tennis watch (20-minute job)'),
                                   ('data/state/bet_log.json', 'built', 60, 'bet tracker (20-minute job)'),
                                   ('data/state/system_fires.json', 'built', 5 * 60, 'system bets (3 runs a day)')):
            b = ts((load(f) or {}).get(key)); age = None if not b else (NOW - b).total_seconds() / 60
            check(f'fresh: {what}', age is not None and age <= mins, f"last built {round(age) if age is not None else '?'} min ago (allowed {mins})")
    # ---- Polymarket sharp feed
    fills = jl('data/polymarket/sharp_fills.jsonl')
    last = max((r.get('ts') or 0 for r in fills), default=0)
    if ACTIVE and fills:
        hrs = (NOW.timestamp() - last) / 3600
        check('sharp feed: Polymarket fills arriving', hrs <= 6, f"newest sharp fill {hrs:.1f} h ago", level='warn' if hrs <= 12 else 'error')
    # ---- open system bets on the board
    view = load('data/state/system_fires.json') or {}
    shown = {f.get('fill_id') for g in view.get('games') or [] for f in g.get('fills') or []}
    ledger = jl('data/state/fills.jsonl')
    open_ = [r for r in ledger if str(r.get('rule_tag', '')).startswith('paper:') and r.get('result') is None and ts(r['start_utc']) and ts(r['start_utc']) > NOW]
    tiers = {k: (v.get('evidence') or {}).get('tier') for k, v in (view.get('rules') or {}).items()}
    missing = [r for r in open_ if r['fill_id'] not in shown and tiers.get(r['rule_tag'][6:]) in ('A', 'B', 'C')]
    check('open system bets all on the board', not missing, f"{len(open_)} open, {len(missing)} missing" + (': ' + ', '.join(f"{r['rule_tag'][6:]} {r['event_id']}" for r in missing[:6]) if missing else ''))
    # ---- duplicates
    seen = {}; dups = []
    for r in ledger:
        if r.get('result') == 'void' or not str(r.get('rule_tag', '')).startswith('paper:'): continue
        k = (r['event_id'], r['rule_tag'], r['market'])
        if k in seen: dups.append(k)
        seen[k] = 1
    tp = jl('data/tennis/fs_paper.jsonl'); tk = {}; tdup = 0
    for p in tp:
        k = (frozenset((p.get('fav_name'), p.get('opp_name'))), (p.get('start') or '')[:10])
        tdup += k in tk; tk[k] = 1
    check('no duplicate bets in the records', not dups and not tdup, f"{len(dups)} duplicate system fills, {tdup} duplicate tennis picks")
    # ---- tennis picks on the watch
    tw = load('data/state/tennis_watch.json') or {}
    rows = {r.get('event_id') for r in tw.get('rows') or []}
    topen = [p for p in tp if ts(p.get('start')) and ts(p['start']) > NOW]
    tmiss = [p for p in topen if p['event_id'] not in rows]
    check('open tennis picks on the tennis watch', not tmiss, f"{len(topen)} open, {len(tmiss)} not on the watch" + (': ' + ', '.join(p.get('fav_name') or '?' for p in tmiss[:5]) if tmiss else ''), level='warn')
    # ---- bet tracker completeness
    bl = load('data/state/bet_log.json') or {}
    ids = {r.get('id') for r in bl.get('rows') or []}
    want = {'s:' + r['fill_id'] for r in ledger if r.get('result') != 'void' and r.get('mclass', 'game') == 'game' and str(r.get('rule_tag', '')).startswith('paper:')}
    _seen = set()    # 11/9: the tracker counts one sharp bet per game, market and side (the first line logged), same here
    for p in sorted(jl('data/state/sharp_paper.jsonl'), key=lambda p: p.get('logged') or ''):
        k = (p.get('slug'), p.get('mtype'), p.get('side'))
        if k not in _seen: _seen.add(k); want.add('p:' + p['cond'])
    gap = want - ids
    check('bet tracker has every flagged bet', not gap, f"{len(want)} in the records, {len(gap)} missing from the tracker", level='warn' if len(gap) <= 3 else 'error')
    ok = all(c['ok'] or c['level'] == 'warn' for c in C)
    prev = load('data/state/audit.json') or {}
    prev_bad = {c['name'] for c in prev.get('checks') or [] if not c['ok']}
    new_bad = [c for c in C if not c['ok'] and c['name'] not in prev_bad]
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), ok=ok, checks=C), open(OUT, 'w'), indent=1)
    topic = os.environ.get('NTFY_TOPIC')
    if new_bad and topic:
        msg = '\n'.join(f"{c['name']}: {c['detail']}" for c in new_bad)
        try: urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{topic}", data=msg.encode(), method='POST', headers={'Title': 'Board check failed', 'Tags': 'warning', 'Priority': 'default'}), timeout=15)
        except Exception as e: print(f"[audit] ntfy failed: {e}")
    print(f"[audit] {'OK' if ok else 'PROBLEMS'}: " + '; '.join(f"{c['name']}={'ok' if c['ok'] else c['detail']}" for c in C))


if __name__ == '__main__':
    main()
