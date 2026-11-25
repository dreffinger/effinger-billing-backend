#!/usr/bin/env node
// PLAIN ENGLISH (self-test of the Insurance Refresh Board page, 11/25/2026)
// Decides: nothing. Opens boards/templates/tracker.html in a headless browser with a stand-in board store and a stand-in Google
//   Drive (no network, no patient data - every card, file and id here is invented) and proves the page's "Run updates from Drive"
//   sync does what the billing runs rely on:
//     1. EVERY run file in the Drive inbox is read - the listing is followed page by page (Drive answered 5 files and a
//        "next page" token on 11/25/2026; the page stopped at the first page, so most run files never reached the board);
//     2. a file the page applied is RECORDED in the registry (meta/drive_sync) and never applied twice - the store hands the page
//        frozen data, and writing into it was silently dropped, so nothing had been recorded since September;
//     3. when several waiting files touch one card, the NEWEST file's status / need / why win (the old page kept the oldest:
//        its own stamp from the first file made every later one look out of date);
//     4. William's own action on a card still wins over a file written before it - measured against the time the run READ the
//        board (`asof`) when the file carries it;
//     5. a run file can never wipe what is on a card: notes / checks / api are added to, never replaced - even when a file sends
//        the whole card again (that is how William's 11/19 answers on two cards were erased);
//     6. a file too old to speak for a card is recorded as skipped, and stays recorded;
//     7. the "$ waiting" tile adds up even when a card's amount was typed as text ("$315.00") - one such card made the tile read $0.
// Never touches: AdvancedMD, Drive, the real board. Run: node tools/selftest/test_board_page.js   (needs the pre-installed Playwright)
'use strict';
const fs = require('fs'), path = require('path'), os = require('os');
const { chromium } = require('playwright');
const ROOT = path.resolve(__dirname, '..', '..');
const PAGE = process.env.BOARD_PAGE || path.join(ROOT, 'boards', 'templates', 'tracker.html');

