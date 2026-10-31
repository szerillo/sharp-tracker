"""The ruler: a weighted, devigged, cross-venue fair probability for one side of one market at one timestamp (spec §5-§7).

No projection enters here. Weights are the PRIOR vector from constants.py until fit_weights() has replaced it; every result carries
`status` ('prior' | 'fitted') and the venue detail so the dashboard can tag it.
"""
import os, sys, json, bisect, datetime as dt, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from sharp import constants as C, norm as N, devig as DV
from sharp import sports as SP

OTHER = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}
EXCHANGES = {v for v, c in C.VENUE_CLASS.items() if c == 'exchange'}
WEIGHTS_FILE = os.path.join(os.path.dirname(HERE), 'data', 'state', 'weights_fitted.json')


def weights_for(sport, mclass):
    """Fitted vector when one exists for this sport/class and passed its gate, else the prior. Returns (dict, status, meta)."""
    if os.path.exists(WEIGHTS_FILE):
        w = json.load(open(WEIGHTS_FILE)).get(f"{sport}:{mclass}")
        if w and w.get('status') == 'fitted': return w['value'], 'fitted', w
    c = C.WEIGHTS[(sport, mclass)]
    return c['value'], 'prior', c


def capped_weights(w):
    """Normalise and cap any venue at WEIGHT_CAP of the total (spec §7); redistribute the excess to the others."""
    w = {k: float(v) for k, v in w.items() if v and v > 0}
    cap = C.WEIGHT_CAP['value']
    for _ in range(10):
        s = sum(w.values())
        if not s: return {}
        n = {k: v / s for k, v in w.items()}
        over = {k: v for k, v in n.items() if v > cap + 1e-9}
        if not over or len(n) == 1: return n
        excess = sum(v - cap for v in over.values()); rest = {k: v for k, v in n.items() if k not in over}
        rs = sum(rest.values())
        w = {**{k: cap for k in over}, **{k: v + excess * (v / rs if rs else 1 / len(rest)) for k, v in rest.items()}}
    return n


def depth_usd(r):
    """Resting dollars within 3c of best on this side (build_db writes `depth3` per row in DOLLARS: Novig 1c-contracts x price / 100, Kalshi oblog dollars, Polymarket shares x price). None if unknown."""
    try: x = json.loads(r[14]) if r[14] else None
    except Exception: return None
    if not x or x.get('depth3') is None: return None
    return float(x['depth3'])


NOT_A_BOOK = {'AN_Open', 'Kalshi', 'Novig', 'Polymarket'}      # never vote on which line is the main one


