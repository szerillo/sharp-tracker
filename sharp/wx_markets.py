#!/usr/bin/env python3
"""Kalshi daily-high temperature markets: calibration and observation-locked brackets (Sean, 11/9).
Data (data/research/wx_kalshi): <SERIES>.markets.json + trades/ (loggers/kalshi_weather.py), obs/<station>.csv (IEM ASOS, every report),
cli/K<station>.json (IEM's copy of the NWS daily climate report, the settlement number).
Day: the CLI day is local standard time (midnight to midnight LST, so 1 AM to 1 AM during daylight time).
1. Calibration: each bracket's last trade before a clock time (evening before, 8 AM, 11 AM, 2 PM, 5 PM local), bucketed, against settlement.
2. Locked by observation: at each trade, the highest temperature reported so far that day. A bracket whose top is below it cannot win;
   an 'above X' bracket with X already reached cannot lose. Trades at a price that ignores that are the "sure thing" to measure.
   Checked first: how often the CLI high is at least the highest report (the CLI uses finer data, so it should be always).
Usage: python3 sharp/wx_markets.py"""
import os, json, gzip, glob, csv, collections, math, datetime as dt
from zoneinfo import ZoneInfo
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'research', 'wx_kalshi')
CITY = {'KXHIGHNY': ('NYC', 'America/New_York'), 'KXHIGHCHI': ('MDW', 'America/Chicago'), 'KXHIGHMIA': ('MIA', 'America/New_York'),
        'KXHIGHAUS': ('ATT', 'America/Chicago'), 'KXHIGHLAX': ('LAX', 'America/Los_Angeles'), 'KXHIGHDEN': ('DEN', 'America/Denver'),
        'KXHIGHTDC': ('DCA', 'America/New_York')}
P = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
def lst_day(t, tz):
    """the CLI day a UTC time belongs to: local standard time"""
    loc = t.astimezone(ZoneInfo(tz)); std = loc - (loc.dst() or dt.timedelta(0)); return std.date()
rows = []; locked = []; checks = collections.Counter()
for s, (st, tz) in CITY.items():
    mp = os.path.join(D, f'{s}.markets.json')
    if not os.path.exists(mp): continue
    M = json.load(open(mp)).get('markets') or []
    cli = {r['valid']: r.get('high') for r in json.load(open(os.path.join(D, 'cli', f'K{st}.json'))).get('results', []) if r.get('high') not in (None, 'M')}
    obs = collections.defaultdict(list)          # CLI day -> [(utc ts, temp F)]
    for r in csv.DictReader(open(os.path.join(D, 'obs', f'{st}.csv'))):
        try: t = dt.datetime.strptime(r['valid'], '%Y-%m-%d %H:%M').replace(tzinfo=dt.timezone.utc); v = float(r['tmpf'])
        except Exception: continue
        obs[lst_day(t, tz).isoformat()].append((t.timestamp(), v))
    for k in obs: obs[k].sort()
    for day, L in obs.items():
        if day in cli: checks['cli >= highest report' if float(cli[day]) >= max(v for _, v in L) - 0.5 else 'cli BELOW highest report'] += 1
    for m in M:
        if m.get('result') not in ('yes', 'no'): continue
        tp = os.path.join(D, 'trades', m['ticker'] + '.jsonl.gz')
        if not os.path.exists(tp): continue
        lo, hi, ty = m.get('floor_strike'), m.get('cap_strike'), m.get('strike_type')
        # bracket in whole degrees: 'greater' X -> high > X; 'less' X -> high < X; 'between' a-b -> a <= high <= b
        day = dt.datetime.strptime(m['event_ticker'].split('-')[1], '%y%b%d').date().isoformat()
        win = m['result'] == 'yes'
        T = sorted((P(t['ts']).timestamp(), t['yes'], t['n'], t['taker']) for l in gzip.open(tp, 'rt') for t in [json.loads(l)])
        O = obs.get(day, []); oi = 0; mx = None
        loc0 = dt.datetime.fromisoformat(day).replace(tzinfo=ZoneInfo(tz))
        marks = {'evening before (6 PM)': loc0 - dt.timedelta(hours=6), '8 AM': loc0 + dt.timedelta(hours=8), '11 AM': loc0 + dt.timedelta(hours=11),
                 '2 PM': loc0 + dt.timedelta(hours=14), '5 PM': loc0 + dt.timedelta(hours=17)}
        for lab, t0 in marks.items():
            pre = [x for x in T if x[0] <= t0.timestamp()]
            if pre and t0.timestamp() - pre[-1][0] < 3 * 3600: rows.append(dict(s=s, day=day, mark=lab, p=pre[-1][1], win=win))
        for ts, yes, n, tk in T:
            while oi < len(O) and O[oi][0] <= ts - 600:          # a report counts 10 minutes after its time (publication lag)
                mx = O[oi][1] if mx is None else max(mx, O[oi][1]); oi += 1
            if mx is None: continue
            m_ = round(mx)
            dead = (ty == 'less' and m_ >= lo if lo is not None else False) or (ty == 'less' and hi is not None and m_ >= hi) or \
                   (ty == 'between' and hi is not None and m_ > hi)
            sure = (ty == 'greater' and lo is not None and m_ > lo) or (ty == 'between' and False)
            if dead or sure:
                locked.append(dict(s=s, kind='dead (cannot win)' if dead else 'sure (cannot lose)', yes=yes, n=n, taker=tk, win=win, day=day))