// ---- the stand-in runtime injected before the page's own script: window.claude.use('db' | 'mcp' | 'downloads')
const MOCK = `(() => {
  const cfg = window.__cfg || {};
  const clone = o => JSON.parse(JSON.stringify(o));
  const deepFreeze = o => { if (o && typeof o === 'object' && !Object.isFrozen(o)) { Object.freeze(o); for (const k of Object.keys(o)) deepFreeze(o[k]); } return o; };
  const store = new Map(Object.entries(cfg.docs || {}).map(([k, v]) => [k, clone(v)]));
  const listeners = []; const log = window.__log = { drive: [], writes: [] };
  let pending = false;
  const notify = () => { if (pending) return; pending = true; Promise.resolve().then(() => { pending = false; for (const l of listeners.slice()) l(); }); };
  // the store's contract: delivered snapshots and their data() are FROZEN
  const snap = p => { const has = store.has(p); const data = has ? deepFreeze(clone(store.get(p))) : undefined; return { id: p.split('/').pop(), exists: has, data: () => data, metadata: { fromCache: false, hasPendingWrites: false } }; };
  const merge = (dst, src) => { for (const [k, v] of Object.entries(src)) { if (v && typeof v === 'object' && !Array.isArray(v) && dst[k] && typeof dst[k] === 'object' && !Array.isArray(dst[k])) merge(dst[k], v); else dst[k] = clone(v); } };
  const body = d => { if (!d || typeof d !== 'object' || Array.isArray(d)) throw { code: 'invalid_argument', message: 'body must be an object' }; return clone(d); };
  const docRef = p => ({ id: p.split('/').pop(), path: p,
    get: async () => snap(p),
    set: async d => { store.set(p, body(d)); log.writes.push(['set', p]); notify(); },
    update: async d => { if (!store.has(p)) throw { code: 'invalid_argument', message: 'update needs the document' }; merge(store.get(p), body(d)); log.writes.push(['update', p, Object.keys(d)]); notify(); },
    delete: async () => { store.delete(p); log.writes.push(['delete', p]); notify(); },
    acquire: async () => ({ acquired: true }),
    onSnapshot: next => { const f = () => next(snap(p)); listeners.push(f); Promise.resolve().then(f); return () => {}; },
    collection: c => colRef(p + '/' + c) });
  const colRef = c => {
    const docsOf = () => [...store.keys()].filter(k => k.startsWith(c + '/') && k.slice(c.length + 1).indexOf('/') < 0).sort().map(snap);
    const qs = () => { const docs = docsOf(); return { docs, size: docs.length, empty: !docs.length, docChanges: () => [], metadata: { fromCache: false, hasPendingWrites: false } }; };
    const q = { path: c, get: async () => qs(), onSnapshot: next => { const f = () => next(qs()); listeners.push(f); Promise.resolve().then(f); return () => {}; }, doc: id => docRef(c + '/' + id), where: () => q, orderBy: () => q, limit: () => q };
    return q; };
  const db = Object.freeze({ doc: docRef, collection: colRef });
  const b64 = s => btoa(unescape(encodeURIComponent(s)));
  const mcp = Object.freeze({ callTool: async (server, tool, input) => {
    input = input || {}; log.drive.push([tool, clone(input)]);
    if (server !== 'Google Drive') throw { code: 'server_not_connected', message: server };
    if (cfg.failDriveAtCall && log.drive.length === cfg.failDriveAtCall) throw { code: 'server_unavailable', message: 'test outage' };
    if (cfg.refuseOrderBy && tool === 'search_files' && input.orderBy) throw { code: 'tool_error', message: 'orderBy is not supported' };
    if (tool === 'search_files') {
      // as the real connector answered on 11/25/2026: newest first, SHORT pages whatever pageSize asks for, a token for the next page
      let list = (cfg.files || []).slice().sort((a, b) => String(b.createdTime).localeCompare(String(a.createdTime)));
      const m = String(input.query || '').match(/title contains '([^']+)'/); if (m) list = list.filter(f => f.title.includes(m[1]));
      const size = Math.min(Number(input.pageSize) || 100, cfg.pageSize || 5);
      const start = input.pageToken ? Number(String(input.pageToken).replace('tok-', '')) : 0;
      const out = { files: list.slice(start, start + size).map(f => ({ id: f.id, title: f.title, createdTime: f.createdTime, modifiedTime: f.createdTime, mimeType: 'application/json' })) };
      if (start + size < list.length) out.nextPageToken = 'tok-' + (start + size);
      return { content: [], payload: out };
    }
    if (tool === 'download_file_content') { const f = (cfg.files || []).find(x => x.id === input.fileId); if (!f) throw { code: 'tool_error', message: 'no such file' }; return { content: [], payload: { content: b64(JSON.stringify(f.body)) } }; }
    throw { code: 'not_in_manifest', message: tool };
  } });
  window.claude = Object.freeze({ use: async n => n === 'db' ? db : n === 'mcp' ? mcp : n === 'downloads' ? { save: async () => {} } : null });
  window.__store = { get: p => store.has(p) ? clone(store.get(p)) : null, keys: () => [...store.keys()], put: (p, v) => { store.set(p, clone(v)); notify(); } };
})();`;

const FAILS = []; let N = 0;
const check = (name, ok, detail) => { N++; console.log((ok ? 'ok   ' : 'FAIL ') + name + (ok || detail === undefined ? '' : '  -> ' + JSON.stringify(detail))); if (!ok) FAILS.push(name); };
const iso = msAgo => new Date(Date.now() - msAgo).toISOString();
const H = 3600e3, D = 24 * H;
const file = (n, msAgo, ops, extra) => ({ id: 'file-' + n, title: 'board_updates_' + n + '.json', createdTime: iso(msAgo), body: Object.assign({ schema: 'irb-board-updates/1', source: 'test ' + n, created: iso(msAgo), ops }, extra || {}) });
const card = (o) => Object.assign({ patient: 'TEST,CARD', dob: '', facility: '', amdid: '', mbi: '', need: 'old need', why: '', amount: 0, status: 'claude', notes: [], created: iso(30 * D), updated: iso(30 * D) }, o || {});
const REG0 = { applied: { 'gone-1': { title: 'board_updates_gone.json', at: iso(60 * D), ops: 1, failed: 0, error: 'x'.repeat(170) } }, lastCheck: iso(1 * D), codeRev: 20261112, note: 'test registry' };

