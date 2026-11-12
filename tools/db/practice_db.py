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
#   cascade_runs/<stamp>   one night of the insurance cascade (practices/ehpa/registers/cascade_runs/<stamp>.json, tools/db/cascade_record.py)
#   snapshots/<kind>-<stamp>  approvals (approvals_pending.json), practice master data (carriers, facilities, practice), repo head
# PHI: only what main already holds - chart ids, visit/charge ids, dates, codes, dollars, carrier codes. Names never (phi_gate guards main).
#
# 11/6/2026 (William: "this section ... does not appear to be updating like it should ... data from any other scheduled billing runs
#   I would like to update and push to that artifact as well"): the page had stopped moving because (1) nothing wrote the nightly
#   cascade's row and (2) `build --run` packed only the calling run's own stamp, so the GitHub Actions engine's reports (12 a day,
#   committed by no Claude session) never reached billing_runs. Now EVERY build also SWEEPS what main holds and the database does not
#   yet: engine and routine reports (reports/button/<stamp>.json), ERA registers, feed batches and cascade nights of the last
#   --sweep-days (7, at most 40). The WRITTEN REGISTER practices/ehpa/registers/practice_db_written.jsonl - one JSON line per
#   document, {"k": "<collection>/<doc_id>", "at": when, "by": which run}, kept sorted, `merge=union` in .gitattributes so two runs'
#   registers merge line by line - is what makes that safe: a document another run already sent is never emitted again (a `set` of
#   an id the database holds fails the WHOLE batch), and every id a build emits is recorded at once (optimistic). A rebuild of the
#   SAME run stamp re-emits that run's own files (so a build repeated by mistake loses nothing). The run's own documents go in
#   writes_N.json; the swept ones go in one file set PER DAY, newest day first (writes_sweep_<YYYYMMDD>_N.json), so a collision
#   touches one day's file. EVERY run commits and pushes the register right after its batch calls (CALLS.md prints the command) -
#   a register left uncommitted through a later `git rebase --autostash` can come back with conflict markers, and an unreadable
#   register fails every build closed. Entries older than 45 days are dropped; nothing here ever looks back that far.
# Usage:
#   python3 tools/db/practice_db.py build --run <stamp> [--check-result ingested|nothing_new|blocked|failed --check-line "<gcs line>"] [--no-feed-check] [--no-sweep]
#        -> outbox/practice_db/<stamp>/ : docs/*.json + writes_1.json ... (this run) + writes_sweep_<day>_1.json ... (what other runs left behind) + CALLS.md
#        --no-feed-check: a run that never looked at the Claimocity bucket (the nightly cascade) writes no feed_checks row
#   python3 tools/db/practice_db.py build --sweep [--sweep-days 7]          -> the sweep alone (any session; out = outbox/practice_db/sweep_<build>)
#   python3 tools/db/practice_db.py build --all [--since YYYYMMDD]           -> every batch, run, ERA run, cascade night and snapshot on hand the register lacks
#                                                                               (never older than the register's 45-day memory; an older --since is raised to it)
#   python3 tools/db/practice_db.py build --practice                          -> the practice master-data snapshots only
# 11/12/2026 (William: "eras are being posted should be green ... everything billable is in advanced md ... put a box ... referencing the
#   neon database and ... the webapp, both functional and up to date, with links"): three more sources.
#   (1) ERA RUNS FROM THE ENGINE'S REPORTS: the GitHub Actions engine posts ERAs every two hours but keeps its era_* registers in its own
#       workspace - main gets the run's report and nothing else - so every era_runs document since 10/16 had 0 lines and the page read the
#       posting as stopped. A stamp with a report and no era_* register now gets its era_runs document from the report's `era` step
#       (era_doc_from_report: schema practice-era-run/2, engine=true, checks before/after from summary.era, the check rows the step listed,
#       checks_posted = the Post button's check presses, fallback_lines, co45_corrected (re-posts, never added to a total), dollars posted;
#       line_count null - the report counts no lines). A register-based document with no posted line on file takes the same fields from its
#       run's report (report_merged=true); a register's checks before/after total is the sum of the checks' unposted amounts when the register
#       kept no total (documents sent before 11/12/2026 and not resent still read 0 or null there). Only a run that did something, or left
#       checks unposted, gets a document; a quiet look is already in billing_runs.summary.era, which the page reads for "the newest run
#       looked at the ERA center".
#   (2) RETRY BATCHES: feed_recon_<stamp>R.json (claimocity_retry_dx.py - the visits an earlier batch skipped, entered later) are swept
#       into feed_batches too, with retry=true and no feed_checks row (a retry looks at no bucket); the page ranks what AdvancedMD got
#       above an earlier skip of the same encounter.
#   (3) SERVICE SNAPSHOTS, every build: snapshots/neon-<stamp> (tools/db/neon_db.py health --json: documents, last load, last routine run,
#       the web app's own access log) and snapshots/webapp-<stamp> (GET https://app.ehpa.dev/health and the home page's title, timed).
#       The page's "Permanent store and web app" box reads the newest of each that got through. --no-services skips them;
#       --neon-url-file <path> hands the connection-string file to neon_db.py (a laptop session) - this script never reads it. Both probes run
#       at once and answer within about a minute from a container that reaches neither host; a stored error is redacted and never a URL.
#   --resend <collection>/<doc_id> (repeatable): a document the database holds that this script now builds differently is rebuilt whatever
#       the register says and goes in writes_resend_N.json - every entry there REPLACES a document, so the sender adds its version (if_version).
#   python3 tools/db/practice_db.py trim --out <dir> --file <writes file> --exists <collection>/<doc_id> [--exists ...]
#        -> the ArtifactData answer said that document ALREADY EXISTS (the register had fallen behind the database): the entry leaves
#           the writes file (the register keeps it); send the same file again, repeat while another is named - never `unsent` for this
#   python3 tools/db/practice_db.py unsent --out <dir> [--file <writes file>] [--exists <collection>/<doc_id> ...]
#        -> the ArtifactData call was refused, asked for an approval, answered quota_exceeded / invalid_argument or any other error:
#           its ids leave the register so the next run resends them (--exists keeps the ones the answer said the database already holds)
# Options: --repo /home/claude/effinger-billing-backend  --ws /home/claude/unbilled  --out <dir>  --max-doc-kb 200  --no-services  --neon-url-file <path>  --resend <collection>/<doc_id>
#          --register <file> (default <repo>/practices/ehpa/registers/practice_db_written.jsonl)  --no-register (emit, record nothing - a dry look)
import os, sys, re, json, glob, datetime, collections

