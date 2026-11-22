// Bet Labs current picks + screen inventory (11/22). Run in Sean's signed-in Chrome on a sportsinsights.actionnetwork.com/betlabs/screen page
// (window.analyticsData must exist). Read-only: GET requests only, nothing in the account changes. Leaves the JSON in <article><pre> for
// get_page_text and returns [pulled, screens, picks, chars, hash, errors]; the hash (x = x*31 + charCode, whitespace collapsed) checks the copy.
(async () => {
  if (!window.analyticsData || !window.analyticsData.AllScreens) return ['NOT_SIGNED_IN', location.href];
  const P = t => JSON.parse(t.replace(/^[^(]*\(/, '').replace(/\);?\s*$/, ''));
  const T = window.analyticsData.AllScreens.filter(s => /^(Tested|Tracked):/.test(s.ScreenName));
  const fv = f => f.ScreenFilterType === 'range' ? `${f.NumberValue1}..${f.NumberValue2}` : (f.StringValueDisplay || f.StringValue || String(f.BooleanValue));
  const DROP = new Set(['Play', 'Home Team', 'Visitor Team', 'DateSort', 'Event_Date', 'Season_Type', 'Over_/_Under', 'Home_/_Visitor', 'Favorite_/_Dog']);
  const dd = s => { const [m, d, y] = s.split('/').map(Number); return `${2000 + y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`; };
  const out = {pulled: new Date().toISOString().replace(/\.\d+Z$/, 'Z'), inv: [], picks: []}, errs = [];
  for (const s of T) {
    out.inv.push({id: s.ScreenId, name: s.ScreenName, grade: s.Grade, roi: Math.round(s.ROI * 10) / 10, record: `${s.Wins}-${s.Losses}`,
                  filters: (s.ScreenFilters || []).filter(f => f.Active !== false).map(f => `${f.FilterName} ${fv(f)}`).join('; ')});
    try {
      const j = P(await (await fetch(`/dataservice/betlabsDataService.ashx?Task=SportEvents.GetLiveGames&screenId=${s.ScreenId}&callback=jsonCallback&_=${Date.now()}`)).text());
      for (const e of ((Array.isArray(j) ? j[0] : j) || {}).SportEvents || [])
        out.picks.push({sid: s.ScreenId, date: dd(e.Event_Date), play: String(e.Play).replace(/^Play on /, ''), away: e['Visitor Team'], home: e['Home Team'],
                        info: Object.entries(e).filter(([k]) => !DROP.has(k)).map(([k, v]) => `${k.replace(/_/g, ' ')} ${v}`).join(', ')});
    } catch (x) { errs.push(s.ScreenId + ':' + x.message); }
  }
  const txt = JSON.stringify(out); document.body.innerHTML = '<article><pre id=o></pre></article>'; document.getElementById('o').textContent = txt;
  let h = 0; for (const c of txt.replace(/\s+/g, ' ')) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return [out.pulled, out.inv.length, out.picks.length, txt.length, h, errs];
})()
