#!/usr/bin/env python3
"""Pre-registered systems engine: every tracker run, for each game inside the fire window, evaluate the rules for its sport and the
first time a rule triggers write ONE paper fill at the best bettable price at that moment (BetMGM excluded, Kalshi fee included) with
rule_tag 'paper:<tag>', graded like any fill with CLV vs the ruler. State: data/state/system_fired.json (game x tag, never fires
twice). View: data/state/system_fires.json (games with triggers, fills, per-tag record, rule descriptions in DESC).
Rules and their sources: RULES / DESC below; audits in docs/betlabs_*.md and docs/exchange_signals_audit_2026-10-29.md.
Stacking: one bet per game per market x side. Publication gate per tag: 100 graded fills AND positive CLV."""
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
         'awfuldog': dict(market='spread', side='dog', stake=0.5), 'bounce15_1h': dict(market='1h_spread', side='dog', stake=0.5),
         # exchange signals (docs/exchange_signals_audit_2026-10-29.md): fired inside T-1.5h, at the exchange that shows the signal
         'xch_homedog_fade': dict(market='ml|spread', side='away', stake=0.5, sport='nfl,nba,cfb,nhl,mlb', venue='Novig'),
         'nba_momentum': dict(market='ml|spread|total', side='continuation', stake=0.5, sport='nba', venue='Novig|Kalshi'),
         # Bet Labs round 2 leans (docs/betlabs_segments_audit_2026-10-30.md), paper only
         'nhl_pl_fav_gap': dict(market='spread', side='fav', stake=0.5, sport='nhl'), 'nhl_pl_fav_strong_opp': dict(market='spread', side='fav', stake=0.5, sport='nhl'),
         'nhl_pl_dog_bigml': dict(market='spread', side='dog', stake=0.5, sport='nhl'),
         'nba_1h_under_hot_over': dict(market='1h_total', side='under', stake=0.5, sport='nba'),
         # Bet Labs round 3 watch tier (docs/betlabs_account_systems_audit_2026-10-30.md), paper only
         'nhl_early_home_fav_qual': dict(market='ml', side='home', stake=0.5, sport='nhl'), 'nba_under_good_home_over': dict(market='total', side='under', stake=0.5, sport='nba'),
         'cfb_road_dog_low_total': dict(market='spread', side='away', stake=0.5, sport='cfb')}
