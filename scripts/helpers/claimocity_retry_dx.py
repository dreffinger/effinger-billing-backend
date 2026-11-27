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
# 11/25/2026 (William, STANDING: "for any diagnosis not in the master file yet change it to i10 and send me an email with the codes needed to be
#   added" - said right after "Add diagnosis S82.843D in AMD Master Files change this diagnosis to i10"): a skipped visit no longer waits for
#   its code to be added. It is READY as soon as every charge line carries at least one diagnosis code and I10 itself is in AMD's list - the
#   import then puts I10 in the place of each code the list does not have (claimocity_import.py, DX_INSTEAD; the same word stands below). The
#   codes are still printed, for the email: "retry-dx: N visit(s) entered with I10 in place of codes not in AMD's diagnosis list: <codes>"
#   (a dry run: "would be entered"), and the retry's own digest carries the line 'EMAIL WILLIAM: outbox/dx_codes_needed_<stamp>R.txt' with
#   the text claimocity_report.py wrote there. A charge line with NO diagnosis code at all still waits (there is nothing to change to I10) and
#   is named for William. When I10 is not in the list everything is as before: the visit waits on its codes and they are printed.
# Decides: nothing new. For every skipped-dx row in registers/feed_import_*.json whose (patient, DOS, CPT set) was never created:
#   1 gets the batch's parsed messages (feed_parsed_<stamp>.json, else re-parses hl7/<stamp>/, else re-downloads the batch's files from
#     the bucket with claimocity_gcs.py --fetch), 2 re-checks the codes in AMD (claimocity_dx.py looks null codes up again), 3 imports
#     only the messages that are ready (above), under a NEW stamp <now>R (import, verify, inspector, report -
#     the same scripts as claimocity_ingest.py; dedupe is the registers + the chart's live charges, so a retry is a no-op the second time).
# Codes the visits still wait on (only when I10 itself is not in the list) are printed: "still wait on codes not in AMD's diagnosis list:
#   M51.17, M51.86" - that line goes into the digest under Holds, with the fix: William adds the code in AMD (Master Files > Diagnosis
#   Codes > New, ICD-10 code + description).
# Dry by default (prints what would be entered, writes nothing in AMD); --live enters. Exit 0 done (also when nothing to retry), 2 a step failed.
# Usage: cd /home/claude/unbilled && python3 claimocity_retry_dx.py [--live] [--stamp <UTC stamp>] [--no-stedi]
# 11/25/2026 (the second verification of the death check): the same for a visit the import kept out with "a date of death is on record for this chart but its
#   day cannot be read - not entered" (the workspace's cache carried the privacy gate's placeholder and nobody named the day): it is handed to the import again,
#   which asks again - it is entered once a day AFTER the visit is known, kept out for good once a day before it is, and waits until then.
#   THIS KIND MUST CONVERGE BY ITS OWN RULES (the independent check of that round, the same day). A held visit is NOT entered by the retry, so 'a no-op the second
#   time' did not hold for it: every live retry wrote the held row again into its own register (stamp ...R) and kept its own batch file, and the next run read
#   both as one more batch - 1, 2, 4, 8 messages per run in one workspace, one more stale 'batch(es) <stamp>R ... not on hand' line per run in a fresh container,
#   and no end once the visit was 'kept out for good'. So: (1) a held row is taken only from a register that is NOT a retry's own; (2) each visit - the feed
#   patient, its codes, its dates of service - goes to the import at most ONCE per run; (3) it is left alone for good once a LATER register, a retry's own included,
#   shows that visit entered (a created row), kept out for good ('DOS after date of death ...'), or answered 'all lines already in AMD' - the import writes
#   the visit's codes and dates of service into all three rows: the held row, the 'DOS after' row and (since the third round of 11/25/2026) the 'already' row.
#   Until then the 'already' row named the feed patient only, and it ended the retry only where the retry's own batch file was on hand and named that one
#   visit, or the reconciliation register named it: in a new container, and after a retry that had handed over two visits of the chart, the visit was handed
#   over again in every run. A row of a register from before still counts the old way. Only a register LATER than the one that held the visit ends its retry -
#   never an earlier one (a charge can be voided in between). The line this step prints about such charts
#   names only the charts whose visit this run really hands over. Nothing here reads the cache of dates of death: the import decides, every run, from what it reads.
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
POS_RULE = 'POS_RULE_VERSION = "2026-11-26.1"'; REPO_HELPERS = "/home/claude/effinger-billing-backend/scripts/helpers"
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
DEATH_DAY_WHY = "a date of death is on record for this chart but its day cannot be read - not entered"      # the same line as in claimocity_import.py (the self-test holds the two together)
DEATH_AFTER_WHY = "DOS after date of death"      # how the import's row starts for a visit it keeps out FOR GOOD (a day is known and lies before the visit)
ALREADY_WHY = "all lines already in AMD"         # the import's answer for a visit the chart already carries
death_day = set()  # the charts of the held visits THIS run hands over (chart ids only - for the one line this step prints about them)
held = {}          # stamp -> {feed patient id: [(the row's codes, the visit's lines {(code, MM/DD/YYYY)} - None for a row that names no dates, the chart id)]}: the visits kept out with DEATH_DAY_WHY - from registers that are NOT a retry's own
ended = []         # (stamp, feed patient id, the visit's lines) of every 'DOS after date of death' row that names its visit: kept out for good
answered = []      # (stamp, feed patient id, the visit's lines) of every 'all lines already in AMD' row that names its visit - the import writes the visit's codes and dates of service into that row since 11/25/2026 (the third round): the chart carries the visit
already_r = []     # (a retry's own stamp, feed patient id) of every 'all lines already in AMD' row in a retry's own register that names NO visit (a register from before that day) - _kept_out reads which one from that retry's batch file
def _norm(stamp): return re.sub(r"[^0-9TZR]", "", str(stamp))      # 2026-11-10T1319Z and 20261110T1319Z are the same batch; a retry's stamp ends with R and sorts behind the batch of its minute
def _lines(row):
    """The visit a skip row names - {(code, its date of service MM/DD/YYYY)} from its cpts and dos_lines - or None when the row does not name it line by line."""
    cp, dl = row.get("cpts"), row.get("dos_lines")
    if not (isinstance(cp, list) and isinstance(dl, list) and cp and len(cp) == len(dl) and all(isinstance(x, str) and x for x in cp + dl)): return None
    return frozenset(zip(cp, dl))
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
        elif why.startswith(DEATH_DAY_WHY):                                   # 11/25/2026 (the second verification of the death check): the import kept the visit out because a
            # death is on record for the chart and nobody could name its day - it is handed to the import again, which asks again and enters it, keeps it out for good (a
            # day before the visit), or keeps it waiting. THE RETRY MUST CONVERGE (the independent check of that round, finding 3): every live retry writes this row again
            # into its OWN register (stamp ...R) and keeps its own batch file - read as a batch of their own, the visit was handed over once more for each: 1, 2, 4, 8
            # messages per run. So the row is taken only from a register that is NOT a retry's own; the visit goes to the import at most once per run; and it is left
            # alone for good once a LATER register shows it entered, answered 'already', or kept out with 'DOS after date of death' (_kept_out, below).
            if stamp.endswith("R"): continue
            _c = {c_ for c_ in (row.get("cpts") or []) if isinstance(c_, str) and c_}
            if row.get("feed_id") and _c: held.setdefault(stamp, {}).setdefault(row["feed_id"], []).append((_c, _lines(row), str(row.get("pid") or "?")))
        elif why.startswith(DEATH_AFTER_WHY):                                 # kept out for good - of ANY register, a retry's own included (the row names its visit since 11/25/2026)
            if row.get("feed_id") and _lines(row): ended.append((_norm(stamp), row["feed_id"], _lines(row)))
        elif why == ALREADY_WHY and row.get("feed_id"):                       # the chart already carries the visit: of ANY register when the row names its visit; a row that names none counts from a retry's own register only (its batch file says which visit)
            if _lines(row): answered.append((_norm(stamp), row["feed_id"], _lines(row)))
            elif stamp.endswith("R"): already_r.append((stamp, row["feed_id"]))
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
if not want and not held:
    print("retry-dx: nothing to retry (no 'no usable dx' skip, no 'unknown CPT' skip the import can enter now and no visit kept out for a date of death nobody could read in the registers)" + UNKNOWN_NOTE); sys.exit(0)

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

