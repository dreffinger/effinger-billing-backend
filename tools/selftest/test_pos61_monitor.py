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
#       still prints its lines and writes its register; a visit that is settled is not read again (--all reads every one);
#     - a line is said from the day the monitor first sees the visit denied or paid low - whatever date AdvancedMD gives the payment;
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
check("3 the run ends well although one visit could not be read and one import register is not readable", lambda: rc1 == 0 and not any(l.startswith("RAISED") for l in out1), lambda: (rc1, out1[-3:]))
check("3 ONE login, then ONE read of its own history for every rehab-stay visit that has a visit id - the 61 group and the comparison group, nothing else (no acute stay, no nursing visit, no skipped or failed row, no decisions file)",
      lambda: calls1[0] == ("login",) and [c[0] for c in calls1].count("login") == 1 and reads(calls1) == sorted(AT61 + AT21) and all(c[0] in ("login", "fetch_visit") for c in calls1), lambda: calls1)
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
      lambda: ST["7008"] == "could not be read" and row(reg1, "vst7008")["unread"] == "TimeoutError" and any(l.startswith("REHAB MONITOR") and "vst7008" in l and "pat9104" in l and "TimeoutError" in l for l in out1) and ST["7009"] == "paid", lambda: (row(reg1, "vst7008"), [l for l in out1 if "7008" in l]))
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
            "resent", "zero_codes", "balance", "ins_balance", "other", "closed", "low", "low_vs", "low_of", "before", "stale", "unread", "void", "answer", "asked", "since", "said"}
check("4 every row of the register holds only the fields the helper names - ids, dates, codes, states and dollars", lambda: all(set(v) <= ROW_KEYS for v in reg1["visits"]) and len(reg1["visits"]) == 24, lambda: sorted({k for v in reg1["visits"] for k in v} - ROW_KEYS))
def shapes_ok(v):
    """Every value of a row has the shape of what it is said to be: nothing free-text can ride in."""
    d = r"\d\d/\d\d/\d{4}"; code = r"(?:[A-Z]{2}-)?[A-Z]?\d{1,3}|(?:MA|M|N)\d{1,4}|\?"; proc = r"\d{4}[0-9A-Z]|[A-Z]\d{4}"
    tests = {"visit": r"(vst\d+)?", "chart": r"pat\d+", "dos": d, "initial": "(%s)?" % d, "read": d, "billed": "(%s)?" % d, "paid_on": d, "denied_on": d, "resent": d, "asked": d, "since": d, "said": r"denied|paid low", "carrier": r"[A-Za-z0-9]{0,12}", "code": proc,
             "group": r"61|21", "batch": r"[0-9A-Za-z_]+", "unread": r"[A-Za-z ]+", "state": r"[a-z$0 ]+", "answer": r"[a-z]+", "sign": r"[a-z0-9 \-]*", "low_of": r"[a-z0-9 /()'\-]+"}
    for k, rx in tests.items():
        if k in v and not re.fullmatch(rx, str(v[k])): return (k, v[k])
    for k in ("cpts", "denial", "remarks", "pay_codes", "zero_codes", "before"):
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

# ==== 6. the next runs: what is settled is not read again; time passes ==================================================================================
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
check("7 --max 5: five visits are read, the oldest dates of service first; the others are counted as not read yet and the line says that the next run goes on",
      lambda: rcA == 0 and len(reads(callsA)) == 5 and reads(callsA) == ["7005", "7006", "7011", "7012", "7013"] and regA["counts"]["at 61"]["unread"] + regA["counts"]["kept at 21"]["unread"] == 19
      and any(l.startswith("REHAB MONITOR") and "--max 5" in l and "the next run" in l for l in outA) and row(regA, "vst7001")["state"] == "not read yet", lambda: (reads(callsA), [l for l in outA if l.startswith("REHAB MONITOR")]))
rcB, outB, regB, callsB = run(W7, "--max", "5", today="2026-12-21")
check("7 ... the next run reads five that were never read - not the same five again (of those, the ones that are not settled wait their turn and keep what the last read showed)",
      lambda: rcB == 0 and len(reads(callsB)) == 5 and not (set(reads(callsB)) & set(reads(callsA))) and row(regB, "vst7005")["state"] == "unanswered" and row(regB, "vst7005")["stale"] is True and row(regB, "vst7005")["read"] == "12/20/2026", lambda: (reads(callsA), reads(callsB), row(regB, "vst7005")))
