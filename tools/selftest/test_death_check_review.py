#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the date-of-death check of the Charge Review step - William, 11/25/2026)
# Decides: nothing. Runs scripts/helpers/death_check_review.py INSIDE this process, as the program a run starts, with stand-in amd / resave /
#   stedi / elig_amd modules and a throwaway folder (no AdvancedMD, no vendor, no network, no patient data - every name, date, number and id
#   below is invented and put together at run time; the last checks prove the privacy gate leaves this file and the helper alone). The
#   guard it runs with is either a scripted stand-in (to pin every word and number) or the REAL scripts/helpers/deceased_guard.py, loaded
#   from its file with the stand-ins in place (to prove the two work together - with a guard that counts its free and bought answers in
#   COUNTS and with one that does not). It proves what William asked for on 11/25/2026 ("... verify date of death first so as not to bill
#   any after the date of death to straight medicare ... and check before submitting"):
#     - the helper lists Charge Review with the ONE proven list call (getreviewcharges class=chargeentry, as columns_scan.py sends it) after
#       ONE login, and puts EVERY charge of the listing through deceased_guard.check_charge(<charge id>, 1) - once each, whatever form the
#       ids take; it sends NOTHING else to AdvancedMD (no approval, no save, no void, no rebill) and reads each charge ONCE, for the
#       words and to see that there was something to check - nothing but the ids is taken from the listing;
#     - ONE read of each charge: the guard, which reads the charge it checks itself, is handed the very answer the helper looked at - so
#       it never decides on a second read that failed in between (the real guard passes an answer with no chart in it; with two reads a
#       charge of a patient who has passed away came out 'clear' - check 10n); a read of another charge is not touched, an answer with
#       nothing to check in it is not handed over (the guard then reads for itself and may still block), and the stand-in's own
#       resave.detail is back in its place afterwards;
#     - one line per BLOCKED charge with the chart id, visit id, charge id, date of service, code and the fixed words - and NEVER the day
#       the patient passed away, the guard's own reason, a name, a birth date or a number, although the stand-in's answers and the guard's
#       reason carry all of them;
#     - THE SECOND QUESTION (deceased_guard.check - the call the runs' own code made until now): every charge is asked about at sequence 1,
#       and a charge whose visit's own insurance order (the list AdvancedMD built, or the insorder attribute) starts with another plan, or
#       whose care-management code stands under a procedure id the guard's list does not hold, is asked about once more - with the chart,
#       the date of service, the carrier of that first plan and the code itself. The carrier of the first plan is read where the
#       registry shows it - on the insurance-order list's own first row (the row with ordinal 0, wherever it stands) - and on the plan
#       element at that sequence, and bare digits are written the way the guard's list holds them (car<digits>): a detail that shows no
#       plan element at all still gets its straight-Medicare claim asked about. With the REAL guard a straight-Medicare claim whose
#       Medicare plan stands at sequence 2, a care-management charge entered under an unknown procedure id and a straight-Medicare claim
#       whose detail names the carrier on the list's row only are blocked - the question about sequence 1 alone lets all three through;
#     - one line per charge that could not be checked (the guard raised; a visit without a charge; a charge without an id) with the fixed
#       words and the error by its kind only - and the other charges are still checked; 'not blocked' counts as checked only when there
#       was something to check: a charge whose own detail carries no chart, no date of service or no row of that charge (a Fault - the
#       guard does not raise on it, it passes it), or that cannot be read at all, is NOT CHECKED - never 'clear';
#     - one line per charge whose look-up failed ('date of death unverified' - not a block), and LAST the summary line with every count:
#       charges and visits listed, checked, needed a Medicare answer (care management or straight Medicare, by the guard's own lists),
#       answered free / bought when the guard counts them (COUNTS) and "not counted" when it does not, BLOCKED, not checked, unverified -
#       with the REAL guard the free / bought part is exactly what that guard counted during the start, whichever guard it is;
#     - exit 0 = everything checked and nothing blocked; 3 = a charge blocked or not checked; 2 = Charge Review could not be listed (the
#       call failed, the answer is no list - not XML, or well-formed but not AdvancedMD's - a Fault, a login that failed), an option it
#       does not know, a helper it cannot load, an error of its own - each with ONE plain line, never a traceback, and no guard call made;
#     - --dry = the guard's cache only (allow_lookup=False for every charge), said in the summary line, in a register of its own name;
#     - the register registers/death_check_review_<UTC stamp>.json under the folder the helper is started in: chart ids, visit ids, charge
#       ids, dates of service, codes, the counts and the fixed words - nothing else; the privacy gate leaves it and the printed lines alone;
#     - with the REAL guard: a day on Medicare's record before the date of service blocks a straight-Medicare charge and a care-management
#       charge on another plan; a look-up that fails blocks nothing and is said; a day already in the guard's cache blocks with no call at
#       all; a charge that is neither care management nor straight Medicare at sequence 1 is asked about nothing; --dry asks nothing;
#     - (review fix of 11/25/2026, checks 10x1 to 10x5 and 11a2) the number a run compares with its own listing of Charge Review is the
#       number of charges LISTED, the summary line's first number: in every start made here it is what the listing holds, the charges
#       checked and the NOT CHECKED lines about a charge add up to it, and both live prompts name it (they first named the number checked,
#       so every answer with a NOT CHECKED charge sent the run to guard calls of its own). A NOT CHECKED charge stays unapproved whatever
#       such a call answers: with the REAL guard, check_charge passes the very charge the helper could not check where check blocks it;
#     - (the same fix) the helper lists only what is still waiting in Charge Review, so a run starts it before ANY save of the step: a
#       visit that a gate's save (a full-visit save that carries approval 1) took out of Charge Review first is never put through the
#       guard - only the number listed, smaller than the run's own listing from before the save, shows it - and the header says so.
# Run: python3 tools/selftest/test_death_check_review.py   (exit 1 on any failure; the last line says how many checks ran and how many failed)
import os, sys, io, re, json, glob, time, types, shutil, atexit, tempfile, datetime, contextlib
import importlib.abc, importlib.machinery
# THIS SELF-TEST NEVER REACHES ADVANCEDMD, THE VENDOR OR ANY OTHER HOST. Every network route is closed here, before anything else is loaded:
# scripts/helpers and core hold the REAL amd / resave / stedi / elig_amd modules, and importing them would talk to the practice's billing
# system and the paid vendor. So: (1) the helper and the guard are read from their files and run here with stand-in modules in sys.modules;
# (2) any import that would come from the checkout, or of a live module that has no stand-in, is refused; (3) the network is shut either
# way. No program is started.
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPER = "scripts/helpers/death_check_review.py"; GUARD = "scripts/helpers/deceased_guard.py"
LIVE = {"amd", "resave", "txh", "void_tx", "era_post", "deceased_guard", "stedi", "requests", "medicare_store", "stedi_prices", "stedi_usage",
        "precheck", "elig_amd", "add_ins", "ins_update", "freq1_visit", "move_to_ins"}
class _Refuse(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in LIVE: raise ImportError("refused: %s is a live-system module - only stand-ins are used here" % name)
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is not None and spec.origin and os.path.abspath(spec.origin).startswith(ROOT + os.sep):
            raise ImportError("refused: %s would be loaded from the checkout (%s)" % (name, spec.origin))
        return None
sys.meta_path.insert(0, _Refuse())
FAILS = []; COUNT = [0]
def check(name, cond, extra=""):
    """One check. cond and extra may be functions: a check that cannot even be worked out (the helper is not there yet) FAILS - it never
    ends the self-test early."""
    COUNT[0] += 1
    try: ok = bool(cond() if callable(cond) else cond)
    except Exception as e: ok = False; extra = "could not be worked out - %s: %s" % (type(e).__name__, str(e)[:200])
    try: shown = extra() if callable(extra) else extra
    except Exception as e: shown = "(%s)" % type(e).__name__
    print(("ok   " if ok else "FAIL ") + name + (("  -> " + str(shown)[:700]) if shown != "" and not ok else ""))
    if not ok: FAILS.append(name)
def _raises(f, exc=Exception):
    try: f()
    except exc: return True
    except Exception: return False
    return False
def _read(rel):
    with open(os.path.join(ROOT, rel)) as fh: return fh.read()

# ---- the throwaway folder; the guard's cache path is set BEFORE the real guard is loaded (it takes the path when it is loaded) --------------
TMP = tempfile.mkdtemp(prefix="dcr_selftest_"); atexit.register(shutil.rmtree, TMP, True)
DCACHE = os.path.join(TMP, "guard", "deceased_cache.json"); os.environ["DECEASED_CACHE"] = DCACHE
def _snapshot():
    out = {}
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x != ".git"]
        for f in files:
            p = os.path.join(d, f)
            try: st = os.stat(p); out[p] = (st.st_size, st.st_mtime_ns)
            except OSError: pass
    return out
BEFORE = _snapshot()
_PATH = list(sys.path)

# ---- invented values: every name, day and number is put together here, at run time ---------------------------------------------------------
TODAY = datetime.date.today()
def ago(n): return TODAY - datetime.timedelta(days=n)
def mdy(d): return d.strftime("%m/%d/%Y")
def iso(d): return d.isoformat()
def ymd(d): return d.strftime("%Y%m%d")
def faces(d): return [iso(d), mdy(d), ymd(d), "%d/%d/%d" % (d.month, d.day, d.year)]
LAST_S = "QVORK" + "LEBANT"; FIRST_S = "ZELM" + "AVRO"; NAME_S = LAST_S + "," + FIRST_S      # AdvancedMD's LAST,FIRST form (the pieces are no words and nobody's name)
BORN_S = datetime.date(1941, 3, 4)                                                           # the invented patient's first day
GONE = datetime.date(TODAY.year - 1, 3, 9); GONE2 = datetime.date(TODAY.year - 1, 4, 17)    # the invented days a patient passed away: last year, so no date of service, no stamp and no fixed word below can look like one
MBI_S = "2FH5" + "UF6NK84"; MEM_S = "H7741" + "90263"                                        # a Medicare number and a plan's own number
SECRETS = [LAST_S, FIRST_S, MBI_S, MEM_S] + faces(BORN_S) + faces(GONE) + faces(GONE2)
DOS_A, DOS_B, DOS_C = ago(5), ago(3), ago(2)                                                # dates of service: a few days ago
BLOCK = "date of death before the date of service - do NOT approve; void (William 10/4 and 11/25/2026)"      # the fixed words of the specification, word for word
UNCHECKED = "could not be checked - do not approve this charge on this run"
UNVERIFIED = "date of death unverified (the look-up failed) - not a block; say it in the report"
NOTHING = "approve NOTHING on this helper's word"
def leaks(text): return [s for s in SECRETS if s in str(text)]

# ---- the stand-in AdvancedMD and vendor (nothing here can reach either) ------------------------------------------------------------------------
CALLS = []                     # every call into the stand-ins, in order: ("login",) ("post", action, class, body, timeout) ("detail", charge) ("elig", plan) ("FORBIDDEN", what)
VENDOR = []                    # every paid Medicare ask the guard made of the stand-in vendor (the chart it was about)
STATE = {"listing": "", "login": None, "details": {}, "charts": {}, "medicare": {}, "free": {}}
def listing_xml(visits, bare=False, tail=""):
    """The answer of the list call: visits with their charges (the element and attribute names columns_scan.py reads). Every row carries what a
    real answer would carry too - the patient's name, a day, plan numbers - and a code and a date that are NOT the charge's own, so the checks
    can prove that nothing but the ids is taken from the listing and that none of the rest is ever printed or written."""
    v_, p_, c_ = ("", "", "") if bare else ("vst", "pat", "charge"); rows = ""
    for vid, pid, cids in visits:
        chg = "".join('<charge %sproccode="pcode1" begindate="%s" patientname="%s" subscribernum="%s"/>' % (('id="%s%s" ' % (c_, c)) if c else "", mdy(BORN_S), NAME_S, MEM_S) for c in cids)
        rows += '<visit id="%s%s" patientid="%s%s" patientname="%s" dob="%s" subscribernum="%s"><chargelist>%s</chargelist></visit>' % (v_, vid, p_, pid, NAME_S, mdy(BORN_S), MBI_S, chg)
    return "<PPMDResults><Results><visitlist>%s</visitlist>%s</Results><Error/></PPMDResults>" % (rows, tail)
def detail_xml(cid, pid, vid, dos, proc, code, plans, order="1,2", order_list=None):
    """The charge's own detail (getchargedetaildataicd10 by charge id) as deceased_guard.check_charge and resave.py read it: the patient, the
    visit with its date and its insurance order (the insorder attribute; order_list = the rows of the insurance-order LIST AdvancedMD
    built, in claim order - each a plan sequence, or (sequence, carrier) for a row that names its carrier as the registry says the rows
    do), the charge with its procedure id, the procedure list (id -> code) and the chart's plans with their sequence (plans [] = a detail
    that shows no plan element at all). The list's rows are written the way the registry describes them (docs/captured_calls.md, 'The
    list, not the attribute'): the ordinal starts at 0 and the rows come OUT of claim order - here the last one first."""
    plan = "".join('<insplan id="ins%s%d" sequence="%s" carrier="%s" subscribernum="%s"/>' % (pid, i, s, car, MBI_S if car == "car6085" else MEM_S) for i, (s, car) in enumerate(plans))
    rows_ = [(i, r if isinstance(r, tuple) else (r, None)) for i, r in enumerate(order_list or [])]
    olist = "" if order_list is None else "<insuranceorderlist>%s</insuranceorderlist>" % "".join(
        '<insuranceorder %sordinal="%d" sequence="%s"/>' % (('carrier="%s" ' % c) if c is not None else "", i, q) for i, (q, c) in reversed(rows_))
    return ('<PPMDResults><Results><patient id="pat%s" name="%s" dob="%s"/><visit id="vst%s" date="%s" insorder="%s">%s<chargelist><charge id="charge%s" proccode="%s" fee="100.00" '
            'begindate="%s"/></chargelist></visit><proccodelist><proccode id="%s" code="%s"/></proccodelist><insplanlist>%s</insplanlist></Results><Error/></PPMDResults>'
            % (pid, NAME_S, mdy(BORN_S), vid, mdy(dos), order, olist, cid, proc, mdy(dos), proc, code, plan))
