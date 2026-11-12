// What the Insurance Refresh Board looks like in the app. The rules are the board's own (boards/templates/tracker.html: headline,
// kindOf, facEntries, facInfo, insIdOf, the filters, the counts, the sort) ported here so the Neon copy reads the same as the board.
// CHANGE BOTH when a rule changes: scripts/test-boardview.mjs runs the board's functions and these side by side and fails on a
// difference. Pure functions over plain data (no DOM, no network), so that test can run them under node. Read-only: no compose box,
// no Post, no Mark done - those stay on the board. Everything that comes from a card goes through esc() before it becomes HTML.
// Class names start with "rb-" so they cannot meet the hub's .card / .chip / .tile rules; the counts reuse the app's own tiles.

export type Card = {
  id: string; patient: string | null; chart: string | null; dob: string | null; turn: string; need: string | null; why: string | null;
  amount: number | null; insid: string | null; inscarrier: string | null; mbi: string | null; insplans: string | null;
  facnow: unknown; facilities: string | null; lastfac: string | null; lastdos: string | null; facility: string | null; updated: string | null;
  notes_n: number; checks_n: number; api_n: number; is_new: boolean;
  last_note_who: string | null; last_note_at: string | null; last_note_text: string | null; last_note_more: boolean;
};
export type Board = { url: string; synced_at: string | null; changed_at: string | null; items: Card[] };
export type CardDetail = {
  id: string;
  notes: { who: string; at: string; text: string }[];
  checks: { k: string; src: string; res: string; when: string; at: string }[];
  api: { src: string; at: string; text: string }[];
};
export type DetailState = CardDetail | "loading" | { error: string };
export type BoardState = { filter: string; query: string; open: Set<string>; details: Map<string, DetailState> };
export type FacInfo = { name: string; kind: string; dos: string; res: { name: string; kind: string } | null; src: string };

export const FILTERS: [string, string, string][] = [
  ["william", "Your turn", ""],
  ["new", "New for you", "Your-turn cards where Claude added something after your last note"],
  ["open", "Open", ""],
  ["claude", "Claude's turn", ""],
  ["done", "Done", ""],
  ["all", "Everything", ""],
];

export const esc = (s: unknown) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);
const money = (n: unknown) => "$" + Math.round(Number(n) || 0).toLocaleString("en-US");
const when = (iso: unknown) => { if (!iso) return ""; const d = new Date(String(iso)); return isNaN(d.getTime()) ? "" : d.toLocaleString("en-US", { month: "numeric", day: "numeric", hour: "numeric", minute: "2-digit" }); };
const whenLong = (iso: unknown) => { if (!iso) return ""; const d = new Date(String(iso)); return isNaN(d.getTime()) ? "" : d.toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); };

// The one thing needed now: the first sentence of the need (its 'WILLIAM:' / 'DONE 9/14:' prefix dropped); the rest is listed under it.
export function headline(need: unknown): { h: string; rest: string } {
  const s = String(need || "").replace(/^\s*(?:WILLIAM(?: FLAG)?|CLAUDE|DONE[^:]{0,40}|RESOLVED[^:]{0,40}|CLOSED[^:]{0,40}|Rebilled[^:]{0,40})\s*:\s*/i, "").trim();
  if (!s) return { h: "", rest: "" };
  const m = s.match(/^([\s\S]{15,230}?[.!?])(?=\s|$)/);
  let h = m ? m[1] : s;
  if (h.length > 230) { const cut = h.lastIndexOf(" ", 215); h = h.slice(0, cut > 80 ? cut : 215) + "…"; }
  const rest = s.slice(h.endsWith("…") ? h.length - 1 : h.length).trim();
  return { h, rest };
}

// Insurance id: the run writes insid (+ inscarrier = the plan that bills first); older cards only have mbi.
export function insIdOf(c: Pick<Card, "insid" | "inscarrier" | "mbi">): { id: string; car: string } {
  if (c.insid) return { id: String(c.insid), car: String(c.inscarrier || "") };
  if (c.mbi) return { id: String(c.mbi), car: "" };
  return { id: "", car: "" };
}