class EventQuotes:
    """All ticks of one event in memory, indexed by (venue, market, line, side) and sorted by time."""
    def __init__(self, conn, event_id):
        self.idx = collections.defaultdict(list)
        self.event = conn.execute("SELECT event_id, et_date, start_utc, away, home FROM events WHERE event_id=?", (event_id,)).fetchone()
        row = conn.execute("SELECT sport FROM events WHERE event_id=?", (event_id,)).fetchone(); self.sport = row[0] if row else 'mlb'
        for r in conn.execute("""SELECT ts_utc, venue, market, line, side, implied, bid, ask, mid, flags, price_american, "limit", participant, player_name, extra FROM ticks
                                 WHERE event_id=? ORDER BY ts_utc""", (event_id,)):
            self.idx[(r[1], r[2], r[3], r[4], r[12])].append(r)
        self.keys = collections.defaultdict(set)      # (market, line, participant) -> venues
        self.names = {}
        last_ts = {}                                   # (venue, market, participant) -> (latest ts, lines quoted at it)
        for (v, m, l, s, p) in self.idx:
            self.keys[(m, l, p)].add(v)
            if p and self.idx[(v, m, l, s, p)][0][13]: self.names[p] = self.idx[(v, m, l, s, p)][0][13]
            if v in NOT_A_BOOK or l is None: continue
            t = self.idx[(v, m, l, s, p)][-1][0]; cur = last_ts.get((v, m, p))
            if cur is None or t > cur[0]: last_ts[(v, m, p)] = (t, {l})
            elif t == cur[0]: cur[1].add(l)
        # (market, line, participant) -> books whose LATEST quote is this line. Main lines come from this, not from every line a book has
        # ever hung (a total that moved 49.5 -> 47.5 used to lose to its own history) and never from the opener or the exchanges' strike ladders.
        self.current = collections.defaultdict(set)
        for (v, m, p), (t, ls) in last_ts.items():
            for l in ls: self.current[(m, l, p)].add(v)

    def latest(self, venue, market, line, side, ts_iso, max_age_min, participant=None):
        L = self.idx.get((venue, market, line, side, participant))
        if not L: return None
        i = bisect.bisect_right([r[0] for r in L], ts_iso) - 1
        if i < 0: return None
        r = L[i]
        age = (N.parse_ts(ts_iso) - N.parse_ts(r[0])).total_seconds() / 60
        if age > max_age_min: return None
        return r

    def venue_prob(self, venue, market, line, side, ts_iso, method, participant=None, max_age=None):
        """Devigged probability of `side` at `venue` as of ts, or (None, reason)."""
        is_x = venue in EXCHANGES
        if max_age is None: max_age = C.STALE_EXCHANGE_MIN['value'] if is_x else C.STALE_BOOK_MIN['value']
        r = self.latest(venue, market, line, side, ts_iso, max_age, participant)
        if not r: return None, 'no_quote'
        if self.sport == 'soccer' and market.endswith('ml'):
            return self.three_way_prob(venue, market, ts_iso, max_age, side)
        base = market.split('_')[-1] if market.startswith(('1h_', '1q_', '1p_')) else market
        two_sided_team = base in ('ml', 'rl', 'spread') or market in ('f5_ml', 'f5_rl')
        other_line = line if base not in ('rl', 'spread') or line is None else -line
        other_part = participant
        if two_sided_team and self.event: other_part = self.event[4] if side == 'away' else self.event[3]
        o = self.latest(venue, market, other_line, OTHER.get(side), ts_iso, max_age, other_part)
        flags = set((r[9] or '').split(','))
        if is_x:
            if r[6] is None or r[7] is None: return None, 'oneside'
            if 'wide' in flags or (r[7] - r[6]) > C.EXCHANGE_SPREAD_MAX['value']: return None, f'wide {round(100 * (r[7] - r[6]))}c'
            d_this, d_other = depth_usd(r), depth_usd(o) if o else None
            if d_this is not None and d_other is not None and min(d_this, d_other) < C.EXCHANGE_MIN_DEPTH_USD['value']:
                return None, f'thin ${int(min(d_this, d_other))}'
            p = r[8]
            if (market == 'f5_ml' or market.endswith('_ml') and market != 'ml' or market == 'ml' and self.sport in ('nfl', 'cfb')) and venue == 'Kalshi':   # three-way (tie is its own ticker): condition on no tie
                if not o or o[8] is None: return None, 'no_other'
                p = p / (p + o[8])
            return p, 'ok'
        if not o: return None, 'no_other'
        return DV.devig_pair(r[5], o[5], method), 'ok'

    def three_way_prob(self, venue, market, ts_iso, max_age, side):
        """Soccer moneyline: home / away / draw are three sides of one market at every venue; devig by normalising the three implied probabilities."""
        imp = {}
        for s_ in ('home', 'away', 'draw'):
            part = None if s_ == 'draw' else (self.event[4] if s_ == 'home' else self.event[3]) if self.event else None
            q = self.latest(venue, market, None, s_, ts_iso, max_age, part)
            if not q: return None, f'no_{s_}'
            if venue in EXCHANGES:
                if q[6] is None or q[7] is None: return None, 'oneside'
                if (q[7] - q[6]) > C.EXCHANGE_SPREAD_MAX['value']: return None, f'wide {round(100 * (q[7] - q[6]))}c'
                imp[s_] = q[8] if q[8] is not None else (q[6] + q[7]) / 2
            else:
                if q[5] is None: return None, 'no_price'
                imp[s_] = q[5]
        tot = sum(imp.values())
        if not 0.95 < tot < 1.25: return None, f'overround {round(tot, 3)}'
        return imp[side] / tot, 'ok'

    def fair(self, market, line, side, ts_iso, participant=None, sport=None):
        sport = sport or self.sport
        if market == '1p_ml': return dict(fair=None, status='threeway', n=0, detail={}, weights={})   # NHL first-period ML is three-way at every venue (tie ~20%); two-way devig would be wrong. Not priced until draw quotes are logged.
        mclass = N.MARKET_CLASS(market) if sport == 'mlb' else SP.market_class(market)
        w, status, meta = weights_for(sport, mclass)
        method = C.DEVIG_METHOD[(sport, mclass)]['value']
        detail = {}; probs = {}
        for v in self.keys.get((market, line, participant), set()):
            if v not in C.RULER_ELIGIBLE: continue
            p, why = self.venue_prob(v, market, line, side, ts_iso, method, participant)
            detail[v] = {'p': p, 'why': why}
            if p is not None and w.get(v, 0) > 0: probs[v] = p
        # one big make order is not a price: an exchange quote far from the books on the same line needs company
        books = [p for v, p in probs.items() if v not in EXCHANGES]
        if books:
            med = sorted(books)[len(books) // 2]
            for v in [v for v in probs if v in EXCHANGES]:
                gap = probs[v] - med
                if abs(gap) > C.EXCHANGE_OUTLIER_PTS['value']:
                    near = sum(1 for u, p in probs.items() if u != v and abs(p - probs[v]) <= 0.03)
                    if near < C.EXCHANGE_OUTLIER_CONFIRM['value']:
                        detail[v] = {'p': None, 'why': f'outlier {gap * 100:+.0f}pts', 'p_raw': probs[v]}; del probs[v]
        if not probs: return dict(fair=None, status=status, n=0, detail=detail, weights={})
        cw = capped_weights({v: w[v] for v in probs})
        fair = sum(cw[v] * probs[v] for v in probs)
        return dict(fair=fair, status=status, n=len(probs), detail=detail, weights=cw, devig=method)


def best_price(eq, market, line, side, ts_iso, participant=None, exclude=()):
    """Best bettable price (highest decimal / lowest implied) across venues at ts, excluding unbettable venues. Returns list sorted best-first."""
    rows = []
    three_way = market in ('f5_ml', '1h_ml', '1q_ml') or (market == 'ml' and getattr(eq, 'sport', 'mlb') in ('nfl', 'cfb'))
    if getattr(eq, 'sport', None) == 'soccer': three_way = False   # draw is its own side at every venue: the same bet everywhere   # tie is a loss on the exchange, a push at the book
    for (v, m, l, s, p), L in eq.idx.items():
        if m != market or l != line or s != side or p != participant or v in C.UNBETTABLE_VENUES['value'] or v in exclude: continue
        if three_way and v == 'Kalshi' and market != 'ml': continue      # not the same bet as the book price; the period ML tie rate is far too high to ignore
        if C.VENUE_CLASS.get(v) == 'reference': continue
        r = eq.latest(v, m, l, s, ts_iso, 90, p)
        if not r or r[5] is None: continue
        cost = r[5]
        if v == 'Kalshi' and r[7] is not None:
            import math
            cost = r[7] + math.ceil(C.KALSHI_TAKER_FEE['value'] * r[7] * (1 - r[7]) * 100) / 100
        rows.append(dict(venue=v, implied=r[5], cost=cost, american=r[10], cost_american=N.prob_to_american(cost), ts=r[0], limit=r[11], bid=r[6], ask=r[7], flags=r[9]))
    return sorted(rows, key=lambda x: x['cost'])