def _visit(m): return frozenset((c["cpt"], mdy(c["dos"][:8])) for c in m["FT1"])      # a message's lines: each code under its own date of service
def _kept_out(stamp, fid, lines):
    """True when a register LATER than the one that held the visit (stamp) - a retry's own included - shows that very visit kept out for good ('DOS after date of
    death') or answered 'all lines already in AMD': a row that names the visit's lines (the import writes them into both rows; into the 'already' row since
    11/25/2026, the third round - so that answer ends the retry also in a new container, where the retry's batch file did not travel, and in a retry that handed
    over two visits of the patient). An 'already' row of a register from before names the feed patient only: it counts when the row is a retry's own and that
    retry's batch file is on hand and shows that it handed over this visit and no other of the patient. (A visit a later register shows ENTERED, or the
    reconciliation register shows entered or answered 'already', is in `covered` like every retried visit.) Nothing here reads the cache: the import decides,
    this only reads rows."""
    s0 = _norm(stamp)
    if any(st > s0 and f == fid and ln == lines for st, f, ln in ended + answered): return True
    for st, f in already_r:
        if f != fid or _norm(st) <= s0: continue
        try: mine = [x for x in json.load(open("feed_parsed_%s.json" % st)) if isinstance(x, dict) and x.get("pid") == fid]
        except Exception: continue
        if mine and all(_visit(x) == lines for x in mine): return True
    return False