a = sys.argv[1:]
def opt(name, default=None): return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default
def opts(name): return [a[i + 1] for i, x in enumerate(a[:-1]) if x == name]
CMD = a[0] if a and not a[0].startswith("--") else "build"
REPO = opt("--repo", "/home/claude/effinger-billing-backend"); WS = opt("--ws", "/home/claude/unbilled")
RUN = opt("--run"); ALL = "--all" in a; PRACTICE = "--practice" in a; SWEEP_ONLY = "--sweep" in a
MAXKB = int(opt("--max-doc-kb", "200"))
URL = "https://claude.ai/artifact/QrLJpUcpFv3cFRB9xHfLyk"
NOW = datetime.datetime.now(datetime.timezone.utc)
BUILD = NOW.strftime("%Y%m%dT%H%MZ")
BUILDS = NOW.strftime("%Y%m%dT%H%M%SZ")   # 11/12/2026: a build that is not a run names itself (BY, default --out) to the second - two sweeps in one minute must not take each other's documents or folder
OUT = opt("--out", os.path.join(WS, "outbox", "practice_db", RUN or ("all_" + BUILDS if ALL else ("sweep_" + BUILDS if SWEEP_ONLY else BUILDS))))
REG = os.path.join(REPO, "practices", "ehpa", "registers")
REGF = opt("--register", os.path.join(REG, "practice_db_written.jsonl"))
NOREG = "--no-register" in a
SWEEP_DAYS = max(0, min(40, int(opt("--sweep-days", "7"))))
NO_SWEEP = "--no-sweep" in a or ALL or PRACTICE
NO_FEED_CHECK = "--no-feed-check" in a
NO_SERVICES = "--no-services" in a
KEEP_DAYS = 45                                   # register entries older than this are dropped - no build ever looks back that far
FLOOR45 = (NOW - datetime.timedelta(days=KEEP_DAYS)).strftime("%Y%m%d")
SINCE = opt("--since", ""); SINCE_NOTE = ""
if ALL and SINCE < FLOOR45: SINCE_NOTE = " (--since raised to %s: the register remembers %d days, an older backfill would resend what the database holds)" % (FLOOR45, KEEP_DAYS); SINCE = FLOOR45
RESEND = set(opts("--resend"))          # <collection>/<doc_id> the database holds and the builder now builds differently: rebuilt, sent from writes_resend_N.json with if_version
BY = RUN or ("sweep " + BUILDS if SWEEP_ONLY else ("all " + BUILDS if ALL else "practice " + BUILDS))   # who is sending: a rebuild of the same run re-emits its own files
def load(p, default=None):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return default
def money(x):
    try: return round(float(str(x).replace("$", "").replace(",", "") or 0), 2)
    except Exception: return 0.0
def clip(s, n): s = "" if s is None else str(s); return s if len(s) <= n else s[:n - 1] + "…"
def norm_stamp(s): return re.sub(r"[^0-9TZR]", "", s or "")
def stamp_day(s):
    """YYYYMMDD of a plain run stamp (2026-11-06T0535Z / 20261106T0535Z); None for anything else. A retry register such as
    feed_recon_20261102T1904ZR.json fails this test on purpose: sweep() takes those in its own loop (retry_day strips the R)"""
    m = re.fullmatch(r"(\d{8})T\d{4}Z", norm_stamp(s)); return m.group(1) if m else None
def retry_day(s):
    """YYYYMMDD of a retry stamp (20261102T1904ZR, claimocity_retry_dx.py); None for anything else"""
    m = re.fullmatch(r"(\d{8})T\d{4}ZR", norm_stamp(s)); return m.group(1) if m else None
def iso_now(): return NOW.strftime("%Y-%m-%dT%H:%M:%SZ")

