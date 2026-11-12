// CCM notes: the CCM Documentation Hub's notes, read from Neon (ccm.* views, /api/ccm/*, ccm.ts). READ-ONLY - a note is opened
// and read here; signing stays on the hub page on claude.ai, which every page here links to. Pages: #ccm (the months and the
// newest month's notes), #ccm/m/<YYYY-MM>, #ccm/note/<chart>_<YYYY-MM>, #ccm/patients, #ccm/p/<chart>, #ccm/signed.
// PATIENT DATA: names and birth dates are shown here, as on the hub. They arrive only from /api/ccm/* (a verified session for an
// allowed, confirmed email; every request logged in ops.app_access_log) and are never kept in the browser beyond this page's
// memory (no localStorage); Refresh and Sign out drop them.
import { $, esc, cached, crumbs, safeUrl } from "./core";

export const CCM_NAV: [string, string][] = [["ccm", "Months"], ["ccm/patients", "Patients"], ["ccm/signed", "Signed notes"]];

type Counts = { notes: number; ready: number; flagged: number; noname: number; signed: number };
type Summary = { totals: Counts & { patients: number; months: number }; months: (Counts & { month: string })[]; built_at: string | null; last_signed_at: string | null; last_recorded_at: string | null; evidence: number; faxes: number; hub: string; build: string };
type Note = { note_id: string; chart_id: string; patient_name: string | null; birth_date: string | null; codes: string[]; minutes: number | null; flag: string; insurance: string; status: string; written_on: string | null; signed_by: string | null; signed_at: string | null; location?: string; provider?: string };

const fmt = (n: unknown) => Number(n || 0).toLocaleString("en-US");
const monthName = (ym: string) => { const m = /^(\d{4})-(\d{2})/.exec(ym || ""); return m ? new Date(Date.UTC(+m[1], +m[2] - 1, 15)).toLocaleString("en-US", { month: "long", year: "numeric", timeZone: "UTC" }) : ym; };
const when = (s: unknown) => { if (!s) return ""; const d = new Date(String(s)); return isNaN(d.getTime()) ? String(s) : d.toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }); };
// the hub's stamp: the day and time in Eastern, MM/DD/YYYY HH:MM:SS
const eastern = (s: unknown) => { const d = new Date(String(s)); if (isNaN(d.getTime())) return ""; const p = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }).formatToParts(d); const g = (t: string) => (p.find((x) => x.type === t) || { value: "" }).value; return `${g("month")}/${g("day")}/${g("year")} ${g("hour")}:${g("minute")}:${g("second")}`; };
const STATE: Record<string, [string, string]> = { "ready to sign": ["ready", "Ready to sign"], flagged: ["flagged", "Flagged - review"], "no name yet": ["noname", "Waiting for name"], signed: ["signed", "Signed and recorded"] };
const statePill = (s: string) => { const st = STATE[s] || ["noname", s || "unknown"]; return `<span class="pill ${esc(st[0])}">${esc(st[1])}</span>`; };
const hubBtn = (url: string, text = "Sign on the CCM Documentation Hub") => { const u = safeUrl(url); return u ? `<a class="btn primary" href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(text)} <span class="ext" aria-hidden="true">↗</span></a>` : ""; };
const chips = (t: Counts) => `<div class="chips">${[["", "Notes", t.notes], ["ready", "Ready to sign", t.ready], ["flagged", "Flagged for you", t.flagged], ["noname", "Waiting for a name", t.noname], ["signed", "Signed", t.signed]]
  .map(([k, l, v]) => `<span class="pill ${esc(String(k || "dim"))}">${fmt(v)} ${esc(String(l))}</span>`).join("")}</div>`;

let filter = "all", query = "", shown = 150;

export async function showCcm(parts: string[]): Promise<string> {
  const main = $("#main");
  const sub = parts[1] || "";
  if (sub === "note" && parts[2]) { await showNote(main, parts[2]); return "ccm"; }
  if (sub === "patients") { await showPatients(main); return "ccm/patients"; }
  if (sub === "p" && parts[2]) { await showPatient(main, parts[2]); return "ccm/patients"; }
  if (sub === "signed") { await showSigned(main); return "ccm/signed"; }
  await showMonths(main, sub === "m" ? parts[2] || "" : "");
  return "ccm";
}

