#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the mirror's feed-register step, 11/25/2026 - widened the same day after the independent review, and
#   once more after the independent verification of the corrected step)
# Decides: nothing. Loads tools/mirror/mirror.py, points it at two throwaway folders (an invented workspace and an invented repository
#   tree - no network, no AdvancedMD, no patient data, nothing committed anywhere) and proves what `mirror.py sync` and
#   `mirror.py feed-registers` do with the Claimocity feed's registers:
#     - a batch register the workspace has and main does not (feed_import / feed_newcharts / feed_verify / feed_inspector / feed_fixholds /
#       feed_recon of any stamp, retry stamps included, and the order sweep's four - feed_order_sweep / _coverage / _resave / _fixclin, with
#       the "_N" the sweep puts on a stamp) is copied into practices/ehpa/registers/;
#     - a batch register main already has is replaced only by a FULLER workspace copy (more rows), whatever the file times say: a restored
#       copy with more rows is carried although its file is older, a shorter one never replaces a fuller one, equal rows keep main's;
#     - the registers of a stamp whose ingest is still running are not carried this time, and the line says so for the top of the report;
#     - the file register claimocity_ingest.json is MERGED: every file and every run either side knows stays (the file main did not know
#       is added; a file only main knows is not lost) - this is the register whose loss made three runs read a feed file twice;
#     - the patient map is merged and MAIN's chart stays where the two disagree (the line names the feed patient); the diagnosis cache is
#       read from the workspace ROOT, where the feed helpers keep it, a known code is never replaced by "not in AdvancedMD", and where the
#       two sides hold DIFFERENT ids for a code MAIN's id stays and the line names the code; the insurance-intake register
#       feed_in1_intake.json and - when a run wrote it - feed_dx_needed.json are merged entry by entry;
#     - (11/25/2026) feed_identity_<stamp>.json - which chart each new feed patient went to, and by which rule - travels like every other
#       batch register, and the place-of-service-61 monitor's register pos61_monitor.json is never mixed: the LATER run's stays, whole;
#     - `mirror.py feed-registers` (for a run that commits by hand) runs the privacy gate over the registers folder before it returns and
#       exits non-zero when the gate fails - and when a standing file on main is no longer JSON (the conflict markers of a pull with
#       rebase), with one line for the top of the report, so that the run's own commit of the folder does not follow; it commits and
#       stages nothing itself (asked of git on a throwaway checkout, not only searched for in its source);
#     - files whose home is main (the owner's approved file, William's quality exceptions) and files that are not feed registers are
#       never copied from the workspace; nothing is ever deleted; a broken JSON file stops nothing and is said; no odd input raises;
#     - with no workspace registers folder the step says so and does nothing;
#     - the runbook's step (e) and the three prompts that run the feed say what a run does with a line that ENDS 'TOP OF THE REPORT', in
#       the words the step really prints (section 11 reads those four texts; nothing else in the repository is read);
#     - (11/25/2026, the verification of the feed part) the helper step lets no OLDER workspace copy of a feed helper back over the
#       repository's - the parser and the download step had no marker, and the marker of the shared helper list also stood in the copy from
#       before (section 13 runs the step over the repository's real helpers, copied into the throwaway tree); and William's standing word
#       feed_same_person.json is looked at by the same guard as the other standing files, so a broken hand edit never rides into a commit
#       (section 14).
# How the gate is proven, both ways offline: (1) a stand-in gate script that writes down how it was called (and one that fails);
#   (2) the real phi_gate.py, copied into the throwaway tree (its tree mode works on the checkout it sits in) with an empty stand-in name
#   map, on an empty `git init` of that folder: an invented date behind the words the import writes for a visit after a recorded death
#   must come out as a placeholder. The one look at this machine's real process list starts four harmless stand-in processes (two
#   named like the ingest, one that only names it in an argument, one shell that runs a file of its name) under stamps of this run's
#   own - several copies of this self-test may run on one machine at once - and ends them; every other check replaces that look.
# Why: on 11/10, 11/21 and 11/24/2026 the morning run entered 60 / 84 / 26 feed visits in AdvancedMD and committed no feed register
#   (the runbook's step (e) was prose a busy run skipped). The next fresh container took main's older file register, saw the same feed
#   file as new and read it again; the visit-level records of two of those batches exist nowhere. The review of the first version of the
#   step found that none of its 16 checks would have caught what was still wrong (the diagnosis cache looked for in the wrong folder, no
#   gate in `feed-registers`, the sweep's and the intake's registers left out, a short copy on main kept for good, a days-old patient map
#   undoing a correction made on main). The verification of the corrected step, the same day, found what was still open: a file register
#   with conflict markers went to main through the run's own commit (`feed-registers` ended 0); no text told a run to act on the line's
#   ending; a days-old diagnosis cache wrote an old id back over one corrected on main; two checks proved less than their names said
#   (no check asked for the ending on a patient-map difference; "commits nothing" was a search of the source text); and the look at
#   the real process list failed when several copies of this self-test ran at once.
# Run: python3 tools/selftest/test_mirror_feed_registers.py   (exit 1 on any failure)
import os, sys, json, time, shutil, tempfile, importlib.util, io, contextlib, atexit, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("mirror_under_test", os.path.join(ROOT, "tools", "mirror", "mirror.py"))
mirror = importlib.util.module_from_spec(spec); spec.loader.exec_module(mirror)
FAILS = []
SAID = {}                                                         # what the step printed in each case a person has to see - section 11 holds the runbook's words to these very lines
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  -> " + str(extra)[:500]) if extra != "" and not cond else ""))
    if not cond: FAILS.append(name)
TMP = tempfile.mkdtemp(prefix="mirror_feedreg_"); atexit.register(shutil.rmtree, TMP, ignore_errors=True)
for _k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"): os.environ.pop(_k, None)      # started from inside a git hook, nothing here may point git at the real repository
REAL_SCAN = getattr(mirror, "_running_ingest_stamps", None)       # the real look at the process list - section 7 tests it by itself
NO_INGEST = lambda: []
mirror._running_ingest_stamps = NO_INGEST                         # everywhere else: "no ingest is running", whatever runs on this machine
REAL_GATE = mirror.GATE
mirror.GATE = os.path.join(TMP, "no_gate_named_here.py")          # the real gate works on the checkout it sits in - the REAL repository: no check may start it (section 8 uses a copy inside the throwaway tree)
START = "feed registers: %d file(s) carried into practices/ehpa/registers/"      # the start of the line the runbook, the prompts and the lessons quote
OLDER = 3 * 86400                                                 # a file three days older than the one it is compared with
def setup(label):
    ws = os.path.join(TMP, label, "ws"); repo = os.path.join(TMP, label, "repo")
    os.makedirs(os.path.join(ws, "registers")); os.makedirs(os.path.join(repo, "practices", "ehpa", "registers"))
    mirror.WS = ws; mirror.ROOT = repo
    return ws, os.path.join(repo, "practices", "ehpa", "registers")
def put(d, name, obj, age=0):
    p = os.path.join(d, name); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(obj if isinstance(obj, str) else json.dumps(obj, indent=1))
    if age: t = time.time() - age; os.utime(p, (t, t))
    return p
def get(d, name): return json.load(open(os.path.join(d, name)))
def run():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): n = mirror.sync_feed_registers()
    return n, buf.getvalue()
def cli(*args):
    """mirror.py's command line (its main()) with these arguments -> (what it exited with - None when it simply returned -, what it printed)"""
    buf = io.StringIO(); old = sys.argv; sys.argv = ["mirror.py"] + list(args); code = None
    try:
        with contextlib.redirect_stdout(buf): mirror.main()
    except SystemExit as e: code = e.code
    finally: sys.argv = old
    return code, buf.getvalue()
def lines(out): return [l for l in out.splitlines() if l.startswith("feed registers:")]
def line(out): return (lines(out) or [""])[0]
def rows(n, tag): return [{"pid": "pat%d" % i, "visit": "vst%d" % i, "from": tag} for i in range(n)]
def side(reg, name):
    """whose copy main holds now: every fixture row says where it is from"""
    t = open(os.path.join(reg, name)).read(); return "workspace" if '"workspace' in t else "main" if '"main' in t else "?"

# ---- 1. batch registers -----------------------------------------------------------------------------------------------------------------
ws, reg = setup("batch"); wr = os.path.join(ws, "registers")
BATCH = ["feed_import_20261124T1241Z.json", "feed_newcharts_20261124T1241Z.json", "feed_verify_20261124T1241Z.json", "feed_inspector_20261124T1241Z.json",
         "feed_fixholds_20261124T1241Z.json", "feed_recon_20261124T1241Z.json", "feed_import_20261113T0157ZR.json", "feed_order_sweep_20261124T184408Z.json"]
for b in BATCH: put(wr, b, {"created": [{"pid": "pat9", "visit": "vst1"}], "from": "workspace"})
put(wr, "feed_order_approved.json", {"approved_by": "invented", "from": "workspace", "visits": ["vstA", "vstB", "vstC"]})      # home is main: never from the workspace, however much more it holds
put(wr, "quality_exceptions.json", {"from": "workspace"})                                    # home is main
put(wr, "feed_same_person.json", {"pat9": {"feed_ids": ["x"], "approved_by": "invented", "from": "workspace"}})      # home is main (William's standing word 'same person', 11/25/2026): the workspace holds only a copy the ingest made
put(wr, "era_checks_before_20261124.json", {"from": "workspace"})                            # not a feed register: another step mirrors it
put(wr, "feed_import_SELFTEST.json", {"from": "workspace"})                                  # not a batch stamp
put(reg, "feed_order_approved.json", {"approved_by": "the owner", "from": "main"})
n, out = run()
check("1a every batch register main does not have is copied (import, new charts, verify, inspector, fix-holds, recon, a retry stamp, the order sweep)",
      all(os.path.exists(os.path.join(reg, b)) and get(reg, b)["from"] == "workspace" for b in BATCH), [b for b in BATCH if not os.path.exists(os.path.join(reg, b))])
check("1a2 a copied register is the workspace's file byte for byte", all(open(os.path.join(reg, b), "rb").read() == open(os.path.join(wr, b), "rb").read() for b in BATCH if os.path.exists(os.path.join(reg, b))))
check("1b the step says what it did in ONE line that starts 'feed registers: N file(s) carried into practices/ehpa/registers/' (the start other texts quote) and counts the files",
      n == len(BATCH) and len(lines(out)) == 1 and line(out).startswith(START % len(BATCH)) and len(out.splitlines()) == 1, (n, out))
check("1c files whose home is main are never taken from the workspace (the owner's approved file, the quality exceptions), nor files that are not feed registers",
      get(reg, "feed_order_approved.json")["from"] == "main" and not os.path.exists(os.path.join(reg, "quality_exceptions.json")) and not os.path.exists(os.path.join(reg, "feed_same_person.json"))
      and not os.path.exists(os.path.join(reg, "era_checks_before_20261124.json")) and not os.path.exists(os.path.join(reg, "feed_import_SELFTEST.json")), sorted(os.listdir(reg)))
n2, out2 = run()
check("1d a second run copies nothing (main's copies now hold what the workspace's hold) and says 0", n2 == 0 and "feed registers: 0 file(s)" in out2, (n2, out2))

# A register BOTH sides have and that differs: the FULLER copy is the one main gets. CHANGED 11/25/2026 after the review - the first version
# let the NEWER FILE win (old check 1e), and after a clone every file of main is newer than every restored one: a short copy on main (a
# batch that was still being entered when a run mirrored) could never be replaced by the full restored one.
ws, reg = setup("fuller"); wr = os.path.join(ws, "registers")
def imp(n, tag): return {"created": rows(n, tag), "skipped": [], "failed": []}
put(reg, "feed_import_20261124T1241Z.json", imp(2, "main")); put(wr, "feed_import_20261124T1241Z.json", imp(200, "workspace"), age=OLDER)            # main short and fresh (the clone), the restored copy full and three days OLDER
put(reg, "feed_import_20261122T1240Z.json", imp(200, "main"), age=OLDER); put(wr, "feed_import_20261122T1240Z.json", imp(120, "workspace"))            # main full, the workspace copy shorter and NEWER
put(reg, "feed_import_20261120T1240Z.json", imp(3, "main, scrubbed by the gate"), age=OLDER); put(wr, "feed_import_20261120T1240Z.json", imp(3, "workspace, raw"))      # equal rows, the workspace file newer
put(reg, "feed_recon_20261120T1240Z.json", {"rows": rows(3, "main, scrubbed by the gate")}); put(wr, "feed_recon_20261120T1240Z.json", {"rows": rows(3, "workspace, raw")}, age=OLDER)      # equal rows, the workspace file older
n, out = run()
check("1e CHANGED (content decides, no longer the file time): a restored workspace copy with MORE rows than main's is carried although its file is three days OLDER than main's",
      side(reg, "feed_import_20261124T1241Z.json") == "workspace" and len(get(reg, "feed_import_20261124T1241Z.json")["created"]) == 200, (n, out))
check("1f a workspace copy with FEWER rows never replaces main's fuller copy, although its file is the NEWER one (the old rule would have copied it)",
      side(reg, "feed_import_20261122T1240Z.json") == "main" and len(get(reg, "feed_import_20261122T1240Z.json")["created"]) == 200, (n, out))
