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
SPORTS = ('nfl', 'nba', 'nhl', 'cfb', 'cbb', 'soccer', 'mlb', 'wnba', 'tennis')
VENUES = ('Novig', 'Kalshi', 'FD', 'Caesars', 'DK')
KFEE = 0.07; STEP = 600; MAX_AGE = 45 * 60
NOW = dt.datetime.now(dt.timezone.utc)


def ts(s): return dt.datetime.fromisoformat(s.replace(' ', 'T').replace('Z', '+00:00').replace('+00:00:00', '+00:00')) if s else None
def implied(a): return 100 / (a + 100) if a > 0 else -a / (-a + 100)
def size_units(cat): return 0.5 if cat in ('system A', 'system B', 'sharp A') else 0.25


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
        for sub in ('ticks', 'ticks5'):
            for d in days:
                f = os.path.join(ROOT, 'data', sport, sub, f'{d}.jsonl.gz')
                if not os.path.exists(f): continue
                try:
                    for l in gzip.open(f, 'rt'):
                        if '"event_id"' not in l: continue
                        r = json.loads(l)
                        if r.get('event_id') not in events or r.get('venue') not in VENUES: continue
                        c = cost(r)
                        if c is None or not 0 < c < 1: continue
                        line = r.get('line'); line = None if line is None else float(line)
                        self.s[(r['event_id'], r['market'], r['side'], line)][r['venue']].append((ts(r['ts']).timestamp(), c))
                except (EOFError, OSError): pass
        for k in self.s:
            for v in self.s[k]: self.s[k][v].sort()

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
                         start=r['start_utc'], market=r['market'], side=r['side'], line=r.get('line'), flagged=r['ts_utc'], venue=r['venue'], price=r['implied'], won=won))
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
            best, close = path(T, key, t0, st)
            if best: b.update(best=round(best[0], 4), best_venue=best[2], best_at=dt.datetime.fromtimestamp(best[1], dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                              best_after_min=round((best[1] - t0) / 60), best_before_start_min=round((st - best[1]) / 60))
            if close:
                b['close_board'] = close; cb = {v: c for v, c in close.items() if v != 'DK'} or close
                b['close'] = min(cb.values()); b['clv'] = round(100 * (b['close'] - b['price']), 2)
    # raw ticks roll off after 10 days (sharp/rolloff.py): keep a bet's path from the last build when the tape is gone
    old = {b.get('id'): b for b in (json.load(open(OUT)).get('rows') or [])} if os.path.exists(OUT) else {}
    for b in bets:
        o = old.get(b['id']) or {}
        for k in ('best', 'best_venue', 'best_at', 'best_after_min', 'best_before_start_min', 'close_board', 'close', 'clv'):
            if b.get(k) is None and o.get(k) is not None: b[k] = o[k]
    for b in bets:
        b['bet_type'] = b['market'].replace('1s_ml', 'set1_ml')
        b['size'] = size_units(b['cat']); b['units'] = units(b['price'], b['won'], b['size'])
        b['lead_h'] = round((ts(b['start']) - ts(b['flagged'])).total_seconds() / 3600, 1)
    # ---- summaries
    def summ(L):
        G_ = [b for b in L if b['won'] is not None]; cl = [b['clv'] for b in L if b.get('clv') is not None]
        gain = [100 * (b['price'] - b['best']) for b in L if b.get('best') is not None]
        later = [b for b in L if b.get('best') is not None and 100 * (b['price'] - b['best']) >= 1]
        return dict(n=len(L), graded=len(G_), w=sum(1 for b in G_ if b['won'] == 1), l=sum(1 for b in G_ if b['won'] == 0), p=sum(1 for b in G_ if b['won'] == 0.5),
                    units=round(sum(b['units'] or 0 for b in G_), 2), clv=round(sum(cl) / len(cl), 2) if cl else None, clv_n=len(cl),
                    best_gain=round(sum(gain) / len(gain), 2) if gain else None, better_later=len(later), lead_h=round(sum(b['lead_h'] for b in L) / len(L), 1) if L else None)
    groups = collections.defaultdict(list)
    for b in bets:
        for k in ((b['cat'], 'all', 'all'), (b['cat'], b['sport'] or '?', 'all'), (b['cat'], b['sport'] or '?', b['bet_type']), ('all', b['sport'] or '?', b['bet_type']), ('all', b['sport'] or '?', 'all'), ('all', 'all', 'all')):
            groups['|'.join(k)].append(b)
    out = dict(built=NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), venues=list(VENUES),
               summary={k: summ(v) for k, v in sorted(groups.items())},
               rows=sorted(bets, key=lambda b: b['start'], reverse=True))
    json.dump(out, open(OUT, 'w'), separators=(',', ':'), default=str)
    s = out['summary'].get('all|all|all', {})
    print(f"[bet_log] {len(bets)} flagged bets ({s.get('graded')} graded, {s.get('units')}u, CLV {s.get('clv')} on {s.get('clv_n')}); {sum(1 for b in bets if b.get('best') is not None)} with a price path")


if __name__ == '__main__':
    main()
