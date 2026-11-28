"""td_append_guard (Sean OK 11/27): two writers append to the same row logs at the same time and both push through the workflows' own
`git pull --rebase -X theirs` loop. Without the merge driver, rows are lost (the 11/27 prices_fast CBB bug, reproduced first as a control);
with it, every row from both writers survives, for a .jsonl and a .jsonl.gz, and a graded ledger row replaces its ungraded copy.
Run: python3 -m unittest tests.test_append_merge"""
import gzip, json, os, shutil, subprocess, sys, tempfile, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, ROOT)
from sharp import append_merge as M

DRIVER = f'python3 {os.path.join(ROOT, "sharp", "append_merge.py")} %O %A %B %P'
ATTR = open(os.path.join(ROOT, '.gitattributes')).read()


def sh(cwd, *a):
    r = subprocess.run(a, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def rows(path):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b': raw = gzip.decompress(raw)
    return [l for l in raw.decode().split('\n') if l.strip()]


def append(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if path.endswith('.gz'):
        with gzip.open(path, 'at') as f: f.write(''.join(l + '\n' for l in lines))
    else:
        with open(path, 'a') as f: f.write(''.join(l + '\n' for l in lines))


class TwoWriters(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.origin = os.path.join(self.d, 'origin.git')
        sh(self.d, 'git', 'init', '-q', '--bare', '-b', 'main', self.origin)
        self.seed = self.clone('seed')
        open(os.path.join(self.seed, '.gitattributes'), 'w').write(ATTR)
        self.files = ['data/cbb/ticks5/2026-11-27.jsonl.gz', 'data/state/sharp_paper.jsonl', 'data/kalshi/flow_paper.jsonl']
        for f in self.files: append(os.path.join(self.seed, f), [json.dumps(dict(ts='13:00', w='seed', n=i, cond=f'c{i}', side='yes', event_id=i, market='ml', line=None)) for i in range(3)])
        self.commit(self.seed, 'seed'); sh(self.seed, 'git', 'push', '-q', 'origin', 'HEAD:main')

    def tearDown(self): shutil.rmtree(self.d, ignore_errors=True)

    def clone(self, name, driver=False):
        p = os.path.join(self.d, name); sh(self.d, 'git', 'clone', '-q', self.origin, p)
        sh(p, 'git', 'config', 'user.email', 't@t'); sh(p, 'git', 'config', 'user.name', name)
        if driver: sh(p, 'git', 'config', 'merge.rowlog.driver', DRIVER)
        return p

    def commit(self, p, msg): sh(p, 'git', 'add', '-A'); return sh(p, 'git', 'commit', '-qm', msg)

    def push_like_the_workflows(self, p):
        """the workflows' commit step: up to 6 tries of pull --rebase -X theirs, then push"""
        for _ in range(6):
            c, out = sh(p, 'git', 'pull', '-q', '--rebase', '-X', 'theirs', '--no-tags', 'origin', 'main')
            if c == 0 and sh(p, 'git', 'push', '-q', 'origin', 'HEAD:main')[0] == 0: return True
            sh(p, 'git', 'rebase', '--abort')
        return False

    def race(self, driver):
        """writer 1 (the CBB tape job) and writer 2 (the trades job) both start from the same main and append different rows"""
        w1, w2 = self.clone('w1', driver), self.clone('w2', driver)
        for f in self.files:
            append(os.path.join(w1, f), [json.dumps(dict(ts='14:23', w='w1', n=i, cond=f'a{i}', side='yes', event_id=100 + i, market='ml', line=None)) for i in range(4)])
            append(os.path.join(w2, f), [json.dumps(dict(ts='14:24', w='w2', n=i, cond=f'b{i}', side='no', event_id=200 + i, market='ml', line=None)) for i in range(5)])
        self.commit(w1, 'w1'); self.commit(w2, 'w2')
        self.assertTrue(self.push_like_the_workflows(w1)); self.assertTrue(self.push_like_the_workflows(w2))
        final = self.clone('final')
        return {f: rows(os.path.join(final, f)) for f in self.files}

    def test_control_without_driver_rows_are_lost(self):
        got = self.race(driver=False)
        self.assertTrue(any(sum('"w1"' in l for l in R) < 4 or sum('"w2"' in l for l in R) < 5 for R in got.values()),
                        'expected the old -X theirs behaviour to drop rows (the bug)')

    def test_with_driver_no_row_is_lost(self):
        got = self.race(driver=True)
        for f, R in got.items():
            self.assertEqual(sum('"seed"' in l for l in R), 3, f)
            self.assertEqual(sum('"w1"' in l for l in R), 4, f)
            self.assertEqual(sum('"w2"' in l for l in R), 5, f)
            self.assertEqual(len(R), 12, f)
            self.assertEqual(len(set(R)), 12, f)


class MergeRules(unittest.TestCase):
    def test_append_log_keeps_both_sides_in_order(self):
        O = ['a', 'b']; A = O + ['c', 'd']; B = O + ['e']
        self.assertEqual(M.merge(O, A, B), ['a', 'b', 'c', 'd', 'e'])

    def test_append_log_repeated_line_counts(self):
        O = ['x']; A = ['x', 'x']; B = ['x', 'x', 'x']
        self.assertEqual(M.merge(O, A, B).count('x'), 4)          # base 1, A added 1, B added 2

    def test_ledger_graded_row_replaces_ungraded(self):
        r = lambda **k: json.dumps(dict(dict(cond='c1', side='yes', won=None), **k))
        O = [r()]; A = [r(), json.dumps(dict(cond='c2', side='yes'))]; B = [r(won=1)]
        out = M.merge(O, A, B, ('cond', 'side'))
        self.assertEqual(len(out), 2); self.assertEqual(json.loads(out[0])['won'], 1)

    def test_ledger_changed_on_both_sides_merges_fields(self):
        O = [json.dumps(dict(key='k', won=None, close=None))]
        A = [json.dumps(dict(key='k', won=None, close=0.55))]; B = [json.dumps(dict(key='k', won=1, close=None))]
        self.assertEqual(json.loads(M.merge(O, A, B, ('key',))[0]), dict(key='k', won=1, close=0.55))

    def test_ledger_dedupe_on_one_side_is_respected(self):
        O = [json.dumps(dict(event_id=1, rule='r', n=1)), json.dumps(dict(event_id=2, rule='r'))]
        A = O[:1]; B = O + [json.dumps(dict(event_id=3, rule='r'))]
        self.assertEqual([json.loads(l)['event_id'] for l in M.merge(O, A, B, ('event_id', 'rule'))], [1, 3])

    def test_every_rewritten_ledger_has_a_key_and_a_rowlog_attribute(self):
        import fnmatch
        pats = [l.split()[0] for l in ATTR.splitlines() if 'merge=rowlog' in l]
        for p in list(M.KEYS) + ['data/cbb/ticks5/2026-11-27.jsonl.gz', 'data/kalshi/trades5/2026-11-27.jsonl.gz']:
            self.assertTrue(any(fnmatch.fnmatch(p, x.replace('**/', '*')) for x in pats), p)

    def test_every_pushing_workflow_configures_the_driver(self):
        wd = os.path.join(ROOT, '.github', 'workflows')
        for f in sorted(os.listdir(wd)):
            s = open(os.path.join(wd, f)).read()
            if 'git push' in s and 'git pull' in s:
                self.assertIn('merge.rowlog.driver', s, f)


if __name__ == '__main__':
    unittest.main()
