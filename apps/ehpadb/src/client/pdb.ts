// The Practice Database page's views on this site (tools/db/practice_db_page.html; its address comes from /api/links, never from here):
// Overview, Census inputs, Billing runs, ERA, Approvals, Raw data and Mirror & sources, drawn the way the page draws them, from the
// same documents read out of Neon (/api/pdb/*, pdb.ts). The page's other views on this site (Accounts receivable, Denials, Nightly
// cascade, Credentialing, Treasury, Routines) stay the generic tables of views.ts; where a generic view of the same name exists, its
// tables are kept underneath a richer view ("The same data as plain tables"). Pages: #db/<view>.
// Chart ids, dates of service, codes and dollars only - no patient name, birth date or member id is asked for here.
import { $, esc, api, cached, safeUrl } from "./core";
import { genericInto, drawDays, drawPairs, isoDay, fdate, longDay, daysAgo, eachDay, type DayRow, type NightRow } from "./dashboard";

export const DB_NAV: [string, string][] = [
  ["overview", "Overview"], ["feed", "Census inputs"], ["runs", "Billing runs"], ["era", "ERA"], ["approvals", "Approvals"],
  ["ar", "Accounts receivable"], ["denials", "Denials"], ["cascade", "Nightly cascade"], ["credentialing", "Credentialing"],
  ["treasury", "Treasury"], ["routines", "Routines"], ["data", "Raw data"], ["mirror", "Mirror & sources"],
];
const RICH = new Set(["overview", "feed", "runs", "era", "approvals", "data", "mirror"]);
const label = (v: string) => (v.charAt(0).toUpperCase() + v.slice(1)).replace(/_/g, " ");
// the rail: the page's views first, then the generic ones the server defines (a generic view added later still appears)
export function dbNav(generic: string[]): [string, string][] {
  const known = new Set(DB_NAV.map(([k]) => k));
  return [...DB_NAV.filter(([k]) => RICH.has(k) || generic.includes(k)), ...generic.filter((g) => !known.has(g)).map((g) => [g, label(g)] as [string, string])];
}
export const isRichView = (v: string) => RICH.has(v);

// ---- formatting (the page's) -----------------------------------------------------------------------------------------------------
const fmt = (n: unknown) => Number(n || 0).toLocaleString("en-US");
const usd = (n: unknown) => "$" + Number(n || 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
const usd2 = (n: unknown) => "$" + Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const when = (s: unknown) => { if (!s) return ""; const d = new Date(String(s)); return isNaN(d.getTime()) ? String(s) : d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); };
const hoursSince = (s: unknown): number | null => { if (!s) return null; const t = new Date(String(s)).getTime(); return isNaN(t) ? null : (Date.now() - t) / 36e5; };
const ago = (s: unknown) => { const h = hoursSince(s); if (h === null) return s ? String(s) : "never"; if (h < 1) return Math.max(1, Math.round(h * 60)) + " min ago"; if (h < 48) return Math.round(h) + " h ago"; return Math.round(h / 24) + " days ago"; };
const etDate = (s: unknown) => { const d = new Date(String(s)); if (isNaN(d.getTime())) return ""; try { return d.toLocaleDateString("en-CA", { timeZone: "America/New_York" }); } catch { return isoDay(d); } };
const dayOf = (s: unknown) => String(s || "").slice(0, 10);
const fileDay = (s: unknown) => String(s || "").replace(/^(\d{4})(\d{2})(\d{2})$/, "$1-$2-$3");
const plural = (n: number, one: string, many: string) => fmt(n) + " " + (n === 1 ? one : many);
const ls = { get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* private window */ } } };
const tile = (l: string, v: string, s = "", cls = "") => `<div class="tile ${esc(cls)}"><div class="tile-l">${esc(l)}</div><div class="tile-v">${esc(v)}</div>${s ? `<div class="tile-s">${esc(s)}</div>` : ""}</div>`;
const block = (title: string, note: string, body: string, id = "") => `<section class="block"${id ? ` id="${esc(id)}"` : ""}><header><h2>${esc(title)}</h2>${note ? `<span class="note">${esc(note)}</span>` : ""}</header>${body}</section>`;
const pill = (cls: string, text: string) => `<span class="pill ${esc(cls)}">${esc(text)}</span>`;
const ext = (url: unknown, text: string) => { const u = safeUrl(url); return u ? `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(text)}</a>` : esc(text); };
const plain = (name: string) => `<details class="more" id="plain-${esc(name)}"><summary>The same data as plain tables (ehpa.* views)</summary><div id="generic"></div></details>`;
function wirePlain(name: string) {
  const d = document.getElementById("plain-" + name) as HTMLDetailsElement | null; if (!d) return;
  d.addEventListener("toggle", () => { const box = d.querySelector("#generic") as HTMLElement; if (d.open && !box.dataset.done) { box.dataset.done = "1"; box.innerHTML = `<p class="note">Loading…</p>`; genericInto(name, box, { charts: false }).catch((e) => { box.innerHTML = `<p class="note">${esc(e.message || String(e))}</p>`; }); } });
}

export async function showDb(view: string): Promise<void> {
  const main = $("#main");
  if (view === "overview") return showOverview(main);
  if (view === "feed") return showFeed(main);
  if (view === "runs") return showRuns(main);
  if (view === "era") return showEra(main);
  if (view === "approvals") return showApprovals(main);
  if (view === "data") return showData(main);
  if (view === "mirror") return showMirror(main);
}

