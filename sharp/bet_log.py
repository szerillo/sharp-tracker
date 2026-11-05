#!/usr/bin/env python3
"""Daily bet log (Sean, 11/2): every bet the tracker flagged, in one ledger, so a bigger sample can say what to target.

One row per flagged bet, from three sources:
  systems   data/state/fills.jsonl (every rule fill; category from the rule's tier: system A / system B / lean C / paper P)
  sharp     data/state/sharp_paper.jsonl (Polymarket sharp-account flags; category sharp A / sharp B / sharp watch)
  tennis    data/tennis/fs_paper.jsonl (set-1 favourite rule; graded in data/tennis/fs_graded.json)
Each row carries: sport, bet type (market: ml, spread, total, 1h_spread, set1 ...), when it flagged and at what price and venue, the
price path across every venue Sean can bet (Novig, Kalshi with its fee, FanDuel, Caesars, DraftKings) from the flag to the start, the
best price in that window and when it was there, the closing board (best price per venue at the start), the result, units at Sean's
sizing (system A/B and sharp A 0.5u, the rest 0.25u; to win on favourites, to risk on plus money) and CLV (closing best price minus the
flagged price, in points; positive = beat the close). Paths come from the logged ticks (data/<sport>/ticks, ticks5); Polymarket is
not on that tape, so a Polymarket flag's path starts from the books.
Writes data/state/bet_log.json (rows + summaries by category x sport x bet type). Usage: python3 sharp/bet_log.py"""
import os, sys, re, json, gzip, glob, math, bisect, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
SD = os.path.join(ROOT, 'data', 'state'); OUT = os.path.join(SD, 'bet_log.json')
SPORTS = ('nfl', 'nba', 'nhl', 'cfb', 'cbb', 'soccer', 'mlb', 'wnba', 'mma', 'tennis')
VENUES = ('Novig', 'Kalshi', 'FD', 'Caesars', 'DK'); REF = ('Pinnacle', 'AN_Consensus')
OTH = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}
UNIT = {'mlb': 'runs', 'nhl': 'goals', 'soccer': 'goals'}            # everything else: points
KEYS = {('nfl', 'spread'): [3, 7, 10, 14, 6, 4, 17], ('cfb', 'spread'): [3, 7, 10, 14, 17, 21], ('nfl', 'total'): [37, 41, 43, 44, 47, 51]}
KFEE = 0.07; STEP = 600; MAX_AGE = 45 * 60
NOW = dt.datetime.now(dt.timezone.utc)


def ts(s): return dt.datetime.fromisoformat(s.replace(' ', 'T').replace('Z', '+00:00').replace('+00:00:00', '+00:00')) if s else None
def implied(a): return 100 / (a + 100) if a > 0 else -a / (-a + 100)
HALF_U = {'nba_1h_under_hot_over'}       # tier C rules sized at 0.5u (Sean, 11/4)
def size_units(cat, rule=None, sport=None): return 0.0 if cat == 'watch' else 0.5 if (cat in ('system A', 'system B') or (cat == 'sharp A' and sport != 'soccer') or rule in HALF_U) else 0.25


def units(p, won, size):
    if won is None or p is None or not 0 < p < 1: return None
    if won == 0.5: return 0.0
    if p > 0.5: return round(size if won else -size * p / (1 - p), 3)
    return round(size * (1 - p) / p if won else -size, 3)


def cost(r):
    if r.get('ask') is not None:
        a = r['ask']; return a + (math.ceil(KFEE * a * (1 - a) * 100) / 100 if r['venue'] == 'Kalshi' else 0)
    if r.get('american') is not None: return implied(r['american'])
    return None


def schedules():
    S = {}
    for sp in SPORTS:
        p = os.path.join(ROOT, 'data', sp, 'schedule.json' if sp != 'tennis' else 'events.json')
        if os.path.exists(p):
            for k, v in json.load(open(p)).items(): S[k] = dict(v, sport=sp)
    return S


