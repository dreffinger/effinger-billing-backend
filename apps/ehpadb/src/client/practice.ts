// Practice Optimization for one practice: the universal framework applied to the practice the app belongs to. One bundle
// (/api/upo/practice/<code>) holds its standing per area, its metric values, risk findings, recommendations, projects, the work
// list and the valuation. Pages: #practice (summary), #practice/scorecard, /areas, /risks, /plan, /projects, /worklist, /valuation.
// The only thing this page changes is a work-list row's status and note (POST /api/upo/practice/<code>/worklist/<id>).
import { $, esc, cached, clearCache, apiPost, say, rich, ul, block, table, tile, tag, list, empty, statusChip, appliesChip, sevChip, metricValue, usd, usdK, range, day, extLink, PRACTICE } from "./core";

type PCat = { category_slug: string; category: string; domain_slug: string; domain: string; domain_ord: number; category_ord: number; applicability: string; status: string; priority?: number; assessment?: string; evidence?: unknown; next_step?: string };
type PMetric = { metric_slug: string; name: string; category_slug: string; category: string; domain_slug: string; unit?: string; direction?: string; definition?: string; formula?: string; benchmark_best?: string; benchmark_typical?: string; benchmark_red?: string; benchmark_note?: string; as_of?: string; value?: number; value_text?: string; status?: string; basis?: string; note?: string; source?: string };
type Risk = { id: string; ord: number; title: string; severity?: string; likelihood?: string; category_slug?: string; category?: string; what_we_see?: string; rule?: string; exposure?: string; recommended_review?: string; control?: string; sources?: unknown; status?: string };
type Rec = { id: string; ord: number; kind?: string; category_slug?: string; category?: string; title: string; why?: string; what?: unknown; impact_low?: number; impact_high?: number; impact_basis?: string; effort?: string; horizon?: string; owner?: string; project_slug?: string; confidence?: string };
type Project = { slug: string; ord: number; title: string; objective?: string; category_slug?: string; priority?: string; status?: string; impact_low?: number; impact_high?: number; impact_note?: string; owner?: string; start_by?: string; target_date?: string; success_measures?: unknown; steps?: unknown; items: number; items_done: number };
type Work = { id: string; project_slug?: string; ord: number; title: string; detail?: string; owner?: string; due?: string; status: string; note?: string; updated_at?: string; updated_by?: string };
type Valuation = { as_of: string; method: string; low?: number; base?: number; high?: number; inputs?: Record<string, unknown>; bridge?: { label: string; amount?: number; note?: string; kind?: string }[]; notes?: string };
type Bundle = { practice: { code: string; name: string; specialty?: string; setting?: string; profile?: Record<string, any>; updated_at?: string } | null; categories: PCat[]; metrics: PMetric[]; risks: Risk[]; recommendations: Rec[]; projects: Project[]; worklist: Work[]; valuations: Valuation[]; meta: Record<string, any> };

const PATH = "/api/upo/practice/" + PRACTICE;
const bundle = () => cached<Bundle>(PATH);

export const PRACTICE_NAV: [string, string][] = [["practice", "Summary"], ["practice/scorecard", "Scorecard"], ["practice/areas", "Areas"], ["practice/risks", "Risk review"], ["practice/plan", "Recommendations"], ["practice/projects", "Projects"], ["practice/worklist", "Work list"], ["practice/valuation", "Valuation"]];

const KIND: Record<string, string> = { revenue: "Revenue", risk: "Risk", cost: "Cost", value: "Sale value", capability: "Capability" };
const OWNER: Record<string, string> = { william: "William", claude: "Claude", pam: "Nurse practitioner", cpa: "Accountant", attorney: "Healthcare attorney", staff: "Staff" };
const owner = (o: unknown) => OWNER[String(o || "").toLowerCase()] || String(o || "");
const WSTATUS: [string, string][] = [["open", "Open"], ["doing", "In progress"], ["waiting", "Waiting on someone"], ["done", "Done"], ["dropped", "Dropped"]];
const SEV_ORD: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
const impact = (lo: unknown, hi: unknown) => { const r = range(lo, hi); return r ? r + " a year" : ""; };