msgs = []; handed = set()
for stamp in sorted(set(want) | set(held)):
    ids = want.get(stamp, {}); hd = held.get(stamp, {})
    for m in parsed_for(stamp):
        fid = m.get("pid")
        if fid not in ids and fid not in hd: continue                           # 11/25/2026: a message with no patient id (no PID line) is nobody's skip - passed over, it never stops the retry
        cpts = {c["cpt"] for c in m["FT1"]}; lines = _visit(m)
        by_skip = bool(cpts & ids.get(fid, set()))                               # a 'no usable dx' / 'unknown CPT' skip names one of its codes
        why_held = next((x for x in hd.get(fid, []) if (x[1] == lines if x[1] is not None else bool(cpts & x[0]))), None)      # a held row names this visit (line by line; a row without dates: by one of its codes)
        if not by_skip and why_held is None: continue                            # another visit of that patient - not the one a skip names
        if cpts - KNOWN_CPTS: unknown_cpts.update(c for c in cpts - KNOWN_CPTS if c); continue   # review round 3: a second code the import does not know yet
        if all(c["cpt"] in covered.get((m["pid"], mdy(c["dos"][:8])), set()) for c in m["FT1"]): continue   # every line, under its own date, is in AdvancedMD
        if not by_skip:                                                          # a visit held for a lost day (and for nothing else): once per run, and not once a later register settled it
            if (fid, lines) in handed or _kept_out(stamp, fid, lines): continue
            handed.add((fid, lines)); death_day.add(why_held[2])
        m = dict(m); m["_batch"] = stamp; msgs.append(m)
UNKNOWN_NOTE = unknown_note()
if not msgs:
    print("retry-dx: nothing to retry (every skipped visit that can be retried has been entered or kept out for good since)" + UNKNOWN_NOTE); sys.exit(0)
if death_day: print("retry-dx: %d chart(s) have a visit that was kept out because a date of death is on record and its day could not be read (%s) - handed to the import again: it asks again and enters the visit, keeps it out for good, or keeps it waiting" % (len(death_day), ", ".join(sorted(death_day))))