class Tape:
    """(event, market, side, line) -> venue -> sorted [(t, cost)] for the events asked for, from the 20-minute and 5-minute tick logs."""
    def __init__(self, sport, events, days):
        self.s = collections.defaultdict(lambda: collections.defaultdict(list))
        self.raw = collections.defaultdict(lambda: collections.defaultdict(list)); self.lines = collections.defaultdict(lambda: collections.defaultdict(list))
        for sub in ('ticks', 'ticks5'):
            for d in days:
                f = os.path.join(ROOT, 'data', sport, sub, f'{d}.jsonl.gz')
                if not os.path.exists(f): continue
                try:
                    for l in gzip.open(f, 'rt'):
                        if '"event_id"' not in l: continue
                        r = json.loads(l)
                        if r.get('event_id') not in events or r.get('venue') not in VENUES + REF: continue
                        line = r.get('line'); line = None if line is None else float(line); t = ts(r['ts']).timestamp()
                        key = (r['event_id'], r['market'], r['side'], line)
                        if r['venue'] in REF or r['venue'] == 'Novig':
                            p = implied(r['american']) if r.get('american') is not None else ((r['bid'] + r['ask']) / 2 if r.get('bid') is not None and r.get('ask') is not None else None)
                            if p is not None and 0 < p < 1:
                                self.raw[key][r['venue']].append((t, p, r.get('limit') or ((r.get('extra') or {}).get('qty_best'))))
                            if r['venue'] in ('AN_Consensus', 'Pinnacle'): self.lines[(r['event_id'], r['market'], r['side'])][r['venue']].append((t, line))
                        if r['venue'] not in VENUES: continue
                        c = cost(r)
                        if c is None or not 0 < c < 1: continue
                        self.s[key][r['venue']].append((t, c))
                except (EOFError, OSError): pass
        for D_ in (self.s, self.raw, self.lines):
            for k in D_:
                for v in D_[k]: D_[k][v].sort(key=lambda x: x[0])

    def last(self, L, t, age=MAX_AGE):
        i = bisect.bisect_right([x[0] for x in L], t) - 1
        return L[i] if i >= 0 and t - L[i][0] <= age else None

    def novig_pin(self, key, t):
        """No-vig Pinnacle probability of this exact side and line at t (multiplicative, both sides quoted); Novig mid as the fallback."""
        ev, m, side, line = key
        okey = (ev, m, OTH.get(side), line if (line is None or 'total' in m) else -line)
        a = self.last(self.raw.get(key, {}).get('Pinnacle', []), t); b = self.last(self.raw.get(okey, {}).get('Pinnacle', []), t)
        if a and b: return a[1] / (a[1] + b[1]), 'Pinnacle'
        n = self.last(self.raw.get(key, {}).get('Novig', []), t)
        return (n[1], 'Novig mid') if n else (None, None)

    def depth(self, key, t):
        out = {}
        for v, nm in (('Pinnacle', 'pinnacle_limit'), ('Novig', 'novig_qty')):
            x = self.last(self.raw.get(key, {}).get(v, []), t)
            if x and x[2]: out[nm] = x[2] if v == 'Pinnacle' else round(x[2] * x[1] / 100)     # Novig quantity is in cents of payout: dollars = qty x price / 100
        return out

    def main_line(self, ev, m, side, t):
        for v in ('AN_Consensus', 'Pinnacle'):
            x = self.last(self.lines.get((ev, m, side), {}).get(v, []), t, 90 * 60)
            if x and x[1] is not None: return x[1], v
        return None, None

    def board(self, key, t):
        out = {}
        for v, L in (self.s.get(key) or {}).items():
            i = bisect.bisect_right(L, (t, 9)) - 1
            if i >= 0 and t - L[i][0] <= MAX_AGE: out[v] = round(L[i][1], 4)
        return out


def path(T, key, t0, st):
    """Best price from the flag to the start: (best cost, when, venue), the closing board and its best, sampled every 10 minutes."""
    best = None; t = t0
    while t < st:
        b = {v: c for v, c in T.board(key, t).items() if v != 'DK'} or T.board(key, t)
        if b:
            v = min(b, key=b.get)
            if best is None or b[v] < best[0] - 1e-9: best = (b[v], t, v)
        t += STEP
    close = T.board(key, st - 60)
    return best, close


