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
#   9 to 16 NO VISIT OF THE FEED IS LOST WITHOUT A WORD (11/25/2026, the independent verification of the feed part - each section says what it
#     found). A feed file is not registered while a visit of it is not on a chart: a message that could not be read (9), a visit AdvancedMD
#     refused at entry (15); the download step fetches a file again whose copy in the bucket has another size than the one that was read
#     (10); a message without a Claimocity id is counted by file date and message number and keeps its file back (11); a DRY ingest leaves
#     the patient map alone (12); every line of the driver's own that is for William reaches the identity register and the top of the
#     digest (13), also the question about a new chart whose run was cut before its digest (14); the digest names EVERY Claimocity id of a
#     row and prints only chart ids and visit ids from the insurance check's file (13); the reconciliation never says 'already in AMD' for
#     a visit that was not entered (16). Sections 9 to 15 run the REAL parser, digest and reconciliation around the driver.
# Usage: python3 tools/selftest/test_feed_driver.py     (exit 1 on any FAIL)
import os, sys, io, re, json, types, shutil, tempfile, atexit, contextlib, importlib.util, subprocess
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

def sandbox(label, files, ws_map=None, main_map=None, main_yes={}):
    """a throwaway workspace with its inbox and registers, and a throwaway clone whose scripts/helpers holds the repository's real feed helpers
    (so the driver's own make_current finds every helper current) -> (workspace, the clone's scripts/helpers, the clone's registers folder).
    main_yes: the clone's feed_same_person.json - an empty object as it stands on main; None = the clone holds no such file; a text = written as it is"""
    w = os.path.join(TMP, label, "ws"); r = os.path.join(TMP, label, "repo", "scripts", "helpers"); mreg = os.path.join(TMP, label, "repo", "practices", "ehpa", "registers")
    for d in (os.path.join(w, "inbox", "claimocity"), os.path.join(w, "registers"), r, mreg): os.makedirs(d)
    for f in HC.FEED_HELPERS:
        if os.path.exists(os.path.join(HELPERS, f)): shutil.copy2(os.path.join(HELPERS, f), os.path.join(r, f)); shutil.copy2(os.path.join(HELPERS, f), os.path.join(w, f))
    for f in files: open(os.path.join(w, "inbox", "claimocity", f), "w").write("MSH|invented %s\n" % f)
    if ws_map is not None: json.dump(ws_map, open(os.path.join(w, "registers", "claimocity_patient_map.json"), "w"))
    if main_map is not None: open(os.path.join(mreg, "claimocity_patient_map.json"), "w").write(main_map if isinstance(main_map, str) else json.dumps(main_map))
    if main_yes is not None: open(os.path.join(mreg, "feed_same_person.json"), "w").write(main_yes if isinstance(main_yes, str) else json.dumps(main_yes))
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
            if "--all" in cmd: json.dump({"created": created or [], "skipped": [], "failed": []}, open(os.path.join(w, "registers", "feed_import_%s.json" % stamp), "w"))      # like the real import: a dry run writes no register
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
def yes_case(label, ws_doc, main_doc, clone=True, files=("20261126a.hl7",), live=True):
    """one start of the driver: the workspace's copy of the file as the state bundle restored it (ws_doc), the repository's file (main_doc: None = the clone holds none,
    a text = written as it is); clone=False = there is no clone at all -> (the driver's error, its SAME PERSON FILE lines, the workspace's copy afterwards, the notes of its identity register)"""
    w_, r_, mreg_ = sandbox(label, list(files), ws_map={FID(1): "pat9001"}, main_yes=main_doc)
    if ws_doc is not None: json.dump(ws_doc, open(os.path.join(w_, "registers", "feed_same_person.json"), "w"))
    if not clone: shutil.rmtree(os.path.join(os.path.dirname(os.path.dirname(r_)), "practices"))
    o_, calls_, e_ = driver_run(w_, r_, ARGS(S1, live=live), steps(w_, S1, [msg(1, "20261126")], {}))
    return e_, [l for l in o_.splitlines() if l.startswith("SAME PERSON FILE:")], rd(w_, "registers", "feed_same_person.json"), [n for n in (ident(w_, S1) or {}).get("notes") or [] if n.startswith("SAME PERSON FILE:")]
YES_M = {"pat9001": {"feed_ids": [FID(1)], "approved_by": "William 11/26/2026 (board)"}}; YES_W = {"pat9777": {"feed_ids": [FID(2)], "approved_by": "William 11/20/2026"}}
check("1g William's standing word 'same person' (registers/feed_same_person.json): the repository's file is copied into the workspace, whole, at every start - an entry taken out on main does not come back from a restored workspace",
      lambda: yes_case("yes_main", YES_W, YES_M)[:3] == ("", [], YES_M) and yes_case("yes_new", None, YES_M)[:3] == ("", [], YES_M) and yes_case("yes_empty", YES_W, {})[:3] == ("", [], {}),
      lambda: (yes_case("yes_main_x", YES_W, YES_M), yes_case("yes_empty_x", YES_W, {})))
_twice = '{"pat9001": {"feed_ids": ["%s"], "approved_by": "William 11/26/2026 (board)"},\n "pat9001": {"feed_ids": ["%s"], "approved_by": "William 11/27/2026 (board)"}}' % (FID(1), FID(2))
_tw = sandbox("yes_twice", ["20261126a.hl7"], ws_map={FID(1): "pat9001"}, main_yes=_twice); _two, _tcalls, _te = driver_run(_tw[0], _tw[1], ARGS(S1), steps(_tw[0], S1, [msg(1, "20261126")], {}))
check("1g2 ... the repository's file goes over as its TEXT: a chart the file names twice reaches the workspace with BOTH entries (written again from the parsed object only the last one arrived - before the insurance check, which reads both and says what does not count, ever saw it)",
      lambda: _te == "" and open(os.path.join(_tw[0], "registers", "feed_same_person.json")).read() == _twice, lambda: (_te, open(os.path.join(_tw[0], "registers", "feed_same_person.json")).read()[:200]))
# 11/25/2026 (the verification of William's standing word): with the repository's file MISSING the workspace's older copy was left as it was, without a word, and with the file
# unreadable it was kept and only said - an entry William had taken out on main still freed its chart: a paid look-up was bought and a plan added on a word he had taken back.
# The file's home is main; when main says nothing, nobody's standing word counts in that run.
def _emptied(c, how): return c[0] == "" and c[2] == {} and len(c[1]) == 1 and how in c[1][0] and "nobody's standing word counts in this run" in c[1][0] and c[1][0].endswith("TOP OF THE REPORT")
check("1h CHANGED (until then the workspace's copy stayed and counted): the clone is there and holds NO such file - the workspace's copy is emptied, so nobody's standing word counts in that run, and ONE line says so for the top of the report; the ingest goes on",
      lambda: _emptied(yes_case("yes_nomain", YES_W, None), "is missing"), lambda: yes_case("yes_nomain_x", YES_W, None))
check("1h2 CHANGED the same when the repository's file cannot be read or is no JSON object (half written, the conflict markers of a pull, empty, a list): the copy is emptied and the line says what is wrong with the file - no longer 'this workspace's copy is used as it is'",
      lambda: all(_emptied(yes_case("yes_bad%d" % i, YES_W, t), "could not be read") for i, t in enumerate(["{ half", "<" * 7 + " ours\n{}\n" + "=" * 7 + "\n{}\n" + ">" * 7 + " theirs\n", "", json.dumps(["pat1"]), json.dumps("x")])),
      lambda: [yes_case("yes_badx%d" % i, YES_W, t) for i, t in enumerate(["{ half", ""])])
check("1h3 ... also on a quiet day (no new file) and in a dry run - and a live run with a file carries the line to its identity register, from where the digest prints it at the top",
      lambda: _emptied(yes_case("yes_quiet", YES_W, None, files=()), "is missing") and _emptied(yes_case("yes_dry", YES_W, "{ half", live=False), "could not be read") and len(yes_case("yes_note", YES_W, None)[3]) == 1,
      lambda: (yes_case("yes_quiet_x", YES_W, None, files=()), yes_case("yes_note_x", YES_W, None)))
check("1h4 only with NO clone at all (a run without GitHub) does the workspace's copy stay and count - nothing else can be known there; a plain line says how many charts it frees and that a word taken back on main is not known to this run (no line when the copy frees nobody)",
      lambda: (lambda c, d: c[0] == "" and c[2] == YES_W and len(c[1]) == 1 and "no repository clone" in c[1][0] and "1 chart(s)" in c[1][0] and "TOP OF THE REPORT" not in c[1][0] and d[:3] == ("", [], {}))(
          yes_case("yes_noclone", YES_W, None, clone=False), yes_case("yes_noclone_empty", {}, None, clone=False)), lambda: yes_case("yes_noclone_x", YES_W, None, clone=False))

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
_noline = dict(msg(3, "20261127"), FT1=[])
o, calls, e = driver_run(w, r, ARGS(S3), steps(w, S3, [msg(1, "20261127"), _noline, msg(1, "20261128")], {KEY(3): answer(9, "", ids=[FID(3)], why=FI.WHY_NEW)}, newcharts={KEY(3): "pat9301"}))
check("3e2 CHANGED (its second half is 3e3 now) a record WITHOUT A CHARGE LINE is no visit: the no-chart rule does not keep its file back (what keeps the file of a broken message back is the parse step's count - section 9)",
      lambda: e == "" and sorted(ingest(w).get("files") or {}) == ["20261127a.hl7", "20261128a.hl7"] and "NOT REGISTERED" not in o, lambda: (e, o[-500:], sorted(ingest(w).get("files") or {})))
check("3e2b ... and nobody is looked up, and no chart is made, for a patient whose only message carries nothing to enter (11/25/2026: a message the file ended in - its patient line may be cut short too - went to the match step, "
      "and a new chart could be made from it; the patient map then sent that patient's real visits to that chart)",
      lambda: e == "" and "claimocity_match.py" not in calls and "claimocity_newcharts.py" not in calls and pm(w) == {FID(1): "pat9101"} and match(w, S3).get(KEY(3)) is None, lambda: (e, calls, pm(w), match(w, S3).get(KEY(3))))
w, r, mreg = sandbox("nochart_noid", ["20261127a.hl7", "20261128a.hl7"], ws_map={FID(1): "pat9101"})
_noid = dict(msg(1, "20261128"), pid=""); _nullid = dict(msg(1, "20261128"), pid=None)      # a charge line and NO Claimocity id, handed on by a parse step that did not count it (an older copy of the parser)
o, calls, e = driver_run(w, r, ARGS(S3), steps(w, S3, [msg(1, "20261127"), _noid, _nullid], {KEY(1): answer(0, "", status="AMBIGUOUS", will=True, ids=[], why=FI.WHY_NO_ID)}))
_l = next((l for l in o.splitlines() if l.startswith("NOT REGISTERED:") and "no Claimocity id" in l), "")
check("3e3 CHANGED (until 11/25/2026 such a file was registered as done and the visit was never entered - the verification's finding): a record with a charge line and NO Claimocity id is a visit nobody can enter - its file is NOT registered, "
      "ONE line for the top of the report says how many such messages and in which file, the RESULT line counts them, and the patient map learns no empty id",
      lambda: e == "" and sorted(ingest(w).get("files") or {}) == ["20261127a.hl7"] and "20261128a.hl7" in _l and "2 message(s)" in _l and "file 20261128" in _l and _l.endswith("TOP OF THE REPORT")
      and re.search(r"RESULT stamp %s: files 2, messages 3, .*2 message\(s\) could not be read.*1 file\(s\) NOT registered" % S3, o) is not None and pm(w) == {FID(1): "pat9101"},
      lambda: (e, _l, o[-600:], sorted(ingest(w).get("files") or {}), pm(w)))
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
def report_run(label, stamp, created, identity=None, inspector=None, newcharts=None, unreadable=None, verify=None, failed=None):
    """the report helper over ONE invented batch -> (its digest's lines, its error)"""
    d = os.path.join(TMP, "report_" + label); os.makedirs(os.path.join(d, "registers")); os.makedirs(os.path.join(d, "outbox"))
    json.dump({"created": created, "skipped": [], "failed": failed or []}, open(os.path.join(d, "registers", "feed_import_%s.json" % stamp), "w"))
    if identity is not None: open(os.path.join(d, "registers", "feed_identity_%s.json" % stamp), "w").write(identity if isinstance(identity, str) else json.dumps(identity))
    if inspector is not None: json.dump(inspector, open(os.path.join(d, "registers", "feed_inspector_%s.json" % stamp), "w"))
    if newcharts is not None: json.dump(newcharts, open(os.path.join(d, "registers", "feed_newcharts_%s.json" % stamp), "w"))
    if unreadable is not None: open(os.path.join(d, "registers", "feed_unreadable_%s.json" % stamp), "w").write(unreadable if isinstance(unreadable, str) else json.dumps(unreadable))
    if verify is not None: json.dump(verify, open(os.path.join(d, "feed_verify_%s.json" % stamp), "w"))      # the insurance check's own file, in the workspace (the digest writes the register copy)
    shutil.copy2(os.path.join(HELPERS, "feed_identity.py"), os.path.join(d, "feed_identity.py"))
    return digest_of(d, stamp)
def digest_of(d, stamp):
    """the report helper inside this process, over a folder that already holds its registers (a throwaway batch, or the workspace a driver run left) -> (its digest's lines, its error)"""
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
# 11/25/2026 (round 2 of the second review): the sentence 'neither Claimocity nor the chart carries a real birth date' was untrue of a chart whose feed patient came with two DIFFERENT real
# birth dates (the insurance check holds that chart under the same record key). The record now says which case it is - no_birth_date_case, a fixed word - and the digest has a true sentence
# for each; a record without the word (an older one), or with anything else in its place, reads as before, and what stands in that field is never printed
VER7c = {"pat9401": vrec(["vst7005", "vst7008"], no_birth_date=["vst7005", "vst7008"], no_birth_date_case="neither side"), "pat9402": vrec(["vst7009", "vst7010"], no_birth_date=["vst7009", "vst7010"], no_birth_date_case="two dates"),
         "pat9403": vrec(["vst7011"], no_birth_date=["vst7011"]), "pat9404": vrec(["vst7012"], no_birth_date=["vst7012"], no_birth_date_case=NAME(3)), "pat9405": vrec(["vst7013"], no_birth_date=["vst7013"], no_birth_date_case=["two dates"]),
         NAME(2).replace(", ", ","): vrec(["vst7014"], no_birth_date=["vst7014"], no_birth_date_case="two dates")}
