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
# NO VISIT OF THE FEED IS LOST WITHOUT A WORD (11/25/2026, the independent verification of the rules above - each found a visit that was never
#   entered while its file was registered as done). A file is NOT REGISTERED, either, while
#   - a message of it could not be read, or carries no Claimocity id (the parse step counts each by file date and message number in
#     registers/feed_unreadable_<stamp>.json): every start reads the file again and says so, until the copy that is read is whole. Until then
#     such a file was registered after one line whose advice could not work - every feed file is named by its day, the copy job never copies
#     a name the bucket holds, and the download step took only names this register did not know. The register now records the SIZE of each
#     file it registers, and claimocity_gcs.py fetches a registered file again when the bucket's copy has another size;
#   - AdvancedMD refused one of its visits at the first call (the import's failed row 'addvisit: ...' - nothing was made): the next start
#     reads the file again and the import tries once more. A failed row that says a visit WAS made, or that nobody knows what AdvancedMD
#     kept, never keeps a file back (reading it again would make a second empty visit in every run): it stands at the top of the digest.
#   WHAT ENDS SUCH A HOLD when the visit can never be entered - Claimocity cannot send the message again, AdvancedMD will never take the
#   visit: William's word, and then ONE start with --register-anyway <file>[,<file>]. It registers the file and says at the top what is
#   given up. It never registers a file that holds a patient with NO chart - that is settled by a chart, never by giving the visit up.
#   THE DRIVER'S OWN LINES FOR WILLIAM end ' - TOP OF THE REPORT' wherever they are printed, and a live run carries them to main in the
#   identity register ("notes" - until then that list was never filled), from where the digest prints them at the top. The lines about a
#   file that is kept back travel as lists of their own (not_registered, not_registered_unreadable, not_registered_refused,
#   registered_anyway and, by its cause, registered_anyway_unreadable / registered_anyway_refused). A NEW CHART WHOSE RUN WAS CUT
#   before its digest: the next run says at its top what was for William about that chart
#   (from the cut run's new-chart register) and writes the identity register the cut run did not, so that it is said once.
#   A patient whose only message carries nothing to enter is not looked up and gets no chart in this run (the message may be one the file
#   ended in, its patient line cut short too).
# Never deletes or moves anything on Claimocity or Drive. Dry mode (default) parses, matches against the map, and lists what WOULD be
#   created (the import's --dry reads AMD; it writes nothing). A DRY RUN LEAVES THE PATIENT MAP ALONE (11/25/2026): until then it wrote
#   every chart the identity rule chose into the map, and the live run after it took those patients as known - none of the rule's lines
#   for William was said. It takes the repository's chart in memory only, registers no file, writes no identity register and takes the
#   parse step's count of unreadable messages away again. What a dry run still writes, none of it a decision about a patient: its own
#   row in the file register's list of runs (marked not live), this stamp's working files and logs, what the diagnosis-code look-up
#   answered (the code cache), the feed helpers made the repository's (as at every start), and this workspace's copies of the two
#   registers whose home is the repository (William's standing word 'same person'; the rehab monitor's when the repository's is later).
#   Exit 0 = done, 2 = a step failed (see logs/claimocity_<stamp>_<step>.log).
# Usage: python3 claimocity_ingest.py --hl7-dir <folder of *.hl7> [--stamp <UTC stamp>] [--live] [--limit N]
#        [--skip-verify] [--skip-inspector] [--no-stedi] [--reprocess] [--register-anyway <file>[,<file>]]   (the last ONLY on William's word)
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
if not hl7_dir: sys.exit("usage: claimocity_ingest.py --hl7-dir <folder> [--stamp S] [--live] [--limit N] [--skip-verify] [--skip-inspector] [--no-stedi] [--reprocess] [--register-anyway <file>[,<file>]]")
# --register-anyway <file>[,<file>] (William's word only) is read HERE, before any step: a start that names no file behind it ends at once. Read where
# it is used - after the import - a slip in the command would have ended the run with its visits entered and no register, no digest and no word.
anyway_arg = ""
if "--register-anyway" in a:
    _i = a.index("--register-anyway")
    if _i + 1 >= len(a) or a[_i + 1].startswith("--"): sys.exit("--register-anyway needs the file name(s) it is for: --register-anyway <file>[,<file>] - nothing was started")
    anyway_arg = a[_i + 1]
