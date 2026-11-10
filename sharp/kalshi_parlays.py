#!/usr/bin/env python3
"""What do parlay makers earn? (Sean 11/10: "think offering parlays even more lucrative".) Kalshi lists every parlay ("multivariate
event") as its own market, public, with its legs and its settled result. A parlay is quoted on request and usually trades once: the
taker buys YES (every leg hits) and the maker holds NO. For every settled parlay with volume: the price paid (last trade), contracts,
legs, result. Maker profit per contract = price - 1 if it hit, else price. Summed by collection, sport of the legs, number of legs and
price. No Kalshi fee is applied (fees on these differ by product; shown before fees).
A sample of markets is checked against the trade tape for the assumption that the taker is on YES.
Usage: python3 sharp/kalshi_parlays.py [pages_per_hour] [days] [skip_days] [out_file]   -> data/research/kalshi_parlays.json"""
import os, sys, json, time, collections, urllib.request, urllib.error
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
API = 'https://api.elections.kalshi.com/trade-api/v2'
MAXP = int(sys.argv[1]) if len(sys.argv) > 1 else 400
SPORT = (('KXNFL', 'NFL'), ('KXNBA', 'NBA'), ('KXNHL', 'NHL'), ('KXNCAAF', 'CFB'), ('KXNCAAMB', 'CBB'), ('KXNCAAB', 'CBB'), ('KXMLB', 'MLB'), ('KXUFC', 'UFC'), ('KXEPL', 'soccer'), ('KXUCL', 'soccer'),
         ('KXLALIGA', 'soccer'), ('KXMLS', 'soccer'), ('KXATP', 'tennis'), ('KXWTA', 'tennis'))


def get(u):
    for i in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + u, headers={'User-Agent': 'sharp-tracker'}), timeout=40) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 * (i + 1)); continue
            return None
        except Exception: time.sleep(2 + i)
    return None


def sport_of(legs):
    s = set()
    for l in legs:
        t = l.get('market_ticker') or ''
        s.add(next((n for p, n in SPORT if t.startswith(p)), 'other'))
    return next(iter(s)) if len(s) == 1 else ('mixed sports' if 'other' not in s else 'mixed / other')


class Acc:
    def __init__(s): s.n = 0; s.c = 0.0; s.take = 0.0; s.put = 0.0; s.pnl = 0.0; s.hit = 0; s.days = collections.defaultdict(float); s.sq = 0.0
    def add(s, p, c, res, day):
        x = (p - res) * c; s.n += 1; s.c += c; s.take += p * c; s.put += (1 - p) * c; s.pnl += x; s.hit += res; s.days[day] += x
    def out(s):
        d = list(s.days.values()); z = None
        if len(d) >= 8:
            m = sum(d) / len(d); sd = (sum((v - m) ** 2 for v in d) / (len(d) - 1)) ** 0.5; z = round(m / (sd / len(d) ** 0.5), 2) if sd else None
        return dict(parlays=s.n, contracts=round(s.c), taker_paid=round(s.take), maker_put_up=round(s.put), maker_pnl=round(s.pnl), taker_roi=round(-100 * s.pnl / s.take, 1) if s.take else None,
                    maker_roi=round(100 * s.pnl / s.put, 2) if s.put else None, hold=round(100 * s.pnl / s.take, 1) if s.take else None, hit_rate=round(100 * s.hit / s.n, 1) if s.n else None,
                    avg_price=round(100 * s.take / s.c, 1) if s.c else None, days=len(d), z_by_day=z, pnl_per_day=round(s.pnl / max(1, len(d))))


