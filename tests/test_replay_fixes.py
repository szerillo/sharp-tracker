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


class CbbDraft(unittest.TestCase):
    def test_draft_applies_and_compiles(self):
        p = os.path.join(ROOT, 'docs', 'drafts', 'cbb_labs_gate_2026-11-27.patch')
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'sharp'))
            open(os.path.join(d, 'sharp', 'systems.py'), 'w').write(open(os.path.join(ROOT, 'sharp', 'systems.py')).read())
            r = subprocess.run(['git', 'apply', p], cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            src = open(os.path.join(d, 'sharp', 'systems.py')).read()
            compile(src, 'systems.py', 'exec')
            self.assertIn('CBB_LABS_GATE = True', src)
        self.assertNotIn('CBB_LABS_GATE', open(os.path.join(ROOT, 'sharp', 'systems.py')).read())     # drafted, not applied


if __name__ == '__main__':
    unittest.main()