check("1g with EQUAL rows main's copy stays (the tree gate may have scrubbed it) - whether the workspace file is newer or older",
      side(reg, "feed_import_20261120T1240Z.json") == "main" and side(reg, "feed_recon_20261120T1240Z.json") == "main", (n, out))
check("1h only the fuller copy counts as carried, and the line names it with both row counts (2 -> 200 rows) behind the unchanged start",
      n == 1 and len(lines(out)) == 1 and line(out).startswith(START % 1) and "feed_import_20261124T1241Z.json (2 -> 200 rows)" in out, (n, out))
n2, out2 = run()
check("1i after that a second run carries nothing: the fuller copy is on main, the shorter and the equal ones are still passed over", n2 == 0 and line(out2).startswith(START % 0), (n2, out2))
# what a "row" is, family by family (in every pair the workspace file is the OLDER one, so only the count can make it win)
ws, reg = setup("rows"); wr = os.path.join(ws, "registers")
put(reg, "feed_import_20261101T0001Z.json", imp(3, "main")); put(wr, "feed_import_20261101T0001Z.json", {"created": rows(1, "workspace"), "skipped": rows(2, "workspace"), "failed": rows(1, "workspace")}, age=OLDER)      # 3 against 1 + 2 + 1
put(reg, "feed_import_20261101T0002Z.json", imp(2, "main")); put(wr, "feed_import_20261101T0002Z.json", {"created": rows(1, "workspace"), "skipped": [], "failed": [], "notes": rows(50, "workspace")}, age=OLDER)      # 2 against 1: the 50 are no rows
put(reg, "feed_recon_20261101T0001Z.json", {"files": ["a", "b", "c", "d", "e"], "rows": rows(1, "main")}); put(wr, "feed_recon_20261101T0001Z.json", {"files": ["a"], "rows": rows(2, "workspace")}, age=OLDER)
put(reg, "feed_recon_20261101T0002Z.json", {"files": ["a"], "rows": rows(2, "main")}); put(wr, "feed_recon_20261101T0002Z.json", {"files": ["a", "b", "c", "d", "e"], "rows": rows(1, "workspace")}, age=OLDER)
put(reg, "feed_inspector_20261101T0001Z.json", {"fixed": rows(1, "main"), "held": rows(1, "main")}); put(wr, "feed_inspector_20261101T0001Z.json", {"fixed": rows(1, "workspace"), "held": rows(1, "workspace"), "quality_removed": rows(1, "workspace")}, age=OLDER)
put(reg, "feed_order_coverage_20261101T000101Z.json", {"what": "invented", "answers": rows(4, "main")}); put(wr, "feed_order_coverage_20261101T000101Z.json", {"what": "invented", "answers": rows(3, "workspace")}, age=OLDER)
put(reg, "feed_newcharts_20261101T0001Z.json", rows(2, "main")); put(wr, "feed_newcharts_20261101T0001Z.json", rows(3, "workspace"), age=OLDER)                                                    # a document that is a list
put(reg, "feed_verify_20261101T0001Z.json", {"pat1": {"from": "main"}}); put(wr, "feed_verify_20261101T0001Z.json", {"pat1": {"from": "workspace"}, "pat2": {"from": "workspace"}}, age=OLDER)        # keyed by chart, no list at all
put(reg, "feed_verify_20261101T0002Z.json", {"pat1": {"from": "main"}, "pat2": {"from": "main"}}); put(wr, "feed_verify_20261101T0002Z.json", {"pat1": {"from": "workspace"}}, age=OLDER)
n, out = run()
check("1j rows of a feed_import register = created + skipped + failed (1 + 2 + 1 beats 3), and a list under any other key is not a row (1 row with 50 notes does not beat 2)",
      side(reg, "feed_import_20261101T0001Z.json") == "workspace" and side(reg, "feed_import_20261101T0002Z.json") == "main", out)
check("1k rows of a feed_recon register = its rows, not its list of files (2 rows of 1 file beat 1 row of 5 files, and not the other way round)",
      side(reg, "feed_recon_20261101T0001Z.json") == "workspace" and side(reg, "feed_recon_20261101T0002Z.json") == "main", out)
check("1l rows of any other family = the total of its top-level lists (inspector 3 beats 2; the sweep's coverage 3 does not beat 4), of a document that is a list = its length, of a register keyed by chart with no list at all (feed_verify) = its entries",
      side(reg, "feed_inspector_20261101T0001Z.json") == "workspace" and side(reg, "feed_order_coverage_20261101T000101Z.json") == "main" and side(reg, "feed_newcharts_20261101T0001Z.json") == "workspace"
      and side(reg, "feed_verify_20261101T0001Z.json") == "workspace" and side(reg, "feed_verify_20261101T0002Z.json") == "main" and n == 5, (n, out))
# the order sweep's registers that hold state (the dated checks bought, the saves and every STOP, the clinician moves) and the "_N" suffix
ws, reg = setup("sweep"); wr = os.path.join(ws, "registers")
SWEEP = ["feed_order_coverage_20261124T184408Z.json", "feed_order_resave_20261124T184408Z.json", "feed_order_fixclin_20261124T184408Z.json", "feed_order_sweep_20261124T184408Z.json",
         "feed_order_sweep_20261124T184408Z_2.json", "feed_order_coverage_20261124T184408Z_2.json", "feed_order_resave_20261124T184408Z_3.json", "feed_order_fixclin_20261124T184408Z_12.json"]
NOT_SWEEP = ["feed_order_notes_20261124T184408Z.json", "feed_order_sweep_20261124T184408Z_2_decisions.json", "feed_order_sweep_20261124T184408Z_x.json", "feed_order_resave_20261124.json", "feed_import_20261124T1241Z_2.json"]
for b in SWEEP + NOT_SWEEP: put(wr, b, {"what": "invented", "rows": rows(1, "workspace")})
n, out = run()
check("1m the order sweep's other registers travel too - feed_order_coverage (keeps a check from being bought twice), feed_order_resave (the pilot and every STOP) and feed_order_fixclin - with or without the '_N' the sweep puts on a stamp when two runs start in one second",
      all(os.path.exists(os.path.join(reg, b)) for b in SWEEP) and n == len(SWEEP), ([b for b in SWEEP if not os.path.exists(os.path.join(reg, b))], out))
check("1n a name that only looks like one of them is not carried (another kind, a '_decisions' file, a suffix that is no number, a stamp without a time, an import stamp with a suffix)",
      not any(os.path.exists(os.path.join(reg, b)) for b in NOT_SWEEP), sorted(os.listdir(reg)))
# a register that is rewritten WHILE the mirror is at work (the sweep runs in the background and writes its registers as it goes)
ws, reg = setup("written_meanwhile"); wr = os.path.join(ws, "registers"); _victim = put(wr, "feed_order_resave_20261124T184408Z.json", {"what": "invented", "rows": rows(2, "workspace")}); _checked = open(_victim, "rb").read()
class _JsonWhileAHelperWrites:
    """the json module as mirror.py sees it - but the first time the register has been read and checked, the background helper writes on"""
    hit = False
    def __getattr__(self, k): return getattr(json, k)
    def loads(self, s, *a, **kw):
        v = json.loads(s, *a, **kw)
        if not self.hit: self.hit = True; open(_victim, "w").write('{"what": "invented", "rows": [ {"pid": "pat1", "half of the next')
        return v
_real_json = mirror.json; mirror.json = _JsonWhileAHelperWrites()
try: n, out = run()
finally: mirror.json = _real_json
check("1o main gets the very bytes that were read and checked: a register a background helper rewrites while the mirror is at work reaches main as the checked version, never as the half-written one",
      os.path.exists(os.path.join(reg, "feed_order_resave_20261124T184408Z.json")) and open(os.path.join(reg, "feed_order_resave_20261124T184408Z.json"), "rb").read() == _checked and n == 1, (n, out))

# ---- 2. the file register is merged ------------------------------------------------------------------------------------------------------
ws, reg = setup("ingest"); wr = os.path.join(ws, "registers")
MAIN_REG = {"files": {"download__20261121.hl7": {"stamp": "20261121T1840Z", "sha256": "aa", "messages": 84, "at": "2026-11-21T18:42:00Z"},
                      "download__20261122.hl7": {"stamp": "20261122T1240Z", "sha256": "bb", "messages": 51, "at": "2026-11-22T12:55:00Z"}},
            "runs": [{"stamp": "20261121T1840Z", "at": "2026-11-21T18:42:00Z", "live": True, "files": ["download__20261121.hl7"], "exit": 0},
                     {"stamp": "20261122T1240Z", "at": "2026-11-22T12:55:00Z", "live": True, "files": ["download__20261122.hl7"], "exit": 0}]}
WS_REG = {"files": {"download__20261121.hl7": {"stamp": "20261121T1240Z", "sha256": "aa", "messages": 84, "at": "2026-11-21T13:05:00Z"},     # the run that REALLY entered them
                    "download__20261124.hl7": {"stamp": "20261124T1241Z", "sha256": "cc", "messages": 26, "at": "2026-11-24T13:00:00Z"}},     # main never heard of this file
          "runs": [{"stamp": "20261121T1240Z", "at": "2026-11-21T13:05:00Z", "live": True, "files": ["download__20261121.hl7"], "exit": 0},
                   {"stamp": "20261124T1241Z", "at": "2026-11-24T13:00:00Z", "live": True, "files": ["download__20261124.hl7"], "exit": 0}]}
put(reg, "claimocity_ingest.json", MAIN_REG); put(wr, "claimocity_ingest.json", WS_REG, age=5 * 86400)      # even an OLD workspace copy is merged: a merge loses nothing
n, out = run(); m = get(reg, "claimocity_ingest.json")
check("2a the file register is MERGED: the file main did not know (20261124) is added and the file only main knows (20261122) is not lost",
      set(m["files"]) == {"download__20261121.hl7", "download__20261122.hl7", "download__20261124.hl7"} and m["files"]["download__20261124.hl7"]["stamp"] == "20261124T1241Z", m["files"])
check("2b for a file both sides know, the EARLIEST registration stays - the run that really entered the visits (not the later re-read)",
      m["files"]["download__20261121.hl7"]["stamp"] == "20261121T1240Z" and m["files"]["download__20261121.hl7"]["at"] == "2026-11-21T13:05:00Z", m["files"]["download__20261121.hl7"])
check("2c every run of both sides is kept once, in time order", [r["stamp"] for r in m["runs"]] == ["20261121T1240Z", "20261121T1840Z", "20261122T1240Z", "20261124T1241Z"], [r["stamp"] for r in m["runs"]])
n_again, _o = run(); m2 = get(reg, "claimocity_ingest.json")
check("2d the merge is repeatable: a second run changes nothing and counts nothing", m2 == m and n_again == 0, n_again)
check("2e the workspace copy itself is not touched", get(wr, "claimocity_ingest.json") == WS_REG)

# ---- 3. the patient map and the diagnosis cache ------------------------------------------------------------------------------------------
ws, reg = setup("maps"); wr = os.path.join(ws, "registers")
put(reg, "claimocity_patient_map.json", {"feedA": "pat1", "feedB": "pat2"}); put(wr, "claimocity_patient_map.json", {"feedB": "pat22", "feedC": "pat3"})
put(reg, "dx_cache_feed.json", {"I10": "dcode1", "E119": "dcode2", "S82843D": None})
put(ws, "dx_cache_feed.json", {"E119": None, "S82843D": "dcode9", "M5117": "dcode7"})                              # the LIVE cache: at the workspace ROOT, where claimocity_dx.py writes it
put(wr, "dx_cache_feed.json", {"I10": "dcode1", "E119": "dcode2", "S82843D": None, "Z9999": "dcode-only-in-the-snapshot"})      # registers/: the bootstrap's snapshot of main, no helper writes it
n, out = run(); SAID["the patient map differs"] = out
check("3a CHANGED (main's chart stays; before, the workspace answered and a days-old restored map undid a correction made on main): the patient map is merged - a patient only the workspace knows is added, and where the two disagree MAIN's chart is kept and the line names the feed patient with both charts so a person can decide - and ends 'TOP OF THE REPORT' (nothing else in this fixture asks for those words)",
      get(reg, "claimocity_patient_map.json") == {"feedA": "pat1", "feedB": "pat2", "feedC": "pat3"} and "patient map: 1 feed patient(s) differ - main's chart kept: feedB (main pat2, workspace pat22)" in out
      and len(lines(out)) == 1 and line(out).startswith(START % 2) and out.rstrip().endswith("TOP OF THE REPORT"), (get(reg, "claimocity_patient_map.json"), out))
check("3b CHANGED (the cache is read from the workspace ROOT, where the feed helpers keep it; before, from registers/, where only a snapshot of main lies): the diagnosis cache is merged - new codes are added, a code that was missing and now has its AdvancedMD id takes it, and a KNOWN code is never replaced by 'not in AdvancedMD'",
      {k: v for k, v in get(reg, "dx_cache_feed.json").items() if k != "Z9999"} == {"I10": "dcode1", "E119": "dcode2", "S82843D": "dcode9", "M5117": "dcode7"}, get(reg, "dx_cache_feed.json"))
