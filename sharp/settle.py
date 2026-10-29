"""Settlement rules per market, written before the first dispute (spec §10). outcome() -> 1 win, 0 loss, None push, 'void' no grade."""
import json


def outcome(market, line, side, participant, res, venue=None, event=None):
    """res: results row dict (home_score, away_score, f5_home, f5_away, rfi, players); event: (away, home)."""
    if not res or res.get('status') != 'final': return 'void'
    hs, as_ = res.get('home_score'), res.get('away_score')
    if hs is None or as_ is None: return 'void'
    f5h, f5a = res.get('f5_home'), res.get('f5_away')
    away, home = (event or (None, None)); sport = res.get('sport') or ((res.get('players') or {}).get('_sport'))

    def ou(value):
        if value is None or line is None: return 'void'
        if value == line: return None
        return int((value > line) == (side == 'over'))

    # registry sports: 1h_ / 1q_ prefixes map onto the period scores; 'spread' behaves like 'rl'
    players_j = res.get('players') or {}
    if isinstance(players_j, str):
        try: players_j = json.loads(players_j)
        except Exception: players_j = {}
    periods = players_j.get('_periods') or {}
    if market.startswith(('1h_', '1q_', '1p_')):
        pre, base = market[:3], market[3:]
        if pre == '1h_': ph, pa = f5h, f5a
        else: ph, pa = periods.get(pre + 'home'), periods.get(pre + 'away')
        if pre == '1p_' and base == 'ml' and ph is not None and ph == pa: return 0   # three-way period ML everywhere: a tie loses
        if sport == 'soccer' and base == 'ml' and ph is not None:
            if side == 'draw': return int(ph == pa)
            if ph == pa: return 0
        if ph is None or pa is None: return 'void'
        if base == 'ml':
            if ph == pa: return 0 if venue == 'Kalshi' else None
            return int((ph > pa) == (side == 'home'))
        if base == 'spread':
            if line is None: return 'void'
            margin = (ph - pa) if side == 'home' else (pa - ph)
            if margin + line == 0: return None
            return int(margin + line > 0)
        if base == 'total': return ou(ph + pa)
        if base == 'tt_home': return ou(ph)
        if base == 'tt_away': return ou(pa)
        return 'void'
    if market == 'spread': market = 'rl'
    if sport == 'mma':
        if market == 'ml': return int((hs > as_) == (side == 'home'))
        if market == 'total':
            r = (res.get('players') or {}).get('_rounds')
            if r is None or line is None: return 'void'
            if abs(r - line) < 1e-9: return None
            return int((r > line) == (side == 'over'))
        return 'void'
    if market == 'ml':
        if side == 'draw': return int(hs == as_)
        if hs == as_: return 0 if sport == 'soccer' else None     # soccer ML is three-way: the draw beats both sides
        return int((hs > as_) == (side == 'home'))
    if market == 'f5_ml':
        if f5h is None: return 'void'
        if f5h == f5a: return 0 if venue == 'Kalshi' else None      # Kalshi F5 is three-way (tie is its own ticker); books push
        return int((f5h > f5a) == (side == 'home'))
    if market in ('rl', 'f5_rl'):
        if line is None: return 'void'
        h, a = (hs, as_) if market == 'rl' else (f5h, f5a)
        if h is None: return 'void'
        margin = (h - a) if side == 'home' else (a - h)
        if abs(line * 4 - round(line * 4)) < 1e-6 and abs(line * 2 - round(line * 2)) > 1e-6: return 'void'   # quarter-goal Asian lines split the stake; not graded
        if margin + line == 0: return None
        return int(margin + line > 0)
    if market == 'total': return ou(hs + as_)
    if market == 'f5_total': return ou(None if f5h is None else f5h + f5a)
    if market == 'tt_home': return ou(hs)
    if market == 'tt_away': return ou(as_)
    if market == 'f5_tt_home': return ou(f5h)
    if market == 'f5_tt_away': return ou(f5a)
    if market == 'rfi': return ou(res.get('rfi'))
    if market.startswith('prop_'):
        stat = market[5:]
        players = res.get('players') or {}
        if isinstance(players, str): players = json.loads(players)
        p = players.get(participant)
        if not p or p.get('played') == 0: return 'void'   # did not appear (DNP void, matches book rules)
        v = p.get(stat)
        if v is None: return 'void'
        if stat in ('K', 'OUTS', 'HA', 'BBA', 'ER') and not p.get('started'): return 'void'   # pitcher props void if not the starter
        return ou(v)
    return 'void'


def pnl(result, implied, stake=1.0):
    """Units won/lost for `stake` units risked at a price with implied cost `implied` (books: 1/decimal; exchanges: ask incl. fee)."""
    if result == 'void' or result is None: return 0.0
    if result == 1: return stake * (1 - implied) / implied
    return -stake
