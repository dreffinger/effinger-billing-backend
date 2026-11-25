# PLAIN ENGLISH (Claimocity feed ingest - the routine step, William 10/28/2026 23:05 ET: "let the claimocity feed just pile up the files
#   there, leave them there and just pull the data we need, import the charges and be done - no need for Gregg").
# One command turns a folder of NEW Claimocity DFT^P03 files (copied from the SFTP by the Cloud Run job into Drive 'Claimocity drop' and
# downloaded by the routine) into AdvancedMD charges exactly the way the 10/28 backlog import did, in this order:
#   1 parse       feed_parse_dft (CR/LF-agnostic)              -> feed_parsed_<stamp>.json
#   2 dx cache    claimocity_dx (lookupdiagcode codeset=10)    -> dx_cache_feed.json (shared, grows)
#   3 match       registers/claimocity_patient_map.json first (Claimocity patient id -> AMD chart from every earlier run), then for the
#                 patients the map does not know claimocity_match (gathers the same-name charts) + claimocity_resolve (decides by the
#                 identity rule of feed_identity.py - William 11/25/2026: a patient the feed sends with a WRONG birth date or the
#                 placeholder goes to the chart that patient already has, never to a second one)   -> feed_match_<stamp>.json
#   4 new charts  claimocity_newcharts (only where the identity rule says NEW CHART: addpatient + updaterespparty + addinsurance from
#                 IN1, member id IN1-49)                                                                              [--live only]
#   5 import      claimocity_import (addvisit + updvisitwithnewcharges + admission date; dedupe = register + live CPT+DOS check)
#   6 verify      claimocity_verify (AMD 271 per plan, deceased guard, Stedi discovery when nothing active, visit insorder) [--live]
#   7 inspector   claimocity_inspector (facility/POS fixes, admission dates, advisory bypasses)                               [--live]
#   8 report      claimocity_report -> feed_digest_<stamp>.md + PHI-light registers/feed_verify_<stamp>.json
# Idempotent: registers/claimocity_ingest.json remembers every file (sha256) already ingested; a file is never processed twice unless
#   --reprocess. A file whose ingest did not finish is read again by the next start under a NEW stamp: what is in AdvancedMD answers
#   'all lines already in AMD', what is missing is entered. A second LIVE start under the SAME stamp is REFUSED (11/25/2026): the import
#   resumes that stamp's register and passes over every message of a patient it lists as skipped - also one the first start never reached.
# THE PATIENT MAP (11/25/2026): the REPOSITORY's patient map answers where it differs from this workspace's. A chart corrected on main - a
#   feed patient re-pointed from a duplicate chart to the proper one (William 11/9/2026: "if a duplicate chart shows up with visits in it
#   just put the visits in the proper chart") - reaches the next ingest; until then the workspace's restored map sent the patient's next
#   visits to the duplicate again. To re-point a feed patient, change the repository's map - never only the workspace's.
# WHICH CHART AND WHY goes to main (11/25/2026): a live run writes registers/feed_identity_<stamp>.json - for every feed patient that was
#   looked up the chart, the rule number and the rule's fixed words, never a name, a birth date or a number of a patient (the match file,
#   which holds those, never leaves the workspace). A field that is not one of the fixed words is withheld, not copied.
# A FILE IS NOT REGISTERED while a patient of it has no chart (11/25/2026) - a new chart AdvancedMD refused, a patient the rule could not
#   decide: the next start reads it again. Until then such a file was registered as done and the visit was never entered or retried
#   (11/13/2026: three chart numbers in a row were taken, the patient got no chart, the visit was lost).
# (11/25/2026) TWO FEED PATIENTS UNDER ONE NAME AND ONE BIRTH DATE: every entry of the match file names the chart of EACH Claimocity id
#   ("by_id") and the import asks by the message's own id - a new id beside a known one goes where the identity rule sends it, never to
#   the known chart by the name alone, and two known ids each keep their own chart.
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
    print("[%s] exit %d  %s" % (name, r.returncode, " | ".join(t[:160] for t in tail)))      # 160: the import's place-of-service line is about 120 characters with real counts (it was cut at 110)
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
POS_RULE = 'POS_RULE_VERSION = "2026-11-25.3"'; REPO_HELPERS = "/home/claude/effinger-billing-backend/scripts/helpers"
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
# ---- the REPOSITORY's patient map answers where the two differ (11/25/2026) -----------------------------------------------------------------
# The workspace's map comes back from the state bundle and can be days old; the mirror keeps MAIN's chart on main where the two disagree
# ("a person decides") - but this driver took a known patient from the workspace's map as it was, so a chart corrected on main never
# reached the feed. Now main's chart replaces the workspace's for every feed patient the two name differently, a patient only main knows
# is added, and the workspace's file is written at once - also on a day with no new file. A value on main that is no chart id is passed
# over; a map on main that cannot be read changes nothing and is said. (The path is the clone's, taken from REPO_HELPERS.)
REPO_MAP = os.path.join(os.path.dirname(os.path.dirname(REPO_HELPERS)), "practices", "ehpa", "registers", "claimocity_patient_map.json")
CHART_ID = re.compile(r"^pat[0-9]+$")
def show_id(fid):      # a Claimocity id is 24 hex characters; anything else is not printed (it could be anything a sender typed)
    return fid if re.fullmatch(r"[0-9A-Fa-f]{24}", str(fid or "")) else "(an id that is not 24 hex characters)"
