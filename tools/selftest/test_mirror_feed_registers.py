#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the mirror's feed-register step, 11/25/2026 - widened the same day after the independent review)
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
#       read from the workspace ROOT, where the feed helpers keep it, and a known code is never replaced by "not in AdvancedMD"; the
#       insurance-intake register feed_in1_intake.json and - when a run wrote it - feed_dx_needed.json are merged entry by entry;
#     - `mirror.py feed-registers` (for a run that commits by hand) runs the privacy gate over the registers folder before it returns and
#       exits non-zero when the gate fails;
#     - files whose home is main (the owner's approved file, William's quality exceptions) and files that are not feed registers are
#       never copied from the workspace; nothing is ever deleted; a broken JSON file stops nothing and is said; no odd input raises;
#     - with no workspace registers folder the step says so and does nothing.
# How the gate is proven, both ways offline: (1) a stand-in gate script that writes down how it was called (and one that fails);
#   (2) the real phi_gate.py, copied into the throwaway tree (its tree mode works on the checkout it sits in) with an empty stand-in name
#   map, on an empty `git init` of that folder: an invented date behind the words the import writes for a visit after a recorded death
#   must come out as a placeholder. The one look at this machine's real process list starts three harmless stand-in processes (two
#   named like the ingest, one that only names it in an argument) and ends them; every other check replaces that look.
# Why: on 11/10, 11/21 and 11/24/2026 the morning run entered 60 / 84 / 26 feed visits in AdvancedMD and committed no feed register
#   (the runbook's step (e) was prose a busy run skipped). The next fresh container took main's older file register, saw the same feed
#   file as new and read it again; the visit-level records of two of those batches exist nowhere. The review of the first version of the
#   step found that none of its 16 checks would have caught what was still wrong (the diagnosis cache looked for in the wrong folder, no
#   gate in `feed-registers`, the sweep's and the intake's registers left out, a short copy on main kept for good, a days-old patient map
#   undoing a correction made on main).
# Run: python3 tools/selftest/test_mirror_feed_registers.py   (exit 1 on any failure)
import os, sys, json, time, shutil, tempfile, importlib.util, io, contextlib, atexit, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("mirror_under_test", os.path.join(ROOT, "tools", "mirror", "mirror.py"))
mirror = importlib.util.module_from_spec(spec); spec.loader.exec_module(mirror)
FAILS = []
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
      get(reg, "feed_order_approved.json")["from"] == "main" and not os.path.exists(os.path.join(reg, "quality_exceptions.json"))
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
n, out = run()
check("3a CHANGED (main's chart stays; before, the workspace answered and a days-old restored map undid a correction made on main): the patient map is merged - a patient only the workspace knows is added, and where the two disagree MAIN's chart is kept and the line names the feed patient with both charts so a person can decide",
      get(reg, "claimocity_patient_map.json") == {"feedA": "pat1", "feedB": "pat2", "feedC": "pat3"} and "patient map: 1 feed patient(s) differ - main's chart kept: feedB" in out and "pat22" in out
      and len(lines(out)) == 1 and line(out).startswith(START % 2), (get(reg, "claimocity_patient_map.json"), out))
check("3b CHANGED (the cache is read from the workspace ROOT, where the feed helpers keep it; before, from registers/, where only a snapshot of main lies): the diagnosis cache is merged - new codes are added, a code that was missing and now has its AdvancedMD id takes it, and a KNOWN code is never replaced by 'not in AdvancedMD'",
      {k: v for k, v in get(reg, "dx_cache_feed.json").items() if k != "Z9999"} == {"I10": "dcode1", "E119": "dcode2", "S82843D": "dcode9", "M5117": "dcode7"}, get(reg, "dx_cache_feed.json"))
check("3b2 the registers/ snapshot is NOT taken when the root file exists (a code only the snapshot holds does not reach main)", "Z9999" not in get(reg, "dx_cache_feed.json"), get(reg, "dx_cache_feed.json"))
check("3b3 both merged files are written the way the feed helpers write them (one entry a line, keys in order), so a diff on main shows only what changed",
      open(os.path.join(reg, "dx_cache_feed.json")).read() == json.dumps({"I10": "dcode1", "E119": "dcode2", "S82843D": "dcode9", "M5117": "dcode7"}, indent=0, sort_keys=True)
      and open(os.path.join(reg, "claimocity_patient_map.json")).read() == json.dumps({"feedA": "pat1", "feedB": "pat2", "feedC": "pat3"}, indent=0, sort_keys=True))
put(wr, "claimocity_patient_map.json", "{ this is not json"); put(wr, "feed_import_20261125T0640Z.json", {"from": "workspace"})
n, out = run()
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
check("3f when many feed patients differ the line counts them all, names the first 20 and says how many more there are - and main's map is not changed",
      "patient map: 25 feed patient(s) differ - main's chart kept: feed00" in out and "feed19" in out and "feed20" not in out and "+5 more" in out and n == 0
      and get(reg, "claimocity_patient_map.json") == {"feed%02d" % i: "pat%d" % i for i in range(25)}, (n, out))

