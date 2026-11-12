// The board's rules, checked. src/boardview.ts is a port of functions in boards/templates/tracker.html (headline, kindOf,
// facEntries, facInfo, insIdOf) and src/board.ts carries its normCheck. This runs BOTH over made-up cards and fails when they answer
// differently, so a change to the board's rules that is not carried into the app shows up as a failing test instead of two pages
// that quietly disagree. Three of the board's rules cannot be run next to the app's - whose turn a card is and whether it is new
// (in the app those are SQL, in ehpa.insurance_refresh_cards) and the filters, sort and counts (the top of the board's render()) -
// so their text in tracker.html is pinned by a fingerprint: when it changes, this test fails and says where to carry the change.
// It also checks what only the app has: the search, the count line, the as-of line, and that nothing from a card reaches the page
// unescaped. Made-up data only - no patient ever appears in this file. Run: npm test
import { build } from "esbuild";
import { readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createHash } from "node:crypto";
import assert from "node:assert/strict";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const tmp = mkdtempSync(join(tmpdir(), "ehpadb-test-"));
let failed = 0, passed = 0;
const test = (name, fn) => { try { fn(); passed++; } catch (e) { failed++; console.error("FAIL  " + name + "\n      " + String(e && e.message ? e.message : e).split("\n").slice(0, 6).join("\n      ")); } };

