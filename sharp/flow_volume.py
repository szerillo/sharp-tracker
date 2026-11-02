#!/usr/bin/env python3
"""Big vs small money, round 3 (Sean, 11/2): bigger single fills, busier markets, and Polymarket.

Rounds 1-2 (docs/flow_split_2026-10-31.md) tested Kalshi and Novig with fill cuts up to $2,500 and found nothing. Not tested yet:
  - single fills of $5,000 and $10,000+ (whales);
  - market volume: does the signal only work on busy markets (where a $1k fill is not just noise in a thin book), or on thin ones
    (where a big fill is more likely informed)?
  - Polymarket (data/polymarket/history, loggers/polymarket_history.py): taker fills since 2024 on settled game markets.
Grid per venue: entry T-6h / T-1h / T-15m  x  big cut $500 / $1k / $2.5k / $5k / $10k  x  DIV (big and small money on opposite sides)
or BIG (big money net, small ignored)  x  market volume before entry: any / $25k+ / $100k+ / $500k+.
Sizes are risk-equivalent (contracts x min(p, 1-p)); small = fills of $50 and under. One bet per game x market type (the line with
the largest |big_net|). Entry = the two-sided mid at the entry time (sharp.exchange_backtest.px_at), no fee; graded on the result and
on CLV (the same side's mid at the start minus entry).
Pre-registered read (written before any result): split each venue's games by start time, first two thirds = train, last third =
holdout. A version "passes" only with train n >= 100 and z >= 2, then holdout n >= 50 and ROI > 0. Luck alone gives about 2.5% of
versions a train z >= 2, and half of those a positive holdout; a real effect needs clearly more passes than that, and holdout z >= 1.5.
Writes data/research/flow_volume.json. Usage: python3 sharp/flow_volume.py [kalshi novig poly]"""
import os, sys, json, gzip, glob, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
import sharp.exchange_backtest as EB
SMALL = 50.0; CUTS = (500.0, 1000.0, 2500.0, 5000.0, 10000.0); ENTRIES = {'T-6h': 6 * 3600, 'T-1h': 3600, 'T-15m': 900}
VOLS = (0, 25000, 100000, 500000); OUT = os.path.join(ROOT, 'data', 'research', 'flow_volume.json')
PH = os.path.join(ROOT, 'data', 'polymarket', 'history')


def poly_rows():
    """-> [(venue, sport, mtype, game_key, start_epoch, result_yes, trades[(t, p_yes, usd, dir)])], plus wallets per trade (for the wallet test)."""
    out = []
    for l in open(os.path.join(PH, 'catalog.jsonl')):
        c = json.loads(l); p = os.path.join(PH, 'trades', f"{c['cond']}.jsonl.gz")
        if not os.path.exists(p) or not c.get('start'): continue
        st = dt.datetime.fromisoformat(c['start'].replace(' ', 'T').replace('+00', '+00:00')).timestamp()
        o0 = c['outcomes'][0]; L = []
        try:
            for l2 in gzip.open(p, 'rt'):
                t = json.loads(l2)
                if 'ts' not in t or t['ts'] >= st: continue
                pr = float(t['price']); sz = float(t['size'])
                if not 0.01 <= pr <= 0.99: continue
                is0 = t.get('outcome') == o0; buy = t['side'] == 'BUY'
                d = 1 if is0 == buy else -1; py = pr if is0 else 1 - pr
                L.append((t['ts'], py, sz * min(pr, 1 - pr), d, t.get('wallet')))
        except (EOFError, OSError): continue
        if L: out.append(('Polymarket', c['tag'], c['market'], f"{c['event']}|{c['market']}", st, 1 if c['winner'] == o0 else 0, L))
    return out


