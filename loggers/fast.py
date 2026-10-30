#!/usr/bin/env python3
"""Five-minute fast tape for the move framework: Pinnacle (with limits), Novig (best bid per outcome from the listing) and Kalshi
(top of book plus the trades since the last run), game markets only, every registry sport in one run.

  python3 loggers/fast.py --sports nfl,nba,nhl      (ticks for those sports)
  python3 loggers/fast.py --trades                  (Kalshi trade tape for every ticker any group has seen)

Reuses loggers/lines.py in LINES_FAST mode (no props, no Novig book calls, no ESPN schedule refresh: the 20-minute job owns
data/<sport>/schedule.json). Output:
  data/<sport>/ticks5/YYYY-MM-DD.jsonl.gz   same row format as ticks/, Pinnacle + Novig + Kalshi only; Kalshi rows carry extra.ticker,
                                            Novig rows extra.market_id (joined to the next-day Novig tape by sharp/moves.py)
  data/kalshi/fast_meta_<group>.json         ticker -> sport, event_id, market, line, yes side for every Kalshi game market seen
  data/kalshi/trades5/YYYY-MM-DD.jsonl.gz    (--trades) every Kalshi trade since the previous pull on a known game-market ticker, from the
                                            global trades feed (one paged call, ~20 pages per 5 minutes): ts, ticker, sport, event_id,
                                            market, line, yes_side, yes_price, count, taker_side, block
Cron jitter is real (1 to 4 min on GitHub Actions); every row carries its true timestamp and the move table works on timestamps.
Read-only. Places nothing."""
import os, sys, json, gzip, glob, time, importlib, collections, datetime as dt, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.environ['LINES_FAST'] = '1'; os.environ.setdefault('LINES_BUDGET_S', '50')
ARGS = sys.argv[1:]
SPORTS = (ARGS[ARGS.index('--sports') + 1] if '--sports' in ARGS else 'nfl,nba,cfb,nhl,soccer,mma').split(',')
KAPI = "https://api.elections.kalshi.com/trade-api/v2"
KD = os.path.join(ROOT, 'data', 'kalshi'); TR = os.path.join(KD, 'trades5'); os.makedirs(TR, exist_ok=True)
TSTATE = os.path.join(KD, 'trades_state.json')   # global trade-tape cursor; per-group ticker metadata lives in fast_meta_<group>.json
GAME = ('ml', 'spread', 'total')   # markets kept: these and their 1h_/1q_/1p_ variants; team totals and props are not move-tape markets
T0 = time.time(); T_LAST = [0.0]


def keep(r):
    m = r['market'].split('_', 1)[-1] if r['market'][:3] in ('1h_', '1q_', '1p_') else r['market']
    return m in GAME


def kget(u, tries=4):
    for i in range(tries):
        dtm = time.time() - T_LAST[0]
        if dtm < 0.3: time.sleep(0.3 - dtm)
        T_LAST[0] = time.time()
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))
        except urllib.error.HTTPError as e:
            if e.code == 404: return {}
            time.sleep(2.0 * (i + 1))
        except Exception: time.sleep(1.5 * (i + 1))
    return {}


def kalshi_trades(min_ts, max_pages=60):
    """The global trade feed since min_ts, newest first, 1000 per page (18k trades per 5 minutes on a weekday, 3% of them ours)."""
    cur = ''; out = []
    for _ in range(max_pages):
        x = kget(f"{KAPI}/markets/trades?min_ts={min_ts}&limit=1000" + (f"&cursor={cur}" if cur else ''))
        out.extend(x.get('trades', [])); cur = x.get('cursor')
        if not cur or not x.get('trades') or time.time() - T0 > 240: break
    return out


def run_sport(sport):
    """Run lines.py's venue fetchers for one sport against the schedule already on disk; return the kept rows."""
    sys.argv = ['lines.py', '--sport', sport]
    import lines as L; L = importlib.reload(L)
    L.ROWS.clear(); rows = []; counts = {}
    leagues = L.CFG.get('leagues') or {'_': {}}
    for lk, lg in leagues.items():
        if L.over_budget(): counts['budget'] = lk; break
        L.CFG.update(lg); L.CFG['league_key'] = None if lk == '_' else lk
        if not os.path.exists(L.SCHED): continue
        M = L.Matcher(json.load(open(L.SCHED)))
        for name, fn, key in (('pinnacle', L.pinnacle, 'pinnacle'), ('kalshi', L.kalshi, 'kalshi'), ('novig', L.novig, 'novig')):
            if L.CFG.get(key) is None: continue
            try: fn(M)
            except Exception as e: counts[f'{name}:{lk}'] = f'{type(e).__name__}: {e}'
    rows = ladder([r for r in L.trim(L.ROWS) if keep(r)])
    return rows, counts, L.et_date(L.NOW).isoformat()


