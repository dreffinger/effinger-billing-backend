#!/usr/bin/env python3
# PLAIN ENGLISH (Universal Practice Optimization loader, William 11/10/2026).
# Decides: nothing about billing. It is the one door between the JSON seed files under optimization/ and the `upo` schema in the
#   practice's Neon Postgres. The seed files are the source: this tool validates them, then makes the database match them.
#   A reload never duplicates a row. Work-list rows are the one exception to "the seed wins": the owner changes their status and
#   note in the app, so a reload updates a row's wording but never its status, note or who last touched it, and never deletes one.
# Where the connection comes from: NEON_DATABASE_URL (the ehpa cloud environment's credential; never printed, never written).
#   It talks to Postgres over Neon's HTTPS SQL endpoint (port 443), the same path tools/db/neon_db.py falls back to, so it works
#   from a container whose egress blocks port 5432.
# Which database: --target prod is the production branch (the host inside NEON_DATABASE_URL). --target preview swaps in the
#   endpoint host of a preview branch, read from --host or the file optimization/.preview_host (git-ignored). There is no
#   default: a command that writes must say which one.
# PHI rule: the seeds and these tables hold aggregates only. validate() refuses a seed that looks like it carries a patient
#   identifier (a date of birth label, a member-id label, an MBI-shaped token, a LAST,FIRST name pair).
# Usage:
#   python3 optimization/tools/upo_load.py validate                      check every seed file; exit 1 with a list on any error
#   python3 optimization/tools/upo_load.py schema --target preview       apply optimization/db/upo_schema.sql (idempotent)
#   python3 optimization/tools/upo_load.py load --target preview         validate, then upsert every table from the seeds
#   python3 optimization/tools/upo_load.py status --target prod          rows per table
#   python3 optimization/tools/upo_load.py sql --target prod "select ..."   one read-only statement, rows as an aligned table
import os, sys, re, json, glob, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.dirname(HERE)                    # optimization/ - where the schema file and .preview_host live
ROOT = os.environ.get("UPO_SEEDS_ROOT") or HOME # where the seed files are read from (a test can point this at a folder of sample seeds)
a = sys.argv[1:]
def opt(name, default=None): return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default
CMD = a[0] if a and not a[0].startswith("--") else "validate"

# ---- connection -------------------------------------------------------------------------------------------------------------------
def base_url():
    v = re.sub(r"\s+", "", os.environ.get("NEON_DATABASE_URL") or os.environ.get("DATABASE_URL") or "")
    if not v.startswith("postgres"): sys.exit("upo_load: NEON_DATABASE_URL is not set")
    return v
def target_url():
    t = opt("--target")
    if t not in ("prod", "preview"): sys.exit("upo_load: say --target prod or --target preview")
    u = base_url()
    if t == "prod": return u, urllib.parse.urlparse(u).hostname
    host = opt("--host")
    f = os.path.join(HOME, ".preview_host")
    if not host and os.path.isfile(f): host = open(f).read().strip()
    if not host: sys.exit("upo_load: --target preview needs --host <endpoint host> or optimization/.preview_host")
    p = urllib.parse.urlparse(u)
    if host == p.hostname: sys.exit("upo_load: the preview host equals the production host")
    netloc = p.netloc.replace(p.hostname, host)
    return urllib.parse.urlunparse(p._replace(netloc=netloc)), host
