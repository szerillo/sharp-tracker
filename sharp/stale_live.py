#!/usr/bin/env python3
"""Stale-book paper lean, live (Sean 11/6; research in docs/stale_books_2026-11-06.md). On the 20-minute tape: a venue Sean bets (Novig,
Kalshi with fee, Polymarket, FD, Caesars, DK) priced 2%+ better than Pinnacle's no-vig fair at the same number, right after Pinnacle moved
1+ point toward that side (the venue has not caught up), at a price under +200. First time per game / market / side / venue.
Appends to data/state/stale_paper.jsonl, grades on the schedule's finals, writes data/state/stale_live.json for the board (Paper rules).
Usage: python3 sharp/stale_live.py"""
import os, sys, json, gzip, glob, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.devig import devig_pair
from sharp.gzlines import lines
VEN = ('Novig', 'Kalshi', 'Polymarket', 'FD', 'Caesars', 'DK')
PAPER = os.path.join(ROOT, 'data', 'state', 'stale_paper.jsonl'); OUT = os.path.join(ROOT, 'data', 'state', 'stale_live.json')
NOW = dt.datetime.fromisoformat(os.environ['STALE_NOW']) if os.environ.get('STALE_NOW') else dt.datetime.now(dt.timezone.utc)      # STALE_NOW: replay a past moment (testing)
EV_MIN, MOVE_MIN, DEC_MAX = 0.02, 0.01, 3.0
SB4_VEN, SB4_EV = ('FD', 'Caesars', 'DK'), 0.04


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def cost(r):
    if r.get('american') is not None:
        a = r['american']; return 1 / (1 + (a / 100 if a > 0 else 100 / -a))
    a = r.get('ask')
    if a is None or not 0.02 < a < 0.98: return None
    if r['venue'] == 'Kalshi': a += math.ceil(0.07 * a * (1 - a) * 100) / 100
    return a


