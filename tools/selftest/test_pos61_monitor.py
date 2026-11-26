#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the place-of-service 61 payment monitor, 11/25/2026)
# Decides: nothing. Loads scripts/helpers/pos61_monitor.py INSIDE this process with stand-in amd / txh modules and a throwaway registers
#   folder (no AdvancedMD, no network, no patient data - every chart, visit, charge, date, dollar and name here is invented) and proves what
#   William asked for on 11/25/2026 ("let us monitor them to make sure they pay and dont deny"):
#     - the monitor reads the import registers and finds the inpatient-rehab visits: those entered at place of service 61 (the new group) and
#       the rehab-stay visits kept at 21 (the comparison group); every other row is left alone and never read;
#     - ONE read of the visit's own history per visit and run (txh.fetch_visit), nothing else of AdvancedMD is ever called, --dry is the same
#       as a live run, and nothing is read at all - not even a login - while there is no rehab visit;
#     - what a read shows: paid (the payer's dollars, never the patient's), denied (a $0 payment line with a reason code that denies), open,
#       billed and unanswered for over 30 days, not billed, written off unpaid, voided, a $0 answer that carries only cost-share /
#       contractual codes, a denial that was paid later, a line riding with the visit;
#     - the printed lines: REHAB AT 61 with the fixed history of place of service 21 beside it, the comparison group, the dollars per code,
#       and one TOP OF THE REPORT line for every denied visit at 61 and for every visit paid under 60% of the 21 average for its code;
#     - a visit that cannot be read is counted and named and never stops the run; three reads in a row without an answer, or a login that
#       fails, end the reading for this run; --max and --seconds hold the reads of one run and the next run reads the rest first (the visits
#       asked for longest ago go first, so a visit that never answers holds up nobody); a run stopped from outside in the middle of a read
#       still prints its lines and writes its register;
#     - (review fixes, 11/25/2026) a run WITHOUT the register of the run before - or with one that is more than two days old - does not read
#       the same oldest visits every time: it starts at another place of the list each day, gets round to every visit, and says in a line
#       that its counts hold only what it read; a visit that is settled is read again on a slow turn (after 7 days, every fifth read of a
#       run), so a payment taken back later is seen - not never; per payer the NEWEST answer leads: a denial dated after that payer's
#       payment, and a denial of a payer that paid nothing (a second payer's after the first one paid), is a denied visit with its line at
#       the top - not an 'earlier denial' of a paid one; and a field that is not what it says carries nothing in: the sign of a stay is one
#       of the import's two, an id is the import's own, a carrier code has at most eight characters, a register is known by its stamp;
#     - a line is said from the day the monitor first sees the visit denied or paid low - whatever date AdvancedMD gives the payment;
#     - (verification of the pull request, 11/25/2026) a HOSPITAL visit that stands at 61 - the import named it when its stay's initial
#       visit reached the feed (the row's list hospital_at61) - is not counted among the rehab visits at 61, has a line of its own, and
#       a denial of it is worded as a visit to correct, never as the payer's answer to 'keep 61 or go back to 21' (section 13);
#     - the register registers/pos61_monitor.json holds chart ids, visit ids, dates of service, codes, carrier codes, reason codes and
#       dollars - never a name, a birth date or a member number, also when AdvancedMD's answer and an error's own words carry them.
# Run: python3 tools/selftest/test_pos61_monitor.py   (exit 1 on any failure)
import os, sys, json, types, tempfile, importlib.util, io, re, contextlib, shutil, time
import xml.etree.ElementTree as ET
# THIS SELF-TEST NEVER REACHES ADVANCEDMD OR ANY OTHER HOST. Every network route is closed here before anything else is loaded, and the
# helper is only ever loaded INSIDE this process with the stand-in modules below (it is never started as a program: scripts/helpers holds
# the real amd / txh, and a program started from that folder would load them).
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPER = os.path.join(ROOT, "scripts", "helpers", "pos61_monitor.py")
AMD_MODULES = ("amd", "resave", "txh", "void_tx", "deceased_guard", "freq1_visit", "move_to_ins", "ins_update", "stedi", "era_post", "manual_post", "payreasons")
FAILS = []; OKS = [0]
def check(name, cond, extra=None):
    """cond and extra are functions: a check that cannot even be worked out (the helper is not there yet) is a FAIL, never a crash."""
    try: ok = bool(cond()); why = ""
    except Exception as e: ok = False; why = "%s: %s" % (type(e).__name__, str(e)[:160])
    if not ok and not why and extra is not None:
        try: why = str(extra())[:700]
        except Exception as e: why = "(%s)" % type(e).__name__
    print(("ok   " if ok else "FAIL ") + name + (("  -> " + why) if (why and not ok) else ""))
    if ok: OKS[0] += 1
    else: FAILS.append(name)

# ---- invented identifiers that must never reach the register or a printed line (each is put together at run time, so no such value sits
#      in the repository and the privacy gate, which scrubs this file like any other before a commit, leaves the test alone) --------------
LAST_S = "QVORK" + "LEBANT"; FIRST_S = "ZELM" + "AVRO"; NAME_S = LAST_S + "," + FIRST_S         # AdvancedMD's LAST,FIRST form (the pieces are no words and nobody's name)
BORN_S = "03/04/" + "1941"                                                                    # a date that is nobody's date of service here
MBI_S = "2FH5" + "UF6NK84"; MEM_S = "H7741" + "90263"                                          # a Medicare number and a plan's own number
SECRETS = (LAST_S, FIRST_S, BORN_S, MBI_S, MEM_S)

# ---- stand-ins for the AdvancedMD modules (nothing here can reach AdvancedMD) ----------------------------------------------------------------
CALLS = []                                                             # every call the helper makes into the stand-ins, in order
STATE = {"login_raises": None}
HIST = {}                                                              # visit number -> its charge rows, or an exception to raise
amd = types.ModuleType("amd"); amd.STAND_IN = True
def _login(*a, **k):
    CALLS.append(("login",))
    if STATE["login_raises"]: raise STATE["login_raises"]
    return ("web", "token")
def _never(*a, **k): CALLS.append(("WRITE", a[:1])); raise AssertionError("the monitor must never send anything to AdvancedMD")
amd.login_cached = _login; amd.post = _never; amd.msg = _never; amd.rebill_charge = _never; amd.call = _never
txh = types.ModuleType("txh"); txh.STAND_IN = True
def pay(amount, date, carrier="FLO02", reasons=(), **more): return dict(more, amount=amount, date=date, carrier=carrier, reasons=list(reasons))
def chg(cid, code, fee, billed="", pays=(), ins="0.00", pat="0.00", carrier="FLO02", void="0", wos=(), **more):
    return dict(more, id="charge%s" % cid, proccode=code, fee=fee, billdate=billed, carrier=carrier, insbal=ins, patbal=pat, void=void, pays=list(pays), wos=list(wos))
def history(vnum, charges):
    """The answer of ONE gettxhistory read for a visit, as the real one is shaped: charge rows with their payment and write-off lines. Every
    row and every payment line carries what the real answer carries too - the patient's name, a birth date, plan numbers - so the checks
    below can prove that none of it is ever written or printed."""
    root = ET.Element("PPMDResults"); lst = ET.SubElement(ET.SubElement(root, "Results"), "chargelist")
    for c in charges:
        a = {k: str(v) for k, v in c.items() if k not in ("pays", "wos")}
        a.setdefault("visit", "vst%s" % vnum); a.setdefault("dos", "11/26/2026")
        a.update(patientname=NAME_S, patient=NAME_S, respname=NAME_S, subscribername=NAME_S, dob=BORN_S, payerinfo="MEDICARE PART B %s / %s" % (MBI_S, MEM_S), subscribernum=MEM_S, facname="HCA REHAB")
        ce = ET.SubElement(lst, "charge", a); pl = ET.SubElement(ce, "paymentlist"); wl = ET.SubElement(ce, "writeofflist")
        for i, p in enumerate(c["pays"]):
            pa = {k: str(v) for k, v in p.items() if k != "reasons"}; pa.update(id="pay%s%d" % (c["id"][6:], i), checknumber="CHK%s" % MEM_S, patientname=NAME_S, name=NAME_S, createtime=pa.get("createtime", pa.get("date", "")))
            pe = ET.SubElement(pl, "payment", pa); rl = ET.SubElement(pe, "payreasonlist")
            for code, amt in p["reasons"]: ET.SubElement(rl, "payreason", {"code": code, "amount": str(amt), "description": "reason text naming %s" % NAME_S})
        for w in c["wos"]: ET.SubElement(wl, "writeoff", dict({k: str(v) for k, v in w.items()}, patientname=NAME_S))
    return root
def _fetch_visit(pid, vid):
    CALLS.append(("fetch_visit", str(pid), str(vid)))
    h = HIST.get(str(vid), [])
    if isinstance(h, BaseException): raise h
    if callable(h): return h()
    return history(str(vid), h)
def _fetch(pid): CALLS.append(("fetch", str(pid))); raise AssertionError("the monitor reads ONE visit at a time, never a whole chart")
txh.fetch_visit = _fetch_visit; txh.fetch = _fetch
sys.modules.update({"amd": amd, "txh": txh})
M = None; LOAD_ERR = ""
try:
    spec = importlib.util.spec_from_file_location("pos61_monitor", HELPER); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    M.PAUSE = 0                                                        # the pause between two reads is for AdvancedMD, not for a self-test
except Exception as e: M = None; LOAD_ERR = "%s: %s" % (type(e).__name__, str(e)[:200])
SRC = open(HELPER).read() if os.path.exists(HELPER) else ""
check("the helper scripts/helpers/pos61_monitor.py is there and loads with the stand-in modules", lambda: M is not None, lambda: LOAD_ERR)
check("the stand-ins are what the helper holds: its amd and its txh are this test's, never the real ones", lambda: M.amd is amd and M.txh is txh and M.amd.STAND_IN and M.txh.STAND_IN)

# ---- a throwaway workspace with import registers as the import writes them --------------------------------------------------------------
TMP = tempfile.mkdtemp(prefix="pos61_")
def rehab(visit, chart, dos, cpts, initial, sign="new admission 1-2 days after an acute stay", kind=None, **more):
    """A register row of a rehab-stay visit entered at 61, as the spec's import writes it."""
    n = len(cpts); k = ["rehab"] * n if kind is None else kind
    return dict({"feed_id": "feedX%s" % chart[3:], "pid": chart, "visit": visit, "charges": ["charge%s%d" % (visit[3:], i) for i in range(n)], "fees": ["1.00"] * n, "at": "2026-11-26T12:41:00",
                 "dos": dos, "dos_lines": [dos] * n, "cpts": cpts, "fac": "fac67", "pos": "61", "pos_feed": "21", "pos_lines": ["61"] * n, "pos_why": ["inpatient rehab stay: " + sign] * n,
                 "pos_kind": k, "pos_err": "", "prof": "prof13", "admit": "20261126", "pos_stored": ["61"] * n, "stay": {"kind": "rehab", "initial": initial, "sign": sign}}, **more)
def kept(visit, chart, dos, cpts, initial, **more):
    """... and of a visit of a rehab stay whose initial visit sits on the chart at 21: kept at 21 (the comparison group)."""
    n = len(cpts)
    return dict(rehab(visit, chart, dos, cpts, initial), fac="fac29", pos="21", pos_lines=["21"] * n, pos_why=[""] * n, pos_kind=["rehab-stay-kept-21"] * n, pos_stored=["21"] * n, **more)
def acute(visit, chart, dos, cpts):
    n = len(cpts)
    return dict(rehab(visit, chart, dos, cpts, dos, sign=""), fac="fac29", pos="21", pos_lines=["21"] * n, pos_why=[""] * n, pos_kind=[""] * n, pos_stored=["21"] * n, stay={"kind": "acute", "initial": dos, "sign": ""})
REG1 = {"created": [
    rehab("vst7001", "pat9101", "11/26/2026", ["99223"], "11/26/2026"),
    rehab("vst7002", "pat9101", "11/27/2026", ["99233"], "11/26/2026"),
    rehab("vst7003", "pat9102", "11/26/2026", ["99223"], "11/26/2026", sign="facility number", kind="rehab"),      # pos_kind as ONE word, not a list: both shapes are read
    rehab("vst7004", "pat9102", "11/27/2026", ["99233"], "11/26/2026", sign="facility number"),
    rehab("vst7005", "pat9103", "11/10/2026", ["99233"], "11/09/2026"),
    rehab("vst7006", "pat9103", "11/11/2026", ["99223"], "11/11/2026"),
    rehab("vst7007", "pat9104", "12/18/2026", ["99233"], "12/16/2026"),
    rehab("vst7008", "pat9104", "12/17/2026", ["99233"], "12/16/2026"),
    rehab("vst7009", "pat9105", "11/27/2026", ["99233"], "11/26/2026"),
    rehab("vst7010", "pat9105", "11/28/2026", ["99233", "99497"], "11/26/2026"),
    kept("vst7101", "pat9201", "11/26/2026", ["99233"], "11/20/2026"), kept("vst7102", "pat9201", "11/27/2026", ["99233"], "11/20/2026"),
    kept("vst7103", "pat9202", "11/26/2026", ["99233"], "11/21/2026"), kept("vst7104", "pat9202", "11/27/2026", ["99232"], "11/21/2026"),
    kept("vst7105", "pat9203", "11/28/2026", ["99233"], "11/22/2026"),
    acute("vst7201", "pat9301", "11/26/2026", ["99223"]), acute("vst7202", "pat9301", "11/27/2026", ["99232"]),
    {"feed_id": "feedX9", "pid": "pat9302", "visit": "vst7203", "charges": ["charge72030"], "dos": "11/26/2026", "cpts": ["99309"], "fac": "fac34", "pos": "32", "pos_kind": ["monthly"]}],      # a nursing visit: no stay at all
    "skipped": [{"feed_id": "feedX8", "pid": "pat9303", "why": "all lines already in AMD", "stay": {"kind": "rehab", "initial": "11/26/2026", "sign": "facility number"}}],
    "failed": [{"feed_id": "feedX7", "pid": "pat9304", "info": rehab("", "pat9304", "11/26/2026", ["99223"], "11/26/2026"), "err": "no visit today"}]}
REG2 = {"created": [
    rehab("vst7011", "pat9106", "11/20/2026", ["99223"], "11/20/2026"),
    rehab("vst7012", "pat9106", "11/21/2026", ["99233"], "11/20/2026"),
    rehab("vst7013", "pat9107", "11/22/2026", ["99233"], "11/20/2026"),
    rehab("vst7014", "pat9107", "11/23/2026", ["99233"], "11/20/2026"),
    rehab("vst7015", "pat9108", "11/24/2026", ["99233"], "11/23/2026"),
    rehab("vst7016", "pat9108", "11/25/2026", ["99233"], "11/23/2026"),
    rehab("vst7017", "pat9109", "11/25/2026", ["99233"], "11/23/2026"),
    rehab("", "pat9109", "11/26/2026", ["99233"], "11/23/2026"),                                                     # the import wrote no visit id for it
    dict(kept("vst7106", "pat9203", "11/29/2026", ["99233"], "11/22/2026"), pos_kind=[""]),                           # a rehab-stay row at 21 that does not carry the kept-21 word: still the comparison group
    acute("vst7204", "pat9305", "11/27/2026", ["99233"])]}
CO45 = ("CO45", "150.30"); PR2 = ("PR2", "17.60")
def fill_history():
    HIST.clear(); HIST.update({
        # --- entered at 61 ---
        "7001": [chg("70010", "99223", "310.00", "11/28/2026", [pay("-142.10", "12/10/2026", reasons=[CO45, PR2])], ins="17.60")],                       # paid; the secondary's share still open
        "7002": [chg("70020", "99233", "160.00", "11/28/2026", [pay("-86.00", "12/10/2026", reasons=[("CO45", "74.00")])])],                              # paid in full: settled
        "7003": [chg("70030", "99223", "310.00", "11/28/2026", [pay("0.00", "12/09/2026", reasons=[("CO58", "310.00"), ("N620", "0.00")])], ins="310.00")],  # DENIED
        "7004": [chg("70040", "99233", "160.00", "12/05/2026", ins="160.00")],                                                                           # billed 15 days ago, no answer: open
        "7005": [chg("70050", "99233", "160.00", "11/12/2026", ins="160.00")],                                                                           # billed 38 days ago, no answer
        "7006": [chg("70060", "99223", "310.00", "11/12/2026", [pay("-70.00", "12/08/2026", reasons=[("CO45", "240.00")])])],                             # paid low (under 60% of 138.67)
        "7007": [chg("70070", "99233", "160.00", "", ins="160.00")],                                                                                     # not billed yet
        "7008": TimeoutError("read timed out for %s born %s" % (NAME_S, BORN_S)),                                                                         # the read fails - and its words name the patient
        "7009": [chg("70090", "99233", "160.00", "11/28/2026", [pay("-50.00", "12/09/2026", carrier="HUM01", reasons=[("CO45", "110.00")])], carrier="HUM01")],   # paid low against the comparison group (90.00)
        "7010": [chg("70100", "99233", "160.00", "11/29/2026", [pay("-88.00", "12/11/2026", reasons=[("CO45", "72.00")])]),
                 chg("70101", "99497", "133.00", "11/29/2026", [pay("0.00", "12/11/2026", reasons=[("CO97", "133.00")])], ins="133.00")],                    # the visit is paid; the line riding with it is denied
        "7011": [chg("70110", "99223", "310.00", "11/22/2026", [pay("0.00", "12/10/2026", reasons=[("CO45", "140.00"), ("PR1", "170.00")])], pat="170.00")],  # a $0 answer: the whole allowed amount is the patient's deductible
        "7012": [chg("70120", "99233", "160.00", "11/23/2026", [pay("0.00", "11/30/2026", reasons=[("CO16", "160.00")])], wos=[{"amount": "-160.00", "wocode": "WOINS", "date": "12/02/2026"}])],   # denied, written off since
        "7013": [chg("70130", "99233", "160.00", "12/05/2026", [pay("0.00", "12/01/2026", reasons=[("CO58", "160.00")])], ins="160.00")],                   # denied 12/01, sent again 12/05
        "7014": [chg("70140", "99233", "160.00", "11/25/2026", void="1")],                                                                               # voided since
        "7015": [chg("70150", "99233", "160.00", "11/25/2026", [pay("-20.00", "12/02/2026", carrier="")], ins="140.00")],                                  # only the PATIENT paid something: the payer has not answered
        "7016": [chg("70160", "99233", "160.00", "12/03/2026", [pay("0.00", "12/01/2026", reasons=[("CO16", "160.00")]), pay("86.00", "12/15/2026", reasons=[("CO45", "74.00")])])],   # denied, then paid (a payment stored without the minus sign)
        "7017": [chg("70170", "99233", "160.00", "11/26/2026", wos=[{"amount": "-160.00", "wocode": "WOINS", "date": "12/12/2026"}])],                      # written off, never paid, never answered
        # --- the comparison group, kept at 21 ---
        "7101": [chg("71010", "99233", "160.00", "11/28/2026", [pay("-90.00", "12/10/2026")])], "7102": [chg("71020", "99233", "160.00", "11/28/2026", [pay("-88.00", "12/10/2026")])],
        "7103": [chg("71030", "99233", "160.00", "11/28/2026", [pay("-92.00", "12/10/2026")])], "7104": [chg("71040", "99232", "111.00", "11/28/2026", [pay("-60.00", "12/10/2026")])],
        "7105": [chg("71050", "99233", "160.00", "11/29/2026", [pay("0.00", "12/11/2026", reasons=[("CO16", "160.00")])], ins="160.00")],
        "7106": [chg("71060", "99233", "160.00", "12/10/2026", ins="160.00")]})