L8x, e8x = report_run("verify_holds_case", S7, ROWS8, verify=VER7c); _nb = has(top(L8x), "NO BIRTH DATE ON EITHER SIDE"); _tw = has(top(L8x), "TWO BIRTH DATES FROM CLAIMOCITY")
check("7k2 a chart whose feed patient came with TWO different real birth dates while the chart carries none (the record's word 'two dates') has a line of its own at the top - it says Claimocity sent two and nobody knows which to ask with, never "
      "'neither Claimocity nor the chart carries a real birth date' - and is not counted in the other line",
      lambda: e8x == "" and len(_tw) == 1 and "1 chart(s)" in _tw[0] and "pat9402 (vst7009 vst7010)" in _tw[0] and "two different real birth dates" in _tw[0] and "face sheet" in _tw[0] and "no paid look-up was bought" in _tw[0]
      and "neither Claimocity nor the chart" not in _tw[0] and not any(p_ in _tw[0] for p_ in ("pat9401", "pat9403", "pat9404", "pat9405")) and len(_nb) == 1 and "pat9402" not in _nb[0], lambda: (e8x, _tw, _nb))
check("7k3 ... a record that says 'neither side', one without the word (an older record) and one with anything else in its place (a text that is not the fixed word, a list) read as before - the line NO BIRTH DATE ON EITHER SIDE; "
      "a record whose key is no chart id is counted there as not shown, whatever its word; and nothing that stands in that field reaches a line at the top",
      lambda: len(_nb) == 1 and "4 chart(s)" in _nb[0] and all(p_ in _nb[0] for p_ in ("pat9401 (vst7005 vst7008)", "pat9403 (vst7011)", "pat9404 (vst7012)", "pat9405 (vst7013)")) and "neither Claimocity nor the chart carries a real birth date" in _nb[0]
      and "1 record(s) not shown" in _nb[0] and "not shown" not in _tw[0] and not any(s_ in "\n".join(top(L8x)) for s_ in secrets(2, 3)) and not any(s_ in "\n".join(L8x) for s_ in secrets(3)), lambda: (e8x, _nb, _tw))
L8y, e8y = report_run("verify_holds_case_only", S7, ROWS8, verify={"pat9402": vrec(["vst7009"], no_birth_date=["vst7009"], no_birth_date_case="two dates")})
check("7k4 ... and when every such chart is of the 'two dates' kind the line NO BIRTH DATE ON EITHER SIDE is not printed at all",
      lambda: e8y == "" and len(has(top(L8y), "TWO BIRTH DATES FROM CLAIMOCITY", "1 chart(s)", "pat9402 (vst7009)")) == 1 and not has(L8y, "NO BIRTH DATE ON EITHER SIDE") and not has(L8y, "neither Claimocity nor the chart"), lambda: (e8y, top(L8y)))
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
      lambda: len(has(_rs, "New rehab stay", "pat9601 11/28/2026", "pat9602 11/29/2026", "facility number")) == 1 and "pat9603" not in " ".join(has(_rs, "New rehab stay")) and "pat9601 11/29/2026" not in " ".join(has(_rs, "New rehab stay")), lambda: _rs)
check("7k a rehab visit the Claim Inspector questions stands at the top with the step's WHOLE sentence (the held rows above are cut at 120 characters), and so does the question about a nursing-facility code under the hospital building; another hold does not",
      lambda: len(has(top(L9), "PLACE OF SERVICE 61", "vst7102", "nothing was changed")) == 1 and len(has(top(L9), "vst7200", "pat9700", "which building was the patient in?")) == 1 and not has(top(L9), "vst7201"), lambda: top(L9))
L9b, e9b = report_run("rehab_none", S7, [vrow("pat9604", "vst7105", "11/29/2026", ["99223"], stay={"kind": "acute", "initial": "11/29/2026", "sign": ""})])
check("7l a batch without a rehab visit gets no such section", lambda: e9b == "" and not any(l.startswith("## Inpatient rehab") for l in L9b), lambda: (e9b, [l for l in L9b if l.startswith("##")]))
# 11/25/2026 (the second round of the verification - its finding about the digest): the rehab lines go by what AdvancedMD STORED where the import read it back (the row's
# pos_stored, one per charge line, read as pos61_monitor.py reads it). Until then they went by what was sent: a rehab visit stored at 21 stood here as 'entered at HCA REHAB,
# place of service 61' and its stay was named as a new rehab stay, while the import and the monitor of the same run said that no visit is at 61.
ROWS9S = [dict(rehab("pat9611", "vst7111", "11/28/2026", ["99223"], "11/28/2026"), pos_stored=["21"]), dict(rehab("pat9611", "vst7112", "11/29/2026", ["99233"], "11/28/2026"), pos_stored=["61"]),
          dict(rehab("pat9612", "vst7113", "11/29/2026", ["99223", "99497"], "11/29/2026"), pos_stored=["61", "21"]), rehab("pat9613", "vst7114", "11/29/2026", ["99223"], "11/29/2026"),
          dict(rehab("pat9614", "vst7115", "11/29/2026", ["99223"], "11/29/2026"), pos_stored=["31"]), dict(rehab("pat9615", "vst7116", "11/29/2026", ["99223"], "11/29/2026"), pos_stored=[]),
          rehab("pat9617", "vst7118", "11/29/2026", ["99232"], "11/20/2026", kept=True)]
L9s, e9s = report_run("rehab_stored", S7, ROWS9S)
_rs9 = L9s[L9s.index(next((l for l in L9s if l.startswith("## Inpatient rehab")), "")):] if any(l.startswith("## Inpatient rehab") for l in L9s) else []
check("7m a rehab visit counts as entered at HCA REHAB / 61 by what AdvancedMD STORED: the read-back holds 61 on one of its lines, or there is no read-back (none, or an empty one - then what was sent counts); a visit sent at 61 and stored elsewhere is NOT one of them - the line counts it apart",
      lambda: e9s == "" and len(has(_rs9, "- 4 visit(s) of a rehab stay entered at HCA REHAB, place of service 61 (4 chart(s)); 1 visit(s) of a rehab stay that began at 21 kept at 21 - the comparison group (1 chart(s))", "2 visit(s) sent at 61")) == 1, lambda: (e9s, _rs9[:5]))
check("7n ... such a visit stands at the TOP OF THE REPORT with its chart, day, code and visit and the place that was stored ('sent at 61, stored at 21') - once, in one line for all of them - and it names no new rehab stay: a stay is named only from an initial visit that stands at 61",
      lambda: len(has(top(_rs9), "sent at 61, stored at")) == 1 and len(has(top(_rs9), "pat9611 11/28/2026 99223 (vst7111) sent at 61, stored at 21", "pat9614 11/29/2026 99223 (vst7115) sent at 61, stored at 31", "NOT at place of service 61")) == 1
      and not has(top(_rs9), "vst7112") and not has(top(_rs9), "vst7113") and len(has(_rs9, "New rehab stay", "pat9612 11/29/2026", "pat9613 11/29/2026", "pat9615 11/29/2026")) == 1
      and "pat9611" not in " ".join(has(_rs9, "New rehab stay")) and "pat9614" not in " ".join(has(_rs9, "New rehab stay")), lambda: _rs9)
L9t, e9t = report_run("rehab_stored_only", S7, [dict(rehab("pat9611", "vst7111", "11/28/2026", ["99223"], "11/28/2026"), pos_stored=["21"])])
check("7o a batch whose only rehab visit was sent at 61 and stored at 21 still gets the section - 0 visits entered at 61, the line at the top, no new rehab stay; and a batch whose visits were read back as sent says nothing of the kind (the lines of 7i and 7j are word for word what they were)",
      lambda: e9t == "" and len(has(L9t, "- 0 visit(s) of a rehab stay entered at HCA REHAB, place of service 61 (0 chart(s)); 0 visit(s)", "1 visit(s) sent at 61")) == 1 and len(has(top(L9t), "pat9611 11/28/2026 99223 (vst7111) sent at 61, stored at 21")) == 1
      and not has(L9t, "New rehab stay") and not has(L9, "sent at 61, stored at") and len(has(_rs, "- 3 visit(s) of a rehab stay entered at HCA REHAB, place of service 61 (2 chart(s)); 1 visit(s) of a rehab stay that began at 21 kept at 21 - the comparison group (1 chart(s)).")) == 1, lambda: (e9t, [l for l in L9t if "rehab" in l.lower()], _rs[:3]))

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

# 11/25/2026 (the verification of the change above): four kinds of message that cannot be entered went on WITHOUT a word and their file was registered as done - a
# charge line that ends before its code (only a line of 19 fields or fewer counted as cut short), a code the file ended in, a message the file ended in before its
# charge line, and a patient line with an EMPTY Claimocity id. Each is counted now, by file date and message number, in the parse step's fixed words.
def ft1(code, keep=26, at25=None):
    """one invented charge line: its first `keep` fields (26 = a whole line); at25 = what stands in its code field instead of code^x (an empty code, a code the file ended in)"""
    f = ["FT1", "1", "", "", "20261130", "20261201", "CG", "", "", "", "1"] + [""] * 8 + ["I10"] + [""] * 5 + [code + "^x" if at25 is None else at25]
    return "|".join(f[:keep])
def hl7x(n, fid=None, lines=None, name=True):
    """one invented message with these charge lines (the text of each; none = one whole line); fid = the Claimocity id of its patient line ("" = an EMPTY one). lines=[] = it ends after its PV1 line"""
    s = ["|".join(["MSH", "^~\\&", "FEED", "X", "X^1083300000", "", "", "20261201120000", "", "DFT^P03", "x%d" % n]), "|".join(["PID", "1", "", FID(n) if fid is None else fid, "", NAME(n).replace(", ", "^") if name else "", "", DOB(n)]),
         "|".join(["PV1", "1", "I", "", "", "", "", "9^DOC^TOR"])]
    return "\r".join(s + ([ft1("99308")] if lines is None else list(lines))) + "\r"
def ends_in(text): return text[:-1]      # the file ENDS in the last line of this text: no line end behind it
W_CUT, W_CODE, W_NOCHARGE, W_NOID = "a line of the message is cut short", "a charge line carries no whole procedure code", "no charge line", "the patient line carries no Claimocity id"
KINDS = [("after field 19 of its charge line", ends_in(hl7x(2, lines=[ft1("99232", keep=20)])), W_CUT), ("after field 24 of its charge line", ends_in(hl7x(2, lines=[ft1("99232", keep=25)])), W_CUT),
         ("inside the code of its charge line", ends_in(hl7x(2, lines=[ft1("99232", at25="992")])), W_CODE), ("a whole charge line with an EMPTY code", hl7x(2, lines=[ft1("99232", at25="")]), W_CODE),
         ("after the PV1 line, before any charge line", ends_in(hl7x(2, lines=[])), W_NOCHARGE), ("inside the patient line, in the name", ends_in("\r".join(hl7x(2, lines=[]).split("\r")[:2])[:-12]), W_NOCHARGE),
         ("a whole second charge line beside one that is cut after field 21", ends_in(hl7x(2, lines=[ft1("99232"), ft1("99497", keep=22)])), W_CUT)]
FK = ["2026" + "12%02dkind.hl7" % (10 + i) for i in range(len(KINDS))]
c8k, o8k, p8k, u8k, w8k = parse_run("kinds", {FK[i]: hl7(1) + body for i, (_what, body, _why) in enumerate(KINDS)})
_cut = lambda p_: [m for m in (p_ or []) if m.get("pid") != FID(1)]
check("8n a file that ends in the middle of its last message - after field 19 or 24 of the charge line, inside the code, before the charge line, inside the patient line - and a charge line with an empty code: "
      "the parse ends without an error and EVERY such message is counted by file date and message number (until 11/25/2026 only a charge line of 19 fields or fewer was; the others went on with an empty or cut code, or with no charge line, and their file was registered)",
      lambda: c8k == 0 and sorted((x["file"], x["message"], x["why"]) for x in u8k["messages"]) == sorted((FK[i][:8], 2, why) for i, (_w, _b, why) in enumerate(KINDS)), lambda: (c8k, u8k, o8k[-2:]))
check("8o ... NOTHING of such a message is handed on to be entered: no charge line at all - not the cut one, not a whole one beside it - and the record says why; the whole message before it in each file is read as before",
      lambda: len(_cut(p8k)) == len(KINDS) and all(m["FT1"] == [] and m.get("unreadable") in (W_CUT, W_CODE, W_NOCHARGE) for m in _cut(p8k)) and [m["FT1"][0]["cpt"] for m in p8k if m.get("pid") == FID(1)] == ["99308"] * len(KINDS),
      lambda: [(m.get("pid"), m.get("FT1"), m.get("unreadable")) for m in p8k or []])
check("8p the parse's last line still starts UNREADABLE, says TOP OF THE REPORT within the driver's 160 characters, and no longer tells a run to 'ask Claimocity to send the file again' as the whole remedy (a file sent again under its own name was never read)",
      lambda: o8k[-1].startswith("UNREADABLE: %d feed message(s)" % len(KINDS)) and "TOP OF THE REPORT" in o8k[-1][:160] and "ask Claimocity to send the file again" not in o8k[-1], lambda: o8k[-1][:300])
FN8 = "2026" + "1220noid.hl7"
c8n, o8n, p8n, u8n, w8n = parse_run("noid", {FN8: hl7(1) + hl7x(2, fid="") + hl7x(3, fid="  ") + hl7(4)})
check("8q a patient line with an EMPTY Claimocity id (a name, a birth date and a charge line are there): the message is counted by file date and message number in fixed words - nobody can say by id whose visit it is, and no step enters a visit by the name alone",
      lambda: c8n == 0 and sorted((x["file"], x["message"], x["why"]) for x in u8n["messages"]) == [(FN8[:8], 2, W_NOID), (FN8[:8], 3, W_NOID)] and not any(s_ in json.dumps(u8n) for s_ in secrets(1, 2, 3, 4)), lambda: (c8n, u8n))
