#!/usr/bin/env python3
"""ProphetX (Sean 11/10: "we can also test ProphetX"; third exchange for the offer scan and the maker tests). Keys come only from the
environment (GitHub secrets PROPHETX_KEY and, if set, PROPHETX_SECRET); nothing is printed or stored.
Two ways in, tried in this order:
  1. market-data key: the key alone as the Authorization header on /partner/affiliate/* (docs.prophetx.co, Market Data Integration)
  2. token pair: POST /partner/auth/login {access_key, secret_key} -> a session token, then /partner/mm/* (the trading API's read side)
Usage: python3 loggers/prophetx.py probe      # which way works, and the shape of what comes back (no prices stored)"""
import os, sys, json, time, urllib.request, urllib.parse, urllib.error
BASE = 'https://cash.api.prophetx.co/partner'
KEY = os.environ.get('PROPHETX_KEY') or ''; SEC = os.environ.get('PROPHETX_SECRET') or ''


def call(path, params=None, headers=None, body=None):
    u = BASE + path + ('?' + urllib.parse.urlencode(params, doseq=True) if params else '')
    h = {'User-Agent': 'sharp-tracker', 'Accept': 'application/json'}; h.update(headers or {})
    data = None
    if body is not None: data = json.dumps(body).encode(); h['Content-Type'] = 'application/json'
    try:
        with urllib.request.urlopen(urllib.request.Request(u, data=data, headers=h, method='POST' if body is not None else 'GET'), timeout=40) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try: msg = e.read().decode()[:300]
        except Exception: msg = ''
        return e.code, msg
    except Exception as e: return 0, f'{type(e).__name__}: {e}'


def shape(x, depth=0):
    if isinstance(x, dict): return {k: shape(v, depth + 1) for k, v in list(x.items())[:14]} if depth < 4 else '{...}'
    if isinstance(x, list): return [shape(x[0], depth + 1), f'... {len(x)} items'] if x else []
    return type(x).__name__ if not isinstance(x, (int, float)) or isinstance(x, bool) else x


def login():
    if not (KEY and SEC): return None
    st, d = call('/auth/login', body=dict(access_key=KEY, secret_key=SEC))
    tok = ((d.get('data') or {}).get('access_token') if isinstance(d, dict) else None)
    print(f'login with the key pair: HTTP {st}, token {"received" if tok else "not received"}' + ('' if tok else f' ({str(d)[:200]})'))
    return tok


def probe():
    print(f'key set: {bool(KEY)} (length {len(KEY)}); secret set: {bool(SEC)}')
    if not KEY: return
    ok = None
    st, d = call('/affiliate/get_tournaments', dict(has_active_events='true'), {'Authorization': KEY})
    print(f'market-data key on /affiliate/get_tournaments: HTTP {st}' + ('' if st == 200 else f' ({str(d)[:200]})'))
    if st == 200: ok = ('affiliate', {'Authorization': KEY})
    tok = login()
    if tok:
        st2, d2 = call('/mm/get_tournaments', dict(has_active_events='true'), {'Authorization': 'Bearer ' + tok})
        print(f'session token on /mm/get_tournaments: HTTP {st2}' + ('' if st2 == 200 else f' ({str(d2)[:200]})'))
        if st2 == 200 and not ok: ok = ('mm', {'Authorization': 'Bearer ' + tok}); d = d2
    if not ok: print('neither way worked'); return
    kind, H = ok; print('using:', kind)
    T = ((d.get('data') or {}).get('tournaments') or []) if isinstance(d, dict) else []
    print(f'{len(T)} tournaments with active events:', sorted({(t.get("sport") or {}).get("name") or "?" for t in T}))
    print('tournament shape:', json.dumps(shape(T[:1])))
    want = [t for t in T if any(k in (t.get('name') or '') for k in ('NBA', 'NFL', 'NHL', 'NCAA'))][:6]
    print('examples:', [(t.get('id'), t.get('name')) for t in want])
    for t in want[:2]:
        st, e = call(f'/{kind}/get_sport_events', dict(tournament_id=t['id']), H)
        E = ((e.get('data') or {}).get('sport_events') or []) if isinstance(e, dict) else []
        print(f"{t.get('name')}: HTTP {st}, {len(E)} events; shape {json.dumps(shape(E[:1]))[:700]}")
        if E:
            ev = E[0]; eid = ev.get('event_id')
            for path in (f'/v4/{kind}/get_markets', f'/{kind}/get_markets'):
                st, m = call(path, dict(event_id=eid), H)
                M = m.get('data') if isinstance(m, dict) else None
                n = len(M) if isinstance(M, list) else len((M or {}).get('markets') or []) if isinstance(M, dict) else 0
                print(f"  {path} for {ev.get('name')}: HTTP {st}, {n} markets")
                if st == 200 and n:
                    L = M if isinstance(M, list) else M.get('markets')
                    print('  market types:', sorted({str(x.get('type')) for x in L})[:40])
                    print('  market shape:', json.dumps(shape(L[:1]))[:1500])
                    break
        time.sleep(0.5)


if __name__ == '__main__':
    if (sys.argv[1:] or ['probe'])[0] == 'probe': probe()
