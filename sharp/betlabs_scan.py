"""Scores a Bet Labs value-distribution scan (sharp/betlabs_scan.js collected in the browser): per filter, the best contiguous window
in train, graded on the holdout, same rules as docs/betlabs_nfl_audit_2026-10-25.md. Input: data/betlabs/<key>.json {items,tr,ho,lt,...}.
python3 -m sharp.betlabs_scan data/betlabs/nhl_ou_under.json  -> markdown table on stdout"""
import json, sys, math

BE = 0.5238


def num(v):
    try: return float(v)
    except Exception: return None


def z_win(w, l):
    n = w + l
    return 0.0 if n == 0 else (w / n - BE) / math.sqrt(BE * (1 - BE) / n)


def roi(w, l, u):
    n = w + l
    return 0.0 if n == 0 else u / (100.0 * n)


def z_roi(w, l, u):
    n = w + l
    return 0.0 if n == 0 else roi(w, l, u) * math.sqrt(n) / 1.1


def score(rows, ml):
    w = sum(r['w'] for r in rows); l = sum(r['l'] for r in rows); u = sum(r['u'] for r in rows)
    return dict(n=w + l, w=w, l=l, win=(w / (w + l) if w + l else 0), roi=roi(w, l, u), z=(z_roi(w, l, u) if ml else z_win(w, l)))


def best_window(rows, ml, min_n):
    rows = [r for r in rows if num(r['v']) is not None]; rows.sort(key=lambda r: num(r['v']))
    best = None; tops = []
    for i in range(len(rows)):
        for j in range(i, len(rows)):
            seg = rows[i:j + 1]; s = score(seg, ml)
            if s['n'] < min_n: continue
            s.update(lo=num(rows[i]['v']), hi=num(rows[j]['v']))
            tops.append(s)
            if best is None or s['z'] > best['z']: best = s
    tops.sort(key=lambda s: -s['z'])
    return best, tops[:40]


def grade(rows, lo, hi, ml):
    seg = [r for r in rows if num(r['v']) is not None and lo <= num(r['v']) <= hi]
    return score(seg, ml)


def run(path, min_n=None):
    d = json.load(open(path)); ml = d['lt'] == 2; min_n = min_n or (300 if d['sport'] == 1 else 500)
    out = []
    for it in d['items']:
        tr = d['tr'].get(str(it['id'])); ho = d['ho'].get(str(it['id']))
        if not tr or not ho: continue
        if it['type'] in ('range', 'dualrange'):
            best, tops = best_window(tr, ml, min_n)
            if not best: continue
            h = grade(ho, best['lo'], best['hi'], ml)
            flips = sum(1 for t in tops if (grade(ho, t['lo'], t['hi'], ml)['roi'] <= 0))
            out.append(dict(item=it['name'], kind='range', lo=best['lo'], hi=best['hi'], tr=best, ho=h, flips=f"{flips}/{len(tops)}",
                            alive=bool(best['roi'] > 0 and h['roi'] > 0 and h['n'] >= 100)))
        else:
            hv = {r['v']: r for r in ho}
            for r in tr:
                s = score([r], ml)
                if s['n'] < min_n: continue
                h = score([hv[r['v']]], ml) if r['v'] in hv else dict(n=0, win=0, roi=0, z=0)
                out.append(dict(item=it['name'] + ' = ' + str(r['v']), kind='list', lo=None, hi=None, tr=s, ho=h, flips='',
                                alive=bool(s['roi'] > 0 and h['roi'] > 0 and h['n'] >= 100 and s['z'] > 1.5)))
    out.sort(key=lambda r: -r['tr']['z'])
    return d, out


def md(d, out, top=25):
    L = [f"### {d['name']} ({'ML' if d['lt'] == 2 else 'spread' if d['lt'] == 1 else 'O/U'}, segment {d['eo']}, side {d.get('side')}): {len(out)} filters scanned",
         "| rank | filter | window | train n / win% / ROI / z | holdout n / win% / ROI | top-40 flips | call |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(out[:top]):
        w = f"{r['lo']:g}..{r['hi']:g}" if r['kind'] == 'range' else ''
        L.append(f"| {i + 1} | {r['item']} | {w} | {r['tr']['n']} / {100 * r['tr']['win']:.1f} / {100 * r['tr']['roi']:+.1f}% / {r['tr']['z']:.2f} | {r['ho']['n']} / {100 * r['ho']['win']:.1f} / {100 * r['ho']['roi']:+.1f}% | {r['flips']} | {'ALIVE' if r['alive'] else 'dead'} |")
    alive = [r for r in out if r['alive']]
    L.append(f"\nSurvivors (positive both halves, holdout n >= 100): {len(alive)} of {len(out)}; " + '; '.join(f"{r['item']} {('%g..%g' % (r['lo'], r['hi'])) if r['kind'] == 'range' else ''} (hold {r['ho']['n']}, {100 * r['ho']['roi']:+.1f}%)" for r in alive[:12]))
    return '\n'.join(L)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        d, out = run(p); print(md(d, out)); print()