// ==== OVERVIEW =====================================================================================================================
type Ov = {
  docs: Record<string, number>; neon: { documents: number; sources: number; last_load: string | null };
  feed: { rows: number; entered: number; not_entered: number; entered_dollars: number }; batches: { n: number; incomplete: string[] };
  last_check: any; last_run: any; last_engine: any; last_era: any; approvals: any; repo: any; cascade: any;
  copies: { pages: number; last_sync: any }; pages: [string, string, string, string][];
};
async function showOverview(main: HTMLElement) {
  const o = await api<Ov>("/api/pdb/overview");
  const docs = Object.values(o.docs || {}).reduce((a, n) => a + Number(n || 0), 0);
  const lc = o.last_check, lr = o.last_run, appr = o.approvals, waiting = Number(appr?.counts?.waiting || 0);
  const tiles = [
    tile("Documents in the practice database", fmt(docs), plural(Object.keys(o.docs || {}).length, "collection", "collections") + " on Neon (source practice_db)", "accent"),
    tile("Feed encounters on hand", fmt(o.feed.rows), fmt(o.feed.entered) + " entered · " + fmt(o.feed.not_entered) + " not entered"),
    tile("Entered by the feed", usd(o.feed.entered_dollars), "fee schedule, all batches"),
    tile("Last feed check", lc ? ago(lc.at) : "—", lc ? String(lc.result || "").replace("_", " ") + " · " + when(lc.at) : "none yet", lc && (hoursSince(lc.at) ?? 99) < 26 ? "ok" : "warn"),
    tile("Last billing run", lr ? ago(lr.at) : "—", lr ? (lr.mode || "") + " · " + when(lr.at) : "none yet"),
    tile("Approvals waiting", appr ? fmt(waiting) : "—", appr ? usd(appr.dollars_waiting) : "no snapshot", appr && waiting ? "warn" : "ok"),
  ].join("");

  // "Is it working?" - the page's checks, from the same documents (the last one is about the Neon copy instead of the page's own limit)
  const H: [string, string, string][] = []; const push = (st: string, title: string, text: string) => H.push([st, title, text]);
  push("ok", "Neon answered", "This view read the practice's Neon Postgres just now: " + fmt(o.neon.documents) + " documents from " + plural(o.neon.sources, "source", "sources") + ".");
  const ageH = hoursSince(lc?.at);
  push(ageH === null ? "bad" : ageH < 26 ? "ok" : "warn", "Feed checked in the last day", lc ? "Last check " + when(lc.at) + " (" + String(lc.result || "").replace("_", " ") + "). The daily task runs 8:34 PM ET; the Billing Button checks on every press." : "No feed check in the database - the next feed run writes one.");
  const nf = lc?.newest_file ? fileDay(lc.newest_file) : null; const nfAge = nf ? Math.round((Date.now() - new Date(nf + "T12:00:00").getTime()) / 864e5) : null;
  push(nfAge === null ? "warn" : nfAge <= 2 ? "ok" : "warn", "Claimocity still delivering", nf && nfAge !== null ? "Newest feed file is dated " + fdate(nf) + (nfAge > 2 ? " - " + nfAge + " days old: check the Cloud Run copy job (claimocity/cloud_run/DEPLOY.md) or Claimocity's delivery." : " (" + plural(nfAge, "day", "days") + " old; Claimocity posts one to two days after the visit).") : "No file date recorded yet.");
  const inc = o.batches?.incomplete || [];
  push(inc.length ? "warn" : "ok", "Every feed message accounted for", inc.length ? inc.length + " batch(es) have fewer rows loaded than messages (" + inc.join(", ") + ") - a part may still be loading." : fmt(o.batches?.n) + " batches, " + fmt(o.feed.rows) + " messages, each with an AdvancedMD outcome.");
  push(o.feed.not_entered ? "warn" : "ok", "Everything billable is in AdvancedMD", o.feed.not_entered ? fmt(o.feed.not_entered) + " encounter(s) are not entered - open Census inputs and filter by a \"Not entered\" reason; each row says why and what clears it." : "Every feed encounter on hand was entered or was already there.");
  const rh = hoursSince(lr?.at);
  push(rh === null ? "bad" : rh < 7 ? "ok" : rh < 26 ? "warn" : "bad", "Billing runs are happening", lr ? "Last run " + when(lr.at) + " (" + (lr.mode || "") + ", " + (lr.status || "") + "). The Claude routine runs every 6 hours and brings the engine's 2-hourly reports with it." : "No billing run in the database yet.");
  const cs = o.cascade, cday = cs ? cs.night || etDate(cs.at) : null;
  push(!cday ? "bad" : cday >= daysAgo(1) ? "ok" : cday >= daysAgo(3) ? "warn" : "bad", "Nightly cascade recorded", cs && cday ? "Last night recorded: " + fdate(cday) + " - " + fmt(cs.checked) + " checked, " + fmt(cs.changed) + " changed" + (Number(cs.dollars_resent) ? ", " + usd(cs.dollars_resent) + " re-sent" : "") + ". The run writes its row at the end of every night (tools/db/cascade_record.py, STEP 5b); a night it could not write is swept in by the next billing run." : "No cascade night in the database yet.");
  const eng = o.last_engine, eh = hoursSince(eng?.at);
  push(eh === null ? "warn" : eh < 9 ? "ok" : eh < 30 ? "warn" : "bad", "Engine reports reaching the database", eng ? "Newest engine report here: " + when(eng.at) + (eng.note ? " (" + eng.note + ")" : "") + ". The engine runs every 2 hours; a Claude run sweeps its reports in within about 6 hours." : "No engine report in the database yet - the next Claude run sweeps them in.");
  const le = o.last_era, ed = hoursSince(le?.at);
  push(ed === null ? "warn" : ed / 24 < 8 ? "ok" : "warn", "ERAs are being posted", le ? "Last posting " + when(le.at) + ": " + fmt(le.line_count) + " lines, " + usd2(le.paid_total) + "." : "No ERA posting recorded yet.");
  push(appr && waiting ? "warn" : "ok", "Approvals", appr ? fmt(waiting) + " waiting (" + usd(appr.dollars_waiting) + "), " + fmt(appr.counts?.approved || 0) + " approved and not yet applied, " + fmt(appr.counts?.done || 0) + " done - snapshot " + when(appr.at) + "." : "No approvals snapshot yet.");
  const repo = o.repo;
  push(repo ? "ok" : "warn", "GitHub main in step", repo ? "Repository head " + (repo.head || "") + " at " + when(repo.at) + " · " + fmt(repo.counts?.registers) + " registers, " + fmt(repo.counts?.button_reports) + " run reports." : "No repository snapshot yet.");
  const sy = o.copies?.last_sync, syH = hoursSince(sy?.at);
  push(o.copies?.pages ? (syH === null ? "warn" : syH < 50 ? "ok" : "warn") : "warn", "Other pages copied here", sy ? "Last sync " + when(sy.at) + ": " + fmt(sy.boards_checked) + " pages, " + fmt(sy.collections_changed) + " copied, " + fmt(sy.collections_unchanged) + " unchanged." + ((syH ?? 0) >= 50 ? " The daily sync has not run in two days - open its routine." : "") : o.copies?.pages ? o.copies.pages + " page copies loaded by hand; no daily sync has run yet (William creates the routine from nightly/practice_db_sync_prompt_v1.txt)." : "No other page has been copied here yet.");
  const ll = hoursSince(o.neon.last_load);
  push(ll === null ? "warn" : ll < 26 ? "ok" : "warn", "Neon is being loaded", o.neon.last_load ? "Last load " + when(o.neon.last_load) + " (ops.load_log). Every billing run copies what it wrote; a day without a load means the runs could not reach Neon." : "No load is recorded in ops.load_log yet.");
  const bad = H.filter((h) => h[0] === "bad").length, warn = H.filter((h) => h[0] === "warn").length;

  main.innerHTML = `<h1>Overview</h1><p class="lead">The Practice Database page, read from the practice's Neon Postgres: what the database holds, whether every routine is writing to it, and the newest numbers the engine reported.</p>
    <section class="tiles" aria-label="Database at a glance">${tiles}</section>
    ${block("Is it working?", bad ? bad + " failing · " + warn + " to watch" : warn ? warn + " to watch, nothing failing" : "all checks pass",
      `<div class="health">${H.map(([st, t, x]) => `<div class="hc ${esc(st)}"><span class="dot" aria-hidden="true"></span><div><b>${esc(t)}</b><span>${esc(x)}</span></div></div>`).join("")}</div>`)}
    <div id="ov-generic"><p class="note">Loading the charts…</p></div>
    <div class="grid2">
      ${block("Where this view reads from", "", `<p>The Practice Database page on claude.ai reads its own artifact database. This site reads the same documents from the practice's permanent store on Neon - <code>raw.documents</code> (source <code>practice_db</code>) through the <code>ehpa.*</code> views of <code>tools/db/neon_schema.sql</code> - so both show the same feed, runs, ERA postings and approvals. Every run writes both: the page's database with ArtifactData, then Neon with <code>tools/db/neon_db.py load-writes</code>.</p><p class="note">Chart ids, dates of service, codes and dollars only. The CCM notes (patient names and birth dates) are in their own section, behind the same sign-in.</p>`)}
      ${block("Billing project pages", "one tap each", `<div class="pages">${(o.pages || []).map(([t, u, k, n]) => { const inside = u.startsWith("#"); const href = inside ? u : safeUrl(u); return href ? `<a href="${esc(href)}"${inside ? "" : ' target="_blank" rel="noopener noreferrer"'}><span class="nm"><span>${esc(t)}</span><span class="kd">${esc(k)}</span></span><span class="nt">${esc(n)}</span></a>` : ""; }).join("")}</div>`)}
    </div>`;
  const box = document.getElementById("ov-generic");
  genericInto("overview", box).catch((e) => { if (box) box.innerHTML = `<p class="note">${esc(e.message || String(e))}</p>`; });
}

// ==== CENSUS INPUTS (the Claimocity feed) ===========================================================================================
type FRow = { batch: string; bat: string | null; p: string; v: string; d: string; c: string[]; dx: string[]; fac: string; pos: string; lead: string; prov: string; fee: number | null; s: string; hold: string; why: string; verdict: string; newchart: string; file: string; pd: string };
type Feed = { columns: string[]; rows: unknown[][]; truncated: boolean; on_hand: { rows: number; dos_min: string | null; dos_max: string | null; pulled_min: string | null; pulled_max: string | null };
  batches: number; lookups: { fac: Record<string, string>; car: Record<string, string>; prov: Record<string, string> }; files: { stamp: string; date: string; messages: string; name: string }[];
  holds: { chart_id: string; hold: string; dos: string }[]; checks: any[]; cascade: any[]; days: any[] };