def chart_xml(pid):
    """The chart record the REAL guard reads (getdemographic): the patient's name and first day, and the plans with their numbers."""
    plan = "".join('<insplan id="ins%s%d" carrier="%s" begindate="%s" enddate="" subscribernum="%s" sequence="%d"/>' % (pid, i, car, mdy(datetime.date(2015, 1, 1)), n_, i + 1)
                   for i, (car, n_) in enumerate(STATE["charts"][pid]))
    return '<PPMDResults><Results><patient id="pat%s" name="%s" dob="%s" deceased="" state="FL"/>%s</Results><Error/></PPMDResults>' % (pid, NAME_S, mdy(BORN_S), plan)
amd = types.ModuleType("amd"); amd.STAND_IN = True
def _login():
    CALLS.append(("login",))
    if STATE["login"] is not None: raise STATE["login"]
    return ("web", "token")
def _msg(action, cls, attrs=None, children=""):
    return '<ppmdmsg action="%s" class="%s" %s>%s</ppmdmsg>' % (action, cls, " ".join('%s="%s"' % kv for kv in (attrs or {}).items()), children)
def _post(body, timeout=None, **more):
    m = re.search(r'action="(\w+)" class="(\w+)"', body); action, cls = (m.group(1), m.group(2)) if m else ("?", "?")
    if action == "getreviewcharges":
        CALLS.append(("post", action, cls, body, timeout))
        if isinstance(STATE["listing"], BaseException): raise STATE["listing"]
        return STATE["listing"]
    if action == "getdemographic":
        CALLS.append(("post", action, cls, body, timeout)); return chart_xml(re.search(r'patientid="(?:pat)?(\d+)"', body).group(1))
    CALLS.append(("FORBIDDEN", "amd.post " + action)); raise AssertionError("nothing else may be sent to AdvancedMD: " + action)
def _elig(insplan_id, stc="30", timeout=120):
    """AdvancedMD's own free check, for a guard that asks it: down (HTTP 503) unless STATE["free"] holds a day for that plan - then the answer
    carries that day (the stand-in summarize below reads it back)."""
    k = re.sub(r"\D", "", str(insplan_id)); CALLS.append(("elig", k))
    if k in STATE["free"]: return 200, json.dumps({"free answer for plan": k, "day": ymd(STATE["free"][k])})
    return 503, "the stand-in's free check is down"      # a guard that asks AdvancedMD's free check first gets no answer here and goes on as before
STRICT = [True]                # False while the REAL guard runs: what a guard looks up in the stand-ins is the guard's own business, not the helper's
def _amd_other(name):
    if not name.startswith("__") and STRICT[0]: CALLS.append(("FORBIDDEN", "amd." + name))
    raise AttributeError(name)
amd.login_cached = _login; amd.msg = _msg; amd.post = _post; amd.check_eligibility = _elig; amd.__getattr__ = _amd_other
resave = types.ModuleType("resave"); resave.STAND_IN = True
def _detail(cid):
    k = re.sub(r"\D", "", str(cid)); CALLS.append(("detail", k)); d = STATE["details"][k]
    if isinstance(d, list): d = d.pop(0) if len(d) > 1 else d[0]      # a list = the answers of the reads in order (the last one stays): AdvancedMD answering differently the second time
    if isinstance(d, BaseException): raise d
    return d
def _resave_other(name):
    if not name.startswith("__") and STRICT[0]: CALLS.append(("FORBIDDEN", "resave." + name))
    raise AttributeError(name)
resave.detail = _detail; resave.__getattr__ = _resave_other
stedi = types.ModuleType("stedi"); stedi.STAND_IN = True
def _medicare(first, last, dob8, member_id=None, dos=None, state=None, pid=None, who=None, max_age_days=None, **more):
    """The vendor client's ONE Medicare answer, scripted per chart: "alive", "failed", or the day Medicare's record shows."""
    VENDOR.append(str(pid)); r = STATE["medicare"].get(str(pid), "alive")
    if r == "failed": return {}, "failed"
    j = {"benefitsInformation": [{"code": "1", "insuranceTypeCode": "MA"}, {"code": "1", "insuranceTypeCode": "MB"}], "errors": [], "planDateInformation": {}}
    if r != "alive": j["planDateInformation"]["dateOfDeath"] = ymd(r)
    return j, "plain"
stedi.medicare = _medicare; stedi.med_summ = lambda j: {"errors": [e.get("code") for e in (j or {}).get("errors") or []]}
elig_amd = types.ModuleType("elig_amd"); elig_amd.STAND_IN = True
def _run_plan(pid, insid, force=False): CALLS.append(("elig", str(insid))); raise RuntimeError("the stand-in's free check is down")
def _summarize(text):
    """what elig_amd.summarize makes of the free answer: status, rejections, Part A / Part B lines and the day on Medicare's record (8 digits)"""
    try: day8 = json.loads(text).get("day")
    except (ValueError, AttributeError, TypeError): day8 = None
    return {"status": "INACTIVE" if day8 else "UNKNOWN", "aaa": [], "partA": [], "partB": [], "date_of_death": day8}
elig_amd.run_plan = _run_plan; elig_amd.summarize = _summarize
STANDINS = {"amd": amd, "resave": resave, "stedi": stedi, "elig_amd": elig_amd}

GUARDS = []                    # every scripted guard made below (a last check: the helper used nothing of them but check_charge, check and the lists)
def scripted(results=None, counts=None, start=None, log=None, bad_counts=None, second=None, peek=None):
    """A scripted guard. results: charge -> True (blocked) / "unverified" / an exception to raise / nothing (clear) - what check_charge says.
    second: chart -> the same, for what check() says (the second question). counts: charge -> what the guard's COUNTS grow by when that
    charge is checked (None = a guard that has no COUNTS). start: where its COUNTS stand before. peek: charge -> the charges this guard
    reads through resave.detail while it checks that one, as the real guard reads the charge it checks (g.seen keeps what it was handed)."""
    g = types.ModuleType("deceased_guard"); g.STAND_IN = True; g.UNDER_TEST = False; g.calls = []; g.checks = []; g.other = []; g.seen = []; g.LOG = [] if log is None else log
    g.MEDICARE = {"FLO02", "car6085"}; g.CCM = {"99487", "99489", "pcode492676", "pcode492677"}; results = results or {}; second = second or {}
    if counts is not None: g.COUNTS = dict(start or {"free asked": 0, "free answered": 0, "paid asked": 0})
    if bad_counts is not None: g.COUNTS = bad_counts
    def say(r):
        if isinstance(r, BaseException): raise r
        if r == "unverified": g.LOG.append("pat7002 DOS %s: date of death UNVERIFIED (lookup failed)" % iso(DOS_B)); return False, ""
        if r is True: return True, "pat7002 DOS %s is after date of death %s (stedi-medicare-271) - claim must not be submitted; void the charge" % (iso(DOS_B), iso(GONE))
        return False, ""
    def check_charge(chargeid, sequencenumber=None, allow_lookup=True):
        g.calls.append((chargeid, sequencenumber, allow_lookup)); r = results.get(str(chargeid))
        for x in (peek or {}).get(str(chargeid)) or []: g.seen.append((x, sys.modules["resave"].detail(x)))
        if not isinstance(r, BaseException):
            for k, n in ((counts or {}).get(str(chargeid)) or {}).items(): g.COUNTS[k] += n
        return say(r)
    def check(pid, dos, carrier=None, proc=None, allow_lookup=True):
        g.checks.append((pid, dos, carrier, proc, allow_lookup)); return say(second.get(str(pid)))
    def _other(name):
        if not name.startswith("__") and name not in ("COUNTS", "LOG", "MEDICARE", "CCM"): g.other.append(name)
        raise AttributeError(name)
    g.check_charge = check_charge; g.check = check; g.__getattr__ = _other; GUARDS.append(g); return g

# ---- the helper, as the program a run starts - inside this process ---------------------------------------------------------------------------
WS_N = [0]; SEEN = []            # SEEN: everything the helper printed and every register it wrote, for the privacy checks at the end
STARTS = []                      # every start of the helper made below, in order (checks 10x1 and 10x2 look at all of them)
def new_ws():
    WS_N[0] += 1; w = os.path.join(TMP, "ws%d" % WS_N[0]); os.makedirs(w); return w
def own_count():
    """What a run's OWN listing of Charge Review counts at this moment, worked out here from the stand-in's answer and never with the helper's
    code: the charge rows, one for each charge id, and every row without an id. None when the answer is no text at all (the call fails)."""
    x = STATE["listing"]
    if not isinstance(x, str): return None
    ids = [re.search(r'\bid="(?:charge)?(\d+)"', a) for a in re.findall(r"<charge\b([^>]*)>", x)]
    return len({m.group(1) for m in ids if m}) + sum(1 for m in ids if not m)
def run(argv=(), guard=None, ws=None, drop=()):
    """One start of the helper -> its exit code, its lines, its register(s) and the calls it made; .own = what the run's own listing of Charge
    Review counts at that moment (own_count). Never raises: with no helper file every value is empty and the checks FAIL on it."""
    w = ws or new_ws(); path = os.path.join(ROOT, HELPER); n0 = len(CALLS); v0 = len(VENDOR); out = io.StringIO(); code = "no exit"; err = ""; own = own_count()
    try: src = _read(HELPER)
    except OSError: src = None; err = "the helper is not there (%s)" % HELPER
    if src is not None:
        mods = dict(STANDINS); mods["deceased_guard"] = guard
        for n in drop: mods.pop(n, None)
        keep = {n: sys.modules.get(n) for n in list(STANDINS) + ["deceased_guard"]}
        for n in keep: sys.modules.pop(n, None)
        sys.modules.update({n: m for n, m in mods.items() if m is not None})
        old = (os.getcwd(), list(sys.argv), time.sleep)
        try:
            os.chdir(w); sys.argv = [path] + list(argv); time.sleep = lambda *_a: None; STRICT[0] = not getattr(guard, "UNDER_TEST", False)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                try: exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path})
                except SystemExit as e: code = e.code
                except BaseException as e: err = "ended with %s - a run would see a traceback" % type(e).__name__
        finally:
            os.chdir(old[0]); sys.argv = old[1]; time.sleep = old[2]; sys.path[:] = _PATH; STRICT[0] = True
            for n, m in keep.items():
                sys.modules.pop(n, None)
                if m is not None: sys.modules[n] = m
    text = out.getvalue(); regs = sorted(glob.glob(os.path.join(w, "registers", "*")))
    reg = None; raw = ""
    if regs:
        try:
            with open(regs[-1]) as fh: raw = fh.read()
            reg = json.loads(raw)
        except (OSError, ValueError): reg = None
    SEEN.append(text); SEEN.append(raw)
    r = types.SimpleNamespace(code=code, out=text, lines=[l for l in text.splitlines() if l.strip()], reg=reg, raw=raw, regs=[os.path.basename(p) for p in regs], ws=w,
                              calls=CALLS[n0:], vendor=VENDOR[v0:], err=err, own=own)
    STARTS.append(r); return r
def posts(r, action=None): return [c for c in r.calls if c[0] == "post" and (action is None or c[1] == action)]
def details(r): return [c[1] for c in r.calls if c[0] == "detail"]
def kind(r, word): return [l for l in r.lines if l.startswith(word)]
def rows(r): return (r.reg or {}).get("rows") or []
def row(r, charge): return next((x for x in rows(r) if x.get("charge") == charge), {})
def scene(visits, bare=False, tail=""):
    """visits: [(visit, chart, [(charge, procedure id, code, carrier at sequence 1, carrier at sequence 2, date of service)])] - sets the stand-in up"""
    STATE.update(listing=listing_xml([(v, p, [c[0] for c in cs]) for v, p, cs in visits], bare=bare, tail=tail), login=None,
                 details={c[0]: detail_xml(c[0], p, v, c[5], c[1], c[2], [(1, c[3]), (2, c[4])]) for v, p, cs in visits for c in cs})
SUMMARY = r"^DEATH CHECK - Charge Review: %d charge\(s\) on %d visit\(s\) listed, %d checked; %d needed a Medicare answer \(CCM or straight Medicare\)%s; %d BLOCKED; %d could not be checked; %d unverified - register registers/death_check_review_\d{4}-\d{2}-\d{2}T\d{6}Z%s\.json$"
NOT_COUNTED = " - free / bought not counted by this guard"
def summary(r, charges, visits, checked, needed, how, blocked, unchecked, unverified, dry=""):
    return bool(r.lines) and re.match(SUMMARY % (charges, visits, checked, needed, re.escape(how), blocked, unchecked, unverified, dry), r.lines[-1]) is not None

# ---- 0. the safety block holds -------------------------------------------------------------------------------------------------------------------
check("0a safety: the real `requests`, a live helper and any module of the checkout are refused by the import blocker",
      lambda: _raises(lambda: _Refuse().find_spec("requests"), ImportError) and _raises(lambda: _Refuse().find_spec("amd"), ImportError)
      and _raises(lambda: _Refuse().find_spec("test_board_ops", [os.path.join(ROOT, "tools", "selftest")]), ImportError))
check("0b safety: the network is shut in this process", lambda: _raises(lambda: _socket.create_connection(("127.0.0.1", 9)), RuntimeError))
check("0c the helper is in the repository, where the workspace builders copy helpers from (scripts/helpers)", lambda: os.path.isfile(os.path.join(ROOT, HELPER)), HELPER)

# ---- 1. every charge of Charge Review goes through the guard --------------------------------------------------------------------------------
FOUR = [("9001", "7001", [("5001", "pcode492676", "99487", "car6404", "car6113", DOS_A), ("5002", "pcode65142", "99349", "car6404", "car6113", DOS_A)]),
        ("9002", "7002", [("5003", "pcode65089", "99232", "car6085", "car6404", DOS_B)]),
        ("9003", "7003", [("5004", "pcode65142", "99349", "car6404", "car6085", DOS_C)])]      # 5004: straight Medicare only at sequence 2
