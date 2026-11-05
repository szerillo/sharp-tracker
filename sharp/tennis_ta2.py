#!/usr/bin/env python3
"""Tennis Abstract, round 2 (Sean, 11/4: "what else can we test beyond first set? players starting rusty in their first match of a
tournament?"). Same framework as sharp/tennis_ta.py: Elo per tour, calibrated match probability p_cal (Elo bin -> observed rate), the
pooled set-1 curve. Every cut reports the favourite's MATCH residual (won - p_cal, in points) and SET-1 residual (won set 1 - curve),
so a cut only matters if it moves the result beyond what the price already says. Best-of-3 unless stated; holdout 2023-2026 where the
cut could be fit; descriptive cuts use all years. No prices: a residual is a modelling input, not a bet, until it beats a close.

  A. First match of the tournament (rust): the favourite's first match vs an opponent who has already played a match in this event
     (byes, qualifiers), both in their first match, the dog's first match. Also a layoff (28+ days since the player's last event) and
     a surface switch (last match on another surface).
  B. Qualifiers in round 1 and 2; head-to-head record; lefties; age; round (final / semi).
  C. Beyond set 1: straight sets (set handicap -1.5 fair price), set 2 after losing set 1, total games (match totals), a tiebreak in
     the match, set-1 total games (over / under the set-1 games line).
Writes data/research/tennis_ta2.json. Usage: python3 sharp/tennis_ta2.py"""
import os, sys, json, math, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import sharp.tennis_ta as T
OUT = os.path.join(ROOT, 'data', 'research', 'tennis_ta2.json')
SET_RE = T.SET_RE


def sets_of(score):
    out = []
    for tok in (score or '').replace('RET', '').split():
        m = SET_RE.match(tok)
        if not m: continue
        a, b = int(m.group(1)), int(m.group(2))
        if max(a, b) < 6: continue
        out.append((a, b))
    return out


