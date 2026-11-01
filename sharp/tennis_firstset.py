#!/usr/bin/env python3
"""First-set tennis backtest on Kalshi's settled history (Sean, 11/1: first-set betting is where he thinks tennis has an edge).

Data: Kalshi KXATPMATCH / KXWTAMATCH (match winner) and KXATPSETWINNER / KXWTASETWINNER set-1 markets with every trade
(release kalshi-history, pulled by .github/workflows/kalshi_backfill_tennis.yml), settled by Kalshi. Match start comes from the ESPN
result (data/tennis/results.jsonl, matched by surname + date): Kalshi keeps trading in play, so without a start a match is skipped.
Prices: two-sided mid of the last yes-buy and no-buy (exchange_backtest.px_at), and the ask (last taker price on the side bet,
within 30 minutes) as the realistic entry. Sizes are risk-equivalent (contracts x min(p, 1-p)). Train = first two thirds of the
dates, test = the last third. Flat 1u per bet, no fee (Kalshi's taker fee is ~1.5-2c a contract near even money).

  T1 calibration    set-1 price at T-15m vs how often that player won set 1, by price bucket (is the favorite under/over-priced?)
  T2 set vs match   set-1 price against the same player's match price: the market's set-1 discount vs the realised one, by
                    match-price bucket; bet the set-1 side where train says the discount is too big / too small
  T3 big vs small   $250 / $500+ fills net one way, $50-and-under the other, before T-15m: bet the big side on set 1
  T4 late move      set-1 mid moved 3+ / 5+ points in the 2 hours before T-15m: follow and fade
Writes data/research/tennis_firstset.json and prints the tables. Usage: python3 sharp/tennis_firstset.py"""
import os, sys, json, gzip, glob, math, re, collections, datetime as dt, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.exchange_backtest as EB

KH = os.path.join(ROOT, 'data', 'kalshi', 'history')
MATCH = ('KXATPMATCH', 'KXWTAMATCH'); SETS = ('KXATPSETWINNER', 'KXWTASETWINNER')
ENTRY = 900; ASK_FRESH = 1800


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return [t for t in re.sub(r'[^a-z\s-]', ' ', s).replace('-', ' ').split() if t]


def sur(n): t = norm(n); return t[-1] if t else ''


def load_markets():
    M = {}
    for f in glob.glob(os.path.join(KH, 'markets-*.jsonl')) + [os.path.join(KH, 'markets.jsonl')]:
        if not os.path.exists(f): continue
        for l in open(f):
            r = json.loads(l)
            if r.get('series') in MATCH + SETS: M[r['ticker']] = r
    return M


def load_trades(series):
    T = collections.defaultdict(list); f = os.path.join(KH, 'trades', f'{series}.jsonl.gz')
    if not os.path.exists(f): return T
    try:
        for l in gzip.open(f, 'rt'):
            r = json.loads(l); y = r['taker'] == 'yes'
            T[r['ticker']].append((ts(r['ts']), r['yes'], r['n'] * min(r['yes'], 1 - r['yes']), 1 if y else -1))
    except (EOFError, OSError): pass
    for k in T: T[k].sort()
    return T


def espn_starts():
    """(date, surname a, surname b) both orders -> (start epoch, first-set winner surname, record)."""
    S = {}
    p = os.path.join(ROOT, 'data', 'tennis', 'results.jsonl')
    for l in open(p):
        r = json.loads(l); d = r['start'][:10]; a, b = sur(r['p1']), sur(r['p2'])
        fs = sur(r['p1']) if r.get('first_set_winner') == 'p1' else (sur(r['p2']) if r.get('first_set_winner') == 'p2' else None)
        for dd in (d,):
            S[(dd, a, b)] = S[(dd, b, a)] = (ts(r['start']), fs, r)
    return S


def code_date(code):
    m = re.match(r'(\d\d)([A-Z]{3})(\d\d)', code)
    if not m: return None
    mon = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'].index(m.group(2)) + 1
    return dt.date(2000 + int(m.group(1)), mon, int(m.group(3)))