# ---- 4. nothing to do --------------------------------------------------------------------------------------------------------------------
ws, reg = setup("none"); shutil.rmtree(os.path.join(ws, "registers"))
n, out = run()
check("4a with no registers folder in the workspace the step says so and does nothing", n == 0 and "feed registers:" in out and os.listdir(reg) == [], out)
src = open(os.path.join(ROOT, "tools", "mirror", "mirror.py")).read()
check("4b `mirror.py sync` runs the step before it commits (after the helpers, before commit_and_push)",
      src.index("sync_feed_registers()", src.index('if cmd == "sync":')) < src.index("commit_and_push(msg)", src.index('if cmd == "sync":')), "order")
_fr = src[src.index('if cmd == "feed-registers":'):] if 'if cmd == "feed-registers":' in src else ""
check("4c CHANGED (the step no longer returns straight away: section 8 proves the gate it runs first): `mirror.py feed-registers` is the step alone, for a run that commits by hand (the daily feed task) - it commits and pushes nothing, and the usage line names it",
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
n, out = run()
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
n, out = run()
check("7d an ingest started without --stamp: its stamp is not known, so nothing is held back - the line says an ingest is still running and that its stamp cannot be read (not that registers were left behind), for the top of the report",
      all(os.path.exists(os.path.join(reg, b)) for b in STILL) and "an ingest is still running (its stamp cannot be read" in out and "not carried this time" not in out
      and out.rstrip().endswith("TOP OF THE REPORT") and line(out).startswith(START % len(STILL)), (n, out))
mirror._running_ingest_stamps = NO_INGEST
if REAL_SCAN is None:
    check("7e the real look at the process list sees a running claimocity_ingest.py and reads its stamp", False, "mirror.py has no _running_ingest_stamps")
elif not os.path.isdir("/proc/%d" % os.getpid()):
    print("ok   7e (not run here: this machine has no /proc, so no running ingest can be seen on it)")
else:
    d = os.path.join(TMP, "processes"); os.makedirs(d)
    standin = put(d, "claimocity_ingest.py", "import time\ntime.sleep(120)\n"); other = put(d, "some_other_helper.py", "import time\ntime.sleep(120)\n")
    procs = [subprocess.Popen([sys.executable, standin, "--hl7-dir", "inbox/claimocity", "--stamp", "2001-02-03T0405Z", "--live"]),       # the way the runbook starts it, in the stamp form the routines write
             subprocess.Popen([sys.executable, "-u", standin, "--hl7-dir", "inbox/claimocity"]),                                          # no --stamp (and an interpreter switch in front)
             subprocess.Popen([sys.executable, other, "claimocity_ingest.py", "--stamp", "20020304T0506Z"])]                              # only NAMES the helper in its arguments (a tail, a grep, a commit message)
    atexit.register(lambda: [p.kill() for p in procs if p.poll() is None])
    try:
        seen = []
        for _try in range(50):
            seen = REAL_SCAN()
            if "20010203T0405Z" in seen and "" in seen: break
            time.sleep(0.1)
        check("7e the real look at the process list (/proc, no outside command) sees a running claimocity_ingest.py and reads its --stamp the way the ingest does (digits, T and Z only); one started without --stamp is seen with no stamp; a process that only names the helper in its arguments is not taken for an ingest",
              "20010203T0405Z" in seen and "" in seen and "20020304T0506Z" not in seen, seen)
    finally:
        for p in procs: p.kill(); p.wait()
    after = REAL_SCAN()
    check("7f once the process has ended it is no longer seen", "20010203T0405Z" not in after and "20020304T0506Z" not in after, after)

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
n, out, ws, wr, reg = kept.get("the look at the process list fails", (0, "", "", "", ""))
check("9e when the look at the process list itself fails, the registers are carried as usual and the line says the check could not be made, for the top of the report",
      bool(reg) and os.path.exists(os.path.join(reg, B1)) and n == 1 and "running ingest" in out and out.rstrip().endswith("TOP OF THE REPORT"), (n, out))
n, out, ws, wr, reg = kept.get("a file where main's registers folder should be", (0, "", "", "", ""))
check("9f when main's registers folder cannot be used at all, nothing is carried, nothing is deleted and the line says why, for the top of the report",
      bool(reg) and os.path.isfile(reg) and n == 0 and line(out).startswith(START % 0) and out.rstrip().endswith("TOP OF THE REPORT") and os.path.exists(os.path.join(wr, B1)), (n, out))

# ---- 10. the privacy gate leaves the two files of this step alone -------------------------------------------------------------------------
sys.path.insert(0, os.path.join(ROOT, "tools", "mirror")); import phi_gate as _pg
for rel in ("tools/mirror/mirror.py", "tools/selftest/test_mirror_feed_registers.py"):
    _t = open(os.path.join(ROOT, rel)).read(); _r = _pg.redact(_t, {}, code=True)
    check("10 the privacy gate's tree rules (what `mirror.py sync` runs over every changed file before a commit) leave %s exactly as it is - every invented value in it that looks like a date, a name part or an identifier is put together at run time" % rel,
          _r == _t, [(a, b) for a, b in zip(_t.splitlines(), _r.splitlines()) if a != b][:2])

print("\n%d failure(s)" % len(FAILS) + (" - all guarantees hold" if not FAILS else ": " + "; ".join(FAILS)))
sys.exit(1 if FAILS else 0)
