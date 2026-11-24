#!/usr/bin/env python3
"""Grade the frozen sharp-money watch snapshots (data/research/signal_log.jsonl, written by sharp/signal_log.py at each start).

Question (Sean, 11/1): when watch signals agree or conflict, is there signal in either side, or do they cancel? And does the Today
page's "Strongest" rule (price and money agree) beat price alone? Families: PRICE = move (sharp move), kmove (Kalshi 4+ pts), back
(steam bet back); MONEY = big (big vs small). Each snapshot is classed:
  agree        price and money on the same side
  price_only   price signals only (one side)
  money_only   big vs small only
  conflict     price and money on opposite sides (graded for each side)
  price_split  price signals pointing both ways
Each lean is graded W / L / P at the line in the snapshot (home number for spreads, the total for totals) against the final score
(data/state/results.jsonl, as day_review.py). Moneylines also report the mean entry price where the snapshot has one (Kalshi ask), so
win rate can be read against what it cost. No ROI is invented for legs without a recorded price.
CLV (the main test for these top-down signals): each signal's Pinnacle devigged price on its side from first sight to the start, in
points (sharp/signal_log.py records it at freeze). Snapshots with CLV but no final score yet count toward CLV only.
Writes data/research/signal_grade.json. Usage: python3 sharp/signal_grade.py"""
import os, sys, json, sqlite3, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
LOG = os.path.join(ROOT, 'data', 'research', 'signal_log.jsonl'); OUT = os.path.join(ROOT, 'data', 'research', 'signal_grade.json')
PRICE = ('move', 'kmove', 'back')
# 11/23 checkpoint (docs/checkpoint_2026-11-23.md): Kalshi 4+ pt movers met the promote line (150+ CLV-graded with CLV z 2+ and ROI not
# below -5%: CLV +0.54 on 283, z 3.83; priced moneylines -1.3% at the ask). Promoted from watch to a sized paper record: every frozen
# kmove snapshot for a game starting from KMOVE_PAPER_FROM, 1u to risk at the snapshot's Kalshi ask plus the taker fee (0.07 x p x (1 - p)),
# graded at the snapshot's line against the final score. Paper only: no units on the board.
# 11/24 (Sean): reverted to the pre-checkpoint status (watch, no sized paper record). The promotion rested on a CLV z; on profit (+0.5% on
# 1,515, about -3% after the Kalshi fee) it does not meet the profit promote line. KMOVE_PAPER_FROM None: no sized record is built.
KMOVE_PAPER_FROM = None


def grade(market, side, line, hs, as_):
    if market == 'ml':
        if hs == as_: return 'P'
        return 'W' if (hs > as_) == (side == 'home') else 'L'
    if line is None: return None
    if market == 'spread':
        m = (hs - as_) + line            # home margin plus the home number
        if m == 0: return 'P'
        return 'W' if (m > 0) == (side == 'home') else 'L'
    if market == 'total':
        t = hs + as_
        if t == line: return 'P'
        return 'W' if (t > line) == (side == 'over') else 'L'
    return None


