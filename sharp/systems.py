#!/usr/bin/env python3
"""Pre-registered systems engine (docs/betlabs_nfl_audit_2026-10-25.md §7). Every tracker run: for each NFL game inside the fire window
(6h-30h before kickoff) evaluate the rules; the first time a rule triggers write ONE paper fill at the best bettable price at that
moment (BetMGM excluded, Kalshi fee included) with rule_tag 'paper:<tag>', so it is graded like any fill with CLV vs the ruler.
State: data/state/system_fired.json (game x tag, never fires twice). View: data/state/system_fires.json (fires today + per-tag record).

Rules (NFL only until another sport has had its own audit):
  wind1014      outdoor, Open-Meteo forecast 10-14 mph sustained at kickoff (the row nearest T-24h)   -> FG under   1.0u
  wind1014_1h   same                                                                                    -> 1H under   0.5u
  vrest8_1h     visitor off >= 8 days                                                                   -> 1H under   0.5u
  mnf_1h        Monday night (ET)                                                                       -> 1H under   0.5u
  awfuldog      dog (consensus spread), season margin avg <= -13 after >= 2 games                        -> FG spread  0.5u
  bounce15_1h   dog, previous game ATS margin <= -15 (DK close via ESPN)                                 -> 1H spread  0.5u
  sharp10       dog, AN consensus money% - ticket% >= 10 (flag only, no fill)
Stacking: one bet per game per outlet market; awfuldog + bounce15_1h on the same game -> the 1H spread only.
Publication gate per tag: 100 graded fills AND positive CLV."""
import os, sys, json, uuid, sqlite3, datetime as dt, collections, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from sharp import norm as N, fair as F, constants as C, season as SEA, fills as FI

ROOT = os.path.abspath(os.path.join(HERE, '..')); SD = os.path.join(ROOT, 'data', 'state'); DB = os.path.join(SD, 'sharp.sqlite')
FIRED = os.path.join(SD, 'system_fired.json'); VIEW = os.path.join(SD, 'system_fires.json'); WX = os.path.join(ROOT, 'data', 'nfl', 'weather', 'weather.jsonl')
WX_CFB = os.path.join(ROOT, 'data', 'cfb', 'weather', 'weather.jsonl')
NOW = dt.datetime.now(dt.timezone.utc); NOW_S = N.iso(NOW)
RULES = {'wind1014': dict(market='total', side='under', stake=1.0), 'wind1014_1h': dict(market='1h_total', side='under', stake=0.5),
         'cfb_wind14': dict(market='total', side='under', stake=1.0, sport='cfb'),
         'vrest8_1h': dict(market='1h_total', side='under', stake=0.5), 'mnf_1h': dict(market='1h_total', side='under', stake=0.5),
         'awfuldog': dict(market='spread', side='dog', stake=0.5), 'bounce15_1h': dict(market='1h_spread', side='dog', stake=0.5)}
WINDOW_H = tuple(float(x) for x in os.environ.get('SYSTEMS_WINDOW', '2,30').split(','))


def weather_t24(event_id, path=None):
    """The forecast row for this game nearest 24h before kickoff (18-30h tolerance), else the latest row."""
    rows = []; path = path or WX
    if os.path.exists(path):
        for l in open(path):
            try: r = json.loads(l)
            except Exception: continue
            if r.get('espn_id') == event_id and r.get('wind_mph') is not None: rows.append(r)
    if not rows: return None
    t24 = [r for r in rows if 18 <= r['hours_to_kickoff'] <= 30]
    return min(t24, key=lambda r: abs(r['hours_to_kickoff'] - 24)) if t24 else rows[-1]


def main_line(eq, market, home):
    """(line_home, n_venues) of the most-quoted home-side line for a spread market; for totals the most-quoted line."""
    nv = collections.Counter()
    for (m, l, p), vs in eq.keys.items():
        if m != market or l is None: continue
        if market.endswith('spread') and p != home: continue
        nv[l] += len(vs)
    if not nv: return None, 0
    l = max(nv, key=lambda k: (nv[k], -abs(k))); return l, nv[l]


def public(conn, ev, market, side):
    r = conn.execute("SELECT extra FROM ticks WHERE event_id=? AND venue='AN_Consensus' AND market=? AND side=? AND extra IS NOT NULL ORDER BY ts_utc DESC LIMIT 1", (ev, market, side)).fetchone()
    return json.loads(r[0]) if r else {}