scene(FOUR); G1 = scripted(); R1 = run(guard=G1)
check("1a ONE login (login_cached) and ONE list call - getreviewcharges class=chargeentry with nocookie=1 and a 120-second limit, as columns_scan.py sends it",
      lambda: R1.calls[:2] == [("login",), R1.calls[1]] and len([c for c in R1.calls if c[0] == "login"]) == 1 and len(posts(R1)) == 1
      and posts(R1)[0][1:3] == ("getreviewcharges", "chargeentry") and 'nocookie="1"' in posts(R1)[0][3] and "batchid" not in posts(R1)[0][3] and posts(R1)[0][4] == 120, lambda: (R1.err, R1.calls[:3]))
check("1b EVERY charge of the listing goes through deceased_guard.check_charge(<charge id>, 1) - once each, in the listing's order, look-ups allowed",
      lambda: G1.calls == [("5001", 1, True), ("5002", 1, True), ("5003", 1, True), ("5004", 1, True)], lambda: G1.calls)
check("1c exit 0: Charge Review was listed, every charge was checked and nothing is blocked", lambda: R1.code == 0 and R1.err == "", lambda: (R1.code, R1.err, R1.out[-300:]))
check("1d the LAST line is the ONE summary line with every count - charges and visits listed, checked, needed a Medicare answer, BLOCKED, not checked, unverified, the register - and no other line is printed",
      lambda: summary(R1, 4, 3, 4, 2, NOT_COUNTED, 0, 0, 0) and len(R1.lines) == 1, lambda: R1.lines)
check("1e 'needed a Medicare answer' is counted by the guard's own lists on what the guard reads: a care-management code (its procedure id) or straight Medicare at SEQUENCE 1 - a Medicare plan at sequence 2 does not count",
      lambda: [x.get("needed") for x in rows(R1)] == [True, False, True, False], lambda: rows(R1))
check("1f the helper reads each charge ONCE, by charge id: the code from the charge's own procedure list, the date of service from its visit, the chart from its patient - nothing but the ids comes from the listing",
      lambda: details(R1) == ["5001", "5002", "5003", "5004"] and [(x["chart"], x["visit"], x["charge"], x["dos"], x["code"]) for x in rows(R1)]
      == [("pat7001", "9001", "5001", iso(DOS_A), "99487"), ("pat7001", "9001", "5002", iso(DOS_A), "99349"), ("pat7002", "9002", "5003", iso(DOS_B), "99232"), ("pat7003", "9003", "5004", iso(DOS_C), "99349")],
      lambda: (details(R1), rows(R1)))
check("1g nothing else is sent to AdvancedMD: no approval, no save, no void, no rebill - the calls are the login, the list call and the reads by charge id",
      lambda: [c[0] for c in R1.calls] == ["login", "post", "detail", "detail", "detail", "detail"], lambda: [c[:2] for c in R1.calls])
scene(FOUR, bare=True); G1b = scripted(); R1b = run(guard=G1b)
check("1h ids without their prefixes in the listing (a visit '9001', a charge '5001' - the form the inspector's listing has) give the same checks and the same register",
      lambda: G1b.calls == G1.calls and R1b.code == 0 and [(x["chart"], x["visit"], x["charge"]) for x in rows(R1b)] == [(x["chart"], x["visit"], x["charge"]) for x in rows(R1)], lambda: (G1b.calls, rows(R1b)))
scene(FOUR); G1i = scripted(peek={"5001": ["5001", "charge5001", "5002"]}); R1i = run(guard=G1i)
check("1i ONE read of each charge: while the guard checks a charge, resave.detail(<that charge>) hands it the very answer the helper has just read and looked at - AdvancedMD is not asked a second time - and a read of ANOTHER charge still goes to AdvancedMD and gets that charge's own answer",
      lambda: G1i.seen == [("5001", STATE["details"]["5001"]), ("charge5001", STATE["details"]["5001"]), ("5002", STATE["details"]["5002"])] and STATE["details"]["5001"] != STATE["details"]["5002"]
      and details(R1i) == ["5001", "5002", "5002", "5003", "5004"] and R1i.code == 0, lambda: (details(R1i), [(a, b[:60]) for a, b in G1i.seen], R1i.lines))
check("1j ... and when the helper is done the stand-in's own resave.detail is back in its place (the helper leaves no changed module behind - also after a guard that raised)",
      lambda: resave.detail is _detail and R1i.code == 0, lambda: resave.detail)

# ---- 2. a BLOCKED charge ----------------------------------------------------------------------------------------------------------------------
scene(FOUR); G2 = scripted({"5003": True}); R2 = run(guard=G2)
check("2a exit 3 when a charge is blocked", lambda: R2.code == 3, lambda: (R2.code, R2.err))
check("2b ONE line for the BLOCKED charge: chart id, visit id, charge id, date of service, code and the fixed words",
      lambda: kind(R2, "BLOCKED") == ["BLOCKED: pat7002 visit 9002 charge 5003 DOS %s code 99232 - %s" % (iso(DOS_B), BLOCK)], lambda: R2.lines)
check("2c the other charges are still checked, and the summary line counts the blocked one", lambda: len(G2.calls) == 4 and summary(R2, 4, 3, 4, 2, NOT_COUNTED, 1, 0, 0) and len(R2.lines) == 2, lambda: R2.lines)
check("2d NEVER the day the patient passed away, the guard's own reason, a name, a birth date or a number - in a printed line or in the register - although the guard's reason and the stand-in's answers carry them",
      lambda: R2.code == 3 and leaks(R2.out + R2.raw) == [] and "stedi-medicare-271" not in R2.out + R2.raw and "claim must not be submitted" not in R2.out + R2.raw
      and iso(GONE) in G2.check_charge("5003", 1)[1], lambda: leaks(R2.out + R2.raw))
check("2e the register's row of the blocked charge says BLOCKED with the fixed words; the other rows say clear",
      lambda: (row(R2, "5003").get("result"), row(R2, "5003").get("words")) == ("BLOCKED", BLOCK) and [x.get("result") for x in rows(R2)] == ["clear", "clear", "BLOCKED", "clear"], lambda: rows(R2))

# ---- 3. a charge that could not be checked ---------------------------------------------------------------------------------------------------
scene(FOUR); G3 = scripted({"5002": RuntimeError("no chart for " + NAME_S + " of " + mdy(BORN_S))}); R3 = run(guard=G3)
check("3a the guard raised for one charge: ONE line with the fixed words and the error by its KIND only, exit 3",
      lambda: kind(R3, "NOT CHECKED") == ["NOT CHECKED: pat7001 visit 9001 charge 5002 (the guard raised RuntimeError) - %s" % UNCHECKED] and R3.code == 3, lambda: (R3.code, R3.lines))
check("3b the other charges are still checked, and the summary line says how many were checked and how many were not",
      lambda: [c[0] for c in G3.calls] == ["5001", "5002", "5003", "5004"] and summary(R3, 4, 3, 3, 2, NOT_COUNTED, 0, 1, 0), lambda: R3.lines)
check("3c the error's own words (they name a patient) are neither printed nor written, and the register's row carries the fixed words",
      lambda: leaks(R3.out + R3.raw) == [] and (row(R3, "5002").get("result"), row(R3, "5002").get("words")) == ("could not be checked", UNCHECKED) and "no chart for" not in R3.out + R3.raw, lambda: (leaks(R3.out + R3.raw), row(R3, "5002")))
scene([("9001", "7001", [FOUR[0][2][0]]), ("9004", "7004", [])]); G3b = scripted(); R3b = run(guard=G3b)
check("3d a visit the listing shows WITHOUT a charge (a visit still being entered) cannot be checked: it is named, exit 3, and the charges that are listed are still checked",
      lambda: kind(R3b, "NOT CHECKED") == ["NOT CHECKED: pat7004 visit 9004 charge ? (no charge listed under this visit) - %s" % UNCHECKED] and R3b.code == 3
      and [c[0] for c in G3b.calls] == ["5001"] and summary(R3b, 1, 2, 1, 1, NOT_COUNTED, 0, 1, 0), lambda: (R3b.code, R3b.lines))
scene([("9001", "7001", [FOUR[0][2][0]]), ("9005", "7005", [("", "pcode1", "99349", "car6404", "car6404", DOS_A)])]); G3c = scripted(); R3c = run(guard=G3c)
check("3e a charge the listing shows WITHOUT an id cannot be checked: it is named, exit 3 - never passed over in silence",
      lambda: kind(R3c, "NOT CHECKED") == ["NOT CHECKED: pat7005 visit 9005 charge ? (a charge without an id in the listing) - %s" % UNCHECKED] and R3c.code == 3
      and [c[0] for c in G3c.calls] == ["5001"] and summary(R3c, 2, 2, 1, 1, NOT_COUNTED, 0, 1, 0), lambda: (R3c.code, R3c.lines))
scene(FOUR); STATE["details"]["5003"] = RuntimeError("read failed for " + NAME_S); G3d = scripted({"5003": True}); R3d = run(guard=G3d)
check("3f the read for the words fails on a charge the guard BLOCKED: the block stands, the line shows '?' for what could not be read (the chart from the listing), and the error's words are not printed",
      lambda: kind(R3d, "BLOCKED") == ["BLOCKED: pat7002 visit 9002 charge 5003 DOS ? code ? - %s" % BLOCK] and R3d.code == 3 and leaks(R3d.out + R3d.raw) == [], lambda: (R3d.code, R3d.lines))
scene(FOUR); STATE["details"]["5001"] = RuntimeError("read failed for " + NAME_S); G3e = scripted(); R3e = run(guard=G3e)
check("3g the guard answers 'not blocked' but the helper cannot read the charge to see what the guard had to go on: NOT CHECKED - 'not blocked' counts as checked only when there was something to check",
      lambda: kind(R3e, "NOT CHECKED") == ["NOT CHECKED: pat7001 visit 9001 charge 5001 (the charge could not be read: RuntimeError) - %s" % UNCHECKED] and R3e.code == 3
      and summary(R3e, 4, 3, 3, 1, NOT_COUNTED, 0, 1, 0) and leaks(R3e.out + R3e.raw) == [], lambda: (R3e.code, R3e.lines, row(R3e, "5001")))
FAULT_X = "<PPMDResults><Results/><Error><Fault><detail><description>no such charge for %s</description></detail></Fault></Error></PPMDResults>" % NAME_S
scene(FOUR); STATE["details"]["5004"] = FAULT_X; G3h = scripted(); R3h = run(guard=G3h)
check("3h the charge's own detail is an answer with NO chart and NO date of service in it (a Fault): a guard that reads that answer has nothing to compare and says 'not blocked' - the helper says NOT CHECKED, never 'clear'",
      lambda: kind(R3h, "NOT CHECKED") == ["NOT CHECKED: pat7003 visit 9003 charge 5004 (no chart or no date of service in the charge's own detail) - %s" % UNCHECKED] and R3h.code == 3
      and summary(R3h, 4, 3, 3, 2, NOT_COUNTED, 0, 1, 0) and row(R3h, "5004").get("result") == "could not be checked" and leaks(R3h.out + R3h.raw) == [], lambda: (R3h.code, R3h.lines, row(R3h, "5004")))
scene(FOUR); STATE["details"]["5002"] = STATE["details"]["5001"]; G3i = scripted(); R3i = run(guard=G3i)
check("3i the charge's own row is not in its detail (the guard, reading the same answer, could not see its code): NOT CHECKED",
      lambda: kind(R3i, "NOT CHECKED") == ["NOT CHECKED: pat7001 visit 9001 charge 5002 (the charge is not in its own detail) - %s" % UNCHECKED] and R3i.code == 3 and summary(R3i, 4, 3, 3, 2, NOT_COUNTED, 0, 1, 0), lambda: (R3i.code, R3i.lines))

# ---- 4. free and bought answers: the guard's COUNTS, when the guard has them ----------------------------------------------------------------
scene(FOUR); G4 = scripted(counts={"5001": {"free asked": 1, "free answered": 1}, "5003": {"free asked": 1, "paid asked": 1}}, start={"free asked": 5, "free answered": 3, "paid asked": 2}); R4 = run(guard=G4)
check("4a a guard that counts (COUNTS): the summary line says how many answers AdvancedMD's free check gave, of how many asked, and how many were bought - what THIS start added, not what the guard had counted before",
      lambda: summary(R4, 4, 3, 4, 2, " - AdvancedMD's free check answered 1 of 2 asked, 1 bought from the vendor", 0, 0, 0) and R4.reg["counts"] == {"free asked": 2, "free answered": 1, "paid asked": 1}, lambda: (R4.lines, (R4.reg or {}).get("counts")))
check("4b a guard without COUNTS (an older guard): the summary line says the answers are not counted, the register holds no counts, and nothing breaks",
      lambda: NOT_COUNTED in R1.lines[-1] and R1.reg["counts"] is None and not hasattr(G1, "COUNTS"), lambda: R1.lines)
scene(FOUR); G4c = scripted(bad_counts=["not", "a", "table"]); R4c = run(guard=G4c)
check("4c a COUNTS that is not the table of three numbers is taken as 'not counted' - never a reason to end without an answer", lambda: R4c.code == 0 and summary(R4c, 4, 3, 4, 2, NOT_COUNTED, 0, 0, 0), lambda: (R4c.code, R4c.lines))

# ---- 5. a look-up that failed: said, never a block ---------------------------------------------------------------------------------------------
scene(FOUR); G5 = scripted({"5003": "unverified"}); R5 = run(guard=G5)
check("5a the guard could not ask Medicare (its LOG gets the UNVERIFIED line) and blocks nothing: ONE line 'date of death unverified' for that charge, exit 0",
      lambda: kind(R5, "UNVERIFIED") == ["UNVERIFIED: pat7002 visit 9002 charge 5003 DOS %s code 99232 - %s" % (iso(DOS_B), UNVERIFIED)] and R5.code == 0, lambda: (R5.code, R5.lines))
check("5b the summary line counts it, and the register's row is clear and marked unverified",
      lambda: summary(R5, 4, 3, 4, 2, NOT_COUNTED, 0, 0, 1) and (row(R5, "5003").get("result"), row(R5, "5003").get("unverified")) == ("clear", True) and not any(x.get("unverified") for x in rows(R5) if x["charge"] != "5003"), lambda: (R5.lines, rows(R5)))
