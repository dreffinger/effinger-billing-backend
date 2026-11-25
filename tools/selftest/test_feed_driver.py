#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the Claimocity feed DRIVER's own part of the identity rule - William 11/25/2026)
# Decides: nothing. Runs scripts/helpers/claimocity_ingest.py INSIDE this process over a throwaway workspace and a throwaway copy of the
#   repository's helpers (its two folder lines are pointed there; every program it would start - parse, dx, match, resolve, new charts,
#   import, report, recon - is answered by a stand-in that starts nothing). No network, no AdvancedMD, no patient data: every name, birth
#   date and id below is invented and put together at run time (the privacy gate rewrites a file that holds one as a literal - the last
#   check proves this file is left alone).
# What it proves (William 11/25/2026: "correct every one that comes to the correct date of birth ... figure our how to do this for other
#   charts that have the same mistake"; 11/9/2026: "if a duplicate chart shows up with visits in it just put the visits in the proper chart"):
#   1 THE REPOSITORY'S PATIENT MAP ANSWERS: a feed patient whose chart was corrected on main (re-pointed from a duplicate chart to the
#     proper one) goes to main's chart from the next ingest on - the workspace's restored map no longer wins - and a patient only main
#     knows is added. A map on main that cannot be read changes nothing and is said.
#   2 THE IDENTITY REGISTER: a live ingest writes registers/feed_identity_<stamp>.json - for every feed patient that was looked up, the
#     chart, the rule number and the fixed words of feed_identity.py; never a name, a birth date or a number of a patient. A field that is
#     not one of the fixed words is withheld, not copied. A dry ingest writes none.
#   3 A FILE IS NOT REGISTERED WHILE A PATIENT OF IT HAS NO CHART (a new chart AdvancedMD refused; a patient the rule could not decide):
#     the next start reads the file again - until 11/25/2026 the file was registered as done and the visit was never entered or retried.
#   4 TWO FEED PATIENTS UNDER ONE NAME AND ONE BIRTH DATE: every entry of the match file names the chart of EACH Claimocity id, so a new id
#     beside a known one goes where the identity rule sends it - never to the known chart by the name alone - and two known ids keep
#     their own charts (the import asks by the message's own id; tools/selftest/test_pos_rule.py proves that side).
#   5 The driver prints no letter of a patient's name (its dry line used to show four), and shows a step's last lines whole.
#   7 THE DIGEST SAYS IT (claimocity_report.py, run inside this process too): which chart each looked-up feed patient went to and what is
#     for William (from the identity register), where the feed's birth date and the chart's differ (from the import's rows), and the
#     inpatient-rehab visits at place of service 61 with each new rehab stay (William 11/25/2026) - chart ids only, fixed words only.
#   8 ONE BROKEN MESSAGE NEVER STOPS THE FEED (feed_parse_dft_1028.py, started as its own program): a message without a patient line, or
#     with a line cut short, used to end the parse with an error - no visit of that day was entered. Now every other message goes
#     through, nothing is entered from the broken one, and it is counted in registers/feed_unreadable_<stamp>.json (file date and
#     message number only) and at the top of the digest.
# Usage: python3 tools/selftest/test_feed_driver.py     (exit 1 on any FAIL)
import os, sys, io, re, json, types, shutil, tempfile, atexit, contextlib, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPERS = os.path.join(ROOT, "scripts", "helpers")
sys.dont_write_bytecode = True
OK = [0]; FAILS = []
def check(name, cond, extra=""):
    """cond / extra may be a function: a check that cannot even be worked out (a register that was never written) FAILS - it never ends the self-test early"""
    try: ok = bool(cond() if callable(cond) else cond)
    except Exception as ex: ok = False; extra = "could not be worked out - %s: %s" % (type(ex).__name__, ex)
    try: shown = extra() if callable(extra) else extra
    except Exception as ex: shown = "%s: %s" % (type(ex).__name__, ex)
    print(("ok   " if ok else "FAIL ") + name + (("  -> " + str(shown)[:700]) if shown != "" and not ok else ""))
    if ok: OK[0] += 1
    else: FAILS.append(name)
TMP = tempfile.mkdtemp(prefix="feed_driver_"); atexit.register(shutil.rmtree, TMP, ignore_errors=True)
def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
FI = _load("feed_identity_t", os.path.join(HELPERS, "feed_identity.py"))
HC = _load("claimocity_helpers_current_t", os.path.join(HELPERS, "claimocity_helpers_current.py"))
DRIVER = "claimocity_ingest.py"; DSRC = open(os.path.join(HELPERS, DRIVER)).read()

# ---- invented patients: every name and date is put together here, at run time ---------------------------------------------------------------
def FID(n): return ("%02x" % n) * 12                                    # a Claimocity id: 24 hex characters
def NAME(n): return "ZZ" + "QUILL" + "ABCDEFGH"[n] + ", " + "MIRA" + "ABCDEFGH"[n]      # LAST, FIRST of invented patient n
def DOB(n): return "19" + "%02d" % (40 + n) + "03" + "%02d" % (10 + n)   # a real date of invented patient n
NODOB = "1900" + "0101"                                                   # the placeholder Claimocity sends
def KEY(n, dob=None): return NAME(n).upper().strip() + "|" + (DOB(n) if dob is None else dob)
def secrets(*ns): return [x for n in ns for x in (NAME(n).split(",")[0], NAME(n).split(", ")[1], DOB(n), DOB(n)[4:6] + "/" + DOB(n)[6:] + "/" + DOB(n)[:4])]
def msg(n, f, dob=None, fid=None): return {"pid": fid or FID(n), "name": NAME(n), "dob": DOB(n) if dob is None else dob, "file": f, "FT1": [{"cpt": "99308", "dos": "20261120", "dx": "I10", "units": "1"}]}

def sandbox(label, files, ws_map=None, main_map=None):
    """a throwaway workspace with its inbox and registers, and a throwaway clone whose scripts/helpers holds the repository's real feed helpers
    (so the driver's own make_current finds every helper current) -> (workspace, the clone's scripts/helpers, the clone's registers folder)"""
    w = os.path.join(TMP, label, "ws"); r = os.path.join(TMP, label, "repo", "scripts", "helpers"); mreg = os.path.join(TMP, label, "repo", "practices", "ehpa", "registers")
    for d in (os.path.join(w, "inbox", "claimocity"), os.path.join(w, "registers"), r, mreg): os.makedirs(d)
    for f in HC.FEED_HELPERS:
        if os.path.exists(os.path.join(HELPERS, f)): shutil.copy2(os.path.join(HELPERS, f), os.path.join(r, f)); shutil.copy2(os.path.join(HELPERS, f), os.path.join(w, f))
    for f in files: open(os.path.join(w, "inbox", "claimocity", f), "w").write("MSH|invented %s\n" % f)
    if ws_map is not None: json.dump(ws_map, open(os.path.join(w, "registers", "claimocity_patient_map.json"), "w"))
    if main_map is not None: open(os.path.join(mreg, "claimocity_patient_map.json"), "w").write(main_map if isinstance(main_map, str) else json.dumps(main_map))
    return w, r, mreg
def rd(*p):
    try: return json.load(open(os.path.join(*p)))
    except (OSError, ValueError): return None

def driver_run(w, r, argv, on_step):
    """the driver itself, inside this process: its WS and REPO_HELPERS lines point at the sandbox; -> (what it printed, the steps it started, its error)"""
    src = DSRC.replace('WS = "/home/claude/unbilled"', "WS = %r" % w, 1).replace('REPO_HELPERS = "/home/claude/effinger-billing-backend/scripts/helpers"', "REPO_HELPERS = %r" % r, 1)
    live = [ln for ln in src.split("\n") if ("/home/claude/unbilled" in ln or "/home/claude/effinger-billing-backend" in ln) and not ln.lstrip().startswith("#")]
    if live: raise RuntimeError("the sandbox copy still names a live folder outside a comment - not run: %r" % live[:2])
    calls = []; sub = types.ModuleType("subprocess"); sub.STDOUT = -2; sub.PIPE = -1
    def _run(cmd, **k):
        b = os.path.basename(str(cmd[2] if str(cmd[1]) == "-I" else cmd[1])); calls.append(b); txt = on_step(b, cmd) or "DONE {}"; rc = 0
        if isinstance(txt, tuple): txt, rc = txt
        if hasattr(k.get("stdout"), "write"): k["stdout"].write(txt + "\n")
        return types.SimpleNamespace(returncode=rc, stdout="", stderr="")
    sub.run = _run
    old_sub = sys.modules.get("subprocess"); old_cwd = os.getcwd(); old_argv = sys.argv[:]; old_env = dict(os.environ); out = io.StringIO(); err = ""
    try:
        for k in ("FEED_STAMP", "FEED_HL7_DIR", "FEED_DX_CACHE", "FEED_CHART_PREFIX", "QUALITY_CODE", "MVP_CODE"): os.environ.pop(k, None)
        sys.modules["subprocess"] = sub; sys.argv = [os.path.join(w, DRIVER)] + list(argv)
        with contextlib.redirect_stdout(out):
            try: exec(compile(src, os.path.join(w, DRIVER), "exec"), {"__name__": "__main__", "__file__": os.path.join(w, DRIVER)})
            except SystemExit: pass
            except Exception as e: err = "%s: %s" % (type(e).__name__, e)
    finally:
        if old_sub is None: sys.modules.pop("subprocess", None)      # it was not loaded before: leaving None behind would stop every later import of it
        else: sys.modules["subprocess"] = old_sub
        os.chdir(old_cwd); sys.argv = old_argv; os.environ.clear(); os.environ.update(old_env)
    return out.getvalue(), calls, err

