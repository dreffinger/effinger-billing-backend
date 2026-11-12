// The ehpa Practice Database (the dashboard): every view the server defines in views.ts, rendered from the generic
// {title, note, charts[], sections[]} shape, plus the three first-look charts. This is the page the app opened on before the
// applications hub existed; it lives under "#db/<view>" (the old "#<view>" links still work). The Practice Database page's
// richer views (pdb.ts) draw their own content and add the generic tables of the same name underneath (genericInto), and use
// the chart drawing here (drawDays, drawPairs).
import { $, esc, api, say } from "./core";

type Section = { heading: string; note?: string; columns: string[]; rows: unknown[][]; kinds?: string[] };
type Chart = { id: string; kind: "days" | "pairs"; title: string; note?: string; fill?: string; rows: Record<string, unknown>[] };
type View = { title: string; note?: string; charts?: Chart[]; sections: Section[]; generated_at: string };

let views: string[] | null = null;
export async function dashboardViews(): Promise<string[]> {
  if (!views) views = await api<string[]>("/api/views");
  return views;
}
export function forgetDashboard() { views = null; }
export const isDashboardView = (name: string) => !!views && views.includes(name);

export async function showDashboard(name: string) {
  const main = $("#main");
  const all = await dashboardViews();
  const view = all.includes(name) ? name : all[0] || "overview";
  main.innerHTML = `<p class="note">Loading ${esc(view)}…</p>`;
  const v = await api<View>("/api/view/" + encodeURIComponent(view));
  render(v);
  return view;
}

// the generic view's charts and tables drawn into a box of a richer page (no title of its own); nothing when the view does not exist
export async function genericInto(name: string, box: HTMLElement | null, opts: { charts?: boolean } = {}) {
  if (!box) return;
  const all = await dashboardViews();
  if (!all.includes(name)) { box.innerHTML = ""; return; }
  const v = await api<View>("/api/view/" + encodeURIComponent(name));
  if (opts.charts !== false) lastCharts = v.charts || [];
  box.innerHTML = (opts.charts !== false && lastCharts.length ? `<div id="charts">${chartsHtml(lastCharts)}</div>` : "") + sectionsHtml(v.sections) +
    `<p class="foot">Generated ${esc(new Date(v.generated_at).toLocaleString("en-US"))} from the practice's Neon Postgres (ehpa.* views).</p>`;
}

function fmtCell(v: unknown, kind?: string): string {
  if (v === null || v === undefined || v === "") return "<span class=dim>·</span>";
  if (kind === "money") { const n = Number(v); return isNaN(n) ? esc(v) : "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  if (kind === "int") { const n = Number(v); return isNaN(n) ? esc(v) : n.toLocaleString("en-US"); }
  if (kind === "when") { const d = new Date(String(v)); return isNaN(d.getTime()) ? esc(v) : d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); }
  if (Array.isArray(v)) return esc(v.join(", "));
  if (typeof v === "object") return "<code>" + esc(JSON.stringify(v)).slice(0, 400) + "</code>";
  return esc(v);
}

// ---- the three first-look charts (ported from the Practice Database artifact's feed view) ---------------------------------------
export type DayRow = { date: string; visits: number; lines: number; dollars: number; patients: number; notin: number };
export type NightRow = { date: string; run: { checked: number; changed: number; dollars: number; done?: string; at?: string } | null };
const num = (v: unknown) => Number(v || 0) || 0;
const fmt = (n: number) => n.toLocaleString("en-US");
const usd = (n: number) => "$" + Math.round(n).toLocaleString("en-US");
export const isoDay = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);   // the viewer's calendar day
export const fdate = (s: string) => { const d = new Date(s + "T12:00:00"); return isNaN(d.getTime()) ? s : d.toLocaleDateString("en-US", { month: "short", day: "numeric" }); };
export const longDay = (s: string) => { const d = new Date(s + "T12:00:00"); return isNaN(d.getTime()) ? s : d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }); };
export const daysAgo = (n: number) => { const d = new Date(); d.setDate(d.getDate() - n); return isoDay(d); };
const ls = { get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch {} } };
let win = ls.get("ehpa-win") || "week";
let lastCharts: Chart[] = [];