def workspace(name, regs, extra=None):
    """A registers folder holding the given import registers ({stamp: register}); returns the folder."""
    d = os.path.join(TMP, name, "registers"); os.makedirs(d)
    for stamp, reg in regs.items(): json.dump(reg, open(os.path.join(d, "feed_import_%s.json" % stamp), "w"), indent=1)
    for fname, text in (extra or {}).items(): open(os.path.join(d, fname), "w").write(text)
    return d
def run(regdir, *args, today="2026-12-20"):
    """One run of the monitor inside this process -> (exit code, printed lines, its register or None, the stand-in calls it made)."""
    del CALLS[:]; out = io.StringIO(); rc = None; err = ""
    argv = (["--registers", regdir] if regdir else []) + (["--today", today] if today else []) + list(args)
    with contextlib.redirect_stdout(out):
        try: rc = M.main(argv)
        except SystemExit as e: rc = e.code
        except Exception as e: err = "%s: %s" % (type(e).__name__, str(e)[:200])
    f = os.path.join(regdir, "pos61_monitor.json") if regdir else ""
    try: reg = json.load(open(f)) if f and os.path.exists(f) else None
    except Exception: reg = "NOT JSON"
    lines = out.getvalue().splitlines()
    if err: lines.append("RAISED " + err)
    return rc, lines, reg, list(CALLS)
def row(reg, visit): return next((v for v in (reg or {}).get("visits") or [] if v.get("visit") == visit), {})
def line(lines, start): return next((l for l in lines if l.startswith(start)), "")
def tops(lines): return [l for l in lines if l.startswith("TOP OF THE REPORT")]
def reads(calls): return sorted(c[2] for c in calls if c[0] == "fetch_visit")
QUESTION = "- for William: keep 61 or go back to 21 for this payer?"
BASE = "at 21 the average was $138.67 on 95 paid of 121 sent"

# ==== 1. the fixed history of place of service 21, and the helper's own words ======================================================================
check("1 the baseline is the practice's own history at place of service 21 - 121 sent, 95 paid, average $138.67, 10 denied unpaid - kept as constants",
      lambda: M.BASELINE_21 == {"sent": 121, "paid": 95, "average": 138.67, "denied_unpaid": 10}, lambda: M.BASELINE_21)
check("1 ... with a comment beside them that says where the numbers came from (the practice's AdvancedMD history pulled 11/10/2026: second initial hospital visits within 30 days at 21 since 11/2025)",
      lambda: bool(re.search(r"BASELINE_21 = \{[^\n]*#[^\n]*11/10/2026", SRC)) and "second initial hospital visits within 30 days" in SRC and "since 11/2025" in SRC)
check("1 the limits are the spec's: unanswered after 30 days, paid low under 60% of the 21 average", lambda: (M.UNANSWERED_DAYS, M.UNDER_SHARE) == (30, 0.60), lambda: (M.UNANSWERED_DAYS, M.UNDER_SHARE))
check("1 the helper keeps its PLAIN ENGLISH header: read-only, what it reads, what it writes, and that the register holds no name, birth date or member number",
      lambda: SRC.split("\nimport ", 1)[0].count("# PLAIN ENGLISH (") == 1 and all(w in SRC.split("\nimport ", 1)[0] for w in ("READ-ONLY", "registers/pos61_monitor.json", "txh.fetch_visit", "never a name, a birth date or a member number", "William, 11/25/2026", "Never:")))
check("1 the helper calls nothing of AdvancedMD but the login and the ONE-visit history read (its source holds no other use of amd or txh)",
      lambda: set(re.findall(r"\bamd\.(\w+)", SRC)) == {"login_cached"} and set(re.findall(r"\btxh\.(\w+)", SRC)) <= {"fetch_visit", "py"} and "fetch_visit" in re.findall(r"\btxh\.(\w+)", SRC), lambda: (set(re.findall(r"\bamd\.(\w+)", SRC)), set(re.findall(r"\btxh\.(\w+)", SRC))))
def loads(src):
    """The names a piece of Python loads with import / from, first name of each (as tools/selftest/test_pos_rule.py reads them)."""
    out_ = set()
    for kind, rest in re.findall(r"^[ \t]*(import|from)[ \t]+([^\n#]+)", src, re.M):
        for n in (rest.split(",") if kind == "import" else [rest]):
            n = n.strip().split()[0].split(".")[0] if n.strip() else ""
            if n: out_.add(n)
    return out_
check("1 ... and of the modules that talk to AdvancedMD or the vendor it loads amd and txh only", lambda: loads(SRC) & set(AMD_MODULES) == {"amd", "txh"}, lambda: loads(SRC))
check("1 every option is a quoted word of its argument reader (the routines' texts are checked against that): --registers --workspace --today --max --seconds --all --line-days --dry --live",
      lambda: all(('"%s"' % o) in SRC for o in ("--registers", "--workspace", "--today", "--max", "--seconds", "--all", "--line-days", "--dry", "--live")), lambda: [o for o in ("--registers", "--workspace", "--today", "--max", "--seconds", "--all", "--line-days", "--dry", "--live") if ('"%s"' % o) not in SRC])
check("1 ... and it holds no word of a call that changes anything there (no save, void, rebill, payment or bypass action)",
      lambda: bool(SRC) and not re.search(r"updvisit|addvisit|addpayments|updextrainsinfo|bypassclaimedits|chargerebill|void_charge|rebill_charge|set_insorder|amd\.post|amd\.msg|massrebill|posterapayments", SRC))

# ==== 2. no rehab visit yet ========================================================================================================================
fill_history()
W0 = workspace("none", {"20261126T1240Z": {"created": [acute("vst7201", "pat9301", "11/26/2026", ["99223"]), REG1["created"][-1]], "skipped": [], "failed": []}})
rc0, out0, reg0, calls0 = run(W0)
check("2 no rehab visit yet: ONE line is printed - it says so, with the 21 history beside it, and names the register - and the run ends well",
      lambda: rc0 == 0 and out0 == ["REHAB AT 61: no inpatient-rehab visit has been entered yet - nothing to monitor (" + BASE + ") - register: " + os.path.join(W0, "pos61_monitor.json")], lambda: (rc0, out0))
check("2 ... nothing of AdvancedMD is touched - no login, no read", lambda: rc0 == 0 and calls0 == [], lambda: (rc0, calls0))
check("2 ... and the register is written with zero counts and no visit", lambda: reg0["visits"] == [] and reg0["counts"]["at 61"]["entered"] == 0 and reg0["counts"]["at 61"]["paid"] == 0 and reg0["counts"]["at 61"]["denied"] == 0
      and reg0["counts"]["kept at 21"]["entered"] == 0 and reg0["baseline_21"]["average"] == 138.67 and reg0["top"] == [], lambda: reg0)
W00 = os.path.join(TMP, "empty", "registers"); os.makedirs(W00)
rc00, out00, reg00, calls00 = run(W00)
check("2 a registers folder with no import register at all: the same one line, zero counts, nothing read", lambda: rc00 == 0 and len(out00) == 1 and out00[0].startswith("REHAB AT 61: no ") and calls00 == [] and reg00["visits"] == []
      and reg00["lines"] == ["REHAB AT 61: no inpatient-rehab visit has been entered yet - nothing to monitor (" + BASE + ")"], lambda: (rc00, out00))
rcn, outn, regn, callsn = run(os.path.join(TMP, "nowhere", "registers"))
check("2 a registers folder that is not there ends with a plain sentence and exit 2 - not with a zero count, a new folder or a traceback",
      lambda: rcn == 2 and any("registers folder not found" in l for l in outn) and not any(l.startswith(("REHAB AT 61", "RAISED")) for l in outn) and not os.path.exists(os.path.join(TMP, "nowhere")) and callsn == [], lambda: (rcn, outn))

# ==== 3. the full picture: one run over two import registers ==========================================================================================
fill_history()
W1 = workspace("full", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2},
               extra={"feed_import_20261126T1240Z_decisions.json": json.dumps({"created": [rehab("vst7999", "pat9999", "11/26/2026", ["99223"], "11/26/2026")]}),      # not an import register: never read
                      "feed_import_20261128T1240Z.json": "{ this is not a register",                                                                            # cannot be read: named, the others still are
                      "feed_recon_20261126T1240Z.json": json.dumps({"rows": [{"v": "vst7001", "prov": "x"}]})})
rc1, out1, reg1, calls1 = run(W1)
AT61 = ["7001", "7002", "7003", "7004", "7005", "7006", "7007", "7008", "7009", "7010", "7011", "7012", "7013", "7014", "7015", "7016", "7017"]
AT21 = ["7101", "7102", "7103", "7104", "7105", "7106"]
# The order a run WITHOUT its memory reads these 23 visits in on 12/20/2026: the list by date of service, from that day's place in it. The place
# is the day's number times the golden ratio: 739970 x 0.6180339887... leaves .610655 behind the point, and .610655 x 23 = 14.04 - 14 visits
# are passed over and read last. (Worked out here by hand, not with the helper: the check below would not see a wrong rule otherwise.)
BY_DOS = ["7005", "7006", "7011", "7012", "7013", "7014", "7015", "7016", "7017", "7001", "7003", "7101", "7103", "7002", "7004", "7009", "7102", "7104", "7010", "7105", "7106", "7008", "7007"]
TURN1220 = BY_DOS[14:] + BY_DOS[:14]      # 7004, 7009, 7102, 7104, 7010, 7105, 7106, 7008, 7007, then 7005 ... 7002
def asked(calls): return [c[2] for c in calls if c[0] == "fetch_visit"]      # the visits a run asked for, in the order it asked
check("3 the run ends well although one visit could not be read and one import register is not readable", lambda: rc1 == 0 and not any(l.startswith("RAISED") for l in out1), lambda: (rc1, out1[-3:]))
check("3 ONE login, then ONE read of its own history for every rehab-stay visit that has a visit id - the 61 group and the comparison group, nothing else (no acute stay, no nursing visit, no skipped or failed row, no decisions file)",
      lambda: calls1[0] == ("login",) and [c[0] for c in calls1].count("login") == 1 and reads(calls1) == sorted(AT61 + AT21) and all(c[0] in ("login", "fetch_visit") for c in calls1), lambda: calls1)
check("3 ... a run that has no register of an earlier run reads the visits by date of service from the DAY'S place in that list, not from the oldest one every time (11/25/2026: every run started at the same oldest visits)",
      lambda: asked(calls1) == TURN1220 and sorted(TURN1220) == sorted(AT61 + AT21), lambda: asked(calls1))
check("3 ... each read is asked with the chart's and the visit's NUMBER (as the runs' own read is)", lambda: ("fetch_visit", "9101", "7001") in calls1 and ("fetch_visit", "9203", "7106") in calls1)
S61 = line(out1, "REHAB AT 61:")
check("3 the line REHAB AT 61 - entered, billed, paid with the dollars and the average per initial visit beside the 21 history, denied with the codes, unanswered over 30 days - exactly as the spec words it",
      lambda: S61.startswith("REHAB AT 61: 17 visit(s) entered; 14 billed; 6 paid ($522.10, average $106.05 per initial visit - " + BASE + "); 3 denied (codes CO-58 x2, CO-16 x1") and "; 1 billed and unanswered for over 30 days" in S61, lambda: S61)
check("3 ... and what the spec's five numbers do not hold is said behind them, never dropped: paid low, a $0 answer without a denial code, written off unpaid, not read, voided",
      lambda: all(w in S61 for w in ("1 of them written off since", "; 2 paid low", "; 1 answered with $0 and no denial code (CO-45 x1, PR-1 x1)", "; 1 written off unpaid", "; 1 not billed yet", "; 2 could not be read", "; 1 voided since (not counted)")), lambda: S61)
S21 = line(out1, "REHAB STAYS KEPT AT 21")
check("3 the comparison group has its own line in the same words: the rehab-stay visits kept at 21",
      lambda: S21 == "REHAB STAYS KEPT AT 21 (the comparison group): 6 visit(s) entered; 6 billed; 4 paid ($330.00); 1 denied (codes CO-16 x1); 0 billed and unanswered for over 30 days", lambda: S21)
SPC = line(out1, "REHAB PAID PER CODE")
check("3 the dollars per code, 61 beside 21: an initial visit against the fixed history, a follow-up against the comparison group",
      lambda: SPC == "REHAB PAID PER CODE - at 61 / at 21: 99223 $106.05 x2 / $138.67 x95 (the practice's history of 11/10/2026); 99232 none yet / $60.00 x1; 99233 $77.50 x4 / $90.00 x3", lambda: SPC)
ST = {v: row(reg1, "vst" + v).get("state") for v in AT61 + AT21}
check("3 paid: a payment of the payer on the visit's own line", lambda: ST["7001"] == ST["7002"] == "paid" and row(reg1, "vst7001")["paid"] == 142.10 and row(reg1, "vst7001")["paid_on"] == "12/10/2026" and row(reg1, "vst7001")["carrier"] == "FLO02" and row(reg1, "vst7001")["billed"] == "11/28/2026", lambda: row(reg1, "vst7001"))
check("3 denied: a $0 payment line with a reason code - the codes, the remark code, the day and the balance are kept", lambda: ST["7003"] == "denied" and row(reg1, "vst7003")["denial"] == ["CO-58"] and row(reg1, "vst7003")["remarks"] == ["N620"]
      and row(reg1, "vst7003")["denied_on"] == "12/09/2026" and row(reg1, "vst7003")["balance"] == 310.0 and row(reg1, "vst7003")["paid"] == 0, lambda: row(reg1, "vst7003"))
check("3 open: billed 15 days ago, no answer yet", lambda: ST["7004"] == "open" and row(reg1, "vst7004")["days"] == 15, lambda: row(reg1, "vst7004"))
check("3 unanswered: billed 38 days ago, no answer", lambda: ST["7005"] == "unanswered" and row(reg1, "vst7005")["days"] == 38, lambda: row(reg1, "vst7005"))
check("3 not billed: no bill date on its charge", lambda: ST["7007"] == "not billed" and not row(reg1, "vst7007").get("billed"), lambda: row(reg1, "vst7007"))
check("3 a read that fails: the visit is counted and named, its state says so, and the run went on to the visits after it",
      lambda: ST["7008"] == "could not be read" and row(reg1, "vst7008")["unread"] == "TimeoutError" and any(l.startswith("REHAB MONITOR") and "vst7008" in l and "pat9104" in l and "TimeoutError" in l for l in out1) and asked(calls1).index("7008") < asked(calls1).index("7007") < asked(calls1).index("7005") and ST["7007"] == "not billed" and ST["7005"] == "unanswered", lambda: (row(reg1, "vst7008"), [l for l in out1 if "7008" in l]))
check("3 the visit the import wrote no visit id for is counted and named the same way - and never asked for", lambda: any(l.startswith("REHAB MONITOR") and "no visit id" in l and "pat9109" in l and "11/26/2026" in l for l in out1)
      and len([v for v in reg1["visits"] if not v.get("visit")]) == 1 and [v for v in reg1["visits"] if not v.get("visit")][0]["state"] == "could not be read", lambda: [l for l in out1 if l.startswith("REHAB MONITOR")])
check("3 paid low: an initial visit paid $70.00 is under 60% of the $138.67 history", lambda: ST["7006"] == "paid" and row(reg1, "vst7006")["low"] is True and row(reg1, "vst7006")["low_vs"] == 138.67 and not row(reg1, "vst7001").get("low"), lambda: row(reg1, "vst7006"))
check("3 paid low: a follow-up paid $50.00 is under 60% of the $90.00 the comparison group averages for that code; $86.00 and $88.00 are not", lambda: row(reg1, "vst7009")["low"] is True and row(reg1, "vst7009")["low_vs"] == 90.0
      and not row(reg1, "vst7002").get("low") and not row(reg1, "vst7010").get("low") and row(reg1, "vst7009")["carrier"] == "HUM01", lambda: row(reg1, "vst7009"))
check("3 a line riding with the visit (99497) that is denied while the visit itself is paid: the visit is paid, the line is kept in its row and said in one plain line - not a place-of-service line",
      lambda: ST["7010"] == "paid" and row(reg1, "vst7010")["paid"] == 88.0 and row(reg1, "vst7010")["code"] == "99233" and row(reg1, "vst7010")["other"] == [{"code": "99497", "answer": "denied", "paid": 0.0, "denial": ["CO-97"], "balance": 133.0}] and row(reg1, "vst7010")["closed"] is False
      and any(l.startswith("REHAB MONITOR") and "vst7010" in l and "99497" in l and "CO-97" in l for l in out1) and not any("7010" in l for l in tops(out1)), lambda: (row(reg1, "vst7010"), [l for l in out1 if "7010" in l]))
check("3 a $0 answer whose codes are only cost share and the contractual amount (PR-1 with CO-45) is not counted as a denial - the practice's own reading (aging_refresh.py, denials_refresh.py) - and it is not lost either: its own state, its codes",
      lambda: ST["7011"] == "answered $0" and row(reg1, "vst7011")["zero_codes"] == ["CO-45", "PR-1"] and not row(reg1, "vst7011").get("denial") and row(reg1, "vst7011")["balance"] == 170.0, lambda: row(reg1, "vst7011"))
