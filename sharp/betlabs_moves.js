// Market-wide open-to-close study (Sean, 11/1): not "do our systems' games move" (docs/betlabs_line_move_audit_2026-10-30.md) but
// "when a line moves N points from open to close, does the close overshoot?" Three answers are possible:
//   follow wins  - the move was right and did not go far enough (bet with the move, even at the close)
//   fade wins    - the move overcorrected; the side the money pushed away from is the value at the close
//   both lose    - the close is right and the vig takes both sides (books just won)
// Bet Labs grades at the close, so this is the closing-price question. Bet Labs has open and close only, not the path; the
// "moved then came back" question needs the move tape (data/state/moves.json: p0 -> p1 -> close) and is graded there as it settles.
//
// Inject sharp/betlabs_scan.js first (BL.call / BL.items), then this file, on any screen of the sport and line type
// (sportsinsights.actionnetwork.com/betlabs/screen?ScreenId=...). The screen must have no other filters.
//   await BM.run(screenId)          -> window.BMRES[screenId] = per side, per move value, train and holdout W / L / units
//   BM.table(screenId)              -> text: move bucket x follow / fade ROI, train | holdout
// Side filter: the screen's side item (home / away, over / under, found by name). Change item: "Spread Change Open to Close",
// "O/U Change Open to Close" or "Moneyline Change Open to Close", found by name from the screen's line type.
window.BM = {
 TRAIN: '08/01/2003 - 02/28/2021', HOLD: '03/01/2021 - 10/31/2026',
 find(re){ return BL.items().find(i => re.test(i.name)); },
 changeItem(){ const lt = analyticsData.Screen.LineType; return lt === 3 ? this.find(/^O\/U Change Open to Close/i) : lt === 2 ? this.find(/^Moneyline Change Open to Close/i) : this.find(/^Spread Change Open to Close/i); },
 sideItem(){ return this.find(/^(Home\/Away|Home or Away)$/i) || this.find(/Home.?Away/i); },
 ouItem(){ return this.find(/^(Over\/Under|Over or Under|O\/U Side)$/i) || this.find(/Over.?Under/i); },
 async pull(sid, item, dfid, range){ await BL.call('ScreenFilters.SetDateFilter', {filterId: dfid, value: range}); const a = await BL.call('ScreenFilters.Add', {screenId: sid, dataItemId: item.id});
  try { return await BL.values(sid, item, a.FilterId); } finally { await BL.call('ScreenFilters.DeleteFilter', {ScreenId: sid, filterId: a.FilterId}); } },
 async run(sid){ const ch = this.changeItem(); const lt = analyticsData.Screen.LineType; const sideIt = lt === 3 ? this.ouItem() : this.sideItem();
  if (!ch || !sideIt) return {err: 'items not found', ch: ch && ch.name, side: sideIt && sideIt.name, names: BL.items().map(i => i.name).filter(n => /change|home|away|over|under/i.test(n))};
  const sides = lt === 3 ? ['Over', 'Under'] : ['Home', 'Away']; const out = {name: analyticsData.Screen.ScreenName, sport: analyticsData.Screen.SportId, lt, change: ch.name, side: sideIt.name, res: {}};
  const dfid = await BL.dateFilter(sid);
  try { for (const s of sides){ const fid = await BL.setSide(sid, sideIt.id, s);
    try { out.res[s] = {tr: await this.pull(sid, ch, dfid, this.TRAIN), ho: await this.pull(sid, ch, dfid, this.HOLD)}; }
    finally { await BL.call('ScreenFilters.DeleteFilter', {ScreenId: sid, filterId: fid}); } } }
  finally { await BL.call('ScreenFilters.DeleteFilter', {ScreenId: sid, filterId: dfid}); }
  (window.BMRES = window.BMRES || {})[sid] = out; return {ok: true, sides: Object.keys(out.res), rows: Object.values(out.res).map(r => r.tr.length + r.ho.length)}; },
 // A side's change value is from that side's perspective in Bet Labs (spread: + = the side got more points, i.e. the market moved
 // AWAY from it; O/U: + = total went up, which is toward the over). "Follow" = the side the market moved toward.
 table(sid, buckets){ const d = window.BMRES[sid]; const lt = d.lt; buckets = buckets || (lt === 2 ? [[1,9],[10,19],[20,39],[40,999]] : [[0.5,1],[1.5,2],[2.5,3],[3.5,4.5],[5,99]]);
  const agg = (rows, lo, hi, sign) => { let w = 0, l = 0, u = 0; for (const r of rows){ const x = parseFloat(r.v); if (isNaN(x)) continue; const m = sign * x; if (m >= lo && m <= hi){ w += r.w; l += r.l; u += r.u; } } return {n: w + l, w, l, roi: w + l ? u / (100 * (w + l)) : 0}; };
  const f = s => s.n ? `${s.n} ${(100 * s.w / s.n).toFixed(1)}% ${(100 * s.roi).toFixed(1)}%` : '-';
  const sides = Object.keys(d.res); let txt = `${d.name} | ${d.change} | follow = side the line moved toward | train ${this.TRAIN} | holdout ${this.HOLD}\n`;
  for (const [lo, hi] of buckets){
   // spreads / ML: a side whose number shrank (value < 0 for spread, ML moved toward it) is the "follow" side
   const fol = {tr: {n:0,w:0,l:0,u:0}, ho: {n:0,w:0,l:0,u:0}}, fad = {tr: {n:0,w:0,l:0,u:0}, ho: {n:0,w:0,l:0,u:0}};
   for (const s of sides) for (const k of ['tr', 'ho']){
    const rows = d.res[s][k];
    const towardSign = lt === 3 ? (s === 'Over' ? 1 : -1) : -1;     // O/U: over follows a rise; spread / ML: the side whose number fell
    const a = agg(rows, lo, hi, towardSign), b = agg(rows, lo, hi, -towardSign);
    for (const [T, x] of [[fol, a], [fad, b]]){ T[k].n += x.n; T[k].w += x.w; T[k].l += x.l; T[k].u += x.roi * 100 * x.n; } }
   const fin = s => ({n: s.n, w: s.w, roi: s.n ? s.u / (100 * s.n) : 0});
   txt += `move ${lo}-${hi}: FOLLOW T ${f(fin(fol.tr))} H ${f(fin(fol.ho))} | FADE T ${f(fin(fad.tr))} H ${f(fin(fad.ho))}\n`; }
  return txt; }
};
