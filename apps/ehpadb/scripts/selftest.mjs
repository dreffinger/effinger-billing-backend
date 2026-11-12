// PLAIN ENGLISH (offline self-test of the ehpa applications Function, 11/12/2026). Builds src/index.ts exactly as it is deployed,
// with three stand-ins - Postgres (pg), Neon's function hooks (@neon/functions) and the Auth server's key set (jose's remote JWKS) -
// and asks it every question a browser can ask. It proves:
//   1. every /api route the app registers (the old ones and the new pdb / ccm / links routes, GET and POST) answers 401 with no
//      session, 401 for a token signed by another key, 403 for a signed-in account whose email is not allowed and 403 for an
//      allowed address whose owner never confirmed it - and in all four cases no data query runs and nothing is logged;
//   2. for the allowed, confirmed account every route runs, and every request is written to ops.app_access_log with its route;
//   3. every statement a GET route sends is a SELECT (the access-log INSERT aside) - the CCM and Practice Database routes write nothing;
//   4. the public answers ("/", /theme.js, /app.js, /health) carry no patient data and no claude.ai page address, and every answer
//      carries the Content-Security-Policy and no-store headers;
//   5. the color schemes: "/" is Light before any script runs, offers the five ehpa schemes with the Practice Database page's exact
//      tokens (tools/db/practice_db_page.html), and /theme.js applies a remembered pick, ignores an unknown one and survives a browser
//      that refuses localStorage.
// Never touches: Neon, the Auth server, the network (fetch is replaced by a refusal; the database address is made up). No patient
// data: the one "patient" below is invented here. Writes only src/generated/client-bundle.ts (the bundle it checks; git-ignored).
// Run: node scripts/selftest.mjs   (from apps/ehpadb; exit 1 on any failure) - tools/selftest/test_ehpadb_app.py runs it too.
import { build } from "esbuild";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import vm from "node:vm";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repo = resolve(root, "..", "..");
const FAILS = []; let RAN = 0;
const check = (name, cond, extra = "") => { RAN++; console.log((cond ? "ok   " : "FAIL ") + name + (cond ? "" : "  -> " + String(extra).slice(0, 500))); if (!cond) FAILS.push(name); };

// ---- no network: any fetch is refused (the remote key set is replaced below; pg is a stand-in) ------------------------------------
globalThis.fetch = async () => { throw new Error("the self-test must not use the network"); };
// the Function's own refusal notes ("jwt rejected", "forbidden email" ...) are expected here by the dozen; count them instead
let refusalNotes = 0; console.warn = () => { refusalNotes++; };

// ---- the browser bundle, built the way npm run build:client builds it ---------------------------------------------------------------
const b = spawnSync(process.execPath, [resolve(root, "scripts/bundle-client.mjs")], { cwd: root, encoding: "utf8" });
check("the browser bundle builds (scripts/bundle-client.mjs)", b.status === 0, b.stderr || b.stdout);

// ---- the stand-ins ---------------------------------------------------------------------------------------------------------------------
const INVENTED = "Zyxwv Testpatient";   // an invented name: it must never leave a route that is not behind the gate
const USERS = { "u-owner": ["owner@invalid.test", true], "u-stranger": ["stranger@invalid.test", true], "u-unconfirmed": ["late@invalid.test", false] };
globalThis.__SELFTEST__ = { sql: [], users: USERS, invented: INVENTED, pending: [] };
const PG_STUB = `export class Pool { constructor() {}
  async query(q, params = []) {
    const S = globalThis.__SELFTEST__; const text = typeof q === "string" ? q : q.text; S.sql.push({ text, params });
    if (/from neon_auth\\."user"/.test(text)) { const u = S.users[params[0]]; return { rows: u ? [{ email: u[0], verified: u[1] }] : [], fields: [] }; }
    if (/^\\s*insert into ops\\.app_access_log/i.test(text)) return { rows: [], fields: [], rowCount: 1 };
    if (/^\\s*update /i.test(text)) return { rows: [{ id: params[1], status: params[2] }], fields: [], rowCount: 1 };
    if (typeof q === "object" && q.rowMode === "array") return { rows: [], fields: [] };
    // every other question gets one answer document holding the invented patient, so a leak would show
    return { rows: [{ doc: { note: { note_id: "pat1_2026-10", patient_name: S.invented }, patients: [{ name: S.invented }], months: [], totals: {}, rows: [], runs: [] } }], fields: [] };
  } }`;
const FN_STUB = `export function attachDatabasePool() {} export function waitUntil(p) { globalThis.__SELFTEST__.pending.push(p); }`;
const josePath = resolve(root, "node_modules/jose/dist/webapi/index.js");
const JOSE_SHIM = `export * from ${JSON.stringify(josePath)}; import { createLocalJWKSet } from ${JSON.stringify(josePath)};
  export function createRemoteJWKSet() { return createLocalJWKSet(globalThis.__SELFTEST__.jwks); }`;