repointed = []         # [{"feed_id", "was", "now"}] - the identity register carries it to main and the report prints it
def _main_map():
    if not os.path.exists(REPO_MAP): return
    try:
        main = json.load(open(REPO_MAP))
        if not isinstance(main, dict): raise ValueError("no JSON object")
    except Exception as e:
        print("PATIENT MAP: the repository's map could not be read (%s) - this workspace's map is used as it is, so a chart corrected on main does not reach this run - TOP OF THE REPORT" % type(e).__name__); return
    added = 0
    for fid, chart in main.items():
        if not (isinstance(fid, str) and fid and isinstance(chart, str) and CHART_ID.match(chart)): continue
        if fid not in pmap: pmap[fid] = chart; added += 1
        elif pmap[fid] != chart:
            repointed.append({"feed_id": fid, "was": pmap[fid] if isinstance(pmap[fid], str) and CHART_ID.match(pmap[fid]) else "", "now": chart}); pmap[fid] = chart
    if repointed or added:
        json.dump(pmap, open(MAPF, "w"), indent=0, sort_keys=True)
        print("PATIENT MAP: %d feed patient(s) now go to the repository's chart%s; %d added from the repository's map" % (
            len(repointed), (" - " + ", ".join("%s (was %s, now %s)" % (show_id(x["feed_id"]), x["was"] or "?", x["now"]) for x in repointed[:20]) + (" (+%d more)" % (len(repointed) - 20) if len(repointed) > 20 else "")) if repointed else "", added))
_main_map()
# ---- the identity rule's own words (feed_identity.py - the copy here, else the clone's) -------------------------------------------------------
# Loaded only for its fixed words and for problems(), the proof that an entry holds nothing but fixed words, chart ids and rule numbers.
# Without it (a workspace and a clone that both lack the file) nothing of an entry is copied to the register: every field is withheld.
ID_FIELDS = ("rule", "why", "flags", "candidates", "evidence", "feed_dob", "for_william")      # = feed_identity.PHI_FREE_FIELDS (the self-test holds the two together)
def _identity():
    for _p in (os.path.join(HERE, "feed_identity.py"), os.path.join(REPO_HELPERS, "feed_identity.py")):
        try:
            import importlib.util as _iu; _sp = _iu.spec_from_file_location("feed_identity", _p); _m = _iu.module_from_spec(_sp); _sp.loader.exec_module(_m)
            if all(hasattr(_m, a_) for a_ in ("WHY_MAP", "WHY_SHARED", "IDENTITY_RULE_VERSION", "PHI_FREE_FIELDS", "problems", "real_dob")): return _m      # a file of that name that is not the rule (an older or a broken copy) is not used
        except Exception: continue
    return None