async function showMonths(main: HTMLElement, wanted: string) {
  const s = await cached<Summary>("/api/ccm/summary");
  const months = s.months || [];
  const month = months.some((m) => m.month === wanted) ? wanted : months[0]?.month || "";
  const t = s.totals || ({} as Summary["totals"]);
  const head = `<h1>CCM notes</h1><p class="lead">One late-entry note for every patient and month a chronic care management charge was billed, as the CCM Documentation Hub holds them in the practice database. Read them here; sign them on the hub.</p>
    <div class="bar">${chips(t)}<span style="display:flex;gap:8px;flex-wrap:wrap">${hubBtn(s.hub)}</span></div>
    <p class="note">${fmt(t.patients)} patients · ${fmt(t.months)} months · notes built ${esc(when(s.built_at))}${s.last_signed_at ? " · last signing " + esc(when(s.last_signed_at)) : ""}${s.last_recorded_at ? ", recorded " + esc(when(s.last_recorded_at)) : ""} · supporting items on file: ${fmt(s.evidence)} · faxes archived: ${fmt(s.faxes)}</p>`;
  if (!month) { main.innerHTML = head + `<p class="note">No CCM note is in the database yet.</p>`; return; }
  main.innerHTML = head + `<div class="ccm"><nav class="months" aria-label="Months">${months.map((m) => `<a href="#ccm/m/${esc(m.month)}"${m.month === month ? ' aria-current="page"' : ""}><span class="mn">${esc(monthName(m.month))}</span><span class="mc">${fmt(m.notes)}</span><span class="ms">${fmt(m.ready)} ready · ${fmt(m.flagged)} flagged${m.noname ? " · " + fmt(m.noname) + " waiting" : ""}${m.signed ? " · " + fmt(m.signed) + " signed" : ""}</span></a>`).join("")}</nav>
    <div style="min-width:0" id="month-notes"><p class="note">Reading the notes for ${esc(monthName(month))}…</p></div></div>`;
  const box = $("#month-notes");
  const d = await cached<{ notes: Note[]; hub: string }>("/api/ccm/month/" + encodeURIComponent(month));
  const notes = d.notes || [];
  const matches = (n: Note) => {
    if (filter === "ready" && n.status !== "ready to sign") return false;
    if (filter === "flagged" && n.status !== "flagged") return false;
    if (filter === "noname" && n.status !== "no name yet") return false;
    if (filter === "signed" && n.status !== "signed") return false;
    const q = query.trim().toLowerCase();
    return !q || (n.patient_name || "").toLowerCase().includes(q) || n.chart_id.toLowerCase().includes(q);
  };
  const draw = () => {
    const rows = notes.filter(matches);
    const ready = notes.filter((n) => n.status === "ready to sign").length;
    box.innerHTML = `<section class="block"><header><h2>${esc(monthName(month))}</h2><span class="note">${fmt(notes.length)} notes · ${fmt(ready)} ready to sign</span></header>
      <div class="filters"><div class="seg" role="group" aria-label="Show">${[["all", "All"], ["ready", "Ready"], ["flagged", "Flagged"], ["noname", "Waiting for name"], ["signed", "Signed"]].map(([k, l]) => `<button type="button" data-filter="${k}" aria-pressed="${filter === k}">${l}</button>`).join("")}</div>
        <input type="search" id="ccm-q" placeholder="Find a patient or chart" aria-label="Find a patient or chart" value="${esc(query)}"></div>
      ${rows.length ? `<div class="tablewrap"><table><thead><tr><th>Patient</th><th>Birth date</th><th>Chart</th><th>Codes</th><th>Location</th><th>Status</th><th>Signed</th><th></th></tr></thead><tbody>${rows.slice(0, shown).map((n) => `<tr><td>${n.patient_name ? esc(n.patient_name) : '<span class="dim">name not read yet</span>'}${n.flag ? `<div class="flagtext">${esc(n.flag)}</div>` : ""}</td><td class="mono">${esc(n.birth_date || "")}</td><td class="mono"><a href="#ccm/p/${esc(encodeURIComponent(n.chart_id))}">${esc(n.chart_id)}</a></td><td class="mono">${esc((n.codes || []).join(" + "))}</td><td>${esc(n.location || "")}</td><td>${statePill(n.status)}</td><td class="note"${n.signed_by ? ` title="${esc("Signed by " + n.signed_by)}"` : ""}>${n.signed_at ? esc(when(n.signed_at)) : ""}</td><td><a class="btn" href="#ccm/note/${esc(encodeURIComponent(n.note_id))}">Open</a></td></tr>`).join("")}</tbody></table></div>${rows.length > shown ? `<div class="pager"><button class="btn" type="button" id="ccm-more">Show ${fmt(Math.min(200, rows.length - shown))} more of ${fmt(rows.length - shown)}</button></div>` : ""}` : `<p class="note">No notes match.</p>`}
      <p class="note" style="margin-top:8px">Flagged notes need your own look on the hub (a duplicate charge, a code set without a ready-made statement, or a line under another clinician); they are never part of a "sign all".</p></section>`;
    box.querySelectorAll<HTMLElement>("[data-filter]").forEach((b) => b.addEventListener("click", () => { filter = b.dataset.filter || "all"; shown = 150; draw(); }));
    const q = box.querySelector("#ccm-q") as HTMLInputElement;
    q.addEventListener("input", () => { query = q.value; shown = 150; const pos = q.selectionStart; draw(); const again = box.querySelector("#ccm-q") as HTMLInputElement; again.focus(); try { again.setSelectionRange(pos, pos); } catch { /* not a text field */ } });
    box.querySelector("#ccm-more")?.addEventListener("click", () => { shown += 200; draw(); });
  };
  draw();
}

