#!/usr/bin/env python3
"""Live watch list for the pre-registered tennis first-set rule tennis_fs_fav (docs/tennis_firstset_2026-11-01.md), and its paper log.

For every upcoming tennis match in the latest tick snapshots (data/tennis/ticks + ticks5):
  match favourite = Pinnacle's no-vig match price (falls back to the Kalshi / Novig match mid when Pinnacle has no line)
  fair set-1 price for the favourite = independent-sets model + 3.3 points (the Novig + ESPN gap), never above the match price
  best bettable set-1 price = the lowest cost of the favourite's set 1 at Kalshi (ask + taker fee) or Novig (ask); Pinnacle's set-1
  no-vig price is shown as the sharp reference, not as a place to bet
A match is flagged when the favourite is 55%+ on the match and fair minus cost is 1 point or more. The first time a match is
flagged it is written to data/tennis/fs_paper.jsonl (price, venue, Pinnacle set-1 reference, Kalshi set-1 ticker) and graded once the
match starts: from the ESPN set score, or from Kalshi's settlement for Challenger / ITF matches ESPN does not carry. CLV = Pinnacle's
last pregame no-vig set-1 price minus the price taken.
Writes data/state/tennis_watch.json. Usage: python3 sharp/tennis_watch.py"""
import os, sys, json, gzip, glob, math, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
TD = os.path.join(ROOT, 'data', 'tennis'); OUT = os.path.join(ROOT, 'data', 'state', 'tennis_watch.json'); PAPER = os.path.join(TD, 'fs_paper.jsonl')
NOW = dt.datetime.fromisoformat(os.environ['TENNIS_NOW'].replace('Z', '+00:00')) if os.environ.get('TENNIS_NOW') else dt.datetime.now(dt.timezone.utc);   # TENNIS_NOW replays a past run (backfill)
GAP = 0.033; MIN_FAV = 0.55; MIN_EDGE = 0.01; KFEE = 0.07; STALE_MIN = 45


def s_from_match(p):
    lo, hi = 0.0, 1.0
    for _ in range(50):
        m = (lo + hi) / 2
        if m * m * (3 - 2 * m) < p: lo = m
        else: hi = m
    return (lo + hi) / 2


# ---- Tennis Abstract set-1 model (11/4, sharp/tennis_ta.py --map): fair set-1 = the observed set-1 rate of favourites at this calibrated
# match probability, by tour and level (ATP / WTA x tour / Challenger / ITF, best-of-5 for men's slams), from 621k matches 2015-2026,
# plus a serve-profile adjustment (both players' trailing hold rates): a dog who holds 3%+ more than the favourite takes set 1 about
# 4 points more often than the curve says; a favourite who holds more, 1.3 points less often than... (see docs/tennis_ta_2026-11-04.md).
MAP = json.load(open(os.path.join(ROOT, 'data', 'research', 'tennis_set1_map.json'))) if os.path.exists(os.path.join(ROOT, 'data', 'research', 'tennis_set1_map.json')) else None
PROF = json.load(open(os.path.join(ROOT, 'data', 'state', 'tennis_profiles.json'))) if os.path.exists(os.path.join(ROOT, 'data', 'state', 'tennis_profiles.json')) else {}
SLAMS = ('australian open', 'roland garros', 'french open', 'wimbledon', 'us open')
SERVE_ADJ = {'dog': -0.041, 'fav': 0.013, 'similar': -0.013}


def ta_group(e):
    t = (e.get('tour') or '').lower(); tn = (e.get('tournament') or '').lower()
    tour = 'wta' if t.startswith('wta') or 'wta' in tn or 'women' in tn or 'ladies' in tn else 'atp'
    lvl = 'chall' if 'challenger' in tn or 'challenger' in t else 'itf' if t.startswith('itf') or 'itf' in tn or 'futures' in tn else 'tour'
    if lvl == 'itf' and tour == 'atp': lvl = 'itf'
    bo5 = tour == 'atp' and lvl == 'tour' and any(s in tn for s in SLAMS)
    g = f"{tour}_{lvl}" + ('_bo5' if bo5 else '')
    return g if MAP and g in MAP['groups'] else (f"{tour}_tour" if MAP and f"{tour}_tour" in MAP['groups'] else None)