def build():
    M = load_markets(); TR = {}
    for s in MATCH + SETS: TR.update(load_trades(s))
    S = espn_starts()
    ev = collections.defaultdict(lambda: dict(match={}, set1={}))
    for tk, m in M.items():
        parts = m['event_ticker'].split('-')
        if m['series'] in SETS:
            if len(parts) < 3 or parts[-1] != '1': continue
            ev[parts[1]]['set1'][tk] = m
        else: ev[parts[1]]['match'][tk] = m
    rows = []; miss = collections.Counter()
    for code, d in ev.items():
        if len(d['set1']) != 2: miss['no set-1 pair'] += 1; continue
        names = {tk: m.get('sub') or '' for tk, m in d['set1'].items()}
        a, b = [sur(n) for n in names.values()]
        cd = code_date(code)
        hit = None
        for dd in ((cd + dt.timedelta(days=k)).isoformat() for k in (0, -1, 1)) if cd else []:
            hit = S.get((dd, a, b))
            if hit: break
        if not hit: miss['no ESPN start'] += 1; continue
        start, fs_winner, rec = hit
        if rec.get('retired') and not rec.get('first_set_complete'): miss['first set not completed'] += 1; continue
        for tk, m in d['set1'].items():
            if m.get('result') not in ('yes', 'no'): continue
            player = names[tk]; pre = [x for x in TR.get(tk, []) if x[0] < start]
            if len(pre) < 3: continue
            mtk = next((t for t, mm in d['match'].items() if sur(mm.get('sub') or '') == sur(player)), None)
            mpre = [x for x in TR.get(mtk, []) if x[0] < start] if mtk else []
            rows.append(dict(code=code, tour='atp' if m['series'].startswith('KXATP') else 'wta', player=player, start=start, won=1 if m['result'] == 'yes' else 0,
                             espn_fs=fs_winner, set1=pre, match=mpre, result_check=(fs_winner == sur(player)) == (m['result'] == 'yes') if fs_winner else None))
            break                                   # one row per match: the first player's set-1 market (the other is its mirror)
    return rows, miss


def price(L, t):
    p, two = EB.px_at(L, t)
    return p if two == 2 else None


def ask(L, t, d):
    """What a taker paid for the side bet (d=+1 yes, -1 no) if it printed within ASK_FRESH of t."""
    x = next((x for x in reversed(L) if x[0] <= t and x[3] == d), None)
    if not x or t - x[0] > ASK_FRESH: return None
    return x[1] if d > 0 else 1 - x[1]


def bet(r, d, t, entry='mid'):
    p = price(r['set1'], t)
    if p is None: return None
    pr = (p if d > 0 else 1 - p) if entry == 'mid' else ask(r['set1'], t, d)
    if pr is None or not 0.03 < pr < 0.97: return None
    won = r['won'] if d > 0 else 1 - r['won']
    cl = price(r['set1'], r['start'] - 60)
    return dict(roi=(1 - pr) / pr if won else -1.0, won=won, price=pr, clv=None if cl is None else 100 * ((cl if d > 0 else 1 - cl) - pr))


def stats(B):
    B = [b for b in B if b]
    if not B: return dict(n=0)
    r = [b['roi'] for b in B]; mu = sum(r) / len(r); sd = (sum((x - mu) ** 2 for x in r) / max(1, len(r) - 1)) ** 0.5
    c = [b['clv'] for b in B if b['clv'] is not None]
    return dict(n=len(B), win=round(sum(b['won'] for b in B) / len(B), 3), price=round(sum(b['price'] for b in B) / len(B), 3), roi=round(100 * mu, 1),
                z=round(mu / (sd / math.sqrt(len(B))), 2) if len(B) > 2 and sd > 0 else 0, clv=round(sum(c) / len(c), 2) if c else None)