# ---- the written register: what the database already holds ---------------------------------------------------------------------------
reg = {"schema": "practice-db-written/2", "docs": {}}
if os.path.exists(REGF):                                  # fail CLOSED: an unreadable register (conflict markers, a truncated line) must never read as "nothing was sent"
    try:
        with open(REGF, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                line = line.strip()
                if not line: continue
                try: e = json.loads(line)
                except Exception: raise ValueError("line %d is not JSON: %s" % (n, line[:50]))
                if not isinstance(e, dict) or not e.get("k"): raise ValueError("line %d is not a register line: %s" % (n, line[:50]))
                cur = reg["docs"].get(e["k"])
                if cur is None or (e.get("at") or "") >= (cur.get("at") or ""): reg["docs"][e["k"]] = {"at": e.get("at"), "by": e.get("by")}   # the newest line per id wins (union merges may repeat an id)
    except Exception as ex:
        sys.exit("practice_db: the register %s is unreadable (%s) - restore it before building: git checkout origin/main -- practices/ehpa/registers/practice_db_written.jsonl" % (REGF, str(ex)[:90]))
def written(coll, did):
    """True when ANOTHER run already sent this document (this run's own earlier build does not count - a rebuild re-emits it).
    An id named with --resend is rebuilt whatever the register says."""
    if "%s/%s" % (coll, did) in RESEND: return False
    rec = reg["docs"].get("%s/%s" % (coll, did)); return bool(rec) and rec.get("by") != BY
def save_register():
    if NOREG: return
    for k in list(reg["docs"]):
        coll, did = k.split("/", 1)
        base = re.sub(r"\.p\d+$", "", did)                                                                   # a split part: <id>.p2
        d = stamp_day(base) or retry_day(base) or stamp_day(base.split("-", 1)[1] if "-" in base and base.split("-", 1)[0].isalpha() else "")   # snapshots/approvals-<stamp>, feed_batches/<stamp>R
        if coll != "practice" and d and d < FLOOR45: del reg["docs"][k]
    os.makedirs(os.path.dirname(os.path.abspath(REGF)), exist_ok=True)
    with open(REGF, "w", encoding="utf-8", newline="\n") as fh:          # one sorted line per document: git's union merge keeps two runs' additions
        for k in sorted(reg["docs"]):
            fh.write(json.dumps({"k": k, "at": reg["docs"][k].get("at"), "by": reg["docs"][k].get("by")}, separators=(",", ":"), sort_keys=True) + "\n")

# ---- trim: the answer named a document that already exists -------------------------------------------------------------------------------
if CMD == "trim":
    out = opt("--out"); f = opt("--file"); ex = set(opts("--exists"))
    if not (out and f and ex): sys.exit("usage: practice_db.py trim --out <dir> --file <writes file> --exists <collection>/<doc_id> [--exists ...]")
    p = os.path.join(out, f); arr = load(p, None)
    if arr is None: sys.exit("trim: %s not found or not a writes file" % p)
    keep = [e for e in arr if "%s/%s" % (e.get("collection"), e.get("doc_id")) not in ex]
    removed = len(arr) - len(keep)
    for k in ex: reg["docs"][k] = {"at": iso_now(), "by": "trim (already in the database)"}   # a "by" no run owns: never re-emitted, not even by a rebuild of the run that sent it
    if keep: json.dump(keep, open(p, "w", encoding="utf-8"), indent=0); tail = "%d entr%s left in %s - send that file again" % (len(keep), "y" if len(keep) == 1 else "ies", f)
    else: os.remove(p); tail = "%s is now empty and was removed - nothing more to send from it" % f
    save_register()
    print("trim: %d entr%s dropped from the writes file (the database already holds %s); %s" % (removed, "y" if removed == 1 else "ies", ", ".join(sorted(ex)), tail)); sys.exit(0)

# ---- unsent: a refused batch leaves the register --------------------------------------------------------------------------------------
if CMD == "unsent":
    out = opt("--out")
    if not out: sys.exit("usage: practice_db.py unsent --out <dir> [--file writes_N.json] [--exists <collection>/<doc_id> ...]")
    if opt("--file"):
        files = [os.path.join(out, opt("--file"))]
        if not os.path.isfile(files[0]): sys.exit("unsent: %s not found - name the writes file exactly as CALLS.md lists it (nothing changed)" % files[0])
    else:
        files = sorted(glob.glob(os.path.join(out, "writes_*.json")))
        if not files: sys.exit("unsent: no writes_*.json under %s - check --out (nothing changed)" % out)
    exists = set(opts("--exists"))
    n = kept = 0
    for f in files:
        arr = load(f, None)
        if not isinstance(arr, list): sys.exit("unsent: %s is not a writes file (nothing changed)" % f)
        for e in arr:
            key = "%s/%s" % (e.get("collection"), e.get("doc_id"))
            if key in exists: kept += 1; continue
            if reg["docs"].pop(key, None) is not None: n += 1
    save_register()
    if n: print("unsent: %d document id(s) from %d batch file(s) left the register (%d kept as already in the database) - the next build's sweep resends reports, ERA runs, feed batches, feed checks and cascade nights; this run's own snapshots are not resent (the next run writes its own) - to retry this run's own rows now, build the same stamp again and send its writes_1.json [%s]" % (n, len(files), kept, REGF))
    else: print("unsent: nothing left the register - none of the %d batch file(s)' ids was recorded as sent (%d kept as already in the database); nothing to resend [%s]" % (len(files), kept, REGF))
    sys.exit(0)
if CMD != "build": sys.exit("usage: practice_db.py build ... | trim ... | unsent ... (see the header)")

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

docs = []   # (collection, doc_id, body, swept)
_seen = set(); skipped = collections.Counter()
def add(collection, doc_id, body, swept=False):
    if (collection, doc_id) in _seen: return          # a stamp can appear under two spellings (2026-10-20T1328Z and 20261020T1328Z): one document
    _seen.add((collection, doc_id))
    if written(collection, doc_id): skipped[collection] += 1; return     # another run sent it - a second `set` would fail the whole batch
    body = dict(body); body.setdefault("_written", iso_now()); body.setdefault("_source", "tools/db/practice_db.py")
    if swept: body["_swept_by"] = BY
    s = json.dumps(body, separators=(",", ":"))
    if len(s) <= MAXKB * 1024 or "rows" not in body: docs.append((collection, doc_id, body, swept)); return
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
        docs.append((collection, doc_id if i == 0 else "%s.p%d" % (doc_id, i + 1), b, swept))

# ---- feed --------------------------------------------------------------------------------------------------------------------------------
def feed_batch_body(stamp):
    rec = load(os.path.join(REG, "feed_recon_%s.json" % stamp)) or load(os.path.join(WS, "registers", "feed_recon_%s.json" % stamp))
    if not rec: return None
    facs = sorted({r.get("fac") for r in rec["rows"] if r.get("fac")}); cars = sorted({r.get("lead") for r in rec["rows"] if r.get("lead")}); provs = sorted({r.get("prov") for r in rec["rows"] if r.get("prov")})
    return {"schema": "practice-feed-batch/1", "stamp": stamp, "at": rec.get("at") or rec.get("built"), "built": rec.get("built"), "live": rec.get("live"), "files": rec.get("files", []),
            "retry": bool(retry_day(stamp)),                                                                     # a retry batch (claimocity_retry_dx.py): visits an earlier batch skipped
            "dmin": rec.get("dmin"), "dmax": rec.get("dmax"), "counts": rec.get("counts", {}), "rows": rec["rows"],
            "lookups": {"fac": {f: fac_name(f) for f in facs}, "car": {c: CODE2NAME.get(c, c) for c in cars}, "prov": {p: clin(p) for p in provs}},
            "source": "practices/ehpa/registers/feed_recon_%s.json" % stamp}
def feed_batch_doc(stamp, swept=False):
    body = feed_batch_body(stamp)
    if body: add("feed_batches", stamp, body, swept)
    return body

def feed_check_doc(stamp, result, line, batch=None, swept=False):
    regi = load(os.path.join(REG, "claimocity_ingest.json")) or load(os.path.join(WS, "registers", "claimocity_ingest.json")) or {"files": {}, "runs": []}
    run = next((r for r in reversed(regi.get("runs", [])) if norm_stamp(r.get("stamp")) == norm_stamp(stamp)), {})
    files = sorted(regi.get("files", {}), key=lambda k: regi["files"][k].get("at") or "")
    newest = max((re.match(r"\d{8}", k).group(0) for k in regi.get("files", {}) if re.match(r"\d{8}", k)), default=None)
    body = {"schema": "practice-feed-check/1", "stamp": stamp, "at": run.get("at") or (batch or {}).get("at") or iso_now(), "result": result, "line": clip(line, 300),
            "files_registered": len(files), "newest_file": newest, "files_new": len(run.get("files") or []), "live": run.get("live"), "exit": run.get("exit")}
    if batch: body.update({"visits": batch["counts"].get("entered"), "dollars": batch["counts"].get("dollars"), "messages": batch["counts"].get("messages"), "new_charts": batch["counts"].get("new_charts")})
    add("feed_checks", stamp, body, swept)

# ---- billing runs ----------------------------------------------------------------------------------------------------------------------
def run_doc(stamp, swept=False):
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
    add("billing_runs", norm_stamp(stamp), body, swept); return body

# ---- ERA runs ----------------------------------------------------------------------------------------------------------------------------
def era_doc(stamp, swept=False):
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
        tot = x.get("total")
        if not tot:                                   # review round 2: a register that kept each check's unposted amount but no total
            amts = [money(c.get("unpostedamount")) for c in (x.get("checks") or []) if isinstance(c, dict) and c.get("unpostedamount") is not None]
            if amts: tot = round(sum(amts), 2)
        return {"count": x.get("count"), "total": tot, "checks": [c if isinstance(c, str) else {k: v for k, v in c.items() if k in ("id", "check", "checkid", "payer", "amount", "total", "date", "carrier")} for c in (x.get("checks") or [])[:60] if isinstance(c, (str, dict))]}
    body = {"schema": "practice-era-run/1", "stamp": stamp, "at": None, "checks_before": chk(before), "checks_after": chk(after), "lines": lines[:800],
            "line_count": len(lines) if isinstance(new, dict) else None, "paid_total": round(sum(l["paid"] for l in lines), 2), "outcomes": dict(outcomes),
            "audit": {"checks": audit.get("checks", [])[:60], "rows": len(audit.get("rows", [])), "flags": [[clip(x, 60) for x in (f if isinstance(f, list) else [f])] for f in audit.get("flags", [])[:80]]} if isinstance(audit, dict) else None,
            "fallback": {"keys": sorted((fb or {}).keys())[:20]} if isinstance(fb, dict) else None, "dry": bool(new.get("dry")) if isinstance(new, dict) else False,
            "source": "practices/ehpa/registers/era_*_%s.json" % stamp}
    m = re.match(r"(\d{4})-?(\d{2})-?(\d{2})T(\d{2})(\d{2})Z", stamp)
    if m: body["at"] = "%s-%s-%sT%s:%s:00Z" % m.groups()
    if not lines:                                    # review round 1 (11/12/2026): no posted line on file (a run that left only checks before/after) - its report
        rep = rb = None                              # says what the era step did; 17 such runs of 10/19-10/31 read "0 lines" while checks were posted
        for st in report_twins(stamp):               # review round 2: the register's own report first, then its twins - only one whose checks-before count agrees
            r = report_era(st)
            if not r or not (r["touched"] or r["paid"]): continue
            se = r["j"].get("summary", {}).get("era") if isinstance(r["j"].get("summary"), dict) else None
            b4 = se.get("before") if isinstance(se, dict) and isinstance(se.get("before"), dict) else {}
            cnt = (body.get("checks_before") or {}).get("count")
            if cnt is None or b4.get("checks") is None or int(float(b4.get("checks") or 0)) == int(float(cnt or 0)): rep, rb = r, b4; break
        if rep:
            body.update(rep["fields"]); body["report_merged"] = True
            if not body["paid_total"]: body["paid_total"] = rep["paid"]
            body["outcomes"] = dict(rep["outcomes"], **body["outcomes"])
            cb = body.get("checks_before")
            if isinstance(cb, dict) and not cb.get("total") and money(rb.get("unposted")): cb["total"] = money(rb.get("unposted"))
            body["source"] += " + reports/button/%s.json (the era step)" % rep["stamp"]
    add("era_runs", norm_stamp(stamp), body, swept); return body
def era_stamps():
    return sorted({re.sub(r"^era_(new|checks_before|checks_after|audit|fallback_live)_|\.json$", "", os.path.basename(p)) for p in glob.glob(os.path.join(REG, "era_*_20*.json")) if "_dry" not in p})
ERA_OUTCOMES = (("posted (Post button)", "era_post lines"), ("posted (fallback)", "fallback posted"), ("CO-45 corrected", "co45 lines corrected"),
                ("CO-45 for review", "co45 lines for review"), ("checks dismissed", "checks dismissed"), ("checks held", "checks held"), ("denial lines recorded", "denial lines recorded"))
def report_era(stamp):
    """the `era` step of reports/button/<stamp>.json - what the run's own report says its ERA work was - or None (no report, no era step).
    checks_posted = the Post button's presses: era_post.py prints one POST line per check, and the engine counts those lines as 'era_post
    lines'; the report holds no count of the visit lines those checks paid. fallback_lines = lines the fallback posted one by one.
    co45_corrected = lines the Post button had already posted that the CO-45 relink voided and posted again - never added to a posted
    total (review round 1, 11/12/2026: an earlier build summed the three as 'lines posted')."""
    j = load(os.path.join(REPO, "reports", "button", "%s.json" % stamp))
    if not j: return None
    st = next((s for s in (j.get("steps") or []) if isinstance(s, dict) and s.get("name") == "era"), None)
    if not st: return None
    c = st.get("counts") if isinstance(st.get("counts"), dict) else {}; d = st.get("dollars") if isinstance(st.get("dollars"), dict) else {}
    def n(x):
        try: return int(float(x or 0))
        except Exception: return 0
    f = {"checks_posted": n(c.get("era_post lines")), "fallback_lines": n(c.get("fallback posted")), "co45_corrected": n(c.get("co45 lines corrected")),
         "run_url": j.get("run_url") or None, "status": st.get("status"), "summary": clip(st.get("summary"), 300), "errors": [clip(e, 240) for e in (st.get("errors") or [])[:4]]}
    touched = f["checks_posted"] + f["fallback_lines"] + f["co45_corrected"] + n(c.get("checks dismissed")) + n(c.get("checks held")) + n(c.get("co45 lines for review"))
    return {"stamp": stamp, "j": j, "st": st, "c": c, "d": d, "n": n, "fields": f, "touched": touched, "paid": money(d.get("posted this run")),
            "outcomes": {label: n(c.get(k)) for label, k in ERA_OUTCOMES if n(c.get(k))}}
def era_doc_from_report(stamp, swept=False):
    """11/12/2026: the ERA document of a run that left no era_* register on main (the GitHub Actions engine - its registers stay in its own
    workspace), built from the report's `era` step (report_era): checks before/after from summary.era with the check rows the step listed,
    checks posted, fallback lines, CO-45 corrections and dollars posted. line_count stays null - the report does not count posted lines.
    A run that did nothing and left no unposted check gets no document (its quiet look is in billing_runs.summary.era)."""
    rep = report_era(stamp)
    if not rep: return None
    j, st, c, d, n = rep["j"], rep["st"], rep["c"], rep["d"], rep["n"]
    se = j.get("summary", {}).get("era") if isinstance(j.get("summary"), dict) else None
    before = se.get("before") if isinstance(se, dict) and isinstance(se.get("before"), dict) else None
    after = se.get("after") if isinstance(se, dict) and isinstance(se.get("after"), dict) else None
    left = n((after or {}).get("checks"))
    if not rep["touched"] and not left and not money((before or {}).get("unposted")) and not n((before or {}).get("checks")): return None
    rows = [{"check": l.get("check"), "payer": clip(l.get("payer"), 30), "checknumber": l.get("checknumber"), "amount": money(l.get("amount")), "unposted": money(l.get("unposted"))}
            for l in (st.get("lines") or []) if isinstance(l, dict) and l.get("stage") == "before"][:60]
    def chk(x, checks):
        return {"count": n(x.get("checks")), "total": money(x.get("unposted")), "checks": checks} if isinstance(x, dict) else None
    body = {"schema": "practice-era-run/2", "stamp": j.get("stamp") or stamp, "at": st.get("ended") or st.get("started") or j.get("ended") or j.get("started"),
            "checks_before": chk(before, rows), "checks_after": chk(after, []), "lines": [], "line_count": None, "paid_total": rep["paid"],
            "outcomes": rep["outcomes"], "counts": {k: v for k, v in c.items() if isinstance(v, (int, float))}, "dollars": {k: money(v) for k, v in d.items()},
            "audit": None, "fallback": None, "dry": (j.get("mode") or "live") != "live", "engine": True,
            "source": "reports/button/%s.json - the era step (the engine keeps its era_* registers in its own workspace)" % stamp}
    body.update(rep["fields"])
    if not body["at"]:
        m = re.match(r"(\d{4})-?(\d{2})-?(\d{2})T(\d{2})(\d{2})Z", stamp)
        if m: body["at"] = "%s-%s-%sT%s:%s:00Z" % m.groups()
    add("era_runs", norm_stamp(stamp), body, swept); return body

# ---- the nightly insurance cascade (tools/db/cascade_record.py writes the register file at the end of every night) ---------------------
def cascade_doc(stamp, swept=False):
    stem = re.sub(r"^(\d{4})-?(\d{2})-?(\d{2})T(\d{2})(\d{2})Z$", r"\1-\2-\3T\4\5Z", norm_stamp(stamp)) if stamp_day(stamp) else stamp
    j = load(os.path.join(REG, "cascade_runs", stem + ".json"))
    if not j: return None
    body = dict(j); body.setdefault("schema", "practice-cascade-run/1"); body.setdefault("source", "practices/ehpa/registers/cascade_runs/%s.json" % stem)
    add("cascade_runs", stem, body, swept); return body
def cascade_stems():
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(REG, "cascade_runs", "20*.json")))

