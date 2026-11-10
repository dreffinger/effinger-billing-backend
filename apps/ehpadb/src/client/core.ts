// Shared browser helpers for the ehpa applications: the Neon Auth client, the short-lived token every /api call carries, safe
// HTML building (every value from the server is escaped before it reaches the page), number and date formatting, and the small
// set of display pieces (chips, tiles, lists, tables, content blocks) the application pages are built from.
import { createAuthClient } from "@neon/auth";

const root = document.documentElement;
export const AUTH_URL = root.getAttribute("data-auth-url") || "";
export const IDLE_MINUTES = Number(root.getAttribute("data-idle-minutes") || "30");
export const PRACTICE = root.getAttribute("data-practice") || "ehpa";
export const auth: any = createAuthClient(AUTH_URL);

export const $ = <T extends HTMLElement = HTMLElement>(sel: string) => document.querySelector(sel) as T;
export const esc = (s: unknown) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);

// ---- the session token ----------------------------------------------------------------------------------------------------------
let tokenCache: { token: string; at: number } | null = null;
export function forgetToken() { tokenCache = null; }
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

async function answer<T>(r: Response): Promise<T> {
  if (r.status === 401) { tokenCache = null; throw new Error("Session expired - sign in again."); }
  if (r.status === 403) {   // the server says which gate refused: an address that is not on the list, or one that was never confirmed
    let why = "";
    try { why = String((await r.json())?.error || ""); } catch { /* not JSON */ }
    throw new Error(why ? why.charAt(0).toUpperCase() + why.slice(1) + (/[.!?]$/.test(why) ? "" : ".") : "This account is not allowed to see the practice data.");
  }
  if (!r.ok) {
    let msg = "";
    try { msg = (await r.json())?.error || ""; } catch { /* not JSON */ }
    throw new Error(msg || "Server answered " + r.status);
  }
  return r.json();
}
export async function api<T>(path: string): Promise<T> {
  return answer<T>(await fetch(path, { headers: { authorization: "Bearer " + (await token()) }, cache: "no-store" }));
}
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return answer<T>(await fetch(path, { method: "POST", headers: { authorization: "Bearer " + (await token()), "content-type": "application/json" }, body: JSON.stringify(body), cache: "no-store" }));
}

// one fetch per bundle per sign-in; Refresh clears them
const cache = new Map<string, Promise<unknown>>();
export function cached<T>(path: string): Promise<T> {
  if (!cache.has(path)) { const p = api<T>(path); p.catch(() => cache.delete(path)); cache.set(path, p); }
  return cache.get(path) as Promise<T>;
}
export function clearCache(path?: string) { if (path) cache.delete(path); else cache.clear(); }

export function say(msg: string, kind: "ok" | "err" | "" = "") {
  const s = $("#status"); s.textContent = msg; s.className = "status " + kind;
}

// ---- formatting -------------------------------------------------------------------------------------------------------------------
export const num = (v: unknown) => Number(v || 0) || 0;
export const fmtInt = (n: unknown) => (n === null || n === undefined || n === "" || isNaN(Number(n)) ? "" : Math.round(Number(n)).toLocaleString("en-US"));
export const usd = (n: unknown) => (n === null || n === undefined || n === "" || isNaN(Number(n)) ? "" : (Number(n) < 0 ? "-$" : "$") + Math.abs(Math.round(Number(n))).toLocaleString("en-US"));
export const usdK = (n: unknown) => { const v = Number(n); if (n === null || n === undefined || isNaN(v)) return ""; const a = Math.abs(v); return (v < 0 ? "-$" : "$") + (a >= 1_000_000 ? (a / 1_000_000).toFixed(2).replace(/\.?0+$/, "") + "M" : a >= 10_000 ? Math.round(a / 1000) + "K" : Math.round(a).toLocaleString("en-US")); };
export const range = (lo: unknown, hi: unknown, f: (n: unknown) => string = usdK) => { const a = f(lo), b = f(hi); return a && b && a !== b ? a + " to " + b : a || b; };
export const day = (s: unknown) => { if (!s) return ""; const d = new Date(String(s).length <= 10 ? String(s) + "T12:00:00" : String(s)); return isNaN(d.getTime()) ? String(s) : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }); };
export const plural = (n: unknown, one: string, many: string) => `${Number(n) || 0} ${Number(n) === 1 ? one : many}`;
export const list = (v: unknown): string[] => (Array.isArray(v) ? v.map((x) => (typeof x === "string" ? x : x && typeof x === "object" ? JSON.stringify(x) : String(x))) : []);