async function pageSummary(): Promise<string> {
  const b = await bundle(); const p = b.practice!;
  const head = b.meta?.[`practice:${p.code}:summary`] || {};
  const v = b.valuations.find((x) => x.method === "summary");
  const applicable = b.categories.filter((c) => c.applicability !== "not_applicable");
  const count = (s: string) => applicable.filter((c) => c.status === s).length;
  const openWork = b.worklist.filter((w) => w.status !== "done" && w.status !== "dropped");
  const hot = b.risks.filter((r) => r.severity === "critical" || r.severity === "high");
  const now = b.projects.filter((x) => x.priority === "now");
  const tiles = (Array.isArray(head.tiles) ? head.tiles : []).map((t: any) => tile(String(t.label || ""), String(t.value || ""), String(t.sub || ""), String(t.tone || ""))).join("");
  const byDomain = [...new Set(applicable.map((c) => c.domain))].map((dname) => {
    const cs = applicable.filter((c) => c.domain === dname); const n = (s: string) => cs.filter((c) => c.status === s).length;
    const seg = (s: string) => (n(s) ? `<span class="seg-${s}" style="flex:${n(s)}" title="${n(s)} ${s}"></span>` : "");
    return [esc(dname), `<div class="stack" role="img" aria-label="${n("red")} act, ${n("amber")} watch, ${n("green")} on track, ${n("unknown")} no data">${seg("red")}${seg("amber")}${seg("green")}${seg("unknown")}</div>`, String(n("red")), String(n("amber")), String(n("green")), String(n("unknown"))];
  });
  return `<h1>${esc(p.name)}: practice optimization</h1>
    <p class="lead">${rich(head.lead || "The universal framework applied to this practice: where it stands in each area, the numbers behind that, the risks to review, and the work to do next.")}</p>
    <div class="tiles">${tiles}${v ? tile("Indicative value of the practice", usdK(v.base), range(v.low, v.high) + " range", "accent") : ""}${tile("Areas needing action", String(count("red")), `${count("amber")} to watch · ${count("green")} on track`, count("red") ? "warn" : "")}${tile("High-severity risks to review", String(hot.length), `${b.risks.length} findings in all`, hot.length ? "warn" : "")}${tile("Open work-list items", String(openWork.length), `${now.length} project${now.length === 1 ? "" : "s"} to start now`)}</div>
    ${head.headline ? block("The short version", ul(head.headline, "bullets")) : ""}
    ${block("Do these first", b.recommendations.slice(0, 6).length ? table([{ h: "Recommendation" }, { h: "Type", w: "10%" }, { h: "Worth", w: "18%" }, { h: "Effort", w: "9%" }], b.recommendations.slice(0, 6).map((r) => [`<strong>${esc(r.title)}</strong>${r.why ? `<div class="note">${rich(r.why)}</div>` : ""}`, tag(KIND[r.kind || ""] || r.kind, "kind-" + (r.kind || "")), esc(impact(r.impact_low, r.impact_high) || r.impact_basis || ""), esc(r.effort || "")])) + `<p><a href="#practice/plan">All ${b.recommendations.length} recommendations</a></p>` : "", "ranked by payoff and urgency")}
    ${hot.length ? block("Risks to review first", table([{ h: "Finding" }, { h: "Severity", w: "11%" }], hot.slice(0, 6).map((r) => [`<a href="#practice/risks">${esc(r.title)}</a>${r.what_we_see ? `<div class="note">${rich(r.what_we_see)}</div>` : ""}`, sevChip(r.severity)])), "patterns in the practice's own numbers, not conclusions") : ""}
    ${byDomain.length ? block("Standing by domain", table([{ h: "Domain" }, { h: "", w: "30%" }, { h: "Act", num: true }, { h: "Watch", num: true }, { h: "On track", num: true }, { h: "No data", num: true }], byDomain) + `<p><a href="#practice/areas">Every area with its assessment</a></p>`) : ""}
    <p class="foot">${esc(head.as_of ? "Assessed " + day(head.as_of) + ". " : "")}Aggregates only: dollars, counts and rates. This is management information for the owner, not legal, tax, coding or valuation advice.</p>`;
}

