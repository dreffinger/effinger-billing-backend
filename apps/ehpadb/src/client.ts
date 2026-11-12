// The browser side of the ehpa applications. One sign-in (Neon Auth, Managed Better Auth) opens a hub with the practice's
// applications: Universal Practice Optimization (the framework for any practice), Practice Optimization for this practice
// (the framework applied to it), the ehpa Practice Database (the dashboard this app started as, with the Practice Database
// page's views), the CCM notes (read-only) and Learn. Every page is drawn in the browser from JSON the Function returns after
// checking the session; nothing is embedded in the HTML the server sends - the header buttons to the practice's claude.ai pages
// included (/api/links). The color scheme switcher works before sign-in too (it holds no data).
// Routes are the part of the address after "#": home | upo/... | practice/... | db/<view> | ccm/... | learn/.... The
// dashboard's old links ("#overview", "#ar", ...) still work.
import { $, esc, auth, say, cached, clearCache, forgetToken, IDLE_MINUTES, PRACTICE, usdK, range, plural, safeUrl } from "./client/core";
import { showDashboard, dashboardViews, forgetDashboard } from "./client/dashboard";
import { showUpo, UPO_NAV } from "./client/upo";
import { showPractice, PRACTICE_NAV } from "./client/practice";
import { showLearn, learnNav } from "./client/learn";
import { dbNav, showDb, isRichView } from "./client/pdb";
import { showCcm, CCM_NAV } from "./client/ccm";
import { initPalette } from "./client/palette";

initPalette();

type Summary = { universal: { domains: number; categories: number; metrics: number; sources: number }; library: { items: number; claims: number }; learn: { modules: number };
  practice: { code: string; name: string; areas_red: number; areas_amber: number; areas_green: number; risks_high: number; work_open: number; projects_now: number; value_low: number | null; value_base: number | null; value_high: number | null } | null;
  database: { last_run_at: string | null; outstanding_total: number | null } };

const APPS: [string, string][] = [["home", "Home"], ["upo", "Universal Practice Optimization"], ["practice", "My practice"], ["db", "Practice Database"], ["ccm", "CCM notes"], ["learn", "Learn"]];
type CcmTotals = { totals?: { notes: number; ready: number; flagged: number; signed: number; patients: number } };

// ---- the header buttons: the practice's pages on claude.ai, asked for after sign-in so the public page names none of them ------
async function showLinks() {
  const box = $("#links");
  try {
    const links = await cached<{ key: string; label: string; url: string; note: string }[]>("/api/links");
    box.innerHTML = links.map((l) => { const u = safeUrl(l.url); return u ? `<a class="btn" href="${esc(u)}" target="_blank" rel="noopener noreferrer" title="${esc(l.note)}" data-link="${esc(l.key)}">${esc(l.label)} <span class="ext" aria-hidden="true">↗</span></a>` : ""; }).join("");
    box.hidden = !box.innerHTML;
  } catch { box.hidden = true; box.innerHTML = ""; }
}

// ---- idle sign-out (HIPAA asks for a session timeout) ------------------------------------------------------------------------
let idleTimer: number | undefined;
function armIdle() {
  if (idleTimer) window.clearTimeout(idleTimer);
  idleTimer = window.setTimeout(async () => { await signOut("Signed out after " + IDLE_MINUTES + " minutes without activity."); }, IDLE_MINUTES * 60_000);
}
["click", "keydown", "mousemove", "scroll", "touchstart"].forEach((ev) => addEventListener(ev, () => { if ($("#app").hidden === false) armIdle(); }, { passive: true }));

async function signOut(reason?: string) {
  try { await auth.signOut(); } catch { /* already signed out */ }
  forgetToken(); clearCache(); forgetDashboard();
  showSignIn(reason);
}

// ---- screens ------------------------------------------------------------------------------------------------------------------
function showSignIn(msg?: string) {
  $("#app").hidden = true; $("#gate").hidden = false; $("#who").textContent = ""; $("#appbar").hidden = true; $("#session").hidden = true; $("#main").innerHTML = "";
  $("#links").hidden = true; $("#links").innerHTML = "";
  if (msg) say(msg, "");
}
async function showApp(user: { email?: string; name?: string }) {
  $("#gate").hidden = true; $("#app").hidden = false; $("#appbar").hidden = false; $("#session").hidden = false;
  $("#who").textContent = user.name || user.email || "";
  $("#appbar").innerHTML = APPS.map(([k, label]) => `<a href="#${k}" data-app="${k}">${esc(label)}</a>`).join("");
  armIdle();
  showLinks();
  await route();
}

function rail(items: [string, string][], current: string) {
  const nav = $("#nav");
  nav.hidden = !items.length;
  nav.innerHTML = items.map(([href, label]) => `<a href="#${esc(href)}"${href === current ? ' aria-current="page"' : ""}>${esc(label)}</a>`).join("");
}