try {
  // ---- the app's side: bundle the two modules for node --------------------------------------------------------------------------
  await build({ entryPoints: [resolve(root, "src/boardview.ts"), resolve(root, "src/board.ts")], outdir: tmp, bundle: true, format: "esm", platform: "node", target: ["node22"], outExtension: { ".js": ".mjs" }, logLevel: "silent" });
  const view = await import(pathToFileURL(join(tmp, "boardview.mjs")).href);
  const server = await import(pathToFileURL(join(tmp, "board.mjs")).href);

  // ---- the board's side: the block of tracker.html that holds its rules --------------------------------------------------------
  const tracker = readFileSync(resolve(root, "../../boards/templates/tracker.html"), "utf8");
  const a = tracker.indexOf("let items=[]; let filter="), b = tracker.indexOf("function render(){", a);
  assert.ok(a > 0 && b > a, "could not find the board's rules in boards/templates/tracker.html (this test reads the block from `let items=[]; let filter=` up to `function render(){`); update the markers here and carry any rule change into src/boardview.ts");
  const orig = new Function(tracker.slice(a, b) + "\nreturn { headline, normCheck, insIdOf, kindOf, facEntries, facInfo, turnOf, newness, KIND_LABEL };")();
  // every name either kindOf knows, read from its own text: a name added or dropped on one side then shows up as a difference
  const words = (fn) => String(fn).match(/[A-Z][A-Z ]*[A-Z]/g) || [];
  const KNOWN = [...new Set([...words(orig.kindOf), ...words(view.kindOf)])];

  // ---- made-up inputs --------------------------------------------------------------------------------------------------------
  const long = "This sentence has no full stop and keeps going so that the headline has to be cut at a word boundary somewhere before the two hundred and thirtieth character which is the longest a headline may be on a card and then some more words follow to make sure of it";
  const NEEDS = [null, undefined, "", "   ", "Short.", "Need the MBI.", "Need the current insurance plan and its member id.", "WILLIAM: Need a new facesheet from the facility. Then the claim can go.",
    "WILLIAM FLAG: Which plan since 3/2026? The chart shows two.", "CLAUDE: Checking eligibility with the payer tonight. Will post the result.", "DONE 9/14: Rebilled to the Medicare plan. Paid.",
    "RESOLVED by the 10/3 run: plan re-pointed. Nothing more needed.", "CLOSED (duplicate): see the other card. This one is done.", "Rebilled 10/3: sent to the secondary. Waiting on the remit.",
    "No terminator here at all but long enough to be a headline by itself", long, long + ". And a second sentence.", "First line\nsecond line continues. Third sentence here.", "Ends with a question mark here? Then more.",
    "Ends with bang right here now! Then more text.", "DONE: ok.", "claude : lower case prefix works too. Second.", "A sentence with an abbreviation e.g. this one keeps going. Next."];
  // every length around the numbers in headline (15, 80, 215, 230): a first sentence of n characters, with and without spaces to cut at
  for (let n = 1; n <= 260; n++) NEEDS.push("ab ".repeat(90).slice(0, n) + ". Next one.", "x".repeat(n) + ". Next one.", "y".repeat(n) + " " + "x".repeat(250));
  const PLACES = ["", null, "Brookdale Hermitage ALF", "Azalea Gardens Assisted Living", "Aviata (admit 9/25 from TMH)", "Centre Pointe Health & Rehab", "Center Pointe", "Eden Springs Nursing", "Seven Hills", "St. Jasper", "St Jasper",
    "HCA Rehab", "Inpatient Rehab Unit", "IRF", "TMH", "HCA", "Capital Regional Medical Center", "Memorial ER", "Emergency Department", "Independent Living at The Pines", "IL", "Developmental Center", "ICF",
    "Telehealth", "Individual Patient Homes", "Home", "North Florida Senior Care", "Office", "SNF", "NF", "LTC", "Skilled Unit", "Rehab", "Westminster Oaks Health Center", "SNF / ALF", "SNF (99306 8/27/2026)",
    "ALF", "Some Unknown Place", "Harbor Chase", "HarborChase of Somewhere", "Memory Care Cottage", "Grove at Canopy", "Tapestry", "Parry House", "Bertrand", "Lake Park", "Aspire", "Oakes", "Brynwood", "a & b"];
  const blank = { facnow: null, facilities: null, lastfac: null, lastdos: null, facility: null };
  const FACS = [blank,
    { ...blank, facnow: { name: "Aviata", kind: "SNF", dos: "10/26/2026" } }, { ...blank, facnow: { name: "TMH", dos: "11/01/2026", res: { name: "Brookdale Hermitage ALF" } } },
    { ...blank, facnow: { name: "Somewhere", kind: "hosp", dos: "", res: { name: "Eden Springs", kind: "snf" } } }, { ...blank, facnow: { kind: "SNF" }, lastfac: "Lake Park", lastdos: "09/30/2026" },
    { ...blank, facnow: [], facility: "SNF" }, { ...blank, facnow: "text", facility: "ALF" },
    { ...blank, facilities: "TMH 10/26 · Brookdale Hermitage ALF 8/26–10/26 · Eden Springs 7/26 (Pam)" }, { ...blank, facilities: "Brookdale Hermitage ALF 9/26-10/26" }, { ...blank, facilities: "No Date Place · Other 1/26" },
    { ...blank, facilities: "HCA Rehab 10/26 · Somewhere Unknown 9/26" }, { ...blank, facilities: "   ·  " }, { ...blank, lastfac: "Seven Hills", lastdos: "10/02/2026" }, { ...blank, lastfac: "Mystery", lastdos: null },
    { ...blank, facility: "SNF / ALF" }, { ...blank, facility: "SNF (99306 8/27/2026)" }, { ...blank, facility: "ALF" }, { ...blank, facility: "NF" }, { ...blank, facility: "TMH/HCA" }, { ...blank, facility: "  Westminster Oaks  " }, { ...blank, facility: "Somewhere else" }];
  for (const k of KNOWN) FACS.push({ ...blank, facnow: { name: k } }, { ...blank, facilities: k + " 9/26–10/26 · Example Place 8/26" }, { ...blank, lastfac: k, lastdos: "10/02/2026" }, { ...blank, facility: k });
  const INS = [{ insid: "ABC123", inscarrier: "MEDICARE", mbi: "1AA0AA0AA00" }, { insid: "", inscarrier: "X", mbi: "1AA0AA0AA00" }, { insid: null, inscarrier: null, mbi: null }, { insid: "Z9", inscarrier: null, mbi: null }, { insid: "", inscarrier: "", mbi: "" }];
  const CHECKS = [null, undefined, "text", 7, [], {}, { ok: "ok", src: "Stedi 271", result: "active 1/1/2026", when: "9/14" }, { ok: "no", src: "AMD eligibility", result: "inactive", when: "9/15" }, { ok: "na", src: "Discovery", result: "" },
    { ok: "human", src: "William", result: "call the facility", when: "9/16" }, { ok: "yes", src: "Old shape", result: "found" }, { ok: true, src: "bool", result: "x" },
    { result: "ok", step: "eligibility", text: "active", at: "2026-10-01T05:00:00Z" }, { result: "no", step: "mbi lookup", text: "not found", at: "2026-10-01T05:00:00Z" }, { result: "found", step: "discovery", text: "a plan" },
    { result: "human", text: "no step at all" }, { result: "na" }, { result: "unknown word", step: 0 }, { src: "", result: "ok", text: "empty src means the run's shape" }, { src: "S", step: "T", result: "R", text: "X", when: "W", at: "2026-10-02T05:00:00Z" }];

  // ---- the port answers as the board does -----------------------------------------------------------------------------------
  test("headline: same first sentence and rest as the board, at every length", () => { for (const n of NEEDS) assert.deepEqual(view.headline(n), orig.headline(n), "need " + String(JSON.stringify(n)).slice(0, 60)); });
  test("kindOf: same kind of place as the board, for every name either side knows and every pair of them", () => {
    for (const p of [...PLACES, ...KNOWN, ...KNOWN.flatMap((x) => KNOWN.map((y) => x + " " + y))]) assert.equal(view.kindOf(p), orig.kindOf(p), "place " + JSON.stringify(p));
  });
  test("KIND_LABEL: same labels as the board", () => assert.deepEqual(view.KIND_LABEL, orig.KIND_LABEL));
  test("facEntries: same reading of the facilities line", () => { for (const f of FACS) assert.deepEqual(view.facEntries(f), orig.facEntries(f), JSON.stringify(f.facilities)); });
  test("facInfo: same facility, kind, date and residence as the board", () => { for (const f of FACS) assert.deepEqual(view.facInfo(f), orig.facInfo(f), JSON.stringify(f)); });
  test("insIdOf: same insurance id and carrier as the board", () => { for (const i of INS) assert.deepEqual(view.insIdOf(i), orig.insIdOf(i), JSON.stringify(i)); });
  test("normCheck: same result, source and text for both shapes of a check", () => {
    for (const c of CHECKS) {
      const mine = server.normCheck(c), theirs = orig.normCheck(c);
      assert.deepEqual({ k: mine.k, src: mine.src, res: mine.res }, { k: theirs.k, src: theirs.src, res: theirs.res }, JSON.stringify(c));
      assert.equal(!!(mine.when || mine.at), !!theirs.when, "a time shows on one side only: " + JSON.stringify(c));
    }
    // the one place the port does NOT follow the board: a result spelled like a built-in property name (the board's lookup table is a
    // plain object, so 'toString' passes for a known result there and prints a function as the icon); here it is simply unknown
    for (const word of ["toString", "constructor", "__proto__", "hasOwnProperty"]) { assert.equal(server.normCheck({ result: word, step: "s" }).k, "na"); assert.equal(server.normCheck({ ok: word, src: "s" }).k, "na"); }
  });
  test("turnOf, newness and render()'s filter, sort and counts: as they were when ported", () => {
    const c = tracker.indexOf("const list=$('#list');", b);
    assert.ok(c > b, "could not find the top of the board's render() (from `function render(){` up to its `const list=` line)");
    const now = createHash("sha256").update((String(orig.turnOf) + String(orig.newness) + tracker.slice(b, c)).replace(/\s+/g, "")).digest("hex").slice(0, 16);
    assert.equal(now, "0bc43d5a4afc2ee8", "the board's turn / new rule or its filter, sort or counts changed in tracker.html. Carry the change into ehpa.insurance_refresh_cards (tools/db/neon_schema.sql: turn, is_new) and into passes() / visibleCards() / counts() in src/boardview.ts, then put the new value (" + now + ") here");
  });

  // ---- what only the app has ----------------------------------------------------------------------------------------------------
  const card = (o) => ({ id: "id-" + o.patient, patient: null, chart: null, dob: null, turn: "claude", need: null, why: null, amount: null, insid: null, inscarrier: null, mbi: null, insplans: null,
    facnow: null, facilities: null, lastfac: null, lastdos: null, facility: null, updated: null, notes_n: 0, checks_n: 0, api_n: 0, is_new: false, last_note_who: null, last_note_at: null, last_note_text: null, last_note_more: false, ...o });
  const board = { url: "https://example.invalid/board", synced_at: "2026-11-11T08:42:03Z", changed_at: "2026-11-11T08:42:00Z", items: [
    card({ patient: "ZETA,ANN", turn: "william", is_new: true, amount: 100, chart: "1001", need: "WILLIAM: Need a new facesheet from the facility. Then rebill.", facility: "SNF" }),
    card({ patient: "alpha,bob", turn: "william", is_new: false, amount: 50, chart: "1002", inscarrier: "MEDICARE", insid: "ABC123" }),
    card({ patient: "Alpha,Bob", turn: "claude", amount: 500, chart: "1003", facilities: "Brookdale Hermitage ALF 9/26–10/26 · TMH 8/26" }),
    card({ patient: "MIDDLE,CAT", turn: "claude", amount: null, chart: "1004", is_new: true }),          // new only counts on William's turn
    card({ patient: "OMEGA,DAN", turn: "done", amount: 900, chart: "1005", lastfac: "Seven Hills" }),
    card({ patient: null, turn: "done", amount: 0, chart: null }),
  ] };
  const names = (f, q = "") => view.visibleCards(board, { filter: f, query: q }).map((c) => c.patient);
  test("filters: the six the board has", () => {
    assert.deepEqual(names("william"), ["alpha,bob", "ZETA,ANN"]);
    assert.deepEqual(names("new"), ["ZETA,ANN"]);
    assert.deepEqual(names("claude"), ["Alpha,Bob", "MIDDLE,CAT"]);
    assert.deepEqual(names("open"), ["Alpha,Bob", "alpha,bob", "MIDDLE,CAT", "ZETA,ANN"]);   // A to Z, then the larger amount first
    assert.deepEqual(names("done"), [null, "OMEGA,DAN"]);
    assert.equal(names("all").length, 6);
  });
  test("search: looks through every card, whatever the filter; every word must match", () => {
    assert.deepEqual(names("william", "omega"), ["OMEGA,DAN"]);
    assert.deepEqual(names("done", "1003"), ["Alpha,Bob"]);
    assert.deepEqual(names("done", "brookdale alpha"), ["Alpha,Bob"]);
    assert.deepEqual(names("all", "medicare abc123"), ["alpha,bob"]);
    assert.deepEqual(names("all", "facesheet"), ["ZETA,ANN"]);
    assert.deepEqual(names("all", "nobody-by-this-name"), []);
    assert.deepEqual(names("william", "   "), ["alpha,bob", "ZETA,ANN"]);
  });
  test("counts: your turn, new, Claude's turn, dollars waiting, done", () => assert.deepEqual(view.counts(board), { mine: 2, fresh: 1, claude: 2, waiting: 650, done: 2, all: 6 }));

  const st = (o = {}) => ({ filter: "william", query: "", open: new Set(), details: new Map(), ...o });
  const balanced = (html) => { for (const t of ["article", "div", "span", "button", "p", "b"]) assert.equal((html.match(new RegExp("<" + t + "[ >]", "g")) || []).length, (html.match(new RegExp("</" + t + ">", "g")) || []).length, "unbalanced <" + t + ">"); };
  test("a card: the board's wording for each turn", () => {
    const mine = view.cardHtml(board.items[0], st());
    assert.ok(mine.includes("New: what I need from you") && mine.includes("Need a new facesheet from the facility.") && mine.includes(">Then rebill.<") && mine.includes("$100") && mine.includes('class="rb-pill new"'));
    assert.ok(view.cardHtml(board.items[1], st()).includes("What I need from you") && view.cardHtml(board.items[1], st()).includes("(nothing written yet)"));
    assert.ok(view.cardHtml(board.items[2], st()).includes("Claude is on it") && view.cardHtml(board.items[2], st()).includes("Seen at: Brookdale Hermitage ALF"));
    assert.ok(!view.cardHtml(board.items[3], st()).includes("rb-pill new"), "a card on Claude's turn is never New");
    assert.ok(view.cardHtml(board.items[5], st()).includes("(no name on the card)") && !view.cardHtml(board.items[5], st()).includes("no active plan"));
    assert.ok(view.cardHtml(board.items[1], st()).includes('<span class="car">MEDICARE</span>') && view.cardHtml(board.items[0], st()).includes("no active plan on the chart"));
    for (const c of board.items) balanced(view.cardHtml(c, st()));
  });
  test("a card's notes: asked for only when opened; latest marked; Stedi lookups marked", () => {
    const c = card({ patient: "NOTES,ED", notes_n: 2, checks_n: 2, api_n: 1, last_note_who: "Claude", last_note_at: "2026-11-10T05:00:00Z", last_note_text: "x".repeat(280), last_note_more: true });
    const shut = view.cardHtml(c, st());
    assert.ok(shut.includes('aria-expanded="false"') && shut.includes("Show notes (2), lookup trail (2), API results (1)") && shut.includes("latest of 2") && !shut.includes("rb-detail"));
    assert.ok(view.cardHtml(c, st({ open: new Set([c.id]), details: new Map([[c.id, "loading"]]) })).includes("Loading the notes"));
    assert.ok(view.cardHtml(c, st({ open: new Set([c.id]), details: new Map([[c.id, { error: "Session expired - sign in again." }]]) })).includes("Session expired"));
    const detail = { id: c.id, notes: [{ who: "William", at: "2026-11-09T05:00:00Z", text: "first" }, { who: "Claude", at: "2026-11-10T05:00:00Z", text: "second" }],
      checks: [{ k: "ok", src: "Stedi 271", res: "active", when: "9/14", at: "" }, { k: "bogus", src: "AMD", res: "inactive", when: "", at: "2026-10-01T05:00:00Z" }], api: [{ src: "eligibility", at: "2026-10-01", text: "{ }" }] };
    const open = view.cardHtml(c, st({ open: new Set([c.id]), details: new Map([[c.id, detail]]) }));
    assert.ok(open.includes('aria-expanded="true"') && open.includes("Hide notes (2)") && open.includes("Notes · 2") && open.includes("<b>latest</b>") && open.includes('class="rb-by w"') && open.includes('class="rb-by c"'));
    assert.ok(open.includes('class="tr ok stedi"') && open.includes('class="tr na"') && open.includes("(9/14)") && open.includes('class="ab"'));
    balanced(open);
    assert.ok(!view.cardHtml(card({ patient: "BARE,AL" }), st()).includes("data-card"), "no button when there is nothing more to show");
  });
  test("nothing from a card reaches the page as markup", () => {
    const bad = '"><img src=x onerror=alert(1)><script>alert(2)</script>';
    const c = card({ id: 'x" onclick="y', patient: bad, chart: bad, dob: bad, need: "WILLIAM: " + bad + " and enough words to be a sentence. " + bad, why: bad, insid: bad, inscarrier: bad, insplans: bad + " · " + bad,
      facnow: { name: bad, kind: bad, dos: bad, res: { name: bad, kind: bad } }, facilities: bad + " · " + bad, updated: bad, notes_n: 1, checks_n: 1, api_n: 1, last_note_who: bad, last_note_at: bad, last_note_text: bad });
    const detail = { id: c.id, notes: [{ who: bad, at: bad, text: bad }], checks: [{ k: bad, src: bad, res: bad, when: bad, at: bad }], api: [{ src: bad, at: bad, text: bad }] };
    const html = view.cardHtml(c, st({ open: new Set([c.id]), details: new Map([[c.id, detail]]) })) + view.boardShellHtml({ ...board, url: 'https://x.invalid/" onmouseover="z', items: [c] }, st({ query: bad }));
    for (const s of ["<img", "<script", 'onclick="y', 'onmouseover="z', "onerror=alert(1)>"]) assert.ok(!html.includes(s), "unescaped: " + s);
    assert.ok(html.includes('data-id="x&quot; onclick=&quot;y"') && html.includes("&lt;img src=x onerror=alert(1)&gt;"));
    assert.ok(!/class="fkind [^"]*[^a-z "][^"]*"/.test(html), "a facility kind is only ever letters in the class");
    balanced(html);
  });
  test("the view: counts, the as-of line, the filters, the count line, the list", () => {
    const fresh = view.boardShellHtml(board, st(), Date.parse("2026-11-11T20:00:00Z"));
    assert.ok(fresh.includes("Copied from the board") && !fresh.includes("rb-asof stale") && fresh.includes(">1 new<") && fresh.includes('class="tile accent"') && fresh.includes("$650") && fresh.includes('data-f="william" aria-pressed="true"') && fresh.includes('data-f="done" aria-pressed="false"'));
    assert.ok(fresh.includes('href="https://example.invalid/board" target="_blank" rel="noopener noreferrer"') && fresh.includes('<p id="board-count" class="rb-count" role="status" aria-live="polite">2 cards</p>'));
    const stale = view.boardShellHtml(board, st(), Date.parse("2026-11-13T09:00:00Z"));
    assert.ok(stale.includes("rb-asof stale") && stale.includes("The nightly copy has not run since"));
    assert.ok(view.boardShellHtml({ ...board, synced_at: null }, st()).includes("No copy of the board has been recorded yet."));
    assert.equal(view.boardCountText(board, st({ filter: "new" })), "1 card");
    assert.ok(view.boardListHtml({ ...board, items: [] }, st({ filter: "new" })).includes("Nothing new."));
    assert.ok(view.boardCountText(board, st({ query: "omega" })).startsWith("1 of 6 cards match") && view.boardListHtml(board, st({ query: "zzzz" })).includes("No card matches that."));
    // while a search is typed no filter is in force, so none shows as pressed
    assert.ok(!view.boardShellHtml(board, st({ filter: "done", query: "omega" })).includes('aria-pressed="true"') && view.boardShellHtml(board, st({ filter: "done", query: "  " })).includes('data-f="done" aria-pressed="true"'));
    balanced(fresh);
  });
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
console.log(failed ? `${failed} failed, ${passed} passed` : `all ${passed} checks passed (the board's rules in tracker.html and the port in src/boardview.ts agree)`);
process.exit(failed ? 1 : 0);
