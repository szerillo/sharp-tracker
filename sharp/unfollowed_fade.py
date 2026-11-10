#!/usr/bin/env python3
"""Fade of exchange moves Pinnacle does not follow (docs/review_2026-11-10.md; checkpoint 11/9: exchange-led moves Pinnacle did not follow
have CLV -1.22 on 1,044). From the move tape (data/state/moves.jsonl.gz, sharp/moves.py): a 2+ point move that started on Kalshi or
Novig, on a market Pinnacle quotes, that Pinnacle has not followed by 1 point within 30 minutes (knowable at the time). The fade buys the
other side at the origin's price after the move plus a cost (1c, and 2.5c for Kalshi's fee and spread). In the tape p1 is the home / over
price, the move's side is home/over when dir > 0, and outcome is the move's side.
z is clustered by game (a game has several moves). Usage: python3 sharp/unfollowed_fade.py"""
import os, json, gzip, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
R = [json.loads(l) for l in gzip.open(os.path.join(ROOT, 'data', 'state', 'moves.jsonl.gz'), 'rt')]
f = lambda m: (m.get('followed') or {}).get('Pinnacle')
sp_ = lambda m: m['p1'] if m['dir'] > 0 else 1 - m['p1']          # price of the move's side after the move
BASE = [m for m in R if m.get('settled') and m.get('clv_pts') is not None and m['origin'] in ('Kalshi', 'Novig') and 'Pinnacle' in (m.get('followed') or {})
        and m.get('outcome') in (0, 1) and not m.get('push')]


def st(L, label, first=False):
    if first:
        seen = set(); L2 = []
        for m in sorted(L, key=lambda m: m['ts']):
            k = (m['event_id'], m['market'])
            if k not in seen: seen.add(k); L2.append(m)
        L = L2
    if len(L) < 20: print(f'  {label:<42} n {len(L)}'); return
    out = []
    for c in (0.01, 0.025):
        ev = collections.defaultdict(float); tot = 0.0
        for m in L:
            q = min(0.99, 1 - sp_(m) + c); x = (1 / q - 1) if m['outcome'] == 0 else -1; ev[m['event_id']] += x; tot += x
        mean = tot / len(L); se = sum(s * s for s in ev.values()) ** 0.5 / len(L); out.append(f"{100 * mean:+.1f}% (z {mean / se:+.2f})")
    cl = collections.defaultdict(list)
    for m in L: cl[m['event_id']].append(m['clv_pts'])
    g = [sum(v) / len(v) for v in cl.values()]; gm = sum(g) / len(g); sd = (sum((x - gm) ** 2 for x in g) / max(1, len(g) - 1)) ** 0.5
    print(f"  {label:<42} n {len(L):>4} games {len(cl):>3} mover CLV {sum(m['clv_pts'] for m in L) / len(L):+.2f} (z {gm / (sd / len(g) ** 0.5):+.1f}) | fade price {sum(1 - sp_(m) for m in L) / len(L):.3f} "
          f"won {sum(1 for m in L if m['outcome'] == 0) / len(L):.3f} | ROI at +1c {out[0]}, at +2.5c {out[1]}")


print('By minutes until Pinnacle followed (all exchange-led moves on markets Pinnacle quotes)')
for lab, fn in (('followed within 30m', lambda m: f(m) is not None and f(m) <= 30), ('followed later than 30m', lambda m: f(m) is not None and f(m) > 30), ('never followed', lambda m: f(m) is None)):
    st([m for m in BASE if fn(m)], lab)
N = [m for m in BASE if f(m) is None or f(m) > 30]
print('Not followed within 30 minutes (knowable at the time)')
st(N, 'all moves'); st(N, 'first move per game and market', True)
for o in ('Kalshi', 'Novig'): st([m for m in N if m['origin'] == o], o)
for mk in ('ml', 'spread', 'total'): st([m for m in N if m['market'] == mk], mk); st([m for m in N if m['market'] == mk], mk + ', first per game', True)
for s in ('nba', 'cbb', 'nhl', 'cfb', 'nfl', 'soccer'): st([m for m in N if m['sport'] == s], s)
for lab, fn in (('move toward the favourite (side 55%+)', lambda m: sp_(m) >= .55), ('move toward a near-even side', lambda m: .45 <= sp_(m) < .55), ('move toward the dog (side under 45%)', lambda m: sp_(m) < .45),
                ('size 2-3 pts', lambda m: m['size_pts'] < 3), ('size 3-5', lambda m: 3 <= m['size_pts'] < 5), ('size 5+', lambda m: m['size_pts'] >= 5),
                ('24h+ out', lambda m: m['ttk_h'] >= 24), ('6-24h', lambda m: 6 <= m['ttk_h'] < 24), ('1-6h', lambda m: 1 <= m['ttk_h'] < 6), ('under 1h', lambda m: m['ttk_h'] < 1),
                ('Kalshi flow under $500', lambda m: (m.get('kalshi') or {}).get('usd', 0) < 500), ('Kalshi flow $500+', lambda m: (m.get('kalshi') or {}).get('usd', 0) >= 500)):
    st([m for m in N if fn(m)], lab)
days = sorted({m['ts'][:10] for m in N}); half = days[len(days) // 2]
st([m for m in N if m['ts'][:10] < half], 'before ' + half); st([m for m in N if m['ts'][:10] >= half], half + ' on')