# Evidence per tag: Bet Labs train / holdout record (regular season, closing lines; holdout = 03/2021 on), positive holdout seasons, and a tier:
#   A = holdout z >= 2 with a mechanism (wind family); B = positive both halves, most seasons positive, z 1-2; C = lean (thin or z < 1).
# These are what the screen shows next to a fire. The forward record (W-L, ROI, CLV) is a diagnostic, not a gate: a rule the market does
# not price can keep winning with zero CLV, so nothing here waits for CLV before it is shown as a bet.
EVIDENCE = {'wind1014': dict(tier='A', train='533-376 all-time (2003-), +13.3%', hold='positive on both halves', seasons='5 of 6', src='docs/betlabs_nfl_audit_2026-10-25.md'),
            'wind1014_1h': dict(tier='A', train='403-300 all-time, +10.4%', hold='positive on both halves', seasons='4 of 6', src='docs/betlabs_nfl_audit_2026-10-25.md'),
            'cfb_wind14': dict(tier='A', train='555-402 all-time, +12%', hold='positive on both halves', seasons='5 of 6', src='docs/betlabs_cfb_audit_2026-10-29.md'),
            'vrest8_1h': dict(tier='B', train='454-357 all-time, +7.7%', hold='positive on both halves', seasons='5 of 6', src='docs/betlabs_nfl_audit_2026-10-25.md'),
            'mnf_1h': dict(tier='B', train='168-118 all-time, +12.3%', hold='positive on both halves', seasons='4 of 6', src='docs/betlabs_nfl_audit_2026-10-25.md'),
            'awfuldog': dict(tier='B', train='203-133', hold='51-31 (+17.2% all-time)', seasons='6 of 6 (n ~15 a season)', src='docs/betlabs_nfl_audit_2026-10-25.md'),
            'bounce15_1h': dict(tier='B', train='312-258', hold='117-80 (+7.5% all-time)', seasons='4 of 6', src='docs/betlabs_nfl_audit_2026-10-25.md'),
            'xch_homedog_fade': dict(tier='C', train='exchange audit, sparse tape', hold='+12% at the close, n 300', seasons='two months', src='docs/exchange_signals_audit_2026-10-29.md'),
            'nba_momentum': dict(tier='C', train='exchange audit, sparse tape', hold='continuation +4 to +6 pts', seasons='two months', src='docs/exchange_signals_audit_2026-10-29.md'),
            'nhl_pl_fav_gap': dict(tier='B', train='502, +17.4%', hold='196, +14.6%', seasons='5 of 7', src='docs/betlabs_segments_audit_2026-10-30.md'),
            'nhl_pl_fav_strong_opp': dict(tier='B', train='992, +11.9%', hold='405, +12.8%', seasons='5 of 7', src='docs/betlabs_segments_audit_2026-10-30.md'),
            'nhl_pl_dog_bigml': dict(tier='C', train='810, +6.0%', hold='310, +7.4%', seasons='4 of 7', src='docs/betlabs_segments_audit_2026-10-30.md'),
            'nba_1h_under_hot_over': dict(tier='C', train='508, +8.4%', hold='257, +6.1%', seasons='see audit', src='docs/betlabs_segments_audit_2026-10-30.md'),
            'nhl_early_home_fav_qual': dict(tier='B', train='1,459, +3.0%', hold='463, +7.2%', seasons='5 of 7', src='docs/betlabs_account_systems_audit_2026-10-30.md'),
            'nba_under_good_home_over': dict(tier='B', train='978, +10.9%', hold='344, +6.4%', seasons='5 of 6', src='docs/betlabs_account_systems_audit_2026-10-30.md'),
            'cfb_road_dog_low_total': dict(tier='B', train='645, +14.9%', hold='238, +7.3%', seasons='5 of 6', src='docs/betlabs_account_systems_audit_2026-10-30.md')}
# nhl_over_busy_goalie retired 10/30: positive in 2 of 7 seasons and the goalie-saves field thins to a handful of games after 2023.
DESC = {'wind1014': 'NFL outdoor, Open-Meteo sustained wind 10-14 mph at T-24h: full-game under', 'wind1014_1h': 'same wind band: first-half under',
        'cfb_wind14': 'CFB outdoor, wind 14+ mph at T-24h: full-game under', 'vrest8_1h': 'NFL visitor off 8-30 days: first-half under', 'mnf_1h': 'Monday night: first-half under',
        'awfuldog': 'NFL dog with season margin -13 or worse (2+ games): full-game spread', 'bounce15_1h': 'NFL dog whose last game lost ATS by 15+: first-half spread',
        'xch_homedog_fade': 'Novig home side two-sided at 20-35c inside T-90m: take the road side on Novig', 'nba_momentum': 'NBA exchange mid moved 3c+ since T-6h: continuation at that exchange',
        'nhl_pl_fav_gap': "NHL favorite -1.5 when the OPPONENT's win% is 22+ points higher than the favorite's (market rates the favorite above its record)", 'nhl_pl_fav_strong_opp': 'NHL favorite -1.5 when the opponent wins 66%+',
        'nhl_pl_dog_bigml': 'NHL dog +1.5 when the dog ML is +181 to +196', 'nba_1h_under_hot_over': 'NBA 1H under when the visitor has gone over 71%+ of the time',
        'nhl_early_home_fav_qual': 'NHL home favorite, game 24 or earlier, vs an opponent winning 51%+: moneyline', 'nba_under_good_home_over': 'NBA under: home team over 58%+, home 1-2 days off, visitor 1-3, total down 0.5+ from open',
        'cfb_road_dog_low_total': 'CFB conference game, road dog of 7+ with a total of 48 or less: road spread'}