# ---- snapshots -----------------------------------------------------------------------------------------------------------------------------
def approvals_snapshot(stamp):
    ap = load(os.path.join(REG, "approvals_pending.json"))
    if not ap: return None
    items = [{"id": i.get("id"), "stamp": i.get("stamp"), "at": i.get("at"), "what": clip(i.get("what"), 240), "dollars": i.get("dollars"), "status": i.get("status"),
              "answer": clip(i.get("answer"), 160), "reason": clip(i.get("reason"), 160), "ui": clip(i.get("ui"), 200), "cmd": clip(i.get("cmd"), 200)} for i in ap.get("items", [])]
    st = collections.Counter(i["status"] for i in items)
    add("snapshots", "approvals-%s" % stamp, {"schema": "practice-snapshot/1", "kind": "approvals", "stamp": stamp, "at": iso_now(), "counts": dict(st),
                                              "dollars_waiting": round(sum(money(i["dollars"]) for i in items if i["status"] == "waiting"), 2), "rows": items,
                                              "page": "https://claude.ai/artifact/HuYd2bSm2NxkFgYRqra7wR", "source": "practices/ehpa/registers/approvals_pending.json"})
def repo_snapshot(stamp):
    import subprocess
    def git(*args):
        try: return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception: return ""
    head = git("rev-parse", "--short", "HEAD"); last = git("log", "-1", "--format=%H|%cI|%s")
    counts = {"registers": len(glob.glob(os.path.join(REG, "*.json"))), "button_reports": len(glob.glob(os.path.join(REPO, "reports", "button", "20*.json"))),
              "feed_recon": len(glob.glob(os.path.join(REG, "feed_recon_*.json"))), "helpers": len(glob.glob(os.path.join(REPO, "scripts", "helpers", "*.py"))),
              "cascade_nights": len(cascade_stems())}
    add("snapshots", "repo-%s" % stamp, {"schema": "practice-snapshot/1", "kind": "repo", "stamp": stamp, "at": iso_now(), "head": head,
                                         "last_commit": clip(last, 300), "counts": counts, "repo": "https://github.com/dreffinger/effinger-billing-backend",
                                         "branches": {"main": "the record", "claude/effinger-billing-backend-mirror-w74pqv": "the synced copy the Project reads"}})
