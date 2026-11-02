#!/usr/bin/env python3
# PLAIN ENGLISH (ehpa Practice Database - William 11/1/2026: "make this an ehpa practice database with all this information in it ...
#   a database that can be used for all other data involved in the billing and credentialing projects ... include the billing
#   information and ERAs").
# The database is the claude.ai artifact database of the page https://claude.ai/artifact/QrLJpUcpFv3cFRB9xHfLyk ("ehpa Practice
#   Database", formerly Claimocity Feed Monitoring): JSON documents in collections, written by Claude sessions and routines with the
#   ArtifactData tool, read by the page itself (db capability) - no GitHub connector, no prompts in the browser.
# This script turns the PHI-light records on GitHub main into database documents and writes them as files, plus the exact
#   ArtifactData `batch` calls that store them. It never talks to the database itself (the model makes the ArtifactData call).
# Collections it fills (every document <= 200 KB, split into .p2/.p3 parts when larger; ids are run stamps so a run never overwrites
#   another run's document and no version pinning is needed):
#   feed_batches/<stamp>   one Claimocity ingest batch: every feed message and what AdvancedMD got (registers/feed_recon_<stamp>.json)
#   feed_checks/<stamp>    one line per feed run, ingest or "nothing new" (what the bucket held, when it was checked)
#   billing_runs/<stamp>   one Billing Button / scheduled billing run, compacted from reports/button/<stamp>.json
#   era_runs/<stamp>       one run's ERA posting work (era_new / era_checks_before+after / era_audit registers of that stamp)
#   snapshots/<kind>-<stamp>  approvals (approvals_pending.json), practice master data (carriers, facilities, practice), repo head
# PHI: only what main already holds - chart ids, visit/charge ids, dates, codes, dollars, carrier codes. Names never (phi_gate guards main).
# Usage:
#   python3 tools/db/practice_db.py build --run <stamp> [--check-result ingested|nothing_new|blocked|failed --check-line "<gcs line>"]
#        -> outbox/practice_db/<stamp>/ : docs/*.json + writes_1.json ... + CALLS.md   (one routine run; usually 1 batch)
#   python3 tools/db/practice_db.py build --all [--since YYYYMMDD]    -> every batch, run and snapshot on hand (backfill; many batches)
#   python3 tools/db/practice_db.py build --practice                   -> the practice master-data snapshots only
# Options: --repo /home/claude/effinger-billing-backend  --ws /home/claude/unbilled  --out <dir>  --max-doc-kb 200
import os, sys, re, json, glob, datetime, collections

a = sys.argv[1:]
def opt(name, default=None): return a[a.index(name) + 1] if name in a else default
REPO = opt("--repo", "/home/claude/effinger-billing-backend"); WS = opt("--ws", "/home/claude/unbilled")
RUN = opt("--run"); ALL = "--all" in a; PRACTICE = "--practice" in a; SINCE = opt("--since", "")
MAXKB = int(opt("--max-doc-kb", "200"))
URL = "https://claude.ai/artifact/QrLJpUcpFv3cFRB9xHfLyk"
NOW = datetime.datetime.now(datetime.timezone.utc)
BUILD = NOW.strftime("%Y%m%dT%H%MZ")
OUT = opt("--out", os.path.join(WS, "outbox", "practice_db", RUN or ("all_" + BUILD if ALL else BUILD)))
REG = os.path.join(REPO, "practices", "ehpa", "registers")
def load(p, default=None):
    try: return json.load(open(p))
    except Exception: return default
def money(x):
    try: return round(float(str(x).replace("$", "").replace(",", "") or 0), 2)
    except Exception: return 0.0
def clip(s, n): s = "" if s is None else str(s); return s if len(s) <= n else s[:n - 1] + "…"
def norm_stamp(s): return re.sub(r"[^0-9TZR]", "", s or "")