def answer(rule, chart="", status=None, flags=(), cands=(), ev=(), dob="real", will=False, ids=(), why=None):
    """one decided entry of the match file, the way claimocity_resolve.py writes it (plus the workspace-only fields that must never be copied)"""
    e = {"status": status or ("FOUND" if chart else "MISSING" if rule == 9 else "AMBIGUOUS"), "pids": [chart] if chart else [], "feed_ids": list(ids), "decided_for": list(ids),
         "identity_rule": FI.IDENTITY_RULE_VERSION, "rule": rule, "why": why or FI.WHY.get(rule, FI.WHY_DISAGREE), "flags": list(flags), "candidates": list(cands), "evidence": list(ev),
         "feed_dob": dob, "for_william": will, "resolution": "rule %d" % rule, "lookup": [{"pid": c, "name": NAME(7), "dob": DOB(7)} for c in cands], "cut": ""}
    if chart: e["resolved"] = chart
    return e
def steps(w, stamp, parsed, decided, newcharts=None, created=None, tail=None):
    """the stand-in for every program the driver starts: the parse writes these messages, the resolve these answers, the new-chart step makes
    the charts of `newcharts` ({key: chart}) and the import a register with `created` rows"""
    def on_step(b, cmd):
        if b == "feed_parse_dft_1028.py": json.dump(parsed, open(os.path.join(w, str(cmd[-1])), "w"))
        if b == "claimocity_match.py": json.dump({k: dict(v, status="AMBIGUOUS", rule=0, why=FI.WHY_NOT_YET) for k, v in decided.items()}, open(os.path.join(w, "feed_match_%s.json" % stamp), "w"))
        if b == "claimocity_resolve.py": json.dump(decided, open(os.path.join(w, "feed_match_%s.json" % stamp), "w"))
        if b == "claimocity_newcharts.py":
            m = json.load(open(os.path.join(w, "feed_match_%s.json" % stamp)))
            for k, v in m.items():
                if v.get("status") == "MISSING" and not v.get("resolved"):
                    if k in (newcharts or {}): v["resolved"] = newcharts[k]
                    else: v["flags"] = list(v.get("flags") or []) + [FI.FLAG_NO_CHART_MADE]; v["for_william"] = True; v["amd_answer"] = "refused for " + NAME(2)
            json.dump(m, open(os.path.join(w, "feed_match_%s.json" % stamp), "w"))
        if b == "claimocity_import.py":
            json.dump({"created": created or [], "skipped": [], "failed": []}, open(os.path.join(w, "registers", "feed_import_%s.json" % stamp), "w"))
            return tail or "DONE {}"
    return on_step
def pm(w): return rd(w, "registers", "claimocity_patient_map.json") or {}
def ident(w, stamp): return rd(w, "registers", "feed_identity_%s.json" % stamp)
def match(w, stamp): return rd(w, "feed_match_%s.json" % stamp) or {}
def ingest(w): return rd(w, "registers", "claimocity_ingest.json") or {}
ARGS = lambda stamp, live=True: ("--hl7-dir", "inbox/claimocity", "--stamp", stamp, "--skip-verify", "--skip-inspector") + (("--live",) if live else ())

# ---- 1. the repository's patient map answers where the two differ ----------------------------------------------------------------------------
S1 = "20261126T1240Z"
w, r, mreg = sandbox("map", ["20261126a.hl7"], ws_map={FID(1): "pat9001", FID(2): "pat9002"}, main_map={FID(1): "pat9001", FID(2): "pat9902", FID(3): "pat9003", FID(4): "", FID(5): 77})
o, calls, e = driver_run(w, r, ARGS(S1), steps(w, S1, [msg(1, "20261126"), msg(2, "20261126")], {}))
check("1a a feed patient whose chart was corrected on main goes to MAIN's chart: the ingest takes the repository's chart, not the one its restored workspace map still names",
      e == "" and match(w, S1).get(KEY(2), {}).get("resolved") == "pat9902" and match(w, S1).get(KEY(1), {}).get("resolved") == "pat9001", (e, o[-600:], match(w, S1)))
check("1b the workspace's map is corrected for good (the next run and the mirror see one chart), a feed patient only main knows is added, and a value on main that is no chart id is passed over",
      pm(w) == {FID(1): "pat9001", FID(2): "pat9902", FID(3): "pat9003"}, pm(w))
_l = next((l for l in o.splitlines() if l.startswith("PATIENT MAP:")), "")
check("1c ONE line says it - how many feed patients now go to the repository's chart, each with the chart it was and the chart it is, how many were added - and the line shows no letter of a name",
      "1 feed patient(s) now go to the repository's chart" in _l and "%s (was pat9002, now pat9902)" % FID(2) in _l and "1 added from the repository's map" in _l and not any(s in o for s in secrets(1, 2)), (_l, o[-400:]))
check("1d the live run's identity register names the re-pointed feed patient with both charts (the report prints it from there)",
      (ident(w, S1) or {}).get("repointed") == [{"feed_id": FID(2), "was": "pat9002", "now": "pat9902"}], ident(w, S1))
w, r, mreg = sandbox("map2", ["20261126a.hl7"], ws_map={FID(1): "pat9001"}, main_map="<" * 7 + " ours\n{}\n" + "=" * 7 + "\n{}\n" + ">" * 7 + " theirs\n")
o, calls, e = driver_run(w, r, ARGS(S1), steps(w, S1, [msg(1, "20261126")], {}))
check("1e a map on main that cannot be read (the conflict markers of a pull) changes nothing: the workspace's map is used as it is, the line says so for the top of the report, and the ingest goes on",
      e == "" and pm(w) == {FID(1): "pat9001"} and any(l.startswith("PATIENT MAP: the repository's map could not be read") and l.endswith("TOP OF THE REPORT") for l in o.splitlines()) and "RESULT stamp" in o, (e, o[-500:]))
w, r, mreg = sandbox("map3", ["20261126a.hl7"], ws_map={FID(1): "pat9001"})
o, calls, e = driver_run(w, r, ARGS(S1), steps(w, S1, [msg(1, "20261126")], {}))
check("1f no map on main (a workspace without a clone): nothing is said and nothing changes", e == "" and "PATIENT MAP" not in o and pm(w) == {FID(1): "pat9001"}, (e, o[-300:]))
w, r, mreg = sandbox("map4", [], ws_map={FID(2): "pat9002"}, main_map={FID(2): "pat9902"})
o, calls, e = driver_run(w, r, ARGS(S1), lambda b, cmd: None)
check("1g on a quiet day (no new file) the map is corrected all the same - before the driver stops", e == "" and "nothing new - done" in o and pm(w) == {FID(2): "pat9902"} and calls == [], (e, o[-300:], pm(w)))

# the rehab monitor's register (pos61_monitor.json): the repository's copy when it is the LATER one - the review of the monitor (11/25/2026): the
# workspace's copy comes back from the state bundle and can be older than the one the mirror carried to main; the monitor goes by it for whose turn it is.
def mon_reg(at, tag): return {"version": "2026-11-25.2", "at": at, "lines": ["REHAB AT 61: " + tag], "top": [], "visits": {"vst" + tag: {"last_read": at[:10]}}}
def mon_case(label, ws_at, main_at, main_text=None):
    w_, r_, mreg_ = sandbox(label, ["20261126a.hl7"], ws_map={FID(1): "pat9001"})
    if ws_at is not None: json.dump(mon_reg(ws_at, "ws"), open(os.path.join(w_, "registers", "pos61_monitor.json"), "w"))
    if main_text is not None: open(os.path.join(mreg_, "pos61_monitor.json"), "w").write(main_text)
    elif main_at is not None: json.dump(mon_reg(main_at, "main"), open(os.path.join(mreg_, "pos61_monitor.json"), "w"))
    o_, calls_, e_ = driver_run(w_, r_, ARGS(S1), steps(w_, S1, [msg(1, "20261126")], {}))
    return e_, [l for l in o_.splitlines() if l.startswith("REHAB MONITOR REGISTER:")], (rd(w_, "registers", "pos61_monitor.json") or {}).get("lines")
check("1e the rehab monitor's register: the repository's copy is taken, whole, when it is LATER than the one this workspace was restored with (one line says so) - and when the workspace has none",
      lambda: mon_case("mon_later", "2026-11-25T06:40:00Z", "2026-11-26T00:41:10Z") == ("", ["REHAB MONITOR REGISTER: the repository's copy (2026-11-26T00:41:10Z) is later than this workspace's (2026-11-25T06:40:00Z) - taken, whole"], ["REHAB AT 61: main"])
      and (lambda c: c[0] == "" and len(c[1]) == 1 and c[2] == ["REHAB AT 61: main"])(mon_case("mon_none", None, "2026-11-26T00:41:10Z")), lambda: (mon_case("mon_later_x", "2026-11-25T06:40:00Z", "2026-11-26T00:41:10Z"), mon_case("mon_none_x", None, "2026-11-26T00:41:10Z")))
check("1f ... the workspace's own copy stays when it is the later one, or as late; and a copy on main that cannot be read, carries no time or is no register changes nothing - no line, the ingest goes on",
      lambda: all(mon_case("mon_keep%d" % i, "2026-11-26T00:41:10Z", a, t) == ("", [], ["REHAB AT 61: ws"]) for i, (a, t) in enumerate([("2026-11-25T06:40:00Z", None), ("2026-11-26T00:41:10Z", None), (None, "{ half"), (None, json.dumps({"lines": ["x"]})), (None, json.dumps(["at"])), (None, json.dumps({"at": "tomorrow"})), (None, None)])))

# William's standing word that a chart is a feed patient (registers/feed_same_person.json - the insurance check and the intake read it): its home is the
# repository; the ingest copies main's file into the workspace, whole, at every start - a workspace copy restored from the state bundle is only a copy.
def yes_case(label, ws_doc, main_doc):
    w_, r_, mreg_ = sandbox(label, ["20261126a.hl7"], ws_map={FID(1): "pat9001"})
    if ws_doc is not None: json.dump(ws_doc, open(os.path.join(w_, "registers", "feed_same_person.json"), "w"))
    if main_doc is not None: open(os.path.join(mreg_, "feed_same_person.json"), "w").write(main_doc if isinstance(main_doc, str) else json.dumps(main_doc))
    o_, calls_, e_ = driver_run(w_, r_, ARGS(S1), steps(w_, S1, [msg(1, "20261126")], {}))
    return e_, [l for l in o_.splitlines() if l.startswith("SAME PERSON FILE:")], rd(w_, "registers", "feed_same_person.json")