def main():
    A = collections.defaultdict(Acc); seen = collections.Counter(); sample = []; days = set()
    # 11/10: one day of the unfiltered listing is 400,000 markets (mostly 15-minute crypto and FX parlays), so sports history is pulled
    # by series: same-game and multi-game parlay series, up to MAXP pages each.
    SERIES = sys.argv[2].split(',') if len(sys.argv) > 2 else ['KXMVENFLSINGLEGAME', 'KXMVENBASINGLEGAME', 'KXMVENFLMULTIGAMEEXTENDED', 'KXMVENBAMULTIGAMEEXTENDED', 'KXMVESPORTSMULTIGAMEEXTENDED', 'KXMVENFLMULTIGAME']
    # 11/10: the series filter returns almost nothing (sports parlays sit in the cross-category collection with everything else), so the
    # history is a sample: for each of the last DAYS days, each hour's first PER pages of parlays settled in that hour.
    import datetime as dt
    DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 14; PER = MAXP
    now = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    SKIP = int(sys.argv[3]) if len(sys.argv) > 3 else 0            # days back to start from (an older, separate sample)
    OUTF = os.path.join(ROOT, 'data', 'research', sys.argv[4] if len(sys.argv) > 4 else 'kalshi_parlays.json')
    WIN = [(int((now - dt.timedelta(hours=h + 1)).timestamp()), int((now - dt.timedelta(hours=h)).timestamp())) for h in range(SKIP * 24, (SKIP + DAYS) * 24)]
    for (lo, hi), page in ((w_, p_) for w_ in WIN for p_ in range(PER)):
        ser = 'sample'
        if page == 0: cur = ''; stop = False
        if stop: continue
        d = get(f'/markets?mve_filter=only&status=settled&limit=1000&min_settled_ts={lo}&max_settled_ts={hi}' + (f'&cursor={cur}' if cur else ''))
        if not d: seen['page failed'] += 1; stop = True; continue
        for m in d.get('markets') or []:
            seen['markets'] += 1
            res = m.get('result'); vol = float(m.get('volume_fp') or m.get('volume') or 0)
            try: p = float(m.get('last_price_dollars') or 0)
            except Exception: p = 0
            if res not in ('yes', 'no') or vol <= 0 or not 0.005 <= p <= 0.995: seen['no result, volume or price'] += 1; continue
            legs = m.get('mve_selected_legs') or []; day = dt.datetime.fromtimestamp(lo, dt.timezone.utc).strftime('%Y-%m-%d'); days.add(day)
            r = 1.0 if res == 'yes' else 0.0; sp = sport_of(legs); nl = len(legs); col = (m.get('mve_collection_ticker') or '?')
            games = len({l.get('event_ticker') for l in legs})
            is_sport = sp not in ('other', 'mixed / other')
            for key in (('all',), ('kind', 'sports legs only' if is_sport else 'other or mixed'), ('sport', sp), ('legs', '2' if nl == 2 else '3' if nl == 3 else '4-5' if nl <= 5 else '6+'),
                        ('games', 'same game' if games == 1 else 'two games' if games == 2 else '3+ games'),
                        ('price', 'under 5c' if p < .05 else '5-15c' if p < .15 else '15-30c' if p < .3 else '30-50c' if p < .5 else '50c+'),
                        ('sport legs', sp, '2' if nl == 2 else '3' if nl == 3 else '4+'), ('sport price', sp, 'under 15c' if p < .15 else '15-50c' if p < .5 else '50c+'),
                        ('sport games', sp, 'same game' if games == 1 else 'multi game'), ('month', day[:7])):
                A[key].add(p, vol, r, day)
            if len(sample) < 60 and seen['markets'] % 500 == 7: sample.append(m['ticker'])
        cur = d.get('cursor')
        if not cur or not d.get('markets'): stop = True
        if page == 0 and WIN.index((lo, hi)) % 24 == 0:
            json.dump(dict(partial=True, seen=dict(seen), days=[min(days) if days else None, max(days) if days else None, len(days)], rows={' | '.join(k): a.out() for k, a in A.items()}), open(OUTF, 'w'), indent=0)
            print(f'window {WIN.index((lo, hi))} of {len(WIN)}: {dict(seen)}; days {min(days) if days else None} to {max(days) if days else None}', flush=True)
        time.sleep(0.2)
    # check: is the taker on YES, and is there one trade per parlay?
    ty = tn = one = 0
    for tk in sample:
        t = get(f'/markets/trades?ticker={tk}&limit=100'); time.sleep(0.3)
        T = (t or {}).get('trades') or []
        if not T: continue
        one += 1 if len(T) == 1 else 0
        for x in T: ty += x.get('taker_side') == 'yes'; tn += x.get('taker_side') == 'no'
    out = dict(seen=dict(seen), days=[min(days) if days else None, max(days) if days else None, len(days)], check=dict(sampled=len(sample), single_trade=one, taker_yes=ty, taker_no=tn),
               rows={' | '.join(k): a.out() for k, a in A.items()})
    json.dump(out, open(OUTF, 'w'), indent=0)
    print(out['seen'], out['days'], out['check'])
    for k in sorted(out['rows']):
        r = out['rows'][k]
        if r['parlays'] >= 150: print(f"{k:<46} parlays {r['parlays']:>8} taker paid ${r['taker_paid']:>11,} maker put up ${r['maker_put_up']:>12,} | maker P&L ${r['maker_pnl']:>10,} = {str(r['hold']):>6}% of what takers paid, {str(r['maker_roi']):>6}% of what makers put up (z {r['z_by_day']}, {r['days']} days) | hit {r['hit_rate']}% avg price {r['avg_price']}c")


if __name__ == '__main__': main()