fill_history()
for _v in AT61 + AT21: HIST[_v] = ConnectionError("no answer for %s" % NAME_S)
W8 = workspace("down", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rcC, outC, regC, callsC = run(W8)
check("7 AdvancedMD does not answer: after three reads in a row without an answer the run stops asking, says so in one line, names what it could not read, writes its register and ends well",
      lambda: rcC == 0 and len(reads(callsC)) == 3 and any(l.startswith("REHAB MONITOR") and "three reads in a row" in l for l in outC) and regC["counts"]["at 61"]["unread"] == 18 and regC["counts"]["at 61"]["paid"] == 0
      and line(outC, "REHAB AT 61:").startswith("REHAB AT 61: 18 visit(s) entered; 0 billed; 0 paid") and "; 4 could not be read" in line(outC, "REHAB AT 61:") and "; 14 not read yet" in line(outC, "REHAB AT 61:")
      and regC["counts"]["kept at 21"]["unread"] == 6 and not tops(outC) and not any(NAME_S in l for l in outC), lambda: (rcC, len(reads(callsC)), outC))
fill_history()
for _v in ("7004", "7006"): HIST[_v] = ValueError("not an answer")
W9 = workspace("two", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rcD, outD, regD, callsD = run(W9)
check("7 two reads that fail with good reads between them stop nothing: every other visit is read", lambda: rcD == 0 and reads(callsD) == sorted(AT61 + AT21) and regD["counts"]["at 61"]["unread"] == 4 and row(regD, "vst7004")["unread"] == "ValueError"
      and row(regD, "vst7005")["state"] == "unanswered", lambda: (rcD, len(reads(callsD)), regD["counts"]["at 61"]))
fill_history()
for _v in ("7005", "7006", "7011"): HIST[_v] = ConnectionError("gone")      # the three visits with the oldest dates of service never answer
WR = workspace("turn", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rcR1, outR1, regR1, callsR1 = run(WR)
rcR2, outR2, regR2, callsR2 = run(WR, today="2026-12-21")
check("7 three visits that never answer hold up nobody for long: the first run stops at them, the next run starts with the visits it never asked for, reads them all and only then asks those three again",
      lambda: rcR1 == rcR2 == 0 and reads(callsR1) == ["7005", "7006", "7011"] and row(regR1, "vst7005")["asked"] == "12/20/2026" and len(reads(callsR2)) == 23 and [c[2] for c in callsR2 if c[0] == "fetch_visit"][-3:] == ["7005", "7006", "7011"]
      and row(regR2, "vst7001")["state"] == "paid" and row(regR2, "vst7005")["state"] == "could not be read" and row(regR2, "vst7005")["asked"] == "12/21/2026" and "asked" not in row(regR2, "vst7001"), lambda: (reads(callsR1), [c[2] for c in callsR2 if c[0] == "fetch_visit"]))
fill_history(); _ticks = [0]
def _clock(): _ticks[0] += 10; return _ticks[0]      # every look at the clock is ten seconds later
_real_clock = getattr(M, "CLOCK", None)
if M is not None: M.CLOCK = _clock
WT = workspace("time", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
rcT, outT, regT, callsT = run(WT, "--seconds", "25")
if M is not None: M.CLOCK = _real_clock
check("7 --seconds 25: the time of one run is looked at before each read - with ten seconds a read, two visits are read; the line says that the next run goes on, and the run ends well",
      lambda: rcT == 0 and reads(callsT) == ["7005", "7006"] and any(l.startswith("REHAB MONITOR") and "--seconds 25" in l and "the next run" in l for l in outT) and regT["ended"] == "time" and regT["limits"]["seconds"] == 25
      and row(regT, "vst7005")["state"] == "unanswered" and row(regT, "vst7011")["state"] == "not read yet", lambda: (rcT, reads(callsT), [l for l in outT if l.startswith("REHAB MONITOR")]))
check("7 ... without --seconds one run reads for 90 seconds at most (a call with the usual two-minute limit ends by itself) and for 400 visits at most", lambda: (M.SECONDS, M.MAX_READS, reg1["limits"]["seconds"], reg1["limits"]["max_reads"]) == (90, 400, 90, 400))
import signal as _signal
_CAUGHT = []
def _test_term(*_a): _CAUGHT.append("the signal reached this test's own handler: the helper had none of its own")
_old_term = _signal.signal(_signal.SIGTERM, _test_term)
fill_history()
def _cut_off():      # the third read is cut off by a time limit: the signal such a limit sends to the helper
    if os.name == "posix": os.kill(os.getpid(), _signal.SIGTERM); time.sleep(0.05)      # the real signal, to this very process (whoever holds the handler at that moment catches it - nobody is ended)
    elif callable(_signal.getsignal(_signal.SIGTERM)): _signal.getsignal(_signal.SIGTERM)(_signal.SIGTERM, None)      # where sending it would end the process: the handler in place is called as the signal would call it
    return history("7011", [chg("70110", "99223", "310.00", "11/22/2026", ins="310.00")])
HIST["7011"] = _cut_off
WK = workspace("term", {"20261126T1240Z": REG1, "20261127T1240ZR": REG2})
try: rcK, outK, regK, callsK = run(WK)
finally: _after_term = _signal.getsignal(_signal.SIGTERM); _signal.signal(_signal.SIGTERM, _old_term)
check("7 stopped from outside (a time limit) in the middle of a read: the reading ends there, the lines are still printed and the register is still written with what was read, and one line says so",
      lambda: rcK == 0 and _CAUGHT == [] and reads(callsK) == ["7005", "7006", "7011"] and row(regK, "vst7005")["state"] == "unanswered" and row(regK, "vst7006")["state"] == "paid" and row(regK, "vst7001")["state"] == "not read yet"
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
check("8 a low payment AdvancedMD dates four months back still has its line when the monitor sees it for the first time: the 14 days run from that day (ten days later the line is there, fifteen days later it is not) and the visit is not read again for it",
      lambda: P["low"] is True and len(tops(P["_out"])) == 1 and (P["said"], P["since"]) == ("paid low", "12/20/2026") and len(tops(P10[1])) == 1 and row(P10[2], "vst7400")["since"] == "12/20/2026" and tops(P15[1]) == []
      and "; 1 paid low" in line(P15[1], "REHAB AT 61:") and P10[3] == [] and P15[3] == [], lambda: (P, P10[1], P15[1]))
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
WD = workspace("twice", {"20261126T1240Z": {"created": [rehab("vst7001", "pat9101", "11/26/2026", ["99223"], "11/26/2026")]}, "20261126T1240ZR": {"created": [dict(rehab("vst7001", "pat9101", "11/26/2026", ["99223"], "11/26/2026"), fac="fac29", pos="21", pos_lines=["21"], pos_kind=["rehab-stay-kept-21"])]}})
rcW, outW, regW, callsW = run(WD)
check("8 a visit named in two import registers is ONE visit, read once, and the later register says where it stands", lambda: rcW == 0 and reads(callsW) == ["7001"] and len(regW["visits"]) == 1 and regW["visits"][0]["group"] == "21" and regW["visits"][0]["batch"] == "20261126T1240ZR"
      and outW[0].startswith("REHAB AT 61: no ") and line(outW, "REHAB STAYS KEPT AT 21").startswith("REHAB STAYS KEPT AT 21 (the comparison group): 1 visit(s) entered; 1 billed; 1 paid ($142.10)"), lambda: (rcW, outW))
fill_history()
_no_stay = {k: v for k, v in rehab("vst7002", "pat9101", "11/27/2026", ["99233"], "11/26/2026").items() if k != "stay"}
WS_ = workspace("nostay", {"20261126T1240Z": {"created": ["not a row", 7, None, {"visit": "vst7999"}, {"pid": "pat1", "stay": "rehab", "pos": "61x", "cpts": 5}, dict(rehab("vst7003", "pat9102", "11/26/2026", ["99223"], "11/26/2026"), pos="31", pos_lines=["31"]),
                                                              _no_stay, rehab("vst7001", "pat9101", "11/26/2026", ["99223"], "11/26/2026")], "skipped": "x", "failed": None}, "20261127T1240Z": ["a list, not a register"], "20261129T1240Z": {"created": "none"}})
rcS, outS, regS, callsS = run(WS_)
check("8 a row with a charge line at 61 is the new group also when the import wrote no stay beside it (61 is only ever written for a rehab stay); rows that are not rows, and registers that are not registers, stop nothing",
      lambda: rcS == 0 and reads(callsS) == ["7001", "7002"] and [v["group"] for v in regS["visits"]] == ["61", "61"] and line(outS, "REHAB AT 61:").startswith("REHAB AT 61: 2 visit(s) entered; 2 billed; 2 paid ($228.10")
      and regS["unreadable_registers"] == ["feed_import_20261127T1240Z.json"], lambda: (rcS, outS))
check("8 ... and a rehab-stay row that stands at neither 61 nor 21 is named, never read and never counted", lambda: any(l.startswith("REHAB MONITOR") and "neither 61 nor 21" in l and "vst7003" in l for l in outS) and "7003" not in reads(callsS), lambda: outS)
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

shutil.rmtree(TMP, ignore_errors=True)
print("\n%d check(s): %d ok, %d FAILED" % (OKS[0] + len(FAILS), OKS[0], len(FAILS)) + ("" if not FAILS else " - " + "; ".join(n[:60] for n in FAILS[:8]) + (" ..." if len(FAILS) > 8 else "")))
sys.exit(1 if FAILS else 0)