check("3 denied and written off since: still a denied visit, with no balance left", lambda: ST["7012"] == "denied" and row(reg1, "vst7012")["denial"] == ["CO-16"] and row(reg1, "vst7012")["balance"] == 0 and row(reg1, "vst7012")["closed"] is True, lambda: row(reg1, "vst7012"))
check("3 denied and sent again since: still denied until the payer pays - the row says when it went out again", lambda: ST["7013"] == "denied" and row(reg1, "vst7013")["resent"] == "12/05/2026" and not row(reg1, "vst7003").get("resent"), lambda: row(reg1, "vst7013"))
check("3 voided since: every charge of the visit reads void - not counted as entered, never a paid or denied visit", lambda: ST["7014"] == "voided", lambda: row(reg1, "vst7014"))
check("3 a payment of the PATIENT is not the payer's answer: the visit stays open", lambda: ST["7015"] == "open" and row(reg1, "vst7015")["paid"] == 0 and row(reg1, "vst7015")["days"] == 25, lambda: row(reg1, "vst7015"))
check("3 denied first, paid later: paid - whatever sign the payment is stored with - and the earlier denial is kept in the row", lambda: ST["7016"] == "paid" and row(reg1, "vst7016")["paid"] == 86.0 and row(reg1, "vst7016")["before"] == ["CO-16"] and not row(reg1, "vst7016").get("denial"), lambda: row(reg1, "vst7016"))
check("3 written off unpaid: billed, never answered, no balance left", lambda: ST["7017"] == "written off" and row(reg1, "vst7017")["balance"] == 0, lambda: row(reg1, "vst7017"))
check("3 the comparison group is read the same way (paid, denied, open) and never gets a place-of-service line", lambda: [ST[v] for v in AT21] == ["paid", "paid", "paid", "paid", "denied", "open"]
      and all(row(reg1, "vst" + v)["group"] == "21" for v in AT21) and all(row(reg1, "vst" + v)["group"] == "61" for v in AT61) and not any(("vst" + v) in l for v in AT21 for l in tops(out1)), lambda: ST)
check("3 the rows carry what the import wrote of the stay: its initial visit's date and the sign", lambda: row(reg1, "vst7003")["initial"] == "11/26/2026" and row(reg1, "vst7003")["sign"] == "facility number"
      and row(reg1, "vst7001")["sign"] == "new admission 1-2 days after an acute stay" and row(reg1, "vst7001")["batch"] == "20261126T1240Z" and row(reg1, "vst7011")["batch"] == "20261127T1240ZR" and row(reg1, "vst7001")["cpts"] == ["99223"], lambda: row(reg1, "vst7003"))
T1 = tops(out1)
D3 = line(T1, "TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7003")
check("3 EVERY denied visit at 61 has ONE line that starts TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: and ends with the question for William",
      lambda: sorted(re.findall(r"vst\d+", " ".join(l for l in T1 if " DENIED: " in l))) == ["vst7003", "vst7012", "vst7013"] and all(l.endswith(QUESTION) for l in T1) and len([l for l in T1 if " DENIED: " in l]) == 3, lambda: T1)
check("3 ... with the visit, the chart, the date of service, the carrier code and the reason / remark codes",
      lambda: D3 == "TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7003 pat9102 service date 11/26/2026 99223 carrier FLO02 denied 12/09/2026 with CO-58 (remark N620), balance $310.00 " + QUESTION, lambda: D3)
check("3 ... a denied visit that went out again says so in its line", lambda: "sent again 12/05/2026 - no answer yet" in line(T1, "TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7013"), lambda: T1)
check("3 ... a denied visit that was written off since is said too when the monitor sees it for the first time - its line says that it was written off",
      lambda: line(T1, "TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7012") == "TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7012 pat9106 service date 11/21/2026 99233 carrier FLO02 denied 11/30/2026 with CO-16, balance $0.00 (written off since) " + QUESTION and "3 denied" in S61, lambda: T1)
L6 = line(T1, "TOP OF THE REPORT - PLACE OF SERVICE 61 paid low: vst7006")
check("3 a visit paid under 60% of the 21 average for its code has its TOP OF THE REPORT line (paid low), with what it is measured against",
      lambda: L6 == "TOP OF THE REPORT - PLACE OF SERVICE 61 paid low: vst7006 pat9103 service date 11/11/2026 99223 carrier FLO02 paid $70.00 on 12/08/2026 - under 60% of the $138.67 average at 21 for 99223 (the practice's history of 11/10/2026) " + QUESTION, lambda: L6)
check("3 ... the follow-up paid low is measured against the comparison group", lambda: "vst7009 pat9105 service date 11/27/2026 99233 carrier HUM01 paid $50.00 on 12/09/2026 - under 60% of the $90.00 average at 21 for 99233 (3 paid visit(s) of the comparison group)" in line(T1, "TOP OF THE REPORT - PLACE OF SERVICE 61 paid low: vst7009"), lambda: T1)
check("3 ... and the $0 answer without a denial code has a line too (paid $0.00, its codes named, said not to be a denial)", lambda: "paid $0.00 on 12/10/2026" in line(T1, "TOP OF THE REPORT - PLACE OF SERVICE 61 paid low: vst7011") and "CO-45, PR-1" in line(T1, "TOP OF THE REPORT - PLACE OF SERVICE 61 paid low: vst7011")
      and "no denial code" in line(T1, "TOP OF THE REPORT - PLACE OF SERVICE 61 paid low: vst7011"), lambda: T1)
check("3 the TOP OF THE REPORT lines are those six and no other - the denied visits first", lambda: sorted(re.findall(r"vst\d+", " ".join(T1))) == ["vst7003", "vst7006", "vst7009", "vst7011", "vst7012", "vst7013"] and len(T1) == 6
      and [" DENIED: " in l for l in T1] == [True] * 3 + [False] * 3, lambda: T1)
check("3 each of those visits carries the day the monitor first saw it so, and which line it has (that is what the line's 14 days are counted from)",
      lambda: [(row(reg1, "vst" + v).get("said"), row(reg1, "vst" + v).get("since")) for v in ("7003", "7012", "7006", "7011")] == [("denied", "12/20/2026")] * 2 + [("paid low", "12/20/2026")] * 2 and "since" not in row(reg1, "vst7001") and "said" not in row(reg1, "vst7105"),
      lambda: [(row(reg1, "vst" + v).get("said"), row(reg1, "vst" + v).get("since")) for v in ("7003", "7012", "7006", "7011", "7001", "7105")])
check("3 the import register that could not be read is named, and so is the fact that its visits are not in the counts", lambda: any(l.startswith("REHAB MONITOR") and "feed_import_20261128T1240Z.json" in l and "could not be read" in l for l in out1), lambda: [l for l in out1 if l.startswith("REHAB MONITOR")])
check("3 the last printed line names the register", lambda: out1[-1] == "register: %s" % os.path.join(W1, "pos61_monitor.json"), lambda: out1[-1])
C61 = (reg1 or {}).get("counts", {}).get("at 61", {}); C21 = (reg1 or {}).get("counts", {}).get("kept at 21", {})
check("3 the register's counts are the line's numbers", lambda: (C61["entered"], C61["billed"], C61["paid"], C61["paid_dollars"], C61["initial_paid"], C61["initial_average"], C61["denied"], C61["unanswered"], C61["open"], C61["paid_low"]) == (17, 14, 6, 522.10, 2, 106.05, 3, 1, 2, 2)
      and C61["denied_codes"] == {"CO-58": 2, "CO-16": 1} and (C61["not_billed"], C61["zero_answer"], C61["written_off"], C61["unread"], C61["voided"]) == (1, 1, 1, 2, 1) and (C21["entered"], C21["paid"], C21["paid_dollars"], C21["denied"]) == (6, 4, 330.0, 1), lambda: (C61, C21))
check("3 the register holds every printed line as it was printed (the digest can carry them without working anything out again)", lambda: reg1["lines"] == [l for l in out1 if l.startswith("REHAB")] and reg1["top"] == T1 and len(reg1["lines"]) >= 3, lambda: (reg1.get("lines"), reg1.get("top")))
check("3 the register says what it is, the day it was made for, the limits, the baseline and that nothing was written to AdvancedMD", lambda: reg1["today"] == "12/20/2026" and reg1["baseline_21"] == M.BASELINE_21 and "read only" in reg1["mode"]
      and reg1["limits"]["unanswered_days"] == 30 and reg1["limits"]["low_share"] == 0.6 and reg1["version"] == M.POS61_MONITOR_VERSION and len(reg1["visits"]) == 24 and reg1["unreadable_registers"] == ["feed_import_20261128T1240Z.json"], lambda: {k: v for k, v in reg1.items() if k not in ("visits", "lines", "top")})

# ==== 4. the privacy of the register and of every printed line =======================================================================================
RTXT = open(os.path.join(W1, "pos61_monitor.json")).read() if os.path.exists(os.path.join(W1, "pos61_monitor.json")) else ""
check("4 the stand-in's answers DO carry a name, a birth date and plan numbers on every charge row and payment line (so the next checks prove something)",
      lambda: all(s in ET.tostring(history("7001", HIST["7001"])).decode() for s in SECRETS) and NAME_S in str(HIST["7008"]))
check("4 the register holds none of them - no name, no birth date, no member number, also not from the words of the error of the read that failed",
      lambda: bool(RTXT) and not any(s in RTXT for s in SECRETS) and not re.search(r"(?i)medicare part b|reason text|read timed out|HCA REHAB|CHK", RTXT), lambda: [s for s in SECRETS if s in RTXT])
check("4 ... and neither does any printed line", lambda: rc1 == 0 and len(out1) > 8 and not any(s in l for s in SECRETS for l in out1) and not any("timed out" in l for l in out1), lambda: [l for l in out1 if any(s in l for s in SECRETS)])
ROW_KEYS = {"visit", "chart", "dos", "cpts", "group", "batch", "initial", "sign", "state", "read", "code", "fee", "carrier", "billed", "days", "paid", "paid_on", "pay_codes", "denial", "remarks", "denied_on",
            "resent", "zero_codes", "balance", "ins_balance", "other", "closed", "low", "low_vs", "low_of", "before", "stale", "unread", "void", "answer", "asked", "since", "said", "paid_by", "pending", "dup"}
check("4 every row of the register holds only the fields the helper names - ids, dates, codes, states and dollars", lambda: all(set(v) <= ROW_KEYS for v in reg1["visits"]) and len(reg1["visits"]) == 24, lambda: sorted({k for v in reg1["visits"] for k in v} - ROW_KEYS))
def shapes_ok(v):
    """Every value of a row has the shape of what it is said to be: nothing free-text can ride in."""
    d = r"\d\d/\d\d/\d{4}"; code = r"(?:[A-Z]{2}-)?[A-Z]?\d{1,3}|(?:MA|M|N)\d{1,4}|\?"; proc = r"\d{4}[0-9A-Z]|[A-Z]\d{4}"
    tests = {"visit": r"(vst\d+)?", "chart": r"pat\d+", "dos": d, "initial": "(%s)?" % d, "read": d, "billed": "(%s)?" % d, "paid_on": d, "denied_on": d, "resent": d, "asked": d, "since": d, "said": r"denied|paid low", "carrier": r"([A-Za-z0-9]{2,8})?", "paid_by": r"[A-Za-z0-9]{2,8}", "pending": r"True", "code": proc,
             "group": r"61|21", "batch": r"\d{4,8}(T\d{4,6}Z[0-9A-Z]{0,4})?", "unread": r"[A-Za-z ]+", "state": r"[a-z$0 ]+", "answer": r"[a-z]+", "sign": r"(facility number|new admission 1-2 days after an acute stay)?", "low_of": r"[a-z0-9 /()'\-]+"}
    for k, rx in tests.items():
        if k in v and not re.fullmatch(rx, str(v[k])): return (k, v[k])
    for k in ("cpts", "denial", "remarks", "pay_codes", "zero_codes", "before", "dup"):
        if k in v and not all(re.fullmatch(code if k != "cpts" else proc, str(x)) for x in v[k]): return (k, v[k])
    for k in ("fee", "paid", "balance", "ins_balance", "low_vs", "days"):
        if k in v and (isinstance(v[k], bool) or not isinstance(v[k], (int, float)) or v[k] != v[k] or abs(v[k]) == float("inf")): return (k, v[k])
    for o in v.get("other") or []:
        if set(o) != {"code", "answer", "paid", "denial", "balance"} or not re.fullmatch("(%s)?" % proc, str(o["code"])) or not all(re.fullmatch(code, str(x)) for x in o["denial"]): return ("other", o)
    return None
check("4 ... and every value has the shape of an id, a date, a code, a state word or a number", lambda: [x for x in (shapes_ok(v) for v in reg1["visits"]) if x] == [], lambda: [x for x in (shapes_ok(v) for v in reg1["visits"]) if x])
sys.path.insert(0, os.path.join(ROOT, "tools", "mirror"))
try: import phi_gate
except Exception: phi_gate = None
check("4 the repository's own privacy gate (tools/mirror/phi_gate.py) finds nothing to change in the register and nothing to refuse", lambda: phi_gate.redact(RTXT, {}, code=False) == RTXT and phi_gate.check(RTXT) == [] and len(RTXT) > 2000, lambda: phi_gate.check(RTXT))
check("4 ... nor in the printed lines", lambda: rc1 == 0 and len(out1) > 8 and phi_gate.redact("\n".join(out1), {}, code=False) == "\n".join(out1) and phi_gate.check("\n".join(out1)) == [])
check("4 ... and the gate would have changed them had a name, a birth date or a number been there (the check above is not empty)",
      lambda: phi_gate.redact('{"name": "%s", "dob": "%s", "subscribernum": "%s"} %s' % (NAME_S, BORN_S, MEM_S, MBI_S), {}, code=False) == '{"name": "[name]", "dob": "[DOB]", "subscribernum": "[member id]"} [MBI]')
check("4 the gate leaves the helper and this self-test as they are (it scrubs every changed file before a commit: a file it rewrites is a file that no longer says what was tested)",
      lambda: len(SRC) > 2000 and phi_gate.redact(SRC, {}, code=True) == SRC and phi_gate.redact(open(os.path.abspath(__file__)).read(), {}, code=True) == open(os.path.abspath(__file__)).read())
def odd_history():
    """An answer whose fields hold what they should not: a carrier field with a name in it, reason codes that are words, dates that are text."""
    r_ = history("7301", [chg("73010", "99233", "160.00", "soon " + NAME_S, [pay("0.00", "the day " + NAME_S, carrier=NAME_S, reasons=[(NAME_S, "1.00"), ("CO58", "160.00"), ("see " + MEM_S, "0")])], ins="160.00", carrier="CARRIER OF " + NAME_S)])
    for c_ in r_.iter("charge"): c_.set("proccode", "99233"); c_.set("fee", "160.00")
    return r_
HIST["7301"] = odd_history
W4 = workspace("odd", {"20261126T1240Z": {"created": [rehab("vst7301", "pat9401", "11/26/2026", ["99233"], "11/25/2026", sign="a sign " + NAME_S)]}})
rc4, out4, reg4, calls4 = run(W4); T4 = open(os.path.join(W4, "pos61_monitor.json")).read() if os.path.exists(os.path.join(W4, "pos61_monitor.json")) else ""
check("4 an answer whose carrier, date and reason-code fields hold free text: only what has the shape of a code or a date is kept - the denial is still seen, the carrier is left empty, an odd code is written '?'",
      lambda: rc4 == 0 and row(reg4, "vst7301")["state"] == "denied" and row(reg4, "vst7301")["denial"] == ["?", "CO-58"] and not row(reg4, "vst7301").get("carrier") and not row(reg4, "vst7301").get("billed") and "carrier not named" in " ".join(tops(out4))
      and not any(s in T4 for s in SECRETS) and not any(s in l for s in SECRETS for l in out4) and shapes_ok(row(reg4, "vst7301")) is None and row(reg4, "vst7301").get("sign", "") == "", lambda: (rc4, row(reg4, "vst7301"), out4))

fill_history()
W4b = workspace("memory", {"20261126T1240Z": REG1}); rc4b, out4b, reg4b, calls4b = run(W4b)
if isinstance(reg4b, dict):      # the register comes back through the repository: here somebody (or some tool) has written into the settled visit vst7002 and the open visit vst7004
    for v_ in reg4b["visits"]:
        if v_.get("visit") == "vst7002": v_.update(carrier=NAME_S, pay_codes=[NAME_S, "CO-45"], paid_on="the day of " + NAME_S, code=LAST_S[:5], paid="86 dollars of " + NAME_S, patientname=NAME_S, said=NAME_S, since=BORN_S + " " + NAME_S, asked=NAME_S, balance=float("nan"),
                                                  other=[{"code": NAME_S, "answer": NAME_S, "paid": "x", "denial": [NAME_S, "CO-97"], "balance": float("inf"), "name": NAME_S}], unread=NAME_S, low_of=NAME_S, state=NAME_S, sign=NAME_S, initial=NAME_S)
        if v_.get("visit") == "vst7004": v_.update(carrier=NAME_S, billed=NAME_S, denial=[MEM_S], answer=NAME_S, dob=BORN_S, closed=True)      # ... and marked settled although nothing in the row bears that out
        if v_.get("visit") == "vst7006": v_.update(since=BORN_S, billed=BORN_S, paid_on=BORN_S)      # a date where a date belongs - but a date from before the visit itself
    reg4b["lines"] = [NAME_S]; reg4b["top"] = [NAME_S]; reg4b[NAME_S] = MEM_S
    json.dump(reg4b, open(os.path.join(W4b, "pos61_monitor.json"), "w"), indent=1)
HIST["7004"] = ConnectionError("gone")      # ... and the open visit cannot be read today: what the register says of it is all the monitor has
rc4c, out4c, reg4c, calls4c = run(W4b, today="2026-12-21"); T4c = open(os.path.join(W4b, "pos61_monitor.json")).read() if os.path.exists(os.path.join(W4b, "pos61_monitor.json")) else ""
check("4 the register of the run before is the monitor's memory, and nothing rides through it: a name, a date or a number somebody wrote into a row is not carried on - each field is taken over only in the shape it has, a field the helper does not name not at all",
      lambda: rc4b == rc4c == 0 and "7002" not in reads(calls4c) and not any(s in T4c for s in SECRETS) and LAST_S[:5] not in T4c and not any(s in l for s in SECRETS for l in out4c) and all(set(v) <= ROW_KEYS for v in reg4c["visits"])
      and [x for x in (shapes_ok(v) for v in reg4c["visits"]) if x] == [] and row(reg4c, "vst7002")["state"] == "paid" and row(reg4c, "vst7002")["pay_codes"] == ["?", "CO-45"] and row(reg4c, "vst7002")["read"] == "12/20/2026"
      and "carrier" not in row(reg4c, "vst7002") and row(reg4c, "vst7002")["code"] == "99233" and "7004" in reads(calls4c) and row(reg4c, "vst7004")["unread"] == "ConnectionError" and row(reg4c, "vst7004")["stale"] is True
      and row(reg4c, "vst7004")["closed"] is False and "NaN" not in T4c and "Infinity" not in T4c
      and sorted(reg4c) == sorted(k for k in reg4b if k != NAME_S), lambda: (rc4b, rc4c, row(reg4c, "vst7002"), row(reg4c, "vst7004"), [l for l in out4c if any(s in l for s in SECRETS)]))