# ---- 3 re-check the codes in AMD (null cache entries are looked up again) ---------------------------------------------------------
env = dict(os.environ, FEED_STAMP=rstamp, FEED_DX_CACHE=os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json"), PYTHONPATH=WS + ":" + HERE)
json.dump(msgs, open("feed_parsed_%s.json" % rstamp, "w"), indent=1)
os.makedirs("logs", exist_ok=True)
def step(name, cmd, must=True):
    log = "logs/claimocity_%s_%s.log" % (rstamp, name)
    with open(log, "w") as fh: r = subprocess.run(cmd, cwd=WS, env=env, stdout=fh, stderr=subprocess.STDOUT, text=True)
    tail = open(log).read().strip().splitlines()[-3:]
    print("[%s] exit %d  %s" % (name, r.returncode, " | ".join(t[:160] for t in tail)))
    if r.returncode and must: print("STEP FAILED:", name, "- see", log); sys.exit(2)
    return r.returncode
step("dx", [sys.executable, os.path.join(HERE, "claimocity_dx.py")])
cache = json.load(open(env["FEED_DX_CACHE"]))
# WHICH VISITS ARE READY (William 11/25/2026, STANDING: "for any diagnosis not in the master file yet change it to i10 and send me an email with the codes needed to be
# added"). Until that day a visit was ready only when every charge line had a code AMD's list knows; a visit whose only code was missing waited until William added it
# (two 99309 visits waited on S82.843D since the batches of 11/13 and 11/22/2026). Now, when I10 itself is in the list, every charge line that carries at least ONE
# diagnosis code can go in: the import puts I10 in the place of each code the list does not have. The codes no longer hold the visit back - they are printed below and
# named in the retry's digest for William's email. A charge line with NO code at all still waits: there is nothing to change to I10. When I10 is not in the list
# (i10 false) this is the old rule, line for line.
DX_INSTEAD = "I10"      # the code that stands in a missing code's place - the same line as in claimocity_import.py (William 11/25/2026); the self-test holds the two together
i10 = bool(cache.get(DX_INSTEAD))
ready, waiting, missing, nocode = [], 0, set(), 0      # nocode: the visits that wait because a charge line carries no diagnosis code at all
for m in msgs:
    ok = True; bare = False
    for c in m["FT1"]:
        codes = [x.strip() for x in (c.get("dx") or "").split("^") if x.strip()]
        if i10 and codes: continue                                               # this line can go in: a code the list knows as it is, I10 for every other
        if not any(cache.get(x) for x in codes):
            ok = False; missing.update(x for x in codes if not cache.get(x)); bare = bare or not codes
    if ok: ready.append(m)
    else: waiting += 1; nocode += 1 if bare else 0
NOCODE = "a charge line that carries no diagnosis code at all"
def with_instead(ms):
    """(how many of these visits go in with I10 in a code's place, those codes) as the cache shows it: the codes on their charge lines that AMD's list does not have.
    Nothing when I10 itself is not in the list - then the import leaves such a code off, as it always did."""
    n, codes = 0, set()
    for m_ in (ms if i10 else []):
        u = {x.strip() for c in m_["FT1"] for x in (c.get("dx") or "").split("^") if x.strip() and not cache.get(x.strip())}
        if u: n += 1; codes |= u
    return n, codes
if not ready:
    if missing: print("retry-dx: %d visit(s) still wait on codes not in AMD's diagnosis list: %s (valid ICD-10 - William adds them in AMD Master Files > Diagnosis Codes; the next run enters the visits)" % (waiting, ", ".join(sorted(missing))))
    else: print("retry-dx: %d visit(s) still wait: %s - for William (Claimocity sent the line without a code; there is nothing to change to %s)" % (waiting, NOCODE, DX_INSTEAD))
    os.remove("feed_parsed_%s.json" % rstamp); sys.exit(0)

# ---- 4 import (+ verify, inspector, report when live) under the retry stamp ----------------------------------------------------------
json.dump(ready, open("feed_parsed_%s.json" % rstamp, "w"), indent=1)
match = {}
for m in ready:
    key = m["name"].upper().strip() + "|" + m["dob"][:8]; pid = pmap.get(m["pid"])
    if not pid: print("retry-dx: feed patient %s has no chart in the patient map - skipped" % m["pid"]); continue
    e = match.setdefault(key, {"status": "FOUND", "pids": [pid], "amd_names": [], "feed_ids": [], "resolved": pid, "via": "patient map (retry)", "by_id": {}})
    if m["pid"] not in e["feed_ids"]: e["feed_ids"].append(m["pid"])
    e["by_id"][m["pid"]] = pid      # 11/25/2026: each Claimocity id keeps the chart the map names for it (the import asks by the message's own id) - of two ids under one name and birth date the first one's chart is no longer used for both
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
_ni, _ci = with_instead(ready)      # after the batches without feed files were taken out: what this retry hands to the import
print("retry-dx stamp %s | %d visit(s) from batch(es) %s now have usable codes%s%s | mode %s" % (rstamp, len(ready), ", ".join(batches),
      (" (%d of them with %s in place of codes not in AMD's diagnosis list)" % (_ni, DX_INSTEAD)) if _ni else "",
      ("; %d still wait%s" % (waiting, (" on " + ", ".join(sorted(missing)) + (" and " + NOCODE if nocode else "")) if missing else (": " + NOCODE))) if waiting else "", "LIVE" if live else "DRY"))
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
# 11/25/2026 (William: "... and send me an email with the codes needed to be added"): the codes that went in as I10, in one line. A live retry reads them from its own
# import register (the rows that carry dx_instead - what was really entered); a dry retry writes no register and says what would be entered, by the cache.
_ent = [r for r in imp["created"] if isinstance(r, dict) and r.get("dx_instead")]
if live: _ni, _ci = len(_ent), {c for r in _ent for c in (r.get("missing_dx") or []) if isinstance(c, str)}
if _ni: print("retry-dx: %d visit(s) %s with %s in place of codes not in AMD's diagnosis list: %s (William 11/25/2026 - he adds them in AMD Master Files > Diagnosis Codes; %s)" % (
    _ni, "entered" if live else "would be entered", DX_INSTEAD, ", ".join(sorted(_ci)), "this retry's digest names the file that holds the text of his email" if live else "a live retry enters them and its digest names the file for his email"))
print("RESULT retry %s: visits created %d, skipped %d, failed %d%s%s%s" % (rstamp, len(imp["created"]), len(imp["skipped"]), len(imp["failed"]),
      "" if live else " (DRY - nothing written)", (" | still waiting on codes: " + ", ".join(sorted(missing))) if missing else "",
      (" | %d visit(s) still wait: %s - for William (Claimocity sent the line without a code)" % (nocode, NOCODE)) if nocode else "") + UNKNOWN_NOTE + pos_warn)
if live and os.path.exists("feed_digest_%s.md" % rstamp): print("digest: feed_digest_%s.md" % rstamp)
