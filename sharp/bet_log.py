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
# 11/10 (Sean, docs/review_2026-11-10.md): sharp flags carry no units from here. Flags logged before this keep the size they were tracked at.
# 11/24 (Sean): the way back to units no longer depends on beating Pinnacle's close. A sport x grade slice of sharp flags goes live only on
# the profit promote line (docs/checkpoint_rules_2026-11-02.md, 11/24 amendment): 100+ graded, a 10% or smaller chance of a result this good
# at break-even after fees, ROI positive in both halves. Live slices so far: soccer A and B (11/21), NBA B at 0.25u (11/24, a test; 0.25u is the minimum live size).
SHARP_PAPER_FROM = '2026-11-10T10:00:00Z'
# 11/21 (Sean via Kirk): SOCCER sharp flags, grade A and B with nothing against, are real bets at 0.25u for games starting from here on
# (soccer sharp A 23-18, +17.4% ROI on 41 since 11/3). No backfill: games that started earlier stay paper. Every other sport stays paper.
SOCCER_SHARP_LIVE_FROM = '2026-11-21T18:45:00Z'
# 11/24 (Sean via Kirk): a Kalshi 4+ move against is a shown warning, not a block, for games starting from KALSHI_WARN_FROM (re-read 12/8,
# docs/decisions_2026-11-24.md). Earlier games keep the block they were tracked under, so nothing is re-scored backwards.
KALSHI_WARN_FROM = '2026-11-24T19:00:00Z'
def kalshi_blocks(start): return (start or '') < KALSHI_WARN_FROM
def soccer_sharp_live(cat, sport, start, against=False):
    return cat in ('sharp A', 'sharp B') and sport == 'soccer' and not (against and kalshi_blocks(start)) and (start or '') >= SOCCER_SHARP_LIVE_FROM
# 11/24 (Sean via Kirk): NBA sharp flags graded B are a live test for games starting from here (paper record +11.6% on 53, p 0.18);
# re-read at 100 graded flags. NBA A and watch flags stay paper. Size 0.25u: Sean 11/24, 0.25u is the minimum live size, no 0.10u tests.
NBA_SHARP_B_LIVE_FROM = '2026-11-24T19:00:00Z'; NBA_SHARP_B_SIZE = 0.25
def nba_sharp_b_live(cat, sport, start): return cat == 'sharp B' and sport == 'nba' and (start or '') >= NBA_SHARP_B_LIVE_FROM
# 11/14: a rule promoted from paper counts as a bet only for fills logged from its promotion on; its earlier paper fills stay paper, so
# no units are backdated into the record.
PROMOTED_FROM = {'xch_homedog_fade': '2026-11-14T08:30:00Z'}     # Sean 11/14: paper -> tier C
# Sean 11/18: every paper rule -> tier C; games that started before the switch stay paper in the record, open ones count as tier C (they show as bets)
PROMOTED_FROM.update({k: '2026-11-19T04:00:00Z' for k in ['awfuldog_deep', 'wind1014_cold', 'nfl_road_dog_7510', 'nhl_loss_streak_over', 'mlb_road_over_under', 'nba_roadtrip_over',
    'cfb_day_over', 'nfl_fade_fav_bye', 'bounce15_1h', 'nba_momentum', 'nhl_pl_fav_gap', 'nhl_pl_fav_strong_opp', 'nhl_pl_dog_bigml', 'nba_1h_under_hot_over',
    'nba_under_good_home_over_small', 'cfb_road_dog_low_total', 'cfb_road_streak_dog', 'cbb_under_good_over_drop']})
PROMOTED_BY_START = set(PROMOTED_FROM) - {'xch_homedog_fade'}
# 11/21 (Sean): demoted back to paper. Fills on games that started from the promotion up to this cutoff keep their tier C record; later ones are paper.
DEMOTED_FROM = {'cfb_day_over': '2026-11-21T19:20:00Z',
                # cfb_road_dog_low_total: the 11/23 retirement rested on CLV; 11/24 (Sean) restored to tier C, so it has no demotion cutoff.
                }
