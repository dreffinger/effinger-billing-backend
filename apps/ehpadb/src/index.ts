// PLAIN ENGLISH: the ehpa applications, a Neon Function next to the practice's Postgres. It serves ONE page ("/", no data in
// it), two browser scripts (/theme.js - the remembered color scheme, applied before the first paint - and /app.js), and JSON
// (/api/*): the dashboard views read from ehpa.* (views.ts), the Practice Database page's views read from ehpa.*/ops.*/raw.*
// (pdb.ts), the CCM notes read from ccm.* (ccm.ts), the Universal Practice Optimization bundles read from upo.* (upo.ts), and
// the header buttons (links.ts). Every /api request must carry a Neon Auth JWT (Authorization: Bearer) that verifies against the
// branch's JWKS AND belong to an email in ALLOWED_EMAILS whose owner confirmed it; anything else is 401/403 before a query runs.
// Each allowed request is written to ops.app_access_log (who, what, when, status) - the access trail HIPAA asks for.
// The database role is the one Neon injects (DATABASE_URL, pooled); the code SELECTs from ehpa.*/ops.*/raw.*/ccm.*/upo.*,
// INSERTs into ops.app_access_log, and UPDATEs one thing: the status and note of a work-list row (upo.ts). The CCM routes carry
// patient names and birth dates, so they exist only behind that gate; nothing a patient owns is in "/", /theme.js or /app.js.
// The function's native URL is public by design; auth is the gate.
import { Hono } from "hono";
import { Pool } from "pg";
import { attachDatabasePool, waitUntil } from "@neon/functions";
import { createRemoteJWKSet, jwtVerify, decodeJwt } from "jose";
import { CLIENT_JS } from "./generated/client-bundle";
import { pageHtml } from "./page";
import { themeJs } from "./palettes";
import { VIEWS, runView } from "./views";
import { registerUpo } from "./upo";
import { registerPdb } from "./pdb";
import { registerCcm } from "./ccm";
import { HEADER_LINKS } from "./links";

const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 5 });
attachDatabasePool(pool);

const AUTH_BASE = process.env.NEON_AUTH_BASE_URL || "";
const JWKS_URL = process.env.NEON_AUTH_JWKS_URL || "";
const jwks = JWKS_URL ? createRemoteJWKSet(new URL(JWKS_URL)) : null;
const ALLOWED = (process.env.ALLOWED_EMAILS || "").toLowerCase().split(",").map((s) => s.trim()).filter(Boolean);
// Addresses that may pass without a confirmed email. For the automated browser test on a preview branch only: the list is ignored
// on the production branch, whatever the environment says.
const TEST_UNVERIFIED = ["production", "main"].includes(process.env.NEON_BRANCH || "") ? [] : (process.env.TEST_UNVERIFIED_EMAILS || "").toLowerCase().split(",").map((s) => s.trim()).filter(Boolean);
const IDLE = process.env.SESSION_IDLE_MINUTES || "30";
const PRACTICE = /^[a-z0-9]{2,20}$/.test(process.env.PRACTICE_CODE || "") ? (process.env.PRACTICE_CODE as string) : "ehpa";   // the practice "My practice" opens

type Vars = { user: { id: string; email: string } };
const app = new Hono<{ Variables: Vars }>();

// security headers on everything: the page may only talk to itself and to the Neon Auth origin
app.use("*", async (c, next) => {
  await next();
  const authOrigin = AUTH_BASE ? new URL(AUTH_BASE).origin : "";
  c.header("Content-Security-Policy", `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ${authOrigin}; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`);
  c.header("X-Content-Type-Options", "nosniff");
  c.header("Referrer-Policy", "no-referrer");
  c.header("Cache-Control", "no-store");
});

app.get("/health", (c) => c.text("ok"));
app.get("/", (c) => c.html(pageHtml(AUTH_BASE, IDLE, PRACTICE)));
app.get("/app.js", (c) => c.body(CLIENT_JS, 200, { "content-type": "text/javascript; charset=utf-8" }));
const THEME_JS = themeJs();
app.get("/theme.js", (c) => c.body(THEME_JS, 200, { "content-type": "text/javascript; charset=utf-8" }));