FI = _identity()
WHY_MAP = FI.WHY_MAP if FI else "known from the patient map"; WHY_SHARED = FI.WHY_SHARED if FI else "several Claimocity ids under one name are not known to be one person"
def _real(d8):
    try: return bool(FI.real_dob(d8, utcnow().strftime("%Y%m%d"))) if FI else bool(re.fullmatch(r"(19[0-9]{2}|20[0-9]{2})[0-9]{4}", d8)) and not d8.startswith("1900")
    except Exception: return False
if not files:
    print("nothing new - done"); finish(0)
# ---- a second LIVE start under the SAME stamp is refused, before anything is touched (11/25/2026, independent review) ----------------------
# claimocity_import.py resumes a stamp's register (no created row is lost) and, on that resume, counts every patient the register lists as
# skipped as done - every message of that patient, also one the first start never reached. Such a message is then in no created / skipped /
# failed row, this driver registers the file, and the charge is never entered and never retried (the review reproduced it with the real
# import: a CCM 99487 lost that way; main's registers show a patient with a skipped and an entered message in one batch in 2 of 26).
# A start under a NEW stamp has no register to resume: it reads the file from the top and the chart's live charges decide each line.
_prior_reg = "registers/feed_import_%s.json" % stamp
if live and os.path.exists(_prior_reg):
    print("STEP FAILED: stamp %s already has an import register (%s) from an earlier start. A second start under the SAME stamp would pass over whole patients - "
          "start the ingest again under a NEW stamp (this stamp plus one minute), with a log of that name: it reads the same file again, enters what is missing "
          "and answers 'all lines already in AMD' for the rest." % (stamp, _prior_reg))
    finish(2)
env["FEED_HL7_DIR"] = os.path.abspath(batch)
# ---- 1 parse, 2 dx -----------------------------------------------------------------------------------------------------------
step("parse", [sys.executable, "-I", os.path.join(WS, "feed_parse_dft_1028.py"), env["FEED_HL7_DIR"], "feed_parsed_%s.json" % stamp])
parsed = json.load(open("feed_parsed_%s.json" % stamp))
step("dx", [sys.executable, os.path.join(HERE, "claimocity_dx.py")])
# ---- 3 match: the map first, lookups only for unknown patients ---------------------------------------------------------------
# EVERY ENTRY NAMES THE CHART OF EACH CLAIMOCITY ID ("by_id", 11/25/2026). The match file is keyed by name and birth date, and until now the
# import took a message's chart from that key alone - so two feed patients under one name and birth date (a namesake; the placeholder
# date; a second Claimocity id of one person) shared ONE chart: a new id beside a known one silently got the known chart and its own
# decision was dropped, and of two known ids the first one's chart was used for both. Now each id keeps its own: a known id the chart the
# map names for it, a looked-up id the chart the identity rule chose (or the new chart made for it), an id nobody decided none - and the
# import asks by the message's own id (claimocity_import.py chart_of). "resolved" stays what it was for a reader that does not know by_id.
def _key(m): return str(m.get("name") or "").upper().strip() + "|" + str(m.get("dob") or "")[:8]      # the import's own key (chart_of), also for a message that carries no name or date
known, unknown = {}, []; notes = []      # notes: lines for William the driver itself has to say (Claimocity ids and chart ids only) - printed, and carried to main by the identity register
known_ids = set()
for m in parsed:
    key = _key(m)
    if m["pid"] in pmap:
        chart = pmap[m["pid"]]; known_ids.add(m["pid"])
        # the entry carries the same fields as one the identity rule decided (rule "map" and the map's fixed words), so every reader finds them
        e = known.setdefault(key, {"status": "FOUND", "pids": [chart], "amd_names": [], "feed_ids": [], "resolved": chart, "via": "patient map", "by_id": {},
                                   "rule": "map", "why": WHY_MAP, "flags": [], "candidates": [], "evidence": [], "feed_dob": "real" if _real(m["dob"][:8]) else "none", "for_william": False})
        e["by_id"][m["pid"]] = chart
        if m["pid"] not in e["feed_ids"]: e["feed_ids"].append(m["pid"])
    else:
        unknown.append(m)
