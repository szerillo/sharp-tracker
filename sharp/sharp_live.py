#!/usr/bin/env python3
"""Sharp-account flags for the Today page (Sean, 11/2: follow the sharps, but do not flag 100 games; tell me if a sharp comes in on the
other side after I have a position).

Input: data/polymarket/sharp_fills.jsonl (loggers/poly_sharps.py, every 5 minutes). Per upcoming game market:
  FLAG    the first moment a top-50 account (or, from 11/2, a top-200 account also in that sport's own top 50: the strongest tier in
          docs/flow_volume_2026-11-02.md) bets a side, or two different top-200 accounts are on the same side, with no top-200
          account on the other side yet. Backtest (holdout Sep 1 to Nov 1, entry 5 minutes after, data/research/sharp_accounts_filters.json):
          about 8-9 games a day, +0.96 pts CLV (z 7.4) vs +0.78 for every single top-200 bet (19 games a day).
  OTHER SIDE  after a flag, a top-200 account bets the other side. Backtest: holding still averaged +1.12 pts CLV vs +0.89 locked in by
          getting out at the mid 5 minutes later (194 cases), so the default is to hold; the row says so, with the current price to get out.
  Accounts on both sides before any flag: no flag (head-to-head at T-15m had no edge either way).
Price: the current best ask on the flagged side from the Polymarket CLOB (what a follower pays now), next to what the sharps paid.
Kalshi veto (moneylines): if Kalshi's price has moved 4+ points against the flagged side since its first two-sided price
(data/state/flow_live.json moves), the row is marked "Kalshi against" and moved below the others. Backtest (top 200, 5 minutes behind,
moneylines since September): CLV +1.10 when Kalshi had moved 4+ the same way, +0.99 under 4, +0.24 when 4+ against.
Paper log: data/state/sharp_paper.jsonl, one row per flag at the ask when first seen; graded after the game on the result (Gamma) and on
CLV vs Polymarket's two-sided close (public trade tape). Writes data/state/sharp_accounts.json.
Usage: python3 sharp/sharp_live.py"""
import os, sys, re, json, time, math, datetime as dt, urllib.request, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'loggers'))
import polydata                      # Data API v2 (v1 retired 11/2)
FILLS = os.path.join(ROOT, 'data', 'polymarket', 'sharp_fills.jsonl'); OUT = os.path.join(ROOT, 'data', 'state', 'sharp_accounts.json')
PAPER = os.path.join(ROOT, 'data', 'state', 'sharp_paper.jsonl'); META = os.path.join(ROOT, 'data', 'polymarket', '_sharp_meta.json')
NOW = time.time(); TOP_RANK = 50; TWO = 2
LEAGUES = {'nfl', 'nba', 'nhl', 'cfb', 'cbb', 'mlb', 'wnba', 'epl', 'bun', 'ucl', 'mls'}   # cbb added 11/2: top 200 +0.39 CLV (z 3.0) on 2025-26


def g(u):
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=20))
        except Exception: time.sleep(1 + i)
    return None


def epoch(s): return dt.datetime.fromisoformat(s.replace(' ', 'T').replace('+00', '+00:00').replace('Z', '+00:00')).timestamp()


def bet_text(r, side):
    """'Celtics -6.5', 'Over 220.5', 'Magic ML'. Polymarket spread questions name the team the line belongs to: 'Spread: Celtics (-6.5)'."""
    if set(r.get('outcomes') or []) == {'Yes', 'No'}: return f"{(r.get('q') or '').rstrip('?')}: {side}"     # soccer: one yes/no market per team
    if r['mtype'] == 'ml': return f"{side} ML"
    if r['mtype'] == 'total': return f"{side} {r['line']}"
    m = re.search(r':\s*(.+?)\s*\(([-+]?[\d.]+)\)', r.get('q') or '')
    if m:
        team, ln = m.group(1), float(m.group(2))
        mine = ln if side.lower().startswith(team.lower()[:6]) or team.lower().startswith(side.lower()[:6]) else -ln
        return f"{side} {mine:+g}"
    return f"{side} spread {r.get('line')}"


def ask(token):
    b = g(f"https://clob.polymarket.com/book?token_id={token}") or {}
    a = [float(x['price']) for x in b.get('asks') or []]
    return min(a) if a else None


