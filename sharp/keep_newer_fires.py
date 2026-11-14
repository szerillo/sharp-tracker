#!/usr/bin/env python3
"""The tracker job owns data/state/system_fires.json and system_fired.json. Run after `git pull --rebase` in another job's commit step:
if main holds a newer tracker build than this job's copy, put main's files back and amend this job's commit, so a rebase with -X theirs
can never lay an older build over a newer one (11/14: the signals job did that 40 seconds after the 9:40 AM tracker run). Same rule as
the pre-commit guard: this job's small late-pass edits are redone on its next run.
Usage: python3 sharp/keep_newer_fires.py [ref]   (default origin/main)"""
import json, subprocess, sys
REF = sys.argv[1] if len(sys.argv) > 1 else 'origin/main'
F = ['data/state/system_fires.json', 'data/state/system_fired.json']
def built(txt):
    try: return json.loads(txt).get('built') or ''
    except Exception: return ''
remote = subprocess.run(['git', 'show', f'{REF}:{F[0]}'], capture_output=True, text=True).stdout
try: local = open(F[0]).read()
except Exception: local = ''
if built(remote) > built(local):
    print(f"[keep_newer_fires] {REF} has tracker build {built(remote)}, this job has {built(local)}: keeping {REF}'s system files")
    subprocess.run(['git', 'checkout', '-q', REF, '--'] + F)
    subprocess.run(['git', 'add'] + F)
    if subprocess.run(['git', 'diff', '--cached', '--quiet']).returncode != 0:
        subprocess.run(['git', 'commit', '-q', '--amend', '--no-edit'])
