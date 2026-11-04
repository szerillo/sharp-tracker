#!/usr/bin/env python3
"""Live fills by the Polymarket sharp accounts (Sean, 11/2: follow the sharps). Every 5 minutes (prices_fast, trades group): for each
account on data/state/poly_sharps_list.json (top 200 by CLV, sharp/poly_rescore.py), pull its recent taker fills from
data-api.polymarket.com, keep pregame fills on game moneylines / spreads / totals (no UFC: the backtest was negative there) of $100+
risk-equivalent (shares x min(p, 1-p)), and append them to data/polymarket/sharp_fills.jsonl. Market metadata (question, type, line,
outcomes, tokens, start) comes from the Gamma API and is cached in data/polymarket/_sharp_meta.json.
Usage: python3 loggers/poly_sharps.py"""
import os, json, time, datetime as dt, urllib.request, urllib.error, concurrent.futures as cf
import polydata                      # Data API v2 (v1 retired 11/2 and returned 410: no fills were logged 11/2 evening to 11/4)
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
PD = os.path.join(ROOT, 'data', 'polymarket'); LIST = os.path.join(ROOT, 'data', 'state', 'poly_sharps_list.json')
OUT = os.path.join(PD, 'sharp_fills.jsonl'); PROPS = os.path.join(PD, 'sharp_prop_fills.jsonl'); META = os.path.join(PD, '_sharp_meta.json'); STATE = os.path.join(PD, '_sharp_state.json')
D = "https://data-api.polymarket.com"; G = "https://gamma-api.polymarket.com"; MIN_USD = 100.0
LEAGUES = {'nfl', 'nba', 'nhl', 'cfb', 'cbb', 'mlb', 'wnba', 'epl', 'bun', 'ucl', 'mls'}   # cbb added 11/2: top 200 +0.39 CLV (z 3.0) on 2025-26
TYPES = {'moneyline': 'ml', 'spreads': 'spread', 'totals': 'total'}


def g(u):
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'sharp-tracker'}), timeout=25))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 * (i + 1)); continue
            return None
        except Exception: time.sleep(1 + i)
    return None


def main():
    if not os.path.exists(LIST): print('[poly_sharps] no account list'); return
    LS = json.load(open(LIST)); acc = {a['w']: a for a in LS['accounts']}
    for sp_ in LS.get('specialists') or []: acc.setdefault(sp_['w'], dict(w=sp_['w'], rank=None, specialist=sp_['sports']))   # logged, not flagged (11/2: archive to test)
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    meta = json.load(open(META)) if os.path.exists(META) else {}
    with cf.ThreadPoolExecutor(16) as ex:     # 414 accounts on the v2 API: 8 threads took 2.5 min and pushed the trades job past its limit (11/4)
        res = dict(zip(acc, ex.map(lambda w: polydata.trades(user=w, limit=100), acc)))
    need = {t['conditionId'] for T in res.values() for t in T if t.get('conditionId') and (t['conditionId'] not in meta or 'stat' not in meta[t['conditionId']])}
    need = list(need)
    for i in range(0, len(need), 20):
        M = g(f"{G}/markets?" + '&'.join(f'condition_ids={c}' for c in need[i:i + 20])) or []
        for m in M:
            try: outs = json.loads(m.get('outcomes') or '[]'); toks = json.loads(m.get('clobTokenIds') or '[]')
            except Exception: outs, toks = [], []
            meta[m['conditionId']] = dict(type=TYPES.get(m.get('sportsMarketType')), stat=m.get('sportsMarketType'), q=m.get('question'), line=m.get('line'), outcomes=outs, tokens=toks,
                                          start=m.get('gameStartTime'), slug=(m.get('events') or [{}])[0].get('slug') or m.get('slug'),
                                          title=(m.get('events') or [{}])[0].get('title'))
        for c in need[i:i + 20]: meta.setdefault(c, dict(type=None))
    seen = set()
    if os.path.exists(OUT):
        for l in open(OUT):
            try: r = json.loads(l); seen.add((r['tx'], r['cond'], r['outcome']))
            except Exception: pass
    new = []; props = []
    for w, T in res.items():
        last = st.get(w, 0)
        for t in T:
            ts = int(t.get('timestamp') or 0); c = t.get('conditionId'); m = meta.get(c) or {}
            if ts <= last or not m.get('start') or len(m.get('outcomes') or []) != 2: continue
            prop = not m.get('type') and bool(m.get('stat'))                # player / game props: archived only (11/2), never flagged
            if not m.get('type') and not prop: continue
            if not prop and (m.get('slug') or '').split('-')[0] not in LEAGUES: continue      # game lines: only leagues in the backtest
            start = dt.datetime.fromisoformat(m['start'].replace(' ', 'T').replace('+00', '+00:00')).timestamp()
            if ts >= start: continue
            p = float(t['price']); usd = float(t['size']) * min(p, 1 - p)
            if usd < MIN_USD or not 0.01 <= p <= 0.99: continue
            o = t.get('outcome'); outs = m['outcomes']
            if o not in outs: continue
            bet = o if t['side'] == 'BUY' else outs[1 - outs.index(o)]
            price = p if t['side'] == 'BUY' else 1 - p                 # what the account paid for the side it now holds
            k = (t.get('transactionHash'), c, o)
            if k in seen: continue
            seen.add(k)
            spk = {'epl': 'soccer', 'ucl': 'soccer', 'mls': 'soccer', 'bun': 'soccer'}.get(m['slug'].split('-')[0], m['slug'].split('-')[0])
            if prop:
                props.append(dict(ts=ts, w=w, rank=acc[w]['rank'], specialist=bool(acc[w].get('specialist')), cond=c, slug=m['slug'], stat=m['stat'], q=m.get('q'),
                                  line=m.get('line'), outcomes=outs, bet=bet, price=round(price, 4), usd=round(usd, 2), start=m['start'], tx=t.get('transactionHash')))
                continue
            new.append(dict(ts=ts, w=w, rank=acc[w]['rank'], both=spk in (acc[w].get('sport_top50') or []), specialist=bool(acc[w].get('specialist')), cond=c, slug=m['slug'], title=m.get('title'), mtype=m['type'], q=m.get('q'), line=m.get('line'),
                            outcomes=outs, outcome=o, side=t['side'], bet=bet, price=round(price, 4), size=float(t['size']), usd=round(usd, 2),
                            start=m['start'], tx=t.get('transactionHash')))
        if T: st[w] = max([last] + [int(t.get('timestamp') or 0) for t in T])
    with open(OUT, 'a') as f:
        for r in sorted(new, key=lambda r: r['ts']): f.write(json.dumps(r) + '\n')
    with open(PROPS, 'a') as f:                                      # prop fills: built up for a later test (Polymarket props were too thin on 11/2)
        for r in sorted(props, key=lambda r: r['ts']): f.write(json.dumps(r) + '\n')
    json.dump(st, open(STATE, 'w')); json.dump(meta, open(META, 'w'), separators=(',', ':'))
    print(f"[poly_sharps] {len(acc)} accounts, {sum(len(T) for T in res.values())} recent fills, {len(new)} new pregame game-line fills and {len(props)} prop fills of ${MIN_USD:.0f}+")


if __name__ == '__main__':
    main()
