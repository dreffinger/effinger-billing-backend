#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the mirror's feed-register step, 11/25/2026)
# Decides: nothing. Loads tools/mirror/mirror.py, points it at two throwaway folders (an invented workspace and an invented repository
#   tree - no git, no network, no AdvancedMD, no patient data) and proves what `mirror.py sync` now does with the Claimocity feed's
#   registers before it commits:
#     - a batch register the workspace has and main does not (feed_import / feed_newcharts / feed_verify / feed_inspector / feed_fixholds /
#       feed_recon / feed_order_sweep of any stamp, retry stamps included) is copied into practices/ehpa/registers/;
#     - a batch register main already has is replaced only by a NEWER workspace copy - a fresh container's older copy never overwrites it;
#     - the file register claimocity_ingest.json is MERGED: every file and every run either side knows stays (the file main did not know
#       is added; a file only main knows is not lost) - this is the register whose loss made three runs read a feed file twice;
#     - the patient map and the diagnosis cache are merged the same way, and a known code is never replaced by "not in AdvancedMD";
#     - files whose home is main (the owner's approved file, William's quality exceptions) and files that are not feed registers are
#       never copied from the workspace; nothing is ever deleted; a broken JSON file stops nothing and is said;
#     - with no workspace registers folder the step says so and does nothing.
# Why: on 11/10, 11/21 and 11/24/2026 the morning run entered 60 / 84 / 26 feed visits in AdvancedMD and committed no feed register
#   (the runbook's step (e) was prose a busy run skipped). The next fresh container took main's older file register, saw the same feed
#   file as new and read it again; the visit-level records of two of those batches exist nowhere.
# Run: python3 tools/selftest/test_mirror_feed_registers.py   (exit 1 on any failure)
import os, sys, json, time, shutil, tempfile, importlib.util, io, contextlib, atexit
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("mirror_under_test", os.path.join(ROOT, "tools", "mirror", "mirror.py"))
mirror = importlib.util.module_from_spec(spec); spec.loader.exec_module(mirror)
FAILS = []
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  -> " + str(extra)[:500]) if extra != "" and not cond else ""))
    if not cond: FAILS.append(name)
TMP = tempfile.mkdtemp(prefix="mirror_feedreg_"); atexit.register(shutil.rmtree, TMP, ignore_errors=True)
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

# ---- 1. batch registers -----------------------------------------------------------------------------------------------------------------
ws, reg = setup("batch"); wr = os.path.join(ws, "registers")
BATCH = ["feed_import_20261124T1241Z.json", "feed_newcharts_20261124T1241Z.json", "feed_verify_20261124T1241Z.json", "feed_inspector_20261124T1241Z.json",
         "feed_fixholds_20261124T1241Z.json", "feed_recon_20261124T1241Z.json", "feed_import_20261113T0157ZR.json", "feed_order_sweep_20261124T184408Z.json"]
for b in BATCH: put(wr, b, {"created": [{"pid": "pat9", "visit": "vst1"}], "from": "workspace"})
put(wr, "feed_order_approved.json", {"approved_by": "invented", "from": "workspace"})          # home is main: never from the workspace
put(wr, "quality_exceptions.json", {"from": "workspace"})                                    # home is main
put(wr, "era_checks_before_20261124.json", {"from": "workspace"})                            # not a feed register: another step mirrors it
put(wr, "feed_import_SELFTEST.json", {"from": "workspace"})                                  # not a batch stamp
put(reg, "feed_order_approved.json", {"approved_by": "the owner", "from": "main"})
n, out = run()
check("1a every batch register main does not have is copied (import, new charts, verify, inspector, fix-holds, recon, a retry stamp, the order sweep)",
      all(os.path.exists(os.path.join(reg, b)) and get(reg, b)["from"] == "workspace" for b in BATCH), [b for b in BATCH if not os.path.exists(os.path.join(reg, b))])