check("8r ... its record is still handed on as it came - the empty id, the name and date, its charge line - and marked (the match step weighs a name and date that came without an id, and the reconciliation lists the visit as not entered); the messages around it are untouched",
      lambda: [(m["pid"].strip(), len(m["FT1"]), m.get("unreadable")) for m in p8n] == [(FID(1), 1, None), ("", 1, W_NOID), ("", 1, W_NOID), (FID(4), 1, None)], lambda: [(m.get("pid"), m.get("FT1"), m.get("unreadable")) for m in p8n or []])
_psrc = open(PARSER).read(); _words = lambda src, names: [eval(re.search(r"^%s\s*=\s*(.+?)\s*(?:#.*)?$" % re.escape(n_), src, re.M).group(1)) for n_ in names]
check("8s the fixed words of a message that cannot be entered are the same five in the parser, the driver and the digest (the driver holds a file for them, the digest prints only them)",
      lambda: (lambda p_, d_, r_: len(p_) == 5 and p_ == d_ == r_ and W_CUT in p_ and W_CODE in p_ and W_NOCHARGE in p_ and W_NOID in p_)(
          sorted(x for t_ in _words(_psrc, ["NO_PATIENT, CUT_SHORT", "NO_CODE, NO_CHARGE, NO_ID"]) for x in t_), sorted(_words(DSRC, ["UNREADABLE_WORDS"])[0]), sorted(_words(RSRC, ["_UW"])[0])),
      lambda: (_words(_psrc, ["NO_PATIENT, CUT_SHORT"]), re.findall(r"^(?:UNREADABLE_WORDS|_UW)\s*=.*$", DSRC + "\n" + RSRC, re.M)))

# ---- 9. a file is not registered while a message of it could not be read (11/25/2026, the verification's first finding) ----------------------------
# What it found: a message that could not be read was passed over, the rest of its file went in - and the driver REGISTERED the file as done. The digest
# said 'ask Claimocity to send the file again; the next ingest reads it when it arrives', but every feed file is named by its day, the copy job never
# copies a name the bucket already holds, and the download step took only names the file register did not know: the whole file was never read, the visit
# never entered, and no later digest said so again. Now the file stays unregistered - the same hold as for a patient with no chart: every start reads it
# again (nothing is entered twice) and says so at the top, until the copy that is read is whole or William says the message is lost.
RECON = os.path.join(HELPERS, "claimocity_recon.py")
def pipe(w, stamp, decided=None, newcharts=None, made=None, refuse=(), half=(), stop="", parsed=None):
    """The stand-in for the programs the driver starts, closer to a run than steps(): the PARSE is the real parser, started as its own program over the batch's files; the import enters a
    visit exactly where the real import finds a chart (the chart the match file names for the message's OWN Claimocity id - a visit an earlier batch entered is not entered again) and
    leaves a failed row for the Claimocity ids of `refuse` (AdvancedMD refused the visit itself: nothing was made) and of `half` (the visit was made, its charges were refused); the
    digest and the reconciliation are the real helpers. made = the rows the new-chart step writes into its register; stop = the step in which the run is cut. Match and resolve answer `decided`.
    parsed = these messages instead of the real parser (a batch whose file is only a name)."""
    base = steps(w, stamp, parsed, decided or {}, newcharts=newcharts)
    def on_step(b, cmd):
        if stop and b == stop: return "cut here - the stand-in of a run that ended in this step", 1
        if b == "feed_parse_dft_1028.py" and parsed is None:
            r_ = subprocess.run([sys.executable, "-I", PARSER, str(cmd[3]), str(cmd[4])], cwd=w, capture_output=True, text=True)
            return (r_.stdout + r_.stderr).strip() or "(nothing printed)", r_.returncode
        if b == "claimocity_newcharts.py":
            base(b, cmd)
            if made is not None: json.dump({"created": made, "failed": []}, open(os.path.join(w, "registers", "feed_newcharts_%s.json" % stamp), "w"))
            return "DONE created %d" % len(made or [])
        if b == "claimocity_import.py":
            read_ = rd(w, "feed_parsed_%s.json" % stamp) or []; m_ = match(w, stamp); created = []; failed = []
            before = {(x["feed_id"], x["dos"], tuple(x["cpts"])) for f_ in os.listdir(os.path.join(w, "registers")) if f_.startswith("feed_import_") for x in (rd(w, "registers", f_) or {}).get("created", [])}
            for m in read_:
                e_ = m_.get(str(m.get("name") or "").upper().strip() + "|" + str(m.get("dob") or "")[:8]) or {}; chart = (e_.get("by_id") or {}).get(m.get("pid"))
                if not m.get("FT1") or not chart: continue
                d_ = m["FT1"][0]["dos"][:8]; dos = "%s/%s/%s" % (d_[4:6], d_[6:], d_[:4]); cpts = [c["cpt"] for c in m["FT1"]]
                if (m["pid"], dos, tuple(cpts)) in before: continue
                if m["pid"] in refuse: failed.append({"feed_id": m["pid"], "pid": chart, "info": {"dos": dos, "cpts": cpts}, "lines": [], "err": "addvisit: <Fault>an invented refusal</Fault>"})
                elif m["pid"] in half: failed.append({"feed_id": m["pid"], "pid": chart, "info": {"dos": dos, "cpts": cpts}, "lines": [], "empty_visit": "vst88" + m["pid"][:2], "err": "<Fault>an invented refusal of the charges</Fault>"})
                else: created.append(vrow(chart, "vst7%03d" % (len(before) + len(created)), dos, cpts, feed_id=m["pid"]))
            if "--all" in cmd: json.dump({"created": created, "skipped": [], "failed": failed}, open(os.path.join(w, "registers", "feed_import_%s.json" % stamp), "w"))
            return "DONE created %d failed %d" % (len(created), len(failed))
        if b == "claimocity_report.py":
            lines_, err_ = digest_of(w, stamp); return ("digest of %d line(s)" % len(lines_)) if not err_ else err_, (1 if err_ else 0)
        if b == "claimocity_recon.py":
            r_ = subprocess.run([sys.executable, RECON, stamp, "--ws", w], capture_output=True, text=True); return (r_.stdout + r_.stderr).strip() or "(nothing printed)", r_.returncode
        return base(b, cmd)
    return on_step
def digest(w, stamp):
    try: return open(os.path.join(w, "feed_digest_%s.md" % stamp)).read().splitlines()
    except OSError: return []
def entered(w, stamp): return [(x["feed_id"], x["pid"]) for x in (rd(w, "registers", "feed_import_%s.json" % stamp) or {}).get("created", [])]
def said(o, start, *words): return [l for l in o.splitlines() if l.startswith(start) and all(x in l for x in words)]
def result(o): return next((l for l in o.splitlines() if l.startswith("RESULT stamp")), "")
MAP9 = {FID(n): "pat910%d" % n for n in (1, 2, 3)}
S9, S9b, S9c = "20261202T1240Z", "20261202T1840Z", "20261203T1240Z"; F9 = "2026" + "1202" + "ab" * 12 + ".hl7"      # the day's file as Claimocity names it: the day and one fixed id
WHOLE9 = hl7(1) + hl7(2) + hl7x(3, lines=[ft1("99309")]); CUT9 = hl7(1) + hl7(2) + ends_in(hl7x(3, lines=[ft1("99309", keep=8)]))
w, r, mreg = sandbox("cut_file", [F9], ws_map=MAP9); IN9 = os.path.join(w, "inbox", "claimocity", F9); open(IN9, "w").write(CUT9)
o, calls, e = driver_run(w, r, ARGS(S9), pipe(w, S9)); o9 = o
_l9 = said(o, "NOT REGISTERED:", "could not be read"); D9 = digest(w, S9); I9 = ident(w, S9) or {}
check("9a the day's file reached the bucket cut in its last message: the two whole visits go in, nothing of the third - and the file is NOT registered (until 11/25/2026 it was registered as done: "
      "the whole file, sent again under its own name, was then never read and the third visit never entered)",
      lambda: e == "" and entered(w, S9) == [(FID(1), "pat9101"), (FID(2), "pat9102")] and (ingest(w).get("files") or {}) == {}, lambda: (e, o[-700:], entered(w, S9), sorted(ingest(w).get("files") or {})))
check("9b ONE line says it for the top of the report - the file, the message by file date and number with the parse step's fixed words, that every start reads the file again, and what ends it; the RESULT line counts the message and the file",
      lambda: len(_l9) == 1 and _l9[0].startswith("NOT REGISTERED: 1 file(s) hold a feed message that could not be read") and F9 in _l9[0] and "file %s message 3 (%s)" % (F9[:8], W_CUT) in _l9[0] and "every start reads" in _l9[0]
      and "--register-anyway" in _l9[0] and _l9[0].endswith("TOP OF THE REPORT") and re.search(r"RESULT stamp %s: files 1, messages 3, visits created 2, .*1 message\(s\) could not be read, 1 file\(s\) NOT registered" % S9, o) is not None
      and not any(s_ in o for s_ in secrets(1, 2, 3)), lambda: (_l9, result(o)))
check("9c the identity register names the file that is kept back for it, and the digest says at the top what happened and what ends it - the copy job does not replace a file the bucket holds, so the whole file must be put there, "
      "or William says the message is lost - and no longer 'the next ingest reads it when it arrives'",
      lambda: I9.get("not_registered_unreadable") == [F9] and I9.get("not_registered") == [] and len(has(top(D9), "1 feed message(s) could not be read", "file %s message 3 (%s)" % (F9[:8], W_CUT), "NOT entered", "NOT REGISTERED", F9, "Claimocity", "--register-anyway")) == 1
      and not has(D9, "the next ingest reads it when it arrives"), lambda: (I9.get("not_registered_unreadable"), top(D9)))
o, calls, e = driver_run(w, r, ARGS(S9b), pipe(w, S9b))
check("9d the NEXT start reads the same file again under its new stamp - the cut copy is still all there is: no visit is entered twice, the same line stands at the top again, and the file is still not registered",
      lambda: e == "" and "1 new file(s) of 1" in o and entered(w, S9b) == [] and len(said(o, "NOT REGISTERED: 1 file(s) hold a feed message that could not be read", F9)) == 1 and (ingest(w).get("files") or {}) == {}
      and len(has(top(digest(w, S9b)), "1 feed message(s) could not be read", "NOT REGISTERED")) == 1, lambda: (e, o[-600:], entered(w, S9b)))
open(IN9, "w").write(WHOLE9)      # the whole file is in the inbox under the same name: what the download step brings once the bucket holds it (section 10)
o, calls, e = driver_run(w, r, ARGS(S9c), pipe(w, S9c))
check("9e once the WHOLE file is there under the same name the next start reads it, enters the third visit - once - and registers the file, with its size on record (the download step compares it with the bucket's); nothing is said at the top any more",
      lambda: e == "" and entered(w, S9c) == [(FID(3), "pat9103")] and sorted(ingest(w).get("files") or {}) == [F9] and ingest(w)["files"][F9].get("bytes") == len(WHOLE9.encode()) and "NOT REGISTERED" not in o
      and "could not be read" not in result(o) and not has(digest(w, S9c), "could not be read") and rd(w, "registers", "feed_unreadable_%s.json" % S9c) is None, lambda: (e, o[-600:], entered(w, S9c), ingest(w).get("files")))
w, r, mreg = sandbox("cut_closed", [F9, "20261203b.hl7"], ws_map={FID(1): "pat9101", FID(2): "pat9102", FID(3): "pat9103"})
open(os.path.join(w, "inbox", "claimocity", F9), "w").write(CUT9); open(os.path.join(w, "inbox", "claimocity", "20261203b.hl7"), "w").write(hl7(1) + hl7x(5))
o, calls, e = driver_run(w, r, ARGS(S9) + ("--register-anyway", "download__" + F9 + ",20261203b.hl7"), pipe(w, S9, decided={KEY(5): answer(0, "", status="AMBIGUOUS", will=True, ids=[FID(5)], why=FI.WHY_DISAGREE)}))
_lw = said(o, "REGISTERED ON WILLIAM'S WORD")
check("9f what ends it when Claimocity cannot send the message again: on William's word the ingest is started once with --register-anyway <file> - the file is registered, ONE line for the top says which messages are given up, the file register keeps a note, "
      "and the digest says the file was registered on his word (a file whose message can never be read would otherwise be read and reported in every run for ever)",
      lambda: e == "" and F9 in (ingest(w).get("files") or {}) and len(_lw) == 1 and F9 in _lw[0] and "file %s message 3 (%s)" % (F9[:8], W_CUT) in _lw[0] and _lw[0].endswith("TOP OF THE REPORT") and "William" in str(ingest(w)["files"][F9].get("note"))
      and (ident(w, S9) or {}).get("registered_anyway") == [F9] and len(has(top(digest(w, S9)), "1 feed message(s) could not be read", "REGISTERED ON WILLIAM'S WORD", F9)) == 1 and not said(o, "NOT REGISTERED:", "could not be read"),
      lambda: (e, _lw, ingest(w).get("files"), top(digest(w, S9))))
check("9g ... the option never registers a file that holds a patient with NO chart: that is settled by a chart (William's answer, the repository's map), never by giving the visit up",
      lambda: "20261203b.hl7" not in (ingest(w).get("files") or {}) and len(said(o, "NOT REGISTERED:", "a patient with no chart", "20261203b.hl7", FID(5))) == 1 and "20261203b.hl7" not in _lw[0], lambda: (said(o, "NOT REGISTERED:"), _lw))