# ---- lookups shared by every batch document ----------------------------------------------------------------------------------------
FAC = load(os.path.join(REPO, "practices", "ehpa", "facilities.json"), {}) or load(os.path.join(WS, "facilities.json"), {}) or {}
CAR = load(os.path.join(WS, "carriers_rich.json"), {}) or load(os.path.join(REPO, "practices", "ehpa", "carriers.json"), {}) or {}
CODE2NAME = {v[0]: v[1] for v in CAR.values() if isinstance(v, list) and len(v) > 1}
FAC_SHORT = {"fac29": "HCA Capital Hospital", "fac34": "Brynwood (Monticello)", "fac33": "Centre Pointe Health & Rehab", "fac58": "Westminster Bertrand", "fac32": "Aspire at Tallahassee", "fac1350": "Oakes Southwood"}
def fac_name(fid):
    if fid in FAC_SHORT: return FAC_SHORT[fid]
    n = FAC.get(fid) if isinstance(FAC, dict) else None
    if not n: return fid or "unknown facility"
    n = re.sub(r"\s*\((TALLAHASSEE|MONTICELLO|QUINCY|CRAWFORDVILLE)\)\s*$", "", n)
    words = n.split(); half = len(words) // 2
    if half and words[:half] == words[half:2 * half]: words = words[:half]
    n = " ".join(w for w in words if w.upper() not in ("LLC", "INC", "LP"))
    return n.title().replace("Alf", "ALF").replace("Snf", "SNF").replace("Hca", "HCA").replace("Tmh", "TMH").replace(" And ", " & ")[:40]
CLIN = {"EFFINGER WILLIAM": "Dr. Effinger (DO)", "GARLAND-G PAMELA": "Pamela G. (ARNP)"}
def clin(p):
    if not p: return "Clinician on file"
    if re.search(r"[.()]", str(p)): return p          # already a label (claimocity_recon.py writes labels since 11/2)
    k = re.sub(r"[^A-Z ]", "", p.upper()).strip()
    if k in CLIN: return CLIN[k]
    parts = k.split(); return (parts[-1].title() + " " + parts[0][0] + ".") if len(parts) > 1 else parts[0].title()

docs = []   # (collection, doc_id, body)
def add(collection, doc_id, body):
    body = dict(body); body.setdefault("_written", NOW.strftime("%Y-%m-%dT%H:%M:%SZ")); body.setdefault("_source", "tools/db/practice_db.py")
    s = json.dumps(body, separators=(",", ":"))
    if len(s) <= MAXKB * 1024 or "rows" not in body: docs.append((collection, doc_id, body)); return
    rows = body["rows"]; parts = []; cur = []; base = {k: v for k, v in body.items() if k != "rows"}
    budget = MAXKB * 1024 - len(json.dumps(base, separators=(",", ":"))) - 200
    size = 0
    for r in rows:
        rs = len(json.dumps(r, separators=(",", ":"))) + 1
        if cur and size + rs > budget: parts.append(cur); cur = []; size = 0
        cur.append(r); size += rs
    if cur: parts.append(cur)
    for i, chunk in enumerate(parts):
        b = dict(base); b["rows"] = chunk; b["part"] = i + 1; b["parts"] = len(parts)
        docs.append((collection, doc_id if i == 0 else "%s.p%d" % (doc_id, i + 1), b))

# ---- feed --------------------------------------------------------------------------------------------------------------------------------
def feed_batch_doc(stamp):
    rec = load(os.path.join(REG, "feed_recon_%s.json" % stamp)) or load(os.path.join(WS, "registers", "feed_recon_%s.json" % stamp))
    if not rec: return None
    facs = sorted({r.get("fac") for r in rec["rows"] if r.get("fac")}); cars = sorted({r.get("lead") for r in rec["rows"] if r.get("lead")}); provs = sorted({r.get("prov") for r in rec["rows"] if r.get("prov")})
    body = {"schema": "practice-feed-batch/1", "stamp": stamp, "at": rec.get("at"), "built": rec.get("built"), "live": rec.get("live"), "files": rec.get("files", []),
            "dmin": rec.get("dmin"), "dmax": rec.get("dmax"), "counts": rec.get("counts", {}), "rows": rec["rows"],
            "lookups": {"fac": {f: fac_name(f) for f in facs}, "car": {c: CODE2NAME.get(c, c) for c in cars}, "prov": {p: clin(p) for p in provs}},
            "source": "practices/ehpa/registers/feed_recon_%s.json" % stamp}
    add("feed_batches", stamp, body); return body