check("4 ... a date is only carried on when it is not older than the visit's own date of service (no bill, payment or run of the monitor is): a birth date written where a date belongs is dropped, and the line's 14 days start again",
      lambda: "7006" not in reads(calls4c) and row(reg4c, "vst7006")["state"] == "paid" and row(reg4c, "vst7006")["since"] == "12/21/2026" and "billed" not in row(reg4c, "vst7006") and "paid_on" not in row(reg4c, "vst7006") and BORN_S not in T4c
      and any("vst7006" in l for l in tops(out4c)), lambda: row(reg4c, "vst7006"))

# ==== 5. --dry is the same as a live run; the folder and the day come from arguments or the environment =============================================
fill_history()
W5 = workspace("dry", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rc5, out5, reg5, calls5 = run(W5, "--dry")
W5b = workspace("live", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rc5b, out5b, reg5b, calls5b = run(W5b, "--live")
same = lambda a, b: {k: v for k, v in a.items() if k != "at"} == {k: v for k, v in b.items() if k != "at"}
check("5 --dry and --live are the same run: the same reads, the same lines, the same register (the helper never writes to AdvancedMD, so there is nothing to hold back)",
      lambda: rc5 == rc5b == 0 and calls5 == calls5b and [l.replace(W5, "") for l in out5] == [l.replace(W5b, "") for l in out5b] and same(reg5, reg5b) and len(reg5["visits"]) == 24 and reads(calls5) == sorted(AT61 + AT21), lambda: (rc5, rc5b, len(calls5), len(calls5b)))
check("5 ... and in every run so far the stand-in was never asked to send anything", lambda: rc1 == rc5 == rc5b == rc4 == 0 and len(calls1) > 20 and not any(c[0] in ("WRITE", "fetch") for c in calls1 + calls5 + calls5b + calls4))
_old_env = os.environ.get("BILLING_WORKSPACE"); _old_cwd = os.getcwd()
try:
    os.environ["BILLING_WORKSPACE"] = os.path.dirname(W0); rc5c, out5c, reg5c, calls5c = run(None)
    os.environ.pop("BILLING_WORKSPACE"); os.chdir(os.path.dirname(W00)); rc5d, out5d, reg5d, calls5d = run(None); P5D = os.path.realpath(out5d[-1].split("register: ")[-1]) if out5d else ""
    rc5e, out5e, reg5e, calls5e = run(None, "--workspace", os.path.dirname(W0))
finally:
    os.chdir(_old_cwd)
    if _old_env is None: os.environ.pop("BILLING_WORKSPACE", None)
    else: os.environ["BILLING_WORKSPACE"] = _old_env
check("5 without --registers the folder is <workspace>/registers: the workspace from --workspace, else BILLING_WORKSPACE, else the folder the helper is started in (as its neighbours)",
      lambda: rc5c == 0 and out5c[-1].endswith("register: %s" % os.path.join(W0, "pos61_monitor.json")) and rc5d == 0 and P5D == os.path.realpath(os.path.join(W00, "pos61_monitor.json"))
      and rc5e == 0 and out5e[-1].endswith("register: %s" % os.path.join(W0, "pos61_monitor.json")), lambda: (out5c[-1:], out5d[-1:], out5e[-1:]))
rc5f, out5f, _r, calls5f = run(W0, today="20th of December")
rc5g, out5g, _r, calls5g = run(W0, "--max")
rc5h, out5h, _r, calls5h = run(W0, "--max", "many")
check("5 a day that is no date, or --max without a number, ends with a plain sentence and exit 2 - nothing read", lambda: (rc5f, rc5g, rc5h) == (2, 2, 2) and "--today" in " ".join(out5f) and "--max" in " ".join(out5g) and "--max" in " ".join(out5h)
      and calls5f == calls5g == calls5h == [] and not any(l.startswith("RAISED") for l in out5f + out5g + out5h), lambda: (rc5f, out5f, rc5g, out5g, rc5h, out5h))
rc5j, out5j, _r, calls5j = run(W0, "--stamp", "20261220T1240Z")
check("5 an option the helper does not know is refused in one plain sentence (a misspelt --registers must not make it read another folder)", lambda: rc5j == 2 and "does not know '--stamp'" in " ".join(out5j) and calls5j == [] and len(out5j) == 1, lambda: (rc5j, out5j))
rc5i, out5i, reg5i, _c = run(W0, today="12/20/2026")
check("5 --today takes the day as 2026-12-20 or as 12/20/2026", lambda: rc5i == 0 and reg5i["today"] == "12/20/2026", lambda: (rc5i, out5i))

# ==== 6. the next runs: what is settled is not read again the next day (section 10: it waits for its slow turn); time passes ==========================
SETTLED = ["7002", "7006", "7009", "7011", "7012", "7014", "7016", "7017", "7101", "7102", "7103", "7104"]      # paid with no insurance balance left, a $0 answer the payer is done with, denied or unanswered with no balance left, voided
rc6, out6, reg6, calls6 = run(W1, today="2026-12-21")
check("6 the next run reads again only what is not settled: a visit paid with no insurance balance left, written off or voided keeps what the last read showed",
      lambda: rc6 == 0 and reads(calls6) == sorted(set(AT61 + AT21) - set(SETTLED)) and all(row(reg6, "vst" + v)["read"] == "12/20/2026" for v in SETTLED) and row(reg6, "vst7001")["read"] == "12/21/2026", lambda: (reads(calls6), [row(reg6, "vst" + v).get("read") for v in SETTLED]))
check("6 ... the numbers stay whole: the settled visits are still counted", lambda: line(out6, "REHAB AT 61:").startswith("REHAB AT 61: 17 visit(s) entered; 14 billed; 6 paid ($522.10, average $106.05 per initial visit - ") and line(out6, "REHAB STAYS KEPT AT 21") == S21
      and sorted(re.findall(r"vst\d+", " ".join(tops(out6)))) == ["vst7003", "vst7006", "vst7009", "vst7011", "vst7012", "vst7013"] and row(reg6, "vst7006")["since"] == "12/20/2026", lambda: (line(out6, "REHAB AT 61:"), tops(out6)))
check("6 ... and the days go on: the visit billed 15 days ago reads 16", lambda: row(reg6, "vst7004")["days"] == 16 and row(reg6, "vst7004")["state"] == "open", lambda: row(reg6, "vst7004"))
HIST["7004"] = [chg("70040", "99233", "160.00", "12/05/2026", [pay("-87.00", "12/21/2026", reasons=[("CO45", "73.00")])])]      # the open visit is paid
HIST["7003"] = [chg("70030", "99223", "310.00", "12/12/2026", [pay("0.00", "12/09/2026", reasons=[("CO58", "310.00")]), pay("-141.00", "12/22/2026", reasons=[("CO45", "169.00")])])]   # the denied visit is paid after all
HIST["7008"] = [chg("70080", "99233", "160.00", "12/19/2026", ins="160.00")]                                                 # the visit that could not be read answers now
rc7, out7, reg7, calls7 = run(W1, today="2026-12-23")
check("6 a later run: the open visit is paid, the denied visit is paid after all (its line is gone, the denial stays in its row), the visit that could not be read is read",
      lambda: rc7 == 0 and row(reg7, "vst7004")["state"] == "paid" and row(reg7, "vst7003")["state"] == "paid" and row(reg7, "vst7003")["before"] == ["CO-58"] and row(reg7, "vst7008")["state"] == "open"
      and not any("vst7003" in l for l in tops(out7)) and "since" not in row(reg7, "vst7003") and "said" not in row(reg7, "vst7003") and "8 paid ($750.10, average $117.70 per initial visit" in line(out7, "REHAB AT 61:") and "2 denied (codes CO-16 x1, CO-58 x1" in line(out7, "REHAB AT 61:"), lambda: (line(out7, "REHAB AT 61:"), tops(out7)))
rc8, out8, reg8, calls8 = run(W1, today="2027-01-20")
check("6 a month later: what was open is unanswered over 30 days; a visit paid low, and a denied visit with no balance left, that the monitor has said for more than 14 days has no line any more - it stays in the count and in the register; a denied visit that still carries a balance keeps its line",
      lambda: rc8 == 0 and row(reg8, "vst7008")["state"] == "unanswered" and row(reg8, "vst7008")["days"] == 32 and not any(" paid low: " in l for l in tops(out8)) and "; 2 paid low" in line(out8, "REHAB AT 61:")
      and sorted(re.findall(r"vst\d+", " ".join(tops(out8)))) == ["vst7013"] and "2 denied" in line(out8, "REHAB AT 61:") and row(reg8, "vst7012")["since"] == "12/20/2026", lambda: (row(reg8, "vst7008"), tops(out8), line(out8, "REHAB AT 61:")))
rc8b, out8b, reg8b, calls8b = run(W1, "--line-days", "0", today="2027-01-20")
check("6 --line-days 0 keeps every such line for as long as the visit is denied or paid low", lambda: rc8b == 0 and sorted(re.findall(r"vst\d+", " ".join(l for l in tops(out8b) if " paid low: " in l))) == ["vst7006", "vst7009", "vst7011"]
      and sorted(re.findall(r"vst\d+", " ".join(l for l in tops(out8b) if " DENIED: " in l))) == ["vst7012", "vst7013"], lambda: tops(out8b))
rc9, out9, reg9, calls9 = run(W1, "--all", today="2027-01-20")
check("6 --all reads every visit again, the settled ones too", lambda: rc9 == 0 and reads(calls9) == sorted(AT61 + AT21) and row(reg9, "vst7002")["read"] == "01/20/2027", lambda: reads(calls9))
open(os.path.join(W1, "pos61_monitor.json"), "w").write("{ half a register")
rc10, out10, reg10, calls10 = run(W1, today="2027-01-21")
check("6 a register of its own that cannot be read is no reason to stop: every visit is read again and the register is written whole", lambda: rc10 == 0 and reads(calls10) == sorted(AT61 + AT21) and isinstance(reg10, dict) and len(reg10["visits"]) == 24, lambda: (rc10, out10[-2:]))

# ==== 7. a run is never held up: the cap, three reads in a row without an answer, a login that fails ===================================================
fill_history()
W7 = workspace("cap", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rcA, outA, regA, callsA = run(W7, "--max", "5")
check("7 --max 5: five visits are read, the first five of the day's order; the others are counted as not read yet and the line says that the next run goes on",
      lambda: rcA == 0 and len(reads(callsA)) == 5 and asked(callsA) == TURN1220[:5] == ["7004", "7009", "7102", "7104", "7010"] and regA["counts"]["at 61"]["unread"] + regA["counts"]["kept at 21"]["unread"] == 19
      and any(l.startswith("REHAB MONITOR") and "--max 5" in l and "the next run" in l for l in outA) and row(regA, "vst7001")["state"] == "not read yet", lambda: (reads(callsA), [l for l in outA if l.startswith("REHAB MONITOR")]))
rcB, outB, regB, callsB = run(W7, "--max", "5", today="2026-12-21")
check("7 ... the next run reads five that were never read - not the same five again (of those, the ones that are not settled wait their turn and keep what the last read showed)",
      lambda: rcB == 0 and len(reads(callsB)) == 5 and not (set(reads(callsB)) & set(reads(callsA))) and row(regB, "vst7004")["state"] == "open" and row(regB, "vst7004")["stale"] is True and row(regB, "vst7004")["read"] == "12/20/2026"
      and not any("no register of an earlier run" in l for l in outB), lambda: (reads(callsA), reads(callsB), row(regB, "vst7004")))
fill_history()
for _v in AT61 + AT21: HIST[_v] = ConnectionError("no answer for %s" % NAME_S)
W8 = workspace("down", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rcC, outC, regC, callsC = run(W8)
check("7 AdvancedMD does not answer: after three reads in a row without an answer the run stops asking, says so in one line, names what it could not read, writes its register and ends well",
      lambda: rcC == 0 and len(reads(callsC)) == 3 and any(l.startswith("REHAB MONITOR") and "three reads in a row" in l for l in outC) and regC["counts"]["at 61"]["unread"] == 18 and regC["counts"]["at 61"]["paid"] == 0
      and asked(callsC) == TURN1220[:3] and line(outC, "REHAB AT 61:").startswith("REHAB AT 61: 18 visit(s) entered; 0 billed; 0 paid") and "; 3 could not be read" in line(outC, "REHAB AT 61:") and "; 15 not read yet" in line(outC, "REHAB AT 61:")
      and "; 1 could not be read; 5 not read yet" in line(outC, "REHAB STAYS KEPT AT 21")
      and regC["counts"]["kept at 21"]["unread"] == 6 and not tops(outC) and not any(NAME_S in l for l in outC), lambda: (rcC, len(reads(callsC)), outC))
fill_history()
for _v in ("7004", "7006"): HIST[_v] = ValueError("not an answer")
W9 = workspace("two", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rcD, outD, regD, callsD = run(W9)
check("7 two reads that fail with good reads between them stop nothing: every other visit is read", lambda: rcD == 0 and reads(callsD) == sorted(AT61 + AT21) and regD["counts"]["at 61"]["unread"] == 4 and row(regD, "vst7004")["unread"] == "ValueError"
      and row(regD, "vst7005")["state"] == "unanswered", lambda: (rcD, len(reads(callsD)), regD["counts"]["at 61"]))
fill_history()
for _v in TURN1220[:3]: HIST[_v] = ConnectionError("gone")      # the three visits the day's order starts with (7004, 7009, 7102) never answer
WR = workspace("turn", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rcR1, outR1, regR1, callsR1 = run(WR)
rcR2, outR2, regR2, callsR2 = run(WR, today="2026-12-21")
check("7 three visits that never answer hold up nobody for long: the first run stops at them, the next run starts with the visits it never asked for, reads them all and only then asks those three again",
      lambda: rcR1 == rcR2 == 0 and asked(callsR1) == ["7004", "7009", "7102"] and row(regR1, "vst7004")["asked"] == "12/20/2026" and len(reads(callsR2)) == 23 and asked(callsR2)[-3:] == ["7004", "7009", "7102"]
      and row(regR2, "vst7001")["state"] == "paid" and row(regR2, "vst7004")["state"] == "could not be read" and row(regR2, "vst7004")["asked"] == "12/21/2026" and "asked" not in row(regR2, "vst7001"), lambda: (asked(callsR1), asked(callsR2)))
fill_history(); _ticks = [0]
def _clock(): _ticks[0] += 10; return _ticks[0]      # every look at the clock is ten seconds later
_real_clock = getattr(M, "CLOCK", None)
if M is not None: M.CLOCK = _clock
WT = workspace("time", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rcT, outT, regT, callsT = run(WT, "--seconds", "25")
if M is not None: M.CLOCK = _real_clock
check("7 --seconds 25: the time of one run is looked at before each read - with ten seconds a read, two visits are read; the line says that the next run goes on, and the run ends well",
      lambda: rcT == 0 and asked(callsT) == ["7004", "7009"] and any(l.startswith("REHAB MONITOR") and "--seconds 25" in l and "the next run" in l for l in outT) and regT["ended"] == "time" and regT["limits"]["seconds"] == 25
      and row(regT, "vst7004")["state"] == "open" and row(regT, "vst7011")["state"] == "not read yet", lambda: (rcT, asked(callsT), [l for l in outT if l.startswith("REHAB MONITOR")]))
check("7 ... without --seconds one run reads for 90 seconds at most (a call with the usual two-minute limit ends by itself) and for 400 visits at most", lambda: (M.SECONDS, M.MAX_READS, reg1["limits"]["seconds"], reg1["limits"]["max_reads"]) == (90, 400, 90, 400))
import signal as _signal
_CAUGHT = []
def _test_term(*_a): _CAUGHT.append("the signal reached this test's own handler: the helper had none of its own")
_old_term = _signal.signal(_signal.SIGTERM, _test_term)
fill_history()
def _cut_off():      # the third read is cut off by a time limit: the signal such a limit sends to the helper
    if os.name == "posix": os.kill(os.getpid(), _signal.SIGTERM); time.sleep(0.05)      # the real signal, to this very process (whoever holds the handler at that moment catches it - nobody is ended)
    elif callable(_signal.getsignal(_signal.SIGTERM)): _signal.getsignal(_signal.SIGTERM)(_signal.SIGTERM, None)      # where sending it would end the process: the handler in place is called as the signal would call it
    return history("7102", [chg("71020", "99233", "160.00", "11/28/2026", ins="160.00")])
HIST["7102"] = _cut_off      # the third visit of the day's order
WK = workspace("term", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
try: rcK, outK, regK, callsK = run(WK)
finally: _after_term = _signal.getsignal(_signal.SIGTERM); _signal.signal(_signal.SIGTERM, _old_term)
check("7 stopped from outside (a time limit) in the middle of a read: the reading ends there, the lines are still printed and the register is still written with what was read, and one line says so",
      lambda: rcK == 0 and _CAUGHT == [] and asked(callsK) == ["7004", "7009", "7102"] and row(regK, "vst7004")["state"] == "open" and row(regK, "vst7009")["state"] == "paid" and row(regK, "vst7102")["state"] == "not read yet" and row(regK, "vst7001")["state"] == "not read yet"
      and any(l.startswith("REHAB MONITOR") and "stopped from outside" in l and "after 3 read(s)" in l for l in outK) and regK["ended"] == "stopped" and outK[-1].startswith("register: ") and line(outK, "REHAB AT 61:") != "", lambda: (rcK, _CAUGHT, reads(callsK), outK[-3:]))
check("7 ... and the helper leaves the process as it found it: whoever caught that signal before the run catches it again after it", lambda: _after_term is _test_term)
fill_history(); STATE["login_raises"] = RuntimeError("login refused for %s" % NAME_S)
W10 = workspace("nologin", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rcE, outE, regE, callsE = run(W10); STATE["login_raises"] = None
check("7 the login fails: nothing is read, one line says so (the error's kind, never its words), every visit is counted as not read, the register is written and the run ends well",
      lambda: rcE == 0 and callsE == [("login",)] and any(l.startswith("REHAB MONITOR") and "login" in l and "RuntimeError" in l for l in outE) and not any(NAME_S in l or "refused" in l for l in outE)
      and regE["counts"]["at 61"]["unread"] == 18 and "; 17 not read yet" in line(outE, "REHAB AT 61:") and not tops(outE) and isinstance(regE, dict), lambda: (rcE, callsE, outE))
fill_history()
rcF, outF, regF, callsF = run(W10, today="2026-12-21")
check("7 ... and the run after it reads everything", lambda: rcF == 0 and reads(callsF) == sorted(AT61 + AT21) and line(outF, "REHAB AT 61:").startswith("REHAB AT 61: 17 visit(s) entered; 14 billed; 6 paid ($522.10"), lambda: (rcF, line(outF, "REHAB AT 61:")))
HIST["7003"] = ConnectionError("gone")
rcG, outG, regG, callsG = run(W10, today="2026-12-22")
check("7 a visit that was read before and cannot be read today keeps what the last read showed - its denial line is still printed - and is named as not read today",
      lambda: rcG == 0 and row(regG, "vst7003")["state"] == "denied" and row(regG, "vst7003")["stale"] is True and row(regG, "vst7003")["unread"] == "ConnectionError" and row(regG, "vst7003")["read"] == "12/21/2026"
      and any("vst7003" in l for l in tops(outG)) and any(l.startswith("REHAB MONITOR") and "vst7003" in l and "ConnectionError" in l for l in outG) and "3 denied" in line(outG, "REHAB AT 61:"), lambda: (row(regG, "vst7003"), [l for l in outG if "7003" in l]))

# ==== 8. the reading of one answer, piece by piece ====================================================================================================
def one(charges, vnum="7400", today="2026-12-20", cpts=("99233",)):
    """The row the monitor writes for ONE visit at 61 (date of service 07/15/2026) whose history is the given charge rows."""
    HIST[vnum] = charges; d = workspace("one%d" % len(os.listdir(TMP)), {"20261126T1240Z": {"created": [rehab("vst" + vnum, "pat9500", "07/15/2026", list(cpts), "07/14/2026")]}})
    rc_, out_, reg_, calls_ = run(d, today=today); r_ = dict(row(reg_, "vst" + vnum)); r_["_out"] = out_; r_["_rc"] = rc_; r_["_dir"] = d; return r_
R0 = one([chg("74000", "99233", "160.00", "01/01/1900", [pay("-88.00", BORN_S, createtime="12/31/1899")]), chg("74001", "99497", "133.00", "07/10/2026", ins="133.00")])
check("8 a bill date or a payment date older than the visit's own date of service is no such date (a placeholder, another field's value) and is not kept - the payment still counts, without a day: no date from before the visit is ever written",
      lambda: R0["state"] == "paid" and R0["paid"] == 88.0 and "billed" not in R0 and "paid_on" not in R0 and R0["other"] == [{"code": "99497", "answer": "none", "paid": 0.0, "denial": [], "balance": 133.0}]
      and not any(s in json.dumps({k: v for k, v in R0.items() if not k.startswith("_")}) + " ".join(l for l in R0["_out"] if not l.startswith("register: ")) for s in (BORN_S, "1900", "1899", "07/10/2026"))
      and one([chg("74000", "99233", "160.00", "07/15/2026", [pay("-88.00", "07/15/2026")])])["billed"] == "07/15/2026", lambda: R0)
S0 = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("0.00", "12/10/2026", reasons=[("PR204", "160.00")])], ins="0.00", pat="160.00")])      # denied, and the whole amount now stands on the PATIENT
S1 = run(S0.get("_dir", ""), today="2027-02-01") if S0.get("_dir") else (None, [], None, [])
S2 = one([chg("74000", "99233", "160.00", "11/28/2026", ins="0.00", pat="160.00")])                                                                  # no answer at all, the amount moved to the patient
S3 = run(S2.get("_dir", ""), today="2027-02-01") if S2.get("_dir") else (None, [], None, [])
check("8 a denied visit whose amount now stands on the patient is not settled: it is read again in every run and keeps its line for as long as that balance stands; a visit with no answer and its amount on the patient is not settled either",
      lambda: S0["state"] == "denied" and S0["closed"] is False and S0["balance"] == 160.0 and S0["ins_balance"] == 0 and reads(S1[3]) == ["7400"] and len(tops(S1[1])) == 1 and "PR-204" in tops(S1[1])[0]
      and S2["state"] == "open" and S2["closed"] is False and reads(S3[3]) == ["7400"] and row(S3[2], "vst7400")["state"] == "unanswered", lambda: (S0, S1[1], S2, S3[1]))
A = one([chg("74000", "99233", "160.00", "11/20/2026", ins="160.00")])
check("8 billed exactly 30 days ago is still open; 31 days is unanswered", lambda: A["state"] == "open" and A["days"] == 30 and one([chg("74000", "99233", "160.00", "11/19/2026", ins="160.00")])["state"] == "unanswered", lambda: A)
B = one([chg("74000", "99223", "310.00", "11/28/2026", [pay("-83.21", "12/10/2026")])], cpts=("99223",))
B2 = one([chg("74000", "99223", "310.00", "11/28/2026", [pay("-83.20", "12/10/2026")])], cpts=("99223",))
check("8 paid low is UNDER 60% of the 21 average (60% of $138.67 is $83.202): $83.21 is not, $83.20 is", lambda: B["state"] == "paid" and not B.get("low") and B2["low"] is True and not tops(B["_out"]) and len(tops(B2["_out"])) == 1, lambda: (B, B2))
P = one([chg("74000", "99223", "310.00", "08/01/2026", [pay("-50.00", "08/20/2026")])], cpts=("99223",))      # paid low four months before the monitor sees the visit for the first time
P10 = run(P.get("_dir", ""), today="2026-12-30") if P.get("_dir") else (None, [], None, []); P15 = run(P.get("_dir", ""), today="2027-01-04") if P.get("_dir") else (None, [], None, [])
check("8 a low payment AdvancedMD dates four months back still has its line when the monitor sees it for the first time: the 14 days run from that day (ten days later the line is there, fifteen days later it is not) - the visit is settled, so it is read again only on its slow turn (ten days later: once; five days after that: not)",
      lambda: P["low"] is True and len(tops(P["_out"])) == 1 and (P["said"], P["since"]) == ("paid low", "12/20/2026") and len(tops(P10[1])) == 1 and row(P10[2], "vst7400")["since"] == "12/20/2026" and tops(P15[1]) == []
      and "; 1 paid low" in line(P15[1], "REHAB AT 61:") and asked(P10[3]) == ["7400"] and P15[3] == [] and row(P15[2], "vst7400")["read"] == "12/30/2026", lambda: (P, P10[1], P10[3], P15[1], P15[3]))
C = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("-50.00", "12/10/2026")])])
check("8 a follow-up paid $50.00 has no line while the comparison group has no three paid visits of that code: there is no 21 average to measure it against, and the row says so",
      lambda: C["state"] == "paid" and not C.get("low") and "no 21 average" in C["low_of"] and not tops(C["_out"]), lambda: C)
def beside(n21, paid61, code="99233"):
    """ONE visit at 61 paid `paid61`, beside n21 visits of the same code kept at 21 that were paid $90.00 each -> the row of the visit at 61."""
    created = [rehab("vst7500", "pat9600", "11/26/2026", [code], "11/25/2026")] + [kept("vst76%02d" % i, "pat9601", "11/2%d/2026" % (i % 8), [code], "11/15/2026") for i in range(n21)]
    HIST["7500"] = [chg("75000", code, "160.00", "11/28/2026", [pay("-" + paid61, "12/10/2026")])]
    for i in range(n21): HIST["76%02d" % i] = [chg("76%02d0" % i, code, "160.00", "11/28/2026", [pay("-90.00", "12/10/2026")])]
    rc_, out_, reg_, calls_ = run(workspace("beside%d" % len(os.listdir(TMP)), {"20261126T1240Z": {"created": created}})); r_ = dict(row(reg_, "vst7500")); r_["_out"] = out_; return r_
C2 = beside(2, "40.00"); C3 = beside(3, "40.00")
check("8 ... two paid visits of the comparison group are not yet an average (one unusual payment would decide); with the third the $40.00 is paid low against their $90.00",
      lambda: not C2.get("low") and "no 21 average" in C2["low_of"] and not tops(C2["_out"]) and C3["low"] is True and C3["low_vs"] == 90.0 and C3["low_of"] == "3 paid visit(s) of the comparison group" and len(tops(C3["_out"])) == 1, lambda: (C2, C3))
C4 = beside(3, "54.00"); C5 = beside(3, "53.99")
check("8 ... and exactly 60% is not UNDER 60%: $54.00 of $90.00 has no line, $53.99 has", lambda: C4["state"] == "paid" and not C4.get("low") and not tops(C4["_out"]) and C5["low"] is True and len(tops(C5["_out"])) == 1, lambda: (C4, C5))
D = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("-90.00", "12/10/2026", void="1"), pay("0.00", "12/11/2026", reasons=[("CO50", "160.00")], void="1")], ins="160.00")])
check("8 a voided payment line is no payment and no denial", lambda: D["state"] == "open" and D["paid"] == 0 and not D.get("denial"), lambda: D)
E = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("-90.00", "12/10/2026"), pay("90.00", "12/15/2026"), pay("0.00", "12/15/2026", reasons=[("CO58", "160.00")])], ins="160.00")])
check("8 a payment taken back (the same dollars with the other sign) leaves nothing paid: the visit is denied by the $0 line that came with it", lambda: E["state"] == "denied" and E["paid"] == 0 and E["denial"] == ["CO-58"], lambda: E)
F = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("-90.00", "12/10/2026")]), chg("74001", "99233", "-160.00", "11/28/2026", [pay("0.00", "12/03/2026", reasons=[("CO4", "160.00")])], ins="160.00"), chg("74002", "99233", "160.00", "11/28/2026", void="1", pays=[pay("0.00", "12/01/2026", reasons=[("CO16", "160.00")])]),
         dict(chg("74003", "99233", "160.00", "11/28/2026", [pay("0.00", "12/02/2026", reasons=[("CO18", "160.00")])], ins="160.00"), visit="vst7499")])