F9n = "2026" + "1205d.hl7"
w, r, mreg = sandbox("cut_closed_nochart", [F9n], ws_map=MAP9); open(os.path.join(w, "inbox", "claimocity", F9n), "w").write(hl7(1) + hl7x(5) + ends_in(hl7x(2, lines=[ft1("99309", keep=8)])))
o, calls, e = driver_run(w, r, ARGS(S9) + ("--register-anyway", F9n), pipe(w, S9, decided={KEY(5): answer(0, "", status="AMBIGUOUS", will=True, ids=[FID(5)], why=FI.WHY_DISAGREE)})); I9n = ident(w, S9) or {}
check("9g2 ... also not when the same file holds a message that cannot be read: the file stays unregistered, nothing says it was registered on William's word - not the driver, not its register, not the digest - "
      "one plain line says why the option did nothing, and BOTH reasons the file is kept back for still stand at the top",
      lambda: e == "" and (ingest(w).get("files") or {}) == {} and not said(o, "REGISTERED ON WILLIAM'S WORD") and len(said(o, "--register-anyway: " + F9n, "holds a patient with no chart", "nothing is done")) == 1
      and len(said(o, "NOT REGISTERED:", "a patient with no chart", F9n, FID(5))) == 1 and len(said(o, "NOT REGISTERED:", "could not be read", F9n)) == 1
      and I9n.get("registered_anyway") == [] and I9n.get("not_registered") == [F9n] and I9n.get("not_registered_unreadable") == [F9n]
      and len(has(top(digest(w, S9)), "1 feed message(s) could not be read", "NOT REGISTERED (" + F9n)) == 1 and not has(digest(w, S9), "WILLIAM'S WORD"),
      lambda: (e, [l for l in o.splitlines() if "REGISTER" in l or "register-anyway" in l], {k: v for k, v in I9n.items() if "regist" in k}, top(digest(w, S9))))
w, r, mreg = sandbox("anyway_no_name", [F9], ws_map=MAP9); open(os.path.join(w, "inbox", "claimocity", F9), "w").write(CUT9)
o, calls, e = driver_run(w, r, ARGS(S9) + ("--register-anyway",), pipe(w, S9)); _o2, _c2, _e2 = driver_run(w, r, ARGS(S9)[:-1] + ("--register-anyway", "--live"), pipe(w, S9))
check("9g3 a start with --register-anyway and NO file name behind it (the option last, or another option where the name belongs) ends at once - before any step, nothing entered and nothing written "
      "(read where it is used, it would have ended the run AFTER the import: the visits entered, no register, no digest, no word)",
      lambda: e == "" and calls == [] and _e2 == "" and _c2 == [] and not os.path.exists(os.path.join(w, "registers", "feed_import_%s.json" % S9)) and (ingest(w).get("runs") or []) == [], lambda: (e, calls, _e2, _c2, o[-300:]))
F9m = "2026" + "1204c.hl7"
w, r, mreg = sandbox("cut_one_closed", [F9, F9m], ws_map=MAP9)
open(os.path.join(w, "inbox", "claimocity", F9), "w").write(CUT9); open(os.path.join(w, "inbox", "claimocity", F9m), "w").write(hl7(1) + ends_in(hl7x(2, lines=[ft1("99309", keep=8)])))
o, calls, e = driver_run(w, r, ARGS(S9) + ("--register-anyway", F9), pipe(w, S9)); _lw2 = said(o, "REGISTERED ON WILLIAM'S WORD"); _lk2 = said(o, "NOT REGISTERED:", "could not be read"); D9m = digest(w, S9); I9m = ident(w, S9) or {}
check("9f2 two files with a message that cannot be read, and William's word for ONE of them: that one is registered, the other stays unregistered - each of the driver's two lines names its own file only, and the digest's line says which file is kept back "
      "and which was registered on his word (it named the kept file alone, as if every message it lists were still waited for)",
      lambda: e == "" and sorted(ingest(w).get("files") or {}) == [F9] and len(_lw2) == 1 and F9 in _lw2[0] and F9m not in _lw2[0] and len(_lk2) == 1 and F9m in _lk2[0] and F9 not in _lk2[0]
      and I9m.get("registered_anyway") == [F9] and I9m.get("registered_anyway_unreadable") == [F9] and I9m.get("registered_anyway_refused") == [] and I9m.get("not_registered_unreadable") == [F9m]
      and len(has(top(D9m), "2 feed message(s) could not be read", "NOT REGISTERED: " + F9m, "REGISTERED ON WILLIAM'S WORD: " + F9, "--register-anyway")) == 1,
      lambda: (e, _lw2, _lk2, {k: v for k, v in I9m.items() if "regist" in k}, top(D9m)))
w, r, mreg = sandbox("cut_dry", [F9], ws_map=MAP9); open(os.path.join(w, "inbox", "claimocity", F9), "w").write(CUT9)
o, calls, e = driver_run(w, r, ARGS(S9, live=False), pipe(w, S9))
check("9h a DRY ingest of such a file says nothing about files it would not register (as for a patient with no chart) and leaves no register of its own behind - the parse step's count of this batch is taken away again (it would travel to main as a batch register)",
      lambda: e == "" and "NOT REGISTERED" not in o and (ingest(w).get("files") or {}) == {} and not os.path.exists(os.path.join(w, "registers", "feed_unreadable_%s.json" % S9)) and any("UNREADABLE: 1 feed message(s)" in l for l in o.splitlines())
      and "1 message(s) could not be read" in result(o), lambda: (e, o[-500:], os.listdir(os.path.join(w, "registers"))))
w, r, mreg = sandbox("cut_odd_name", ["feed_of_today.hl7", "20261203b.hl7"], ws_map=MAP9)
open(os.path.join(w, "inbox", "claimocity", "feed_of_today.hl7"), "w").write(CUT9); open(os.path.join(w, "inbox", "claimocity", "20261203b.hl7"), "w").write(hl7(1))
o, calls, e = driver_run(w, r, ARGS(S9), pipe(w, S9))
check("9i a file whose name does not begin with its day (the parse step names it '?'): it is the one kept back - not the dated file beside it",
      lambda: e == "" and sorted(ingest(w).get("files") or {}) == ["20261203b.hl7"] and len(said(o, "NOT REGISTERED: 1 file(s) hold a feed message that could not be read", "feed_of_today.hl7", "file ? message 3")) == 1, lambda: (e, o[-500:], sorted(ingest(w).get("files") or {})))
w, r, mreg = sandbox("cut_register_broken", [F9], ws_map=MAP9); open(os.path.join(w, "inbox", "claimocity", F9), "w").write(CUT9)
def _spoil(b, cmd, _p=pipe(w, S9)):
    out = _p(b, cmd)
    if b == "feed_parse_dft_1028.py": open(os.path.join(w, "registers", "feed_unreadable_%s.json" % S9), "w").write("{ half written")
    return out
o, calls, e = driver_run(w, r, ARGS(S9), _spoil)
check("9j the parse step's count of this batch is there but cannot be read: every file of the batch is kept back (never none), and the line says so",
      lambda: e == "" and (ingest(w).get("files") or {}) == {} and len(said(o, "NOT REGISTERED: 1 file(s)", "could not be read", F9)) == 1 and said(o, "NOT REGISTERED:")[0].endswith("TOP OF THE REPORT"), lambda: (e, o[-500:]))

# ---- 10. the download step fetches a file again whose copy in the bucket has another size than the one that was read ---------------------------------
# (the same finding.) claimocity_gcs.py took only names the file register did not know; a file that was read while Claimocity was still writing it - cut
# BETWEEN two messages, so that nothing in it is broken - was registered, and the rest of that day's visits was never read. The driver now records the size
# of the file it registers, and the download step fetches a registered file again when the bucket's object has another size: the driver then reads it as new
# by its content and the import enters what is missing. The 44 files registered before that day carry no size and are never fetched again for it.
GCS = open(os.path.join(HELPERS, "claimocity_gcs.py")).read()
def gcs_run(label, register, bucket, args=(), inbox=None):
    """The REAL download step - only its workspace line points at a throwaway folder - over a stand-in `gcloud` that lists and copies from a local folder: no network, no key.
    register = the file register's entries; bucket = {object name: its text}; inbox = files already in the inbox -> (exit code, what it printed, {file in the inbox: its text})"""
    d = os.path.join(TMP, "gcs_" + label); bk = os.path.join(d, "bucket"); bn = os.path.join(d, "bin"); box = os.path.join(d, "inbox", "claimocity")
    for x in (bk, bn, box, os.path.join(d, "registers"), os.path.join(d, "secrets")): os.makedirs(x)
    json.dump({"files": register, "runs": []}, open(os.path.join(d, "registers", "claimocity_ingest.json"), "w")); json.dump({"client_email": "stand-in@example.invalid"}, open(os.path.join(d, "secrets", "claimocity_gcs_key.json"), "w"))
    for n_, t_ in bucket.items(): open(os.path.join(bk, n_), "w").write(t_)
    for n_, t_ in (inbox or {}).items(): open(os.path.join(box, n_), "w").write(t_)
    g = os.path.join(bn, "gcloud")
    open(g, "w").write("#!/bin/sh\n# a stand-in for the Google Cloud command: it lists and copies from a local folder\n"
                       'if [ "$1" = "auth" ]; then exit 0; fi\n'
                       'if [ "$1" = "storage" ] && [ "$2" = "ls" ]; then for f in "$FAKE_BUCKET"/*; do [ -e "$f" ] || continue; printf \'%10d  2026-12-03T05:00:00Z  gs://bucket/%s\\n\' "$(wc -c < "$f")" "$(basename "$f")"; done; exit 0; fi\n'
                       'if [ "$1" = "storage" ] && [ "$2" = "cp" ]; then cp "$FAKE_BUCKET/$(basename "$3")" "$4"; exit $?; fi\nexit 1\n')
    os.chmod(g, 0o755)
    if GCS.count('WS = "/home/claude/unbilled"') != 1: return -1, "the helper's workspace line was not found once", {}
    open(os.path.join(d, "gcs_under_test.py"), "w").write(GCS.replace('WS = "/home/claude/unbilled"', "WS = %r" % d))
    r_ = subprocess.run([sys.executable, os.path.join(d, "gcs_under_test.py")] + list(args), cwd=d, capture_output=True, text=True, env=dict(os.environ, PATH=bn + os.pathsep + os.environ.get("PATH", ""), FAKE_BUCKET=bk, PYTHONDONTWRITEBYTECODE="1"))
    return r_.returncode, (r_.stdout + r_.stderr).strip(), {n_: open(os.path.join(box, n_), newline="").read() for n_ in sorted(os.listdir(box))}
def reg9(text, size=True): return dict({"stamp": S9, "sha256": "invented", "messages": 2, "at": "2026-12-02T12:45:00Z"}, **({"bytes": len(text.encode())} if size else {}))
PART9 = hl7(1) + hl7(2); OBJ9 = "download__" + F9; OTHER9 = "2026" + "1201" + "ab" * 12 + ".hl7"
c10, o10, in10 = gcs_run("changed", {F9: reg9(PART9), OTHER9: reg9(hl7(4))}, {OBJ9: WHOLE9, "download__" + OTHER9: hl7(4)})
check("10a a file the register knows whose object in the bucket has ANOTHER size than the one that was read (the bucket's copy was replaced by the whole file): the download step fetches it again and says so - until 11/25/2026 it answered '0 new' and nothing ever read the whole file",
      lambda: c10 == 0 and in10 == {OBJ9: WHOLE9} and "1 new" in o10.splitlines()[0] and any(OBJ9 in l and "changed" in l and str(len(PART9.encode())) in l for l in o10.splitlines()[1:]), lambda: (c10, o10, sorted(in10)))
c10b, o10b, in10b = gcs_run("same", {F9: reg9(WHOLE9), OTHER9: reg9(hl7(4), size=False)}, {OBJ9: WHOLE9, "download__" + OTHER9: hl7(4) + hl7(5), "download__2026" + "1204" + "ab" * 12 + ".hl7": hl7(6), "download__empty.hl7": ""})
check("10b ... a registered file of the same size is not fetched again; a file registered BEFORE the size was recorded (the 44 files up to that day) is never fetched again for its size; a file the register does not know is fetched as before; an empty one never",
      lambda: c10b == 0 and sorted(in10b) == ["download__2026" + "1204" + "ab" * 12 + ".hl7"] and "1 new" in o10b.splitlines()[0] and "changed" not in o10b, lambda: (c10b, o10b, sorted(in10b)))
c10c, o10c, in10c = gcs_run("listonly", {F9: reg9(PART9)}, {OBJ9: WHOLE9}, args=("--list-only",))
check("10c the daily task's cheap look (--list-only) counts such a file as new too - so that the run goes on to fetch and read it - and downloads nothing", lambda: c10c == 0 and in10c == {} and "1 new" in o10c.splitlines()[0] and "changed" in o10c, lambda: (c10c, o10c))
c10d, o10d, in10d = gcs_run("held", {}, {OBJ9: CUT9}, inbox={OBJ9: CUT9})
check("10d a file the driver keeps back (it is not in the file register) is new to every later run's download step; a copy of the same size already in the inbox is not fetched twice",
      lambda: c10d == 0 and in10d == {OBJ9: CUT9} and "1 new (1 downloaded" in o10d.splitlines()[0], lambda: (c10d, o10d))
w, r, mreg = sandbox("resent", [F9], ws_map=MAP9); IN10 = os.path.join(w, "inbox", "claimocity", F9); open(IN10, "w").write(PART9)
o, calls, e = driver_run(w, r, ARGS(S9), pipe(w, S9)); _first = dict(ingest(w).get("files") or {})
c10e, o10e, in10e = gcs_run("resent", _first, {OBJ9: WHOLE9}); open(IN10, "w").write(in10e.get(OBJ9, PART9))
o2, calls, e2 = driver_run(w, r, ARGS(S9c), pipe(w, S9c))
check("10e the two together, as a run does them: the file was read while it held two of its three messages (nothing in it was broken) and was registered; the whole file is in the bucket under the same name - "
      "the download step fetches it, the driver reads it as new by its content, the third visit is entered once and the register records the new size",
      lambda: e == "" and e2 == "" and entered(w, S9) == [(FID(1), "pat9101"), (FID(2), "pat9102")] and _first[F9].get("bytes") == len(PART9.encode()) and in10e == {OBJ9: WHOLE9} and entered(w, S9c) == [(FID(3), "pat9103")]
      and ingest(w)["files"][F9].get("bytes") == len(WHOLE9.encode()) and ingest(w)["files"][F9].get("stamp") == S9c, lambda: (e, e2, _first, o10e, entered(w, S9c), ingest(w).get("files")))