def feed_check_doc(stamp, result, line, batch=None):
    reg = load(os.path.join(REG, "claimocity_ingest.json")) or load(os.path.join(WS, "registers", "claimocity_ingest.json")) or {"files": {}, "runs": []}
    run = next((r for r in reversed(reg.get("runs", [])) if norm_stamp(r.get("stamp")) == norm_stamp(stamp)), {})
    files = sorted(reg.get("files", {}), key=lambda k: reg["files"][k].get("at") or "")
    newest = max((re.match(r"\d{8}", k).group(0) for k in reg.get("files", {}) if re.match(r"\d{8}", k)), default=None)
    body = {"schema": "practice-feed-check/1", "stamp": stamp, "at": run.get("at") or NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "result": result, "line": clip(line, 300),
            "files_registered": len(files), "newest_file": newest, "files_new": len(run.get("files") or []), "live": run.get("live"), "exit": run.get("exit")}
    if batch: body.update({"visits": batch["counts"].get("entered"), "dollars": batch["counts"].get("dollars"), "messages": batch["counts"].get("messages"), "new_charts": batch["counts"].get("new_charts")})
    add("feed_checks", stamp, body)

# ---- billing runs ----------------------------------------------------------------------------------------------------------------------
def run_doc(stamp):
    p = os.path.join(REPO, "reports", "button", "%s.json" % stamp); j = load(p)
    if not j: return None
    steps = []
    for s in j.get("steps") or []:
        steps.append({"name": s.get("name"), "title": clip(s.get("title"), 80), "status": s.get("status"), "summary": clip(s.get("summary"), 700),
                      "counts": s.get("counts") if isinstance(s.get("counts"), (dict, int, float)) else None, "dollars": s.get("dollars"), "lines": s.get("lines"),
                      "errors": [clip(e, 240) for e in (s.get("errors") or [])[:4]], "started": s.get("started"), "ended": s.get("ended")})
    pk = [{k: clip(v, 200) if isinstance(v, str) else v for k, v in (x.items() if isinstance(x, dict) else [("text", x)])} for x in (j.get("packages") or [])[:20]]
    body = {"schema": "practice-billing-run/1", "stamp": j.get("stamp") or stamp, "mode": j.get("mode"), "status": j.get("status"), "headline": clip(j.get("headline"), 600),
            "note": clip(j.get("note"), 200), "run_url": j.get("run_url"), "started": j.get("started"), "ended": j.get("ended"), "at": j.get("ended") or j.get("started"),
            "summary": j.get("summary") if isinstance(j.get("summary"), dict) else {"text": clip(j.get("summary"), 600)}, "steps": steps, "packages": pk,
            "waiting": [clip(w if isinstance(w, str) else json.dumps(w), 240) for w in (j.get("waiting") or [])[:30]], "errors": [clip(e if isinstance(e, str) else json.dumps(e), 240) for e in (j.get("errors") or [])[:10]],
            "brief": clip(j.get("brief"), 300), "source": "reports/button/%s.json" % stamp}
    if "visits" in body["summary"] and isinstance(body["summary"]["visits"], list): body["summary"] = {k: v for k, v in body["summary"].items() if k != "visits"}
    add("billing_runs", norm_stamp(stamp), body); return body