YES_M = {"pat9001": {"feed_ids": [FID(1)], "approved_by": "William 11/26/2026 (board)"}}; YES_W = {"pat9777": {"feed_ids": [FID(2)], "approved_by": "William 11/20/2026"}}
check("1g William's standing word 'same person' (registers/feed_same_person.json): the repository's file is copied into the workspace, whole, at every start - an entry taken out on main does not come back from a restored workspace; with no file on main the workspace's is left as it is",
      lambda: yes_case("yes_main", YES_W, YES_M) == ("", [], YES_M) and yes_case("yes_new", None, YES_M) == ("", [], YES_M) and yes_case("yes_empty", YES_W, {}) == ("", [], {}) and yes_case("yes_nomain", YES_W, None) == ("", [], YES_W),
      lambda: (yes_case("yes_main_x", YES_W, YES_M), yes_case("yes_empty_x", YES_W, {})))
check("1h ... a file on main that cannot be read, or is no JSON object, is not copied: the workspace's copy stays, one line says so for the top of the report, and the ingest goes on",
      lambda: all((lambda c: c[0] == "" and len(c[1]) == 1 and c[1][0].endswith("TOP OF THE REPORT") and c[2] == YES_W)(yes_case("yes_bad%d" % i, YES_W, t)) for i, t in enumerate(["{ half", json.dumps(["pat1"]), json.dumps("x")])))

# ---- 2. the identity register ------------------------------------------------------------------------------------------------------------------
S2 = "20261126T1840Z"
DEC = {KEY(1, DOB(1)[:7] + "9"): answer(5, "pat9101", flags=[FI.FLAG_DATE + FI.SLIP_DIGIT], cands=["pat9101", "pat9102"], ev=["slip:" + FI.SLIP_DIGIT], ids=[FID(1)]),      # the 11/17 shape: one digit off
       KEY(2, NODOB): answer(7, "pat9201", status="AMBIGUOUS", flags=[FI.FLAG_NO_FEED_DOB], cands=["pat9201", "pat9202"], dob="none", ids=[FID(2)]),                              # the 11/8 shape: the placeholder
       KEY(3): answer(9, "", cands=[], ids=[FID(3)], why=FI.WHY_NEW),                                                                                                           # a plain new patient
       KEY(4): answer(9, "", flags=[FI.FLAG_NOT_USED], cands=["pat9401"], will=True, ids=[FID(4)], why=FI.WHY_NEW_BESIDE)}                                                    # a new chart beside a same-name chart
PARSED2 = [msg(0, "20261126"), msg(1, "20261126", DOB(1)[:7] + "9"), msg(2, "20261126", NODOB), msg(3, "20261126"), msg(4, "20261126")]
w, r, mreg = sandbox("ident", ["20261126b.hl7"], ws_map={FID(0): "pat9000"})
o, calls, e = driver_run(w, r, ARGS(S2), steps(w, S2, PARSED2, DEC, newcharts={KEY(3): "pat9301", KEY(4): "pat9402"}))
I2 = ident(w, S2) or {}; ROWS = {tuple(p.get("feed_ids") or []): p for p in I2.get("patients") or []}
check("2a a live ingest writes registers/feed_identity_<stamp>.json: one row for every feed patient that was LOOKED UP (the patients known from the map are counted, not listed)",
      e == "" and sorted(ROWS) == sorted([(FID(1),), (FID(2),), (FID(3),), (FID(4),)]) and (I2.get("counts") or {}).get("known from the patient map") == 1 and (I2.get("counts") or {}).get("looked up") == 4
      and I2.get("stamp") == S2 and I2.get("identity_rule") == FI.IDENTITY_RULE_VERSION, (e, o[-500:], I2))
check("2b a row holds the chart, the rule number and the rule's fixed words - exactly the fields feed_identity.py names as free of patient data - and whether the chart is a new one",
      lambda: len(ROWS) == 4 and all(set(p) == set(FI.PHI_FREE_FIELDS) | {"feed_ids", "chart", "status", "new_chart"} for p in ROWS.values())
      and (ROWS[(FID(1),)]["chart"], ROWS[(FID(1),)]["rule"], ROWS[(FID(1),)]["flags"], ROWS[(FID(1),)]["new_chart"]) == ("pat9101", 5, [FI.FLAG_DATE + FI.SLIP_DIGIT], False)
      and (ROWS[(FID(2),)]["chart"], ROWS[(FID(2),)]["rule"], ROWS[(FID(2),)]["feed_dob"]) == ("pat9201", 7, "none")
      and (ROWS[(FID(3),)]["chart"], ROWS[(FID(3),)]["new_chart"], ROWS[(FID(4),)]["chart"], ROWS[(FID(4),)]["new_chart"], ROWS[(FID(4),)]["for_william"]) == ("pat9301", True, "pat9402", True, True), ROWS)
check("2c the driver's own field list is feed_identity.py's (one list, two places - they cannot drift apart unseen)",
      lambda: re.search(r"^ID_FIELDS = (\(.*?\))", DSRC, re.M) is not None and eval(re.search(r"^ID_FIELDS = (\(.*?\))", DSRC, re.M).group(1)) == FI.PHI_FREE_FIELDS)
_txt = json.dumps(I2) + o; _keys = ['"lookup"', '"amd_answer"', '"resolution"', '"amd_names"']
check("2d no name and no birth date reaches the register or a printed line, and none of the workspace-only fields of the match file (the candidates' names and dates, AdvancedMD's own words) is in the register",
      not any(s in _txt for s in secrets(0, 1, 2, 3, 4, 7) + [NODOB]) and not any(k in json.dumps(I2) for k in _keys), [s for s in secrets(0, 1, 2, 3, 4, 7) + [NODOB] if s in _txt] + [k for k in _keys if k in json.dumps(I2)])
check("2e the patient map learns every looked-up patient's chart, the new charts included (the next run takes them from the map)",
      pm(w) == {FID(0): "pat9000", FID(1): "pat9101", FID(2): "pat9201", FID(3): "pat9301", FID(4): "pat9402"}, pm(w))
check("2f the entries the driver makes for the patients it knows from the map carry the same fields as a decided one: rule 'map' and the map's fixed words",
      lambda: (match(w, S2).get(KEY(0)) or {}).get("rule") == "map" and (match(w, S2).get(KEY(0)) or {}).get("why") == FI.WHY_MAP and FI.problems(match(w, S2).get(KEY(0)) or {}) == [], match(w, S2).get(KEY(0)))
BAD = dict(DEC); BAD[KEY(1, DOB(1)[:7] + "9")] = dict(DEC[KEY(1, DOB(1)[:7] + "9")], why="matched to " + NAME(1), flags=["born " + DOB(1)])
w, r, mreg = sandbox("ident_bad", ["20261126b.hl7"], ws_map={FID(0): "pat9000"})
o, calls, e = driver_run(w, r, ARGS(S2), steps(w, S2, PARSED2, BAD, newcharts={KEY(3): "pat9301", KEY(4): "pat9402"}))
I2b = ident(w, S2) or {}; _row = next((p for p in I2b.get("patients") or [] if p.get("feed_ids") == [FID(1)]), {})
check("2g a field that is NOT one of the fixed words is withheld, never copied: the row keeps the chart and names the fields left out - the patient's name and date do not reach the register",
      e == "" and _row.get("chart") == "pat9101" and sorted(_row.get("withheld") or []) == ["flags", "why"] and "why" not in _row and "flags" not in _row and not any(s in json.dumps(I2b) for s in secrets(1)), (e, _row))
w, r, mreg = sandbox("ident_dry", ["20261126b.hl7"], ws_map={FID(0): "pat9000"})
o, calls, e = driver_run(w, r, ARGS(S2, live=False), steps(w, S2, PARSED2, DEC))
check("2h a DRY ingest writes no identity register and starts no new-chart step; its line about the charts it WOULD make gives a count and the Claimocity ids - no letter of a name (it used to print four)",
      e == "" and ident(w, S2) is None and "claimocity_newcharts.py" not in calls and any(l.startswith("DRY: 2 patient(s) would get a NEW chart") and FID(3) in l and FID(4) in l for l in o.splitlines())
      and not any(s[:4] in o for s in secrets(3, 4)), (e, calls, o[-500:]))

# ---- 3. a file is not registered while a patient of it has no chart -----------------------------------------------------------------------------
S3 = "20261127T1240Z"
DEC3 = {KEY(3): answer(9, "", ids=[FID(3)], why=FI.WHY_NEW), KEY(5): answer(0, "", status="AMBIGUOUS", will=True, ids=[FID(5)], why=FI.WHY_DISAGREE), KEY(1): answer(2, "pat9101", ids=[FID(1)])}
PARSED3 = [msg(1, "20261127"), msg(3, "20261127"), msg(1, "20261128"), msg(5, "20261129"), msg(1, "20261130")]
w, r, mreg = sandbox("nochart", ["20261127a.hl7", "20261128a.hl7", "20261129a.hl7", "20261130a.hl7"], ws_map={})
o, calls, e = driver_run(w, r, ARGS(S3), steps(w, S3, PARSED3, DEC3, newcharts={}))      # the new chart of patient 3 is refused; patient 5 is not decided
_reg = ingest(w); _l = next((l for l in o.splitlines() if l.startswith("NOT REGISTERED:")), "")
check("3a a file that holds a patient with NO chart - a new chart AdvancedMD refused, a patient the rule could not decide - is NOT registered; the files whose patients all have a chart are",
      e == "" and sorted(_reg.get("files") or {}) == ["20261128a.hl7", "20261130a.hl7"], (e, o[-700:], sorted(_reg.get("files") or {})))