# ---- 11. a message without a Claimocity id (the verification's second finding) -------------------------------------------------------------------------
# What it found: a message with a name, a birth date and a charge line whose patient line carries an EMPTY Claimocity id was never entered (the import asks for
# the chart of the message's own id) and its file was registered as done; the digest had at most one line for any number of such messages, with no file and
# no message number - and for one whose name and date a known patient shares, nothing at all. Entering it by the name is not the remedy (never by the name
# alone - and the reconciliation and the insurance check find a message by its Claimocity id). The parse step counts it like every other message that cannot be
# entered: file date and message number at the top, counted in the RESULT line - and its file is not registered: the visit is not on a chart, a corrected file
# is read as soon as it is there, and William's word (--register-anyway) ends it when Claimocity cannot send one.
S11 = "20261204T1240Z"; F11a, F11b = "2026" + "1204a.hl7", "2026" + "1205b.hl7"
w, r, mreg = sandbox("no_id", [F11a, F11b, "20261206c.hl7"], ws_map={FID(1): "pat9101"})
open(os.path.join(w, "inbox", "claimocity", F11a), "w").write(hl7(1) + hl7x(1, fid="")); open(os.path.join(w, "inbox", "claimocity", F11b), "w").write(hl7x(2, fid="")); open(os.path.join(w, "inbox", "claimocity", "20261206c.hl7"), "w").write(hl7(1))
_noid11 = {KEY(1): answer(0, "", status="AMBIGUOUS", will=True, ids=[], why=FI.WHY_NO_ID), KEY(2): answer(0, "", status="AMBIGUOUS", will=True, ids=[], why=FI.WHY_NO_ID)}      # what the match step writes for a key no Claimocity id carries
o, calls, e = driver_run(w, r, ARGS(S11), pipe(w, S11, decided=_noid11)); _l11 = said(o, "NOT REGISTERED:", "could not be read"); D11 = digest(w, S11)
check("11a a message with an EMPTY Claimocity id - one under the name and birth date of a patient the map knows, one under a name nobody has a chart for: neither is entered (never by the name alone), the map learns no empty id - and BOTH files stay unregistered "
      "(until 11/25/2026 both were registered as done and the two visits were never entered: the hold asked for a patient id)",
      lambda: e == "" and entered(w, S11) == [(FID(1), "pat9101"), (FID(1), "pat9101")] and sorted(ingest(w).get("files") or {}) == ["20261206c.hl7"] and pm(w) == {FID(1): "pat9101"}, lambda: (e, o[-700:], entered(w, S11), sorted(ingest(w).get("files") or {}), pm(w)))
check("11b ONE line for the top names each such message by file date and message number - also the one whose name and date a known patient shares, about which nothing at all was said - and the RESULT line counts them",
      lambda: len(_l11) == 1 and _l11[0].startswith("NOT REGISTERED: 2 file(s) hold a feed message that could not be read") and "file %s message 2 (%s)" % (F11a[:8], W_NOID) in _l11[0] and "file %s message 1 (%s)" % (F11b[:8], W_NOID) in _l11[0]
      and _l11[0].endswith("TOP OF THE REPORT") and "2 message(s) could not be read, 2 file(s) NOT registered" in result(o) and not any(s_ in o for s_ in secrets(1, 2)), lambda: (_l11, result(o)))
check("11c the digest says it at the top with both messages, and the reconciliation register - the record that every charge of the feed is in AdvancedMD - lists the two visits as NOT entered, with the reason that they carry no Claimocity id "
      "(it said 'patient not found by name and date of birth' although nothing had been looked up) and counts the messages that could not be read",
      lambda: len(has(top(D11), "2 feed message(s) could not be read", "file %s message 2 (%s)" % (F11a[:8], W_NOID), "file %s message 1 (%s)" % (F11b[:8], W_NOID), "NOT REGISTERED", F11a, F11b)) == 1
      and (lambda rc: sorted((x["f"], x["s"]) for x in rc["rows"]) == [("", "nochart"), ("", "nochart"), (FID(1), "entered"), (FID(1), "entered")] and all("no Claimocity id" in x["why"] for x in rc["rows"] if not x["f"]) and rc["counts"].get("unreadable") == 2)(
          rd(w, "registers", "feed_recon_%s.json" % S11) or {"rows": [], "counts": {}}), lambda: (top(D11), rd(w, "registers", "feed_recon_%s.json" % S11)))
check("11d the one vague line it had - 'no chart chosen and none made for Claimocity id (an id that is not 24 hex characters): the message carries no Claimocity id', once for any number of such messages - is gone: "
      "a key that no Claimocity id carries is nobody's row in the identity register, and nobody is counted as looked up for it",
      lambda: not has(D11, "an id that is not 24 hex characters") and (ident(w, S11) or {}).get("patients") == [] and (ident(w, S11) or {}).get("counts", {}).get("looked up") == 0 and len(has(D11, "0 looked up", "0 with NO chart")) == 1,
      lambda: (has(D11, "24 hex"), ident(w, S11)))
w, r, mreg = sandbox("no_id_map", [F11b], ws_map={FID(1): "pat9101", "": "pat9999"}); open(os.path.join(w, "inbox", "claimocity", F11b), "w").write(hl7x(2, fid=""))
o, calls, e = driver_run(w, r, ARGS(S11), pipe(w, S11, decided={KEY(2): answer(0, "", status="AMBIGUOUS", will=True, ids=[], why=FI.WHY_NO_ID)}))
check("11e a patient map that holds an EMPTY Claimocity id (a slip of an older run, or of a hand) never makes a message without an id a known patient: its visit is not entered on that chart - by no chart at all - and its file stays unregistered",
      lambda: e == "" and entered(w, S11) == [] and (ingest(w).get("files") or {}) == {} and "pat9999" not in json.dumps(match(w, S11)) and len(said(o, "NOT REGISTERED:", "could not be read", F11b)) == 1,
      lambda: (e, o[-500:], entered(w, S11), match(w, S11)))
L11f, e11f = report_run("noid_own_count", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], identity=dict(IDENT7, not_registered_unreadable=["2026" + "1128a.hl7"]))
L11g, e11g = report_run("noid_own_count_closed", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], identity=dict(IDENT7, registered_anyway=["2026" + "1128a.hl7"], registered_anyway_unreadable=["2026" + "1128a.hl7"]))
check("11f a batch whose parse step did not count such a message (an older copy of the parser - the driver counts it itself and keeps the file back, check 3e3): the digest still says at the top that a visit is not entered, "
      "with the file and what ends it - and, once the file was registered on William's word, that it was given up",
      lambda: e11f == "" and e11g == "" and len(has(top(L11f), "a feed message carries a charge line and no Claimocity id", "NOT entered", "NOT REGISTERED", "1128a.hl7", "--register-anyway")) == 1
      and len(has(top(L11g), "a feed message carries a charge line and no Claimocity id", "NOT entered", "REGISTERED ON WILLIAM'S WORD", "1128a.hl7")) == 1 and not has(top(L7), "no Claimocity id"), lambda: (e11f, e11g, top(L11f), top(L11g)))

# ---- 12. a DRY ingest leaves the patient map alone (the verification) ------------------------------------------------------------------------------------
# What it found: a dry ingest wrote registers/claimocity_patient_map.json with every chart the identity rule chose - while its last line said 'nothing written'.
# The live ingest of the same file then took those patients as 'known from the patient map': its identity register had no row for them and its digest none
# of the rule's lines for William. What else a dry run writes was gone through: it also took the repository's chart into the workspace's map FILE, so the live
# run after it no longer said which feed patients were re-pointed, and the parse step's count of unreadable messages stayed behind as a batch register (9h).
S12 = "20261205T1240Z"
w, r, mreg = sandbox("dry_map", ["20261126b.hl7"], ws_map={FID(0): "pat9000", FID(5): "pat9002"}, main_map={FID(0): "pat9000", FID(5): "pat9902"})
_before = open(os.path.join(w, "registers", "claimocity_patient_map.json")).read()
o, calls, e = driver_run(w, r, ARGS(S12, live=False), steps(w, S12, PARSED2 + [msg(5, "20261126")], DEC)); od = o
check("12a a DRY ingest that looked four patients up leaves the patient map exactly as it was - no chart the identity rule chose is learned (until 11/25/2026 the dry run wrote them all)",
      lambda: e == "" and open(os.path.join(w, "registers", "claimocity_patient_map.json")).read() == _before and "(DRY - nothing written, files not registered)" in o, lambda: (e, pm(w), o[-300:]))
check("12b ... it still SHOWS what a live run would do: the match file of the dry run names the repository's chart for a feed patient re-pointed on main - taken in memory only, the workspace's map file is not written - and the line says so",
      lambda: (match(w, S12).get(KEY(5)) or {}).get("resolved") == "pat9902" and len(said(o, "PATIENT MAP: 1 feed patient(s) now go to the repository's chart", "DRY")) == 1 and pm(w).get(FID(5)) == "pat9002", lambda: (match(w, S12).get(KEY(5)), said(o, "PATIENT MAP:"), pm(w)))
o, calls, e = driver_run(w, r, ARGS(S12), steps(w, S12, PARSED2 + [msg(5, "20261126")], DEC, newcharts={KEY(3): "pat9301", KEY(4): "pat9402"}))
check("12c the LIVE ingest of the same file after it finds what the dry run found: the four patients are looked up again and listed in its identity register (not 'known from the patient map'), the re-pointed feed patient is named there with both charts, and now the map learns",
      lambda: e == "" and len((ident(w, S12) or {}).get("patients") or []) == 4 and (ident(w, S12) or {}).get("counts", {}).get("known from the patient map") == 2 and (ident(w, S12) or {}).get("repointed") == [{"feed_id": FID(5), "was": "pat9002", "now": "pat9902"}]
      and pm(w) == {FID(0): "pat9000", FID(5): "pat9902", FID(1): "pat9101", FID(2): "pat9201", FID(3): "pat9301", FID(4): "pat9402"}, lambda: (e, o[-400:], ident(w, S12), pm(w)))
check("12d what a dry run does write is its own row in the file register's list of runs, marked not live - no file is registered, no identity register is written",
      lambda: (lambda runs: len(runs) == 2 and runs[0].get("live") is False and runs[0].get("stamp") == S12 and runs[1].get("live") is True)(ingest(w).get("runs") or []), lambda: ingest(w).get("runs"))

# ---- 13. the driver's own lines for William reach the identity register and the top of the digest; what the digest prints from two registers ----------------
# What the verification found: the driver's list 'notes' ("printed, and carried to main by the identity register") was never filled, so its lines that end
# TOP OF THE REPORT stood in its own log only - the repository's map could not be read, two known Claimocity ids of one name on two charts. And in the digest: the
# top line for a name-and-date key several Claimocity ids share named only the first id (which can be the one that HAS a chart); the two lines from the insurance
# check's file printed the record's key and the strings of its list without a look at their shape.
S13 = "20261206T1240Z"; MARKED = "<" * 7 + " ours\n{}\n" + "=" * 7 + "\n{}\n" + ">" * 7 + " theirs\n"
w, r, mreg = sandbox("notes", ["20261128a.hl7"], ws_map={FID(1): "pat9101", TWIN: "pat9102"}, main_map=MARKED, main_yes=None)
open(os.path.join(w, "inbox", "claimocity", "20261128a.hl7"), "w").write(hl7(1) + hl7x(1, fid=TWIN))
o, calls, e = driver_run(w, r, ARGS(S13), pipe(w, S13, decided={})); N13 = (ident(w, S13) or {}).get("notes") or []; D13 = digest(w, S13)
_tops = [l[:-len(" - TOP OF THE REPORT")] for l in o.splitlines() if l.endswith(" - TOP OF THE REPORT")]
check("13a every line of the driver's own that ends TOP OF THE REPORT is carried by the identity register (its notes were always empty): the repository's map that could not be read, the standing file that is missing, "
      "and two known Claimocity ids under one name and birth date that go to two charts",
      lambda: e == "" and len(_tops) == 3 and N13 == _tops and any(n.startswith("PATIENT MAP: the repository's map could not be read") for n in N13) and any(n.startswith("SAME PERSON FILE:") for n in N13)
      and any(n.startswith("PATIENT MAP: 2 Claimocity ids under one name and birth date go to 2 charts") and "pat9101" in n and "pat9102" in n for n in N13), lambda: (e, _tops, N13))
check("13b ... and the digest prints each of them at the top, word for word", lambda: len(N13) == 3 and all(len(has(top(D13), n)) == 1 for n in N13), lambda: (N13, top(D13)))
UP = "AB" + FID(1)[2:]      # a Claimocity id that begins with capital letters
L13c, e13c = report_run("notes_shape", S13, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], identity=dict(IDENT7, patients=[], notes=["two ids on two charts (%s on pat9101, %s on pat9102)" % (FID(1), UP), "a hand-made line for " + NAME(1).replace(", ", ","), "seen on 11/29/2026"]))
check("13c a note is printed only when it holds no date and nothing shaped like a LAST,FIRST name - and a Claimocity id written in capital letters behind a comma is not taken for one (such a note was left out)",
      lambda: e13c == "" and len(has(top(L13c), "two ids on two charts", UP)) == 1 and not has(L13c, "hand-made") and not has(L13c, "seen on") and not any(s_ in "\n".join(L13c) for s_ in secrets(1)), lambda: (e13c, top(L13c)))
# the top line for a key several Claimocity ids share (the resolve step's answer WHY_SHARED: one row with every id, no chart)
SH = lambda ids, **k: dict(dict(feed_ids=list(ids), chart="", status="AMBIGUOUS", new_chart=False, rule=0, why=FI.WHY_SHARED, flags=[], candidates=["pat9101", "pat9102"], evidence=[], feed_dob="none", for_william=True), **k)
OWN = dict(feed_ids=[FID(1)], chart="pat9101", status="FOUND", new_chart=False, rule=2, why=FI.WHY[2], flags=[], candidates=["pat9101", "pat9102"], evidence=[], feed_dob="real", for_william=False)
def shared_digest(label, rows): return report_run(label, S13, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], identity=dict(IDENT7, patients=rows, notes=[], not_registered=[], repointed=[]))
L13d, e13d = shared_digest("shared_ab", [OWN, SH([FID(1), TWIN])]); L13e, e13e = shared_digest("shared_ba", [SH([TWIN, FID(1)]), OWN]); _sh = lambda L: has(top(L), "no chart chosen and none made", FI.WHY_SHARED)
check("13d the top line for a name-and-date key two Claimocity ids share names BOTH ids and says which of them has a chart through a key of its own and which has none - whatever the order of the messages "
      "(it named the first id alone: the one whose visit had gone in, while the id without a chart stood nowhere in the digest)",
      lambda: e13d == "" and e13e == "" and all(len(_sh(L)) == 1 and FID(1) in _sh(L)[0] and TWIN in _sh(L)[0] and "%s has pat9101" % FID(1) in _sh(L)[0] and "%s has no chart" % TWIN in _sh(L)[0] for L in (L13d, L13e)), lambda: (e13d, _sh(L13d), _sh(L13e)))