scene(FOUR); G5b = scripted({"5003": "unverified"}, log=["pat1 DOS x: date of death UNVERIFIED (lookup failed)"]); R5b = run(guard=G5b)
check("5c an UNVERIFIED line the guard's LOG held BEFORE this start is not counted again", lambda: summary(R5b, 4, 3, 4, 2, NOT_COUNTED, 0, 0, 1) and len(kind(R5b, "UNVERIFIED")) == 1, lambda: R5b.lines)

# ---- 6. --dry: the guard's cache only ----------------------------------------------------------------------------------------------------------
scene(FOUR); G6 = scripted({"5003": True}); R6 = run(["--dry"], guard=G6)
check("6a --dry: every charge goes through the guard with allow_lookup=False (the cache only - Medicare is not asked, nothing is bought)",
      lambda: G6.calls == [("5001", 1, False), ("5002", 1, False), ("5003", 1, False), ("5004", 1, False)], lambda: G6.calls)
check("6b --dry: the summary line says so and that it is no clearance to approve; a day the cache knows still blocks (exit 3)",
      lambda: summary(R6, 4, 3, 4, 2, " - none asked (--dry: the guard's cache only, NOT a clearance to approve)", 1, 0, 0, dry="_dry") and R6.code == 3 and len(kind(R6, "BLOCKED")) == 1, lambda: (R6.code, R6.lines))
check("6c --dry: the register has a name of its own (..._dry.json) and says dry inside - it is never taken for a live check", lambda: len(R6.regs) == 1 and R6.regs[0].endswith("_dry.json") and R6.reg["dry"] is True and R1.reg["dry"] is False, lambda: R6.regs)
scene(FOUR); G6d = scripted(); R6d = run(["--live"], guard=G6d)
check("6d --live is the default said out loud (look-ups allowed)", lambda: R6d.code == 0 and G6d.calls == G1.calls and R6d.reg["dry"] is False, lambda: (R6d.code, R6d.lines))

# ---- 7. the register ----------------------------------------------------------------------------------------------------------------------------
check("7a the register is ONE file registers/death_check_review_<UTC stamp>.json under the folder the helper is started in, written whole (no temporary file left)",
      lambda: len(R1.regs) == 1 and re.match(r"death_check_review_\d{4}-\d{2}-\d{2}T\d{6}Z\.json$", R1.regs[0]) is not None and os.path.isfile(os.path.join(R1.ws, "registers", R1.regs[0])), lambda: R1.regs)
check("7b it holds the helper's name and version, the stamp, the exit code, the counts and one row per charge - chart id, visit id, charge id, date of service, code, the result",
      lambda: R1.reg["helper"] == "death_check_review.py" and re.match(r"\d{4}-\d{2}-\d{2}\.\d+$", R1.reg["version"]) is not None and R1.reg["stamp"] in R1.regs[0] and (R1.reg["exit"], R2.reg["exit"]) == (0, 3)
      and R1.reg["listed"] == {"visits": 3, "charges": 4} and (R1.reg["checked"], R1.reg["needed"], R1.reg["blocked"], R1.reg["unchecked"], R1.reg["unverified"]) == (4, 2, 0, 0, 0)
      and (R2.reg["blocked"], R3.reg["unchecked"], R5.reg["unverified"]) == (1, 1, 1) and all(set(x) <= {"chart", "visit", "charge", "dos", "code", "needed", "result", "unverified", "why", "words"} for r_ in (R1, R2, R3, R5) for x in rows(r_)),
      lambda: R1.reg)
check("7c its lines are the printed lines, word for word", lambda: R2.reg["lines"] == R2.lines and R1.reg["lines"] == R1.lines, lambda: (R2.reg or {}).get("lines"))
_W7 = new_ws(); open(os.path.join(_W7, "registers"), "w").close(); scene(FOUR); G7 = scripted({"5003": True}); R7 = run(guard=G7, ws=_W7)
check("7d a register that cannot be written does not take the answer away: the lines and the exit code stand, and the summary line says the register was NOT written",
      lambda: R7.code == 3 and len(kind(R7, "BLOCKED")) == 1 and re.search(r" - register NOT written \(\w+\)$", R7.lines[-1]) is not None and R7.lines[-1].startswith("DEATH CHECK - Charge Review: 4 charge(s)"), lambda: (R7.code, R7.lines))

# ---- 8. exit 2: Charge Review could not be listed - nothing may be approved on the helper's word -------------------------------------------
def unlisted(r, why, guard):
    return (r.code == 2 and r.lines == ["DEATH CHECK - Charge Review could not be listed (%s) - nothing was checked: %s" % (why, NOTHING)] and guard.calls == [] and details(r) == [] and r.regs == [] and r.err == "")
scene(FOUR); STATE["listing"] = RuntimeError("timed out for " + NAME_S); G8a = scripted(); R8a = run(guard=G8a)
check("8a the list call fails: exit 2, ONE plain line (the error by its kind), no guard call, no read, no register", lambda: unlisted(R8a, "the list call failed: RuntimeError", G8a) and leaks(R8a.out) == [], lambda: (R8a.code, R8a.lines, R8a.err))
scene(FOUR); STATE["listing"] = "<html>Service Unavailable"; G8b = scripted(); R8b = run(guard=G8b)
check("8b the answer is not a list (not XML): exit 2", lambda: unlisted(R8b, "the answer is not a list", G8b), lambda: (R8b.code, R8b.lines, R8b.err))
scene(FOUR); STATE["listing"] = "<html><head><title>Service Unavailable</title></head><body><h1>try again later, %s</h1></body></html>" % NAME_S; G8k = scripted(); R8k = run(guard=G8k)
check("8b2 the answer is well-formed but not AdvancedMD's (a gateway's page: no Results in it): exit 2 - never read as 'nothing is waiting in Charge Review'", lambda: unlisted(R8k, "the answer is not a list", G8k) and leaks(R8k.out) == [], lambda: (R8k.code, R8k.lines, R8k.err))
STATE.update(listing="<Results><visitlist/></Results>", login=None, details={}); G8l = scripted(); R8l = run(guard=G8l)
check("8b3 an answer that is AdvancedMD's bare Results element (the registry shows such answers) IS a list: an empty one is an empty Charge Review, exit 0", lambda: R8l.code == 0 and summary(R8l, 0, 0, 0, 0, NOT_COUNTED, 0, 0, 0), lambda: (R8l.code, R8l.lines))
scene(FOUR); STATE["listing"] = "<PPMDResults><Results/><Error><Fault><detail><description>no session for %s</description></detail></Fault></Error></PPMDResults>" % NAME_S; G8c = scripted(); R8c = run(guard=G8c)
check("8c AdvancedMD answers a Fault: exit 2 - never read as 'nothing is waiting' - and the Fault's own words are not printed", lambda: unlisted(R8c, "AdvancedMD answered a Fault", G8c) and leaks(R8c.out) == [], lambda: (R8c.code, R8c.lines, R8c.err))
scene(FOUR); STATE["listing"] = '<PPMDResults><Results success="0"/><Error/></PPMDResults>'; G8d = scripted(); R8d = run(guard=G8d)
check("8d AdvancedMD answers success 0: exit 2", lambda: unlisted(R8d, "AdvancedMD answered success 0", G8d), lambda: (R8d.code, R8d.lines, R8d.err))
scene(FOUR); STATE["listing"] = "<PPMDResults><Results/><Error>refused for %s</Error></PPMDResults>" % NAME_S; G8e = scripted(); R8e = run(guard=G8e)
check("8e an Error element that is not empty (every good answer carries an empty one): exit 2, its words not printed", lambda: unlisted(R8e, "AdvancedMD answered an error", G8e) and leaks(R8e.out) == [], lambda: (R8e.code, R8e.lines, R8e.err))
scene(FOUR); STATE["login"] = RuntimeError("LOGIN STEP2 FAILED for " + NAME_S); G8f = scripted(); R8f = run(guard=G8f)
check("8f the login fails: exit 2, the list call is not even sent, and the login is not tried a second time",
      lambda: unlisted(R8f, "the login failed: RuntimeError", G8f) and posts(R8f) == [] and [c[0] for c in R8f.calls] == ["login"] and leaks(R8f.out) == [], lambda: (R8f.code, R8f.lines, R8f.calls))
scene(FOUR); G8g = scripted(); R8g = run(["--batch"], guard=G8g)
check("8g an option it does not know is refused, not passed over: exit 2, ONE line with the usage, no login, no call",
      lambda: R8g.code == 2 and R8g.lines == ["DEATH CHECK - it does not know '--batch' - nothing was checked: %s (usage: python3 death_check_review.py [--dry])" % NOTHING] and R8g.calls == [] and G8g.calls == [] and R8g.regs == [], lambda: (R8g.code, R8g.lines))
scene(FOUR); G8h = scripted(); R8h = run(["--dry", "--live"], guard=G8h)
check("8h --dry and --live together are refused the same way (which of the two was meant?)", lambda: R8h.code == 2 and len(R8h.lines) == 1 and NOTHING in R8h.lines[0] and R8h.calls == [] and G8h.calls == [], lambda: (R8h.code, R8h.lines))
scene(FOUR); G8i = scripted(); R8i = run(guard=G8i, drop=("resave",))
check("8i a helper it needs cannot be loaded (resave.py missing from the workspace): exit 2 with ONE plain line - never Python's own error text - and no call at all",
      lambda: R8i.code == 2 and R8i.lines == ["DEATH CHECK - amd.py, resave.py or deceased_guard.py could not be loaded (ImportError) - nothing was checked: %s" % NOTHING] and R8i.calls == [] and R8i.err == "", lambda: (R8i.code, R8i.lines, R8i.err))
class _BadLog(list):
    def __len__(self): raise RuntimeError("the log broke for " + NAME_S)
scene(FOUR); G8j = scripted(log=_BadLog()); R8j = run(guard=G8j)
check("8j an error of the helper's own ends it with ONE plain last line - the error's kind and the line of the file, never its words, never Python's own error text - and exit 2",
      lambda: R8j.code == 2 and R8j.err == "" and re.match(r"DEATH CHECK - this helper ended on an error of its own \(RuntimeError at line \d+ of death_check_review\.py\) - whatever it printed above does not count: %s$" % re.escape(NOTHING), R8j.lines[-1]) is not None
      and "Traceback" not in R8j.out and leaks(R8j.out) == [] and R8j.regs == [], lambda: (R8j.code, R8j.lines, R8j.err))

# ---- 9. what the listing can look like -------------------------------------------------------------------------------------------------------------
STATE.update(listing="<PPMDResults><Results><visitlist/></Results><Error/></PPMDResults>", login=None, details={}); G9a = scripted(); R9a = run(guard=G9a)
check("9a an empty Charge Review: exit 0, the summary line says 0 charges, and the register is still written (a record that the step looked)",
      lambda: R9a.code == 0 and summary(R9a, 0, 0, 0, 0, NOT_COUNTED, 0, 0, 0) and len(R9a.lines) == 1 and G9a.calls == [] and rows(R9a) == [] and len(R9a.regs) == 1, lambda: (R9a.code, R9a.lines))
scene([("9001", "7001", [FOUR[0][2][0], FOUR[0][2][0]]), ("9006", "7001", [FOUR[0][2][0]])]); G9b = scripted(); R9b = run(guard=G9b)
check("9b a charge the listing shows more than once is checked once and counted once", lambda: [c[0] for c in G9b.calls] == ["5001"] and summary(R9b, 1, 2, 1, 1, NOT_COUNTED, 0, 0, 0) and R9b.code == 0, lambda: (G9b.calls, R9b.lines))
scene([("9001", "7001", [FOUR[0][2][0]])], tail='<chargelist><charge id="charge5009" proccode="pcode1"/></chargelist>')
STATE["details"]["5009"] = detail_xml("5009", "7009", "9009", DOS_C, "pcode492677", "99489", [(1, "car6404")]); G9c = scripted({"5009": True}); R9c = run(guard=G9c)
check("9c a charge row OUTSIDE every visit element is checked too - its visit and chart come from the charge's own detail",
      lambda: [c[0] for c in G9c.calls] == ["5001", "5009"] and kind(R9c, "BLOCKED") == ["BLOCKED: pat7009 visit 9009 charge 5009 DOS %s code 99489 - %s" % (iso(DOS_C), BLOCK)] and summary(R9c, 2, 1, 2, 2, NOT_COUNTED, 1, 0, 0), lambda: (G9c.calls, R9c.lines))
scene(FOUR); STATE["details"]["5004"] = detail_xml("5004", "7003", "9003", DOS_C, "99349", "", [(1, "FLO02")]).replace('<proccodelist><proccode id="99349" code=""/></proccodelist>', ""); G9d = scripted(); R9d = run(guard=G9d)
check("9d a charge whose detail carries the code itself (no procedure list) is shown by that code, and the carrier CODE of straight Medicare (FLO02) counts as the carrier id does",
      lambda: (row(R9d, "5004").get("code"), row(R9d, "5004").get("needed")) == ("99349", True) and summary(R9d, 4, 3, 4, 3, NOT_COUNTED, 0, 0, 0), lambda: (row(R9d, "5004"), R9d.lines))
LONG = [("20" + "261124", "19" + "561207", [("20" + "111213", "pcode65089", "99232", "car6085", "car6404", DOS_B)])]      # a visit, a chart and a charge id of eight digits that READ like dates (put together here)
scene(LONG); G9e = scripted({LONG[0][2][0][0]: True}); R9e = run(guard=G9e)
check("9e ids as long as the practice's own (eight digits, some reading like a date) are printed and written as they are - and the privacy gate leaves the BLOCKED line and the register alone (no day stands behind the word death in them)",
      lambda: kind(R9e, "BLOCKED") == ["BLOCKED: pat%s visit %s charge %s DOS %s code 99232 - %s" % (LONG[0][1], LONG[0][0], LONG[0][2][0][0], iso(DOS_B), BLOCK)] and R9e.code == 3
      and (row(R9e, LONG[0][2][0][0]).get("chart"), row(R9e, LONG[0][2][0][0]).get("visit")) == ("pat" + LONG[0][1], LONG[0][0]), lambda: (R9e.code, R9e.lines, rows(R9e)))

