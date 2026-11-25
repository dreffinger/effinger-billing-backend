# PLAIN ENGLISH (Claimocity feed ingest - the routine step, William 10/28/2026 23:05 ET: "let the claimocity feed just pile up the files
#   there, leave them there and just pull the data we need, import the charges and be done - no need for Gregg").
# One command turns a folder of NEW Claimocity DFT^P03 files (copied from the SFTP by the Cloud Run job into Drive 'Claimocity drop' and
# downloaded by the routine) into AdvancedMD charges exactly the way the 10/28 backlog import did, in this order:
#   1 parse       feed_parse_dft (CR/LF-agnostic)              -> feed_parsed_<stamp>.json
#   2 dx cache    claimocity_dx (lookupdiagcode codeset=10)    -> dx_cache_feed.json (shared, grows)
#   3 match       registers/claimocity_patient_map.json first (Claimocity patient id -> AMD chart from every earlier run), then
#                 claimocity_match + claimocity_resolve for the unknown patients (lookuppatient by name + DOB; several same-DOB charts ->
#                 the one with the most recent charge)                                  -> feed_match_<stamp>.json
#   4 new charts  claimocity_newcharts (addpatient + updaterespparty + addinsurance from IN1, member id IN1-49)   [--live only]
#   5 import      claimocity_import (addvisit + updvisitwithnewcharges + admission date; dedupe = register + live CPT+DOS check)
#   6 verify      claimocity_verify (AMD 271 per plan, deceased guard, Stedi discovery when nothing active, visit insorder) [--live]
#   7 inspector   claimocity_inspector (facility/POS fixes, admission dates, advisory bypasses)                               [--live]
#   8 report      claimocity_report -> feed_digest_<stamp>.md + PHI-light registers/feed_verify_<stamp>.json
# Idempotent: registers/claimocity_ingest.json remembers every file (sha256) already ingested; a file is never processed twice unless
#   --reprocess; inside a batch the import's own register + live-charge check make a re-run a no-op.
# Never deletes or moves anything on Claimocity or Drive. Dry mode (default) parses, matches against the map, and lists what WOULD be
#   created (the import's --dry reads AMD; it writes nothing). Exit 0 = done, 2 = a step failed (see logs/claimocity_<stamp>_<step>.log).
# Usage: python3 claimocity_ingest.py --hl7-dir <folder of *.hl7> [--stamp <UTC stamp>] [--live] [--limit N]
#        [--skip-verify] [--skip-inspector] [--no-stedi] [--reprocess]
import os, sys, json, glob, hashlib, shutil, subprocess, datetime, collections, re
WS = "/home/claude/unbilled"
def utcnow(): return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)   # naive UTC, no deprecation warning
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
def opt(name, default=None):
    return a[a.index(name) + 1] if name in a else default
hl7_dir = opt("--hl7-dir"); live = "--live" in a; limit = opt("--limit"); reprocess = "--reprocess" in a
stamp = opt("--stamp", utcnow().strftime("%Y%m%dT%H%MZ"))
# any stamp form is accepted (the routines write 2026-10-29T0121Z, this script 20261029T0121Z): keep digits/T/Z only, so the
# chart prefix F<yymmdd> (first free -NN, probed by claimocity_newcharts) and every feed_*_<stamp>.json name come out the same whichever form the caller passed
stamp = re.sub(r"[^0-9TZ]", "", stamp)
if not re.match(r"^\d{8}T\d{4}Z$", stamp): sys.exit("stamp must look like 20261029T0121Z (or 2026-10-29T0121Z); got %r" % stamp)
if not hl7_dir: sys.exit("usage: claimocity_ingest.py --hl7-dir <folder> [--stamp S] [--live] [--limit N] [--skip-verify] [--skip-inspector] [--no-stedi] [--reprocess]")
os.chdir(WS); os.makedirs("registers", exist_ok=True); os.makedirs("logs", exist_ok=True); os.makedirs("hl7", exist_ok=True)
REGF = "registers/claimocity_ingest.json"
reg = json.load(open(REGF)) if os.path.exists(REGF) else {"files": {}, "runs": []}
MAPF = "registers/claimocity_patient_map.json"
pmap = json.load(open(MAPF)) if os.path.exists(MAPF) else {}
env = dict(os.environ, FEED_STAMP=stamp, FEED_DX_CACHE=os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json"),
           FEED_CHART_PREFIX=os.environ.get("FEED_CHART_PREFIX", "F" + stamp[2:8]), PYTHONPATH=WS + ":" + HERE)
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
def step(name, cmd, must=True):
    log = "logs/claimocity_%s_%s.log" % (stamp, name)
    with open(log, "w") as fh:
        r = subprocess.run(cmd, cwd=WS, env=env, stdout=fh, stderr=subprocess.STDOUT, text=True)
    tail = open(log).read().strip().splitlines()[-3:]
    print("[%s] exit %d  %s" % (name, r.returncode, " | ".join(t[:110] for t in tail)))
    if r.returncode and must:
        print("STEP FAILED:", name, "- see", log); finish(2)
    return r.returncode
