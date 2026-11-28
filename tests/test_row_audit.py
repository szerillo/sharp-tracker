"""11/28: sharp/research/row_audit.py once counted a dropped row again for every push that re-logged it (it reported parlays_paper
304,103 missing; the distinct count was 11,102). This pins the distinct count: a row dropped twice and re-logged once in between is one
missing row, charged to the writer that first logged it; a row dropped and re-logged for good is not missing.
Run: python3 -m unittest tests.test_row_audit"""
import json, os, shutil, subprocess, sys, tempfile, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, ROOT)
from sharp.research import row_audit as RA

F = 'data/state/sharp_paper.jsonl'          # keyed by (cond, side)
LOG = 'data/state/results.jsonl'            # whole-line append log


class RowAudit(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.saved = RA.ROOT; RA.ROOT = self.d; self.n = 0
        for a in (['init', '-q', '-b', 'main'], ['config', 'user.email', 't@t'], ['config', 'user.name', 't']): subprocess.run(['git', *a], cwd=self.d)
        os.makedirs(os.path.join(self.d, 'data', 'state'))

    def tearDown(self): RA.ROOT = self.saved; shutil.rmtree(self.d, ignore_errors=True)

    def push(self, writer, ledger, log):
        self.n += 1
        open(os.path.join(self.d, F), 'w').write(''.join(json.dumps(dict(cond=c, side='yes', v=v)) + '\n' for c, v in ledger))
        open(os.path.join(self.d, LOG), 'w').write(''.join(l + '\n' for l in log))
        env = dict(os.environ, GIT_AUTHOR_DATE=f'2026-11-27T1{self.n}:00:00Z', GIT_COMMITTER_DATE=f'2026-11-27T1{self.n}:00:00Z')
        subprocess.run(['git', 'add', '-A'], cwd=self.d); subprocess.run(['git', 'commit', '-qm', f'{writer} x'], cwd=self.d, env=env)
        subprocess.run(['git', 'update-ref', 'refs/remotes/origin/main', 'HEAD'], cwd=self.d)

    def test_each_missing_row_counted_once(self):
        self.push('fast', [('a', 1), ('b', 1)], ['r1', 'r2'])
        self.push('signals', [('a', 1)], ['r1'])                           # b and r2 dropped
        self.push('fast', [('a', 1), ('b', 2)], ['r1', 'r2'])               # re-logged (b at a new price)
        self.push('signals', [('a', 1), ('c', 1)], ['r1', 'r3'])            # b and r2 dropped again; c, r3 added
        self.push('fast', [('a', 1), ('c', 1), ('d', 1)], ['r1', 'r3', 'r2'])   # r2 back for good; d added
        R = RA.audit(F, '2026-11-27T00:00Z', '2026-11-28T00:00Z')
        self.assertEqual(len(R['pushes_that_dropped_rows']), 2)
        self.assertEqual(R['added_rows_missing_on_main_now'], {'fast': 1})   # only b; once, though it was logged twice
        L = RA.audit(LOG, '2026-11-27T00:00Z', '2026-11-28T00:00Z')
        self.assertEqual(sum(L['added_rows_missing_on_main_now'].values()), 0)   # r2 is back


if __name__ == '__main__':
    unittest.main()