class DB:
    def __init__(self): self.url, self.host = target_url()
    def q(self, sql, params=None):
        body = json.dumps({"query": sql, "params": params or []}).encode()
        req = urllib.request.Request("https://%s/sql" % self.host, data=body, method="POST",
            headers={"Neon-Connection-String": self.url, "Content-Type": "application/json", "Neon-Array-Mode": "true", "Neon-Raw-Text-Output": "true"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r: j = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            try: msg = json.loads(msg).get("message", msg)
            except Exception: pass
            raise RuntimeError("SQL failed: %s\n   statement: %s" % (msg[:600], re.sub(r"\s+", " ", sql)[:200]))
        return [f["name"] for f in j.get("fields", [])], j.get("rows", []), j.get("rowCount")

# ---- seeds ------------------------------------------------------------------------------------------------------------------------
def jload(rel, default=None):
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p): return default
    with open(p, encoding="utf-8") as f: return json.load(f)
def read_seeds():
    s = {"domains": jload("universal/domains.json", []), "sources": jload("universal/sources.json", []), "categories": [], "metrics": [],
         "vendor_items": jload("vendor/vendor_items.json", []), "vendor_claims": jload("vendor/vendor_claims.json", []), "learning_modules": [],
         "practices": [], "practice_categories": [], "practice_metrics": [], "risk_findings": [], "recommendations": [], "projects": [], "worklist_items": [], "valuations": [], "meta": jload("universal/meta.json", [])}
    for p in sorted(glob.glob(os.path.join(ROOT, "universal", "domains", "*.json"))):
        d = json.load(open(p, encoding="utf-8")); dom = d.get("domain") or os.path.basename(p)[:-5]
        for i, c in enumerate(d.get("categories", [])):
            c = dict(c); ms = c.pop("metrics", []) or []
            c.setdefault("domain_slug", dom); c.setdefault("ord", i + 1)
            s["categories"].append(c)
            for k, m in enumerate(ms):
                m = dict(m); m.setdefault("category_slug", c["slug"]); m.setdefault("ord", k + 1); s["metrics"].append(m)
    for p in sorted(glob.glob(os.path.join(ROOT, "learning", "*.json"))):
        s["learning_modules"].append(json.load(open(p, encoding="utf-8")))
    for pd in sorted(glob.glob(os.path.join(ROOT, "practices", "*", ""))):
        code = os.path.basename(os.path.dirname(pd)); rel = lambda n: os.path.join("practices", code, n)
        prof = jload(rel("practice.json"))
        if not prof: continue
        prof.setdefault("code", code); s["practices"].append(prof)
        for key, fn in (("practice_categories", "categories.json"), ("practice_metrics", "metrics.json"), ("risk_findings", "risk_findings.json"),
                        ("recommendations", "recommendations.json"), ("projects", "projects.json"), ("worklist_items", "worklist.json"), ("valuations", "valuation.json")):
            for row in jload(rel(fn), []) or []:
                row = dict(row); row.setdefault("practice", code); s[key].append(row)
    return s

# table -> (primary key columns, [(column, sql type)], mode)   mode: sync = seed wins and missing rows are deleted; keep = upsert, protected columns survive
T = {
 "domains": (["slug"], [("slug","text"),("ord","int"),("name","text"),("summary","text"),("why_it_matters","text"),("owner_role","text"),("frameworks","jsonb")], "sync"),
 "sources": (["slug"], [("slug","text"),("title","text"),("publisher","text"),("year","text"),("url","text"),("kind","text"),("note","text")], "sync"),
 "categories": (["slug"], [("slug","text"),("domain_slug","text"),("ord","int"),("name","text"),("summary","text"),("good_looks_like","jsonb"),("failure_modes","jsonb"),("key_questions","jsonb"),("actions","jsonb"),("applies_when","text"),("vendor_refs","jsonb"),("sources","jsonb"),("evidence_note","text")], "sync"),
 "metrics": (["slug"], [("slug","text"),("category_slug","text"),("ord","int"),("name","text"),("definition","text"),("formula","text"),("unit","text"),("direction","text"),("cadence","text"),("benchmark_best","text"),("benchmark_typical","text"),("benchmark_red","text"),("benchmark_note","text"),("confidence","text"),("sources","jsonb"),("data_hint","text"),("vendor_claim","text"),("vendor_verdict","text")], "sync"),
 "vendor_items": (["slug"], [("slug","text"),("vendor","text"),("bundle","text"),("title","text"),("doc_type","text"),("pages","int"),("words","int"),("list_price_usd","numeric"),("quality_score","int"),("specificity_score","int"),("practice_relevance_score","int"),("summary","text"),("top_ideas","jsonb"),("red_flags","jsonb"),("domains","jsonb"),("claims_checked","int"),("claims_supported","int"),("claims_partly","int"),("claims_contradicted","int"),("claims_outdated","int"),("claims_unverifiable","int"),("verdict","text")], "sync"),
 "vendor_claims": (["id"], [("id","text"),("item_slug","text"),("claim","text"),("kind","text"),("stakes","text"),("verdict","text"),("correct_statement","text"),("source_title","text"),("source_url","text"),("confidence","text"),("practice_impact","text")], "sync"),
 "learning_modules": (["slug"], [("slug","text"),("ord","int"),("title","text"),("audience","text"),("summary","text"),("minutes","int"),("body","jsonb"),("artifact_url","text")], "sync"),
 "practices": (["code"], [("code","text"),("name","text"),("specialty","text"),("setting","text"),("profile","jsonb")], "keep"),
 "practice_categories": (["practice","category_slug"], [("practice","text"),("category_slug","text"),("applicability","text"),("status","text"),("priority","int"),("assessment","text"),("evidence","jsonb"),("next_step","text")], "sync"),
 "practice_metrics": (["practice","metric_slug","as_of"], [("practice","text"),("metric_slug","text"),("as_of","date"),("value","numeric"),("value_text","text"),("status","text"),("basis","text"),("note","text"),("source","text")], "sync"),
 "risk_findings": (["id"], [("id","text"),("practice","text"),("ord","int"),("title","text"),("severity","text"),("likelihood","text"),("category_slug","text"),("what_we_see","text"),("rule","text"),("exposure","text"),("recommended_review","text"),("control","text"),("sources","jsonb")], "keep"),
 "recommendations": (["id"], [("id","text"),("practice","text"),("ord","int"),("kind","text"),("category_slug","text"),("title","text"),("why","text"),("what","jsonb"),("impact_low","numeric"),("impact_high","numeric"),("impact_basis","text"),("effort","text"),("horizon","text"),("owner","text"),("project_slug","text"),("confidence","text")], "sync"),
 "projects": (["practice","slug"], [("practice","text"),("slug","text"),("ord","int"),("title","text"),("objective","text"),("category_slug","text"),("priority","text"),("impact_low","numeric"),("impact_high","numeric"),("impact_note","text"),("owner","text"),("start_by","date"),("target_date","date"),("success_measures","jsonb"),("steps","jsonb")], "keep"),
 "worklist_items": (["id"], [("id","text"),("practice","text"),("project_slug","text"),("ord","int"),("title","text"),("detail","text"),("owner","text"),("due","date")], "keep"),
 "valuations": (["practice","as_of","method"], [("practice","text"),("as_of","date"),("method","text"),("low","numeric"),("base","numeric"),("high","numeric"),("inputs","jsonb"),("bridge","jsonb"),("notes","text")], "sync"),
 "meta": (["key"], [("key","text"),("value","jsonb")], "keep"),
}
ORDER = ["domains", "sources", "categories", "metrics", "vendor_items", "vendor_claims", "learning_modules", "practices", "practice_categories", "practice_metrics", "risk_findings", "recommendations", "projects", "worklist_items", "valuations", "meta"]
REQUIRED = {"domains": ["slug","ord","name","summary"], "categories": ["slug","domain_slug","name","summary"], "metrics": ["slug","category_slug","name","definition"], "sources": ["slug","title"],
            "vendor_items": ["slug","vendor","title"], "vendor_claims": ["id","item_slug","claim"], "learning_modules": ["slug","ord","title","body"], "practices": ["code","name"],
            "practice_categories": ["practice","category_slug","applicability","status"], "practice_metrics": ["practice","metric_slug","as_of"], "risk_findings": ["id","practice","ord","title"],
            "recommendations": ["id","practice","ord","title"], "projects": ["practice","slug","ord","title"], "worklist_items": ["id","practice","ord","title"], "valuations": ["practice","as_of","method"], "meta": ["key","value"]}
ENUMS = {("metrics","direction"): {"higher","lower","range","info",None}, ("metrics","confidence"): {"high","medium","low","none",None}, ("sources","kind"): {"primary","secondary","vendor","practice",None},
         ("practice_categories","applicability"): {"core","relevant","minor","not_applicable"}, ("practice_categories","status"): {"green","amber","red","unknown","na"},
         ("practice_metrics","status"): {"green","amber","red","unknown","na",None}, ("practice_metrics","basis"): {"measured","estimated","unknown",None},
         ("risk_findings","severity"): {"critical","high","medium","low",None}, ("risk_findings","likelihood"): {"high","medium","low","unknown",None},
         ("recommendations","kind"): {"revenue","risk","cost","value","capability",None}, ("projects","priority"): {"now","next","later",None}}
ZERO = {("vendor_items", c) for c in ("claims_checked", "claims_supported", "claims_partly", "claims_contradicted", "claims_outdated", "claims_unverifiable")} | {("metrics", "ord")}
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,78}$")
PHI = [(re.compile(r"\b[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y]{2}\d{2}\b"), "an MBI-shaped token"),
       (re.compile(r"(?i)\b(date of birth|dob)\s*[:=]\s*\d"), "a date of birth"), (re.compile(r"(?i)\bmember\s*(id|number|#)\s*[:=]\s*[A-Z0-9]{6,}"), "a member id"),
       (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "an SSN-shaped token"), (re.compile(r"\b[A-Z]{3,},[A-Z]{3,}\b"), "a LAST,FIRST name pair")]