def finish(code):
    reg["runs"].append({"stamp": stamp, "at": utcnow().isoformat() + "Z", "live": live, "files": files, "exit": code})
    json.dump(reg, open(REGF, "w"), indent=1); sys.exit(code)
# ---- which files are new ----------------------------------------------------------------------------------------------
batch = os.path.join("hl7", stamp); os.makedirs(batch, exist_ok=True)
files = []
def sftp_name(b): return re.sub(r"^(download__)+", "", b)   # Drive copies are named download__<sftp name>; the register keys the SFTP name
known_sha = {v.get("sha256") for v in reg["files"].values()}
for f in sorted(glob.glob(os.path.join(hl7_dir, "*.hl7"))):
    b = sftp_name(os.path.basename(f)); s = sha(f)
    if os.path.getsize(f) == 0: print("empty file skipped:", b); continue
    if not reprocess and ((b in reg["files"] and reg["files"][b].get("sha256") == s) or s in known_sha): continue   # same name+content or same content under another name
    shutil.copy(f, os.path.join(batch, b)); files.append(b)
print("stamp %s | %d new file(s) of %d in %s | mode %s" % (stamp, len(files), len(glob.glob(os.path.join(hl7_dir, "*.hl7"))), hl7_dir, "LIVE" if live else "DRY"))
# ---- the feed helpers are the repository's (11/10/2026, reviewers C2 and W1) --------------------------------------------------------------
# The place-of-service rule lives in claimocity_import.py (marker = its POS_RULE_VERSION line, the one mirror.py protects). On EVERY run - also when
# nothing is new, so the retry of the same routine runs current helpers too - every feed helper here is compared with the repository clone's copy
# and replaced when it differs (claimocity_helpers_current.make_current, the one function this driver and claimocity_retry_dx.py share). Without a
# clone each helper is checked by its version line. An old helper is said at the end of the RESULT line, never a reason to hold a visit (rules.md part 6).
POS_RULE = 'POS_RULE_VERSION = "2026-11-25.1"'; REPO_HELPERS = "/home/claude/effinger-billing-backend/scripts/helpers"
def _helpers_current():
    """(console lines, RESULT warning) from make_current in claimocity_helpers_current.py - the copy here, else the clone's."""
    for _p in (os.path.join(HERE, "claimocity_helpers_current.py"), os.path.join(REPO_HELPERS, "claimocity_helpers_current.py")):
        try:
            import importlib.util as _iu; _sp = _iu.spec_from_file_location("claimocity_helpers_current", _p); _m = _iu.module_from_spec(_sp); _sp.loader.exec_module(_m)
            return _m.make_current(HERE, REPO_HELPERS, POS_RULE)
        except Exception: continue
    try: _ok = POS_RULE in open(os.path.join(HERE, "claimocity_import.py"), errors="replace").read()
    except OSError: _ok = False
    return [], " | FEED HELPERS NOT CHECKED: claimocity_helpers_current.py is missing here and in the repository%s" % ("" if _ok else " | PLACE OF SERVICE RULE NOT CURRENT: claimocity_import.py here is missing, an old copy or an earlier version of the rule and no repository copy was found - for William to check: the place of service of every nursing-building line this run entered, and the clinician and building of every visit whose patient has another message in the batch (a routine changes nothing on these visits)")
_hl, pos_warn = _helpers_current()
for _l in _hl: print(_l)
if not files:
    print("nothing new - done"); finish(0)