check("3b2 the registers/ snapshot is NOT taken when the root file exists (a code only the snapshot holds does not reach main)", "Z9999" not in get(reg, "dx_cache_feed.json"), get(reg, "dx_cache_feed.json"))
check("3b3 both merged files are written the way the feed helpers write them (one entry a line, keys in order), so a diff on main shows only what changed",
      open(os.path.join(reg, "dx_cache_feed.json")).read() == json.dumps({"I10": "dcode1", "E119": "dcode2", "S82843D": "dcode9", "M5117": "dcode7"}, indent=0, sort_keys=True)
      and open(os.path.join(reg, "claimocity_patient_map.json")).read() == json.dumps({"feedA": "pat1", "feedB": "pat2", "feedC": "pat3"}, indent=0, sort_keys=True))
put(wr, "claimocity_patient_map.json", "{ this is not json"); put(wr, "feed_import_20261125T0640Z.json", {"from": "workspace"})
n, out = run(); SAID["a file could not be read"] = out
check("3c a workspace file that cannot be read stops nothing: it is named, main's copy stays as it is, and the other registers are still copied",
      get(reg, "claimocity_patient_map.json") == {"feedA": "pat1", "feedB": "pat2", "feedC": "pat3"} and os.path.exists(os.path.join(reg, "feed_import_20261125T0640Z.json")) and "claimocity_patient_map.json" in out and "could not be read" in out, out)
ws, reg = setup("dxfallback"); wr = os.path.join(ws, "registers")
put(reg, "dx_cache_feed.json", {"I10": "dcode1"}); put(wr, "dx_cache_feed.json", {"I10": "dcode1", "M5117": "dcode7"})          # no cache at the workspace root here
n, out = run()
check("3d only when the workspace has NO cache at its root is the registers/ copy merged instead (the fallback)", get(reg, "dx_cache_feed.json") == {"I10": "dcode1", "M5117": "dcode7"} and n == 1, (n, out))
ws, reg = setup("dxrootbroken"); wr = os.path.join(ws, "registers")
put(reg, "dx_cache_feed.json", {"I10": "dcode1"}); put(ws, "dx_cache_feed.json", "{ this is not json"); put(wr, "dx_cache_feed.json", {"I10": "dcode1", "Z9999": "dcode-only-in-the-snapshot"})
n, out = run()
check("3d2 a cache at the workspace root that cannot be read is named for the top of the report - the registers/ snapshot is not taken in its place, and main's cache stays as it is",
      get(reg, "dx_cache_feed.json") == {"I10": "dcode1"} and n == 0 and "dx_cache_feed.json" in out and "could not be read" in out and out.rstrip().endswith("TOP OF THE REPORT"), (n, out))
ws, reg = setup("dxrootonly"); shutil.rmtree(os.path.join(ws, "registers"))
put(reg, "dx_cache_feed.json", {"I10": "dcode1"}); put(ws, "dx_cache_feed.json", {"M5117": "dcode7"})
n, out = run()
check("3e the live cache at the workspace root is merged even in a workspace that has no registers folder", get(reg, "dx_cache_feed.json") == {"I10": "dcode1", "M5117": "dcode7"} and n == 1 and line(out).startswith(START % 1), (n, out))
ws, reg = setup("mapcap"); wr = os.path.join(ws, "registers")
put(reg, "claimocity_patient_map.json", {"feed%02d" % i: "pat%d" % i for i in range(25)}); put(wr, "claimocity_patient_map.json", {"feed%02d" % i: "pat9%d" % i for i in range(25)})
n, out = run()
check("3f when many feed patients differ the line counts them all, names the first 20 and says how many more there are - main's map is not changed, and the line ends 'TOP OF THE REPORT' although nothing was carried",
      "patient map: 25 feed patient(s) differ - main's chart kept: feed00" in out and "feed19" in out and "feed20" not in out and "+5 more" in out and n == 0
      and get(reg, "claimocity_patient_map.json") == {"feed%02d" % i: "pat%d" % i for i in range(25)} and out.rstrip().endswith("TOP OF THE REPORT"), (n, out))
# A code BOTH sides hold under two DIFFERENT AdvancedMD ids (11/25/2026, the independent verification of the corrected step): MAIN's id stays
# and the line names the code for a person - the patient map's rule. Until then the workspace's id replaced main's without a word, and since
# the live cache at the workspace root is the source that happened in every sync: a days-old cache restored from the state bundle undid an
# id corrected on main, also in a run that never ran the feed - and the daily feed task then sent that id on the charge. (claimocity_dx.py
# looks a code up only while the cache holds no id for it, so a cached id is not this run's fresher knowledge.)
ws, reg = setup("dxdiffer"); wr = os.path.join(ws, "registers")
MAIN_DX = {"I10": "dcode1", "M51.17": "dcode-corrected-on-main", "E11.9": None, "Z74.1": "dcode5"}
WS_DX = {"I10": "dcode1", "M51.17": "dcode-old", "E11.9": "dcode2", "Z74.1": None, "R26.89": "dcode9", "F03.90": None}      # the same id, another id, an id for main's null, a null for main's id, two codes main lacks
put(reg, "dx_cache_feed.json", MAIN_DX); put(ws, "dx_cache_feed.json", WS_DX, age=OLDER)
n, out = run(); SAID["the diagnosis cache differs"] = out
check("3g CHANGED RULE (where both sides hold an id MAIN's stays; before, the workspace's replaced it without a word): a diagnosis code main and the workspace hold under two different AdvancedMD ids keeps MAIN's id; everything else is as before - a code main lacks is added, an id takes the place of main's 'not in AdvancedMD', never the other way round",
      get(reg, "dx_cache_feed.json") == {"I10": "dcode1", "M51.17": "dcode-corrected-on-main", "E11.9": "dcode2", "Z74.1": "dcode5", "R26.89": "dcode9", "F03.90": None} and n == 1, (n, get(reg, "dx_cache_feed.json")))
check("3g2 the line names that code with both ids behind its unchanged start, for a person to decide, and ends 'TOP OF THE REPORT' (nothing else in this fixture asks for those words); the codes that merely fill a gap are not named",
      len(lines(out)) == 1 and len(out.splitlines()) == 1 and line(out).startswith(START % 1) and "diagnosis cache: 1 code(s) differ - main's id kept: M51.17 (main dcode-corrected-on-main, workspace dcode-old)" in out
      and out.rstrip().endswith("TOP OF THE REPORT") and not any(c in out for c in ("E11.9", "Z74.1", "R26.89", "F03.90", "I10")), out)
n2, out2 = run()
check("3g3 a second run changes nothing on main and counts nothing - and still names the code for the top of the report, as long as the two sides differ; the workspace's cache is not touched",
      n2 == 0 and get(reg, "dx_cache_feed.json") == {"I10": "dcode1", "M51.17": "dcode-corrected-on-main", "E11.9": "dcode2", "Z74.1": "dcode5", "R26.89": "dcode9", "F03.90": None} and line(out2).startswith(START % 0)
      and "diagnosis cache: 1 code(s) differ - main's id kept: M51.17 (main dcode-corrected-on-main, workspace dcode-old)" in out2 and out2.rstrip().endswith("TOP OF THE REPORT") and get(ws, "dx_cache_feed.json") == WS_DX, (n2, out2))
ws, reg = setup("dxcap"); wr = os.path.join(ws, "registers")
put(reg, "dx_cache_feed.json", {"A%02d.1" % i: "dcode1%02d" % i for i in range(25)}); put(ws, "dx_cache_feed.json", {"A%02d.1" % i: "dcode2%02d" % i for i in range(25)})
n, out = run()
check("3h when many codes differ the line counts them all, names the first 20 and says how many more there are - and main's cache is not changed",
      "diagnosis cache: 25 code(s) differ - main's id kept: A00.1 (main dcode100, workspace dcode200)" in out and "A19.1" in out and "A20.1" not in out and "+5 more" in out and n == 0
      and get(reg, "dx_cache_feed.json") == {"A%02d.1" % i: "dcode1%02d" % i for i in range(25)} and out.rstrip().endswith("TOP OF THE REPORT"), (n, out))
ws, reg = setup("mapanddx"); wr = os.path.join(ws, "registers")
put(reg, "claimocity_patient_map.json", {"feedA": "pat1"}); put(wr, "claimocity_patient_map.json", {"feedA": "pat11"}); put(reg, "dx_cache_feed.json", {"M51.17": "dcode1"}); put(ws, "dx_cache_feed.json", {"M51.17": "dcode2"})
n, out = run()
check("3i when the patient map AND the diagnosis cache disagree, ONE line says both - the patient map first - and ends 'TOP OF THE REPORT' once",
      len(out.splitlines()) == 1 and 0 < out.find("patient map: 1 feed patient(s) differ - main's chart kept: feedA (main pat1, workspace pat11)") < out.find("diagnosis cache: 1 code(s) differ - main's id kept: M51.17 (main dcode1, workspace dcode2)")
      and out.count("TOP OF THE REPORT") == 1 and out.rstrip().endswith("TOP OF THE REPORT") and n == 0, (n, out))

# ---- 4. nothing to do --------------------------------------------------------------------------------------------------------------------
ws, reg = setup("none"); shutil.rmtree(os.path.join(ws, "registers"))
n, out = run()
check("4a with no registers folder in the workspace the step says so and does nothing", n == 0 and "feed registers:" in out and os.listdir(reg) == [], out)
src = open(os.path.join(ROOT, "tools", "mirror", "mirror.py")).read()
check("4b `mirror.py sync` runs the step before it commits (after the helpers, before commit_and_push)",
      src.index("sync_feed_registers()", src.index('if cmd == "sync":')) < src.index("commit_and_push(msg)", src.index('if cmd == "sync":')), "order")
_fr = src[src.index('if cmd == "feed-registers":'):] if 'if cmd == "feed-registers":' in src else ""
check("4c CHANGED NAME (it is a search of the source text and said more than it proves; 8c2 and 8k prove on a throwaway checkout that nothing is committed or staged): `mirror.py feed-registers` is the step alone, for a run that commits by hand (the daily feed task) - its own lines call the step, name no commit-and-push and no git command, and the usage line names it",
      "sync_feed_registers()" in _fr and "commit_and_push" not in _fr and "git " not in _fr.split("sys.exit(")[0] and "postman|feed-registers]" in src, "subcommand")

# ---- 5. the insurance-intake register (feed_in1_intake.json: chart|carrier -> what was done, with the run's stamp) ------------------------
ws, reg = setup("intake"); wr = os.path.join(ws, "registers")
MAIN_IN1 = {"1001|FLO99": {"outcome": "listed - invented (only main knows this one)", "stamp": "2026-11-19T0755Z"},
            "1002|SUN01": {"outcome": "added SUN01 as ins7 seq 2 (main, the older run)", "ins": "ins7", "stamp": "2026-11-19T0755Z"},
            "1003|MCAD": {"outcome": "not active - invented (main, the newer run)", "stamp": "2026-11-24T1241Z"},
            "1004|HUM01": {"outcome": "listed - the same run's entry, as the gate left it (main)", "stamp": "2026-11-22T1240Z"},
            "1006|SIM01": {"outcome": "listed - no stamp (main)"}}
WS_IN1 = {"1002|SUN01": {"outcome": "listed - invented (workspace, the newer run)", "stamp": "20261122T1240Z"},                  # the other stamp form the helpers write
          "1003|MCAD": {"outcome": "listed - invented (workspace, the older run)", "stamp": "2026-11-19T0755Z"},
          "1004|HUM01": {"outcome": "listed - the same run's entry, raw (workspace)", "stamp": "2026-11-22T1240Z"},
          "1005|AAR01": {"outcome": "added AAR01 as ins9 seq 2 (only the workspace knows this one)", "ins": "ins9", "stamp": "2026-11-24T1241Z"},
          "1006|SIM01": {"outcome": "listed - no stamp (workspace)"}}
put(reg, "feed_in1_intake.json", MAIN_IN1); put(wr, "feed_in1_intake.json", WS_IN1, age=5 * 86400)
n, out = run(); m = get(reg, "feed_in1_intake.json")
check("5a the insurance-intake register is MERGED: a chart and carrier only main knows stays, one only the workspace knows is added (so no chart and carrier is asked - and no Medicaid check bought - twice)",
      set(m) == {"1001|FLO99", "1002|SUN01", "1003|MCAD", "1004|HUM01", "1005|AAR01", "1006|SIM01"} and m["1001|FLO99"] == MAIN_IN1["1001|FLO99"] and m["1005|AAR01"] == WS_IN1["1005|AAR01"] and n == 1, (n, m))
check("5b for a chart and carrier both know, the entry of the NEWER run stays, whole (never a mix of two entries) - whichever side holds it and in whichever stamp form",
      m["1002|SUN01"] == WS_IN1["1002|SUN01"] and m["1003|MCAD"] == MAIN_IN1["1003|MCAD"], (m["1002|SUN01"], m["1003|MCAD"]))
check("5c the same run's entry on both sides: main's stays (the tree gate may have scrubbed it); an entry with no stamp on either side: the workspace's",
      m["1004|HUM01"] == MAIN_IN1["1004|HUM01"] and m["1006|SIM01"] == WS_IN1["1006|SIM01"], (m["1004|HUM01"], m["1006|SIM01"]))
