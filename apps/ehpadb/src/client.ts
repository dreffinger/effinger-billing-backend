// The browser side of the ehpa Practice Database app. Signs William in with Neon Auth (Managed Better Auth), keeps a short-lived
// JWT for the Function's /api routes, renders every view from the generic {title, note, sections[]} shape the server returns, and
// signs out after SESSION_IDLE_MINUTES without activity. No data is embedded in the page; everything is fetched after sign-in.
import { createAuthClient } from "@neon/auth";

type Section = { heading: string; note?: string; columns: string[]; rows: unknown[][]; kinds?: string[] };
type Chart = { id: string; kind: "days" | "pairs"; title: string; note?: string; fill?: string; rows: Record<string, unknown>[] };
type View = { title: string; note?: string; charts?: Chart[]; sections: Section[]; generated_at: string };

const root = document.documentElement;
const AUTH_URL = root.getAttribute("data-auth-url") || "";
const IDLE_MINUTES = Number(root.getAttribute("data-idle-minutes") || "30");
const auth: any = createAuthClient(AUTH_URL);

const $ = <T extends HTMLElement = HTMLElement>(sel: string) => document.querySelector(sel) as T;
const esc = (s: unknown) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);

let tokenCache: { token: string; at: number } | null = null;
async function token(): Promise<string> {
  if (tokenCache && Date.now() - tokenCache.at < 9 * 60_000) return tokenCache.token;
  let t: string | undefined;
  if (typeof auth.token === "function") {
    const r = await auth.token();
    t = r?.data?.token;
  }
  if (!t) {
    const r = await fetch(AUTH_URL.replace(/\/$/, "") + "/token", { credentials: "include" });
    if (r.ok) t = (await r.json())?.token;
  }
  if (!t) throw new Error("Could not get a session token; sign in again.");
  tokenCache = { token: t, at: Date.now() };
  return t;
}

async function api<T>(path: string): Promise<T> {
  const r = await fetch(path, { headers: { authorization: "Bearer " + (await token()) }, cache: "no-store" });
  if (r.status === 401) { tokenCache = null; throw new Error("Session expired - sign in again."); }
  if (r.status === 403) throw new Error("This account is not allowed to see the practice data.");
  if (!r.ok) throw new Error("Server answered " + r.status + ": " + (await r.text()).slice(0, 200));
  return r.json();
}

function say(msg: string, kind: "ok" | "err" | "" = "") {
  const s = $("#status"); s.textContent = msg; s.className = "status " + kind;
}

// ---- idle sign-out (HIPAA asks for a session timeout) ------------------------------------------------------------------------
let idleTimer: number | undefined;
function armIdle() {
  if (idleTimer) window.clearTimeout(idleTimer);
  idleTimer = window.setTimeout(async () => { await signOut("Signed out after " + IDLE_MINUTES + " minutes without activity."); }, IDLE_MINUTES * 60_000);
}
["click", "keydown", "mousemove", "scroll", "touchstart"].forEach((ev) => addEventListener(ev, () => { if ($("#app").hidden === false) armIdle(); }, { passive: true }));

async function signOut(reason?: string) {
  try { await auth.signOut(); } catch {}
  tokenCache = null;
  showSignIn(reason);
}

// ---- screens ------------------------------------------------------------------------------------------------------------------
function showSignIn(msg?: string) {
  $("#app").hidden = true; $("#gate").hidden = false; $("#who").textContent = "";
  if (msg) say(msg, "");
}
async function showApp(user: { email?: string; name?: string }) {
  $("#gate").hidden = true; $("#app").hidden = false;
  $("#who").textContent = user.name || user.email || "";
  armIdle();
  await loadViews();
}

let views: string[] = [];
async function loadViews() {
  try {
    views = await api<string[]>("/api/views");
    const nav = $("#nav"); nav.innerHTML = views.map((v) => `<a href="#${esc(v)}" data-view="${esc(v)}">${esc(v.replace(/_/g, " "))}</a>`).join("");
    route();
  } catch (e: any) { say(e.message || String(e), "err"); }
}

