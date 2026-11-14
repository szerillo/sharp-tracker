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
from sharp.teammatch import hit as team_hit, side as team_side   # 11/7: whole-name team matching (the 'St' bug)
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
# 11/10 (Sean, docs/review_2026-11-10.md): sharp flags carry no units from here until they beat Pinnacle's close (Sharp A +0.06 on 97, 45-69).
# Flags logged before this keep the size they were tracked at.
SHARP_PAPER_FROM = '2026-11-10T10:00:00Z'
# 11/14: a rule promoted from paper counts as a bet only for fills logged from its promotion on; its earlier paper fills stay paper, so
# no units are backdated into the record.
PROMOTED_FROM = {'xch_homedog_fade': '2026-11-14T08:30:00Z'}     # Sean 11/14: paper -> tier C
def size_units(cat, rule=None, sport=None, flagged=None):
    if cat == 'watch' or (cat.startswith('sharp') and (flagged or '') >= SHARP_PAPER_FROM): return 0.0
    return 0.5 if (cat in ('system A', 'system B') or (cat == 'sharp A' and sport != 'soccer') or rule in HALF_U) else 0.25


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
        i = bisect.bisect_right(L, t, key=lambda x: x[0]) - 1     # 11/7: was building the whole time list on every lookup (the job's slow step)
        return L[i] if i >= 0 and t - L[i][0] <= age else None

    def novig_pin(self, key, t):
        """No-vig Pinnacle probability of this exact side and line at t (multiplicative, both sides quoted); Novig mid as the fallback."""
        ev, m, side, line = key
        if m == 'ml':
            # 11/9: soccer moneyline is three-way. Devigging home against away alone treated the draw as a push and overstated every
            # soccer ML fair by 10-20 points. When Pinnacle has a draw quote, normalise all three; 'not_home' / 'not_away' = 1 - that side.
            D = {s_: self.last(self.raw.get((ev, m, s_, line), {}).get('Pinnacle', []), t) for s_ in ('home', 'away', 'draw')}
            if D['draw'] or side in ('draw', 'not_home', 'not_away'):
                if not all(D.values()):
                    n = self.last(self.raw.get(key, {}).get('Novig', []), t)   # Novig's soccer ML is one Yes/No market per outcome: its mid is already three-way
                    return (n[1], 'Novig mid') if n else (None, None)
                tot = sum(x[1] for x in D.values()); P = {s_: x[1] / tot for s_, x in D.items()}
                P['not_home'] = 1 - P['home']; P['not_away'] = 1 - P['away']
                return (P[side], 'Pinnacle') if side in P else (None, None)
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
        if tag in PROMOTED_FROM and (r.get('ts_utc') or '') < PROMOTED_FROM[tag]: cat = 'paper P'
        e = S.get(r['event_id']) or {}
        won = {'W': 1, 'L': 0, 'P': 0.5}.get(r.get('result'))
        bets.append(dict(id='s:' + r['fill_id'], src='system', cat=cat, rule=tag, sport=e.get('sport'), event_id=r['event_id'], game=f"{e.get('away', '?')} @ {e.get('home', '?')}",
                         start=r['start_utc'], market=r['market'], side=r['side'], line=r.get('line'), flagged=r['ts_utc'], venue=r['venue'], price=r['implied'], won=won, fair_at_flag=r.get('fair_at_fill')))
    # ---- Polymarket sharp-account flags
    import sharp.sharp_live as SL
    meta = json.load(open(SL.META)) if os.path.exists(SL.META) else {}
    seen_ladder = set()    # 11/9: one bet per game, market and side; extra lines of a laddered flag (each its own Polymarket market) are skipped
    for p in sorted((json.loads(l) for l in open(os.path.join(SD, 'sharp_paper.jsonl'))), key=lambda p: p.get('logged') or ''):
        lk = (p.get('slug'), p.get('mtype'), p.get('side'))
        if lk in seen_ladder: continue
        seen_ladder.add(lk)
        row = dict(title=(meta.get(p['cond']) or {}).get('title') or '', start=p['start'], side=p['side'], mtype=p['mtype'], bet=p['bet'])
        SL.map_rows([row])
        num = re.findall(r'[-+]?\d+(?:\.\d+)?', p['bet']); line = float(num[-1]) if p['mtype'] in ('spread', 'total') and num else None
        g = p.get('grade') or 'B'
        bets.append(dict(id='p:' + p['cond'], src='sharp', cat=f"sharp {g}", rule=p.get('why'), sport=row.get('sport') or ({'ucl': 'soccer', 'epl': 'soccer', 'mls': 'soccer', 'bun': 'soccer'}.get(p['slug'].split('-')[0], p['slug'].split('-')[0]) if p.get('slug') else None),
                         event_id=row.get('event_id'), game=f"{row.get('away', '')} @ {row.get('home', '')}" if row.get('event_id') else p.get('slug'),
                         start=p['start'], market=p['mtype'], side=row.get('side_std'), line=line, flagged=p['logged'], venue='Polymarket', price=p['price'],
                         won={'W': 1, 'L': 0}.get(p.get('result')), bet=p['bet']))
    # ---- Grade C sharp rows (11/8, Sean): sharp accounts plus money or a price move, no flag. Logged off the published page by the board
    # check (sharp/sharp_c_log.py) at the price shown when first seen; graded here from final scores (below, with the watch signals).
    cp = os.path.join(SD, 'sharp_c_paper.jsonl')
    if os.path.exists(cp):
        for l in open(cp):
            try: c = json.loads(l)
            except Exception: continue
            if not c.get('price'): continue
            e = S.get(c['event_id']) or S.get(str(c['event_id'])) or {}
            bets.append(dict(id='c:' + c['key'], src='sharp', cat='sharp C', rule='sharps + market move, no flag', sport=e.get('sport'), event_id=c['event_id'],
                             game=f"{e.get('away', '?')} @ {e.get('home', '?')}", start=c['start'], market=c['market'], side=c['side'], line=c.get('line'),
                             flagged=c['logged'], venue=(c.get('price_text') or '').split(' ')[-1][:20] or None, price=c['price'], won=None, bet=c.get('bet')))
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
    # ---- tennis hot favourite (tour level = lean C, 0.25u; Challenger = paper) and hot dog (paper), from tennis_watch's paper logs
    TOUR = ('atp_tour', 'wta_tour', 'atp_tour_bo5', 'wta_tour_bo5')
    for fn, gn, rule in (('hot_paper.jsonl', 'hot_graded.json', 'tennis_hot_fav'), ('hotdog_paper.jsonl', 'hotdog_graded.json', 'tennis_hot_dog')):
        tp = os.path.join(ROOT, 'data', 'tennis', fn); tg = os.path.join(ROOT, 'data', 'tennis', gn)
        if not os.path.exists(tp): continue
        G2 = {g['event_id']: g for g in (json.load(open(tg)) if os.path.exists(tg) else [])}
        for l in open(tp):
            p = json.loads(l); g_ = G2.get(p['event_id'])
            live = rule == 'tennis_hot_fav' and p.get('level') in TOUR and bool((p.get('settled') or {}).get('ok'))   # 11/5: settled favourites only
            side = p.get('side') or p['fav']; pick = p.get('pick_name') or p.get('fav_name')
            bets.append(dict(id=f"{'th' if rule == 'tennis_hot_fav' else 'td'}:{p['event_id']}", src='tennis', cat='system B' if live else 'paper P', rule=rule, sport='tennis', event_id=p['event_id'],   # 11/5 (Sean): settled favourites are tier B, 0.5u
                             game=f"{p.get('fav_name')} vs {p.get('opp_name')}", start=p['start'], market='ml', side=side, line=None, flagged=p['ts'], venue=p['venue'], price=p['price'],
                             won=None if not g_ else (1 if g_['won'] else 0), bet=f"{pick} to win"))
    # ---- MMA steam favourite (11/5, tier C 0.25u): sharp/mma_steam.py paper log, graded from ESPN
    mp = os.path.join(ROOT, 'data', 'mma', 'steam_paper.jsonl'); mg = os.path.join(ROOT, 'data', 'mma', 'steam_graded.json')
    if os.path.exists(mp):
        G3 = {g['key']: g for g in (json.load(open(mg)) if os.path.exists(mg) else [])}
        seen_ms = set()    # 11/7: the same fight was logged under two key formats (an older hash and the ESPN id): one bet per fight and pick
        for l in open(mp):
            p = json.loads(l); g_ = G3.get(p['key'])
            fk = (p['start'][:10], p['fav_name'], p['dog_name'], p.get('espn_side') or 'home')
            if fk in seen_ms: continue
            seen_ms.add(fk)
            bets.append(dict(id=f"ms:{p['key']}", src='mma', cat='lean C', rule='mma_steam_fav', sport='mma', event_id=p.get('espn') or p['key'], game=f"{p['fav_name']} vs {p['dog_name']}", start=p['start'],
                             market='ml', side=p.get('espn_side') or 'home', line=None, flagged=p['ts'], venue=p['venue'], price=p['price'], won=None if not g_ else (1 if g_['won'] else 0), bet=f"{p['fav_name']} to win"))
    # ---- Kalshi NHL late-flow paper lean (sharp/kalshi_flow.py), tier P
    kp = os.path.join(ROOT, 'data', 'kalshi', 'flow_paper.jsonl')
    if os.path.exists(kp):
        for l in open(kp):
            p = json.loads(l)
            bets.append(dict(id=f"kf:{p['event_id']}:{p['market']}:{p.get('line')}", src='paper', cat='paper P', rule='kalshi_nhl_flow', sport='nhl', event_id=str(p['event_id']), game=p.get('game') or '',
                             start=p['start'].replace('Z', ':00Z') if len(p['start']) == 17 else p['start'], market=p['market'], side=p['side'], line=p.get('line'), flagged=p['logged'], venue='Kalshi', price=p['price'],
                             won=p.get('won') if p.get('won') in (0, 1) else None, bet=p.get('bet') or f"{p['side']} {p.get('line') or ''}".strip()))
    # ---- 11/6 leans with their own logs: derivatives off the curve, prop price gaps, stale books (graded in their own logs)
    W_ = lambda w: w if w in (0, 0.5, 1) else None
    cp = os.path.join(SD, 'curve_paper.jsonl')
    if os.path.exists(cp):
        for l in open(cp):
            p = json.loads(l); mk = {'totals_h1': '1h_total', 'totals_q1': '1q_total', 'totals_p3': '3p_total', 'spreads_p1': '1p_spread'}.get(p['market']) or ('tt_' + (p.get('team') or 'home'))
            bets.append(dict(id=f"cv:{p['key']}", src='curve', cat={'A': 'system A', 'B': 'system B', 'C': 'lean C'}.get(p.get('tier'), 'paper P'), rule=p['rule'], sport=p['sport'], event_id=p.get('espn') or p['key'],
                             game=p['game'], start=p['start'], market=mk, side=p['side'], line=p['line'], flagged=p['flagged'], venue=p.get('book') or 'Pinnacle',
                             price=round(1 / (p.get('price') or p['pin_price']), 4), won=W_(p.get('won')),
                             bet=f"{p['side'].title()} {p['line']} {({'1h_total': '1H total', '1q_total': '1Q total'}.get(mk) or ((p.get('team_name') or '') + ' team total'))}"))
    pp_ = os.path.join(SD, 'props_paper.jsonl')
    if os.path.exists(pp_):
        for l in open(pp_):
            p = json.loads(l); live = (p['sport'] == 'nba' and p['market'] == 'player_threes') or (p['sport'] == 'nhl' and p.get('flagged', '') >= '2026-11-06T23:00')   # 11/6 (Sean): NHL saves / shots unders to tier C
            bets.append(dict(id=f"pr:{p['key']}", src='props', cat='lean C' if live else 'paper P', rule=f"{p['sport']}_prop_under_gap" if p['sport'] != 'nba' else ('nba_threes_under_gap' if live else 'nba_prop_under_gap'), sport=p['sport'],
                             event_id=p.get('espn') or p['key'], game=p['game'], start=p['start'], market='prop_' + p['market'].replace('player_', ''), side='under', line=p['line'],
                             flagged=p['flagged'], venue=p['book'], price=round(1 / p['price'], 4), won=W_(p.get('won')), bet=f"{p['player']} under {p['line']} {p['market'].replace('player_', '').replace('_', ' ')}"))
    sp_ = os.path.join(SD, 'stale_paper.jsonl')
    if os.path.exists(sp_):
        for l in open(sp_):
            p = json.loads(l)
            bets.append(dict(id=f"sb:{p['key']}", src='paper', cat='paper P', rule='stale_book_sb4' if p.get('kind') == 'sb4' else 'stale_book', sport=p['sport'], event_id=p['event_id'], game=p['game'],
                             start=p['start'].replace('Z', ':00Z') if len(p['start']) == 17 else p['start'], market=p['market'], side=p['side'], line=p.get('line'), flagged=p['flagged'],
                             venue=p['venue'], price=p['price'], won=W_(p.get('won'))))
    # ---- 11/10 women's college basketball paper rules (loggers/wncaab_live.py; graded in their own log from ESPN finals)
    wp_ = os.path.join(SD, 'wncaab_paper.jsonl')
    if os.path.exists(wp_):
        for l in open(wp_):
            try: p = json.loads(l)
            except Exception: continue
            bets.append(dict(id=f"wc:{p['key']}", src='paper', cat='paper P', rule=p['rule'], sport='wncaab', event_id=p.get('espn') or p['event_id'], game=p['game'],
                             start=p['start'], market='spread', side=p['side'], line=p['line'], flagged=p['flagged'], venue=p['book'], price=p['price'],
                             won=W_(p.get('won')), bet=p.get('bet')))
    # ---- price paths
    # 11/7 (Sean: "have it update quicker"): the tape is the slow part (43.7M tick lines a run, 95% of this step). A game 12+ hours past its
    # start has a final close, CLV and line movement, so those fields are kept in data/state/bet_paths.json and its tape is not read again.
    PATHS_F = os.path.join(SD, 'bet_paths.json')
    try: PATHS = json.load(open(PATHS_F))
    except Exception: PATHS = {}
    FROZEN_BEFORE = (NOW_ if 'NOW_' in globals() else dt.datetime.now(dt.timezone.utc)).timestamp() - 12 * 3600
    by = collections.defaultdict(list); snap0 = {}
    for b in bets:
        if not (b.get('sport') and b.get('event_id') and b.get('side')): continue
        try: done_ = ts(b['start']).timestamp() < FROZEN_BEFORE
        except Exception: done_ = False
        pk = f"{b['id']}|{b.get('flagged')}"
        s3 = b.get('sport') == 'soccer' and b.get('market') == 'ml'   # 11/9: entries frozen before the three-way soccer fix are recomputed once
        if done_ and pk in PATHS and (not s3 or PATHS[pk].get('fair3')): b.update(PATHS[pk]); continue
        snap0[id(b)] = (pk, done_, dict(b)); by[b['sport']].append(b)
        if s3: b['fair3'] = 1                                      # after the snapshot, so the cache entry records it
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
            # market move from our first tape point to the flag, toward (+) or away from (-) the side taken. 11/5 Polymarket re-score at
            # Pinnacle's close (data/research/poly_pinnacle.json): top-200 fills WITH Pinnacle's move +5.5% out of sample, AGAINST it -8.4%.
            base = re.sub(r'^(1h|1q|1p)_', '', b['market'])    # 11/8: was set only further down, so this used the previous bet's market
            try:
                mv = None
                if base in ('spread', 'total') and b['line'] is not None and not (base == 'spread' and b['sport'] in ('nhl', 'mlb')):
                    LL = [x for v in T.lines.get((b['event_id'], b['market'], b['side']), {}).values() for x in v if x[1] is not None]
                    if LL:
                        t_first = min(x[0] for x in LL); ol0, _ = T.main_line(b['event_id'], b['market'], b['side'], t_first + 1); lf, _ = T.main_line(b['event_id'], b['market'], b['side'], t0)
                        if ol0 is not None and lf is not None: mv = round((lf - ol0) if (base == 'total' and b['side'] == 'over') else (ol0 - lf), 1)
                else:
                    PP_ = T.raw.get(key, {}).get('Pinnacle', [])
                    if PP_:
                        nv0_, _ = T.novig_pin(key, PP_[0][0] + 1); nvf_, _ = T.novig_pin(key, t0)
                        if nv0_ is not None and nvf_ is not None: mv = round(100 * (nvf_ - nv0_), 1)
                if mv is not None: b['move_at_flag'] = dict(pts=mv, dir='with' if mv > 0 else 'against' if mv < 0 else 'flat', unit='pts' if base == 'ml' or base.endswith('ml') else UNIT.get(b['sport'], 'points'))
            except Exception: pass
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
    for L in by.values():
        for b in L:
            pk, done_, b0 = snap0[id(b)]
            if done_: PATHS[pk] = {k: v for k, v in b.items() if k not in b0 or b0[k] != v}
    try: json.dump(PATHS, open(PATHS_F, 'w'), separators=(',', ':'))
    except Exception as e: print(f'[bet_log] path cache not saved: {e}')
    print(f"[bet_log] price paths: {sum(len(L) for L in by.values())} bets read from the tape, {len(PATHS)} frozen in the cache")
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
        if not r or b['sport'] == 'tennis' or not b['side'] or m.startswith(('1q_', 'tt_', 'prop_')): continue      # no quarter / team / player scores in results.jsonl
        h_, a_ = (r.get('f5_home'), r.get('f5_away')) if m.startswith('1h_') else (r['home_score'], r['away_score'])
        if h_ is None: continue
        base = re.sub(r'^(1h|1q|1p)_', '', m); L = float(b['line'] or 0)
        if base == 'total': b['margin'] = round((L - (h_ + a_)) if b['side'] == 'under' else ((h_ + a_) - L), 1)
        elif base == 'spread': b['margin'] = round(((h_ - a_) if b['side'] == 'home' else (a_ - h_)) + L, 1)
        elif base == 'ml': b['margin'] = (h_ - a_) if b['side'] == 'home' else (a_ - h_)
        b['unit_name'] = UNIT.get(b['sport'], 'points')
        if (b['src'] == 'watch' or b['cat'] == 'sharp C') and b['won'] is None and b.get('margin') is not None and (base != 'total' and base != 'spread' or b['line'] is not None):
            b['won'] = 1 if b['margin'] > 0 else 0 if b['margin'] < 0 else 0.5
    # correlation (Sean, 11/2): bets on one game in one family (the team side: moneyline / spread, any period; or the total, any period)
    fam = lambda m: 'total' if ('total' in m or re.sub(r'^(1h|1q|1p)_', '', m).startswith('tt_')) else ('side' if re.sub(r'^(1h|1q|1p)_', '', m) in ('ml', 'spread') else None)
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
    # 11/5 (Sean): cross-reference by game x market family x side (any period or number), systems and sharp signals both ways; watch rows excluded
    sameb = collections.defaultdict(list)
    for b in bets:
        if b.get('event_id') and b.get('side') and b['src'] != 'tennis' and b.get('cat') != 'watch': sameb[(b['event_id'], re.sub(r'^(1h|1q|1p)_', '', b['market'] or ''), b['side'])].append(b)
    for L in sameb.values():
        if len(L) > 1:
            for b in L: b['also'] = [dict(src=x['src'], cat=x['cat'], rule=(x.get('rule') or '').split(' | ')[0][:60], flagged=x.get('flagged')) for x in L if x is not b]
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
        # 11/9: soccer ML fairs before the three-way fix were 10-20 pts too high; never carry those forward (a rolled-off one becomes blank)
        s3 = b.get('sport') == 'soccer' and b.get('market') == 'ml'
        if s3:
            if not o.get('fair3'): o = {k: v for k, v in o.items() if k not in ('nv_close', 'nv_src', 'clv_nv', 'fair_at_flag', 'fair_src', 'edge')}
            b['fair3'] = 1
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
        b['size'] = size_units(b['cat'], b.get('rule'), b.get('sport'), b.get('flagged')); b['units'] = units(b['price'], b['won'], b['size'])
        # 11/10 (Sean: "yes, do all that"; docs/review_2026-11-10.md): the price to rest instead of taking, 1c under the fair price at the flag
        # (Novig or Kalshi), and whether the best price on a bettable venue later got there. Pre-registered: filled against never filled,
        # read at 150 filled.
        f_ = b.get('fair_at_flag')
        if f_ is not None and 0.03 < f_ < 0.97:
            b['rest'] = round(f_ - 0.01, 3)
            if b.get('best') is not None: b['rest_filled'] = bool(b['best'] <= b['rest'] + 1e-9)
        b['lead_h'] = round((ts(b['start']) - ts(b['flagged'])).total_seconds() / 3600, 1)
    # ---- summaries
    def summ(L):
        G_ = [b for b in L if b['won'] is not None]; cl = [b['clv'] for b in L if b.get('clv') is not None]
        gain = [100 * (b['price'] - b['best']) for b in L if b.get('best') is not None and b.get('price') is not None]
        later = [b for b in L if b.get('best') is not None and b.get('price') is not None and 100 * (b['price'] - b['best']) >= 1]
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
    # 11/5 (Sean): never count both sides of one game. Among counted bets (systems, leans, sharp A/B, tennis), a later bet on the other
    # team (moneyline or spread) or the other side of the total is kept on the list but not counted (counted=False, conflict_with=id)
    COUNTED = ('system A', 'system B', 'lean C', 'sharp A', 'sharp B', 'sharp C', 'tennis')
    # 11/5 (Sean): only the other side of the SAME market cancels: the later bet stays listed, not counted, no units, with a note. A spread on
    # one team and a moneyline on the other always both count; they are labelled as a middle (both can win) or a reverse middle (both can lose).
    per_ = lambda b: '1h' if b['market'].startswith(('1h_', '1p_', '1s_')) else 'fg'
    # 11/14 (Sean): sharp flags are a signal under test, so each one counts on its own: a sharp flag is never cancelled, and is only
    # compared with other sharp flags (both sides flagged = labelled, both count). Bets (systems, leans, tennis) keep one side per market.
    fam_ = lambda b: 'sharp' if b['cat'].startswith('sharp') else 'bets'
    # 11/14: soccer moneyline is three-way, so "X to win: No" leans to the other team. Same lean = same direction (not a conflict or middle).
    lean_ = lambda b: {'home': 1, 'not_away': 1, 'away': -1, 'not_home': -1}.get(b['side'], 0)
    tsec = lambda b: ts(b['flagged']).timestamp() if b.get('flagged') else None
    grp_ = collections.defaultdict(list)
    for b in bets:
        if b['cat'] in COUNTED and b.get('event_id'): grp_[(str(b['event_id']), per_(b), fam_(b))].append(b)
    desc_ = lambda x: f"{x['cat']} {x.get('bet') or x['side']}"
    def gap_(k, b):
        g = (tsec(b) - tsec(k)) / 3600 if tsec(b) is not None and tsec(k) is not None else None
        for x in (k, b):
            if g is not None and (x.get('pair_gap_h') is None or g < x['pair_gap_h']): x['pair_gap_h'] = round(g, 1)
        return round(g, 1) if g is not None else None
    for (_, _, fam), L_ in grp_.items():
        L_.sort(key=lambda b: b.get('flagged') or '')
        for i, b in enumerate(L_):
            for k in L_[:i]:
                if k.get('counted') is False or k['side'] == b['side']: continue
                if lean_(k) and lean_(k) == lean_(b): continue          # soccer: "X: No" and "Y: Yes" point the same way
                if k['market'] == b['market'] and {k['side'], b['side']} == {'not_home', 'not_away'}:
                    g = gap_(k, b)      # both "not to win" bets win on a draw
                    b.setdefault('middle', []).append(dict(kind='middle', with_=desc_(k), gap_h=g)); k.setdefault('middle', []).append(dict(kind='middle', with_=desc_(b), gap_h=g))
                elif k['market'] == b['market'] and fam == 'sharp':
                    g = gap_(k, b)
                    b.setdefault('both_sides', []).append(dict(with_=desc_(k), gap_h=g)); k.setdefault('both_sides', []).append(dict(with_=desc_(b), gap_h=g))
                elif k['market'] == b['market'] and b.get('counted') is not False:
                    g = gap_(k, b)
                    b['counted'] = False; b['conflict_with'] = k['id']; b['conflict_desc'] = desc_(k); b['units_raw'] = b.get('units'); b['units'] = None
                    k.setdefault('cancelled_later', []).append(desc_(b))
                elif {k['market'].replace('1h_', ''), b['market'].replace('1h_', '')} == {'ml', 'spread'}:
                    sp = k if 'spread' in k['market'] else b
                    kind = 'middle' if (sp.get('line') or 0) > 0 else 'reverse middle'; g = gap_(k, b)
                    b.setdefault('middle', []).append(dict(kind=kind, with_=desc_(k), gap_h=g)); k.setdefault('middle', []).append(dict(kind=kind, with_=desc_(b), gap_h=g))
    # 11/5 (Sean): the watch-only market signals (Kalshi move, bet back, big money, sharp move) graded by kind, so the board can show
    # whether they are doing anything; flat ROI at the flagged price and mean no-vig CLV
    wk = {}
    for kind in ('Kalshi move', 'bet back', 'big money', 'sharp move'):
        S_ = [b for b in bets if b['cat'] == 'watch' and b.get('rule') == kind and b.get('won') is not None and b.get('price')]
        c_ = [b['clv_nv'] for b in S_ if b.get('clv_nv') is not None]
        if S_: wk[kind] = dict(n=len(S_), w=sum(1 for b in S_ if b['won'] == 1), l=sum(1 for b in S_ if b['won'] == 0),
                                roi=round(sum((1 / b['price'] - 1) if b['won'] == 1 else -1 if b['won'] == 0 else 0 for b in S_) / len(S_) * 100, 1),
                                clv_nv=round(sum(c_) / len(c_), 2) if c_ else None, clv_n=len(c_))
    tag_stats = tag_bets(bets)
    def rest_summ(L):
        L = [b for b in L if b.get('won') in (0, 1) and b.get('rest') is not None and b.get('rest_filled') is not None and b.get('price')]
        def rec(G_, pk):
            if not G_: return dict(n=0)
            x = [(1 / pk(b) - 1) if b['won'] == 1 else -1 for b in G_]; m = sum(x) / len(x); sd = (sum((v - m) ** 2 for v in x) / max(1, len(x) - 1)) ** 0.5
            return dict(n=len(G_), w=sum(1 for b in G_ if b['won'] == 1), l=sum(1 for b in G_ if b['won'] == 0), roi=round(100 * m, 1), z=round(m / (sd / len(x) ** 0.5), 2) if sd else None)
        F = [b for b in L if b['rest_filled']]; N = [b for b in L if not b['rest_filled']]
        return dict(filled_at_rest=rec(F, lambda b: b['rest']), filled_at_flag=rec(F, lambda b: b['price']), never_at_flag=rec(N, lambda b: b['price']), all_at_flag=rec(L, lambda b: b['price']))
    RG = {'bets': lambda b: b['cat'] in ('system A', 'system B', 'lean C', 'sharp A', 'sharp B', 'tennis'), 'systems and leans': lambda b: b['cat'] in ('system A', 'system B', 'lean C'),
          'sharp flags': lambda b: b['cat'] in ('sharp A', 'sharp B'), 'paper rules': lambda b: b['cat'] == 'paper P', 'watch signals': lambda b: b['cat'] == 'watch', 'everything': lambda b: True}
    rest = {k: rest_summ([b for b in bets if fn(b)]) for k, fn in RG.items()}
    rest['since'] = {k: rest_summ([b for b in bets if fn(b) and (b.get('flagged') or '') >= '2026-11-10T10:00:00Z']) for k, fn in RG.items()}     # the forward test
    out = dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), venues=list(VENUES), opposed=opp_summ, watch_kinds=wk, tag_stats=tag_stats, rest=rest,
               summary={k: summ(v) for k, v in sorted(groups.items())},
               rows=sorted(bets, key=lambda b: b['start'], reverse=True))
    json.dump(out, open(OUT, 'w'), separators=(',', ':'), default=str)
    s = out['summary'].get('all|all|all', {})
    print(f"[bet_log] {len(bets)} flagged bets ({s.get('graded')} graded, {s.get('units')}u, CLV {s.get('clv')} on {s.get('clv_n')}); {sum(1 for b in bets if b.get('best') is not None)} with a price path")