os.chdir(WS); os.makedirs("registers", exist_ok=True); os.makedirs("logs", exist_ok=True); os.makedirs("hl7", exist_ok=True)
REGF = "registers/claimocity_ingest.json"
reg = json.load(open(REGF)) if os.path.exists(REGF) else {"files": {}, "runs": []}
MAPF = "registers/claimocity_patient_map.json"
pmap = json.load(open(MAPF)) if os.path.exists(MAPF) else {}
env = dict(os.environ, FEED_STAMP=stamp, FEED_DX_CACHE=os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json"),
           FEED_CHART_PREFIX=os.environ.get("FEED_CHART_PREFIX", "F" + stamp[2:8]), PYTHONPATH=WS + ":" + HERE)
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
# The driver's own lines for William (11/25/2026, the verification: they ended ' - TOP OF THE REPORT' in this log and reached no digest and no
# register - the list below was never filled). top() prints the line with that ending and keeps it; a live run writes the list into the
# identity register and the digest prints each one at the top. Claimocity ids, chart ids, file names, stamps and fixed words only - never a
# name, never a date. A day with no new file and a run that ends in a failed step write no register: there the printed line is all there is.
notes = []
def top(line):
    print(line + " - TOP OF THE REPORT"); notes.append(line)
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
POS_RULE = 'POS_RULE_VERSION = "2026-11-25.5"'; REPO_HELPERS = "/home/claude/effinger-billing-backend/scripts/helpers"
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
# is added, and the workspace's file is written at once - also on a day with no new file (a dry run writes nothing: 11/25/2026). A value
# on main that is no chart id is passed over; a map on main that cannot be read changes nothing and is said. (The path is the clone's,
# taken from REPO_HELPERS.)
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
        top("PATIENT MAP: the repository's map could not be read (%s) - this workspace's map is used as it is, so a chart corrected on main does not reach this run" % type(e).__name__); return
    added = 0
    for fid, chart in main.items():
        if not (isinstance(fid, str) and fid and isinstance(chart, str) and CHART_ID.match(chart)): continue
        if fid not in pmap: pmap[fid] = chart; added += 1
        elif pmap[fid] != chart:
            repointed.append({"feed_id": fid, "was": pmap[fid] if isinstance(pmap[fid], str) and CHART_ID.match(pmap[fid]) else "", "now": chart}); pmap[fid] = chart
    if repointed or added:
        if live: json.dump(pmap, open(MAPF, "w"), indent=0, sort_keys=True)      # a dry run takes the repository's chart in memory only: the live run after it still finds the difference, writes the file and names the feed patient in its register
        print("PATIENT MAP: %d feed patient(s) now go to the repository's chart%s; %d added from the repository's map%s" % (
            len(repointed), (" - " + ", ".join("%s (was %s, now %s)" % (show_id(x["feed_id"]), x["was"] or "?", x["now"]) for x in repointed[:20]) + (" (+%d more)" % (len(repointed) - 20) if len(repointed) > 20 else "")) if repointed else "", added,
            "" if live else " (DRY: taken for this look only - this workspace's map file is not written)"))
