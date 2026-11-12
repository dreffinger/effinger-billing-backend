#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test, 11/12/2026): apps/ehpadb - the practice's Neon website (app.ehpa.dev), William's sign-in page over the
#   practice database, with the Practice Database page's views, the CCM notes and the header buttons added on 11/12/2026.
# Decides: nothing. It proves, reading the app's source files only (part 1) and then the app itself built with stand-ins (part 2):
#   1. the five ehpa color schemes are the Practice Database page's, token for token (tools/db/practice_db_page.html), Light is the
#      default, and the pick is applied before the first paint by a script from the site itself (/theme.js - the page's
#      Content-Security-Policy refuses inline scripts);
#   2. the header buttons go to the Practice Database page, the Insurance Refresh Board, the CCM Documentation Hub and the CCM Hub
#      Build, and no claude.ai page address is written into the public page or the browser script (they come from /api/links);
#   3. every route group (the old ones, links, the Practice Database views, the CCM notes) is registered AFTER the sign-in gate in
#      src/index.ts, and the new route files send only SELECT statements - the CCM section is read-only (signing stays on the hub);
#   4. part 2 runs apps/ehpadb/scripts/selftest.mjs (npm test): the real Function, built with stand-ins for Postgres and the Auth
#      server's keys, asked every /api question with no session, a forged token, a not-allowed email and an unconfirmed one (401/403,
#      no query, no data) and as the owner (runs, logged in ops.app_access_log with its route); the public answers carry no patient
#      data; /theme.js applies, ignores and survives what it should. Part 2 needs node and `npm ci` in apps/ehpadb; without them it
#      says SKIPPED and part 1 still decides.
# Never touches: Neon, the Auth server, AdvancedMD, the network (Python's sockets are shut; the node part replaces fetch, pg and the key
#   set). Nothing is deployed and no program under scripts/helpers, boards/ or core is started. No patient data: the one name the node
#   part uses is invented at run time.
# Run: python3 tools/selftest/test_ehpadb_app.py   (exit 1 on any failure)
import os, re, sys, json, shutil, subprocess
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(ROOT, "apps", "ehpadb")
FAILS = []; RAN = [0]
def check(name, cond, extra=""):
    RAN[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:600]))
    if not cond: FAILS.append(name)
def read(*p):
    path = os.path.join(*p)
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""
norm = lambda s: re.sub(r"\s+", " ", s or "").strip()

# ---- 1. the color schemes ---------------------------------------------------------------------------------------------------------
page = read(ROOT, "tools", "db", "practice_db_page.html")
pal = read(APP, "src", "palettes.ts")
check("the Practice Database page and src/palettes.ts are both there", page != "" and pal != "")
want = {k: norm(v) for k, v in re.findall(r':root\[data-ehpa="([a-z]+)"\]\{([^}]*)\}', page)[:5]}
got = {k: norm(v) for k, v in re.findall(r'^\s+([a-z]+): "([^"]*)",\s*$', pal.split("export const TOKENS", 1)[-1].split("};", 1)[0], re.M)}
check("the page offers the five ehpa schemes", sorted(want) == ["lapis", "light", "midnight", "navy", "plum"], sorted(want))
for k in ["lapis", "midnight", "navy", "plum", "light"]:
    check("the %s tokens are the Practice Database page's, word for word" % k, k in got and got.get(k) == want.get(k), (got.get(k) or "")[:160])
cas_page = dict((("light" if "data-ehpa" in sel else "dark"), norm(body)) for sel, body in re.findall(r'(:root(?:\[data-ehpa="light"\])?)\{(--cascade:[^}]*)\}', page))
check("the cascade chart's two purples are the page's (dark and Light)", 'CASCADE_DARK = "%s"' % cas_page.get("dark", "?") in pal and 'CASCADE_LIGHT = "%s"' % cas_page.get("light", "?") in pal, cas_page)
order = re.findall(r'\["([a-z]+)", "[A-Za-z]+", "#[0-9a-f]{6}", "#[0-9a-f]{6}"\]', pal)
page_order = re.findall(r'data-pal="([a-z]+)"', page)
check("the switcher's order and labels are the page's (Lapis, Midnight, Navy, Plum, Light)", order == page_order == ["lapis", "midnight", "navy", "plum", "light"], (order, page_order))
check('Light is the default (DEFAULT_PALETTE = "light")', re.search(r'DEFAULT_PALETTE = "light"', pal) is not None)
idx = read(APP, "src", "index.ts"); shell = read(APP, "src", "page.ts")
check("the remembered pick is applied before the first paint: /theme.js is served and loaded in <head> before the styles",
      'app.get("/theme.js"' in idx and shell.find('<script src="/theme.js"></script>') != -1 and shell.find('<script src="/theme.js"></script>') < shell.find("<style>"))
