#!/usr/bin/env python3
# PLAIN ENGLISH (ehpa Practice Database on Neon - William 11/6/2026: "sign up with neon ... for ehpa permanent database ... back up all
#   practice databases such as ehpa database using this database ... have all the routines send the outputs and all to this database
#   as well to start collecting all the AMD charts and patient data and claims and ERAs").
# Decides: nothing about billing. It is the ONE door every routine and chat session uses to write to the practice's permanent Postgres
#   database on Neon (organization ehpa, project ehpa-database = steep-rain-79347575, AWS us-east-1, database neondb) and to read it back.
#   The claude.ai artifact databases stay what the boards read today; this database is the permanent copy of all of them plus every
#   run's output, so a question that crosses two boards (denials by payer against days in A/R) can finally be asked in SQL.
# Three layers (schema names): raw.* keeps every document exactly as the source wrote it (one row per collection/doc_id, JSON body,
#   sha256, upserted - never duplicated); ops.* keeps what each routine run did (ops.routine_runs) and what each load did (ops.load_log);
#   ehpa.* holds the typed tables and views built FROM raw.* by tools/db/neon_schema.sql (visits, claims, ERA lines, denials, deposits ...).
# Where the connection string comes from (first hit wins; it is a secret - never printed, never committed): the NEON_DATABASE_URL (or
#   DATABASE_URL) environment variable; --url-file <path>; <repo>/secrets/neon_database_url; /home/claude/unbilled/secrets/neon_database_url;
#   ~/.config/ehpa/neon_database_url. secrets/ is git-ignored in this repository.
# How it talks to Postgres (NEON_DB_MODE = auto | pg | http): psycopg 3 or pg8000 over the Postgres wire protocol (port 5432, TLS) when
#   one is importable and the port is open, else Neon's HTTPS SQL endpoint on port 443 (POST https://<endpoint>/sql with the
#   Neon-Connection-String header) - the same database, so a container whose egress policy blocks 5432 still writes. The PostgREST
#   "Data API" is NOT used (Neon excludes it from its HIPAA coverage).
# PHI rule: this database is the HIPAA store (BAA with Databricks on the Scale plan, hipaa=true on the project). Until the marker row
#   ops.settings('hipaa_enabled' = 'true') exists, every load command refuses to run unless --no-phi-check is given, so nothing with a
#   chart id in it lands in a project that is not yet flagged. Patient data never goes into table names, comments or this script's output.
# Usage (one plain command each; every one prints ONE line and exits 0, non-zero only on a real failure):
#   python3 tools/db/neon_db.py init                                   create the raw/ops/ehpa schemas and tables (idempotent) and apply tools/db/neon_schema.sql when present
#   python3 tools/db/neon_db.py egress-test                            which paths reach the database from here: TCP 5432, TLS 443, Postgres wire, HTTPS SQL (exit 3 = none)
#   python3 tools/db/neon_db.py load-writes --out <dir>                every writes_*.json tools/db/practice_db.py built (op/collection/doc_id/file_path) -> raw.documents source=practice_db
#   python3 tools/db/neon_db.py load-docs --src <dir> --source <slug>  every <collection>/<doc_id>.json an ArtifactData list wrote with out_dir -> raw.documents (the artifact's own database, by slug)
#   python3 tools/db/neon_db.py load-page --slug <slug> --url <url> --file <index.html> [--title <t>]   the page's HTML -> raw.artifact_pages
#   python3 tools/db/neon_db.py load-files --root <dir> --source repo [--prefix practices/ehpa/registers]  every *.json / *.jsonl / *.md under root -> raw.documents (collection = folder path, doc_id = file name)
#   python3 tools/db/neon_db.py run-log --routine <name> --stamp <stamp> --status <ok|partial|failed> --headline "<one line>" [--summary <json file>] [--started <ISO>] [--session <url>] [--commit <sha>]
#   python3 tools/db/neon_db.py set --key hipaa_enabled --value true   write an ops.settings row (the HIPAA marker, or anything else small)
#   python3 tools/db/neon_db.py health                                 rows per source/collection, newest document, last loads and runs
#   python3 tools/db/neon_db.py sql "select ..."                       one read-only statement, rows as JSON (for a quick look; writes are refused here)
# Options: --repo /home/claude/effinger-billing-backend  --ws /home/claude/unbilled  --by "<who is loading>" (default: $CLAUDE_SESSION_URL or the user name)  --dry (count, write nothing)
import os, sys, re, json, glob, hashlib, time, socket, ssl, datetime, getpass, urllib.request, urllib.parse

