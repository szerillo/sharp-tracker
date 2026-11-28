"""11/27 (td_replay_fixes): regular-season checks, the 2020 bubble and Utah fixes in the replay, the rule_replay.json record reader, and the
CBB Bet Labs list draft. Run: python3 -m unittest tests.test_replay_fixes"""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'sharp')); sys.path.insert(0, ROOT)
import rule_replay as RR
from sharp import odds_db as ODB

U = dt.timezone.utc


class RegularSeasonReplay(unittest.TestCase):
    def test_bubble_games_are_not_regular_season(self):
        self.assertFalse(RR.regular_season('nhl', None, dt.datetime(2020, 8, 5, tzinfo=U)))      # 2020 bubble, ESPN type blank
        self.assertFalse(RR.regular_season('nba', None, dt.datetime(2020, 9, 30, tzinfo=U)))
        self.assertTrue(RR.regular_season('nhl', None, dt.datetime(2021, 1, 20, tzinfo=U)))       # blank type outside the bubble counts
        self.assertTrue(RR.regular_season('cfb', None, dt.datetime(2020, 9, 12, tzinfo=U)))       # the bubble rule is NHL / NBA only
        self.assertFalse(RR.regular_season('nhl', 3, dt.datetime(2023, 5, 1, tzinfo=U)))          # playoffs
        self.assertFalse(RR.regular_season('nhl', 1, dt.datetime(2023, 9, 25, tzinfo=U)))         # preseason
        self.assertTrue(RR.regular_season('nhl', 2, dt.datetime(2020, 8, 5, tzinfo=U)))           # an explicit type wins

    def test_2020_21_record_leaves_out_the_bubble(self):
        """Carolina's 2020-21 record must not include its August 2020 bubble games (the 47-of-50 win% mismatch with Bet Labs)."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'data', 'state'))
            H = {'nhl': {
                'b1': dict(start='2020-08-03T20:00Z', home='CAR', away='NYR', hs=3, as_=2, stype=None),    # bubble wins
                'b2': dict(start='2020-08-05T20:00Z', home='NYR', away='CAR', hs=1, as_=4, stype=None),
                'r1': dict(start='2021-01-15T00:00Z', home='CAR', away='DET', hs=0, as_=3, stype=2),       # 2020-21 regular season
                'r2': dict(start='2021-01-17T00:00Z', home='DET', away='CAR', hs=1, as_=2, stype=2),
                'p1': dict(start='2021-05-20T00:00Z', home='CAR', away='NSH', hs=5, as_=2, stype=3)}}     # playoffs
            json.dump(H, open(os.path.join(d, 'data', 'state', 'hist_schedule.json'), 'w'))
            old = RR.ROOT; RR.ROOT = d
            try:
                g = dict(id='x', sport='nhl', start=dt.datetime(2021, 6, 1, tzinfo=U), home='Carolina Hurricanes', away='Detroit Red Wings', home_ab='CAR', away_ab='DET',
                         hs=None, as_=None, tot_close=None, regular=True)
                RR.profiles([g])
            finally: RR.ROOT = old
        self.assertEqual((g['home_games'], g['home_wins'], g['home_win_pct']), (2, 1, 50))     # r1 loss, r2 win; no bubble, no playoff game

    def test_record_reader_does_not_double_count(self):
        """summary_record() is the 'all' row; season rows add up to it. Summing every key (the 11/25 PUSHBACK error) gives twice the bets."""
        D = json.load(open(os.path.join(ROOT, 'data', 'research', 'rule_replay.json')))
        for k in D:
            a = RR.summary_record(D, k); S = RR.season_rows(D, k)
            self.assertNotIn('all', S)
            self.assertEqual(sum(v['n'] for v in S.values()), a['n'], k)
            self.assertEqual(sum(v['n'] for v in D[k].values()), 2 * a['n'], k)


class PuckLineGrading(unittest.TestCase):
    def game(self, sp_close):
        return dict(hs=4, as_=1, sp_close=sp_close, sp_home_dec=1.40 if sp_close > 0 else 3.20, sp_away_dec=3.20 if sp_close > 0 else 1.40, p_open=None, p_close=None, sp_open=None)

    def test_price_only_on_the_posted_line(self):
        """Pinnacle hung -1.5 on the visitor (home +1.5 at 1.40): a home -1.5 bet has no Pinnacle price and is not graded. Before 11/27 it
        was paid at the +1.5 price."""
        g = self.game(1.5)
        self.assertIsNone(RR.grade(g, 'spread', 'home', -1.5))
        self.assertEqual(RR.grade(g, 'spread', 'home', 1.5)[:2], (1, 1.40))
        self.assertEqual(RR.grade(g, 'spread', 'away', -1.5)[:2], (0, 3.20))
        self.assertEqual(RR.grade(g, 'spread', 'home', -1.5, result_only=True)[:2], (1, None))     # market_replay prices it itself
        g2 = self.game(-1.5)
        self.assertEqual(RR.grade(g2, 'spread', 'home', -1.5)[:2], (1, 3.20))
        self.assertIsNone(RR.grade(g2, 'spread', 'home', -2.5))                                     # no made-up 1.91 any more


class NoMadeUpPrices(unittest.TestCase):
    """Data-strict: a replay grades only at a price it has. Flags a hard-coded decimal price used as a fallback ("or 1.909",
    "dec = 1.91", "dec=1.95") anywhere in the tools. A line that is not a price fallback can carry "# placeholders only" to be skipped."""
    PAT = __import__('re').compile(r"(\bor\s+|dec\w*\s*=\s*)1\.9\d*\b")

    def test_no_price_fallbacks(self):
        bad = []
        for top in ('sharp', 'loggers'):
            for dp, _, fs in os.walk(os.path.join(ROOT, top)):
                for f in fs:
                    if not f.endswith('.py'): continue
                    for i, line in enumerate(open(os.path.join(dp, f), encoding='utf-8', errors='ignore'), 1):
                        code = line.split('#', 1)[0]
                        if self.PAT.search(code) and 'placeholders only' not in line: bad.append(f"{os.path.relpath(os.path.join(dp, f), ROOT)}:{i}: {line.strip()[:120]}")
        self.assertEqual(bad, [], 'made-up price fallbacks:\n' + '\n'.join(bad))


class UtahAbbreviations(unittest.TestCase):
    def test_utah_matches_either_abbreviation(self):
        st = dt.datetime(2024, 10, 9, 2, 10, tzinfo=U)
        idx = {('UTAH', 'CHI'): [dict(start='2024-10-09T02:00Z', home='UTAH', away='CHI', hs=5, as_=2, eid='1')]}
        h = ODB.match_hist('nhl', 'UTA', 'CHI', st, idx)      # espn_teams.json says UTA for "Utah Hockey Club"; the 2024-25 schedule says UTAH
        self.assertIsNotNone(h); self.assertEqual(h['home'], 'UTAH')
        self.assertIsNone(ODB.match_hist('nhl', 'UTA', 'CHI', st + dt.timedelta(hours=8), idx))     # still inside the 6-hour window only
        self.assertIsNone(ODB.match_hist('nba', 'UTA', 'CHI', st, idx))                              # NBA Utah is a different team
        self.assertEqual(ODB.abbr_variants('nhl', 'BOS'), ['BOS'])


class LiveRegularSeason(unittest.TestCase):
    def test_live_rules_skip_postseason(self):
        import systems as S
        S.SCHED_CACHE['nhl'] = {'po': {'season_type': 3}, 'rs': {'season_type': 2}, 'old': {}, 'pre': {'season_type': 1}}
        try:
            self.assertFalse(S.regular_season('nhl', 'po')); self.assertFalse(S.regular_season('nhl', 'pre'))
            self.assertTrue(S.regular_season('nhl', 'rs')); self.assertTrue(S.regular_season('nhl', 'old'))
        finally: S.SCHED_CACHE.pop('nhl', None)

    def test_every_saved_screen_is_regular_season(self):
        """If Sean saves a screen that includes the playoffs, the live check above needs a per-rule exception: this test says so."""
        R = json.load(open(os.path.join(ROOT, 'data', 'betlabs', 'records.json')))['screens']
        for sid, v in R.items():
            self.assertTrue(any('regular season' in f.lower() for f in v['filters']), f"{sid} {v['name']}")


class CbbListOnly(unittest.TestCase):
    def test_gate_is_applied(self):
        """11/27: Sean approved the drafted CBB change; cbb_under_good_over_drop bets only games on Bet Labs' list."""
        src = open(os.path.join(ROOT, 'sharp', 'systems.py')).read()
        self.assertIn('CBB_LABS_GATE = True', src)
        self.assertIn("labs_pick(1792184,", src)
        for line in ("if not on_:", "flag only, no bet", "why = f\"{labs_label(pick_)}"):
            self.assertIn(line, src)

    def test_neutral_site_listing_matches_swapped(self):
        """Bet Labs listed Fresno State @ South Alabama on 11/27; ESPN has Fresno State at home (neutral site). Same game, either order."""
        import systems as S
        old = (list(S._BLP), S.NOW)
        S._BLP[:] = [dict(pulled='2026-11-27T03:42:25Z', picks=[dict(sid=1792184, away='Fresno State', home='South Alabama', info='x')])]
        S.NOW = S.N.parse_ts('2026-11-27T11:00:00Z')
        try:
            self.assertTrue(S.labs_pick(1792184, 'South Alabama Jaguars', 'Fresno State Bulldogs')[0])
            self.assertTrue(S.labs_pick(1792184, 'Fresno State Bulldogs', 'South Alabama Jaguars')[0])
            self.assertFalse(S.labs_pick(1792184, 'Fresno State Bulldogs', 'Alabama Crimson Tide')[0])
            self.assertIs(S.labs_pick(1792184, 'Fresno State Bulldogs', 'South Alabama Jaguars', max_h=1)[0], None)     # stale pull: no bet
        finally: S._BLP[:] = old[0]; S.NOW = old[1]