def main():
    S = schedules()
    tiers = {k: (v.get('evidence') or {}).get('tier') for k, v in json.load(open(os.path.join(SD, 'system_fires.json')))['rules'].items()}
    bets = []
    # ---- systems
    for l in open(os.path.join(SD, 'fills.jsonl')):
        r = json.loads(l)
        if r.get('result') == 'void' or r.get('mclass', 'game') != 'game': continue
        tag = str(r.get('rule_tag', '')).replace('paper:', ''); tier = tiers.get(tag)
        cat = {'A': 'system A', 'B': 'system B', 'C': 'lean C', 'P': 'paper P'}.get(tier, 'paper P')
        e = S.get(r['event_id']) or {}
        won = {'W': 1, 'L': 0, 'P': 0.5}.get(r.get('result'))
        bets.append(dict(id='s:' + r['fill_id'], src='system', cat=cat, rule=tag, sport=e.get('sport'), event_id=r['event_id'], game=f"{e.get('away', '?')} @ {e.get('home', '?')}",
                         start=r['start_utc'], market=r['market'], side=r['side'], line=r.get('line'), flagged=r['ts_utc'], venue=r['venue'], price=r['implied'], won=won, fair_at_flag=r.get('fair_at_fill')))
    # ---- Polymarket sharp-account flags
    import sharp.sharp_live as SL
    meta = json.load(open(SL.META)) if os.path.exists(SL.META) else {}
    for l in open(os.path.join(SD, 'sharp_paper.jsonl')):
        p = json.loads(l)
        row = dict(title=(meta.get(p['cond']) or {}).get('title') or '', start=p['start'], side=p['side'], mtype=p['mtype'], bet=p['bet'])
        SL.map_rows([row])
        num = re.findall(r'[-+]?\d+(?:\.\d+)?', p['bet']); line = float(num[-1]) if p['mtype'] in ('spread', 'total') and num else None
        g = p.get('grade') or 'B'
        bets.append(dict(id='p:' + p['cond'], src='sharp', cat=f"sharp {g}", rule=p.get('why'), sport=row.get('sport') or ({'ucl': 'soccer', 'epl': 'soccer', 'mls': 'soccer', 'bun': 'soccer'}.get(p['slug'].split('-')[0], p['slug'].split('-')[0]) if p.get('slug') else None),
                         event_id=row.get('event_id'), game=f"{row.get('away', '')} @ {row.get('home', '')}" if row.get('event_id') else p.get('slug'),
                         start=p['start'], market=p['mtype'], side=row.get('side_std'), line=line, flagged=p['logged'], venue='Polymarket', price=p['price'],
                         won={'W': 1, 'L': 0}.get(p.get('result')), bet=p['bet']))
    # ---- tennis set 1
    tp = os.path.join(ROOT, 'data', 'tennis', 'fs_paper.jsonl'); tg = os.path.join(ROOT, 'data', 'tennis', 'fs_graded.json')
    G = {g['event_id']: g for g in (json.load(open(tg)) if os.path.exists(tg) else [])}
    if os.path.exists(tp):
        for l in open(tp):
            p = json.loads(l); g_ = G.get(p['event_id'])
            bets.append(dict(id='t:' + p['event_id'], src='tennis', cat='tennis', rule='tennis_fs_fav', sport='tennis', event_id=p['event_id'], game=f"{p.get('fav_name')} vs {p.get('opp_name')}",
                             start=p['start'], market='1s_ml', side=p['fav'], line=None, flagged=p['ts'], venue=p['venue'], price=p['price'],
                             won=None if not g_ else (1 if g_['won'] else 0), bet=f"{p.get('fav_name')} set 1"))
    # ---- watch-only sharp-money signals (Sean, 11/4: "signals have appeared all week, MMA for instance, why aren't those in the tracker?"):
    # sharp move, big money, Kalshi 4+ move, bet back, one row per game x market x kind, from the frozen snapshots (sharp/signal_log.py,
    # data/research/signal_log.jsonl) plus the live pregame ones (data/state/signal_snap.json). No units (watch), graded W/L at the
    # line in the snapshot, CLV against the no-vig price when the signal was first seen (Kalshi ask for Kalshi moves and bet backs).
    WK = {'move': 'sharp move', 'big': 'big money', 'kmove': 'Kalshi move', 'back': 'bet back'}
    snaps = {}
    lp = os.path.join(ROOT, 'data', 'research', 'signal_log.jsonl')
    if os.path.exists(lp):
        for l in open(lp):
            try: r = json.loads(l); snaps[(r['event_id'], r['market'])] = r
            except Exception: pass
    try:
        for k, r in json.load(open(os.path.join(SD, 'signal_snap.json'))).items(): snaps.setdefault((r['event_id'], r['market']), r)
    except Exception: pass
    for (ev, mk), r in snaps.items():
        e = S.get(ev) or {}
        for kind, sg in (r.get('signals') or {}).items():
            side = sg.get('side'); ln = sg.get('line')
            if not side or kind not in WK: continue
            if mk == 'spread' and ln is not None: ln = ln if side == 'home' else -ln      # snapshots log the home number
            pr = (sg.get('ask') if kind == 'kmove' else sg.get('cost') if kind == 'back' else None)
            pr = pr / 100 if pr else None
            bets.append(dict(id=f"w:{ev}|{mk}|{kind}", src='watch', cat='watch', rule=WK[kind], sport=r.get('sport') or e.get('sport'), event_id=ev,
                             game=f"{e.get('away', '?')} @ {e.get('home', '?')}", start=r['start'].replace('Z', ':00Z') if len(r['start']) == 17 else r['start'], market=mk, side=side, line=ln,
                             flagged=sg.get('first') or r.get('ts'), venue='Kalshi' if kind in ('kmove', 'back') else 'no-vig', price=pr, won=None))
    # ---- price paths
    by = collections.defaultdict(list)
    for b in bets:
        if b['sport'] and b['event_id'] and b['side']: by[b['sport']].append(b)
    for sp, L in by.items():
        days = sorted({(ts(b['start']) + dt.timedelta(days=i)).astimezone(dt.timezone(dt.timedelta(hours=-5))).date().isoformat() for b in L for i in (-2, -1, 0)})
        T = Tape(sp, {b['event_id'] for b in L}, days)
        for b in L:
            st = ts(b['start']).timestamp(); t0 = ts(b['flagged']).timestamp()
            key = (b['event_id'], b['market'], b['side'], None if b['line'] is None else float(b['line']))
            if b['price'] is None:              # watch rows without an entry price: the no-vig price when first seen is the reference
                nv0, src0 = T.novig_pin(key, t0)
                if nv0 is None: continue
                b['price'] = round(nv0, 4); b['venue'] = f"no-vig ({src0})"
            best, close = path(T, key, t0, st)
            if best: b.update(best=round(best[0], 4), best_venue=best[2], best_at=dt.datetime.fromtimestamp(best[1], dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                              best_after_min=round((best[1] - t0) / 60), best_before_start_min=round((st - best[1]) / 60))
            if close:
                b['close_board'] = close; cb = {v: c for v, c in close.items() if v != 'DK'} or close
                b['close'] = min(cb.values()); b['clv'] = round(100 * (b['close'] - b['price']), 2)
            # no-vig close at the same number (Pinnacle, else the Novig mid): CLV that does not carry the vig
            nv, src = T.novig_pin(key, st - 60)
            if nv is not None: b['nv_close'] = round(nv, 4); b['nv_src'] = src; b['clv_nv'] = round(100 * (nv - b['price']), 2)
            # edge at the flag: the fair price then minus the price taken (systems carry their own ruler fair)
            fa, fsrc = (b['fair_at_flag'], 'ruler') if b.get('fair_at_flag') is not None else T.novig_pin(key, t0)
            if fa is not None: b['fair_at_flag'] = round(fa, 4); b['fair_src'] = fsrc; b['edge'] = round(100 * (fa - b['price']), 2)
            d_ = T.depth(key, t0)
            if d_: b['depth'] = d_
            # line movement in points / runs / goals, against the main line at the close (consensus, else Pinnacle)
            base = re.sub(r'^(1h|1q|1p)_', '', b['market'])
            if base in ('spread', 'total') and b['line'] is not None and not (base == 'spread' and b['sport'] in ('nhl', 'mlb')):   # puck / run lines sit at 1.5: the price moves, not the number
                cl, csrc = T.main_line(b['event_id'], b['market'], b['side'], st - 60); ol, _ = T.main_line(b['event_id'], b['market'], b['side'], t0)
                if cl is not None:
                    fl = float(b['line'])
                    b['close_line'] = cl; b['open_line'] = ol
                    # positive = the number taken beat the closing number: under / spread side want a higher number than the close, over a lower one
                    # an alternate number (more than a point off the main line when it flagged) is compared main-to-main: how the market moved
                    ref = fl if ol is None or abs(fl - ol) <= 1 else ol
                    if ref != fl: b['alt_line'] = True
                    b['line_value'] = round(cl - ref, 1) if (base == 'total' and b['side'] == 'over') else round(ref - cl, 1)
                    ks = KEYS.get((b['sport'], base)) or []
                    lo, hi = sorted([abs(ref), abs(cl)]) if base == 'spread' else sorted([ref, cl])
                    b['keys_crossed'] = [k for k in ks if lo <= k <= hi and lo != hi]     # moving onto or off a key number counts (-3 to -3.5 crosses 3)
    # margin against the number, from final scores (data/state/results.jsonl; 1H from the half-time fields)
    RES = {}
    rp = os.path.join(SD, 'results.jsonl')
    if os.path.exists(rp):
        for l in open(rp):
            try: r = json.loads(l)
            except Exception: continue
            if r.get('status') == 'final' and r.get('home_score') is not None: RES[r['event_id']] = r
    for b in bets:
        r = RES.get(b['event_id']); m = b['market']
        if not r or b['sport'] == 'tennis' or not b['side']: continue
        h_, a_ = (r.get('f5_home'), r.get('f5_away')) if m.startswith('1h_') else (r['home_score'], r['away_score'])
        if h_ is None: continue
        base = re.sub(r'^(1h|1q|1p)_', '', m); L = float(b['line'] or 0)
        if base == 'total': b['margin'] = round((L - (h_ + a_)) if b['side'] == 'under' else ((h_ + a_) - L), 1)
        elif base == 'spread': b['margin'] = round(((h_ - a_) if b['side'] == 'home' else (a_ - h_)) + L, 1)
        elif base == 'ml': b['margin'] = (h_ - a_) if b['side'] == 'home' else (a_ - h_)
        b['unit_name'] = UNIT.get(b['sport'], 'points')
        if b['src'] == 'watch' and b['won'] is None and b.get('margin') is not None and (base != 'total' and base != 'spread' or b['line'] is not None):
            b['won'] = 1 if b['margin'] > 0 else 0 if b['margin'] < 0 else 0.5
    # correlation (Sean, 11/2): bets on one game in one family (the team side: moneyline / spread, any period; or the total, any period)
    fam = lambda m: 'total' if 'total' in m else ('side' if re.sub(r'^(1h|1q|1p)_', '', m) in ('ml', 'spread') else None)
    grp = collections.defaultdict(list)
    for b in bets:
        if b['event_id'] and b['side'] and fam(b['market']) and b['cat'] != 'paper P': grp[(b['event_id'], fam(b['market']))].append(b)
    for (ev, fm), L in grp.items():
        for b in L:
            same = [x['id'] for x in L if x is not b and x['side'] == b['side']]; opp = [x['id'] for x in L if x['side'] != b['side']]
            b['position'] = f"{ev}|{fm}|{b['side']}"
            if same: b['corr_same'] = same
            if opp: b['corr_opp'] = opp
    # the same bet (game, market, side, number) flagged by more than one rule or source: each stays (different reasons), noted on each
    sameb = collections.defaultdict(list)
    for b in bets:
        if b['event_id'] and b['side'] and b['src'] != 'tennis': sameb[(b['event_id'], b['market'], b['side'], None if b['line'] is None else float(b['line']))].append(b)
    for L in sameb.values():
        if len(L) > 1:
            for b in L: b['also'] = [f"{x['cat']}" + (f" ({x['rule']})" if x['src'] == 'system' else '') for x in L if x is not b]
    # what else was on the board when the bet flagged: snapped the first time this log sees a bet within an hour of its flag
    try: SA = json.load(open(os.path.join(SD, 'sharp_accounts.json')))
    except Exception: SA = {}
    try: FLv = json.load(open(os.path.join(SD, 'flow_live.json')))
    except Exception: FLv = {}
    def ctx(b):
        base = re.sub(r'^(1h|1q|1p)_', '', b['market']); ms = ['total'] if base == 'total' else ['ml', 'spread']; out = {}
        for m in ms:
            x = (SA.get('by_event') or {}).get(f"{b['event_id']}|{m}") or {}
            if x.get(b['side']): out['sharps_with'] = max(out.get('sharps_with', 0), x[b['side']]['n'])
            if x.get(OTH.get(b['side'])): out['sharps_against'] = max(out.get('sharps_against', 0), x[OTH[b['side']]]['n'])
            for r in FLv.get('rows') or []:
                if r.get('event_id') == b['event_id'] and r.get('market') == m and r.get('divergent'): out['big_money'] = 'with' if r.get('big_side') == b['side'] else 'against'
            for r in FLv.get('moves') or []:
                if r.get('event_id') == b['event_id'] and r.get('market') == m: out['kalshi_move'] = 'with' if r.get('side') == b['side'] else 'against'
        return out
    # raw ticks roll off after 10 days (sharp/rolloff.py): keep a bet's path from the last build when the tape is gone
    old = {b.get('id'): b for b in (json.load(open(OUT)).get('rows') or [])} if os.path.exists(OUT) else {}
    for b in bets:
        o = old.get(b['id']) or {}
        for k in ('alt_line', 'best', 'best_venue', 'best_at', 'best_after_min', 'best_before_start_min', 'close_board', 'close', 'clv', 'nv_close', 'nv_src', 'clv_nv',
                  'fair_at_flag', 'fair_src', 'edge', 'depth', 'close_line', 'open_line', 'line_value', 'keys_crossed', 'ctx'):
            if b.get(k) is None and o.get(k) is not None: b[k] = o[k]
        if b.get('ctx') is None and b['event_id'] and b['side'] and 0 <= (NOW - ts(b['flagged'])).total_seconds() <= 3600: b['ctx'] = ctx(b)
    # ---- sharps against (Sean, 11/4: "note on the tracker when an NBA under got opposed by sharp money and would have been taken off the
    # board, so how they perform is easy to see; backfill tonight's"). Recomputed from the whole Polymarket sharp-fill log every run, so it
    # covers every bet back to 10/10. Top-200 accounts only (specialists excluded), the same full-game market family, opposite side, before
    # the start: 'at_flag' when the first one came before the bet flagged (today's board would hold it), 'after' when after (it gets greyed
    # late; the bet already stood). The bet stays in every record; this only labels it.
    opp_stats = sharps_against(bets, S)
    for b in bets:
        b['bet_type'] = b['market'].replace('1s_ml', 'set1_ml')
        b['size'] = size_units(b['cat'], b.get('rule'), b.get('sport')); b['units'] = units(b['price'], b['won'], b['size'])
        b['lead_h'] = round((ts(b['start']) - ts(b['flagged'])).total_seconds() / 3600, 1)
    # ---- summaries
    def summ(L):
        G_ = [b for b in L if b['won'] is not None]; cl = [b['clv'] for b in L if b.get('clv') is not None]
        gain = [100 * (b['price'] - b['best']) for b in L if b.get('best') is not None]
        later = [b for b in L if b.get('best') is not None and 100 * (b['price'] - b['best']) >= 1]
        nvc = [b['clv_nv'] for b in L if b.get('clv_nv') is not None]; lv = [b['line_value'] for b in L if b.get('line_value') is not None]; ed = [b['edge'] for b in L if b.get('edge') is not None]
        return dict(positions=len({b.get('position') or b['id'] for b in L}), clv_nv=round(sum(nvc) / len(nvc), 2) if nvc else None, clv_nv_n=len(nvc),
                    line_value=round(sum(lv) / len(lv), 2) if lv else None, edge=round(sum(ed) / len(ed), 2) if ed else None, n=len(L), graded=len(G_), w=sum(1 for b in G_ if b['won'] == 1), l=sum(1 for b in G_ if b['won'] == 0), p=sum(1 for b in G_ if b['won'] == 0.5),
                    units=round(sum(b['units'] or 0 for b in G_), 2), clv=round(sum(cl) / len(cl), 2) if cl else None, clv_n=len(cl),
                    best_gain=round(sum(gain) / len(gain), 2) if gain else None, better_later=len(later), lead_h=round(sum(b['lead_h'] for b in L) / len(L), 1) if L else None)
    groups = collections.defaultdict(list)
    for b in bets:
        if b['cat'] == 'watch':
            for k in (('watch', 'all', 'all'), ('watch', b['sport'] or '?', 'all'), ('watch', b['sport'] or '?', b['bet_type'])): groups['|'.join(k)].append(b)
            continue
        for k in ((b['cat'], 'all', 'all'), (b['cat'], b['sport'] or '?', 'all'), (b['cat'], b['sport'] or '?', b['bet_type']), ('all', b['sport'] or '?', b['bet_type']), ('all', b['sport'] or '?', 'all'), ('all', 'all', 'all')):
            groups['|'.join(k)].append(b)
    opp_summ = {k: summ([b for b in bets if (b.get('opp') or {}).get('when') == k and b['src'] != 'paper']) for k in ('at_flag', 'after')}
    opp_summ['none'] = summ([b for b in bets if b['event_id'] and b['side'] and not b.get('opp') and b['src'] in ('system', 'sharp')])
    out = dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), venues=list(VENUES), opposed=opp_summ,
               summary={k: summ(v) for k, v in sorted(groups.items())},
               rows=sorted(bets, key=lambda b: b['start'], reverse=True))
    json.dump(out, open(OUT, 'w'), separators=(',', ':'), default=str)
    s = out['summary'].get('all|all|all', {})
    print(f"[bet_log] {len(bets)} flagged bets ({s.get('graded')} graded, {s.get('units')}u, CLV {s.get('clv')} on {s.get('clv_n')}); {sum(1 for b in bets if b.get('best') is not None)} with a price path")