for key, e in known.items():
    if len(set(e["by_id"].values())) > 1:      # said, not held: each visit goes to its own id's chart
        print("PATIENT MAP: %d Claimocity ids under one name and birth date go to %d charts (%s) - each visit goes to its own id's chart; if they are one person the charts are duplicates" % (
            len(e["by_id"]), len(set(e["by_id"].values())), ", ".join("%s on %s" % (show_id(i), c) for i, c in sorted(e["by_id"].items()))))
json.dump(unknown, open("feed_unknown_%s.json" % stamp, "w"), indent=1)
print("match: %d patients known from the map, %d message(s) from %d unknown patient(s) need a lookup" % (len(known), len(unknown), len({(m["name"], m["dob"][:8]) for m in unknown})))
matchf = "feed_match_%s.json" % stamp
if unknown:
    step("match", [sys.executable, os.path.join(HERE, "claimocity_match.py"), "feed_unknown_%s.json" % stamp])
    step("resolve", [sys.executable, os.path.join(HERE, "claimocity_resolve.py")])
    looked = json.load(open(matchf))
else:
    looked = {}
shared = sorted(k for k in known if k in looked)      # a name-and-date key a KNOWN id shares with a looked-up one: the identity rule's entry stays (the new-chart step works on it), the known ids come in below
for k, e in known.items():
    if k not in looked: looked[k] = e
json.dump(looked, open(matchf, "w"), indent=1)
c = collections.Counter((v["status"], bool(v.get("resolved"))) for v in looked.values())
print("match result:", dict(c))
# ---- 4 new charts (live) -----------------------------------------------------------------------------------------------------
missing = [k for k, v in looked.items() if v["status"] == "MISSING" and not v.get("resolved")]
if missing:
    if live: step("newcharts", [sys.executable, os.path.join(HERE, "claimocity_newcharts.py")])
    else:      # a count and the Claimocity ids - never a letter of a name (until 11/25/2026 it printed the first four)
        _new = sorted({tuple(looked[k].get("decided_for") or looked[k].get("feed_ids") or [k]) for k in missing})
        print("DRY: %d patient(s) would get a NEW chart (addpatient + IN1 insurance) - Claimocity id(s): %s" % (len(_new), ", ".join(show_id(i[0]) for i in _new)[:600]))
# ---- the chart of each Claimocity id, written into the match file before the import reads it ----------------------------------------------
looked = json.load(open(matchf))
for k, v in looked.items():
    by = dict(known[k]["by_id"]) if k in known else {}                     # a known id: the chart the map names for it - never another
    if v.get("rule") != "map" and CHART_ID.match(str(v.get("resolved") or "")):
        for i in (v.get("decided_for") or v.get("feed_ids") or []): by.setdefault(i, v["resolved"])      # a looked-up id: the chart the rule chose, or the new chart made for it
    v["by_id"] = by
    if k in shared:
        v["decided_chart"] = v.get("resolved") or ""; v["resolved"] = known[k]["resolved"]      # for a reader that does not know by_id the key reads as it always did: the known chart
json.dump(looked, open(matchf, "w"), indent=1)
# ---- 5 import -------------------------------------------------------------------------------------------------------------------
# (the feed helpers were made the repository's at the start of this run - make_current above; pos_warn says what could not be)
cmd = [sys.executable, os.path.join(HERE, "claimocity_import.py"), "--all" if live else "--dry"]
if limit: cmd += ["--limit", str(limit)]
step("import", cmd)
# the patient map learns every chart this batch touched (feed patient id -> AMD chart), for the next run - each id its own chart
looked = json.load(open(matchf))
for v in looked.values():
    for fid, chart in (v.get("by_id") or {}).items():
        if fid and CHART_ID.match(str(chart or "")): pmap[fid] = chart
json.dump(pmap, open(MAPF, "w"), indent=0, sort_keys=True)
# ---- a file is not registered while a patient of it has no chart (11/25/2026) -------------------------------------------------------------------
# No chart = the match file, as the import read it, names no chart for the message's Claimocity id: a new chart AdvancedMD refused
# (claimocity_newcharts.py: 'new chart not made'), a patient the identity rule could not decide (rule 0). The import passes such a
# message over ("no chart") and writes no row for it - and until now the file was registered as done all the same.
def _nochart(m):      # a message that IS a visit of somebody (a patient id and at least one charge line - the import passes any other over) and has no chart
    return bool(m.get("pid")) and bool(m.get("FT1")) and not ((looked.get(_key(m)) or {}).get("by_id") or {}).get(m["pid"])