def main():
    M = T.load(); T.elo_run(M); T.serve_profiles(M)
    annotate(M)
    rows = T.fav_rows(M)
    # calibration per group and the pooled curve, as in tennis_ta.mapping
    cal = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for r in rows: c = cal[T.grp(r)][T.binp(r['p'])]; c[0] += 1; c[1] += r['fav_won']
    for r in rows:
        c = cal[T.grp(r)].get(T.binp(r['p'])); r['p_cal'] = c[1] / c[0] if c and c[0] >= 100 else None
    rows = [r for r in rows if r.get('p_cal') is not None]
    pooled = T.curve([r for r in rows if r['bo'] == 3])
    for r in rows: r['s1_curve'] = T.interp(pooled, r['p_cal']) if r['bo'] == 3 else None
    R = {}
    def cut(name, rows_, keyf, min_n=300):
        Tt = collections.defaultdict(lambda: [0, 0, 0.0, 0, 0.0])      # n, fav won, sum p_cal, fav s1, sum curve
        for r in rows_:
            k = keyf(r)
            if k is None: continue
            t = Tt[k]; t[0] += 1; t[1] += r['fav_won']; t[2] += r['p_cal']
            if r['s1_curve'] is not None: t[3] += r['fav_s1']; t[4] += r['s1_curve']
        R[name] = {str(k): dict(n=n, fav_won=round(w / n, 3), price=round(sp / n, 3), match_resid=round(100 * (w / n - sp / n), 1),
                               set1=round(s / n, 3), set1_curve=round(sc / n, 3), set1_resid=round(100 * (s / n - sc / n), 1)) for k, (n, w, sp, s, sc) in sorted(Tt.items(), key=lambda kv: str(kv[0])) if n >= min_n}
    fav = lambda r, k: r[('w_' if r['fav_won'] else 'l_') + k]
    dog = lambda r, k: r[('l_' if r['fav_won'] else 'w_') + k]
    bo3 = [r for r in rows if r['bo'] == 3 and r.get('tid')]
    hold = [r for r in bo3 if r['date'] >= T.HOLD]
    # A. rust
    cut('A1 first match of the event (bo3, all years)', bo3, lambda r: ('fav first match, dog has played' if fav(r, 'first') and not dog(r, 'first') else 'dog first match, fav has played' if dog(r, 'first') and not fav(r, 'first') else 'both first match' if fav(r, 'first') else 'both have played'))
    cut('A1h first match of the event (holdout)', hold, lambda r: ('fav first match, dog has played' if fav(r, 'first') and not dog(r, 'first') else 'dog first match, fav has played' if dog(r, 'first') and not fav(r, 'first') else 'both first match' if fav(r, 'first') else 'both have played'))
    cut('A1t first match, by tour x level', bo3, lambda r: f"{T.grp(r)}: " + ('fav first, dog played' if fav(r, 'first') and not dog(r, 'first') else 'dog first, fav played' if dog(r, 'first') and not fav(r, 'first') else 'other'))
    cut('A2 layoff 28+ days since last event', bo3, lambda r: ('fav off 28+ days' if fav(r, 'layoff') and not dog(r, 'layoff') else 'dog off 28+ days' if dog(r, 'layoff') and not fav(r, 'layoff') else 'both off 28+' if fav(r, 'layoff') and dog(r, 'layoff') else 'neither') if fav(r, 'layoff') is not None and dog(r, 'layoff') is not None else None)
    cut('A3 surface switch (last match on another surface)', bo3, lambda r: ('fav switched, dog did not' if fav(r, 'switch') and not dog(r, 'switch') else 'dog switched, fav did not' if dog(r, 'switch') and not fav(r, 'switch') else 'both switched' if fav(r, 'switch') else 'neither'))
    cut('A3s surface switch by surface', bo3, lambda r: f"{r['surface']}: " + ('fav switched only' if fav(r, 'switch') and not dog(r, 'switch') else 'dog switched only' if dog(r, 'switch') and not fav(r, 'switch') else 'other'))
    # refined rust cuts: tour + Challenger only (Elo is reliable there; the ITF files mix qualifying into the event), both players in
    # their first match of the event (so a layoff or a surface switch is not confounded with having played qualifying here)
    tc = [r for r in bo3 if T.grp(r) in ('atp_tour', 'atp_chall', 'wta_tour')]
    first_both = [r for r in tc if fav(r, 'first') and dog(r, 'first')]
    cut('A1r first match of the event, tour + Challenger, holdout', [r for r in tc if r['date'] >= T.HOLD], lambda r: ('fav first match, dog has played' if fav(r, 'first') and not dog(r, 'first') else 'dog first match, fav has played' if dog(r, 'first') and not fav(r, 'first') else 'both first match' if fav(r, 'first') else 'both have played'), min_n=200)
    cut('A2r layoff 28+ days, tour + Challenger, both in their first match', first_both, lambda r: ('fav off 28+ days' if fav(r, 'layoff') and not dog(r, 'layoff') else 'dog off 28+ days' if dog(r, 'layoff') and not fav(r, 'layoff') else 'both off 28+' if fav(r, 'layoff') and dog(r, 'layoff') else 'neither') if fav(r, 'layoff') is not None and dog(r, 'layoff') is not None else None, min_n=200)
    cut('A3r surface switch, tour + Challenger, both in their first match', first_both, lambda r: ('fav switched, dog did not' if fav(r, 'switch') and not dog(r, 'switch') else 'dog switched, fav did not' if dog(r, 'switch') and not fav(r, 'switch') else 'both switched' if fav(r, 'switch') else 'neither'), min_n=200)
    cut('A3r2 surface switch, same, holdout', [r for r in first_both if r['date'] >= T.HOLD], lambda r: ('fav switched, dog did not' if fav(r, 'switch') and not dog(r, 'switch') else 'dog switched, fav did not' if dog(r, 'switch') and not fav(r, 'switch') else 'both switched' if fav(r, 'switch') else 'neither'), min_n=200)
    cut('B2r head-to-head, tour + Challenger, holdout', [r for r in tc if r['date'] >= T.HOLD], lambda r: ('no prior meetings' if fav(r, 'h2h') + dog(r, 'h2h') == 0 else 'fav leads h2h' if fav(r, 'h2h') > dog(r, 'h2h') else 'dog leads h2h' if dog(r, 'h2h') > fav(r, 'h2h') else 'h2h level'), min_n=200)
    cut('B5r round, tour level only', [r for r in tc if T.grp(r) in ('atp_tour', 'wta_tour')], lambda r: r.get('rnd') if r.get('rnd') in ('F', 'SF', 'QF', 'R16', 'R32', 'R64', 'R128') else None, min_n=200)
    # B. qualifiers, h2h, hand, age, round
    cut('B1 qualifier (entry Q) in R32/R64/R128', [r for r in bo3 if r.get('rnd') in ('R32', 'R64', 'R128')], lambda r: ('fav is a qualifier' if fav(r, 'entry') == 'Q' else 'dog is a qualifier' if dog(r, 'entry') == 'Q' else 'neither'))
    cut('B1b lucky loser / wild card', bo3, lambda r: ('dog is a lucky loser' if dog(r, 'entry') == 'LL' else 'dog is a wild card' if dog(r, 'entry') == 'WC' else 'fav is a wild card' if fav(r, 'entry') == 'WC' else None))
    cut('B2 head-to-head before this match', bo3, lambda r: ('no prior meetings' if fav(r, 'h2h') + dog(r, 'h2h') == 0 else 'fav leads h2h' if fav(r, 'h2h') > dog(r, 'h2h') else 'dog leads h2h' if dog(r, 'h2h') > fav(r, 'h2h') else 'h2h level'))
    cut('B2b dog leads h2h by 2+', bo3, lambda r: 'dog leads by 2+' if dog(r, 'h2h') - fav(r, 'h2h') >= 2 else 'fav leads by 2+' if fav(r, 'h2h') - dog(r, 'h2h') >= 2 else None)
    cut('B3 left-handers', bo3, lambda r: ('fav lefty vs righty' if fav(r, 'hand') == 'L' and dog(r, 'hand') == 'R' else 'dog lefty vs righty' if dog(r, 'hand') == 'L' and fav(r, 'hand') == 'R' else 'both right' if fav(r, 'hand') == 'R' and dog(r, 'hand') == 'R' else None))
    cut('B4 age', [r for r in bo3 if fav(r, 'age') and dog(r, 'age')], lambda r: ('fav 33+' if fav(r, 'age') >= 33 else 'fav under 21' if fav(r, 'age') < 21 else None) or ('dog 33+' if dog(r, 'age') >= 33 else 'dog under 21' if dog(r, 'age') < 21 else None))
    cut('B5 round', bo3, lambda r: r.get('rnd') if r.get('rnd') in ('F', 'SF', 'QF', 'R16', 'R32', 'R64', 'R128', 'Q1', 'Q2', 'Q3') else None)
    # C. beyond set 1 (bo3, by calibrated match probability bin)
    pb = lambda r: f"p {T.binp(r['p_cal']):.2f}"
    S = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0.0, 0, 0, 0.0])   # n, fav won, fav won 2-0, fav lost s1 & won s2, fav lost s1 n, games sum, tiebreak any, s1 games>=10, s1 games sum
    for r in bo3:
        st = sets_of(r.get('score') or '')
        if len(st) < 2: continue
        t = S[(r['tour'], pb(r))]; t[0] += 1; t[1] += r['fav_won']
        fw = r['fav_won']; sets_fav = [(a, b) if fw else (b, a) for a, b in st]
        t[2] += fw and len(st) == 2
        if not r['fav_s1']:
            t[4] += 1; t[3] += sets_fav[1][0] > sets_fav[1][1]
        g = sum(a + b for a, b in st); t[5] += g; t[6] += any(max(a, b) == 7 and min(a, b) == 6 for a, b in st); t[7] += (st[0][0] + st[0][1]) >= 10; t[8] += st[0][0] + st[0][1]
    R['C beyond set 1 (bo3, 2+ sets played)'] = {f"{k[0]} {k[1]}": dict(n=n, fav_won=round(w / n, 3), straight_sets=round(w20 / n, 3), straight_given_win=round(w20 / w, 3) if w else None,
                                                                         set2_after_losing_set1=round(s2 / ls1, 3) if ls1 else None, games_mean=round(gs / n, 2), tiebreak_in_match=round(tb / n, 3),
                                                                         set1_10plus_games=round(s10 / n, 3), set1_games_mean=round(s1g / n, 2))
                                                 for k, (n, w, w20, s2, ls1, gs, tb, s10, s1g) in sorted(S.items()) if n >= 500}
    json.dump(R, open(OUT, 'w'), indent=1)
    for k, v in R.items():
        print(f"\n== {k}")
        for kk, vv in v.items(): print(f"  {kk:44} {vv}")