check("8 a void charge, a reversal row (a negative amount) and a row of another visit in the answer are not this visit's lines - whatever $0 lines they carry", lambda: F["state"] == "paid" and F["paid"] == 90.0 and not F.get("denial") and not F.get("before")
      and F["fee"] == 160.0 and F["balance"] == 0 and F["closed"] is True, lambda: F)
G = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("-88.00", "12/10/2026")]), chg("74001", "1123F", "0.01", "12/15/2026", [pay("0.00", "12/18/2026", reasons=[("CO246", "0.01")])], ins="0.01")])
check("8 a no-charge reporting line (1123F / M0004) is never the visit: its bill date, its $0 answer and its code are left out", lambda: G["state"] == "paid" and G["billed"] == "11/28/2026" and not G.get("other") and not G.get("zero_codes"), lambda: G)
H = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("0.00", "12/10/2026", reasons=[("PR27", "160.00")]), pay("0.00", "12/12/2026", carrier="HUM01", reasons=[("OAA1", "160.00"), ("MA04", "0")])], ins="160.00")])
check("8 two denials of one visit: every code is kept (a code that is a letter and a number too), the newest day and the carrier of the newest denial are the row's", lambda: H["state"] == "denied" and H["denial"] == ["OA-A1", "PR-27"] and H["remarks"] == ["MA04"] and H["denied_on"] == "12/12/2026" and H["carrier"] == "HUM01", lambda: H)
I = one([chg("74000", "99233", "160.00", "2026-11-28T00:00:00", [pay("-88.00", "2026-12-10")])])
check("8 a date as 2026-11-28 is read like 11/28/2026", lambda: I["billed"] == "11/28/2026" and I["paid_on"] == "12/10/2026", lambda: I)
J = one([dict(chg("74000", "99233", "160.00", "11/28/2026", [pay("-88.00", "12/10/2026")]), insbalance="20.00", patbalance="5.00", insbal="", patbal="")])
check("8 the balances are read under either name AdvancedMD gives them (insbal / insbalance)", lambda: J["balance"] == 25.0 and J["ins_balance"] == 20.0 and J["closed"] is False, lambda: J)
K = one(lambda: ET.fromstring("<PPMDResults><Results><Fault><detail><description>no such visit for %s</description></detail></Fault></Results></PPMDResults>" % NAME_S))
check("8 an answer with no charge row for the visit (a fault, an empty history) is 'could not be read' - never 'voided', never a zero - and its words are not kept",
      lambda: K["state"] == "could not be read" and K["unread"] == "no charge row in the answer" and K["_rc"] == 0 and not any(NAME_S in l for l in K["_out"]), lambda: K)
Q = one([chg("74000", LAST_S[:5], "nan", "11/28/2026", [pay("-inf", "12/10/2026"), pay("-88.00", "12/11/2026")], ins="inf", pat="1e400")])
check("8 a procedure field that holds five letters is no code (the row keeps the import's own code), and an amount that is no number is no amount: the register stays plain JSON",
      lambda: Q["_rc"] == 0 and Q["code"] == "99233" and LAST_S[:5] not in json.dumps({k: v for k, v in Q.items() if not k.startswith("_")}) and (Q["fee"], Q["balance"], Q["ins_balance"], Q["paid"]) == (0.0, 0.0, 0.0, 88.0) and shapes_ok(Q) is None
      and [M.cpt(x) for x in ("99223", "1123F", "M0004", "g0506", "ABCDE", "9922", "992233", None)] == ["99223", "1123F", "M0004", "G0506", "", "", "", ""] and [M.f(x) for x in ("nan", "inf", "-inf", "1e400", "-1,234.50", "$20.00", None, "", "x")] == [0, 0, 0, 0, -1234.5, 20.0, 0, 0, 0], lambda: Q)
N = one([chg("74000", "99497", "133.00", "11/28/2026", [pay("0.00", "12/10/2026", reasons=[("CO58", "133.00")])], ins="133.00")], cpts=("99497",))
check("8 a rehab-stay row whose only line is not a hospital visit code is judged by that line", lambda: N["state"] == "denied" and N["code"] == "99497" and len(tops(N["_out"])) == 1, lambda: N)
fill_history()
WD = workspace("twice", {"20261126T1240Z": {"created": [rehab("vst7001", "pat9101", "11/26/2026", ["99223"], "11/26/2026")]}, "20261126T1240ZR": {"created": [dict(rehab("vst7001", "pat9101", "11/26/2026", ["99223"], "11/26/2026"), fac="fac29", pos="21", pos_lines=["21"], pos_stored=["21"], pos_kind=["rehab-stay-kept-21"])]}})      # (pos_stored follows what the row says it sent, as the import writes it - since 11/25/2026 the stored place is the one that counts)
rcW, outW, regW, callsW = run(WD)
check("8 a visit named in two import registers is ONE visit, read once, and the later register says where it stands", lambda: rcW == 0 and reads(callsW) == ["7001"] and len(regW["visits"]) == 1 and regW["visits"][0]["group"] == "21" and regW["visits"][0]["batch"] == "20261126T1240ZR"
      and outW[0].startswith("REHAB AT 61: no ") and line(outW, "REHAB STAYS KEPT AT 21").startswith("REHAB STAYS KEPT AT 21 (the comparison group): 1 visit(s) entered; 1 billed; 1 paid ($142.10)"), lambda: (rcW, outW))
fill_history()
_no_stay = {k: v for k, v in rehab("vst7002", "pat9101", "11/27/2026", ["99233"], "11/26/2026").items() if k != "stay"}
WS_ = workspace("nostay", {"20261126T1240Z": {"created": ["not a row", 7, None, {"visit": "vst7999"}, {"pid": "pat1", "stay": "rehab", "pos": "61x", "cpts": 5}, dict(rehab("vst7003", "pat9102", "11/26/2026", ["99223"], "11/26/2026"), pos="31", pos_lines=["31"], pos_stored=["31"]),
                                                              _no_stay, rehab("vst7001", "pat9101", "11/26/2026", ["99223"], "11/26/2026")], "skipped": "x", "failed": None}, "20261127T1240Z": ["a list, not a register"], "20261129T1240Z": {"created": "none"}})
rcS, outS, regS, callsS = run(WS_)
check("8 a row with a charge line at 61 is the new group also when the import wrote no stay beside it (61 is only ever written for a rehab stay); rows that are not rows, and registers that are not registers, stop nothing",
      lambda: rcS == 0 and reads(callsS) == ["7001", "7002"] and [v["group"] for v in regS["visits"]] == ["61", "61"] and line(outS, "REHAB AT 61:").startswith("REHAB AT 61: 2 visit(s) entered; 2 billed; 2 paid ($228.10")
      and regS["unreadable_registers"] == ["feed_import_20261127T1240Z.json"], lambda: (rcS, outS))
check("8 ... and a rehab-stay row that stands at neither 61 nor 21 is named, never read and never counted", lambda: any(l.startswith("REHAB MONITOR") and "neither 61 nor 21" in l and "vst7003" in l for l in outS) and "7003" not in reads(callsS), lambda: outS)
# the review's finding (11/25/2026): the group went by what the import SENT - a rehab visit AdvancedMD stored at 21 (the import says POS NOT KEPT at the
# top of its report) was counted, and compared, as a visit at 61. Where the import read the place of service back (pos_stored, one per line), that is the
# place the claim goes out with, and the group is taken from it.
_g = lambda **more: M.group_of(rehab("vst7900", "pat7900", "11/27/2026", ["99232"], "11/26/2026", **more))
check("8 the group of a visit is what AdvancedMD STORED where the import read it back: sent at 61 and stored at 21 = the comparison group (its claim goes out at 21), stored at another place = neither; with no read-back, or one that is not one place per line, what was sent counts as before",
      lambda: (_g(), _g(pos_stored=["21"]), _g(pos_stored=["31"]), _g(pos_stored=None), _g(pos_stored=[]), _g(pos_stored=["21", "21"]), _g(pos_stored="21")) == ("61", "21", "other", "61", "61", "61", "61")
      and M.group_of(rehab("vst7901", "pat7900", "11/27/2026", ["99232", "99497"], "11/26/2026", pos_stored=["61", "21"])) == "61" and M.group_of(kept("vst7902", "pat7900", "11/27/2026", ["99232"], "11/26/2026")) == "21"
      and M.group_of(dict(kept("vst7903", "pat7900", "11/27/2026", ["99232"], "11/26/2026"), pos_stored=["61"])) == "61",
      lambda: (_g(), _g(pos_stored=["21"]), _g(pos_stored=["31"]), _g(pos_stored=None), _g(pos_stored=[]), _g(pos_stored=["21", "21"]), _g(pos_stored="21")))