check("5d it is written the way feed_in1_intake.py writes it, main's entries in their order and the new ones behind them",
      open(os.path.join(reg, "feed_in1_intake.json")).read() == json.dumps({"1001|FLO99": MAIN_IN1["1001|FLO99"], "1002|SUN01": WS_IN1["1002|SUN01"], "1003|MCAD": MAIN_IN1["1003|MCAD"], "1004|HUM01": MAIN_IN1["1004|HUM01"],
                                                                         "1006|SIM01": WS_IN1["1006|SIM01"], "1005|AAR01": WS_IN1["1005|AAR01"]}, indent=1))
n_again, _o = run()
check("5e the merge is repeatable (a second run changes nothing and counts nothing) and the workspace copy is not touched", get(reg, "feed_in1_intake.json") == m and n_again == 0 and get(wr, "feed_in1_intake.json") == WS_IN1, n_again)

# ---- 6. feed_dx_needed.json (the diagnosis codes the feed carried that are not in AdvancedMD's list yet) - only when a run wrote it ---------
# The two field names are put together here: the privacy gate takes a quoted value behind them for a name part and would rewrite THIS file.
# It does the same to the register itself on main: a stamp that holds a letter (every stamp form the feed helpers write holds a T and a Z)
# comes out as [name] under these two names. The helper that writes the register therefore has to write those two stamps without a letter
# or under other names - first_seen / last_seen pass the gate (8f), and the merge treats both spellings alike (6g).
F, L = "fir" + "st", "la" + "st"
def dxn(first, last, visits, emailed): return {F: first, L: last, "visits": visits, "emailed": emailed}
ws, reg = setup("dxneeded"); wr = os.path.join(ws, "registers")
MAIN_DXN = {"M51.17": dxn("2026-11-10T1240Z", "2026-11-20T1240Z", 4, ""),
            "E11.649": dxn("20261101T0640Z", "20261105T0640Z", 2, "20261105T2200Z"),               # only main knows this code
            "R26.89": dxn("2026-11-22T1240Z", "2026-11-22T1240Z", 1, "2026-11-22T2200Z"),
            "Z74.1": dxn("", "20261110T0640Z", 7, "20261110T2200Z")}
WS_DXN = {"M51.17": dxn("20261105T0640Z", "20261124T1241Z", 3, "20261124T2200Z"),                  # seen earlier, seen later, fewer visits, emailed
          "R26.89": dxn("2026-11-23T1240Z", "2026-11-24T1241Z", 5, ""),                            # seen later only, more visits, not emailed here
          "Z74.1": dxn("20261102T0640Z", "20261109T0640Z", 7, "20261120T2200Z"),                   # main has no first stamp; both were emailed
          "S82.843D": dxn("20261124T1241Z", "20261124T1241Z", 1, "")}                              # only the workspace knows this code
put(reg, "feed_dx_needed.json", MAIN_DXN); put(wr, "feed_dx_needed.json", WS_DXN, age=5 * 86400)
n, out = run(); m = get(reg, "feed_dx_needed.json")
check("6a feed_dx_needed.json is merged code by code: a code only main knows stays as it is and a code only the workspace knows is added",
      set(m) == {"M51.17", "E11.649", "R26.89", "Z74.1", "S82.843D"} and m["E11.649"] == MAIN_DXN["E11.649"] and m["S82.843D"] == WS_DXN["S82.843D"] and n == 1, (n, m))
check("6b for a code both know: first = the EARLIER stamp that is set, last = the LATER, visits = the LARGER, emailed = the LATER one that is set - whichever side holds it and in whichever stamp form",
      m["M51.17"] == dxn("20261105T0640Z", "20261124T1241Z", 4, "20261124T2200Z") and m["R26.89"] == dxn("2026-11-22T1240Z", "2026-11-24T1241Z", 5, "2026-11-22T2200Z")
      and m["Z74.1"] == dxn("20261102T0640Z", "20261110T0640Z", 7, "20261120T2200Z"), (m.get("M51.17"), m.get("R26.89"), m.get("Z74.1")))
n_again, _o = run()
check("6c the merge is repeatable (a second run changes nothing and counts nothing) and the workspace copy is not touched", get(reg, "feed_dx_needed.json") == m and n_again == 0 and get(wr, "feed_dx_needed.json") == WS_DXN, n_again)
ws, reg = setup("dxneeded_none"); put(reg, "feed_dx_needed.json", MAIN_DXN)
n, out = run()
check("6d only when the workspace has the file: a workspace without feed_dx_needed.json leaves main's copy exactly as it is", get(reg, "feed_dx_needed.json") == MAIN_DXN and n == 0, (n, out))
ws, reg = setup("dxneeded_new"); wr = os.path.join(ws, "registers"); put(wr, "feed_dx_needed.json", WS_DXN)
n, out = run()
check("6e main gets the register the first time a workspace has it", os.path.exists(os.path.join(reg, "feed_dx_needed.json")) and get(reg, "feed_dx_needed.json") == WS_DXN and n == 1, (n, out))
ws, reg = setup("dxneeded_placeholder"); wr = os.path.join(ws, "registers")
put(reg, "feed_dx_needed.json", {"M51.17": dxn("[name]", "[name]", 2, "")}); put(wr, "feed_dx_needed.json", {"M51.17": dxn("20261105T0640Z", "20261124T1241Z", 2, "")})
n, out = run()
check("6f a value that is no stamp (the privacy gate's placeholder on main, an empty text) counts as not set: the other side's stamp is taken",
      get(reg, "feed_dx_needed.json") == {"M51.17": dxn("20261105T0640Z", "20261124T1241Z", 2, "")}, get(reg, "feed_dx_needed.json"))
ws, reg = setup("dxneeded_names"); wr = os.path.join(ws, "registers")
put(reg, "feed_dx_needed.json", {"M51.17": {"first_seen": "2026-11-10T1240Z", "last_seen": "2026-11-20T1240Z", "visits": 4, "emailed": "", "note": "main's"}})
put(wr, "feed_dx_needed.json", {"M51.17": {"first_seen": "20261105T0640Z", "last_seen": "20261124T1241Z", "visits": 3, "emailed": "20261124T2200Z", "note": "the workspace's", "kind": "invented"}})
n, out = run()
check("6g the same rule holds when the helper names the two stamps first_seen / last_seen (names the privacy gate leaves alone); any other field both sides hold stays main's, and one only the workspace holds is added",
      get(reg, "feed_dx_needed.json") == {"M51.17": {"first_seen": "20261105T0640Z", "last_seen": "20261124T1241Z", "visits": 4, "emailed": "20261124T2200Z", "note": "main's", "kind": "invented"}}, get(reg, "feed_dx_needed.json"))

# ---- 7. the registers of a stamp whose ingest is still running ---------------------------------------------------------------------------
ws, reg = setup("running"); wr = os.path.join(ws, "registers")
STILL = ["feed_import_20261125T0640Z.json", "feed_newcharts_20261125T0640Z.json"]                                    # the running ingest's own registers, half written
DONE = ["feed_import_20261124T1241Z.json", "feed_recon_20261124T1241Z.json", "feed_import_20261125T0640ZR.json", "feed_order_sweep_20261125T064000Z.json"]      # another batch, a retry stamp, the sweep
for b in STILL + DONE: put(wr, b, imp(1, "workspace"))
put(reg, "claimocity_patient_map.json", {"feedA": "pat1"}); put(wr, "claimocity_patient_map.json", {"feedA": "pat1", "feedC": "pat3"})
mirror._running_ingest_stamps = lambda: ["20261125T0640Z"]
n, out = run(); SAID["an ingest is still running"] = out
check("7a the batch registers of a stamp whose ingest is still running are NOT carried this time; every other register is, and the standing files are still merged",
      not any(os.path.exists(os.path.join(reg, b)) for b in STILL) and all(os.path.exists(os.path.join(reg, b)) for b in DONE) and get(reg, "claimocity_patient_map.json") == {"feedA": "pat1", "feedC": "pat3"} and n == len(DONE) + 1, (n, out, sorted(os.listdir(reg))))
check("7b the line says so behind its unchanged start - which stamp, how many registers - and ends 'TOP OF THE REPORT'",
      len(lines(out)) == 1 and line(out).startswith(START % (len(DONE) + 1)) and "an ingest is still running (stamp 20261125T0640Z): its 2 register(s) are not carried this time - TOP OF THE REPORT" in out
      and out.rstrip().endswith("TOP OF THE REPORT"), out)
mirror._running_ingest_stamps = NO_INGEST
n, out = run()
check("7c once the ingest has ended the next mirror carries them, and the line no longer speaks of a running ingest", all(os.path.exists(os.path.join(reg, b)) for b in STILL) and n == len(STILL) and "still running" not in out and "TOP OF THE REPORT" not in out, (n, out))
ws, reg = setup("running_nostamp"); wr = os.path.join(ws, "registers")
for b in STILL: put(wr, b, imp(1, "workspace"))
mirror._running_ingest_stamps = lambda: [""]
n, out = run(); SAID["an ingest is still running, its stamp not readable"] = out
check("7d an ingest started without --stamp: its stamp is not known, so nothing is held back - the line says an ingest is still running and that its stamp cannot be read (not that registers were left behind), for the top of the report. CHANGED WORDS: it tells the run to mirror again when the ingest has ended - it no longer says 'until the next mirror', which promised too much (with equal rows a finished copy does not replace an unfinished one)",
      all(os.path.exists(os.path.join(reg, b)) for b in STILL) and "an ingest is still running (its stamp cannot be read" in out and "not carried this time" not in out
      and "a register it is still writing may be on main unfinished - mirror again when it has ended - TOP OF THE REPORT" in out and "until the next mirror" not in out
      and out.rstrip().endswith("TOP OF THE REPORT") and line(out).startswith(START % len(STILL)), (n, out))
mirror._running_ingest_stamps = NO_INGEST
if REAL_SCAN is None:
    check("7e the real look at the process list sees a running claimocity_ingest.py and reads its stamp", False, "mirror.py has no _running_ingest_stamps")
elif not os.path.isdir("/proc/%d" % os.getpid()):
    print("ok   7e (not run here: this machine has no /proc, so no running ingest can be seen on it)")
else:
    d = os.path.join(TMP, "processes"); os.makedirs(d)
    standin = put(d, "claimocity_ingest.py", "import time\ntime.sleep(120)\n"); other = put(d, "some_other_helper.py", "import time\ntime.sleep(120)\n")
    notpy = put(os.path.join(d, "not_python"), "claimocity_ingest.py", "read _wait_here\n")      # a SHELL script of the helper's name: it waits on its input until it is ended
    # This run's OWN made-up stamps (11/25/2026, the independent verification): several copies of this self-test run on one machine at once
    # (parallel sessions), and with one fixed stamp for all of them each saw the others' stand-ins - check 7f failed in 13 of 180 runs, six
    # at a time, and such a failure reads like a defect in mirror.py. The number of this process is the time of day: no two processes that
    # are alive at the same moment share it.
    _me = "%04d" % os.getpid()
    S_IN, S_SEEN, S_OTHER, S_NOTPY = "2001-02-03T%sZ" % _me, "20010203T%sZ" % _me, "20020304T%sZ" % _me, "20030405T%sZ" % _me
    def _argv(p):
        try: return [x for x in open("/proc/%d/cmdline" % p.pid, "rb").read().split(b"\0") if x]
        except OSError: return []
    procs = [subprocess.Popen([sys.executable, standin, "--hl7-dir", "inbox/claimocity", "--stamp", S_IN, "--live"]),      # the way the runbook starts it, in the stamp form the routines write
             subprocess.Popen([sys.executable, "-u", standin, "--hl7-dir", "inbox/claimocity"]),                           # no --stamp (and an interpreter switch in front)
             subprocess.Popen([sys.executable, other, "claimocity_ingest.py", "--stamp", S_OTHER])]                        # only NAMES the helper in its arguments (a tail, a grep, a commit message)
    atexit.register(lambda: [p.kill() for p in procs if p.poll() is None])
    _nosh = ""
    try: procs.append(subprocess.Popen(["sh", notpy, "--stamp", S_NOTPY], stdin=subprocess.PIPE))                        # the helper's name as its script, but NO Python process (a shell, a pager, an editor that has the file open)
    except OSError as e: _nosh = "sh could not be started (%s)" % type(e).__name__
    try:
        for _try in range(100):
            if all(len(_argv(p)) > 2 for p in procs): break      # a process that has just been started shows an EMPTY command line for a moment: wait for ALL of them - the ones that must NOT be taken for an ingest included - and then look ONCE (the old loop stopped as soon as the two that must be seen were seen: a scan that takes any Python process naming the helper for an ingest passed in 10 of 40 runs)
            time.sleep(0.1)
        _shown = [len(_argv(p)) for p in procs]; seen = REAL_SCAN()
        check("7e CHANGED (one look, after ALL the stand-ins show their command line; this run's own stamps; a fourth stand-in that is no Python process): the real look at the process list (/proc, no outside command) sees a running claimocity_ingest.py and reads its --stamp the way the ingest does (digits, T and Z only); one started without --stamp is seen with no stamp; a process that only names the helper in its arguments is not taken for an ingest, nor is one that is no Python process (a shell that runs a file of the helper's name)",
              S_SEEN in seen and "" in seen and S_OTHER not in seen and S_NOTPY not in seen and not _nosh and len(procs) == 4 and all(x > 2 for x in _shown), (seen, _nosh, _shown))
    finally:
        for p in procs:
            p.kill(); p.wait()
            if p.stdin: p.stdin.close()
    after = REAL_SCAN()
    check("7f CHANGED (this run's own stand-ins only: several copies of the self-test may run on one machine at once): once the processes have ended they are no longer seen", S_SEEN not in after and S_OTHER not in after and S_NOTPY not in after, after)

