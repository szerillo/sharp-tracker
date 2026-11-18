#!/usr/bin/env python3
"""board_r10 follow-up: CLV question, pass shares, live tracker record, combined estimate and sizing tiers (docs/validation/TIER_RULES.md).
Reads data/research/validation.json (sharp/validate_systems.py) and data/state/fills.jsonl. Writes docs/validation/FOLLOWUP.md and
data/research/validation_followup.json. Read-only: no tier in the tool is changed."""
import os, json, math, collections, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
J = json.load(open(os.path.join(ROOT, 'data', 'research', 'validation.json')))
FILLS = [json.loads(l) for l in open(os.path.join(ROOT, 'data', 'state', 'fills.jsonl')) if l.strip()]
OUT = os.path.join(ROOT, 'docs', 'validation', 'FOLLOWUP.md'); OUTJ = os.path.join(ROOT, 'data', 'research', 'validation_followup.json')
INSUFF = ['cbb_bigloss_vs_top5', 'xch_homedog_fade', 'cfb_q1_under_curve', 'cfb_tt_under_curve', 'cbb_1h_total_curve', 'nhl_p1_spread_curve']
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
pct = lambda x: 'n/a' if x is None else f"{100 * x:+.1f}%"
p3 = lambda x: 'n/a' if x is None else f"{x:.3f}"

# ---- live record per rule tag: graded fills, voids out, profit per unit risked at the filled price
live = collections.defaultdict(lambda: dict(w=0, l=0, p=0, units=0.0, risk=0.0, per_unit=[], first=None))
for f in FILLS:
    if f.get('void_at') or f.get('result') not in ('W', 'L', 'P'): continue
    t = f['rule_tag'].split(':', 1)[-1]; x = live[t]; x[{'W': 'w', 'L': 'l', 'P': 'p'}[f['result']]] += 1
    x['units'] += f['pnl_units']; x['risk'] += f['stake']; x['per_unit'].append(f['pnl_units'] / f['stake'])
    x['first'] = min(x['first'] or f['ts_utc'], f['ts_utc'])
for x in live.values(): x['n'] = len(x['per_unit']); x['roi'] = sum(x['per_unit']) / x['n'] if x['n'] else None
allr = dict(w=sum(x['w'] for x in live.values()), l=sum(x['l'] for x in live.values()), units=sum(x['units'] for x in live.values()))


def combine(R, L):
    """Normal precision-weighted update of the walk-forward ROI with the live ROI; same per-bet sd for both (TIER_RULES.md)."""
    sd = R.get('wf_sd'); m0, n0 = R.get('wf_roi'), R.get('wf_n') or 0
    if sd is None or m0 is None or n0 < 2: return None
    w0 = n0 / sd ** 2; num, den = m0 * w0, w0
    if L and L['n']: w1 = L['n'] / sd ** 2; num += L['roi'] * w1; den += w1
    m = num / den; se = 1 / math.sqrt(den)
    return dict(roi=m, se=se, p_pos=Phi(m / se), live_share=(L['n'] / (L['n'] + n0)) if L and L['n'] else 0.0,
                hist_only_p_pos=Phi(m0 / (sd / math.sqrt(n0))))


def tier(R, L, C):
    """docs/validation/TIER_RULES.md, applied as written."""
    collapse = bool(L and L['n'] >= 20 and L['roi'] <= -0.10)
    if C is None: return 'C', 'no replayable history: Tier C at most until a replay exists'
    a = [R['p_wf'] is not None and R['p_wf'] < 0.01, R['wf_n'] >= 100, (R['wf_roi'] or 0) >= 0.05, C['p_pos'] >= 0.975,
         (R['p_grid'] or 1) < 0.20 or bool(L and L['n'] >= 50 and L['roi'] > 0), not collapse]
    if all(a): return 'A', 'meets every Tier A bar'
    b = [C['p_pos'] >= 0.90, R['wf_n'] >= 60, (R['wf_roi'] or 0) > 0, (R['p_wf'] is not None and R['p_wf'] < 0.05) or (R['p_single'] is not None and R['p_single'] < 0.05), not collapse]
    names_a = ['blind p_wf < 0.01', 'WF N >= 100', 'WF ROI >= +5%', 'combined P(ROI>0) >= 0.975', 'search p < 0.20 or 50+ winning live bets', 'no live collapse']
    miss_a = [n for n, ok in zip(names_a, a) if not ok]
    if all(b): return 'B', 'misses Tier A on: ' + ', '.join(miss_a)
    names_b = ['combined P(ROI>0) >= 0.90', 'WF N >= 60', 'WF ROI > 0', 'p_wf or plain p < 0.05', 'no live collapse']
    return 'C', 'misses Tier B on: ' + ', '.join(n for n, ok in zip(names_b, b) if not ok)