async function route() {
  const name = (location.hash || "").replace("#", "") || views[0] || "overview";
  document.querySelectorAll("#nav a").forEach((a) => { a.toggleAttribute("aria-current", (a as HTMLElement).dataset.view === name); });
  const main = $("#main"); main.innerHTML = `<p class="note">Loading ${esc(name)}…</p>`;
  try {
    const v = await api<View>("/api/view/" + encodeURIComponent(name));
    render(v);
    say("");
  } catch (e: any) { main.innerHTML = ""; say(e.message || String(e), "err"); }
}
addEventListener("hashchange", route);

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
type DayRow = { date: string; visits: number; lines: number; dollars: number; patients: number; notin: number };
type NightRow = { date: string; run: { checked: number; changed: number; dollars: number; done?: string; at?: string } | null };
const num = (v: unknown) => Number(v || 0) || 0;
const fmt = (n: number) => n.toLocaleString("en-US");
const usd = (n: number) => "$" + Math.round(n).toLocaleString("en-US");
const isoDay = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);   // the viewer's calendar day
const fdate = (s: string) => { const d = new Date(s + "T12:00:00"); return isNaN(d.getTime()) ? s : d.toLocaleDateString("en-US", { month: "short", day: "numeric" }); };
const longDay = (s: string) => { const d = new Date(s + "T12:00:00"); return isNaN(d.getTime()) ? s : d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }); };
const daysAgo = (n: number) => { const d = new Date(); d.setDate(d.getDate() - n); return isoDay(d); };
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
function eachDay(lo: string, hi: string): string[] {
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

function drawDays(days: DayRow[], o: { fill: string; label: string; verb: string; what: string }): { svg: string; note: string } {
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

function drawPairs(nights: NightRow[]): { svg: string; note: string } {
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
        s += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="3" fill="${fill}"><title>${esc(tip)}</title></rect>`;
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

function render(v: View) {
  const main = $("#main");
  const parts = [`<h1>${esc(v.title)}</h1>`];
  if (v.note) parts.push(`<p class="lead">${esc(v.note)}</p>`);
  lastCharts = v.charts || [];
  if (lastCharts.length) parts.push(`<div id="charts">${chartsHtml(lastCharts)}</div>`);
  for (const s of v.sections) {
    const kinds = s.kinds || [];
    parts.push(`<section class="block"><header><h2>${esc(s.heading)}</h2>${s.note ? `<span class="note">${esc(s.note)}</span>` : ""}</header>`);
    if (!s.rows.length) { parts.push(`<p class="note">Nothing here.</p></section>`); continue; }
    parts.push(`<div class="tablewrap"><table><thead><tr>${s.columns.map((c, i) => `<th class="${kinds[i] === "money" || kinds[i] === "int" ? "num" : ""}">${esc(c.replace(/_/g, " "))}</th>`).join("")}</tr></thead><tbody>`);
    for (const r of s.rows) parts.push(`<tr>${r.map((c, i) => `<td class="${kinds[i] === "money" || kinds[i] === "int" ? "num" : ""}">${fmtCell(c, kinds[i])}</td>`).join("")}</tr>`);
    parts.push(`</tbody></table></div></section>`);
  }
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

// ---- sign-in / sign-up forms ----------------------------------------------------------------------------------------------------
$("#form-signin").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target as HTMLFormElement;
  const email = (f.elements.namedItem("email") as HTMLInputElement).value.trim();
  const password = (f.elements.namedItem("password") as HTMLInputElement).value;
  say("Signing in…");
  try {
    const { data, error } = await auth.signIn.email({ email, password });
    if (error) throw new Error(error.message || "Sign-in failed");
    await showApp(data?.user || { email });
  } catch (e: any) { say(e.message || String(e), "err"); }
});
$("#form-signup").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target as HTMLFormElement;
  const name = (f.elements.namedItem("name") as HTMLInputElement).value.trim();
  const email = (f.elements.namedItem("email") as HTMLInputElement).value.trim();
  const password = (f.elements.namedItem("password") as HTMLInputElement).value;
  say("Creating the account…");
  try {
    const { data, error } = await auth.signUp.email({ email, password, name });
    if (error) throw new Error(error.message || "Sign-up failed");
    await showApp(data?.user || { email, name });
  } catch (e: any) { say(e.message || String(e), "err"); }
});
$("#google").addEventListener("click", async () => {
  say("Opening Google sign-in…");
  try {
    const { error } = await auth.signIn.social({ provider: "google", callbackURL: location.origin + "/" });
    if (error) throw new Error(error.message || "Google sign-in failed");
  } catch (e: any) { say(e.message || String(e), "err"); }
});
$("#toggle-signup").addEventListener("click", () => { $("#form-signup").hidden = !$("#form-signup").hidden; $("#form-signin").hidden = !$("#form-signin").hidden; });
$("#signout").addEventListener("click", () => signOut("Signed out."));
$("#refresh").addEventListener("click", () => route());

// ---- boot: restore the session if the browser still has one ------------------------------------------------------------------
(async () => {
  try {
    const { data } = await auth.getSession();
    if (data?.user) await showApp(data.user); else showSignIn();
  } catch { showSignIn(); }
})();