_tally = getattr(M, "tally", None)
def _broken(*a, **k): raise RuntimeError("an error whose words name %s" % NAME_S)
if M is not None: M.tally = _broken
rcX, outX, regX, callsX = run(workspace("own", {"20261126T1240Z": {"created": [rehab("vst7001", "pat9101", "11/26/2026", ["99223"], "11/26/2026")]}}))
if M is not None: M.tally = _tally
check("8 an error of the helper's own ends it with ONE plain line - the error's kind and the line of the helper, never its words - and exit 2: no traceback in a run's log, nothing raised into the run",
      lambda: rcX == 2 and len(outX) == 1 and outX[0].startswith("REHAB MONITOR: the monitor ended on an error of its own (RuntimeError at line ") and "of pos61_monitor.py" in outX[0] and NAME_S not in outX[0] and "names" not in outX[0], lambda: (rcX, outX))
WF = workspace("nowrite", {"20261126T1240Z": {"created": [rehab("vst7001", "pat9101", "11/26/2026", ["99223"], "11/26/2026")]}}); os.makedirs(os.path.join(WF, "pos61_monitor.json"))      # a folder stands where the register goes
rcF2, outF2, regF2, callsF2 = run(WF)
check("8 a register that cannot be written: the lines are printed all the same, one line says that the register is not written, exit 2, and no half-written file is left behind",
      lambda: rcF2 == 2 and line(outF2, "REHAB AT 61:").startswith("REHAB AT 61: 1 visit(s) entered; 1 billed; 1 paid ($142.10") and any(l.startswith("REHAB MONITOR: its register") and "could not be written" in l for l in outF2)
      and sorted(os.listdir(WF)) == ["feed_import_20261126T1240Z.json", "pos61_monitor.json"] and not any(l.startswith(("RAISED", "register: ")) for l in outF2), lambda: (rcF2, outF2, sorted(os.listdir(WF))))
check("8 the reason codes as the report writes them: the group and the number (CO-58), a remark code as it is (N620), anything else '?'",
      lambda: [M.show(M.reason(c)) for c in ("CO58", "co-45", "PR2", "OA23", "PI253", "COA1", "PRB9", "58", "A1", "MA04", "N620", "M56", "see note", "", None)] == ["CO-58", "CO-45", "PR-2", "OA-23", "PI-253", "CO-A1", "PR-B9", "58", "A1", "MA04", "N620", "M56", "?", "", ""])
def _tuple_of(rel, name):
    """The codes a helper keeps under that name, read from its source text (the helper itself is never loaded here: it talks to AdvancedMD)."""
    m_ = re.search(r"^%s = [({]([^)}]*)[)}]" % name, open(os.path.join(ROOT, rel)).read(), re.M); return set(re.findall(r'"([0-9A-Z]+)"', m_.group(1))) if m_ else None
check("8 the codes that never make a denial are the ones the practice's ageing page never counts as one either - 45, 253, 23, 94, 246 and the cost shares 1, 2, 3 - code for code with both copies of aging_refresh.py (a code added there alone would be a denial here and none there)",
      lambda: set(M.INFO_REASONS) == {"45", "253", "23", "94", "1", "2", "3", "246"} == _tuple_of("tools/button/aging_refresh.py", "INFO_REASONS") == _tuple_of("scripts/helpers/aging_refresh.py", "INFO_REASONS"),
      lambda: (sorted(M.INFO_REASONS), _tuple_of("tools/button/aging_refresh.py", "INFO_REASONS"), _tuple_of("scripts/helpers/aging_refresh.py", "INFO_REASONS")))
check("8 ... and the no-charge reporting lines that are never the visit are that page's own (1123F, 1124F, M0004)", lambda: set(M.REPORTING) == {"1123F", "1124F", "M0004"} == _tuple_of("tools/button/aging_refresh.py", "REPORTING") == _tuple_of("scripts/helpers/aging_refresh.py", "REPORTING"))
_imp = open(os.path.join(ROOT, "scripts", "helpers", "claimocity_import.py")).read(); _fam = re.search(r'set\("(99221 [0-9 ]+)"\.split\(\)\)', _imp)      # the hospital set of the import's EM_FAMILY, from its source text
check("8 the codes that ARE the visit are the import's own hospital visit family (EM_FAMILY), code for code, and an initial hospital visit is 99221-99223",
      lambda: set(M.HOSP_FAMILY) == set(_fam.group(1).split()) and M.INITIAL == {"99221", "99222", "99223"} and M.INITIAL < set(M.HOSP_FAMILY), lambda: (sorted(M.HOSP_FAMILY), _fam and _fam.group(1)))

# ==== 9. a run WITHOUT its memory (review finding, 11/25/2026: every such run read the same oldest visits; a denial on a newer one was never seen) =======
fill_history()
V9 = ["75%02d" % i for i in range(12)]                                                    # twelve visits at 61, dates of service 11/10 ... 11/21/2026
CREATED9 = [rehab("vst" + v, "pat96" + v[2:], "11/%02d/2026" % (10 + i), ["99233"], "11/09/2026") for i, v in enumerate(V9)]
for v in V9[:11]: HIST[v] = [chg(v + "0", "99233", "160.00", "11/28/2026", [pay("-86.00", "12/10/2026", reasons=[("CO45", "74.00")])])]      # eleven are paid in full ...
HIST["7511"] = [chg("75110", "99233", "160.00", "11/28/2026", [pay("0.00", "12/10/2026", reasons=[("CO58", "160.00")])], ins="160.00")]         # ... the NEWEST one is denied
W9A = workspace("nomem", {"20261126T1240Z": {"created": CREATED9}}); RUNS9 = []
for _t in ("2026-12-20", "2026-12-21", "2026-12-22", "2026-12-23", "2026-12-24", "2026-12-25"):
    _rc, _out, _reg, _calls = run(W9A, "--max", "5", today=_t); RUNS9.append((_rc, _out, asked(_calls)))
    try: os.remove(os.path.join(W9A, "pos61_monitor.json"))      # the fresh container of every run: the register of the run before is not there
    except OSError: pass
check("9 a workspace that never holds the register of the run before (five reads a run, six days): the runs do NOT read the same five visits again and again - every one of the twelve visits is read, and the denied one has its DENIED line",
      lambda: all(r[0] == 0 and len(r[2]) == 5 for r in RUNS9) and len({tuple(r[2]) for r in RUNS9}) == 6 and sorted({v for r in RUNS9 for v in r[2]}) == V9 and any("vst7511" in l for r in RUNS9 for l in tops(r[1])), lambda: [r[2] for r in RUNS9])
check("9 ... each such run reads five visits in a row of the list by date of service, starting at that day's place in it: 12/20 at the 8th of 12 (.610655 x 12 = 7.3), 12/21 at the 3rd (.228689 x 12 = 2.7), 12/22 at the 11th and round to the start (.846723 x 12 = 10.2)",
      lambda: [r[2] for r in RUNS9[:3]] == [["7507", "7508", "7509", "7510", "7511"], ["7502", "7503", "7504", "7505", "7506"], ["7510", "7511", "7500", "7501", "7502"]], lambda: [r[2] for r in RUNS9[:3]])
check("9 ... and each of them says so in one line - it had no register of an earlier run to go by, its counts and lines hold only what it read - and promises the next run's order only 'as long as this run's register reaches it'",
      lambda: all(len([l for l in r[1] if l.startswith("REHAB MONITOR") and "no register of an earlier run" in l and "pos61_monitor.json was not there or could not be read" in l and "hold only what this run read" in l and "another place each day" in l]) == 1
                  and any(l.startswith("REHAB MONITOR") and "7 visit(s) were not read in this run (--max 5 reads a run) - the next run reads them first, as long as this run's register reaches it" in l for l in r[1]) for r in RUNS9), lambda: [l for l in RUNS9[0][1] if l.startswith("REHAB MONITOR")])
W9B = workspace("mem", {"20261126T1240Z": {"created": CREATED9}}); RUNS9B = []
for _t in ("2026-12-20", "2026-12-21", "2026-12-22"):
    _rc, _out, _reg, _calls = run(W9B, "--max", "5", today=_t); RUNS9B.append((_rc, _out, asked(_calls), _reg))
check("9 with the register kept the runs go on where the one before stopped: 5, then 5 others, then the last 2 and - again - the denied visit, which is not settled; only the first run speaks of a missing register",
      lambda: [r[2] for r in RUNS9B] == [["7507", "7508", "7509", "7510", "7511"], ["7501", "7502", "7503", "7504", "7505"], ["7506", "7500", "7511"]] and [any("no register of an earlier run" in l for l in r[1]) for r in RUNS9B] == [True, False, False]
      and not any("were not read in this run" in l for l in RUNS9B[2][1]) and all(any("vst7511" in l for l in tops(r[1])) for r in RUNS9B), lambda: [r[2] for r in RUNS9B])
W9C = workspace("oldmem", {"20261126T1240Z": {"created": CREATED9}}); rc9c, out9c, reg9c, calls9c = run(W9C, "--max", "5")      # 12/20: five are read and remembered ...
_frozen = open(os.path.join(W9C, "pos61_monitor.json")).read() if os.path.exists(os.path.join(W9C, "pos61_monitor.json")) else "{}"; RUNS9C = []
for _t in ("2026-12-25", "2026-12-26"):      # ... and then the SAME register of 12/20 comes back before every run (the runs' own registers are not carried on, or cannot be written)
    open(os.path.join(W9C, "pos61_monitor.json"), "w").write(_frozen); _rc, _out, _reg, _calls = run(W9C, "--max", "5", today=_t); RUNS9C.append((_rc, _out, asked(_calls), _reg))
check("9 a register that is more than two days old is not trusted for whose turn it is (the same old register comes back before every run): the runs still get round - the seven visits it never read, and the denied one, are all read within two runs, not the same five each time",
      lambda: asked(calls9c) == ["7507", "7508", "7509", "7510", "7511"] and [r[2] for r in RUNS9C] == [["7505", "7506", "7511", "7500", "7501"], ["7502", "7503", "7504", "7505", "7506"]]
      and sorted({v for r in RUNS9C for v in r[2]}) == V9[:7] + ["7511"], lambda: (asked(calls9c), [r[2] for r in RUNS9C]))
check("9 ... what that register says of a visit still stands until the visit is read again (the settled ones stay counted as paid), and the run says in one line how old the register is that came back",
      lambda: all(r[0] == 0 and row(r[3], "vst7508")["state"] == "paid" and row(r[3], "vst7508")["read"] == "12/20/2026" for r in RUNS9C)
      and len([l for l in RUNS9C[0][1] if l.startswith("REHAB MONITOR") and "no register of an earlier run to go by (the one that came back is of 12/20/2026, 5 days before this run)" in l]) == 1, lambda: [l for l in RUNS9C[0][1] if l.startswith("REHAB MONITOR")])
def _cover(n, k, days, first="2026-12-01"):
    """How many of n visits a run without memory reaches within `days` days when it reads k a run from the place the helper gives for each day."""
    d0 = M.day(first); seen = set()
    for i in range(days):
        s = M.start_of(d0 + M.datetime.timedelta(days=i), n); seen |= {(s + j) % n for j in range(k)}
    return len(seen)
check("9 the day's place spreads the starts evenly whatever one run reads: 720 visits at 57 reads a run are all reached within 25 days, at 36 a run within 40 days, at 20 a run within 62 days (the delivered order: the same 57 for ever)",
      lambda: (_cover(720, 57, 25), _cover(720, 36, 40), _cover(720, 20, 62), _cover(300, 57, 10), _cover(12, 5, 3)) == (720, 720, 720, 300, 12) and M.start_of(M.day("2026-12-20"), 23) == 14 and M.start_of(M.day("2026-12-20"), 0) == 0
      and all(0 <= M.start_of(M.day("2026-12-01") + M.datetime.timedelta(days=i), n) < n for i in range(60) for n in (1, 2, 7, 23)), lambda: (_cover(720, 57, 25), _cover(720, 36, 40), _cover(720, 20, 62)))
check("9 a run that reads every visit says nothing of a missing register (the first run ever has none either); a register that cannot be written says what that means for the next run",
      lambda: not any("no register of an earlier run" in l for l in out1 + out5 + out10) and any(l.startswith("REHAB MONITOR: its register") and "could not be written" in l and "the next run does not know what this run read" in l for l in outF2), lambda: outF2)
HEAD = SRC.split("\nimport ", 1)[0]
check("9 the header no longer says that nothing is lost without the memory - it says what such a run does and what its lines hold", lambda: "nothing is lost" not in SRC and "WITHOUT THE MEMORY" in HEAD and "golden ratio" in HEAD and "more than 2 days old" in HEAD and (M.TURN_DAYS, round(M.GOLDEN, 6)) == (2, 0.618034))

# ==== 10. a settled visit is read again on a slow turn (review finding: it was never read again - a payment taken back later was never reported) ==========
fill_history()
TB = one([chg("74000", "99223", "310.00", "11/28/2026", [pay("-142.10", "12/10/2026", reasons=[("CO45", "167.90")])])], cpts=("99223",))      # 12/20: paid, nothing left on insurance - settled
TB1 = run(TB.get("_dir", ""), today="2026-12-21") if TB.get("_dir") else (None, [], None, []); TB6 = run(TB.get("_dir", ""), today="2026-12-26") if TB.get("_dir") else (None, [], None, [])
TB7 = run(TB.get("_dir", ""), today="2026-12-27") if TB.get("_dir") else (None, [], None, []); TB13 = run(TB.get("_dir", ""), today="2027-01-02") if TB.get("_dir") else (None, [], None, [])
HIST["7400"] = [chg("74000", "99223", "310.00", "11/28/2026", [pay("-142.10", "12/10/2026", reasons=[("CO45", "167.90")]), pay("142.10", "01/15/2027"), pay("0.00", "01/15/2027", reasons=[("CO58", "310.00"), ("N620", "0")])], ins="310.00")]
TB27 = run(TB.get("_dir", ""), today="2027-01-16") if TB.get("_dir") else (None, [], None, [])      # the payer took the payment back on 01/15 and denied with CO-58: the $310.00 stands on insurance again
check("10 a settled visit is not read again the next day nor on the sixth day - on the seventh day it is (SETTLED_DAYS), and then not again for six days",
      lambda: TB["closed"] is True and TB["state"] == "paid" and [asked(x[3]) for x in (TB1, TB6, TB7, TB13)] == [[], [], ["7400"], []] and row(TB13[2], "vst7400")["read"] == "12/27/2026" and (M.SETTLED_DAYS, M.SETTLED_EVERY) == (7, 5), lambda: (TB, [x[3] for x in (TB1, TB6, TB7, TB13)]))
check("10 a payment taken back and denied AFTER the visit was settled is seen at its next slow read: the visit is denied, the dollars are out of the paid count, and the DENIED line stands at the top",
      lambda: TB27[0] == 0 and asked(TB27[3]) == ["7400"] and row(TB27[2], "vst7400")["state"] == "denied" and row(TB27[2], "vst7400")["closed"] is False and row(TB27[2], "vst7400")["paid"] == 0 and row(TB27[2], "vst7400")["balance"] == 310.0
      and tops(TB27[1]) == ["TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7400 pat9500 service date 07/15/2026 99223 carrier FLO02 denied 01/15/2027 with CO-58 (remark N620), balance $310.00 " + QUESTION]
      and line(TB27[1], "REHAB AT 61:").startswith("REHAB AT 61: 1 visit(s) entered; 1 billed; 0 paid ($0.00, no initial visit paid yet - " + BASE + "); 1 denied (codes CO-58 x1)"), lambda: (asked(TB27[3]), TB27[1]))
V10 = ["78%02d" % i for i in range(20)]      # twenty visits at 61: the first twelve billed and never answered (not settled), the last eight paid in full (settled)
for i, v in enumerate(V10): HIST[v] = [chg(v + "0", "99233", "160.00", "11/28/2026", ins="160.00")] if i < 12 else [chg(v + "0", "99233", "160.00", "11/28/2026", [pay("-86.00", "11/30/2026", reasons=[("CO45", "74.00")])])]
WS10 = workspace("slow", {"20261126T1240Z": {"created": [rehab("vst" + v, "pat98" + v[2:], "11/%02d/2026" % (1 + i), ["99233"], "10/31/2026") for i, v in enumerate(V10)]}})
S1 = run(WS10, today="2026-12-01"); S2 = run(WS10, "--max", "12", today="2026-12-07"); S3 = run(WS10, "--max", "10", today="2026-12-08")
check("10 six days after every visit was read: the twelve that are not settled are read again, none of the settled ones yet",
      lambda: S1[0] == S2[0] == 0 and sorted(asked(S1[3])) == V10 and sorted(asked(S2[3])) == V10[:12] and all(row(S2[2], "vst" + v)["closed"] is True and row(S2[2], "vst" + v)["read"] == "12/01/2026" for v in V10[12:]), lambda: (asked(S1[3]), asked(S2[3])))
check("10 with more visits waiting than one run reads, every FIFTH read of the run goes to a settled visit - the one read longest ago - so the settled ones are neither forgotten nor in the way: ten reads = eight unsettled and two settled",
      lambda: S3[0] == 0 and asked(S3[3]) == ["7800", "7801", "7802", "7803", "7812", "7804", "7805", "7806", "7807", "7813"] and row(S3[2], "vst7812")["read"] == "12/08/2026" and row(S3[2], "vst7814")["read"] == "12/01/2026", lambda: asked(S3[3]))
check("10 ... the line of that run counts the four UNSETTLED visits it did not get to - the settled ones that wait for their slow turn are not 'not read' and are not marked stale",
      lambda: any(l.startswith("REHAB MONITOR: 4 visit(s) were not read in this run (--max 10 reads a run)") for l in S3[1]) and all(row(S3[2], "vst" + v).get("stale") is True for v in V10[8:12]) and not any(row(S3[2], "vst" + v).get("stale") for v in V10[12:])
      and not any("settled visit(s) were last read" in l for l in S3[1]), lambda: [l for l in S3[1] if l.startswith("REHAB MONITOR")])
