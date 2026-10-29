#!/usr/bin/env python3
"""Raw-tick roll-off: the repo keeps a rolling KEEP_DAYS window of per-sport tick files (data/<sport>/ticks/*.jsonl.gz) and the Novig
daily summaries; older files are uploaded to the GitHub release `raw-archive` (one asset per file) and removed from the tree.
Grading is incremental (closes.jsonl.gz persists), so nothing downstream needs the old raw ticks. Dry run with --dry.
Needs `gh` and GITHUB_TOKEN (Actions provides both); without them it only reports."""
import os, sys, glob, subprocess, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
KEEP_DAYS = int(os.environ.get('ROLLOFF_KEEP_DAYS', 10)); REL = 'raw-archive'; DRY = '--dry' in sys.argv
PATTERNS = ['data/nfl/ticks/*.jsonl.gz', 'data/nba/ticks/*.jsonl.gz', 'data/cfb/ticks/*.jsonl.gz', 'data/polymarket/*.jsonl']


def main():
    cutoff = (dt.date.today() - dt.timedelta(days=KEEP_DAYS)).isoformat(); todo = []
    for pat in PATTERNS:
        for f in sorted(glob.glob(os.path.join(ROOT, pat))):
            day = os.path.basename(f)[:10]
            if day < cutoff and day[:4].isdigit(): todo.append(f)
    if not todo: print(f'[rolloff] nothing older than {cutoff}'); return
    have_gh = subprocess.run(['gh', 'auth', 'status'], capture_output=True).returncode == 0 or os.environ.get('GITHUB_TOKEN')
    if DRY or not have_gh:
        print(f"[rolloff] {'dry run' if DRY else 'no gh auth'}: would archive {len(todo)} files: " + ', '.join(os.path.relpath(f, ROOT) for f in todo[:6])); return
    subprocess.run(['gh', 'release', 'view', REL], capture_output=True) .returncode == 0 or subprocess.run(['gh', 'release', 'create', REL, '--title', 'raw tick archive', '--notes', 'Rolled-off raw price logs, one asset per sport-day. Named <sport>__<file>.'], check=True)
    n = 0
    for f in todo:
        sport = os.path.relpath(f, ROOT).split('/')[1]; name = f"{sport}__{os.path.basename(f)}"
        if subprocess.run(['gh', 'release', 'upload', REL, f"{f}#{name}", '--clobber'], capture_output=True).returncode == 0:
            subprocess.run(['git', 'rm', '-q', os.path.relpath(f, ROOT)], cwd=ROOT); n += 1
        else: print(f'[rolloff] upload failed, kept {f}')
    print(f'[rolloff] archived {n}/{len(todo)} files older than {cutoff} to release {REL}')


if __name__ == '__main__':
    main()