let browser, wrapped;
async function open(cfg) {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.route(/^https?:/, r => r.abort());                       // fonts / pdf.js: not needed here
  const errors = []; page.on('pageerror', e => errors.push(String(e)));
  await page.addInitScript(c => { window.__cfg = c; }, cfg);
  await page.addInitScript({ content: MOCK });
  await page.goto('file://' + wrapped);
  const settle = async () => page.waitForFunction(() => { const el = document.querySelector('#sync-st'); return !!el && /(^|\s)(ok|err)(\s|$)/.test(el.className); }, null, { timeout: 20000 });
  await settle();
  return {
    page, errors,
    get: p => page.evaluate(q => window.__store.get(q), p),
    put: (p, v) => page.evaluate(([q, w]) => window.__store.put(q, w), [p, v]),
    keys: () => page.evaluate(() => window.__store.keys()),
    drive: () => page.evaluate(() => window.__log.drive),
    writes: () => page.evaluate(() => window.__log.writes),
    status: () => page.evaluate(() => document.querySelector('#sync-st').textContent),
    text: sel => page.evaluate(s => (document.querySelector(s) || {}).textContent, sel),
    resync: async () => { await page.evaluate(() => window.__ehpaRefresh()); await settle(); },
    close: () => ctx.close(),
  };
}