function windowRange(dates: string[]): [string, string] {
  const today = isoDay(new Date());
  if (win === "week") return [daysAgo(6), today];
  if (win === "month") return [daysAgo(29), today];
  const ds = dates.slice().sort();
  return [ds[0] || today, (ds[ds.length - 1] || today) > today ? ds[ds.length - 1] : today];
}
export function eachDay(lo: string, hi: string): string[] {
  const out: string[] = [];
  for (let d = new Date(lo + "T12:00:00"); isoDay(d) <= hi && out.length < 400; d.setDate(d.getDate() + 1)) out.push(isoDay(d));
  return out;
}
function daySeries(rows: Record<string, unknown>[]): DayRow[] {
  const by: Record<string, DayRow> = {};
  rows.forEach((r) => { by[String(r.date)] = { date: String(r.date), visits: num(r.visits), lines: num(r.lines), dollars: num(r.dollars), patients: num(r.patients), notin: num(r.notin) }; });
  const [lo, hi] = windowRange(Object.keys(by));
  return eachDay(lo, hi).map((k) => by[k] || { date: k, visits: 0, lines: 0, dollars: 0, patients: 0, notin: 0 });
}
function nightSeries(rows: Record<string, unknown>[]): NightRow[] {
  const by: Record<string, NightRow["run"]> = {};
  rows.forEach((r) => { by[String(r.date)] = { checked: num(r.checked), changed: num(r.changed), dollars: num(r.dollars), done: r.done ? String(r.done) : "", at: r.at ? String(r.at) : "" }; });
  const keys = Object.keys(by).sort(); const today = isoDay(new Date());
  if (!keys.length) return [];
  const wlo = windowRange(keys)[0]; const lo = keys[0] > wlo ? keys[0] : wlo; const hi = keys[keys.length - 1] > today ? keys[keys.length - 1] : today;
  return eachDay(lo, hi).map((k) => ({ date: k, run: by[k] || null }));
}

export function drawDays(days: DayRow[], o: { fill: string; label: string; verb: string; what: string }): { svg: string; note: string } {
  if (!days.length) return { svg: `<p class="note">No days in this window.</p>`, note: "" };
  const W = 960, H = 230, L = 38, R = 12, T = 18, B = 34, n = days.length;
  const max = Math.max(1, ...days.map((d) => d.visits + d.notin)); const step = (W - L - R) / n; const bw = Math.max(3, Math.min(26, step - 3));
  const ticks = [...new Set([0, Math.ceil(max / 2), max])]; const today = isoDay(new Date());
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.label)}">`;
  ticks.forEach((t) => { const y = T + (H - T - B) * (1 - t / max); s += `<line x1="${L}" x2="${W - R}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--line)"/><text x="${L - 8}" y="${(y + 4).toFixed(1)}" text-anchor="end" font-size="11" fill="var(--dim)" font-family="var(--mono)">${t}</text>`; });
  days.forEach((d, i) => {
    const x = L + i * step + (step - bw) / 2; const h = (H - T - B) * (d.visits / max); const hn = (H - T - B) * (d.notin / max); const y = T + (H - T - B) - h;
    const tip = `${longDay(d.date)}: ${fmt(d.visits)} ${o.verb} · ${fmt(d.lines)} lines · ${usd(d.dollars)} · ${fmt(d.patients)} patients${d.notin ? ` · ${fmt(d.notin)} not entered` : ""}`;
    s += `<rect x="${x.toFixed(1)}" y="${d.visits ? y.toFixed(1) : H - B - 2}" width="${bw.toFixed(1)}" height="${d.visits ? h.toFixed(1) : 2}" rx="3" fill="${d.visits ? `var(--${o.fill})` : "var(--line-strong)"}"${d.date === today ? ` stroke="var(--accent-2)" stroke-width="2"` : ""}><title>${esc(tip)}</title></rect>`;
    if (d.notin) s += `<rect x="${x.toFixed(1)}" y="${(y - hn).toFixed(1)}" width="${bw.toFixed(1)}" height="${hn.toFixed(1)}" rx="3" fill="var(--warn)"><title>${esc(tip)}</title></rect>`;
    const every = n > 14 ? Math.ceil(n / 10) : 1; if (i % every === 0 || i === n - 1) s += `<text x="${(x + bw / 2).toFixed(1)}" y="${H - B + 16}" text-anchor="middle" font-size="11" fill="var(--dim)" font-family="var(--mono)">${esc(fdate(d.date))}</text>`;
  });
  s += `</svg>`;
  const busy = days.filter((d) => d.visits).length; const peak = days.reduce((a, b) => (b.visits > a.visits ? b : a), days[0]);
  return { svg: s, note: `${busy} of ${n} days ${o.what} · peak ${fmt(peak.visits)} on ${fdate(peak.date)} · amber = not entered` };
}

