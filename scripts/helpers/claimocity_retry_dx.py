# PLAIN ENGLISH (Claimocity feed: retry the visits an earlier batch skipped as "no usable dx for <CPT>").
# Why: AdvancedMD only accepts diagnosis codes that are in the PRACTICE's diagnosis list (Master Files > Diagnosis Codes). A valid ICD-10
#   code the practice never used before (10/31/2026: M51.17 and M51.86, chart F261031-04, two hospital visits) is "not in AMD" to
#   lookupdiagcode, so claimocity_import.py skips the visit and records it under "skipped" with why "no usable dx for <CPT>". Once
#   William adds the code to AMD's list, this driver enters those visits - nothing else re-reads a file the register already knows.
# 11/12/2026: the same for the "unknown CPT <code>" skips (99349 home visits, batches 10/30 and 11/6): once the code is in claimocity_import.py's
#   PCODE table the visit is retried like a dx skip; a code the import still does not know is printed ("still waiting on CPT codes the import
#   does not know: ...") for the report. The feed step runs this driver every run right after the ingest (runbook step c1), so a cleared skip
#   is entered by the next run - with --live only; dry prints what it would enter. Review round 1 (11/12/2026): a visit is left alone once the
#   registers show AdvancedMD has every code of it - created rows of any batch AND the recon rows entered / already / voided (the import's
#   "already" answer leaves no created row, so a skip it answered that way used to be retried on every run); a code counts as known only when
#   it is in both PCODE and FEE; this run's row goes into claimocity_ingest.json before the recon, which reads its time and mode there.
# Decides: nothing new. For every skipped-dx row in registers/feed_import_*.json whose (patient, DOS, CPT set) was never created:
#   1 gets the batch's parsed messages (feed_parsed_<stamp>.json, else re-parses hl7/<stamp>/, else re-downloads the batch's files from
#     the bucket with claimocity_gcs.py --fetch), 2 re-checks the codes in AMD (claimocity_dx.py looks null codes up again), 3 imports
#     only the messages whose every charge line now has a usable code, under a NEW stamp <now>R (import, verify, inspector, report -
#     the same scripts as claimocity_ingest.py; dedupe is the registers + the chart's live charges, so a retry is a no-op the second time).
# Codes still missing are printed: "still wait on codes not in AMD's diagnosis list: M51.17, M51.86" - that line goes into the digest
#   under Holds, with the fix: William adds the code in AMD (Master Files > Diagnosis Codes > New, ICD-10 code + description).
# Dry by default (prints what would be entered, writes nothing in AMD); --live enters. Exit 0 done (also when nothing to retry), 2 a step failed.
# Usage: cd /home/claude/unbilled && python3 claimocity_retry_dx.py [--live] [--stamp <UTC stamp>] [--no-stedi]
import os, sys, re, json, glob, subprocess, datetime, collections
WS = "/home/claude/unbilled"; HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(WS)
a = sys.argv[1:]; live = "--live" in a
def opt(name, default=None): return a[a.index(name) + 1] if name in a else default
def utcnow(): return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
rstamp = re.sub(r"[^0-9TZ]", "", opt("--stamp", utcnow().strftime("%Y%m%dT%H%MZ"))) + "R"
def mdy(yyyymmdd): return "%s/%s/%s" % (yyyymmdd[4:6], yyyymmdd[6:8], yyyymmdd[0:4])
# 11/10/2026 (reviewers W1, C2): the retry enters charges with the same import helper as the ingest, so before anything runs it makes the feed
# helpers here the repository's copies exactly as the ingest does - the one shared function claimocity_helpers_current.make_current: with the clone
# there, every helper that differs is replaced by the clone's copy; without one, each is checked by its version line. It never holds a visit for
# this (rules.md part 6): what could not be made current is said at the end of the RESULT line and goes to the top of the report.
POS_RULE = 'POS_RULE_VERSION = "2026-11-25.1"'; REPO_HELPERS = "/home/claude/effinger-billing-backend/scripts/helpers"
REPO_REGS = os.path.join(os.path.dirname(os.path.dirname(REPO_HELPERS)), "practices", "ehpa", "registers")   # the recon registers on main (the workspace copies come first); derived, so the selftest sandbox moves it too
def _helpers_current():
    """(console lines, RESULT warning) from make_current in claimocity_helpers_current.py - the copy here, else the clone's."""
    for _p in (os.path.join(HERE, "claimocity_helpers_current.py"), os.path.join(REPO_HELPERS, "claimocity_helpers_current.py")):
        try:
            import importlib.util as _iu; _sp = _iu.spec_from_file_location("claimocity_helpers_current", _p); _m = _iu.module_from_spec(_sp); _sp.loader.exec_module(_m)
            return _m.make_current(HERE, REPO_HELPERS, POS_RULE)
        except Exception: continue
    try: _ok = POS_RULE in open(os.path.join(HERE, "claimocity_import.py"), errors="replace").read()
    except OSError: _ok = False
    return [], " | FEED HELPERS NOT CHECKED: claimocity_helpers_current.py is missing here and in the repository%s" % ("" if _ok else " | PLACE OF SERVICE RULE NOT CURRENT: claimocity_import.py here is missing, an old copy or an earlier version of the rule and no repository copy was found - for William to check: the place of service, the building and the clinician of every visit this retry entered (a routine changes nothing on these visits)")
