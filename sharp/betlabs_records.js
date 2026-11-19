// Bet Labs full backtest records for Sean's saved Tested:/Tracked: screens (11/19). Read only.
// Run in a signed-in Bet Labs page (https://sportsinsights.actionnetwork.com/betlabs/screen?ScreenId=1772775), with the screen ids
// in IDS (from data/state/betlabs_inventory.json). It builds window._BLREC, a compact JSON string: per screen the summary Bet Labs shows
// (record, units, ROI, z, grade), the record since the screen was saved (Built*), the current season, the filters as Bet Labs words them,
// the date the screen was created, and per-season splits computed from Bet Labs' own past-picks list (SportEvents.GetGames).
// Units are Bet Labs' $100 units divided by 100. ROI = units / (W + L + P), as Bet Labs computes it.
// Then read window._BLREC out (it is about 30-60 KB: render it into the page and use get_page_text, or read in chunks), save it as
// betlabs_in.json and run: python3 sharp/betlabs_records.py betlabs_in.json
window.blRecords = async function (IDS) {   // runs ~1-2 minutes: start it without awaiting, then poll window._BLPROG
  const P = t => JSON.parse(t.replace(/^[^(]*\(/, '').replace(/\);?\s*$/, ''));
  const all = (window.analyticsData && window.analyticsData.AllScreens) || [];
  const r1 = x => Math.round(x * 10) / 10, r2 = x => Math.round(x * 100) / 100;
  const season = (sport, d) => {           // d = 'YYYY-MM-DD'
    const y = +d.slice(0, 4), m = +d.slice(5, 7);
    if (/NFL|NCAAF|CFB/i.test(sport)) return String(m >= 8 ? y : y - 1);
    if (/MLB|WNBA/i.test(sport)) return String(y);
    const s = m >= 8 ? y : y - 1; return `${s}-${String((s + 1) % 100).padStart(2, '0')}`;
  };
  const dd = s => { const [m, d, y] = s.split('/').map(Number); return `${y < 100 ? 2000 + y : y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`; };
  window._BLPROG = 0;
  const out = { pulled_at: new Date().toISOString().replace(/\.\d+Z$/, 'Z'), screens: {} }, errs = [];
  for (const id of IDS) {
    try {
      const s = all.find(x => x.ScreenId == id) || {};
      const html = await (await fetch(`/betlabs/screen?ScreenId=${id}`)).text();
      // the page carries analyticsData as a JS literal; the saved screen's own block starts at ",Screen:{" (CreatedDate: new Date(ms))
      const k = html.indexOf(',Screen:{'), cm = k > 0 ? html.slice(k).match(/CreatedDate:new Date\((-?\d+)\)/) : null;
      const created = cm && +cm[1] > 0 ? new Date(+cm[1]).toISOString().slice(0, 10) : null;
      const j = P(await (await fetch(`/dataservice/betlabsDataService.ashx?Task=SportEvents.GetGames&screenId=${id}&callback=jsonCallback&_=${Date.now()}`)).text());
      const ev = ((Array.isArray(j) ? j[0] : j) || {}).SportEvents || [];
      const by = {}, since = { w: 0, l: 0, p: 0, u: 0 };
      let first = null, last = null;
      for (const e of ev) {
        const d = dd(e.Event_Date), k = season(s.SportName || '', d), u = (e['Units Won'] || 0) / 100;
        const b = by[k] = by[k] || { w: 0, l: 0, p: 0, u: 0 };
        const res = e.Result; b[res === 'W' ? 'w' : res === 'L' ? 'l' : 'p']++; b.u += u;
        if (created && d >= created) { since[res === 'W' ? 'w' : res === 'L' ? 'l' : 'p']++; since.u += u; }
        if (!first || d < first) first = d; if (!last || d > last) last = d;
      }
      const seasons = Object.fromEntries(Object.entries(by).sort().map(([k, b]) => [k, [b.w, b.l, b.p, r2(b.u), r1(100 * b.u / Math.max(1, b.w + b.l + b.p))]]));
      out.screens[id] = {
        name: s.ScreenName, sport: s.SportName, grade: s.Grade, bet_type: s.BetTypeId, line_type: s.LineType, fade: !!s.IsFadeSystem,
        filters: (s.ScreenFilters || []).filter(f => f.Active !== false).map(f => `${f.FilterName}: ${f.Description}`.replace(/\s+/g, ' ').trim()),
        all_time: { w: s.Wins, l: s.Losses, p: s.Pushes, units: r2((s.UnitsWon || 0) / 100), roi: r1(s.ROI || 0), z: r2(s.ZScore || 0), n: ev.length, first, last },
        since_saved: { created, w: s.BuiltWins, l: s.BuiltLosses, p: s.BuiltPushes, units: r2((s.BuiltUnits || 0) / 100), from_picks: [since.w, since.l, since.p, r2(since.u)] },
        this_season: { w: s.SeasonWins, l: s.SeasonLosses, p: s.SeasonPushes, units: r2((s.SeasonUnits || 0) / 100) },
        seasons,
      };
    } catch (e) { errs.push(`${id}: ${String(e.message || e).slice(0, 60)}`); }
    window._BLPROG++;
  }
  out.errors = errs;
  window._BLREC = JSON.stringify(out);
  return { screens: Object.keys(out.screens).length, errors: errs, bytes: window._BLREC.length };
};
