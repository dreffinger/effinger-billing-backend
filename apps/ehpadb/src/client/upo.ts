// Universal Practice Optimization: the framework that applies to any practice. One bundle (/api/upo/universal) holds the
// domains, categories, metrics and sources; every page here is drawn from it in the browser, so moving around costs no request.
// Pages: #upo (the domains), #upo/d/<domain>, #upo/c/<category>, #upo/metrics, #upo/sources, #upo/library, #upo/library/<item>.
import { $, esc, cached, rich, ul, block, table, tile, crumbs, tag, extLink, list, empty, statusChip, appliesChip, verdictChip, PRACTICE, fmtInt, usd } from "./core";

export type Domain = { slug: string; ord: number; name: string; summary: string; why_it_matters?: string; owner_role?: string; frameworks?: unknown };
export type Action = { action: string; detail?: string; cadence?: string; effort?: string; impact?: string };
export type Category = { slug: string; domain_slug: string; ord: number; name: string; summary: string; good_looks_like?: unknown; failure_modes?: unknown; key_questions?: unknown; actions?: Action[]; applies_when?: string; vendor_refs?: { item?: string; note?: string }[]; sources?: string[]; evidence_note?: string };
export type Metric = { slug: string; category_slug: string; ord: number; name: string; definition: string; formula?: string; unit?: string; direction?: string; cadence?: string; benchmark_best?: string; benchmark_typical?: string; benchmark_red?: string; benchmark_note?: string; confidence?: string; sources?: string[]; data_hint?: string; vendor_claim?: string; vendor_verdict?: string };
export type Source = { slug: string; title: string; publisher?: string; year?: string; url?: string; kind?: string; note?: string };
export type Universal = { domains: Domain[]; categories: Category[]; metrics: Metric[]; sources: Source[]; meta: Record<string, any> };
type Item = { slug: string; vendor: string; bundle?: string; title: string; doc_type?: string; pages?: number; words?: number; list_price_usd?: number; quality_score?: number; specificity_score?: number; practice_relevance_score?: number; summary?: string; top_ideas?: unknown; red_flags?: unknown; domains?: unknown; claims_checked: number; claims_supported: number; claims_partly: number; claims_contradicted: number; claims_outdated: number; claims_unverifiable: number; verdict?: string };
type Claim = { id: string; item_slug: string; claim: string; kind?: string; stakes?: string; verdict?: string; correct_statement?: string; source_title?: string; source_url?: string; confidence?: string; practice_impact?: string };
type Library = { items: Item[]; claims: Claim[]; meta: Record<string, any> };
type PracticeLite = { practice: { name: string } | null; categories: { category_slug: string; applicability: string; status: string; assessment?: string; next_step?: string }[] };

export const universal = () => cached<Universal>("/api/upo/universal");
const library = () => cached<Library>("/api/upo/library");

export const UPO_NAV: [string, string][] = [["upo", "Framework"], ["upo/metrics", "Metric library"], ["upo/library", "Purchased library review"], ["upo/sources", "Sources"]];

const DIR: Record<string, string> = { higher: "Higher is better", lower: "Lower is better", range: "Stay inside the range", info: "Context, not a target" };
const CONF: Record<string, string> = { high: "Benchmark read on the source", medium: "Benchmark from a reputable secondary source", low: "Benchmark weakly supported", none: "No reliable public benchmark" };

function sourceLine(u: Universal, slugs: unknown): string {
  const by = new Map(u.sources.map((s) => [s.slug, s]));
  const items = list(slugs).map((sl) => by.get(sl)).filter(Boolean) as Source[];
  if (!items.length) return "";
  return `<ul class="sources">${items.map((s) => `<li>${extLink(s.url, s.title)}${s.publisher || s.year ? ` <span class="dim">${esc([s.publisher, s.year].filter(Boolean).join(", "))}</span>` : ""}</li>`).join("")}</ul>`;
}