# ---- 9x. the SECOND question - the plan the claim goes to FIRST and the code itself: deceased_guard.check, the call the runs' own code made ----
def one(cid, order, plans, proc="pcode65142", code="99349", order_list=None, pid="7201", vid="9201"):
    """ONE charge in Charge Review whose detail shows this insurance order and these plans [(sequence, carrier)]; order_list = the rows of
    the insurance-order list ("2", or ("2", carrier) for a row that names its carrier)"""
    STATE.update(listing=listing_xml([(vid, pid, [cid])]), login=None, details={cid: detail_xml(cid, pid, vid, DOS_A, proc, code, plans, order=order, order_list=order_list)})
SECOND = ("7201", iso(DOS_A), "car6085", "99349", True)      # the second question of the charges below: chart, date of service, the carrier of the visit's first plan, the code, look-ups allowed
one("5201", "3,1", [(1, "car6404"), (3, "car6085")]); GX1 = scripted(); RX1 = run(guard=GX1)
check("9x1 a visit whose insurance order starts with ANOTHER plan than sequence 1 (order '3,1'): the charge is asked about at sequence 1 like every charge (check_charge) AND a second time with the chart, the date of service, the carrier of the plan the claim really goes to FIRST and the code itself (deceased_guard.check)",
      lambda: GX1.calls == [("5201", 1, True)] and GX1.checks == [SECOND] and RX1.code == 0, lambda: (GX1.calls, GX1.checks, RX1.lines))
check("9x2 ... and 'needed a Medicare answer' counts that plan: straight Medicare at sequence 3, first in the visit's order, counts although the plan at sequence 1 is another carrier",
      lambda: row(RX1, "5201").get("needed") is True and summary(RX1, 1, 1, 1, 1, NOT_COUNTED, 0, 0, 0), lambda: (row(RX1, "5201"), RX1.lines))
one("5202", "1,3", [(1, "car6404"), (3, "car6085")]); GX2 = scripted(); RX2 = run(guard=GX2)
check("9x3 a visit whose order starts with sequence 1 (and whose code is no care-management code) is asked about ONCE, as the specification says - a Medicare plan further down the order asks nothing and does not count",
      lambda: GX2.calls == [("5202", 1, True)] and GX2.checks == [] and row(RX2, "5202").get("needed") is False, lambda: (GX2.calls, GX2.checks, row(RX2, "5202")))
one("5203", "2,1", [(1, "car6404"), (2, "car6085")]); GX3 = scripted(second={"7201": True}); RX3 = run(guard=GX3)
check("9x4 the day is found only by the second question (the visit's FIRST plan, sequence 2): the charge is BLOCKED - asked about sequence 1 alone it would have passed",
      lambda: GX3.calls == [("5203", 1, True)] and GX3.checks == [SECOND] and kind(RX3, "BLOCKED") == ["BLOCKED: pat7201 visit 9201 charge 5203 DOS %s code 99349 - %s" % (iso(DOS_A), BLOCK)] and RX3.code == 3
      and leaks(RX3.out + RX3.raw) == [], lambda: (GX3.calls, GX3.checks, RX3.lines))
one("5204", "2,1", [(1, "car6085"), (2, "car6404")]); GX4 = scripted({"5204": True}, second={"7201": True}); RX4 = run(guard=GX4)
check("9x5 a charge the guard blocks at sequence 1 is BLOCKED at once - no second question is asked", lambda: GX4.calls == [("5204", 1, True)] and GX4.checks == [] and RX4.code == 3 and len(kind(RX4, "BLOCKED")) == 1, lambda: (GX4.calls, GX4.checks, RX4.lines))
one("5205", "1", [(1, "car6404"), (2, "car6085")], order_list=["2", "1"]); GX5 = scripted(); RX5 = run(guard=GX5)
check("9x6 the insurance-order LIST AdvancedMD built counts too (a claim is built from the list): the attribute says 1, the list starts with plan 2 - the second question is asked with plan 2's carrier",
      lambda: GX5.calls == [("5205", 1, True)] and GX5.checks == [SECOND] and row(RX5, "5205").get("needed") is True, lambda: (GX5.calls, GX5.checks, row(RX5, "5205")))
one("5206", "", [(1, "car6404"), (2, "car6085")]); GX6 = scripted(); RX6 = run(guard=GX6)
one("5207", "x,2", [(1, "car6404"), (2, "car6085")]); GX7 = scripted(); RX7 = run(guard=GX7)
check("9x7 a visit that shows no order, or one that does not begin with a number, gets no second question", lambda: GX6.calls == [("5206", 1, True)] and GX7.calls == [("5207", 1, True)] and GX6.checks == GX7.checks == [] and RX6.code == RX7.code == 0,
      lambda: (GX6.calls, GX6.checks, GX7.calls, GX7.checks))
one("5208", "3,1", [(1, "car6404"), (3, "car6085")]); GX8 = scripted(); RX8 = run(["--dry"], guard=GX8)
check("9x8 --dry asks both questions from the cache only", lambda: GX8.calls == [("5208", 1, False)] and GX8.checks == [SECOND[:4] + (False,)] and RX8.code == 0 and RX8.reg["dry"] is True, lambda: (GX8.calls, GX8.checks, RX8.code))
one("5209", "3,1", [(1, "car6404"), (3, "car6085")]); STATE["details"]["5209"] = RuntimeError("read failed for " + NAME_S); GX9 = scripted({"5209": True}); RX9 = run(guard=GX9)
check("9x9 when the charge cannot be read (no order, no code to ask a second time with) the guard is still asked at sequence 1 - a block there stands", lambda: GX9.calls == [("5209", 1, True)] and GX9.checks == [] and RX9.code == 3 and len(kind(RX9, "BLOCKED")) == 1,
      lambda: (GX9.calls, GX9.checks, RX9.lines))
one("5210", "1,2", [(1, "car6404"), (2, "car6113")], proc="pcode555555", code="99489"); GY1 = scripted(); RY1 = run(guard=GY1)
check("9y1 a care-management code the guard's list knows by its CODE, on a charge whose procedure id the list does not hold (check_charge hands the guard the id): the second question is asked with the code itself, and the charge counts as one that needed a Medicare answer",
      lambda: GY1.calls == [("5210", 1, True)] and GY1.checks == [("7201", iso(DOS_A), "car6404", "99489", True)] and (row(RY1, "5210").get("needed"), row(RY1, "5210").get("code")) == (True, "99489") and RY1.code == 0, lambda: (GY1.calls, GY1.checks, row(RY1, "5210")))
one("5211", "1,2", [(1, "car6404"), (2, "car6113")], proc="pcode555555", code="99489"); GY2 = scripted(second={"7201": True}); RY2 = run(guard=GY2)
check("9y2 ... and a day that question finds blocks the charge", lambda: kind(RY2, "BLOCKED") == ["BLOCKED: pat7201 visit 9201 charge 5211 DOS %s code 99489 - %s" % (iso(DOS_A), BLOCK)] and RY2.code == 3 and leaks(RY2.out + RY2.raw) == [], lambda: (GY2.checks, RY2.lines))
one("5212", "1,2", [(1, "car6404"), (2, "car6113")], proc="pcode492677", code="99489"); GY3 = scripted(); RY3 = run(guard=GY3)
check("9y3 a care-management code the guard knows by its procedure id gets no second question - the first one already told the guard", lambda: GY3.calls == [("5212", 1, True)] and GY3.checks == [] and row(RY3, "5212").get("needed") is True, lambda: (GY3.calls, GY3.checks, row(RY3, "5212")))
one("5213", "1,2", [(1, "car6404"), (2, "car6113")], proc="pcode555555", code="99489"); GY4 = scripted(second={"7201": RuntimeError("no chart for " + NAME_S)}); RY4 = run(guard=GY4)
check("9y4 the guard raises on the second question: the charge is NOT CHECKED (the error by its kind only), exit 3", lambda: kind(RY4, "NOT CHECKED") == ["NOT CHECKED: pat7201 visit 9201 charge 5213 (the guard raised RuntimeError) - %s" % UNCHECKED] and RY4.code == 3
      and leaks(RY4.out + RY4.raw) == [], lambda: (GY4.checks, RY4.lines))
one("5214", "1,2", [(1, "car6404"), (2, "car6113")], proc="pcode555555", code="99489"); GY5 = scripted(second={"7201": "unverified"}); RY5 = run(guard=GY5)
check("9y5 a look-up that fails on the second question is said like any other (ONE UNVERIFIED line, no block)", lambda: len(kind(RY5, "UNVERIFIED")) == 1 and RY5.code == 0 and summary(RY5, 1, 1, 1, 1, NOT_COUNTED, 0, 0, 1), lambda: (GY5.checks, RY5.lines))

# ---- 9z. the carrier of the plan the claim goes to first, as the insurance-order LIST's own first row names it ---------------------------------
one("5301", "1", [], order_list=[("1", "car6085"), ("2", "car6404")]); GZ1 = scripted(); RZ1 = run(guard=GZ1)
check("9z1 a detail that shows NO plan element (check_charge then hands the guard no carrier at all) while the insurance-order list's first row names straight Medicare: the second question is asked with that carrier - the row with ordinal 0, wherever it stands in the answer - and the charge counts as one that needed a Medicare answer",
      lambda: GZ1.calls == [("5301", 1, True)] and GZ1.checks == [SECOND] and row(RZ1, "5301").get("needed") is True and RZ1.code == 0, lambda: (GZ1.calls, GZ1.checks, row(RZ1, "5301")))
one("5302", "1", [], order_list=[("1", "6085")]); GZ2 = scripted(); RZ2 = run(guard=GZ2)
check("9z2 a carrier the row gives as bare digits (this answer gives the chart's id without its prefix too) is handed to the guard in the form the guard's own list holds: car<digits>",
      lambda: GZ2.checks == [SECOND] and row(RZ2, "5302").get("needed") is True, lambda: (GZ2.checks, row(RZ2, "5302")))
one("5303", "1", [], order_list=[("1", "FLO02")]); GZ3 = scripted(); RZ3 = run(guard=GZ3)
check("9z3 a carrier the row gives as the carrier's code (FLO02) is handed over as it is - the guard's list holds straight Medicare under both", lambda: GZ3.checks == [SECOND[:2] + ("FLO02",) + SECOND[3:]] and row(RZ3, "5303").get("needed") is True, lambda: (GZ3.checks, row(RZ3, "5303")))
one("5304", "1,2", [(1, "car6404"), (2, "car6085")], order_list=[("1", "car6404"), ("2", "car6085")]); GZ4 = scripted(); RZ4 = run(guard=GZ4)
check("9z4 the row names the very carrier the plan at sequence 1 shows (the usual case): ONE question, no second one - and a Medicare plan further down the list asks nothing", lambda: GZ4.calls == [("5304", 1, True)] and GZ4.checks == [] and row(RZ4, "5304").get("needed") is False,
      lambda: (GZ4.calls, GZ4.checks, row(RZ4, "5304")))
one("5305", "1", [(1, "6085")]); GZ5 = scripted(); RZ5 = run(guard=GZ5)
check("9z5 the plan at sequence 1 itself shows its carrier as bare digits (check_charge hands the guard those digits, which its list does not hold): the second question is asked in the list's own form", lambda: GZ5.checks == [SECOND] and row(RZ5, "5305").get("needed") is True,
      lambda: (GZ5.checks, row(RZ5, "5305")))
one("5307", "1", [(1, "car6085")], order_list=[("1", "FLO02")]); GZ7 = scripted({"5307": "unverified"}); RZ7 = run(guard=GZ7)
check("9z7 the row names straight Medicare by its code and the plan at sequence 1 by its id - one payer to the guard, whose list holds both: ONE question (a second one would only make a look-up that failed be tried twice)",
      lambda: GZ7.calls == [("5307", 1, True)] and GZ7.checks == [] and row(RZ7, "5307").get("needed") is True and len(kind(RZ7, "UNVERIFIED")) == 1, lambda: (GZ7.calls, GZ7.checks, RZ7.lines))
one("5306", "1", [(1, "car6404")], order_list=[("1", NAME_S)]); GZ6 = scripted(); RZ6 = run(guard=GZ6)
check("9z6 a 'carrier' that is not one word of letters and digits is never handed on", lambda: GZ6.checks == [] and RZ6.code == 0 and leaks(RZ6.out + RZ6.raw) == [], lambda: (GZ6.checks, RZ6.lines))

# ---- 10. with the REAL guard (scripts/helpers/deceased_guard.py, loaded from its file with the stand-ins in place) ---------------------------
DG = None; DG_ERR = ""
_had = {n: sys.modules.get(n) for n in STANDINS}
try:
    sys.modules.update(STANDINS)      # a guard that loads amd / resave / stedi / elig_amd as soon as it is loaded finds the stand-ins, never the live modules
    DG = types.ModuleType("deceased_guard"); DG.__file__ = os.path.join(ROOT, GUARD); DG.UNDER_TEST = True
    exec(compile(_read(GUARD), DG.__file__, "exec"), DG.__dict__)
except Exception as e: DG_ERR = "%s: %s" % (type(e).__name__, e); DG = None
finally:
    sys.path[:] = _PATH
    for n, m in _had.items():
        sys.modules.pop(n, None)
        if m is not None: sys.modules[n] = m
check("10a the real guard is loaded from its file and writes its cache in the throwaway folder - never the repository's (its cache path is the one set here)",
      lambda: DG is not None and DG.CACHE == DCACHE and callable(DG.check_charge), lambda: DG_ERR or getattr(DG, "CACHE", None))
def cache():
    try:
        with open(DCACHE) as fh: return json.load(fh)
    except (OSError, ValueError): return {}