// one note, read-only, laid out like the hub's paper note (the hub adds the letterhead and is where it is signed)
async function showNote(main: HTMLElement, id: string) {
  const d = await cached<{ note: Note & { month: string; sha: string | null }; draft: { fields: any; statement: string; built_at: string } | null; signed: { fields: any; signed_by: string; signed_at: string; written_on: string; sha: string; via: string; recorded_at: string } | null; hub: string }>("/api/ccm/note/" + encodeURIComponent(id));
  const n = d.note, signed = d.signed;
  const f = Object.assign({}, d.draft?.fields || {}, signed?.fields || {});
  if (!signed && d.draft && !f.statement) f.statement = d.draft.statement || "";
  const charges: unknown[][] = Array.isArray(f.charges) ? f.charges : [];
  const evidence: unknown[][] = Array.isArray(f.evidence) ? f.evidence : [];
  const written = signed ? signed.written_on || f.written || "" : "the day it is signed";
  const paper = `<article class="paper" aria-label="The note as on paper">
    <div class="side${signed ? "" : " draft"}">${signed ? "Electronically Signed and Reviewed by " + esc(signed.signed_by) + " " + esc(eastern(signed.signed_at)) : "DRAFT - NOT SIGNED"}</div>
    <div class="ptop"><span>${esc(f.patient || n.patient_name || "(name not read yet)")} (${esc(f.dob || n.birth_date || "")}) #${esc(f.chart || n.chart_id)}</span><span>CCM month: ${esc(monthName(f.month || n.month))}</span></div>
    <div class="head"><h2>${esc(f.practice || "")}</h2></div>
    <div class="pgrid"><div><b>Patient:</b> ${esc(f.patient || n.patient_name || "")}</div><div><b>DOB:</b> ${esc(f.dob || n.birth_date || "")}</div><div><b>Primary Ins:</b> ${esc(f.insurance || n.insurance || "")}</div>
      <div><b>Location:</b> ${esc(f.location || "")}</div><div><b>Provider:</b> ${esc(f.provider || "")}</div><div><b>Chart:</b> ${esc(f.chart || n.chart_id)}</div></div>
    <h3>Chronic care management charges - ${esc(monthName(f.month || n.month))}</h3>
    <div class="tablewrap"><table><thead><tr><th>Charge date</th><th>Code</th><th>Visit</th><th>Charge</th></tr></thead><tbody>${charges.map((c) => `<tr>${[0, 1, 2, 3].map((i) => `<td>${esc((c || [])[i] ?? "")}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="4">No charge line on the record.</td></tr>`}</tbody></table></div>
    <h3>LATE ENTRY</h3><div class="late"><p><b>${esc(f.late_entry || "")}</b> Written ${esc(written)}.</p><p>${f.statement ? esc(f.statement) : "<i>No ready-made statement: this month's statement is written on the hub before it is signed.</i>"}</p></div>
    <h3>Supporting documentation on file for ${esc(monthName(f.month || n.month))}</h3>
    ${evidence.length ? `<ul>${evidence.map((x) => `<li><b>${esc((x || [])[0] ?? "")}</b> - ${esc((x || [])[1] ?? "")} - ${esc((x || [])[2] ?? "")}${(x || [])[3] ? ` <span style="color:#666;font-size:11px">(${esc(x[3])})</span>` : ""}</li>`).join("")}</ul>` : `<p>No supporting item is on file for this month. The statement above stands alone.</p>`}
    <div class="sig">Rendering Provider Signature - ${esc(f.provider || "")}</div><div class="pfoot">${esc(f.practice || "")} | ${esc(f.provider || "")} | Late entry written ${esc(written)}</div></article>`;
  main.innerHTML = `${crumbs([["CCM notes", "#ccm"], [monthName(n.month), "#ccm/m/" + n.month], [n.patient_name || n.chart_id]])}
    <h1>${esc(n.patient_name || n.chart_id)} · ${esc(monthName(n.month))}</h1>
    <div class="bar"><div class="chips">${statePill(n.status)}${(n.codes || []).map((c) => `<span class="chip">${esc(c)}</span>`).join("")}${n.minutes ? `<span class="chip soft">${fmt(n.minutes)} minutes</span>` : ""}</div><span style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn" href="#ccm/p/${esc(encodeURIComponent(n.chart_id))}">Every month for this patient</a>${hubBtn(d.hub, signed ? "Open the CCM Documentation Hub" : "Sign on the CCM Documentation Hub")}</span></div>
    ${n.flag ? `<aside class="callout warn"><strong>Flagged for your own look</strong><p>${esc(n.flag)}</p></aside>` : ""}
    ${signed ? `<p class="note">Signed by ${esc(signed.signed_by)} on ${esc(when(signed.signed_at))}, written ${esc(signed.written_on || "")}; recorded in the practice database ${esc(when(signed.recorded_at))}${signed.via ? " from the hub page" : ""}. A signed note is final: the database refuses any change to it, and a correction is a new late entry. Fingerprint <code>${esc(String(signed.sha || "").slice(0, 16))}…</code></p>`
      : `<p class="note">This is the draft the hub shows. It becomes a signed late entry only when it is signed on the CCM Documentation Hub; this page never signs.</p>`}
    ${paper}`;
}

async function showPatients(main: HTMLElement) {
  const d = await cached<{ patients: any[]; hub: string }>("/api/ccm/patients");
  const all = d.patients || [];
  main.innerHTML = `<h1>CCM patients</h1><p class="lead">Every patient with a chronic care management charge, with the months on the chart and where their notes stand.</p>
    <div class="filters"><input type="search" id="pt-q" placeholder="Find a patient or chart" aria-label="Find a patient or chart" value="${esc(query)}"></div><div id="pt-list"></div>`;
  const draw = () => {
    const q = query.trim().toLowerCase(); const rows = all.filter((p) => !q || String(p.name || "").toLowerCase().includes(q) || String(p.chart_id).toLowerCase().includes(q));
    $("#pt-list").innerHTML = `<section class="block"><header><h2>Patients</h2><span class="note">${fmt(rows.length)} of ${fmt(all.length)}</span></header>${rows.length ? `<div class="tablewrap"><table><thead><tr><th>Patient</th><th>Birth date</th><th>Sex</th><th>Chart</th><th class="num">Months</th><th class="num">Signed</th><th class="num">Ready</th><th class="num">Flagged</th><th>First</th><th>Last</th></tr></thead><tbody>${rows.slice(0, 400).map((p) => `<tr><td><a href="#ccm/p/${esc(encodeURIComponent(p.chart_id))}">${p.name ? esc(p.name) : '<span class="dim">name not read yet</span>'}</a></td><td class="mono">${esc(p.birth_date || "")}</td><td>${esc(p.sex || "")}</td><td class="mono">${esc(p.chart_id)}</td><td class="num">${fmt(p.months)}</td><td class="num">${fmt(p.signed)}</td><td class="num">${fmt(p.ready)}</td><td class="num">${fmt(p.flagged)}</td><td class="mono">${esc(p.first_month || "")}</td><td class="mono">${esc(p.last_month || "")}</td></tr>`).join("")}</tbody></table></div>${rows.length > 400 ? `<p class="note">The first 400 are listed; search to find the others.</p>` : ""}` : `<p class="note">No patient matches.</p>`}</section>`;
  };
  draw();
  $("#pt-q").addEventListener("input", (ev) => { query = (ev.target as HTMLInputElement).value; draw(); });
}

async function showPatient(main: HTMLElement, chart: string) {
  const d = await cached<{ patient: any; notes: any[]; chart: string; hub: string }>("/api/ccm/patient/" + encodeURIComponent(chart));
  const p = d.patient || {}, notes = d.notes || [];
  main.innerHTML = `${crumbs([["CCM notes", "#ccm"], ["Patients", "#ccm/patients"], [p.name || d.chart]])}
    <h1>${esc(p.name || d.chart)}</h1>
    <div class="bar"><div class="chips"><span class="chip">Chart ${esc(d.chart)}</span>${p.birth_date ? `<span class="chip">Born ${esc(p.birth_date)}</span>` : ""}${p.sex ? `<span class="chip soft">${esc(p.sex)}</span>` : ""}<span class="chip soft">${fmt(notes.length)} months of CCM</span></div>${hubBtn(d.hub)}</div>
    <section class="block"><header><h2>Months</h2><span class="note">newest first</span></header>${notes.length ? `<div class="tablewrap"><table><thead><tr><th>Month</th><th>Codes</th><th class="num">Minutes</th><th>Location</th><th>Insurance</th><th>Status</th><th>Signed</th><th></th></tr></thead><tbody>${notes.map((n) => `<tr><td>${esc(monthName(n.month))}${n.flag ? `<div class="flagtext">${esc(n.flag)}</div>` : ""}</td><td class="mono">${esc((n.codes || []).join(" + "))}</td><td class="num">${n.minutes ? fmt(n.minutes) : ""}</td><td>${esc(n.location || "")}</td><td>${esc(n.insurance || "")}</td><td>${statePill(n.status)}</td><td class="note">${n.signed_at ? esc(when(n.signed_at)) : ""}</td><td><a class="btn" href="#ccm/note/${esc(encodeURIComponent(n.note_id))}">Open</a></td></tr>`).join("")}</tbody></table></div>` : `<p class="note">No CCM month on this chart.</p>`}</section>`;
}

async function showSigned(main: HTMLElement) {
  const d = await cached<{ signed: any[]; hub: string }>("/api/ccm/signed");
  const rows = d.signed || [];
  main.innerHTML = `<h1>Signed notes</h1><p class="lead">The newest signings recorded in the practice database. A signing made on the hub appears here once it is verified against the stored draft and recorded (scripts/helpers/ccm_build.py signatures); a signed note is final.</p>
    <div class="bar"><span class="note">${fmt(rows.length)} newest signings</span>${hubBtn(d.hub, "Open the CCM Documentation Hub")}</div>
    <section class="block">${rows.length ? `<div class="tablewrap"><table><thead><tr><th>Signed</th><th>Patient</th><th>Chart</th><th>Month</th><th>Written</th><th>By</th><th>Recorded</th><th></th></tr></thead><tbody>${rows.map((s) => `<tr><td class="mono">${esc(when(s.signed_at))}</td><td>${s.patient_name ? esc(s.patient_name) : '<span class="dim">name not read yet</span>'}</td><td class="mono">${esc(s.chart_id)}</td><td>${esc(monthName(s.month))}</td><td class="mono">${esc(s.written_on || "")}</td><td>${esc(s.signed_by || "")}</td><td class="note">${esc(when(s.recorded_at))}</td><td><a class="btn" href="#ccm/note/${esc(encodeURIComponent(s.note_id))}">Open</a></td></tr>`).join("")}</tbody></table></div>` : `<p class="note">No signed note is recorded yet.</p>`}</section>`;
}