def validate(s):
    errs = []
    def e(msg): errs.append(msg)
    for t in ORDER:
        pk, cols, _ = T[t]; names = {c for c, _ in cols}; seen = set()
        for i, r in enumerate(s[t]):
            where = "%s[%d]%s" % (t, i, (" " + str(r.get(pk[0]))) if isinstance(r, dict) else "")
            if not isinstance(r, dict): e(where + ": not an object"); continue
            for k in REQUIRED.get(t, []):
                if r.get(k) in (None, "", []): e(where + ": missing " + k)
            extra = set(r) - names
            if extra: e(where + ": unknown field(s) " + ", ".join(sorted(extra)))
            key = tuple(str(r.get(k)) for k in pk)
            if key in seen: e(where + ": duplicate key " + "/".join(key))
            seen.add(key)
            for c, typ in cols:
                v = r.get(c)
                if v is None: continue
                if typ == "jsonb" and not isinstance(v, (list, dict)): e("%s.%s: expected a list or object" % (where, c))
                if typ in ("int", "numeric") and (isinstance(v, bool) or not isinstance(v, (int, float))): e("%s.%s: expected a number, got %r" % (where, c, v))
                if typ == "int" and isinstance(v, float) and v != int(v): e("%s.%s: expected a whole number" % (where, c))
                if typ == "date" and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(v)): e("%s.%s: expected YYYY-MM-DD" % (where, c))
                if typ == "text" and not isinstance(v, str): e("%s.%s: expected text" % (where, c))
                if (t, c) in ENUMS and v not in ENUMS[(t, c)]: e("%s.%s: %r is not one of %s" % (where, c, v, sorted(x for x in ENUMS[(t, c)] if x)))
            if t in ("domains", "categories", "metrics", "sources", "vendor_items", "learning_modules") and not SLUG.match(str(r.get("slug", ""))): e(where + ": bad slug")
            blob = json.dumps(r, ensure_ascii=False)
            for rx, what in PHI:
                if t.startswith("vendor") and what.startswith("a LAST"): continue
                m = rx.search(blob)
                if m: e("%s: looks like it carries %s (%r) - seeds hold aggregates only" % (where, what, m.group(0)[:20]))
    have = lambda t, k="slug": {r.get(k) for r in s[t] if isinstance(r, dict)}
    dom, cat, met, src, items, pr = have("domains"), have("categories"), have("metrics"), have("sources"), have("vendor_items"), have("practices", "code")
    for r in s["categories"]:
        if r.get("domain_slug") not in dom: e("category %s: unknown domain %s" % (r.get("slug"), r.get("domain_slug")))
        for x in r.get("sources") or []:
            if x not in src: e("category %s: unknown source %s" % (r.get("slug"), x))
        for x in r.get("actions") or []:
            if not isinstance(x, dict) or not x.get("action"): e("category %s: every action needs an 'action'" % r.get("slug"))
    for r in s["metrics"]:
        if r.get("category_slug") not in cat: e("metric %s: unknown category %s" % (r.get("slug"), r.get("category_slug")))
        for x in r.get("sources") or []:
            if x not in src: e("metric %s: unknown source %s" % (r.get("slug"), x))
    for r in s["vendor_claims"]:
        if r.get("item_slug") not in items: e("vendor claim %s: unknown item %s" % (r.get("id"), r.get("item_slug")))
    for t, col, pool, label in (("practice_categories","category_slug",cat,"category"), ("practice_metrics","metric_slug",met,"metric")):
        for r in s[t]:
            if r.get(col) not in pool: e("%s %s: unknown %s %s" % (t, r.get("practice"), label, r.get(col)))
    for t in ("risk_findings", "recommendations", "projects"):
        for r in s[t]:
            if r.get("category_slug") and r.get("category_slug") not in cat: e("%s %s: unknown category %s" % (t, r.get("id") or r.get("slug"), r.get("category_slug")))
    for t in ("practice_categories","practice_metrics","risk_findings","recommendations","projects","worklist_items","valuations"):
        for r in s[t]:
            if r.get("practice") not in pr: e("%s: unknown practice %s" % (t, r.get("practice")))
    projs = {(r.get("practice"), r.get("slug")) for r in s["projects"]}
    for t in ("recommendations", "worklist_items"):
        for r in s[t]:
            if r.get("project_slug") and (r.get("practice"), r.get("project_slug")) not in projs: e("%s %s: unknown project %s" % (t, r.get("id"), r.get("project_slug")))
    return errs