# ---- 8. `mirror.py feed-registers` scrubs what it carried before it returns --------------------------------------------------------------
# (a run that commits by hand has no other gate: `sync` scrubs at its commit, this subcommand commits nothing)
ws, reg = setup("gate_standin"); wr = os.path.join(ws, "registers"); marker = os.path.join(TMP, "gate_standin", "how_the_gate_was_called.json")
def standin_gate(code):
    return put(os.path.join(TMP, "gate_standin"), "standin_gate_%d.py" % code,
               "import sys, os, json\njson.dump({'argv': sys.argv[1:], 'cwd': os.getcwd(), 'seen': sorted(os.listdir(os.path.join('practices', 'ehpa', 'registers')))}, open(%r, 'w'))\n"
               "print('stand-in gate: looked at the folder')\nsys.stderr.write('stand-in gate: its own error text\\n')\nsys.exit(%d)\n" % (marker, code))
put(wr, "feed_import_20261125T0640Z.json", imp(1, "workspace"))
mirror.GATE = standin_gate(0)
code, out = cli("feed-registers")
called = json.load(open(marker)) if os.path.exists(marker) else {}
check("8a `mirror.py feed-registers` carries the registers and THEN runs the privacy gate over the registers folder, the way `sync` runs it over the whole tree: `<gate> tree practices/ehpa/registers` from the repository root, after the copy, its output printed behind the step's line",
      called.get("argv") == ["tree", "practices/ehpa/registers"] and os.path.realpath(called.get("cwd", "")) == os.path.realpath(mirror.ROOT) and "feed_import_20261125T0640Z.json" in called.get("seen", [])
      and code in (None, 0) and "stand-in gate: looked at the folder" in out and out.index("feed registers:") < out.index("stand-in gate: looked at the folder"), (code, called, out))
if os.path.exists(marker): os.remove(marker)
mirror.GATE = standin_gate(3)
code, out = cli("feed-registers")
check("8b when the gate fails, `mirror.py feed-registers` exits non-zero with one clear line - the registers it carried are NOT scrubbed, commit nothing from the folder - and the gate's own error text is printed",
      os.path.exists(marker) and isinstance(code, str) and "phi_gate tree FAILED" in code and "NOT scrubbed" in code and "commit nothing" in code and "stand-in gate: its own error text" in out, (code, out))
# ... and it does not end well while a standing file on main is no longer JSON (11/25/2026, the independent verification of the corrected step).
# Two runs that add their rows to the file register at the same place leave conflict markers in it after a pull with rebase. The step names
# such a file and leaves it for a person - but the subcommand ended 0, so the run's own `&& git add && git commit && git push` went on and
# put the markers on main, where the ingest of every later container stops before it reads a file: the feed is down until a person repairs main.
ws, reg = setup("unreadable"); wr = os.path.join(ws, "registers"); mirror.GATE = standin_gate(0)
if os.path.exists(marker): os.remove(marker)
MARKED = "<" * 7 + " ours\n" + json.dumps(MAIN_REG, indent=1) + "\n" + "=" * 7 + "\n" + json.dumps(WS_REG, indent=1) + "\n" + ">" * 7 + " theirs\n"      # what such a pull leaves in the file - put together here, so that no line of THIS file looks like a conflict
put(reg, "claimocity_ingest.json", MARKED); put(wr, "claimocity_ingest.json", WS_REG); put(wr, "feed_import_20261125T0640Z.json", imp(1, "workspace"))
code, out = cli("feed-registers"); SAID["a standing file on main is not readable"] = code if isinstance(code, str) else ""
check("8g when a standing file on main is no longer JSON (the file register with the conflict markers of a pull with rebase), `mirror.py feed-registers` ends NON-ZERO - so the run's `&& git add && git commit && git push` does not go on - with ONE line 'feed registers: NOT READABLE on main: claimocity_ingest.json (conflict markers) - commit NOTHING from practices/ehpa/registers ...' that ends 'TOP OF THE REPORT'; the file is left exactly as it is, and the gate was still run over what was carried",
      isinstance(code, str) and code.startswith("feed registers: NOT READABLE on main: claimocity_ingest.json (conflict markers) - commit NOTHING from practices/ehpa/registers") and code.rstrip().endswith("TOP OF THE REPORT") and "\n" not in code.strip()
      and open(os.path.join(reg, "claimocity_ingest.json")).read() == MARKED and os.path.exists(marker) and os.path.exists(os.path.join(reg, "feed_import_20261125T0640Z.json"))
      and len(lines(out)) == 1 and "could not be read and left as they are on main: claimocity_ingest.json" in out and out.index("feed registers:") < out.index("stand-in gate: looked at the folder"), (code, out))
put(reg, "claimocity_ingest.json", MAIN_REG)                         # the repair: main's copy is put back
code, out = cli("feed-registers")
check("8h once main's copy is JSON again the same command ends as usual (exit 0) and MERGES this workspace's rows into it - nothing either side knew is lost, and the line no longer asks for the top of the report",
      code in (None, 0) and set(get(reg, "claimocity_ingest.json")["files"]) == {"download__20261121.hl7", "download__20261122.hl7", "download__20261124.hl7"} and "NOT READABLE" not in out and "TOP OF THE REPORT" not in out
      and line(out).startswith(START % 1), (code, out))
ws, reg = setup("unreadable_main_only"); wr = os.path.join(ws, "registers")
put(reg, "claimocity_patient_map.json", "<" * 7 + " ours\n{}\n" + "=" * 7 + "\n{}\n" + ">" * 7 + " theirs\n"); put(reg, "feed_in1_intake.json", ""); put(reg, "feed_dx_needed.json", ["a", "list"])
put(reg, "dx_cache_feed.json", {"I10": "dcode1"}); put(reg, "claimocity_ingest.json", MAIN_REG); put(wr, "feed_import_20261125T0640Z.json", imp(1, "workspace"))
code, out = cli("feed-registers")
check("8i the same for a standing file the WORKSPACE does not hold at all (the step's own line never looks at main's copy then) - conflict markers, an EMPTY file, JSON that is no object: each is named with what is wrong; the standing files that are readable are not named",
      isinstance(code, str) and code.startswith("feed registers: NOT READABLE on main: claimocity_patient_map.json (conflict markers), feed_in1_intake.json (empty), feed_dx_needed.json (no JSON object) - commit NOTHING from practices/ehpa/registers")
      and "dx_cache_feed.json" not in code and "claimocity_ingest.json" not in code and code.rstrip().endswith("TOP OF THE REPORT") and "could not be read" not in out and "TOP OF THE REPORT" not in out and line(out).startswith(START % 1), (code, out))
ws, reg = setup("unreadable_no_file"); wr = os.path.join(ws, "registers")
os.symlink(os.path.join(TMP, "nowhere", "x.json"), os.path.join(reg, "feed_in1_intake.json")); os.makedirs(os.path.join(reg, "feed_dx_needed.json")); open(os.path.join(reg, "dx_cache_feed.json"), "wb").write(b"\xff\xfe{\x80")
code, out = cli("feed-registers")
check("8i2 and for whatever else stands in a standing file's place on main and cannot be read as JSON - a link that leads nowhere, a folder, bytes that are no text: each is named with the kind of error",
      isinstance(code, str) and code.startswith("feed registers: NOT READABLE on main: dx_cache_feed.json (") and ", feed_in1_intake.json (" in code and ", feed_dx_needed.json (" in code and "commit NOTHING" in code
      and code.rstrip().endswith("TOP OF THE REPORT") and not any(w in code for w in ("(conflict markers)", "(empty)", "(no JSON object)")), (code, out))
ws, reg = setup("gate_real"); wr = os.path.join(ws, "registers"); repo = mirror.ROOT
os.makedirs(os.path.join(repo, "tools", "mirror")); mirror.GATE = shutil.copy(REAL_GATE, os.path.join(repo, "tools", "mirror", "phi_gate.py"))      # the gate's tree mode works on the checkout it sits in
try: _git = subprocess.run(["git", "init", "-q", repo], capture_output=True, text=True).returncode
except OSError as e: _git = "git could not be started (%s)" % type(e).__name__
_had = os.environ.get("PHI_MAP"); os.environ["PHI_MAP"] = put(os.path.join(TMP, "gate_real"), "standin_map.json", {"names": {}})      # an empty stand-in name map: the real one (PHI, Drive only) is never read here
DAY = "2026-01-" + "02"                                              # an invented day, put together here so that the gate leaves THIS file alone
WHY = "DOS after date of " + "death " + DAY + " (deceased cache)"    # what the import writes into a skipped row beside the chart number
put(wr, "feed_import_20261125T0640Z.json", {"created": [], "skipped": [{"pid": "pat9", "why": WHY}], "failed": []})
put(os.path.join(repo, "notes"), "elsewhere.json", {"why": WHY})     # not in the registers folder
code, out = cli("feed-registers")
_txt = open(os.path.join(reg, "feed_import_20261125T0640Z.json")).read() if os.path.exists(os.path.join(reg, "feed_import_20261125T0640Z.json")) else "(not carried)"
check("8c the REAL gate, on a throwaway checkout: a register carried by `mirror.py feed-registers` no longer holds the day behind 'date of death' - main's copy says [DOB], the chart number beside it stays, the workspace copy is not touched",
      _git == 0 and code in (None, 0) and DAY not in _txt and "[DOB]" in _txt and "pat9" in _txt and DAY in open(os.path.join(wr, "feed_import_20261125T0640Z.json")).read() and "scrubbed in place" in out, (_git, code, out, _txt[:300]))
check("8d the subcommand's gate looks at the registers folder only - a file elsewhere in the tree is left to the whole-tree gate `mirror.py sync` runs at its commit", DAY in open(os.path.join(repo, "notes", "elsewhere.json")).read(), out)
def _checkout_state():
    """(is there a commit, is anything staged) in the throwaway checkout, asked of git itself: (False, False) = nothing was committed and nothing was added"""
    try: return (subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "-q", "HEAD"], capture_output=True).returncode == 0, subprocess.run(["git", "-C", repo, "diff", "--cached", "--quiet"], capture_output=True).returncode != 0)
    except OSError as e: return "git could not be started (%s)" % type(e).__name__
check("8c2 the subcommand COMMITTED nothing and STAGED nothing in that checkout - asked of git itself (check 4c only searches the subcommand's source text: a commit written any other way would pass it)", _git == 0 and _checkout_state() == (False, False), (_git, _checkout_state()))
code, out = cli("feed-registers")
_txt2 = open(os.path.join(reg, "feed_import_20261125T0640Z.json")).read() if os.path.exists(os.path.join(reg, "feed_import_20261125T0640Z.json")) else "(not carried)"
check("8e a second `mirror.py feed-registers` carries nothing: the raw workspace copy (the same rows) does not come back over the copy the gate scrubbed",
      code in (None, 0) and _txt2 == _txt and line(out).startswith(START % 0) and "scrubbed in place" not in out, (code, out))
_dxn_safe = {"M51.17": {"first_seen": "20261105T0640Z", "last_seen": "20261124T1241Z", "visits": 2, "emailed": "20261124T2200Z"}}
put(wr, "feed_dx_needed.json", _dxn_safe)
code, out = cli("feed-registers"); code2, out2 = cli("feed-registers")
check("8f a feed_dx_needed.json whose two stamps sit under first_seen / last_seen comes through the REAL gate exactly as it was merged, and the next run finds nothing to do (under the two bare names the gate would write [name] over a stamp that holds a letter)",
      code in (None, 0) and os.path.exists(os.path.join(reg, "feed_dx_needed.json")) and get(reg, "feed_dx_needed.json") == _dxn_safe and line(out).startswith(START % 1) and "feed_dx_needed.json" not in out
      and code2 in (None, 0) and line(out2).startswith(START % 0), (code, out, code2, out2))
put(reg, "claimocity_ingest.json", MARKED); put(wr, "claimocity_ingest.json", WS_REG)
code, out = cli("feed-registers")
check("8j the REAL gate does not stand in for that check: it reads text, not JSON, passes over a file register with conflict markers and leaves it byte for byte - the subcommand still ends non-zero with the NOT READABLE line, behind the gate's own output",
      isinstance(code, str) and code.startswith("feed registers: NOT READABLE on main: claimocity_ingest.json (conflict markers) - commit NOTHING") and open(os.path.join(reg, "claimocity_ingest.json")).read() == MARKED
      and "tree: " in out and "could not be read and left as they are on main: claimocity_ingest.json" in out, (code, out))