def main():
    rows, miss = build()
    chk = [r['result_check'] for r in rows if r['result_check'] is not None]
    print(f"[firstset] {len(rows)} matches with a set-1 market, ESPN start and pregame trades; skipped {dict(miss)}; "
          f"Kalshi vs ESPN first-set winner agree {sum(chk)}/{len(chk)}")
    if not rows: return
    rows.sort(key=lambda r: r['start']); cut = rows[int(len(rows) * 2 / 3)]['start']
    split = lambda r: 'train' if r['start'] < cut else 'test'
    out = {}
    # T1 calibration
    print("\nT1  set-1 price 15 min before start vs set-1 result (favourite side), by price bucket")
    buck = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        p = price(r['set1'], r['start'] - ENTRY)
        if p is None: continue
        fav_p = max(p, 1 - p); fav_won = r['won'] if p >= 0.5 else 1 - r['won']
        b = min(int((fav_p - 0.5) / 0.05), 8)
        buck[b][split(r)].append((fav_p, fav_won)); buck[b]['all'].append((fav_p, fav_won))
    t1 = {}
    for b in sorted(buck):
        lo = 0.5 + 0.05 * b; cells = []
        for k in ('train', 'test', 'all'):
            L = buck[b][k]
            if L: cells.append(f"{k} n {len(L):>4} priced {sum(x for x, _ in L) / len(L):.3f} won {sum(y for _, y in L) / len(L):.3f}")
        t1[f"{lo:.2f}"] = {k: dict(n=len(v), priced=sum(x for x, _ in v) / len(v), won=sum(y for _, y in v) / len(v)) for k, v in buck[b].items() if v}
        print(f"  fav {lo:.2f}-{lo + 0.05:.2f}: " + ' | '.join(cells))
    out['T1'] = t1
    # T2 set vs match
    print("\nT2  set-1 price vs the same player's match price (15 min out), favourite by match price")
    t2rows = []
    for r in rows:
        ps, pm = price(r['set1'], r['start'] - ENTRY), price(r['match'], r['start'] - ENTRY) if r['match'] else None
        if ps is None or pm is None: continue
        fav = 1 if pm >= 0.5 else -1
        t2rows.append(dict(r=r, pm=pm if fav > 0 else 1 - pm, ps=ps if fav > 0 else 1 - ps, won=r['won'] if fav > 0 else 1 - r['won'], fav=fav, split=split(r)))
    mb = collections.defaultdict(lambda: collections.defaultdict(list))
    for x in t2rows: mb[min(int((x['pm'] - 0.5) / 0.1), 4)][x['split']].append(x)
    rule = {}
    for b in sorted(mb):
        lo = 0.5 + 0.1 * b; line = []
        for k in ('train', 'test'):
            L = mb[b][k]
            if L: line.append(f"{k} n {len(L):>4} match {sum(x['pm'] for x in L) / len(L):.3f} set1 priced {sum(x['ps'] for x in L) / len(L):.3f} set1 won {sum(x['won'] for x in L) / len(L):.3f}")
        tr = mb[b]['train']
        if len(tr) >= 50: rule[b] = sum(x['won'] for x in tr) / len(tr) - sum(x['ps'] for x in tr) / len(tr)   # + = favourite under-priced on set 1
        print(f"  match fav {lo:.1f}-{lo + 0.1:.1f}: " + ' | '.join(line))
    for entry in ('mid', 'ask'):
        B = {'train': [], 'test': []}
        for x in t2rows:
            b = min(int((x['pm'] - 0.5) / 0.1), 4)
            if b not in rule or abs(rule[b]) < 0.02: continue
            d = x['fav'] * (1 if rule[b] > 0 else -1)
            B[x['split']].append(bet(x['r'], d, x['r']['start'] - ENTRY, entry))
        out[f'T2_{entry}'] = {k: stats(v) for k, v in B.items()}
        print(f"  rule from train (bet the set-1 side the train buckets say is under-priced by 2+ pts), entry at {entry}: train {stats(B['train'])}  TEST {stats(B['test'])}")
    # T3 big vs small
    print("\nT3  big vs small money on set 1 before T-15m (risk-equivalent)")
    for th in (250, 500, 1000):
        for entry in ('mid', 'ask'):
            B = {'train': [], 'test': []}
            for r in rows:
                E = r['start'] - ENTRY; pre = [x for x in r['set1'] if x[0] < E]
                bn = sum(u * d for _, _, u, d in pre if u >= th); sn = sum(u * d for _, _, u, d in pre if u <= 50)
                if abs(bn) < th or sn == 0 or (bn > 0) == (sn > 0): continue
                B[split(r)].append(bet(r, 1 if bn > 0 else -1, E, entry))
            out[f'T3_{th}_{entry}'] = {k: stats(v) for k, v in B.items()}
            print(f"  big >= ${th} vs small <= $50, entry {entry}: train {stats(B['train'])}  TEST {stats(B['test'])}")
    # T4 late move
    print("\nT4  set-1 mid moved over the 2 hours before T-15m")
    for mv in (3, 5):
        for kind in ('follow', 'fade'):
            for entry in ('mid', 'ask'):
                B = {'train': [], 'test': []}
                for r in rows:
                    E = r['start'] - ENTRY; p1, p0 = price(r['set1'], E), price(r['set1'], E - 7200)
                    if p1 is None or p0 is None or abs(100 * (p1 - p0)) < mv: continue
                    d = (1 if p1 > p0 else -1) * (1 if kind == 'follow' else -1)
                    B[split(r)].append(bet(r, d, E, entry))
                out[f'T4_{mv}_{kind}_{entry}'] = {k: stats(v) for k, v in B.items()}
                print(f"  {mv}+ pts, {kind}, entry {entry}: train {stats(B['train'])}  TEST {stats(B['test'])}")
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'tennis_firstset.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