check("3b ONE line says it for the top of the report: how many files, which, which Claimocity ids - and that the next start reads them again",
      _l.startswith("NOT REGISTERED: 2 file(s)") and "20261127a.hl7" in _l and "20261129a.hl7" in _l and FID(3) in _l and FID(5) in _l and "the next start reads" in _l and _l.endswith("TOP OF THE REPORT")
      and not any(s in o for s in secrets(1, 3, 5)), (_l, o[-400:]))
check("3c the RESULT line counts them, and the identity register lists the files and shows both patients without a chart (the refused one flagged 'new chart not made')",
      lambda: re.search(r"RESULT stamp %s: files 4, .*2 file\(s\) NOT registered" % S3, o) is not None and (ident(w, S3) or {}).get("not_registered") == ["20261127a.hl7", "20261129a.hl7"]
      and {tuple(p["feed_ids"]): (p["chart"], FI.FLAG_NO_CHART_MADE in (p.get("flags") or [])) for p in (ident(w, S3) or {}).get("patients") or []}
      == {(FID(1),): ("pat9101", False), (FID(3),): ("", True), (FID(5),): ("", False)}, (o[-300:], ident(w, S3)))
check("3d the patient map learns no chart for such a patient", pm(w) == {FID(1): "pat9101"}, pm(w))
S3b = "20261127T1241Z"
o, calls, e = driver_run(w, r, ARGS(S3b), steps(w, S3b, [msg(1, "20261127"), msg(3, "20261127"), msg(5, "20261129")], {KEY(3): DEC3[KEY(3)], KEY(5): answer(2, "pat9501", ids=[FID(5)])}, newcharts={KEY(3): "pat9301"}))
check("3e the NEXT start reads exactly those two files again (a new stamp), and once every patient has a chart they are registered - nothing is lost and nothing is asked a third time",
      e == "" and "2 new file(s) of 4" in o and sorted(ingest(w).get("files") or {}) == ["20261127a.hl7", "20261128a.hl7", "20261129a.hl7", "20261130a.hl7"] and "NOT REGISTERED" not in o
      and pm(w) == {FID(1): "pat9101", FID(3): "pat9301", FID(5): "pat9501"}, (e, o[-600:], sorted(ingest(w).get("files") or {})))
w, r, mreg = sandbox("nochart_empty", ["20261127a.hl7", "20261128a.hl7"], ws_map={FID(1): "pat9101"})
_noline = dict(msg(3, "20261127"), FT1=[]); _nopid = {"pid": None, "file": "20261128", "FT1": [{"cpt": "99308", "dos": "20261120", "dx": "I10", "units": "1"}], "name": "", "dob": ""}
o, calls, e = driver_run(w, r, ARGS(S3), steps(w, S3, [msg(1, "20261127"), _noline, msg(1, "20261128"), _nopid], {KEY(3): answer(0, "", status="AMBIGUOUS", will=True, ids=[FID(3)], why=FI.WHY_DISAGREE)}))
check("3e2 a message that is nobody's visit does not keep its file back: one without a charge line (also of a patient with no chart) and one without a patient id are passed over by the import, and their files are registered",
      lambda: e == "" and sorted(ingest(w).get("files") or {}) == ["20261127a.hl7", "20261128a.hl7"] and "NOT REGISTERED" not in o, lambda: (e, o[-500:], sorted(ingest(w).get("files") or {})))
w, r, mreg = sandbox("nochart_dry", ["20261127a.hl7"], ws_map={})
o, calls, e = driver_run(w, r, ARGS(S3, live=False), steps(w, S3, PARSED3[:2], DEC3))
check("3f a dry ingest registers no file, as before, and says nothing about files it would not register", e == "" and (ingest(w).get("files") or {}) == {} and "NOT REGISTERED" not in o and "(DRY - nothing written, files not registered)" in o, (e, o[-300:]))

# ---- 4. two feed patients under one name and birth date: each Claimocity id keeps its own chart -------------------------------------------------
S4 = "20261128T1240Z"; TWIN = FID(6)[:22] + "ff"      # a second Claimocity id under the name and date of patient 1
def by_id(w, stamp, key): return (match(w, stamp).get(key) or {}).get("by_id")
def irow(w, stamp, fid): return next((p for p in (ident(w, stamp) or {}).get("patients") or [] if p.get("feed_ids") == [fid]), {})
TWO = [msg(1, "20261128"), msg(1, "20261128", fid=TWIN)]
w, r, mreg = sandbox("shared_same", ["20261128a.hl7"], ws_map={FID(1): "pat9101"})
o, calls, e = driver_run(w, r, ARGS(S4), steps(w, S4, TWO, {KEY(1): answer(2, "pat9101", ids=[TWIN])}))
check("4a a NEW Claimocity id under the name and birth date of a known one, for whom the identity rule chose the SAME chart: one patient - both ids are named with that chart, the visits go in, and the map learns the new id",
      lambda: e == "" and by_id(w, S4, KEY(1)) == {FID(1): "pat9101", TWIN: "pat9101"} and match(w, S4)[KEY(1)].get("resolved") == "pat9101" and pm(w) == {FID(1): "pat9101", TWIN: "pat9101"}
      and "NOT REGISTERED" not in o and sorted(ingest(w).get("files") or {}) == ["20261128a.hl7"], lambda: (e, o[-500:], match(w, S4)))
w, r, mreg = sandbox("shared_other", ["20261128a.hl7"], ws_map={FID(1): "pat9101"})
o, calls, e = driver_run(w, r, ARGS(S4), steps(w, S4, TWO, {KEY(1): answer(4, "pat9777", ids=[TWIN], ev=["ssn"])}))
check("4b ... when the identity rule points the new id to ANOTHER chart, the two are not put on one chart by the name alone: each id is named with its own chart (the import asks by the message's own id), the map learns the new id's chart, and the register's row shows it",
      lambda: e == "" and by_id(w, S4, KEY(1)) == {FID(1): "pat9101", TWIN: "pat9777"} and pm(w) == {FID(1): "pat9101", TWIN: "pat9777"} and (irow(w, S4, TWIN).get("chart"), irow(w, S4, TWIN).get("rule")) == ("pat9777", 4)
      and sorted(ingest(w).get("files") or {}) == ["20261128a.hl7"] and not any(s in o for s in secrets(1)), lambda: (e, o[-500:], match(w, S4).get(KEY(1)), ident(w, S4)))
check("4b2 ... and for a reader that does not know the per-id charts the key still reads as it always did - the KNOWN chart - never the new id's (the rule's own choice is kept beside it)",
      lambda: match(w, S4)[KEY(1)].get("resolved") == "pat9101" and match(w, S4)[KEY(1)].get("decided_chart") == "pat9777", lambda: match(w, S4).get(KEY(1)))
w, r, mreg = sandbox("shared_new", ["20261128a.hl7"], ws_map={FID(1): "pat9101"})
o, calls, e = driver_run(w, r, ARGS(S4), steps(w, S4, TWO, {KEY(1): answer(9, "", ids=[TWIN], why=FI.WHY_NEW)}, newcharts={KEY(1): "pat9888"}))
check("4c ... when the rule says NEW CHART for the new id, the new-chart step still gets its entry (the known id's entry does not cover it up): the new chart is the new id's, the known id keeps its own",
      lambda: e == "" and "claimocity_newcharts.py" in calls and by_id(w, S4, KEY(1)) == {FID(1): "pat9101", TWIN: "pat9888"} and pm(w) == {FID(1): "pat9101", TWIN: "pat9888"}
      and (irow(w, S4, TWIN).get("chart"), irow(w, S4, TWIN).get("new_chart")) == ("pat9888", True), lambda: (e, calls, o[-500:], match(w, S4).get(KEY(1))))
w, r, mreg = sandbox("shared_none", ["20261128a.hl7", "20261129a.hl7"], ws_map={FID(1): "pat9101"})
o, calls, e = driver_run(w, r, ARGS(S4), steps(w, S4, TWO + [msg(1, "20261129")], {KEY(1): answer(0, "", status="AMBIGUOUS", will=True, ids=[TWIN], why=FI.WHY_SHARED)}))
_l = next((l for l in o.splitlines() if l.startswith("NOT REGISTERED:")), "")
check("4d ... when the rule cannot decide the new id, the new id gets NO chart (it is never entered on the known chart by the name alone) while the known id's visits go in; only the file that holds the new id stays unregistered, and the line names the new id alone",
      lambda: e == "" and by_id(w, S4, KEY(1)) == {FID(1): "pat9101"} and pm(w) == {FID(1): "pat9101"} and sorted(ingest(w).get("files") or {}) == ["20261129a.hl7"] and "20261128a.hl7" in _l and TWIN in _l and FID(1) not in _l
      and irow(w, S4, TWIN).get("chart") == "" and irow(w, S4, TWIN).get("for_william") is True, lambda: (e, _l, o[-500:], match(w, S4).get(KEY(1))))
w, r, mreg = sandbox("known_two", ["20261128a.hl7"], ws_map={FID(1): "pat9101", TWIN: "pat9102"})
o, calls, e = driver_run(w, r, ARGS(S4), steps(w, S4, TWO, {}))
check("4e two KNOWN Claimocity ids of one name and birth date that the map sends to two charts: each id keeps its own chart (until now the first one's chart was used for both and the map was rewritten), and a line says there may be duplicate charts",
      lambda: e == "" and by_id(w, S4, KEY(1)) == {FID(1): "pat9101", TWIN: "pat9102"} and pm(w) == {FID(1): "pat9101", TWIN: "pat9102"}
      and any(l.startswith("PATIENT MAP: 2 Claimocity ids under one name and birth date go to 2 charts") and "pat9101" in l and "pat9102" in l for l in o.splitlines()) and not any(s in o for s in secrets(1)), lambda: (e, o[-500:], match(w, S4).get(KEY(1))))
check("4f every entry names the chart of each of its Claimocity ids - also the plain ones (a known patient; a looked-up patient)",
      lambda: by_id(os.path.join(TMP, "ident", "ws"), S2, KEY(0)) == {FID(0): "pat9000"} and by_id(os.path.join(TMP, "ident", "ws"), S2, KEY(3)) == {FID(3): "pat9301"} and by_id(os.path.join(TMP, "nochart", "ws"), S3, KEY(5)) == {},
      lambda: (match(os.path.join(TMP, "ident", "ws"), S2).get(KEY(0)), match(os.path.join(TMP, "nochart", "ws"), S3).get(KEY(5))))