const stubs = { name: "stand-ins", setup(bd) {
  bd.onResolve({ filter: /^(pg|@neon\/functions|jose)$/ }, (a) => ({ path: a.path, namespace: "stub" }));
  bd.onLoad({ filter: /.*/, namespace: "stub" }, (a) => ({ contents: a.path === "pg" ? PG_STUB : a.path === "jose" ? JOSE_SHIM : FN_STUB, loader: "js", resolveDir: root }));
} };

// ---- the environment the Function reads at start ------------------------------------------------------------------------------
Object.assign(process.env, { DATABASE_URL: "postgres://selftest:selftest@db.invalid/neondb", NEON_AUTH_BASE_URL: "https://auth.invalid/neondb/auth",
  // the allowed list in mixed case: the Function compares it case-blind. late@ is allowed but never confirmed its address.
  NEON_AUTH_JWKS_URL: "https://auth.invalid/neondb/auth/.well-known/jwks.json", ALLOWED_EMAILS: "Owner@invalid.test, late@invalid.test", SESSION_IDLE_MINUTES: "30",
  NEON_BRANCH: "production", TEST_UNVERIFIED_EMAILS: "late@invalid.test" });   // ignored on the production branch, as it must be
const jose = await import(pathToFileURL(josePath).href);
const { publicKey, privateKey } = await jose.generateKeyPair("ES256");
const { privateKey: otherKey } = await jose.generateKeyPair("ES256");
globalThis.__SELFTEST__.jwks = { keys: [{ ...(await jose.exportJWK(publicKey)), kid: "k1", alg: "ES256" }] };
const token = (sub, email, key = privateKey) => new jose.SignJWT({ email }).setProtectedHeader({ alg: "ES256", kid: "k1" }).setIssuer("https://auth.invalid").setSubject(sub).setIssuedAt().setExpirationTime("15m").sign(key);

const out = await build({ entryPoints: [resolve(root, "src/index.ts")], bundle: true, platform: "node", format: "esm", write: false, plugins: [stubs], logLevel: "silent" });
const app = (await import("data:text/javascript;base64," + Buffer.from(out.outputFiles[0].text).toString("base64"))).default;

const ask = async (method, path, auth, body) => {
  const S = globalThis.__SELFTEST__; const before = S.sql.length;
  const headers = auth ? { authorization: "Bearer " + auth } : {};
  if (body) headers["content-type"] = "application/json";
  const res = await app.fetch(new Request("http://app.invalid" + path, { method, headers, body: body ? JSON.stringify(body) : undefined }));
  await Promise.all(S.pending.splice(0));
  const text = await res.text();
  return { status: res.status, text, headers: res.headers, sql: S.sql.slice(before) };
};

// ---- 1-3. every /api route, under every kind of caller ---------------------------------------------------------------------------
const SAMPLE = { stamp: "20261112T0119Z", id: "pat1_2026-10", collection: "billing_runs", month: "2026-10", chart: "pat1", code: "ehpa", name: "overview" };
const routes = [...new Map(app.routes.filter((r) => r.path.startsWith("/api/") && r.method !== "ALL").map((r) => [r.method + " " + r.path, r])).values()];
const paths = routes.map((r) => r.path);
for (const want of ["/api/links", "/api/pdb/overview", "/api/pdb/feed", "/api/pdb/runs", "/api/pdb/run/:stamp", "/api/pdb/era", "/api/pdb/era/:stamp", "/api/pdb/approvals", "/api/pdb/mirror",
  "/api/pdb/data", "/api/pdb/data/:collection", "/api/pdb/doc/:collection/:id", "/api/ccm/summary", "/api/ccm/month/:month", "/api/ccm/note/:id", "/api/ccm/patients", "/api/ccm/patient/:chart", "/api/ccm/signed"])
  check("route registered: " + want, paths.includes(want));