# ---- ERA runs ----------------------------------------------------------------------------------------------------------------------------
def era_doc(stamp):
    new = load(os.path.join(REG, "era_new_%s.json" % stamp)); before = load(os.path.join(REG, "era_checks_before_%s.json" % stamp)); after = load(os.path.join(REG, "era_checks_after_%s.json" % stamp))
    audit = load(os.path.join(REG, "era_audit_%s.json" % stamp)); fb = load(os.path.join(REG, "era_fallback_live_%s.json" % stamp))
    if not any([new, before, after, audit, fb]): return None
    lines = []
    for l in ((new or {}).get("lines", []) if isinstance(new, dict) else []):
        lines.append({"check": l.get("checkid"), "p": l.get("pid"), "v": l.get("visitid"), "cpt": l.get("cpt"), "dos": l.get("dos"), "paid": money(l.get("paid")), "status": l.get("claimstatus"),
                      "carcs": l.get("carcs") if isinstance(l.get("carcs"), list) else ([l.get("carcs")] if l.get("carcs") else []), "outcome": clip(l.get("outcome"), 120), "primary": l.get("primary")})
    outcomes = collections.Counter(clip(l.get("outcome"), 40) for l in lines)
    def chk(x):
        if isinstance(x, list): x = {"count": len(x), "total": None, "checks": x}
        if not isinstance(x, dict): return None
        return {"count": x.get("count"), "total": x.get("total"), "checks": [c if isinstance(c, str) else {k: v for k, v in c.items() if k in ("id", "check", "checkid", "payer", "amount", "total", "date", "carrier")} for c in (x.get("checks") or [])[:60] if isinstance(c, (str, dict))]}
    body = {"schema": "practice-era-run/1", "stamp": stamp, "at": None, "checks_before": chk(before), "checks_after": chk(after), "lines": lines[:800],
            "line_count": len(lines), "paid_total": round(sum(l["paid"] for l in lines), 2), "outcomes": dict(outcomes),
            "audit": {"checks": audit.get("checks", [])[:60], "rows": len(audit.get("rows", [])), "flags": [[clip(x, 60) for x in (f if isinstance(f, list) else [f])] for f in audit.get("flags", [])[:80]]} if isinstance(audit, dict) else None,
            "fallback": {"keys": sorted((fb or {}).keys())[:20]} if isinstance(fb, dict) else None, "dry": bool(new.get("dry")) if isinstance(new, dict) else False,
            "source": "practices/ehpa/registers/era_*_%s.json" % stamp}
    m = re.match(r"(\d{4})-?(\d{2})-?(\d{2})T(\d{2})(\d{2})Z", stamp)
    if m: body["at"] = "%s-%s-%sT%s:%s:00Z" % m.groups()
    add("era_runs", norm_stamp(stamp), body); return body

# ---- snapshots -----------------------------------------------------------------------------------------------------------------------------
def approvals_snapshot(stamp):
    ap = load(os.path.join(REG, "approvals_pending.json"))
    if not ap: return None
    items = [{"id": i.get("id"), "stamp": i.get("stamp"), "at": i.get("at"), "what": clip(i.get("what"), 240), "dollars": i.get("dollars"), "status": i.get("status"),
              "answer": clip(i.get("answer"), 160), "reason": clip(i.get("reason"), 160), "ui": clip(i.get("ui"), 200), "cmd": clip(i.get("cmd"), 200)} for i in ap.get("items", [])]
    st = collections.Counter(i["status"] for i in items)
    add("snapshots", "approvals-%s" % stamp, {"schema": "practice-snapshot/1", "kind": "approvals", "stamp": stamp, "at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "counts": dict(st),
                                              "dollars_waiting": round(sum(money(i["dollars"]) for i in items if i["status"] == "waiting"), 2), "rows": items,
                                              "page": "https://claude.ai/artifact/HuYd2bSm2NxkFgYRqra7wR", "source": "practices/ehpa/registers/approvals_pending.json"})
def repo_snapshot(stamp):
    import subprocess
    def git(*args):
        try: return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception: return ""
    head = git("rev-parse", "--short", "HEAD"); last = git("log", "-1", "--format=%H|%cI|%s")
    counts = {"registers": len(glob.glob(os.path.join(REG, "*.json"))), "button_reports": len(glob.glob(os.path.join(REPO, "reports", "button", "20*.json"))),
              "feed_recon": len(glob.glob(os.path.join(REG, "feed_recon_*.json"))), "helpers": len(glob.glob(os.path.join(REPO, "scripts", "helpers", "*.py")))}
    add("snapshots", "repo-%s" % stamp, {"schema": "practice-snapshot/1", "kind": "repo", "stamp": stamp, "at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "head": head,
                                         "last_commit": clip(last, 300), "counts": counts, "repo": "https://github.com/dreffinger/effinger-billing-backend",
                                         "branches": {"main": "the record", "claude/effinger-billing-backend-mirror-w74pqv": "the synced copy the Project reads"}})
