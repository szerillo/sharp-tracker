#!/usr/bin/env python3
"""Monday scoreboard, computed from the ledger and the latest exports (no model, no prose generation):
data/state/weekly.json (page: Weekly tab) and docs/weekly/YYYY-MM-DD.md (the same, as text). Run by weekly.yml every Monday 08:45 ET
and on demand. Sections: systems forward record by tag, last 7 days of paper fills, real fills, this week's triggers, top edges now,
log health."""
import os, sys, json, datetime as dt, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from sharp import norm as N, fills as FI

ROOT = os.path.abspath(os.path.join(HERE, '..')); SD = os.path.join(ROOT, 'data', 'state'); WD = os.path.join(ROOT, 'docs', 'weekly'); os.makedirs(WD, exist_ok=True)
NOW = dt.datetime.now(dt.timezone.utc); NOW_S = N.iso(NOW)


def load(name):
    p = os.path.join(SD, name)
    return json.load(open(p)) if os.path.exists(p) else None


def et(iso):
    d = N.parse_ts(iso); off = -5 if d >= dt.datetime(2026, 11, 1, 6, tzinfo=dt.timezone.utc) else -4
    return (d + dt.timedelta(hours=off)).strftime('%a %b %d %I:%M %p').replace(' 0', ' ')


def main():
    fills = FI.load(); week_ago = NOW - dt.timedelta(days=7)
    def rec(rows):
        s = dict(n=len(rows), w=0, l=0, p=0, units=0.0, pnl=0.0, clv=[], graded=0)
        for r in rows:
            s['units'] += r.get('stake') or 0
            if r.get('result') in ('W', 'L', 'P'):
                s['graded'] += 1; s[{'W': 'w', 'L': 'l', 'P': 'p'}[r['result']]] += 1; s['pnl'] += r.get('pnl_units') or 0
                if r.get('fair_at_close') is not None and not r.get('late'): s['clv'].append(100 * (r['fair_at_close'] - r['implied']))
        s['clv_avg'] = round(sum(s['clv']) / len(s['clv']), 2) if s['clv'] else None; s['n_clv'] = len(s['clv']); del s['clv']
        s['pnl'] = round(s['pnl'], 3); s['roi'] = round(100 * s['pnl'] / s['units'], 1) if s['units'] else None
        return s
    paper = [r for r in fills if str(r.get('rule_tag', '')).startswith('paper:')]; real = [r for r in fills if not str(r.get('rule_tag', '')).startswith('paper:')]
    by_tag = {t: dict(rec([r for r in paper if r['rule_tag'] == f'paper:{t}']), gate=100) for t in sorted({r['rule_tag'][6:] for r in paper})}
    for s in by_tag.values(): s['published'] = bool(s['graded'] >= s['gate'] and (s['clv_avg'] or 0) > 0)
    def row(r):
        return dict(ts=r['ts_utc'], game=r.get('event_id'), market=r['market'], side=r['side'], line=r.get('line'), player=r.get('player_name') or r.get('participant'),
                    venue=r['venue'], price=r['price_american'], stake=r['stake'], tag=r.get('rule_tag'), result=r.get('result'), pnl=r.get('pnl_units'),
                    clv=(round(100 * (r['fair_at_close'] - r['implied']), 2) if r.get('fair_at_close') is not None and not r.get('late') else None), note=r.get('note'))
    # event names from the per-sport dashboards + sqlite-free lookup via schedule files
    names = {}
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'soccer'):
        p = os.path.join(ROOT, 'data', sp, 'schedule.json')
        if os.path.exists(p):
            for eid, e in json.load(open(p)).items(): names[eid] = f"{e.get('away')}@{e.get('home')} ({sp.upper()})"
    paper_week = [dict(row(r), game=names.get(r['event_id'], r['event_id'])) for r in paper if N.parse_ts(r['ts_utc']) >= week_ago]
    real_rows = [dict(row(r), game=names.get(r['event_id'], r['event_id'])) for r in real]
    real_by = {k: rec([r for r in real if r.get(key) == k]) for key in ('venue', 'market') for k in sorted({r.get(key) for r in real if r.get(key)})}
    sysv = load('system_fires.json') or {}; edges = load('edges.json') or {}; dash = load('dashboard.json') or {}
    top = [e for e in edges.get('edges', []) if e.get('fair_n', 0) >= 3 and e.get('ttk_h', 0) > 0][:15]
    health = []
    for s in (dash.get('index') or {}).get('sports', []):
        d = load(f"dashboard_{s['sport']}.json") or {}; age = (NOW - N.parse_ts(d['built'])).total_seconds() / 3600 if d.get('built') else None
        health.append(dict(sport=s['sport'], games=s['games'], ticks=s['ticks'], events=s['events'], settled=s['settled'], built=d.get('built'), age_h=round(age, 1) if age is not None else None,
                           flag=(age is None or age > 2)))
    out = dict(built=NOW_S, week_start=N.iso(week_ago), systems=by_tag, paper_last7=paper_week, real=dict(fills=real_rows, by=real_by, total=rec(real)),
               triggers=dict(games=sysv.get('games', []), fired_now=sysv.get('fired_now', []), built=sysv.get('built')), top_edges=top, edges_built=edges.get('built'), health=health)
    json.dump(out, open(os.path.join(SD, 'weekly.json'), 'w'), default=str, separators=(',', ':'))
    # markdown twin
    L = [f"# Sharp tracker weekly - {et(NOW_S)} ET", '', '## Systems forward record (paper fills at best price; gate = 100 graded with positive CLV)', '',
         '| tag | fills | graded | W-L-P | units | P&L | ROI | CLV avg (n) | status |', '|---|---|---|---|---|---|---|---|---|']
    for t, s in by_tag.items():
        L.append(f"| {t} | {s['n']} | {s['graded']} | {s['w']}-{s['l']}-{s['p']} | {s['units']:.1f} | {s['pnl']:+.2f} | {s['roi'] if s['roi'] is not None else '-'} | {s['clv_avg'] if s['clv_avg'] is not None else '-'} ({s['n_clv']}) | {'published' if s['published'] else 'gated'} |")
    if not by_tag: L.append('| (no paper fills yet) | | | | | | | | |')
    L += ['', '## Paper fills, last 7 days', '', '| when (UTC) | game | bet | venue | price | stake | tag | result | P&L | CLV |', '|---|---|---|---|---|---|---|---|---|---|']
    for r in paper_week: L.append(f"| {r['ts'][:16]} | {r['game']} | {r['market']} {r['side']} {r['line'] if r['line'] is not None else ''} | {r['venue']} | {r['price']:+d} | {r['stake']} | {r['tag'][6:]} | {r['result'] or 'open'} | {r['pnl'] if r['pnl'] is not None else '-'} | {r['clv'] if r['clv'] is not None else '-'} |")
    if not paper_week: L.append('| none | | | | | | | | | |')
    L += ['', f"## Real fills ({len(real_rows)} on file): {out['real']['total']['w']}-{out['real']['total']['l']}-{out['real']['total']['p']}, {out['real']['total']['pnl']:+.2f}u, CLV avg {out['real']['total']['clv_avg']}", '']
    for r in real_rows[-25:]: L.append(f"- {r['ts'][:16]} {r['game']} {r['market']} {r['side']} {r['line'] if r['line'] is not None else ''} {r['player'] or ''} @ {r['venue']} {r['price']:+d} x{r['stake']} [{r['tag']}] {r['result'] or 'open'} CLV {r['clv'] if r['clv'] is not None else '-'}")
    L += ['', '## Triggers in the fire window now', '']
    for g in out['triggers']['games']: L.append(f"- {g['away']}@{g['home']} T-{g['hours_to_kickoff']}h: " + '; '.join(f"{t}: {w}" for t, w in g['triggers'].items()))
    if not out['triggers']['games']: L.append('- none')
    L += ['', '## Top edges now (fair from >= 3 venues; prior weights until a sport is fitted)', '', '| sport | game | kickoff ET | bet | best | fair | edge |', '|---|---|---|---|---|---|---|']
    for e in top:
        bet = f"{e.get('player') or ''} {e['market']} {e['side']} {e['line'] if e.get('line') is not None else ''}".strip()
        L.append(f"| {e['sport'].upper()} | {e['game']} | {et(e['start_utc'])} | {bet} | {e['venue']} {e['price']:+d} | {100 * e['fair']:.1f}% ({e['fair_n']}) | {e['edge_pts']:+.2f} |")
    L += ['', '## Log health', '']
    for h in health: L.append(f"- {h['sport'].upper()}: {h['games']} games on the board, {h['ticks']:,} ticks, {h['settled']} settled; built {h['age_h']}h ago" + (' **STALE**' if h['flag'] else ''))
    md = '\n'.join(L) + '\n'
    open(os.path.join(WD, f"{NOW.strftime('%Y-%m-%d')}.md"), 'w').write(md); open(os.path.join(WD, 'latest.md'), 'w').write(md)
    print(f"[weekly] {len(by_tag)} tags, {len(paper_week)} paper fills last 7d, {len(real_rows)} real fills, {len(top)} edges, {sum(1 for h in health if h['flag'])} stale sports")


if __name__ == '__main__':
    main()