const owner = await token("u-owner", "owner@invalid.test"), stranger = await token("u-stranger", "stranger@invalid.test");
const unconfirmed = await token("u-unconfirmed", "late@invalid.test"), forged = await token("u-owner", "owner@invalid.test", otherKey);
let leaks = 0, writes = [];
for (const r of routes) {
  const path = r.path.replace(/:([a-z]+)/g, (_m, k) => SAMPLE[k] || "x");
  const body = r.method === "POST" ? { status: "done" } : undefined;
  const label = r.method + " " + r.path;
  const none = await ask(r.method, path, null, body);
  check(label + " - no session: 401, no query", none.status === 401 && none.sql.length === 0, none.status + " " + none.sql.length);
  const bad = await ask(r.method, path, forged, body);
  check(label + " - token from another key: 401, no query", bad.status === 401 && bad.sql.length === 0, bad.status + " " + bad.sql.length);
  const out1 = await ask(r.method, path, stranger, body);
  check(label + " - email not allowed: 403, only the account lookup ran", out1.status === 403 && out1.sql.every((s) => /neon_auth\."user"/.test(s.text)), out1.status + " " + out1.sql.map((s) => s.text.slice(0, 40)).join(" | "));
  const out2 = await ask(r.method, path, unconfirmed, body);
  check(label + " - allowed address never confirmed: 403, only the account lookup ran", out2.status === 403 && out2.sql.every((s) => /neon_auth\."user"/.test(s.text)), out2.status + " " + out2.sql.length);
  for (const x of [none, bad, out1, out2]) if (x.text.includes(INVENTED)) leaks++;
  const ok = await ask(r.method, path, owner, body);
  const log = ok.sql.find((s) => /^\s*insert into ops\.app_access_log/i.test(s.text));
  check(label + " - allowed and confirmed: runs and is logged with its route", ![401, 403].includes(ok.status) && log && log.params[0] === "owner@invalid.test" && log.params[2] === path, ok.status + " " + JSON.stringify(log?.params || null));
  for (const s of ok.sql) if (!/^\s*(select|with)\b/i.test(s.text) && !/^\s*insert into ops\.app_access_log/i.test(s.text)) writes.push(label + ": " + s.text.trim().slice(0, 60));
}
check("no answer to a caller without a good session or an allowed, confirmed email carried patient data", leaks === 0, leaks);
check("every statement a GET route sends is a SELECT (the one write is the owner's work-list POST)", writes.every((w) => w.startsWith("POST /api/upo/practice/:code/worklist/:id")), writes.join(" || "));
check("an unknown /api path is behind the gate too (401 without a session)", (await ask("GET", "/api/ccm/anything", null)).status === 401);
check("the Function noted every refusal in its log (" + refusalNotes + " notes)", refusalNotes >= routes.length * 3, refusalNotes);

// ---- 4. the public answers ---------------------------------------------------------------------------------------------------------
const PAGE_RE = /claude\.ai\/artifact|drive\.google\.com|trig_0/;
for (const p of ["/", "/theme.js", "/app.js", "/health"]) {
  const r = await ask("GET", p, null);
  check(p + " answers 200 with no query", r.status === 200 && r.sql.length === 0, r.status);
  check(p + " carries no patient data and no page address", !r.text.includes(INVENTED) && !PAGE_RE.test(r.text), (r.text.match(PAGE_RE) || [""])[0]);
  check(p + " carries the Content-Security-Policy and no-store", /script-src 'self'/.test(r.headers.get("content-security-policy") || "") && r.headers.get("cache-control") === "no-store");
}

// ---- 5. the color schemes ---------------------------------------------------------------------------------------------------------
const home = (await ask("GET", "/", null)).text;
check('"/" starts Light (data-ehpa="light" on <html>, Light tokens on :root)', /<html[^>]* data-ehpa="light"/.test(home) && /:root\{--bg:#ffffff;/.test(home));
check('"/" loads /theme.js in <head>, before the styles and the body', home.indexOf('<script src="/theme.js"></script>') > 0 && home.indexOf('<script src="/theme.js"></script>') < home.indexOf("<style>"));
const offered = [...home.matchAll(/data-pal="([a-z]+)"/g)].map((m) => m[1]);
check("the switcher offers the five ehpa schemes in the page's order", offered.join(",") === "lapis,midnight,navy,plum,light", offered.join(","));
const switcher = (home.match(/<div class="pal"[^>]*>([\s\S]*?)<\/div>/) || [])[1] || "";
check("Light is the pressed button before any script runs", /data-pal="light" aria-pressed="true"/.test(switcher) && (switcher.match(/aria-pressed="true"/g) || []).length === 1, switcher.slice(0, 200));
const norm = (s) => s.replace(/\s+/g, " ").trim();
const pdbPage = readFileSync(resolve(repo, "tools/db/practice_db_page.html"), "utf8");
for (const k of ["lapis", "midnight", "navy", "plum", "light"]) {
  const want = (pdbPage.match(new RegExp(`:root\\[data-ehpa="${k}"\\]\\{([^}]*)\\}`)) || [])[1];
  const got = (home.match(new RegExp(`:root\\[data-ehpa="${k}"\\]\\{([^}]*)\\}`)) || [])[1];
  check(`the ${k} tokens are the Practice Database page's`, want && got && norm(got).startsWith(norm(want)), norm(got || "").slice(0, 120));
}
const themeJs = (await ask("GET", "/theme.js", null)).text;
const runTheme = (stored, throws = false) => { const attrs = {}; const ctx = { document: { documentElement: { setAttribute: (k, v) => { attrs[k] = v; } } },
  localStorage: { getItem: (k) => { if (throws) throw new Error("blocked"); return k === "ehpa-palette" ? stored : null; } } }; vm.runInNewContext(themeJs, ctx); return attrs["data-ehpa"]; };
check("/theme.js: nothing remembered -> Light", runTheme(null) === "light");
check("/theme.js: a remembered pick is applied before the first paint", runTheme("plum") === "plum" && runTheme("lapis") === "lapis");
check("/theme.js: an unknown value -> Light", runTheme("<b>x</b>") === "light");
check("/theme.js: a browser that refuses localStorage -> Light", runTheme("navy", true) === "light");

console.log(`\nehpadb selftest: ${RAN} checks, ${FAILS.length} failed`);
process.exit(FAILS.length ? 1 : 0);
