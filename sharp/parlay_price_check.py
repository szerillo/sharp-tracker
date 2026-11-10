#!/usr/bin/env python3
"""Check on sharp/kalshi_parlays.py (11/10): that script scores every contract of a parlay at its LAST price with the taker on YES.
Here, for a sample of settled two- and three-leg parlays, every trade is read off the tape and the maker is scored exactly (each
trade at its own price, on the side the maker actually held), next to the shortcut for the same parlays.
Usage: python3 sharp/parlay_price_check.py [n] [hours_back]   -> data/research/parlay_price_check.json"""
import os, sys, json, time, urllib.request, urllib.error
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
API = 'https://api.elections.kalshi.com/trade-api/v2'
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300; BACK = int(sys.argv[2]) if len(sys.argv) > 2 else 20


def get(u):
    for i in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + u, headers={'User-Agent': 'sharp-tracker'}), timeout=30) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 * (i + 1)); continue
            return None
        except Exception: time.sleep(1 + i)
    return None


def main():
    now = int(time.time()) // 3600 * 3600; M = []
    for h in range(BACK, BACK + 72, 3):                       # every third hour over three days, so several slates are in the sample
        d = get(f'/markets?mve_filter=only&status=settled&limit=1000&min_settled_ts={now - (h + 1) * 3600}&max_settled_ts={now - h * 3600}') or {}
        for m in d.get('markets') or []:
            try: p = float(m.get('last_price_dollars') or 0); v = float(m.get('volume_fp') or 0)
            except Exception: continue
            if m.get('result') in ('yes', 'no') and v > 0 and 0.005 <= p <= 0.995 and 2 <= len(m.get('mve_selected_legs') or []) <= 3: M.append((m['ticker'], p, v, 1.0 if m['result'] == 'yes' else 0.0, len(m['mve_selected_legs'])))
        time.sleep(0.3)
    step = max(1, len(M) // N); M = M[::step][:N]
    A = {k: dict(n=0, stake_s=0.0, pnl_s=0.0, stake_x=0.0, pnl_x=0.0, vol_tape=0.0, vol_listed=0.0, no_taker=0.0) for k in ('all', '2 legs', '3 legs')}
    for tk, p, v, res, nl in M:
        T = []; cur = ''
        for _ in range(5):
            d = get(f'/markets/trades?ticker={tk}&limit=1000' + (f'&cursor={cur}' if cur else '')) or {}
            T += d.get('trades') or []; cur = d.get('cursor')
            if not cur: break
        time.sleep(0.12)
        if not T: continue
        for k in ('all', f'{nl} legs'):
            a = A[k]; a['n'] += 1; a['stake_s'] += p * v; a['pnl_s'] += (p - res) * v; a['vol_listed'] += v
            for t in T:
                c = float(t['count_fp']); yp = float(t['yes_price_dollars']); a['vol_tape'] += c
                if t.get('taker_side') == 'yes': a['stake_x'] += yp * c; a['pnl_x'] += (yp - res) * c                 # maker sold YES at yp
                else: a['stake_x'] += (1 - yp) * c; a['pnl_x'] += (res - yp) * c; a['no_taker'] += c                   # maker bought YES at yp
    out = {k: dict(parlays=a['n'], shortcut_pct_of_stakes=round(100 * a['pnl_s'] / a['stake_s'], 1) if a['stake_s'] else None, exact_pct_of_stakes=round(100 * a['pnl_x'] / a['stake_x'], 1) if a['stake_x'] else None,
                   shortcut_stakes=round(a['stake_s']), exact_stakes=round(a['stake_x']), contracts_on_tape_vs_listed=round(a['vol_tape'] / a['vol_listed'], 3) if a['vol_listed'] else None,
                   share_of_contracts_taker_on_no=round(a['no_taker'] / a['vol_tape'], 3) if a['vol_tape'] else None) for k, a in A.items()}
    json.dump(out, open(os.path.join(ROOT, 'data', 'research', 'parlay_price_check.json'), 'w'), indent=0)
    for k, r in out.items(): print(k, r)


if __name__ == '__main__': main()
