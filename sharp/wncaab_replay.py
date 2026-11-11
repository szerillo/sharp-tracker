#!/usr/bin/env python3
"""Women's college basketball spread replay (rebuilds the 11/9 test in docs/wncaab_mma_2026-11-09.md, whose script was not saved).
Odds API history (data/oddsapi/compact/wncaab.jsonl.gz, US books only: there is no Pinnacle in this sport), ESPN results
(data/state/hist_schedule.json), names matched through data/state/espn_teams.json the way sharp/odds_db.py does.
Per game: the line is the median home spread across books (BetMGM left out); open = the first snapshot, close = the last snapshot
before the start; 3+ books at the close. Bets at the best price among books on the median number.
  move_follow: the median spread moved 1+ point open to close; bet the side it moved toward, at the close.
  dog_7_10: the closing dog is +7 to +10; bet the dog.
Usage: python3 sharp/wncaab_replay.py [compact] [hist_schedule] [espn_teams]   -> data/research/wncaab_replay.json"""
import os, sys, json, gzip, statistics, collections, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, ROOT)
from sharp.oddsapi_edge import norm
A = sys.argv[1:] + [None] * 3
SRC = A[0] or os.path.join(ROOT, 'data', 'oddsapi', 'compact', 'wncaab.jsonl.gz')
HIST = A[1] or os.path.join(ROOT, 'data', 'state', 'hist_schedule.json'); TEAMS = A[2] or os.path.join(ROOT, 'data', 'state', 'espn_teams.json')
SKIP_BOOKS = ('betmgm',)
ONE_SNAP = os.environ.get('WNC_ONE_SNAP', '1') == '1' # games with one snapshot before the start count (open = close); this is how the 11/9 test counted (it reproduces the dog cell exactly)
NEAR = os.environ.get('WNC_NEAR') == '1'
POST = os.environ.get('WNC_POST') == '1'             # 11/10 check only: let the close be a snapshot taken after the start (in-game lines; look-ahead)             # 11/10 check: no book on the median number -> the posted number nearest it


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00') if s.endswith('Z') else s)


def season(t): return f"{t.year}-{str(t.year + 1)[2:]}" if t.month >= 8 else f"{t.year - 1}-{str(t.year)[2:]}"


def snap(books):
    """median home spread across books and, per book, (home line, home dec, away dec)"""
    L = {b: v['sp'] for b, v in books.items() if b not in SKIP_BOOKS and v.get('sp') and v['sp'][0] is not None}
    if not L: return None, {}
    return statistics.median(x[0] for x in L.values()), L


def best_at(L, med, side):
    ok = [(v[1] if side == 'home' else v[2], b) for b, v in L.items() if abs(v[0] - med) < 1e-9]
    if not ok and NEAR:
        d = min(abs(v[0] - med) for v in L.values()); ok = [(v[1] if side == 'home' else v[2], b, v[0]) for b, v in L.items() if abs(abs(v[0] - med) - d) < 1e-9]
        ok = [max(ok, key=lambda z: (z[2] if side == 'home' else -z[2], z[0]))]          # of the nearest numbers, the one better for the bettor
        return ok[0]
    return max(ok) + (med,) if ok else None