_hl, pos_warn = _helpers_current()
for _l in _hl: print(_l)
REGF = "registers/claimocity_ingest.json"
reg = json.load(open(REGF)) if os.path.exists(REGF) else {"files": {}, "runs": []}
pmap = json.load(open("registers/claimocity_patient_map.json")) if os.path.exists("registers/claimocity_patient_map.json") else {}

# ---- 1 what was skipped for dx or an unknown CPT, and what has been created since ------------------------------------------------
def _known_cpts():
    """the CPT codes claimocity_import.py can enter (the copy that will run - here, else the repository's): the codes in BOTH its PCODE and FEE
    tables - a code in PCODE alone would fail at the fee lookup and be retried every run (review round 1); HCPCS-style codes count too"""
    for p in (os.path.join(HERE, "claimocity_import.py"), os.path.join(REPO_HELPERS, "claimocity_import.py")):
        try: src = open(p, errors="replace").read()
        except OSError: continue
        mp = re.search(r"^PCODE\s*=\s*\{(.*?)\}", src, re.S | re.M); mf = re.search(r"^FEE\s*=\s*\{(.*?)\}", src, re.S | re.M)
        if mp and mf: return set(re.findall(r'"([0-9A-Z]{5})"\s*:\s*"pcode\d+"', mp.group(1))) & set(re.findall(r'"([0-9A-Z]{5})"\s*:\s*"[0-9.]+"', mf.group(1)))
    return set()
KNOWN_CPTS = _known_cpts(); unknown_cpts = set()
want = {}          # stamp -> {feed patient id: the CPT codes its skips name} - review round 2: a visit is retried only when it carries one of them
nocpt = set()      # review round 3: feed ids whose skip named no code at all (a feed line without a CPT) - for William; the import itself keeps out a
                   # visit after a recorded date of death or on a chart flagged deceased, reading both fresh on every run (no guard here can go stale)
covered = collections.defaultdict(set)   # (feed patient id, MM/DD/YYYY) -> the CPT codes AdvancedMD has for that visit
for rf in sorted(glob.glob("registers/feed_import_*.json")):
    if rf.endswith("_decisions.json"): continue
    try: r = json.load(open(rf))
    except Exception: continue
    stamp = re.sub(r"^registers/feed_import_|\.json$", "", rf)
    for row in r.get("created", []):
        if row.get("feed_id"):
            cp = row.get("cpts") or []; dl = row.get("dos_lines") or [row.get("dos")] * len(cp)
            for c_, d_ in zip(cp, dl): covered[(row["feed_id"], d_)].add(c_)       # review round 3: each line under its own date (a message can carry two)
            if row.get("dos_feed"): covered[(row["feed_id"], row["dos_feed"])].update(cp)
    for row in r.get("skipped", []):
        why = str(row.get("why", ""))
        if why.startswith("no usable dx"): want.setdefault(stamp, {}).setdefault(row["feed_id"], set()).add(why.split()[-1].strip())
        elif why.startswith("unknown CPT"):                                    # 11/12: retried once the import knows the code
            mc = re.match(r"unknown CPT (\S+)\s*$", why)
            if not mc: nocpt.add(str(row.get("feed_id") or "?"))
            elif mc.group(1) in KNOWN_CPTS: want.setdefault(stamp, {}).setdefault(row["feed_id"], set()).add(mc.group(1))
            else: unknown_cpts.add(mc.group(1))