check("13e ... and the count line counts patients, not rows: two were looked up, ONE is without a chart",
      lambda: all(len(has(L, "2 looked up", "1 with NO chart")) == 1 for L in (L13d, L13e)), lambda: [l for l in L13d if "looked up" in l])
L13f, e13f = shared_digest("shared_plain", [SH([FID(1), TWIN, FID(2)])])
check("13f a key whose ids ALL have no chart: every id is named, none is said to have a chart, and three patients are counted", lambda: e13f == "" and len(_sh(L13f)) == 1 and all(i in _sh(L13f)[0] for i in (FID(1), TWIN, FID(2))) and " has pat" not in _sh(L13f)[0]
      and len(has(L13f, "3 looked up", "3 with NO chart")) == 1, lambda: (e13f, _sh(L13f), [l for l in L13f if "looked up" in l]))
L13g, e13g = shared_digest("shared_each", [OWN, SH([FID(1), TWIN], each=[[FID(1), "pat9101"], [TWIN, "a new chart"]]), SH([FID(2), FID(3)], each=[[FID(2), NAME(2)], [FID(3), "pat9"]])])
check("13g when the driver carried what the rule gives each id on its own (the resolve step's words, taken only as Claimocity ids, chart ids and its three fixed answers) the line says it - William's answer names the chart of each id; "
      "a value of another shape is never printed",
      lambda: e13g == "" and len(has(top(L13g), FID(1), TWIN, "each on its own: %s -> pat9101; %s -> a new chart" % (FID(1), TWIN))) == 1 and len(has(top(L13g), FID(2), FID(3))) == 1 and not has(top(L13g), FID(2), "each on its own")
      and not any(s_ in "\n".join(L13g) for s_ in secrets(2)), lambda: (e13g, top(L13g)))
w, r, mreg = sandbox("shared_driver", ["20261128a.hl7", "20261129a.hl7"], ws_map={})
o, calls, e = driver_run(w, r, ARGS(S4s), steps(w, S4s, [msg(1, "20261128"), msg(1, "20261129", dob=P1900), msg(1, "20261129", dob=P1900, fid=TWIN)], {KEY(1): answer(2, "pat9101", ids=[FID(1)]), KSH: _none}))
_er = next((p for p in (ident(w, S4s) or {}).get("patients") or [] if len(p.get("feed_ids") or []) == 2), {})
check("13h the driver carries it: the row of a shared key that got no chart names, for each id, what the resolve step said the rule gives it on its own - and a row with a chart carries no such field",
      lambda: e == "" and _er.get("each") == [[FID(1), "pat9101"], [TWIN, "a new chart"]] and all("each" not in p for p in (ident(w, S4s) or {}).get("patients") or [] if p.get("chart")), lambda: (e, ident(w, S4s)))
# the two lines from the insurance check's file (same person? / no birth date on either side): chart ids and visit ids only
ODD13 = {"pat9301": vrec(["vst7004"], same_person=["vst7004", NAME(1), 7, None, {"x": 1}]), NAME(2).replace(", ", ","): vrec(["vst7009"], same_person=[NAME(2), "vst7009"]), "pat9303": vrec(["vst7005"], no_birth_date=[NAME(3), 5]),
         "pat9304": vrec(["vst7006", "7007"], no_birth_date=["vst7006", "7007"])}
L13i, e13i = report_run("verify_odd", S7, ROWS8, verify=ODD13); _sp = has(top(L13i), "SAME PERSON?"); _nb = has(top(L13i), "NO BIRTH DATE ON EITHER SIDE")
check("13i the digest's lines SAME PERSON? and NO BIRTH DATE ON EITHER SIDE print a record only when its key is a chart id and only the entries of its list that are visit ids: a hand-made or odd record with a name in it "
      "reaches no line at the top (it was printed there word for word), and the line says how many records are not shown",
      lambda: e13i == "" and len(_sp) == 1 and "1 chart(s)" in _sp[0] and "pat9301 (vst7004)" in _sp[0] and "1 record(s) not shown" in _sp[0] and len(_nb) == 1 and "1 chart(s)" in _nb[0] and "pat9304 (vst7006 7007)" in _nb[0]
      and "1 record(s) not shown" in _nb[0] and "pat9303" not in _nb[0] and not any(s_ in "\n".join(top(L13i)) for s_ in secrets(1, 2, 3)), lambda: (e13i, _sp, _nb))

# ---- 14. the question about a new chart travels with the chart, not with the run that made it (the verification) ------------------------------------------
# What it found: a run cut after the new-chart step (five of the eleven ingests from 11/13 to 11/24 were cut) had made the charts and written its new-chart
# register, but no identity register and no digest. The next run found each new chart by its Claimocity id (rule 1) and its digest said '0 new chart(s) made':
# 'new chart ... beside same-name charts - same person or not?' and 'face sheet needed' never reached William. And a run whose identity register could not be
# written had no 'Which chart' section at all.
S14a, S14b, S14c = "20261207T1240Z", "20261207T1241Z", "20261208T1240Z"
MADE14 = [{"pid": "pat9402", "chart": "F261207-01", "feed_ids": [FID(4)], "plans": [], "rule": 9, "why": FI.WHY_NEW_BESIDE, "flags": [FI.FLAG_NOT_USED], "dob": "real", "for_william": True},
          {"pid": "pat9301", "chart": "F261207-02", "feed_ids": [FID(3)], "plans": [], "rule": 9, "why": FI.WHY_NEW, "flags": [FI.FLAG_NO_FEED_DOB], "dob": "none", "for_william": True},
          {"pid": "pat9601", "chart": "F261207-03", "feed_ids": [FID(6)], "plans": [], "rule": 9, "why": FI.WHY_NEW, "flags": [], "dob": "real", "for_william": False}]
DEC14 = {KEY(4): answer(9, "", flags=[FI.FLAG_NOT_USED], cands=["pat9401", "pat9411"], will=True, ids=[FID(4)], why=FI.WHY_NEW_BESIDE), KEY(3, NODOB): answer(9, "", flags=[FI.FLAG_NO_FEED_DOB], dob="none", will=True, ids=[FID(3)], why=FI.WHY_NEW),
         KEY(6): answer(9, "", ids=[FID(6)], why=FI.WHY_NEW)}
P14 = [msg(4, "20261207"), msg(3, "20261207", NODOB), msg(6, "20261207")]; NEW14 = {KEY(4): "pat9402", KEY(3, NODOB): "pat9301", KEY(6): "pat9601"}
FOUND14 = {KEY(4): answer(1, "pat9402", cands=["pat9401", "pat9402", "pat9411"], ev=["mrn"], ids=[FID(4)]), KEY(3, NODOB): answer(1, "pat9301", cands=["pat9301"], ev=["mrn"], dob="none", ids=[FID(3)]), KEY(6): answer(1, "pat9601", cands=["pat9601"], ev=["mrn"], ids=[FID(6)])}
def cut_then_next(label, keep_match=True, made=MADE14, second_stop=""):
    """run 1 is cut in its import step, after the new-chart step made the charts and wrote its register; run 2 reads the same file under a new stamp and finds each chart by its Claimocity id.
    -> (workspace, clone, run 1 with what it left behind, run 2, a function that starts one more run - with a new file in the inbox, so that it has something to read)"""
    w_, r_, mreg_ = sandbox(label, ["20261207a.hl7"], ws_map={})
    o1, c1, e1 = driver_run(w_, r_, ARGS(S14a), pipe(w_, S14a, decided=DEC14, newcharts=NEW14, made=made, stop="claimocity_import.py", parsed=P14))
    left = {"identity": ident(w_, S14a), "digest": digest(w_, S14a), "files": dict(ingest(w_).get("files") or {}), "new charts": len((rd(w_, "registers", "feed_newcharts_%s.json" % S14a) or {}).get("created") or [])}      # what run 1 left behind
    if not keep_match and os.path.exists(os.path.join(w_, "feed_match_%s.json" % S14a)): os.remove(os.path.join(w_, "feed_match_%s.json" % S14a))      # a fresh container: the match file never leaves the workspace it was written in
    def nxt(stamp, newfile="", stop=""):
        if newfile: open(os.path.join(w_, "inbox", "claimocity", newfile), "w").write("MSH|invented\n")
        return driver_run(w_, r_, ARGS(stamp), pipe(w_, stamp, decided=FOUND14, parsed=P14, stop=stop))
    o2, c2, e2 = nxt(S14b, stop=second_stop)
    return w_, r_, (o1, e1, left), (o2, e2), nxt
w, r, _r1, _r2, _next = cut_then_next("cut_run"); D14 = digest(w, S14b)
check("14a the run that was cut: the charts are made and its new-chart register holds the rows for William, but it wrote no identity register and no digest, and the file is not registered",
      lambda: _r1[1] == "" and "STEP FAILED: import" in _r1[0] and _r1[2] == {"identity": None, "digest": [], "files": {}, "new charts": 3}, lambda: _r1)
check("14b the NEXT run - which finds each new chart by its Claimocity id and makes none - says at the top of ITS digest what the cut run never said: the new chart beside same-name charts with the question and those charts, "
      "and the new chart without a birth date that needs a face sheet; each names the stamp of the run that made the chart. The plain new chart is not a line",
      lambda: _r2[1] == "" and len(has(top(D14), S14a, "new chart pat9402 was made beside 2 same-name chart(s) (pat9401, pat9411)", "same person or not?")) == 1 and len(has(top(D14), S14a, "new chart pat9301 was made", "face sheet needed")) == 1
      and not has(D14, "pat9601 was made") and len(has(D14, "0 new chart(s) made")) == 1, lambda: (_r2[1], _r2[0][-500:], top(D14)))
check("14c ... and it is said ONCE: that run writes the identity register the cut run did not (its rows from the new-chart register, marked with the stamp that said them), so the run after it says nothing of it again",
      lambda: (lambda reg, third: (reg or {}).get("recovered_by") == S14b and sorted(p["chart"] for p in reg["patients"]) == ["pat9301", "pat9402", "pat9601"] and all(set(p) >= set(FI.PHI_FREE_FIELDS) | {"feed_ids", "chart", "status", "new_chart"} for p in reg["patients"])
               and third[2] == "" and "RESULT stamp" in third[0] and len(digest(w, S14c)) > 5 and not has(digest(w, S14c), "same person or not?") and not has(digest(w, S14c), "face sheet needed"))(ident(w, S14a), _next(S14c, "20261208a.hl7")), lambda: (ident(w, S14a), top(digest(w, S14c))))
w2, r2, _q1, _q2, _n2 = cut_then_next("cut_run_fresh", keep_match=False); D14f = digest(w2, S14b)
check("14d in a fresh container the cut run's match file is gone (it never leaves its workspace) and with it the list of the same-name charts: the question is still asked at the top - it says where the charts are named - and the face sheet is still asked for",
      lambda: _q2[1] == "" and len(has(top(D14f), S14a, "new chart pat9402 was made beside same-name charts", "same person or not?")) == 1 and len(has(top(D14f), S14a, "new chart pat9301 was made", "face sheet needed")) == 1 and not has(top(D14f), "beside 0 same-name"),
      lambda: (_q2[1], top(D14f)))
OLD14 = [{"pid": "pat9402", "chart": "F261207-01", "feed_ids": [FID(4)], "plans": []}, {"pid": "pat9301", "chart": "F261207-02", "feed_ids": [FID(3)], "plans": [], "respparty_named": True}]
w3, r3, _o1, _o2, _n3 = cut_then_next("cut_run_old", made=OLD14)
check("14e the new-chart registers written before 11/25/2026 (18 on main, none with an identity register beside it) carry no rule and no word for William: nothing is said for them and no identity register is written for their stamp",
      lambda: _o2[1] == "" and ident(w3, S14a) is None and not has(digest(w3, S14b), S14a), lambda: (_o2[1], ident(w3, S14a), top(digest(w3, S14b))))
w4, r4, _d1, _d2, _n4 = cut_then_next("cut_run_no_digest", second_stop="claimocity_report.py"); _i4 = ident(w4, S14a); _d3 = _n4(S14c, "20261208a.hl7")
check("14h ... and it is said UNTIL a digest stands: a next run whose report step fails writes no digest - its log carries the two lines, each ending TOP OF THE REPORT, but it does NOT write the cut run's identity register; "
      "the run after it says them at the top of its digest and writes that register then",
      lambda: _d2[1] == "" and "[report] exit 1" in _d2[0] and digest(w4, S14b) == [] and _i4 is None and len([l for l in _d2[0].splitlines() if l.startswith("from the run of stamp %s" % S14a) and l.endswith("TOP OF THE REPORT")]) == 2
      and _d3[2] == "" and len(has(top(digest(w4, S14c)), S14a, "new chart pat9402 was made", "same person or not?")) == 1 and len(has(top(digest(w4, S14c)), S14a, "new chart pat9301 was made", "face sheet needed")) == 1
      and (ident(w4, S14a) or {}).get("recovered_by") == S14c, lambda: (_d2[1], _d2[0][-600:], _i4, top(digest(w4, S14c)), (ident(w4, S14a) or {}).get("recovered_by")))
w, r, mreg = sandbox("no_identity", ["20261207a.hl7"], ws_map={}); os.makedirs(os.path.join(w, "registers", "feed_identity_%s.json" % S14a))      # a folder where the register belongs: it cannot be written
o, calls, e = driver_run(w, r, ARGS(S14a), pipe(w, S14a, decided=DEC14, newcharts=NEW14, made=MADE14, parsed=P14)); D14n = digest(w, S14a)
check("14f a run whose identity register cannot be written: the driver says so for the top of the report and goes on, and the digest - which has no 'Which chart' section then - still asks at the top what is for William about this batch's new charts, "
      "from the new-chart register, and each line says that the identity register does not list the chart (until then the question stood in no digest)",
      lambda: e == "" and len(said(o, "IDENTITY REGISTER NOT WRITTEN")) == 1 and said(o, "IDENTITY REGISTER NOT WRITTEN")[0].endswith("TOP OF THE REPORT") and "RESULT stamp" in o
      and len(has(top(D14n), "new chart pat9402 was made beside same-name charts", "same person or not?", "identity register")) == 1 and len(has(top(D14n), "new chart pat9301 was made", "face sheet needed", "identity register")) == 1
      and not has(D14n, "pat9601 was made"), lambda: (e, said(o, "IDENTITY"), top(D14n)))