print('CLI high vs the highest report that day:', dict(checks))
print('\n1. Calibration: bracket price at a clock time against the result')
for mark in ('evening before (6 PM)', '8 AM', '11 AM', '2 PM', '5 PM'):
    R = [r for r in rows if r['mark'] == mark]
    if not R: continue
    print(f'  {mark} ({len(R)} brackets)')
    for lo, hi in ((0, .05), (.05, .15), (.15, .3), (.3, .5), (.5, .7), (.7, .85), (.85, .95), (.95, 1.01)):
        L = [r for r in R if lo <= r['p'] < hi]
        if len(L) < 15: continue
        w = sum(r['win'] for r in L); pm = sum(r['p'] for r in L) / len(L)
        roi_y = (w - sum(r['p'] for r in L)) / sum(r['p'] for r in L); roi_n = ((len(L) - w) - sum(1 - r['p'] for r in L)) / sum(1 - r['p'] for r in L)
        print(f'    priced {lo:.2f}-{hi:.2f}: n={len(L):4}  priced {100 * pm:5.1f}%  won {100 * w / len(L):5.1f}%   buy yes {100 * roi_y:+6.1f}%   buy no {100 * roi_n:+6.1f}%')
print('\n2. Trades after the observations had already settled the bracket (report counted 10 minutes after its time)')
for kind in ('dead (cannot win)', 'sure (cannot lose)'):
    L = [x for x in locked if x['kind'] == kind]
    if not L: continue
    agree = sum(1 for x in L if x['win'] == (kind.startswith('sure')))
    print(f'  {kind}: {len(L)} trades, settled as the observations said in {agree} ({100 * agree / len(L):.2f}%)')
    for lo, hi in ((0.01, 0.02), (0.02, 0.05), (0.05, 0.15), (0.15, 0.5), (0.5, 0.95), (0.95, 0.99), (0.99, 1.0)):
        X = [x for x in L if lo <= x['yes'] < hi]
        if not X: continue
        usd = sum((x['yes'] if kind.startswith('dead') else 1 - x['yes']) * x['n'] for x in X)
        print(f'    yes traded at {lo:.2f}-{hi:.2f}: {len(X):6} trades, {sum(x["n"] for x in X):10,.0f} contracts; the riskless side was offered for ${usd:,.0f} of profit at settlement')