S4 = run(WS10, "--max", "4", today="2027-01-15"); S5 = run(WS10, today="2027-01-16")
check("10 when the slow turn falls behind - settled visits last read more than 30 days ago that the run did not get to - one line says how many, since when, and what that means",
      lambda: S4[0] == 0 and len(asked(S4[3])) == 4 and set(asked(S4[3])) <= set(V10[:12]) and len([l for l in S4[1] if l.startswith("REHAB MONITOR: 8 settled visit(s) were last read more than 30 days ago (the oldest on 12/01/2026) and this run did not get to them") and "taken back" in l and "--seconds" in l]) == 1
      and M.SETTLED_LATE == 30, lambda: [l for l in S4[1] if l.startswith("REHAB MONITOR")])
check("10 ... and a run with time left reads them: the unsettled visits and, between them and after them, every settled one that is due",
      lambda: S5[0] == 0 and sorted(asked(S5[3])) == V10 and not any("settled visit(s) were last read" in l or "were not read in this run" in l for l in S5[1]) and all(row(S5[2], "vst" + v)["read"] == "01/16/2027" for v in V10), lambda: (asked(S5[3]), [l for l in S5[1] if l.startswith("REHAB MONITOR")]))
check("10 the header says what a settled visit is and that it is read again on a SLOW TURN (no longer: never, unless somebody calls --all)", lambda: "SLOW TURN" in HEAD and "is not read\n#   again" not in HEAD and "is not read again" not in HEAD and "every fifth read" in HEAD)

# ==== 11. per payer the NEWEST answer leads (review finding: a denial dated after a payment was filed as an earlier one - the visit read paid) =============
fill_history()
FIRST_PAID = [pay("-111.00", "12/10/2026", reasons=[("CO45", "171.33"), ("PR2", "27.67")])]
NA = one([chg("74000", "99223", "310.00", "12/12/2026", FIRST_PAID + [pay("0.00", "12/18/2026", carrier="MCAD", reasons=[("CO58", "27.67"), ("N620", "0")])], ins="27.67", carrier="MCAD")], cpts=("99223",))
check("11 the first payer paid on 12/10, the SECOND payer answered $0 with CO-58 on 12/18 and its share still stands on insurance: the visit is DENIED - by that payer, on that day - not 'paid'; the first payer's dollars stay in the row and the visit stays open",
      lambda: NA["state"] == "denied" and NA["denial"] == ["CO-58"] and NA["remarks"] == ["N620"] and NA["carrier"] == "MCAD" and NA["denied_on"] == "12/18/2026" and (NA["paid"], NA["paid_by"], NA["paid_on"]) == (111.0, "FLO02", "12/10/2026")
      and NA["balance"] == 27.67 and NA["closed"] is False and "before" not in NA and "pending" not in NA and "resent" not in NA and (NA["said"], NA["since"]) == ("denied", "12/20/2026"), lambda: NA)
check("11 ... its line stands at the top, with the payment beside the denial",
      lambda: tops(NA["_out"]) == ["TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7400 pat9500 service date 07/15/2026 99223 carrier MCAD denied 12/18/2026 with CO-58 (remark N620), balance $27.67, with $111.00 paid by FLO02 on 12/10/2026 " + QUESTION], lambda: NA["_out"])
check("11 ... and the count says it: one denied, with the dollars that were paid on it named and NOT counted as paid",
      lambda: line(NA["_out"], "REHAB AT 61:") == "REHAB AT 61: 1 visit(s) entered; 1 billed; 0 paid ($0.00, no initial visit paid yet - " + BASE + "); 1 denied (codes CO-58 x1 - $111.00 paid on 1 of them, not counted as paid); 0 billed and unanswered for over 30 days"
      and not line(NA["_out"], "REHAB PAID PER CODE"), lambda: NA["_out"])
NB = one([chg("74000", "99223", "310.00", "11/28/2026", [pay("-142.10", "12/10/2026", reasons=[("CO45", "167.90")]), pay("0.00", "01/15/2027", reasons=[("CO58", "310.00")])], ins="0.00")], cpts=("99223",), today="2027-01-16")
NB1 = run(NB.get("_dir", ""), today="2027-01-17") if NB.get("_dir") else (None, [], None, []); NB45 = run(NB.get("_dir", ""), today="2027-03-02") if NB.get("_dir") else (None, [], None, [])
HIST["7400"] = [chg("74000", "99223", "310.00", "11/28/2026", [pay("-142.10", "12/10/2026", reasons=[("CO45", "167.90")]), pay("0.00", "01/15/2027", reasons=[("CO58", "310.00")]), pay("142.10", "03/05/2027")], ins="310.00")]      # 03/05: the take-back is on the charge
NB48 = run(NB.get("_dir", ""), today="2027-03-06") if NB.get("_dir") else (None, [], None, [])
check("11 the SAME payer paid on 12/10 and answered again on 01/15 with $0 and CO-58 (its take-back is not on the charge yet): denied - its newest answer leads; the payment that still stands is named, and the visit is NOT settled although no balance shows",
      lambda: NB["state"] == "denied" and NB["denial"] == ["CO-58"] and NB["pending"] is True and NB["closed"] is False and (NB["paid"], NB["paid_by"], NB["paid_on"], NB["denied_on"], NB["balance"]) == (142.1, "FLO02", "12/10/2026", "01/15/2027", 0.0)
      and tops(NB["_out"]) == ["TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7400 pat9500 service date 07/15/2026 99223 carrier FLO02 denied 01/15/2027 with CO-58, balance $0.00, with $142.10 paid by FLO02 on 12/10/2026 (the payer that denies: its payment still stands) " + QUESTION]
      and "1 denied (codes CO-58 x1 - $142.10 paid on 1 of them, not counted as paid)" in line(NB["_out"], "REHAB AT 61:") and "written off" not in line(NB["_out"], "REHAB AT 61:"), lambda: (NB, NB["_out"]))
check("11 ... it is read again in EVERY run for as long as that payment stands against the denial; its line is said for 14 days like every line without a balance (nothing would end it if the take-back never came) and the visit stays in the count",
      lambda: asked(NB1[3]) == ["7400"] and len(tops(NB1[1])) == 1 and "its payment still stands" in tops(NB1[1])[0] and asked(NB45[3]) == ["7400"] and tops(NB45[1]) == [] and row(NB45[2], "vst7400")["closed"] is False
      and "1 denied (codes CO-58 x1 - $142.10 paid on 1 of them, not counted as paid)" in line(NB45[1], "REHAB AT 61:") and row(NB45[2], "vst7400")["since"] == "01/16/2027", lambda: (NB1[3], NB1[1], NB45[3], NB45[1]))
check("11 ... and the day the take-back is on the charge the line is back, to stay: the balance stands on insurance again and nothing is paid",
      lambda: asked(NB48[3]) == ["7400"] and row(NB48[2], "vst7400")["paid"] == 0 and "pending" not in row(NB48[2], "vst7400") and "paid_by" not in row(NB48[2], "vst7400")
      and tops(NB48[1]) == ["TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7400 pat9500 service date 07/15/2026 99223 carrier FLO02 denied 01/15/2027 with CO-58, balance $310.00 " + QUESTION]
      and line(NB48[1], "REHAB AT 61:").startswith("REHAB AT 61: 1 visit(s) entered; 1 billed; 0 paid ($0.00, no initial visit paid yet - " + BASE + "); 1 denied (codes CO-58 x1); "), lambda: (NB48[3], NB48[1], row(NB48[2], "vst7400")))
NC = one([chg("74000", "99233", "160.00", "12/12/2026", [pay("-70.00", "12/10/2026", reasons=[("CO45", "72.40"), ("PR2", "17.60")]), pay("0.00", "12/18/2026", carrier="MCAD", reasons=[("CO58", "17.60")])], ins="0.00", carrier="MCAD")])
NC15 = run(NC.get("_dir", ""), today="2027-01-04") if NC.get("_dir") else (None, [], None, [])
check("11 the second payer's denial after the first one paid, with nothing left on insurance since: still a denied visit, said at the top for its 14 days and kept in the count - and settled (nothing more is expected); the line does not guess that it was written off",
      lambda: NC["state"] == "denied" and NC["closed"] is True and NC["balance"] == 0 and "pending" not in NC
      and tops(NC["_out"]) == ["TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7400 pat9500 service date 07/15/2026 99233 carrier MCAD denied 12/18/2026 with CO-58, balance $0.00, with $70.00 paid by FLO02 on 12/10/2026 " + QUESTION]
      and tops(NC15[1]) == [] and "1 denied (codes CO-58 x1 - $70.00 paid on 1 of them, not counted as paid)" in line(NC15[1], "REHAB AT 61:"), lambda: (NC, NC["_out"], NC15[1]))
ND = one([chg("74000", "99223", "310.00", "12/12/2026", [pay("0.00", "12/10/2026", reasons=[("CO45", "140.00"), ("PR1", "170.00")]), pay("0.00", "12/18/2026", carrier="MCAD", reasons=[("CO58", "170.00")])], ins="170.00", carrier="MCAD")], cpts=("99223",))
check("11 (as before) the first payer answered $0 with cost-share codes only, the second payer denied: denied by the second payer",
      lambda: ND["state"] == "denied" and ND["carrier"] == "MCAD" and ND["paid"] == 0 and "paid_by" not in ND and tops(ND["_out"]) == ["TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7400 pat9500 service date 07/15/2026 99223 carrier MCAD denied 12/18/2026 with CO-58, balance $170.00 " + QUESTION], lambda: (ND, ND["_out"]))
OTHER_FIRST = [pay("0.00", "12/01/2026", carrier="HUM01", reasons=[("CO58", "160.00")]), pay("-90.00", "12/10/2026", reasons=[("CO45", "70.00")])]      # one payer denied on 12/01, ANOTHER payer paid on 12/10
NE = one([chg("74000", "99233", "160.00", "12/03/2026", OTHER_FIRST, ins="0.00")]); NE2 = one([chg("74000", "99233", "160.00", "12/03/2026", OTHER_FIRST, ins="70.00")])
check("11 a denial of a payer that paid NOTHING stands also when ANOTHER payer paid afterwards (the first payer denied for the place of service, a second plan paid a part): denied by the first payer, the payment named, and never 'no answer yet' - open while a balance stands on insurance, settled once none does",
      lambda: [(x["state"], x["carrier"], x["denial"], x["paid"], x["paid_by"], x["closed"], "before" in x, "resent" in x) for x in (NE, NE2)] == [("denied", "HUM01", ["CO-58"], 90.0, "FLO02", True, False, False), ("denied", "HUM01", ["CO-58"], 90.0, "FLO02", False, False, False)]
      and tops(NE["_out"]) == ["TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7400 pat9500 service date 07/15/2026 99233 carrier HUM01 denied 12/01/2026 with CO-58, balance $0.00, with $90.00 paid by FLO02 on 12/10/2026 " + QUESTION]
      and tops(NE2["_out"]) == ["TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7400 pat9500 service date 07/15/2026 99233 carrier HUM01 denied 12/01/2026 with CO-58, balance $70.00, with $90.00 paid by FLO02 on 12/10/2026 " + QUESTION], lambda: (NE, NE2, NE["_out"], NE2["_out"]))
NF1 = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("-90.00", "12/10/2026", carrier="", source="2"), pay("0.00", "12/18/2026", carrier="", reasons=[("CO58", "160.00")])], ins="0.00")])
NF2 = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("0.00", "12/01/2026", carrier="", reasons=[("CO58", "160.00")]), pay("-90.00", "12/10/2026", carrier="", source="2")], ins="0.00")])
NF3 = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("0.00", "12/01/2026", carrier="", reasons=[("CO58", "160.00")]), pay("-90.00", "12/10/2026", reasons=[("CO45", "70.00")])], ins="0.00")])
NF4 = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("-90.00", "12/10/2026", reasons=[("CO45", "70.00")]), pay("0.00", "12/10/2026", reasons=[("CO58", "160.00")])], ins="0.00")])
check("11 lines that name no carrier are never taken for ANOTHER payer's - the dates decide: a denial after the payment is a denial, a denial before it (or on the same day) is an earlier one and the visit is paid",
      lambda: NF1["state"] == "denied" and NF1["pending"] is True and NF1["paid"] == 90.0 and "paid_by" not in NF1 and "with $90.00 paid on 12/10/2026 (the payer that denies: its payment still stands)" in tops(NF1["_out"])[0]
      and [(x["state"], x.get("before"), x["closed"]) for x in (NF2, NF3, NF4)] == [("paid", ["CO-58"], True)] * 3, lambda: (NF1, NF2, NF3, NF4))
DUP = lambda code, car="FLO02", more=(): one([chg("74000", "99233", "160.00", "11/28/2026", [pay("-90.00", "12/10/2026", reasons=[("CO45", "70.00")]), pay("0.00", "12/20/2026", carrier=car, reasons=[(code, "160.00")] + list(more))], ins="0.00")])
NG1 = DUP("CO18"); NG2 = DUP("OAB13"); NG3 = DUP("CO18", more=[("CO58", "160.00")]); NG4 = DUP("CO18", car="HUM01")
NG5 = one([chg("74000", "99233", "160.00", "11/28/2026", [pay("0.00", "12/20/2026", reasons=[("CO18", "160.00")])], ins="160.00")])
check("11 one exception: a $0 line that only says the claim was paid already (18 exact duplicate, B13 previously paid), dated after the SAME payer's standing payment, denies nothing - the visit stays paid and settled, the code is kept in the row under 'dup'",
      lambda: [(x["state"], x.get("dup"), x["closed"], tops(x["_out"])) for x in (NG1, NG2)] == [("paid", ["CO-18"], True, []), ("paid", ["OA-B13"], True, [])] and "before" not in NG1 and set(M.ALREADY_PAID) == {"18", "B13"}, lambda: (NG1, NG2))
check("11 ... with a code beside it that denies, from a payer that paid nothing, or with nothing paid at all, the same code IS a denial",
      lambda: [(x["state"], x["denial"]) for x in (NG3, NG4, NG5)] == [("denied", ["CO-18", "CO-58"]), ("denied", ["CO-18"]), ("denied", ["CO-18"])] and NG3["pending"] is True and NG4["carrier"] == "HUM01" and "pending" not in NG4, lambda: (NG3, NG4, NG5))
NH = one([chg("74000", "99223", "310.00", "12/05/2026", [pay("0.00", "12/01/2026", reasons=[("CO58", "310.00")]), pay("0.00", "12/15/2026", reasons=[("CO45", "140.00"), ("PR1", "170.00")])], ins="0.00", pat="170.00")], cpts=("99223",))
NH2 = run(NH.get("_dir", ""), today="2027-03-20") if NH.get("_dir") else (None, [], None, [])
check("11 denied on 12/01, sent again, and the SAME payer answered on 12/15 with $0 and cost-share codes only: its newest answer is no denial - 'answered $0', the denial kept as an earlier one; no DENIED line stands for months with the words 'no answer yet'",
      lambda: NH["state"] == "answered $0" and NH["zero_codes"] == ["CO-45", "PR-1"] and NH["before"] == ["CO-58"] and "denial" not in NH and "resent" not in NH and NH["paid_on"] == "12/15/2026"
      and [l.startswith("TOP OF THE REPORT - PLACE OF SERVICE 61 paid low: vst7400 ") for l in tops(NH["_out"])] == [True] and tops(NH2[1]) == [] and "0 denied" in line(NH2[1], "REHAB AT 61:") and "; 1 answered with $0 and no denial code (CO-45 x1, PR-1 x1)" in line(NH2[1], "REHAB AT 61:"), lambda: (NH, NH["_out"], NH2[1]))
NI = one([chg("74000", "99223", "310.00", "12/05/2026", [pay("0.00", "12/01/2026", reasons=[("CO58", "310.00")]), pay("0.00", "12/15/2026", carrier="MCAD", reasons=[("OA23", "310.00")])], ins="310.00")], cpts=("99223",))
check("11 ... ANOTHER payer's later $0 answer leaves the first payer's denial standing - and its line says 'sent again ... no answer yet' only when no answer of any payer is dated after the day it went out again",
      lambda: NI["state"] == "denied" and NI["carrier"] == "FLO02" and NI["denied_on"] == "12/01/2026" and "resent" not in NI and "no answer yet" not in tops(NI["_out"])[0] and "sent again 12/05/2026 - no answer yet" in line(T1, "TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7013"), lambda: (NI, NI["_out"]))
NJ = one([chg("74000", "99223", "310.00", "11/28/2026", [pay("0.00", "12/01/2026", reasons=[("CO58", "310.00")]), pay("0.00", "12/15/2026", reasons=[("N620", "0")])], ins="310.00")], cpts=("99223",))
check("11 ... a later $0 line that carries a remark code only answers nothing: the denial stands, and the remark is kept with it",
      lambda: NJ["state"] == "denied" and NJ["denial"] == ["CO-58"] and NJ["denied_on"] == "12/01/2026" and "before" not in NJ and NJ.get("remarks") == ["N620"] and "(remark N620)" in tops(NJ["_out"])[0], lambda: (NJ, NJ["_out"]))
for i in range(3): HIST["760%d" % i] = [chg("760%d0" % i, "99223", "310.00", "12/05/2026", [pay("0.00", "12/01/2026", reasons=[("CO58", "310.00"), ("N620", "0")]), pay("-142.10", "12/20/2026", reasons=[("CO45", "167.90")])])]
rcZ, outZ, regZ, callsZ = run(workspace("first", {"20261126T1240Z": {"created": [rehab("vst760%d" % i, "pat970%d" % i, "11/2%d/2026" % i, ["99223"], "11/2%d/2026" % i) for i in range(3)]}}), today="2026-12-21")
check("11 a denial that the same payer paid afterwards is an earlier one (as before) - and it is no longer silent: the count line says how many of the paid visits were paid only after a denial, with the codes",
      lambda: rcZ == 0 and line(outZ, "REHAB AT 61:") == "REHAB AT 61: 3 visit(s) entered; 3 billed; 3 paid ($426.30, average $142.10 per initial visit - " + BASE + "); 0 denied; 0 billed and unanswered for over 30 days; 3 paid only after a denial (CO-58 x3)"
      and regZ["counts"]["at 61"]["paid_after_denial"] == 3 and "; 1 paid only after a denial (CO-16 x1)" in S61 and "paid only after a denial" not in S21, lambda: (outZ, S61))