# 11/24 (Sean via Kirk, docs/decisions_2026-11-24.md): tier C -> paper. Games that started before this keep their tier C record.
DEMOTED_FROM.update({k: '2026-11-24T19:00:00Z' for k in ['nhl_skid_fade_road', 'nfl_fade_fav_bye', 'nba_ats_hot_home', 'nba_bigfav_over', 'nhl_loss_streak_over',
    'nba_badteams_under', 'nfl_road_dog_7510', 'mlb_road_over_under', 'nba_roadtrip_over', 'nhl_bounce_home_ml', 'bounce15_1h', 'nhl_pl_fav_strong_opp',
    'nhl_pl_fav_gap', 'nba_under_good_home_over_small', 'cfb_road_streak_dog', 'cbb_under_good_over_drop', 'awfuldog_deep', 'wind1014_cold']})
# 11/18 (Sean): everything is 0.25u for now, every tier (favourite: to win 0.25u; plus money: risk 0.25u). Bets flagged before this keep
# the size they were tracked at, so nothing is resized backwards.
FLAT_QUARTER_FROM = '2026-11-18T20:30:00Z'
# 11/16 evening (Sean, tools/betting/AUTO_TENNIS_PROPS.md): the only real-money tennis angle is the big-serving underdog (tennis_serve_dog);
# every other tennis angle (set-1 favourite, settled / hot favourite, hot dog, serve favourite) is paper. Matches starting from here are
# logged that way, so serve dogs are graded as bets and the rest as paper; earlier matches keep the category they were tracked under.
TENNIS_POLICY_FROM = '2026-11-17T04:00:00Z'
def tennis_cat(rule, start, old):
    if (start or '') < TENNIS_POLICY_FROM: return old
    return 'tennis' if rule == 'tennis_serve_dog' else 'paper P'
def size_units(cat, rule=None, sport=None, flagged=None, start=None, against=False):
    if soccer_sharp_live(cat, sport, start, against): return 0.25
    if nba_sharp_b_live(cat, sport, start): return NBA_SHARP_B_SIZE
    if cat == 'watch' or (cat.startswith('sharp') and (flagged or '') >= SHARP_PAPER_FROM): return 0.0
    if (flagged or '') >= FLAT_QUARTER_FROM: return 0.25
    return 0.5 if (cat in ('system A', 'system B') or (cat == 'sharp A' and sport != 'soccer') or rule in HALF_U) else 0.25


# 11/20 (Sekulic): a 0.998 price on an empty exchange book graded a 0.25u to-win loss as -124.75u. Guards: a row priced above 0.95, or above
# 0.90 for an underdog rule, is not graded (shown as excluded, out of every record); and no row can lose more than LOSS_CAP x its size,
# whatever its price: 19 x, the risk of a to-win bet at the 0.95 ceiling (0.25u size: at most 4.75u). A tighter cap would understate real
# favourite losses (a 0.25u to-win bet at -450 loses 1.125u).
LOSS_CAP = 19
def bad_price(p, rule):
    return p is not None and (p > 0.95 or ('dog' in (rule or '') and p > 0.90))


def units(p, won, size):
    if won is None or p is None or not 0 < p < 1: return None
    if won == 0.5: return 0.0
    if p > 0.5: return round(size if won else max(-size * p / (1 - p), -LOSS_CAP * size), 3)
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