class NoFillReason(unittest.TestCase):
    """11/27: a triggered rule that does not fill says why in system_fires.json (games[].no_fill[tag]). Liberty @ St. Thomas: only Pinnacle
    quoted the total, so there was no bettable price."""
    def test_reasons(self):
        import systems as S
        saved = (S.F.best_price, S.FI.load, S.NOW)
        class EQ:
            def fair(self, *a): return dict(fair=0.5, status='ok')
        try:
            S.FI.load = lambda: []
            S.NOW = S.N.parse_ts('2026-11-27T13:00:00Z')
            start = '2026-11-27T17:00:00Z'
            S.F.best_price = lambda *a, **k: []
            game = dict(triggers={}, fills=[])
            S.take(None, EQ(), {}, [], game, 'e1', start, 'LIB', 'STMN', 'cbb_under_good_over_drop', 'total', 146.5, 'under', None, 0.5, 'why')
            self.assertEqual(game['no_fill']['cbb_under_good_over_drop'], 'no bettable venue quotes this total at 146.5')
            S.F.best_price = lambda *a, **k: [dict(cost=0.70, venue='Novig')]
            game = dict(triggers={}, fills=[])
            S.take(None, EQ(), {}, [], game, 'e2', start, 'LIB', 'STMN', 'cbb_under_good_over_drop', 'total', 146.5, 'under', None, 0.5, 'why')
            self.assertIn('past -150/+150', game['no_fill']['cbb_under_good_over_drop'])
            game = dict(triggers={}, fills=[])
            S.take(None, EQ(), {}, [], game, 'e3', '2026-11-27T13:30:00Z', 'LIB', 'STMN', 'cbb_under_good_over_drop', 'total', 146.5, 'under', None, 0.5, 'why')
            self.assertIn('shown, not filled', game['no_fill']['cbb_under_good_over_drop'])
        finally: S.F.best_price, S.FI.load, S.NOW = saved