check("8k after every `mirror.py feed-registers` of this section - registers carried, nothing new, a standing file merged, a standing file that is not readable - that checkout still holds no commit and nothing staged",
      _git == 0 and _checkout_state() == (False, False), (_git, _checkout_state()))
# ---- 8m. the end-of-run `sync`: a standing file that is not readable never rides into its commit (11/25/2026, the check of the verification) ----
# `feed-registers` ends non-zero on such a file, but a run that did not act on that line still reaches `mirror.py sync`, whose commit takes the whole tree: the
# verification's checker replayed it with the real `sync` - conflict markers in the file register went to main and the feed was down. feed_standing_put_back()
# runs in `sync` before the commit: the copy the checkout last committed comes back in the file's place.
def _g(*a): return subprocess.run(["git", "-C", repo, "-c", "user.name=selftest", "-c", "user.email=selftest@example.invalid"] + list(a), capture_output=True, text=True)
_has = hasattr(mirror, "feed_standing_put_back")
put(reg, "claimocity_ingest.json", MAIN_REG); put(reg, "claimocity_patient_map.json", {"feedA": "pat1"}); _g("add", "-A"); _c1 = _g("commit", "-q", "-m", "a readable state").returncode
put(reg, "claimocity_ingest.json", MARKED)                                           # what a stopped pull leaves in the working copy
_back = mirror.feed_standing_put_back() if _has else None
check("8m the end-of-run `sync` puts the committed copy back in the place of a standing file that is no longer JSON and differs from it - the conflict markers never reach a commit, the readable copy stays, and the file is named with what was wrong",
      _git == 0 and _c1 == 0 and _has and get(reg, "claimocity_ingest.json") == MAIN_REG and _back == ["claimocity_ingest.json (conflict markers) - the committed copy was put back"], (_git, _c1, _has, _back))
_src_sync = src[src.index('if cmd == "sync":'):src.index('if cmd == "postman":')]
check("8m2 `mirror.py sync` runs that step after the feed registers were carried and BEFORE its commit, and prints one line that ends TOP OF THE REPORT when a file was put back or stays unreadable",
      "feed_standing_put_back()" in _src_sync and _src_sync.index("sync_feed_registers()") < _src_sync.index("feed_standing_put_back()") < _src_sync.index("commit_and_push(msg)") and "TOP OF THE REPORT" in _src_sync, "order")
put(reg, "claimocity_patient_map.json", MARKED); _g("add", "-A"); _g("commit", "-q", "-m", "main itself holds an unreadable map")
_back2 = mirror.feed_standing_put_back() if _has else None
check("8m3 a standing file that is unreadable in the committed copy itself is left as it is (nothing here can repair main - a person does) and is named as such; nothing else is touched",
      _has and open(os.path.join(reg, "claimocity_patient_map.json")).read() == MARKED and _back2 == ["claimocity_patient_map.json (conflict markers) - the committed copy is not readable either: a person repairs it on main"]
      and get(reg, "claimocity_ingest.json") == MAIN_REG, _back2)
_g("rm", "-q", "--cached", "practices/ehpa/registers/claimocity_patient_map.json"); _g("commit", "-q", "-m", "the map is not committed"); put(reg, "claimocity_patient_map.json", {"feedA": "pat1"})
os.remove(os.path.join(reg, "feed_dx_needed.json")) if os.path.lexists(os.path.join(reg, "feed_dx_needed.json")) else None
open(os.path.join(reg, "feed_dx_needed.json"), "w").write("")                       # the list of 8f is in the commit above: emptied here, the committed copy must come back
_back3 = mirror.feed_standing_put_back() if _has else None
check("8m4 an EMPTY standing file is put back the same way, and a readable file that is not committed (the map here) is left alone",
      _has and get(reg, "feed_dx_needed.json") == _dxn_safe and get(reg, "claimocity_patient_map.json") == {"feedA": "pat1"} and _back3 == ["feed_dx_needed.json (empty) - the committed copy was put back"], _back3)
_g("rm", "-q", "--cached", "practices/ehpa/registers/feed_dx_needed.json"); _g("commit", "-q", "-m", "the list is not committed either"); open(os.path.join(reg, "feed_dx_needed.json"), "w").write("{ not json")
_back4 = mirror.feed_standing_put_back() if _has else None
check("8m5 an unreadable standing file the checkout holds NO committed copy of is taken out of the tree (kept beside the workspace's outbox, never deleted) - it cannot be committed either",
      _has and not os.path.lexists(os.path.join(reg, "feed_dx_needed.json")) and _back4 is not None and len(_back4) == 1 and _back4[0].startswith("feed_dx_needed.json (JSONDecodeError) - no committed copy: moved out of the tree to ")
      and os.path.exists(_back4[0].split("moved out of the tree to ")[1]), _back4)
if _had is None: del os.environ["PHI_MAP"]
else: os.environ["PHI_MAP"] = _had
mirror.GATE = os.path.join(TMP, "no_gate_named_here.py")

# ---- 9. no odd input stops the step ------------------------------------------------------------------------------------------------------
B1, B2 = "feed_import_20261125T0640Z.json", "feed_recon_20261125T0640Z.json"
DEEP = "[" * 20000 + "]" * 20000
def _raise(): raise RuntimeError("invented failure of the look at the process list")
def odd_list(ws, wr, reg): put(reg, B1, [1]); put(wr, B1, [1, 2]); put(wr, "claimocity_patient_map.json", ["a", "list"]); put(wr, "feed_dx_needed.json", [1, 2]); put(wr, "feed_in1_intake.json", "7")
def odd_bytes(ws, wr, reg): put(reg, B1, imp(1, "main")); open(os.path.join(wr, B1), "wb").write(b"\xff\xfe{\x80"); open(os.path.join(wr, "claimocity_ingest.json"), "wb").write(b"\xff\xfe"); open(os.path.join(ws, "dx_cache_feed.json"), "wb").write(b"\x80\x81")
def odd_main_batch(ws, wr, reg): put(reg, B1, "{ this is not json"); put(wr, B1, imp(1, "workspace")); put(reg, B2, ""); put(wr, B2, {"rows": rows(1, "workspace")})
def odd_main_standing(ws, wr, reg): put(reg, "claimocity_ingest.json", "{ this is not json"); put(wr, "claimocity_ingest.json", WS_REG); put(reg, "dx_cache_feed.json", ""); put(ws, "dx_cache_feed.json", {"I10": "dcode1"})
def odd_dirs(ws, wr, reg): os.makedirs(os.path.join(wr, B1)); os.makedirs(os.path.join(wr, "claimocity_patient_map.json")); os.makedirs(os.path.join(ws, "dx_cache_feed.json")); os.makedirs(os.path.join(wr, "feed_dx_needed.json"))
def odd_links(ws, wr, reg): os.symlink(os.path.join(TMP, "nowhere", "x.json"), os.path.join(wr, B1)); os.symlink(os.path.join(TMP, "nowhere", "y.json"), os.path.join(ws, "dx_cache_feed.json")); os.symlink(os.path.join(TMP, "nowhere", "z.json"), os.path.join(wr, "feed_in1_intake.json"))
def odd_empty(ws, wr, reg): put(wr, B1, ""); put(wr, "feed_in1_intake.json", ""); put(ws, "dx_cache_feed.json", ""); put(wr, "claimocity_ingest.json", "")
def odd_deep_ws(ws, wr, reg): put(reg, B1, imp(1, "main")); put(wr, B1, DEEP); put(wr, B2, DEEP); put(wr, "claimocity_patient_map.json", DEEP)
def odd_deep_main(ws, wr, reg): put(reg, B1, DEEP); put(wr, B1, imp(1, "workspace")); put(reg, "claimocity_patient_map.json", DEEP); put(wr, "claimocity_patient_map.json", {"feedA": "pat1"})
def odd_intake(ws, wr, reg):
    put(reg, "feed_in1_intake.json", {"1|A": "a text", "2|B": {"outcome": "x"}, "3|C": ["a list"], "4|D": {"stamp": 5}, "5|E": None})
    put(wr, "feed_in1_intake.json", {"1|A": {"outcome": "y", "stamp": ["a list"]}, "2|B": 7, "3|C": None, "4|D": {"stamp": {"a": 1}}, "5|E": {"stamp": "2026-11-24T1241Z"}})
def odd_dxn(ws, wr, reg):
    put(reg, "feed_dx_needed.json", {"A1": dxn(5, None, "three", True), "B2": "a text", "C3": dxn("", "", None, None), "D4": {"visits": 2}, "E5": [1]})
    put(wr, "feed_dx_needed.json", {"A1": dxn(["x"], {"a": 1}, 2.5, 0), "B2": dxn("2026-11-01", "2026-11-02", 1, ""), "C3": ["a list"], "D4": {F: "20261101T0640Z"}, "E5": None, "F6": 7})
def odd_map(ws, wr, reg): put(reg, "claimocity_patient_map.json", {"feedA": {"a": 1}, "feedB": 5, "feedC": None}); put(wr, "claimocity_patient_map.json", {"feedA": ["x"], "feedB": None, "feedC": "pat3", "feedD": {"b": 2}})
def odd_ingest(ws, wr, reg): put(reg, "claimocity_ingest.json", {"files": ["a list"], "runs": {"a": 1}}); put(wr, "claimocity_ingest.json", {"files": {"a.hl7": {"sha256": "1"}}, "runs": "a text"})
def odd_dst_dirs(ws, wr, reg): os.makedirs(os.path.join(reg, B1)); put(wr, B1, imp(1, "workspace")); os.makedirs(os.path.join(reg, "claimocity_ingest.json")); put(wr, "claimocity_ingest.json", WS_REG); os.makedirs(os.path.join(reg, "dx_cache_feed.json")); put(ws, "dx_cache_feed.json", {"I10": "dcode1"})
def odd_scan_fails(ws, wr, reg): put(wr, B1, imp(1, "workspace")); mirror._running_ingest_stamps = _raise
def odd_scan_answers(ws, wr, reg): put(wr, B1, imp(1, "workspace")); mirror._running_ingest_stamps = lambda: [None, 5, "", "20261125T0640Z", ["x"], {"a": 1}]
def odd_scan_none(ws, wr, reg): put(wr, B1, imp(1, "workspace")); mirror._running_ingest_stamps = lambda: None
def odd_scan_number(ws, wr, reg): put(wr, B1, imp(1, "workspace")); mirror._running_ingest_stamps = lambda: 7
def odd_main_is_file(ws, wr, reg): shutil.rmtree(reg); open(reg, "w").write("a file where main's registers folder should be"); put(wr, B1, imp(1, "workspace")); put(wr, "claimocity_ingest.json", WS_REG)
def odd_ws_is_file(ws, wr, reg): shutil.rmtree(wr); open(wr, "w").write("a file where the workspace's registers folder should be")
ODD = [("lists where objects belong", odd_list), ("bytes that are not UTF-8", odd_bytes), ("broken JSON and an empty file on main, batch registers", odd_main_batch), ("broken JSON and an empty file on main, standing files", odd_main_standing),
       ("folders named like registers and like the live cache", odd_dirs), ("dangling links", odd_links), ("empty workspace files", odd_empty), ("JSON nested 20,000 deep in the workspace", odd_deep_ws),
       ("JSON nested 20,000 deep on main", odd_deep_main), ("intake entries that are no entries", odd_intake), ("feed_dx_needed entries that are no entries", odd_dxn), ("a patient map whose charts are not text", odd_map),
       ("a file register whose parts have the wrong kind", odd_ingest), ("folders on main where files belong", odd_dst_dirs), ("the look at the process list fails", odd_scan_fails),
       ("the look at the process list answers with odd things", odd_scan_answers), ("the look at the process list answers nothing", odd_scan_none), ("the look at the process list answers a number", odd_scan_number),
       ("a file where main's registers folder should be", odd_main_is_file), ("a file where the workspace's registers folder should be", odd_ws_is_file)]
broke = []; kept = {}
for i, (label, build) in enumerate(ODD):
    ws, reg = setup("odd%02d" % i); wr = os.path.join(ws, "registers")
    try:
        build(ws, wr, reg); n, out = run()
        if not isinstance(n, int) or len(lines(out)) != 1 or len(out.splitlines()) != 1: broke.append("%s: not ONE 'feed registers:' line and a count (%r, %r)" % (label, n, out[:200]))
        kept[label] = (n, out, ws, wr, reg)
    except (Exception, SystemExit) as e: broke.append("%s: %s %s" % (label, type(e).__name__, str(e)[:120]))
    finally: mirror._running_ingest_stamps = NO_INGEST
check("9a none of %d kinds of odd input stops the step - each time it returns a count and prints its ONE line (lists for objects, bytes that are not UTF-8, broken JSON and empty files on either side, folders and dangling links in place of files, JSON nested 20,000 deep, entries of the wrong kind in every merged file, a look at the process list that fails or answers nonsense, a file where a folder should be)" % len(ODD), not broke, broke)
n, out, ws, wr, reg = kept.get("broken JSON and an empty file on main, batch registers", (0, "", "", "", ""))
check("9b a batch register main holds broken or empty is replaced by the workspace's readable copy (a copy that cannot be read is never the fuller one), and the line says so",
      bool(reg) and side(reg, B1) == "workspace" and side(reg, B2) == "workspace" and n == 2 and "unreadable -> 1 rows" in out, (n, out))
