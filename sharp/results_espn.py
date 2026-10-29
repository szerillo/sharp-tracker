"""Results for the registry sports from the ESPN summary endpoint: final score, 1H / 1Q scores (stored in the f5_* columns and the
players json under '_periods'), and per-player box stats keyed by player_key with the canonical stat codes used by the prop markets."""
import json, time, urllib.request
from sharp import norm as N
from sharp import sports as SP


def g(u, tries=4):
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60))
        except Exception: time.sleep(1.5 * (i + 1))
    return {}


def _num(x):
    try: return float(x)
    except Exception: return None


def _split(x, i):
    try: return float(str(x).replace('/', '-').split('-')[i])
    except Exception: return None


def parse_players(sport, box):
    players = {}
    for tp in box.get('players', []):
        team = tp.get('team', {}).get('abbreviation')
        for cat in tp.get('statistics', []):
            keys = cat.get('keys') or []
            for a in cat.get('athletes', []):
                name = (a.get('athlete') or {}).get('displayName'); key = N.player_key(name)
                if not key or a.get('didNotPlay'): continue
                st = dict(zip(keys, a.get('stats') or [])); row = players.setdefault(key, dict(name=name, team=team))
                if sport in ('nfl', 'cfb'):
                    if cat['name'] == 'passing':
                        row.update(PASSYDS=_num(st.get('passingYards')), PASSTD=_num(st.get('passingTouchdowns')), INT=_num(st.get('interceptions')),
                                   PASSCOMP=_split(st.get('completions/passingAttempts'), 0), PASSATT=_split(st.get('completions/passingAttempts'), 1))
                    elif cat['name'] == 'rushing':
                        row.update(RUSHYDS=_num(st.get('rushingYards')), RUSHATT=_num(st.get('rushingAttempts')), RUSHTD=_num(st.get('rushingTouchdowns')))
                    elif cat['name'] == 'receiving':
                        row.update(RECYDS=_num(st.get('receivingYards')), REC=_num(st.get('receptions')), RECTD=_num(st.get('receivingTouchdowns')), TGTS=_num(st.get('receivingTargets')))
                elif sport == 'nhl':
                    if cat['name'] in ('forwards', 'defenses', 'defensemen', 'skaters'):
                        row.update(GOALS=_num(st.get('goals')), AST=_num(st.get('assists')), PTS=_num(st.get('points')), SOG=_num(st.get('shotsTotal')) if st.get('shotsTotal') is not None else _num(st.get('shots')), played=1)
                    elif cat['name'] in ('goalies', 'goalie'):
                        row.update(SAVES=_num(st.get('saves')), GA=_num(st.get('goalsAgainst')), played=1 if (_num(st.get('saves')) or 0) > 0 or (_num(st.get('goalsAgainst')) or 0) > 0 else 0)
                elif sport == 'nba':
                    row.update(PTS=_num(st.get('points')), REB=_num(st.get('rebounds')), AST=_num(st.get('assists')), STL=_num(st.get('steals')), BLK=_num(st.get('blocks')),
                               TOV=_num(st.get('turnovers')), MIN=_num(st.get('minutes')),
                               FGM=_split(st.get('fieldGoalsMade-fieldGoalsAttempted'), 0), FTM=_split(st.get('freeThrowsMade-freeThrowsAttempted'), 0),
                               **{'3PM': _split(st.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted'), 0)})
    # derived
    for p in players.values():
        if sport in ('nfl', 'cfb'):
            p['ANYTD'] = (p.get('RUSHTD') or 0) + (p.get('RECTD') or 0)
            if p.get('RUSHYDS') is not None or p.get('RECYDS') is not None: p['RUSHRECYDS'] = (p.get('RUSHYDS') or 0) + (p.get('RECYDS') or 0)
            if p.get('PASSYDS') is not None: p['PASSRUSHYDS'] = p['PASSYDS'] + (p.get('RUSHYDS') or 0)
            p['played'] = 1
        elif sport == 'nba':
            if p.get('PTS') is not None:
                p['PRA'] = p['PTS'] + (p.get('REB') or 0) + (p.get('AST') or 0); p['PR'] = p['PTS'] + (p.get('REB') or 0)
                p['PA'] = p['PTS'] + (p.get('AST') or 0); p['RA'] = (p.get('REB') or 0) + (p.get('AST') or 0)
            p['played'] = 1 if (p.get('MIN') or 0) > 0 else 0
    return players


def pull(sport, event_id):
    s = g(f"https://site.api.espn.com/apis/site/v2/sports/{SP.SPORTS[sport]['espn']}/summary?event={event_id}")
    comp = ((s.get('header') or {}).get('competitions') or [{}])[0]; st = (comp.get('status') or {}).get('type') or {}
    if not st: return None
    if st.get('name') in ('STATUS_POSTPONED', 'STATUS_CANCELED'): return dict(event_id=str(event_id), status='postponed', detail=st.get('name'))
    if not st.get('completed'): return None
    sc = {}
    for c in comp.get('competitors', []):
        ls = [_num(l.get('displayValue') if 'displayValue' in l else l.get('value')) or 0 for l in (c.get('linescores') or [])]
        sc[c.get('homeAway')] = dict(score=_num(c.get('score')), q=ls)
    h, a = sc.get('home', {}), sc.get('away', {})
    if h.get('score') is None or a.get('score') is None: return None
    per = {}
    for side, d in (('home', h), ('away', a)):
        q = d.get('q') or []
        if len(q) >= 2: per[f'1h_{side}'] = q[0] + q[1]
        if len(q) >= 1: per[f'1q_{side}'] = q[0]; per[f'1p_{side}'] = q[0]
    players = parse_players(sport, s.get('boxscore') or {}); players['_periods'] = per
    return dict(event_id=str(event_id), status='final', actual_start=comp.get('date'), home_score=int(h['score']), away_score=int(a['score']),
                f5_home=per.get('1h_home'), f5_away=per.get('1h_away'), rfi=None, players=players, sport=sport)