def practice_snapshots():
    for name, path in (("carriers", "carriers.json"), ("facilities", "facilities.json"), ("practice", "practice.json")):
        j = load(os.path.join(REPO, "practices", "ehpa", path))
        if j is None: continue
        add("practice", name, {"schema": "practice-master/1", "name": name, "data": j, "source": "practices/ehpa/%s" % path})

# ---- the permanent store and the practice web app (11/12/2026 - the page's "Permanent store and web app" box) ----------------------------
NEON_PROJECT = "steep-rain-79347575"                                    # the Neon project id (tools/mirror/phi_gate.py knows it is not a name)
NEON_CONSOLE = "https://console.neon.tech/app/projects/" + NEON_PROJECT
WEBAPP = {"url": "https://app.ehpa.dev/", "health_url": "https://app.ehpa.dev/health", "alt": "https://ehpa.dev/",
          "host": "Neon Functions - the function ehpadb in the project ehpa-database (not Vercel); custom domains app.ehpa.dev and ehpa.dev"}
def redact(s):
    """driver and OS text can echo a connection string (libpq does for some malformed URIs): nothing stored here or shown on the page carries one"""
    s = re.sub(r"(?i)postgres(?:ql)?://\S*", "postgres://[redacted]", str(s or ""))
    s = re.sub(r"://[^/\s@]*@", "://[redacted]@", s)
    s = re.sub(r"[^\s\x22\x27/@]+:[^\s\x22\x27/@]+@", "[redacted]@", s)                 # user:password@ with or without a scheme (review round 2)
    s = re.sub(r'(percent-encoded (?:token|value): )"[^"]*"', r'\1"[redacted]"', s)    # libpq names the bad token - from inside the password
    return re.sub(r"(?i)\b(password|passwd|pwd)\s*=\s*\S+", r"\1=[redacted]", s)
NEON_PROBE_S = 90         # the whole health call; neon_db.py gets 15 s per wire driver and 30 s for the HTTPS route (NEON_CONNECT_TIMEOUT / NEON_HTTP_TIMEOUT),
                          # so a container that reaches nothing answers in about a minute - inside one shell command's two minutes, with the web probe beside it