def upsert(db, t, rows):
    pk, cols, mode = T[t]
    names = [c for c, _ in cols]
    rec = ", ".join('"%s" %s' % (c, typ) for c, typ in cols)
    def pick(c, typ):
        if typ == "jsonb": return "coalesce(x.\"%s\", '%s'::jsonb)" % (c, "{}" if c in ("profile", "inputs", "body", "value") else "[]")
        if (t, c) in ZERO: return 'coalesce(x."%s", 0)' % c            # a NOT NULL column with a default: an absent seed value must not arrive as NULL
        return 'x."%s"' % c
    sel = ", ".join(pick(c, typ) for c, typ in cols)
    upd = [c for c in names if c not in pk]
    stamp = ", updated_at = now()" if t in ("domains","categories","metrics","learning_modules","practices","practice_categories","risk_findings","projects","worklist_items","meta") else ""
    sql = 'insert into upo.%s (%s) select %s from jsonb_to_recordset($1::jsonb) as x(%s) on conflict (%s) do %s' % (
        t, ", ".join('"%s"' % c for c in names), sel, rec, ", ".join('"%s"' % c for c in pk),
        ("update set " + ", ".join('"%s" = excluded."%s"' % (c, c) for c in upd) + stamp) if upd else "nothing")
    n = 0
    for i in range(0, len(rows), 200):
        chunk = [{c: r.get(c) for c in names} for r in rows[i:i + 200]]
        _, _, rc = db.q(sql, [json.dumps(chunk, ensure_ascii=False)]); n += rc or 0
    gone = 0
    if mode == "sync":
        keyexpr = " || '|' || ".join('"%s"::text' % c for c in pk)
        keys = ["|".join(str(r.get(c)) for c in pk) for r in rows]
        _, _, gone = db.q("delete from upo.%s where not (%s = any(select jsonb_array_elements_text($1::jsonb)))" % (t, keyexpr), [json.dumps(keys)])
    return n, gone or 0

