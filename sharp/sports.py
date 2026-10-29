"""Sport registry for the generic loggers/build (NFL, NBA, CFB; MLB keeps its own loggers for now).
Canonical team code = ESPN abbreviation. Everything else maps onto it: Pinnacle full names, Kalshi ticker codes,
Action Network abbreviations, Novig event descriptions ('Dallas Cowboys @ Philadelphia Eagles'), Polymarket slugs (nfl-dal-phi-date).
Canonical event id = ESPN event id. Markets: ml, spread, total, tt_home, tt_away and the same with 1h_ / 1q_ prefixes; props prop_<STAT>."""
import re, datetime as dt

NFL = {
    'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL', 'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
    'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL', 'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
    'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX', 'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV',
    'Los Angeles Chargers': 'LAC', 'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN', 'New England Patriots': 'NE',
    'New Orleans Saints': 'NO', 'New York Giants': 'NYG', 'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
    'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB', 'Tennessee Titans': 'TEN', 'Washington Commanders': 'WSH'}
NBA = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET', 'Golden State Warriors': 'GS', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC', 'LA Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL',
    'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NO', 'New York Knicks': 'NY', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL',
    'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SA',
    'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTAH', 'Washington Wizards': 'WSH'}
# vendor code -> canonical, applied before equality checks (both leagues; a code that is valid canonical in one league is left alone there)
CODE_FIX = {'nfl': {'JAC': 'JAX', 'LA': 'LAR', 'WAS': 'WSH', 'LVR': 'LV', 'ARZ': 'ARI', 'TAM': 'TB', 'GNB': 'GB', 'KAN': 'KC', 'NWE': 'NE', 'NOR': 'NO', 'SFO': 'SF'},
            'nba': {'GSW': 'GS', 'NOP': 'NO', 'NYK': 'NY', 'SAS': 'SA', 'UTA': 'UTAH', 'WAS': 'WSH', 'PHO': 'PHX', 'BRK': 'BKN', 'CHO': 'CHA', 'LA': 'LAL'},
            'cfb': {}}

PERIODS = {'full': '', '1h': '1h_', '1q': '1q_'}
# Kalshi series -> (market, period prefix); same pattern per league prefix
KALSHI_GAME = {'GAME': ('ml', ''), 'SPREAD': ('spread', ''), 'TOTAL': ('total', ''), 'TEAMTOTAL': ('tt', ''),
               '1H': ('ml', '1h_'), '1HSPREAD': ('spread', '1h_'), '1HTOTAL': ('total', '1h_'), '1HTEAMTOTAL': ('tt', '1h_'),
               '1Q': ('ml', '1q_'), '1QSPREAD': ('spread', '1q_'), '1QTOTAL': ('total', '1q_'), '1QTEAMTOTAL': ('tt', '1q_')}
KALSHI_PROPS = {'nfl': {'PASSYDS': 'PASSYDS', 'RSHYDS': 'RUSHYDS', 'RECYDS': 'RECYDS', 'REC': 'REC', 'PASSTDS': 'PASSTD', 'TD': 'ANYTD', 'ANYTD': 'ANYTD',
                        'RSHATT': 'RUSHATT', 'PASSATT': 'PASSATT', 'PASSCOMP': 'PASSCOMP', 'PASSINT': 'INT', 'RRYDS': 'RUSHRECYDS'},
                'nba': {'PTS': 'PTS', 'REB': 'REB', 'AST': 'AST', 'PRA': 'PRA', 'PR': 'PR', 'PA': 'PA', 'RA': 'RA', '3PT': '3PM', 'STL': 'STL', 'BLK': 'BLK', 'FTM': 'FTM'},
                'cfb': {}}
NOVIG_PROPS = {'nfl': {'PASSING_YARDS': 'PASSYDS', 'RUSHING_YARDS': 'RUSHYDS', 'RECEIVING_YARDS': 'RECYDS', 'RECEPTIONS': 'REC', 'PASSING_TOUCHDOWNS': 'PASSTD',
                       'TOUCHDOWNS': 'ANYTD', 'RUSHING_ATTEMPTS': 'RUSHATT', 'PASSING_ATTEMPTS': 'PASSATT', 'PASSING_COMPLETIONS': 'PASSCOMP',
                       'INTERCEPTIONS': 'INT', 'RUSHING_AND_RECEIVING_YARDS': 'RUSHRECYDS', 'PASSING_AND_RUSHING_YARDS': 'PASSRUSHYDS'},
               'nba': {'POINTS': 'PTS', 'REBOUNDS': 'REB', 'ASSISTS': 'AST', 'POINTS_REBOUNDS_ASSISTS': 'PRA', 'POINTS_REBOUNDS': 'PR', 'POINTS_ASSISTS': 'PA',
                       'REBOUNDS_ASSISTS': 'RA', 'THREE_POINTERS': '3PM', 'STEALS': 'STL', 'BLOCKS': 'BLK'},
               'cfb': {}}
NOVIG_GAME = {'MONEY': ('ml', ''), 'SPREAD': ('spread', ''), 'TOTAL': ('total', ''), 'TEAM_TOTAL': ('tt', ''),
              'MONEY_1H': ('ml', '1h_'), 'SPREAD_1H': ('spread', '1h_'), 'TOTAL_1H': ('total', '1h_'), 'TEAM_TOTAL_1H': ('tt', '1h_'),
              'MONEY_1Q': ('ml', '1q_'), 'SPREAD_1Q': ('spread', '1q_'), 'TOTAL_1Q': ('total', '1q_')}