# 11/24 (Kirk): the bet log carries the board's own call for every row (board_status / board_why), so an automated placer that reads
# bet_log.json bets only what the page shows as a bet. Values: bet, held, pass (bought out), dropped, wait (wind before 12h), paper.
# The page's sharp-flag logic (index.html renderToday): a flag is HELD when a sharp took the other side (status 'other side'), sharp
# accounts sit on the other side, or a market signal against is tagged (big money, bet back, sharp move, sharp accounts, sharp flag,
# system; a Kalshi move only for games before KALSHI_WARN_FROM); PASS when the ask is 5c+ above what the sharps paid (bought out);
# DROPPED when the flag is no longer live or conflicts. Calls freeze at the start: a started game keeps its last pre-start call.
WIND_TAGS = {'wind1014', 'wind1014_1h', 'cfb_wind14', 'wind1014_cold'}
HOLD_TAGS = ('big money against', 'bet back against', 'sharp move against', 'sharp accts against', 'sharp flag against', 'system against')
def board_status(bets):
    now = NOW.strftime('%Y-%m-%dT%H:%M:%SZ')
    try: prev = {r['id']: (r.get('board_status'), r.get('board_why')) for r in json.load(open(OUT)).get('rows', []) if r.get('board_status')}
    except Exception: prev = {}
    try: SAJ = json.load(open(os.path.join(SD, 'sharp_accounts.json')))
    except Exception: SAJ = {}
    SAR = {r.get('cond'): r for r in SAJ.get('rows', []) if r.get('cond')}
    for b in bets:
        st_ = b.get('start') or ''
        if st_ and st_ <= now and b['id'] in prev:
            b['board_status'], b['board_why'] = prev[b['id']]
            if b['board_status'] == 'held': b['held'] = True
            continue
        tg = set(b.get('tags') or []); st, why = 'bet', ''
        if b.get('excluded') or b.get('lapsed'): st, why = 'dropped', b.get('excluded') or 'trigger lapsed'
        elif b.get('counted') is False: st, why = 'dropped', 'conflicting systems cancel'
        elif b['cat'] == 'watch' or not b.get('size'): st, why = 'paper', 'paper or watch only: no units'
        elif b.get('src') == 'sharp':
            r = SAR.get(b['id'][2:]) if b['id'].startswith('p:') else None
            ag = [t.replace(' against', '') for t in HOLD_TAGS if t in tg] + (['Kalshi move'] if 'Kalshi move against' in tg and kalshi_blocks(st_) else [])
            if r is not None and (r.get('status') not in ('live', 'other side') or r.get('conflict') or (r.get('kalshi_against') and kalshi_blocks(st_))):
                st, why = 'dropped', 'flag no longer live' if r.get('status') not in ('live', 'other side') else 'a signal on the other side' if r.get('conflict') else 'Kalshi moved the other way'
            elif (r is not None and r.get('status') == 'other side') or ag:
                st, why = 'held', '; '.join((['a sharp took the other side'] if r is not None and r.get('status') == 'other side' else []) + ([', '.join(ag) + ' against'] if ag else []))
            elif r is not None and r.get('ask') is not None and r.get('paid') is not None and r['ask'] - r['paid'] >= 0.05 - 1e-9:
                st, why = 'pass', f"bought out: ask {round(100 * r['ask'])}c vs the sharps' {round(100 * r['paid'])}c"
        elif b.get('held'): st, why = 'held', 'a rule on the other side' if 'system against' in tg else 'Kalshi moved the other way'
        elif b.get('rule') in WIND_TAGS and st_ and (dt.datetime.fromisoformat(st_.replace('Z', '+00:00')) - NOW).total_seconds() > 12 * 3600: st, why = 'wait', 'wind rules wait until 12h before kickoff'
        b['board_status'], b['board_why'] = st, why
        if st == 'held': b['held'] = True


# 11/24 (Kirk, research for Sean; docs/cancel_and_sharp_signal_2026-11-24.md): the sample to decide what should cancel a system play.
# One row per system position (systems, curve, props, tennis, MMA, paper rules; sharp flags and watch signals are not system plays), with
# every signal on the other side (kind, grade, first seen, hours before the start, before or after the system fired, its price, and the
# Kalshi move size in points from the day reviews) and every signal on the same side. Both sides are paper-graded: the play at its own
# price, and the other side at the price the opposing signal showed (or 1 - price), flat 1u (favourite to win 1u, plus money risk 1u).
# Research only: nothing on the board reads it. Written to data/state/against_panel.json every build.
AGAINST_PANEL = os.path.join(SD, 'against_panel.json')
def _flat1(p, won):
    if won is None or p is None or not 0 < p < 1: return None
    if won == 0.5: return 0.0
    return (1.0 if won else -p / (1 - p)) if p > 0.5 else ((1 - p) / p if won else -1.0)
