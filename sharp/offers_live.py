#!/usr/bin/env python3
"""Offers to rest, live (Sean 11/10: "scan Kalshi and Novig daily for opportunities that are way off from market, to offer"; research in
docs/maker_2026-11-10.md and sharp/offer_scan.py). On the 10-minute tape, every Kalshi and Novig market side where Pinnacle quotes both
sides at the same line and our bid would be first in line. The bid is 1c under Pinnacle's no-vig fair on Novig spreads, totals, team totals
and period lines, 2c on props (1c in the last hour), 1c on moneylines in the last hour only, 2c on Kalshi (rules from the 11/10 maker
tests). Whole cents on Kalshi, half cents on Novig. Paper only: nothing is placed.
Left out: period moneylines (a tie loses on Kalshi and is refunded at Pinnacle), soccer moneylines (three-way), games more than 24 hours
out (maker fills that early lost on Kalshi) or inside 10 minutes, fair prices outside 8-92%.
Writes data/state/offers.json for the board and appends each offer the first time it is seen to data/state/offers_paper.jsonl, so fills
(data/*/trades5_soft, data/*/trades5) and the close can be marked later.
Usage: python3 sharp/offers_live.py"""
import os, sys, json, glob, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
from sharp.gzlines import lines
OUT = os.path.join(ROOT, 'data', 'state', 'offers.json'); PAPER = os.path.join(ROOT, 'data', 'state', 'offers_paper.jsonl')
NOW = dt.datetime.fromisoformat(os.environ['OFFERS_NOW']) if os.environ.get('OFFERS_NOW') else dt.datetime.now(dt.timezone.utc)
# 11/10: quotes reach the repo 10 to 20 minutes after they are taken (the price job's commit), so 25 minutes left almost nothing to
# scan (22 priced sides at 7 AM). 45 minutes, the bet log's own limit, with the venue and Pinnacle quotes within 15 minutes of each other.
ROOM_MIN, EDGE, FRESH, PIN_FRESH, MAX_H = 0.03, 0.02, 45 * 60, 45 * 60, 24
TICK = dict(Kalshi=0.01, Novig=0.005)
OTH = dict(home='away', away='home', over='under', under='over')
SKIP = ('1h_ml', '1q_ml', '1p_ml', '1s_ml')


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
def imp(a): return 100.0 / (a + 100.0) if a > 0 else -a / (-a + 100.0)
def totlike(m): return 'total' in m or m.startswith('prop_') or 'tt_' in m