LADDER = 3   # strikes kept per venue x event x market x side: the main line and its neighbours (exchanges list every alternate)


def ladder(rows):
    def p(r):
        if r.get('bid') is not None and r.get('ask') is not None: return (r['bid'] + r['ask']) / 2
        if r.get('ask') is not None: return r['ask']
        a = r.get('american')
        if a is not None: return 1 / (1 + a / 100) if a > 0 else 1 / (1 + 100 / -a)
        return 0.5
    out = []; by = collections.defaultdict(list)
    for r in rows:
        if r.get('line') is None or r['market'].endswith('ml'): out.append(r)
        else: by[(r['event_id'], r['venue'], r['market'], r['side'])].append(r)
    for L_ in by.values():
        L_.sort(key=lambda r: abs(p(r) - 0.5)); out.extend(L_[:LADDER])
    return out


def main():
    now = dt.datetime.now(dt.timezone.utc)
    if '--trades' in ARGS:
        meta = {}
        for f in glob.glob(os.path.join(KD, 'fast_meta_*.json')): meta.update(json.load(open(f)))
        st = json.load(open(TSTATE)) if os.path.exists(TSTATE) else {}
        since = int(st.get('last_ts') or now.timestamp() - 600)
        raw = kalshi_trades(since); rows = []; newest = since
        for t in raw:
            m = meta.get(t['ticker'])
            tt = int(dt.datetime.fromisoformat(t['created_time'].replace('Z', '+00:00')).timestamp()); newest = max(newest, tt)
            if not m: continue
            rows.append(dict(ts=t['created_time'], ticker=t['ticker'], **m, yes_price=float(t.get('yes_price_dollars') or 0), count=float(t.get('count_fp') or t.get('count') or 0),
                             taker_side=t.get('taker_side'), block=bool(t.get('is_block_trade'))))
        if rows:
            with gzip.open(os.path.join(TR, f'{now.date().isoformat()}.jsonl.gz'), 'at') as f:
                for t in rows: f.write(json.dumps(t, separators=(',', ':')) + '\n')
        json.dump({'last_ts': newest + 1 if raw else since, 'pulled': now.isoformat()}, open(TSTATE, 'w'))
        print(f"[fast trades] {round(time.time() - T0)}s; {len(raw)} trades since {since}, {len(rows)} on {len({r['ticker'] for r in rows})} known game tickers ({len(meta)} tickers in meta)")
        return
    slug = '-'.join(SPORTS); mp = os.path.join(KD, f'fast_meta_{slug}.json'); meta = json.load(open(mp)) if os.path.exists(mp) else {}
    report = []
    for sport in SPORTS:
        if time.time() - T0 > 300: report.append(f'{sport}: skipped (time)'); continue
        t_s = time.time()
        try: rows, counts, day = run_sport(sport)
        except Exception as e: report.append(f'{sport}: {type(e).__name__}: {e}'); continue
        if rows:
            d = os.path.join(ROOT, 'data', sport, 'ticks5'); os.makedirs(d, exist_ok=True)
            with gzip.open(os.path.join(d, f'{day}.jsonl.gz'), 'at') as f:
                for r in rows: f.write(json.dumps(r, separators=(',', ':')) + '\n')
        for r in rows:
            if r['venue'] != 'Kalshi' or not (r.get('extra') or {}).get('ticker'): continue
            yes = r['extra'].get('yes'); line = r.get('line') if r['side'] == yes else (-r['line'] if r.get('line') is not None and r['market'].endswith('spread') else r.get('line'))
            meta[r['extra']['ticker']] = dict(sport=sport, event_id=r['event_id'], market=r['market'], line=line, yes_side=yes, seen=day)
        byv = collections.Counter(r['venue'] for r in rows)
        report.append(f"{sport}: {len(rows)} ticks {dict(byv)} on {len({r['event_id'] for r in rows})} events in {round(time.time() - t_s)}s" + (f" {counts}" if counts else ''))
    cut = (now - dt.timedelta(days=14)).date().isoformat(); meta = {k: v for k, v in meta.items() if v.get('seen', '9') >= cut}
    json.dump(meta, open(mp, 'w'), separators=(',', ':'))
    print(f"[fast] {round(time.time() - T0)}s; " + '; '.join(report))


if __name__ == '__main__':
    main()