def tally(): return dict(DG.COUNTS) if isinstance(getattr(DG, "COUNTS", None), dict) else None
R0 = types.SimpleNamespace(code=None, out="", lines=[], reg=None, raw="", regs=[], ws="", calls=[], vendor=[], err="the real guard could not be loaded"); T0 = T1 = None
if DG is not None:
    one("5109", "1", [(1, "car6085")], proc="pcode65089", code="99232", pid="7109", vid="9109")
    STATE["charts"] = {"7109": [("car6085", MBI_S)]}; STATE["medicare"] = {"7109": GONE}; STATE["free"] = {"71090": GONE}      # the day is on Medicare's record whichever way the guard asks: AdvancedMD's free check (plan ins71090) or the vendor
    T0 = tally(); R0 = run(guard=DG); T1 = tally(); STATE["free"] = {}
def said(r, t0, t1):
    """the part of the summary line about free and bought answers must be exactly what the guard itself counted during that start"""
    if t0 is None or t1 is None: return NOT_COUNTED in r.lines[-1] and r.reg["counts"] is None
    d = {k: t1[k] - t0[k] for k in t1}
    return r.reg["counts"] == d and (" - AdvancedMD's free check answered %d of %d asked, %d bought from the vendor; " % (d["free answered"], d["free asked"], d["paid asked"])) in r.lines[-1]
check("10a2 the first start with the real guard: the day on Medicare's record blocks the charge whichever way this guard asks (AdvancedMD's free check first, or the vendor at once), and what the guard itself counted during the start - free checks asked and answered, answers bought - is exactly what the summary line and the register say ('not counted' for a guard without COUNTS)",
      lambda: R0.code == 3 and kind(R0, "BLOCKED") == ["BLOCKED: pat7109 visit 9109 charge 5109 DOS %s code 99232 - %s" % (iso(DOS_A), BLOCK)] and said(R0, T0, T1) and (T1 is None or sum(T1[k] - T0[k] for k in T1) >= 1)
      and (R0.vendor == ["7109"] or any(c[0] == "elig" for c in R0.calls)) and leaks(R0.out + R0.raw) == [], lambda: (R0.code, R0.err, R0.lines, T0, T1, R0.vendor))
FIVE = [("9101", "7101", [("5101", "pcode65089", "99232", "car6085", "car6404", DOS_A)]),       # straight Medicare; Medicare's record shows a day before the date of service
        ("9102", "7102", [("5102", "pcode492676", "99487", "car6404", "car6113", DOS_A)]),      # care management on another plan, no Medicare plan on the chart; the same
        ("9103", "7103", [("5103", "pcode65089", "99232", "car6085", "car6404", DOS_B)]),       # straight Medicare; nothing on Medicare's record
        ("9104", "7104", [("5104", "pcode65089", "99232", "car6085", "car6404", DOS_B)]),       # straight Medicare; the look-up fails
        ("9105", "7105", [("5105", "pcode65142", "99349", "car6404", "car6085", DOS_C)])]       # neither care management nor straight Medicare at sequence 1
def real_scene():
    scene(FIVE); del DG.LOG[:]; STATE["free"] = {}
    STATE["charts"] = {"7101": [("car6085", MBI_S)], "7102": [("car6404", MEM_S)], "7103": [("car6085", MBI_S)], "7104": [("car6085", MBI_S)], "7105": [("car6404", MEM_S), ("car6085", MBI_S)]}
    STATE["medicare"] = {"7101": GONE, "7102": GONE2, "7103": "alive", "7104": "failed"}
COUNTED = r" - AdvancedMD's free check answered \d+ of \d+ asked, \d+ bought from the vendor"
def real_summary(r, charges, visits, checked, needed, blocked, unchecked, unverified, how=None, dry=""):
    """the summary line with the real guard: the part about free and bought answers is the guard's own count when it has one"""
    how = how if how is not None else (COUNTED if isinstance(getattr(DG, "COUNTS", None), dict) else re.escape(NOT_COUNTED))
    return bool(r.lines) and re.match(SUMMARY % (charges, visits, checked, needed, how, blocked, unchecked, unverified, dry), r.lines[-1]) is not None
RA = RB = RC = RD = RE = RF = RG = types.SimpleNamespace(code=None, out="", lines=[], reg=None, raw="", regs=[], ws="", calls=[], vendor=[], err="the real guard could not be loaded")
if DG is not None:
    real_scene(); RA = run(guard=DG)
check("10b a day on Medicare's record before the date of service blocks the straight-Medicare charge AND the care-management charge on another plan: two BLOCKED lines, exit 3",
      lambda: RA.code == 3 and kind(RA, "BLOCKED") == ["BLOCKED: pat7101 visit 9101 charge 5101 DOS %s code 99232 - %s" % (iso(DOS_A), BLOCK), "BLOCKED: pat7102 visit 9102 charge 5102 DOS %s code 99487 - %s" % (iso(DOS_A), BLOCK)],
      lambda: (RA.code, RA.err, RA.lines))
check("10c a look-up that fails blocks nothing and is said: ONE UNVERIFIED line for that charge (the guard's own LOG line is its source), and the charge counts as checked",
      lambda: kind(RA, "UNVERIFIED") == ["UNVERIFIED: pat7104 visit 9104 charge 5104 DOS %s code 99232 - %s" % (iso(DOS_B), UNVERIFIED)] and sum(1 for x in DG.LOG if "UNVERIFIED" in str(x)) == 1 and row(RA, "5104").get("result") == "clear",
      lambda: (RA.lines, getattr(DG, "LOG", None)))
check("10d the summary line: 5 charges on 5 visits listed, 5 checked, 4 needed a Medicare answer, 2 BLOCKED, 0 not checked, 1 unverified - and no line of the helper's for the two clear charges",
      lambda: real_summary(RA, 5, 5, 5, 4, 2, 0, 1) and len([l for l in RA.lines if l.startswith(("BLOCKED", "NOT CHECKED", "UNVERIFIED", "DEATH CHECK"))]) == 4, lambda: RA.lines)
def charts_read(r):
    """the charts the guard read (getdemographic), each once, in order - how often a guard reads one chart is the guard's own business"""
    out = []
    for c in posts(r, "getdemographic"):
        p = re.search(r'patientid="(?:pat)?(\d+)"', c[3]).group(1)
        if p not in out: out.append(p)
    return out
check("10e Medicare is asked about the four charts whose charge is care management or goes to straight Medicare at sequence 1 - and about nothing for the fifth (its Medicare plan is at sequence 2)",
      lambda: RA.vendor == ["7101", "7102", "7103", "7104"] and charts_read(RA) == ["7101", "7102", "7103", "7104"], lambda: (RA.vendor, [c[1] for c in RA.calls]))
check("10f the day itself is in the GUARD's cache (where it belongs) and nowhere in what the helper printed or wrote",
      lambda: cache()["7101"]["dod"] == iso(GONE) and cache()["7102"]["dod"] == iso(GONE2) and leaks(RA.out + RA.raw) == [], lambda: (cache(), leaks(RA.out + RA.raw)))
if DG is not None:
    real_scene(); RB = run(guard=DG)
check("10g a second start: a day already in the guard's cache blocks with NO call at all - no chart read, no free check, nothing bought - and a chart with a fresh 'nothing on record' is not asked about again",
      lambda: RB.code == 3 and len(kind(RB, "BLOCKED")) == 2 and RB.vendor == ["7104"] and charts_read(RB) == ["7104"]
      and not any(c[0] == "elig" and c[1].startswith(("ins7101", "ins7102", "ins7103", "7101", "7102", "7103")) for c in RB.calls), lambda: (RB.code, RB.vendor, [c[:2] for c in RB.calls]))
if DG is not None:
    real_scene(); shutil.rmtree(os.path.dirname(DCACHE), True); RC = run(["--dry"], guard=DG)
check("10h --dry with the real guard and an empty cache: nothing is asked (no chart read, no free check, nothing bought), nothing is known, nothing is blocked - and the summary line says it is no clearance",
      lambda: RC.code == 0 and RC.vendor == [] and posts(RC, "getdemographic") == [] and not any(c[0] == "elig" for c in RC.calls) and real_summary(RC, 5, 5, 5, 4, 0, 0, 0, how=re.escape(" - none asked (--dry: the guard's cache only, NOT a clearance to approve)"), dry="_dry")
      and cache() == {}, lambda: (RC.code, RC.lines, RC.vendor))
if DG is not None:
    real_scene(); os.makedirs(os.path.dirname(DCACHE), exist_ok=True)
    with open(DCACHE, "w") as fh: json.dump({"7101": {"dod": iso(GONE), "checked": iso(TODAY), "src": "an earlier look-up"}}, fh)
    RD = run(["--dry"], guard=DG)
check("10i --dry with a day in the guard's cache: that charge is BLOCKED from the cache alone (exit 3), still with no call", lambda: RD.code == 3 and kind(RD, "BLOCKED") == ["BLOCKED: pat7101 visit 9101 charge 5101 DOS %s code 99232 - %s" % (iso(DOS_A), BLOCK)]
      and RD.vendor == [] and posts(RD, "getdemographic") == [], lambda: (RD.code, RD.lines))
if DG is not None:
    real_scene(); shutil.rmtree(os.path.dirname(DCACHE), True); STATE["details"]["5103"] = FAULT_X; RE = run(guard=DG)
check("10j with the REAL guard, a charge whose detail answer carries no chart and no date of service (a Fault) is NOT CHECKED - whether the guard raises on such an answer or passes it - and Medicare is asked nothing about it",
      lambda: len(kind(RE, "NOT CHECKED")) == 1 and kind(RE, "NOT CHECKED")[0].startswith("NOT CHECKED: pat7103 visit 9103 charge 5103 (") and kind(RE, "NOT CHECKED")[0].endswith(") - " + UNCHECKED) and RE.code == 3
      and row(RE, "5103").get("result") == "could not be checked" and RE.vendor == ["7101", "7102", "7104"] and real_summary(RE, 5, 5, 4, 3, 2, 1, 1) and leaks(RE.out + RE.raw) == [], lambda: (RE.code, RE.lines, RE.vendor))
if DG is not None:
    shutil.rmtree(os.path.dirname(DCACHE), True); del DG.LOG[:]
    one("5106", "2,1", [(1, "car6404"), (2, "car6085")], pid="7106", vid="9106")
    STATE["charts"] = {"7106": [("car6404", MEM_S), ("car6085", MBI_S)]}; STATE["medicare"] = {"7106": GONE}
    RF = run(guard=DG)
check("10k with the REAL guard, a straight-Medicare claim whose Medicare plan stands at sequence 2 and FIRST in the visit's order: Medicare is asked (asked about sequence 1 alone it is not) and the day on its record blocks the charge",
      lambda: RF.vendor == ["7106"] and kind(RF, "BLOCKED") == ["BLOCKED: pat7106 visit 9106 charge 5106 DOS %s code 99349 - %s" % (iso(DOS_A), BLOCK)] and RF.code == 3 and leaks(RF.out + RF.raw) == [], lambda: (RF.code, RF.lines, RF.vendor))
if DG is not None:
    shutil.rmtree(os.path.dirname(DCACHE), True); del DG.LOG[:]
    one("5107", "1", [(1, "car6404")], proc="pcode555555", code="99490", pid="7107", vid="9107")
    STATE["charts"] = {"7107": [("car6404", MEM_S)]}; STATE["medicare"] = {"7107": GONE2}
    RG = run(guard=DG)
check("10l with the REAL guard, a care-management code (99490) on a plan that is not Medicare, entered under a procedure id the guard's list does not hold: Medicare is asked by the code itself (asked by the id alone it is not) and the day on its record blocks the charge",
      lambda: "99490" in DG.CCM and "pcode555555" not in DG.CCM and RG.vendor == ["7107"] and kind(RG, "BLOCKED") == ["BLOCKED: pat7107 visit 9107 charge 5107 DOS %s code 99490 - %s" % (iso(DOS_A), BLOCK)] and RG.code == 3
      and leaks(RG.out + RG.raw) == [], lambda: (RG.code, RG.lines, RG.vendor))
check("10m with the REAL guard each charge is read ONCE: the guard, which reads the charge it checks itself (resave.detail), is handed the answer the helper has just read",
      lambda: details(RA) == ["5101", "5102", "5103", "5104", "5105"] and details(RB) == ["5101", "5102", "5103", "5104", "5105"], lambda: (details(RA), details(RB)))
RH = RG
if DG is not None:
    shutil.rmtree(os.path.dirname(DCACHE), True); del DG.LOG[:]
    one("5108", "1", [(1, "car6085")], proc="pcode65089", code="99232", pid="7108", vid="9108"); STATE["details"]["5108"] = [STATE["details"]["5108"], FAULT_X]
    STATE["charts"] = {"7108": [("car6085", MBI_S)]}; STATE["medicare"] = {"7108": GONE}
    RH = run(guard=DG)
check("10n with the REAL guard, AdvancedMD answers the charge's detail ONCE and a Fault from then on: the guard decides on the answer the helper looked at - Medicare is asked and the day on its record blocks the charge. (Read a second time, the guard would get the Fault, find no chart in it and pass the charge - and the helper, whose own read was good, would call it clear.)",
      lambda: RH.vendor == ["7108"] and kind(RH, "BLOCKED") == ["BLOCKED: pat7108 visit 9108 charge 5108 DOS %s code 99232 - %s" % (iso(DOS_A), BLOCK)] and RH.code == 3 and details(RH) == ["5108"]
      and leaks(RH.out + RH.raw) == [], lambda: (RH.code, RH.lines, RH.vendor, details(RH)))
RI = RG
if DG is not None:
    shutil.rmtree(os.path.dirname(DCACHE), True); del DG.LOG[:]
    one("5110", "1", [(1, "car6085")], proc="pcode65089", code="99232", pid="7110", vid="9110"); STATE["details"]["5110"] = [FAULT_X, STATE["details"]["5110"]]
    STATE["charts"] = {"7110": [("car6085", MBI_S)]}; STATE["medicare"] = {"7110": GONE}
    RI = run(guard=DG)
check("10p with the REAL guard, the other way round - the helper's own read of the charge is a Fault, the next read is good: an answer with nothing to check in it is NOT handed to the guard, the guard reads for itself and the day it finds blocks the charge (a block always stands; the line shows '?' for what the helper could not read)",
      lambda: details(RI) == ["5110", "5110"] and RI.vendor == ["7110"] and kind(RI, "BLOCKED") == ["BLOCKED: pat7110 visit 9110 charge 5110 DOS ? code ? - %s" % BLOCK] and RI.code == 3 and leaks(RI.out + RI.raw) == [],
      lambda: (RI.code, RI.lines, RI.vendor, details(RI)))
