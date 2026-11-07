// The browser side of the ehpa Practice Database app. Signs William in with Neon Auth (Managed Better Auth), keeps a short-lived
// JWT for the Function's /api routes, renders every view from the generic {title, note, sections[]} shape the server returns, and
// signs out after SESSION_IDLE_MINUTES without activity. No data is embedded in the page; everything is fetched after sign-in.
import { createAuthClient } from "@neon/auth";

type Section = { heading: string; note?: string; columns: string[]; rows: unknown[][]; kinds?: string[] };
type View = { title: string; note?: string; sections: Section[]; generated_at: string };

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

function render(v: View) {
  const main = $("#main");
  const parts = [`<h1>${esc(v.title)}</h1>`];
  if (v.note) parts.push(`<p class="lead">${esc(v.note)}</p>`);
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