# review round 1: what AdvancedMD got, from the recon registers - a visit the import answered "already" (the chart carries it) has no created row,
# and its skip row stays in the old batch for good; without this it was fetched, imported and reconciled again on every run
for rf in sorted(set(glob.glob("registers/feed_recon_*.json")) | set(glob.glob(os.path.join(REPO_REGS, "feed_recon_*.json")))):
    try: rows = (json.load(open(rf)) or {}).get("rows") or []
    except Exception: continue
    sure = lambda x: x.get("s") in ("entered", "voided") or (x.get("s") == "already" and x.get("why") == "all lines already in AMD")
    mixed = {x.get("f") for x in rows if not sure(x)}      # review round 2: the recon hands a patient's skip rows out in order, so with two outcomes in one
    for row in rows:                                       # batch an 'already' can sit on the wrong visit - one counts only when every row of that patient is certain
        if sure(row) and (row.get("s") != "already" or row.get("f") not in mixed) and row.get("f") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row.get("d") or "")):
            covered[(row["f"], mdy(row["d"].replace("-", "")))].update(row.get("c") or [])
def unknown_note():
    s = (" | still waiting on CPT codes the import does not know: " + ", ".join(sorted(unknown_cpts)) + " (add them to PCODE and FEE in claimocity_import.py)") if unknown_cpts else ""
    return s + ((" | a feed line without a CPT code (feed ids %s) - for William: Claimocity sent the visit with no code" % ", ".join(sorted(nocpt))) if nocpt else "")
UNKNOWN_NOTE = unknown_note()
if not want:
    print("retry-dx: nothing to retry (no 'no usable dx' skip and no 'unknown CPT' skip the import can enter now in the registers)" + UNKNOWN_NOTE); sys.exit(0)

# ---- 2 the messages behind those skips ------------------------------------------------------------------------------------------
def parsed_for(stamp):
    pf = "feed_parsed_%s.json" % stamp
    if os.path.exists(pf): return json.load(open(pf))
    batch = os.path.join("hl7", stamp); os.makedirs(batch, exist_ok=True)
    if not glob.glob(os.path.join(batch, "*.hl7")):
        names = [n for n, v in reg.get("files", {}).items() if v.get("stamp") == stamp]
        if not names: print("retry-dx: batch %s - no files in the register, cannot re-read" % stamp); return []
        c = subprocess.run([sys.executable, os.path.join(HERE, "claimocity_gcs.py"), "--fetch", ",".join(names), "--dest", batch], capture_output=True, text=True)
        print("retry-dx: fetched batch %s files: %s" % (stamp, (c.stdout.strip().splitlines() or ["?"])[0][:160]))
        for f in glob.glob(os.path.join(batch, "download__*.hl7")):      # the bucket names carry the download__ prefix; the parser keys files by their first 8 digits
            os.replace(f, os.path.join(batch, re.sub(r"^(download__)+", "", os.path.basename(f))))
    if not glob.glob(os.path.join(batch, "*.hl7")): return []
    c = subprocess.run([sys.executable, "-I", os.path.join(WS, "feed_parse_dft_1028.py"), os.path.abspath(batch), pf], capture_output=True, text=True)
    if c.returncode or not os.path.exists(pf): print("retry-dx: parse of batch %s failed: %s" % (stamp, (c.stdout + c.stderr)[-200:])); return []
    return json.load(open(pf))

