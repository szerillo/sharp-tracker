#!/usr/bin/env python3
"""11/27 (Kirk, next steps): did every Bet Labs listing on a screen the tool BETS FROM THE LIST reach the tool?

Since 11/24 the wind rules, and since 11/27 cbb_under_good_over_drop, bet only games on Sean's Bet Labs list. If a listed game never
matches a tool game (a name the matcher misses, home and visitor swapped at a neutral site, as with Fresno State v South Alabama on 11/27),
the bet silently never happens. sharp/audit.py calls unmatched() every run and shows the misses as a warning on the board's audit banner.
Name matching follows sharp/systems.py (_bnm / _bsame), in either home/visitor order."""
import datetime as dt

ET = __import__('zoneinfo').ZoneInfo('America/New_York')
# Bet Labs screen -> the rule that bets straight from its list (sharp/systems.py WIND_SCREENS and the 11/27 CBB gate)
LIST_RULES = {1772775: ('nfl', 'wind1014'), 769171: ('nfl', 'wind1014_1h'), 1783043: ('cfb', 'cfb_wind14'), 1792184: ('cbb', 'cbb_under_good_over_drop')}


def _nm(x): return ''.join(c for c in (x or '').lower().replace('los angeles', 'la').replace('international', 'intl').replace('state', 'st') if c.isalnum() or c == ' ').split()


def same(a, b):
    x, y = _nm(a), _nm(b)
    if not x or not y or x[0] != y[0]: return False
    n = min(len(x), len(y)); L = x if len(x) >= len(y) else y
    return x[:n] == y[:n] and (len(L) == n or L[n] not in ('st', 'tech', 'a', 'am', 'intl', 'southern', 'northern'))


def game_matches(p, g):
    two = lambda x: _nm(x)[:2]
    def m(a, h): return ((same(p['away'], a) and same(p['home'], h)) or (same(p['away'], a) and two(p['home']) == two(h))
                         or (same(p['home'], h) and two(p['away']) == two(a)))
    a, h = g.get('away_name') or g.get('away'), g.get('home_name') or g.get('home')
    return m(a, h) or m(h, a)


def logged(g, rule):
    """11/28: the rule already logged a row for this game (a fill, or a row left untracked because two rules conflict, Sean's 11/18 rule)."""
    return any((r or {}).get('tag') == rule for r in (g.get('fills') or []) + (g.get('untracked') or []))


def started(g, now):
    try: return dt.datetime.fromisoformat(str(g.get('start_utc') or g.get('start')).replace('Z', '+00:00')) <= now
    except ValueError: return False


def unmatched(picks, games, today=None, now=None):
    """Listings for today (ET) on the list-betting screens that no tool game carries a trigger for. Returns [(rule, 'away @ home', why)].
    11/28: a listing whose rule already logged a row for the game, or whose game has started (triggers clear at kickoff), is not a miss
    (UCF @ Colorado 11/28: logged 11/27, untracked by the conflict with cfb_day_over, flagged after kickoff)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    today = today or now.astimezone(ET).date().isoformat()
    out = []
    for p in picks or []:
        if p.get('sid') not in LIST_RULES or p.get('date') != today: continue
        sport, rule = LIST_RULES[p['sid']]
        G = [g for g in games or [] if g.get('sport', sport) == sport and game_matches(p, g)]
        if not G: out.append((rule, f"{p['away']} @ {p['home']}", 'not on the board: no tool game matched (names, or the game is missing from the schedule)')); continue
        if not any(rule in (g.get('triggers') or {}) or logged(g, rule) or started(g, now) for g in G):
            out.append((rule, f"{p['away']} @ {p['home']}", 'matched a tool game, but the rule did not trigger'))
    return out