HIST["7400"] = ConnectionError("gone"); NA2 = run(NA.get("_dir", ""), today="2026-12-21") if NA.get("_dir") else (None, [], None, [])
if isinstance(NA2[2], dict):      # ... and what the register carries of it comes back in shape only: here somebody has written into the three new fields
    for v_ in NA2[2]["visits"]: v_.update(paid_by=NAME_S, pending=NAME_S, dup=[NAME_S, "CO-18"])
    json.dump(NA2[2], open(os.path.join(NA["_dir"], "pos61_monitor.json"), "w"), indent=1)
NA3 = run(NA.get("_dir", ""), today="2026-12-22") if NA.get("_dir") else (None, [], None, []); TNA3 = json.dumps(NA3[2]) + " ".join(NA3[1])
check("11 a denied visit that cannot be read today keeps its line word for word from the register (the payment beside the denial too); what somebody wrote into the new fields is not carried on - a carrier code, a list of codes and a plain yes are all they hold",
      lambda: NA2[0] == NA3[0] == 0 and tops(NA2[1]) == tops(NA["_out"]) and row(NA2[2], "vst7400")["stale"] is True and row(NA3[2], "vst7400")["state"] == "denied" and "paid_by" not in row(NA3[2], "vst7400") and "pending" not in row(NA3[2], "vst7400")
      and row(NA3[2], "vst7400")["dup"] == ["?", "CO-18"] and not any(s in TNA3 for s in SECRETS) and shapes_ok(row(NA3[2], "vst7400")) is None and shapes_ok(dict(NB)) is None and set(k for k in NB if not k.startswith("_")) <= ROW_KEYS, lambda: (NA2[1], row(NA3[2], "vst7400")))
check("11 the header says the rule: per payer the newest answer leads, what makes an earlier denial, and the one exception", lambda: "PER PAYER THE NEWEST ANSWER LEADS" in HEAD and "B13" in HEAD and '"before"' in HEAD and '"dup"' in HEAD)

# ==== 12. nothing rides in through a field that is not what it says (11/25/2026: four ways a name or a number could have reached the register) =========
fill_history()
LOW_S = (LAST_S + " " + FIRST_S).lower(); HYPH_S = "03-04-" + "1941"; DIGITS_S = MEM_S[1:]      # the invented name in small letters, the invented birth date with hyphens, the digits of the invented plan number
MORE = SECRETS + (LAST_S.lower(), FIRST_S.lower(), HYPH_S, DIGITS_S)
for _v in ("7301", "7302", "7303", "7304"): HIST[_v] = [chg(_v + "0", "99233", "160.00", "11/28/2026", [pay("0.00", "12/09/2026", reasons=[("CO58", "160.00")])], ins="160.00")]
HIST["7305"] = [chg("73050", "99233", "160.00", "11/28/2026", [pay("0.00", "12/09/2026", carrier=LAST_S, reasons=[("CO58", "160.00")])], ins="160.00", carrier=MEM_S)]      # ONE word where a carrier code belongs, a plan number on the charge
W12 = workspace("ride", {"20261126T1240Z": {"created": [rehab("vst7301", "pat9401", "11/26/2026", ["99233"], "11/25/2026", sign=LOW_S + " " + HYPH_S),                      # words in small letters and a date where the import's sign belongs
                                                        dict(rehab("vst7302", "pat9402", "11/26/2026", ["99233"], "11/25/2026"), pid="%s member %s" % (LAST_S, MEM_S)),   # words and a plan number where the chart id belongs
                                                        dict(rehab("vst7303", "pat9403", "11/26/2026", ["99233"], "11/25/2026"), visit="see %s %s" % (LAST_S, MEM_S)),     # ... and where the visit id belongs
                                                        rehab("vst7305", "pat9405", "11/26/2026", ["99233"], "11/25/2026")]},
                         LAST_S + "_" + FIRST_S: {"created": [rehab("vst7304", "pat9404", "11/26/2026", ["99233"], "11/25/2026")]}},                                       # a register whose FILE NAME carries words, not a stamp
                extra={"feed_import_%s,%s.json" % (LAST_S, FIRST_S): "{ not a register"})                                                                                 # ... and one like it that cannot be read
rc12, out12, reg12, calls12 = run(W12); T12 = (open(os.path.join(W12, "pos61_monitor.json")).read() if os.path.exists(os.path.join(W12, "pos61_monitor.json")) else "") + "\n".join(l for l in out12 if not l.startswith("register: "))
check("12 words, a date or a plan number in a field of an import register, in its file name or in a carrier field of AdvancedMD's answer: none of it reaches the register or a printed line - not in small letters, not with hyphens, not as a run of digits",
      lambda: rc12 == 0 and len(T12) > 2000 and [s for s in MORE if s in T12] == [] and [x for x in (shapes_ok(v) for v in reg12["visits"]) if x] == [] and all(set(v) <= ROW_KEYS for v in reg12["visits"]), lambda: ([s for s in MORE if s in T12], [x for x in (shapes_ok(v) for v in (reg12 or {}).get("visits", [])) if x]))
check("12 the sign of a stay is one of the import's own two (or none): anything else in that field is left out, the visit is read all the same",
      lambda: "sign" not in row(reg12, "vst7301") and row(reg12, "vst7301")["state"] == "denied" and row(reg1, "vst7003")["sign"] == "facility number" and row(reg1, "vst7001")["sign"] == "new admission 1-2 days after an acute stay"
      and set(M.SIGNS) == {"facility number", "new admission 1-2 days after an acute stay"}, lambda: row(reg12, "vst7301"))
check("12 a chart id or a visit id is the import's own (pat123, vst123, or the bare number): digits out of other text are no id - the row is counted and named as 'could not be read', and never asked for",
      lambda: sorted(reads(calls12)) == ["7301", "7304", "7305"] and sorted((v.get("visit", ""), v.get("chart", ""), v["state"], v.get("unread")) for v in reg12["visits"] if v.get("unread")) == [("", "pat9403", "could not be read", "no visit id in the import register"), ("vst7302", "", "could not be read", "no chart id in the import register")]
      and [M.ident(x, "pat") for x in ("pat123", "123", 123, " pat9 ", "pat", "p123", "pat12 3", "pat123x", "vst123", None, True, "member " + MEM_S)] == ["123", "123", "123", "9", "", "", "", "", "", "", "", ""], lambda: ([c for c in calls12 if c[0] == "fetch_visit"], [v for v in reg12["visits"] if v.get("unread")]))
check("12 an import register is known by the stamp in its file name: one named otherwise is still read, but its name is not kept; one that cannot be read is counted, and named only when its name is a register's",
      lambda: row(reg12, "vst7304")["state"] == "denied" and "batch" not in row(reg12, "vst7304") and row(reg12, "vst7301")["batch"] == "20261126T1240Z" and reg12["unreadable_registers"] == ["a feed_import file with another kind of name"]
      and any(l.startswith("REHAB MONITOR: 1 import register(s) could not be read") and "a feed_import file with another kind of name" in l for l in out12) and reg1["unreadable_registers"] == ["feed_import_20261128T1240Z.json"]
      and [M.stamp_of(n) for n in ("feed_import_20261126T1240Z.json", "feed_import_20261125T0438ZR.json", "feed_import_1028.json", "feed_import_%s.json" % LAST_S, "feed_import_20261126T1240Z_decisions.json")] == ["20261126T1240Z", "20261125T0438ZR", "1028", "", ""], lambda: (row(reg12, "vst7304"), reg12["unreadable_registers"]))
check("12 a carrier code is at most eight letters and digits: a plan number or a long word in that field is left out (the denial is still seen, the line says 'carrier not named'); the practice's codes pass",
      lambda: row(reg12, "vst7305")["state"] == "denied" and "carrier" not in row(reg12, "vst7305") and "carrier not named" in line(out12, "TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7305")
      and [M.carrier_code(x) for x in ("FLO02", "MCAD", "UHCMA", "AAR01", "VACCN", "BCBS", MEM_S, LAST_S, MBI_S, "A", "FLO 02", "", None)] == ["FLO02", "MCAD", "UHCMA", "AAR01", "VACCN", "BCBS", "", "", "", "", "", "", ""], lambda: (row(reg12, "vst7305"), tops(out12)))

# ==== 13. a HOSPITAL visit that stands at 61 (verification of the pull request, 11/25/2026) ============================================================
# A follow-up of a NEW hospital stay can go in at HCA REHAB / 61 before that stay's initial visit reaches the feed - for everything in hand it is a visit of the
# rehab stay before it. When the initial visit comes the import says so on its row (pos_err 'PLACE OF SERVICE 61 on <day> belongs to this HOSPITAL stay ...') and
# names the days in the row's list hospital_at61. The monitor never read that: it counted the hospital visit in 'REHAB AT 61', put its payment or its denial into
# the numbers William asked for, and printed a denial of it - which is what a hospital visit billed at the rehab unit is likely to get - as 'PLACE OF SERVICE 61
# DENIED ... keep 61 or go back to 21 for this payer?'. The payer did not answer a rehab visit at 61, and the line did not say that the import had already named
# the visit as one to correct. Every chart, visit and date below is invented.
def late_initial(visit, chart, dos, days):
    """The row of a hospital stay's initial visit that reached the feed late: entered at the hospital / 21, with the import's words and its list of the days of that stay's visits that stand at 61."""
    return dict(acute(visit, chart, dos, ["99223"]), pos_err="PLACE OF SERVICE 61 on %s belongs to this HOSPITAL stay - it went in at HCA REHAB before the stay's initial visit (this one) reached the feed" % days[0], hospital_at61=list(days))
REG13A = {"created": [rehab("vst7401", "pat9401", "11/11/2026", ["99223"], "11/11/2026"), rehab("vst7402", "pat9401", "11/12/2026", ["99233"], "11/11/2026"),
                      rehab("vst7403", "pat9401", "11/16/2026", ["99233"], "11/11/2026"),      # the hospital follow-up that went in at 61, read as a visit of the rehab stay before it
                      rehab("vst7406", "pat9402", "11/16/2026", ["99233"], "11/12/2026"),      # another chart's rehab visit of that same day
                      rehab("vst7407", "pat9403", "11/20/2026", ["99233"], "11/18/2026"), rehab("vst7409", "pat9404", "11/21/2026", ["99233"], "11/19/2026")], "skipped": [], "failed": []}
REG13B = {"created": [late_initial("vst7404", "pat9401", "11/15/2026", ["11/16/2026"]), acute("vst7405", "pat9401", "11/17/2026", ["99233"]),
                      dict(acute("vst7408", "pat9403", "11/21/2026", ["99233"]), pos_err="PLACE OF SERVICE 61 on 11/20/2026, 21 here: the stay is MIXED", mixed_at61=["11/20/2026"]),      # a follow-up that went in at 21 behind a visit at 61: nothing says that the visit at 61 is a hospital visit
                      late_initial("vst7410", "pat9404", "11/20/2026", ["11/22/2026", "not a day", 7, None, "11/21/2026", NAME_S])], "skipped": [], "failed": []}      # a list with odd entries beside a good one, and a day no visit stands on
def fill13():
    HIST.clear(); HIST.update({
        "7401": [chg("74010", "99223", "310.00", "11/28/2026", [pay("-142.10", "12/10/2026", reasons=[CO45])])], "7402": [chg("74020", "99233", "160.00", "11/28/2026", [pay("-86.00", "12/10/2026", reasons=[("CO45", "74.00")])])],
        "7403": [chg("74030", "99233", "160.00", "11/28/2026", [pay("0.00", "12/09/2026", reasons=[("CO58", "160.00")])], ins="160.00")],      # the hospital visit billed at the rehab unit: denied for its place of service
        "7406": [chg("74060", "99233", "160.00", "11/28/2026", [pay("-88.00", "12/10/2026", reasons=[("CO45", "72.00")])])], "7407": [chg("74070", "99233", "160.00", "11/28/2026", [pay("-90.00", "12/10/2026", reasons=[("CO45", "70.00")])])],
        "7409": [chg("74090", "99233", "160.00", "11/28/2026", [pay("-84.00", "12/10/2026", reasons=[("CO45", "76.00")])])]})
fill13(); W13 = workspace("hosp61", {"20261117T1240Z": REG13A, "20261118T1240Z": REG13B}); rc13, out13, reg13, calls13 = run(W13)
H61 = "hospital at 61"; TOP13 = "TOP OF THE REPORT - HOSPITAL VISIT AT PLACE OF SERVICE 61 DENIED: vst7403 pat9401 service date 11/16/2026 99233 carrier FLO02 denied 12/09/2026 with CO-58, balance $160.00"
check("13 a hospital visit the import named as standing at 61 (hospital_at61 on the row of its stay's late initial visit) is NOT counted among the rehab visits at 61 - 'REHAB AT 61' counts the four rehab visits, all paid, none denied; "
      "another chart's rehab visit of the same day, and a visit at 61 that a row only calls mixed (mixed_at61), stay rehab visits",
      lambda: rc13 == 0 and line(out13, "REHAB AT 61:").startswith("REHAB AT 61: 4 visit(s) entered; 4 billed; 4 paid ($406.10, average $142.10 per initial visit - " + BASE + "); 0 denied;")
      and [row(reg13, v).get("group") for v in ("vst7401", "vst7402", "vst7403", "vst7406", "vst7407", "vst7409")] == ["61", "61", H61, "61", "61", H61] and reg13["counts"]["at 61"]["entered"] == 4 and reg13["counts"]["at 61"]["denied"] == 0,
      lambda: (rc13, out13, [row(reg13, v).get("group") for v in ("vst7401", "vst7402", "vst7403", "vst7406", "vst7407", "vst7409")]))
check("13 ... it is still read - one read of its own history, like every visit - and it has a line of its own that says what it is, that the import named it, and that William corrects the visit: both such visits by visit, chart, date of service and what the payer answered",
      lambda: {"7403", "7409"} <= set(reads(calls13)) and len(reads(calls13)) == 6 and line(out13, "REHAB MONITOR: 2 visit(s) at 61 belong to a HOSPITAL stay") != ""
      and all(w in line(out13, "REHAB MONITOR: 2 visit(s) at 61 belong to a HOSPITAL stay") for w in ("the import said so", "not counted above", "William corrects", "vst7403 pat9401 service date 11/16/2026 (denied)", "vst7409 pat9404 service date 11/21/2026 (paid)")),
      lambda: (reads(calls13), [l for l in out13 if l.startswith("REHAB MONITOR")]))
check("13 a DENIAL of such a visit goes to the top of the report as a visit to correct - with the payer's own codes and the balance - and NOT as the payer's answer to a rehab visit at 61: no 'PLACE OF SERVICE 61 DENIED' line for it, and nobody is asked 'keep 61 or go back to 21 for this payer?'",
      lambda: tops(out13) == [l for l in tops(out13) if l.startswith(TOP13)] and len(tops(out13)) == 1 and QUESTION not in tops(out13)[0] and "keep 61" not in tops(out13)[0].replace("'keep 61 or go back to 21'", "") and "belongs to a hospital stay" in tops(out13)[0]
      and "for William" in tops(out13)[0] and "correct the visit" in tops(out13)[0] and reg13["top"] == tops(out13), lambda: tops(out13))
check("13 its payment is not in the dollars per code either, and the register says for each such visit which batch's import register named it (a stamp, nothing else) and keeps the group's own numbers",
      lambda: "99233 $88.00 x3" in line(out13, "REHAB PAID PER CODE") and row(reg13, "vst7403").get("named") == "20261118T1240Z" and row(reg13, "vst7409").get("named") == "20261118T1240Z" and "named" not in row(reg13, "vst7401")
      and (reg13["counts"]["hospital visits at 61"]["entered"], reg13["counts"]["hospital visits at 61"]["paid"], reg13["counts"]["hospital visits at 61"]["denied"]) == (2, 1, 1) and row(reg13, "vst7403")["state"] == "denied" and row(reg13, "vst7409")["state"] == "paid",
      lambda: (line(out13, "REHAB PAID PER CODE"), row(reg13, "vst7403"), reg13["counts"].get("hospital visits at 61")))
check("13 only a real day of that chart is taken from the list: an odd entry, a day no visit of the chart stands on and a name carry nothing in - nothing of them is written or printed, and no visit of another chart is touched",
      lambda: row(reg13, "vst7406")["group"] == "61" and not any(NAME_S in l for l in out13) and NAME_S not in json.dumps(reg13) and "not a day" not in json.dumps(reg13) and len(reg13["visits"]) == 6, lambda: (row(reg13, "vst7406"), len(reg13["visits"])))
rc13b, out13b, reg13b, calls13b = run(W13, today="2027-01-25")
check("13 the line of that denied visit is said again in every later run for as long as the visit carries a balance - also five weeks on - like every denied visit; and without the import's word the same registers read as before (five visits at 61, one of them denied, William asked about the payer)",
      lambda: rc13b == 0 and len(tops(out13b)) == 1 and tops(out13b)[0].startswith(TOP13) and row(reg13b, "vst7403").get("since") == "12/20/2026"
      and (lambda r: r[0] == 0 and line(r[1], "REHAB AT 61:").startswith("REHAB AT 61: 6 visit(s) entered; 6 billed; 5 paid") and len(tops(r[1])) == 1 and tops(r[1])[0].startswith("TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: vst7403") and tops(r[1])[0].endswith(QUESTION))(
          run(workspace("hosp61_noword", {"20261117T1240Z": REG13A, "20261118T1240Z": {"created": [dict(r, hospital_at61=None) for r in REG13B["created"]], "skipped": [], "failed": []}}))),
      lambda: (tops(out13b), row(reg13b, "vst7403")))
check("13 the helper's header says it: what such a visit is, where the monitor reads it, and what it prints for it",
      lambda: all(w in SRC.split("\nimport ", 1)[0] for w in ("hospital_at61", "HOSPITAL VISIT AT PLACE OF SERVICE 61 DENIED", "belong to a HOSPITAL stay")), lambda: [w for w in ("hospital_at61", "HOSPITAL VISIT AT PLACE OF SERVICE 61 DENIED", "belong to a HOSPITAL stay") if w not in SRC.split("\nimport ", 1)[0]])

shutil.rmtree(TMP, ignore_errors=True)
print("\n%d check(s): %d ok, %d FAILED" % (OKS[0] + len(FAILS), OKS[0], len(FAILS)) + ("" if not FAILS else " - " + "; ".join(n[:60] for n in FAILS[:8]) + (" ..." if len(FAILS) > 8 else "")))
sys.exit(1 if FAILS else 0)