def paper_fill(conn, eq, ev, start, market, line, side, part, tag, stake, note):
    best = F.best_price(eq, market, line, side, NOW_S, part)
    if not best: return None
    b = best[0]; fr = eq.fair(market, line, side, NOW_S, part)
    imp = b['cost']; price = N.prob_to_american(imp)
    row = dict(fill_id=uuid.uuid4().hex[:12], ts_utc=NOW_S, event_id=ev, start_utc=start, market=market, mclass='game', participant=part, player_name=None,
               line=line, side=side, venue=b['venue'], price_american=price, price_decimal=round(1 / imp, 4), implied=round(imp, 5), stake=stake,
               rule_tag=f'paper:{tag}', fair_at_fill=round(fr['fair'], 5) if fr['fair'] is not None else None, fair_at_fill_status=fr['status'],
               fair_at_fill_detail={k: (round(v['p'], 4) if v['p'] is not None else v['why']) for k, v in fr['detail'].items()},
               fair_weights={k: round(v, 3) for k, v in fr['weights'].items()}, late=0, note=note, paper=1)
    rows = FI.load(); rows.append(row); FI.save(rows)
    return row


def main():
    conn = sqlite3.connect(DB)
    fired = json.load(open(FIRED)) if os.path.exists(FIRED) else {}
    fires_now = []; view_games = []
    for ev, start, away, home in conn.execute("SELECT event_id, start_utc, away, home FROM events WHERE sport='nfl' ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (WINDOW_H[0] <= ttk <= WINDOW_H[1]): continue
        eq = F.EventQuotes(conn, ev); trig = {}
        wx = weather_t24(ev)
        pv = SEA.profile('nfl', away, st); ph = SEA.profile('nfl', home, st)
        sp_line, sp_n = main_line(eq, 'spread', home)       # home line
        dog = None
        if sp_line is not None and sp_line != 0: dog = 'home' if sp_line > 0 else 'away'
        et_dow = (st + dt.timedelta(hours=-5 if st >= dt.datetime(2026, 11, 1, 6, tzinfo=dt.timezone.utc) else -4)).strftime('%A')
        # --- rules
        if wx and not wx.get('indoor') and 10 <= wx['wind_mph'] <= 14:
            trig['wind1014'] = f"forecast {wx['wind_mph']} mph (gust {wx.get('gust_mph')}) at T-{wx['hours_to_kickoff']:.0f}h, {wx.get('temp_f')}F"
            trig['wind1014_1h'] = trig['wind1014']
        if pv.get('games') and pv.get('days_since_last') is not None and pv['days_since_last'] >= 8:
            trig['vrest8_1h'] = f"{away} off {pv['days_since_last']:.0f} days"
        if et_dow == 'Monday': trig['mnf_1h'] = 'Monday night'
        if dog:
            dp = pv if dog == 'away' else ph; dteam = away if dog == 'away' else home
            if dp.get('games', 0) >= 2 and dp.get('margin_avg') is not None and dp['margin_avg'] <= -13:
                trig['awfuldog'] = f"{dteam} season margin {dp['margin_avg']:+.1f} over {dp['games']} games, dog {('+' if sp_line > 0 else '')}{sp_line if dog == 'home' else -sp_line}"
            if dp.get('last_ats_margin') is not None and dp['last_ats_margin'] <= -15:
                trig['bounce15_1h'] = f"{dteam} previous game ATS margin {dp['last_ats_margin']:+.1f}"
            pub = public(conn, ev, 'spread', dog)
            if pub.get('money_pct') is not None and pub.get('tickets_pct') is not None and pub['money_pct'] - pub['tickets_pct'] >= 10:
                trig['sharp10'] = f"{dteam} money {pub['money_pct']}% vs tickets {pub['tickets_pct']}%"
        if 'awfuldog' in trig and 'bounce15_1h' in trig: trig['awfuldog'] += ' (skipped: bounce15_1h takes the game)'; skip_awful = True
        else: skip_awful = False
        game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=sp_line, dog=dog, triggers=trig,
                    wind=wx and dict(mph=wx['wind_mph'], gust=wx.get('gust_mph'), temp_f=wx.get('temp_f'), at_h=wx['hours_to_kickoff']), fills=[])
        taken = {(f['market'], f['side']) for k, f in fired.items() if k.startswith(ev + ':') and f.get('fill_id')}   # one bet per game per market x side
        for tag in [t for t in ('wind1014', 'wind1014_1h', 'vrest8_1h', 'mnf_1h', 'awfuldog', 'bounce15_1h') if t in trig]:   # priority order
            why = trig[tag]
            if tag == 'awfuldog' and skip_awful: continue
            key = f"{ev}:{tag}"
            if key in fired: game['fills'].append(fired[key]); continue
            r = RULES[tag]; market = r['market']
            if r['side'] == 'dog':
                side = dog; part = away if dog == 'away' else home
                line = (sp_line if dog == 'home' else -sp_line) if market == 'spread' else None
                if market == '1h_spread':
                    hl, hn = main_line(eq, '1h_spread', home)
                    if hl is None: continue
                    line = hl if dog == 'home' else -hl
            else:
                side = r['side']; part = None; line, n = main_line(eq, market, home)
                if line is None: continue
            if (market, side) in taken:
                fired[key] = dict(tag=tag, stacked=True, market=market, side=side, why=why + ' (same bet already taken by a higher-priority rule)'); game['fills'].append(fired[key]); continue
            row = paper_fill(conn, eq, ev, start, market, line, side, part, tag, r['stake'], why)
            if not row: continue
            taken.add((market, side))
            rec = dict(tag=tag, fill_id=row['fill_id'], ts=NOW_S, market=market, side=side, line=line, venue=row['venue'], price=row['price_american'],
                       fair=row['fair_at_fill'], edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why)
            fired[key] = rec; game['fills'].append(rec); fires_now.append(dict(game=f"{away}@{home}", **rec))
        if trig: view_games.append(game)
    # CFB: wind >= 14 mph -> under (docs/betlabs_cfb_audit_2026-10-29.md). Only rule audited for CFB.
    for ev, start, away, home in conn.execute("SELECT event_id, start_utc, away, home FROM events WHERE sport='cfb' ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (WINDOW_H[0] <= ttk <= WINDOW_H[1]): continue
        wx = weather_t24(ev, WX_CFB)
        if not wx or wx.get('indoor') or wx.get('wind_mph') is None or wx['wind_mph'] < 14: continue
        eq = F.EventQuotes(conn, ev); why = f"forecast {wx['wind_mph']} mph (gust {wx.get('gust_mph')}) at T-{wx['hours_to_kickoff']:.0f}h, {wx.get('temp_f')}F"
        game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=None, dog=None, triggers={'cfb_wind14': why},
                    wind=dict(mph=wx['wind_mph'], gust=wx.get('gust_mph'), temp_f=wx.get('temp_f'), at_h=wx['hours_to_kickoff']), fills=[], sport='cfb')
        key = f"{ev}:cfb_wind14"
        if key in fired: game['fills'].append(fired[key])
        else:
            line, n = main_line(eq, 'total', home)
            if line is not None:
                row = paper_fill(conn, eq, ev, start, 'total', line, 'under', None, 'cfb_wind14', 1.0, why)
                if row:
                    rec_ = dict(tag='cfb_wind14', fill_id=row['fill_id'], ts=NOW_S, market='total', side='under', line=line, venue=row['venue'], price=row['price_american'],
                                fair=row['fair_at_fill'], edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why)
                    fired[key] = rec_; game['fills'].append(rec_); fires_now.append(dict(game=f"{away}@{home}", **rec_))
        view_games.append(game)
    json.dump(fired, open(FIRED, 'w'), indent=0)
    # per-tag forward record from the ledger
    rec = collections.defaultdict(lambda: dict(n=0, graded=0, w=0, l=0, p=0, pnl=0.0, clv=[], gate=100))
    for f in FI.load():
        t = (f.get('rule_tag') or '')
        if not t.startswith('paper:'): continue
        s = rec[t[6:]]; s['n'] += 1
        if f.get('result') in ('W', 'L', 'P'):
            s['graded'] += 1; s[{'W': 'w', 'L': 'l', 'P': 'p'}[f['result']]] += 1; s['pnl'] += f.get('pnl_units') or 0
            if f.get('fair_at_close') is not None: s['clv'].append(100 * (f['fair_at_close'] - f['implied']))
    for s in rec.values():
        s['clv_avg'] = round(sum(s['clv']) / len(s['clv']), 2) if s['clv'] else None; s['n_clv'] = len(s['clv']); del s['clv']; s['pnl'] = round(s['pnl'], 3)
        s['published'] = bool(s['graded'] >= s['gate'] and (s['clv_avg'] or 0) > 0)
    json.dump(dict(built=NOW_S, window_h=WINDOW_H, rules={k: dict(v, tag=k) for k, v in RULES.items()}, games=view_games, fired_now=fires_now, record=dict(rec)),
              open(VIEW, 'w'), default=str, separators=(',', ':'))
    print(f"[systems] {len(view_games)} games with triggers in the {WINDOW_H[0]}-{WINDOW_H[1]}h window; {len(fires_now)} new paper fills; tags on file {dict((k, v['n']) for k, v in rec.items())}")
    conn.close()


if __name__ == '__main__':
    main()