def neon_body(stamp):
    """what `neon_db.py health --json` sees: documents, pairs, last load, last routine run, the web app's own access log. reachable=False with a
    short reason when the database cannot be reached from here (no connection string, no path, no answer in time) - redacted, never a URL."""
    import subprocess
    cmd = [sys.executable, os.path.join(REPO, "tools", "db", "neon_db.py"), "health", "--json", "--repo", REPO, "--ws", WS]
    if opt("--neon-url-file"): cmd += ["--url-file", opt("--neon-url-file")]
    body = {"schema": "practice-snapshot/1", "kind": "neon", "stamp": stamp, "at": iso_now(), "reachable": False, "project": NEON_PROJECT, "console": NEON_CONSOLE,
            "source": "tools/db/neon_db.py health --json"}
    env = dict(os.environ, PYTHONUTF8="1", NEON_CONNECT_TIMEOUT="15", NEON_HTTP_TIMEOUT="30")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=NEON_PROBE_S, env=env)
        line = next((l for l in reversed((r.stdout or "").splitlines()) if l.startswith("{")), "")
        if r.returncode == 0 and line:
            body.update(json.loads(line)); body["reachable"] = True
        else:                                     # review rounds 2-3: a stored document gets a fixed phrase, never driver text; blocked = this environment cannot reach Neon
            said = (r.stderr or "") + "\n" + (r.stdout or "")
            if "no connection string" in said:
                body["error"] = "no connection string in this environment (NEON_DATABASE_URL or the git-ignored secrets file)"; body["blocked"] = True
            elif "does not read as a URL" in said:
                body["error"] = "the connection string in this environment does not read as a URL - tools/db/neon_db.py health says how to fix it"
            elif re.search(r"password authentication failed|28P01|HTTP Error 40[13]|is disabled|exceeded|quota|role \S+ does not exist|database \S+ does not exist", said, re.I):
                body["error"] = "the database refused this build's connection (credentials, a disabled endpoint or a quota) - tools/db/neon_db.py health shows the drivers' answers"
            elif "no path to the database" in said:
                body["error"] = "no path to the database from here - tools/db/neon_db.py health shows the drivers' answers"
                body["blocked"] = bool(re.search(r"timed out|timeout|refused|getaddrinfo|Name or service not known|nodename nor servname|Temporary failure in name resolution|failed to resolve host|could not translate host name|Tunnel connection failed|Network is unreachable|No route to host", said, re.I))
            else: body["error"] = "neon_db.py health failed (exit %s) - tools/db/neon_db.py health shows why" % r.returncode
    except subprocess.TimeoutExpired: body["error"] = "neon_db.py did not answer within %d s" % NEON_PROBE_S; body["blocked"] = True
    except Exception as ex: body["error"] = "neon_db.py could not be run (%s)" % type(ex).__name__
    return body
def webapp_body(stamp):
    """does the practice web app answer? GET /health (200 'ok') timed, then GET / for the title. A redirect (a sign-in page, another host) is
    said, never read as the app's 'ok'. From a container whose egress policy refuses the host the probe says blocked=True instead of
    reachable, and the page falls back to the newest probe that got through."""
    import urllib.request, urllib.error, time as _t
    body = {"schema": "practice-snapshot/1", "kind": "webapp", "stamp": stamp, "at": iso_now(), "reachable": False, "blocked": False, "ok": False, "source": "GET %s" % WEBAPP["health_url"]}
    body.update(WEBAPP); hdr = {"User-Agent": "ehpa-practice-db/1 (health probe)"}
    try:
        t0 = _t.time()
        with urllib.request.urlopen(urllib.request.Request(WEBAPP["health_url"], headers=hdr), timeout=15) as r:
            txt = r.read(200).decode("utf-8", "replace"); final = r.geturl(); body.update({"status": r.status, "body": clip(txt.strip(), 40)})
        body["ms"] = int((_t.time() - t0) * 1000); body["reachable"] = True
        if final and final.rstrip("/") != WEBAPP["health_url"].rstrip("/"):
            body["final_url"] = clip(final, 160); body["error"] = clip("redirected to %s" % final, 160)
        body["ok"] = body["status"] == 200 and body["body"].lower().startswith("ok") and not body.get("final_url")
        try:
            with urllib.request.urlopen(urllib.request.Request(WEBAPP["url"], headers=hdr), timeout=15) as r: html = r.read(80000).decode("utf-8", "replace"); body["home_status"] = r.status
            m = re.search(r"<title>(.*?)</title>", html, re.S | re.I); body["title"] = clip(re.sub(r"\s+", " ", m.group(1)).strip(), 80) if m else None
        except Exception as ex: body["home_error"] = clip(redact(ex), 160)
    except urllib.error.HTTPError as ex:
        body.update({"status": ex.code, "reachable": True, "error": clip("HTTP %s %s" % (ex.code, ex.reason), 160)})
    except Exception as ex:
        s = redact(ex); body["error"] = clip(s, 200)
        if re.search(r"403|Forbidden|proxy|Tunnel connection failed|policy|Name or service not known|nodename nor servname", s, re.I): body["blocked"] = True
    return body
def service_snapshots(stamp):
    """snapshots/neon-<stamp> and snapshots/webapp-<stamp>, both probes at once"""
    if NO_SERVICES: return
    import threading
    got = {}
    t = threading.Thread(target=lambda: got.__setitem__("neon", neon_body(stamp)), daemon=True); t.start()
    w = webapp_body(stamp); t.join(NEON_PROBE_S + 15)
    n = got.get("neon") or {"schema": "practice-snapshot/1", "kind": "neon", "stamp": stamp, "at": iso_now(), "reachable": False, "project": NEON_PROJECT, "console": NEON_CONSOLE,
                            "source": "tools/db/neon_db.py health --json", "error": "neon_db.py did not answer within %d s" % NEON_PROBE_S}
    add("snapshots", "neon-%s" % stamp, n); add("snapshots", "webapp-%s" % stamp, w)

def report_groups():
    """reports/button/<stamp>[-engine|-routine|-sweep].json grouped by document id (norm_stamp drops the suffix), the plain name first -
    '-' sorts before '.', so a suffixed twin used to take the id by glob order (review round 1, 11/12/2026)"""
    by = collections.OrderedDict()
    for p in sorted(glob.glob(os.path.join(REPO, "reports", "button", "20*.json"))):
        st = os.path.basename(p)[:-5]; by.setdefault(norm_stamp(st), []).append(st)
    return [sorted(v, key=lambda s: (bool(re.search(r"-[a-z]+$", s)), s)) for v in by.values()]