def close_mid(cond, start):
    """Polymarket two-sided close from the public tape (last yes-buy and last no-buy before the start, within 2h), yes = outcome 0."""
    T = polydata.trades(condition=cond, limit=500, max_rows=1500)
    meta = json.load(open(META)).get(cond) or {}; o0 = (meta.get('outcomes') or [None])[0]
    ly = ln = None
    for t in sorted(T, key=lambda t: t['timestamp']):
        if t['timestamp'] >= start: break
        p = float(t['price']); is0 = t.get('outcome') == o0; buy = t['side'] == 'BUY'
        py = p if is0 else 1 - p
        if is0 == buy: ly = (t['timestamp'], py)
        else: ln = (t['timestamp'], py)
    if ly and ln and abs(ly[0] - ln[0]) <= 7200: return (ly[1] + ln[1]) / 2
    return None


ALERTS = os.path.join(ROOT, 'data', 'state', 'sharp_alerts.json')


def ntfy(title, msg, click, tags, prio='high'):
    topic = os.environ.get('NTFY_TOPIC')
    if not topic: return False
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=msg.encode('utf-8'), method='POST',
                                 headers={'Title': title.encode('ascii', 'ignore').decode(), 'Click': click, 'Tags': tags, 'Priority': prio})
    try: urllib.request.urlopen(req, timeout=15); return True
    except Exception as e: print(f"[sharp_live] ntfy failed: {e}"); return False