n, out, ws, wr, reg = kept.get("broken JSON and an empty file on main, standing files", (0, "", "", "", ""))
check("9c a standing file main holds BROKEN is never written over (what main knows may still be in it): it is named for the top of the report and left for a person - one main holds EMPTY knows nothing and simply takes what the workspace knows",
      bool(reg) and open(os.path.join(reg, "claimocity_ingest.json")).read() == "{ this is not json" and get(reg, "dx_cache_feed.json") == {"I10": "dcode1"} and n == 1
      and "claimocity_ingest.json" in out and "dx_cache_feed.json" not in out and "could not be read" in out and out.rstrip().endswith("TOP OF THE REPORT"), (n, out))
n, out, ws, wr, reg = kept.get("JSON nested 20,000 deep in the workspace", (0, "", "", "", ""))
check("9d a workspace file that cannot be read never costs main anything: a register main holds readable stays and is passed over without a word (nothing is lost), a register main does not have and the patient map are not written and are named for the top of the report",
      bool(reg) and side(reg, B1) == "main" and not os.path.exists(os.path.join(reg, B2)) and not os.path.exists(os.path.join(reg, "claimocity_patient_map.json")) and n == 0
      and B1 not in out and B2 in out and "claimocity_patient_map.json" in out and out.rstrip().endswith("TOP OF THE REPORT"), (n, out))
n, out, ws, wr, reg = kept.get("the look at the process list fails", (0, "", "", "", "")); SAID["the look for a running ingest failed"] = out
check("9e when the look at the process list itself fails, the registers are carried as usual and the line says the check could not be made, for the top of the report",
      bool(reg) and os.path.exists(os.path.join(reg, B1)) and n == 1 and "running ingest" in out and out.rstrip().endswith("TOP OF THE REPORT"), (n, out))
n, out, ws, wr, reg = kept.get("a file where main's registers folder should be", (0, "", "", "", "")); SAID["the step stopped early"] = out
check("9f when main's registers folder cannot be used at all, nothing is carried, nothing is deleted and the line says why, for the top of the report",
      bool(reg) and os.path.isfile(reg) and n == 0 and line(out).startswith(START % 0) and out.rstrip().endswith("TOP OF THE REPORT") and os.path.exists(os.path.join(wr, B1)), (n, out))

# ---- 10. the privacy gate leaves the two files of this step alone -------------------------------------------------------------------------
sys.path.insert(0, os.path.join(ROOT, "tools", "mirror")); import phi_gate as _pg
for rel in ("tools/mirror/mirror.py", "tools/selftest/test_mirror_feed_registers.py"):
    _t = open(os.path.join(ROOT, rel)).read(); _r = _pg.redact(_t, {}, code=True)
    check("10 the privacy gate's tree rules (what `mirror.py sync` runs over every changed file before a commit) leave %s exactly as it is - every invented value in it that looks like a date, a name part or an identifier is put together at run time" % rel,
          _r == _t, [(a, b) for a, b in zip(_t.splitlines(), _r.splitlines()) if a != b][:2])

# ---- 11. the texts a run follows say what to do with the line -----------------------------------------------------------------------------
# (11/25/2026, the independent verification.) The step ends its line 'TOP OF THE REPORT' when a person has to see it. Until then every rule about
# those words in the runbook and the prompts was for a line that STARTS with them, and no text spoke of this line beyond its start: registers
# held back for a running ingest, or a feed patient whose visits this workspace enters on another chart than main names, could be printed
# and never reach William. The runbook's step (e) now says what a run does with each wording - and every wording it quotes is held here to a
# line this self-test saw the step print (SAID), so that a reworded line cannot leave the runbook quoting words no run will ever read.
_stepfile = os.path.join(ROOT, "nightly", "claimocity_feed_step.md")
if not os.path.exists(_stepfile):
    print("ok   11 (not run here: this tree holds no nightly/claimocity_feed_step.md - a copy of the two tools alone)")
else:
    _e = next((l for l in open(_stepfile, encoding="utf-8").read().split("\n") if l.startswith("(e) ")), "")
    _at = _e.find("its line starts 'feed registers: N file(s) carried'"); _rule = _e.find("WHEN THAT LINE ENDS 'TOP OF THE REPORT', copy the WHOLE line to the top of the report word for word")
    check("11a the runbook's step (e) says what a run does with a 'feed registers:' line that ENDS 'TOP OF THE REPORT' - the WHOLE line goes to the top of the report word for word, from `feed-registers` and from the end-of-run `sync` alike - right behind the sentence that quotes the line's start",
          0 <= _at < _rule < _at + 80 and "from `feed-registers` and from the end-of-run `sync` alike" in _e[_rule:_rule + 200], (_at, _rule))
    # (which case, the words of the printed line the runbook quotes, what the runbook tells the run to do about it)
    WORDS = [("an ingest is still running", ["an ingest is still running (stamp ", "register(s) are not carried this time"], "when the ingest has ended run the same command again, BEFORE the state bundle is packed and before the run ends"),
             ("an ingest is still running, its stamp not readable", ["stamp cannot be read from its command line"], "the same when"),
             ("the patient map differs", ["patient map: ", "feed patient(s) differ - main's chart kept: "], "for William, with both chart numbers"),
             ("the diagnosis cache differs", ["diagnosis cache: ", "code(s) differ - main's id kept: "], "for William, with the code and both ids"),
             ("a file could not be read", ["could not be read and left as they are on main: "], "that register did not travel"),
             ("the look for a running ingest failed", ["the look for a running ingest failed"], "goes to the top of the report as it stands"),
             ("the step stopped early", ["the step stopped early"], "goes to the top of the report as it stands"),
             ("a standing file on main is not readable", ["feed registers: NOT READABLE on main: ", " - commit NOTHING from practices/ehpa/registers"], "ENDED NON-ZERO")]
    _lost = []; _said = _e[max(_rule, 0):]
    for _kind, _frags, _todo in WORDS:
        _lost += ["%s - the runbook does not quote %r" % (_kind, f) for f in _frags if f not in _said] + ["%s - the step did not print %r" % (_kind, f) for f in _frags if f not in SAID.get(_kind, "")]
        if _todo not in _said: _lost.append("%s - the runbook does not say %r" % (_kind, _todo))
        if not SAID.get(_kind, "").rstrip().endswith("TOP OF THE REPORT"): _lost.append("%s - the printed line does not end TOP OF THE REPORT" % _kind)
    check("11b every wording that makes the line a matter for the top of the report - a running ingest (its stamp readable or not), a patient-map difference, a diagnosis-cache difference, a file that could not be read, a failed look at the process list, the step stopping early, a standing file on main that is not readable - is quoted in step (e) the way the step really prints it (each quote is found in a line printed earlier in this self-test), together with what the run does about it",
          _rule >= 0 and not _lost, _lost)
    _repair = ("the end-of-run `sync` no longer carries such a file to main", "First `git status --long`", "then `git checkout origin/main -- practices/ehpa/registers/<file>`", "then the same command again",
               "When the status said 'rebase in progress' (the pull stopped half way), end the rebase afterwards with `git rebase --continue`", "put ` -- practices/ehpa/registers` behind the commit's message in that command",
               "a `git stash pop` of what the pull left 'safe in the stash' brings the markers back", "a pull that prints CONFLICT")
    check("11c step (e) says how the NOT READABLE line is acted on: at once and before anything else is committed (the end-of-run `sync` no longer carries such a file to main - 8m - but a commit by hand still would) - main's own copy back and the same command again; a pull that stopped half way is ended afterwards; with no rebase in progress the commit is limited to the registers folder, so that nothing the autostash staged rides along; the stash is left alone - and its rule for a rejected push says that a pull which prints CONFLICT calls for the command at once",
          all(x in _said for x in _repair) and [_said.find(x) for x in _repair[1:6]] == sorted(_said.find(x) for x in _repair[1:6]), [x for x in _repair if x not in _said])
    _miss = []
    for _f in ("feed_daily.txt", "columns.txt", "billing_button.txt"):
        _p = os.path.join(ROOT, "nightly", "live", _f); _t = open(_p, encoding="utf-8").read() if os.path.exists(_p) else ""
        _i = _t.find("'feed registers:' line that ends 'TOP OF THE REPORT'"); _j = _t.find("goes to the top of the report word for word - runbook step (e)", max(_i, 0))
        if not 0 <= _i < _j < _i + 240: _miss.append(_f)
    check("11d each of the three prompts that run the feed (the daily feed task, the columns run, the Billing Button) says in one clause that a 'feed registers:' line that ends 'TOP OF THE REPORT' goes to the top of the report word for word, and names runbook step (e)", not _miss, _miss)

# ---- 12. the identity register and the place-of-service-61 monitor's register (11/25/2026) --------------------------------------------------
# William 11/25/2026: a feed patient with a wrong birth date goes to the chart he already has (scripts/helpers/feed_identity.py); which chart
# each new feed patient went to, and by which rule, is written to feed_identity_<stamp>.json - chart ids, rule numbers and fixed words only.
# The same day: rehab visits go out at place of service 61 and pos61_monitor.py follows their payment; its register is one run's finding
# (the digest's lines and the monitor's memory), so the register of the LATER run stays, whole.
mirror._running_ingest_stamps = NO_INGEST
ws, reg = setup("identity"); wr = os.path.join(ws, "registers")
IDENT = ["feed_identity_20261126T1240Z.json", "feed_identity_20261126T1840ZR.json"]
NOT_IDENT = ["feed_identity.json", "feed_identity_20261126T1240Z_decisions.json", "feed_identity_2026" "1126.json", "feed_identities_20261126T1240Z.json"]      # the third: a stamp without a time (put together here - the privacy gate reads a word and eight digits as a name and a birth date)
for b in IDENT + NOT_IDENT: put(wr, b, {"stamp": "invented", "patients": rows(2, "workspace")})
n, out = run()
check("12a the feed's identity register (which chart each new feed patient went to and by which rule - chart ids and rule numbers only) travels to main like every other batch register, a retry stamp included; a name that only looks like one does not",
      all(os.path.exists(os.path.join(reg, b)) for b in IDENT) and not any(os.path.exists(os.path.join(reg, b)) for b in NOT_IDENT) and n == len(IDENT), (n, out, sorted(os.listdir(reg))))
put(reg, IDENT[0], {"stamp": "invented", "patients": rows(1, "main")}); put(reg, IDENT[1], {"stamp": "invented", "patients": rows(3, "main")}); n, out = run()
check("12b ... and by the same rule as the others: a FULLER workspace copy (its rows are its patients) replaces main's shorter one, a shorter one never replaces main's fuller one",
      side(reg, IDENT[0]) == "workspace" and side(reg, IDENT[1]) == "main" and n == 1 and "1 fuller workspace copy replaced main's shorter one: %s (1 -> 2 rows)" % IDENT[0] in line(out), (n, out))
UNR = "feed_unreadable_20261126T1240Z.json"      # the parse step's register of feed messages it could not read (11/25/2026: one broken message no longer stops the feed)
ws, reg = setup("parse_unreadable"); wr = os.path.join(ws, "registers"); put(wr, UNR, {"stamp": "invented", "messages": rows(2, "workspace")}); put(wr, "feed_unreadable.json", {"stamp": "invented", "messages": rows(1, "workspace")}); n, out = run()
check("12b2 the register of the feed messages the parse step could not read (file date, message number and fixed words only) travels to main like every other batch register; a name without a stamp does not",
      os.path.exists(os.path.join(reg, UNR)) and not os.path.exists(os.path.join(reg, "feed_unreadable.json")) and n == 1, (n, out, sorted(os.listdir(reg))))
MONF = "pos61_monitor.json"
def mon(at, tag, k=1): return {"version": "2026-11-25.1", "at": at, "lines": ["REHAB AT 61: %d visit(s) entered" % k], "top": [], "visits": rows(k, tag)}
ws, reg = setup("pos61"); wr = os.path.join(ws, "registers")
put(wr, MONF, mon("2026-11-26T12:40:00Z", "workspace", 2)); n, out = run()
check("12c main gets the place-of-service-61 monitor's register the first time a workspace has it, written the way the monitor writes it (one field a line)",
      os.path.exists(os.path.join(reg, MONF)) and get(reg, MONF) == mon("2026-11-26T12:40:00Z", "workspace", 2) and n == 1
      and open(os.path.join(reg, MONF)).read() == json.dumps(mon("2026-11-26T12:40:00Z", "workspace", 2), indent=1), (n, out))
put(reg, MONF, mon("2026-11-27T12:40:00Z", "main", 5)); n, out = run()
check("12d the register of the LATER run stays, whole: a restored workspace's older register never replaces main's newer one, however the file times stand (it is one run's finding - the digest's lines and the monitor's memory - never a mix of two)",
      get(reg, MONF) == mon("2026-11-27T12:40:00Z", "main", 5) and n == 0, (n, out))