def evaluate(rows, venue):
    rows = sorted(rows, key=lambda r: r[4])
    games = sorted({r[3] for r in rows}, key=lambda g: min(r[4] for r in rows if r[3] == g)) if len(rows) < 1 else None
    starts = sorted(r[4] for r in rows); cut_t = starts[int(len(starts) * 2 / 3)] if starts else 0
    res = {}
    # precompute per row: sorted pregame trades
    R = [(sp, mt, gk, start, ry, sorted(x[:4] for x in L)) for v, sp, mt, gk, start, ry, L in rows]
    for entry, sec in ENTRIES.items():
        feats = []
        for sp, mt, gk, start, ry, L in R:
            E = start - sec; pre = [x for x in L if x[0] < E]
            if len(pre) < 5: continue
            px, two = EB.px_at(pre, E)
            if px is None or two != 2: continue
            cl, two_c = EB.px_at(L, start)
            vol = sum(x[2] for x in pre); sn = sum(x[2] * x[3] for x in pre if x[2] <= SMALL)
            bn = {c: sum(x[2] * x[3] for x in pre if x[2] >= c) for c in CUTS}
            feats.append((sp, mt, gk, start, ry, px, cl if two_c == 2 else None, vol, sn, bn))
        for c in CUTS:
            for kind in ('DIV', 'BIG'):
                for vmin in VOLS:
                    best = {}
                    for sp, mt, gk, start, ry, px, cl, vol, sn, bn in feats:
                        b = bn[c]
                        if abs(b) < c or vol < vmin: continue
                        if kind == 'DIV' and (sn == 0 or (b > 0) == (sn > 0)): continue
                        d = 1 if b > 0 else -1; price = px if d > 0 else 1 - px
                        if not 0.05 < price < 0.95: continue
                        won = ry if d > 0 else 1 - ry
                        rec = dict(roi=(1 - price) / price if won else -1.0, won=won, price=price, clv=None if cl is None else 100 * ((cl if d > 0 else 1 - cl) - price),
                                   big=abs(b), hold=start >= cut_t, sport=sp)
                        if gk not in best or rec['big'] > best[gk]['big']: best[gk] = rec
                    for part, B in (('train', [b for b in best.values() if not b['hold']]), ('hold', [b for b in best.values() if b['hold']])):
                        if not B: continue
                        roi = [b['roi'] for b in B]; mu = sum(roi) / len(roi); sd = (sum((x - mu) ** 2 for x in roi) / max(1, len(roi) - 1)) ** 0.5
                        cv = [b['clv'] for b in B if b['clv'] is not None]
                        res.setdefault(f"{venue}|{entry}|{int(c)}|{kind}|vol{vmin}", {})[part] = dict(
                            n=len(B), roi=round(100 * mu, 1), z=round(mu / (sd / math.sqrt(len(B))), 2) if sd and len(B) > 1 else None,
                            win=round(sum(b['won'] for b in B) / len(B), 3), price=round(sum(b['price'] for b in B) / len(B), 3),
                            clv=round(sum(cv) / len(cv), 2) if cv else None)
    return res, dt.datetime.fromtimestamp(cut_t, dt.timezone.utc).strftime('%Y-%m-%d') if cut_t else None