w, r, mreg = sandbox("identity_no_rows", ["20261207a.hl7"], ws_map={})
_odd14 = {KEY(5): dict(answer(0, "", status="AMBIGUOUS", will=True, ids=[FID(5)], why=FI.WHY_DISAGREE), decided_for=[[FID(5)]])}      # an entry whose list of ids holds a list: the rows of the register cannot be built from it
o, calls, e = driver_run(w, r, ARGS(S14a), pipe(w, S14a, decided=_odd14, parsed=[msg(5, "20261207")])); I14r = ident(w, S14a) or {}; D14r = digest(w, S14a)
check("14f2 a run whose which-chart ROWS cannot be built (an entry of the match file is not what it should be): the register is still written - without a row of a patient, and its own line says so - "
      "so the driver's lines and the file that is kept back reach the digest's top (without it the digest had no word of either)",
      lambda: e == "" and len(said(o, "IDENTITY REGISTER NOT WRITTEN")) == 1 and I14r.get("patients") == [] and I14r.get("not_registered") == ["20261207a.hl7"]
      and len([n_ for n_ in I14r.get("notes") or [] if n_.startswith("IDENTITY REGISTER NOT WRITTEN") and "no row of a patient" in n_]) == 1
      and len(has(top(D14r), "IDENTITY REGISTER NOT WRITTEN", "no row of a patient")) == 1 and len(has(top(D14r), "NOT REGISTERED", "20261207a.hl7")) == 1, lambda: (e, said(o, "IDENTITY"), I14r, top(D14r)))
check("14g the three flags the digest reads from a row of the new-chart register are the identity rule's own words (the row carries them as that step wrote them)", all(x in RSRC for x in (FI.FLAG_NOT_USED, FI.FLAG_CUT, FI.FLAG_TWO_DATES)))

# ---- 15. a visit AdvancedMD refuses at entry (the verification; the same on main until then) ----------------------------------------------------------------
# What it found: a visit AdvancedMD refused left a failed row, its file was registered as done, it was never read again and never retried (the retry of step
# (c1) retries two kinds of skipped row only), and the digest named it in a body line. Now every failed row stands at the top of the digest. Where the refusal
# was of the visit itself - the import's row 'addvisit: ...': nothing was made in AdvancedMD - the file is not registered: the next start reads it again and
# the import tries once more (a visit entered by hand meanwhile answers 'already'). A row that says a visit WAS made, or that nobody knows what AdvancedMD
# kept, never keeps a file back: reading it again would make a second empty visit in every run - it is for William, at the top.
S15, S15b, S15c = "20261209T1240Z", "20261209T1840Z", "20261210T1240Z"; FA, FB, FC = "2026" + "1207a.hl7", "2026" + "1208b.hl7", "2026" + "1209c.hl7"      # three days: the driver ties a message to its file by the day the file is named for
w, r, mreg = sandbox("refused", [FA, FB, FC], ws_map=MAP9)
for f_, n_ in ((FA, 1), (FB, 2), (FC, 3)): open(os.path.join(w, "inbox", "claimocity", f_), "w").write(hl7(n_))
o, calls, e = driver_run(w, r, ARGS(S15), pipe(w, S15, refuse=(FID(1),), half=(FID(2),))); _l15 = said(o, "NOT REGISTERED:", "refused at entry"); D15 = digest(w, S15)
check("15a a visit AdvancedMD refused outright (nothing of it was made) keeps its file unregistered - until 11/25/2026 the file was registered as done and the visit was never tried again; a visit that WAS made and whose charges were refused does not "
      "(reading that file again would make a second empty visit in every run), nor does a visit that went in",
      lambda: e == "" and entered(w, S15) == [(FID(3), "pat9103")] and sorted(ingest(w).get("files") or {}) == [FB, FC], lambda: (e, o[-700:], entered(w, S15), sorted(ingest(w).get("files") or {})))
check("15b ONE line says it for the top of the report - the file, the chart, that nothing was made and that the next start tries again - and the RESULT line counts the file",
      lambda: len(_l15) == 1 and _l15[0].startswith("NOT REGISTERED: 1 file(s) hold a visit AdvancedMD refused at entry") and FA in _l15[0] and "pat9101" in _l15[0] and FB not in _l15[0] and _l15[0].endswith("TOP OF THE REPORT")
      and re.search(r"RESULT stamp %s: files 3, messages 3, visits created 1, skipped 0, failed 2, 1 file\(s\) NOT registered \(a visit AdvancedMD refused at entry" % S15, o) is not None and (ident(w, S15) or {}).get("not_registered_refused") == [FA], lambda: (_l15, result(o), ident(w, S15)))
check("15c the digest names BOTH failed visits at the top (they stood in a body line only): the refused one with its chart, date and code and that its file is read again; the one whose entry did not finish with the visit AdvancedMD made - for William, no routine sends it again",
      lambda: len(has(top(D15), "1 visit(s) AdvancedMD REFUSED at entry", "pat9101 11/30/2026 99308", "NOT REGISTERED", FA)) == 1 and len(has(top(D15), "1 visit(s) whose entry did NOT FINISH", "pat9102 11/30/2026 99308", "vst8802", "William")) == 1
      and len(has(D15, "2 visit(s) FAILED")) == 1, lambda: top(D15))
o, calls, e = driver_run(w, r, ARGS(S15b), pipe(w, S15b))
check("15d the next start reads that one file again; AdvancedMD takes the visit now - it is entered once and the file is registered",
      lambda: e == "" and "1 new file(s) of 3" in o and entered(w, S15b) == [(FID(1), "pat9101")] and sorted(ingest(w).get("files") or {}) == [FA, FB, FC] and "NOT REGISTERED" not in o, lambda: (e, o[-500:], entered(w, S15b)))
w, r, mreg = sandbox("refused_closed", [FA], ws_map=MAP9); open(os.path.join(w, "inbox", "claimocity", FA), "w").write(hl7(1))
o, calls, e = driver_run(w, r, ARGS(S15) + ("--register-anyway", FA), pipe(w, S15, refuse=(FID(1),)))
check("15e a visit AdvancedMD will never take is ended the same way as a message that cannot be read: on William's word, --register-anyway <file> - registered, with ONE line for the top that names the chart whose visit is given up",
      lambda: e == "" and FA in (ingest(w).get("files") or {}) and len(said(o, "REGISTERED ON WILLIAM'S WORD", FA, "pat9101")) == 1 and not said(o, "NOT REGISTERED:"), lambda: (e, o[-500:]))
D15e = digest(w, S15); I15e = ident(w, S15) or {}
check("15e2 ... and the digest says it of the refused visit ONLY: its line at the top names the chart and the file registered on William's word - and no line speaks of a feed message that could not be read "
      "(the digest took any file registered on his word for one with a message without a Claimocity id, and said so at the top)",
      lambda: len(has(top(D15e), "1 visit(s) AdvancedMD REFUSED at entry", "pat9101", "REGISTERED ON WILLIAM'S WORD", FA)) == 1 and not has(D15e, "could not be read") and not has(D15e, "no Claimocity id")
      and I15e.get("registered_anyway") == [FA] and I15e.get("registered_anyway_refused") == [FA] and I15e.get("registered_anyway_unreadable") == [], lambda: (top(D15e), {k: v for k, v in I15e.items() if "regist" in k}))
FD = "2026" + "1210d.hl7"
w, r, mreg = sandbox("both_closed", [FA, FD], ws_map=MAP9); open(os.path.join(w, "inbox", "claimocity", FA), "w").write(hl7(1)); open(os.path.join(w, "inbox", "claimocity", FD), "w").write(hl7(2) + ends_in(hl7x(3, lines=[ft1("99309", keep=8)])))
o, calls, e = driver_run(w, r, ARGS(S15) + ("--register-anyway", FA + "," + FD), pipe(w, S15, refuse=(FID(1),))); D15g = digest(w, S15); I15g = ident(w, S15) or {}
check("15e3 one file given up for a refused visit and one for a message that cannot be read, in one start: both are registered, and each of the digest's two lines names its OWN file - the refused visit's line not the file of the broken message, and the other way round",
      lambda: e == "" and sorted(ingest(w).get("files") or {}) == [FA, FD] and I15g.get("registered_anyway") == [FA, FD] and I15g.get("registered_anyway_refused") == [FA] and I15g.get("registered_anyway_unreadable") == [FD]
      and (lambda a_, b_: len(a_) == 1 and FA in a_[0] and FD not in a_[0] and len(b_) == 1 and FD in b_[0] and FA not in b_[0])(has(top(D15g), "1 visit(s) AdvancedMD REFUSED at entry", "REGISTERED ON WILLIAM'S WORD"), has(top(D15g), "1 feed message(s) could not be read", "REGISTERED ON WILLIAM'S WORD")),
      lambda: (e, o[-400:], {k: v for k, v in I15g.items() if "regist" in k}, top(D15g)))
L15f, e15f = report_run("failed_kinds", S7, [vrow("pat9101", "vst7001", "11/29/2026", ["99308"])], failed=[
    {"feed_id": FID(2), "pid": "pat9102", "info": {"dos": "11/29/2026", "cpts": ["99309"]}, "lines": [], "err": "addvisit: <Fault>refused for " + NAME(2) + "</Fault>"},
    {"feed_id": FID(3), "pid": "pat9103", "lines": [["99232", "11/28/2026", "X"]], "err": "TimeoutError: read timed out"}, "not a row"])
check("15f a batch without an identity register (the retry's own batch): the refused visit is still at the top, without a word about a file - and a failed row that says nothing of a visit (an error while it was entered) is named by its chart, with the lines the feed showed; "
      "AdvancedMD's own words are never printed",
      lambda: e15f == "" and len(has(top(L15f), "1 visit(s) AdvancedMD REFUSED at entry", "pat9102 11/29/2026 99309")) == 1 and not has(top(L15f), "REFUSED at entry", "NOT REGISTERED") and len(has(top(L15f), "1 visit(s) whose entry did NOT FINISH", "pat9103", "99232")) == 1
      and not any(s_ in "\n".join(L15f) for s_ in secrets(2)), lambda: (e15f, top(L15f)))

# ---- 16. the reconciliation never says 'already in AMD' for a visit that was not entered (the verification) ----------------------------------------------
# What it found: the import takes a message's chart from the entry of the message's OWN name-and-date key; the reconciliation took it from any entry that named
# the Claimocity id (and from the patient map, which has learned the batch by then) and called a message without a created or skipped row 'already'. An id with
# a chart through one key whose other message stood under a key with no chart was recorded as 'visit already on the chart' - no such visit was on any chart.
S16 = "20261211T1240Z"
def recon_run(label, parsed, matchf, created, pmap, skipped=(), unreadable=None):
    """the REAL reconciliation helper, started as its own program over a throwaway workspace -> (exit code, what it printed, its register)"""
    d = os.path.join(TMP, "recon_" + label); os.makedirs(os.path.join(d, "registers"))
    json.dump(parsed, open(os.path.join(d, "feed_parsed_%s.json" % S16), "w")); json.dump(matchf, open(os.path.join(d, "feed_match_%s.json" % S16), "w")); json.dump(pmap, open(os.path.join(d, "registers", "claimocity_patient_map.json"), "w"))
    json.dump({"created": created, "skipped": list(skipped), "failed": []}, open(os.path.join(d, "registers", "feed_import_%s.json" % S16), "w"))
    if unreadable is not None: json.dump(unreadable, open(os.path.join(d, "registers", "feed_unreadable_%s.json" % S16), "w"))
    r_ = subprocess.run([sys.executable, RECON, S16, "--ws", d], capture_output=True, text=True)
    return r_.returncode, (r_.stdout + r_.stderr).strip(), rd(d, "registers", "feed_recon_%s.json" % S16)
def m16(n, f, d8=None, fid=None, dos="20261127", prov="DOC TOR"): return dict(msg(n, f, dob=d8, fid=fid), FT1=[{"cpt": "99308", "dos": dos, "dx": "I10", "units": "1"}], provider=prov)      # d8: the birth date the feed sent (the placeholder, or none = the patient's own)
PAR16 = [m16(1, "20261128", dos="20261127"), m16(1, "20261129", d8=P1900, dos="20261128"), m16(1, "20261129", d8=P1900, fid=TWIN, dos="20261128"), m16(2, "20261129", dos="20261101")]
MAT16 = {KEY(1): dict(answer(2, "pat9301", ids=[FID(1)]), by_id={FID(1): "pat9301"}), KSH: dict(_none, by_id={}), KEY(2): {"status": "FOUND", "resolved": "pat9202", "feed_ids": [FID(2)], "by_id": {FID(2): "pat9202"}, "rule": "map"}}
c16, o16, R16 = recon_run("own_key", PAR16, MAT16, [vrow("pat9301", "vst7001", "11/27/2026", ["99308"], feed_id=FID(1))], {FID(1): "pat9301", FID(2): "pat9202"})
_row = lambda rc, fid, d: next((x for x in (rc or {}).get("rows", []) if x["f"] == fid and x["d"] == d), {})
check("16a a Claimocity id that has a chart through one name-and-date key while its OTHER message stands under a key with no chart: that message is recorded as not entered - no chart, waiting - and never as 'visit already on the chart' "
      "(the record goes to main and to the page that is to show that every charge of the feed is in AdvancedMD)",
      lambda: c16 == 0 and _row(R16, FID(1), "2026-11-27").get("s") == "entered" and _row(R16, FID(1), "2026-11-28").get("s") == "nochart" and _row(R16, FID(1), "2026-11-28").get("p") is None and "not entered" in _row(R16, FID(1), "2026-11-28").get("why", "")
      and _row(R16, TWIN, "2026-11-28").get("s") == "nochart" and R16["counts"]["already"] == 1 and R16["counts"]["nochart"] == 2 and "1 already in AMD" in o16 and "2 no chart" in o16, lambda: (c16, o16, (R16 or {}).get("rows")))