check("the Content-Security-Policy still refuses inline scripts (script-src 'self' only)", "script-src 'self';" in idx and "unsafe-inline'; img-src" in idx and "script-src 'self' 'unsafe-inline'" not in idx)

# ---- 2. the header buttons ----------------------------------------------------------------------------------------------------------
links = read(APP, "src", "links.ts")
for label, art in [("Practice Database", "QrLJpUcpFv3cFRB9xHfLyk"), ("Insurance Refresh Board", "NXKjnsha2dTyGHsiB4k6zg"), ("CCM Documentation Hub", "GSd9jcvXoBmxc9NkX2mWmR"), ("CCM Hub Build", "Fsc6yZZLxuumAiJG9FAp8K")]:
    head = links.split("export const HEADER_LINKS", 1)[-1].split("];", 1)[0]
    m = re.search(r'label: "%s", url: ([A-Z_]+)' % re.escape(label), head)
    const = m and re.search(r'export const %s = art\("([A-Za-z0-9]+)"\)' % m.group(1), links)
    check("header button: %s -> claude.ai/artifact/%s" % (label, art), bool(const) and const.group(1) == art)
client_src = "".join(read(APP, "src", f) for f in ["client.ts", "page.ts"]) + "".join(read(APP, "src", "client", f) for f in sorted(os.listdir(os.path.join(APP, "src", "client"))) if os.path.isdir(os.path.join(APP, "src", "client")))
check("no claude.ai page, Drive folder or scheduled-task id is written into the public page or the browser code", not re.search(r"claude\.ai/artifact|drive\.google\.com|trig_0", client_src), re.findall(r"claude\.ai/artifact/\w+|trig_\w+", client_src)[:3])
check("the browser asks /api/links for the buttons after sign-in", '"/api/links"' in read(APP, "src", "client.ts"))

# ---- 3. the gate comes first, and the new routes only read ------------------------------------------------------------------------
gate = idx.find('app.use("/api/*"')
check("the sign-in gate (app.use(\"/api/*\")) is in src/index.ts", gate > 0)
for reg in ['app.get("/api/me"', 'app.get("/api/view/:name"', "registerUpo(app", 'app.get("/api/links"', "registerPdb(app", "registerCcm(app"]:
    at = idx.find(reg)
    check("%s...) is registered after the gate" % reg, at > gate > 0, at)
check("no /api route is registered before the gate", not re.search(r'app\.(get|post|put|patch|delete)\("/api', idx[:gate]))
for f in ["pdb.ts", "ccm.ts"]:
    src = read(APP, "src", f)
    check("src/%s exists and registers its routes with app.get only" % f, src != "" and "app.post(" not in src and "app.put(" not in src and "app.delete(" not in src)
    sql = re.findall(r"`([^`]*)`", src)
    bad = [s[:60] for s in sql if re.search(r"\b(insert\s+into|update\s+\w+\s+set|delete\s+from|drop\s|alter\s|create\s|grant\s|truncate\s)", s, re.I)]
    check("src/%s sends no write: every SQL text in it is a SELECT" % f, not bad, bad)
ccm = read(APP, "src", "ccm.ts")
check("the CCM section reads the ccm.* views only (ccm.notes, ccm.signed_notes, ccm.patients, ccm.months)", set(re.findall(r"\bccm\.([a-z_]+)", ccm)) <= {"notes", "signed_notes", "patients", "months", "evidence", "faxes", "ts"}, set(re.findall(r"\bccm\.([a-z_]+)", ccm)))

# ---- 4. the app itself, built with stand-ins (node) -----------------------------------------------------------------------------------
node = shutil.which("node")
if not node or not os.path.isdir(os.path.join(APP, "node_modules", "esbuild")) or not os.path.isdir(os.path.join(APP, "node_modules", "jose")):
    print("SKIPPED part 2 (node, or apps/ehpadb/node_modules, is missing - run `npm ci` in apps/ehpadb to include it)")
else:
    env = dict(os.environ, HTTPS_PROXY="http://proxy.invalid:9", HTTP_PROXY="http://proxy.invalid:9", NO_PROXY="")
    for k in ("NEON_DATABASE_URL", "DATABASE_URL", "NEON_API_KEY"): env.pop(k, None)
    r = subprocess.run([node, os.path.join("scripts", "selftest.mjs")], cwd=APP, env=env, capture_output=True, text=True, timeout=600)
    lines = (r.stdout or "").splitlines()
    fails = [l for l in lines if l.startswith("FAIL ")]
    summary = next((l for l in reversed(lines) if l.startswith("ehpadb selftest:")), "")
    check("apps/ehpadb/scripts/selftest.mjs passes (%s)" % (summary or "no summary"), r.returncode == 0 and not fails and summary != "", "\n".join(fails[:12]) or (r.stderr or "")[-600:])

print("\ntest_ehpadb_app: %d checks, %d failed" % (RAN[0], len(FAILS)))
sys.exit(1 if FAILS else 0)