async function pageScorecard(): Promise<string> {
  const b = await bundle();
  if (!b.metrics.length) return `<h1>Scorecard</h1>${empty("No metric values have been loaded yet.")}`;
  const doms = [...new Set(b.metrics.map((m) => m.domain_slug))];
  const name = (slug: string) => b.categories.find((c) => c.domain_slug === slug)?.domain || slug;
  const n = (s: string) => b.metrics.filter((m) => m.status === s).length;
  return `<h1>Scorecard</h1><p class="lead">The practice's own numbers against the benchmarks in the framework. "Estimated" means the figure is derived from partial data; "not measured" means the data to compute it is not collected yet.</p>
    <div class="tiles">${tile("Act", String(n("red")), "", n("red") ? "warn" : "")}${tile("Watch", String(n("amber")))}${tile("On track", String(n("green")))}${tile("Not measured yet", String(b.metrics.filter((m) => m.basis === "unknown" || m.status === "unknown").length))}</div>
    ${doms.map((d) => block(name(d), table([{ h: "Metric" }, { h: "This practice", w: "16%" }, { h: "Benchmark", w: "24%" }, { h: "Standing", w: "11%" }, { h: "As of", w: "10%" }],
      b.metrics.filter((m) => m.domain_slug === d).map((m) => [`<a href="#upo/c/${esc(m.category_slug)}"><strong>${esc(m.name)}</strong></a>${m.note ? `<div class="note">${rich(m.note)}</div>` : ""}`,
        `<span class="big">${esc(metricValue(m))}</span>${m.basis && m.basis !== "measured" ? `<div class="note">${esc(m.basis)}</div>` : ""}`,
        [m.benchmark_best ? `<div><span class="dim">Best:</span> ${rich(m.benchmark_best)}</div>` : "", m.benchmark_typical ? `<div><span class="dim">Typical:</span> ${rich(m.benchmark_typical)}</div>` : "", m.benchmark_red ? `<div><span class="dim">Red flag:</span> ${rich(m.benchmark_red)}</div>` : ""].join("") || `<span class="dim">no reliable benchmark</span>`,
        statusChip(m.status), esc(day(m.as_of))])))).join("")}`;
}

let areaFilter = { applies: "", status: "" };
async function pageAreas(): Promise<string> {
  const b = await bundle();
  const rows = b.categories.filter((c) => (!areaFilter.applies || c.applicability === areaFilter.applies) && (!areaFilter.status || c.status === areaFilter.status));
  const doms = [...new Set(rows.map((c) => c.domain))];
  const opt = (v: string, label: string, cur: string) => `<option value="${esc(v)}"${cur === v ? " selected" : ""}>${esc(label)}</option>`;
  return `<h1>Areas</h1><p class="lead">Every area of the universal framework, judged for this practice: whether it applies, where the practice stands, and the next step.</p>
    <form class="filters" id="area-filter"><label>Applies<select name="applies">${opt("", "All", areaFilter.applies)}${opt("core", "Core", areaFilter.applies)}${opt("relevant", "Relevant", areaFilter.applies)}${opt("minor", "Minor", areaFilter.applies)}${opt("not_applicable", "Does not apply", areaFilter.applies)}</select></label>
      <label>Standing<select name="status">${opt("", "All", areaFilter.status)}${opt("red", "Act", areaFilter.status)}${opt("amber", "Watch", areaFilter.status)}${opt("green", "On track", areaFilter.status)}${opt("unknown", "No data yet", areaFilter.status)}</select></label>
      <span class="note" aria-live="polite">${rows.length} of ${b.categories.length} areas</span></form>
    ${doms.length ? doms.map((d) => block(d, rows.filter((c) => c.domain === d).map((c) => `<article class="area"><header><h3><a href="#upo/c/${esc(c.category_slug)}">${esc(c.category)}</a></h3><div class="chips">${appliesChip(c.applicability)}${c.applicability === "not_applicable" ? "" : statusChip(c.status)}</div></header>
        ${c.assessment ? `<p>${rich(c.assessment)}</p>` : ""}${ul(c.evidence, "bullets evidence")}${c.next_step ? `<p><strong>Next step:</strong> ${rich(c.next_step)}</p>` : ""}</article>`).join(""))).join("") : empty("No area matches those filters.")}`;
}