def main():
    if not os.path.exists(LOG): print('[signal_grade] no log yet'); return
    rows = [json.loads(l) for l in open(LOG) if l.strip()]
    res = {}
    for l in open(os.path.join(ROOT, 'data', 'state', 'results.jsonl')):       # same source as day_review.py
        try: r_ = json.loads(l)
        except Exception: continue
        if r_.get('status') == 'final' and r_.get('home_score') is not None: res[r_['event_id']] = (r_['home_score'], r_['away_score'])
    T = collections.defaultdict(lambda: dict(W=0, L=0, P=0, prices=[], clv=[]))
    graded = 0
    for r in rows:
        sc = res.get(r['event_id'])
        hs, as_ = sc if sc else (None, None); sig = r['signals']; mk = r['market']
        ps = {k: v for k, v in sig.items() if k in PRICE}; mo = sig.get('big')
        psides = {v['side'] for v in ps.values()}
        if len(psides) > 1: cls = 'price_split'
        elif ps and mo: cls = 'agree' if mo['side'] in psides else 'conflict'
        elif ps: cls = 'price_only'
        elif mo: cls = 'money_only'
        else: continue
        graded += bool(sc)
        legs = []
        if cls == 'conflict': legs = [('conflict: price side', next(iter(ps.values()))), ('conflict: money side', mo)]
        elif cls == 'price_split': legs = [(f'price_split: {k}', v) for k, v in ps.items()]
        else: legs = [(cls, mo if cls == 'money_only' else next(iter(ps.values())))]
        for k, v in sig.items(): legs.append((f'kind: {k}' + (f" ({v.get('state')})" if k == 'kmove' else ''), v))
        for name, v in legs:
            c = T[f'{name} | {mk}']
            if v.get('clv') is not None: c['clv'].append(v['clv'])
            g = grade(mk, v['side'], v.get('line'), hs, as_) if sc else None
            if not g: continue
            c[g] += 1
            pr = v.get('ask') if v.get('ask') is not None else v.get('cost')
            if mk == 'ml' and pr is not None and g != 'P': c['prices'].append(pr / 100)
    kp = []
    for r in rows:
        v = r['signals'].get('kmove'); s_ = r['start'] if len(r['start']) > 17 else r['start'].replace('Z', ':00Z')
        if not KMOVE_PAPER_FROM or not v or v.get('ask') is None or s_ < KMOVE_PAPER_FROM: continue
        sc = res.get(r['event_id']); g = grade(r['market'], v['side'], v.get('line'), *sc) if sc else None
        if not g: continue
        p = v['ask'] / 100; pe = p + 0.07 * p * (1 - p)
        kp.append(dict(event_id=r['event_id'], market=r['market'], side=v['side'], line=v.get('line'), start=r['start'], ask=v['ask'], result=g,
                       pnl=0.0 if g == 'P' else round((1 - pe) / pe if g == 'W' else -1.0, 3), clv=v.get('clv')))
    kmove_paper = dict(since=KMOVE_PAPER_FROM, n=len(kp), W=sum(x['result'] == 'W' for x in kp), L=sum(x['result'] == 'L' for x in kp), P=sum(x['result'] == 'P' for x in kp),
                       units=round(sum(x['pnl'] for x in kp), 2), clv_n=sum(x['clv'] is not None for x in kp),
                       clv=round(sum(x['clv'] for x in kp if x['clv'] is not None) / max(1, sum(x['clv'] is not None for x in kp)), 2), recent=kp[-20:])
    out = {}
    for k, c in sorted(T.items()):
        n = c['W'] + c['L']
        out[k] = dict(W=c['W'], L=c['L'], P=c['P'], win=round(c['W'] / n, 3) if n else None,
                      mean_price=round(sum(c['prices']) / len(c['prices']), 3) if c['prices'] else None,
                      clv_n=len(c['clv']), clv=round(sum(c['clv']) / len(c['clv']), 2) if c['clv'] else None,
                      clv_pos=round(sum(x > 0 for x in c['clv']) / len(c['clv']), 2) if c['clv'] else None)
    json.dump(dict(snapshots=len(rows), graded=graded, cells=out, kmove_paper=kmove_paper), open(OUT, 'w'), indent=1)
    if KMOVE_PAPER_FROM: print(f"[signal_grade] kmove paper since {KMOVE_PAPER_FROM}: {kmove_paper['W']}-{kmove_paper['L']}-{kmove_paper['P']}, {kmove_paper['units']:+}u")
    print(f"[signal_grade] {len(rows)} snapshots, {graded} with a final score")
    for k, v in out.items(): print(f"  {k:40} {v['W']}-{v['L']}-{v['P']}  win {v['win']}  price {v['mean_price']}  CLV {v['clv']} on {v['clv_n']}")


if __name__ == '__main__':
    main()