held_files = sorted(b for b in files if any(_nochart(m) for m in parsed if m["file"] == b[:8] or b.startswith(m["file"]))) if live else []
held_ids = sorted({str(m["pid"]) for m in parsed if _nochart(m)}) if live else []
if held_files:
    print("NOT REGISTERED: %d file(s) hold a patient with no chart - %s - Claimocity id(s) %s: the next start reads them again (a visit already in AdvancedMD answers 'all lines already in AMD') - TOP OF THE REPORT" % (
        len(held_files), ", ".join(held_files[:20]) + (" (+%d more)" % (len(held_files) - 20) if len(held_files) > 20 else ""), ", ".join(show_id(i) for i in held_ids[:20]) + (" (+%d more)" % (len(held_ids) - 20) if len(held_ids) > 20 else "")))
# ---- which chart and why: registers/feed_identity_<stamp>.json (live; the mirror carries it to main) ----------------------------------------------
def _safe_id(i): return i if isinstance(i, str) and re.fullmatch(r"[0-9A-Za-z]{6,40}", i) else "(odd id)"
def _identity_register():
    rows = []; seen = set()
    for k, v in looked.items():
        if v.get("rule") == "map": continue                                # known from the map: counted below, not listed
        ids = tuple(i for i in (v.get("decided_for") or v.get("feed_ids") or []) if i not in known_ids)      # the ids the rule decided - on a key they share with a known id, not that one
        if ids in seen: continue                                           # the same answer stands under every name-and-date key of the patient
        seen.add(ids)
        chart = next((c for c in ((v.get("by_id") or {}).get(i) for i in ids) if CHART_ID.match(str(c or ""))), "")
        row = {"feed_ids": [_safe_id(i) for i in ids], "chart": chart, "status": v.get("status") if v.get("status") in ("FOUND", "AMBIGUOUS", "MISSING") else "", "new_chart": bool(chart) and v.get("rule") == 9}
        bad = FI.problems(v) if FI else list(ID_FIELDS)                    # what is NOT a fixed word, a chart id or a rule number is never copied
        for f in ID_FIELDS:
            if f not in bad: row[f] = v.get(f)
        if bad: row["withheld"] = sorted(bad)
        rows.append(row)
    doc = {"stamp": stamp, "at": utcnow().isoformat() + "Z", "identity_rule": FI.IDENTITY_RULE_VERSION if FI else "",
           "counts": {"known from the patient map": len(known_ids), "looked up": len(rows), "new charts": sum(1 for r_ in rows if r_["new_chart"]),
                      "for William": sum(1 for r_ in rows if r_.get("for_william") is True), "no chart": sum(1 for r_ in rows if not r_["chart"])},
           "repointed": repointed, "patients": rows, "notes": notes, "not_registered": held_files}
    tmp = "registers/feed_identity_%s.json.tmp" % stamp
    json.dump(doc, open(tmp, "w"), indent=1); os.replace(tmp, "registers/feed_identity_%s.json" % stamp)
if live:
    try: _identity_register()
    except Exception as _e: print("IDENTITY REGISTER NOT WRITTEN (%s) - which chart each new feed patient went to is in logs/claimocity_%s_resolve.log only - TOP OF THE REPORT" % (type(_e).__name__, stamp))
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
    if live and b not in held_files:
        reg["files"][b] = {"stamp": stamp, "sha256": sha(os.path.join(batch, b)), "messages": len(msgs), "at": utcnow().isoformat() + "Z"}
print("RESULT stamp %s: files %d, messages %d, visits created %d, skipped %d, failed %d%s%s" % (
    stamp, len(files), len(parsed), len(imp["created"]), len(imp["skipped"]), len(imp["failed"]), (", %d file(s) NOT registered (a patient with no chart - read again by the next start)" % len(held_files)) if held_files else "",
    ("" if live else " (DRY - nothing written, files not registered)") + pos_warn))
if live and os.path.exists("feed_digest_%s.md" % stamp): print("digest: feed_digest_%s.md" % stamp)
finish(0)