_RG = None
def report_twins(stamp):
    """the reports that share this stamp's document id: the stamp's own first, then the plain name, then suffixed twins"""
    global _RG
    if _RG is None: _RG = {norm_stamp(g[0]): g for g in report_groups()}
    g = _RG.get(norm_stamp(stamp)) or []
    return ([stamp] if stamp in g else []) + [s for s in g if s != stamp]

# ---- the sweep: what main holds and the database does not yet (the last SWEEP_DAYS days) -------------------------------------------------
def sweep():
    floor = (NOW - datetime.timedelta(days=SWEEP_DAYS)).strftime("%Y%m%d")
    for group in report_groups():
        d = stamp_day(group[0])
        if d and d >= floor and not written("billing_runs", norm_stamp(group[0])): run_doc(group[0], swept=True)
    for st in era_stamps():
        d = stamp_day(st)
        if d and d >= floor and not written("era_runs", norm_stamp(st)): era_doc(st, swept=True)
    have_reg = {norm_stamp(s) for s in era_stamps()}                                   # 11/12: the engine's postings - a report on main, no era_* register
    for group in report_groups():
        d = stamp_day(group[0]); nid = norm_stamp(group[0])
        if d and d >= floor and nid not in have_reg and not written("era_runs", nid):
            for st in group:                                                            # twins: the first whose era step did something
                if era_doc_from_report(st, swept=True): break
    for p in sorted(glob.glob(os.path.join(REG, "feed_recon_*R.json"))):               # 11/12: retry batches (claimocity_retry_dx.py) - skipped visits of earlier batches, entered later
        st = re.sub(r"^feed_recon_|\.json$", "", os.path.basename(p)); d = retry_day(st)
        if d and d >= floor and not written("feed_batches", st):
            body = feed_batch_body(st)
            if body: add("feed_batches", st, body, True)
    for p in sorted(glob.glob(os.path.join(REG, "feed_recon_*.json"))):
        st = re.sub(r"^feed_recon_|\.json$", "", os.path.basename(p)); d = stamp_day(st)
        if not (d and d >= floor): continue
        body = feed_batch_body(st) if not written("feed_batches", st) else None
        if body: add("feed_batches", st, body, True)
        if not written("feed_checks", st): feed_check_doc(st, "ingested", "swept from practices/ehpa/registers on main", body or feed_batch_body(st), True)
    regi = load(os.path.join(REG, "claimocity_ingest.json")) or {}                     # feed runs that ingested nothing have no recon file: their check row comes from the ingest register
    for run in (regi.get("runs") or []) if isinstance(regi, dict) else []:
        st = norm_stamp(run.get("stamp", "")); d = stamp_day(st)
        if not (d and d >= floor) or written("feed_checks", st): continue
        body = feed_batch_body(st)
        feed_check_doc(st, "ingested" if (run.get("files") or body) else "nothing_new", "swept from registers/claimocity_ingest.json on main", body, True)
    for stem in cascade_stems():
        d = stamp_day(stem)
        if d and d >= floor and not written("cascade_runs", stem): cascade_doc(stem, swept=True)

# ---- assemble ----------------------------------------------------------------------------------------------------------------------------
made = collections.Counter(); made_swept = collections.Counter()
if RUN:
    st = norm_stamp(RUN)
    b = feed_batch_doc(st)
    if not NO_FEED_CHECK:
        result = opt("--check-result") or ("ingested" if b else "nothing_new")
        feed_check_doc(st, result, opt("--check-line", ""), b)
    r = run_doc(RUN) or run_doc(st)
    e = era_doc(RUN) or era_doc(re.sub(r"(\d{4})(\d{2})(\d{2})T", r"\1-\2-\3T", st)) or era_doc_from_report(RUN) or era_doc_from_report(re.sub(r"(\d{4})(\d{2})(\d{2})T", r"\1-\2-\3T", st))
    cascade_doc(RUN)
    approvals_snapshot(st); repo_snapshot(st); service_snapshots(st)
    if not NO_SWEEP: sweep()
elif SWEEP_ONLY:
    sweep(); service_snapshots(BUILD)
elif ALL:
    for p in sorted(glob.glob(os.path.join(REG, "feed_recon_*.json"))) or sorted(glob.glob(os.path.join(WS, "registers", "feed_recon_*.json"))):
        st = re.sub(r"^feed_recon_|\.json$", "", os.path.basename(p))
        if not stamp_day(st) or stamp_day(st) < SINCE: continue
        b = feed_batch_doc(st); feed_check_doc(st, "ingested", "backfill from registers", b or feed_batch_body(st))
    for group in report_groups():
        if not stamp_day(group[0]) or stamp_day(group[0]) < SINCE: continue
        run_doc(group[0])
    for st in era_stamps():
        if not stamp_day(st) or stamp_day(st) < SINCE: continue
        era_doc(st)
    have_reg = {norm_stamp(s) for s in era_stamps()}
    for group in report_groups():
        if not stamp_day(group[0]) or stamp_day(group[0]) < SINCE or norm_stamp(group[0]) in have_reg: continue
        for st in group:
            if era_doc_from_report(st): break
    for p in sorted(glob.glob(os.path.join(REG, "feed_recon_*R.json"))):
        st = re.sub(r"^feed_recon_|\.json$", "", os.path.basename(p))
        if not retry_day(st) or retry_day(st) < SINCE: continue
        feed_batch_doc(st)
    for stem in cascade_stems():
        if not stamp_day(stem) or stamp_day(stem) < SINCE: continue
        cascade_doc(stem)
    approvals_snapshot(BUILD); repo_snapshot(BUILD); practice_snapshots(); service_snapshots(BUILD)
elif PRACTICE:
    practice_snapshots()
else:
    sys.exit("usage: practice_db.py build --run <stamp> | --sweep | --all [--since YYYYMMDD] | --practice   (trim / unsent: see the header)")

os.makedirs(os.path.join(OUT, "docs"), exist_ok=True)
for f in os.listdir(OUT):
    if f.startswith("writes_") and f.endswith(".json"): os.remove(os.path.join(OUT, f))
def pack(entries, prefix):
    batches, cur, cur_bytes = [], [], 0
    for coll, did, body, _ in entries:
        fn = os.path.join(OUT, "docs", "%s__%s.json" % (coll.replace("/", "~"), did))
        s = json.dumps(body, separators=(",", ":")); open(fn, "w", encoding="utf-8").write(s)
        entry = {"op": "set", "collection": coll, "doc_id": did, "file_path": fn}
        if cur and (len(cur) >= 50 or cur_bytes + len(s) > 900 * 1024): batches.append(cur); cur, cur_bytes = [], 0
        cur.append(entry); cur_bytes += len(s)
    if cur: batches.append(cur)
    names = []
    for i, b in enumerate(batches):
        name = "writes_%s%d.json" % (prefix, i + 1); names.append(name)
        json.dump(b, open(os.path.join(OUT, name), "w", encoding="utf-8"), indent=0)
    return names, batches
