"""Grade C sharp rows into a paper log (Sean, 11/8). A Grade C row (sharp accounts plus big money or a price move on the same side, no
flag) is built on the page from the live signals, so the board check, which opens the published page, is what sees it. This appends each
new one (game, market, side) to data/state/sharp_c_paper.jsonl at the price shown when first seen, and records when it was last seen
(a row can drop off when a signal against it appears). The bet tracker (sharp/bet_log.py) grades them from final scores.
Usage: python3 sharp/sharp_c_log.py board_check.json data/state/sharp_c_paper.jsonl"""
import json, os, re, sys, datetime as dt


def implied(txt):
    """first price in the price cell: American odds (+150 / -120) or cents (62¢ / 0.62)."""
    t = txt or ''
    m = re.search(r'(?<![\d.])([+-]\d{3,4})(?!\d)', t)
    if m:
        a = int(m.group(1)); return round(100 / (a + 100) if a > 0 else -a / (-a + 100), 4)
    m = re.search(r'(\d{1,2}(?:\.\d)?)\s*¢', t)
    if m: return round(float(m.group(1)) / 100, 4)
    return None


def line_of(bet, mk):
    if mk not in ('spread', 'total', '1h_spread', '1h_total') and not mk.startswith(('tt_', '1h_tt')): return None
    n = re.findall(r'[-+]?\d+(?:\.\d+)?', bet or '')
    return float(n[-1]) if n else None


def main(src, dst):
    rows = json.load(open(src)).get('sharp_c') or []
    have = {}
    if os.path.exists(dst):
        for l in open(dst):
            try: d = json.loads(l); have[d['key']] = d
            except Exception: pass
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'); new = 0
    for r in rows:
        if not r.get('ev') or not r.get('side') or not r.get('t'): continue
        start = dt.datetime.fromtimestamp(r['t'] / 1000, dt.timezone.utc)
        if start <= dt.datetime.now(dt.timezone.utc): continue           # only pregame rows
        k = f"{r['ev']}|{r['mk']}|{r['side']}"
        if k in have: have[k]['last_seen'] = now; continue
        bet = r.get('bet') or (r.get('lbl') or '').split(' · ')[0]
        have[k] = dict(key=k, event_id=r['ev'], market=r['mk'], side=r['side'], bet=bet.strip(), line=line_of(bet, r['mk']),
                       start=start.strftime('%Y-%m-%dT%H:%M:%SZ'), logged=now, last_seen=now, price=implied(r.get('price')),
                       price_text=r.get('price'), size=r.get('size'), why=(r.get('lbl') or '').split(' · ', 1)[-1][:120])
        new += 1
    with open(dst, 'w') as f:
        for d in sorted(have.values(), key=lambda d: (d['start'], d['key'])): f.write(json.dumps(d) + '\n')
    print(f'[sharp C] {len(rows)} Grade C rows on the page, {new} new; {len(have)} logged')
    return new


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