# two UNKNOWN Claimocity ids under one name that carries no date of birth - the review of the identity rule: the resolve step weighs each on its own and
# writes ONE answer under the key they share - a chart (with both ids under decided_for) when the rule gives both the same one, else rule 0 with
# decided_for [] and what was gathered for each under "sharers" (names and dates of charts: workspace only).
S4s = "20261128T1250Z"; P1900 = "19" + "000101"; KSH = KEY(1, P1900); TWO0 = [msg(1, "20261128", dob=P1900), msg(1, "20261128", dob=P1900, fid=TWIN)]
SHARERS = [{"ids": [FID(1)], "lookup": [{"pid": "pat9101", "name": NAME(7), "dob": DOB(7)}], "cut": "", "every_spelling": True}, {"ids": [TWIN], "lookup": [{"pid": "pat9101", "name": NAME(7), "dob": DOB(7)}], "cut": "", "every_spelling": True}]
w, r, mreg = sandbox("sharers_same", ["20261128a.hl7"], ws_map={})
o, calls, e = driver_run(w, r, ARGS(S4s), steps(w, S4s, TWO0, {KSH: dict(answer(7, "pat9101", ids=sorted([FID(1), TWIN]), flags=[FI.FLAG_NO_FEED_DOB], cands=["pat9101"], dob="none"), sharers=SHARERS)}))
_row = next((p for p in (ident(w, S4s) or {}).get("patients") or []), {})
check("4g two UNKNOWN Claimocity ids under one name with no birth date, the rule giving both the SAME chart: both ids are named with it, both visits go in, the map learns both, the file is registered - and nothing of what was gathered for each ('sharers') reaches the register",
      lambda: e == "" and by_id(w, S4s, KSH) == {FID(1): "pat9101", TWIN: "pat9101"} and pm(w) == {FID(1): "pat9101", TWIN: "pat9101"} and "NOT REGISTERED" not in o and sorted(ingest(w).get("files") or {}) == ["20261128a.hl7"]
      and sorted(_row.get("feed_ids") or []) == sorted([FID(1), TWIN]) and (_row.get("chart"), _row.get("rule")) == ("pat9101", 7) and "sharers" not in json.dumps(ident(w, S4s)) and not any(x in json.dumps(ident(w, S4s)) + o for x in secrets(1, 7)),
      lambda: (e, o[-500:], match(w, S4s).get(KSH), ident(w, S4s)))
w, r, mreg = sandbox("sharers_none", ["20261128a.hl7", "20261129a.hl7"], ws_map={FID(2): "pat9201"})
_none = dict(answer(0, "", status="AMBIGUOUS", will=True, ids=sorted([FID(1), TWIN]), why=FI.WHY_SHARED, cands=["pat9101"], dob="none"), decided_for=[], sharers=SHARERS,
             resolution="not decided: %s - no chart chosen, none made (each on its own: %s -> pat9101; %s -> a new chart)" % (FI.WHY_SHARED, FID(1), TWIN))
o, calls, e = driver_run(w, r, ARGS(S4s), steps(w, S4s, TWO0 + [msg(2, "20261129")], {KSH: _none}))
_l = next((l for l in o.splitlines() if l.startswith("NOT REGISTERED:")), ""); _row = next((p for p in (ident(w, S4s) or {}).get("patients") or []), {})
check("4h ... the rule NOT giving both the same chart: the key carries no chart - neither id is named with one, neither visit is entered, the map learns neither, their file stays unregistered and the line names both ids; the register's row shows no chart, for William",
      lambda: e == "" and by_id(w, S4s, KSH) == {} and pm(w) == {FID(2): "pat9201"} and sorted(ingest(w).get("files") or {}) == ["20261129a.hl7"] and "20261128a.hl7" in _l and FID(1) in _l and TWIN in _l
      and "claimocity_newcharts.py" not in calls and sorted(_row.get("feed_ids") or []) == sorted([FID(1), TWIN]) and (_row.get("chart"), _row.get("rule"), _row.get("for_william"), _row.get("why")) == ("", 0, True, FI.WHY_SHARED)
      and "sharers" not in json.dumps(ident(w, S4s)) and not any(x in json.dumps(ident(w, S4s)) + o for x in secrets(1, 7)), lambda: (e, _l, calls, match(w, S4s).get(KSH), ident(w, S4s)))
w, r, mreg = sandbox("sharers_own", ["20261128a.hl7", "20261129a.hl7"], ws_map={})
o, calls, e = driver_run(w, r, ARGS(S4s), steps(w, S4s, [msg(1, "20261128"), msg(1, "20261129", dob=P1900), msg(1, "20261129", dob=P1900, fid=TWIN)], {KEY(1): answer(2, "pat9101", ids=[FID(1)]), KSH: _none}))
check("4i ... and an id that HAS a chart through a key of its own (it also came with its real date) keeps it there: that visit goes in and the map learns the id - while its message under the shared key with no chart is not entered, and only that file is read again",
      lambda: e == "" and by_id(w, S4s, KEY(1)) == {FID(1): "pat9101"} and by_id(w, S4s, KSH) == {} and pm(w) == {FID(1): "pat9101"} and sorted(ingest(w).get("files") or {}) == ["20261128a.hl7"]
      and "20261129a.hl7" in next((l for l in o.splitlines() if l.startswith("NOT REGISTERED:")), ""), lambda: (e, o[-600:], match(w, S4s)))
w, r, mreg = sandbox("new_waits", ["20261128a.hl7", "20261129a.hl7"], ws_map={})
o, calls, e = driver_run(w, r, ARGS(S4s), steps(w, S4s, [msg(3, "20261128"), msg(3, "20261129", dob=DOB(4), fid=TWIN)],
                                                {KEY(3): answer(9, "", ids=[FID(3)], why=FI.WHY_NEW), KEY(3, DOB(4)): answer(0, "", status="AMBIGUOUS", ids=[TWIN], why=FI.WHY_SAME_RUN)}, newcharts={KEY(3): "pat9301"}))
_wrow = irow(w, S4s, TWIN)
check("4j a patient whose NEW chart waits for the next run (another Claimocity id of the same name got a new chart in this run - feed_identity.new_chart_waits): the first one's chart is made and its visit goes in; the one that waits gets no chart, its file is read again, "
      "and the register's row says why in the rule's fixed words - not for William",
      lambda: e == "" and by_id(w, S4s, KEY(3)) == {FID(3): "pat9301"} and by_id(w, S4s, KEY(3, DOB(4))) == {} and pm(w) == {FID(3): "pat9301"} and sorted(ingest(w).get("files") or {}) == ["20261128a.hl7"]
      and (_wrow.get("chart"), _wrow.get("rule"), _wrow.get("why"), _wrow.get("for_william")) == ("", 0, FI.WHY_SAME_RUN, False) and "withheld" not in _wrow, lambda: (e, o[-500:], match(w, S4s), ident(w, S4s)))

# ---- 5. what the driver prints -------------------------------------------------------------------------------------------------------------------
S5 = "20261129T1240Z"; LONG = "POS RULE: CCM 32 x12, CCM 31 x0, visits 32 x104, visits 31 x18, not applied x0, unknown bldg x0, rehab 61 x11/21 x24 - END"
w, r, mreg = sandbox("tail", ["20261129a.hl7"], ws_map={FID(1): "pat9101"})
o, calls, e = driver_run(w, r, ARGS(S5), steps(w, S5, [msg(1, "20261129")], {}, tail=LONG + "\nDONE {}"))
check("5a a step's last lines are shown whole up to 160 characters (the import's place-of-service line is 120 with real counts; it used to be cut at 110)", e == "" and LONG in o, (e, [l for l in o.splitlines() if l.startswith("[import]")]))
check("5b the driver's header states the three rules of 11/25/2026 (the repository's map answers; the identity register; a file is not registered while a patient of it has no chart) and its step 3 names the identity rule",
      all(x in DSRC.split("\nimport os, sys")[0] for x in ("feed_identity.py", "the REPOSITORY's patient map answers", "registers/feed_identity_<stamp>.json", "A FILE IS NOT REGISTERED while a patient of it has no chart", "William 11/25/2026")), DSRC[:300])
check("5c every helper of the identity rule travels with the others: the shared list the driver makes current on every run names the match, resolve and new-chart steps and the rule itself",
      all(f in HC.FEED_HELPERS for f in ("claimocity_match.py", "claimocity_resolve.py", "claimocity_newcharts.py", "feed_identity.py")), HC.FEED_HELPERS)

