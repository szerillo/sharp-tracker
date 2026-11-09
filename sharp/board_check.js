#!/usr/bin/env node
// Board check (Sean, 11/6: "Why do we keep having things that aren't showing up on the board? We can't have that.")
// Opens the PUBLISHED page in a real browser, exactly as Sean sees it on load (default filters, every dropdown closed), and checks that
// every sized open bet in the bet tracker (system A/B, lean C, sharp A/B/C; systems, sharp flags, curve and prop rules) that starts
// between now and the board's default window end has a VISIBLE row on the page (same game and side). A bet shown greyed with no size
// (held, conflicted) counts as shown and is listed separately. Also checks that the system-bet file was rebuilt by the last tracker run.
// Exit 1 and a phone alert (NTFY_TOPIC) when anything is missing. Writes board_check.json next to it.
// Usage: node sharp/board_check.js [https://szerillo.github.io/sharp-tracker/]
const { chromium } = require('playwright');
const fs = require('fs');
const SITE = (process.argv[2] || 'https://szerillo.github.io/sharp-tracker/').replace(/\/?$/, '/');
const SIZED = new Set(['system A', 'system B', 'lean C', 'sharp A', 'sharp B', 'sharp C']);
const SRC = new Set(['system', 'sharp', 'curve', 'props']);