def ta_interp(cv, x):
    if x <= cv[0][0]: return cv[0][1] + (x - cv[0][0]) * (cv[0][1] - 0.5) / max(1e-6, cv[0][0] - 0.5)
    for (x0, y0, _), (x1, y1, _) in zip(cv, cv[1:]):
        if x0 <= x <= x1: return y0 + (y1 - y0) * (x - x0) / max(1e-9, x1 - x0)
    return cv[-1][1]                     # past the last well-populated bin: flat (the top bins are thin)


def _norm(s):
    import unicodedata, re
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return [t for t in re.sub(r'[^a-z\s-]', ' ', s).replace('-', ' ').split() if t]


_PIDX = None
def profile(name):
    """Tennis Abstract profile by name: same surname and first initial (or a unique surname)."""
    global _PIDX
    if _PIDX is None:
        _PIDX = {}
        for n, p in PROF.items():
            t = _norm(n)
            if t: _PIDX.setdefault(t[-1], []).append((t[0][0] if t else '', n, p))
    t = _norm(name)
    if not t: return None
    c = _PIDX.get(t[-1]) or []
    hit = [x for x in c if x[0] == t[0][0]] or (c if len(c) == 1 else [])
    return hit[0][2] if len(hit) == 1 else None


def serve_note(pf_, po_):
    """-> (adjustment, text) from the two players' trailing hold rates, None when either is unknown."""
    if not pf_ or not po_ or pf_.get('hold') is None or po_.get('hold') is None: return None
    hf, ho = pf_['hold'], po_['hold']
    k = 'dog' if ho > hf + 0.03 else 'fav' if hf > ho + 0.03 else 'similar'
    return SERVE_ADJ[k], f"holds: favourite {100 * hf:.0f}%, opponent {100 * ho:.0f}% ({'dog is the bigger server' if k == 'dog' else 'favourite is the bigger server' if k == 'fav' else 'similar'})"


def implied(a): return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def latest():
    """(event, market, venue, side) -> latest tick within STALE_MIN."""
    L = {}
    for d in ('ticks', 'ticks5'):
        for f in sorted(glob.glob(os.path.join(TD, d, '*.jsonl.gz')))[-2:]:
            try:
                for l in gzip.open(f, 'rt'):
                    r = json.loads(l)
                    if r['market'] not in ('ml', '1s_ml') or ts(r['ts']) > NOW: continue
                    k = (r['event_id'], r['market'], r['venue'], r['side'])
                    if k not in L or r['ts'] > L[k]['ts']: L[k] = r
            except (EOFError, OSError): pass
    return {k: v for k, v in L.items() if (NOW - ts(v['ts'])).total_seconds() <= STALE_MIN * 60}


def novig_pin_p(L, ev, mk, side):
    h, a = L.get((ev, mk, 'Pinnacle', 'home')), L.get((ev, mk, 'Pinnacle', 'away'))
    if h and a and h.get('american') and a.get('american'):
        ph, pa = implied(h['american']), implied(a['american']); p = ph / (ph + pa)
        return p if side == 'home' else 1 - p
    return None


def mid(L, ev, mk, venue, side):
    r = L.get((ev, mk, venue, side))
    if r and r.get('bid') and r.get('ask') and r['ask'] - r['bid'] <= 0.06: return (r['bid'] + r['ask']) / 2
    return None


def kalshi_result(ticker):
    """True / False once Kalshi has settled the set-1 market, else None."""
    import urllib.request
    try:
        m = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}", headers={'User-Agent': 'sharp-tracker'}), timeout=20)).get('market') or {}
    except Exception: return None
    return {'yes': True, 'no': False}.get(m.get('result')) if m.get('status') in ('settled', 'finalized', 'determined') or m.get('result') in ('yes', 'no') else None