// the page's groupings (ported from tools/feed/feed_monitor.py by the page)
function service(c: string): string {
  c = (c || "").toUpperCase();
  if (["99221", "99222", "99223"].includes(c)) return "Hospital admission"; if (["99231", "99232", "99233"].includes(c)) return "Hospital follow-up";
  if (["99238", "99239"].includes(c)) return "Hospital discharge"; if (["99234", "99235", "99236"].includes(c)) return "Observation same-day";
  if (/^9928[1-5]$/.test(c)) return "Emergency visit"; if (["99304", "99305", "99306"].includes(c)) return "SNF admission";
  if (["99307", "99308", "99309", "99310"].includes(c)) return "SNF follow-up"; if (["99315", "99316"].includes(c)) return "SNF discharge";
  if (/^9934[1-9]$|^99350$/.test(c)) return "Home / ALF visit"; if (["99487", "99489", "99490", "99491", "99437", "99439", "G0506"].includes(c)) return "Chronic care management";
  if (["99497", "99498"].includes(c)) return "Advance care planning"; if (["G0438", "G0439", "G0402"].includes(c)) return "Annual wellness";
  if (["99495", "99496"].includes(c)) return "Transitional care"; if (["99358", "99359", "G2211", "G0136"].includes(c)) return "Prolonged / add-on";
  return "Other";
}
const MA = new Set(["HUM01", "UNI20", "CAP07", "UHCMA", "WEL04", "AET12", "AET07", "CIG13", "DEV01", "CPL01", "FBM01"]);
const MCD = new Set(["FLO99", "FCC", "SUN01", "SIM01", "MCAD", "MOL01", "STA01", "HUMMD"]);
function payerCat(code: string, name: string): string {
  if (!code) return "No active plan"; const c = code.toUpperCase(), n = (name || "").toUpperCase();
  if (MA.has(c) || /ADVANTAGE|DUAL COMPLETE|MEDICARE HMO|MEDICARE PPO|CAREPLUS|DEVOTED|WELLCARE/.test(n)) return "Medicare Advantage";
  if (MCD.has(c) || /MEDICAID|MCD|COMMUNITY CARE|SUNSHINE STATE|SIMPLY|MOLINA|STAYWELL|LTC/.test(n)) return "Medicaid / LTC";
  if (["MC", "FLO02", "MCR"].includes(c) || /\bMEDICARE\b/.test(n)) return "Medicare";
  if (["VACCN", "TRI05", "TRI01"].includes(c) || /\bVA\b|VETERAN|TRICARE|CCN/.test(n)) return "VA / TRICARE";
  return "Commercial / other";
}
const STATUS: Record<string, [string, string]> = { entered: ["Entered in AdvancedMD", "ok"], already: ["Already in AdvancedMD", "dim"], hold: ["Entered - insurance hold", "warn"], dx: ["Not entered - diagnosis code not in AMD list", "warn"],
  deceased: ["Not entered - after date of death", "bad"], cpt: ["Not entered - unknown CPT", "warn"], skipped: ["Not entered - skipped", "warn"], failed: ["Failed", "bad"], nochart: ["No chart matched", "bad"],
  voided: ["Entered, then voided", "dim"], unrecorded: ["Outcome not recorded", "dim"] };
const NOT_IN = ["dx", "deceased", "cpt", "skipped", "failed", "nochart"];
const rowStatus = (r: FRow) => (r.s === "entered" && r.hold ? "hold" : r.s);

let fwin = ls.get("ehpa-feed-win") || "week";
let reconFilter = ls.get("ehpa-recon-filter") || "all", reconShown = 200, reconQ = "", reconSort = "date";
function feedRange(): [string, string] | null { const t = isoDay(new Date()); return fwin === "week" ? [daysAgo(6), t] : fwin === "month" ? [daysAgo(29), t] : null; }

function hbars(list: { name: string; [k: string]: any }[], o: { key: string; alt?: boolean; cls?: (r: any) => string; extra?: (r: any) => string }): string {
  if (!list.length) return `<div class="note">Nothing in this window.</div>`;
  const max = Math.max(1, ...list.map((r) => Number(r[o.key] || 0)));
  return `<div class="hbars">${list.map((r) => { const v = Number(r[o.key] || 0); const w = Math.max(2, Math.round((100 * v) / max)); const cls = o.cls ? o.cls(r) : o.alt ? "alt" : ""; const x = o.extra ? o.extra(r) : "";
    return `<div class="hb" title="${esc(r.name)}"><span class="nm">${esc(r.name)}</span><span class="tr"><i class="${esc(cls)}" style="width:${w}%"></i></span><span class="vl">${fmt(v)}${x ? `<small>${esc(x)}</small>` : ""}</span></div>`; }).join("")}</div>`;
}
function group(rs: FRow[], keyf: (r: FRow, cpt: string) => string) {
  const cnt: Record<string, number> = {}, dol: Record<string, number> = {}, vis: Record<string, number> = {};
  rs.forEach((r) => { const seen = new Set<string>(); const cs = r.c || []; cs.forEach((cpt) => { const k = keyf(r, cpt); cnt[k] = (cnt[k] || 0) + 1; dol[k] = (dol[k] || 0) + Number(r.fee || 0) / Math.max(1, cs.length); if (!seen.has(k)) { vis[k] = (vis[k] || 0) + 1; seen.add(k); } }); });
  return Object.keys(cnt).sort((a, b) => cnt[b] - cnt[a]).map((k) => ({ name: k, lines: cnt[k], visits: vis[k], dollars: dol[k] }));
}
function dayRows(rows: FRow[], dayOfRow: (r: FRow) => string, lo: string, hi: string): DayRow[] {
  const by: Record<string, { visits: number; lines: number; dollars: number; pats: Set<string>; notin: number }> = {};
  const at = (k: string) => by[k] || (by[k] = { visits: 0, lines: 0, dollars: 0, pats: new Set(), notin: 0 });
  rows.forEach((r) => { const k = dayOfRow(r); if (!k || k < lo || k > hi) return; if (r.s === "entered") { const d = at(k); d.visits++; d.lines += (r.c || []).length; d.dollars += Number(r.fee || 0); d.pats.add(r.p); } else if (NOT_IN.includes(r.s)) at(k).notin++; });
  return eachDay(lo, hi).map((k) => { const e = by[k]; return { date: k, visits: e ? e.visits : 0, lines: e ? e.lines : 0, dollars: e ? e.dollars : 0, patients: e ? e.pats.size : 0, notin: e ? e.notin : 0 }; });
}