def doc_day(coll, did, body):
    """the day a swept document belongs to (its stamp), for one sweep file set per day"""
    for s in (body.get("stamp"), re.sub(r"\.p\d+$", "", did), (body.get("at") or "")[:10].replace("-", "") + "T0000Z"):
        d = stamp_day(str(s)) if s else None
        if d: return d
    return "other"
resend = [d for d in docs if "%s/%s" % (d[0], d[1]) in RESEND]; docs_new = [d for d in docs if "%s/%s" % (d[0], d[1]) not in RESEND]
own = [d for d in docs_new if not d[3]]; swept = [d for d in docs_new if d[3]]
for coll, _, _, _ in own: made[coll] += 1
for coll, _, _, _ in swept: made_swept[coll] += 1
own_names, own_batches = pack(own, "")
sw_names, sw_batches = [], []
rs_names, rs_batches = pack(resend, "resend_") if resend else ([], [])
for day in sorted({doc_day(c, i, b) for c, i, b, _ in swept}, reverse=True):
    n, bb = pack([x for x in swept if doc_day(x[0], x[1], x[2]) == day], "sweep_%s_" % day); sw_names += n; sw_batches += bb
for coll, did, _, _ in docs: reg["docs"]["%s/%s" % (coll, did)] = {"at": iso_now(), "by": BY}
unreached = sorted(RESEND - {"%s/%s" % (c, i) for c, i, _, _ in docs})
for k in unreached: print("practice_db: --resend %s was NOT rebuilt - this build never reached it (outside --sweep-days, a typo, or no record of it on main); widen --sweep-days or use --all" % k, file=sys.stderr)
save_register()
calls = ["# ehpa Practice Database - calls for this build (%s%s)" % (BUILD, SINCE_NOTE), "",
         "This run's documents: " + (", ".join("%s %d" % kv for kv in sorted(made.items())) or "none"),
         "Swept from main (other runs' records the database did not have yet): " + (", ".join("%s %d" % kv for kv in sorted(made_swept.items())) or "none"),
         "Already in the database, not sent again: " + (", ".join("%s %d" % kv for kv in sorted(skipped.items())) or "none"), "",
         "For each writes file below make ONE ArtifactData call: action \"batch\", url \"%s\", writes = the file's JSON array verbatim (each entry is {op, collection, doc_id, file_path}; every doc_id is new as far as the register knows, so no if_version - writes_resend_N.json, below, is the one exception)." % URL,
         "Two answers need a hand: (a) the answer names a document that ALREADY EXISTS (the register had fallen behind the database): `python3 tools/db/practice_db.py trim --out %s --file <that writes file> --exists <collection>/<doc_id>` drops that one entry (the register keeps it) - send the same file again, and repeat while the answer names another document; never `unsent` for this. (b) the call was refused, asked for an approval, answered quota_exceeded / invalid_argument or any other error: do not retry it - `python3 tools/db/practice_db.py unsent --out %s --file <that writes file>` takes its ids back out of the register so the next run resends them; report it (quota_exceeded / invalid_argument verbatim) and go on." % (OUT, OUT),
         (("DRY BUILD (--no-register): nothing was recorded in the register %s - do not send these files; build again without --no-register to send them." % REGF) if NOREG else "The register %s now lists every document above as sent. Commit and push it RIGHT AFTER the batch calls (every run, before any later rebase or mirror step): `cd %s && git add practices/ehpa/registers/practice_db_written.jsonl && git commit -q -m \"practice db register %s\" && git pull -q --rebase --autostash origin main && git push origin HEAD:main` (nothing to commit = fine; a rejected push is reported, never forced; the file merges line by line with another run's)." % (REGF, REPO, RUN or BUILD)),
         "Run the build ONCE per run. A second build of the same stamp re-emits this run's own files (and sweeps again); send only what was not sent before.",
         "PERMANENT STORE (Neon Postgres - William 11/6/2026: \"have all the routines send the outputs and all to this database as well\"): right after the batch calls, ONE plain command copies the same documents (this run's and the swept ones) into the practice's HIPAA database: `cd %s && python3 tools/db/neon_db.py load-writes --out %s`, then `python3 tools/db/neon_db.py run-log --routine \"<this routine's name>\" --stamp %s --status ok|partial|failed --headline \"<the report's one line>\"` records the run in ops.routine_runs. Each prints one line for the report. The connection string is NEON_DATABASE_URL (an environment credential of the ehpa cloud environment) or, when absent, secrets/neon_database_url written once per container from the Gmail thread 'neon database url' (like the other keys; never Drive, never committed); 'no connection string', 'no path to the database' (the egress policy blocks the Neon hosts) or 'REFUSED' is reported verbatim and never retried - the artifact batches above stand on their own; when it failed, run the same command again next run with this --out." % (REPO, OUT, RUN or BUILD), ""]
for name, b in zip(own_names, own_batches): calls.append("- %s : %d documents (%s)" % (name, len(b), ", ".join(sorted({e['collection'] for e in b}))))
for name, b in zip(sw_names, sw_batches): calls.append("- %s : %d swept documents (%s)" % (name, len(b), ", ".join(sorted({e['collection'] for e in b}))))
for name, b in zip(rs_names, rs_batches): calls.append("- %s : %d RESENT documents (%s) - each REPLACES a document the database holds: read it (ArtifactData get) and add its version to the entry as if_version before the batch call. Never trim or unsent this file: if the answer names a changed version, read that document again, fix its if_version and send the file again; if this folder is lost, build again with the same --resend ids" % (name, len(b), ", ".join(sorted({e['collection'] for e in b}))))
if unreached: calls.append("- --resend NOT rebuilt (this build never reached them - widen --sweep-days or use --all): " + ", ".join(unreached))
if not docs: calls.append("- nothing to write: every document is already in the database")
open(os.path.join(OUT, "CALLS.md"), "w", encoding="utf-8").write("\n".join(calls) + "\n")
print("practice_db build %s -> %s : %d document(s) in %d batch file(s) [%s] + %d swept in %d sweep file(s) [%s]%s; %d already in the database%s%s" % (
    BUILD, OUT, len(own), len(own_names), ", ".join("%s %d" % kv for kv in sorted(made.items())) or "-", len(swept), len(sw_names),
    ", ".join("%s %d" % kv for kv in sorted(made_swept.items())) or "-", (" + %d resent in %d file(s) (need if_version)" % (len(resend), len(rs_names))) if resend else "",
    sum(skipped.values()), "" if NOREG else "; register updated", SINCE_NOTE))