# ---- 7. the feed's digest says it (claimocity_report.py, run inside this process over invented registers) -----------------------------------------
REPORT = os.path.join(HELPERS, "claimocity_report.py"); RSRC = open(REPORT).read()
def report_run(label, stamp, created, identity=None, inspector=None, newcharts=None, unreadable=None, verify=None):
    """the report helper over ONE invented batch -> (its digest's lines, its error)"""
    d = os.path.join(TMP, "report_" + label); os.makedirs(os.path.join(d, "registers")); os.makedirs(os.path.join(d, "outbox"))
    json.dump({"created": created, "skipped": [], "failed": []}, open(os.path.join(d, "registers", "feed_import_%s.json" % stamp), "w"))
    if identity is not None: open(os.path.join(d, "registers", "feed_identity_%s.json" % stamp), "w").write(identity if isinstance(identity, str) else json.dumps(identity))
    if inspector is not None: json.dump(inspector, open(os.path.join(d, "registers", "feed_inspector_%s.json" % stamp), "w"))
    if newcharts is not None: json.dump(newcharts, open(os.path.join(d, "registers", "feed_newcharts_%s.json" % stamp), "w"))
    if unreadable is not None: open(os.path.join(d, "registers", "feed_unreadable_%s.json" % stamp), "w").write(unreadable if isinstance(unreadable, str) else json.dumps(unreadable))
    if verify is not None: json.dump(verify, open(os.path.join(d, "feed_verify_%s.json" % stamp), "w"))      # the insurance check's own file, in the workspace (the digest writes the register copy)
    shutil.copy2(os.path.join(HELPERS, "feed_identity.py"), os.path.join(d, "feed_identity.py"))
    old_cwd = os.getcwd(); old_env = dict(os.environ); old_path = list(sys.path); old_fi = sys.modules.pop("feed_identity", None); out = io.StringIO(); err = ""
    try:
        os.chdir(d); os.environ["FEED_STAMP"] = stamp; sys.path.insert(0, d)
        with contextlib.redirect_stdout(out):
            try: exec(compile(RSRC, REPORT, "exec"), {"__name__": "__main__", "__file__": REPORT})
            except SystemExit: pass
            except Exception as e: err = "%s: %s" % (type(e).__name__, e)
    finally:
        os.chdir(old_cwd); os.environ.clear(); os.environ.update(old_env); sys.path[:] = old_path; sys.modules.pop("feed_identity", None)
        if old_fi is not None: sys.modules["feed_identity"] = old_fi
    try: lines = open(os.path.join(d, "feed_digest_%s.md" % stamp)).read().splitlines()
    except OSError: lines = []
    return lines, err
def vrow(pid, visit, dos, cpts, **more):
    r_ = {"pid": pid, "visit": visit, "dos": dos, "cpts": list(cpts), "fees": ["100.00"] * len(cpts), "charges": ["chg%s%d" % (visit[3:], i) for i in range(len(cpts))], "fac": "fac29", "pos": "21", "pos_feed": "21",
          "pos_lines": ["21"] * len(cpts), "pos_kind": [""] * len(cpts), "pos_err": "", "feed_id": FID(1)}
    r_.update(more); return r_
def top(lines): return [l for l in lines if "TOP OF THE REPORT" in l]
def has(lines, *words): return [l for l in lines if all(w in l for w in words)]
S7 = "20261130T1240Z"
IDENT7 = {"stamp": S7, "at": "2026-11-30T12:45:00Z", "identity_rule": FI.IDENTITY_RULE_VERSION,
          "counts": {"known from the patient map": 41, "looked up": 6, "new charts": 2, "for William": 3, "no chart": 2},
          "repointed": [{"feed_id": FID(9), "was": "pat9002", "now": "pat9902"}],
          "patients": [dict(feed_ids=[FID(1)], chart="pat9101", status="FOUND", new_chart=False, rule=2, why=FI.WHY[2], flags=[], candidates=["pat9101"], evidence=[], feed_dob="real", for_william=False),
                       dict(feed_ids=[FID(2)], chart="pat9201", status="AMBIGUOUS", new_chart=False, rule=5, why=FI.WHY[5], flags=[FI.FLAG_DATE + FI.SLIP_DIGIT], candidates=["pat9201", "pat9202"], evidence=["slip:" + FI.SLIP_DIGIT], feed_dob="real", for_william=False),
                       dict(feed_ids=[FID(3)], chart="pat9301", status="MISSING", new_chart=True, rule=9, why=FI.WHY_NEW_BESIDE, flags=[FI.FLAG_NOT_USED], candidates=["pat9311", "pat9312"], evidence=[], feed_dob="real", for_william=True),
                       dict(feed_ids=[FID(4)], chart="pat9401", status="MISSING", new_chart=True, rule=9, why=FI.WHY_NEW, flags=[FI.FLAG_NO_FEED_DOB], candidates=[], evidence=[], feed_dob="none", for_william=True),
                       dict(feed_ids=[FID(5)], chart="", status="AMBIGUOUS", new_chart=False, rule=0, why=FI.WHY_DISAGREE, flags=[], candidates=["pat9501", "pat9502"], evidence=[], feed_dob="real", for_william=True),
                       dict(feed_ids=[FID(6)], chart="", status="MISSING", new_chart=False, rule=9, why=FI.WHY_NEW, flags=[FI.FLAG_NO_CHART_MADE], candidates=[], evidence=[], feed_dob="real", for_william=True)],
          "notes": [], "not_registered": ["20261130a.hl7"]}
L7, e7 = report_run("identity", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], identity=IDENT7)
_sec = L7[L7.index(next((l for l in L7 if l.startswith("## Which chart")), "")):] if any(l.startswith("## Which chart") for l in L7) else []
check("7a the digest gets a section 'Which chart' from the identity register: ONE line with the counts - known from the map, looked up (by rule), new charts, no chart",
      lambda: e7 == "" and len(has(_sec, "41 feed patient(s) known from the patient map", "6 looked up", "rule 2 x1", "rule 5 x1", "rule 9 x3", "rule 0 x1", "2 new chart(s)", "2 with NO chart")) == 1, lambda: (e7, _sec[:6]))
check("7b what is for William stands at the TOP OF THE REPORT, one line each, chart ids and Claimocity ids only: a new chart beside same-name charts (the question, with those charts), a new chart with no birth date (face sheet needed), a patient nobody could decide, a new chart that could not be made",
      lambda: len(has(top(_sec), "pat9301", "pat9311", "pat9312", "same person or not?")) == 1 and len(has(top(_sec), "pat9401", "face sheet needed")) == 1
      and len(has(top(_sec), "no chart chosen and none made", FID(5))) == 1 and len(has(top(_sec), "could NOT be made", FID(6))) == 1, lambda: top(_sec))
check("7c a match by a slip in the birth date is said in the section's body with the chart and the kind of slip - not at the top; a plain match by name and date gets no line of its own",
      lambda: len(has(_sec, "pat9201", FI.SLIP_DIGIT)) == 1 and not has(top(_sec), "pat9201") and not has(_sec, "pat9101"), lambda: _sec)
L7r, e7r = report_run("identity_dob", S7, [vrow("pat9201", "vst7002", "11/29/2026", ["99308"], dob_note="differs: one digit")], identity=IDENT7)
check("7c2 with the 'Which chart' section in the digest the birth-date line stands inside it (no heading of its own)",
      lambda: e7r == "" and len([l for l in L7r if l.startswith("- Birth dates:")]) == 1 and not any(l.startswith("## Birth dates") for l in L7r)
      and L7r.index(next(l for l in L7r if l.startswith("## Which chart"))) < L7r.index(next(l for l in L7r if l.startswith("- Birth dates:"))) < L7r.index(next(l for l in L7r if l.startswith("## Next"))), lambda: (e7r, [l[:60] for l in L7r if l.startswith(("##", "- Birth"))]))
check("7d the files that stay unregistered are named at the top (the next start reads them again), and a feed patient re-pointed to the repository's chart in the body with both charts",
      lambda: len(has(top(_sec), "NOT REGISTERED", "20261130a.hl7", "the next start reads")) == 1 and len(has(_sec, "Patient map", FID(9), "pat9002", "pat9902")) == 1, lambda: _sec)
BAD7 = json.loads(json.dumps(IDENT7)); BAD7["patients"] = [dict(feed_ids=[FID(2)], chart="pat9201", status="FOUND", new_chart=False, withheld=["flags", "why"], rule=5, candidates=[], evidence=[], feed_dob="real", for_william=False),
                                                           dict(feed_ids=[FID(3)], chart="pat9301", status="FOUND", new_chart=False, rule=5, why="matched to " + NAME(3), flags=[], candidates=[], evidence=[], feed_dob="real", for_william=False)]
L7b, e7b = report_run("identity_bad", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], identity=BAD7)
check("7e a row whose words were withheld is named at the top with the fields left out; and a word in the register that is NOT one of the rule's fixed words is never printed (the digest goes to Drive)",
      lambda: e7b == "" and len(has(top(L7b), FID(2), "pat9201", "flags, why")) == 1 and not any(x in "\n".join(L7b) for x in secrets(3)) and len(has(top(L7b), FID(3), "pat9301")) == 1, lambda: (e7b, top(L7b)))
L7c, e7c = report_run("identity_none", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])])
L7d, e7d = report_run("identity_broken", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], identity="{ half written")
check("7f a batch without an identity register (an older batch, a retry) gets no such section; a register that cannot be read gets ONE line at the top and the digest is still written whole",
      lambda: e7c == "" and not any("Which chart" in l for l in L7c) and e7d == "" and len(has(top(L7d), "which-chart lines could not be built")) == 1 and any(l.startswith("## Next") for l in L7d), lambda: (e7c, e7d, top(L7d)))
# birth dates (the import's rows: dob_note - fixed words, never a date)
ROWS8 = [vrow("pat9101", "vst7001", "11/29/2026", ["99308"], dob_note="same"), vrow("pat9201", "vst7002", "11/29/2026", ["99308"], dob_note="differs: one digit"), vrow("pat9201", "vst7003", "11/30/2026", ["99308"], dob_note="differs: one digit"),
         vrow("pat9301", "vst7004", "11/29/2026", ["99309"], dob_note="differs: far"), vrow("pat9401", "vst7005", "11/29/2026", ["99309"], dob_note="no birth date from Claimocity"), vrow("pat9501", "vst7006", "11/29/2026", ["99309"], dob_note="chart has no birth date")]
L8, e8 = report_run("dob", S7, ROWS8)
_bd = [l for l in L8 if l.startswith("- Birth dates:")]
check("7g ONE line says where the feed's birth date and the chart's differ - by chart, with the kind of difference, a chart once - and where Claimocity sent none or the chart has none; it says the visit went on the chart as it stands",
      lambda: e8 == "" and len(_bd) == 1 and "differ on 2 chart(s)" in _bd[0] and "pat9201 one digit" in _bd[0] and "pat9301 far" in _bd[0] and "no birth date for 1 chart(s) (pat9401)" in _bd[0] and "1 chart(s) carry no birth date themselves (pat9501)" in _bd[0]
      and "pat9101" not in _bd[0] and "TOP OF THE REPORT" not in _bd[0] and L8[L8.index(_bd[0]) - 1].startswith("## Birth dates"), lambda: (e8, _bd))
