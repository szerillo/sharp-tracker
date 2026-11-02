#!/usr/bin/env python3
"""Sharp-account flags for the Today page (Sean, 11/2: follow the sharps, but do not flag 100 games; tell me if a sharp comes in on the
other side after I have a position).

Input: data/polymarket/sharp_fills.jsonl (loggers/poly_sharps.py, every 5 minutes). Per upcoming game market:
  FLAG    the first moment a top-50 account bets a side, or two different top-200 accounts are on the same side, with no top-200
          account on the other side yet. Backtest (holdout Sep 1 to Nov 1, entry 5 minutes after, data/research/sharp_accounts_filters.json):
          about 8-9 games a day, +0.96 pts CLV (z 7.4) vs +0.78 for every single top-200 bet (19 games a day).
  OTHER SIDE  after a flag, a top-200 account bets the other side. Backtest: holding still averaged +1.12 pts CLV vs +0.89 locked in by
          getting out at the mid 5 minutes later (194 cases), so the default is to hold; the row says so, with the current price to get out.
  Accounts on both sides before any flag: no flag (head-to-head at T-15m had no edge either way).
Price: the current best ask on the flagged side from the Polymarket CLOB (what a follower pays now), next to what the sharps paid.
Paper log: data/state/sharp_paper.jsonl, one row per flag at the ask when first seen; graded after the game on the result (Gamma) and on
CLV vs Polymarket's two-sided close (public trade tape). Writes data/state/sharp_accounts.json.
Usage: python3 sharp/sharp_live.py"""
import os, sys, re, json, time, math, datetime as dt, urllib.request, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
FILLS = os.path.join(ROOT, 'data', 'polymarket', 'sharp_fills.jsonl'); OUT = os.path.join(ROOT, 'data', 'state', 'sharp_accounts.json')
PAPER = os.path.join(ROOT, 'data', 'state', 'sharp_paper.jsonl'); META = os.path.join(ROOT, 'data', 'polymarket', '_sharp_meta.json')
NOW = time.time(); TOP_RANK = 50; TWO = 2


def g(u):
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=20))
        except Exception: time.sleep(1 + i)
    return None


def epoch(s): return dt.datetime.fromisoformat(s.replace(' ', 'T').replace('+00', '+00:00').replace('Z', '+00:00')).timestamp()


def bet_text(r, side):
    """'Celtics -6.5', 'Over 220.5', 'Magic ML'. Polymarket spread questions name the team the line belongs to: 'Spread: Celtics (-6.5)'."""
    if r['mtype'] == 'ml': return f"{side} ML"
    if r['mtype'] == 'total': return f"{side} {r['line']}"
    m = re.search(r':\s*(.+?)\s*\(([-+]?[\d.]+)\)', r.get('q') or '')
    if m:
        team, ln = m.group(1), float(m.group(2))
        mine = ln if side.lower().startswith(team.lower()[:6]) or team.lower().startswith(side.lower()[:6]) else -ln
        return f"{side} {mine:+g}"
    return f"{side} spread {r.get('line')}"


def ask(token):
    b = g(f"https://clob.polymarket.com/book?token_id={token}") or {}
    a = [float(x['price']) for x in b.get('asks') or []]
    return min(a) if a else None


def close_mid(cond, start):
    """Polymarket two-sided close from the public tape (last yes-buy and last no-buy before the start, within 2h), yes = outcome 0."""
    T = g(f"https://data-api.polymarket.com/trades?market={cond}&limit=500&takerOnly=true") or []
    meta = json.load(open(META)).get(cond) or {}; o0 = (meta.get('outcomes') or [None])[0]
    ly = ln = None
    for t in sorted(T, key=lambda t: t['timestamp']):
        if t['timestamp'] >= start: break
        p = float(t['price']); is0 = t.get('outcome') == o0; buy = t['side'] == 'BUY'
        py = p if is0 else 1 - p
        if is0 == buy: ly = (t['timestamp'], py)
        else: ln = (t['timestamp'], py)
    if ly and ln and abs(ly[0] - ln[0]) <= 7200: return (ly[1] + ln[1]) / 2
    return None


