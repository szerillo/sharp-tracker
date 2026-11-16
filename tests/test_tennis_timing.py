import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sharp import tennis_timing as T
from loggers import tennis_lines as L

NOW = dt.datetime(2026, 11, 16, 22, tzinfo=dt.timezone.utc)

class TennisTimingTests(unittest.TestCase):
    def event(self): return {'event_id': 'fixed-fixture', 'start': '2026-11-16T18:00:00Z'}

    def test_delay_is_pregame_not_live(self):
        e = self.event(); T.observe(e, e['start'], 'pinnacle', 'scheduled', NOW)
        self.assertTrue(T.pregame(e, NOW)); self.assertTrue(T.metadata(e, NOW)['awaiting_start'])
        self.assertTrue(T.retain(e, NOW + dt.timedelta(hours=6)))

    def test_clock_alone_does_not_confirm_pregame(self):
        e = self.event(); self.assertFalse(T.pregame(e, NOW)); self.assertTrue(T.retain(e, NOW))

    def test_reschedule_preserves_original_and_records_revision(self):
        e = self.event(); T.observe(e, '2026-11-17T12:00:00Z', 'novig', 'OPEN_PREGAME', NOW)
        self.assertEqual(e['event_id'], 'fixed-fixture'); self.assertEqual(e['original_start'], '2026-11-16T18:00:00Z')
        self.assertEqual(e['start'], '2026-11-17T12:00:00Z'); self.assertEqual(len(e['start_revisions']), 1)

    def test_live_beats_book_pregame(self):
        e = self.event(); T.observe(e, e['start'], 'espn', 'STATUS_IN_PROGRESS', NOW)
        T.observe(e, e['start'], 'novig', 'OPEN_PREGAME', NOW)
        self.assertEqual(e['match_status'], 'live'); self.assertFalse(T.pregame(e, NOW))

    def test_final_cannot_be_resurrected(self):
        e = self.event(); T.observe(e, e['start'], 'espn', 'STATUS_FINAL', NOW)
        T.observe(e, '2026-11-17T12:00:00Z', 'novig', 'OPEN_PREGAME', NOW + dt.timedelta(hours=2))
        self.assertFalse(T.retain(e, NOW)); self.assertFalse(T.pregame(e, NOW))

    def test_stale_source_does_not_override_fresh_revision(self):
        e = self.event(); T.observe(e, '2026-11-17T12:00:00Z', 'novig', 'OPEN_PREGAME', NOW)
        T.observe(e, '2026-11-16T18:00:00Z', 'espn', 'STATUS_SCHEDULED', NOW, '2026-11-16T19:00:00Z')
        self.assertEqual(e['start'], '2026-11-17T12:00:00Z')
        self.assertFalse(T.pregame(e, NOW + dt.timedelta(hours=2)))

    def test_fresh_pinnacle_time_beats_exchange_estimate(self):
        e = self.event(); T.observe(e, '2026-11-17T09:00:00Z', 'pinnacle', 'pending', NOW)
        T.observe(e, '2026-11-17T00:00:00Z', 'novig', 'OPEN_PREGAME', NOW)
        self.assertEqual(e['start'], '2026-11-17T09:00:00Z')

    def test_ledger_reconciles_only_ungraded_tennis(self):
        e = self.event(); T.observe(e, '2026-11-17T12:00:00Z', 'novig', 'OPEN_PREGAME', NOW)
        b = dict(sport='tennis', event_id='fixed-fixture', start='2026-11-16T18:00:00Z', won=None, flagged='2026-11-16T17:00Z')
        T.reconcile_bet(b, {'fixed-fixture': e}, NOW)
        self.assertEqual(b['start'], e['start']); self.assertEqual(b['original_start'], '2026-11-16T18:00:00Z')
        graded = dict(b, won=1); before = copy.deepcopy(graded)
        T.reconcile_bet(graded, {'fixed-fixture': dict(e, start='2026-11-18T00:00Z')}, NOW)
        self.assertEqual(graded, before)

    def test_registry_keeps_id_across_midnight_and_refreshes_start(self):
        with tempfile.TemporaryDirectory() as td, patch.object(L, 'TD', td), patch.object(L, 'EVENTS', str(Path(td)/'events.json')), patch.object(L, 'NOW', NOW):
            r = L.Registry(); k, _ = r.add('Jurij Rodionov', 'Sumit Nagal', NOW)
            r.observe(k, NOW, 'novig', 'OPEN_PREGAME')
            later = NOW + dt.timedelta(hours=16)
            k2, _ = r.add('J. Rodionov', 'S. Nagal', later)
            r.observe(k2, later, 'novig', 'OPEN_PREGAME')
            self.assertEqual(k, k2); self.assertEqual(len(r.ev), 1)
            self.assertEqual(T.timestamp(r.ev[k]['start']), later)

    def test_legacy_schedule_without_checked_at_still_has_start(self):
        with tempfile.TemporaryDirectory() as td, patch.object(L, 'TD', td), patch.object(L, 'EVENTS', str(Path(td)/'events.json')), patch.object(L, 'NOW', NOW):
            Path(td, 'schedule.json').write_text(json.dumps({'123': {'start':'2026-11-17T12:00:00Z','p1':'A. Player','p2':'B. Other','status':'STATUS_SCHEDULED'}}))
            r = L.Registry()
            self.assertEqual(r.ev['123']['start'], '2026-11-17T12:00:00Z')
            self.assertIsNotNone(r.find('A. Player','B. Other', NOW)[0])
            self.assertTrue(r.started('123'))  # unconfirmed, do not ingest possibly live quotes

    def test_no_ticks_from_live_unknown_or_stale_matches(self):
        with tempfile.TemporaryDirectory() as td, patch.object(L, 'TD', td), patch.object(L, 'EVENTS', str(Path(td)/'events.json')), patch.object(L, 'NOW', NOW), patch.object(L, 'ROWS', []):
            r = L.Registry(); k, _ = r.add('A. Player', 'B. Other', NOW)
            L.tick(k, 'ml', 'home', 'Kalshi', 'test', r, ask=.5)
            self.assertEqual(len(L.ROWS), 0)
            r.observe(k, NOW, 'novig', 'OPEN_PREGAME')
            L.tick(k, 'ml', 'home', 'Novig', 'test', r, ask=.5)
            self.assertEqual(len(L.ROWS), 1)
            r.observe(k, NOW, 'pinnacle', 'live')
            L.tick(k, 'ml', 'home', 'Kalshi', 'test', r, ask=.5)
            self.assertEqual(len(L.ROWS), 1)

if __name__ == '__main__': unittest.main()