put(wr, MONF, mon("2026-11-28T12:40:00Z", "workspace", 3), age=OLDER); n, out = run()
check("12e ... and the workspace's register of a later run replaces main's, whole - also when it holds FEWER visits (a voided visit leaves the list) and its file is the older one",
      get(reg, MONF) == mon("2026-11-28T12:40:00Z", "workspace", 3) and n == 1, (n, out))
n2, out2 = run()
check("12f a second run changes nothing and counts nothing, and the workspace's copy is not touched", n2 == 0 and get(reg, MONF) == mon("2026-11-28T12:40:00Z", "workspace", 3) and get(wr, MONF) == mon("2026-11-28T12:40:00Z", "workspace", 3), (n2, out2))
put(reg, MONF, mon("2026-11-28T12:40:00Z", "main", 3)); n, out = run()
check("12g the same run's register on both sides: main's stays (the tree gate may have scrubbed it)", side(reg, MONF) == "main" and n == 0, (n, out))
_noat = lambda tag: {k: v for k, v in mon("x", tag).items() if k != "at"}
put(reg, MONF, _noat("main")); put(wr, MONF, _noat("workspace")); n, out = run()
check("12h no time on either side: nothing says which is the later one, and the workspace's - this run's - stays (the intake register's rule)", side(reg, MONF) == "workspace" and n == 1, (n, out))
put(reg, MONF, mon("2026-11-29T12:40:00Z", "main")); put(wr, MONF, "{ half written"); n, out = run()
check("12i a workspace register that cannot be read stops nothing: it is named for the top of the report and main's copy stays as it is",
      get(reg, MONF) == mon("2026-11-29T12:40:00Z", "main") and "could not be read and left as they are on main: %s (" % MONF in line(out) and line(out).endswith("TOP OF THE REPORT"), (n, out))
put(reg, MONF, "<<<<<<< Updated upstream\n{}\n=======\n{}\n>>>>>>> Stashed changes\n")
check("12j main's copy with the conflict markers of a pull is found by the same guard as the other standing files (`mirror.py feed-registers` then ends non-zero and `sync` puts the committed copy back)",
      any(x.startswith(MONF + " (conflict markers)") for x in mirror.feed_standing_unreadable()), mirror.feed_standing_unreadable())

# ---- 13. the helper step never lets an older workspace copy of a feed helper back over the repository's (11/25/2026, the verification) ----------
# What it found: mirror.py refuses a workspace copy of a protected helper that lacks its marker - but the parser had NO marker (the shared helper list
# said 'the parser has not changed since 10/28/2026', while the change of that day made it survive a broken message), and the marker of the shared
# helper list itself ('compared byte for byte with the clone's copy') also stands in the copy from before. A workspace that held those two older copies
# with a fresher file time (what a state bundle or a Drive copy laid over the clone looks like) put them back over the repository's: the parser stopped
# on a broken message again, and nothing made the identity rule's helpers current in a workspace any more. The download step had no marker either.
_real_helpers = os.path.join(ROOT, "scripts", "helpers")
if not os.path.exists(os.path.join(_real_helpers, "claimocity_helpers_current.py")):
    print("ok   13 (not run here: this tree holds no scripts/helpers - a copy of the two tools alone)")
else:
    _hsp = importlib.util.spec_from_file_location("claimocity_helpers_current_m", os.path.join(_real_helpers, "claimocity_helpers_current.py")); HC = importlib.util.module_from_spec(_hsp); _hsp.loader.exec_module(HC)
    def _markers(name): return [m_ for m_ in (mirror.PROTECTED.get(name), getattr(mirror, "PROTECTED_ALSO", {}).get(name)) if m_]
    _bare = [f_ for f_ in HC.FEED_HELPERS + ("claimocity_gcs.py",) if not _markers(f_) or not all(m_ in open(os.path.join(_real_helpers, f_)).read() for m_ in _markers(f_))]
    check("13a every helper the feed's driver makes current, and the download step, is protected by a marker that stands in the repository's copy (the parser and the download step had none)", not _bare, _bare)
    check("13b the parser's marker is the one the shared helper list names for it (without a clone the driver then notices an old parser - it said 'not checked'), and the shared list is protected by a SECOND sentence, one the copy from before does not carry",
          HC.VERSION_LINES.get("feed_parse_dft_1028.py") == mirror.PROTECTED.get("feed_parse_dft_1028.py") and bool(HC.VERSION_LINES.get("feed_parse_dft_1028.py"))
          and len(_markers("claimocity_helpers_current.py")) == 2 and "has not changed since 10/28/2026 and carries none" not in open(os.path.join(_real_helpers, "claimocity_helpers_current.py")).read(),
          (HC.VERSION_LINES.get("feed_parse_dft_1028.py"), _markers("claimocity_helpers_current.py")))
    ws, reg = setup("helpers"); _repo_h = os.path.join(mirror.ROOT, "scripts", "helpers"); os.makedirs(_repo_h)
    _copy_gate = put(os.path.join(TMP, "helpers"), "copy_gate.py", "import sys, shutil\nshutil.copyfile(sys.argv[1], sys.argv[2])\n")      # a stand-in for the privacy gate's file mode: it carries the file as it is
    OLD_ONES = ["feed_parse_dft_1028.py", "claimocity_helpers_current.py", "claimocity_gcs.py", "claimocity_match.py"]      # the last one has always had a marker: the control
    def _older(name):
        """the copy from before: the repository's text without the line that carries its marker - for the shared helper list without its SECOND sentence only, so that the copy still carries the first, as the copy on main from before this change does"""
        gone = [m_ for m_ in ([getattr(mirror, "PROTECTED_ALSO", {}).get(name)] if name == "claimocity_helpers_current.py" else [mirror.PROTECTED.get(name)]) if m_]
        return "".join(l_ for l_ in open(os.path.join(_real_helpers, name)).read().splitlines(True) if not any(m_ in l_ for m_ in gone)) + "# an older copy\n"
    for f_ in OLD_ONES:
        shutil.copyfile(os.path.join(_real_helpers, f_), os.path.join(_repo_h, f_)); _p = put(ws, f_, _older(f_)); _t = time.time() + 600; os.utime(_p, (_t, _t))      # the workspace's copy is the NEWER file
    put(_repo_h, "some_run_helper.py", "# the repository's copy\n"); _p = put(ws, "some_run_helper.py", "# a helper a run improved\n"); os.utime(_p, (time.time() + 600,) * 2)      # not protected: carried as always
    _g0 = mirror.GATE; mirror.GATE = _copy_gate; _buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(_buf): mirror.sync_helpers()
        _herr = ""
    except (Exception, SystemExit) as _e: _herr = "%s: %s" % (type(_e).__name__, _e)
    finally: mirror.GATE = _g0
    _hout = _buf.getvalue(); _same = {f_: open(os.path.join(_repo_h, f_)).read() == open(os.path.join(_real_helpers, f_)).read() for f_ in OLD_ONES}
    check("13c a workspace that holds the OLDER copy of the parser, of the shared helper list and of the download step with a fresher file time: none of them goes back over the repository's copy - each is named STALE, like the helper that always had a marker "
          "(the parser and the shared list went back: the repository's parser stopped on a broken message again, its shared list no longer named the identity rule's helpers)",
          _herr == "" and all(_same.values()) and all("helpers: STALE workspace copy of %s skipped" % f_ in _hout for f_ in OLD_ONES), (_herr, _same, _hout[-700:]))
    check("13d ... a helper that is not protected is still carried from the workspace when its file is the newer one, and the step's last line counts it",
          open(os.path.join(_repo_h, "some_run_helper.py")).read() == "# a helper a run improved\n" and "helpers: 1 file(s) refreshed into scripts/helpers/" in _hout, _hout[-300:])
    ws, reg = setup("helpers_current"); _repo_h = os.path.join(mirror.ROOT, "scripts", "helpers"); os.makedirs(_repo_h)
    for f_ in OLD_ONES[:3]:
        shutil.copyfile(os.path.join(_real_helpers, f_), os.path.join(_repo_h, f_)); _p = put(ws, f_, open(os.path.join(_real_helpers, f_)).read() + "# a line a run added\n"); os.utime(_p, (time.time() + 600,) * 2)
    mirror.GATE = _copy_gate; _buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(_buf): mirror.sync_helpers()
        _herr = ""
    except (Exception, SystemExit) as _e: _herr = "%s: %s" % (type(_e).__name__, _e)
    finally: mirror.GATE = _g0
    check("13e a workspace copy that carries every marker (this version, with a line a run added) is carried as before - the markers keep an older copy out, never a current one",
          _herr == "" and all(open(os.path.join(_repo_h, f_)).read().endswith("# a line a run added\n") for f_ in OLD_ONES[:3]) and "STALE" not in _buf.getvalue(), (_herr, _buf.getvalue()[-300:]))

# ---- 14. William's standing word 'same person' is a standing file too: a broken copy never rides into a commit (11/25/2026, the verification) --------
# feed_same_person.json is written by hand, on William's word, in the clone. A hand edit that went wrong (half written, the conflict markers of a
# pull) was committed by `sync` like any other change: the guard looked at the six merged standing files only. The ingest of every later run then
# found the file unreadable (it empties the workspace's copy and says so) - until a person repaired main.
ws, reg = setup("yes_file"); put(reg, "feed_same_person.json", '{"pat9": {"feed_ids": ["x"], "approved_by": "invented"},'); put(reg, "claimocity_patient_map.json", {"feedA": "pat1"})
check("14a a half-written feed_same_person.json in the clone is named by the same guard as the other standing files - `mirror.py feed-registers` then ends non-zero and `sync` puts the committed copy back (it was not looked at)",
      mirror.feed_standing_unreadable() == ["feed_same_person.json (JSONDecodeError)"], mirror.feed_standing_unreadable())
put(reg, "feed_same_person.json", "<" * 7 + " ours\n{}\n" + "=" * 7 + "\n{}\n" + ">" * 7 + " theirs\n"); _u1 = mirror.feed_standing_unreadable(); put(reg, "feed_same_person.json", ["pat9"]); _u2 = mirror.feed_standing_unreadable()
put(reg, "feed_same_person.json", {"pat9": {"feed_ids": ["x"], "approved_by": "invented"}}); _u3 = mirror.feed_standing_unreadable(); put(os.path.join(ws, "registers"), "feed_same_person.json", {"pat7": {"feed_ids": ["y"], "approved_by": "from a restored workspace"}}); n, out = run()
check("14b ... with conflict markers and as a JSON list too; a readable one is not named - and the step still never takes that file from a workspace (its home is main: the ingest copies main's file into the workspace)",
      _u1 == ["feed_same_person.json (conflict markers)"] and _u2 == ["feed_same_person.json (no JSON object)"] and _u3 == [] and get(reg, "feed_same_person.json") == {"pat9": {"feed_ids": ["x"], "approved_by": "invented"}} and n == 0, (_u1, _u2, _u3, n, out))
# ---- 15. the charts William called duplicates (feed_duplicate_charts.json) have their home on main too (11/25/2026, the integration) ---------------
# claimocity_match.py reads the workspace's copy, which the ingest replaces with main's at every start. Like feed_same_person.json the file is written
# by hand in the clone, on his word: the step never takes it from a workspace, and a broken copy in the clone is named before any commit.
ws, reg = setup("dup_file"); put(reg, "feed_duplicate_charts.json", {"pat9": {"proper": "pat1", "approved_by": "invented"}}); put(reg, "claimocity_patient_map.json", {"feedA": "pat1"})
put(os.path.join(ws, "registers"), "feed_duplicate_charts.json", {"pat7": {"proper": "pat2", "approved_by": "from a restored workspace"}}); n, out = run(); _d0 = mirror.feed_standing_unreadable()
check("15a feed_duplicate_charts.json is never taken from a workspace (its home is main: the ingest copies main's file into the workspace), and a readable one is not named by the guard",
      get(reg, "feed_duplicate_charts.json") == {"pat9": {"proper": "pat1", "approved_by": "invented"}} and n == 0 and _d0 == [], (n, out, _d0))
put(reg, "feed_duplicate_charts.json", '{"pat9": {"proper": "pat1",'); _d1 = mirror.feed_standing_unreadable(); put(reg, "feed_duplicate_charts.json", ["pat9"]); _d2 = mirror.feed_standing_unreadable()
check("15b ... and a half-written one, or one that is no JSON object, is named by the same guard as the other standing files - it never rides into a commit",
      _d1 == ["feed_duplicate_charts.json (JSONDecodeError)"] and _d2 == ["feed_duplicate_charts.json (no JSON object)"], (_d1, _d2))
check("15c the repository holds the file at its home, as an object (empty until William names a duplicate) - so a workspace's copy can never become main's by a copy that only fills what is missing",
      os.path.isfile(os.path.join(ROOT, "practices", "ehpa", "registers", "feed_duplicate_charts.json")) and isinstance(json.load(open(os.path.join(ROOT, "practices", "ehpa", "registers", "feed_duplicate_charts.json"))), dict)
      and isinstance(json.load(open(os.path.join(ROOT, "practices", "ehpa", "registers", "feed_same_person.json"))), dict))

print("\n%d failure(s)" % len(FAILS) + (" - all guarantees hold" if not FAILS else ": " + "; ".join(FAILS)))
sys.exit(1 if FAILS else 0)