async function showHome() {
  rail([], "");
  const main = $("#main");
  let s: Summary | null = null, ccm: CcmTotals | null = null;
  [s, ccm] = await Promise.all([
    cached<Summary>("/api/upo/summary?practice=" + encodeURIComponent(PRACTICE)).catch(() => null),   // the hub still opens without the counts
    cached<CcmTotals>("/api/ccm/summary").catch(() => null),
  ]);
  const p = s?.practice, ct = ccm?.totals;
  const cards: [string, string, string, string, string][] = [
    ["upo", "Universal Practice Optimization", "The framework for running any medical practice as a business: what to manage, what good looks like, what to measure and what to do about it.",
      s ? `${plural(s.universal.domains, "domain", "domains")} · ${plural(s.universal.categories, "area", "areas")} · ${plural(s.universal.metrics, "metric", "metrics")}` : "", "Open the framework"],
    ["practice", p ? `Practice Optimization: ${p.name}` : "Practice Optimization: my practice", "The framework applied to this practice: scorecard, risk review, valuation, recommendations, projects and the work list.",
      p ? `${p.areas_red} ${p.areas_red === 1 ? "area needs" : "areas need"} action · ${plural(p.work_open, "open work-list item", "open work-list items")}${p.value_base ? " · indicative value " + usdK(p.value_base) + " (" + range(p.value_low, p.value_high) + ")" : ""}` : "", "Open my practice"],
    ["db", "ehpa Practice Database", "The billing dashboard and the Practice Database page's views: census inputs and the Claimocity feed, every billing run, ERA posting, approvals, receivables, denials, the nightly insurance cascade and every routine run.",
      s?.database?.outstanding_total ? `Open receivables ${usdK(s.database.outstanding_total)}${s.database.last_run_at ? " · last run " + new Date(s.database.last_run_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : ""}` : "", "Open the dashboard"],
    ["ccm", "CCM notes", "One late-entry note for every patient and month of chronic care management, read from the practice database. Read them here; sign them on the CCM Documentation Hub.",
      ct ? `${plural(ct.ready, "note", "notes")} ready to sign · ${plural(ct.flagged, "flagged", "flagged")} · ${plural(ct.signed, "signed", "signed")}` : "", "Open the CCM notes"],
  ];
  main.innerHTML = `<h1>Practice applications</h1><p class="lead">One sign-in for the practice's tools. Start with the framework, see how it applies to this practice, or go straight to the billing dashboard.</p>
    <div class="cards hub">${cards.map(([href, title, text, sub, cta], i) => `<a class="card big" href="#${href}"><div class="card-k">${i + 1}</div><h2>${esc(title)}</h2><p>${esc(text)}</p>${sub ? `<div class="card-f">${esc(sub)}</div>` : ""}<span class="cta">${esc(cta)} →</span></a>`).join("")}</div>
    <section class="block"><header><h2>Learn</h2><span class="note">${s ? plural(s.learn.modules, "module", "modules") : ""}</span></header><p>Short courses written for the owner: revenue cycle management as your own CFO, maximizing what the practice sells for, growing the practice, and the code and mechanics behind these pages.</p><p><a class="btn" href="#learn">Open the learning modules</a></p></section>`;
}

async function route() {
  const raw = (location.hash || "").replace(/^#\/?/, "");
  const parts = raw.split("/").filter(Boolean).map((x) => decodeURIComponent(x));
  let app = parts[0] || "home";
  const main = $("#main");
  try {
    // the dashboard's old links were "#<view>"
    if (!["home", "upo", "practice", "learn", "db", "ccm"].includes(app)) {
      const views = dbNav(await dashboardViews()).map(([k]) => k);
      if (views.includes(app)) { parts.unshift("db"); app = "db"; } else { app = "home"; }
    }
    document.querySelectorAll("#appbar a").forEach((a) => { a.toggleAttribute("aria-current", (a as HTMLElement).dataset.app === app); });
    if (app !== "home") main.innerHTML = `<p class="note">Loading…</p>`;
    if (app === "home") await showHome();
    else if (app === "upo") { rail(UPO_NAV, parts[1] === "metrics" || parts[1] === "sources" || parts[1] === "library" ? "upo/" + parts[1] : "upo"); await showUpo(parts); }
    else if (app === "practice") { rail(PRACTICE_NAV, parts[1] ? "practice/" + parts[1] : "practice"); await showPractice(parts); }
    else if (app === "learn") { rail(await learnNav(), parts[1] ? "learn/" + parts[1] : "learn"); await showLearn(parts); }
    else if (app === "ccm") { rail(CCM_NAV, parts[1] === "patients" || parts[1] === "p" ? "ccm/patients" : parts[1] === "signed" ? "ccm/signed" : "ccm"); await showCcm(parts); }
    else {
      // the Practice Database: the page's views (pdb.ts) first, then the generic views the server defines (views.ts)
      const nav = dbNav(await dashboardViews()); const keys = nav.map(([k]) => k);
      const view = keys.includes(parts[1]) ? parts[1] : "overview";
      rail(nav.map(([k, l]) => ["db/" + k, l] as [string, string]), "db/" + view);
      if (isRichView(view)) await showDb(view); else await showDashboard(view);
    }
    say("");
    document.title = (main.querySelector("h1")?.textContent || "Practice applications") + " · ehpa";
    window.scrollTo(0, 0);
  } catch (e: any) { main.innerHTML = ""; say(e.message || String(e), "err"); }
}
addEventListener("hashchange", route);

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
$("#refresh").addEventListener("click", () => { clearCache(); forgetDashboard(); route(); });

// ---- boot: restore the session if the browser still has one ------------------------------------------------------------------
(async () => {
  try {
    const { data } = await auth.getSession();
    if (data?.user) await showApp(data.user); else showSignIn();
  } catch { showSignIn(); }
})();