RJ = RG
if DG is not None:
    shutil.rmtree(os.path.dirname(DCACHE), True); del DG.LOG[:]
    one("5111", "1", [], order_list=[("1", "car6085")], proc="pcode65089", code="99232", pid="7111", vid="9111")
    STATE["charts"] = {"7111": [("car6085", MBI_S)]}; STATE["medicare"] = {"7111": GONE}
    RJ = run(guard=DG)
check("10q with the REAL guard, a straight-Medicare claim whose charge detail shows no plan element - only the insurance-order list's row names the carrier: Medicare is asked (check_charge alone sees no carrier and asks nothing) and the day on its record blocks the charge",
      lambda: RJ.vendor == ["7111"] and kind(RJ, "BLOCKED") == ["BLOCKED: pat7111 visit 9111 charge 5111 DOS %s code 99232 - %s" % (iso(DOS_A), BLOCK)] and RJ.code == 3 and leaks(RJ.out + RJ.raw) == [],
      lambda: (RJ.code, RJ.lines, RJ.vendor))
check("10o after every start with the real guard the stand-in's own resave.detail is back in its place", lambda: resave.detail is _detail)

# ---- 10x. what a run compares with its own listing, and when the helper is started (review fix of 11/25/2026) ---------------------------------
# The texts first told a run to compare the number of charges CHECKED with its own listing of Charge Review and, when the two differ, not to
# rely on the helper but to ask the guard itself. Every answer with a NOT CHECKED charge tripped that rule - the helper working as designed -
# and the guard call the texts name for a run's own check passes the very charge the helper would not clear (10x3). And the texts said only
# "before approvecharges", while the step's two gates save before that - with full-visit saves that carry approval 1 (10x5).
# 10x3 and 10x4 show what the texts say of deceased_guard.check_charge with the guard AS IT IS (it raises nothing when it has nothing to
# compare; it goes by the plan element at the sequence it is given and by the procedure's id). A guard that raises or blocks there instead
# makes those sentences of the texts out of date, not the rules: change the sentences and these two checks together.
def step1(text):
    """the Charge Review step of a live prompt: the line that starts '1. CHARGE REVIEW:'"""
    return next((l for l in text.splitlines() if l.startswith("1. CHARGE REVIEW:")), "")
def said_number(text):
    """which number of the helper's summary line a live prompt tells a run to compare with its own listing: the word behind 'says it'"""
    m = re.search(r"the number of charges its summary line says it (\w+)", step1(text)); return m.group(1).lower() if m else "(the step names none)"
def numbers(r):
    """the numbers of a start's summary line, by their names; {} for a start that ended without one"""
    m = re.match(r"DEATH CHECK - Charge Review: (\d+) charge\(s\) on \d+ visit\(s\) listed, (\d+) checked; .*; (\d+) could not be checked; \d+ unverified - register ", r.lines[-1]) if r.lines else None
    return {"listed": int(m.group(1)), "checked": int(m.group(2)), "could not be checked": int(m.group(3))} if m else {}
def about_a_charge(r):
    """the NOT CHECKED lines of a start that are about a charge - every one but the line about a visit the listing shows without any charge"""
    return [l for l in kind(r, "NOT CHECKED") if "(no charge listed under this visit)" not in l]
def own_call(f):
    """A guard call of a run's OWN (the calls the texts name for it), made here with the stand-ins in place as run() puts them -> what the
    guard answered, or the error it raised."""
    had = {n: sys.modules.get(n) for n in STANDINS}
    try:
        sys.modules.update(STANDINS); STRICT[0] = False
        try: return f()
        except Exception as e: return e
    finally:
        STRICT[0] = True; sys.path[:] = _PATH
        for n, m in had.items():
            sys.modules.pop(n, None)
            if m is not None: sys.modules[n] = m
PROMPTS = {n: _read("nightly/live/" + n) for n in ("columns.txt", "billing_button.txt")}
RK = RG; A_CHARGE = A_CHECK = V_CHARGE = V_CHECK = None
if DG is not None:
    shutil.rmtree(os.path.dirname(DCACHE), True); del DG.LOG[:]
    one("5112", "1", [], order_list=[("1", "car6085")], proc="pcode65089", code="99232", pid="7112", vid="9112")
    STATE["charts"] = {}; STATE["medicare"] = {"7112": GONE}      # while the helper runs the chart cannot be read: the guard raises
    RK = run(guard=DG)
    STATE["charts"] = {"7112": [("car6085", MBI_S)]}              # ... and when the run then asks the guard itself, it can
    _v, _c = len(VENDOR), len(CALLS); A_CHARGE = own_call(lambda: DG.check_charge("5112", 1)); V_CHARGE = (VENDOR[_v:], [c[:2] for c in CALLS[_c:] if c[0] in ("post", "elig")])
    _v = len(VENDOR); A_CHECK = own_call(lambda: DG.check("7112", iso(DOS_A), "car6085", "99232")); V_CHECK = VENDOR[_v:]
A_FAULT = A_CCM = A_CCM2 = V_FAULT = V_CCM = V_CCM2 = None
if DG is not None:
    shutil.rmtree(os.path.dirname(DCACHE), True); del DG.LOG[:]
    STATE["details"]["5113"] = FAULT_X                             # a charge whose own detail is a Fault: no chart, no date of service in it
    _v, _c = len(VENDOR), len(CALLS); A_FAULT = own_call(lambda: DG.check_charge("5113", 1)); V_FAULT = (VENDOR[_v:], [c[:2] for c in CALLS[_c:] if c[0] in ("post", "elig")])
    one("5114", "1", [(1, "car6404")], proc="pcode555555", code="99490", pid="7114", vid="9114")      # a care-management code under a procedure id the guard's list does not hold
    STATE["charts"] = {"7114": [("car6404", MEM_S)]}; STATE["medicare"] = {"7114": GONE2}
    _v, _c = len(VENDOR), len(CALLS); A_CCM = own_call(lambda: DG.check_charge("5114", 1)); V_CCM = (VENDOR[_v:], [c[:2] for c in CALLS[_c:] if c[0] in ("post", "elig")])
    _v = len(VENDOR); A_CCM2 = own_call(lambda: DG.check("7114", iso(DOS_A), "car6404", "99490")); V_CCM2 = VENDOR[_v:]
scene(FOUR); GO1 = scripted({"5003": True}); RO1 = run(guard=GO1)                                  # the helper FIRST: the visit of charge 5003 is still waiting in Charge Review
scene([v for v in FOUR if v[0] != "9002"]); GO2 = scripted({"5003": True}); RO2 = run(guard=GO2)    # the helper AFTER a gate's save (a full-visit save that carries approval 1): that visit has left Charge Review
WITH_LINE = [r for r in STARTS if numbers(r) and r.own is not None]
def not_the_listing():
    """every start in which the number a live prompt names is NOT what the run's own listing of Charge Review holds"""
    return [(n, "the step says: " + said_number(t), numbers(r).get(said_number(t)), "the run's own listing: %d" % r.own, r.lines[-1][:92]) for n, t in sorted(PROMPTS.items()) for r in WITH_LINE if numbers(r).get(said_number(t)) != r.own]
check("10x1 the number the two live prompts tell a run to compare with its own listing of Charge Review IS, in every start of this self-test that ended with a summary line, the number of charges that listing holds - also in the starts with a NOT CHECKED charge. (Review fix of 11/25/2026: the texts first named the number CHECKED - it is smaller by every NOT CHECKED charge, so every such answer told the run that the helper 'has checked nothing'.)",
      lambda: len(WITH_LINE) >= 50 and sum(1 for r in WITH_LINE if about_a_charge(r)) >= 8 and not_the_listing() == [], lambda: (len(WITH_LINE), sum(1 for r in WITH_LINE if about_a_charge(r)), not_the_listing()[:2]))
check("10x2 in every such start the charges checked and the NOT CHECKED lines about a charge add up to the charges listed, and 'could not be checked' counts every NOT CHECKED line (a visit shown without a charge has one too - it is no charge and is not listed as one): the number checked is smaller than the number listed exactly when a charge is NOT CHECKED - the helper working as designed, never a sign that it missed a charge",
      lambda: len(WITH_LINE) >= 50 and all(numbers(r)["checked"] + len(about_a_charge(r)) == numbers(r)["listed"] and numbers(r)["could not be checked"] == len(kind(r, "NOT CHECKED"))
                                          and (numbers(r)["checked"] < numbers(r)["listed"]) == bool(about_a_charge(r)) for r in WITH_LINE),
      lambda: [(numbers(r), kind(r, "NOT CHECKED")) for r in WITH_LINE if numbers(r)["checked"] + len(about_a_charge(r)) != numbers(r)["listed"] or numbers(r)["could not be checked"] != len(kind(r, "NOT CHECKED"))][:3])
check("10x3 with the REAL guard, WHY a NOT CHECKED charge stays unapproved whatever a guard call of the run's own answers: a straight-Medicare charge (its carrier on the insurance-order list's row only) that the helper could not check - the guard raised on the chart read - is asked about again with the two calls the texts name for a run's own check, the chart readable by then. check_charge(<charge id>, <first number of the visit's insorder>) does not block it and asks Medicare nothing; check(<chart>, <date of service>, <the carrier the claim goes to first>, <the code>) asks Medicare and blocks it",
      lambda: kind(RK, "NOT CHECKED") == ["NOT CHECKED: pat7112 visit 9112 charge 5112 (the guard raised KeyError) - %s" % UNCHECKED] and RK.code == 3 and numbers(RK) == {"listed": 1, "checked": 0, "could not be checked": 1}
      and isinstance(A_CHARGE, tuple) and A_CHARGE[0] is False and V_CHARGE == ([], []) and isinstance(A_CHECK, tuple) and A_CHECK[0] is True and V_CHECK == ["7112"] and leaks(RK.out + RK.raw) == [],
      lambda: (RK.code, RK.lines, type(A_CHARGE).__name__ if isinstance(A_CHARGE, Exception) else A_CHARGE, V_CHARGE, type(A_CHECK).__name__ if isinstance(A_CHECK, Exception) else (A_CHECK or [None])[0], V_CHECK))
check("10x4 with the REAL guard, the texts' other words about check_charge: on a charge whose own detail is a Fault (no chart, no date of service in it) it raises nothing, answers 'not blocked' and asks nothing - it had nothing to compare; and a care-management code (99490) on a plan that is not Medicare, under a procedure id the guard's list does not hold, it passes having asked Medicare nothing, where check(<chart>, <date of service>, <that carrier>, <the code>) asks Medicare and blocks",
      lambda: A_FAULT == (False, "") and V_FAULT == ([], []) and "99490" in DG.CCM and "pcode555555" not in DG.CCM and isinstance(A_CCM, tuple) and A_CCM[0] is False and V_CCM == ([], [])
      and isinstance(A_CCM2, tuple) and A_CCM2[0] is True and V_CCM2 == ["7114"],
      lambda: (type(A_FAULT).__name__ if isinstance(A_FAULT, Exception) else A_FAULT, V_FAULT, type(A_CCM).__name__ if isinstance(A_CCM, Exception) else (A_CCM or [None])[0], V_CCM,
               type(A_CCM2).__name__ if isinstance(A_CCM2, Exception) else (A_CCM2 or [None])[0], V_CCM2))
check("10x5 WHY the helper is started before ANY save of the step: it lists only what is still waiting in Charge Review. Started FIRST it blocks the charge of a patient who has passed away (exit 3, the BLOCKED line); started AFTER a gate's save has taken that visit out of Charge Review it cannot know of it - exit 0, every listed charge checked, no line and no guard call for that charge - and only the number LISTED, one less than the run's own listing from before the save, shows that a visit is missing",
      lambda: RO1.code == 3 and kind(RO1, "BLOCKED") == ["BLOCKED: pat7002 visit 9002 charge 5003 DOS %s code 99232 - %s" % (iso(DOS_B), BLOCK)] and RO1.own == 4 == numbers(RO1)["listed"]
      and RO2.code == 0 and [c[0] for c in GO2.calls] == ["5001", "5002", "5004"] and len(RO2.lines) == 1 and numbers(RO2) == {"listed": 3, "checked": 3, "could not be checked": 0} and numbers(RO2)["listed"] != RO1.own,
      lambda: (RO1.code, RO1.lines, RO2.code, RO2.lines, [c[0] for c in GO2.calls]))

# ---- 10y. one start, one chart, two charges: the answer must not depend on which charge is listed first (11/25/2026, the integration) ---------
# Found by the review's fixer and left open: an ordinary visit on a plan that is not Medicare stands FIRST in the listing (the guard asks
# Medicare nothing for it and its cache knows no day yet - clear), then a care-management visit of the SAME chart (the guard asks and learns a
# day before both dates of service - blocked). The first charge came out clear, with no line. Now every charge that came out clear is put to
# the guard's cache once more at the end of the start (nothing is asked, nothing is bought): a day learned later in the start blocks it too.
ORD_Y = ("5301", "pcode65142", "99349", "car6404", "car6113", DOS_B); CCM_Y = ("5302", "pcode492676", "99487", "car6404", "car6113", DOS_A)
def two_y(first, second):
    shutil.rmtree(os.path.dirname(DCACHE), True); scene([("9301", "7301", [first]), ("9302", "7301", [second])])
    STATE["charts"] = {"7301": [("car6404", MEM_S)]}; STATE["medicare"] = {"7301": GONE}; STATE["free"] = {}; del DG.LOG[:]
RY1 = RY2 = RY3 = RY4 = types.SimpleNamespace(code=None, out="", lines=[], reg=None, raw="", regs=[], ws="", calls=[], vendor=[], err="the real guard could not be loaded")
if DG is not None:
    two_y(ORD_Y, CCM_Y); TY0 = tally(); RY1 = run(guard=DG); TY1 = tally()
    two_y(CCM_Y, ORD_Y); RY2 = run(guard=DG)
    two_y(ORD_Y, ("5303", "pcode65142", "99349", "car6404", "car6113", DOS_A)); STATE["medicare"] = {}; RY3 = run(guard=DG)      # two ordinary visits, nothing on anybody's record: both clear, as before
    two_y(ORD_Y, CCM_Y); RY4 = run(("--dry",), guard=DG)                                                                          # --dry: nothing is asked, so no day is learned - nothing changes