// The kind of place, from its name (facility names of the practice, not patient data).
export const KIND_LABEL: Record<string, string> = { SNF: "SNF resident", ALF: "ALF resident", ALFSNF: "ALF or SNF resident", IL: "IL resident", ICF: "ICF resident", HOSP: "hospital inpatient", IRF: "inpatient rehab", HOME: "home visit", TELE: "telehealth", OFFICE: "office", OTHER: "" };
export function kindOf(name: unknown): string {
  const n = String(name || "").toUpperCase().replace(/&/g, " AND ").replace(/\s+/g, " ");
  if (!n) return "OTHER";
  // 1. assisted living (every ALF in the AMD facility list carries 'ALF' in its name)
  if (/\bALF\b|ASSISTED|MEMORY CARE|BROOKDALE|ALLEGRO|AZALEA|CANTERFIELD|CAPITAL SQUARE|GROVE AT CANOPY|HARBOR ?CHASE|PACIFICA|SODALIS|TAPESTRY|PARRY/.test(n)) return "ALF";
  // 2. the nursing facilities by name - before the hospital check, so 'Aviata (admit 9/25 from TMH)' stays the SNF
  if (/BRYNWOOD|OAKES|ASPIRE|AVIATA|CENTRE POINTE|CENTER POINTE|EDEN SPRINGS|LAKE PARK|SEVEN HILLS|ST\.? JASPER|BERTRAND|HEALTH AND REHAB|REHABILITATION CENTER|NURSING/.test(n)) return "SNF";
  if (/HCA REHAB|INPATIENT REHAB|\bIRF\b/.test(n)) return "IRF";
  if (/HOSPITAL|\bHCA\b|\bTMH\b|MEMORIAL|MEDICAL CENTER|\bER\b|EMERGENCY/.test(n)) return "HOSP";
  if (/INDEPENDENT LIVING|\bIL\b/.test(n)) return "IL";
  if (/DEVELOPMENTAL|\bICF\b/.test(n)) return "ICF";
  if (/TELEHEALTH/.test(n)) return "TELE";
  if (/INDIVIDUAL PATIENT HOMES|\bHOME\b/.test(n)) return "HOME";
  if (/NORTH FLORIDA SENIOR CARE|\bOFFICE\b/.test(n)) return "OFFICE";
  // 5. generic nursing-facility tokens (the run's place-of-service guesses: 'SNF (99306 8/27/2026)', 'NF')
  if (/\bSNF\b|\bNF\b|\bLTC\b|SKILLED|REHAB|HEALTH CENTER|WESTMINSTER/.test(n)) return "SNF";
  return "OTHER";
}
// the facilities line: "Name m/yy-m/yy · Name m/yy (Pam)", newest first
export function facEntries(c: Pick<Card, "facilities">): { name: string; range: string; pam: boolean }[] {
  return String(c.facilities || "").split(" · ").map((x) => x.trim()).filter(Boolean).map((x) => {
    const m = x.match(/^(.*?)\s+(\d{1,2}\/\d{2}(?:[–-]\d{1,2}\/\d{2})?)(\s*\(Pam\))?$/);
    return m ? { name: m[1], range: m[2], pam: !!m[3] } : { name: x, range: "", pam: false };
  });
}
const RES_KIND = /^(SNF|ALF|IL|ICF)$/;
// Where the patient is: the chart's newest visit (facnow), else the newest entry of the facilities line, else lastfac, else the text.
export function facInfo(c: Pick<Card, "facnow" | "facilities" | "lastfac" | "lastdos" | "facility">): FacInfo | null {
  const fn = c.facnow as { name?: unknown; kind?: unknown; dos?: unknown; res?: { name?: unknown; kind?: unknown } } | null;
  if (fn && typeof fn === "object" && fn.name) {
    const k = String(fn.kind || kindOf(fn.name)).toUpperCase();
    const res = fn.res && typeof fn.res === "object" && fn.res.name ? { name: String(fn.res.name), kind: String(fn.res.kind || kindOf(fn.res.name)).toUpperCase() } : null;
    return { name: String(fn.name), kind: k, dos: String(fn.dos || ""), res, src: "chart" };
  }
  const ents = facEntries(c);
  if (ents.length) {
    const top = ents[0], k = kindOf(top.name);
    const resEnt = RES_KIND.test(k) ? null : ents.find((e) => RES_KIND.test(kindOf(e.name)));
    return { name: top.name, kind: k, dos: top.range ? "thru " + top.range.split(/[–-]/).pop() : "", res: resEnt ? { name: resEnt.name, kind: kindOf(resEnt.name) } : null, src: "visits" };
  }
  if (c.lastfac) return { name: String(c.lastfac), kind: kindOf(c.lastfac), dos: String(c.lastdos || ""), res: null, src: "chart" };
  const t = String(c.facility || "").trim();
  if (t) {
    const generic = /^(SNF|ALF|NF|HCA|TMH)(\b|[\s\/(])/i.test(t);
    let k = kindOf(t);
    if (generic && /\bALF\b/i.test(t) && /\b(SNF|NF)\b/i.test(t)) k = "ALFSNF";   // the run's 'SNF / ALF' place-of-service guess: which one is not known yet
    return { name: t, kind: k, dos: "", res: null, src: generic ? "guess" : "text" };
  }
  return null;
}
function facBadge(c: Card): string {
  const f = facInfo(c);
  if (!f) return c.chart && /^\d+$/.test(String(c.chart).trim()) ? `<div class="rb-fac unknown" title="No facility on this card yet. The backend fills it from the chart's visits."><span class="fname">facility not on file yet</span></div>` : "";
  const lbl = KIND_LABEL[f.kind] || "";
  const cls = String(f.kind || "other").toLowerCase().replace(/[^a-z]/g, "");
  const res = f.res ? `<span class="fres">resident at <b>${esc(f.res.name)}</b> · ${esc(KIND_LABEL[f.res.kind] || f.res.kind)}</span>` : "";
  const title = f.src === "guess" ? "Place-of-service type from the visit codes. The actual facility name lands when the backend reads the chart." : "From the AMD chart: the facility of the newest visit, with where the patient lives";
  return `<div class="rb-fac${f.src === "guess" ? " unknown" : ""}" title="${esc(title)}"><span class="fname">${esc(f.name)}</span>${lbl ? `<span class="fkind ${cls}">${esc(lbl)}</span>` : ""}${f.dos ? `<span class="fdos">${esc(f.dos)}</span>` : ""}${res}</div>`;
}

// ---- which cards show, and in what order (the board's filters; a search looks through every card) -------------------------------
const hay = new WeakMap<Card, string>();
function haystack(c: Card): string {
  let h = hay.get(c);
  if (h === undefined) {
    const fn = c.facnow && typeof c.facnow === "object" ? (c.facnow as { name?: unknown }).name : "";
    h = [c.patient, c.chart, c.dob, fn, c.facilities, c.lastfac, c.facility, c.inscarrier, c.insid, c.mbi, c.insplans, c.need, c.why].map((x) => String(x ?? "")).join(" \n ").toLowerCase();
    hay.set(c, h);
  }
  return h;
}
export const queryTokens = (q: string) => q.toLowerCase().split(/\s+/).filter(Boolean);
export function passes(c: Card, filter: string): boolean {
  if (filter === "all") return true;
  if (filter === "open") return c.turn !== "done";
  if (filter === "new") return c.turn === "william" && !!c.is_new;
  return c.turn === filter;
}
export function visibleCards(b: Board, st: Pick<BoardState, "filter" | "query">): Card[] {
  const tokens = queryTokens(st.query);
  const pool = tokens.length ? b.items.filter((c) => { const h = haystack(c); return tokens.every((t) => h.includes(t)); }) : b.items.filter((c) => passes(c, st.filter));
  // A to Z by last name, then the larger amount first (William 9/14)
  return pool.slice().sort((x, y) => String(x.patient || "").localeCompare(String(y.patient || ""), undefined, { sensitivity: "base" }) || Number(y.amount || 0) - Number(x.amount || 0));
}
export function counts(b: Board) {
  const open = b.items.filter((c) => c.turn !== "done");
  const mine = open.filter((c) => c.turn === "william");
  return { mine: mine.length, fresh: mine.filter((c) => c.is_new).length, claude: open.filter((c) => c.turn === "claude").length, waiting: open.reduce((s, c) => s + (Number(c.amount) || 0), 0), done: b.items.length - open.length, all: b.items.length };
}

// ---- one card ----------------------------------------------------------------------------------------------------------------------
const TIC: Record<string, string> = { ok: "✓", no: "✗", na: "○", human: "→" };   // a lookup that answered, did not, was not applicable, went to a person
export function detailHtml(d: DetailState | undefined): string {
  if (!d) return "";
  if (d === "loading") return `<div class="rb-wide rb-detail"><p class="note">Loading the notes and the lookup trail…</p></div>`;
  if ("error" in d) return `<div class="rb-wide rb-detail"><p class="status err">${esc(d.error)}</p></div>`;
  const notes = d.notes.length ? `<div class="rb-thread"><div class="rb-th">Notes · ${d.notes.length}</div>${d.notes.map((n, i) => `<div class="rb-tnote"><span class="rb-by ${n.who === "William" ? "w" : "c"}">${esc(n.who)}</span><span>${esc(n.text)}</span><span class="rb-at">${esc(when(n.at))}${d.notes.length > 1 && i === d.notes.length - 1 ? " · <b>latest</b>" : ""}</span></div>`).join("")}</div>` : "";
  const trail = d.checks.length ? `<div class="rb-trail"><div class="rb-th">Lookup trail: checks already run (blue = Stedi lookups)</div>${d.checks.map((c) => {
    const k = Object.prototype.hasOwnProperty.call(TIC, c.k) ? c.k : "na";
    const st = /stedi|eligib|mbi lookup|discovery|277|271/i.test(c.src) ? " stedi" : "";
    const at = c.when || when(c.at);
    return `<div class="tr ${k}${st}"><span class="ic">${TIC[k]}</span><span class="src">${esc(c.src)}</span><span class="res">${esc(c.res)}${at ? ` <span class="rb-at">(${esc(at)})</span>` : ""}</span></div>`;
  }).join("")}</div>` : "";
  const api = d.api.length ? `<div class="rb-api">${d.api.map((x) => `<div class="ab"><div class="ah"><span>${esc(x.src)}</span><span class="rb-at">${esc(x.at)}</span></div><div class="ax">${esc(x.text)}</div></div>`).join("")}</div>` : "";
  return `<div class="rb-wide rb-detail">${notes}${trail}${api}${notes || trail || api ? "" : `<p class="note">Nothing more on this card.</p>`}</div>`;
}

export function cardHtml(c: Card, st: Pick<BoardState, "open" | "details">): string {
  const t = c.turn === "done" ? "done" : c.turn === "william" ? "william" : "claude";
  const isNew = t === "william" && !!c.is_new;
  const label = t === "william" ? "William" : t === "claude" ? "Claude" : "Done";
  const ins = insIdOf(c), chartNo = c.chart || "";
  const idParts: string[] = [];
  if (chartNo) idParts.push(`<span class="k">AMD</span><span class="v">${esc(chartNo)}</span>`);
  if (c.dob) idParts.push(`<span class="k">DOB</span><span class="v">${esc(c.dob)}</span>`);
  if (ins.id) idParts.push(`<span class="k">Ins</span><span class="v">${esc(ins.id)}</span>${ins.car ? ` <span class="car">${esc(ins.car)}</span>` : ""}`);
  else if (chartNo) idParts.push(`<span class="k">Ins</span><span class="car">no active plan on the chart</span>`);
  const idline = idParts.length ? `<div class="rb-idline" title="From the AMD chart: chart number, date of birth, the insurance id of the plan that bills first">${idParts.map((x) => `<span class="part">${x}</span>`).join(`<span class="sep">·</span>`)}</div>` : "";
  const hl = headline(c.need);
  const lead = t === "done" ? "Done" : t === "claude" ? "Claude is on it" : isNew ? "New: what I need from you" : "What I need from you";
  const morePlans = String(c.insplans || "").includes(" · ") ? String(c.insplans || "").split(" · ").slice(1).join(" · ") : "";
  const moreFacs = String(c.facilities || "").includes(" · ") ? String(c.facilities || "") : "";
  const extras: string[] = [];
  if (hl.rest) extras.push(`<div class="rest">${esc(hl.rest)}</div>`);
  if (c.why) extras.push(`<div class="why">${esc(c.why)}</div>`);
  if (morePlans) extras.push(`<div class="facs" title="Other plans on the chart, in billing order">Also on the chart: ${esc(morePlans)}</div>`);
  if (moreFacs) extras.push(`<div class="facs" title="Every facility where the patient was seen (from AMD visits), newest first">Seen at: ${esc(moreFacs)}</div>`);
  const last = c.last_note_text ? `<div class="rb-wide rb-last"><span class="rb-by ${c.last_note_who === "William" ? "w" : "c"}">${esc(c.last_note_who || "note")}</span><span>${esc(c.last_note_text)}${c.last_note_more ? "…" : ""}</span><span class="rb-at">${esc(when(c.last_note_at))}${c.notes_n > 1 ? " · latest of " + c.notes_n : ""}</span></div>` : "";
  const more = [c.notes_n ? `notes (${c.notes_n})` : "", c.checks_n ? `lookup trail (${c.checks_n})` : "", c.api_n ? `API results (${c.api_n})` : ""].filter(Boolean);
  const isOpen = st.open.has(c.id);
  const moreBtn = more.length ? `<div class="rb-wide rb-more"><button class="btn" type="button" data-card="${esc(c.id)}" aria-expanded="${isOpen}">${isOpen ? "Hide" : "Show"} ${esc(more.join(", "))}</button></div>` : "";
  return `<article class="rb-card t-${t}${isNew ? " is-new" : ""}" data-id="${esc(c.id)}">
<div>${facBadge(c)}<div class="rb-who">${esc(c.patient) || `<span class="dim">(no name on the card)</span>`}</div>${idline}</div>
<div class="rb-need"><span class="rb-lead">${lead}</span><div class="rb-ask">${esc(hl.h) || `<span class="dim">(nothing written yet)</span>`}</div>${extras.join("")}</div>
<div class="rb-amt">${Number(c.amount) > 0 ? money(c.amount) : ""}</div>
<div>${isNew ? `<span class="rb-pill new" title="Claude added something after your last note on this card">New</span>` : ""}<span class="rb-pill ${t}">${label}</span><div class="rb-upd">${c.updated ? "updated " + esc(when(c.updated)) : ""}</div></div>
${last}${moreBtn}${isOpen ? detailHtml(st.details.get(c.id)) : ""}
</article>`;
}

// ---- the view: counts, the as-of line, the filters, the search box, the count line, the list --------------------------------------
// A search looks through every card whatever the filter, so while one is typed no filter shows as pressed, and choosing a filter
// clears the search (../client/board.ts): every control always does what it says. The count line is its own element so that a
// screen reader hears it change (the list under it is replaced on every repaint).
export const searching = (st: Pick<BoardState, "query">) => queryTokens(st.query).length > 0;
export function boardCountText(b: Board, st: BoardState): string {
  const n = visibleCards(b, st).length;
  return searching(st) ? `${n} of ${b.items.length} cards match, looking through every card. Choose a filter to clear the search.` : `${n} card${n === 1 ? "" : "s"}`;
}
export function boardListHtml(b: Board, st: BoardState): string {
  const show = visibleCards(b, st);
  if (!show.length) return `<div class="rb-empty">${searching(st) ? "No card matches that." : st.filter === "new" ? "Nothing new. Every card on your turn already has your latest word on it." : "Nothing here."}</div>`;
  return show.map((c) => cardHtml(c, st)).join("");
}

const tile = (label: string, value: string, sub = "", cls = "") => `<div class="tile ${cls}"><div class="tile-l">${esc(label)}</div><div class="tile-v">${esc(value)}</div>${sub ? `<div class="tile-s">${esc(sub)}</div>` : ""}</div>`;
export function boardShellHtml(b: Board, st: BoardState, now: number = Date.now()): string {
  const n = counts(b);
  const synced = b.synced_at ? new Date(b.synced_at).getTime() : NaN;
  const stale = !isNaN(synced) && now - synced > 36 * 3600_000;
  const asof = b.synced_at && !isNaN(synced)
    ? `${stale ? "The nightly copy has not run since " : "Copied from the board "}${esc(whenLong(b.synced_at))}. Notes and changes made on the board after that show here after the next nightly copy.`
    : "No copy of the board has been recorded yet.";
  return `<div class="tiles">${tile("Your turn", String(n.mine), n.fresh ? n.fresh + " new" : "", "accent")}${tile("Claude's turn", String(n.claude))}${tile("$ waiting", money(n.waiting), "on the open cards")}${tile("Done", String(n.done), "", "ok")}</div>
<p class="rb-asof${stale ? " stale" : ""}">${asof} This page is read-only: to post a note or hand a patient to Claude, <a href="${esc(b.url)}" target="_blank" rel="noopener noreferrer">open the board</a>.</p>
<div class="rb-tools">
<div class="seg" id="board-f" role="group" aria-label="Filter">${FILTERS.map(([k, l, tip]) => `<button type="button" data-f="${k}" aria-pressed="${!searching(st) && st.filter === k}"${tip ? ` title="${esc(tip)}"` : ""}>${esc(l)}</button>`).join("")}</div>
<input id="board-q" type="search" value="${esc(st.query)}" placeholder="Find a patient, chart number, facility or plan" aria-label="Find a card" autocomplete="off" spellcheck="false">
</div>
<p id="board-count" class="rb-count" role="status" aria-live="polite">${esc(boardCountText(b, st))}</p>
<div id="board-list">${boardListHtml(b, st)}</div>`;
}