a = sys.argv[1:]
def opt(name, default=None): return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default
CMD = a[0] if a and not a[0].startswith("--") else "health"
REPO = opt("--repo", os.environ.get("EHPA_REPO") or ("/home/claude/effinger-billing-backend" if os.path.isdir("/home/claude") else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
WS = opt("--ws", os.environ.get("EHPA_WS") or "/home/claude/unbilled")
DRY = "--dry" in a
BY = opt("--by", os.environ.get("CLAUDE_SESSION_URL") or os.environ.get("GITHUB_RUN_ID") and ("github actions run " + os.environ["GITHUB_RUN_ID"]) or getpass.getuser())
NOW = datetime.datetime.now(datetime.timezone.utc)
def iso_now(): return NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
def sha(s): return hashlib.sha256(s.encode("utf-8") if isinstance(s, str) else s).hexdigest()
def dumps(x): return json.dumps(x, separators=(",", ":"), sort_keys=True, default=str)
STAMP_RE = re.compile(r"(\d{4})-?(\d{2})-?(\d{2})T(\d{2})(\d{2})Z")

# ---- the connection string ----------------------------------------------------------------------------------------------------------
def database_url():
    for k in ("NEON_DATABASE_URL", "DATABASE_URL"):
        v = (os.environ.get(k) or "").strip()
        if v.startswith("postgres"): return v
    for p in (opt("--url-file"), os.path.join(REPO, "secrets", "neon_database_url"), os.path.join(WS, "secrets", "neon_database_url"), os.path.expanduser("~/.config/ehpa/neon_database_url")):
        if p and os.path.isfile(p):
            v = open(p, encoding="utf-8").read().strip()
            if v.startswith("postgres"): return v
    sys.exit("neon_db: no connection string - set NEON_DATABASE_URL, or write it to %s (chmod 600; the file is git-ignored)" % os.path.join(REPO, "secrets", "neon_database_url"))

# ---- the three ways to reach Postgres -----------------------------------------------------------------------------------------------
class DB:
    """execute(sql, params) with %s placeholders in every mode; rows come back as lists"""
    def __init__(self, url, mode=None):
        self.url = url; self.mode = (mode or os.environ.get("NEON_DB_MODE") or "auto").lower(); self.kind = None; self.conn = None; self.tried = []
        u = urllib.parse.urlparse(url); self.host = u.hostname; self.port = u.port or 5432; self.user = urllib.parse.unquote(u.username or ""); self.password = urllib.parse.unquote(u.password or ""); self.dbname = (u.path or "/neondb").lstrip("/").split("?")[0] or "neondb"
    def connect(self):
        if self.mode in ("auto", "pg"):
            try:
                import psycopg
                self.conn = psycopg.connect(self.url, connect_timeout=20, autocommit=True); self.kind = "psycopg"; return self
            except ImportError: self.tried.append("psycopg not installed")
            except Exception as e:
                self.tried.append("psycopg: " + str(e)[:120])
                if self.mode == "pg": raise
            try:
                import pg8000.dbapi as pg
                self.conn = pg.connect(user=self.user, password=self.password, host=self.host, port=self.port, database=self.dbname, ssl_context=ssl.create_default_context(), timeout=20)
                self.conn.autocommit = True; self.kind = "pg8000"; return self
            except ImportError: self.tried.append("pg8000 not installed")
            except Exception as e:
                self.tried.append("pg8000: " + str(e)[:120])
                if self.mode == "pg": raise
        self.kind = "http"
        try: self.execute("select 1")
        except Exception as e: raise SystemExit("neon_db: no path to the database (%s; http: %s)" % ("; ".join(self.tried) or "wire protocol not tried", str(e)[:160]))
        return self
    def _http(self, sql, params):
        n = [0]
        def repl(m): n[0] += 1; return "$%d" % n[0]
        q = re.sub(r"%s", repl, sql)
        body = json.dumps({"query": q, "params": [p if (p is None or isinstance(p, (int, float, bool))) else str(p) for p in (params or [])]}).encode("utf-8")
        req = urllib.request.Request("https://%s/sql" % self.host, data=body, method="POST", headers={"Neon-Connection-String": self.url, "Content-Type": "application/json", "Neon-Array-Mode": "true", "Neon-Raw-Text-Output": "true"})
        with urllib.request.urlopen(req, timeout=120) as r: j = json.loads(r.read().decode("utf-8"))
        return j.get("rows") or [], j.get("rowCount")
    def execute(self, sql, params=None, fetch=None):
        if self.kind == "http":
            rows, rc = self._http(sql, params)
            return rows if (fetch or fetch is None) else rc
        cur = self.conn.cursor(); cur.execute(sql, params or None)
        try:
            if cur.description: return [list(r) for r in cur.fetchall()]
            return cur.rowcount
        finally: cur.close()
    def close(self):
        try:
            if self.conn: self.conn.close()
        except Exception: pass

def connect(): return DB(database_url()).connect()

# ---- schema -------------------------------------------------------------------------------------------------------------------------
DDL = """
create schema if not exists raw;
create schema if not exists ops;
create schema if not exists ehpa;
create table if not exists raw.documents (
  source text not null, collection text not null, doc_id text not null,
  body jsonb not null, body_sha256 text not null, version integer, written_at timestamptz, stamp text,
  loaded_at timestamptz not null default now(), first_loaded_at timestamptz not null default now(), loaded_by text,
  primary key (source, collection, doc_id));
create index if not exists documents_collection_written_idx on raw.documents (collection, written_at desc);
create index if not exists documents_stamp_idx on raw.documents (stamp);
create index if not exists documents_body_gin on raw.documents using gin (body jsonb_path_ops);
create table if not exists raw.artifact_pages (
  slug text not null, url text not null, title text, html text not null, html_sha256 text not null, bytes integer not null,
  saved_at timestamptz not null default now(), saved_by text, primary key (slug, html_sha256));
create table if not exists raw.files (
  source text not null, relpath text not null, text_body text not null, sha256 text not null, bytes integer not null,
  file_mtime timestamptz, loaded_at timestamptz not null default now(), loaded_by text, primary key (source, relpath));
create table if not exists ops.routine_runs (
  id bigserial primary key, routine text not null, stamp text not null, started_at timestamptz, finished_at timestamptz not null default now(),
  status text, headline text, summary jsonb, session_url text, commit_sha text, loaded_by text, unique (routine, stamp));
create table if not exists ops.load_log (
  id bigserial primary key, at timestamptz not null default now(), command text, source text, inserted integer default 0, updated integer default 0,
  unchanged integer default 0, bytes bigint default 0, duration_ms integer, loaded_by text, note text);
create table if not exists ops.settings (key text primary key, value text, updated_at timestamptz not null default now(), updated_by text);
create or replace view ops.v_health as
  select source, collection, count(*) as documents, max(written_at) as newest_written, max(loaded_at) as last_loaded, sum(length(body::text)) as bytes
  from raw.documents group by 1, 2 order by 1, 2;
"""
UPSERT_DOC = """insert into raw.documents (source, collection, doc_id, body, body_sha256, version, written_at, stamp, loaded_by)
values (%s, %s, %s, %s::jsonb, %s, %s, %s::timestamptz, %s, %s)
on conflict (source, collection, doc_id) do update set body = excluded.body, body_sha256 = excluded.body_sha256, version = excluded.version,
  written_at = excluded.written_at, stamp = excluded.stamp, loaded_at = now(), loaded_by = excluded.loaded_by
where raw.documents.body_sha256 <> excluded.body_sha256
returning (xmax = 0) as inserted"""

def hipaa_ok(db):
    if "--no-phi-check" in a: return True
    try: rows = db.execute("select value from ops.settings where key = 'hipaa_enabled'")
    except Exception: return False
    return bool(rows) and str(rows[0][0]).lower() == "true"
def require_hipaa(db, what):
    if not hipaa_ok(db): sys.exit("neon_db: REFUSED to load %s - the database is not marked HIPAA-ready (ops.settings hipaa_enabled). Enable HIPAA on the Neon project, then: python3 tools/db/neon_db.py set --key hipaa_enabled --value true  (or pass --no-phi-check for data that carries no chart ids or patients)" % what)

def written_at_of(body, doc_id):
    for k in ("_written", "at", "built", "finished", "ended", "saved_at", "updated", "updatedAt", "created", "createdAt"):
        v = body.get(k) if isinstance(body, dict) else None
        if isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}", v): return v
        if isinstance(v, (int, float)) and v > 1e12: return datetime.datetime.fromtimestamp(v / 1000, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    m = STAMP_RE.search(doc_id or "")
    return "%s-%s-%sT%s:%s:00Z" % m.groups() if m else None
def stamp_of(body, doc_id):
    s = body.get("stamp") if isinstance(body, dict) else None
    if isinstance(s, str) and STAMP_RE.search(s): return re.sub(r"[^0-9TZ]", "", STAMP_RE.search(s).group(0))
    m = STAMP_RE.search(doc_id or ""); return re.sub(r"[^0-9TZ]", "", m.group(0)) if m else None

def upsert_documents(db, source, items, command):
    """items: iterable of (collection, doc_id, body dict|list, version|None). Returns counts; writes ops.load_log."""
    t0 = time.perf_counter(); ins = upd = same = 0; nbytes = 0
    for coll, did, body, ver in items:
        s = dumps(body); h = sha(s); nbytes += len(s)
        if DRY: ins += 1; continue
        r = db.execute(UPSERT_DOC, [source, coll, did, s, h, ver, written_at_of(body, did), stamp_of(body, did), BY])   # one round trip: no row back = unchanged
        if not r: same += 1
        elif str(r[0][0]).lower() in ("true", "t", "1"): ins += 1
        else: upd += 1
    ms = int((time.perf_counter() - t0) * 1000)
    if not DRY: db.execute("insert into ops.load_log (command, source, inserted, updated, unchanged, bytes, duration_ms, loaded_by) values (%s, %s, %s, %s, %s, %s, %s, %s)", [command, source, ins, upd, same, nbytes, ms, BY])
    return ins, upd, same, nbytes, ms

def load_json(p):
    with open(p, encoding="utf-8") as fh: return json.load(fh)

# ---- commands -----------------------------------------------------------------------------------------------------------------------
if CMD == "egress-test":
    url = database_url(); u = urllib.parse.urlparse(url); host = u.hostname; out = {}
    t = time.perf_counter()
    try: s = socket.create_connection((host, u.port or 5432), timeout=10); s.close(); out["tcp_5432"] = {"ok": True, "ms": int((time.perf_counter() - t) * 1000)}
    except Exception as e: out["tcp_5432"] = {"ok": False, "err": str(e)[:100]}
    t = time.perf_counter()
    try: s = ssl.create_default_context().wrap_socket(socket.create_connection((host, 443), timeout=10), server_hostname=host); s.close(); out["tls_443"] = {"ok": True, "ms": int((time.perf_counter() - t) * 1000)}
    except Exception as e: out["tls_443"] = {"ok": False, "err": str(e)[:100]}
    for mode in ("pg", "http"):
        t = time.perf_counter()
        try:
            db = DB(url, mode).connect(); r = db.execute("select current_database(), current_user, version()"); db.close()
            out[mode] = {"ok": True, "ms": int((time.perf_counter() - t) * 1000), "driver": db.kind, "db": r[0][0], "role": r[0][1], "server": str(r[0][2]).split(" on ")[0][:32]}
        except BaseException as e: out[mode] = {"ok": False, "err": str(e)[:160]}
    ok = any(v.get("ok") for k, v in out.items() if k in ("pg", "http"))
    print("neon egress-test %s: %s" % ("OK" if ok else "BLOCKED", json.dumps(out, separators=(",", ":"))))
    sys.exit(0 if ok else 3)

db = connect()
if CMD == "init":
    for stmt in [s.strip() for s in DDL.split(";\n") if s.strip()]: db.execute(stmt)
    extra = os.path.join(REPO, "tools", "db", "neon_schema.sql"); applied = "no neon_schema.sql"
    if os.path.isfile(extra):
        sqltext = open(extra, encoding="utf-8").read(); n = 0
        if db.kind == "http":
            for stmt in [s for s in re.split(r";\s*\n(?=\S)", sqltext) if s.strip() and not s.strip().startswith("--")]: db.execute(stmt); n += 1
        else: db.execute(sqltext); n = sqltext.count(";")
        applied = "neon_schema.sql applied (%d statement%s)" % (n, "" if n == 1 else "s")
    hip = hipaa_ok(db)
    print("neon init via %s: raw/ops/ehpa schemas and tables ready; %s; hipaa marker %s" % (db.kind, applied, "set" if hip else "NOT set (loads of chart-level data refuse until `set --key hipaa_enabled --value true`)"))

elif CMD == "set":
    k, v = opt("--key"), opt("--value")
    if not k or v is None: sys.exit("usage: neon_db.py set --key <key> --value <value>")
    db.execute("insert into ops.settings (key, value, updated_by) values (%s, %s, %s) on conflict (key) do update set value = excluded.value, updated_at = now(), updated_by = excluded.updated_by", [k, v, BY])
    print("neon set: %s = %s" % (k, v))

elif CMD == "load-writes":
    out = opt("--out")
    if not out or not os.path.isdir(out): sys.exit("usage: neon_db.py load-writes --out <dir with writes_*.json from practice_db.py>")
    require_hipaa(db, "practice database documents")
    files = sorted(glob.glob(os.path.join(out, "writes_*.json"))); items = []
    for f in files:
        for e in load_json(f):
            if e.get("op") != "set": continue
            body = load_json(e["file_path"]) if e.get("file_path") else e.get("data")
            if body is None: continue
            items.append((e["collection"], e["doc_id"], body, None))
    ins, upd, same, nb, ms = upsert_documents(db, "practice_db", items, "load-writes " + os.path.basename(out.rstrip("/\\")))
    print("neon load-writes via %s: %d writes file(s), %d document(s) -> %d new, %d updated, %d unchanged (%d KB, %d ms)%s" % (db.kind, len(files), len(items), ins, upd, same, nb // 1024, ms, " [dry]" if DRY else ""))

elif CMD == "load-docs":
    src, source = opt("--src"), opt("--source")
    if not (src and source and os.path.isdir(src)): sys.exit("usage: neon_db.py load-docs --src <dir of <collection>/<doc_id>.json> --source <artifact slug>")
    require_hipaa(db, "artifact documents of " + source)
    items = []
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src).replace(os.sep, "/")
        if rel == ".": continue
        for f in sorted(files):
            if not f.endswith(".json"): continue
            try: body = load_json(os.path.join(root, f))
            except Exception: continue
            items.append((rel, f[:-5], body, None))
    ins, upd, same, nb, ms = upsert_documents(db, source, items, "load-docs " + source)
    colls = sorted({c for c, _, _, _ in items})
    print("neon load-docs via %s: %s -> %d document(s) in %d collection(s) [%s] -> %d new, %d updated, %d unchanged (%d KB, %d ms)%s" % (db.kind, source, len(items), len(colls), ", ".join(colls)[:200], ins, upd, same, nb // 1024, ms, " [dry]" if DRY else ""))

elif CMD == "load-page":
    slug, url, f, title = opt("--slug"), opt("--url"), opt("--file"), opt("--title")
    if not (slug and url and f and os.path.isfile(f)): sys.exit("usage: neon_db.py load-page --slug <slug> --url <url> --file <index.html> [--title <t>]")
    require_hipaa(db, "the page " + slug)
    html = open(f, encoding="utf-8", errors="replace").read(); h = sha(html)
    if not title:
        m = re.search(r"<title>(.*?)</title>", html, re.S | re.I); title = (m.group(1).strip() if m else slug)[:200]
    prev = db.execute("select 1 from raw.artifact_pages where slug = %s and html_sha256 = %s", [slug, h])
    if prev: print("neon load-page: %s unchanged (sha %s)" % (slug, h[:12]))
    elif DRY: print("neon load-page: %s would store %d bytes [dry]" % (slug, len(html)))
    else:
        db.execute("insert into raw.artifact_pages (slug, url, title, html, html_sha256, bytes, saved_by) values (%s, %s, %s, %s, %s, %s, %s)", [slug, url, title, html, h, len(html.encode("utf-8")), BY])
        db.execute("insert into ops.load_log (command, source, inserted, bytes, loaded_by) values ('load-page', %s, 1, %s, %s)", [slug, len(html), BY])
        print("neon load-page via %s: %s stored (%d KB, sha %s)" % (db.kind, slug, len(html) // 1024, h[:12]))

elif CMD == "load-files":
    root, source, prefix = opt("--root"), opt("--source", "repo"), opt("--prefix", "")
    if not (root and os.path.isdir(root)): sys.exit("usage: neon_db.py load-files --root <dir> --source repo [--prefix <collection prefix>]")
    require_hipaa(db, "files under " + root)
    items = []; texts = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules", "secrets")]
        rel = os.path.relpath(r, root).replace(os.sep, "/"); coll = "/".join(x for x in (prefix, "" if rel == "." else rel) if x) or "root"
        for f in sorted(files):
            p = os.path.join(r, f)
            try:
                if f.endswith(".json"): items.append((coll, f[:-5], load_json(p), None))
                elif f.endswith(".jsonl"):
                    lines = []
                    for ln in open(p, encoding="utf-8"):
                        ln = ln.strip()
                        if ln:
                            try: lines.append(json.loads(ln))
                            except Exception: lines.append({"_raw": ln})
                    items.append((coll, f, {"lines": lines, "count": len(lines)}, None))
                elif f.endswith((".md", ".txt", ".csv", ".log")): texts.append((coll + "/" + f, open(p, encoding="utf-8", errors="replace").read(), os.path.getmtime(p)))
            except Exception: continue
    ins, upd, same, nb, ms = upsert_documents(db, source, items, "load-files " + (prefix or os.path.basename(root)))
    tn = 0
    for relpath, text, mt in texts:
        h = sha(text)
        if DRY: tn += 1; continue
        prev = db.execute("select sha256 from raw.files where source = %s and relpath = %s", [source, relpath])
        if prev and prev[0][0] == h: continue
        db.execute("insert into raw.files (source, relpath, text_body, sha256, bytes, file_mtime, loaded_by) values (%s, %s, %s, %s, %s, %s::timestamptz, %s) on conflict (source, relpath) do update set text_body = excluded.text_body, sha256 = excluded.sha256, bytes = excluded.bytes, file_mtime = excluded.file_mtime, loaded_at = now(), loaded_by = excluded.loaded_by",
                   [source, relpath, text, h, len(text.encode("utf-8")), datetime.datetime.fromtimestamp(mt, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), BY]); tn += 1
    print("neon load-files via %s: %s -> %d JSON document(s) (%d new, %d updated, %d unchanged) + %d text file(s) written (%d KB, %d ms)%s" % (db.kind, prefix or root, len(items), ins, upd, same, tn, nb // 1024, ms, " [dry]" if DRY else ""))

elif CMD == "run-log":
    routine, stamp, status, headline = opt("--routine"), opt("--stamp"), opt("--status", "ok"), opt("--headline", "")
    if not (routine and stamp): sys.exit("usage: neon_db.py run-log --routine <name> --stamp <stamp> --status ok|partial|failed --headline \"...\" [--summary <json file>] [--started <ISO>] [--session <url>] [--commit <sha>]")
    summary = load_json(opt("--summary")) if opt("--summary") and os.path.isfile(opt("--summary")) else None
    m = STAMP_RE.search(stamp); stamp_n = re.sub(r"[^0-9TZ]", "", m.group(0)) if m else stamp
    started = opt("--started") or ("%s-%s-%sT%s:%s:00Z" % m.groups() if m else None)
    if DRY: print("neon run-log: would record %s %s %s [dry]" % (routine, stamp_n, status))
    else:
        db.execute("""insert into ops.routine_runs (routine, stamp, started_at, status, headline, summary, session_url, commit_sha, loaded_by)
                      values (%s, %s, %s::timestamptz, %s, %s, %s::jsonb, %s, %s, %s)
                      on conflict (routine, stamp) do update set status = excluded.status, headline = excluded.headline, summary = coalesce(excluded.summary, ops.routine_runs.summary),
                      finished_at = now(), session_url = coalesce(excluded.session_url, ops.routine_runs.session_url), commit_sha = coalesce(excluded.commit_sha, ops.routine_runs.commit_sha), loaded_by = excluded.loaded_by""",
                   [routine, stamp_n, started, status, headline[:600], dumps(summary) if summary is not None else None, opt("--session") or os.environ.get("CLAUDE_SESSION_URL"), opt("--commit"), BY])
        print("neon run-log via %s: %s %s recorded as %s" % (db.kind, routine, stamp_n, status))

elif CMD == "health":
    rows = db.execute("select source, collection, documents, newest_written, last_loaded, bytes from ops.v_health")
    tot = sum(int(r[2]) for r in rows); nb = sum(int(r[5] or 0) for r in rows)
    pages = db.execute("select count(*), count(distinct slug) from raw.artifact_pages")[0]
    runs = db.execute("select count(*), max(finished_at) from ops.routine_runs")[0]
    loads = db.execute("select count(*), max(at) from ops.load_log")[0]
    hip = hipaa_ok(db)
    print("neon health via %s: %d documents (%d MB) in %d source/collection pairs; %s page versions of %s pages; %s routine runs (last %s); %s loads (last %s); hipaa marker %s" % (db.kind, tot, nb // 1048576, len(rows), pages[0], pages[1], runs[0], runs[1], loads[0], loads[1], "set" if hip else "NOT set"))
    for r in rows: print("  %-26s %-40s %6s docs  newest %s" % (r[0], r[1][:40], r[2], str(r[3])[:19] if r[3] else "-"))

elif CMD == "sql":
    q = (a[1] if len(a) > 1 else "").strip()
    if not q or not re.match(r"^(select|with|show|explain|table)\b", q, re.I) or ";" in q.rstrip(";"): sys.exit("usage: neon_db.py sql \"select ...\"  (one read-only statement)")
    rows = db.execute(q.rstrip(";"))
    print(json.dumps(rows[:500], default=str));
    if len(rows) > 500: print("... %d rows, 500 shown" % len(rows), file=sys.stderr)
else:
    sys.exit("usage: neon_db.py init | egress-test | load-writes | load-docs | load-page | load-files | run-log | set | health | sql (see the header)")
db.close()
