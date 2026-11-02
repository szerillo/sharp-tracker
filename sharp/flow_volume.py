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
LAGS = (60, 300, 900, 3600)
SMALL = 50.0; CUTS = (500.0, 1000.0, 2500.0, 5000.0, 10000.0); ENTRIES = {'T-6h': 6 * 3600, 'T-1h': 3600, 'T-15m': 900}
VOLS = (0, 25000, 100000, 500000); OUT = os.path.join(ROOT, 'data', 'research', 'flow_volume.json')
PH = os.path.join(ROOT, 'data', 'polymarket', 'history')


def poly_markets():
    """Polymarket settled game markets with a trade file: (catalog row, start epoch), oldest first."""
    out = []
    for l in open(os.path.join(PH, 'catalog.jsonl')):
        c = json.loads(l); p = os.path.join(PH, 'trades', f"{c['cond']}.jsonl.gz")
        if not os.path.exists(p) or not c.get('start'): continue
        out.append((c, dt.datetime.fromisoformat(c['start'].replace(' ', 'T').replace('+00', '+00:00')).timestamp()))
    return sorted(out, key=lambda x: x[1])


def poly_trades(c, st):
    """Pregame taker fills of one market -> sorted [(t, p_yes, usd_risk_equivalent, dir, wallet)], yes = the first outcome."""
    o0 = c['outcomes'][0]; L = []
    try:
        for l2 in gzip.open(os.path.join(PH, 'trades', f"{c['cond']}.jsonl.gz"), 'rt'):
            t = json.loads(l2)
            if 'ts' not in t or t['ts'] >= st: continue
            pr = float(t['price']); sz = float(t['size'])
            if not 0.01 <= pr <= 0.99: continue
            is0 = t.get('outcome') == o0; buy = t['side'] == 'BUY'
            L.append((t['ts'], pr if is0 else 1 - pr, sz * min(pr, 1 - pr), 1 if is0 == buy else -1, t.get('wallet')))
    except (EOFError, OSError): return []
    return sorted(L)


def feats_for(sp, mt, gk, start, ry, L):
    """One market -> {entry: feature tuple} (the grid only needs these, so trades are not kept in memory)."""
    out = {}
    cl, two_c = EB.px_at(L, start)
    for entry, sec in ENTRIES.items():
        E = start - sec; pre = [x for x in L if x[0] < E]
        if len(pre) < 5: continue
        px, two = EB.px_at(pre, E)
        if px is None or two != 2: continue
        vol = sum(x[2] for x in pre); sn = sum(x[2] * x[3] for x in pre if x[2] <= SMALL)
        out[entry] = (sp, mt, gk, start, ry, px, cl if two_c == 2 else None, vol, sn, {c: sum(x[2] * x[3] for x in pre if x[2] >= c) for c in CUTS})
    return out


def grid(F, cut_t, venue):
    res = {}
    for entry, feats in F.items():
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
    return res


def evaluate(rows, venue):
    starts = sorted(r[4] for r in rows); cut_t = starts[int(len(starts) * 2 / 3)] if starts else 0
    F = collections.defaultdict(list)
    for v, sp, mt, gk, start, ry, L in rows:
        for e, f in feats_for(sp, mt, gk, start, ry, sorted(x[:4] for x in L)).items(): F[e].append(f)
    return grid(F, cut_t, venue), dt.datetime.fromtimestamp(cut_t, dt.timezone.utc).strftime('%Y-%m-%d') if cut_t else None