rows = []
for k, R in J.items():
    L = live.get(k); C = combine(R, L); t, why = tier(R, L, C)
    flag = bool(C and C['roi'] <= 0 and (not L or L['units'] <= 0))
    rows.append(dict(rule=k, sport=R['sport'], tier=t, why=why, retire_flag=flag, old=R['verdict'], live={kk: v for kk, v in (L or {}).items() if kk != 'per_unit'}, comb=C,
                     wf_roi=R['wf_roi'], wf_n=R['wf_n'], wf_record=R.get('wf_record'), p_wf=R['p_wf'], p_grid=R['p_grid'], p_single=R['p_single'], n=R['n'], roi=R['roi']))
for k in INSUFF:
    L = live.get(k); rows.append(dict(rule=k, sport='', tier='C', why='no replayable history: Tier C at most until a replay exists', retire_flag=False, old='INSUFFICIENT DATA',
                                      live={kk: v for kk, v in (L or {}).items() if kk != 'per_unit'}, comb=None, wf_roi=None, wf_n=0, wf_record=None, p_wf=None, p_grid=None, p_single=None, n=0, roi=None))
rows.sort(key=lambda r: ({'A': 0, 'B': 1, 'C': 2}[r['tier']], -(r['comb']['p_pos'] if r['comb'] else 0)))

# ---- pass shares (section 1)
V = [R for R in J.values()]; nV = len(V)
share = lambda key, a: sum(1 for R in V if R[key] is not None and R[key] < a)
S = {f'{key}_{a}': share(key, a) for key in ('p_grid', 'p_single', 'p_wf') for a in (0.01, 0.05, 0.10)}


def lrec(L):
    return f"{L['w']}-{L['l']}{'-' + str(L['p']) if L.get('p') else ''}, {L['units']:+.1f}u" if L and L.get('n') else 'none'


# ---- report
D = []
D += ['# Validation audit follow-up (board_r10)', '',
      f"Built {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC by sharp/validate_followup.py. Sections 1 to 3 of Kirk's 11/18 follow-up. Discovery (section 4) is in "
      "[DISCOVERY.md](DISCOVERY.md). Recommendations only: no tier in the tool was changed.", '',
      '## 1. What the verdicts were based on (two-minute read)', '',
      '**CLV played no part.** Every number in the audit is profit on graded results: each historical bet is placed at Pinnacle\'s last price before the start and settled '
      'on the final score. Because the bet is taken at the close, CLV is zero by construction. The audit asks only whether the result beats the closing price, '
      'which is the "what the market misses" question Sean cares about. CLV appears on the board as a diagnostic only.', '',
      '**Correction on the bar.** The search-adjusted test (gate 2) had a bar of p < 0.05, not 0.01. The 0.01 bar belonged to gate 4, the shuffle test on the blind '
      'walk-forward results, and applied only when a system had 2 or more blind seasons.', '',
      '**What the search-adjusted test protects against.** Every system was picked from a range of nearby versions (wind 10 to 14 rather than 9 to 15, a 60% ATS '
      'cutoff rather than 55%). Search enough versions of any idea and the best one will look good even on random results. The test shuffles the results, re-runs '
      'the same range, and asks how often the best version on noise matches the real system. If it does so a third of the time, the in-sample record says little on its own.', '',
      f"**How many of the {nV} systems pass each test:**", '',
      '| Test | p < 0.01 | p < 0.05 | p < 0.10 |', '|---|---|---|---|',
      f"| Search-adjusted (gate 2) | {S['p_grid_0.01']} | {S['p_grid_0.05']} | {S['p_grid_0.1']} |",
      f"| Plain single-filter permutation | {S['p_single_0.01']} | {S['p_single_0.05']} | {S['p_single_0.1']} |",
      f"| Blind walk-forward permutation (gate 4) | {S['p_wf_0.01']} | {S['p_wf_0.05']} | {S['p_wf_0.1']} |", '',
      f"By chance alone you would expect about {0.05 * nV:.1f} systems below 0.05 and {0.10 * nV:.1f} below 0.10 on any one of these tests. "
      'Most systems look real on the plain test and do not survive the search-adjusted one. The tiers below lean on the blind walk-forward instead, because there the '
      'version is chosen on past seasons only, so the search is already paid for. They also add the live record.', '',
      '## 2. Live tracker record and how much it should move each verdict', '',
      f"From data/state/fills.jsonl: graded fills by rule tag, voids out, each bet scored per unit risked at the filled price. All rules: {allr['w']}-{allr['l']}, {allr['units']:+.1f}u.", '',
      'Combined estimate: the blind walk-forward ROI and the live ROI, each weighted by its number of bets (a normal precision-weighted update, same per-bet spread for both). '
      '"Live weight" is the live bets\' share of that weight. **The live samples are small:** at about -110, 16 bets carry a standard error of about 24 ROI points, '
      'so 13-3 is consistent with anything from no edge to a large one. A record of that size moves a 100+ bet walk-forward estimate only a little.', '',
      '| System | Live record | Live ROI (N) | Blind WF ROI (N) | Combined ROI | P(ROI > 0): history only, then with live | Live weight |', '|---|---|---|---|---|---|---|']