def sharps_against(bets, S):
    """Label each bet with the Polymarket top-200 accounts on the other side of its game (see main). -> number labelled."""
    p = os.path.join(ROOT, 'data', 'polymarket', 'sharp_fills.jsonl')
    if not os.path.exists(p): return 0
    raw = {}
    for sp in SPORTS:
        q = os.path.join(ROOT, 'data', sp, 'schedule.json')
        if sp != 'tennis' and os.path.exists(q):
            try: raw.update(json.load(open(q)))
            except Exception: pass
    nick = lambda t: (((t or {}).get('shortDisplayName') or (t or {}).get('name') or (t or {}).get('displayName') or '').lower().split() or [''])[-1]
    byday = collections.defaultdict(list)
    for l in open(p):
        try: x = json.loads(l)
        except Exception: continue
        if x.get('rank') is None or x.get('specialist'): continue
        byday[(x.get('start') or '')[:10]].append(x)
    n = 0
    for b in bets:
        if b['src'] == 'tennis' or not b.get('event_id') or not b.get('side'): continue
        e = raw.get(b['event_id'])
        if not e: continue
        a_, h_ = nick(e.get('away_team')), nick(e.get('home_team'))
        if not a_ or not h_: continue
        base = re.sub(r'^(1h|1q|1p)_', '', b['market']); fam = ('total',) if base == 'total' else ('ml', 'spread')
        t_flag = ts(b['flagged']).timestamp(); t_start = ts(b['start']).timestamp()
        W = {}
        for x in byday.get(b['start'][:10], []):
            t = (x.get('title') or '').lower()
            if a_ not in t or h_ not in t or x.get('mtype') not in fam or x['ts'] >= t_start: continue
            bt = (x.get('bet') or '').lower()
            xs = (bt.split()[0] if bt else None) if base == 'total' else ('away' if a_ in bt else 'home' if h_ in bt else None)
            if xs is None or xs == b['side']: continue
            w = W.setdefault(x['w'], dict(first=x['ts'], usd=0.0, rank=x['rank'])); w['first'] = min(w['first'], x['ts']); w['usd'] += x.get('usd') or 0
        if not W: continue
        first = min(w['first'] for w in W.values())
        b['opp'] = dict(n=len(W), usd=round(sum(w['usd'] for w in W.values())), best_rank=min(w['rank'] for w in W.values()),
                        first=dt.datetime.fromtimestamp(first, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), when='at_flag' if first <= t_flag else 'after',
                        min_before_start=round((t_start - first) / 60))
        n += 1
    return n


if __name__ == '__main__':
    main()