check("16b ... a message of a known patient with no row in this batch's import register, whose own key does name its chart, is still 'already' (an earlier batch entered that visit)",
      lambda: _row(R16, FID(2), "2026-11-01").get("s") == "already" and _row(R16, FID(2), "2026-11-01").get("p") == "pat9202", lambda: _row(R16, FID(2), "2026-11-01"))
c16c, o16c, R16c = recon_run("old_match", PAR16[:1] + PAR16[3:], {KEY(1): {"status": "FOUND", "resolved": "pat9301", "feed_ids": [FID(1)]}}, [], {FID(1): "pat9301", FID(2): "pat9202"})
check("16c a match file from before the charts were named per Claimocity id, and a message whose key the match file does not hold at all (a known patient in an older batch): read as before - the key's chart, else the patient map's",
      lambda: c16c == 0 and [x["s"] for x in R16c["rows"]] == ["already", "already"] and [x["p"] for x in R16c["rows"]] == ["pat9301", "pat9202"], lambda: (c16c, o16c, (R16c or {}).get("rows")))
c16d, o16d, R16d = recon_run("clinician", [m16(1, "20261128", prov="9"), m16(2, "20261128", prov="")], {KEY(1): dict(answer(2, "pat9301", ids=[FID(1)]), by_id={FID(1): "pat9301"})}, [vrow("pat9301", "vst7001", "11/27/2026", ["99308"], feed_id=FID(1))], {FID(1): "pat9301"},
                             unreadable={"stamp": S16, "messages": [{"file": "20261128", "message": 3, "why": W_CUT}, {"file": "20261128", "message": 4, "why": W_NOCHARGE}]})
check("16d a message whose clinician field carries a number and no name no longer ends the reconciliation with an error (the register of that batch was then not written at all); and the register counts the messages of the batch that could not be read - they have no row",
      lambda: c16d == 0 and R16d is not None and len(R16d["rows"]) == 2 and R16d["rows"][0]["prov"] == "Clinician on file" and R16d["counts"].get("unreadable") == 2 and "2 message(s) could not be read" in o16d, lambda: (c16d, o16d[-400:], R16d))

# ---- 6. the privacy gate leaves this file and the driver alone --------------------------------------------------------------------------------------
sys.path.insert(0, os.path.join(ROOT, "tools", "mirror")); import phi_gate as _pg
for rel in ("tools/selftest/test_feed_driver.py", "scripts/helpers/claimocity_ingest.py", "scripts/helpers/claimocity_report.py", "scripts/helpers/feed_parse_dft_1028.py", "scripts/helpers/claimocity_recon.py",
            "scripts/helpers/claimocity_gcs.py", "scripts/helpers/claimocity_helpers_current.py"):
    _t = open(os.path.join(ROOT, rel)).read(); _r = _pg.redact(_t, {}, code=True)
    check("6 the privacy gate's tree rules leave %s exactly as it is (every invented value is put together at run time)" % rel, _r == _t, [(a, b) for a, b in zip(_t.splitlines(), _r.splitlines()) if a != b][:2])

# ... and the registers the driver, the parse step and the reconciliation wrote in the runs above (they travel to main, a public repository): every identity register with the
# driver's own lines and the lists of files it keeps back, every count of unreadable messages, every reconciliation register and file register of the throwaway workspaces
_regs = [os.path.join(TMP, d_, "ws", "registers", f_) for d_ in sorted(os.listdir(TMP)) if os.path.isdir(os.path.join(TMP, d_, "ws", "registers")) for f_ in sorted(os.listdir(os.path.join(TMP, d_, "ws", "registers")))
         if os.path.isfile(os.path.join(TMP, d_, "ws", "registers", f_)) and (f_.startswith(("feed_identity_", "feed_unreadable_", "feed_recon_")) and f_.endswith(".json") or f_ == "claimocity_ingest.json")]
_texts = {f_: open(f_).read() for f_ in _regs}; _changed = [f_[len(TMP):] for f_, x_ in _texts.items() if _pg.redact(x_, {}) != x_]
_docs = [json.loads(x_) for f_, x_ in _texts.items() if "feed_identity_" in f_]
check("6b the privacy gate leaves every such register of this self-test exactly as it was written - the driver's notes, the files it keeps back and the words 'registered on William's word', the parse step's fixed sentences, the reconciliation's reasons (%d registers)" % len(_regs),
      len(_regs) >= 60 and not _changed and sum(1 for d_ in _docs if d_.get("notes")) >= 5 and any(d_.get("not_registered_unreadable") for d_ in _docs) and any(d_.get("not_registered_refused") for d_ in _docs)
      and any(d_.get("registered_anyway") for d_ in _docs) and any(d_.get("recovered_by") for d_ in _docs) and any("each" in p_ for d_ in _docs for p_ in d_.get("patients") or []) and any("note" in v_ for f_, x_ in _texts.items() if f_.endswith("claimocity_ingest.json") for v_ in json.loads(x_).get("files", {}).values()),
      lambda: (len(_regs), _changed[:5], sum(1 for d_ in _docs if d_.get("notes"))))

# ---- 17. the wiring of the identity fixes into the driver (11/25/2026, the integration of the verification's fixes) ----------------------------------------
# (a) by_proof: on a name-and-date key several Claimocity ids share that got no chart of its own, the resolve step names for each id that has PROOF of its own
#     chart that chart ("by_proof") and that id's own answer ("proof_rows"). The driver takes them into the charts it names per id - the import asks by the
#     message's own id - and gives each such id a row of its own in the identity register. Until then such ids had no chart, run after run.
S17 = "20261130T1240Z"; F17 = S17[:8]; TWIN17 = FID(3)[:22] + "ee"; K17 = KEY(3, "")      # (F17: the file date, taken from the stamp - the privacy gate rewrites a date that stands right behind an empty birth date)
def prow(fid, chart, rule=1): return {"feed_ids": [fid], "chart": chart, "rule": rule, "why": FI.WHY[rule], "flags": [], "candidates": [], "evidence": [], "feed_dob": "none", "for_william": False}
def proof_run(label, why, by, rows, will, left=None):
    """left: the ids the resolve step leaves WITHOUT a chart - its entry names only those under decided_for as soon as one id has proof and another has none
    (feed_ids keeps every id of the key); None = every id is named there, as when all of them have proof"""
    w_, r_, mreg_ = sandbox(label, ["20261130a.hl7"])
    e_ = dict(answer(0, "", status="AMBIGUOUS", dob="none", will=will, ids=[FID(3), TWIN17], why=why), by_proof=by, proof_rows=rows)
    if left is not None: e_["decided_for"] = list(left)
    o_, calls_, err_ = driver_run(w_, r_, ARGS(S17), steps(w_, S17, [msg(3, F17, dob=""), msg(3, F17, dob="", fid=TWIN17)], {K17: e_}))
    return w_, o_, err_
w, o, e = proof_run("proof_both", FI.WHY_EACH_PROOF, {FID(3): "pat9301", TWIN17: "pat9302"}, [prow(FID(3), "pat9301"), prow(TWIN17, "pat9302", 4)], False)
_rows17 = sorted((p_.get("feed_ids"), p_.get("chart"), p_.get("rule")) for p_ in (ident(w, S17) or {}).get("patients") or [])
check("17a two Claimocity ids under one name and no birth date, EACH with proof of its own chart (by_proof): the driver names each id with its own chart for the import, the map learns both, the file is registered - until then neither had a chart, run after run",
      lambda: e == "" and by_id(w, S17, K17) == {FID(3): "pat9301", TWIN17: "pat9302"} and pm(w) == {FID(3): "pat9301", TWIN17: "pat9302"} and "NOT REGISTERED" not in o
      and sorted(ingest(w).get("files") or {}) == ["20261130a.hl7"], lambda: (e, o[-500:], match(w, S17).get(K17), pm(w)))
check("17b ... the identity register carries ONE row for each such id - its own chart, its own rule, the rule's fixed words - and no row for the key itself (it has nothing more to say); nothing of a name or a date",
      lambda: _rows17 == [([FID(3)], "pat9301", 1), ([TWIN17], "pat9302", 4)] and not any(x in json.dumps(ident(w, S17)) for x in secrets(3)), lambda: (_rows17, ident(w, S17)))
w, o, e = proof_run("proof_one", FI.WHY_SHARED, {FID(3): "pat9301"}, [prow(FID(3), "pat9301")], True, left=[TWIN17])
_rows17 = sorted((tuple(p_.get("feed_ids") or []), p_.get("chart"), p_.get("rule")) for p_ in (ident(w, S17) or {}).get("patients") or [])
check("17c ... when only ONE of the ids has proof (the resolve step then names only the OTHER id under decided_for) the id with proof still gets its chart and its row - it got neither at first: the driver read decided_for alone - and the other stays without a chart: the key's own row names that id with NO chart (never the first id's chart), the file is not registered, and the map learns the one id only",
      lambda: e == "" and by_id(w, S17, K17) == {FID(3): "pat9301"} and pm(w) == {FID(3): "pat9301"} and _rows17 == [((FID(3),), "pat9301", 1), ((TWIN17,), "", 0)]
      and (ident(w, S17) or {}).get("not_registered") == ["20261130a.hl7"] and sorted(ingest(w).get("files") or {}) == [], lambda: (e, o[-600:], _rows17, match(w, S17).get(K17)))
w, o, e = proof_run("proof_one_all", FI.WHY_SHARED, {FID(3): "pat9301"}, [prow(FID(3), "pat9301")], True)
_rows17b = sorted((tuple(p_.get("feed_ids") or []), p_.get("chart"), p_.get("rule")) for p_ in (ident(w, S17) or {}).get("patients") or [])
check("17c2 ... the same when an entry names every id under decided_for: the key's own row shows NO chart for the ids it names (never the proven id's chart for all)",
      lambda: e == "" and by_id(w, S17, K17) == {FID(3): "pat9301"} and _rows17b == [((FID(3),), "pat9301", 1), ((FID(3), TWIN17), "", 0)], lambda: (e, _rows17b))
w, o, e = proof_run("proof_odd", FI.WHY_EACH_PROOF, {FID(3): NAME(3), TWIN17: "pat9302", "": "pat9303", 7: "pat9304"}, [dict(prow(FID(3), "pat9301"), why="invented words " + NAME(3)), prow(TWIN17, "pat9302"), "odd", {"feed_ids": [TWIN17], "chart": NAME(3)}], False)
check("17d ... only a chart id is taken from by_proof and only a row in the rule's fixed words from proof_rows: a name where a chart id should stand, an empty id, a row with invented words - none of them is used or reaches the register",
      lambda: e == "" and by_id(w, S17, K17) == {TWIN17: "pat9302"} and not any(x in json.dumps(ident(w, S17)) for x in secrets(3)) and not any(x in o for x in secrets(3)), lambda: (e, by_id(w, S17, K17), ident(w, S17)))
# (b) the charts William has called duplicates (registers/feed_duplicate_charts.json - claimocity_match.py never offers such a chart, the proper one stands in
#     its place): the file's home is main, as for his standing word 'same person' - the workspace's copy is replaced at every start
def dup_case(label, ws_doc, main_doc, clone=True, live=True):
    w_, r_, mreg_ = sandbox(label, ["20261126a.hl7"], ws_map={FID(1): "pat9001"})
    if main_doc is not None: open(os.path.join(mreg_, "feed_duplicate_charts.json"), "w").write(main_doc if isinstance(main_doc, str) else json.dumps(main_doc))
    if ws_doc is not None: json.dump(ws_doc, open(os.path.join(w_, "registers", "feed_duplicate_charts.json"), "w"))
    if not clone: shutil.rmtree(os.path.join(os.path.dirname(os.path.dirname(r_)), "practices"))
    o_, calls_, e_ = driver_run(w_, r_, ARGS(S1, live=live), steps(w_, S1, [msg(1, "20261126")], {}))
    return e_, [l for l in o_.splitlines() if l.startswith("DUPLICATE CHARTS FILE:")], rd(w_, "registers", "feed_duplicate_charts.json")
DUP_M = {"pat9777": {"proper": "pat9001", "approved_by": "William 11/26/2026 (board)"}}; DUP_W = {"pat9555": {"proper": "pat9002", "approved_by": "William 11/20/2026 (board)"}}
check("17e the charts William called duplicates (registers/feed_duplicate_charts.json): the repository's file is copied into the workspace, whole, at every start - an entry taken out on main does not come back from a restored workspace; with no such file on main the copy is emptied without a word (no chart counts as a duplicate)",
      lambda: dup_case("dup_main", DUP_W, DUP_M) == ("", [], DUP_M) and dup_case("dup_new", None, DUP_M) == ("", [], DUP_M) and dup_case("dup_none", DUP_W, None) == ("", [], {}) and dup_case("dup_dry", DUP_W, DUP_M, live=False) == ("", [], DUP_M),
      lambda: (dup_case("dup_main_x", DUP_W, DUP_M), dup_case("dup_none_x", DUP_W, None)))
_d1 = dup_case("dup_half", DUP_W, '{"pat9777": {"proper": "pat9001",'); _d2 = dup_case("dup_list", DUP_W, ["pat9777"])
check("17f ... when the repository's file cannot be read or is no JSON object the copy is emptied and ONE line says so for the top of the report (no chart counts as a duplicate in that run - a restored workspace's older list never decides)",
      lambda: all(c[0] == "" and c[2] == {} and len(c[1]) == 1 and "no chart counts as a duplicate in this run" in c[1][0] and c[1][0].endswith("TOP OF THE REPORT") for c in (_d1, _d2)), lambda: (_d1, _d2))
check("17g ... only with NO clone at all does the workspace's copy stay as it is", lambda: dup_case("dup_noclone", DUP_W, None, clone=False) == ("", [], DUP_W), lambda: dup_case("dup_noclone_x", DUP_W, None, clone=False))

print("\n%d check(s): %d ok, %d FAIL" % (OK[0] + len(FAILS), OK[0], len(FAILS)))
sys.exit(1 if FAILS else 0)