export function metricValue(m: { value?: unknown; value_text?: unknown; unit?: unknown }): string {
  if (m.value_text) return String(m.value_text);
  if (m.value === null || m.value === undefined || m.value === "") return "not measured";
  const v = Number(m.value); if (isNaN(v)) return String(m.value);
  const unit = String(m.unit || "");
  if (unit === "percent") return (Math.round(v * 10) / 10).toLocaleString("en-US") + "%";
  if (unit === "dollars") return usd(v);
  if (unit === "days") return (Math.round(v * 10) / 10).toLocaleString("en-US") + " days";
  if (unit === "ratio") return (Math.round(v * 100) / 100).toLocaleString("en-US");
  return v.toLocaleString("en-US");
}

// safe inline markup for text written in the seed files: **bold**, `code`, [label](https://...)
export function rich(s: unknown): string {
  let t = esc(s);
  t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
  t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_m, label, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`);
  return t;
}
export const safeUrl = (u: unknown) => (typeof u === "string" && /^https?:\/\//i.test(u) ? u : "");
export const extLink = (u: unknown, label?: unknown) => { const s = safeUrl(u); return s ? `<a href="${esc(s)}" target="_blank" rel="noopener noreferrer">${esc(label || s.replace(/^https?:\/\/(www\.)?/, "").slice(0, 70))}</a>` : esc(label || ""); };

// ---- display pieces ---------------------------------------------------------------------------------------------------------------
const STATUS_LABEL: Record<string, string> = { green: "On track", amber: "Watch", red: "Act", unknown: "No data yet", na: "Not applicable" };
const APPLIES_LABEL: Record<string, string> = { core: "Core", relevant: "Relevant", minor: "Minor", not_applicable: "Does not apply" };
export const statusChip = (s: unknown) => { const k = String(s || "unknown"); return `<span class="chip st-${esc(k)}"><i></i>${esc(STATUS_LABEL[k] || k)}</span>`; };
export const appliesChip = (s: unknown) => { const k = String(s || ""); return `<span class="chip ap-${esc(k)}">${esc(APPLIES_LABEL[k] || k)}</span>`; };
export const sevChip = (s: unknown) => { const k = String(s || "medium"); return `<span class="chip sev-${esc(k)}"><i></i>${esc(k.charAt(0).toUpperCase() + k.slice(1))}</span>`; };
export const tag = (s: unknown, cls = "") => (s === null || s === undefined || s === "" ? "" : `<span class="chip ${esc(cls)}">${esc(s)}</span>`);
export const VERDICT_LABEL: Record<string, string> = { SUPPORTED: "Supported", PARTLY: "Partly right", CONTRADICTED: "Contradicted", OUTDATED: "Outdated", UNVERIFIABLE: "Could not verify" };
export const verdictChip = (v: unknown) => { const k = String(v || ""); return `<span class="chip vd-${esc(k.toLowerCase())}"><i></i>${esc(VERDICT_LABEL[k] || k)}</span>`; };

export const ul = (items: unknown, cls = "") => { const a = list(items); return a.length ? `<ul class="${esc(cls)}">${a.map((x) => `<li>${rich(x)}</li>`).join("")}</ul>` : ""; };
export const block = (title: string, body: string, note = "", id = "") => (body ? `<section class="block"${id ? ` id="${esc(id)}"` : ""}><header><h2>${esc(title)}</h2>${note ? `<span class="note">${esc(note)}</span>` : ""}</header>${body}</section>` : "");
export const tile = (label: string, value: string, sub = "", cls = "") => `<div class="tile ${esc(cls)}"><div class="tile-l">${esc(label)}</div><div class="tile-v">${esc(value)}</div>${sub ? `<div class="tile-s">${esc(sub)}</div>` : ""}</div>`;
export const empty = (what: string) => `<p class="note">${esc(what)}</p>`;
export function table(cols: { h: string; num?: boolean; w?: string }[], rows: string[][], cls = ""): string {
  if (!rows.length) return empty("Nothing here yet.");
  return `<div class="tablewrap"><table class="${esc(cls)}"><thead><tr>${cols.map((c) => `<th class="${c.num ? "num" : ""}"${c.w ? ` style="width:${esc(c.w)}"` : ""}>${esc(c.h)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((cell, i) => `<td class="${cols[i]?.num ? "num" : ""}">${cell}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
export const crumbs = (parts: [string, string?][]) => `<nav class="crumbs" aria-label="Breadcrumb">${parts.map(([label, href]) => (href ? `<a href="${esc(href)}">${esc(label)}</a>` : `<span aria-current="page">${esc(label)}</span>`)).join('<span class="sep">/</span>')}</nav>`;

// content blocks: the learning modules (and any long-form page) are stored as {"sections":[{"heading","blocks":[...]}]}
export type Block = { type: string; [k: string]: any };
export function renderBlock(b: Block, key: string): string {
  switch (b.type) {
    case "p": return `<p>${rich(b.text)}</p>`;
    case "lead": return `<p class="lead">${rich(b.text)}</p>`;
    case "list": return ul(b.items, "bullets");
    case "steps": return `<ol class="steps">${list(b.items).map((x) => `<li>${rich(x)}</li>`).join("")}</ol>`;
    case "callout": return `<aside class="callout ${esc(b.tone || "note")}">${b.title ? `<strong>${esc(b.title)}</strong>` : ""}<p>${rich(b.text)}</p></aside>`;
    case "kv": return `<dl class="kv">${(Array.isArray(b.items) ? b.items : []).map((r: any) => `<div><dt>${rich(r?.[0])}</dt><dd>${rich(r?.[1])}</dd></div>`).join("")}</dl>`;
    case "formula": return `<div class="formula">${b.label ? `<div class="formula-l">${esc(b.label)}</div>` : ""}<div class="formula-e">${rich(b.expr)}</div>${b.example ? `<div class="note">${rich(b.example)}</div>` : ""}</div>`;
    case "code": return `<pre class="code" tabindex="0"><code>${esc(b.text)}</code></pre>${b.caption ? `<p class="note">${rich(b.caption)}</p>` : ""}`;
    case "table": {
      const cols = list(b.columns); const numeric = new Set<number>((Array.isArray(b.numeric) ? b.numeric : []).map(Number));
      const rows = (Array.isArray(b.rows) ? b.rows : []).map((r: any) => (Array.isArray(r) ? r : []).map((c: unknown) => rich(c)));
      return table(cols.map((h, i) => ({ h, num: numeric.has(i) })), rows) + (b.caption ? `<p class="note">${rich(b.caption)}</p>` : "");
    }
    case "quiz": {
      const choices = list(b.choices);
      return `<div class="quiz" data-quiz="${esc(key)}" data-answer="${esc(b.answer)}"><p class="quiz-q">${rich(b.q)}</p><div class="quiz-c">${choices.map((ch, i) => `<button type="button" class="btn" data-choice="${i}">${rich(ch)}</button>`).join("")}</div><p class="quiz-why note" hidden>${rich(b.why)}</p></div>`;
    }
    default: return "";
  }
}
// quizzes answer in place: the chosen button is marked, the right one is shown, the explanation appears
document.addEventListener("click", (ev) => {
  const b = (ev.target as HTMLElement).closest(".quiz button[data-choice]") as HTMLElement | null;
  if (!b) return;
  const q = b.closest(".quiz") as HTMLElement; const right = q.dataset.answer;
  q.querySelectorAll("button[data-choice]").forEach((x) => { const el = x as HTMLElement; el.classList.toggle("right", el.dataset.choice === right); el.classList.toggle("wrong", el === b && el.dataset.choice !== right); el.setAttribute("aria-pressed", String(el === b)); });
  const why = q.querySelector(".quiz-why") as HTMLElement; if (why) why.hidden = false;
});
