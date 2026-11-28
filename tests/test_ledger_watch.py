"""11/27: sharp/ledger_watch.py alerts when a push drops paper-ledger rows; it must stay quiet when rows are only added or graded.
Run: python3 -m unittest tests.test_ledger_watch"""
import json, os, shutil, subprocess, sys, tempfile, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, ROOT)
from sharp import ledger_watch as LW

F = 'data/state/sharp_paper.jsonl'


class LedgerWatch(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.saved = LW.ROOT; LW.ROOT = self.d
        for a in (['init', '-q', '-b', 'main'], ['config', 'user.email', 't@t'], ['config', 'user.name', 't']): subprocess.run(['git', *a], cwd=self.d)
        self.snap = os.path.join(self.d, 'snap.json')

    def tearDown(self): LW.ROOT = self.saved; shutil.rmtree(self.d, ignore_errors=True)

    def main_has(self, rows):
        os.makedirs(os.path.join(self.d, 'data/state'), exist_ok=True)
        open(os.path.join(self.d, F), 'w').write(''.join(json.dumps(r) + '\n' for r in rows))
        subprocess.run(['git', 'add', '-A'], cwd=self.d); subprocess.run(['git', 'commit', '-qm', 'x'], cwd=self.d)
        return LW.check(fetch=False, ref='HEAD', snap=self.snap).get(F, 0)

    def test_added_and_graded_rows_are_quiet_and_a_drop_alerts(self):
        r = lambda c, **k: dict(cond=c, side='yes', **k)
        self.assertEqual(self.main_has([r('a'), r('b')]), 0)                 # first audit: nothing to compare
        self.assertEqual(self.main_has([r('a', won=1), r('b'), r('c')]), 0)  # graded in place + a new row
        self.assertEqual(self.main_has([r('a', won=1), r('c')]), 1)          # 'b' dropped by a push
        self.assertEqual(self.main_has([r('a', won=1), r('c')]), 0)          # alert once, then the new snapshot


if __name__ == '__main__':
    unittest.main()