def alerts(rows):
    """Phone push (ntfy, topic in the NTFY_TOPIC repo secret) when a flag first appears, and when a sharp later takes the other side of
    a flag already pushed. Not pushed: flags with Kalshi 4+ against, or when the ask is already 5c+ above what the sharps paid (edge gone).
    The first run with no state only records what is on the board, so nothing old is pushed."""
    first = not os.path.exists(ALERTS)
    st = json.load(open(ALERTS)) if not first else {}
    c = lambda x: f"{100 * x:.0f}c" if x is not None else '?'
    for r in rows:
        if epoch(r['start']) <= NOW: continue
        s = st.setdefault(r['cond'], {})
        when = dt.datetime.fromisoformat(r['start'].replace('Z', '+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).strftime('%a %-I:%M %p ET')
        if 'flag' not in s:
            ok = r['status'] == 'live' and not r.get('kalshi_against') and not r.get('conflict') and r.get('ask') is not None and r['ask'] - r['paid'] <= 0.05
            if ok and not first:
                ntfy(f"Sharp: {r['bet']}", f"{r['title']} · {when}\n{r['n_accounts']} sharp account{'s' if r['n_accounts'] != 1 else ''}, ${r['usd']:,}\nSharps paid {c(r['paid'])}, ask now {c(r['ask'])}",
                     r['link'], 'chart_with_upwards_trend')
            s['flag'] = int(NOW) if ok or first else None
            if not (ok or first): del st[r['cond']]
        if first and r['status'] == 'other side': s['other'] = int(NOW)       # already on the board: record, do not push
        elif r['status'] == 'other side' and s.get('flag') and 'other' not in s:
            o = r['other']
            if not first:
                ntfy(f"Sharp on the other side: {r['bet']}", f"{r['title']} · {when}\n{o['n_accounts']} sharp account{'s' if o['n_accounts'] != 1 else ''} bet the other side (${o['usd']:,}). "
                     f"Backtest: holding still beat getting out (+1.12 vs +0.89 pts).{' Sell about ' + c(r['exit_bid']) + '.' if r.get('exit_bid') else ''}",
                     r['link'], 'warning', 'default')
            s['other'] = int(NOW)
    st = {k: v for k, v in st.items() if v.get('flag') and NOW - v['flag'] < 10 * 86400}
    json.dump(st, open(ALERTS, 'w'))


def by_event(F):
    """Top-200 Polymarket accounts per upcoming game x full-game market, keyed 'event_id|market' with our schedule's sides
    (home / away / over / under): {side: {n, best_rank, usd}}. Matched by start time (within 15 min) and team nicknames in the
    Polymarket title; soccer yes/no markets are not mapped. Used by the system-bet tags and the watch's third evidence family."""
    sched = {}
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'cbb', 'soccer', 'mlb', 'wnba'):
        try: sched.update(json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json'))))
        except Exception: pass
    nick = lambda t: (((t or {}).get('shortDisplayName') or (t or {}).get('name') or (t or {}).get('displayName') or '').lower().split() or [''])[-1]
    idx = collections.defaultdict(list)
    for cond, L in F.items(): idx[round(epoch(L[0]['start']) / 900)].append(L)
    out = {}
    for ev, e in sched.items():
        try: st = epoch(e['start'].replace('Z', '+00:00'))
        except Exception: continue
        if st <= NOW: continue
        a, h = nick(e.get('away_team')), nick(e.get('home_team'))
        if not a or not h: continue
        D = collections.defaultdict(lambda: collections.defaultdict(dict))
        for k in (round(st / 900) - 1, round(st / 900), round(st / 900) + 1):
            for L in idx.get(k, []):
                r0 = L[0]; t = (r0.get('title') or '').lower()
                if abs(epoch(r0['start']) - st) > 900 or a not in t or h not in t: continue
                for r in L:
                    b = r['bet'].lower()
                    side = b if r0['mtype'] == 'total' else ('away' if a in b else 'home' if h in b else None)
                    if side in ('home', 'away', 'over', 'under'): D[r0['mtype']][side].setdefault(r['w'], r)
        for mk, sides in D.items():
            out[f"{ev}|{mk}"] = {sd: dict(n=len(W), best_rank=min(r['rank'] for r in W.values()), usd=round(sum(r['usd'] for r in W.values()))) for sd, W in sides.items()}
    return out


def sys_tags(BE):
    """Tag each open system bet (data/state/system_fired.json) with the top-200 accounts on the same full-game market (by_event):
    with (same side) / against (other side). First-half and period bets are tagged against the full-game market. The first time a bet is tagged, the tag is appended to
    data/state/sys_sharp_tags.jsonl so agreement can be graded against the bet's result later."""
    try: fired = json.load(open(os.path.join(ROOT, 'data', 'state', 'system_fired.json')))
    except Exception: return {}
    OTH = {'home': 'away', 'away': 'home', 'over': 'under', 'under': 'over'}; out = {}
    for k, f in fired.items():
        base = re.sub(r'^(1h|1q|1p)_', '', f['market'])          # 11/2 (Sean): first-half / period leans are tagged against the full-game market
        if not f.get('fill_id') or f.get('void') or base not in ('ml', 'spread', 'total'): continue
        x = BE.get(f"{k.split(':')[0]}|{base}")
        if not x: continue
        w, ag = x.get(f['side']), x.get(OTH.get(f['side']))
        if w or ag: out[k] = {'with': w, 'against': ag}
    log = os.path.join(ROOT, 'data', 'state', 'sys_sharp_tags.jsonl'); seen = set()
    if os.path.exists(log):
        for l in open(log):
            try: seen.add(json.loads(l)['key'])
            except Exception: pass
    with open(log, 'a') as fh:
        for k, v in out.items():
            if k not in seen: fh.write(json.dumps(dict(key=k, fill_id=fired[k]['fill_id'], ts=dt.datetime.fromtimestamp(NOW, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), **v)) + '\n')
    return out


def conflicts(rows):
    """Mark flags that any other live watch signal opposes (Sean, 11/2: only no-conflict flags): big vs small money, a Kalshi 4+ move
    or a Kalshi bet-back on the other side of the same game x market (data/state/flow_live.json). Such flags are not pushed and show
    as Mixed on the page."""
    try: FLv = json.load(open(os.path.join(ROOT, 'data', 'state', 'flow_live.json')))
    except Exception: return
    opp = collections.defaultdict(set)
    for r in FLv.get('rows') or []:
        if r.get('divergent') and r.get('show') is not False: opp[(r['event_id'], r['market'])].add(('big money', r['big_side']))
    for r in FLv.get('moves') or []: opp[(r['event_id'], r['market'])].add(('Kalshi move', r['side']))
    for r in (FLv.get('steam') or {}).get('rows') or []:
        if r.get('state') == 'reversed': opp[(r['event_id'], r['market'])].add(('Kalshi bet back', r['rev_side']))
    for r in rows:
        if not r.get('event_id'): continue
        against = sorted({k for k, sd in opp.get((r['event_id'], r['mtype']), ()) if sd != r.get('side_std')})
        if against: r['conflict'] = against
        r['money_with'] = ('big money', r.get('side_std')) in opp.get((r['event_id'], r['mtype']), ())
    for r in rows: r['grade'] = grade(r)


def grade(r):
    """Sean, 11/2 (sharp/account_count.py): A = a sport-proven account flagged it, or big money is on the same side (0.5u); B = any other
    flag (0.25u); 'watch' = an NBA flag with a single account (-0.39 CLV on 31 in the walk-forward test)."""
    if r.get('sport') == 'nba' and (r.get('n_accounts') or 0) < 2: return 'watch'
    return 'A' if r.get('proven') or r.get('money_with') else 'B'


SIZE = 0.25        # sharp signals: grade A 0.5u, B and NBA-single watch rows 0.25u (Sean, 11/2); to WIN over 50%, to RISK on plus money
GSIZE = {'A': 0.5}


def units(p, won, size=SIZE):
    """Result in Sean's units for a bet at implied cost p: size to win when p > 0.5, size to risk otherwise."""
    if p > 0.5: return round(size if won else -size * p / (1 - p), 3)
    return round(size * (1 - p) / p if won else -size, 3)


_BOARD = {}
def venue_prices(r, board=None):
    """Best bettable price per venue (Novig, Kalshi with fee, FD, Caesars, DK) for the flagged side, from the tracker's latest board
    (data/state/dashboard_<sport>.json, rebuilt every run of the tracker; its prices can be up to ~30 minutes old). None when the game or
    the exact line is not on the board (Polymarket soccer yes/no markets never match: 'No' is a double chance)."""
    sp, ev, side = r.get('sport'), r.get('event_id'), r.get('side_std')
    if not (sp and ev and side): return None
    B = board
    if B is None:
        if sp not in _BOARD:
            try: _BOARD[sp] = json.load(open(os.path.join(ROOT, 'data', 'state', f'dashboard_{sp}.json')))
            except Exception: _BOARD[sp] = {}
        B = _BOARD[sp]
    num = re.findall(r'[-+]?\d+(?:\.\d+)?', r.get('bet') or '')
    line = float(num[-1]) if r.get('mtype') in ('spread', 'total') and num else None
    for g_ in B.get('board') or []:
        if str(g_.get('event_id')) != str(ev): continue
        for m in g_.get('markets') or []:
            if m['market'] != r.get('mtype') or m['side'] != side or (line is not None and m.get('line') != line) or (line is None and m.get('line') not in (None, 0)): continue
            q = {b['venue']: round(b['cost'], 4) for b in m.get('best') or []}
            if not q: return None
            return dict(at=g_.get('priced_at') or B.get('built'), fair=m.get('fair'), q=q)
    return None


def map_rows(rows):
    """Attach our schedule's game (event_id, sport, teams, start) and side (home / away / over / under) to each flag, the same way
    by_event matches (start within 15 min, team nicknames in the Polymarket title), so the page can merge flags into the watch."""
    sched = {}
    for sp in ('nfl', 'nba', 'nhl', 'cfb', 'cbb', 'soccer', 'mlb', 'wnba'):
        try:
            for k, v in json.load(open(os.path.join(ROOT, 'data', sp, 'schedule.json'))).items(): sched[k] = dict(v, sport=sp)
        except Exception: pass
    nick = lambda t: (((t or {}).get('shortDisplayName') or (t or {}).get('name') or (t or {}).get('displayName') or '').lower().split() or [''])[-1]
    for r in rows:
        st = epoch(r['start']); t = (r.get('title') or '').lower(); b = (r.get('side') or '').lower()
        for ev, e in sched.items():
            try:
                if abs(epoch(e['start'].replace('Z', '+00:00')) - st) > 900: continue
            except Exception: continue
            a, h = nick(e.get('away_team')), nick(e.get('home_team'))
            if not a or not h or a not in t or h not in t: continue
            side = b if r['mtype'] == 'total' else ('away' if a in b else 'home' if h in b else None)
            if side not in ('home', 'away', 'over', 'under'): break
            r.update(event_id=ev, sport=e['sport'], league=e.get('league'), away=e['away'], home=e['home'], away_name=(e.get('away_team') or {}).get('displayName'),
                     home_name=(e.get('home_team') or {}).get('displayName'), game_start=e['start'], side_std=side)
            break


def main():
    if not os.path.exists(FILLS): print('[sharp_live] no fills yet'); return
    F = collections.defaultdict(list)
    for l in open(FILLS):
        try: r = json.loads(l)
        except Exception: continue
        if r.get('rank') and epoch(r['start']) > NOW - 6 * 3600 and (r.get('slug') or '').split('-')[0] in LEAGUES: F[r['cond']].append(r)   # specialists (rank None) are logged only
    meta = json.load(open(META)) if os.path.exists(META) else {}
    paper = [json.loads(l) for l in open(PAPER)] if os.path.exists(PAPER) else []
    logged = {p['cond'] for p in paper}
    KM = []
    try: KM = [m for m in json.load(open(os.path.join(ROOT, 'data', 'state', 'flow_live.json'))).get('moves') or [] if m['market'] == 'ml']
    except Exception: pass
    def kalshi_against(title, side, start):
        """Kalshi moneyline mover for this game (same start within 15 min, team names match), moved 4+ against `side`."""
        nm = lambda x: (x or '').lower().split()[-1] if x else ''
        for k in KM:
            if abs(epoch(k['start']) - start) > 900: continue
            teams = {nm(k.get('away_name')): 'away', nm(k.get('home_name')): 'home'}
            if not any(t and t in (title or '').lower() for t in teams): continue
            mine = next((v for t, v in teams.items() if t and t in side.lower()), None)
            if mine and k['side'] != mine: return k
        return None
    rows = []
    for cond, L in F.items():
        L.sort(key=lambda r: r['ts']); m = meta.get(cond) or {}; start = epoch(L[0]['start'])
        sides = collections.defaultdict(dict); flag = None
        for r in L:
            if flag is None:
                sides[r['bet']].setdefault(r['w'], r)
                other = [s for s in sides if s != r['bet']]
                if any(sides[s] for s in other): continue          # sharps already on both sides: no flag
                accts = sides[r['bet']]
                if r['rank'] <= TOP_RANK or r.get('both') or len(accts) >= TWO: flag = dict(side=r['bet'], ts=r['ts'], trigger=r)
            else:
                sides[r['bet']].setdefault(r['w'], r)
        if not flag: continue
        side = flag['side']; opp = [r for r in L if r['bet'] != side and r['ts'] > flag['ts']]
        with_ = list(sides[side].values()); paid = sum(r['price'] * r['usd'] for r in with_) / sum(r['usd'] for r in with_)
        outs = L[0]['outcomes']; tok = (m.get('tokens') or [None, None])[outs.index(side)] if side in outs else None
        a = ask(tok) if tok and start > NOW else None
        row = dict(cond=cond, slug=L[0]['slug'], title=L[0].get('title'), mtype=L[0]['mtype'], start=dt.datetime.fromtimestamp(start, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                   bet=bet_text(L[0], side), side=side, flagged=dt.datetime.fromtimestamp(flag['ts'], dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                   why=(f"{len(sides[side])} top-200 accounts" if len(sides[side]) >= 2 else 'a top-50 account' if flag['trigger']['rank'] <= TOP_RANK
                        else 'a top-200 account also in this sport\'s top 50'),
                   # 11/2 grades (sharp/account_count.py): a sport-proven account (top 200 and its sport's top 50) is the strongest trigger
                   proven=any(r.get('both') for r in with_) or bool(flag['trigger'].get('both')),
                   trigger=('proven' if flag['trigger'].get('both') else 'top50' if flag['trigger']['rank'] <= TOP_RANK and len(sides[side]) < TWO else 'two'),
                   n_accounts=len(sides[side]), best_rank=min(r['rank'] for r in with_), usd=round(sum(r['usd'] for r in with_)), paid=round(paid, 3), ask=a,
                   status='other side' if opp else 'live', link=f"https://polymarket.us/event/{L[0]['slug']}",
                   other=dict(n_accounts=len({r['w'] for r in opp}), best_rank=min(r['rank'] for r in opp), usd=round(sum(r['usd'] for r in opp)),
                              first=dt.datetime.fromtimestamp(opp[0]['ts'], dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')) if opp else None)
        if opp:
            otok = (m.get('tokens') or [None, None])[outs.index(opp[0]['bet'])] if opp[0]['bet'] in outs else None
            row['exit_bid'] = round(1 - ask(otok), 3) if otok and start > NOW and ask(otok) else None   # selling our side = buying the other side's ask
        ka = kalshi_against(row['title'], side, start) if row['mtype'] == 'ml' and side not in ('Yes', 'No') else None
        row['kalshi_against'] = dict(move=ka['move'], now=ka.get('now'), state=ka.get('state')) if ka else None
        row['logged'] = cond in logged
        rows.append(row)
        if cond not in logged and start > NOW and a and not opp:      # a flag first seen after a sharp already took the other side is not logged
            map_rows([row]); conflicts([row])
            paper.append(dict(grade=row.get('grade'), venues=venue_prices(row), event_id=row.get('event_id'), cond=cond, slug=row['slug'], bet=row['bet'], side=side, mtype=row['mtype'], start=row['start'], flagged=row['flagged'],
                              logged=dt.datetime.fromtimestamp(NOW, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), price=a, why=row['why'], best_rank=row['best_rank'],
                              kalshi_against=bool(row['kalshi_against'])))
            logged.add(cond); row['logged'] = True
    # grade paper rows after the game: result from Gamma, CLV vs Polymarket's two-sided close
    for p in paper:
        if p.get('result') or epoch(p['start']) > NOW - 3 * 3600: continue
        M = g(f"https://gamma-api.polymarket.com/markets?condition_ids={p['cond']}&closed=true") or []   # Gamma leaves settled markets out unless closed=true (the paper record never graded)
        if not M: continue
        try: outs = json.loads(M[0]['outcomes']); px = [float(x) for x in json.loads(M[0].get('outcomePrices') or '[]')]
        except Exception: continue
        if sorted(px) != [0.0, 1.0]: continue
        won = px[outs.index(p['side'])] == 1.0; p['result'] = 'W' if won else 'L'
        p['pnl'] = round((1 - p['price']) / p['price'] if won else -1.0, 3)          # 1u to risk at the Polymarket ask (kept for the research)
        sz = GSIZE.get(p.get('grade'), SIZE); p['u'] = units(p['price'], won, sz)                                                 # Sean's sizing (0.25u to win / to risk) at the Polymarket ask
        vq = {k: v for k, v in ((p.get('venues') or {}).get('q') or {}).items() if k != 'DK'}      # where Sean bets (DK excluded: low limits)
        if vq: bv = min(vq, key=vq.get); p['best_venue'] = bv; p['best_cost'] = vq[bv]; p['u_venue'] = units(vq[bv], won, sz)
        cm = close_mid(p['cond'], epoch(p['start']))
        if cm is not None:
            q = cm if outs.index(p['side']) == 0 else 1 - cm; p['clv'] = round(100 * (q - p['price']), 2)
            if vq: p['clv_venue'] = round(100 * (q - p['best_cost']), 2)
    with open(PAPER, 'w') as f:
        for p in paper: f.write(json.dumps(p) + '\n')
    G_ = [p for p in paper if p.get('result')]; GV = [p for p in G_ if 'u_venue' in p]
    avg = lambda L, k: round(sum(p[k] for p in L if k in p) / max(1, sum(k in p for p in L)), 2) if any(k in p for p in L) else None
    rec = dict(n=len(G_), won=sum(p['result'] == 'W' for p in G_), units=round(sum(p.get('u', units(p['price'], p['result'] == 'W', GSIZE.get(p.get('grade'), SIZE))) for p in G_), 2),
               by_grade={k: dict(n=len(L_), won=sum(p['result'] == 'W' for p in L_), units=round(sum(p.get('u', 0) for p in L_), 2), clv=avg(L_, 'clv'))
                         for k in ('A', 'B', 'watch') for L_ in [[p for p in G_ if p.get('grade') == k]] if L_},
               units_1u=round(sum(p['pnl'] for p in G_), 2), clv=avg(G_, 'clv'),
               # the same flags at the best price at Novig / Kalshi / FD / Caesars when first seen: can the edge be captured where Sean bets?
               n_venue=len(GV), units_venue=round(sum(p['u_venue'] for p in GV), 2), clv_venue=avg(GV, 'clv_venue'), clv_poly_same=avg(GV, 'clv'))
    map_rows(rows)
    conflicts(rows)
    for r in rows: r['books'] = venue_prices(r) if r['status'] == 'live' else None     # best Novig / Kalshi / FD / Caesars / DK now (11/2)
    alerts(rows)
    BE = by_event(F)
    rows.sort(key=lambda r: (r['status'] != 'live' or bool(r.get('kalshi_against')), r['start']))
    json.dump(dict(built=dt.datetime.fromtimestamp(NOW, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), rows=[r for r in rows if epoch(r['start']) > NOW],
                   record=rec, sys_tags=sys_tags(BE), by_event=BE, rule=f'top-{TOP_RANK} account, a top-200 account that is also in the sport top 50, or {TWO}+ top-200 accounts on one side, none on the other'), open(OUT, 'w'), indent=1)
    print(f"[sharp_live] {sum(epoch(r['start']) > NOW for r in rows)} upcoming flagged markets ({sum(r['status'] == 'other side' for r in rows)} with a sharp on the other side since); paper {rec}")


if __name__ == '__main__':
    main()