(async () => {
  const tpl = fs.readFileSync(PAGE, 'utf8');
  wrapped = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'irb-page-')), 'board.html');
  fs.writeFileSync(wrapped, '<!doctype html><html><head><meta charset=utf8></head><body>' + tpl + '</body></html>');
  browser = await chromium.launch();
  try {
    // ---------- 1 + 2: every page of the listing, each file recorded, nothing applied twice
    {
      const files = []; for (let i = 1; i <= 12; i++) files.push(file('n' + String(i).padStart(2, '0'), (13 - i) * H, [{ op: 'upsert', collection: 'items', id: 'new-' + i, set: { patient: 'NEW,' + i, status: 'william', need: 'ask ' + i, amount: 10 } }]));
      const t = await open({ docs: { 'meta/drive_sync': REG0 }, files, pageSize: 5 });
      const keys = await t.keys();
      check('1. all 12 run files reach the board although Drive lists 5 at a time', keys.filter(k => k.startsWith('items/new-')).length === 12, keys.filter(k => k.startsWith('items/new-')).length);
      const reg = await t.get('meta/drive_sync');
      check('2. every applied file is recorded in the registry', files.every(f => reg.applied[f.id]), Object.keys(reg.applied).length);
      check('2. a registry entry written by hand is trimmed to 80 characters (the save really carries the applied map)', !reg.applied['gone-1'] || String(reg.applied['gone-1'].error || '').length <= 80, reg.applied['gone-1']);
      const before = await t.get('items/new-3'); const w0 = (await t.writes()).filter(w => w[1].startsWith('items/')).length;
      await t.resync();
      const after = await t.get('items/new-3'); const w1 = (await t.writes()).filter(w => w[1].startsWith('items/')).length;
      check('2. a second check applies nothing: no card is written again', w1 === w0, { w0, w1 });
      check('2. a second check leaves the card stamp alone', !!before && !!after && before.updated === after.updated, [before && before.updated, after && after.updated]);
      check('2. the status line says it is up to date', /up to date/i.test(await t.status()), await t.status());
      check('no script error on the page', t.errors.length === 0, t.errors);
      await t.close();
    }
    // ---------- 3: several waiting files on one card - the newest file's state wins
    {
      const files = [
        file('a', 3 * D, [{ op: 'upsert', collection: 'items', id: 'x', set: {}, append: { checks: [{ ok: 'no', src: 'run a', result: 'nothing yet', when: '1/1' }] } }]),
        file('b', 2 * D, [{ op: 'upsert', collection: 'items', id: 'x', set: { status: 'william', need: 'N2 - the card is back with you' }, append: { notes: [{ who: 'Claude', text: 'still needed', at: iso(2 * D) }] } }]),
        file('c', 1 * D, [{ op: 'upsert', collection: 'items', id: 'x', set: { why: 'because c' }, append: { checks: [{ ok: 'no', src: 'run c', result: 'still nothing', when: '1/3' }] } }]),
      ];
      const x = card({ notes: [{ who: 'William', text: 'my answer', at: iso(5 * D) }], updated: iso(5 * D) });
      const t = await open({ docs: { 'meta/drive_sync': REG0, 'items/x': x }, files, pageSize: 5 });
      const r = await t.get('items/x');
      check('3. the later file hands the card back: status william', r.status === 'william', r.status);
      check('3. the later file\'s need is on the card', r.need === 'N2 - the card is back with you', r.need);
      check('3. the newest file\'s why is on the card', r.why === 'because c', r.why);
      check('3. every file\'s checks and notes landed', (r.checks || []).length === 2 && (r.notes || []).length === 2, [(r.checks || []).length, (r.notes || []).length]);
      await t.close();
    }
    // ---------- 4: William's action after the file was written wins; `asof` is the time the run read the board
    {
      const files = [
        file('old', 2 * H, [{ op: 'upsert', collection: 'items', id: 'y', set: { status: 'william', need: 'old ask' }, append: { notes: [{ who: 'Claude', text: 'note from the old file', at: iso(2 * H) }] } }]),
        file('lateupload', 0.5 * H, [{ op: 'upsert', collection: 'items', id: 'z', set: { status: 'william', need: 'asked before he answered' } }], { asof: iso(2 * H) }),
        file('nominal', 0.25 * H, [{ op: 'upsert', collection: 'items', id: 'v', set: { status: 'william', need: 'body time is later than the upload' } }]),
      ];
      files[2].body.created = iso(-3 * H);                              // a body that claims a time AFTER its real upload (seen 11/19/2026)
      const answered = id => card({ status: 'claude', need: 'his answer is here', notes: [{ who: 'William', text: 'answer ' + id, at: iso(1 * H) }], updated: iso(1 * H) });
      const v = card({ status: 'claude', need: 'his answer is here', notes: [{ who: 'William', text: 'answer v', at: iso(0.1 * H) }], updated: iso(0.1 * H) });
      const t = await open({ docs: { 'meta/drive_sync': REG0, 'items/y': answered('y'), 'items/z': answered('z'), 'items/v': v }, files, pageSize: 5 });
      const y = await t.get('items/y'), z = await t.get('items/z'), vv = await t.get('items/v');
      check('4. a file written before his answer does not take the card back', y.status === 'claude' && y.need === 'his answer is here', [y.status, y.need]);
      check('4. ... but its note still lands', y.notes.some(n => n.text === 'note from the old file'), y.notes.length);
      check('4. a file uploaded after his answer but READ before it (asof) does not take the card back', z.status === 'claude' && z.need === 'his answer is here', [z.status, z.need]);
      check('4. a body time later than the real upload is not trusted over the upload time', vv.status === 'claude', vv.status);
      await t.close();
    }
    // ---------- 5: a file can never wipe a card's notes / checks / api
    {
      const t6 = iso(6 * H);                                             // one timestamp, shared by the file and the card it created
      const full = { patient: 'WHOLE,CARD', amdid: '1234567', status: 'william', need: 'CHP number needed', notes: [{ who: 'Claude', text: 'created by the run', at: t6 }], checks: [{ ok: 'human', src: 'William', result: 'number', when: '1/1' }], api: [{ src: 'api', at: t6, text: 'block' }] };
      const files = [
        file('whole', 6 * H, [{ op: 'upsert', collection: 'items', id: 'w', set: full }]),
        file('again', 5.75 * H, [{ op: 'upsert', collection: 'items', id: 'w', set: full }]),                 // the same whole card, sent again - still before his answer
        file('repl', 4 * H, [{ op: 'replace', collection: 'items', id: 'r', data: { patient: 'REPLACED,CARD', status: 'claude', need: 'rewritten by its run', notes: [{ who: 'Claude', text: 'new text', at: iso(4 * H) }] } }]),
      ];
      const w = card({ patient: 'WHOLE,CARD', amdid: '1234567', status: 'claude', need: 'CHP number needed', updated: iso(5.5 * H),
        notes: [{ who: 'Claude', text: 'created by the run', at: t6 }, { who: 'William', text: 'HIS ANSWER - must survive', at: iso(5.5 * H) }],
        checks: [{ ok: 'human', src: 'William', result: 'number', when: '1/1' }, { ok: 'ok', src: 'a later run', result: 'kept', when: '1/2' }], api: [{ src: 'api', at: t6, text: 'block' }] });
      const r0 = card({ patient: 'REPLACED,CARD', updated: iso(10 * D), notes: [{ who: 'Claude', text: 'old text', at: iso(11 * D) }, { who: 'William', text: 'HIS OLD WORD', at: iso(10 * D) }] });
      const t = await open({ docs: { 'meta/drive_sync': REG0, 'items/w': w, 'items/r': r0 }, files, pageSize: 5 });
      const a = await t.get('items/w'), r = await t.get('items/r');
      check('5. his answer is still on the card after the run file is applied again', a.notes.some(n => n.text === 'HIS ANSWER - must survive'), a.notes.map(n => n.text));
      check('5. the card is still on Claude\'s turn (he answered after both files)', a.status === 'claude', a.status);
      check('5. a check added by a later run is still there, and nothing is doubled', a.checks.length === 2 && a.notes.length === 2 && a.api.length === 1, [a.checks.length, a.notes.length, a.api.length]);
      check('5. a replace keeps William\'s own notes', r.need === 'rewritten by its run' && r.notes.some(n => n.text === 'HIS OLD WORD') && r.notes.some(n => n.text === 'new text'), r.notes.map(n => n.text));
      await t.close();
    }
    // ---------- 6: a file too old to speak for a card is recorded as skipped (and stays recorded); a direct write is respected
    {
      const files = [
        file('ancient', 15 * D, [{ op: 'upsert', collection: 'items', id: 'q', set: { status: 'william', need: 'two weeks old' } }]),
        file('recent', 2 * H, [{ op: 'upsert', collection: 'items', id: 'd', set: { status: 'william', need: 'written before the chat closed it' } }]),
        file('fresh', 0.2 * H, [{ op: 'upsert', collection: 'items', id: 'd2', set: { status: 'william', need: 'newer than the chat write' } }]),
      ];
      const q = card({ status: 'claude', need: 'current' });
      // a chat session wrote these two cards directly: it sets `updated`, and knows nothing of the page's own bookkeeping
      const d = card({ status: 'done', need: 'closed by a chat', stateAt: iso(5 * D), syncAt: iso(5 * D), updated: iso(1 * H) });
      const d2 = card({ status: 'claude', need: 'chat note', stateAt: iso(5 * D), syncAt: iso(5 * D), updated: iso(1 * H) });
      const t = await open({ docs: { 'meta/drive_sync': REG0, 'items/q': q, 'items/d': d, 'items/d2': d2 }, files, pageSize: 5 });
      const reg = await t.get('meta/drive_sync');
      check('6. a file older than 10 days is not applied', (await t.get('items/q')).need === 'current');
      check('6. ... and is recorded as skipped', !!reg.applied['file-ancient'] && /skipped/.test(String(reg.applied['file-ancient'].error || '')), reg.applied['file-ancient']);
      check('6. a card a chat closed after the file was written stays closed', (await t.get('items/d')).status === 'done', (await t.get('items/d')).status);
      check('6. a file newer than the chat\'s write does apply', (await t.get('items/d2')).status === 'william', (await t.get('items/d2')).status);
      await t.resync();
      const reg2 = await t.get('meta/drive_sync');
      check('6. the skipped file is still recorded after another check', !!reg2.applied['file-ancient'], Object.keys(reg2.applied));
      check('6. an entry whose file left the inbox long ago is forgotten, entries of files still listed are kept', !reg2.applied['gone-1'] && !!reg2.applied['file-recent'] && !!reg2.applied['file-fresh'], Object.keys(reg2.applied));
      await t.close();
    }
    // ---------- 7: the tiles
    {
      const docs = { 'meta/drive_sync': REG0,
        'items/t1': card({ status: 'william', amount: 100 }), 'items/t2': card({ status: 'william', amount: '$315.00' }),
        'items/t3': card({ status: 'claude', amount: '$0 open (visit 19456964 settled)' }), 'items/t4': card({ status: 'claude', amount: '' }),
        'items/t5': card({ status: 'claude', amount: '1,250.50' }), 'items/t6': card({ status: 'done', amount: 999 }) };
      const t = await open({ docs, files: [], pageSize: 5 });
      await t.page.waitForFunction(() => document.querySelector('#n-william').textContent !== '–');
      check('7. Your turn counts the two cards', (await t.text('#n-william')) === '2', await t.text('#n-william'));
      check('7. "$ waiting" adds text amounts instead of reading $0', (await t.text('#n-amount')) === '$1,666', await t.text('#n-amount'));
      check('7. the Your turn tile carries its own dollars', /\$415/.test(await t.text('#n-william-l')), await t.text('#n-william-l'));
      await t.close();
    }
    // ---------- 8: an outage half way through the listing applies nothing and records nothing
    {
      const files = []; for (let i = 1; i <= 8; i++) files.push(file('o' + i, (9 - i) * H, [{ op: 'upsert', collection: 'items', id: 'out-' + i, set: { patient: 'OUT,' + i, status: 'william' } }]));
      const t = await open({ docs: { 'meta/drive_sync': REG0 }, files, pageSize: 5, failDriveAtCall: 2 });
      const keys = await t.keys(); const reg = await t.get('meta/drive_sync');
      check('8. a listing that failed part way applies no file', keys.filter(k => k.startsWith('items/out-')).length === 0, keys);
      check('8. ... and says so instead of "up to date"', !/up to date/i.test(await t.status()), await t.status());
      check('8. ... and the registry keeps what it had', !!reg.applied['gone-1'], Object.keys(reg.applied));
      await t.close();
    }
    // ---------- 9: a connector that refuses the ordered listing is asked again without the order
    {
      const files = []; for (let i = 1; i <= 7; i++) files.push(file('u' + i, (8 - i) * H, [{ op: 'upsert', collection: 'items', id: 'un-' + i, set: { patient: 'UN,' + i, status: 'william' } }]));
      const t = await open({ docs: { 'meta/drive_sync': REG0 }, files, pageSize: 5, refuseOrderBy: true });
      const keys = await t.keys();
      check('9. the listing still works when the ordered form is refused', keys.filter(k => k.startsWith('items/un-')).length === 7, [keys.length, await t.status()]);
      await t.close();
    }
  } finally { await browser.close(); }
  console.log(FAILS.length ? '\n' + FAILS.length + ' of ' + N + ' checks FAILED' : '\nall ' + N + ' checks passed');
  process.exit(FAILS.length ? 1 : 0);
})().catch(e => { console.error('test harness error:', e); process.exit(2); });