LATE_H = (0.1, 1.5)   # exchange rules fire in the last 90 minutes (the audit priced them at the close)
WINDOW_H = tuple(float(x) for x in os.environ.get('SYSTEMS_WINDOW', '2,30').split(','))


def msw_latest(sport, event_id):
    """Latest MySportsWeather reading for the game (cross-check source; NWS/NBM data)."""
    p = os.path.join(ROOT, 'data', sport, 'weather', 'msw.jsonl'); last = None
    if os.path.exists(p):
        for l in open(p):
            try: r = json.loads(l)
            except Exception: continue
            if r.get('event_id') == event_id and r.get('wind_mph') is not None: last = r
    return last


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


def open_line(conn, ev, market):
    """The opening number for a total: AN_Open's first line, else the earliest line any book quoted."""
    r = conn.execute("SELECT line FROM ticks WHERE event_id=? AND market=? AND venue='AN_Open' AND line IS NOT NULL ORDER BY ts_utc LIMIT 1", (ev, market)).fetchone()
    if not r: r = conn.execute("SELECT line FROM ticks WHERE event_id=? AND market=? AND line IS NOT NULL AND venue NOT IN ('Kalshi','Novig','Polymarket') ORDER BY ts_utc LIMIT 1", (ev, market)).fetchone()
    return r[0] if r else None


def open_ml(conn, ev, side):
    """Opening American moneyline for a side: AN_Open first, else the earliest book quote."""
    r = conn.execute("SELECT price_american FROM ticks WHERE event_id=? AND market='ml' AND side=? AND venue='AN_Open' AND price_american IS NOT NULL ORDER BY ts_utc LIMIT 1", (ev, side)).fetchone()
    if not r: r = conn.execute("SELECT price_american FROM ticks WHERE event_id=? AND market='ml' AND side=? AND price_american IS NOT NULL AND venue NOT IN ('Kalshi','Novig','Polymarket') ORDER BY ts_utc LIMIT 1", (ev, side)).fetchone()
    return r[0] if r else None


def sched_rec(sport, ev):
    p = os.path.join(ROOT, 'data', sport, 'schedule.json'); s = SCHED_CACHE.get(sport)
    if s is None: s = SCHED_CACHE[sport] = json.load(open(p)) if os.path.exists(p) else {}
    return s.get(ev) or {}


SCHED_CACHE = {}


def public(conn, ev, market, side):
    r = conn.execute("SELECT extra FROM ticks WHERE event_id=? AND venue='AN_Consensus' AND market=? AND side=? AND extra IS NOT NULL ORDER BY ts_utc DESC LIMIT 1", (ev, market, side)).fetchone()
    return json.loads(r[0]) if r else {}


LEAN_TAGS = {'nhl_pl_fav_gap', 'nhl_pl_fav_strong_opp', 'nhl_pl_dog_bigml', 'nba_1h_under_hot_over', 'nhl_early_home_fav_qual', 'nba_under_good_home_over'}


def void_fill(fired, key, why):
    """Mark a flagged bet void (not graded, no P&L) and keep the record of why."""
    rec = fired[key]; rec['void'] = True; rec['void_why'] = why
    if rec.get('fill_id'):
        rows = FI.load()
        for r in rows:
            if r['fill_id'] == rec['fill_id'] and r.get('result') is None:
                r['result'] = 'void'; r['pnl_units'] = 0.0; r['note'] = (r.get('note') or '') + f' | VOID: {why}'
        FI.save(rows)
    print(f"[systems] voided {key}: {why}")


def paper_fill(conn, eq, ev, start, market, line, side, part, tag, stake, note, venue=None, min_h=None):
    ttk = (N.parse_ts(start) - NOW).total_seconds() / 3600
    if ttk < (WINDOW_H[0] if min_h is None else min_h): return None      # inside the last hours a new trigger is shown, not filled
    best = F.best_price(eq, market, line, side, NOW_S, part)
    if venue: best = [b for b in best if b['venue'] == venue]
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