export function drawPairs(nights: NightRow[]): { svg: string; note: string } {
  if (!nights.length) return { svg: `<p class="note">No nightly cascade run is recorded yet.</p>`, note: "" };
  const W = 960, H = 240, L = 38, R = 12, T = 22, B = 34, ph = H - T - B, n = nights.length;
  const max = Math.max(1, ...nights.map((d) => (d.run ? Math.max(d.run.checked, d.run.changed) : 0))); const step = (W - L - R) / n; const bw = Math.max(3, Math.min(24, (step - 10) / 2)); const lab = step >= 40;
  const ticks = [...new Set([0, Math.ceil(max / 2), max])]; const today = isoDay(new Date());
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Nightly insurance cascade: pairs checked and visits changed per night">`;
  ticks.forEach((t) => { const y = T + ph * (1 - t / max); s += `<line x1="${L}" x2="${W - R}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--line)"/><text x="${L - 8}" y="${(y + 4).toFixed(1)}" text-anchor="end" font-size="11" fill="var(--dim)" font-family="var(--mono)">${t}</text>`; });
  nights.forEach((d, i) => {
    const cx = L + i * step + step / 2; const r = d.run;
    const tip = r ? `${longDay(d.date)}: ${fmt(r.checked)} checked · ${fmt(r.changed)} changed${r.dollars ? ` · ${usd(r.dollars)} re-sent` : ""}${r.done ? ` · ${r.done}` : ""}` : `${longDay(d.date)}: ${d.date === today ? "this morning's run is not recorded yet" : "no run recorded for this night"}`;
    if (r) {
      ([[r.checked, "var(--cascade)"], [r.changed, "var(--cascade-2)"]] as [number, string][]).forEach(([v, fill], j) => {
        const x = cx + (j ? 1 : -bw - 1); const h = v ? Math.max(2, (ph * v) / max) : 2; const y = T + ph - h;
        s += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="3" fill="${fill}" stroke="var(--cascade-edge)" stroke-width="1"><title>${esc(tip)}</title></rect>`;
        if (lab) s += `<text x="${(x + bw / 2).toFixed(1)}" y="${(y - 5).toFixed(1)}" text-anchor="middle" font-size="10.5" fill="var(--muted)" font-family="var(--mono)">${fmt(v)}</text>`;
      });
    } else s += `<rect x="${(cx - bw - 1).toFixed(1)}" y="${T + ph - 2}" width="${(2 * bw + 2).toFixed(1)}" height="2" rx="1" fill="var(--line-strong)"><title>${esc(tip)}</title></rect>`;
    const every = n > 14 ? Math.ceil(n / 10) : 1; if (i % every === 0 || i === n - 1) s += `<text x="${cx.toFixed(1)}" y="${H - B + 16}" text-anchor="middle" font-size="11" fill="var(--dim)" font-family="var(--mono)">${esc(fdate(d.date))}</text>`;
  });
  s += `</svg>`;
  const runs = nights.filter((d) => d.run).map((d) => d.run!);
  const last = runs[runs.length - 1];
  const note = runs.length ? `${runs.length} night${runs.length === 1 ? "" : "s"} · ${fmt(runs.reduce((a, r) => a + r.checked, 0))} checked · ${fmt(runs.reduce((a, r) => a + r.changed, 0))} changed · ${usd(runs.reduce((a, r) => a + r.dollars, 0))} re-sent · last run ${last.at ? new Date(last.at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : longDay(nights[nights.length - 1].date)}` : "No run recorded in this window.";
  return { svg: s, note };
}

function chartsHtml(charts: Chart[]): string {
  const seg = `<div class="seg" id="win" role="group" aria-label="Window">${[["week", "Past 7 days"], ["month", "Past 30 days"], ["all", "Everything on hand"]].map(([k, l]) => `<button type="button" data-win="${k}" aria-pressed="${win === k}">${l}</button>`).join("")}</div>`;
  const blocks = charts.map((c) => {
    const drawn = c.kind === "pairs" ? drawPairs(nightSeries(c.rows)) : drawDays(daySeries(c.rows), { fill: c.fill || "accent", label: c.title, verb: c.id === "pulled" ? "pulled in" : "entered", what: c.id === "pulled" ? "had visits pulled into AdvancedMD" : "carry feed encounters" });
    const legend = c.kind === "pairs" ? `<div class="legend"><span><i style="background:var(--cascade)"></i>Checked</span><span><i style="background:var(--cascade-2)"></i>Changed</span></div>` : "";
    return `<section class="block"><header><h2>${esc(c.title)}</h2><span class="note">${esc(drawn.note)}</span></header>${c.note ? `<p class="note" style="margin:0 0 8px">${esc(c.note)}</p>` : ""}${legend}<div class="chart">${drawn.svg}</div></section>`;
  });
  return `<div class="bar">${seg}<span class="note">The three first-look charts, as on the Practice Database page.</span></div>` + blocks.join("");
}

function sectionsHtml(sections: Section[]): string {
  const parts: string[] = [];
  for (const s of sections) {
    const kinds = s.kinds || [];
    parts.push(`<section class="block"><header><h2>${esc(s.heading)}</h2>${s.note ? `<span class="note">${esc(s.note)}</span>` : ""}</header>`);
    if (!s.rows.length) { parts.push(`<p class="note">Nothing here.</p></section>`); continue; }
    parts.push(`<div class="tablewrap"><table><thead><tr>${s.columns.map((c, i) => `<th class="${kinds[i] === "money" || kinds[i] === "int" ? "num" : ""}">${esc(c.replace(/_/g, " "))}</th>`).join("")}</tr></thead><tbody>`);
    for (const r of s.rows) parts.push(`<tr>${r.map((c, i) => `<td class="${kinds[i] === "money" || kinds[i] === "int" ? "num" : ""}">${fmtCell(c, kinds[i])}</td>`).join("")}</tr>`);
    parts.push(`</tbody></table></div></section>`);
  }
  return parts.join("");
}

function render(v: View) {
  const main = $("#main");
  const parts = [`<h1>${esc(v.title)}</h1>`];
  if (v.note) parts.push(`<p class="lead">${esc(v.note)}</p>`);
  lastCharts = v.charts || [];
  if (lastCharts.length) parts.push(`<div id="charts">${chartsHtml(lastCharts)}</div>`);
  parts.push(sectionsHtml(v.sections));
  parts.push(`<p class="foot">Generated ${esc(new Date(v.generated_at).toLocaleString("en-US"))} from the practice's Neon Postgres (ehpa.* views). Chart ids, dates of service, codes and dollars only.</p>`);
  main.innerHTML = parts.join("");
}
// the window toggle redraws the charts from the rows already on hand (no new request)
document.addEventListener("click", (ev) => {
  const b = (ev.target as HTMLElement).closest("#win button") as HTMLElement | null;
  if (!b || !b.dataset.win) return;
  win = b.dataset.win; ls.set("ehpa-win", win);
  const box = document.getElementById("charts"); if (box && lastCharts.length) box.innerHTML = chartsHtml(lastCharts);
});