def main():
    if not os.path.exists(FILLS): print('[sharp_live] no fills yet'); return
    F = collections.defaultdict(list)
    for l in open(FILLS):
        try: r = json.loads(l)
        except Exception: continue
        if epoch(r['start']) > NOW - 6 * 3600: F[r['cond']].append(r)
    meta = json.load(open(META)) if os.path.exists(META) else {}
    paper = [json.loads(l) for l in open(PAPER)] if os.path.exists(PAPER) else []
    logged = {p['cond'] for p in paper}
    rows = []
    for cond, L in F.items():
        L.sort(key=lambda r: r['ts']); m = meta.get(cond) or {}; start = epoch(L[0]['start'])
        sides = collections.defaultdict(dict); flag = None
        for r in L:
            if flag is None:
                sides[r['bet']].setdefault(r['w'], r)
                other = [s for s in sides if s != r['bet']]
                if any(sides[s] for s in other): continue          # sharps already on both sides: no flag
                accts = sides[r['bet']]
                if r['rank'] <= TOP_RANK or len(accts) >= TWO: flag = dict(side=r['bet'], ts=r['ts'], trigger=r)
            else:
                sides[r['bet']].setdefault(r['w'], r)
        if not flag: continue
        side = flag['side']; opp = [r for r in L if r['bet'] != side and r['ts'] > flag['ts']]
        with_ = list(sides[side].values()); paid = sum(r['price'] * r['usd'] for r in with_) / sum(r['usd'] for r in with_)
        outs = L[0]['outcomes']; tok = (m.get('tokens') or [None, None])[outs.index(side)] if side in outs else None
        a = ask(tok) if tok and start > NOW else None
        row = dict(cond=cond, slug=L[0]['slug'], title=L[0].get('title'), mtype=L[0]['mtype'], start=dt.datetime.fromtimestamp(start, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                   bet=bet_text(L[0], side), side=side, flagged=dt.datetime.fromtimestamp(flag['ts'], dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                   why=('a top-50 account' if flag['trigger']['rank'] <= TOP_RANK and len(sides[side]) < 2 else f"{len(sides[side])} top-200 accounts"),
                   n_accounts=len(sides[side]), best_rank=min(r['rank'] for r in with_), usd=round(sum(r['usd'] for r in with_)), paid=round(paid, 3), ask=a,
                   status='other side' if opp else 'live', link=f"https://polymarket.us/event/{L[0]['slug']}",
                   other=dict(n_accounts=len({r['w'] for r in opp}), best_rank=min(r['rank'] for r in opp), usd=round(sum(r['usd'] for r in opp)),
                              first=dt.datetime.fromtimestamp(opp[0]['ts'], dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')) if opp else None)
        if opp:
            otok = (m.get('tokens') or [None, None])[outs.index(opp[0]['bet'])] if opp[0]['bet'] in outs else None
            row['exit_bid'] = round(1 - ask(otok), 3) if otok and start > NOW and ask(otok) else None   # selling our side = buying the other side's ask
        rows.append(row)
        if cond not in logged and start > NOW and a:
            paper.append(dict(cond=cond, slug=row['slug'], bet=row['bet'], side=side, mtype=row['mtype'], start=row['start'], flagged=row['flagged'],
                              logged=dt.datetime.fromtimestamp(NOW, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), price=a, why=row['why'], best_rank=row['best_rank']))
            logged.add(cond)
    # grade paper rows after the game: result from Gamma, CLV vs Polymarket's two-sided close
    for p in paper:
        if p.get('result') or epoch(p['start']) > NOW - 3 * 3600: continue
        M = g(f"https://gamma-api.polymarket.com/markets?condition_ids={p['cond']}") or []
        if not M: continue
        try: outs = json.loads(M[0]['outcomes']); px = [float(x) for x in json.loads(M[0].get('outcomePrices') or '[]')]
        except Exception: continue
        if sorted(px) != [0.0, 1.0]: continue
        won = px[outs.index(p['side'])] == 1.0; p['result'] = 'W' if won else 'L'
        p['pnl'] = round((1 - p['price']) / p['price'] if won else -1.0, 3)
        cm = close_mid(p['cond'], epoch(p['start']))
        if cm is not None: q = cm if outs.index(p['side']) == 0 else 1 - cm; p['clv'] = round(100 * (q - p['price']), 2)
    with open(PAPER, 'w') as f:
        for p in paper: f.write(json.dumps(p) + '\n')
    G_ = [p for p in paper if p.get('result')]
    rec = dict(n=len(G_), won=sum(p['result'] == 'W' for p in G_), units=round(sum(p['pnl'] for p in G_), 2),
               clv=round(sum(p['clv'] for p in G_ if 'clv' in p) / max(1, sum('clv' in p for p in G_)), 2) if G_ else None)
    rows.sort(key=lambda r: (r['status'] != 'live', r['start']))
    json.dump(dict(built=dt.datetime.fromtimestamp(NOW, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), rows=[r for r in rows if epoch(r['start']) > NOW],
                   record=rec, rule=f'top-{TOP_RANK} account, or {TWO}+ top-200 accounts on one side, none on the other'), open(OUT, 'w'), indent=1)
    print(f"[sharp_live] {sum(epoch(r['start']) > NOW for r in rows)} upcoming flagged markets ({sum(r['status'] == 'other side' for r in rows)} with a sharp on the other side since); paper {rec}")


if __name__ == '__main__':
    main()