L8b, e8b = report_run("dob_same", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"], dob_note="same"), vrow("pat9102", "vst7002", "11/29/2026", ["99308"])])
check("7h no such line when every visit's feed date is its chart's (or the rows carry no note - an older import)", lambda: e8b == "" and not has(L8b, "Birth dates"), lambda: (e8b, has(L8b, "Birth dates")))
L8c2, e8c2 = report_run("dob_unread", S7, ROWS8 + [vrow("pat9601", "vst7007", "11/29/2026", ["99309"], dob_note="chart not read")])
_bd2 = [l for l in L8c2 if l.startswith("- Birth dates:")]
check("7h2 a chart whose own answer could not be read is a group of its own on that line - never counted as a chart that has none (the review's finding)",
      lambda: e8c2 == "" and len(_bd2) == 1 and "1 chart(s) could not be read (pat9601)" in _bd2[0] and "1 chart(s) carry no birth date themselves (pat9501)" in _bd2[0], lambda: (e8c2, _bd2))
L8c3, e8c3 = report_run("dob_unread_only", S7, [vrow("pat9601", "vst7007", "11/29/2026", ["99309"], dob_note="chart not read")])
check("7h3 ... and it is said when it is the only thing to say", lambda: e8c3 == "" and len(has(L8c3, "- Birth dates:", "1 chart(s) could not be read (pat9601)")) == 1, lambda: (e8c3, has(L8c3, "Birth dates")))
# the insurance check's two holds of 11/25/2026 (review): 'same person?' and 'no birth date on either side' - one line each at the top of the report
def vrec(visits, **more): return dict({"decision": "HOLD", "visits": list(visits), "hold": [], "checks": [], "plans": [], "insorder": "", "lead": ""}, **more)
VER7 = {"pat9301": vrec(["vst7004"], same_person=["vst7004"], lookup_asked="look-up not asked: same person? the two birth dates are far apart", hold=["same person? the two birth dates are far apart - for William: no paid look-up was bought and no plan was added on this step's own word"]),
        "pat9401": vrec(["vst7005", "vst7008"], no_birth_date=["vst7005", "vst7008"], hold=["no active plan: no paid look-up was bought - neither Claimocity nor the chart carries a real birth date to ask with (face sheet needed)"]),
        "pat9101": dict(vrec(["vst7001"]), decision="RELEASE")}
L8v, e8v = report_run("verify_holds", S7, ROWS8, verify=VER7)
_sp = has(top(L8v), "SAME PERSON?"); _nb = has(top(L8v), "NO BIRTH DATE ON EITHER SIDE")
check("7i a chart the insurance check held 'same person?' stands in ONE line at the top of the report - the chart and its visits, that no paid look-up was bought and no plan added, and what William's answer starts",
      lambda: e8v == "" and len(_sp) == 1 and "1 chart(s)" in _sp[0] and "pat9301 (vst7004)" in _sp[0] and "no paid look-up was bought" in _sp[0] and "--same-person" in _sp[0] and "pat9401" not in _sp[0] and "pat9101" not in _sp[0], lambda: (e8v, top(L8v)))
check("7j ... and a chart with no real birth date on either side in another: nothing can be asked without a face sheet",
      lambda: len(_nb) == 1 and "1 chart(s)" in _nb[0] and "pat9401 (vst7005 vst7008)" in _nb[0] and "face sheet" in _nb[0] and "pat9301" not in _nb[0], lambda: top(L8v))
L8w, e8w = report_run("verify_holds_none", S7, ROWS8, verify={"pat9101": dict(vrec(["vst7001"]), decision="RELEASE"), "pat9301": vrec(["vst7004"], same_person="yes", no_birth_date=None), "pat9401": vrec(["vst7005"], same_person=[])})
check("7k neither line when no chart carries such a hold (a value that is no list of visits, or an empty one, is none)", lambda: e8w == "" and not has(L8w, "SAME PERSON?") and not has(L8w, "NO BIRTH DATE ON EITHER SIDE"), lambda: (e8w, top(L8w)))
# a patient whose new chart waits for the next run (feed_identity.new_chart_waits): said in a plain line under 'Which chart' - no question for William
WAIT7 = {"stamp": S7, "identity_rule": FI.IDENTITY_RULE_VERSION, "counts": {"known from the patient map": 0, "looked up": 2, "new charts": 1, "for William": 0, "no chart": 1}, "repointed": [], "notes": [], "not_registered": ["20261129a.hl7"],
         "patients": [{"feed_ids": [FID(3)], "chart": "pat9301", "status": "MISSING", "new_chart": True, "rule": 9, "why": FI.WHY_NEW, "flags": [], "candidates": [], "evidence": [], "feed_dob": "real", "for_william": False},
                      {"feed_ids": [FID(4)], "chart": "", "status": "AMBIGUOUS", "new_chart": False, "rule": 0, "why": FI.WHY_SAME_RUN, "flags": [], "candidates": [], "evidence": [], "feed_dob": "real", "for_william": False}]}
L7w, e7w = report_run("identity_wait", S7, [vrow("pat9301", "vst7004", "11/29/2026", ["99309"])], identity=WAIT7)
check("7l a patient whose new chart waits for the next run (another Claimocity id of the same name got a new chart in this run) is said in a plain line with its Claimocity id - never as a question for William at the top; the file that is read again still is",
      lambda: e7w == "" and len(has(L7w, FID(4), FI.WHY_SAME_RUN)) == 1 and not has(top(L7w), FID(4)) and len(has(top(L7w), "NOT REGISTERED", "20261129a.hl7")) == 1 and has(L7w, "1 with NO chart"), lambda: (e7w, [l for l in L7w if FID(4) in l], top(L7w)))
# inpatient rehab at place of service 61 (the import's rows: stay, pos, pos_kind; the inspector step's held rows)
def rehab(pid, visit, dos, cpts, initial, sign="new admission 1-2 days after an acute stay", kept=False):
    return vrow(pid, visit, dos, cpts, fac="fac29" if kept else "fac67", pos="21" if kept else "61", pos_lines=["21" if kept else "61"] * len(cpts), pos_kind=["rehab-stay-kept-21" if kept else "rehab"] * len(cpts),
                pos_why="inpatient rehab stay: " + sign, stay={"kind": "rehab", "initial": initial, "sign": sign})
ROWS9 = [rehab("pat9601", "vst7101", "11/28/2026", ["99223"], "11/28/2026"), rehab("pat9601", "vst7102", "11/29/2026", ["99233"], "11/28/2026"), rehab("pat9602", "vst7103", "11/29/2026", ["99222", "99497"], "11/29/2026", sign="facility number"),
         rehab("pat9603", "vst7104", "11/29/2026", ["99232"], "11/20/2026", kept=True), vrow("pat9604", "vst7105", "11/29/2026", ["99223"], stay={"kind": "acute", "initial": "11/29/2026", "sign": ""})]
INSP9 = {"held": [{"visit": "7102", "pid": "pat9601", "why": "PLACE OF SERVICE 61: AdvancedMD's Claim Inspector questions rehab visit vst7102 (Pattern 4531: this code is not performed at the place of service on the charge, and a long tail of words that runs well past one hundred and twenty characters) - for William; nothing was changed", "pos61": True},
                  {"visit": "7200", "pid": "pat9700", "why": "nursing-facility code under the hospital building - which building was the patient in? (Pattern 4531)"},
                  {"visit": "7201", "pid": "pat9701", "why": "no admission anchor"}], "bypassed": [], "quality_removed": []}
L9, e9 = report_run("rehab", S7, ROWS9, inspector=INSP9)
_rs = L9[L9.index(next((l for l in L9 if l.startswith("## Inpatient rehab")), "")):] if any(l.startswith("## Inpatient rehab") for l in L9) else []
check("7i the digest gets a section 'Inpatient rehab': how many visits of a rehab stay went in at HCA REHAB / place of service 61 and how many were kept at 21 (the comparison group) - an acute stay is not counted",
      lambda: e9 == "" and len(has(_rs, "3 visit(s)", "place of service 61", "1 visit(s)", "kept at 21")) == 1, lambda: (e9, _rs[:5]))
check("7j each NEW rehab stay is named by chart and date with the sign it was known by - so William can say when it was a readmission to the acute hospital - once per stay, the follow-up visits not again",
      lambda: len(has(_rs, "New rehab stay", "pat9601 11/28/2026", "pat9602 11/29/2026", "facility number")) == 1 and "pat9603" not in " ".join(has(_rs, "New rehab stay")) and "vst7102" not in " ".join(has(_rs, "New rehab stay")), lambda: _rs)
check("7k a rehab visit the Claim Inspector questions stands at the top with the step's WHOLE sentence (the held rows above are cut at 120 characters), and so does the question about a nursing-facility code under the hospital building; another hold does not",
      lambda: len(has(top(L9), "PLACE OF SERVICE 61", "vst7102", "nothing was changed")) == 1 and len(has(top(L9), "vst7200", "pat9700", "which building was the patient in?")) == 1 and not has(top(L9), "vst7201"), lambda: top(L9))
L9b, e9b = report_run("rehab_none", S7, [vrow("pat9604", "vst7105", "11/29/2026", ["99223"], stay={"kind": "acute", "initial": "11/29/2026", "sign": ""})])
check("7l a batch without a rehab visit gets no such section", lambda: e9b == "" and not any(l.startswith("## Inpatient rehab") for l in L9b), lambda: (e9b, [l for l in L9b if l.startswith("##")]))

# ---- 8. one broken message never stops the feed (feed_parse_dft_1028.py as its own program, over invented files) ---------------------------------
import subprocess
PARSER = os.path.join(HELPERS, "feed_parse_dft_1028.py"); S8 = "20261201T1240Z"
def hl7(n, pid=True, cut=None, cpts=("99308",)):
    """one invented message: cut='FT1' ends its last charge line after eight fields, cut='DG1' its diagnosis line after two"""
    s = ["|".join(["MSH", "^~\\&", "FEED", "X", "X^1083300000", "", "", "20261201120000", "", "DFT^P03", "m%d" % n])]
    if pid: s.append("|".join(["PID", "1", "", FID(n), "", NAME(n).replace(", ", "^"), "", DOB(n)]))
    s.append("|".join(["PV1", "1", "I", "", "", "", "", "9^DOC^TOR"]))
    for i, c in enumerate(cpts):
        f = ["FT1", str(i + 1), "", "", "20261130", "20261201", "CG", "", "", "", "1"] + [""] * 8 + ["I10"] + [""] * 5 + [c + "^x"]
        s.append("|".join(f[:8]) if cut == "FT1" and i == len(cpts) - 1 else "|".join(f))
    s.append("DG1|1" if cut == "DG1" else "DG1|1||I10")
    return "\r".join(s) + "\r"
def parse_run(label, files):
    """the parser as the driver starts it (python3 -I, the workspace as its folder) -> (exit code, its printed lines, the parsed list or None, the unreadable register or None)"""
    w = os.path.join(TMP, "parse_" + label); src = os.path.join(w, "hl7", S8); os.makedirs(src); os.makedirs(os.path.join(w, "registers"))
    for fn, body in files.items(): open(os.path.join(src, fn), "w").write(body)
    r = subprocess.run([sys.executable, "-I", PARSER, src, "feed_parsed_%s.json" % S8], cwd=w, capture_output=True, text=True)
    def rd(p_):
        try: return json.load(open(os.path.join(w, p_)))
        except (OSError, ValueError): return None
    return r.returncode, (r.stdout + r.stderr).strip().splitlines(), rd("feed_parsed_%s.json" % S8), rd(os.path.join("registers", "feed_unreadable_%s.json" % S8)), w
F8a, F8b = "2026" + "1201aaaa.hl7", "2026" + "1202bbbb.hl7"
c8, o8, p8, u8, w8 = parse_run("broken", {F8a: hl7(1) + hl7(2, pid=False) + hl7(3, cpts=("99308", "99497")), F8b: hl7(4, cut="FT1", cpts=("99232", "99497")) + hl7(5, cut="DG1") + hl7(6)})
_by = lambda n: [m for m in (p8 or []) if m.get("pid") == FID(n)]
check("8a a file with a message without a patient line, one with a charge line cut short and one with a diagnosis line cut short: the parse ends without an error and writes its file (it used to stop - no visit of the day was entered)",
      lambda: c8 == 0 and isinstance(p8, list) and len(p8) == 5, lambda: (c8, o8[-3:]))
check("8b every other message is read whole, as before",
      lambda: [[c["cpt"] for c in _by(n)[0]["FT1"]] for n in (1, 3, 6)] == [["99308"], ["99308", "99497"], ["99308"]] and all(_by(n)[0]["name"] == NAME(n) and _by(n)[0]["dob"] == DOB(n) and _by(n)[0]["file"] == f_[:8] for n, f_ in ((1, F8a), (3, F8a), (6, F8b))),
      lambda: [(m.get("pid"), [c.get("cpt") for c in m.get("FT1") or []]) for m in p8 or []])
check("8c the message without a patient line is nobody's visit: it is not handed on at all (the driver and every later step read a Claimocity id from each record), and every record that is handed on has one",
      lambda: all("pid" in m and "name" in m and "dob" in m for m in p8) and sorted(m["pid"] for m in p8) == sorted(FID(n) for n in (1, 3, 4, 5, 6)), lambda: [sorted(m) for m in p8 or []])
check("8d NOTHING is entered from a message with a line cut short: it keeps its patient and carries no charge line at all - not even the lines that could be read (the import's own 'feed message without a charge line' row then says it)",
      lambda: [m["FT1"] for m in _by(4) + _by(5)] == [[], []] and [m.get("unreadable") for m in _by(4) + _by(5)] == ["a line of the message is cut short"] * 2, lambda: [(m.get("FT1"), m.get("unreadable")) for m in _by(4) + _by(5)])
check("8e registers/feed_unreadable_<stamp>.json names each of the three by file date and message number, in fixed words - never a name, a birth date or a Claimocity id",
      lambda: u8["stamp"] == S8 and sorted((x["file"], x["message"], x["why"]) for x in u8["messages"]) == [(F8a[:8], 2, "no patient line"), (F8b[:8], 1, "a line of the message is cut short"), (F8b[:8], 2, "a line of the message is cut short")]
              and not any(s_ in json.dumps(u8) for s_ in secrets(1, 2, 3, 4, 5, 6) + [FID(n) for n in range(1, 7)]), lambda: u8)
check("8f the parse's LAST line says it, short enough for the driver's line of a step: how many, that nothing of them was entered, TOP OF THE REPORT - and no name or birth date is printed by the parse at all",
      lambda: o8[-1].startswith("UNREADABLE: 3 feed message(s)") and "TOP OF THE REPORT" in o8[-1][:160] and "registers/feed_unreadable_%s.json" % S8 in o8[-1] and not any(s_ in "\n".join(o8) for s_ in secrets(1, 2, 3, 4, 5, 6)), lambda: o8[-2:])
c8g, o8g, p8g, u8g, w8g = parse_run("good", {F8a: hl7(1) + hl7(3)})
check("8g a batch whose messages can all be read: no such line and no such register",
      lambda: c8g == 0 and len(p8g) == 2 and u8g is None and not any("UNREADABLE" in l for l in o8g), lambda: (c8g, u8g, o8g[-2:]))
c8s, o8s, p8s, u8s, w8s = parse_run("stale", {F8a: hl7(1) + hl7(2, pid=False)})
open(os.path.join(w8s, "hl7", S8, F8a), "w").write(hl7(1))      # the file is sent again, whole
r8s = subprocess.run([sys.executable, "-I", PARSER, os.path.join(w8s, "hl7", S8), "feed_parsed_%s.json" % S8], cwd=w8s, capture_output=True, text=True)
check("8h a second parse of the same batch that finds nothing broken takes the register of the first away (a re-read after the file was sent again)",
      lambda: u8s is not None and r8s.returncode == 0 and not os.path.exists(os.path.join(w8s, "registers", "feed_unreadable_%s.json" % S8)), lambda: (u8s, r8s.returncode, (r8s.stdout + r8s.stderr)[-300:]))
c8n, o8n, p8n, u8n, w8n = parse_run("noreg", {F8a: hl7(1) + hl7(2, pid=False)}); shutil.rmtree(os.path.join(w8n, "registers"))
if os.path.exists(os.path.join(w8n, "feed_parsed_%s.json" % S8)): os.remove(os.path.join(w8n, "feed_parsed_%s.json" % S8))
r8n = subprocess.run([sys.executable, "-I", PARSER, os.path.join(w8n, "hl7", S8), "feed_parsed_%s.json" % S8], cwd=w8n, capture_output=True, text=True)
check("8i started by hand in a folder without registers/: the parse still ends well and still says it in its last line (it makes no folder)",
      lambda: r8n.returncode == 0 and os.path.exists(os.path.join(w8n, "feed_parsed_%s.json" % S8)) and not os.path.exists(os.path.join(w8n, "registers")) and r8n.stdout.strip().splitlines()[-1].startswith("UNREADABLE: 1 feed message(s)"), lambda: (r8n.returncode, (r8n.stdout + r8n.stderr)[-300:]))
L8, e8 = report_run("unreadable", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], unreadable={"stamp": S7, "messages": [{"file": "20261201", "message": 2, "why": "no patient line"}, {"file": "20261202", "message": 1, "why": "a line of the message is cut short"}]})
check("8j the digest puts it at the top: how many feed messages could not be read, which file and which message, that their visits are NOT entered and what to do",
      lambda: e8 == "" and len(has(top(L8), "2 feed message(s) could not be read", "20261201 message 2 (no patient line)", "20261202 message 1 (a line of the message is cut short)", "NOT entered", "Claimocity")) == 1, lambda: (e8, top(L8)))