async function showFeed(main: HTMLElement) {
  const r = feedRange();
  const doc = await cached<Feed>("/api/pdb/feed" + (r ? `?from=${r[0]}&to=${r[1]}` : ""));
  const cols = doc.columns || [];
  const all: FRow[] = (doc.rows || []).map((a) => { const o: any = {}; cols.forEach((c, i) => { o[c] = a[i]; }); o.d = dayOf(o.d); o.pd = dayOf(o.pd); o.c = Array.isArray(o.c) ? o.c : []; o.dx = Array.isArray(o.dx) ? o.dx : []; return o as FRow; });
  const L = doc.lookups || { fac: {}, car: {}, prov: {} };
  const today = isoDay(new Date());
  const ds = all.map((x) => x.d).filter(Boolean).sort();
  const [lo, hi] = r || [ds[0] || today, (ds[ds.length - 1] || today) > today ? ds[ds.length - 1] : today];
  const rs = all.filter((x) => x.d && x.d >= lo && x.d <= hi);
  const ent = rs.filter((x) => x.s === "entered"), notEntered = rs.filter((x) => NOT_IN.includes(x.s)), holdsW = rs.filter((x) => x.s === "entered" && x.hold);
  const pats = new Set(ent.map((x) => x.p)), newc = new Set(rs.filter((x) => x.newchart).map((x) => x.p));
  const tiles = [
    tile("Feed encounters", fmt(rs.length), "messages Claimocity sent for these dates"),
    tile("Entered in AdvancedMD", fmt(ent.length), plural(pats.size, "patient", "patients") + " · " + fmt(ent.reduce((a, x) => a + (x.c || []).length, 0)) + " charge lines", "accent"),
    tile("Charges entered", usd(ent.reduce((a, x) => a + Number(x.fee || 0), 0)), "fee schedule, as entered"),
    tile("Not entered", fmt(notEntered.length), notEntered.length ? "see the table - each has its reason" : "every encounter is in", notEntered.length ? "warn" : "ok"),
    tile("Insurance holds", fmt(holdsW.length), "entered, waiting on a plan or facesheet", holdsW.length ? "warn" : ""),
    tile("New charts", fmt(newc.size), "patients the feed brought in"),
  ].join("");
  // the two day charts: by date of service, and by the Eastern-time day the visit was pulled into AdvancedMD
  const dos = drawDays(dayRows(rs, (x) => x.d, lo, hi), { fill: "accent", label: "Encounters per date of service", verb: "entered", what: "carry feed encounters" });
  const pds = all.map((x) => x.pd).filter(Boolean).sort();
  const [plo, phi] = r || [pds[0] || lo, (pds[pds.length - 1] || today) > today ? pds[pds.length - 1] : today];
  const pulled = drawDays(dayRows(all, (x) => x.pd, plo, phi), { fill: "pulled", label: "Encounters per date pulled into AdvancedMD", verb: "pulled in", what: "had visits pulled into AdvancedMD" });
  // the nightly cascade: one row per night (the newest row of a night wins)
  const byNight: Record<string, any> = {};
  (doc.cascade || []).forEach((c) => { const k = c.night || etDate(c.at); if (k && (!byNight[k] || String(c.at || "") > String(byNight[k].at || ""))) byNight[k] = c; });
  const keys = Object.keys(byNight).sort();
  let cascadeHtml = `<p class="note">No nightly cascade run is recorded yet. Each night appears as a pair of purple bars once its row is written to the <code>cascade_runs</code> collection.</p>`, cascadeNote = "", logRows = "", weekText = "";
  if (keys.length) {
    const clo = keys[0] > lo ? keys[0] : lo, chi = keys[keys.length - 1] > today ? keys[keys.length - 1] : today;
    const nights: NightRow[] = eachDay(clo, chi).map((k) => { const c = byNight[k]; return { date: k, run: c ? { checked: Number(c.checked || 0), changed: Number(c.changed || 0), dollars: Number(c.dollars || 0), done: c.done || "", at: c.at || "" } : null }; });
    const drawn = drawPairs(nights); cascadeHtml = drawn.svg; cascadeNote = drawn.note;
    const inw = nights.filter((n) => n.run).reverse();
    logRows = inw.length ? inw.map((n) => { const c = byNight[n.date]; return `<tr><td class="mono" style="white-space:nowrap">${esc(longDay(n.date))}</td><td class="num">${fmt(c.checked)}</td><td class="num">${fmt(c.changed)}</td><td class="num">${Number(c.dollars) ? usd(c.dollars) : "—"}</td><td>${esc(c.done || "")}${c.note ? `<div class="note">${esc(c.note)}</div>` : ""}</td></tr>`; }).join("")
      : `<tr><td colspan="5" class="note">No run recorded in this window - the last recorded night is ${esc(longDay(keys[keys.length - 1]))}.</td></tr>`;
    // the paragraph under the chart: the past 7 days, written from the same rows
    const wlo = daysAgo(6); const wk = keys.filter((k) => k >= wlo && k <= today); const runs = wk.map((k) => byNight[k]);
    if (!runs.length) weekText = "Past 7 days (" + fdate(wlo) + " – " + fdate(today) + "): no nightly cascade run is recorded here.";
    else {
      const ck = runs.reduce((a, x) => a + Number(x.checked || 0), 0), ch = runs.reduce((a, x) => a + Number(x.changed || 0), 0), dol = runs.reduce((a, x) => a + Number(x.dollars || 0), 0);
      weekText = "Past 7 days (" + fdate(wlo) + " – " + fdate(today) + "): the nightly cascade ran on " + plural(runs.length, "recorded night", "recorded nights") + ", checked " + fmt(ck) + " visit-and-plan pairs, changed " + plural(ch, "visit", "visits") + " in AdvancedMD and re-sent " + usd(dol) + " to the right payer.";
      const top = runs.slice().sort((a, b) => Number(b.dollars || 0) - Number(a.dollars || 0))[0]; if (top && Number(top.dollars)) weekText += " The biggest night was " + fdate(top.night || etDate(top.at)) + ": " + String(top.done || "").replace(/\.$/, "") + ".";
      const quiet = runs.filter((x) => !Number(x.changed)); if (quiet.length) weekText += " " + quiet.map((x) => fdate(x.night || etDate(x.at))).join(", ") + " needed no AdvancedMD change" + (quiet.length === 1 && quiet[0].done ? " (" + String(quiet[0].done).replace(/\.$/, "") + ")" : "") + ".";
      const gaps = eachDay(keys[0] > wlo ? keys[0] : wlo, today).filter((k) => !byNight[k]); if (gaps.length) weekText += " No run is recorded here yet for " + gaps.map(fdate).join(", ") + ".";
    }
  } else logRows = `<tr><td colspan="5" class="note">Nothing recorded yet.</td></tr>`;
  // the last 14 days of scheduled runs (Eastern time), every day listed so a day nothing reached shows as zeros
  const dayMap: Record<string, any> = {}; (doc.days || []).forEach((d) => { dayMap[dayOf(d.day)] = d; });
  const days14 = eachDay(daysAgo(13), today).reverse();
  const runsDay = days14.map((k) => { const d = dayMap[k] || {}; const c = byNight[k];
    return `<tr><td class="mono" style="white-space:nowrap">${esc(longDay(k))}</td><td class="num">${fmt(d.engine)}${Number(d.eng_cascade) ? ` <span class="note">incl. cascade profile</span>` : ""}</td><td class="num">${fmt(d.claude)}</td><td class="num">${Number(d.feed) ? fmt(d.feed) + (Number(d.ingested) ? ` <b>· ${plural(Number(d.ingested), "ingest", "ingests")}, ${fmt(d.visits)} visits</b>` : "") : `<span class="note">none</span>`}</td><td class="num">${Number(d.era_lines) ? fmt(d.era_lines) + " · " + usd2(d.era_paid) : `<span class="note">none</span>`}</td><td>${c ? pill("ok", fmt(c.checked) + " checked · " + fmt(c.changed) + " changed" + (Number(c.dollars) ? " · " + usd(c.dollars) + " re-sent" : "")) : pill("dim", "no row")}</td><td class="mono">${d.last_at ? esc(when(d.last_at)) : ""}</td></tr>`; }).join("");
  const runTotal = days14.reduce((a, k) => a + Number(dayMap[k]?.engine || 0) + Number(dayMap[k]?.claude || 0), 0);
  // the breakdowns
  const oc: Record<string, number> = {}; rs.forEach((x) => { const k = rowStatus(x); oc[k] = (oc[k] || 0) + 1; });
  const dxc: Record<string, number> = {}; rs.forEach((x) => { new Set(x.dx || []).forEach((d) => { dxc[d] = (dxc[d] || 0) + 1; }); });
  const seen = new Set<string>();
  const holds = (doc.holds || []).filter((h) => (seen.has(h.chart_id) ? false : (seen.add(h.chart_id), true)));
  const files = doc.files || [];
  const checks = doc.checks || [];

  main.innerHTML = `<h1>Census inputs</h1><p class="lead">Every way a census comes in, the Claimocity feed first: what it sent and what AdvancedMD got, the nightly insurance cascade and the scheduled runs, as on the Practice Database page.</p>
    <div class="censuscat" role="group" aria-label="Census inputs - the sections">
      <div class="eyebrow">Census inputs · the sections</div>
      <div class="csecs"><span class="csec cur" aria-current="true">Claimocity feed · the record</span><span class="csec" title="A screenshot of the Claimocity app's census list: room, name, visit code, clinician">Claimocity app census list</span><span class="csec" title="A picture, a scan or a fax of the building's own list: room, name, birth date, record number, admit date">Hospital or facility census list</span><span class="csec" title="The ortho report that arrives by fax (RingCentral)">Ortho report (fax)</span><span class="csec" title="A fax, a scan or an upload from a practice that does not use Claimocity: who was seen, on what date, where, which code">Daily census a practice sends in</span></div>
      <div class="note">The Claimocity feed is the electronic section and the record: everything below is the feed. The other sections arrive as pictures, scans and faxes in the Drive folder "aa census imports files"; they support the feed and stand in for it when it is not available. None of them has been read into the database yet.</div>
    </div>
    <div class="bar"><div class="seg" role="group" aria-label="Window" id="fwin">${[["week", "Past 7 days"], ["month", "Past 30 days"], ["all", "Everything on hand"]].map(([k, l]) => `<button type="button" data-win="${k}" aria-pressed="${fwin === k}">${l}</button>`).join("")}</div>
      <span class="note">${esc(fdate(lo) + " – " + fdate(hi) + (r ? "" : " (all feed files on hand)"))}${doc.truncated ? " · the newest 20,000 encounters" : ""}</span></div>
    <section class="tiles" aria-label="Figures">${tiles}</section>
    ${block("Encounters by date pulled into AdvancedMD", pulled.note, `<p class="note" style="margin:0 0 8px">The day each visit came through the Claimocity connection and was entered in AdvancedMD (Eastern time) - today's pull sits at the right edge. The chart below shows the same visits by the day the patient was seen.</p><div class="chart">${pulled.svg}</div>`)}
    ${block("Encounters by date of service", dos.note, `<div class="chart">${dos.svg}</div>`)}
    ${block("Nightly insurance cascade: cases checked and changed", cascadeNote, `<p class="note" style="margin:0 0 8px">One pair of bars per night (the run starts at 05:35 UTC - 12:35 AM Eastern in winter, 1:35 AM in summer). <b>Checked</b> = visit-and-plan pairs the run verified with AdvancedMD or Stedi. <b>Changed</b> = visits it fixed in AdvancedMD (re-pointed, re-routed or re-sent). A grey dash means no run is recorded for that night.</p>
      <div class="legend" aria-hidden="true"><span><i style="background:var(--cascade)"></i>Checked</span><span><i style="background:var(--cascade-2)"></i>Changed</span></div><div class="chart">${cascadeHtml}</div>${weekText ? `<p class="weeknote">${esc(weekText)}</p>` : ""}
      <div class="tablewrap" style="margin-top:12px"><table><thead><tr><th>Night</th><th class="num">Checked</th><th class="num">Changed</th><th class="num">Re-sent</th><th>What was done</th></tr></thead><tbody>${logRows}</tbody></table></div>`)}
    ${block("Scheduled billing runs recorded here", plural(runTotal, "run", "runs") + " in the past 14 days", `<p class="note" style="margin:0 0 8px">One row per day (Eastern time), newest first. <b>Engine</b> = the GitHub Actions billing engine (every 2 hours, plus the 05:35 UTC cascade profile). <b>Claude</b> = the 6-hourly backend routine, Billing Button presses and the daily feed task. <b>Feed</b> = Claimocity bucket checks (ingests in bold). <b>ERA</b> = payment lines posted. <b>Cascade</b> = the nightly insurance cascade's row from the chart above.</p>
      <div class="tablewrap"><table><thead><tr><th>Day</th><th class="num">Engine runs</th><th class="num">Claude runs</th><th class="num">Feed checks</th><th class="num">ERA lines</th><th>Cascade night</th><th>Last run</th></tr></thead><tbody>${runsDay}</tbody></table></div>`)}
    <section class="block"><header><h2>Every feed charge and what AdvancedMD got</h2><span class="note">one row per patient-day the feed sent · the AdvancedMD visit id proves it was entered</span></header>
      <div class="filters" id="recon-filters"></div>
      <div class="filters"><input type="search" id="recon-q" placeholder="Search chart, visit, CPT, date or file…" aria-label="Search the encounters" value="${esc(reconQ)}"><select id="recon-sort" aria-label="Sort"><option value="date">Newest date first</option><option value="status">Not entered first</option><option value="fee">Highest charge first</option></select></div>
      <div class="tablewrap"><table><thead><tr><th>DOS</th><th>Feed file</th><th>Chart</th><th>CPT</th><th class="num">Charge</th><th>In AdvancedMD</th><th>Insurance</th><th>Note</th></tr></thead><tbody id="recon"></tbody></table></div>
      <div class="filters" style="margin-top:10px"><button class="btn" type="button" id="recon-more" hidden>Show more</button><span class="note" id="recon-count"></span></div></section>
    <div class="grid2">
      ${block("Service", "charge lines · dollars", hbars(group(ent, (_x, c) => service(c)), { key: "lines", extra: (x) => usd(x.dollars) }))}
      ${block("Where the patients were seen", "visits", hbars(group(ent, (x) => L.fac[x.fac] || x.fac || "unknown facility"), { key: "visits", alt: true }))}
      ${block("Lead payer on the chart", "visits · after the eligibility cascade", hbars(group(ent, (x) => payerCat(x.lead, L.car[x.lead])), { key: "visits", cls: (x) => (x.name === "No active plan" ? "warn" : "") }))}
      ${block("In AdvancedMD", "what happened to each encounter", hbars(Object.keys(oc).sort((a, b) => oc[b] - oc[a]).map((k) => ({ name: (STATUS[k] || [k])[0], visits: oc[k], c: (STATUS[k] || ["", "dim"])[1] })), { key: "visits", cls: (x) => x.c }))}
      ${block("Clinician", "visits", hbars(group(ent, (x) => L.prov[x.prov] || x.prov || "Clinician on file"), { key: "visits", alt: true }))}
      ${block("Conditions on the feed", "diagnosis codes · patients in this window", `<div class="chips">${Object.keys(dxc).sort((a, b) => dxc[b] - dxc[a]).slice(0, 14).map((d) => `<span class="chip">${esc(d)} · ${fmt(dxc[d])}</span>`).join("") || `<span class="note">No diagnosis codes in this window.</span>`}</div>`)}
    </div>
    ${block("Holds for William", holds.length ? plural(holds.length, "chart", "charts") + " · chart ids only; names stay in the workspace" : "none open",
      `<div class="tablewrap"><table><thead><tr><th>Chart</th><th>Kind</th><th>Why</th><th>DOS</th></tr></thead><tbody>${holds.length ? holds.map((h) => `<tr><td class="mono">${esc(h.chart_id)}</td><td>${pill("warn", /CMS reports|primary|names/.test(h.hold || "") ? "payer" : "facesheet")}</td><td>${esc(h.hold)}</td><td class="mono">${esc(fdate(dayOf(h.dos)))}</td></tr>`).join("") : `<tr><td colspan="4" class="note">Nothing is held.</td></tr>`}</tbody></table></div>`)}
    <div class="grid2">
      ${block("Feed files on hand", plural(files.length, "file", "files") + (doc.on_hand?.dos_min ? " · DOS " + fdate(dayOf(doc.on_hand.dos_min)) + " – " + fdate(dayOf(doc.on_hand.dos_max)) : ""),
        `<div class="chips">${files.map((f) => `<span class="chip" title="${esc((f.name || "") + " · batch " + f.stamp)}">${esc(fdate(fileDay(f.date)))}${f.messages ? " · " + esc(f.messages) : ""}</span>`).join("") || `<span class="note">No feed file in the database yet.</span>`}</div><p class="note" style="margin-top:10px">Feed files on hand start 10/16/2026 (the September copies the old integration had posted are the "outcome not recorded" rows). Days with no bar are days with no feed encounter on hand, not necessarily days without visits; Claimocity posts a visit one to two days after it happens.</p>`)}
      ${block("Feed checks and ingests", "newest first", `<div class="tablewrap"><table><thead><tr><th>When</th><th>Result</th><th>What the bucket held</th><th class="num">Visits</th><th class="num">Dollars</th></tr></thead><tbody>${checks.length ? checks.map((c) => `<tr><td class="mono">${esc(when(c.at))}</td><td>${pill(c.result === "ingested" ? "ok" : c.result === "nothing_new" ? "dim" : "bad", String(c.result || "").replace("_", " "))}</td><td>${esc(c.line || (Number(c.files_new) ? c.files_new + " new file(s)" : ""))}${c.newest_file ? ` <span class="note">newest file ${esc(fdate(fileDay(c.newest_file)))}</span>` : ""}</td><td class="num">${c.visits != null ? fmt(c.visits) : ""}</td><td class="num">${c.dollars != null ? usd(c.dollars) : ""}</td></tr>`).join("") : `<tr><td colspan="5" class="note">No feed check recorded yet - the next feed run writes one.</td></tr>`}</tbody></table></div>`)}
    </div>
    ${plain("feed")}`;

  // the reconciliation table: filter chips by outcome, search, sort, and more rows on demand (the page's renderRecon)
  const counts: Record<string, number> = { all: rs.length }; rs.forEach((x) => { const k = rowStatus(x); counts[k] = (counts[k] || 0) + 1; });
  const order = ["all", "entered", "hold", "already", "dx", "deceased", "cpt", "skipped", "failed", "nochart", "voided", "unrecorded"];
  if (reconFilter !== "all" && !counts[reconFilter]) reconFilter = "all";
  const rank = (x: FRow) => ({ nochart: 0, failed: 1, dx: 2, cpt: 3, skipped: 4, deceased: 5, hold: 6, voided: 7, already: 8, unrecorded: 9, entered: 10 } as Record<string, number>)[rowStatus(x)] ?? 5;
  const sortSel = $("#recon-sort") as HTMLSelectElement; sortSel.value = reconSort;
  const drawRecon = () => {
    $("#recon-filters").innerHTML = order.filter((k) => k === "all" || counts[k]).map((k) => `<button type="button" class="chipbtn" data-f="${k}" aria-pressed="${reconFilter === k}">${esc(k === "all" ? "All encounters" : (STATUS[k] || [k])[0])} <span class="n">${fmt(counts[k] || 0)}</span></button>`).join("");
    let list = reconFilter === "all" ? rs.slice() : rs.filter((x) => rowStatus(x) === reconFilter);
    const q = reconQ.trim().toLowerCase();
    if (q) list = list.filter((x) => [x.p, x.v, x.file, x.d, (x.c || []).join(" "), x.why, x.hold, x.newchart, L.fac[x.fac] || x.fac].join(" ").toLowerCase().includes(q));
    list.sort((a, b) => (reconSort === "fee" ? Number(b.fee || 0) - Number(a.fee || 0) : reconSort === "status" ? rank(a) - rank(b) || (b.d || "").localeCompare(a.d || "") : (b.d || "").localeCompare(a.d || "") || (a.p || "").localeCompare(b.p || "")));
    const shown = list.slice(0, reconShown);
    $("#recon").innerHTML = shown.length ? shown.map((x) => { const k = rowStatus(x); const st = STATUS[k] || [k, "dim"];
      const amd = pill(st[1], st[0]) + (x.v ? `<div class="mono note">${esc(x.v)}</div>` : "");
      const ins = x.s === "entered" ? (x.hold ? pill("warn", "hold") + " " + esc(L.car[x.lead] || x.lead || "") : pill("ok", x.verdict || "released") + " " + esc(L.car[x.lead] || x.lead || "")) : "";
      return `<tr><td class="mono">${esc(fdate(x.d))}</td><td class="mono">${esc(fdate(fileDay(x.file)))}</td><td class="mono">${esc(x.p || "—")}${x.newchart ? `<div class="note">new ${esc(x.newchart)}</div>` : ""}</td><td class="mono">${esc((x.c || []).join(" "))}</td><td class="num">${x.fee != null && x.s === "entered" ? usd(x.fee) : "—"}</td><td>${amd}</td><td>${ins}</td><td class="note">${esc(x.why || x.hold || L.fac[x.fac] || "")}</td></tr>`; }).join("")
      : `<tr><td colspan="8" class="note">${all.length ? "No encounter matches." : "No feed batch in the database yet."}</td></tr>`;
    ($("#recon-more") as HTMLButtonElement).hidden = list.length <= reconShown;
    $("#recon-count").textContent = fmt(shown.length) + " of " + fmt(list.length) + " encounters shown · " + fmt(doc.on_hand?.rows) + " on hand in " + plural(Number(doc.batches || 0), "batch", "batches");
    document.querySelectorAll<HTMLElement>("#recon-filters .chipbtn").forEach((b) => b.addEventListener("click", () => { reconFilter = b.dataset.f || "all"; ls.set("ehpa-recon-filter", reconFilter); reconShown = 200; drawRecon(); }));
  };
  drawRecon();
  $("#recon-q").addEventListener("input", (ev) => { reconQ = (ev.target as HTMLInputElement).value; reconShown = 200; drawRecon(); });
  sortSel.addEventListener("change", () => { reconSort = sortSel.value; drawRecon(); });
  $("#recon-more").addEventListener("click", () => { reconShown += 300; drawRecon(); });
  document.querySelectorAll<HTMLElement>("#fwin button").forEach((b) => b.addEventListener("click", async () => {
    if (!b.dataset.win || b.dataset.win === fwin) return; fwin = b.dataset.win; ls.set("ehpa-feed-win", fwin); reconShown = 200;
    main.querySelectorAll("#fwin button").forEach((x) => x.setAttribute("aria-pressed", String((x as HTMLElement).dataset.win === fwin)));
    try { await showFeed(main); } catch (e: any) { main.insertAdjacentHTML("afterbegin", `<p class="status err">${esc(e.message || String(e))}</p>`); }
  }));
  wirePlain("feed");
}

// ==== BILLING RUNS =================================================================================================================
type Run = { stamp: string; at: string; mode: string; status: string; headline: string; note: string; engine: boolean; columns: any; era: any; packages: number; waiting: number; errors: number; steps: number };
let runsQ = "";
const colsTxt = (c: any) => { if (!c || !c.before) return ""; const f = (x: any) => [x.charge_review, x.claim_inspector, x.unbilled, x.exclusions].map((v) => (v == null ? "·" : v)).join("/"); return f(c.before) + " → " + f(c.after || c.before); };
const isBad = (s: unknown) => /fail|error|refused/i.test(String(s || ""));
async function showRuns(main: HTMLElement) {
  const doc = await cached<{ totals: any; runs: Run[] }>("/api/pdb/runs");
  const t = doc.totals || {}, runs = doc.runs || [], last = runs[0];
  main.innerHTML = `<h1>Billing runs</h1><p class="lead">Every Billing Button press, scheduled billing run and engine report that reached the database: what it found, what it did, and what is waiting on William.</p>
    <section class="tiles" aria-label="Billing run figures">${[
      tile("Runs on hand", fmt(t.runs), "newest " + fmt(Math.min(300, runs.length)) + " listed"),
      tile("Last run", last ? ago(last.at) : "—", last ? when(last.at) + " · " + (last.mode || "") : "none recorded", "accent"),
      tile("Live runs", fmt(t.live), "the rest were dry passes"),
      tile("Runs with a failed step", fmt(t.failed), "open the row for the error", Number(t.failed) ? "warn" : "ok"),
      tile("Approval packages", fmt(t.packages), "written or applied by these runs")].join("")}</section>
    <section class="block"><header><h2>Billing runs</h2><span class="note" id="runs-note"></span></header>
      <div class="filters"><input type="search" id="runs-q" placeholder="Search headline, mode, status…" aria-label="Search runs" value="${esc(runsQ)}"></div>
      <div class="tablewrap"><table><thead><tr><th>Finished</th><th>Mode</th><th>Status</th><th>Headline</th><th>Columns before → after</th><th class="num">ERA</th><th class="num">Packages</th><th class="num">Waiting</th></tr></thead><tbody id="runs"></tbody></table></div>
      <p class="note" style="margin-top:8px">Tap a row for its steps, what is waiting on William and any errors. Columns = Charge Review / Claim Inspector / Unbilled / Exclusions. Engine = the GitHub Actions billing engine; the rest are Claude runs.</p></section>`;
  const draw = () => {
    const q = runsQ.toLowerCase(); const rs = runs.filter((r) => !q || [r.headline, r.mode, r.status, r.note].join(" ").toLowerCase().includes(q));
    $("#runs-note").textContent = plural(rs.length, "run", "runs") + " · tap a row for detail";
    $("#runs").innerHTML = rs.length ? rs.map((r) => { const era = r.era || {}; const eraTxt = era.after ? fmt(era.after.count ?? era.after.checks ?? 0) : "";
      return `<tr class="click" data-stamp="${esc(r.stamp)}" tabindex="0"><td class="mono">${esc(when(r.at))}</td><td>${esc(r.mode || "")}${r.engine ? ` <span class="note">engine</span>` : ""}</td><td>${pill(isBad(r.status) ? "bad" : r.status === "warn" ? "warn" : "ok", r.status || "")}</td><td>${esc(r.headline || "")}</td><td class="mono">${esc(colsTxt(r.columns))}</td><td class="num">${eraTxt}</td><td class="num">${fmt(r.packages)}</td><td class="num">${fmt(r.waiting)}</td></tr>`; }).join("")
      : `<tr><td colspan="8" class="note">No billing run in the database yet.</td></tr>`;
    expandable("#runs", 8, async (stamp) => {
      const d = await cached<any>("/api/pdb/run/" + encodeURIComponent(stamp));
      const li = (x: unknown) => `<li>${esc(typeof x === "string" ? x : JSON.stringify(x))}</li>`;
      return `<b>Steps</b><ul style="margin:4px 0 8px;padding-left:18px">${(d.steps || []).map((s: any) => `<li><b>${esc(s.title || s.name || "step " + s.step_no)}</b> ${pill(isBad(s.status) ? "bad" : "dim", s.status || "")} ${esc(s.summary || "")}${Array.isArray(s.errors) && s.errors.length ? `<div class="note">${esc(s.errors.map((e: unknown) => (typeof e === "string" ? e : JSON.stringify(e))).join(" · "))}</div>` : ""}</li>`).join("") || "<li class=\"note\">No steps recorded.</li>"}</ul>`
        + (d.waiting?.length ? `<b>Waiting on William</b><ul style="margin:4px 0 8px;padding-left:18px">${d.waiting.map(li).join("")}</ul>` : "")
        + (d.errors?.length ? `<b>Errors</b><ul style="margin:4px 0 8px;padding-left:18px">${d.errors.map(li).join("")}</ul>` : "")
        + [d.run_url && safeUrl(d.run_url) ? ext(d.run_url, "the run") : "", d.source_url ? ext(d.source_url, "report on GitHub") : ""].filter(Boolean).join(" · ");
    });
  };
  draw();
  $("#runs-q").addEventListener("input", (ev) => { runsQ = (ev.target as HTMLInputElement).value; draw(); });
}

// a table whose rows open a detail row under them (the page's tap-a-row); the detail is fetched once and kept
function expandable(tbody: string, span: number, detail: (key: string) => Promise<string>) {
  document.querySelectorAll<HTMLTableRowElement>(tbody + " tr.click").forEach((tr) => {
    const open = async () => {
      const next = tr.nextElementSibling;
      if (next && next.classList.contains("exp")) { next.remove(); tr.setAttribute("aria-expanded", "false"); return; }
      const d = document.createElement("tr"); d.className = "exp"; d.innerHTML = `<td colspan="${span}"><span class="note">Loading…</span></td>`; tr.after(d); tr.setAttribute("aria-expanded", "true");
      try { d.innerHTML = `<td colspan="${span}">${await detail(tr.dataset.stamp || "")}</td>`; } catch (e: any) { d.innerHTML = `<td colspan="${span}" class="note">${esc(e.message || String(e))}</td>`; }
    };
    tr.addEventListener("click", open);
    tr.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } });
  });
}

// ==== ERA ==========================================================================================================================
async function showEra(main: HTMLElement) {
  const doc = await cached<{ totals: any; last_posting: any; unposted_now: any; runs: any[] }>("/api/pdb/era");
  const t = doc.totals || {}, last = doc.last_posting, after = doc.unposted_now, rs = doc.runs || [];
  main.innerHTML = `<h1>ERA posting</h1><p class="lead">Remittances the runs posted: unposted checks before and after each run, the lines posted, paid dollars and the adjustment codes on every line.</p>
    <section class="tiles" aria-label="ERA figures">${[
      tile("ERA runs on hand", fmt(t.runs), "runs that touched ERA posting"),
      tile("Lines posted", fmt(t.lines), "payment lines auto-posted", "accent"),
      tile("Paid posted", usd2(t.paid), "from the ERAs those lines came from"),
      tile("Last posting", last ? ago(last.at) : "—", last ? when(last.at) : "none recorded"),
      tile("Unposted checks now", after ? fmt(after.checks_after) : "—", after ? "after the run of " + when(after.at) + (Number(after.checks_after_total) ? " · " + usd(after.checks_after_total) : "") : "")].join("")}</section>
    ${block("ERA posting runs", plural(rs.length, "run", "runs") + " · newest first", `<div class="tablewrap"><table><thead><tr><th>Run</th><th class="num">Checks before</th><th class="num">Checks after</th><th class="num">Lines posted</th><th class="num">Paid</th><th>Outcomes</th><th class="num">Audit flags</th></tr></thead><tbody id="era">${rs.length ? rs.map((r) => `<tr class="click" data-stamp="${esc(r.stamp)}" tabindex="0"><td class="mono">${esc(when(r.at) || r.stamp)}${r.dry ? " " + pill("dim", "dry") : ""}</td><td class="num">${r.checks_before != null ? fmt(r.checks_before) : ""}</td><td class="num">${r.checks_after != null ? fmt(r.checks_after) : ""}</td><td class="num">${fmt(r.line_count)}</td><td class="num">${Number(r.paid_total) ? usd2(r.paid_total) : ""}</td><td>${esc(Object.entries(r.outcomes || {}).map(([k, v]) => k + " " + v).join(" · "))}</td><td class="num">${r.audit_flags ? fmt(r.audit_flags) : ""}</td></tr>`).join("") : `<tr><td colspan="7" class="note">No ERA run in the database yet.</td></tr>`}</tbody></table></div>
      <p class="note" style="margin-top:8px">Tap a run for its posted lines (chart, visit, CPT, DOS, paid, claim status, CARC codes). Checks before/after = unposted ERA checks in AdvancedMD when the run started and when it ended.</p>`)}
    ${plain("era")}`;
  expandable("#era", 7, async (stamp) => {
    const d = await cached<any>("/api/pdb/era/" + encodeURIComponent(stamp));
    const L = d.lines || [], flags = (d.flags || []).slice(0, 30);
    return (L.length ? `<div class="tablewrap"><table><thead><tr><th>Check</th><th>Chart</th><th>Visit</th><th>CPT</th><th>DOS</th><th class="num">Paid</th><th>Status</th><th>CARC</th><th>Outcome</th></tr></thead><tbody>${L.map((l: any) => `<tr><td class="mono">${esc(l.check_id)}</td><td class="mono">${esc(l.chart_id)}</td><td class="mono">${esc(l.visit_id)}</td><td class="mono">${esc(l.cpt)}</td><td class="mono">${esc(dayOf(l.dos))}</td><td class="num">${usd2(l.paid)}</td><td>${esc(l.claim_status ?? "")}</td><td class="mono">${esc((l.carcs || []).join(" "))}</td><td class="note">${esc(l.outcome || "")}</td></tr>`).join("")}</tbody></table></div>${Number(d.total) > L.length ? `<div class="note">${fmt(Number(d.total) - L.length)} more lines in the raw document.</div>` : ""}` : `<div class="note">No posted lines in this run.</div>`)
      + (flags.length ? `<div class="note" style="margin-top:8px"><b>Audit flags</b>: ${esc(flags.map((f: unknown) => (Array.isArray(f) ? f.join(" ") : typeof f === "string" ? f : JSON.stringify(f))).join(" · "))}</div>` : "");
  });
  wirePlain("era");
}

// ==== APPROVALS ====================================================================================================================
let apprFilter = "all";
async function showApprovals(main: HTMLElement) {
  const doc = await cached<{ snapshot: any; rows: any[]; page: string }>("/api/pdb/approvals");
  const rows = doc.rows || [], s = doc.snapshot;
  const c: Record<string, number> = {}; rows.forEach((r) => { c[r.status] = (c[r.status] || 0) + 1; });
  const waitingDollars = rows.filter((r) => r.status === "waiting").reduce((a, r) => a + Number(r.dollars || 0), 0);
  main.innerHTML = `<h1>Approvals</h1><p class="lead">The Mandatory Approvals packages as the newest snapshot recorded them. The cards themselves are approved on the ${ext(doc.page, "Mandatory Approvals page")}; this is the record from <code>practices/ehpa/registers/approvals_pending.json</code>.</p>
    <section class="tiles" aria-label="Approval figures">${[
      tile("Waiting", fmt(c.waiting || 0), s ? usd(s.dollars_waiting ?? waitingDollars) + " to approve" : "no snapshot yet", c.waiting ? "warn" : "ok"),
      tile("Done", fmt(c.done || 0), "applied by a run or on \"go\""),
      tile("Approved, not yet applied", fmt(c.approved || 0), "the next billing run applies them"),
      tile("Declined", fmt(c.declined || 0), "left alone"),
      tile("Snapshot", s ? ago(s.at) : "—", s ? when(s.at) : "")].join("")}</section>
    <section class="block"><header><h2>Mandatory approval packages</h2><span class="note" id="appr-note"></span></header><div class="filters" id="appr-filters"></div>
      <div class="tablewrap"><table><thead><tr><th>Package</th><th>When</th><th>What</th><th class="num">Dollars</th><th>Status</th><th>Answer</th></tr></thead><tbody id="appr"></tbody></table></div></section>
    ${plain("approvals")}`;
  const draw = () => {
    $("#appr-filters").innerHTML = ["all", "waiting", "approved", "done", "declined"].map((k) => `<button type="button" class="chipbtn" data-f="${k}" aria-pressed="${apprFilter === k}">${k} <span class="n">${fmt(k === "all" ? rows.length : c[k] || 0)}</span></button>`).join("");
    const rs = rows.filter((r) => apprFilter === "all" || r.status === apprFilter);
    $("#appr-note").textContent = s ? plural(rs.length, "package", "packages") + " · snapshot " + when(s.at) : "no snapshot in the database yet";
    const page = safeUrl(doc.page);
    $("#appr").innerHTML = rs.length ? rs.map((r) => `<tr><td class="mono">${page ? `<a href="${esc(page + "#" + encodeURIComponent(r.package_id || ""))}" target="_blank" rel="noopener noreferrer">${esc(r.package_id)}</a>` : esc(r.package_id)}</td><td class="mono">${esc(when(r.at))}</td><td>${esc(r.what || "")}${r.ui ? `<div class="note">${esc(r.ui)}</div>` : ""}</td><td class="num">${r.dollars != null ? usd2(r.dollars) : r.dollars_text ? `<span class="note">${esc(r.dollars_text)}</span>` : ""}</td><td>${pill(r.status === "waiting" ? "warn" : r.status === "done" ? "ok" : r.status === "declined" ? "bad" : "run", r.status || "")}</td><td class="note">${esc(r.answer || "")}</td></tr>`).join("")
      : `<tr><td colspan="6" class="note">Nothing here.</td></tr>`;
    document.querySelectorAll<HTMLElement>("#appr-filters .chipbtn").forEach((b) => b.addEventListener("click", () => { apprFilter = b.dataset.f || "all"; draw(); }));
  };
  draw();
  wirePlain("approvals");
}

// ==== MIRROR & SOURCES =============================================================================================================
async function showMirror(main: HTMLElement) {
  const d = await cached<any>("/api/pdb/mirror");
  const card = (t: string, u: string, k: string, n: string) => { const href = safeUrl(u); return href ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer"><span class="nm"><span>${esc(t)}</span><span class="kd">${esc(k)}</span></span><span class="nt">${esc(n)}</span></a>` : ""; };
  const repo = d.repo, sy = d.last_sync;
  main.innerHTML = `<h1>Mirror &amp; sources</h1><p class="lead">Where each copy of the practice's records lives, the copies of the other billing pages, the routines that write, and the master data.</p>
    <div class="grid2">
      ${block("The copies", "", `<p>The record is <b>GitHub main</b> (<code>dreffinger/effinger-billing-backend</code>): code, runbooks, PHI-light registers and reports. Every change is also pushed to the <b>synced branch</b> the claude.ai Project reads, mirrored to the <b>Postman</b> workspace and copied to <b>Google Drive</b>. The Practice Database page keeps a working copy of the structured data in its own database; <b>Neon Postgres</b> keeps the permanent copy, and this site reads it.</p>
        <dl class="kv">${repo ? `<div><dt>Head on main</dt><dd class="mono">${esc(repo.head || "")}</dd></div><div><dt>Last commit</dt><dd>${esc(repo.last_commit || "")}</dd></div><div><dt>Registers</dt><dd class="mono">${fmt(repo.counts?.registers)}</dd></div><div><dt>Run reports</dt><dd class="mono">${fmt(repo.counts?.button_reports)}</dd></div><div><dt>Snapshot</dt><dd>${esc(when(repo.at))}</dd></div>` : `<div><dt>Repository</dt><dd>no snapshot in the database yet</dd></div>`}</dl>`)}
      ${block("Links", "where each copy lives", `<div class="pages">${(d.links || []).map((l: [string, string, string, string]) => card(l[0], l[1], l[2], l[3])).join("")}</div>`)}
    </div>
    ${block("Copies of the other billing pages", "their databases and embedded datasets, copied by the practice database sync · newest copy per page",
      (sy ? `<p class="note">Last sync ${esc(when(sy.at))}: ${fmt(sy.boards_checked)} pages checked, ${fmt(sy.collections_changed)} collection(s) copied, ${fmt(sy.collections_unchanged)} unchanged (an unchanged collection is not copied again - its last copy stays the newest).</p>` : `<p class="note">No sync run recorded yet - the copies below were loaded by hand; the daily sync (nightly/practice_db_sync_prompt_v1.txt) writes one sync_runs line per day once William creates the routine.</p>`)
      + ((d.copies || []).length ? `<div class="tablewrap"><table><thead><tr><th>Page</th><th>Collections copied</th><th class="num">Documents</th><th>Last copy</th></tr></thead><tbody>${d.copies.map((ix: any) => { const cs = Object.entries(ix.collections || {}) as [string, any][]; const n = cs.reduce((a, [, v]) => a + Number(v?.count || 0), 0); return `<tr><td>${ext(ix.url, ix.title || ix.slug)}</td><td class="mono">${esc(cs.map(([k, v]) => k + " (" + fmt(v?.count) + ")").join(" · ") || "none found")}</td><td class="num">${fmt(n)}</td><td class="mono">${esc(when(ix.at))}</td></tr>`; }).join("")}</tbody></table></div><p class="note">The copied documents themselves stay out of this site's Raw data: the other boards can carry patient names (the Insurance Refresh Board does). Open those boards to see them.</p>` : `<p class="note">No page has been copied yet.</p>`))}
    ${block("Routines that write here", "scheduled tasks · open one to see its runs", `<div class="pages">${(d.routines || []).map((r: any) => card(r.name, r.url, "routine", r.what)).join("")}</div>`)}
    ${block("Practice master data", "collection practice · carriers, facilities, practice", (d.practice || []).length ? `<dl class="kv">${d.practice.map((p: any) => `<div><dt>${esc(p.name)}</dt><dd>${p.entries != null ? fmt(p.entries) + " entries" : ""} · <a href="#db/data" data-coll="practice">raw</a>${p.source ? " · " + esc(p.source) : ""}</dd></div>`).join("")}</dl>` : `<p class="note">No master data document yet.</p>`)}`;
  main.querySelectorAll<HTMLElement>("a[data-coll]").forEach((a) => a.addEventListener("click", () => { dataColl = a.dataset.coll || dataColl; ls.set("ehpa-db-coll", dataColl); }));
}

// ==== RAW DATA =====================================================================================================================
let dataColl = ls.get("ehpa-db-coll") || "feed_batches", dataDoc = "", dataQ = "";
function hl(json: string): string {
  return esc(json).replace(/(&quot;(?:(?!&quot;).)*?&quot;(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (m) => { let c = "nn"; if (/^&quot;/.test(m)) c = /:$/.test(m) ? "k" : "s"; else if (/true|false|null/.test(m)) c = "b"; return `<span class="${c}">${m}</span>`; });
}
async function showData(main: HTMLElement) {
  const meta = await cached<{ collections: [string, string][]; counts: Record<string, { documents: number; newest: string; bytes: number }> }>("/api/pdb/data");
  const colls = meta.collections || [];
  if (!colls.some(([c]) => c === dataColl)) dataColl = colls[0]?.[0] || "feed_batches";
  main.innerHTML = `<h1>Raw data</h1><p class="lead">Every document of the practice database, exactly as stored in Neon (<code>raw.documents</code>, source <code>practice_db</code>), newest first. The copies of the other boards (<code>artifact_copies</code>) are left out here: they can carry patient names.</p>
    <section class="block"><header><h2>Documents</h2><span class="note" id="coll-note"></span></header>
      <div class="filters"><select id="coll" aria-label="Collection">${colls.map(([c, d]) => `<option value="${esc(c)}" title="${esc(d)}"${c === dataColl ? " selected" : ""}>${esc(c)} (${fmt(meta.counts?.[c]?.documents || 0)})</option>`).join("")}</select><input type="search" id="doc-q" placeholder="Filter document ids…" aria-label="Filter documents" value="${esc(dataQ)}"></div>
      <div class="browser"><div class="doclist" id="doclist" role="listbox" aria-label="Documents"><span class="note" style="padding:8px">Loading…</span></div>
        <div style="min-width:0"><div class="filters" id="doc-tools" hidden><span class="mono" id="doc-path"></span><button class="btn" type="button" id="doc-copy">Copy JSON</button><button class="btn" type="button" id="doc-dl">Download</button><a class="btn" id="doc-src" href="#" target="_blank" rel="noopener noreferrer" hidden>Source on GitHub</a></div><pre class="json" id="doc-json" tabindex="0">Pick a document.</pre></div></div></section>`;
  let docs: { doc_id: string; written_at: string; bytes: number }[] = [];
  const list = () => {
    const q = dataQ.toLowerCase(); const show = docs.filter((d) => !q || d.doc_id.toLowerCase().includes(q));
    $("#doclist").innerHTML = show.length ? show.map((d) => `<button type="button" role="option" data-id="${esc(d.doc_id)}" aria-pressed="${dataDoc === d.doc_id}" aria-selected="${dataDoc === d.doc_id}">${esc(d.doc_id)}<small>${fmt(Math.round(Number(d.bytes || 0) / 1024))} KB</small></button>`).join("") : `<span class="note" style="padding:8px">No documents.</span>`;
    document.querySelectorAll<HTMLElement>("#doclist button").forEach((b) => b.addEventListener("click", () => { dataDoc = b.dataset.id || ""; list(); open(); }));
  };
  const load = async () => {
    $("#coll-note").textContent = "Loading…";
    try { docs = (await cached<{ docs: any[] }>("/api/pdb/data/" + encodeURIComponent(dataColl))).docs || []; } catch (e: any) { docs = []; $("#coll-note").textContent = e.message || String(e); return; }
    $("#coll-note").textContent = plural(docs.length, "document", "documents") + (docs.length >= 500 ? " (newest 500)" : "");
    list(); if (dataDoc && docs.some((d) => d.doc_id === dataDoc)) open();
  };
  const open = async () => {
    if (!dataDoc) return; const pre = $("#doc-json"); pre.textContent = "Loading…";
    try {
      const d = await cached<any>("/api/pdb/doc/" + encodeURIComponent(dataColl) + "/" + encodeURIComponent(dataDoc));
      const txt = JSON.stringify(d.body, null, 2);
      pre.innerHTML = hl(txt.length > 400000 ? txt.slice(0, 400000) + "\n… (cut short in view; Download for the whole document)" : txt);
      ($("#doc-tools") as HTMLElement).hidden = false; $("#doc-path").textContent = dataColl + "/" + dataDoc + (d.written_at ? " · written " + when(d.written_at) : "");
      const src = $("#doc-src") as HTMLAnchorElement; if (d.source_url) { src.href = d.source_url; src.hidden = false; } else src.hidden = true;
      ($("#doc-copy") as HTMLButtonElement).onclick = async () => { try { await navigator.clipboard.writeText(txt); $("#coll-note").textContent = "Copied " + dataColl + "/" + dataDoc + "."; } catch { const rg = document.createRange(); rg.selectNodeContents(pre); const sel = getSelection(); sel?.removeAllRanges(); sel?.addRange(rg); $("#coll-note").textContent = "Selected - press Ctrl+C / Cmd+C."; } };
      ($("#doc-dl") as HTMLButtonElement).onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([txt], { type: "application/json" })); a.download = dataColl + "__" + dataDoc.replace(/[^A-Za-z0-9._-]/g, "_") + ".json"; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500); };
    } catch (e: any) { pre.textContent = e.message || String(e); }
  };
  $("#coll").addEventListener("change", (ev) => { dataColl = (ev.target as HTMLSelectElement).value; ls.set("ehpa-db-coll", dataColl); dataDoc = ""; ($("#doc-tools") as HTMLElement).hidden = true; $("#doc-json").textContent = "Pick a document."; load(); });
  $("#doc-q").addEventListener("input", (ev) => { dataQ = (ev.target as HTMLInputElement).value; list(); });
  await load();
}
