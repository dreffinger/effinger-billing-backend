// Learn: the learning modules stored in upo.learning_modules. Each module is a list of sections made of content blocks
// (paragraphs, lists, steps, tables, formulas, callouts, code, quick questions) that core.renderBlock draws.
// Pages: #learn (the modules) and #learn/<module>.
import { $, esc, cached, rich, renderBlock, tile, tag, crumbs, empty, extLink, type Block } from "./core";

type Module = { slug: string; ord: number; title: string; audience?: string; summary?: string; minutes?: number; artifact_url?: string; body: { sections?: { heading: string; blocks?: Block[] }[]; takeaways?: string[] } };
const modules = async () => (await cached<{ modules: Module[] }>("/api/upo/learn")).modules;

export async function learnNav(): Promise<[string, string][]> {
  try { return [["learn", "All modules"], ...(await modules()).map((m) => ["learn/" + m.slug, m.title] as [string, string])]; } catch { return [["learn", "All modules"]]; }
}

const slugify = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export async function showLearn(parts: string[]): Promise<void> {
  const ms = await modules(); const main = $("#main");
  const m = parts[1] ? ms.find((x) => x.slug === parts[1]) : null;
  if (!m) {
    main.innerHTML = `<h1>Learn</h1><p class="lead">Short courses written for this practice's owner: how the money moves, how a buyer would value the practice, how to grow it, and how the system behind these pages works.</p>
      ${ms.length ? `<div class="cards">${ms.map((x) => `<a class="card" href="#learn/${esc(x.slug)}"><div class="card-k">${String(x.ord).padStart(2, "0")}</div><h3>${esc(x.title)}</h3><p>${esc(x.summary || "")}</p><div class="card-f">${x.minutes ? x.minutes + " minute read" : ""}${x.audience ? " · " + esc(x.audience) : ""}</div></a>`).join("")}</div>` : empty("The learning modules have not been loaded yet.")}`;
    return;
  }
  const secs = m.body?.sections || [];
  main.innerHTML = `${crumbs([["Learn", "#learn"], [m.title]])}<h1>${esc(m.title)}</h1>${m.summary ? `<p class="lead">${rich(m.summary)}</p>` : ""}
    ${m.audience ? `<div class="chips">${tag("Written for: " + m.audience, "soft")}</div>` : ""}
    <div class="tiles">${m.minutes ? tile("Reading time", m.minutes + " min") : ""}${tile("Sections", String(secs.length))}</div>
    ${m.artifact_url ? `<p class="note">Also published as a standalone page: ${extLink(m.artifact_url, "open the artifact")}</p>` : ""}
    <div class="reading"><nav class="toc" aria-label="In this module"><strong>In this module</strong><ol>${secs.map((s) => `<li><a href="#learn/${esc(m.slug)}" data-jump="${esc(slugify(s.heading))}">${esc(s.heading)}</a></li>`).join("")}</ol></nav>
    <div class="prose">${secs.map((s, i) => `<section class="block" id="sec-${esc(slugify(s.heading))}"><header><h2>${esc(s.heading)}</h2></header>${(s.blocks || []).map((b, j) => renderBlock(b, `${m.slug}-${i}-${j}`)).join("")}</section>`).join("")}
    ${m.body?.takeaways?.length ? `<section class="block"><header><h2>Take away</h2></header><ul class="bullets ok">${m.body.takeaways.map((t) => `<li>${rich(t)}</li>`).join("")}</ul></section>` : ""}</div></div>`;
}
// table-of-contents links scroll inside the module instead of changing the route
document.addEventListener("click", (ev) => {
  const a = (ev.target as HTMLElement).closest("a[data-jump]") as HTMLElement | null;
  if (!a) return;
  ev.preventDefault();
  document.getElementById("sec-" + a.dataset.jump)?.scrollIntoView({ behavior: "smooth", block: "start" });
});