def main():
    G = collections.defaultdict(list)
    for l in gzip.open(SRC, 'rt'):
        try: x = json.loads(l)
        except Exception: continue
        G[x['id']].append(x)
    T = json.load(open(TEAMS)).get('wncaab', {}); alt = {}
    for ab, t in T.items():
        for k in (t.get('name'), (t.get('loc') or '') + ' ' + (t.get('nick') or ''), t.get('short')):
            if k: alt[norm(k)] = ab
    def abbr(name):
        n = norm(name)
        if n in alt: return alt[n]
        best = None
        for k, v in alt.items():
            if len(k) >= 6 and (k in n or n in k) and (best is None or len(k) > len(best[0])): best = (k, v)
        return best[1] if best else None
    idx = collections.defaultdict(list)
    for eid, h in (json.load(open(HIST)).get('wncaab') or {}).items():
        if h.get('hs') is not None and h.get('final', True): idx[(h['home'], h['away'])].append(h)
    R = collections.defaultdict(lambda: dict(n=0, w=0, l=0, p=0, u=0.0, seasons=collections.defaultdict(float)))
    seen = collections.Counter(); picks = []
    for gid, S in G.items():
        S.sort(key=lambda s: s['t']); st = ts(S[0]['start'])
        pre = [s for s in S if ts(s['t']) < st] if not POST else list(S)
        if len(pre) < (1 if ONE_SNAP else 2): seen['fewer than 2 snapshots before the start'] += 1; continue
        o_med, _ = snap(pre[0]['books']); c_med, L = snap(pre[-1]['books'])
        if o_med is None or c_med is None or len(L) < 3: seen['under 3 books at the close'] += 1; continue
        ha, aa = abbr(S[0]['home']), abbr(S[0]['away']); res = None
        for h in idx.get((ha, aa), []):
            if abs((ts(h['start'] if len(h['start']) > 17 else h['start'].replace('Z', ':00Z')) - st).total_seconds()) < 6 * 3600: res = h; break
        if not res: seen['no result'] += 1; continue
        # 11/10: the close must be before ESPN's tip as well as the Odds API's listed start (a listed start later than the real tip
        # would let in-game lines in as the "close")
        tip = ts(res['start'] if len(res['start']) > 17 else res['start'].replace('Z', ':00Z'))
        if not POST and tip < st:
            pre2 = [s for s in S if ts(s['t']) < tip]
            seen['listed start later than ESPN tip'] += 1
            if len(pre2) < len(pre):
                seen['close moved back to before ESPN tip'] += 1
                if not pre2 or (not ONE_SNAP and len(pre2) < 2): seen['no snapshot before ESPN tip'] += 1; continue
                pre = pre2; o_med, _ = snap(pre[0]['books']); c_med, L = snap(pre[-1]['books'])
                if o_med is None or c_med is None or len(L) < 3: seen['under 3 books at the close'] += 1; continue
        seen['graded'] += 1; margin = res['hs'] - res['as_']; sz = season(st)
        bets = []
        mv = c_med - o_med                                  # home spread: negative = home became a bigger favourite
        if abs(mv) >= 1: bets.append(('move_follow', 'home' if mv < 0 else 'away'))
        dog = 'home' if c_med > 0 else 'away' if c_med < 0 else None
        if dog and 7 <= abs(c_med) <= 10: bets.append(('dog_7_10', dog))
        for rule, side in bets:
            b = best_at(L, c_med, side)
            if not b: seen[f'{rule}: no book on the median number'] += 1; continue
            dec, bk, ln = b; cov = (margin + ln) if side == 'home' else (-margin - ln)
            r = R[rule]; r['n'] += 1
            if cov > 0: r['w'] += 1; u = dec - 1
            elif cov < 0: r['l'] += 1; u = -1.0
            else: r['p'] += 1; u = 0.0
            r['u'] += u; r['seasons'][sz] += u
            picks.append(dict(rule=rule, id=gid, start=S[0]['start'], game=f"{S[0]['away']} @ {S[0]['home']}", side=side, open=o_med, close=c_med, book=bk, dec=dec, cover=cov, units=round(u, 3)))
    out = dict(seen=dict(seen), rules={k: dict(bets=v['n'], record=f"{v['w']}-{v['l']}" + (f"-{v['p']}" if v['p'] else ''), units=round(v['u'], 2),
                                              roi=round(100 * v['u'] / max(1, v['w'] + v['l']), 1), seasons={s: round(x, 2) for s, x in sorted(v['seasons'].items())}) for k, v in R.items()})
    json.dump(dict(out, picks=picks), open(os.path.join(ROOT, 'data', 'research', 'wncaab_replay.json'), 'w'), indent=0)
    print(json.dumps(out, indent=1))


if __name__ == '__main__': main()