def main():
    old = []
    if os.path.exists(PAPER):
        for l in open(PAPER):
            try: old.append(json.loads(l))
            except Exception: pass
    seen = {r['key'] for r in old}; new = []
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'cbb'):
        try: sched = json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json')))
        except Exception: continue
        live = {}
        for k, e in sched.items():
            try: st = ts(e['start'].replace('Z', ':00Z') if len(e['start']) == 17 else e['start'])
            except Exception: continue
            if NOW < st <= NOW + dt.timedelta(hours=36): live[k] = st
        if not live: continue
        R = collections.defaultdict(list)
        for f in sorted(glob.glob(os.path.join(ROOT, 'data', sp, 'ticks', '*.jsonl.gz')))[-2:]:
            for l in lines(f):
                if '"Pinnacle"' not in l and not any(f'"{v}"' in l for v in VEN): continue
                try: r = json.loads(l)
                except Exception: continue
                if r.get('event_id') in live and r.get('market') in ('ml', 'spread', 'total') and NOW - ts(r['ts']) < dt.timedelta(hours=6): R[(r['event_id'], r['market'])].append(r)
        for (ev, mk), L in R.items():
            snaps = collections.defaultdict(list)
            for r in L: snaps[r['ts'][:16]].append(r)
            hist = []
            for k in sorted(snaps):
                S = snaps[k]; t = ts(S[0]['ts'])
                P = {}
                for r in S:
                    if r['venue'] == 'Pinnacle': P.setdefault(r['side'], r)
                if len(P) == 2:
                    a, b = list(P.values()); ca, cb = cost(a), cost(b)
                    if ca and cb: hist.append((t, {a['side']: (ca / (ca + cb), a.get('line')), b['side']: (cb / (ca + cb), b.get('line'))}))
            if len(hist) < 2: continue
            t_now, fair = hist[-1]
            if NOW - t_now > dt.timedelta(minutes=50): continue
            prev = [x for x in hist if 1200 <= (t_now - x[0]).total_seconds() <= 2700]
            if not prev: continue
            latest = {}
            for r in L:
                # 11/7 (Sean: "anything that flags late relative to Pinnacle"): the venue's quote within 10 min of Pinnacle's snapshot either way
                # (was 25), so a venue that has already moved is never compared with an older Pinnacle number
                if r['venue'] in VEN and abs((ts(r['ts']) - t_now).total_seconds()) <= 600: latest[(r['venue'], r['side'], r.get('line'))] = r
            cand = {}
            for (v, side, ln), r in latest.items():
                if side not in fair: continue
                p, pl = fair[side]
                if mk != 'ml' and ln != pl: continue
                q = prev[0][1].get(side)
                if not q or q[1] != pl or p - q[0] < MOVE_MIN: continue
                c = cost(r)
                if not c or 1 / c >= DEC_MAX: continue
                ev_ = p / c - 1
                if ev_ < EV_MIN: continue
                # the stricter Pinnacle fair (power devig weights the vig toward the longshot) must still show an edge; the venue's own
                # two-way no-vig is stored next to Pinnacle's (fair-to-fair gap)
                pa_, pb_ = [cost(x) for x in P.values()] if len(P) == 2 else (None, None)
                p_pow = p
                try:
                    ca_ = next(cost(x) for x in P.values() if x['side'] == side); cb_ = next(cost(x) for x in P.values() if x['side'] != side)
                    p_pow = devig_pair(ca_, cb_, 'power')
                except Exception: pass
                if min(p, p_pow) / c - 1 <= 0: continue
                OS = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}.get(side)
                ro = next((x for (v2, s2, l2), x in latest.items() if v2 == v and s2 == OS and (mk == 'ml' or l2 == (-ln if mk == 'spread' else ln))), None)
                vf = (c / (c + cost(ro))) if ro and cost(ro) else None
                key = f'{ev}|{mk}|{side}'           # one lean per side (the best venue), so the record counts each bet once
                e = sched[ev]
                # 11/10 (docs/overnight_2026-11-10.md section 2; Sean: keep tracking the rest): the version history supports is its own
                # paper rule, logged next to the original: a sportsbook moneyline 4%+ over Pinnacle's fair (2020-26: +12.5% on 415,
                # 6 of 7 seasons; 2-4% gaps -2.7%; the original is 20-43 live, 57 of 63 on exchanges).
                if v in SB4_VEN and mk == 'ml' and ev_ >= SB4_EV and ('sb4|' + key) not in seen:
                    cand['sb4|' + key] = max(cand.get('sb4|' + key, {'ev': -1}), dict(key='sb4|' + key, kind='sb4', sport=sp, event_id=ev, game=f"{e.get('away')} @ {e.get('home')}", start=e['start'],
                                             market=mk, side=side, line=ln, venue=v, price=round(c, 4), fair=round(p, 4), fair_power=round(p_pow, 4), venue_fair=round(vf, 4) if vf else None,
                                             fair_gap=round(100 * (p - vf), 1) if vf else None, ev=round(100 * ev_, 1), move=round(100 * (p - q[0]), 1), flagged=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                             team=(e.get('home') if side == 'home' else e.get('away') if side == 'away' else None)), key=lambda x: x['ev'])
                if key in seen: continue
                cand[key] = max(cand.get(key, {'ev': -1}), dict(key=key, sport=sp, event_id=ev, game=f"{e.get('away')} @ {e.get('home')}", start=e['start'], market=mk, side=side, line=ln, venue=v,
                                price=round(c, 4), fair=round(p, 4), fair_power=round(p_pow, 4), venue_fair=round(vf, 4) if vf else None, fair_gap=round(100 * (p - vf), 1) if vf else None,
                                ev=round(100 * ev_, 1), move=round(100 * (p - q[0]), 1), flagged=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                team=(e.get('home') if side == 'home' else e.get('away') if side == 'away' else None)), key=lambda x: x['ev'])
            for k_, x in cand.items(): seen.add(k_); new.append(x)
    rows = old + new
    # grade on the schedule's finals
    for r in rows:
        if r.get('won') is not None: continue
        try: e = json.load(open(os.path.join(ROOT, 'data', r['sport'], 'schedule.json'))).get(r['event_id']) if r['sport'] not in _S else _S[r['sport']].get(r['event_id'])
        except Exception: e = None
        if not e or not e.get('completed'): continue
        try: hs, as_ = float(e['home_team']['score']), float(e['away_team']['score'])
        except Exception: continue
        if r['market'] == 'ml': won = 1 if (hs > as_) == (r['side'] == 'home') else 0
        elif r['market'] == 'spread':
            m = (hs - as_ if r['side'] == 'home' else as_ - hs) + r['line']; won = 0.5 if m == 0 else 1 if m > 0 else 0
        else:
            t = hs + as_; won = 0.5 if t == r['line'] else 1 if (t > r['line']) == (r['side'] == 'over') else 0
        r['won'] = won; r['units'] = round(0.25 * ((1 / r['price'] - 1) if won == 1 else -1 if won == 0 else 0), 3)
    with open(PAPER, 'w') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    g = [r for r in rows if r.get('won') is not None]
    def rec_(g): return dict(n=len(g), won=sum(1 for r in g if r['won'] == 1), lost=sum(1 for r in g if r['won'] == 0), units=round(sum(r['units'] for r in g), 2),
                             roi=round(100 * sum(r['units'] for r in g) / (0.25 * max(1, len(g))), 1))
    rec = rec_([r for r in g if r.get('kind') != 'sb4']); rec4 = rec_([r for r in g if r.get('kind') == 'sb4'])
    open_ = [r for r in rows if r.get('won') is None and ts(r['start'].replace('Z', ':00Z') if len(r['start']) == 17 else r['start']) > NOW - dt.timedelta(hours=4)]
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), record=rec, record_sb4=rec4, rows=open_), open(OUT, 'w'), indent=1)
    print(f'[stale_live] {len(new)} new, {len(open_)} open, record {rec}')


_S = {}
for _sp in ('nfl', 'nba', 'nhl', 'cfb', 'cbb'):
    try: _S[_sp] = json.load(open(os.path.join(ROOT, 'data', _sp, 'schedule.json')))
    except Exception: pass

if __name__ == '__main__':
    main()