function metricCard(u: Universal, m: Metric, withCategory = false): string {
  const cat = u.categories.find((c) => c.slug === m.category_slug);
  const bench = [["Best practice", m.benchmark_best], ["Typical", m.benchmark_typical], ["Red flag", m.benchmark_red]].filter(([, v]) => v);
  return `<article class="metric" id="m-${esc(m.slug)}">
    <header><h3>${esc(m.name)}</h3><div class="chips">${tag(DIR[m.direction || ""] || "", "soft")}${tag(m.cadence, "soft")}${withCategory && cat ? `<a class="chip soft" href="#upo/c/${esc(cat.slug)}">${esc(cat.name)}</a>` : ""}</div></header>
    <p>${rich(m.definition)}</p>
    ${m.formula ? `<div class="formula"><div class="formula-l">How to calculate it</div><div class="formula-e">${rich(m.formula)}</div></div>` : ""}
    ${bench.length ? `<dl class="bench">${bench.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${rich(v)}</dd></div>`).join("")}</dl>` : `<p class="note">${esc(CONF.none)}.</p>`}
    ${m.benchmark_note ? `<p class="note">${rich(m.benchmark_note)}</p>` : ""}
    ${m.confidence && bench.length ? `<p class="note">${esc(CONF[m.confidence] || "")}.</p>` : ""}
    ${m.data_hint ? `<p class="note"><strong>Where the numbers come from:</strong> ${rich(m.data_hint)}</p>` : ""}
    ${m.vendor_claim ? `<p class="note"><strong>The purchased library says:</strong> ${rich(m.vendor_claim)}${m.vendor_verdict ? ` <em>${rich(m.vendor_verdict)}</em>` : ""}</p>` : ""}
    ${sourceLine(u, m.sources)}
  </article>`;
}

async function pageHome(): Promise<string> {
  const u = await universal();
  if (!u.domains.length) return `<h1>Universal Practice Optimization</h1>${empty("The framework has not been loaded into the database yet.")}`;
  const intro = u.meta?.intro || {};
  const cards = u.domains.map((d) => {
    const cats = u.categories.filter((c) => c.domain_slug === d.slug); const nm = u.metrics.filter((m) => cats.some((c) => c.slug === m.category_slug)).length;
    return `<a class="card" href="#upo/d/${esc(d.slug)}"><div class="card-k">${String(d.ord).padStart(2, "0")}</div><h3>${esc(d.name)}</h3><p>${esc(d.summary)}</p><div class="card-f">${cats.length} areas · ${nm} metrics</div></a>`;
  }).join("");
  return `<h1>Universal Practice Optimization</h1>
    <p class="lead">${rich(intro.lead || "A framework for running any medical practice as a business: what to manage, what good looks like, what to measure, and what to do when a number is off.")}</p>
    <div class="tiles">${tile("Domains", String(u.domains.length))}${tile("Areas to manage", String(u.categories.length))}${tile("Metrics with benchmarks", String(u.metrics.length))}${tile("Sources cited", String(u.sources.length))}</div>
    ${intro.how_to_use ? block("How to use it", ul(intro.how_to_use, "bullets")) : ""}
    <div class="cards">${cards}</div>
    ${intro.method ? block("How it was built", `<p>${rich(intro.method)}</p>`) : ""}`;
}

async function pageDomain(slug: string): Promise<string> {
  const u = await universal(); const d = u.domains.find((x) => x.slug === slug);
  if (!d) return `<h1>Not found</h1>${empty("There is no domain with that name.")}`;
  const cats = u.categories.filter((c) => c.domain_slug === d.slug);
  const fw = list(d.frameworks);
  return `${crumbs([["Framework", "#upo"], [d.name]])}<h1>${esc(d.name)}</h1><p class="lead">${rich(d.summary)}</p>
    ${d.why_it_matters ? block("Why it matters", `<p>${rich(d.why_it_matters)}</p>${d.owner_role ? `<p class="note"><strong>Who usually owns it:</strong> ${rich(d.owner_role)}</p>` : ""}`) : ""}
    ${fw.length ? `<p class="note">Maps to: ${fw.map((x) => tag(x, "soft")).join(" ")}</p>` : ""}
    <div class="cards">${cats.map((c) => { const n = u.metrics.filter((m) => m.category_slug === c.slug).length; return `<a class="card" href="#upo/c/${esc(c.slug)}"><h3>${esc(c.name)}</h3><p>${esc(c.summary)}</p><div class="card-f">${(c.actions || []).length} actions · ${n} metrics</div></a>`; }).join("")}</div>`;
}

async function pageCategory(slug: string): Promise<string> {
  const u = await universal(); const c = u.categories.find((x) => x.slug === slug);
  if (!c) return `<h1>Not found</h1>${empty("There is no area with that name.")}`;
  const d = u.domains.find((x) => x.slug === c.domain_slug)!; const ms = u.metrics.filter((m) => m.category_slug === c.slug);
  const sibs = u.categories.filter((x) => x.domain_slug === c.domain_slug); const i = sibs.findIndex((x) => x.slug === c.slug);
  let mine = "";
  try {
    const p = await cached<PracticeLite>("/api/upo/practice/" + PRACTICE); const pc = p.categories.find((x) => x.category_slug === c.slug);
    if (pc && p.practice) mine = block(`For ${p.practice.name}`, `<div class="chips">${appliesChip(pc.applicability)}${statusChip(pc.status)}</div>${pc.assessment ? `<p>${rich(pc.assessment)}</p>` : ""}${pc.next_step ? `<p><strong>Next step:</strong> ${rich(pc.next_step)}</p>` : ""}<p><a href="#practice/areas">See every area for this practice</a></p>`, "", "mine");
  } catch { /* the practice layer is optional on this page */ }
  const acts = (c.actions || []).map((a) => [`<strong>${rich(a.action)}</strong>${a.detail ? `<div class="note">${rich(a.detail)}</div>` : ""}`, esc(a.cadence || ""), esc(a.effort || ""), esc(a.impact || "")]);
  const refs = (c.vendor_refs || []).filter((r) => r && r.item);
  return `${crumbs([["Framework", "#upo"], [d.name, "#upo/d/" + d.slug], [c.name]])}<h1>${esc(c.name)}</h1><p class="lead">${rich(c.summary)}</p>
    ${mine}
    <div class="two">${block("What good looks like", ul(c.good_looks_like, "bullets ok"))}${block("Where it usually breaks", ul(c.failure_modes, "bullets bad"))}</div>
    ${block("Questions to ask", ul(c.key_questions, "bullets"))}
    ${acts.length ? block("What to do", table([{ h: "Action" }, { h: "How often", w: "14%" }, { h: "Effort", w: "10%" }, { h: "Payoff", w: "10%" }], acts)) : ""}
    ${ms.length ? `<section class="block"><header><h2>What to measure</h2><span class="note">${ms.length} metric${ms.length === 1 ? "" : "s"}</span></header>${ms.map((m) => metricCard(u, m)).join("")}</section>` : ""}
    ${c.applies_when ? block("When this applies", `<p>${rich(c.applies_when)}</p>`) : ""}
    ${refs.length ? block("In the purchased library", `<ul class="bullets">${refs.map((r) => `<li><strong>${esc(r.item)}</strong>${r.note ? `: ${rich(r.note)}` : ""}</li>`).join("")}</ul><p class="note">Titles from the CleanClaimRx library the practice bought. See <a href="#upo/library">the review</a> for how each one held up under fact-checking.</p>`) : ""}
    ${c.evidence_note || list(c.sources).length ? block("Evidence", `${c.evidence_note ? `<p>${rich(c.evidence_note)}</p>` : ""}${sourceLine(u, c.sources)}`) : ""}
    <nav class="pager">${i > 0 ? `<a href="#upo/c/${esc(sibs[i - 1].slug)}">← ${esc(sibs[i - 1].name)}</a>` : "<span></span>"}${i < sibs.length - 1 ? `<a href="#upo/c/${esc(sibs[i + 1].slug)}">${esc(sibs[i + 1].name)} →</a>` : "<span></span>"}</nav>`;
}

let metricFilter = { q: "", domain: "" };
async function pageMetrics(): Promise<string> {
  const u = await universal();
  const catDom = new Map(u.categories.map((c) => [c.slug, c.domain_slug]));
  const q = metricFilter.q.trim().toLowerCase();
  const rows = u.metrics.filter((m) => (!metricFilter.domain || catDom.get(m.category_slug) === metricFilter.domain) && (!q || (m.name + " " + m.definition + " " + (m.formula || "")).toLowerCase().includes(q)));
  return `<h1>Metric library</h1><p class="lead">Every metric in the framework with its definition, formula and the benchmark the sources support. Where no reliable public benchmark exists, it says so.</p>
    <form class="filters" id="metric-filter" role="search"><label>Search<input type="search" name="q" value="${esc(metricFilter.q)}" placeholder="days in A/R, denial, overhead…"></label>
      <label>Domain<select name="domain"><option value="">All domains</option>${u.domains.map((d) => `<option value="${esc(d.slug)}"${metricFilter.domain === d.slug ? " selected" : ""}>${esc(d.name)}</option>`).join("")}</select></label>
      <span class="note" aria-live="polite">${rows.length} of ${u.metrics.length}</span></form>
    <section class="block">${rows.length ? rows.map((m) => metricCard(u, m, true)).join("") : empty("No metric matches that search.")}</section>`;
}

async function pageSources(): Promise<string> {
  const u = await universal();
  const kinds: [string, string][] = [["primary", "Primary and official sources"], ["secondary", "Industry and secondary sources"], ["vendor", "Vendor material"], ["practice", "The practice's own records"]];
  const used = new Map<string, number>();
  [...u.categories.map((c) => c.sources), ...u.metrics.map((m) => m.sources)].forEach((ss) => list(ss).forEach((s) => used.set(s, (used.get(s) || 0) + 1)));
  return `<h1>Sources</h1><p class="lead">Where the framework's rules and benchmarks come from. Primary sources are government or standards bodies; secondary sources are industry surveys and professional associations.</p>
    ${kinds.map(([k, label]) => { const ss = u.sources.filter((s) => (s.kind || "secondary") === k); return ss.length ? block(label, table([{ h: "Source" }, { h: "Publisher", w: "22%" }, { h: "Year", w: "8%" }, { h: "Cited", num: true, w: "8%" }], ss.map((s) => [`${extLink(s.url, s.title)}${s.note ? `<div class="note">${rich(s.note)}</div>` : ""}`, esc(s.publisher || ""), esc(s.year || ""), String(used.get(s.slug) || 0)])), `${ss.length}`) : ""; }).join("")}`;
}

const stars = (n: unknown) => { const v = Math.max(0, Math.min(5, Number(n) || 0)); return v ? `<span class="score" title="${v} of 5">${"●".repeat(v)}${"○".repeat(5 - v)}</span>` : ""; };
async function pageLibrary(): Promise<string> {
  const lib = await library();
  if (!lib.items.length) return `<h1>Purchased library review</h1>${empty("The review has not been loaded yet.")}`;
  const sum = (k: keyof Item) => lib.items.reduce((a, x) => a + (Number(x[k]) || 0), 0);
  const checked = sum("claims_checked"); const m = lib.meta?.["library:summary"] || {};
  const bundles = [...new Set(lib.items.map((x) => x.bundle || ""))];
  const isNews = (x: Item) => x.doc_type === "Newsletter issue"; const news = lib.items.filter(isNews); const bought = lib.items.filter((x) => !isNews(x));
  const newsTitle = new Map(news.map((x) => [x.slug, x.title] as [string, string]));
  const newsClaims = lib.claims.filter((c) => newsTitle.has(c.item_slug) && c.verdict && c.verdict !== "not checked");
  return `<h1>Purchased library review</h1><p class="lead">${rich(m.lead || "Every document in the purchased CleanClaimRx library was read in full, summarized, and had its most consequential claims checked against primary sources.")}</p>
    <div class="tiles">${tile("Documents", String(bought.length), fmtInt(sum("pages")) + " pages")}${news.length ? tile("Newsletter issues", String(news.length), "free, read in full") : ""}${tile("Claims checked", String(checked))}${tile("Supported", String(sum("claims_supported")), checked ? Math.round(100 * sum("claims_supported") / checked) + "%" : "")}${tile("Partly right", String(sum("claims_partly")))}${tile("Contradicted or outdated", String(sum("claims_contradicted") + sum("claims_outdated")), "", "warn")}${tile("Could not verify", String(sum("claims_unverifiable")))}</div>
    ${m.verdict ? block("Bottom line", ul(m.verdict, "bullets")) : ""}
    ${newsClaims.length ? block("What the free newsletter reported, checked against the source", table([{ h: "Issue", w: "17%" }, { h: "What it said" }, { h: "Verdict", w: "12%" }, { h: "What is actually true" }],
      newsClaims.map((c) => [`<a href="#upo/library/${esc(c.item_slug)}">${esc((newsTitle.get(c.item_slug) || "").split(":")[0])}</a>`, rich(c.claim), verdictChip(c.verdict), `${rich(c.correct_statement)}${c.practice_impact && c.practice_impact !== "little" ? `<div class="note"><strong>For this practice:</strong> ${rich(c.practice_impact)}</div>` : ""}`]))) : ""}
    ${bundles.map((b) => block(b || "Other", table([{ h: "Document" }, { h: "Pages", num: true, w: "7%" }, { h: "Quality", w: "10%" }, { h: "Fit for this practice", w: "12%" }, { h: "Claims: ok / partly / wrong / unverified", w: "22%" }],
      lib.items.filter((x) => (x.bundle || "") === b).map((x) => [`<a href="#upo/library/${esc(x.slug)}">${esc(x.title)}</a>${x.verdict ? `<div class="note">${rich(x.verdict)}</div>` : ""}`, fmtInt(x.pages), stars(x.quality_score), stars(x.practice_relevance_score), x.claims_checked ? `${x.claims_supported} / ${x.claims_partly} / ${x.claims_contradicted + x.claims_outdated} / ${x.claims_unverifiable}` : `<span class="dim">none checked</span>`])))).join("")}
    <p class="foot">The documents themselves stay in the practice's Drive. This page holds only the practice's own notes about them.</p>`;
}
async function pageLibraryItem(slug: string): Promise<string> {
  const lib = await library(); const x = lib.items.find((i) => i.slug === slug);
  if (!x) return `<h1>Not found</h1>${empty("There is no document with that name.")}`;
  const claims = lib.claims.filter((c) => c.item_slug === slug);
  const u = await universal(); const doms = list(x.domains).map((s) => u.domains.find((d) => d.slug === s)).filter(Boolean) as Domain[];
  return `${crumbs([["Purchased library review", "#upo/library"], [x.title]])}<h1>${esc(x.title)}</h1>
    <div class="chips">${tag(x.bundle, "soft")}${tag(x.doc_type, "soft")}${x.pages ? tag(x.pages + " pages", "soft") : ""}${x.list_price_usd ? tag(usd(x.list_price_usd) + " list", "soft") : ""}</div>
    <div class="tiles">${tile("Quality", (x.quality_score || "?") + " of 5")}${tile("Specificity", (x.specificity_score || "?") + " of 5")}${tile("Fit for this practice", (x.practice_relevance_score || "?") + " of 5")}${tile("Claims checked", String(x.claims_checked), `${x.claims_supported} supported`)}</div>
    ${x.summary ? block("What it covers", `<p>${rich(x.summary)}</p>${doms.length ? `<p class="note">Feeds: ${doms.map((d) => `<a class="chip soft" href="#upo/d/${esc(d.slug)}">${esc(d.name)}</a>`).join(" ")}</p>` : ""}`) : ""}
    <div class="two">${block("Worth adopting", ul(x.top_ideas, "bullets ok"))}${block("Problems found", ul(x.red_flags, "bullets bad"))}</div>
    ${claims.length ? block("Claims checked against primary sources", table([{ h: "What the document says" }, { h: "Verdict", w: "13%" }, { h: "What is actually true" }, { h: "Source", w: "16%" }],
      claims.map((c) => [`${rich(c.claim)}<div class="chips">${tag(c.kind, "soft")}${c.stakes ? tag(c.stakes + " stakes", "soft") : ""}</div>`, verdictChip(c.verdict), `${rich(c.correct_statement)}${c.practice_impact && c.practice_impact !== "little" ? `<div class="note"><strong>For this practice:</strong> ${rich(c.practice_impact)}</div>` : ""}`, extLink(c.source_url, c.source_title)]))) : ""}`;
}

export async function showUpo(parts: string[]): Promise<void> {
  const main = $("#main");
  const [, a, b] = parts;
  let html: string;
  if (!a) html = await pageHome();
  else if (a === "d" && b) html = await pageDomain(b);
  else if (a === "c" && b) html = await pageCategory(b);
  else if (a === "metrics") html = await pageMetrics();
  else if (a === "sources") html = await pageSources();
  else if (a === "library" && b) html = await pageLibraryItem(b);
  else if (a === "library") html = await pageLibrary();
  else html = await pageHome();
  main.innerHTML = html;
}

// the metric library filters redraw the list in place and keep the cursor in the search box
document.addEventListener("input", async (ev) => {
  const f = (ev.target as HTMLElement).closest("#metric-filter") as HTMLFormElement | null;
  if (!f) return;
  const el = ev.target as HTMLInputElement; const pos = el.selectionStart;
  metricFilter = { q: (f.elements.namedItem("q") as HTMLInputElement).value, domain: (f.elements.namedItem("domain") as HTMLSelectElement).value };
  $("#main").innerHTML = await pageMetrics();
  if (el.name === "q") { const n = $("#metric-filter input[name=q]") as HTMLInputElement; n.focus(); try { n.setSelectionRange(pos, pos); } catch { /* not a text field */ } }
});
document.addEventListener("submit", (ev) => { if ((ev.target as HTMLElement).id === "metric-filter") ev.preventDefault(); });