def main():
    rows = []; counts = collections.Counter()
    for sd in sorted(glob.glob(os.path.join(ROOT, 'data', '*', 'schedule.json'))):
        sp = os.path.basename(os.path.dirname(sd))
        try: d = json.load(open(sd))
        except Exception: continue
        ev = d if isinstance(d, list) else (d.get('events') if isinstance(d.get('events'), list) else list(d.values()))
        G = {}
        for e in ev:
            if not (isinstance(e, dict) and e.get('event_id') and e.get('start')): continue
            try: st = ts(e['start'] if len(e['start']) > 17 else e['start'].replace('Z', ':00Z'))
            except Exception: continue
            if dt.timedelta(minutes=10) < st - NOW <= dt.timedelta(hours=MAX_H): G[str(e['event_id'])] = (st, f"{e.get('away') or ''} @ {e.get('home') or ''}".strip(' @'))
        if not G: continue
        last = {}
        for day in sorted({(NOW - dt.timedelta(hours=h)).strftime('%Y-%m-%d') for h in (0, 6, 30)}):
            p = os.path.join(ROOT, 'data', sp, 'ticks', f'{day}.jsonl.gz')
            if not os.path.exists(p): continue
            for l in lines(p):
                if '"Pinnacle"' not in l and '"Kalshi"' not in l and '"Novig"' not in l: continue
                try: x = json.loads(l)
                except Exception: continue
                v = x.get('venue'); m = x.get('market') or ''
                if v not in ('Pinnacle', 'Kalshi', 'Novig') or str(x.get('event_id')) not in G or m in SKIP or (sp == 'soccer' and m == 'ml'): continue
                try: t = ts(x['ts'])
                except Exception: continue
                if (NOW - t).total_seconds() > PIN_FRESH or t > NOW: continue
                k = (v, str(x['event_id']), m, x.get('side'), x.get('line'), x.get('participant') if m.startswith('prop_') else None)
                if k not in last or t >= last[k][0]: last[k] = (t, x)
        for (v, ev_, m, side, line, pk), (t, x) in last.items():
            if v == 'Pinnacle' or side not in OTH or (NOW - t).total_seconds() > FRESH: continue
            a = last.get(('Pinnacle', ev_, m, side, line, pk)); b = last.get(('Pinnacle', ev_, m, OTH[side], line if (line is None or totlike(m)) else -line, pk))
            if not (a and b) or a[1].get('american') is None or b[1].get('american') is None: counts['no Pinnacle price'] += 1; continue
            if abs((t - a[0]).total_seconds()) > 900 or abs((t - b[0]).total_seconds()) > 900: counts['Pinnacle quote not from the same pull'] += 1; continue
            ia, ib = imp(a[1]['american']), imp(b[1]['american']); fair = ia / (ia + ib)
            if not 0.08 <= fair <= 0.92: continue
            bid = x.get('bid') or 0.0; ask = x.get('ask'); room = fair - bid
            counts['priced'] += 1
            # 11/10 (docs/overnight_2026-11-10.md section 8, Novig maker fills against Pinnacle): how far under fair to rest, by market.
            # Novig spreads, totals, team totals and period lines keep the gap at 1c; props need 2c (1c in the last hour); moneylines only
            # hold in the last hour. Kalshi stays at 2c for tracking (its maker fee takes most of a 1c bid).
            hrs = (G[ev_][0] - NOW).total_seconds() / 3600; tk = TICK[v]
            if v == 'Kalshi': edge = EDGE
            elif m == 'ml': edge = 0.01 if hrs <= 1 else None
            elif m.startswith('prop_'): edge = 0.01 if hrs <= 1 else 0.02
            else: edge = 0.01
            if edge is None or room < edge + tk: continue
            ours = math.floor((fair - edge) / tk + 1e-9) * tk
            if ours <= bid + 1e-9 or (ask is not None and ask <= ours + 1e-9): continue
            fee = 0.0175 * ours * (1 - ours) if v == 'Kalshi' else 0.0
            st, game = G[ev_]
            rows.append(dict(key='|'.join(str(z) for z in (v, ev_, m, side, line, pk or '')), venue=v, sport=sp, event_id=ev_, game=game, start=st.strftime('%Y-%m-%dT%H:%M:%SZ'),
                             market=m, side=side, line=line, player=x.get('player') or (pk if pk else None), team=x.get('participant') if not pk else None,
                             fair=round(fair, 4), bid=round(bid, 3), ask=ask, spread=round(ask - bid, 3) if ask is not None and bid else None,
                             offer=round(ours, 3), room=round(room, 3), under=edge, edge=round(fair - ours - fee, 4), seen=t.strftime('%Y-%m-%dT%H:%M:%SZ'),
                             pin_limit=min(z for z in (a[1].get('limit'), b[1].get('limit')) if z) if (a[1].get('limit') or b[1].get('limit')) else None,
                             ticker=(x.get('extra') or {}).get('ticker'), yes=(x.get('extra') or {}).get('yes'), market_id=(x.get('extra') or {}).get('market_id'), outcome_id=(x.get('extra') or {}).get('outcome_id')))
    rows.sort(key=lambda r: -r['room'])
    seen = set()
    if os.path.exists(PAPER):
        for l in open(PAPER):
            try: seen.add(json.loads(l)['key'])
            except Exception: pass
    new = [r for r in rows if r['key'] not in seen]
    if new:
        with open(PAPER, 'a') as f:
            for r in new: f.write(json.dumps(dict(r, logged=NOW.strftime('%Y-%m-%dT%H:%M:%SZ')), separators=(',', ':')) + '\n')
    by = collections.Counter((r['venue'], r['sport'], 'props' if r['market'].startswith('prop_') else r['market']) for r in rows)
    json.dump(dict(updated=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), rule=dict(novig='1c under fair on spreads, totals, team totals, period lines; props 2c (1c in the last hour); moneylines 1c in the last hour only', kalshi='2c under fair', max_hours=MAX_H), n=len(rows),
                   groups=[dict(venue=k[0], sport=k[1], market=k[2], n=n) for k, n in by.most_common()], rows=rows[:200], logged=len(seen) + len(new)),
              open(OUT, 'w'), separators=(',', ':'))
    print(f"[offers] {len(rows)} offers ({len(new)} new) from {counts['priced']} priced sides; {dict(collections.Counter(r['venue'] for r in rows))}; top groups {by.most_common(6)}")


if __name__ == '__main__': main()