async function pageRisks(): Promise<string> {
  const b = await bundle(); const note = b.meta?.[`practice:${PRACTICE}:risk_note`] || {};
  const rs = b.risks.slice().sort((x, y) => (SEV_ORD[x.severity || "medium"] - SEV_ORD[y.severity || "medium"]) || x.ord - y.ord);
  if (!rs.length) return `<h1>Risk review</h1>${empty("No findings have been loaded yet.")}`;
  const n = (s: string) => rs.filter((r) => r.severity === s).length;
  return `<h1>Risk review</h1><p class="lead">${rich(note.lead || "Patterns in the practice's own billing data that an auditor's analytics would also see, set beside the rule each one touches. A pattern is a reason to look at charts, not a finding of error.")}</p>
    <div class="tiles">${tile("Critical", String(n("critical")), "", n("critical") ? "warn" : "")}${tile("High", String(n("high")), "", n("high") ? "warn" : "")}${tile("Medium", String(n("medium")))}${tile("Low", String(n("low")))}</div>
    ${note.how_to_use ? block("How to use this", ul(note.how_to_use, "bullets")) : ""}
    ${rs.map((r) => `<section class="block risk"><header><h2>${esc(r.title)}</h2><div class="chips">${sevChip(r.severity)}${r.likelihood ? tag("Likelihood: " + r.likelihood, "soft") : ""}${r.category ? `<a class="chip soft" href="#upo/c/${esc(r.category_slug)}">${esc(r.category)}</a>` : ""}</div></header>
      <dl class="kv wide">${r.what_we_see ? `<div><dt>What the data shows</dt><dd>${rich(r.what_we_see)}</dd></div>` : ""}${r.rule ? `<div><dt>The rule</dt><dd>${rich(r.rule)}</dd></div>` : ""}${r.exposure ? `<div><dt>What is at stake</dt><dd>${rich(r.exposure)}</dd></div>` : ""}${r.recommended_review ? `<div><dt>How to review it</dt><dd>${rich(r.recommended_review)}</dd></div>` : ""}${r.control ? `<div><dt>The control going forward</dt><dd>${rich(r.control)}</dd></div>` : ""}</dl>
      ${list(r.sources).length ? `<p class="note">Sources: ${(Array.isArray(r.sources) ? r.sources : []).map((s: any) => (typeof s === "string" ? extLink(s) : extLink(s?.url, s?.title))).join(" · ")}</p>` : ""}</section>`).join("")}
    <p class="foot">${rich(note.foot || "Education and management information, not legal advice. Where a chart review suggests money was overpaid, federal law sets a deadline to report and return it; involve a healthcare attorney before and during that review.")}</p>`;
}

async function pagePlan(): Promise<string> {
  const b = await bundle();
  if (!b.recommendations.length) return `<h1>Recommendations</h1>${empty("No recommendations have been loaded yet.")}`;
  const lo = b.recommendations.reduce((a, r) => a + (r.kind === "revenue" || r.kind === "cost" ? Number(r.impact_low) || 0 : 0), 0), hi = b.recommendations.reduce((a, r) => a + (r.kind === "revenue" || r.kind === "cost" ? Number(r.impact_high) || 0 : 0), 0);
  return `<h1>Recommendations</h1><p class="lead">What to change, in order. Each one says why, what to do, what it is worth and how sure the estimate is.</p>
    <div class="tiles">${tile("Recommendations", String(b.recommendations.length))}${hi ? tile("Revenue and cost items, combined", range(lo, hi), "a year, if all were achieved; the estimates overlap, so do not add them to a forecast", "accent") : ""}</div>
    ${b.recommendations.map((r, i) => `<section class="block rec"><header><h2><span class="rank">${i + 1}</span>${esc(r.title)}</h2><div class="chips">${tag(KIND[r.kind || ""] || r.kind, "kind-" + (r.kind || ""))}${r.horizon ? tag(r.horizon, "soft") : ""}${r.effort ? tag("Effort: " + r.effort, "soft") : ""}${r.owner ? tag(owner(r.owner), "soft") : ""}</div></header>
      ${r.why ? `<p>${rich(r.why)}</p>` : ""}${ul(r.what, "bullets")}
      <dl class="kv wide">${impact(r.impact_low, r.impact_high) ? `<div><dt>Worth</dt><dd><strong>${esc(impact(r.impact_low, r.impact_high))}</strong>${r.impact_basis ? ` <span class="note">${rich(r.impact_basis)}</span>` : ""}</dd></div>` : r.impact_basis ? `<div><dt>Worth</dt><dd>${rich(r.impact_basis)}</dd></div>` : ""}${r.confidence ? `<div><dt>Confidence</dt><dd>${esc(r.confidence)}</dd></div>` : ""}${r.category ? `<div><dt>Framework area</dt><dd><a href="#upo/c/${esc(r.category_slug)}">${esc(r.category)}</a></dd></div>` : ""}${r.project_slug ? `<div><dt>Project</dt><dd><a href="#practice/projects">${esc(b.projects.find((p) => p.slug === r.project_slug)?.title || r.project_slug)}</a></dd></div>` : ""}</dl></section>`).join("")}`;
}