def wallets(rows):
    """Polymarket only: does a wallet's past pregame record predict its future bets? Train = first two thirds by start time.
    Wallet score on train = mean CLV of its pregame fills ($100+ risk-equivalent; fill price vs the side's mid at the start), min 30
    fills on 15+ games. Holdout: follow the top-50 / top-200 wallets by train CLV. Entry is NOT at their fill price: the next two-sided
    mid 5 minutes after their fill (what a follower could get), first qualifying fill per game x market, graded on result and CLV."""
    rows = sorted(rows, key=lambda r: r[4]); starts = [r[4] for r in rows]; cut_t = starts[int(len(starts) * 2 / 3)]
    W = collections.defaultdict(lambda: dict(clv=[], games=set()))
    for v, sp, mt, gk, start, ry, L in rows:
        if start >= cut_t: continue
        L = sorted(L); cl, two = EB.px_at([x[:4] for x in L], start)
        if cl is None or two != 2: continue
        for t, py, usd, d, w in L:
            if usd < 100 or not w: continue
            price = py if d > 0 else 1 - py
            W[w]['clv'].append(100 * ((cl if d > 0 else 1 - cl) - price)); W[w]['games'].add(gk)
    score = {w: sum(x['clv']) / len(x['clv']) for w, x in W.items() if len(x['clv']) >= 30 and len(x['games']) >= 15}
    ranked = sorted(score, key=lambda w: -score[w])
    out = dict(wallets_scored=len(score), train_cut=dt.datetime.fromtimestamp(cut_t, dt.timezone.utc).strftime('%Y-%m-%d'))
    for top in (50, 200, 'bottom200'):
        S = set(ranked[-200:]) if top == 'bottom200' else set(ranked[:top])
        recs = []
        for v, sp, mt, gk, start, ry, L in rows:
            if start < cut_t: continue
            L = sorted(L); L4 = [x[:4] for x in L]
            hit = next((x for x in L if x[4] in S and x[2] >= 100), None)
            if not hit: continue
            E = hit[0] + 300
            if E >= start: continue
            px, two = EB.px_at([x for x in L4 if x[0] <= E], E)
            if px is None or two != 2: continue
            cl, two_c = EB.px_at(L4, start); d = hit[3]; price = px if d > 0 else 1 - px
            if not 0.05 < price < 0.95: continue
            won = ry if d > 0 else 1 - ry
            recs.append(dict(roi=(1 - price) / price if won else -1.0, clv=None if two_c != 2 else 100 * ((cl if d > 0 else 1 - cl) - price)))
        if not recs: continue
        roi = [r['roi'] for r in recs]; mu = sum(roi) / len(roi); sd = (sum((x - mu) ** 2 for x in roi) / max(1, len(roi) - 1)) ** 0.5
        cv = [r['clv'] for r in recs if r['clv'] is not None]
        out[f'top{top}' if top != 'bottom200' else 'bottom200'] = dict(n=len(recs), roi=round(100 * mu, 1), z=round(mu / (sd / math.sqrt(len(recs))), 2),
                                                                      clv=round(sum(cv) / len(cv), 2) if cv else None, train_clv_floor=round(min(score[w] for w in S), 2))
    return out


def main():
    want = sys.argv[1:] or ['kalshi', 'novig', 'poly']
    allres = json.load(open(OUT)) if os.path.exists(OUT) else {}
    if 'kalshi' in want or 'novig' in want:
        import sharp.flow_split as FS
        rows = FS.market_rows()
        for v in ('Kalshi', 'Novig'):
            if v.lower() not in want: continue
            r, cut = evaluate([x for x in rows if x[0] == v], v); allres[v] = dict(holdout_from=cut, cells=r); print(f"[flow_volume] {v}: {len(r)} versions, holdout from {cut}", flush=True)
        del rows
    if 'poly' in want:
        rows = poly_rows(); print(f"[flow_volume] Polymarket: {len(rows)} markets with pregame trades", flush=True)
        r, cut = evaluate(rows, 'Polymarket'); allres['Polymarket'] = dict(holdout_from=cut, cells=r, wallets=wallets(rows))
    json.dump(allres, open(OUT, 'w'), indent=1)
    for v, d in allres.items():
        C = d['cells']; tr = [k for k, x in C.items() if 'train' in x and x['train']['n'] >= 100 and (x['train']['z'] or 0) >= 2]
        ok = [k for k in tr if 'hold' in C[k] and C[k]['hold']['n'] >= 50 and C[k]['hold']['roi'] > 0]
        print(f"\n== {v}: {len(C)} versions, holdout from {d['holdout_from']}; train finds (n>=100, z>=2): {len(tr)} (luck ~{0.025 * len(C):.0f}); positive in holdout: {len(ok)}")
        for k in sorted(ok, key=lambda k: -(C[k]['hold']['z'] or 0))[:15]:
            print(f"  {k:36} train n {C[k]['train']['n']:5} {C[k]['train']['roi']:+6.1f}% z {C[k]['train']['z']:5}  |  hold n {C[k]['hold']['n']:5} {C[k]['hold']['roi']:+6.1f}% z {C[k]['hold']['z']}  clv {C[k]['hold']['clv']}")
        if d.get('wallets'): print('  wallets:', d['wallets'])


if __name__ == '__main__':
    main()
