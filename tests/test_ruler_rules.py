"""Pinned cases for the ruler's exclusion rules. Run: python3 -m pytest tests/ or python3 tests/test_ruler_rules.py"""
import os, sys, json, sqlite3
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from sharp import fair as F, constants as C

TS = '2026-10-18T16:00:00Z'


def db_with(rows):
    conn = sqlite3.connect(':memory:'); conn.executescript(open(os.path.join(HERE, '..', 'sharp', 'schema.sql')).read())
    conn.execute("INSERT INTO events VALUES ('E1','nfl','NFL','2026-10-18','2026-10-18T17:00:00Z','CAR','PHI','scheduled','{}')")
    for r in rows:
        venue, side, am, bid, ask, depth = r
        imp = (1 / (1 + am / 100) if am > 0 else -am / (-am + 100)) if am is not None else ask
        flags = 'wide' if (bid is not None and ask is not None and ask - bid > C.EXCHANGE_SPREAD_MAX['value']) else None
        conn.execute("INSERT INTO ticks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (TS, None, 'nfl', 'NFL', 'E1', '2026-10-18T17:00:00Z', 'prop_RUSH', 'prop', 'chuba hubbard', 'Chuba Hubbard', 67.5, side, venue, am, None, imp,
                      bid, ask, (bid + ask) / 2 if bid is not None and ask is not None else None, None, None, None, 'test', flags,
                      json.dumps({'depth3': depth}) if depth is not None else None, 'test'))
    conn.commit(); return conn


BOOKS = [('BetRivers', 'over', -114, None, None, None), ('BetRivers', 'under', -116, None, None, None),
         ('DK', 'over', -114, None, None, None), ('DK', 'under', -116, None, None, None),
         ('FD', 'over', -112, None, None, None), ('FD', 'under', -115, None, None, None),
         ('Caesars', 'over', -113, None, None, None), ('Caesars', 'under', -115, None, None, None)]


def test_hubbard_one_sided_maker_is_wide():
    """Novig: $2.4k bid at 96c on the over, 55c bid on the under -> 41c-wide book -> excluded; fair = book consensus (~53%), not 75%."""
    conn = db_with(BOOKS + [('Novig', 'over', None, 0.96, 1.00, 2400.0), ('Novig', 'under', None, 0.00, 0.04, 61.0)])
    C.WEIGHTS[('nfl', 'prop')] = C.WEIGHTS[('mlb', 'prop')]; C.DEVIG_METHOD[('nfl', 'prop')] = C.DEVIG_METHOD[('mlb', 'prop')]
    r = F.EventQuotes(conn, 'E1').fair('prop_RUSH', 67.5, 'over', TS, 'chuba hubbard', sport='nfl')
    assert r['detail']['Novig']['p'] is None and r['detail']['Novig']['why'].split()[0] in ('wide', 'oneside', 'thin'), r['detail']['Novig']
    assert 0.48 < r['fair'] < 0.56, r['fair']


def test_tight_but_thin_is_excluded():
    conn = db_with(BOOKS + [('Novig', 'over', None, 0.74, 0.76, 120.0), ('Novig', 'under', None, 0.24, 0.26, 90.0)])
    r = F.EventQuotes(conn, 'E1').fair('prop_RUSH', 67.5, 'over', TS, 'chuba hubbard', sport='nfl')
    assert r['detail']['Novig']['why'].startswith('thin'), r['detail']['Novig']


def test_tight_deep_but_alone_is_outlier():
    """Inside the spread rule, deep on both sides, 20 pts from eight books with nobody near it -> outlier, excluded."""
    conn = db_with(BOOKS + [('Novig', 'over', None, 0.74, 0.76, 5000.0), ('Novig', 'under', None, 0.24, 0.26, 5000.0)])
    r = F.EventQuotes(conn, 'E1').fair('prop_RUSH', 67.5, 'over', TS, 'chuba hubbard', sport='nfl')
    assert r['detail']['Novig']['why'].startswith('outlier'), r['detail']['Novig']
    assert 0.48 < r['fair'] < 0.56


def test_tight_deep_and_confirmed_stays():
    """Same quote with Kalshi and Pinnacle within 3 pts -> it is the market, books are stale; Novig stays in."""
    conn = db_with(BOOKS + [('Novig', 'over', None, 0.74, 0.76, 5000.0), ('Novig', 'under', None, 0.24, 0.26, 5000.0),
                            ('Kalshi', 'over', None, 0.73, 0.75, 3000.0), ('Kalshi', 'under', None, 0.25, 0.27, 3000.0),
                            ('Pinnacle', 'over', -280, None, None, None), ('Pinnacle', 'under', 230, None, None, None)])
    r = F.EventQuotes(conn, 'E1').fair('prop_RUSH', 67.5, 'over', TS, 'chuba hubbard', sport='nfl')
    assert r['detail']['Novig']['why'] == 'ok', r['detail']['Novig']
    assert r['fair'] > 0.60


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'): fn(); print('ok', name)