def practice_snapshots():
    for name, path in (("carriers", "carriers.json"), ("facilities", "facilities.json"), ("practice", "practice.json")):
        j = load(os.path.join(REPO, "practices", "ehpa", path))
        if j is None: continue
        add("practice", name, {"schema": "practice-master/1", "name": name, "data": j, "source": "practices/ehpa/%s" % path})

# ---- assemble ----------------------------------------------------------------------------------------------------------------------------
made = collections.Counter()
if RUN:
    st = norm_stamp(RUN)
    b = feed_batch_doc(st)
    result = opt("--check-result") or ("ingested" if b else "nothing_new")
    feed_check_doc(st, result, opt("--check-line", ""), b)
    r = run_doc(RUN) or run_doc(st)
    e = era_doc(RUN) or era_doc(re.sub(r"(\d{4})(\d{2})(\d{2})T", r"\1-\2-\3T", st))
    approvals_snapshot(st); repo_snapshot(st)
elif ALL:
    for p in sorted(glob.glob(os.path.join(REG, "feed_recon_*.json"))) or sorted(glob.glob(os.path.join(WS, "registers", "feed_recon_*.json"))):
        st = re.sub(r"^feed_recon_|\.json$", "", os.path.basename(p))
        if st < SINCE: continue
        b = feed_batch_doc(st); feed_check_doc(st, "ingested", "backfill from registers", b)
    for p in sorted(glob.glob(os.path.join(REPO, "reports", "button", "20*.json"))):
        st = os.path.basename(p)[:-5]
        if norm_stamp(st) < SINCE: continue
        run_doc(st)
    stamps = sorted({re.sub(r"^era_(new|checks_before|checks_after|audit|fallback_live)_|\.json$", "", os.path.basename(p)) for p in glob.glob(os.path.join(REG, "era_*_20*.json")) if "_dry" not in p})
    for st in stamps:
        if norm_stamp(st) < SINCE: continue
        era_doc(st)
    approvals_snapshot(BUILD); repo_snapshot(BUILD); practice_snapshots()
elif PRACTICE:
    practice_snapshots()
else:
    sys.exit("usage: practice_db.py build --run <stamp> | --all [--since YYYYMMDD] | --practice")

os.makedirs(os.path.join(OUT, "docs"), exist_ok=True)
writes, batches, cur, cur_bytes = [], [], [], 0
for coll, did, body in docs:
    fn = os.path.join(OUT, "docs", "%s__%s.json" % (coll.replace("/", "~"), did))
    s = json.dumps(body, separators=(",", ":")); open(fn, "w").write(s)
    made[coll] += 1
    entry = {"op": "set", "collection": coll, "doc_id": did, "file_path": fn}
    if len(cur) >= 50 or cur_bytes + len(s) > 900 * 1024: batches.append(cur); cur, cur_bytes = [], 0
    cur.append(entry); cur_bytes += len(s)
if cur: batches.append(cur)
for i, b in enumerate(batches): json.dump(b, open(os.path.join(OUT, "writes_%d.json" % (i + 1)), "w"), indent=0)
calls = ["# ehpa Practice Database - calls for this build (%s)" % BUILD, "", "Documents: " + ", ".join("%s %d" % kv for kv in sorted(made.items())), "",
         "For each writes_N.json below make ONE ArtifactData call: action \"batch\", url \"%s\", writes = the file's JSON array (each entry is {op, collection, doc_id, file_path}; every doc_id is new, so no if_version)." % URL,
         "A `quota_exceeded` or `invalid_argument` answer is reported verbatim in the digest, never retried; any other failure is retried once.", ""]
for i, b in enumerate(batches): calls.append("- writes_%d.json : %d documents (%s)" % (i + 1, len(b), ", ".join(sorted({e['collection'] for e in b}))))
open(os.path.join(OUT, "CALLS.md"), "w").write("\n".join(calls) + "\n")
print("practice_db build %s -> %s : %d document(s) in %d batch file(s) [%s]" % (BUILD, OUT, len(docs), len(batches), ", ".join("%s %d" % kv for kv in sorted(made.items()))))