for r in rows:
    L, C = r['live'], r['comb']
    D.append(f"| {r['rule']} | {lrec(L)} | {pct(L.get('roi')) if L else 'n/a'} ({L.get('n', 0) if L else 0}) | {pct(r['wf_roi'])} ({r['wf_n']}) | "
             f"{pct(C['roi']) + ' +/- ' + f'{100 * C['se']:.1f}' if C else 'n/a'} | {f'{C['hist_only_p_pos']:.2f} then {C['p_pos']:.2f}' if C else 'n/a'} | {f'{100 * C['live_share']:.0f}%' if C else 'n/a'} |")
other = sorted(((t, x) for t, x in live.items() if t not in J and t not in INSUFF), key=lambda z: -z[1]['n'])
D += ['', 'Live record of the other tracker rules (paper, not in this audit): ' + '; '.join(f"{t} {lrec(x)}" for t, x in other) + '.', '',
      '## 3. Sizing tiers', '',
      'Rules: [TIER_RULES.md](TIER_RULES.md), committed before this scoring. Tier A = real money, full size. Tier B = real money, half size. Tier C = paper. '
      'The retire flag is only a prompt for Sean, and a system winning live is never flagged.', '',
      '| Tier | System | Old verdict | Blind WF ROI (N, record) | p_wf | Search p | Plain p | Live | Combined P(ROI > 0) | Retire flag | Why |', '|---|---|---|---|---|---|---|---|---|---|---|']
for r in rows:
    C = r['comb']
    D.append(f"| {r['tier']} | {r['rule']} | {r['old']} | {pct(r['wf_roi'])} ({r['wf_n']}{', ' + r['wf_record'] if r['wf_record'] else ''}) | {p3(r['p_wf'])} | {p3(r['p_grid'])} | {p3(r['p_single'])} | "
             f"{lrec(r['live'])} | {f'{C['p_pos']:.2f}' if C else 'n/a'} | {'yes' if r['retire_flag'] else 'no'} | {r['why']} |")
cnt = collections.Counter(r['tier'] for r in rows)
D += ['', f"Totals: Tier A {cnt['A']}, Tier B {cnt['B']}, Tier C {cnt['C']}; retire flags {sum(r['retire_flag'] for r in rows)}.", '']
open(OUT, 'w').write('\n'.join(D) + '\n')
json.dump(dict(shares=S, n_systems=nV, all_live=allr, rows=rows, other_live={t: {k: v for k, v in x.items() if k != 'per_unit'} for t, x in live.items()}), open(OUTJ, 'w'), indent=1, default=str)
for r in rows: print(r['tier'], r['rule'], lrec(r['live']), r['comb'] and round(r['comb']['p_pos'], 3), r['why'])
print(S, allr)