async function pageProjects(): Promise<string> {
  const b = await bundle();
  if (!b.projects.length) return `<h1>Projects</h1>${empty("No projects have been loaded yet.")}`;
  const col = (key: string, label: string, sub: string) => { const ps = b.projects.filter((p) => (p.priority || "later") === key); return `<section class="lane"><header><h2>${esc(label)}</h2><span class="note">${esc(sub)} · ${ps.length}</span></header>${ps.map((p) => {
    const pct = p.items ? Math.round((100 * p.items_done) / p.items) : 0;
    return `<article class="proj"><h3>${esc(p.title)}</h3>${p.objective ? `<p>${rich(p.objective)}</p>` : ""}
      <div class="chips">${p.owner ? tag(owner(p.owner), "soft") : ""}${p.target_date ? tag("Target " + day(p.target_date), "soft") : ""}${impact(p.impact_low, p.impact_high) ? tag(impact(p.impact_low, p.impact_high), "kind-revenue") : ""}</div>
      ${p.impact_note ? `<p class="note">${rich(p.impact_note)}</p>` : ""}
      ${list(p.success_measures).length ? `<p class="note"><strong>Done when:</strong></p>${ul(p.success_measures, "bullets")}` : ""}
      ${list(p.steps).length ? `<details><summary>${list(p.steps).length} steps</summary><ol class="steps">${list(p.steps).map((s) => `<li>${rich(s)}</li>`).join("")}</ol></details>` : ""}
      ${p.items ? `<div class="progress" role="img" aria-label="${p.items_done} of ${p.items} work-list items done"><span style="width:${pct}%"></span></div><p class="note"><a href="#practice/worklist" data-project="${esc(p.slug)}">${p.items_done} of ${p.items} work-list items done</a></p>` : ""}</article>`; }).join("") || empty("Nothing in this lane.")}</section>`; };
  return `<h1>Projects</h1><p class="lead">The recommendations grouped into pieces of work with an owner, a finish line and steps. Start with "Now".</p>
    <div class="lanes">${col("now", "Now", "next 30 days")}${col("next", "Next", "30 to 90 days")}${col("later", "Later", "after 90 days")}</div>`;
}

let workFilter = { project: "", owner: "", status: "active" };
const workTiles = (b: Bundle) => { const n = (st: string) => b.worklist.filter((w) => w.status === st).length; return tile("Open", String(n("open"))) + tile("In progress", String(n("doing"))) + tile("Waiting", String(n("waiting"))) + tile("Done", String(n("done")), `of ${b.worklist.length}`); };
async function pageWorklist(): Promise<string> {
  const b = await bundle();
  if (!b.worklist.length) return `<h1>Work list</h1>${empty("No work-list items have been loaded yet.")}`;
  const rows = b.worklist.filter((w) => (!workFilter.project || w.project_slug === workFilter.project) && (!workFilter.owner || (w.owner || "") === workFilter.owner)
    && (workFilter.status === "" || (workFilter.status === "active" ? w.status !== "done" && w.status !== "dropped" : w.status === workFilter.status)));
  const owners = [...new Set(b.worklist.map((w) => w.owner || "").filter(Boolean))];
  const opt = (v: string, label: string, cur: string) => `<option value="${esc(v)}"${cur === v ? " selected" : ""}>${esc(label)}</option>`;
  const proj = (slug?: string) => b.projects.find((p) => p.slug === slug)?.title || "";
  return `<h1>Work list</h1><p class="lead">The individual things to do. Change a row's status or leave a note and press Save; it is stored in the practice database with your name and the time.</p>
    <div class="tiles" id="work-tiles">${workTiles(b)}</div>
    <form class="filters" id="work-filter"><label>Project<select name="project">${opt("", "All projects", workFilter.project)}${b.projects.map((p) => opt(p.slug, p.title, workFilter.project)).join("")}</select></label>
      <label>Owner<select name="owner">${opt("", "Everyone", workFilter.owner)}${owners.map((o) => opt(o, owner(o), workFilter.owner)).join("")}</select></label>
      <label>Status<select name="status">${opt("active", "Not finished", workFilter.status)}${opt("", "All", workFilter.status)}${WSTATUS.map(([v, l]) => opt(v, l, workFilter.status)).join("")}</select></label>
      <span class="note" aria-live="polite">${rows.length} of ${b.worklist.length}</span></form>
    ${rows.length ? rows.map((w) => `<form class="work st-${esc(w.status)}" data-work="${esc(w.id)}"><div class="work-main"><h3>${esc(w.title)}</h3>${w.detail ? `<p>${rich(w.detail)}</p>` : ""}
        <div class="chips">${w.owner ? tag(owner(w.owner), "soft") : ""}${w.due ? tag("Due " + day(w.due), "soft") : ""}${proj(w.project_slug) ? tag(proj(w.project_slug), "soft") : ""}</div>
        ${w.updated_by ? `<p class="note">Last changed ${esc(day(w.updated_at))} by ${esc(w.updated_by)}</p>` : ""}</div>
      <div class="work-edit"><label>Status<select name="status">${WSTATUS.map(([v, l]) => opt(v, l, w.status)).join("")}</select></label><label>Note<textarea name="note" rows="2" maxlength="2000">${esc(w.note || "")}</textarea></label><button class="btn primary" type="submit">Save</button><span class="note work-msg" aria-live="polite"></span></div></form>`).join("") : empty("No item matches those filters.")}`;
}