Y_BLOCKED = sorted(["BLOCKED: pat7301 visit 9301 charge 5301 DOS %s code 99349 - %s" % (iso(DOS_B), BLOCK), "BLOCKED: pat7301 visit 9302 charge 5302 DOS %s code 99487 - %s" % (iso(DOS_A), BLOCK)])
check("10y1 two charges of ONE chart in one start, the ordinary visit listed FIRST and the care-management visit that brings the day from Medicare's record second: BOTH are BLOCKED (exit 3) - the first one too, by the day the start learned after it",
      lambda: RY1.code == 3 and sorted(kind(RY1, "BLOCKED")) == Y_BLOCKED and [x.get("result") for x in rows(RY1)] == ["BLOCKED", "BLOCKED"] and real_summary(RY1, 2, 2, 2, 1, 2, 0, 0), lambda: (RY1.code, RY1.err, RY1.lines, rows(RY1)))
check("10y2 ... the same two charges listed the other way round give the same answer, and the charge blocked at the end of the start is marked so in the register (blocked by a day learned later in this start)",
      lambda: RY2.code == 3 and sorted(kind(RY2, "BLOCKED")) == sorted(l.replace("visit 9301 charge 5301", "visit 9302 charge 5301").replace("visit 9302 charge 5302", "visit 9301 charge 5302") for l in Y_BLOCKED)
      and row(RY1, "5301").get("late") is True and "late" not in row(RY1, "5302") and "late" not in row(RY2, "5301"), lambda: (RY2.code, RY2.lines, rows(RY1), rows(RY2)))
check("10y3 ... the second look at the end asks nobody and buys nothing: the guard's own counts of that start are one charge's (the care-management one), and the summary line says exactly them",
      lambda: said(RY1, TY0, TY1) and (TY1 is None or sum(TY1[k] - TY0[k] for k in TY1) <= 2) and len(RY1.vendor) <= 1 and leaks(RY1.out + RY1.raw) == [], lambda: (TY0, TY1, RY1.vendor, RY1.lines[-1:]))
check("10y4 ... with nothing on anybody's record both charges stay clear with no line, and --dry (nothing asked, so no day learned) blocks nothing more than its cache knows",
      lambda: RY3.code == 0 and kind(RY3, "BLOCKED") == [] and [x.get("result") for x in rows(RY3)] == ["clear", "clear"] and not any("late" in x for x in rows(RY3))
      and RY4.code == 0 and kind(RY4, "BLOCKED") == [] and RY4.vendor == [], lambda: (RY3.code, RY3.lines, RY4.code, RY4.lines, RY4.vendor))

# ---- 10z. the guard's cache file is not there: said, at the top (11/25/2026, the integration; the review's finding on the cache) -----------------
# A guard that finds no cache file starts with nothing: a day the practice already holds is unknown to it until Medicare answers again, and
# for a charge that needs no Medicare answer (another plan, no care-management code) nothing is asked at all. The helper cannot know what a
# missing file would have held - it says that the file is missing, in ONE line that a run puts at the top of its report.
RZ1 = RZ2 = types.SimpleNamespace(code=None, out="", lines=[], reg=None, raw="", regs=[], ws="", calls=[], vendor=[], err="the real guard could not be loaded")
if DG is not None:
    two_y(ORD_Y, CCM_Y); STATE["medicare"] = {}; RZ1 = run(guard=DG)                      # the cache folder was removed by two_y: no cache file
    scene([("9301", "7301", [ORD_Y])]); STATE["medicare"] = {}; RZ2 = run(guard=DG)       # the start before wrote the cache (the care-management charge was answered): the file is there now
MISSING = "CACHE MISSING: the deceased guard's cache file is not there - the guard starts with NOTHING: a date of death the practice already holds is unknown to it until Medicare answers again, and a charge that needs no Medicare answer is not asked about at all - TOP OF THE REPORT"
check("10z1 the guard's cache file is not there at the start: ONE line says so for the top of the report (the first line the helper prints); the exit code and the summary line are what the charges themselves give, and the register keeps the line",
      lambda: RZ1.lines[:1] == [MISSING] and RZ1.code == 0 and real_summary(RZ1, 2, 2, 2, 1, 0, 0, 0) and (RZ1.reg or {}).get("cache_missing") is True and MISSING in ((RZ1.reg or {}).get("lines") or []), lambda: (RZ1.code, RZ1.err, RZ1.lines, (RZ1.reg or {}).get("cache_missing")))
check("10z2 ... with the cache file there no such line is printed, and a guard that names no cache file (an older guard, a stand-in) gets none either",
      lambda: not kind(RZ2, "CACHE MISSING") and (RZ2.reg or {}).get("cache_missing") is False and not kind(R5, "CACHE MISSING") and (R5.reg or {}).get("cache_missing") is False, lambda: (RZ2.lines, (RZ2.reg or {}).get("cache_missing"), R5.lines[:1]))

# ---- 11. the helper's own words, and the privacy gate ---------------------------------------------------------------------------------------------
def helper_text(): return _read(HELPER)
def header(src):
    out = []
    for l in src.splitlines():
        if not l.startswith("#"): break
        out.append(l.lstrip("# "))
    return " ".join(out)
def code_lines(src):
    """the helper's code alone: no comment line, no trailing comment, no docstring"""
    return "\n".join(l.split("  # ")[0] for l in re.sub(r'"""[\s\S]*?"""', '""', src).splitlines() if not l.lstrip().startswith("#"))
check("11a the helper keeps its PLAIN ENGLISH header: what it decides (nothing - the guard does), William's order of 11/25/2026 in his words, what it prints, what it writes, the three exit codes, and what it never does",
      lambda: helper_text().startswith("#!/usr/bin/env python3\n# PLAIN ENGLISH (") and all(x in header(helper_text()) for x in ("Decides:", "William", "11/25/2026", "verify date of death first", "READ-ONLY", "deceased_guard.check_charge", "EXIT: 0 =", "3 =", "2 =", "--dry", "Never")),
      lambda: header(helper_text())[:400])
HEAD_1125 = ("BEFORE approvecharges AND BEFORE ANY SAVE of a Charge Review visit", "WHEN A RUN STARTS IT", 'approval="1"', "recode._save", "dx_primary_fix.save_visit_dx", "gets no gate fix",
             "N - the charges LISTED, the line's first number - is the number a run compares with its own listing", "K is NOT that number")
check("11a2 (review fix of 11/25/2026) the header says WHEN a run starts the helper - before any save of a Charge Review visit, not only before approvecharges: the step's two gates fix a visit with a full-visit save that carries approval 1 and asks no guard, and a visit with a BLOCKED or NOT CHECKED charge gets no such fix - and WHICH number of the summary line a run compares with its own listing: N, the charges listed, never K, the charges checked",
      lambda: all(x in header(helper_text()) for x in HEAD_1125) and "K is the number a run compares" not in header(helper_text()) and "A run starts this helper BEFORE approvecharges." not in header(helper_text()),
      lambda: [x for x in HEAD_1125 if x not in header(helper_text())])
check("11b the helper's code builds ONE AdvancedMD message - the list call - and names no call that writes (approve, save, void, bill, bypass, release, payment)",
      lambda: re.findall(r'amd\.msg\(\s*"(\w+)"\s*,\s*"(\w+)"', code_lines(helper_text())) == [("getreviewcharges", "chargeentry")] and set(re.findall(r"\bamd\.(?!py\b)(\w+)", code_lines(helper_text()))) == {"login_cached", "post", "msg"}
      and set(re.findall(r"\bresave\.(?!py\b)(\w+)", code_lines(helper_text()))) == {"detail"}
      and not re.search(r"approvecharges|updvisit|bypassclaimedits|hideunbillable|hideexclusions|addpayments|rebill_charge|void_tx|chargerebill", code_lines(helper_text())), lambda: sorted(set(re.findall(r"\bamd\.(?!py\b)(\w+)", code_lines(helper_text())))))
M = None
try:
    M = types.ModuleType("death_check_review_under_test"); M.__file__ = os.path.join(ROOT, HELPER)
    exec(compile(_read(HELPER), M.__file__, "exec"), M.__dict__)      # the helper loaded as a module: it does nothing by itself (its AdvancedMD modules are loaded only when it is started)
except Exception: M = None
check("11b2 every value the helper takes from AdvancedMD's answers is kept only in the shape of what it is: an id as its digits, a date of service as a date (the forms the guard reads), a code as a code - a text is never passed on",
      lambda: (M.num("vst9001"), M.num("pat7001"), M.num(None)) == ("9001", "7001", "") and [M.day(x) for x in (mdy(DOS_A), mdy(DOS_A) + " 12:00:00 AM", iso(DOS_A), iso(DOS_A) + "T00:00:00", ymd(DOS_A), "%d/%d/%d" % (DOS_A.month, DOS_A.day, DOS_A.year))] == [iso(DOS_A)] * 6
      and [M.day(x) for x in (NAME_S, "", None, "soon", ymd(DOS_A) + "7")] == [""] * 5 and [M.code_of(x) for x in ("99487", "G0556", "pcode492676", "1123F")] == ["99487", "G0556", "pcode492676", "1123F"]
      and [M.code_of(x) for x in (NAME_S, "two words", "", None, "x" * 13)] == [""] * 5 and M.kind_of(RuntimeError(NAME_S)) == "RuntimeError", lambda: M)
check("11c the fixed words in the helper are the specification's, word for word", lambda: ('"%s"' % BLOCK) in helper_text() and ('"%s"' % UNCHECKED) in helper_text() and ('"%s"' % UNVERIFIED) in helper_text())
check("11d the helper used nothing of the scripted guards but check_charge, check, the guard's lists (LOG, CCM, MEDICARE, COUNTS) and the NAME of its cache file (CACHE - only to say when that file is missing: the helper never opens it) - it never reaches into the guard's cache or its look-up, and never changes the guard",
      lambda: len(GUARDS) > 20 and sum(len(g.calls) for g in GUARDS) > 40 and [[x for x in g.other if x != "CACHE"] for g in GUARDS if [x for x in g.other if x != "CACHE"]] == [] and set(re.findall(r"\bG\.(\w+)", code_lines(helper_text()))) == {"check_charge", "check"}
      and not re.search(r"open\(\s*cpath|json\.load", code_lines(helper_text())),
      lambda: (sum(len(g.calls) for g in GUARDS), [g.other for g in GUARDS if g.other][:3], sorted(set(re.findall(r"\bG\.(\w+)", code_lines(helper_text()))))))
check("11d2 the helper names no cache file and changes no environment variable: the guard takes the cache the run's environment gives it (DECEASED_CACHE, else its own default), exactly as it does for the code a run writes itself - and no cache file appears in the folder the helper is started in",
      lambda: len(code_lines(helper_text())) > 3000 and not re.search(r"environ|putenv|DECEASED_CACHE|deceased_cache", code_lines(helper_text())) and os.environ.get("DECEASED_CACHE") == DCACHE
      and WS_N[0] > 40 and [p for p in glob.glob(os.path.join(TMP, "ws*", "**"), recursive=True) if "cache" in os.path.basename(p)] == [],
      lambda: (re.findall(r"environ|putenv|DECEASED_CACHE|deceased_cache", code_lines(helper_text()))[:3], os.environ.get("DECEASED_CACHE") == DCACHE, [p for p in glob.glob(os.path.join(TMP, "ws*", "**"), recursive=True) if "cache" in os.path.basename(p)][:3]))
check("11e in this whole self-test nothing forbidden was sent to the stand-in AdvancedMD: every message was the list call or (the real guard's) chart read",
      lambda: len(CALLS) > 50 and [c for c in CALLS if c[0] == "FORBIDDEN"] == [] and {c[1] for c in CALLS if c[0] == "post"} <= {"getreviewcharges", "getdemographic"}, lambda: [c for c in CALLS if c[0] == "FORBIDDEN"][:5])
check("11f in this whole self-test no printed line and no register held a name, a birth date, a Medicare or member number, or the day a patient passed away",
      lambda: len(SEEN) > 50 and sum(len(s) for s in SEEN) > 5000 and [x for s in SEEN for x in leaks(s)] == [], lambda: sorted({x for s in SEEN for x in leaks(s)}))
GATE = None
try:
    GATE = types.ModuleType("phi_gate_under_test"); GATE.__file__ = os.path.join(ROOT, "tools", "mirror", "phi_gate.py")
    exec(compile(_read("tools/mirror/phi_gate.py"), GATE.__file__, "exec"), GATE.__dict__)      # the gate's text transform only: pure, no file, no network
except Exception: GATE = None
for rel in ("tools/selftest/test_death_check_review.py", HELPER):
    check("11g the privacy gate's tree rules leave %s exactly as it is (every invented value is put together at run time)" % rel,
          lambda rel=rel: GATE.redact(_read(rel), {}, code=True) == _read(rel), lambda rel=rel: [(a, b) for a, b in zip(_read(rel).splitlines(), GATE.redact(_read(rel), {}, code=True).splitlines()) if a != b][:2])
check("11h the gate also leaves alone every line the helper printed and every register it wrote here (a register that is mirrored reaches the repository as it was written)",
      lambda: len(SEEN) > 50 and sum(len(s) for s in SEEN) > 5000 and [s[:120] for s in SEEN if s and GATE.redact(s, {}, code=False) != s] == [], lambda: [[(a, b) for a, b in zip(s.splitlines(), GATE.redact(s, {}, code=False).splitlines()) if a != b][:1] for s in SEEN if s and GATE.redact(s, {}, code=False) != s][:3])
check("nothing was written in the checkout", lambda: _snapshot() == BEFORE, lambda: sorted(set(_snapshot().items()) ^ set(BEFORE.items()))[:5])
print("test_death_check_review: %d checks, %d failed%s" % (COUNT[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:300]))
sys.exit(1 if FAILS else 0)