def against_panel(bets):
    I = {b['id']: b for b in bets}
    KM = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'research', 'day_review_*.json'))):
        try: L = json.load(open(f))
        except Exception: continue
        for x in L:
            if x.get('family') == 'kmove4': KM.setdefault((str(x.get('event_id')), x.get('market'), x.get('side')), x)
    def lead(t, st):
        try: return round((dt.datetime.fromisoformat(st.replace('Z', '+00:00')) - dt.datetime.fromisoformat(t.replace('Z', '+00:00'))).total_seconds() / 3600, 1)
        except Exception: return None
    rows = []
    for b in bets:
        if b.get('src') not in ('system', 'curve', 'props', 'tennis', 'mma', 'paper') or b.get('excluded'): continue
        sig = lambda ids: [dict(id=i, kind=('sharp flag' if i.startswith('p:') else 'sharp C' if i.startswith('c:') else 'system' if i.startswith(('s:', 'cv:')) else (I.get(i) or {}).get('rule') or i.split('|')[-1]),
                                grade=(I.get(i) or {}).get('cat'), side=(I.get(i) or {}).get('side'), first=(I.get(i) or {}).get('flagged'),
                                lead_h=lead((I.get(i) or {}).get('flagged') or '', b.get('start') or ''), before_system=((I.get(i) or {}).get('flagged') or '9') < (b.get('flagged') or ''),
                                price=(I.get(i) or {}).get('price'), won=(I.get(i) or {}).get('won')) for i in ids]
        ag = sig(b.get('corr_opp') or []); wi = sig(b.get('corr_same') or [])
        mk = (b.get('market') or '').replace('1h_', '').replace('1q_', '').replace('3p_', '').replace('1p_', '')
        km = KM.get((str(b.get('event_id')), mk, {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}.get(b.get('side'))))
        for a in ag:
            if a['kind'] == 'Kalshi move' and km: a['size_pts'] = round(100 * abs(km['at'] - km['first']), 1); a['first'] = a['first'] or km.get('t0')
        po = next((a['price'] for a in ag if a.get('price') and (I.get(a['id']) or {}).get('market') == b.get('market')), None) or (round(1 - b['price'], 4) if b.get('price') else None)
        wo = None if b.get('won') is None else 0.5 if b['won'] == 0.5 else 1 - b['won']
        rows.append(dict(id=b['id'], rule=b.get('rule'), src=b.get('src'), cat=b.get('cat'), sport=b.get('sport'), event_id=b.get('event_id'), market=b.get('market'), side=b.get('side'),
                         start=b.get('start'), flagged=b.get('flagged'), price=b.get('price'), won=b.get('won'), u_play=_flat1(b.get('price'), b.get('won')),
                         price_other=po, u_other=_flat1(po, wo), tags=b.get('tags'), board_status=b.get('board_status'), against=ag, with_=wi))
    json.dump(dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), note='research panel: what should cancel a system play (docs/cancel_and_sharp_signal_2026-11-24.md)', rows=rows),
              open(AGAINST_PANEL, 'w'), separators=(',', ':'), default=str)