def split_sql(text):
    text = re.sub(r"--[^\n]*", "", text)
    return [x.strip() for x in text.split(";") if x.strip()]

def run():
    if CMD == "validate":
        s = read_seeds(); errs = validate(s)
        print("upo seeds: " + ", ".join("%s %d" % (t, len(s[t])) for t in ORDER))
        if errs:
            print("%d problem(s):" % len(errs)); [print("  - " + x) for x in errs[:200]]; sys.exit(1)
        print("upo validate OK")
    elif CMD == "schema":
        db = DB(); stmts = split_sql(open(os.path.join(HOME, "db", "upo_schema.sql"), encoding="utf-8").read())
        for st in stmts: db.q(st)
        print("upo schema OK: %d statements applied on %s (%s)" % (len(stmts), opt("--target"), db.host.split(".")[0]))
    elif CMD == "load":
        s = read_seeds(); errs = validate(s)
        if errs:
            print("upo load REFUSED: %d seed problem(s); run validate" % len(errs)); [print("  - " + x) for x in errs[:60]]; sys.exit(1)
        db = DB(); out = []
        only = opt("--only"); todo = [t for t in ORDER if not only or t in only.split(",")]
        for t in todo:
            if not s[t] and T[t][2] != "sync": continue
            n, gone = upsert(db, t, s[t]); out.append("%s %d%s" % (t, n, (" (-%d)" % gone) if gone else ""))
        print("upo load OK on %s (%s): %s" % (opt("--target"), db.host.split(".")[0], ", ".join(out)))
    elif CMD == "status":
        db = DB(); parts = []
        for t in ORDER:
            try: parts.append("%s %s" % (t, db.q("select count(*) from upo.%s" % t)[1][0][0]))
            except RuntimeError as ex: parts.append("%s ?" % t)
        print("upo status on %s (%s): %s" % (opt("--target"), db.host.split(".")[0], ", ".join(parts)))
    elif CMD == "sql":
        stmt = [x for x in a[1:] if not x.startswith("--") and x not in (opt("--target"), opt("--host"))][-1]
        if not re.match(r"(?is)^\s*(select|with|explain|show)\b", stmt): sys.exit("upo_load sql: read-only statements only")
        cols, rows, _ = DB().q(stmt)
        cells = [[("" if c is None else str(c))[:int(os.environ.get("QW", "70"))] for c in r] for r in rows]
        w = [max([len(cols[i])] + [len(r[i]) for r in cells]) for i in range(len(cols))]
        print(" | ".join(cols[i].ljust(w[i]) for i in range(len(cols)))); print("-+-".join("-" * x for x in w))
        for r in cells: print(" | ".join(r[i].ljust(w[i]) for i in range(len(cols))))
        print("(%d rows)" % len(rows))
    else:
        sys.exit("upo_load: unknown command %r (validate | schema | load | status | sql)" % CMD)

try:
    run()
except RuntimeError as ex:
    print("upo_load FAILED: " + str(ex)); sys.exit(1)