_main_map()
# ---- the rehab monitor's register: the repository's copy when it is the LATER one (11/25/2026, review of the monitor) ------------------------------
# pos61_monitor.py goes by its own register of the run before (whose turn it is to be read; what it has said already). The workspace's copy comes
# back from the state bundle and can be older than the one the mirror carried to main: then main's is copied here, whole - that register is ONE
# run's finding and is never mixed (tools/mirror/mirror.py _merge_pos61 keeps the later one the same way). A copy on main that cannot be read,
# carries no time or is no register changes nothing.
def _main_monitor():
    src = os.path.join(os.path.dirname(REPO_MAP), "pos61_monitor.json"); dst = os.path.join("registers", "pos61_monitor.json")
    def at(p):
        try: d = json.load(open(p))
        except Exception: return None
        return d["at"] if isinstance(d, dict) and isinstance(d.get("at"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", d["at"]) else None
    a = at(src)
    if a is None: return
    b = (at(dst) or "") if os.path.exists(dst) else ""
    if a > b:
        try:
            shutil.copy2(src, dst + ".tmp"); os.replace(dst + ".tmp", dst)
            print("REHAB MONITOR REGISTER: the repository's copy (%s) is later than this workspace's (%s) - taken, whole" % (a, b or "none"))
        except Exception as e: print("REHAB MONITOR REGISTER: the repository's later copy could not be copied (%s) - the monitor starts from this workspace's" % type(e).__name__)
_main_monitor()
# ---- William's standing word 'same person' (registers/feed_same_person.json): main's file, whole (11/25/2026) -----------------------------------
# The insurance check and the intake buy a look-up, or add a plan, only for a chart that is KNOWN to be the feed's patient; a chart held
# 'same person?' is freed by William's yes. So that the next batch does not ask him again, his yes is kept in the repository's
# practices/ehpa/registers/feed_same_person.json - {chart: {"feed_ids": [Claimocity ids], "approved_by": his word and its date}} - written only
# on his word (a chat session, or the run that works his answer on the board card, which commits the file). Its home is main: the workspace's
# copy is only a copy, replaced at every start, so an entry taken out on main never comes back from a restored workspace.
# WHEN MAIN SAYS NOTHING, NOBODY'S STANDING WORD COUNTS (11/25/2026, the verification): with the repository's file missing the workspace's older
# copy was left as it was, without a word, and with the file unreadable it was kept and only said - a yes William had taken back on main still
# freed its chart, and a paid look-up was bought and a plan added on it. Now, whenever the clone is there (its registers folder) and its file is
# missing, cannot be read or is no JSON object, the workspace's copy is EMPTIED for this run and one line says so for the top of the report: a
# chart held 'same person?' stays held until the file on main is repaired (the run repairs it; William is not asked again about a chart he has
# answered). Only with no clone at all - a run without GitHub - does the workspace's copy stay and count: nothing else can be known there.
def _main_same_person():
    home = os.path.dirname(REPO_MAP); src = os.path.join(home, "feed_same_person.json"); dst = os.path.join("registers", "feed_same_person.json")
    def put(doc, text=None):
        # main's file goes over as its TEXT (11/25/2026, the second review of the look-up holds): written again from the parsed object, a chart the file names
        # twice reached the workspace with its last entry only - before the insurance check, which keeps both lists and says what does not count, ever saw it
        with open(dst + ".tmp", "w") as fh:
            if text is not None: fh.write(text)
            else: json.dump(doc, fh, indent=1, sort_keys=True)
        os.replace(dst + ".tmp", dst)
    if not os.path.isdir(home):
        try: n = len(json.load(open(dst)))
        except Exception: n = 0
        if n: print("SAME PERSON FILE: no repository clone here - William's standing word counts as this workspace's copy holds it (%d chart(s)); a yes he took back on main since is not known to this run" % n)
        return
    doc = None; what = "is missing"; text = None
    if os.path.lexists(src):
        try:
            with open(src) as fh: text = fh.read()
            doc = json.loads(text)
            if not isinstance(doc, dict): raise ValueError("no JSON object")
        except Exception as e: doc = None; text = None; what = "could not be read (%s)" % type(e).__name__
    try: put(doc if doc is not None else {}, text if doc is not None else None)
    except Exception as e:
        top("SAME PERSON FILE: this workspace's copy of feed_same_person.json could not be replaced (%s) - the older copy counts as it is in this run: a yes William took back on main may still free a chart" % type(e).__name__); return
    if doc is None: top("SAME PERSON FILE: the repository's feed_same_person.json %s - nobody's standing word counts in this run (this workspace's copy was emptied): a chart held 'same person?' stays held until the file on main is repaired" % what)
_main_same_person()
# ---- the charts William has called duplicates (registers/feed_duplicate_charts.json): main's file, whole (11/25/2026) ------------------------------
# claimocity_match.py never offers a chart this file names as a duplicate - the proper chart stands in its place ({duplicate chart: {"proper": chart,
# "approved_by": his word and its date}}; written only on his word, on main, by the run that works his answer or by a chat session). As for his standing
# word 'same person' the workspace's copy is only a copy, replaced at every start: an entry taken out on main never comes back from a restored
# workspace. With the clone there and no such file on it the copy is emptied without a word (no chart counts as a duplicate - the rule decides by what
# the charts show, as before this file); with a file that cannot be read or is no JSON object the same, and one line says so for the top of the
# report. With no clone at all the workspace's copy stays as it is.
def _main_duplicates():
    home = os.path.dirname(REPO_MAP); src = os.path.join(home, "feed_duplicate_charts.json"); dst = os.path.join("registers", "feed_duplicate_charts.json")
    if not os.path.isdir(home): return
    doc = None; what = ""
    if os.path.lexists(src):
        try:
            with open(src) as fh: doc = json.load(fh)
            if not isinstance(doc, dict): raise ValueError("no JSON object")
        except Exception as e: doc = None; what = "could not be read (%s)" % type(e).__name__
    try:
        with open(dst + ".tmp", "w") as fh: json.dump(doc if doc is not None else {}, fh, indent=1, sort_keys=True)
        os.replace(dst + ".tmp", dst)
    except Exception as e:
        top("DUPLICATE CHARTS FILE: this workspace's copy of feed_duplicate_charts.json could not be replaced (%s) - the older copy counts as it is in this run" % type(e).__name__); return
    if what: top("DUPLICATE CHARTS FILE: the repository's feed_duplicate_charts.json %s - no chart counts as a duplicate in this run (this workspace's copy was emptied): a new Claimocity id can be matched to a chart William called a duplicate until the file on main is repaired" % what)
_main_duplicates()
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
# ---- the messages that cannot be entered as they came: the parse step's count (11/25/2026) ----------------------------------------------------
# feed_parse_dft_1028.py counts every such message in registers/feed_unreadable_<stamp>.json - file date, number of the message in its file and
# one of its five fixed sentences (the same five stand in the parser and in the digest; the self-test holds the three together). A file is not
# registered while that register names a message of it (below). A row that is not a file date, a number and one of the sentences is counted and
# never printed; a register that cannot be read keeps EVERY file of the batch back. A record with a charge line and no Claimocity id that the
# parse step did not count (an older copy of the parser) is the same visit nobody can enter: counted here, by its file date.
UNREADABLE_WORDS = ("no patient line", "a line of the message is cut short", "a charge line carries no whole procedure code", "no charge line", "the patient line carries no Claimocity id")
unread = []; unread_err = ""      # (file date or "?", number of the message in its file or None, the fixed sentence or "")
_unf = "registers/feed_unreadable_%s.json" % stamp
if os.path.exists(_unf):
    try:
        _u = json.load(open(_unf)); _rows = _u.get("messages") if isinstance(_u, dict) else None
        if not isinstance(_rows, list): raise ValueError("no list of messages")
        for _x in _rows:
            _ok = isinstance(_x, dict) and isinstance(_x.get("file"), str) and re.fullmatch(r"\d{8}|\?", _x["file"]) and isinstance(_x.get("message"), int) and not isinstance(_x.get("message"), bool) and _x.get("why") in UNREADABLE_WORDS
            unread.append((_x["file"], _x["message"], _x["why"]) if _ok else ("?", None, ""))
    except Exception as _e: unread_err = type(_e).__name__
    if not live:      # a dry run leaves no batch register behind (the mirror would carry it to main)
        try: os.remove(_unf)
        except OSError: pass
for m in parsed:
    if isinstance(m, dict) and not str(m.get("pid") or "").strip() and m.get("FT1") and not m.get("unreadable"):
        unread.append((str(m.get("file") or "")[:8] if re.fullmatch(r"\d{8}", str(m.get("file") or "")[:8]) else "?", None, UNREADABLE_WORDS[4]))
def _files_of(day):      # the files of this batch a counted message stands for: the file of that day - "?" = one whose name does not begin with its day; none answers to it = every file (never none)
    hit = [b for b in files if (b[:8] == day if day != "?" else not re.fullmatch(r"\d{8}", b[:8]))]
    return hit or list(files)
def _unread_said(rows):
    out = ["file %s message %d (%s)" % u if u[1] is not None else "file %s (%s - not counted by the parse step)" % (u[0], u[2]) for u in rows if u[2]]
    odd = sum(1 for u in rows if not u[2])
    return "; ".join(out[:20]) + (" +%d more" % (len(out) - 20) if len(out) > 20 else "") + (("; " if out else "") + "%d row(s) of the parse step's register that are not a file date, a message number and its fixed words" % odd if odd else "")
unread_files = sorted(set(files) if unread_err else {b for u in unread for b in _files_of(u[0])})
step("dx", [sys.executable, os.path.join(HERE, "claimocity_dx.py")])
# ---- 3 match: the map first, lookups only for unknown patients ---------------------------------------------------------------
# EVERY ENTRY NAMES THE CHART OF EACH CLAIMOCITY ID ("by_id", 11/25/2026). The match file is keyed by name and birth date, and until now the
# import took a message's chart from that key alone - so two feed patients under one name and birth date (a namesake; the placeholder
# date; a second Claimocity id of one person) shared ONE chart: a new id beside a known one silently got the known chart and its own
# decision was dropped, and of two known ids the first one's chart was used for both. Now each id keeps its own: a known id the chart the
# map names for it, a looked-up id the chart the identity rule chose (or the new chart made for it), an id nobody decided none - and the
# import asks by the message's own id (claimocity_import.py chart_of). "resolved" stays what it was for a reader that does not know by_id.
# NOBODY IS LOOKED UP FOR A MESSAGE THAT CARRIES NOTHING TO ENTER (11/25/2026): a message without a charge line - one the file ended in, its
# patient line perhaps cut short too - went to the match step like any other, a new chart could be made from it, and the patient map then sent
# that patient's real visits to that chart. Its patient is looked up by the run that reads the whole message.
def _key(m): return str(m.get("name") or "").upper().strip() + "|" + str(m.get("dob") or "")[:8]      # the import's own key (chart_of), also for a message that carries no name or date
known, unknown = {}, []
known_ids = set()
for m in parsed:
    key = _key(m)
    if str(m.get("pid") or "").strip() and m["pid"] in pmap:      # (an empty id is never a known patient, whatever a map holds under an empty key)
        chart = pmap[m["pid"]]; known_ids.add(m["pid"])
        # the entry carries the same fields as one the identity rule decided (rule "map" and the map's fixed words), so every reader finds them
        e = known.setdefault(key, {"status": "FOUND", "pids": [chart], "amd_names": [], "feed_ids": [], "resolved": chart, "via": "patient map", "by_id": {},
                                   "rule": "map", "why": WHY_MAP, "flags": [], "candidates": [], "evidence": [], "feed_dob": "real" if _real(m["dob"][:8]) else "none", "for_william": False})
        e["by_id"][m["pid"]] = chart
        if m["pid"] not in e["feed_ids"]: e["feed_ids"].append(m["pid"])
    elif m.get("FT1"):
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
    # 11/25/2026 (the verification's fixes, wired here): on a key several Claimocity ids share that got no chart of its own, each id that has PROOF of its own
    # chart goes there (claimocity_resolve.py names it under "by_proof") - until then such ids had no chart, run after run. Only a chart id is taken.
    # ... and only for a Claimocity id the entry itself names: its feed_ids hold EVERY id of the key - decided_for only the ids left without a chart as soon as
    # one id has proof and another has none (claimocity_resolve.py), and it was read alone at first: the id WITH proof then got no chart after all
    _own_ids = {i for f_ in ("feed_ids", "decided_for") for i in (v.get(f_) if isinstance(v.get(f_), list) else []) if isinstance(i, str) and i}
    for i, c_ in (v["by_proof"].items() if isinstance(v.get("by_proof"), dict) else []):
        if i in _own_ids and CHART_ID.match(str(c_ or "")): by.setdefault(i, c_)
    v["by_id"] = by
    if k in shared:
        v["decided_chart"] = v.get("resolved") or ""; v["resolved"] = known[k]["resolved"]      # for a reader that does not know by_id the key reads as it always did: the known chart
json.dump(looked, open(matchf, "w"), indent=1)
# said, not held: several Claimocity ids under one name and birth date that go to several charts - each visit goes to its own id's chart. Worked out
# here, where every id of the batch has its chart (11/25/2026: it was worked out for the known ids alone, before a looked-up id had one, and only
# printed). Not said where the rule made a new chart beside same-name charts in this run: that question stands at the top already.
for k, v in sorted(looked.items()):
    if len(set(v["by_id"].values())) > 1 and not (v.get("rule") == 9 and v.get("for_william") is True):
        top("PATIENT MAP: %d Claimocity ids under one name and birth date go to %d charts (%s) - each visit goes to its own id's chart; if they are one person the charts are duplicates" % (
            len(v["by_id"]), len(set(v["by_id"].values())), ", ".join("%s on %s" % (show_id(i), c_ if CHART_ID.match(str(c_ or "")) else "(not a chart id)") for i, c_ in sorted(v["by_id"].items()))))      # only a chart id is printed and kept (the line goes into the identity register's notes, which the mirror carries to main: a hand slip in the workspace's map must not travel)
# ---- 5 import -------------------------------------------------------------------------------------------------------------------
# (the feed helpers were made the repository's at the start of this run - make_current above; pos_warn says what could not be)
cmd = [sys.executable, os.path.join(HERE, "claimocity_import.py"), "--all" if live else "--dry"]
if limit: cmd += ["--limit", str(limit)]
step("import", cmd)
# the patient map learns every chart this batch touched (feed patient id -> AMD chart), for the next run - each id its own chart. A LIVE run
# only (11/25/2026): a dry run wrote the map too, and the live run after it took every patient the rule had just decided as 'known from the map'
looked = json.load(open(matchf))
if live:
    for v in looked.values():
        for fid, chart in (v.get("by_id") or {}).items():
            if fid and CHART_ID.match(str(chart or "")): pmap[fid] = chart
    json.dump(pmap, open(MAPF, "w"), indent=0, sort_keys=True)
impf = "registers/feed_import_%s.json" % stamp
imp = json.load(open(impf)) if os.path.exists(impf) else {"created": [], "skipped": [], "failed": []}
# ---- a file is not registered while a patient of it has no chart (11/25/2026) -------------------------------------------------------------------
# No chart = the match file, as the import read it, names no chart for the message's Claimocity id: a new chart AdvancedMD refused
# (claimocity_newcharts.py: 'new chart not made'), a patient the identity rule could not decide (rule 0). The import passes such a
# message over ("no chart") and writes no row for it - and until now the file was registered as done all the same.
def _of(b): return [m for m in parsed if m["file"] == b[:8] or b.startswith(m["file"])]      # the messages of one file of the batch
def _nochart(m):      # a message that IS a visit of somebody (a patient id and at least one charge line - the import passes any other over) and has no chart
    return bool(m.get("pid")) and bool(m.get("FT1")) and not ((looked.get(_key(m)) or {}).get("by_id") or {}).get(m["pid"])
held_files = sorted(b for b in files if any(_nochart(m) for m in _of(b))) if live else []
held_ids = sorted({str(m["pid"]) for m in parsed if _nochart(m)}) if live else []
def _names(fs): return ", ".join(fs[:20]) + (" (+%d more)" % (len(fs) - 20) if len(fs) > 20 else "")
if held_files:
    print("NOT REGISTERED: %d file(s) hold a patient with no chart - %s - Claimocity id(s) %s: the next start reads them again (a visit already in AdvancedMD answers 'all lines already in AMD') - TOP OF THE REPORT" % (
        len(held_files), _names(held_files), ", ".join(show_id(i) for i in held_ids[:20]) + (" (+%d more)" % (len(held_ids) - 20) if len(held_ids) > 20 else "")))
# ---- ... nor while a visit of it is not on a chart for another reason (11/25/2026, the verification) ----------------------------------------------
# (1) a message of the file could not be read, or carries no Claimocity id: unread_files above. (2) AdvancedMD refused a visit at its FIRST call:
# the import's failed row says 'addvisit: ...' and names no visit - nothing was made, so reading the file again is safe, and the import then
# tries once more. Every file of the batch that carries a visit of that Claimocity id is kept back. A failed row that names a visit AdvancedMD
# made, or says nothing about one (an error - nobody knows what AdvancedMD kept), keeps no file back: the digest names it at the top.
# --register-anyway <file> (William's word) ends either hold for the files it names; it never ends the hold of a patient with no chart.
_refused = [x for x in (imp.get("failed") or []) if isinstance(x, dict) and isinstance(x.get("err"), str) and x["err"].startswith("addvisit:") and not x.get("empty_visit")]
_ref_ids = {x.get("feed_id") for x in _refused if x.get("feed_id")}
refused_files = sorted(b for b in files if any(m.get("pid") in _ref_ids and m.get("FT1") for m in _of(b)))
def _ref_charts(fs): return ", ".join(sorted({str(x.get("pid")) for x in _refused if CHART_ID.match(str(x.get("pid") or "")) and any(m.get("pid") == x.get("feed_id") for b in fs for m in _of(b))})) or "?"
anyway = {sftp_name(os.path.basename(x.strip())) for x in anyway_arg.split(",") if x.strip()}
given_up = sorted(b for b in files if b in anyway and b not in held_files and (b in unread_files or b in refused_files)) if live else []
for _x in sorted(anyway - set(given_up)):
    print("--register-anyway: %s %s - nothing is done for it" % (_x if re.fullmatch(r"[0-9A-Za-z_.\-]{1,80}", _x) else "(a name of another shape)",
          "holds a patient with no chart, which is settled by a chart and never by this option" if _x in held_files else "is not a file this run keeps back for a message that could not be read or a visit AdvancedMD refused" if live else "is named in a dry run"))
def _why_given_up(fs):
    u = [x for x in unread if set(_files_of(x[0])) & set(fs)]; r_ = [b for b in fs if b in refused_files]; parts = []
    if unread_err and set(fs) & set(unread_files): parts.append("the parse step's count of its unreadable messages could not be read")
    elif u: parts.append("%d message(s) could not be read (%s)" % (len(u), _unread_said(u)))
    if r_: parts.append("AdvancedMD refused a visit at entry (chart(s) %s)" % _ref_charts(r_))
    return " and ".join(parts)
if given_up:
    print("REGISTERED ON WILLIAM'S WORD (--register-anyway): %d file(s) - %s - although %s: what is not entered of them is given up and their file is not read again - TOP OF THE REPORT" % (len(given_up), _names(given_up), _why_given_up(given_up)))
_kept_unread = [b for b in unread_files if b not in given_up] if live else []; _kept_refused = [b for b in refused_files if b not in given_up] if live else []
if _kept_unread:
    _u = [x for x in unread if set(_files_of(x[0])) & set(_kept_unread)]
    print("NOT REGISTERED: %d file(s) hold a feed message that could not be read - %s - %s: nothing of such a message is entered; every start reads the file again (a visit already in AdvancedMD answers 'all lines already in AMD') "
          "until the copy that is read is whole, or William says the message is lost (then ONE start with --register-anyway <file>) - TOP OF THE REPORT" % (
              len(_kept_unread), _names(_kept_unread), ("the parse step's count %s could not be read (%s): every file of this batch is kept back" % (_unf, unread_err)) if unread_err else "%d message(s): %s" % (len(_u), _unread_said(_u))))
if _kept_refused:
    print("NOT REGISTERED: %d file(s) hold a visit AdvancedMD refused at entry - %s - chart(s) %s: nothing of that visit was made; the next start reads the file again and the import tries once more "
          "(every visit already entered answers 'already'); a visit AdvancedMD will never take is ended on William's word (--register-anyway <file>) - TOP OF THE REPORT" % (len(_kept_refused), _names(_kept_refused), _ref_charts(_kept_refused)))
# ---- a new chart whose run was cut before its digest (11/25/2026, the verification) -----------------------------------------------------------------
# A run that ended after its new-chart step - five of the eleven ingests from 11/13 to 11/24 were cut - had made the charts and written
# registers/feed_newcharts_<its stamp>.json, but no identity register and no digest. The next run finds each new chart by its Claimocity id
# (rule 1) and its digest says '0 new chart(s) made': the question about a possible duplicate chart, and the face sheet for a chart made
# with no birth date, were never said. Now: for every EARLIER stamp whose new-chart register is in this workspace, carries the identity
# rule's own words (rule 9 and for_william - the registers from before 11/25/2026 carry neither) and has no identity register beside it,
# this run says what was for William (its notes; the digest prints them at the top) and - once its own digest stands - writes that stamp's
# identity register from the new-chart rows ("recovered_by": this stamp), so that it is said ONCE. The same-name charts of the question come
# from that run's match file when it is still here (it never leaves its workspace); without it the line says where they are named.
def _safe_id(i): return i if isinstance(i, str) and re.fullmatch(r"[0-9A-Za-z]{6,40}", i) else "(odd id)"
recovered = []      # (stamp, the identity register to write for it)
def _earlier_new_charts():
    for f in sorted(glob.glob("registers/feed_newcharts_*.json")):
        st = re.sub(r"^feed_newcharts_|\.json$", "", os.path.basename(f))
        if st == stamp or not re.fullmatch(r"\d{8}T\d{4}ZR?", st) or os.path.lexists("registers/feed_identity_%s.json" % st): continue
        try: made = [c_ for c_ in (json.load(open(f)).get("created") or []) if isinstance(c_, dict) and c_.get("rule") == 9 and isinstance(c_.get("for_william"), bool) and CHART_ID.match(str(c_.get("pid") or ""))]
        except Exception: continue
        if not made: continue
        beside = {}      # Claimocity id -> the same-name charts the rule had before it, from that run's match file
        try:
            for v in json.load(open("feed_match_%s.json" % st)).values():
                if isinstance(v, dict) and v.get("rule") == 9:
                    for i in (v.get("decided_for") or v.get("feed_ids") or []): beside.setdefault(i, [x for x in (v.get("candidates") or []) if isinstance(x, str) and CHART_ID.match(x)])
        except Exception: pass
        rows = []
        for c_ in made:
            ids = [i for i in (c_.get("feed_ids") if isinstance(c_.get("feed_ids"), list) else []) if isinstance(i, str)]
            e = {"rule": 9, "why": c_.get("why"), "flags": c_.get("flags") if isinstance(c_.get("flags"), list) else [], "candidates": [x for x in beside.get(ids[0] if ids else "", []) if x != c_["pid"]], "evidence": [],
                 "feed_dob": c_.get("dob") if c_.get("dob") in ("real", "none") else "none", "for_william": c_["for_william"]}
            bad = FI.problems(e) if FI else list(ID_FIELDS)
            row = {"feed_ids": [_safe_id(i) for i in ids], "chart": c_["pid"], "status": "MISSING", "new_chart": True}
            for f_ in ID_FIELDS:
                if f_ not in bad: row[f_] = e[f_]
            if bad: row["withheld"] = sorted(bad)
            rows.append(row)
            if not c_["for_william"]: continue
            if bad or not FI or not hasattr(FI, "william_lines") or not hasattr(FI, "FLAG_NOT_USED"): said = ["new chart %s was made - what the identity rule said about it is in registers/feed_newcharts_%s.json" % (c_["pid"], st)]
            elif FI.FLAG_NOT_USED in e["flags"] and not e["candidates"]:      # the charts it stood beside are not known here: the question without the list
                said = ["new chart %s was made beside same-name charts with other birth dates and no number in common - same person or not? (the charts are named in logs/claimocity_%s_resolve.log of the workspace that made it)" % (c_["pid"], st)] \
                       + FI.william_lines(dict(e, flags=[x for x in e["flags"] if x != FI.FLAG_NOT_USED]), c_["pid"], ids or "")
            else: said = FI.william_lines(e, c_["pid"], ids or "")      # (every id of the row is named - the rule's lines take a list since 11/25/2026)
            for line in said: top("from the run of stamp %s, which ended before its digest: %s" % (st, line))
        recovered.append((st, {"stamp": st, "at": utcnow().isoformat() + "Z", "identity_rule": FI.IDENTITY_RULE_VERSION if FI else "", "recovered_by": stamp,
                               "counts": {"known from the patient map": 0, "looked up": len(rows), "new charts": len(rows), "for William": sum(1 for r_ in rows if r_.get("for_william") is True), "no chart": 0},
                               "repointed": [], "patients": rows, "notes": [], "not_registered": []}))
if live:
    try: _earlier_new_charts()
    except Exception as _e: print("the new-chart registers of earlier runs could not be looked through (%s) - nothing is said from them in this run" % type(_e).__name__)
# ---- which chart and why: registers/feed_identity_<stamp>.json (live; the mirror carries it to main) ----------------------------------------------
def _each(v, ids):
    """What the rule gives each Claimocity id of a shared key on its own - the resolve step's words '(each on its own: <id> -> <chart>; ...)', taken only when
    every part is a Claimocity id of this row and a chart id or one of its three fixed answers. -> [[id, answer], ...] or None"""
    m_ = re.search(r"\(each on its own: ([^()]*)\)\s*$", str(v.get("resolution") or "")); out = []
    for part in (m_.group(1).split("; ") if m_ else []):
        mm = re.fullmatch(r"([0-9A-Fa-f]{24}) -> (pat[0-9]+|a new chart|no chart)", part.strip())
        if not mm or mm.group(1) not in ids: return None
        out.append([mm.group(1), mm.group(2)])
    return out or None
def _identity_rows():
    rows = []; seen = set()
    for k, v in looked.items():
        if v.get("rule") == "map": continue                                # known from the map: counted below, not listed
        ids = tuple(i for i in (v.get("decided_for") or v.get("feed_ids") or []) if i not in known_ids)      # the ids the rule decided - on a key they share with a known id, not that one
        if ids in seen or not ids: continue                                # the same answer stands under every name-and-date key of the patient; a key no Claimocity id carries (a message without one) is nobody's row - the parse step's count names that message by file date and number
        seen.add(ids)
        # ids that have PROOF of their own chart on a key that got none (by_proof, above): each gets a row of its own - its own chart and its own answer, in the
        # rule's fixed words (a row that carries anything else is not copied) - and is not the key's: the key's own row never shows one id's chart for all
        proofs = []
        for r_ in (v.get("proof_rows") if isinstance(v.get("proof_rows"), list) else []):
            pi = tuple(i for i in (r_.get("feed_ids") if isinstance(r_, dict) and isinstance(r_.get("feed_ids"), list) else []) if isinstance(i, str) and i)
            if not pi or not FI or FI.problems(r_) or not CHART_ID.match(str(r_.get("chart") or "")) or any((v.get("by_id") or {}).get(i) != r_["chart"] for i in pi): continue
            proofs.append((pi, r_))
        for pi, r_ in proofs:
            if pi in seen: continue
            seen.add(pi); rows.append(dict({"feed_ids": [_safe_id(i) for i in pi], "chart": r_["chart"], "status": "FOUND", "new_chart": False}, **{f: r_.get(f) for f in ID_FIELDS}))
        if proofs and FI and v.get("why") == getattr(FI, "WHY_EACH_PROOF", None): continue      # every id of the key has a row of its own: the key itself has nothing more to say
        proved = {i for pi, r_ in proofs for i in pi}
        chart = next((c for c in ((v.get("by_id") or {}).get(i) for i in ids if i not in proved) if CHART_ID.match(str(c or ""))), "")
        row = {"feed_ids": [_safe_id(i) for i in ids], "chart": chart, "status": v.get("status") if v.get("status") in ("FOUND", "AMBIGUOUS", "MISSING") else "", "new_chart": bool(chart) and v.get("rule") == 9}
        bad = FI.problems(v) if FI else list(ID_FIELDS)                    # what is NOT a fixed word, a chart id or a rule number is never copied
        for f in ID_FIELDS:
            if f not in bad: row[f] = v.get(f)
        if bad: row["withheld"] = sorted(bad)
        if not chart and len(ids) > 1 and v.get("why") == WHY_SHARED and _each(v, ids): row["each"] = _each(v, ids)      # a key several ids share that got no chart: what each would get on its own (the digest names every id with it)
        rows.append(row)
    return rows
def _identity_register(rows, said):
    doc = {"stamp": stamp, "at": utcnow().isoformat() + "Z", "identity_rule": FI.IDENTITY_RULE_VERSION if FI else "",
           "counts": {"known from the patient map": len(known_ids), "looked up": len(rows), "new charts": sum(1 for r_ in rows if r_["new_chart"]),
                      "for William": sum(1 for r_ in rows if r_.get("for_william") is True), "no chart": sum(1 for r_ in rows if not r_["chart"])},
           "repointed": repointed, "patients": rows, "notes": said, "not_registered": held_files,
           "not_registered_unreadable": _kept_unread, "not_registered_refused": _kept_refused, "registered_anyway": given_up,
           # ... and for which of the two causes each file was registered on William's word (the digest's two lines each name their own files)
           "registered_anyway_unreadable": [b for b in given_up if b in unread_files], "registered_anyway_refused": [b for b in given_up if b in refused_files]}
    tmp = "registers/feed_identity_%s.json.tmp" % stamp
    with open(tmp, "w") as fh: json.dump(doc, fh, indent=1)
    os.replace(tmp, "registers/feed_identity_%s.json" % stamp)
notes_written = False      # the lines above are on record in this run's identity register (the digest prints them from there)
if live:
    try: _identity_register(_identity_rows(), notes); notes_written = True
    except Exception as _e:
        _line = "IDENTITY REGISTER NOT WRITTEN (%s) - which chart each new feed patient went to is in logs/claimocity_%s_resolve.log only" % (type(_e).__name__, stamp)
        print(_line + " - TOP OF THE REPORT")
        # when it was the ROWS that could not be built, the register is written without them: it still carries the driver's lines and the files that are kept back
        # (the digest prints both at the top), and its own line says what it lacks
        try: _identity_register([], notes + [_line + " (this register was written with no row of a patient: it carries only the driver's own lines and the files that are kept back)"]); notes_written = True
        except Exception: notes.append(_line)
# ---- 6 verify, 7 inspector, 8 report (live) --------------------------------------------------------------------------------------
if live:
    if "--skip-verify" not in a:
        vc = [sys.executable, os.path.join(HERE, "claimocity_verify.py")] + (["--no-stedi"] if "--no-stedi" in a else [])
        step("verify", vc, must=False)
    if "--skip-inspector" not in a:
        step("inspector", [sys.executable, os.path.join(HERE, "claimocity_inspector.py")], must=False)
    step("report", [sys.executable, os.path.join(HERE, "claimocity_report.py")], must=False)
    step("recon", [sys.executable, os.path.join(HERE, "claimocity_recon.py"), stamp], must=False)   # registers/feed_recon_<stamp>.json: every message and its AMD outcome (the Practice Database's feed_batches document)
    if notes_written and os.path.exists("feed_digest_%s.md" % stamp):      # this run's digest stands and carries what was for William about the charts of a run that was cut: that run's identity register is written now, so that it is said once
        for _st, _doc in recovered:
            try:
                with open("registers/feed_identity_%s.json.tmp" % _st, "w") as _fh: json.dump(_doc, _fh, indent=1)
                os.replace("registers/feed_identity_%s.json.tmp" % _st, "registers/feed_identity_%s.json" % _st)
            except Exception as _e: print("the identity register of the earlier run %s could not be written (%s) - its lines are said again by the next run" % (_st, type(_e).__name__))
# ---- register the files ------------------------------------------------------------------------------------------------------------
# (11/25/2026) each entry records the SIZE of the file that was read: claimocity_gcs.py fetches a registered file again when the bucket's copy
# has another size - a file that was read while Claimocity was still writing it is then read whole (the import enters only what is missing).
not_reg = sorted(set(held_files) | set(_kept_unread) | set(_kept_refused))
for b in files:
    if live and b not in not_reg:
        reg["files"][b] = {"stamp": stamp, "sha256": sha(os.path.join(batch, b)), "bytes": os.path.getsize(os.path.join(batch, b)), "messages": len(_of(b)), "at": utcnow().isoformat() + "Z"}
        if b in given_up: reg["files"][b]["note"] = "registered on William's word (--register-anyway) although %s - not entered, not read again" % _why_given_up([b])
_n_unread = len(unread) if not unread_err else 0
_causes = [w for w, fs in (("a patient with no chart", held_files), ("a message that could not be read", _kept_unread), ("a visit AdvancedMD refused at entry", _kept_refused)) if fs]
print("RESULT stamp %s: files %d, messages %d, visits created %d, skipped %d, failed %d%s%s%s" % (
    stamp, len(files), len(parsed), len(imp["created"]), len(imp["skipped"]), len(imp["failed"]),
    (", %d message(s) could not be read" % _n_unread) if _n_unread else ", the parse step's count of unreadable messages could not be read" if unread_err else "",
    (", %d file(s) NOT registered (%s - read again by the next start)" % (len(not_reg), "; ".join(_causes))) if not_reg else "",
    ("" if live else " (DRY - nothing written, files not registered)") + pos_warn))
if live and os.path.exists("feed_digest_%s.md" % stamp): print("digest: feed_digest_%s.md" % stamp)
finish(0)