def main():
    S = schedules()
    SF_ = json.load(open(os.path.join(SD, 'system_fires.json')))
    tiers = {k: (v.get('evidence') or {}).get('tier') for k, v in SF_['rules'].items()}
    # 11/22 (Sean via Kirk): honor lapsed wind bets. A wind fill whose forecast no longer meets the rule before kickoff (system_fires shows
    # it lapsed) is not a bet: no units, not in the record. data/state/lapsed_fills.json keeps the call after kickoff, when system_fires
    # drops the game; a fill that fires again before kickoff comes back. 11/22 (Kirk): every rule, not just wind (Sean tracks his own bets).
    lp_path = os.path.join(SD, 'lapsed_fills.json')
    try: LAPSED = json.load(open(lp_path))
    except Exception: LAPSED = {}
    lap_now, live_now = set(), set()
    for g_ in SF_.get('games', []):
        for f_ in g_.get('fills', []):
            if f_.get('fill_id'): (lap_now if f_.get('lapsed') else live_now).add(f_['fill_id'])
    bets = []
    # ---- systems
    for l in open(os.path.join(SD, 'fills.jsonl')):
        r = json.loads(l)
        if r.get('result') == 'void' or r.get('mclass', 'game') != 'game': continue
        tag = str(r.get('rule_tag', '')).replace('paper:', ''); tier = tiers.get(tag)
        cat = {'A': 'system A', 'B': 'system B', 'C': 'lean C', 'P': 'paper P'}.get(tier, 'paper P')
        if tag in PROMOTED_FROM and (r.get('start_utc' if tag in PROMOTED_BY_START else 'ts_utc') or '') < PROMOTED_FROM[tag]: cat = 'paper P'
        elif tag in DEMOTED_FROM and (r.get('start_utc') or '') < DEMOTED_FROM[tag] and (r.get('start_utc') or '') >= PROMOTED_FROM.get(tag, ''): cat = 'lean C'
        e = S.get(r['event_id']) or {}
        won = {'W': 1, 'L': 0, 'P': 0.5}.get(r.get('result'))
        if (r.get('start_utc') or '') > NOW.strftime('%Y-%m-%dT%H:%M:%SZ'):
            if r['fill_id'] in lap_now: LAPSED[r['fill_id']] = dict(rule=tag, event_id=r['event_id'], start=r['start_utc'], seen=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'))
            elif r['fill_id'] in live_now: LAPSED.pop(r['fill_id'], None)
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
                         won={'W': 1, 'L': 0}.get(p.get('result')), bet=p['bet'], against=bool(p.get('kalshi_against'))))
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
            bets.append(dict(id='t:' + p['event_id'], src='tennis', cat=tennis_cat('tennis_fs_fav', p['start'], 'tennis'), rule='tennis_fs_fav', sport='tennis', event_id=p['event_id'], game=f"{p.get('fav_name')} vs {p.get('opp_name')}",
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
            bets.append(dict(id=f"{'th' if rule == 'tennis_hot_fav' else 'td'}:{p['event_id']}", src='tennis', cat=tennis_cat(rule, p['start'], 'system B' if live else 'paper P'), rule=rule, sport='tennis', event_id=p['event_id'],   # 11/5 (Sean): settled favourites are tier B, 0.5u
                             game=f"{p.get('fav_name')} vs {p.get('opp_name')}", start=p['start'], market='ml', side=side, line=None, flagged=p['ts'], venue=p['venue'], price=p['price'],
                             won=None if not g_ or g_.get('void') else (1 if g_['won'] else 0), bet=f"{pick} to win"))
            if g_ and g_.get('void'): bets[-1]['excluded'] = 'void: the match was not played as listed (no winner settled)'      # 11/24
    # Serve-profile logs are simulated records, not exchange fill evidence.
    sp = os.path.join(ROOT, 'data', 'tennis', 'serve_paper.jsonl')
    sg = os.path.join(ROOT, 'data', 'tennis', 'serve_graded.json')
    if os.path.exists(sp):
        GS = {g['event_id']: g for g in (json.load(open(sg)) if os.path.exists(sg) else [])}
        seen_serve = set()
        for line in open(sp):
            p = json.loads(line)
            key = (p['event_id'], p['rule'], p['side'])
            if key in seen_serve: continue
            seen_serve.add(key)
            g_ = GS.get(p['event_id'])
            bets.append(dict(id=f"tv:{p['event_id']}:{p['rule']}", src='tennis', cat=tennis_cat(p['rule'], p['start'], 'paper P'),
                             rule=p['rule'], sport='tennis', event_id=p['event_id'],
                             game=f"{p.get('fav_name')} vs {p.get('opp_name')}", start=p['start'],
                             market='ml', side=p['side'], line=None, flagged=p['ts'],
                             venue=p['venue'], price=p['price'],
                             won=None if not g_ or g_.get('void') else (1 if g_['won'] else 0),
                             bet=f"{p.get('pick_name')} to win"))
            if g_ and g_.get('void'): bets[-1]['excluded'] = 'void: the match was not played as listed (no winner settled)'      # 11/24
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
    # Current schedule, not immutable flag-time estimates, drives upcoming tennis.
    from sharp.tennis_timing import reconcile_bet
    for b in bets: reconcile_bet(b, S, dt.datetime.now(dt.timezone.utc))
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
        # 11/24: any row still ungraded once the game is final is graded from the score (was watch and sharp C only; kalshi_nhl_flow stopped
        # being graded in its own log after 11/6 and 296 rows sat open)
        if b['won'] is None and not b.get('excluded') and b.get('margin') is not None and (base != 'total' and base != 'spread' or b['line'] is not None):
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
    json.dump(LAPSED, open(lp_path, 'w'), indent=0, sort_keys=True)
    for b in bets:
        b['bet_type'] = b['market'].replace('1s_ml', 'set1_ml')
        b['size'] = size_units(b['cat'], b.get('rule'), b.get('sport'), b.get('flagged'), b.get('start'), b.get('against')); b['units'] = units(b['price'], b['won'], b['size'])
        if b['src'] == 'system' and b['id'][2:] in LAPSED:
            b['lapsed'] = True; b['excluded'] = 'lapsed: the trigger no longer held before the start (forecast or line moved), so not a bet'
            b['units_raw'] = b['units']; b['units'] = None; b['won_raw'] = b['won']; b['won'] = None; b['size'] = 0
        elif bad_price(b['price'], b.get('rule')):
            b['excluded'] = f"price {b['price']} out of range (above 0.95, or above 0.90 for an underdog rule): not graded"
            b['units_raw'] = b['units']; b['units'] = None; b['won_raw'] = b['won']; b['won'] = None
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
    # 11/14 (Sean): what the board holds now: a Kalshi move against a system or lean, or a rule on the other side.
    # 11/24 (Sean): for games from KALSHI_WARN_FROM a Kalshi move against is a warning (b['kalshi_warn']), not a hold.
    for b in bets:
        tg = set(b.get('tags') or [])
        if 'Kalshi move against' in tg: b['kalshi_warn'] = True
        if b['cat'] in ('system A', 'system B', 'lean C', 'tennis') and ('system against' in tg or ('Kalshi move against' in tg and kalshi_blocks(b.get('start')))): b['held'] = True
    board_status(bets)
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
    # ---- 11/21 (Sean via Kirk): Sean's ACTUAL fills (data/state/placed.jsonl, hand-entered from what he reports), graded at his own line
    # and price, 0.25u (favourite: to win 0.25u; plus money: risk 0.25u). Kept apart from the system records, which grade each rule at the
    # price it flagged. A fill inherits the result of its tracker row when that row is the same market, side and line (sharp flags graded
    # on Polymarket, FCS games with no score feed); otherwise it is graded from final scores (data/state/results.jsonl).
    placed = []
    pp = os.path.join(SD, 'placed.jsonl'); BI = {b['id']: b for b in bets}
    if os.path.exists(pp):
        for l in open(pp):
            try: f = json.loads(l)
            except Exception: continue
            won = None; mb = BI.get(f.get('match')) or {}
            if mb and mb.get('market') == f['market'] and mb.get('side') in (f['side'], None) and (mb.get('line') == f.get('line') or f['market'].endswith('ml')): won = mb.get('won')
            r = RES.get(f.get('event_id')) if f.get('event_id') else None
            if won is None and r:
                m = f['market']; h_, a_ = (r.get('f5_home'), r.get('f5_away')) if m.startswith('1h_') else (r.get('home_score'), r.get('away_score'))
                if h_ is not None and a_ is not None:
                    base = re.sub(r'^(1h|1q|1p)_', '', m); L = float(f.get('line') or 0)
                    mg = ((L - (h_ + a_)) if f['side'] == 'under' else ((h_ + a_) - L)) if base == 'total' else (((h_ - a_) if f['side'] == 'home' else (a_ - h_)) + L) if base == 'spread' else ((h_ - a_) if f['side'] == 'home' else (a_ - h_))
                    won = 1 if mg > 0 else 0 if mg < 0 else 0.5
            placed.append(dict(f, won=won, units=units(f['price'], won, f.get('size', 0.25)), tracker=dict(id=mb.get('id'), cat=mb.get('cat'), rule=mb.get('rule'), price=mb.get('price'), line=mb.get('line')) if mb else None))
    G_ = [x for x in placed if x['won'] in (0, 1, 0.5)]
    placed_summ = dict(n=len(placed), graded=len(G_), w=sum(x['won'] == 1 for x in G_), l=sum(x['won'] == 0 for x in G_), p=sum(x['won'] == 0.5 for x in G_), units=round(sum(x['units'] or 0 for x in G_), 2))
    out = dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), venues=list(VENUES), opposed=opp_summ, watch_kinds=wk, tag_stats=tag_stats, rest=rest,
               placed=dict(summary=placed_summ, rows=sorted(placed, key=lambda x: x['start'], reverse=True)),
               summary={k: summ(v) for k, v in sorted(groups.items())},
               rows=sorted(bets, key=lambda b: b['start'], reverse=True))
    json.dump(out, open(OUT, 'w'), separators=(',', ':'), default=str)
    try: against_panel(bets)
    except Exception as e: print(f"[bet_log] against panel failed: {e}")
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