class LabsMatch(unittest.TestCase):
    def test_unmatched(self):
        from sharp import labs_match as LM
        picks = [dict(sid=1792184, date='2026-11-27', away='Fresno State', home='South Alabama'),
                 dict(sid=1792184, date='2026-11-27', away='Liberty', home='St. Thomas'),
                 dict(sid=1792184, date='2026-11-27', away='Old Dominion', home='Virginia Tech'),
                 dict(sid=1792184, date='2026-11-28', away='Someone', home='Else'),            # not today
                 dict(sid=1799442, date='2026-11-27', away='Indiana Pacers', home='Chicago Bulls')]    # not a list-bet screen
        games = [dict(sport='cbb', away_name='South Alabama Jaguars', home_name='Fresno State Bulldogs', triggers={'cbb_under_good_over_drop': 'x'}),   # swapped
                 dict(sport='cbb', away_name='Liberty Flames', home_name='St. Thomas Tommies', triggers={'cbb_labs_gap': 'x'})]
        miss = LM.unmatched(picks, games, today='2026-11-27')
        self.assertEqual([(r, g) for r, g, _ in miss], [('cbb_under_good_over_drop', 'Liberty @ St. Thomas'), ('cbb_under_good_over_drop', 'Old Dominion @ Virginia Tech')])
        self.assertIn('did not trigger', miss[0][2]); self.assertIn('not on the board', miss[1][2])

    def test_logged_or_started_is_not_a_miss(self):          # 11/28: UCF @ Colorado false warning
        import datetime as dt
        from sharp import labs_match as LM
        picks = [dict(sid=1783043, date='2026-11-28', away='UCF', home='Colorado'), dict(sid=1783043, date='2026-11-28', away='UAB', home='North Texas'),
                 dict(sid=1783043, date='2026-11-28', away='Army', home='Navy')]
        games = [dict(sport='cfb', away_name='UCF Knights', home_name='Colorado Buffaloes', start_utc='2026-11-28T19:00:00Z', triggers={},
                      untracked=[dict(tag='cfb_wind14', untracked='cfb_wind14 vs cfb_day_over')]),
                 dict(sport='cfb', away_name='UAB Blazers', home_name='North Texas Mean Green', start_utc='2026-11-28T18:00:00Z', triggers={}),
                 dict(sport='cfb', away_name='Army Black Knights', home_name='Navy Midshipmen', start_utc='2026-11-28T23:00:00Z', triggers={})]
        now = dt.datetime(2026, 11, 28, 19, 57, tzinfo=dt.timezone.utc)
        self.assertEqual([g for _, g, _ in LM.unmatched(picks, games, today='2026-11-28', now=now)], ['Army @ Navy'])


if __name__ == '__main__':
    unittest.main()
