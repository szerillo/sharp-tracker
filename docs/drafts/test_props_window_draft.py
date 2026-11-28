"""Offline test of the DRAFT props window patch (docs/drafts/props_window_2026-11-28.patch). Not in tests/ on purpose: the patch is not
applied (Sean's call), so CI must not run this against live code. It applies the patch to a scratch copy of sharp/ and loggers/, feeds
props_live.main() fake Odds API responses (no key, no network), and checks:
  - an NBA game 2 hours out is checked (3-hour window); an NHL game 2 hours out is not (stays 1 hour)
  - a new lean is published live; the re-check turns it live=false when the edge drops under the rule, and live again when it returns
  - the paper record keeps the first flag's price
Run: python3 docs/drafts/test_props_window_draft.py"""
import datetime as dt, importlib, json, os, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PATCH = os.path.join(ROOT, 'docs', 'drafts', 'props_window_2026-11-28.patch')
NOW = dt.datetime(2026, 11, 28, 20, 0, tzinfo=dt.timezone.utc)
iso = lambda t: t.strftime('%Y-%m-%dT%H:%M:%SZ')


def odds(fd_under, pin_ts):
    q = lambda name, price: dict(name=name, description='Test Player', point=2.5, price=price)
    return dict(bookmakers=[dict(key='pinnacle', markets=[dict(key='player_threes', last_update=pin_ts, outcomes=[q('Over', 1.95), q('Under', 1.90)])]),
                            dict(key='fanduel', markets=[dict(key='player_threes', last_update=pin_ts, outcomes=[q('Over', 1.75), q('Under', fd_under)])])])


class DraftWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        for sub in ('sharp', 'loggers'): shutil.copytree(os.path.join(ROOT, sub), os.path.join(cls.d, sub))
        r = subprocess.run(['git', 'apply', PATCH], cwd=cls.d, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        os.makedirs(os.path.join(cls.d, 'data', 'state'))
        sys.path.insert(0, cls.d)
        os.environ['ODDS_API_KEY'] = 'offline-test'
        cls.M = importlib.import_module('sharp.props_live')
        assert 'WINDOW_H' in vars(cls.M), 'not the patched module'

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.d, ignore_errors=True)

    def run_at(self, now, fd_under):
        M = self.M; M.NOW = now; calls = []
        start = iso(NOW + dt.timedelta(hours=2))
        def get(u):
            calls.append(u)
            if '/sports/basketball_nba/events?' in u: return [dict(id='nba1', commence_time=start, home_team='Home', away_team='Away')]
            if '/sports/icehockey_nhl/events?' in u: return [dict(id='nhl1', commence_time=start, home_team='Home', away_team='Away')]
            if '/events/nba1/odds' in u: return odds(fd_under, iso(now - dt.timedelta(minutes=1)))
            return [] if u.endswith('events?apiKey=offline-test') else None
        M.get = get; M.KEY = 'offline-test'
        M.main()
        rows = [json.loads(l) for l in open(M.PAPER)]
        live = json.load(open(M.OUT))['rows']
        return calls, rows, live

    def test_window_and_recheck(self):
        calls, rows, live = self.run_at(NOW, 2.10)                     # 2 h out, edge about 6%: flagged
        self.assertTrue(any('/events/nba1/odds' in u for u in calls), 'NBA 2 h out is inside the 3-hour window')
        self.assertFalse(any('/events/nhl1/odds' in u for u in calls), 'NHL stays at 1 hour')
        self.assertEqual(len(rows), 1); self.assertEqual(rows[0]['price'], 2.10)
        self.assertIs(live[0].get('live'), True, 'a new lean is published live')
        _, rows, live = self.run_at(NOW + dt.timedelta(minutes=16), 1.95)   # edge gone
        self.assertIs(live[0].get('live'), False)
        _, rows, live = self.run_at(NOW + dt.timedelta(minutes=32), 2.08)   # back over 4% strict EV
        self.assertIs(live[0].get('live'), True)
        self.assertEqual(len(rows), 1); self.assertEqual(rows[0]['price'], 2.10, 'the record keeps the first flag')


if __name__ == '__main__':
    unittest.main()