env["FEED_HL7_DIR"] = os.path.abspath(batch)
# ---- 1 parse, 2 dx -----------------------------------------------------------------------------------------------------------
step("parse", [sys.executable, "-I", os.path.join(WS, "feed_parse_dft_1028.py"), env["FEED_HL7_DIR"], "feed_parsed_%s.json" % stamp])
parsed = json.load(open("feed_parsed_%s.json" % stamp))
step("dx", [sys.executable, os.path.join(HERE, "claimocity_dx.py")])
# ---- 3 match: the map first, lookups only for unknown patients ---------------------------------------------------------------
known, unknown = {}, []
for m in parsed:
    key = m["name"].upper().strip() + "|" + m["dob"][:8]
    if m["pid"] in pmap:
        e = known.setdefault(key, {"status": "FOUND", "pids": [pmap[m["pid"]]], "amd_names": [], "feed_ids": [], "resolved": pmap[m["pid"]], "via": "patient map"})
        if m["pid"] not in e["feed_ids"]: e["feed_ids"].append(m["pid"])
    else:
        unknown.append(m)
json.dump(unknown, open("feed_unknown_%s.json" % stamp, "w"), indent=1)
print("match: %d patients known from the map, %d message(s) from %d unknown patient(s) need a lookup" % (len(known), len(unknown), len({(m["name"], m["dob"][:8]) for m in unknown})))
matchf = "feed_match_%s.json" % stamp
if unknown:
    step("match", [sys.executable, os.path.join(HERE, "claimocity_match.py"), "feed_unknown_%s.json" % stamp])
    step("resolve", [sys.executable, os.path.join(HERE, "claimocity_resolve.py")])
    looked = json.load(open(matchf))
else:
    looked = {}
looked.update(known); json.dump(looked, open(matchf, "w"), indent=1)
c = collections.Counter((v["status"], bool(v.get("resolved"))) for v in looked.values())
print("match result:", dict(c))
# ---- 4 new charts (live) -----------------------------------------------------------------------------------------------------
missing = [k for k, v in looked.items() if v["status"] == "MISSING" and not v.get("resolved")]
if missing:
    if live: step("newcharts", [sys.executable, os.path.join(HERE, "claimocity_newcharts.py")])
    else: print("DRY: %d patient(s) would get a NEW chart (addpatient + IN1 insurance): %s" % (len(missing), ", ".join(k.split("|")[0][:4] + "*" for k in missing)[:200]))
# ---- 5 import -------------------------------------------------------------------------------------------------------------------
# (the feed helpers were made the repository's at the start of this run - make_current above; pos_warn says what could not be)
cmd = [sys.executable, os.path.join(HERE, "claimocity_import.py"), "--all" if live else "--dry"]
if limit: cmd += ["--limit", str(limit)]
step("import", cmd)
# the patient map learns every chart this batch touched (feed patient id -> AMD chart), for the next run
looked = json.load(open(matchf))
for v in looked.values():
    if v.get("resolved"):
        for fid in v.get("feed_ids", []): pmap[fid] = v["resolved"]
json.dump(pmap, open(MAPF, "w"), indent=0, sort_keys=True)
# ---- 6 verify, 7 inspector, 8 report (live) --------------------------------------------------------------------------------------
if live:
    if "--skip-verify" not in a:
        vc = [sys.executable, os.path.join(HERE, "claimocity_verify.py")] + (["--no-stedi"] if "--no-stedi" in a else [])
        step("verify", vc, must=False)
    if "--skip-inspector" not in a:
        step("inspector", [sys.executable, os.path.join(HERE, "claimocity_inspector.py")], must=False)
    step("report", [sys.executable, os.path.join(HERE, "claimocity_report.py")], must=False)
    step("recon", [sys.executable, os.path.join(HERE, "claimocity_recon.py"), stamp], must=False)   # registers/feed_recon_<stamp>.json: every message and its AMD outcome (the Practice Database's feed_batches document)
# ---- register the files ------------------------------------------------------------------------------------------------------------
impf = "registers/feed_import_%s.json" % stamp
imp = json.load(open(impf)) if os.path.exists(impf) else {"created": [], "skipped": [], "failed": []}
for b in files:
    msgs = [m for m in parsed if m["file"] == b[:8] or b.startswith(m["file"])]
    if live:
        reg["files"][b] = {"stamp": stamp, "sha256": sha(os.path.join(batch, b)), "messages": len(msgs), "at": utcnow().isoformat() + "Z"}
print("RESULT stamp %s: files %d, messages %d, visits created %d, skipped %d, failed %d%s" % (
    stamp, len(files), len(parsed), len(imp["created"]), len(imp["skipped"]), len(imp["failed"]), ("" if live else " (DRY - nothing written, files not registered)") + pos_warn))
if live and os.path.exists("feed_digest_%s.md" % stamp): print("digest: feed_digest_%s.md" % stamp)
finish(0)