msgs = []
for stamp, ids in sorted(want.items()):
    for m in parsed_for(stamp):
        if m["pid"] not in ids: continue
        cpts = {c["cpt"] for c in m["FT1"]}
        if not cpts & ids[m["pid"]]: continue                                    # another visit of that patient - not the one the skip names
        if cpts - KNOWN_CPTS: unknown_cpts.update(c for c in cpts - KNOWN_CPTS if c); continue   # review round 3: a second code the import does not know yet
        if all(c["cpt"] in covered.get((m["pid"], mdy(c["dos"][:8])), set()) for c in m["FT1"]): continue   # every line, under its own date, is in AdvancedMD
        m = dict(m); m["_batch"] = stamp; msgs.append(m)
UNKNOWN_NOTE = unknown_note()
if not msgs:
    print("retry-dx: nothing to retry (every skipped visit that can be retried has been entered since)" + UNKNOWN_NOTE); sys.exit(0)

# ---- 3 re-check the codes in AMD (null cache entries are looked up again) ---------------------------------------------------------
env = dict(os.environ, FEED_STAMP=rstamp, FEED_DX_CACHE=os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json"), PYTHONPATH=WS + ":" + HERE)
json.dump(msgs, open("feed_parsed_%s.json" % rstamp, "w"), indent=1)
os.makedirs("logs", exist_ok=True)
def step(name, cmd, must=True):
    log = "logs/claimocity_%s_%s.log" % (rstamp, name)
    with open(log, "w") as fh: r = subprocess.run(cmd, cwd=WS, env=env, stdout=fh, stderr=subprocess.STDOUT, text=True)
    tail = open(log).read().strip().splitlines()[-3:]
    print("[%s] exit %d  %s" % (name, r.returncode, " | ".join(t[:110] for t in tail)))
    if r.returncode and must: print("STEP FAILED:", name, "- see", log); sys.exit(2)
    return r.returncode
step("dx", [sys.executable, os.path.join(HERE, "claimocity_dx.py")])
cache = json.load(open(env["FEED_DX_CACHE"]))
ready, waiting, missing = [], 0, set()
for m in msgs:
    ok = True
    for c in m["FT1"]:
        codes = [x.strip() for x in (c.get("dx") or "").split("^") if x.strip()]
        if not any(cache.get(x) for x in codes):
            ok = False; missing.update(x for x in codes if not cache.get(x))
    if ok: ready.append(m)
    else: waiting += 1
if not ready:
    print("retry-dx: %d visit(s) still wait on codes not in AMD's diagnosis list: %s (valid ICD-10 - William adds them in AMD Master Files > Diagnosis Codes; the next run enters the visits)" % (waiting, ", ".join(sorted(missing))))
    os.remove("feed_parsed_%s.json" % rstamp); sys.exit(0)

# ---- 4 import (+ verify, inspector, report when live) under the retry stamp ----------------------------------------------------------
json.dump(ready, open("feed_parsed_%s.json" % rstamp, "w"), indent=1)
match = {}
for m in ready:
    key = m["name"].upper().strip() + "|" + m["dob"][:8]; pid = pmap.get(m["pid"])
    if not pid: print("retry-dx: feed patient %s has no chart in the patient map - skipped" % m["pid"]); continue
    e = match.setdefault(key, {"status": "FOUND", "pids": [pid], "amd_names": [], "feed_ids": [], "resolved": pid, "via": "patient map (retry)"})
    if m["pid"] not in e["feed_ids"]: e["feed_ids"].append(m["pid"])
json.dump(match, open("feed_match_%s.json" % rstamp, "w"), indent=1)
batches = sorted({m["_batch"] for m in ready})
# 11/10/2026: the import reads the building (and with it the place of service), the provider and the admission date from the raw files.
# One batch folder was not enough: a visit of any other batch, or of a batch whose parsed file was on hand without its HL7 folder, was
# entered with NO facility at the default 31. Every batch's files go into one folder; a batch whose files cannot be had is not retried.
# The import finds each message's OWN building, clinician and admission date in that folder by the message's patient id and its
# (code, DOS) lines (claimocity_import.msg_own), so a hospital visit of one batch and a nursing visit of another keep their own.
import shutil
hdir = os.path.join("hl7", rstamp); os.makedirs(hdir, exist_ok=True); nohl7 = []
for b in batches:
    if not glob.glob(os.path.join("hl7", b, "*.hl7")):
        names = [n for n, v in reg.get("files", {}).items() if v.get("stamp") == b]
        if names:
            os.makedirs(os.path.join("hl7", b), exist_ok=True)
            subprocess.run([sys.executable, os.path.join(HERE, "claimocity_gcs.py"), "--fetch", ",".join(names), "--dest", os.path.join("hl7", b)], capture_output=True, text=True)
            for f in glob.glob(os.path.join("hl7", b, "download__*.hl7")): os.replace(f, os.path.join("hl7", b, re.sub(r"^(download__)+", "", os.path.basename(f))))
    got = glob.glob(os.path.join("hl7", b, "*.hl7"))
    if not got: nohl7.append(b)
    for f in got: shutil.copy(f, os.path.join(hdir, b + "_" + os.path.basename(f)))
if nohl7:
    ready = [m for m in ready if m["_batch"] not in nohl7]
    batches = [b for b in batches if b not in nohl7]
    print("retry-dx: batch(es) %s - the feed files are not on hand and could not be fetched; their visits wait for the next run (never entered without a building)" % ", ".join(nohl7))
    json.dump(ready, open("feed_parsed_%s.json" % rstamp, "w"), indent=1)
    if not ready: os.remove("feed_parsed_%s.json" % rstamp); sys.exit(0)
env["FEED_HL7_DIR"] = os.path.abspath(hdir)
# (the feed helpers were made the repository's at the start of this run - make_current above; pos_warn says what could not be)
print("retry-dx stamp %s | %d visit(s) from batch(es) %s now have usable codes%s | mode %s" % (rstamp, len(ready), ", ".join(batches), ("; %d still wait on %s" % (waiting, ", ".join(sorted(missing)))) if waiting else "", "LIVE" if live else "DRY"))
def save_run_row():
    """this retry's row in registers/claimocity_ingest.json, written BEFORE the recon - claimocity_recon.py reads the run's time and mode from it
    (review round 1: the row used to come last, so feed_recon_<stamp>R.json carried at=null, live=null). The register is read again first: the
    steps above may have written it, and the copy loaded at the start must not overwrite them."""
    cur = json.load(open(REGF)) if os.path.exists(REGF) else {"files": {}, "runs": []}
    runs = cur.setdefault("runs", [])
    if not any(r.get("stamp") == rstamp and bool(r.get("live")) == live for r in runs): runs.append({"stamp": rstamp, "at": utcnow().isoformat() + "Z", "live": live, "files": [], "retry_of": batches, "exit": 0})
    json.dump(cur, open(REGF, "w"), indent=1)
step("import", [sys.executable, os.path.join(HERE, "claimocity_import.py"), "--all" if live else "--dry"])
if live:
    step("verify", [sys.executable, os.path.join(HERE, "claimocity_verify.py")] + (["--no-stedi"] if "--no-stedi" in a else []), must=False)
    step("inspector", [sys.executable, os.path.join(HERE, "claimocity_inspector.py")], must=False)
    step("report", [sys.executable, os.path.join(HERE, "claimocity_report.py")], must=False)
    save_run_row()
    step("recon", [sys.executable, os.path.join(HERE, "claimocity_recon.py"), rstamp], must=False)
impf = "registers/feed_import_%s.json" % rstamp
imp = json.load(open(impf)) if os.path.exists(impf) else {"created": [], "skipped": [], "failed": []}
save_run_row()
print("RESULT retry %s: visits created %d, skipped %d, failed %d%s%s" % (rstamp, len(imp["created"]), len(imp["skipped"]), len(imp["failed"]),
      "" if live else " (DRY - nothing written)", (" | still waiting on codes: " + ", ".join(sorted(missing))) if waiting else "") + UNKNOWN_NOTE + pos_warn)
if live and os.path.exists("feed_digest_%s.md" % rstamp): print("digest: feed_digest_%s.md" % rstamp)