# Fills written under a rule definition later found to be wrong are voided, graded or not, so they never count in that rule's record.
# nhl_pl_fav_gap ran backwards (favorite better than opponent) until the 10/31 fix; every fill before it is void.
RETRO_VOID = {'nhl_pl_fav_gap': ('2026-10-31T08:00:00Z', "fired under the reversed definition (favorite's win% above the opponent's); Bet Labs' rule is the opposite")}


def retro_void(fired):
    rows = FI.load(); ch = 0
    for r in rows:
        t = (r.get('rule_tag') or '').replace('paper:', '')
        if t in RETRO_VOID and r['ts_utc'] < RETRO_VOID[t][0] and r.get('result') != 'void':
            r['result'] = 'void'; r['pnl_units'] = 0.0; r['note'] = (r.get('note') or '') + ' | VOID: ' + RETRO_VOID[t][1]; ch += 1
    if ch: FI.save(rows)
    for k, rec in fired.items():
        t = k.split(':')[1] if ':' in k else ''
        if t in RETRO_VOID and (rec.get('ts') or '') < RETRO_VOID[t][0] and not rec.get('void'):
            rec['void'] = True; rec['void_why'] = RETRO_VOID[t][1]
    if ch: print(f"[systems] retro-voided {ch} fills")


def main():
    conn = sqlite3.connect(DB)
    fired = json.load(open(FIRED)) if os.path.exists(FIRED) else {}
    retro_void(fired)
    fires_now = []; view_games = []
    for ev, start, away, home in conn.execute("SELECT event_id, start_utc, away, home FROM events WHERE sport='nfl' ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (0 < ttk <= WINDOW_H[1]): continue      # visible until kickoff; new fills only inside the window (paper_fill checks)
        eq = F.EventQuotes(conn, ev); trig = {}
        wx = weather_t24(ev)
        pv = SEA.profile('nfl', away, st); ph = SEA.profile('nfl', home, st)
        sp_line, sp_n = main_line(eq, 'spread', home)       # home line
        dog = None
        if sp_line is not None and sp_line != 0: dog = 'home' if sp_line > 0 else 'away'
        et_dow = (st + dt.timedelta(hours=-5 if st >= dt.datetime(2026, 11, 1, 6, tzinfo=dt.timezone.utc) else -4)).strftime('%A')
        # --- rules
        msw = msw_latest('nfl', ev)
        wr = round(wx['wind_mph']) if wx and wx.get('wind_mph') is not None else None     # Bet Labs' wind is whole mph (checked on its 2026 picks 10/31)
        if wx and not wx.get('indoor') and 10 <= wr <= 14:
            trig['wind1014'] = f"forecast {wx['wind_mph']} mph (gust {wx.get('gust_mph')}) at T-{wx['hours_to_kickoff']:.0f}h, {wx.get('temp_f')}F" + (f"; MSW {msw['wind_mph']} mph {msw.get('wind_dir') or ''} gust {msw.get('gust_mph')}" if msw else '; MSW n/a')
            if wr <= 13: trig['wind1014_1h'] = trig['wind1014']      # the tested first-half screen is 10-13 mph, not 10-14
        elif msw and not (wx or {}).get('indoor') and 10 <= round(msw['wind_mph']) <= 14 and wx and wx.get('wind_mph') is not None:
            trig['wind_msw_only'] = f"MSW {msw['wind_mph']} mph in band but Open-Meteo {wx['wind_mph']} mph is not (flag only; the rule fires on Open-Meteo)"
        vdays = (N.et_date(st) - N.et_date(N.parse_ts(pv['last_start']))).days if pv.get('games') and pv.get('last_start') else None   # calendar days, as Bet Labs counts
        if vdays is not None and 8 <= vdays <= 30:
            trig['vrest8_1h'] = f"{away} off {vdays} days"
        if et_dow == 'Monday': trig['mnf_1h'] = 'Monday night'
        if dog:
            dp = pv if dog == 'away' else ph; dteam = away if dog == 'away' else home
            if dp.get('games', 0) >= 1 and dp.get('margin_avg') is not None and dp['margin_avg'] <= -13:     # Bet Labs: no minimum (4 of its 8 2026 picks were week 2)
                trig['awfuldog'] = f"{dteam} season margin {dp['margin_avg']:+.1f} over {dp['games']} games, dog {('+' if sp_line > 0 else '')}{sp_line if dog == 'home' else -sp_line}"
            if dp.get('last_ats_margin') is not None and dp['last_ats_margin'] <= -15:
                trig['bounce15_1h'] = f"{dteam} previous game ATS margin {dp['last_ats_margin']:+.1f}"
        if 'awfuldog' in trig and 'bounce15_1h' in trig: trig['awfuldog'] += ' (skipped: bounce15_1h takes the game)'; skip_awful = True
        else: skip_awful = False
        game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=sp_line, dog=dog, triggers=trig,
                    wind=wx and dict(mph=wx['wind_mph'], gust=wx.get('gust_mph'), temp_f=wx.get('temp_f'), at_h=wx['hours_to_kickoff'],
                                     msw=msw and dict(mph=msw['wind_mph'], gust=msw.get('gust_mph'), dir=msw.get('wind_dir'), rain=msw.get('rain_pct'))), fills=[])
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
        if not (0 < ttk <= WINDOW_H[1]): continue      # visible until kickoff; new fills only inside the window (paper_fill checks)
        wx = weather_t24(ev, WX_CFB); msw = msw_latest('cfb', ev)
        windy = wx and not wx.get('indoor') and wx.get('wind_mph') is not None and round(wx['wind_mph']) >= 14
        msw_only = (not windy) and msw and not (wx or {}).get('indoor') and round(msw.get('wind_mph') or 0) >= 14 and wx and wx.get('wind_mph') is not None
        eq = F.EventQuotes(conn, ev)
        sp_line, _n = main_line(eq, 'spread', home); tl, _n2 = main_line(eq, 'total', None); rec_s = sched_rec('cfb', ev)
        rdlt = sp_line is not None and sp_line <= -7 and tl is not None and tl <= 48 and rec_s.get('conf')
        if not windy and not rdlt and not msw_only: continue
        game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=sp_line, dog=('away' if sp_line and sp_line < 0 else None), triggers={},
                    wind=(dict(mph=wx['wind_mph'], gust=wx.get('gust_mph'), temp_f=wx.get('temp_f'), at_h=wx['hours_to_kickoff']) if wx else None), fills=[], sport='cfb')
        if rdlt:
            why2 = f"conference game, {away} +{-sp_line} on the road, total {tl}"; game['triggers']['cfb_road_dog_low_total'] = why2; key2 = f"{ev}:cfb_road_dog_low_total"
            if key2 in fired: game['fills'].append(fired[key2])
            else:
                row = paper_fill(conn, eq, ev, start, 'spread', -sp_line, 'away', away, 'cfb_road_dog_low_total', 0.5, why2)
                if row:
                    rec_ = dict(tag='cfb_road_dog_low_total', fill_id=row['fill_id'], ts=NOW_S, market='spread', side='away', line=-sp_line, venue=row['venue'], price=row['price_american'],
                                fair=row['fair_at_fill'], edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why2)
                    fired[key2] = rec_; game['fills'].append(rec_); fires_now.append(dict(game=f"{away}@{home}", **rec_))
        if msw_only: game['triggers']['wind_msw_only'] = f"MySportsWeather {msw['wind_mph']} mph at kickoff but Open-Meteo {wx['wind_mph']} mph (the rule fires on Open-Meteo)"
        if not windy: view_games.append(game); continue
        why = f"forecast {wx['wind_mph']} mph (gust {wx.get('gust_mph')}) at T-{wx['hours_to_kickoff']:.0f}h, {wx.get('temp_f')}F" + (f"; MSW {msw['wind_mph']} mph {msw.get('wind_dir') or ''}" if msw else '; MSW n/a')
        game['triggers']['cfb_wind14'] = why
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
    # NHL and NBA leans from the segment audit: one fill per game per tag, inside the normal window.
    for ev, sport, start, away, home in conn.execute("SELECT event_id, sport, start_utc, away, home FROM events WHERE sport IN ('nhl','nba') ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (0 < ttk <= WINDOW_H[1]): continue      # visible until kickoff; new fills only inside the window (paper_fill checks)
        ph, pa = SEA.profile(sport, home, st), SEA.profile(sport, away, st)
        if ph.get('games', 0) < 1 or pa.get('games', 0) < 1: continue      # Bet Labs applies no minimum (its picks start in a team's 2nd game); 8 was ours
        eq = F.EventQuotes(conn, ev); ml_h = eq.fair('ml', None, 'home', NOW_S, home); ml_a = eq.fair('ml', None, 'away', NOW_S, away)
        p_home = ml_h.get('fair') if ml_h else None
        if p_home is None: continue
        fav, dog = (home, away) if p_home >= 0.5 else (away, home); pf, pd = (ph, pa) if fav == home else (pa, ph); fav_side = 'home' if fav == home else 'away'
        trig = {}
        if sport == 'nhl':
            # Bet Labs definitions (checked against its past picks 10/31): Win % = wins / games played (OT and shootout losses are losses),
            # each team's value truncated to a whole percent; "Win % Difference" = OPPONENT's win% minus the team's. So this rule backs a
            # favorite whose opponent has the much better record (the market rates the favorite above its record), not the reverse.
            wf, wd = int(100 * pf['win_pct']), int(100 * pd['win_pct']); rec_ = lambda p_: f"{p_['wins']}-{p_['games'] - p_['wins']}"
            if wd - wf >= 22: trig['nhl_pl_fav_gap'] = ('spread', fav_side, f"favorite {fav} is {wf}% ({rec_(pf)}) but opponent {dog} is {wd}% ({rec_(pd)}): opponent's win% higher by {wd - wf} pts")
            if wd >= 66: trig['nhl_pl_fav_strong_opp'] = ('spread', fav_side, f"opponent {dog} wins {wd}% ({rec_(pd)}); favorite {fav} -1.5 against a strong team")
            dog_side = 'away' if fav_side == 'home' else 'home'; am = open_ml(conn, ev, dog_side)     # Bet Labs filters on the OPENING moneyline
            if am is not None and 181 <= am <= 196: trig['nhl_pl_dog_bigml'] = ('spread', dog_side, f"{dog} opened +{am:.0f} on the moneyline: +1.5 on a big dog")
            if fav == home and ph['games'] + 1 <= 24 and int(100 * pd['win_pct']) >= 51:
                trig['nhl_early_home_fav_qual'] = ('ml', 'home', f"home favorite, game {ph['games'] + 1} of the season, opponent {away} wins {int(100 * pd['win_pct'])}% ({pd['wins']}-{pd['games'] - pd['wins']})")
        else:
            if int(100 * (pa.get('over_pct') or 0)) >= 71: trig['nba_1h_under_hot_over'] = ('1h_total', 'under', f"visitor {away} over rate {100 * pa['over_pct']:.0f}% this season; 1H under (regression lean)")
            # Bet Labs "days between games" = calendar-day gap (back-to-back = 1); checked on its 2026 picks 10/31
            h_off = (N.et_date(st) - N.et_date(N.parse_ts(ph['last_start']))).days if ph.get('last_start') else None
            a_off = (N.et_date(st) - N.et_date(N.parse_ts(pa['last_start']))).days if pa.get('last_start') else None
            if int(100 * (ph.get('over_pct') or 0)) >= 58 and h_off is not None and a_off is not None and 1 <= h_off <= 2 and 1 <= a_off <= 3:
                tl, _n = main_line(eq, 'total', None); op = open_line(conn, ev, 'total')
                if tl is not None and op is not None and op - tl >= 0.5:
                    trig['nba_under_good_home_over'] = ('total', 'under', f"home {home} over rate {int(100 * ph['over_pct'])}%, days since last game: home {h_off}, visitor {a_off}; total {op} -> {tl}")
        # A fired bet whose trigger no longer holds on corrected inputs (e.g. a late-arriving result changed a record) is voided before kickoff.
        for key_ in [k for k in fired if k.startswith(ev + ':') and k.split(':')[1] in LEAN_TAGS and k.split(':')[1] not in trig and not fired[k].get('void')]:
            void_fill(fired, key_, f"trigger no longer holds on current season records ({NOW_S})")
        if not trig: continue
        game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=None, dog=dog, triggers={k: v[2] for k, v in trig.items()}, fills=[], sport=sport)
        for tag, (market, side, why) in trig.items():
            key = f"{ev}:{tag}"
            if key in fired and not fired[key].get('void'): game['fills'].append(fired[key]); continue
            line = None; part = None
            if market == 'spread':
                line = -1.5 if side == fav_side else 1.5; part = home if side == 'home' else away
            elif market == 'ml':
                part = home if side == 'home' else away      # moneyline: no number, the team is the participant
            else:
                line, _n = main_line(eq, market, None)
                if line is None: continue
            row = paper_fill(conn, eq, ev, start, market, line, side, part, tag, 0.5, why)
            if not row: continue
            rec_ = dict(tag=tag, fill_id=row['fill_id'], ts=NOW_S, market=market, side=side, line=line, venue=row['venue'], price=row['price_american'], fair=row['fair_at_fill'],
                        edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why)
            fired[key] = rec_; game['fills'].append(rec_); fires_now.append(dict(game=f"{away}@{home}", **rec_))
        view_games.append(game)
    # Exchange rules, inside T-1.5h. One fill per game per rule; stacking across rules allowed only on different market x side.
    def xmid(eq, venue, market, line, side, part, ts):
        q = eq.latest(venue, market, line, side, ts, 90, part)
        if not q or q[6] is None or q[7] is None or (q[7] - q[6]) > 0.04: return None
        return (q[6] + q[7]) / 2
    for ev, sport, start, away, home in conn.execute("SELECT event_id, sport, start_utc, away, home FROM events WHERE sport IN ('nfl','nba','cfb','nhl','mlb') ORDER BY start_utc").fetchall():
        st = N.parse_ts(start); ttk = (st - NOW).total_seconds() / 3600
        if not (LATE_H[0] <= ttk <= LATE_H[1]): continue
        eq = F.EventQuotes(conn, ev); game = None
        def fire(tag, market, line, side, part, venue, why, stake=0.5):
            nonlocal game
            key = f"{ev}:{tag}:{market}"
            if key in fired: return
            row = paper_fill(conn, eq, ev, start, market, line, side, part, tag, stake, why, venue=venue, min_h=LATE_H[0])
            if not row: return
            rec_ = dict(tag=tag, fill_id=row['fill_id'], ts=NOW_S, market=market, side=side, line=line, venue=row['venue'], price=row['price_american'], fair=row['fair_at_fill'],
                        edge_pts=(round(100 * (row['fair_at_fill'] - row['implied']), 2) if row['fair_at_fill'] is not None else None), why=why)
            fired[key] = rec_; fires_now.append(dict(game=f"{away}@{home}", **rec_))
            if game is None:
                game = dict(event_id=ev, away=away, home=home, start_utc=start, hours_to_kickoff=round(ttk, 1), spread_home=None, dog=None, triggers={}, fills=[], sport=sport); view_games.append(game)
            game['triggers'][tag] = why; game['fills'].append(rec_)
        # xch_homedog_fade: Novig home side two-sided at 20-35c -> buy the away side on Novig (section 9 of the audit: +12% at the close, z -2.5 on the home side)
        for market in ('ml', 'spread'):
            line = None
            if market == 'spread':
                line, _n = main_line(eq, 'spread', home)
                if line is None: continue
            ph = xmid(eq, 'Novig', market, line, 'home', home, NOW_S)
            if ph is not None and 0.20 <= ph <= 0.35:
                fire('xch_homedog_fade', market, (-line if line is not None else None), 'away', away, 'Novig', f"Novig home side mid {ph:.3f} inside T-{ttk:.1f}h; audit band 20-35c")
                break
        # nba_momentum: exchange two-sided mid moved >= 3c since T-6h -> continuation at that exchange
        if sport == 'nba':
            t6 = N.iso(st - dt.timedelta(hours=6))
            for market in ('ml', 'spread', 'total'):
                line = None; part_h, part_a = home, away
                if market == 'spread': line, _n = main_line(eq, 'spread', home)
                elif market == 'total': line, _n = main_line(eq, 'total', None); part_h = part_a = None
                if market != 'ml' and line is None: continue
                side_h = 'home' if market != 'total' else 'over'
                for venue in ('Novig', 'Kalshi'):
                    p_now = xmid(eq, venue, market, line, side_h, part_h, NOW_S); p_6 = xmid(eq, venue, market, line, side_h, part_h, t6)
                    if p_now is None or p_6 is None or abs(p_now - p_6) < 0.03: continue
                    up = p_now > p_6
                    side = side_h if up else ('away' if market != 'total' else 'under'); part = (part_h if up else part_a) if market != 'total' else None
                    fire('nba_momentum', market, (line if (up or market == 'total') else -line) if line is not None else None, side, part, venue,
                         f"{venue} {market} mid {p_6:.3f} at T-6h -> {p_now:.3f} now ({100 * (p_now - p_6):+.1f}c); continuation (audit section 3, NBA only)")
                    break
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
    for g in view_games:
        r_ = sched_rec(g.get('sport', 'nfl'), g['event_id']); g['away_name'] = (r_.get('away_team') or {}).get('displayName') or g['away']; g['home_name'] = (r_.get('home_team') or {}).get('displayName') or g['home']
        g.setdefault('sport', 'nfl')
        g['hours_to_kickoff'] = round((N.parse_ts(g['start_utc']) - NOW).total_seconds() / 3600, 1)
        fired_tags = {f['tag'] for f in g.get('fills', [])}
        if g['hours_to_kickoff'] < WINDOW_H[0]:      # triggers that first appeared inside the last hours never became bets; do not show them as such
            g['triggers'] = {t: w for t, w in g['triggers'].items() if t in fired_tags or t.startswith(('xch_', 'nba_momentum'))}
        g['fills'] = [f for f in g.get('fills', []) if not f.get('void')]
        live = [f for f in g.get('fills', []) if f.get('fill_id') and not f.get('stacked')]
        if live:
            eq = F.EventQuotes(conn, g['event_id'])
            for f in live:
                part = None if f['market'].endswith('total') else (g['home'] if f['side'] == 'home' else g['away'])
                try: best = F.best_price(eq, f['market'], f['line'], f['side'], NOW_S, part)
                except Exception: best = []
                f['now'] = dict(venue=best[0]['venue'], price=N.prob_to_american(best[0]['cost'])) if best else None
    view_games = [g for g in view_games if g['triggers']]
    json.dump(dict(built=NOW_S, window_h=WINDOW_H, rules={k: dict(v, tag=k, desc=DESC.get(k, ''), evidence=EVIDENCE.get(k)) for k, v in RULES.items()}, games=view_games, fired_now=fires_now, record=dict(rec)),
              open(VIEW, 'w'), default=str, separators=(',', ':'))
    print(f"[systems] {len(view_games)} games with triggers in the {WINDOW_H[0]}-{WINDOW_H[1]}h window; {len(fires_now)} new paper fills; tags on file {dict((k, v['n']) for k, v in rec.items())}")
    conn.close()


if __name__ == '__main__':
    main()