check("1b the step says what it did in ONE line that starts 'feed registers:' and counts the files", n == len(BATCH) and any(l.startswith("feed registers: %d file(s)" % len(BATCH)) for l in out.splitlines()), (n, out))
check("1c files whose home is main are never taken from the workspace (the owner's approved file, the quality exceptions), nor files that are not feed registers",
      get(reg, "feed_order_approved.json")["from"] == "main" and not os.path.exists(os.path.join(reg, "quality_exceptions.json"))
      and not os.path.exists(os.path.join(reg, "era_checks_before_20261124.json")) and not os.path.exists(os.path.join(reg, "feed_import_SELFTEST.json")), sorted(os.listdir(reg)))
n2, out2 = run()
check("1d a second run copies nothing (main's copies are as new as the workspace's) and says 0", n2 == 0 and "feed registers: 0 file(s)" in out2, (n2, out2))
put(reg, "feed_recon_20261122T1240Z.json", {"from": "main"}); put(wr, "feed_recon_20261122T1240Z.json", {"from": "an OLDER workspace copy"}, age=3 * 86400)
put(reg, "feed_import_20261120T1240Z.json", {"from": "main"}, age=3 * 86400); put(wr, "feed_import_20261120T1240Z.json", {"from": "a NEWER workspace copy"})
n3, out3 = run()
check("1e a register main already has is replaced only by a NEWER workspace copy - an older one (a fresh container's restored state) never overwrites main's",
      get(reg, "feed_recon_20261122T1240Z.json")["from"] == "main" and get(reg, "feed_import_20261120T1240Z.json")["from"] == "a NEWER workspace copy" and n3 == 1, (n3, out3))

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
put(reg, "dx_cache_feed.json", {"I10": "dcode1", "E119": "dcode2", "S82843D": None}); put(wr, "dx_cache_feed.json", {"E119": None, "S82843D": "dcode9", "M5117": "dcode7"})
n, out = run()
check("3a the patient map is merged: main's charts stay, this run's new patients are added, and for a patient both know the workspace (this run) answers",
      get(reg, "claimocity_patient_map.json") == {"feedA": "pat1", "feedB": "pat22", "feedC": "pat3"}, get(reg, "claimocity_patient_map.json"))
check("3b the diagnosis cache is merged: new codes are added, a code that was missing and now has its AdvancedMD id takes it, and a KNOWN code is never replaced by 'not in AdvancedMD'",
      get(reg, "dx_cache_feed.json") == {"I10": "dcode1", "E119": "dcode2", "S82843D": "dcode9", "M5117": "dcode7"}, get(reg, "dx_cache_feed.json"))
put(wr, "claimocity_patient_map.json", "{ this is not json"); put(wr, "feed_import_20261125T0640Z.json", {"from": "workspace"})
n, out = run()
check("3c a workspace file that cannot be read stops nothing: it is named, main's copy stays as it is, and the other registers are still copied",
      get(reg, "claimocity_patient_map.json") == {"feedA": "pat1", "feedB": "pat22", "feedC": "pat3"} and os.path.exists(os.path.join(reg, "feed_import_20261125T0640Z.json")) and "claimocity_patient_map.json" in out and "could not be read" in out, out)

# ---- 4. nothing to do --------------------------------------------------------------------------------------------------------------------
ws, reg = setup("none"); shutil.rmtree(os.path.join(ws, "registers"))
n, out = run()
check("4a with no registers folder in the workspace the step says so and does nothing", n == 0 and "feed registers:" in out and os.listdir(reg) == [], out)
src = open(os.path.join(ROOT, "tools", "mirror", "mirror.py")).read()
check("4b `mirror.py sync` runs the step before it commits (after the helpers, before commit_and_push)",
      src.index("sync_feed_registers()", src.index('if cmd == "sync":')) < src.index("commit_and_push(msg)", src.index('if cmd == "sync":')), "order")
check("4c `mirror.py feed-registers` runs the step alone, for a run that commits by hand (the daily feed task) - and the usage line names it",
      'if cmd == "feed-registers":' in src and "sync_feed_registers(); return" in src and "postman|feed-registers]" in src, "subcommand")

print("\n%d failure(s)" % len(FAILS) + (" - all guarantees hold" if not FAILS else ": " + "; ".join(FAILS)))
sys.exit(1 if FAILS else 0)