def poly(MK):
    """Grid + wallet test on Polymarket, streaming one market at a time.
    Wallet test: does a wallet's past pregame record predict its future bets? Train = the first two thirds of markets by start time.
    Wallet score on train = mean CLV of its pregame fills ($100+ risk-equivalent; fill price vs the side's two-sided mid at the start),
    min 30 fills on 15+ games. Holdout: follow the top-50 / top-200 wallets (and, as a check, the bottom 200). Entry is NOT their fill
    price: the two-sided mid 5 minutes after their first qualifying fill on that market (what a follower could get), graded on result and CLV."""
    cut_t = MK[int(len(MK) * 2 / 3)][1]
    F = collections.defaultdict(list)
    W = collections.defaultdict(lambda: [0.0, 0, set()])
    scored = None
    hold_first = []          # holdout markets: per wallet, its first $100+ fill (t, dir) -> kept compactly
    for i, (c, st) in enumerate(MK):
        L = poly_trades(c, st)
        if not L: continue
        gk = f"{c['event']}|{c['market']}"; ry = 1 if c['winner'] == c['outcomes'][0] else 0
        L4 = [x[:4] for x in L]
        for e, f in feats_for(c['tag'], c['market'], gk, st, ry, L4).items(): F[e].append(f)
        cl, two = EB.px_at(L4, st)
        if st < cut_t:
            if cl is None or two != 2: continue
            for t, py, usd, d, w in L:
                if usd < 100 or not w: continue
                price = py if d > 0 else 1 - py; x = W[w]
                x[0] += 100 * ((cl if d > 0 else 1 - cl) - price); x[1] += 1; x[2].add(gk)
        else:
            if scored is None:           # markets are in start order, so the train pass is complete here: only scored wallets matter
                scored = {w for w, x in W.items() if x[1] >= 30 and len(x[2]) >= 15}
            firsts = {}
            for t, py, usd, d, w in L:
                if usd >= 100 and w in scored and w not in firsts: firsts[w] = (t, d)
            # follower entries for each wallet are resolved later; keep the follow price now (cheap) for every first fill
            ent = {}
            for w, (t, d) in firsts.items():
                pr = {}
                for lag in LAGS:                 # follower entry: the two-sided mid `lag` seconds after their fill
                    E = t + lag
                    if E >= st: continue
                    px, tw = EB.px_at([x for x in L4 if x[0] <= E], E)
                    if px is None or tw != 2: continue
                    price = px if d > 0 else 1 - px
                    if 0.05 < price < 0.95: pr[lag] = price
                if pr: ent[w] = (t, d, pr)
            hold_first.append((gk, ry, None if two != 2 else cl, ent, c['tag']))
        if i % 2000 == 0: print(f"[flow_volume] Polymarket {i}/{len(MK)} markets", flush=True)
    res = grid(F, cut_t, 'Polymarket'); del F
    score = {w: x[0] / x[1] for w, x in W.items() if x[1] >= 30 and len(x[2]) >= 15}
    ranked = sorted(score, key=lambda w: -score[w])
    wal = dict(wallets_scored=len(score), train_cut=dt.datetime.fromtimestamp(cut_t, dt.timezone.utc).strftime('%Y-%m-%d'))
    def stat(recs):
        roi = [r[0] for r in recs]; mu = sum(roi) / len(roi); sd = (sum((x - mu) ** 2 for x in roi) / max(1, len(roi) - 1)) ** 0.5
        cv = [r[1] for r in recs if r[1] is not None]; cm = sum(cv) / len(cv) if cv else None
        csd = (sum((x - cm) ** 2 for x in cv) / max(1, len(cv) - 1)) ** 0.5 if cv else None
        return dict(n=len(recs), roi=round(100 * mu, 1), z=round(mu / (sd / math.sqrt(len(recs))), 2) if sd else None,
                    clv=round(cm, 2) if cv else None, clv_z=round(cm / (csd / math.sqrt(len(cv))), 2) if cv and csd else None)
    for name, S in (('top50', set(ranked[:50])), ('top200', set(ranked[:200])), ('top1000', set(ranked[:1000])), ('bottom200', set(ranked[-200:]))):
        for lag in LAGS:
            recs = []; bys = collections.defaultdict(list)
            for gk, ry, cl, ent, tag in hold_first:
                hits = sorted((v[0], v[1], v[2][lag]) for w, v in ent.items() if w in S and lag in v[2])
                if not hits: continue
                t, d, price = hits[0]; won = ry if d > 0 else 1 - ry
                r = ((1 - price) / price if won else -1.0, None if cl is None else 100 * ((cl if d > 0 else 1 - cl) - price))
                recs.append(r); bys[tag].append(r)
            if not recs: continue
            k = f'{name}_lag{lag // 60}m'; wal[k] = stat(recs); wal[k]['train_clv_floor'] = round(min(score[w] for w in S), 2) if S else None
            if lag == 300: wal[k]['by_sport'] = {t: stat(v) for t, v in bys.items() if len(v) >= 20}
    return res, wal['train_cut'], wal


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
        MK = poly_markets(); print(f"[flow_volume] Polymarket: {len(MK)} markets with a trade file", flush=True)
        r, cut, wal = poly(MK); allres['Polymarket'] = dict(holdout_from=cut, cells=r, wallets=wal)
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