def annotate(M):
    # ---- per-player event history: first match in this event, last event date, last surface, head-to-head
    by_event_player = collections.defaultdict(int); last_event = {}; last_surface = {}; h2h = collections.defaultdict(lambda: [0, 0])
    raw = {}   # keep per-match raw fields (score, entries, hands, ages, round, tourney) from load(): re-read quickly
    for m in M: pass
    # load() keeps score fields only partly; re-read the raw CSVs for score strings, entries, hands, ages, rounds, tourney ids
    import csv, gzip, glob
    key2raw = {}
    for f in sorted(glob.glob(os.path.join(T.TA, '*_matches_*.csv.gz'))):
        for r in csv.DictReader(gzip.open(f, 'rt', encoding='utf-8', errors='replace')):
            key2raw[(r['tourney_id'], r.get('match_num'), r['winner_id'], r['loser_id'])] = r
    # walk chronologically to build the event-history flags (M is sorted by date, tour, match_num; within an event, match_num rises with rounds)
    ev_seen = collections.defaultdict(set)
    for m in M:
        pass
    # we need tourney_id per match: rebuild from the raw rows in the same order load() produced (date, tour, match_num) is not unique; use a
    # second pass keyed by (date, winner, loser)
    idx = {}
    for k, r in key2raw.items(): idx[(r['tourney_date'], r['winner_id'], r['loser_id'])] = r
    for m in M:
        r = idx.get((str(m['date']), m['w'], m['l']))
        if not r: m['tid'] = None; continue
        tid = r['tourney_id']; m['tid'] = tid; m['rnd'] = r.get('round'); m['w_entry'] = r.get('winner_entry'); m['l_entry'] = r.get('loser_entry')
        m['w_hand'] = r.get('winner_hand'); m['l_hand'] = r.get('loser_hand'); m['score'] = r.get('score'); m['tname'] = r.get('tourney_name'); m['w_seed'] = r.get('winner_seed'); m['l_seed'] = r.get('loser_seed'); m['w_ioc'] = r.get('winner_ioc'); m['l_ioc'] = r.get('loser_ioc')
        try: m['w_age'] = float(r.get('winner_age') or 0) or None; m['l_age'] = float(r.get('loser_age') or 0) or None
        except Exception: m['w_age'] = m['l_age'] = None
        m['w_first'] = m['w'] not in ev_seen[tid]; m['l_first'] = m['l'] not in ev_seen[tid]
        ev_seen[tid].add(m['w']); ev_seen[tid].add(m['l'])
        m['w_layoff'] = (m['date'] != last_event.get(m['w'], m['date'])) and days_between(last_event.get(m['w']), m['date']) >= 28 if m['w'] in last_event else None
        m['l_layoff'] = (m['date'] != last_event.get(m['l'], m['date'])) and days_between(last_event.get(m['l']), m['date']) >= 28 if m['l'] in last_event else None
        m['w_switch'] = last_surface.get(m['w']) not in (None, m['surface']); m['l_switch'] = last_surface.get(m['l']) not in (None, m['surface'])
        hw, hl = h2h[(m['w'], m['l'])], h2h[(m['l'], m['w'])]
        m['w_h2h'] = hw[0]; m['l_h2h'] = hl[0]
        h2h[(m['w'], m['l'])][0] += 1
        last_event[m['w']] = last_event[m['l']] = m['date']; last_surface[m['w']] = last_surface[m['l']] = m['surface']


def days_between(d0, d1):
    a = dt.date(d0 // 10000, d0 // 100 % 100, d0 % 100); b = dt.date(d1 // 10000, d1 // 100 % 100, d1 % 100)
    return (b - a).days


if __name__ == '__main__':
    main()