(async () => {
  const bust = `?v=${Date.now()}`;
  const get = async u => (await fetch(SITE + u + bust, { headers: { 'cache-control': 'no-cache' } })).json();
  const BL = await get('data/state/bet_log.json');
  const SY = await get('data/state/system_fires.json');
  const now = Date.now();
  // Grade C rows come and go with the signals (they are logged from this page), so a C row that left the page is not a missing bet
  const cand = (BL.rows || []).filter(b => SRC.has(b.src) && SIZED.has(b.cat) && b.cat !== 'sharp C' && b.won == null && b.event_id && b.side && Date.parse(b.start) > now + 5 * 60e3);

  // 11/7: a sized bet that matched no schedule game gets no opposing market signals (Georgia State +6.5 showed clean with a Kalshi move
  // against it). Listed every run; FCS games have no schedule, so those are expected and say 'only sharp accounts checked' on the board.
  const unmatched = (BL.rows || []).filter(b => SRC.has(b.src) && SIZED.has(b.cat) && b.won == null && !b.event_id && Date.parse(b.start) > now);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(SITE + bust, { waitUntil: 'networkidle', timeout: 120000 });
  await page.waitForTimeout(8000);
  // the default window is whatever the page itself counts as 'today' (its whenOf), so the check and the board can never disagree
  const inView = await page.evaluate(starts => starts.map(s => whenOf(s) === 'today'), cand.map(b => b.start));
  const want = cand.filter((b, i) => inView[i]);
  // 11/7: the 'Not betting right now' list shows one reason at a time (Hold / Watch / Paper / Not met); a bought-out flag under Watch / passed
  // is on the board, one click away. Collect rows under every chip. A conflict row stands for both sides (data-oside).
  // 11/8 (Sean, Grade C into the tracker): a Grade C sharp row (sharp accounts plus money or a price move, no flag) exists only on the page,
  // so the page is the record of it. Every sized C row on the default view is written out; the pages job appends new ones to
  // data/state/sharp_c_paper.jsonl at the price shown when first seen, and the bet tracker grades them from final scores.
  const sharpC = await page.evaluate(() => [...document.querySelectorAll('tr.erow[data-kind="sharp"][data-tier="C"][data-rank="0"]')].map(tr => ({
    ev: tr.dataset.ev, mk: tr.dataset.mk || '', side: tr.dataset.side, t: +tr.dataset.t || 0, f: +tr.dataset.f || 0, lbl: tr.dataset.lbl || '',
    bet: (tr.querySelector('.bet') || {}).innerText || '', price: ((tr.querySelector('.c-price') || {}).innerText || '').replace(/\s+/g, ' ').trim(),
    size: ((tr.querySelector('.c-size') || {}).innerText || '').replace(/\s+/g, ' ').trim() })));
  const chips = await page.evaluate(() => typeof _nb === 'undefined' ? [null] : ['hold', 'watch', 'paper', 'notmet']);
  const shown = [];
  for (const k of chips) {
    if (k) { await page.evaluate(k => { _nb = k; draw(); }, k); await page.waitForTimeout(300); }
    shown.push(...await page.evaluate(() => [...document.querySelectorAll('tr.erow[data-ev]')].map(tr => {
      const r = tr.getBoundingClientRect(); const closed = tr.closest('details:not([open])');
      // a BET row (rank 0) is what must never sit in a closed dropdown; held / dropped rows keep their size text but are not bets
      return { ev: tr.dataset.ev, side: tr.dataset.side, oside: tr.dataset.oside || '', sized: tr.dataset.sized === '1' && tr.dataset.rank === '0',
               visible: !closed && r.width > 0 && r.height > 0, text: tr.innerText.replace(/\s+/g, ' ').slice(0, 90) };
    })));
  }
  await browser.close();

  const vis = shown.filter(x => x.visible);
  const missing = [], held = [];
  for (const b of want) {
    // 11/8: a soccer 'not to win' flag and a win flag on the other team show as one row (Chelsea not to win + Sunderland to win)
    const N = s => /^not_/.test(s || '') ? ({home: 'away', away: 'home'})[s.slice(4)] : s;
    // a 'Mixed, no lean' row (sharps on both sides of the game) shows every flag in it, with no side of its own (11/8: Saints -10.5 / -2.5)
    const hit = vis.filter(x => String(x.ev) === String(b.event_id) && (x.side === b.side || x.oside === b.side || (N(x.side) === N(b.side) && N(b.side)) || (!x.side && /Mixed, no lean/.test(x.text))));
    if (!hit.length) missing.push(b);
    else if (!hit.some(x => x.sized)) held.push(b);
  }
  const hidden = shown.filter(x => !x.visible && x.sized);
  // the system-bet file must have been rebuilt within the tracker's schedule (3 runs a day, longest gap about 17 hours overnight)
  const sysAgeH = (now - Date.parse(SY.built || 0)) / 3600e3;
  const stale = sysAgeH > 18;
  const fmt = b => `${b.sport} ${b.game} ${b.market} ${b.side}${b.line != null ? ' ' + b.line : ''} (${b.cat}, ${b.rule || b.src})`;
  const out = { checked: new Date().toISOString(), site: SITE, bets_in_window: want.length, rows_visible: vis.length,
                missing: missing.map(fmt), held_unsized: held.map(fmt), sized_rows_hidden_in_dropdowns: hidden.map(x => x.text),
                system_file_age_h: +sysAgeH.toFixed(1), sharp_c: sharpC, unmatched: unmatched.map(u => `${u.game} ${u.bet || ''}`), page_errors: errors, ok: !missing.length && !hidden.length && !stale && !errors.length };
  fs.writeFileSync('board_check.json', JSON.stringify(out, null, 1));
  console.log(`[board check] ${want.length} sized open bets in the window; ${vis.length} rows visible; missing ${missing.length}; held (shown, no size) ${held.length}; sized rows inside closed dropdowns ${hidden.length}; system file ${sysAgeH.toFixed(1)}h old; page errors ${errors.length}`);
  for (const m of out.missing) console.log('  MISSING  ' + m);
  for (const h of out.sized_rows_hidden_in_dropdowns) console.log('  HIDDEN   ' + h);
  if (stale) console.log(`  STALE    system-bet file built ${SY.built}`);
  for (const e of errors) console.log('  PAGE ERROR ' + e);
  for (const u of unmatched) console.log(`  NO GAME MATCH (opposition not checked) ${u.game} ${u.bet || u.side || ''} (${u.cat})`);
  if (!out.ok && process.env.NTFY_TOPIC) {
    const msg = [missing.length && `${missing.length} bet(s) not on the board: ${out.missing.slice(0, 3).join('; ')}`,
                 hidden.length && `${hidden.length} sized row(s) inside a closed dropdown`, stale && `system bets ${sysAgeH.toFixed(0)}h old`,
                 errors.length && `page error: ${errors[0]}`].filter(Boolean).join(' | ');
    await fetch(`https://ntfy.sh/${process.env.NTFY_TOPIC}`, { method: 'POST', headers: { Title: 'Board check failed', Priority: 'high' }, body: msg }).catch(() => {});
  }
  process.exit(out.ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