def pin_closes(evs):
    """(event, side) -> Pinnacle's last pregame no-vig set-1 probability (the close, for CLV)."""
    E = json.load(open(os.path.join(TD, 'events.json'))) if os.path.exists(os.path.join(TD, 'events.json')) else {}
    last = {}
    for d in ('ticks', 'ticks5'):
        for f in sorted(glob.glob(os.path.join(TD, d, '*.jsonl.gz')))[-4:]:
            try:
                for l in gzip.open(f, 'rt'):
                    if '"1s_ml"' not in l or '"Pinnacle"' not in l: continue
                    r = json.loads(l)
                    if r['event_id'] not in evs: continue
                    k = (r['event_id'], r['side'])
                    if k not in last or r['ts'] > last[k]['ts']: last[k] = r
            except (EOFError, OSError): pass
    out = {}
    for ev in evs:
        h, a = last.get((ev, 'home')), last.get((ev, 'away'))
        if h and a and h['ts'][:16] == a['ts'][:16]:
            ph, pa = implied(h['american']), implied(a['american']); out[(ev, 'home')] = ph / (ph + pa); out[(ev, 'away')] = pa / (ph + pa)
    return out


def main():
    E = json.load(open(os.path.join(TD, 'events.json'))) if os.path.exists(os.path.join(TD, 'events.json')) else {}
    L = latest(); evs = {k[0] for k in L}
    paper = {}
    if os.path.exists(PAPER):
        for l in open(PAPER): r = json.loads(l); paper[r['event_id']] = r
    rows = []; new = []
    for ev in evs:
        e = E.get(ev)
        if not e or ts(e['start']) <= NOW: continue
        pm = novig_pin_p(L, ev, 'ml', 'home'); src = 'Pinnacle'
        if pm is None:
            pm = mid(L, ev, 'ml', 'Kalshi', 'home') or mid(L, ev, 'ml', 'Novig', 'home'); src = 'exchange mid'
        if pm is None: continue
        fav = 'home' if pm >= 0.5 else 'away'; pf = pm if fav == 'home' else 1 - pm
        name = (e.get('home_team') if fav == 'home' else e.get('away_team') or {}).get('displayName') if e else None
        opp = (e.get('away_team') if fav == 'home' else e.get('home_team') or {}).get('displayName') if e else None
        model = s_from_match(pf); fair_old = min(model + GAP, pf)
        g = ta_group(e); pf_prof = profile(name); po_prof = profile(opp); sv = serve_note(pf_prof, po_prof)
        if g:
            base = ta_interp(MAP['groups'][g], pf) if g.endswith('bo5') else ta_interp(MAP['pooled'], pf) + MAP['offsets'].get(g, 0.0)
            fair = min(base + (sv[0] if sv else 0.0), pf - 0.01); fair_src = f"Tennis Abstract {g}" + (' + serve profile' if sv else '')
        else:
            fair = fair_old; fair_src = 'independent sets + 3.3'
        cands = []
        for v in ('Kalshi', 'Novig'):
            r = L.get((ev, '1s_ml', v, fav))
            if not r or not r.get('ask') or 'oneside' in (r.get('flags') or []): continue
            cost = r['ask'] + (math.ceil(KFEE * r['ask'] * (1 - r['ask']) * 100) / 100 if v == 'Kalshi' else 0)
            cands.append(dict(venue=v, ask=r['ask'], cost=round(cost, 4), ticker=(r.get('extra') or {}).get('ticker')))
        for v in ('DK', 'FD', 'Caesars'):                # US books via Action Network (11/2): American odds, cost = implied probability
            r = L.get((ev, '1s_ml', v, fav))
            if r and r.get('american') is not None: cands.append(dict(venue=v, american=r['american'], cost=round(implied(r['american']), 4)))
        prices = {c['venue']: c['cost'] for c in cands}
        best = min(cands, key=lambda c: c['cost']) if cands else None
        pin1 = novig_pin_p(L, ev, '1s_ml', fav)
        row = dict(event_id=ev, sport='tennis', league=(e.get('tour') or '').lower() or None, start=e['start'], tour=e.get('tour'), tournament=e.get('tournament'), fav=fav, fav_name=name, opp_name=opp,
                   match_p=round(pf, 4), match_src=src, model=round(model, 4), fair=round(fair, 4), fair_old=round(fair_old, 4), fair_src=fair_src, serve=sv[1] if sv else None,
                   profiles=dict(fav=pf_prof and dict(elo=pf_prof['elo'], hold=pf_prof['hold'], last=pf_prof['last']), opp=po_prof and dict(elo=po_prof['elo'], hold=po_prof['hold'], last=po_prof['last'])), pin_set1=round(pin1, 4) if pin1 else None,
                   best=best, prices=prices, edge=round(fair - best['cost'], 4) if best else None)
        row['flag'] = bool(best and pf >= MIN_FAV and row['edge'] >= MIN_EDGE)
        if ev in paper:                           # already paper-logged: stays on the page even if the price has since gone (11/2)
            row['logged'] = dict(ts=paper[ev]['ts'], venue=paper[ev]['venue'], price=paper[ev]['price'], edge=round(paper[ev]['fair'] - paper[ev]['price'], 4))
        rows.append(row)
        # the same match can carry two ids (a Pinnacle-made id before ESPN lists it, then ESPN's): one pick per match (11/4, Tiafoe set 1)
        same = next((k for k, p in paper.items() if k != ev and {p.get('fav_name'), p.get('opp_name')} == {name, opp} and abs((ts(p['start']) - ts(e['start'])).total_seconds()) <= 6 * 3600), None)
        if same and 'logged' not in row:
            row['logged'] = dict(ts=paper[same]['ts'], venue=paper[same]['venue'], price=paper[same]['price'], edge=round(paper[same]['fair'] - paper[same]['price'], 4))
        if row['flag'] and ev not in paper and not same:
            kt = (L.get((ev, '1s_ml', 'Kalshi', fav)) or {}).get('extra') or {}
            rec = dict(**({'backfill': 1} if os.environ.get('TENNIS_NOW') else {}), event_id=ev, ts=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), start=e['start'], fav=fav, fav_name=name, opp_name=opp, match_p=row['match_p'],
                       fair=row['fair'], venue=best['venue'], price=best['cost'], pin_set1=row['pin_set1'], rule='tennis_fs_fav',
                       kalshi_set1=kt.get('ticker'))            # settles Challenger / ITF matches ESPN does not carry
            new.append(rec); paper[ev] = rec
    if new:
        with open(PAPER, 'a') as f:
            for r in new: f.write(json.dumps(r) + '\n')
    # grade paper entries from ESPN (ESPN ids only; x: matches stay ungraded until a Kalshi/Novig settlement path is added)
    res = {}
    rp = os.path.join(TD, 'results.jsonl')
    if os.path.exists(rp):
        for l in open(rp): r = json.loads(l); res[r['match_id']] = r
    graded = []; closes = pin_closes({ev for ev in paper})
    for ev, p in paper.items():
        if ts(p['start']) > NOW: continue
        r = res.get(ev); won = None; src = None
        if r and r.get('first_set_complete') and r.get('first_set_winner'):
            won = (r['first_set_winner'] == 'p1') == (p['fav'] == 'home'); src = 'ESPN'
        elif p.get('kalshi_set1'):
            won = kalshi_result(p['kalshi_set1']); src = 'Kalshi' if won is not None else None
        if won is None: continue
        c = closes.get((ev, p['fav']))
        graded.append(dict(p, won=won, graded_by=src, pnl=round((1 - p['price']) / p['price'] if won else -1.0, 3),
                           pin_close=round(c, 4) if c else None, clv=round(100 * (c - p['price']), 2) if c else None))
    json.dump(graded, open(os.path.join(TD, 'fs_graded.json'), 'w'), separators=(',', ':'))     # every graded paper pick (sharp/bet_log.py reads it)
    rows.sort(key=lambda r: (not r['flag'], r['start']))
    cl = [g['clv'] for g in graded if g.get('clv') is not None]
    rec = dict(n=len(graded), won=sum(g['won'] for g in graded), units=round(sum(g['pnl'] for g in graded), 2),
               clv=round(sum(cl) / len(cl), 2) if cl else None, clv_n=len(cl)) if graded else dict(n=0)
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), gap=GAP, min_fav=MIN_FAV, min_edge=MIN_EDGE, record=rec, recent=sorted(graded, key=lambda g: g['start'])[-25:],
                   rows=rows), open(OUT, 'w'), separators=(',', ':'))
    print(f"[tennis watch] {len(rows)} upcoming matches priced, {sum(r['flag'] for r in rows)} flagged, {len(new)} new paper entries; record {rec}")


if __name__ == '__main__':
    main()