TAG_ORDER = ['sharp accts with', 'sharp accts against', 'big money with', 'big money against', 'Kalshi move with', 'Kalshi move against',
             'bet back with', 'bet back against', 'sharp move with', 'sharp move against', 'sharp flag against', 'system against', 'any signal against', 'no signal against',
             'system also', 'sharp flag also', 'same-market conflict', 'middle']


def tag_bets(bets):
    """11/7 (Sean: "lets track all aspects of these plays and backtest the sample we have"): tag every non-watch bet with the signals
    around it, then grade the sample by tag. Market signals (big money, Kalshi move, bet back, sharp move) come from the tracker's watch
    rows on the same game and market family (totals with totals; spread and moneyline together), first seen before the start. Sharp
    accounts come from the with / against annotation. A sharp flag also landing on a system bet's side (or the reverse) is tagged too.
    Flat 1 unit at the flagged price; pushes count as no result."""
    # 11/7 (Sean: team totals "may conflict with full game totals"): a team total is a total, so it is compared with the game total's
    # signals and bets (over vs under), never with the spread or moneyline
    fam = lambda m: 'total' if re.sub(r'^(1h|1q|1p)_', '', m or '') in ('total', 'tt_home', 'tt_away') else 'side'
    W = collections.defaultdict(list)
    for w in bets:
        if w['cat'] == 'watch' and w.get('event_id') and w.get('side'): W[(str(w['event_id']), fam(w['market']))].append(w)
    S_side = collections.defaultdict(set)
    for b in bets:
        if b['cat'] != 'watch' and b.get('event_id') and b.get('side'):
            S_side[(str(b['event_id']), fam(b['market']), b['side'])].add('sharp' if b['src'] == 'sharp' else 'paper' if b['cat'] == 'paper P' else 'system')
    for b in bets:
        if b['cat'] == 'watch' or not b.get('event_id') or not b.get('side') or str(b.get('market', '')).startswith('prop'): continue
        t = []
        if b.get('with'): t.append('sharp accts with')
        if b.get('opp'): t.append('sharp accts against')
        f_ = fam(b['market'])
        for w in W.get((str(b['event_id']), f_), []):
            if (w.get('flagged') or '9') >= (b.get('start') or ''): continue
            # a soccer 'not to win' bet (not_home / not_away): money on that team is against it, money on the other team is with it
            ws = b['side'][4:] if str(b['side']).startswith('not_') else None
            t.append(f"{w['rule']} {('against' if w['side'] == ws else 'with') if ws else ('with' if w['side'] == b['side'] else 'against')}")
        # 11/7 (Sean: "Maryland ML should be opposite of Purdue"): a sized sharp flag or system bet on the other team, in the spread or the
        # moneyline, is opposition too (paper rules never count)
        OPPS = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over', 'not_home': 'home', 'not_away': 'away'}
        opp_k = set(S_side.get((str(b['event_id']), f_, OPPS.get(b['side'], '')), set()))
        if b['side'] in ('home', 'away'): opp_k |= S_side.get((str(b['event_id']), f_, 'not_' + b['side']), set())   # a 'not to win' flag on this team
        if 'sharp' in opp_k: t.append('sharp flag against')
        if 'system' in opp_k: t.append('system against')
        if any(x.endswith('against') for x in t): t.append('any signal against')
        else: t.append('no signal against')
        others = S_side.get((str(b['event_id']), f_, b['side']), set())
        if b['src'] == 'sharp' and 'system' in others: t.append('system also')
        if b['src'] != 'sharp' and 'sharp' in others: t.append('sharp flag also')
        if b.get('counted') is False or b.get('both_sides'): t.append('same-market conflict')
        if b.get('middle'): t.append('middle')
        b['tags'] = sorted(set(t), key=lambda x: TAG_ORDER.index(x) if x in TAG_ORDER else 99)
    # the backtest of the sample: graded bets by group (systems and leans / sharp flags / everything) and tag
    groups = {'systems and leans': lambda b: b['src'] in ('system', 'curve', 'props', 'mma', 'tennis') and b['cat'] in ('system A', 'system B', 'lean C', 'tennis'),
              'paper rules': lambda b: b['cat'] == 'paper P', 'sharp flags': lambda b: b['src'] == 'sharp' and b['cat'] in ('sharp A', 'sharp B', 'sharp C')}
    out = {}
    for gname, gf in groups.items():
        G_ = [b for b in bets if b.get('tags') is not None and gf(b) and b.get('won') is not None and b.get('price')]
        def rec(L):
            w = sum(1 for b in L if b['won'] == 1); l = sum(1 for b in L if b['won'] == 0)
            u = sum((1 / b['price'] - 1) if b['won'] == 1 else -1 if b['won'] == 0 else 0 for b in L)
            return dict(n=w + l, w=w, l=l, roi=round(100 * u / max(1, w + l), 1))
        out[gname] = dict(all=rec(G_), tags={tg: rec([b for b in G_ if tg in b['tags']]) for tg in TAG_ORDER if any(tg in b['tags'] for b in G_)})
    return out


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
        A_, H_ = e.get('away_team'), e.get('home_team')
        if not A_ or not H_: continue
        base = re.sub(r'^(1h|1q|1p)_', '', b['market']); fam = ('total',) if base == 'total' else ('ml', 'spread')
        t_flag = ts(b['flagged']).timestamp(); t_start = ts(b['start']).timestamp()
        W = {}; WITH = {}
        for x in byday.get(b['start'][:10], []):
            t = (x.get('title') or '').lower()
            if not team_hit(A_, t) or not team_hit(H_, t) or x.get('mtype') not in fam or x['ts'] >= t_start: continue
            bt = (x.get('bet') or '').lower()
            xs = (bt.split()[0] if bt else None) if base == 'total' else team_side(A_, H_, bt)
            if xs is None: continue
            D = W if xs != b['side'] else WITH
            w = D.setdefault(x['w'], dict(first=x['ts'], usd=0.0, rank=x['rank'])); w['first'] = min(w['first'], x['ts']); w['usd'] += x.get('usd') or 0
        # 11/5 (Sean): also note the sharps WITH the bet (same side), so a system bet that sharp money joined is labelled too
        if WITH and b['src'] not in ('sharp', 'watch'):
            first = min(w['first'] for w in WITH.values())
            b['with'] = dict(n=len(WITH), usd=round(sum(w['usd'] for w in WITH.values())), best_rank=min(w['rank'] for w in WITH.values()),
                             first=dt.datetime.fromtimestamp(first, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), when='at_flag' if first <= t_flag else 'after')
        if not W: continue
        first = min(w['first'] for w in W.values())
        b['opp'] = dict(n=len(W), usd=round(sum(w['usd'] for w in W.values())), best_rank=min(w['rank'] for w in W.values()),
                        first=dt.datetime.fromtimestamp(first, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), when='at_flag' if first <= t_flag else 'after',
                        min_before_start=round((t_start - first) / 60))
        n += 1
    return n


if __name__ == '__main__':
    if os.environ.get('BL_PROFILE'):          # 11/7: where the signals job's slowest step spends its time (top 25 by cumulative time)
        import cProfile, pstats
        pr = cProfile.Profile(); pr.enable(); main(); pr.disable()
        pstats.Stats(pr).sort_stats('cumulative').print_stats(25)
    else:
        main()