// ---- the gate: a verified Neon Auth JWT, an allowed email, and an account whose owner has confirmed that email --------------------------------------------------------------
// Who is asking. The account row is the authority for the address and for whether its owner has confirmed it. A token by itself only
// proves which address was typed at sign-up, and sign-up is open, so an account that never confirmed its address does not pass even
// when the address is on the allowed list. (Google sign-in arrives confirmed.) Answers are kept for a minute to spare the database.
type Account = { email: string; verified: boolean; at: number };
const accounts = new Map<string, Account>();
async function accountOf(payload: Record<string, unknown>): Promise<Account> {
  const sub = typeof payload.sub === "string" ? payload.sub : "";
  const claimed = typeof payload.email === "string" ? payload.email.toLowerCase() : "";
  const none: Account = { email: claimed, verified: false, at: Date.now() };
  if (!sub && !claimed) return none;
  const hit = sub ? accounts.get(sub) : undefined;
  if (hit && Date.now() - hit.at < 60_000) return hit;
  try {
    let r = sub ? await pool.query('select email, "emailVerified" as verified from neon_auth."user" where id = $1 limit 1', [sub]) : { rows: [] as any[] };
    if (!r.rows.length && claimed) r = await pool.query('select email, "emailVerified" as verified from neon_auth."user" where lower(email) = $1 limit 1', [claimed]);
    const row = r.rows[0];
    if (!row?.email) return none;
    const out: Account = { email: String(row.email).toLowerCase(), verified: row.verified === true, at: Date.now() };
    if (sub) accounts.set(sub, out);
    return out;
  } catch (e: any) {
    console.error("account lookup:", e?.message);
    return none;
  }
}

app.use("/api/*", async (c, next) => {
  const started = Date.now();
  const header = c.req.header("authorization") || "";
  if (!header.toLowerCase().startsWith("bearer ")) return c.json({ error: "sign in first" }, 401);
  const raw = header.slice(7).trim();
  if (!jwks) return c.json({ error: "auth is not configured on this branch" }, 503);
  let payload: Record<string, unknown>;
  try {
    const issuer = new URL(AUTH_BASE).origin;
    try {
      ({ payload } = await jwtVerify(raw, jwks, { issuer }));
    } catch (e: any) {
      // Neon's docs give the issuer as the Auth origin; accept the full base URL too, never an unverified token
      const claimed = String(decodeJwt(raw).iss || "");
      if (claimed && (claimed === AUTH_BASE || claimed === AUTH_BASE.replace(/\/$/, ""))) ({ payload } = await jwtVerify(raw, jwks, { issuer: claimed }));
      else throw e;
    }
  } catch (e: any) {
    console.warn("jwt rejected:", e?.code || e?.message || String(e));
    return c.json({ error: "session is not valid; sign in again" }, 401);
  }
  const account = await accountOf(payload); const email = account.email;
  if (!email || !ALLOWED.includes(email)) {
    console.warn("forbidden email", email || "(none)");
    return c.json({ error: "this account is not allowed to see the practice data" }, 403);
  }
  if (!account.verified && !TEST_UNVERIFIED.includes(email)) {
    console.warn("unconfirmed account refused", email);
    return c.json({ error: "this account's email address has not been confirmed, so it cannot open the practice data. Sign in with Google instead." }, 403);
  }
  c.set("user", { id: String(payload.sub || ""), email });
  await next();
  const status = c.res.status, route = c.req.path, ms = Date.now() - started;
  waitUntil(pool.query("insert into ops.app_access_log (user_email, user_id, route, status, ms) values ($1, $2, $3, $4, $5)", [email, String(payload.sub || ""), route, status, ms]).catch((err) => console.error("access log:", err?.message)));
});

app.get("/api/me", (c) => c.json(c.get("user")));
app.get("/api/views", (c) => c.json(Object.keys(VIEWS)));
app.get("/api/view/:name", async (c) => {
  const name = c.req.param("name");
  if (!/^[a-z_]{1,40}$/.test(name)) return c.json({ error: "no such view" }, 404);
  try {
    const v = await runView(pool, name);
    if (!v) return c.json({ error: "no such view" }, 404);
    return c.json(v);
  } catch (e: any) {
    console.error("view", name, e?.message);
    return c.json({ error: "the database answered with an error for this view" }, 500);
  }
});

registerUpo(app, pool, PRACTICE);

// the header buttons to the practice's claude.ai pages (links.ts) - served here, behind the gate, so "/" and /app.js name none
app.get("/api/links", (c) => c.json(HEADER_LINKS));
registerPdb(app, pool);   // the Practice Database page's views, from ehpa.* / ops.* / raw.* (source practice_db)
registerCcm(app, pool);   // the CCM notes, from ccm.* - patient names and birth dates, so only ever behind this gate

app.notFound((c) => c.text("not found", 404));
export default app;