POLY_GAME = {'moneyline': ('ml', ''), 'spreads': ('spread', ''), 'totals': ('total', ''), 'team_totals': ('tt', ''),
             'first_half_spreads': ('spread', '1h_'), 'first_half_totals': ('total', '1h_'), 'first_half_moneyline': ('ml', '1h_')}
POLY_PROPS = {'nfl': {'passing_yards': 'PASSYDS', 'rushing_yards': 'RUSHYDS', 'receiving_yards': 'RECYDS', 'receptions': 'REC', 'passing_touchdowns': 'PASSTD',
                      'anytime_touchdowns': 'ANYTD'},
              'nba': {'points': 'PTS', 'rebounds': 'REB', 'assists': 'AST', 'threes': '3PM', 'pra': 'PRA'}, 'cfb': {}}
AN_PROPS = {'nfl': {}, 'nba': {}, 'cfb': {}}   # filled when the AN prop endpoints are wired for these sports
PIN_PROPS = {'nfl': {'Passing Yards': 'PASSYDS', 'Rushing Yards': 'RUSHYDS', 'Receiving Yards': 'RECYDS', 'Receptions': 'REC', 'Passing TDs': 'PASSTD',
                     'Touchdowns': 'ANYTD', 'Rush Attempts': 'RUSHATT', 'Pass Attempts': 'PASSATT', 'Pass Completions': 'PASSCOMP', 'Interceptions': 'INT'},
             'nba': {'Points': 'PTS', 'Rebounds': 'REB', 'Assists': 'AST', 'Pts+Rebs+Asts': 'PRA', '3 Point FG': '3PM', 'Steals': 'STL', 'Blocks': 'BLK'},
             'cfb': {}}

SPORTS = {
    'nfl': dict(label='NFL', espn='football/nfl', pinnacle=889, kalshi='KXNFL', an='nfl', poly='NFL', novig='NFL', teams=NFL, weather=True,
                horizon_days=8, periods=('full', '1h', '1q'), pin_period={0: '', 1: '1h_', 3: '1q_'}, an_period={'event': '', 'firsthalf': '1h_', 'firstquarter': '1q_'}),
    'nba': dict(label='NBA', espn='basketball/nba', pinnacle=487, kalshi='KXNBA', an='nba', poly='NBA', novig='NBA', teams=NBA, weather=False,
                horizon_days=2, periods=('full', '1h', '1q'), pin_period={0: '', 1: '1h_', 3: '1q_'}, an_period={'event': '', 'firsthalf': '1h_', 'firstquarter': '1q_'}),
    'cfb': dict(label='CFB', espn='football/college-football', pinnacle=880, kalshi='KXNCAAF', an='ncaaf', poly='CFB', novig='NCAAF', teams={}, weather=True,
                horizon_days=8, periods=('full', '1h'), pin_period={0: '', 1: '1h_'}, an_period={'event': '', 'firsthalf': '1h_'}),
}
GAME_MARKET_RE = re.compile(r'^(1h_|1q_)?(ml|spread|total|tt_home|tt_away)$')


def market_class(m):
    return 'game' if GAME_MARKET_RE.match(m) else 'prop'


class Teams:
    """Resolve any vendor spelling to the canonical ESPN code for one sport. CFB learns its names from the ESPN schedule itself."""
    def __init__(self, sport, espn_games=None):
        self.sport = sport; cfg = SPORTS[sport]
        self.full = dict(cfg['teams']); self.codes = set(self.full.values()); self.fix = CODE_FIX[sport]
        self.nick = {}; self.loc = {}
        for name, ab in self.full.items():
            parts = name.split(); self.nick[parts[-1].lower()] = ab; self.loc.setdefault(' '.join(parts[:-1]).lower(), ab)
        for g in espn_games or []:
            for t in (g.get('away_team'), g.get('home_team')):
                if not t: continue
                ab = t['abbr']; self.codes.add(ab)
                for k in (t.get('displayName'), t.get('shortDisplayName'), t.get('name'), t.get('location')):
                    if k: self.full.setdefault(k, ab)
                if t.get('name'): self.nick.setdefault(t['name'].lower(), ab)
                if t.get('location'): self.loc.setdefault(t['location'].lower(), ab)

    def code(self, x):
        if not x: return None
        s = str(x).strip()
        if s in self.full: return self.full[s]
        u = s.upper()
        if u in self.fix: return self.fix[u]
        if u in self.codes: return u
        low = s.lower()
        if low in self.nick: return self.nick[low]
        if low in self.loc: return self.loc[low]
        last = low.split()[-1] if low.split() else ''
        if last in self.nick: return self.nick[last]
        return None


MON = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']


def kalshi_event(ev):
    """'26NOV02CHISEA' -> (date, 'CHI', 'SEA'); NFL/NBA/CFB tickers carry no time. Returns the raw letter blob for the caller to split."""
    m = re.match(r'^(\d\d)([A-Z]{3})(\d\d)([A-Z]+)$', ev)
    if not m: return None
    yy, mon, dd, teams = m.groups()
    return dt.date(2000 + int(yy), MON.index(mon) + 1, int(dd)), teams


def split_codes(blob, codes, fix):
    """'CHISEA' -> ('CHI','SEA') using the known code set; tries 2/3/4-letter away codes."""
    for i in (3, 2, 4):
        a, h = blob[:i], blob[i:]
        a2, h2 = fix.get(a, a), fix.get(h, h)
        if a2 in codes and h2 in codes: return a2, h2
    return None
