"""Expert pick log (Sean, 11/8: log and grade the trusted experts' picks).
Reads each expert's public Action Network profile page (the picks the page itself shows: today's, including settled ones, and pending),
and keeps every pick by its id in data/experts/picks.jsonl, updating result / units_net when Action grades it. Run a few times a day so
picks that settle are caught before they roll off the page. Also snapshots each expert's per-league record (data/experts/records.json).
Action grades the picks; nothing here re-grades them."""
import json, os, re, sys, time, datetime as dt, urllib.request

EXPERTS = {   # profile slug: (name, what Sean follows them for)
    '_Collin1': ('Collin Wilson', 'CFB'), 'Joshua_Nunn': ('Duck', 'CFB'), 'AnthonyDabbundo': ('Dabbundo', 'soccer, NFL'),
    'Stuckey2': ('Stuckey', 'NFL, CFB, CBB'), 'wheatonbrando': ('Brandon Anderson', 'NFL'), 'DerekCarty': ('Derek Carty', 'props'),
    'nick_giffen': ('Nick Giffen', 'props, NFL'), 'The_Oddsmaker': ('Sean Koerner', 'props, NFL, MLB props'),
    'VegasRefund': ('Vegas Refund', 'multi-sport'), 'NicholaskMartin': ('Nick Martin', 'NHL'),
}
OUT = 'data/experts'; PICKS = f'{OUT}/picks.jsonl'; RECS = f'{OUT}/records.json'
KEEP = ('id', 'league_name', 'play', 'game_id', 'type', 'period', 'side_id', 'value', 'odds', 'units', 'units_net', 'result', 'status',
        'created_at', 'updated_at', 'starts_at', 'verified')


def page(slug):
    req = urllib.request.Request(f'https://www.actionnetwork.com/picks/profile/{slug}',
                                 headers={'User-Agent': 'Mozilla/5.0 (sharp-tracker pick log)', 'Accept': 'text/html'})
    html = urllib.request.urlopen(req, timeout=40).read().decode('utf-8', 'replace')
    m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m: raise ValueError(f'no page data ({len(html)} bytes: {re.sub(chr(92)+"s+", " ", html[:160])})')
    return json.loads(m.group(1))['props']['pageProps']['profile']


def flat(pk, slug):
    r = {k: pk.get(k) for k in KEEP if k in pk}
    meta = pk.get('meta') or {}
    r['alt'] = bool(meta.get('is_alt_market')); r['note'] = (meta.get('note') or '')[:300]
    if pk.get('type') == 'parlay' or pk.get('picks'):
        r['legs'] = [l.get('play') for l in (pk.get('picks') or []) if isinstance(l, dict)]
    g = pk.get('game') or {}
    if g: r['game'] = dict(start=g.get('start_time'), teams=[t.get('display_name') for t in g.get('teams') or [] if isinstance(t, dict)])
    r['expert'] = slug; r['name'] = EXPERTS[slug][0]
    return r


def main():
    os.makedirs(OUT, exist_ok=True)
    have = {}
    if os.path.exists(PICKS):
        for l in open(PICKS):
            try: d = json.loads(l); have[d['id']] = d
            except Exception: pass
    try: recs = json.load(open(RECS))
    except Exception: recs = {}
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'); new = upd = bad = 0
    # 11/14: GitHub's runners get Action's bot-check page, so the scheduled run reads the profiles in Sean's Chrome and hands them over as
    # one JSON file: --from-json FILE with {slug: {"picks": [already-flat picks], "pick_stats": {...}}} (same fields as flat() writes)
    pre = None
    if '--from-json' in sys.argv: pre = json.load(open(sys.argv[sys.argv.index('--from-json') + 1]))
    for slug in EXPERTS:
        if pre is not None:
            if slug not in pre: print(f'[experts] {slug}: not in the handed-over file'); bad += 1; continue
            prof = dict(pick_stats=pre[slug].get('pick_stats') or {}); flats = [dict(p, expert=slug, name=EXPERTS[slug][0]) for p in pre[slug].get('picks') or []]
        else:
            try: prof = page(slug)
            except Exception as e:
                print(f'[experts] {slug}: {e}'); bad += 1; continue
            flats = [flat(pk, slug) for pk in prof.get('picks') or []]
        for r in flats:
            old = have.get(r['id'])
            if old is None: r['first_seen'] = now; have[r['id']] = r; new += 1
            elif (old.get('result'), old.get('units_net')) != (r.get('result'), r.get('units_net')):
                r['first_seen'] = old.get('first_seen'); have[r['id']] = r; upd += 1
        ps = (prof.get('pick_stats') or {})
        recs[slug] = dict(name=EXPERTS[slug][0], follow=EXPERTS[slug][1], at=now, stats=ps.get('pick_stats') or ps)
        if pre is None: time.sleep(2)
    with open(PICKS, 'w') as f:
        for d in sorted(have.values(), key=lambda d: (d.get('created_at') or '', d['id'])): f.write(json.dumps(d) + '\n')
    json.dump(recs, open(RECS, 'w'), indent=1)
    print(f'[experts] {len(have)} picks logged ({new} new, {upd} graded or changed); {bad} profiles failed')
    if bad == len(EXPERTS): sys.exit(1)


if __name__ == '__main__':
    main()