L8b, e8b = report_run("unreadable_words", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], unreadable={"stamp": S7, "messages": [{"file": NAME(1), "message": DOB(1), "why": NAME(2)}, {"file": "20261202", "message": 3, "why": "a line of the message is cut short"}]})
check("8k a register row that is not a file date, a number and the fixed words is counted but never copied (a name can never reach the digest through it)",
      lambda: e8b == "" and len(has(top(L8b), "2 feed message(s) could not be read", "20261202 message 3")) == 1 and not any(s_ in "\n".join(L8b) for s_ in secrets(1, 2)), lambda: (e8b, top(L8b)))
L8c, e8c = report_run("unreadable_bad", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], unreadable="{ not json")
check("8l a register that cannot be read is said at the top too - never passed over in silence", lambda: e8c == "" and len(has(top(L8c), "feed_unreadable_%s.json" % S7, "could not be read")) == 1, lambda: (e8c, top(L8c)))
L8d, e8d = report_run("unreadable_none", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])])
check("8m a batch without that register gets no such line", lambda: e8d == "" and not has(L8d, "could not be read"), lambda: (e8d, top(L8d)))

# ---- 6. the privacy gate leaves this file and the driver alone --------------------------------------------------------------------------------------
sys.path.insert(0, os.path.join(ROOT, "tools", "mirror")); import phi_gate as _pg
for rel in ("tools/selftest/test_feed_driver.py", "scripts/helpers/claimocity_ingest.py", "scripts/helpers/claimocity_report.py", "scripts/helpers/feed_parse_dft_1028.py"):
    _t = open(os.path.join(ROOT, rel)).read(); _r = _pg.redact(_t, {}, code=True)
    check("6 the privacy gate's tree rules leave %s exactly as it is (every invented value is put together at run time)" % rel, _r == _t, [(a, b) for a, b in zip(_t.splitlines(), _r.splitlines()) if a != b][:2])

print("\n%d check(s): %d ok, %d FAIL" % (OK[0] + len(FAILS), OK[0], len(FAILS)))
sys.exit(1 if FAILS else 0)
