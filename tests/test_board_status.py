"""11/27: sharp/bet_log.py board_status() decides what the bet tracker and Kirk's jobs treat as a real-money bet (bet / held / dropped /
paper / pass / wait). These tests pin the rules as Sean set them; they change nothing.
  11/18  only a Kalshi move against (or an opposing system) blocks a system bet; sharp-account action never does
  11/24  Kalshi move against cancels again from 2026-11-24T21:45Z (19:00Z to 21:45Z was warning-only)
  11/24  sharp flags: held only for an opposing system or a Kalshi move; big money, bet back, sharp move, sharp accounts, sharp flag
         against are shown, not held; a flag the sharps were bought out of (ask 5c+ over their price) is a pass
  11/24  paper / watch rows are never 'bet', and never frozen as one once they start
  11/18  wind rules show WAIT until 12h before kickoff
Run: python3 -m unittest tests.test_board_status"""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
from sharp import bet_log as B

NOW = dt.datetime(2026, 11, 27, 15, 0, tzinfo=dt.timezone.utc)
LATER = '2026-11-27T23:00:00Z'      # 8h out


def row(**k):
    r = dict(id='s:x', src='system', cat='system B', size=0.25, start=LATER, tags=[], rule='nhl_pl_fav_gap')
    r.update(k); return r


class BoardStatus(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.saved = (B.OUT, B.SD, B.NOW)
        B.OUT = os.path.join(self.d.name, 'bet_log.json'); B.SD = self.d.name; B.NOW = NOW

    def tearDown(self):
        B.OUT, B.SD, B.NOW = self.saved; self.d.cleanup()

    def run_(self, rows, prev=None, sharp=None):
        if prev is not None: json.dump(dict(rows=prev), open(B.OUT, 'w'))
        if sharp is not None: json.dump(dict(rows=sharp), open(os.path.join(B.SD, 'sharp_accounts.json'), 'w'))
        B.board_status(rows)
        return [(r['board_status'], r['board_why']) for r in rows]

    def test_system_rows(self):
        out = self.run_([row(), row(held=True, tags=['system against']), row(held=True, tags=['Kalshi move against']),
                         row(excluded='stale_book: not a checkable row'), row(lapsed=True), row(counted=False)])
        self.assertEqual(out, [('bet', ''), ('held', 'a rule on the other side'), ('held', 'Kalshi moved the other way'),
                               ('dropped', 'stale_book: not a checkable row'), ('dropped', 'trigger lapsed'), ('dropped', 'conflicting systems cancel')])

    def test_paper_and_watch_are_never_bets(self):
        out = self.run_([row(cat='paper P'), row(cat='watch'), row(cat='system A', size=None)])
        self.assertEqual({s for s, _ in out}, {'paper'})

    def test_wind_waits_until_12h(self):
        far = (NOW + dt.timedelta(hours=20)).strftime('%Y-%m-%dT%H:%M:%SZ'); near = (NOW + dt.timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%SZ')
        out = self.run_([row(rule='wind1014', start=far), row(rule='wind1014', start=near), row(rule='nhl_pl_fav_gap', start=far)])
        self.assertEqual([s for s, _ in out], ['wait', 'bet', 'bet'])

    def test_sharp_flags(self):
        S = [dict(cond='c1', status='live'), dict(cond='c2', status='live'), dict(cond='c3', status='live'), dict(cond='c4', status='expired'),
             dict(cond='c5', status='live', ask=0.49, paid=0.39), dict(cond='c6', status='live', kalshi_against=True), dict(cond='c7', status='live')]
        rows = [row(id='p:c1', src='sharp', tags=['big money against', 'sharp accts against']),
                row(id='p:c2', src='sharp', tags=['system against']),
                row(id='p:c3', src='sharp', tags=['Kalshi move against']),
                row(id='p:c4', src='sharp'),
                row(id='p:c5', src='sharp'),
                row(id='p:c6', src='sharp'),
                row(id='p:c7', src='sharp', tags=['Kalshi move against'], start='2026-11-24T20:00:00Z')]      # inside the 11/24 warning-only window
        out = self.run_(rows, sharp=S)
        self.assertEqual(out[0], ('bet', 'shown, not a hold: big money, sharp accts against'))
        self.assertEqual(out[1], ('held', 'system against'))
        self.assertEqual(out[2], ('held', 'Kalshi move against'))
        self.assertEqual(out[3], ('dropped', 'flag no longer live'))
        self.assertEqual(out[4], ('pass', "bought out: ask 49c vs the sharps' 39c"))
        self.assertEqual(out[5], ('dropped', 'Kalshi moved the other way'))
        self.assertEqual(out[6][0], 'bet')

    def test_kalshi_cancel_windows(self):
        self.assertTrue(B.kalshi_blocks('2026-11-24T18:59:00Z'))
        self.assertFalse(B.kalshi_blocks('2026-11-24T19:00:00Z'))
        self.assertFalse(B.kalshi_blocks('2026-11-24T21:44:59Z'))
        self.assertTrue(B.kalshi_blocks('2026-11-24T21:45:00Z'))
        self.assertTrue(B.kalshi_blocks('2026-11-27T23:00:00Z'))

    def test_started_rows_keep_their_call_but_paper_is_never_frozen_as_a_bet(self):
        started = '2026-11-27T14:00:00Z'
        prev = [dict(id='s:a', board_status='held', board_why='Kalshi moved the other way'), dict(id='s:b', board_status='bet', board_why='')]
        rows = [row(id='s:a', start=started), row(id='s:b', start=started, cat='paper P')]
        out = self.run_(rows, prev=prev)
        self.assertEqual(out[0], ('held', 'Kalshi moved the other way')); self.assertTrue(rows[0]['held'])
        self.assertEqual(out[1][0], 'paper')


if __name__ == '__main__':
    unittest.main()