async function pageValuation(): Promise<string> {
  const b = await bundle(); const s = b.valuations.find((v) => v.method === "summary");
  if (!s) return `<h1>Valuation</h1>${empty("No valuation has been loaded yet.")}`;
  const others = b.valuations.filter((v) => v.method !== "summary"); const inputs = s.inputs || {};
  const lo = Number(s.low) || 0, hi = Number(s.high) || 0, base = Number(s.base) || 0;
  const top = Math.max(hi, ...others.map((v) => Number(v.high) || 0)) * 1.08 || 1;
  const bar = (v: Valuation, label: string, strong = false) => { const l = (100 * (Number(v.low) || 0)) / top, w = Math.max(0.6, (100 * ((Number(v.high) || 0) - (Number(v.low) || 0))) / top), m = (100 * (Number(v.base) || 0)) / top;
    return `<div class="vrow${strong ? " strong" : ""}"><div class="vlabel">${esc(label)}</div><div class="vtrack" role="img" aria-label="${esc(label)}: ${esc(range(v.low, v.high))}, most likely ${esc(usdK(v.base))}"><span class="vband" style="left:${l.toFixed(2)}%;width:${w.toFixed(2)}%"></span><span class="vdot" style="left:${m.toFixed(2)}%"></span></div><div class="vnum">${esc(usdK(v.base))}<span class="note"> ${esc(range(v.low, v.high))}</span></div></div>`; };
  const kv = (obj: Record<string, unknown>) => `<dl class="kv wide">${Object.entries(obj).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${typeof v === "number" ? esc(Math.abs(v) >= 1000 ? usd(v) : String(v)) : rich(Array.isArray(v) ? v.join("; ") : v)}</dd></div>`).join("")}</dl>`;
  return `<h1>Valuation</h1><p class="lead">An indicative estimate of what the practice would sell for today, built from its own financial statements and published market evidence. It is a planning number, not an appraisal.</p>
    <div class="tiles">${tile("Most likely enterprise value", usdK(base), "as of " + day(s.as_of), "accent")}${tile("Low case", usdK(lo))}${tile("High case", usdK(hi))}${inputs["Normalized EBITDA"] !== undefined ? tile("Normalized EBITDA", typeof inputs["Normalized EBITDA"] === "number" ? usdK(inputs["Normalized EBITDA"]) : String(inputs["Normalized EBITDA"]), "after paying a physician a market wage") : ""}</div>
    ${block("The range by method", `<div class="vchart">${bar(s, "Conclusion", true)}${others.map((v) => bar(v, v.method)).join("")}</div><p class="note">The band is the low-to-high range; the dot is the most likely figure. Dollar axis starts at zero.</p>`)}
    ${Array.isArray(s.bridge) && s.bridge.length ? block("From earnings to what the owner keeps", table([{ h: "Step" }, { h: "Amount", num: true, w: "18%" }, { h: "Why" }], s.bridge.map((r) => [r.kind === "total" ? `<strong>${esc(r.label)}</strong>` : esc(r.label), r.amount === undefined || r.amount === null ? "" : r.kind === "total" ? `<strong>${esc(usd(r.amount))}</strong>` : esc(usd(r.amount)), rich(r.note || "")]))) : ""}
    ${Object.keys(inputs).length ? block("Inputs and assumptions", kv(inputs)) : ""}
    ${others.map((v) => block(v.method, `${v.notes ? `<p>${rich(v.notes)}</p>` : ""}${v.inputs && Object.keys(v.inputs).length ? kv(v.inputs) : ""}`, range(v.low, v.high))).join("")}
    ${s.notes ? block("What moves the number", `<p>${rich(s.notes)}</p>`) : ""}
    <p class="foot">Not an appraisal, and not tax or legal advice. A sale to a hospital or health system must be at fair market value set by an independent appraiser. See the learning module on maximizing sale value for how buyers think.</p>`;
}

export async function showPractice(parts: string[]): Promise<void> {
  const b = await bundle();
  if (!b.practice) { $("#main").innerHTML = `<h1>Practice optimization</h1>${empty("This practice has not been loaded into the framework yet.")}`; return; }
  const a = parts[1] || "";
  const pages: Record<string, () => Promise<string>> = { "": pageSummary, scorecard: pageScorecard, areas: pageAreas, risks: pageRisks, plan: pagePlan, projects: pageProjects, worklist: pageWorklist, valuation: pageValuation };
  $("#main").innerHTML = await (pages[a] || pageSummary)();
}

// filters redraw in place; a "N of M items done" link on a project opens the work list filtered to it
document.addEventListener("change", async (ev) => {
  const t = ev.target as HTMLElement;
  const af = t.closest("#area-filter") as HTMLFormElement | null;
  if (af) { areaFilter = { applies: (af.elements.namedItem("applies") as HTMLSelectElement).value, status: (af.elements.namedItem("status") as HTMLSelectElement).value }; $("#main").innerHTML = await pageAreas(); return; }
  const wf = t.closest("#work-filter") as HTMLFormElement | null;
  if (wf) { workFilter = { project: (wf.elements.namedItem("project") as HTMLSelectElement).value, owner: (wf.elements.namedItem("owner") as HTMLSelectElement).value, status: (wf.elements.namedItem("status") as HTMLSelectElement).value }; $("#main").innerHTML = await pageWorklist(); }
});
document.addEventListener("click", (ev) => {
  const a = (ev.target as HTMLElement).closest("a[data-project]") as HTMLElement | null;
  if (a) workFilter = { project: a.dataset.project || "", owner: "", status: "" };
});
// saving one work-list row
document.addEventListener("submit", async (ev) => {
  const f = ev.target as HTMLFormElement;
  if (f.id === "area-filter" || f.id === "work-filter") { ev.preventDefault(); return; }
  if (!f.matches("form.work")) return;
  ev.preventDefault();
  const id = f.dataset.work || ""; const msg = f.querySelector(".work-msg") as HTMLElement; const btn = f.querySelector("button[type=submit]") as HTMLButtonElement;
  const status = (f.elements.namedItem("status") as HTMLSelectElement).value, note = (f.elements.namedItem("note") as HTMLTextAreaElement).value;
  btn.disabled = true; msg.textContent = "Saving…"; msg.className = "note work-msg";
  try {
    const r = await apiPost<{ id: string; status: string; note: string; updated_at: string; updated_by: string }>(`${PATH}/worklist/${encodeURIComponent(id)}`, { status, note });
    const b = await bundle(); const w = b.worklist.find((x) => x.id === id);
    if (w) { w.status = r.status; w.note = r.note; w.updated_at = r.updated_at; w.updated_by = r.updated_by; }
    const p = b.projects.find((x) => x.slug === w?.project_slug);
    if (p) p.items_done = b.worklist.filter((x) => x.project_slug === p.slug && x.status === "done").length;
    f.className = "work st-" + r.status; msg.textContent = "Saved"; msg.className = "note work-msg ok"; say("");
    const tiles = document.getElementById("work-tiles"); if (tiles) tiles.innerHTML = workTiles(b);
  } catch (e: any) { msg.textContent = e.message || String(e); msg.className = "note work-msg err"; }
  finally { btn.disabled = false; }
});
export function forgetPractice() { clearCache(PATH); }
