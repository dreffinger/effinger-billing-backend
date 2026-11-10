#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the Medicare-answer rules - look-ups part A, 11/10/2026)
# Decides: nothing. Loads the vendor client (scripts/helpers/stedi.py), the Medicare answer store (medicare_store.py), the deceased-
#   patient guard (deceased_guard.py), the nightly pre-claim check (precheck.py), the price table (stedi_prices.py), the usage reader
#   (stedi_usage.py) and the engine's cascade step (tools/button/run_all.py) INSIDE this process, from their files, with stand-in modules
#   for everything that talks to AdvancedMD or the vendor: a request counter answers every vendor request from a canned table. No network,
#   no AdvancedMD, no vendor, no patient data - every chart, name, number and date here is invented at run time. It proves:
#     - ONE Medicare answer (stedi.medicare): a well-shaped Medicare number on the chart -> one PLAIN check (payer id CMS, the cleaned
#       number, the group provider block, the date of service) and no look-up; 72/73/75/76/58 -> a generation suffix comes off and the
#       plain check goes once more, then ONE look-up whose answer is the result; no usable number -> the look-up; 42/79/80, a time-out or
#       an HTTP error -> nothing else is bought and nothing is stored as an answer; another refusal (41, 61, an empty answer) -> the
#       look-up and a report line; the SSN only when the caller gives one; med_summ reads both kinds of answer and a stored one;
#     - the answer store: one answer per chart and day shared by every helper, each reader's own age rule, an answer about an earlier
#       month never serves a later one, 'asked and failed today' stops a second purchase until the next day, no Medicare number, name or
#       birth date in the file, writes in one step, a store that is missing or broken is an empty one, git ignores patient_db/; hospice
#       only from a code-X line for service type 45 - the Part A line lists 45 for every beneficiary (step 3);
#     - the guard: a date of death learned from a PLAIN answer blocks exactly as one from a look-up; a plain 'not found', an empty reply
#       and a failed call are never kept as 'no death on record'; a failed call blocks nothing and is logged 'UNVERIFIED' as before; two
#       helpers asking about one chart on one day make ONE paid call; the 30 days count from the day Medicare was asked; the chart's own
#       Medicare number (open plan first) is used; the one cache file keeps what other helpers wrote; the block wording and LOG unchanged;
#     - the pre-claim check: the result words are unchanged, 'MBI MISMATCH' only on a look-up answer, no Medicare number in its files for
#       a plain answer, only answers about the visit's own month, --help / an unknown option / --dry make no vendor call; 10 charts asked
#       by three helpers cost 11 requests (9 plain, 2 look-ups) instead of 30 look-ups;
#     - the engine's cascade step no longer starts the pre-claim check and says why; the page texts say the same; the six-hourly run's
#       evening start is gone, so the nightly routine is the one scheduled start;
#     - one usage-log line per paid call (none for the free GET calls) with who / kind / payer / chart / code / first-tier price, and a log
#       that cannot be written never stops a call; the price table gives October's four statement amounts; the reader prices a month;
#     - the core/ copies are the scripts/helpers copies; nothing is written in the checkout.
# Run: python3 tools/selftest/test_lookup_rules.py   (exit 1 on any failure; the last line says how many checks ran and how many failed)
import os, sys, io, re, json, types, glob, time, shutil, atexit, argparse, datetime, tempfile, contextlib, subprocess, traceback
import importlib.abc, importlib.machinery
# THIS SELF-TEST NEVER REACHES ADVANCEDMD, THE VENDOR OR ANY OTHER HOST. Every network route is closed here, before anything else is
# loaded: scripts/helpers and core hold the REAL amd / resave / txh / void_tx / era_post / stedi / deceased_guard modules, and importing
# them would talk to the practice's billing system and the paid vendor. So: (1) the code under test is read from its file and run here
# with stand-in modules in sys.modules (load / run_main below); (2) any import that would come from the checkout and was not loaded that
# way is refused, as is the real `requests`; (3) the network is shut either way. The only programs started are `git check-ignore`.
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    """One check. cond may be a function: it is called here, and an error inside it is a failure (never a crash of the whole test)."""
    COUNT[0] += 1
    if callable(cond):
        try: cond = cond()
        except Exception as e: cond, extra = False, "raised %s: %s" % (type(e).__name__, e)
    print(("ok   " if cond else "FAIL ") + name + (("  -> " + str(extra)[:600]) if extra != "" and not cond else ""))
    if not cond: FAILS.append(name)
def _raises(f, exc=Exception):
    """True when f() raises exc."""
    try: f()
    except exc: return True
    except Exception: return False
    return False
def _try(f, instead="raised"):
    """f(), or `instead` when it raises (a check then fails on the value, it does not stop the group)."""
    try: return f()
    except Exception: return instead
def _read(rel):
    """Every file of the checkout this test reads - the code under test and the texts - is read here and nowhere else."""
    with open(os.path.join(ROOT, rel)) as fh: return fh.read()

# ---- the throwaway folder and the paths the code under test writes to (set BEFORE anything is loaded) ------------------------------
TMP = tempfile.mkdtemp(prefix="lookuprules_"); atexit.register(shutil.rmtree, TMP, True)
STORE = os.path.join(TMP, "patient_db", "medicare_answers.json"); ULOG = os.path.join(TMP, "patient_db", "stedi_usage.log"); DCACHE = os.path.join(TMP, "registers", "deceased_cache.json")
os.environ.update(MEDICARE_STORE=STORE, STEDI_USAGE_LOG=ULOG, DECEASED_CACHE=DCACHE)
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

# ---- invented people, charts and dates (built at run time: nothing here is a real person, number or date) --------------------------
TODAY = datetime.date.today()
def ymd(d): return d.strftime("%Y%m%d")
def mdy(d): return d.strftime("%m/%d/%Y")
def iso(d): return d.isoformat()
def ago(n): return TODAY - datetime.timedelta(days=n)
_LT = "ACDEFGHJKMNPQRTUVWXY"
def mnum(i):
    """An invented number of the Medicare shape, made at run time (no whole number is ever written in this file)."""
    return "%d%s%s%d%s%s%d%s%s%02d" % (1 + i % 9, _LT[i % 20], _LT[(i * 3 + 1) % 20], i % 10, _LT[(i * 7 + 2) % 20], _LT[(i * 11 + 3) % 20],
                                       (i * 3) % 10, _LT[(i * 13 + 4) % 20], _LT[(i * 17 + 5) % 20], i % 100)
def spaced(n): return n[:4] + "-" + n[4:7].lower() + " " + n[7:]      # the same number as a chart may hold it (dashes, a space, lower case)
def nm(last, first): return last + "," + first
PEOPLE = {}                     # the true Medicare record per person key
def person(key, first, last, birth, number, death=None, advantage=None, hospice=False, beneficiary=True):
    PEOPLE[key] = {"first": first, "last": last, "dob8": ymd(birth), "number": number, "death8": ymd(death) if death else None,
                   "advantage": advantage, "hospice": hospice, "beneficiary": beneficiary}
    return PEOPLE[key]
_K = [0]
def newp(death=None, advantage=None, hospice=False, beneficiary=True):
    """A new invented person with a unique name, birth date and number."""
    _K[0] += 1; k = _K[0]
    last = "ZZTEST" + "".join(chr(65 + int(c)) for c in "%03d" % k)
    return person("p%d" % k, "TESTER", last, datetime.date(1930 + k % 20, 1 + k % 12, 1 + k % 27), mnum(k), death, advantage, hospice, beneficiary)
WRONG = [mnum(i) for i in range(95, 100)]        # well-shaped numbers that belong to nobody (a chart holding one has a wrong number)
_C = [0]
def cid():
    """A new invented chart id."""
    _C[0] += 1; return "91%05d" % _C[0]
DESC = {"72": "Invalid/Missing Subscriber/Insured ID", "73": "Invalid/Missing Subscriber/Insured Name", "75": "Subscriber/Insured Not Found",
        "76": "Duplicate Subscriber/Insured ID Number", "58": "Invalid/Missing Date-of-Birth", "42": "Unable to Respond at Current Time",
        "79": "Invalid Participant Identification", "80": "No Response received - Transaction Terminated", "41": "Authorization/Access Restrictions",
        "61": "Date of Death Precedes Date(s) of Service"}
def err_answer(code, sub=None): return {"errors": [{"code": code, "description": DESC.get(code, "error")}], "subscriber": dict(sub or {}), "benefitsInformation": []}
def a271(p, member_echo, address=None):
    """A Medicare answer (271) for an invented person; member_echo is what the answer shows as the member number."""
    b = [{"code": "1", "name": "Active Coverage", "insuranceTypeCode": "MA", "insuranceType": "Medicare Part A", "benefitsDateInformation": {"plan": ymd(datetime.date(2015, 1, 1))}},
         {"code": "1", "name": "Active Coverage", "insuranceTypeCode": "MB", "insuranceType": "Medicare Part B", "benefitsDateInformation": {"plan": ymd(datetime.date(2015, 2, 1))}},
         {"code": "I", "name": "Non-Covered", "serviceTypeCodes": ["41", "54"]}]
    if p["advantage"]:
        b.append({"code": "U", "name": "Contact Following Entity for Eligibility or Benefit Information", "insuranceTypeCode": "HM", "insuranceType": "Health Maintenance Organization",
                  "planCoverage": "TEST ADVANTAGE PLAN", "benefitsDateInformation": {"plan": ymd(datetime.date(TODAY.year, 1, 1))},
                  "benefitsRelatedEntities": [{"entityName": p["advantage"][0], "entityIdentifierValue": p["advantage"][1]}]})
    if p["hospice"]:                                       # hospice may be an entity id of its own (True = 'HSP01')
        b.append({"code": "X", "name": "Health Care Facility", "insuranceTypeCode": "MA", "serviceTypeCodes": ["45"],
                  "benefitsRelatedEntities": [{"entityName": "TEST HOSPICE", "entityIdentifierValue": p["hospice"] if isinstance(p["hospice"], str) else "HSP" + "01"}]})
    pd = {"eligibility": ymd(datetime.date(2015, 1, 1))}
    if p["death8"]: pd["dateOfDeath"] = p["death8"]
    sub = {"memberId": member_echo, "firstName": p["first"], "lastName": p["last"], "dateOfBirth": p["dob8"]}
    if address: sub["address"] = address
    return {"subscriber": sub, "payer": {"name": "CMS"}, "planDateInformation": pd, "benefitsInformation": b, "errors": []}

# ---- stand-in requests: the request counter and the canned vendor ----------------------------------------------------------------
class FakeHTTPError(Exception):
    def __init__(self, status): super().__init__("HTTP %d from the stand-in" % status); self.response = types.SimpleNamespace(status_code=status)
class FakeTimeout(Exception): pass
class Resp:
    def __init__(self, status, body): self.status_code = status; self._body = body
    def raise_for_status(self):
        if self.status_code >= 400: raise FakeHTTPError(self.status_code)
    def json(self): return json.loads(json.dumps(self._body))
SENT = []                       # every vendor request since the last reset(): (url, body)
BILLING = []                    # every billing-system request of the stand-ins (unpaid list, chart record)
OVERRIDE = {}                   # (payer id, member number or last name) -> ("answer", body) / ("http", status) / ("timeout",) / ("raise",)
ON_SEND = []                    # callbacks run on every vendor request (a test can write a file meanwhile)
OTHER = {}                      # other payers: member number -> "active" / "inactive"
UNPAID = []                     # the unpaid list precheck reads
def _vendor(url, body):
    if "insurance-discovery" in url:
        return Resp(200, {"coveragesFound": 1, "items": [{"payer": {"name": "TEST MEDICAID"}, "payerId": "77027", "subscriber": {"memberId": "D" + "7" * 7},
                          "planDateInformation": {"plan": ymd(datetime.date(TODAY.year, 1, 1))}, "benefitsInformation": [{"code": "1", "name": "Active Coverage", "planCoverage": "TEST MMA"}], "confidence": "HIGH"}]})
    if "claimstatus" in url: return Resp(200, {"claims": [], "errors": []})
    payer = body.get("tradingPartnerServiceId"); sub = body.get("subscriber") or {}
    ov = OVERRIDE.get((payer, sub.get("memberId") or sub.get("lastName")))
    if ov:
        if ov[0] == "http": return Resp(ov[1], {"errors": [{"code": "79", "description": DESC["79"]}]})
        if ov[0] == "timeout": raise FakeTimeout("read timed out")
        if ov[0] == "raise": raise RuntimeError("connection reset")
        return Resp(200, ov[1])
    if payer == "CMS":
        p = next((p for p in PEOPLE.values() if p["number"] == sub.get("memberId")), None)
        if p is None or not p["beneficiary"]: return Resp(200, err_answer("72", {"memberId": sub.get("memberId")}))
        if sub.get("lastName") != p["last"]: return Resp(200, err_answer("73", {"memberId": sub.get("memberId")}))
        return Resp(200, a271(p, sub.get("memberId")))
    if payer in ("MBILUNOSSN", "MBILU"):
        p = next((p for p in PEOPLE.values() if (p["first"], p["last"], p["dob8"]) == (sub.get("firstName"), sub.get("lastName"), sub.get("dateOfBirth"))), None)
        if p is None or not p["beneficiary"]: return Resp(200, err_answer("72"))
        return Resp(200, a271(p, p["number"], address={"state": "FL"}))
    st = OTHER.get(sub.get("memberId"), "active")
    return Resp(200, {"planStatus": [{"statusCode": "1" if st == "active" else "6", "status": "Active Coverage" if st == "active" else "Inactive", "planDetails": "TEST PLAN"}],
                      "planDateInformation": {"plan": ymd(datetime.date(TODAY.year, 1, 1))}, "errors": []})
ERA_API = "https://billing-standin.invalid/api"
def _post(url, *a, **kw):
    body = kw.get("json") or {}
    if url.startswith(ERA_API): BILLING.append(url); return Resp(200, UNPAID)
    SENT.append((url, json.loads(json.dumps(body))))
    for f in list(ON_SEND): f(url, body)
    return _vendor(url, body)
GETS = []
def _get(url, *a, **kw): GETS.append(url); return Resp(200, {"items": []})
def standin(name, **attrs):
    m = types.ModuleType(name); m.STAND_IN = True
    for k, v in attrs.items(): setattr(m, k, v)
    return m
fake_requests = standin("requests", post=_post, get=_get, exceptions=types.SimpleNamespace(Timeout=FakeTimeout, HTTPError=FakeHTTPError))
RECORDED = []                   # what the client's date-of-death hook handed to the stand-in guard
fake_guard = standin("deceased_guard", record=lambda pid, j, src="stedi-medicare-271": RECORDED.append((str(pid), json.loads(json.dumps(j)))))
CHARTS = {}                     # the stand-in AdvancedMD: one chart record per invented chart id
LOGINS = []
def chart(pid, p=None, plans=(), deceased="", last=None):
    """plans: (carrier, end date MM/DD/YYYY or '', member number) per plan; p: the person the chart is about (None = a made-up one)."""
    p = p or {"first": "NOPLAN", "last": "ZZNOPLAN", "dob8": ymd(datetime.date(1940, 1, 2))}
    CHARTS[str(pid)] = {"name": nm(last or p["last"], p["first"]), "dob": p["dob8"][4:6] + "/" + p["dob8"][6:] + "/" + p["dob8"][:4], "deceased": deceased, "plans": list(plans)}
    return str(pid)
def _chart_xml(pid):
    c = CHARTS[str(pid)]
    plans = "".join('<insplan id="ins%d" carrier="%s" begindate="%s" enddate="%s" x="" subscribernum="%s" y="" sequence="%d"/>' % (i + 1, car, mdy(datetime.date(2015, 1, 1)), end, num, i + 1)
                    for i, (car, end, num) in enumerate(c["plans"]))
    return '<r><patient name="%s" dob="%s" deceased="%s" state="FL"/>%s</r>' % (c["name"], c["dob"], c["deceased"], plans)
def _amd_post(body, timeout=0):
    pid = re.search(r'patientid="(?:pat)?(\d+)"', body).group(1); BILLING.append("getdemographic " + pid); return _chart_xml(pid)
fake_amd = standin("amd", post=_amd_post, msg=lambda action, cls, attrs=None, children="": '<ppmdmsg action="%s" class="%s" %s/>' % (action, cls, " ".join('%s="%s"' % kv for kv in (attrs or {}).items())),
                   _msgtime=lambda: "t", login_cached=lambda: LOGINS.append(1))
fake_era = standin("era_post", API=ERA_API, H=lambda: {"Content-Type": "application/json"})
RESAVE = {}
fake_resave = standin("resave", detail=lambda cid_: RESAVE[str(cid_)])
sys.modules.update({"requests": fake_requests, "amd": fake_amd, "era_post": fake_era, "resave": fake_resave, "deceased_guard": fake_guard})

# ---- loading the code under test from its file (never by import) ----------------------------------------------------------------
def imports(src):
    """The first names of every module a piece of Python imports (import a.b as c / from a import b -> a)."""
    out = set()
    for kind, rest in re.findall(r"^[ \t]*(import|from)[ \t]+([^\n#]+)", src, re.M):
        for n in (rest.split(",") if kind == "import" else [rest]):
            n = n.strip().split()[0].split(".")[0] if n.strip() else ""
            if n: out.add(n)
    return out
def _ready(n):
    m = sys.modules.get(n); return m is not None and (getattr(m, "STAND_IN", False) or getattr(m, "UNDER_TEST", False))
def _source(rel):
    path = os.path.join(ROOT, rel); src = _read(rel)
    missing = sorted(n for n in imports(src) & LIVE if not _ready(n))
    if missing: raise RuntimeError("no stand-in for %s - %s is not run" % (missing, rel))
    return path, src
def load(rel, name):
    """Load ONE file of the checkout as code under test, as module `name`, with the stand-ins in place."""
    path, src = _source(rel)
    m = types.ModuleType(name); m.__file__ = path; m.UNDER_TEST = True
    exec(compile(src, path, "exec"), m.__dict__)
    return m
def run_main(rel, argv, cwd):
    """Run ONE file of the checkout as a program INSIDE this process (its imports are the stand-ins / modules loaded here)."""
    path, src = _source(rel)
    old_cwd, old_argv, old_sleep = os.getcwd(), list(sys.argv), time.sleep
    out, err, code = io.StringIO(), io.StringIO(), 0
    try:
        os.chdir(cwd); sys.argv = [path] + list(argv); time.sleep = lambda *_a: None
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try: exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path})
            except SystemExit as e: code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    finally:
        os.chdir(old_cwd); sys.argv = old_argv; time.sleep = old_sleep
    return code, out.getvalue(), err.getvalue()

# ---- 0. the safety block holds ------------------------------------------------------------------------------------------------
_refused = False
try: load("scripts/helpers/precheck.py", "precheck_without_standins")
except RuntimeError as e: _refused = "stedi" in str(e)
check("safety: code under test is not run until every live module it loads has a stand-in or was loaded here (precheck before the client is refused)", _refused)
check("safety: the real `requests`, a live helper and any module of the checkout are refused by the import blocker",
      lambda: _raises(lambda: _Refuse().find_spec("requests"), ImportError) and _raises(lambda: _Refuse().find_spec("amd"), ImportError)
      and _raises(lambda: _Refuse().find_spec("test_board_ops", [os.path.join(ROOT, "tools", "selftest")]), ImportError))
check("safety: the network is shut in this process", lambda: _raises(lambda: _socket.create_connection(("127.0.0.1", 9)), RuntimeError))

PR = load("scripts/helpers/stedi_prices.py", "stedi_prices"); sys.modules["stedi_prices"] = PR
MS = load("scripts/helpers/medicare_store.py", "medicare_store"); sys.modules["medicare_store"] = MS
ST = load("scripts/helpers/stedi.py", "stedi"); sys.modules["stedi"] = ST
ST_FIRST_WHO = ST.WHO
US = load("scripts/helpers/stedi_usage.py", "stedi_usage")
PRACTICE = json.loads(_read("practices/ehpa/practice.json"))
DG = None                       # the real guard, loaded with stand-ins for the guard tests (section 4)
def reset():
    del SENT[:]; del BILLING[:]; del RECORDED[:]; del LOGINS[:]; del GETS[:]; OVERRIDE.clear(); OTHER.clear(); del ON_SEND[:]; del UNPAID[:]; del ST.NOTES[:]
    for p in (STORE, ULOG, DCACHE):
        if os.path.isdir(p): shutil.rmtree(p)
        elif os.path.exists(p): os.remove(p)
    ST.WHO = "test_lookup_rules.py"
    if DG is not None: del DG.LOG[:]; DG._ASKED.clear()
def kinds(): return [b.get("tradingPartnerServiceId") or ("discovery" if "discovery" in u else "?") for u, b in SENT]
def ask(*a, **k):
    err = io.StringIO()
    with contextlib.redirect_stderr(err): j, how = ST.medicare(*a, **k)
    return j, how, err.getvalue()
def askp(p, number="same", **k):
    """stedi.medicare for an invented person (number='same' = the person's own number on the chart)."""
    return ask(p["first"], k.pop("last", p["last"]), p["dob8"], member_id=p["number"] if number == "same" else number, **k)
def store_json():
    try:
        with open(STORE) as fh: return json.load(fh)
    except Exception: return None
def store_chart(pid): return ((store_json() or {}).get("charts") or {}).get(str(pid)) or {}
def store_edit(fn):
    d = store_json(); fn(d)
    with open(STORE, "w") as fh: json.dump(d, fh)
def cache_json():
    try:
        with open(DCACHE) as fh: return json.load(fh)
    except Exception: return None
def log_lines():
    try:
        with open(ULOG) as fh: return [l.split("\t") for l in fh.read().splitlines() if l.strip()]
    except OSError: return []
def text_of(path):
    try:
        with open(path, errors="replace") as fh: return fh.read()
    except OSError: return ""
def first_of_month(d): return d.replace(day=1)
def next_month(d): return (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
def prev_month(d): return (d.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)

# ==== 1. the price table and the usage reader =================================================================================
def t_prices():
    check("prices: October claim status 6,770 = $889.50; 1,300 = $232.50; 400 = $97.50 (the claim-status reader's figures)",
          lambda: (PR.price("claim status", 6770), PR.price("claim status", 1300), PR.price("claim status", 400)) == (889.50, 232.50, 97.50))
    check("prices: October look-ups 986 without SSN + 78 with SSN, each on its own ladder = $783.50",
          lambda: (PR.price("look-up without SSN", 986), PR.price("look-up with SSN", 78), round(PR.price("look-up without SSN", 986) + PR.price("look-up with SSN", 78), 2)) == (705.50, 78.00, 783.50))
    check("prices: October discovery 187 = $237.00 and eligibility 505 = $113.25", lambda: (PR.price("discovery", 187), PR.price("eligibility", 505)) == (237.00, 113.25))
    check("prices: a plain Medicare check is billed as an eligibility check (one ladder: $0.30, then $0.15 after the 250th)",
          lambda: PR.ladder_of("plain Medicare") == "eligibility" and PR.first_tier("plain Medicare") == 0.30 and PR.price("plain Medicare", 10, before=250) == PR.price("eligibility", 10, before=250) == 1.50
          and PR.price("eligibility", 10, before=245) == 2.25)
    check("prices: the tiers at their edges (100 / 750 / 1,250 look-ups and searches; 250 / 3,500 / 10,000 checks) and the breakdown text",
          lambda: PR.price("look-up without SSN", 100) == 100.0 and PR.price("look-up without SSN", 101) == 100.75 and abs(PR.price("look-up without SSN", 1251) - 837.90) < 0.005
          and abs(PR.price("eligibility", 10001) - 1212.58) < 0.005 and PR.breakdown("discovery", 187) == "100 x $1.50 + 87 x $1.00" and PR.price("discovery", 1, before=100) == 1.00
          and abs(PR.price("discovery", 1251) - (150 + 650 + 375 + 0.65)) < 0.005)
    check("prices: first-tier price per kind ($0.30 eligibility / plain Medicare / claim status, $1.00 each look-up, $1.50 discovery); an unknown kind is refused",
          lambda: [PR.first_tier(k) for k in PR.KINDS] == [0.30, 0.30, 1.00, 1.00, 1.50, 0.30] and _raises(lambda: PR.price("phone call", 1), KeyError))

def t_usage_reader():
    month = TODAY.strftime("%Y-%m"); other = prev_month(TODAY).strftime("%Y-%m")
    lines = []
    def add(n, who, kind, payer, code="ok", mon=month, chart="9188801"):
        for i in range(n): lines.append("\t".join((mon + "-01T05:%02d:00Z" % (i % 60), who, kind, payer, chart, code, "%.2f" % PR.first_tier(kind))))
    add(90, "guard", "look-up without SSN", "MBILUNOSSN"); add(20, "hold fixer", "look-up with SSN", "MBILU"); add(5, "guard", "plain Medicare", "CMS")
    add(3, "pre-claim check", "eligibility", "87726"); add(1, "feed check", "discovery", "-"); add(2, "guard", "plain Medicare", "CMS", code="http 503")
    add(4, "guard", "plain Medicare", "CMS", mon=other)
    path = os.path.join(TMP, "usage_reader.log")
    with open(path, "w") as fh: fh.write("\n".join(lines) + "\nnot a log line\n")
    rep = US.month_report(US.read(path), month)
    check("usage reader: a month's calls are counted by kind and helper, other months and HTTP errors apart (119 calls, 2 HTTP errors)",
          lambda: rep["calls"] == 119 and rep["http_errors"] == 2 and rep["kinds"]["look-up without SSN"]["calls"] == 90 and rep["kinds"]["plain Medicare"]["calls"] == 5, rep)
    check("usage reader: each look-up kind is priced on its OWN ladder (90 + 20 = $110.00, not $107.50) and plain Medicare shares the eligibility ladder; month $113.90",
          lambda: rep["ladders"]["look-up without SSN"]["dollars"] == 90.0 and rep["ladders"]["look-up with SSN"]["dollars"] == 20.0 and rep["ladders"]["eligibility"]["calls"] == 8
          and rep["ladders"]["eligibility"]["dollars"] == 2.40 and rep["dollars"] == 113.90, rep)
    check("usage reader: by helper - guard $91.50, hold fixer $20.00, pre-claim check $0.90, feed check $1.50",
          lambda: {w: v["dollars"] for w, v in rep["helpers"].items()} == {"guard": 91.50, "hold fixer": 20.00, "pre-claim check": 0.90, "feed check": 1.50}, rep.get("helpers"))
    units = {"claim status": 6770, "look-up without SSN": 986, "look-up with SSN": 78, "discovery": 187, "eligibility": 505}
    ur = US.units_report(units)
    check("usage reader: October's statement units give $889.50, $705.50 + $78.00 = $783.50, $237.00 and $113.25",
          lambda: [ur[k][0] for k in units] == [889.50, 705.50, 78.00, 237.00, 113.25], ur)
    out = io.StringIO()
    with contextlib.redirect_stdout(out): rc1 = US.main(["--units", ",".join("%s=%d" % kv for kv in units.items())]); rc2 = US.main([month, "--log", path])
    o = out.getvalue()
    check("usage reader: the printed report shows the statement amounts and a month by helper, and never a chart id",
          lambda: rc1 == 0 and rc2 == 0 and all(x in o for x in ("889.50", "705.50", "78.00", "237.00", "113.25", "by helper", "hold fixer")) and "9188801" not in o, o[-800:])

# ==== 2. the vendor client alone (stand-in guard) =============================================================================
def t_shape():
    good = [mnum(i) for i in range(1, 60)]
    check("client: invented numbers of the Medicare shape are accepted, cleaned of spaces and dashes and upper-cased",
          lambda: all(ST.medicare_number(x) == x for x in good) and ST.medicare_number(spaced(good[3])) == good[3] and ST.medicare_number(" " + good[4].lower() + " ") == good[4])
    n = good[6]; bad = [n[:10], n + "1", "0" + n[1:], None, "", "".join(str(i) for i in range(1, 10)) + "A", "XQ" + "4" * 8]
    for pos in (1, 2, 4, 5, 7, 8):
        for letter in "SLOIBZ": bad.append(n[:pos] + letter + n[pos + 1:])
    for pos in (1, 4, 7, 8): bad.append(n[:pos] + "5" + n[pos + 1:])      # a digit where a letter must be
    for pos in (0, 3, 6, 9, 10): bad.append(n[:pos] + "K" + n[pos + 1:])  # a letter where a digit must be
    check("client: anything else on the chart (wrong length, S L O I B Z, a digit or letter out of place, an old number, a plan's member id) is not a Medicare number",
          lambda: [x for x in bad if ST.medicare_number(x) is not None] == [], [x for x in bad if ST.medicare_number(x) is not None])

def t_plain_good():
    reset(); p = newp(); pid = cid(); dos = ago(2)
    j, how, err = askp(p, number=spaced(p["number"]), dos=ymd(dos), pid=pid, who="test caller")
    u, b = SENT[0] if SENT else ("", {})
    check("client: a well-shaped number on the chart -> exactly ONE request: a PLAIN check (payer id CMS) with the cleaned number, the group provider block and the date of service; no look-up",
          lambda: how == "plain" and len(SENT) == 1 and b["tradingPartnerServiceId"] == "CMS" and b["subscriber"]["memberId"] == p["number"] and b["provider"] == ST.PROV
          and b["encounter"]["dateOfService"] == ymd(dos) and u.endswith("/change/medicalnetwork/eligibility/v3"), (how, SENT))
    check("client: the group provider block is the group's number - the one enrolled at the vendor (practice.json group_npi = stedi.enrolled_npi)",
          lambda: ST.PROV["npi"] == str(PRACTICE["group_npi"]) == str(PRACTICE["stedi"]["enrolled_npi"]))
    check("client: the plain answer is the result and the date-of-death hook got it (chart id given)", lambda: j["benefitsInformation"] and RECORDED == [(pid, j)], RECORDED)
    s = store_chart(pid).get("answers") or [{}]
    check("client: the answer is written to the store once - day asked, date of service, how, who - with no Medicare number, name or birth date",
          lambda: len(s) == 1 and s[0]["asked"] == iso(TODAY) and s[0]["dos"] == ymd(dos) and s[0]["how"] == "plain" and s[0]["who"] == "test caller" and s[0]["active"] is True
          and not any(x in text_of(STORE) for x in (p["number"], p["last"], p["dob8"])), s)
    reset(); j, how, err = askp(p, dos=ymd(dos))
    check("client: without a chart id the hook records nothing and nothing is stored (the store is per chart)", lambda: how == "plain" and RECORDED == [] and store_json() is None)

def t_not_found():
    res = []
    for code in ("72", "73", "75", "76", "58"):
        reset(); p = newp(); pid = cid()
        OVERRIDE[("CMS", p["number"])] = ("answer", err_answer(code, {"memberId": p["number"]}))
        j, how, err = askp(p, dos=ymd(ago(3)), pid=pid)
        look = SENT[1][1] if len(SENT) > 1 else {}
        res.append((code, kinds(), how, (j.get("subscriber") or {}).get("memberId") == p["number"] and not j.get("errors"), [x[1].get("errors") for x in RECORDED],
                    (store_chart(pid).get("answers") or [{}])[0].get("how"), look.get("subscriber", {}).get("address"), "ssn" in look.get("subscriber", {}), (look.get("encounter") or {}).get("dateOfService")))
    check("client: Medicare says not found (72, 73, 75, 76, 58) -> exactly ONE look-up after the plain check, and the look-up's answer is the result",
          lambda: all(r[1] == ["CMS", "MBILUNOSSN"] and r[2] == "lookup after plain" and r[3] for r in res), res)
    check("client: a plain 'not found' is never the result and never reaches the date-of-death hook or the store as an answer (only the look-up's answer does)",
          lambda: all(r[4] == [[]] and r[5] == "lookup after plain" for r in res), res)
    check("client: that look-up goes by name, birth date and state FL with the date of service - no SSN fetched or sent",
          lambda: all(r[6] == {"state": "FL"} and r[7] is False and r[8] == ymd(ago(3)) for r in res), res)

def t_wrong_number():
    reset(); p = newp(); pid = cid()
    j, how, err = askp(p, number=WRONG[0], dos=ymd(ago(1)), pid=pid)
    f = ST.medicare_facts(j, how, WRONG[0]); s = (store_chart(pid).get("answers") or [{}])[0]
    check("client: a wrong (well-shaped) number -> plain 72, then the look-up finds Medicare's own number; only a look-up can say the numbers differ",
          lambda: kinds() == ["CMS", "MBILUNOSSN"] and how == "lookup after plain" and j["subscriber"]["memberId"] == p["number"] and f["number_differs"] is True and s["number_differs"] is True, (kinds(), how, f))
    reset(); j2, how2, _ = askp(p, dos=ymd(ago(1)), pid=pid)
    check("client: a plain answer only echoes the number sent - it never says the chart's number differs (LOOKUP_KINDS has no 'plain')",
          lambda: how2 == "plain" and ST.medicare_facts(j2, how2, ST.medicare_number(spaced(p["number"])))["number_differs"] is None and "plain" not in ST.LOOKUP_KINDS
          and (store_chart(pid).get("answers") or [{}])[0].get("number_differs") is None)

def t_suffix():
    res = []
    for form in ("%s JR", "%s, JR.", "%s III", "%s IV", "%s SR.", "%s II", "%s,JR", "%s jr"):
        reset(); p = newp()
        j, how, err = askp(p, last=form % p["last"], dos=ymd(ago(1)), pid=cid())
        res.append((form, kinds(), how, SENT[1][1]["subscriber"]["lastName"] if len(SENT) > 1 else None, p["last"]))
    check("client: a generation suffix on the chart (JR, SR, II, III, IV, with or without a comma or full stop) -> the plain check goes ONCE more without it, no look-up",
          lambda: all(r[1] == ["CMS", "CMS"] and r[2] == "plain" and r[3] == r[4] for r in res), res)
    reset(); p = newp(); j, how, err = askp(p, last=p["last"] + "X", dos=ymd(ago(1))); k1 = kinds()
    reset(); q = newp(); j2, how2, _ = askp(q, last=q["last"] + "IV", dos=ymd(ago(1)))
    check("client: no suffix (or letters that only look like one, with no space or comma before them) -> no second plain check, straight to the look-up",
          lambda: k1 == kinds() == ["CMS", "MBILUNOSSN"] and how == how2 == "lookup after plain", (k1, kinds()))
    reset(); p = newp(); j, how, err = askp(p, number=WRONG[1], last=p["last"] + " JR", dos=ymd(ago(1)))
    check("client: suffix and still not found -> exactly two plain checks and ONE look-up (by the name without the suffix), whose answer is the result",
          lambda: kinds() == ["CMS", "CMS", "MBILUNOSSN"] and SENT[2][1]["subscriber"]["lastName"] == p["last"] and how == "lookup after plain" and j["subscriber"]["memberId"] == p["number"], kinds())

def t_no_number():
    res = []
    for number in (None, "", "".join(str(i) for i in range(1, 10)) + "A", "XQ" + "3" * 9, WRONG[2][:10]):
        reset(); p = newp(); j, how, err = askp(p, number=number, dos=ymd(ago(4)), pid=cid())
        b = SENT[0][1] if SENT else {}
        res.append((number, kinds(), how, b.get("provider") == ST.PROV, (b.get("encounter") or {}).get("dateOfService"), b.get("subscriber", {}).get("address")))
    check("client: no usable Medicare number on the chart (none, an old number, a plan's member id, a short one) -> the look-up as before, no plain check",
          lambda: all(r[1] == ["MBILUNOSSN"] and r[2] == "lookup" and r[3] and r[4] == ymd(ago(4)) and r[5] == {"state": "FL"} for r in res), res)

def t_down():
    res = []
    for code in ("42", "79", "80"):
        reset(); p = newp(); pid = cid(); OVERRIDE[("CMS", p["number"])] = ("answer", err_answer(code, {"memberId": p["number"]}))
        j, how, err = askp(p, dos=ymd(ago(1)), pid=pid); c = store_chart(pid)
        res.append((code, kinds(), how, c.get("answers"), (c.get("failed") or {}).get("day"), RECORDED))
    check("client: Medicare or the vendor down (42, 79, 80) -> no second call of another kind; how = 'failed'; nothing stored as an answer, only 'asked and failed today'",
          lambda: all(r[1] == ["CMS"] and r[2] == "failed" and not r[3] and r[4] == iso(TODAY) and r[5] == [] for r in res), res)
    res = []
    for ov, word in ((("timeout",), "time-out"), (("http", 503), "http 503"), (("raise",), "error RuntimeError")):
        reset(); p = newp(); pid = cid(); OVERRIDE[("CMS", p["number"])] = ov
        j, how, err = askp(p, dos=ymd(ago(1)), pid=pid); c = store_chart(pid)
        res.append((word, kinds(), how, j.get("failed"), c.get("answers"), (c.get("failed") or {}).get("reason")))
    check("client: a time-out, an HTTP error or a broken connection on the plain check -> 'failed', ONE request, nothing else bought or stored as an answer",
          lambda: all(r[1] == ["CMS"] and r[2] == "failed" and r[3] == r[0] and not r[4] and r[5] == r[0] for r in res), res)
    res = []
    for ov in (("answer", err_answer("42")), ("timeout",), ("http", 500)):
        reset(); p = newp(); pid = cid(); OVERRIDE[("MBILUNOSSN", p["last"])] = ov
        j, how, err = askp(p, number=None, dos=ymd(ago(1)), pid=pid)
        res.append((ov[0], kinds(), how, store_chart(pid).get("answers")))
    check("client: the look-up itself down (42, a time-out, an HTTP error) -> 'failed', ONE request, no answer stored",
          lambda: all(r[1] == ["MBILUNOSSN"] and r[2] == "failed" and not r[3] for r in res), res)
    reset(); p = newp(); pid = cid(); OVERRIDE[("CMS", p["number"])] = ("timeout",)
    askp(p, dos=ymd(ago(1)), pid=pid, max_age_days=0); OVERRIDE.clear(); n1 = len(SENT)
    j, how, err = askp(p, dos=ymd(ago(1)), pid=pid, max_age_days=30)
    check("client: 'asked and failed today' stops a second purchase the same day by another caller (it gets 'failed', no request)", lambda: n1 == 1 and len(SENT) == 1 and how == "failed", (n1, len(SENT), how))
    store_edit(lambda d: d["charts"][pid]["failed"].update(day=iso(ago(1))))
    j, how, err = askp(p, dos=ymd(ago(1)), pid=pid, max_age_days=30)
    check("client: the next day the failing chart is asked again (one plain check, a real answer now)", lambda: len(SENT) == 2 and how == "plain" and "failed" not in store_chart(pid), (len(SENT), how))

def t_other_refusal():
    res = []
    for code in ("41", "61"):
        reset(); p = newp(); pid = cid(); OVERRIDE[("CMS", p["number"])] = ("answer", err_answer(code, {"memberId": p["number"]}))
        j, how, err = askp(p, dos=ymd(ago(1)), pid=pid)
        res.append((code, kinds(), how, list(ST.NOTES), err))
    reset(); p = newp(); OVERRIDE[("CMS", p["number"])] = ("answer", {"errors": [], "subscriber": {"memberId": p["number"]}, "benefitsInformation": []})
    j, how, err = askp(p, dos=ymd(ago(1)), pid=cid()); res.append(("empty", kinds(), how, list(ST.NOTES), err))
    check("client: any other refusal of the plain check (41 provider not cleared, 61, an answer with no Part A or Part B) -> the look-up, as before, and ONE report line saying so",
          lambda: all(r[1] == ["CMS", "MBILUNOSSN"] and r[2] == "lookup after plain" and len(r[3]) == 1 and "look-up was bought" in r[3][0] and r[3][0] in r[4] for r in res)
          and "41" in res[0][3][0] and "61" in res[1][3][0] and "no Part A or Part B" in res[2][3][0], res)

def t_ssn():
    ssn = "".join(str((i * 7 + 3) % 10) for i in range(9))
    reset(); p = newp(); j, how, err = askp(p, number=None, ssn=ssn, dos=ymd(ago(1)), pid=cid())
    b = SENT[0][1] if SENT else {}
    check("client: with an SSN the caller passed -> the look-up with SSN (MBILU); kind 'look-up with SSN' at $1.00 in the usage log",
          lambda: kinds() == ["MBILU"] and b["subscriber"].get("ssn") == ssn and "address" not in b["subscriber"] and how == "lookup" and log_lines()[-1][2] == "look-up with SSN" and log_lines()[-1][6] == "1.00")
    reset(); p = newp(); askp(p, number=None, dos=ymd(ago(1)))
    check("client: no SSN given -> never one sent (MBILUNOSSN by name, birth date and state)", lambda: kinds() == ["MBILUNOSSN"] and "ssn" not in SENT[0][1]["subscriber"])
    reset(); p = newp(); askp(p, ssn=ssn, dos=ymd(ago(1)))
    check("client: a good number and an SSN -> only the plain check, the SSN goes nowhere", lambda: kinds() == ["CMS"] and ssn not in json.dumps(SENT))
    check("client: the SSN is in no file the client writes (usage log, store)", lambda: ssn not in text_of(ULOG) and ssn not in text_of(STORE))

def t_med_summ():
    p = newp(death=ago(20), advantage=("TEST ADVANTAGE", "H" + str(4521)), hospice=True)
    plain = a271(p, p["number"]); look = a271(p, p["number"], address={"state": "FL", "city": "TEST"})
    mp, ml = ST.med_summ(plain), ST.med_summ(look)
    check("client: med_summ reads a plain answer and a look-up answer alike - Part A, Part B, date of death, other payers",
          lambda: all(mp[k] == ml[k] for k in ("partA", "partB", "death", "other", "errors")) and mp["death"] == p["death8"])
    want = {"mbi": p["number"], "name": "%s, %s" % (p["last"], p["first"]), "dob": p["dob8"], "death": p["death8"], "address": {"state": "FL", "city": "TEST"}, "errors": [],
            "partA": ymd(datetime.date(2015, 1, 1)), "partB": ymd(datetime.date(2015, 2, 1)),
            "other": [{"code": "U", "type": "HM", "typeName": "Health Maintenance Organization", "plan": "TEST ADVANTAGE PLAN", "dates": {"plan": ymd(datetime.date(TODAY.year, 1, 1))}, "entity": [("TEST ADVANTAGE", "H" + str(4521))]},
                      {"code": "X", "type": "MA", "typeName": None, "plan": None, "dates": None, "entity": [("TEST HOSPICE", "HSP" + "01")]}]}
    check("client: med_summ of a look-up answer is exactly what it was before this change", lambda: ml == want, ml)
    e = ST.med_summ(err_answer("72"))
    check("client: med_summ of an error answer lists the code first ('72 ...'), as before", lambda: e["errors"] == ["72 " + DESC["72"]] and e["partA"] is None)
    stored = {"stored": {"asked": iso(TODAY), "dos": ymd(TODAY), "how": "plain", "who": "x"}, "death": p["death8"], "partA": "A", "partB": "B", "other": [{"code": "U"}], "errors": [], "active": True}
    check("client: med_summ reads an answer from the store (no number, name, birth date or address in it)",
          lambda: ST.med_summ(stored) == {"mbi": None, "name": None, "dob": None, "death": p["death8"], "address": None, "errors": [], "partA": "A", "partB": "B", "other": [{"code": "U"}]})
    ma = newp(advantage=("TEST ADVANTAGE", "H" + str(4521))); hp = newp(hospice=True)
    check("client: the store's hospice fact is service type 45 - an Advantage plan whose id holds '45' is not hospice",
          lambda: ST.medicare_facts(a271(ma, ma["number"]), "plain")["hospice"] is False and ST.medicare_facts(a271(hp, hp["number"]), "plain")["hospice"] is True)
    # step 3: a real Medicare answer lists hospice (45) among the services of its Part A lines for EVERY beneficiary (the vendor's own look-up
    # example; the two plain answers of 10/8/2026) - only a code-X line for 45 (the hospice provider's line) is a hospice election
    rp = newp(); real = a271(rp, rp["number"]); pa = [x for x in real["benefitsInformation"] if x.get("insuranceTypeCode") == "MA" and x.get("code") == "1"][0]
    pa["serviceTypeCodes"] = ["30", "42", "45", "48", "49", "69", "76", "83", "A5", "A7", "AG", "BT", "BU", "BV"]
    real["benefitsInformation"].append({"code": "C", "name": "Deductible", "insuranceTypeCode": "MA", "serviceTypeCodes": ["30", "42", "45", "48"], "benefitAmount": "0"})
    check("client: a Part A line that lists hospice (45) among its covered services, as every Medicare answer does, is not hospice in the store; a code-X line for 45 is",
          lambda: ST.medicare_facts(real, "plain")["hospice"] is False and ST.medicare_facts(a271(hp, hp["number"]), "lookup")["hospice"] is True)
    f = ST.medicare_facts(a271(p, p["number"]), "plain")
    check("client: the facts kept per answer: active, Part A / B, the Advantage plan (name, id, dates), hospice, date of death, errors - and nothing else",
          lambda: f["active"] is True and f["partA"] and f["partB"] and f["other"][0]["entity"] == [("TEST ADVANTAGE", "H" + str(4521))] and f["death"] == p["death8"]
          and set(f) == {"active", "partA", "partB", "other", "hospice", "death", "errors", "number_differs"}, f)

def t_usage_log():
    reset(); p = newp(); pid = cid(); dos = ymd(ago(1))
    askp(p, dos=dos, pid=pid, who="guard")                                                  # plain Medicare, chart id, who=guard
    ST.WHO = "some helper.py"; ST.mbi(p["first"], p["last"], p["dob8"], "FL", dos)          # look-up without SSN, no chart id
    ST.elig("87726", p["first"], p["last"], p["dob8"], "M" + "1" * 9, dos, pid=pid)          # eligibility at a payer
    ST.disc(p["first"], p["last"], p["dob8"], "FL", dos)                                     # discovery
    ST._post(ST.API + "/change/medicalnetwork/claimstatus/v2", {"tradingPartnerServiceId": "87726", "claimNumber": "X"})   # claim status (section 9 sends these)
    OVERRIDE[("CMS", WRONG[3])] = ("answer", err_answer("72")); ST.elig("CMS", p["first"], p["last"], p["dob8"], WRONG[3], dos)   # an answer with an error code
    L = log_lines()
    check("usage: ONE line per paid call (every POST through _post), in order", lambda: len(L) == len(SENT) == 6, (len(L), len(SENT)))
    check("usage: the kind of call - plain Medicare, look-up without SSN, eligibility, discovery, claim status",
          lambda: [l[2] for l in L] == ["plain Medicare", "look-up without SSN", "eligibility", "discovery", "claim status", "plain Medicare"], [l[2] for l in L])
    check("usage: the payer id (none for discovery), the first-tier list price of each call",
          lambda: [l[3] for l in L] == ["CMS", "MBILUNOSSN", "87726", "-", "87726", "CMS"] and [l[6] for l in L] == ["0.30", "1.00", "0.30", "1.50", "0.30", "0.30"], L)
    check("usage: who asked - the caller's who, else stedi.WHO a helper set once; the chart id when the caller passed one",
          lambda: [l[1] for l in L] == ["guard"] + ["some helper.py"] * 5 and [l[4] for l in L] == [pid, "-", pid, "-", "-", "-"], L)
    now = datetime.datetime.now(datetime.timezone.utc)
    check("usage: the time in UTC and the first error code or 'ok'",
          lambda: all(re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", l[0]) for l in L) and abs((now - datetime.datetime.strptime(L[0][0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)).total_seconds()) < 300
          and [l[5] for l in L] == ["ok", "ok", "ok", "ok", "ok", "72"], L)
    check("usage: by default WHO is the program's file name", lambda: ST_FIRST_WHO == os.path.basename(sys.argv[0]), ST_FIRST_WHO)
    n = len(L); ST.payers("test"); ST.enrollments()
    check("usage: the two free GET calls (payer search, enrollments) are not counted", lambda: len(GETS) == 2 and len(log_lines()) == n)
    OVERRIDE[("CMS", p["number"])] = ("timeout",); r1 = _raises(lambda: ST.elig("CMS", p["first"], p["last"], p["dob8"], p["number"], dos), FakeTimeout)
    OVERRIDE[("CMS", p["number"])] = ("http", 503); r2 = _raises(lambda: ST.elig("CMS", p["first"], p["last"], p["dob8"], p["number"], dos), FakeHTTPError)
    check("usage: a call that fails still leaves its line ('time-out', 'http 503') and fails for the caller exactly as before", lambda: r1 and r2 and [l[5] for l in log_lines()[-2:]] == ["time-out", "http 503"])
    check("usage: no Medicare number, name or birth date in the log", lambda: not any(x in text_of(ULOG) for x in (p["number"], p["last"], p["dob8"], WRONG[3])))
    OVERRIDE.clear(); os.environ["STEDI_USAGE_LOG"] = os.path.join(TMP, "a_folder_not_a_file"); os.makedirs(os.environ["STEDI_USAGE_LOG"], exist_ok=True)
    try: j, how, err = askp(p, dos=dos)
    finally: os.environ["STEDI_USAGE_LOG"] = ULOG
    check("usage: a log that cannot be written never stops the call", lambda: how == "plain" and j.get("benefitsInformation"))
    sys.modules.pop("stedi_prices", None)
    try: ST.elig("CMS", p["first"], p["last"], p["dob8"], p["number"], dos)
    finally: sys.modules["stedi_prices"] = PR
    check("usage: without the price table the line is still written (empty price) and the call goes on", lambda: log_lines()[-1][2] == "plain Medicare" and log_lines()[-1][6] == "")

def t_cli():
    reset(); p = newp(); dos = ymd(ago(1))
    code, out, err = run_main("scripts/helpers/stedi.py", ["medicare", p["first"], p["last"], p["dob8"], p["number"], dos], TMP)
    check("client CLI: `stedi.py medicare FIRST LAST DOB NUMBER DOS` -> one plain check, prints the summary with how",
          lambda: code == 0 and kinds() == ["CMS"] and json.loads(out)["how"] == "plain" and json.loads(out)["partB"], (code, out[-300:], err[-300:]))
    reset(); code, out, err = run_main("scripts/helpers/stedi.py", ["medicare", p["first"], p["last"], p["dob8"], "-", dos], TMP)
    check("client CLI: `medicare ... - DOS` (no number) -> the look-up", lambda: code == 0 and kinds() == ["MBILUNOSSN"] and json.loads(out)["how"] == "lookup")
    reset(); code, out, err = run_main("scripts/helpers/stedi.py", ["mbi", p["first"], p["last"], p["dob8"], "FL", dos], TMP)
    reset2 = list(SENT); del SENT[:]
    code2, out2, err2 = run_main("scripts/helpers/stedi.py", ["elig", "87726", p["first"], p["last"], p["dob8"], "M" + "2" * 9, dos], TMP)
    check("client CLI: `mbi` and `elig` stay as they are (a look-up; an eligibility check at the payer named)",
          lambda: code == 0 and [b["tradingPartnerServiceId"] for _, b in reset2] == ["MBILUNOSSN"] and json.loads(out)["mbi"] == p["number"]
          and code2 == 0 and kinds() == ["87726"] and "planStatus" in json.loads(out2))

# ==== 3. the answer store ======================================================================================================
def t_store():
    reset()
    saved = os.environ.pop("MEDICARE_STORE")
    try: default = MS.path()
    finally: os.environ["MEDICARE_STORE"] = saved
    check("store: ONE file - $MEDICARE_STORE, default patient_db/medicare_answers.json beside the helper (the workspace root)",
          lambda: MS.path() == STORE and default == os.path.join(os.path.dirname(MS.__file__), "patient_db", "medicare_answers.json"))
    rels = ["patient_db/medicare_answers.json", "patient_db/stedi_usage.log", "scripts/helpers/patient_db/medicare_answers.json", "scripts/helpers/patient_db/stedi_usage.log",
            "core/patient_db/medicare_answers.json", "core/patient_db/stedi_usage.log"]
    ign = [subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", r], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode for r in rels]
    check("store: git ignores patient_db/ - the store and the usage log can never be committed", lambda: ign == [0] * len(rels), dict(zip(rels, ign)))
    pid = cid(); dos = ymd(ago(1)); facts = {"active": True, "partA": "A", "partB": "B", "other": [], "hospice": False, "death": None, "errors": [], "number_differs": None}
    MS.put(pid, facts, "plain", "first", dos); MS.put(pid, dict(facts, partB="B2"), "plain", "second", dos)
    MS.put(pid, facts, "plain", "other month", ymd(next_month(TODAY)))
    a = store_chart(pid).get("answers") or []
    check("store: one answer per chart per day (and month of service asked about) - a second answer the same day replaces the first",
          lambda: len(a) == 2 and [x["who"] for x in a if x["dos"] == dos] == ["second"] and MS.get(pid, 0, dos)["partB"] == "B2", a)
    reset(); pid = cid()
    MS.put(pid, facts, "plain", "x", dos); store_edit(lambda d: d["charts"][pid]["answers"][0].update(asked=iso(ago(30))))
    g30 = MS.get(pid, 30, dos); g29 = MS.get(pid, 29, dos)
    store_edit(lambda d: d["charts"][pid]["answers"][0].update(asked=iso(ago(31)))); g31 = MS.get(pid, 30, dos)
    check("store: each reader brings its own age limit - an answer 30 days old serves the guard's 30 days, not 29; 31 days old serves nobody at 30",
          lambda: g30 is not None and g29 is None and g31 is None)
    reset(); pid = cid(); MS.put(pid, facts, "plain", "x", ymd(TODAY))
    check("store: max age 0 = asked today only; no age given = the store is not read", lambda: MS.get(pid, 0, ymd(TODAY)) is not None and MS.get(pid, None, ymd(TODAY)) is None)
    reset(); pid = cid(); vis = TODAY
    MS.put(pid, facts, "plain", "x", ymd(prev_month(vis))); before = MS.get(pid, 60, ymd(vis))
    reset(); MS.put(pid, facts, "plain", "x", ymd(next_month(vis))); later = MS.get(pid, 60, ymd(vis))
    reset(); MS.put(pid, facts, "plain", "x", ymd(first_of_month(vis))); same = MS.get(pid, 60, ymd(vis))
    check("store: an answer about an earlier month never serves a later one; the same month or a later date of service may",
          lambda: before is None and later is not None and same is not None)
    reset(); pid = cid(); MS.put(pid, {"errors": ["42 x"], "reason": "time-out"}, "failed", "guard", dos)
    f1 = MS.get(pid, 30, dos)
    store_edit(lambda d: d["charts"][pid]["failed"].update(day=iso(ago(1)))); f2 = MS.get(pid, 30, dos)
    reset(); MS.put(pid, {"errors": [], "reason": "time-out"}, "failed", "guard", dos); MS.put(pid, facts, "plain", "x", dos); f3 = MS.get(pid, 30, dos)
    check("store: a failed call is kept only as 'asked and failed today' (never as an answer); the next day it is gone; a real answer the same day replaces it",
          lambda: f1 and f1.get("failed") is True and f1.get("reason") == "time-out" and f2 is None and f3 and not f3.get("failed") and "failed" not in store_chart(pid), (f1, f2, f3))
    reset(); pid = cid(); p = newp()
    MS.put(pid, dict(facts, errors=["72 not found " + p["number"]], other=[{"code": "U", "entity": [["TEST", p["number"]]], "plan": "x"}], name=p["last"], dob=p["dob8"], mbi=p["number"]), "lookup", "x", dos)
    t = text_of(STORE)
    check("store: no Medicare number, name or birth date in the file - not kept, and anything shaped like a number is blanked", lambda: t and not any(x in t for x in (p["number"], p["last"], p["dob8"])), t[:400])
    reset(); pid = cid(); MS.put(pid, facts, "plain", "x", dos); good = text_of(STORE); real_dump = MS.json.dump
    def boom(*a, **k): raise OSError("disk full (stand-in)")
    MS.json.dump = boom
    try: r = MS.put(cid(), facts, "plain", "x", dos)
    finally: MS.json.dump = real_dump
    left = [x for x in os.listdir(os.path.dirname(STORE)) if x != os.path.basename(STORE)]
    check("store: a write goes to a temporary file renamed into place - a write that fails leaves the old file whole, leaves no temporary file and does not raise",
          lambda: r is False and text_of(STORE) == good and left == [], (r, left))
    res = []
    for content in (None, "", "{not json", "[1, 2]", json.dumps({"charts": {pid: {"answers": "garbage"}}})):
        reset()
        if content is not None:
            os.makedirs(os.path.dirname(STORE), exist_ok=True)
            with open(STORE, "w") as fh: fh.write(content)
        res.append(_try(lambda: MS.get(pid, 30, dos)))
    reset(); os.makedirs(STORE)                                  # a folder where the file should be: nothing can be read or written
    p = newp(); j, how, err = askp(p, dos=dos, pid=pid, max_age_days=30)
    check("store: a missing, empty or broken store is an empty store, and a store that cannot be written never stops the caller",
          lambda: res == [None] * 5 and how == "plain" and len(SENT) == 1, res)
    reset(); p = newp(); pid = cid()
    askp(p, dos=dos, pid=pid, max_age_days=0, who="feed check"); askp(p, dos=dos, pid=pid, max_age_days=0, who="pre-claim check")
    j, how, err = askp(p, dos=dos, pid=pid, max_age_days=30, who="guard")
    check("store: through stedi.medicare, two more helpers asking about the same chart the same day make NO new request (one paid call in all)",
          lambda: len(SENT) == 1 and how == "plain" and j["stored"]["who"] == "feed check" and j["stored"]["how"] == "plain")
    askp(p, dos=dos, pid=pid, who="no age rule")
    check("store: a caller that gives no age rule is not served from the store (it asks), and its answer is written", lambda: len(SENT) == 2 and (store_chart(pid).get("answers") or [{}])[-1]["who"] == "no age rule")

# ==== 4. the deceased-patient guard (the real guard file, loaded with stand-ins) ===============================================
def guard_check(pid, dos, carrier="car6085", proc="99309"):
    err = io.StringIO()
    with contextlib.redirect_stderr(err): return DG.check(pid, dos, carrier, proc)
def t_guard_death():
    reset(); dead = newp(death=ago(20)); dos = ago(5)
    a = chart(cid(), dead, plans=[("car6085", "", dead["number"])])
    b = chart(cid(), dead, plans=[("car6404", "", "M" + "4" * 9)])        # the same person, no Medicare plan on this chart: the look-up
    ra = guard_check(a, iso(dos)); ka = kinds(); del SENT[:]
    rb = guard_check(b, iso(dos)); kb = kinds()
    want = "pat%s DOS %s is after date of death %s (stedi-medicare-271) - claim must not be submitted; void the charge"
    check("guard: a date of death learned from a PLAIN answer blocks the claim exactly as one from a look-up (same rule, same wording)",
          lambda: ka == ["CMS"] and kb == ["MBILUNOSSN"] and ra == (True, want % (a, iso(dos), iso(ago(20)))) and rb == (True, want % (b, iso(dos), iso(ago(20)))), (ka, kb, ra, rb))
    c = cache_json() or {}
    check("guard: the date of death is kept in the guard's cache for both charts", lambda: c[a]["dod"] == c[b]["dod"] == iso(ago(20)) and c[a]["src"] == "stedi-medicare-271")
    del SENT[:]; r2 = guard_check(a, iso(ago(1)))
    check("guard: a later claim of that chart is blocked from the cache, with no new request", lambda: r2[0] is True and SENT == [])
    reset(); d2 = newp(death=first_of_month(TODAY)); h = chart(cid(), d2, plans=[("car6085", "", d2["number"])])
    rc = guard_check(h, iso(first_of_month(TODAY) + datetime.timedelta(days=1)), proc="99490"); ro = guard_check(h, iso(first_of_month(TODAY)), proc="99490")
    check("guard: the care-management wording in the month of death is unchanged, and a date of service on the date of death is not blocked",
          lambda: rc[0] is True and rc[1].endswith("; CCM in the month of death needs a DOS on/before the death date, else void") and ro == (False, ""), (rc, ro))

def t_guard_not_found_failed():
    real_record = DG.record; seen = []
    def spy(pid, j, src="stedi-medicare-271"): seen.append((pid, json.loads(json.dumps(j)))); return real_record(pid, j, src)
    DG.record = spy
    try:
        res = []
        for look in (("timeout",), ("answer", err_answer("42")), ("http", 403), ("answer", {"errors": [], "benefitsInformation": [], "subscriber": {}})):
            reset(); del seen[:]; p = newp(); dos = iso(ago(2))
            pid = chart(cid(), p, plans=[("car6085", "", WRONG[4])]); OVERRIDE[("MBILUNOSSN", p["last"])] = look
            r = guard_check(pid, dos)
            res.append((look[0], kinds(), r, list(DG.LOG), (cache_json() or {}).get(pid), store_chart(pid).get("answers"), [s[1].get("errors") for s in seen]))
    finally: DG.record = real_record
    unv = "pat%s DOS %s: date of death UNVERIFIED (lookup failed)"
    check("guard: a plain 'not found' followed by a failed look-up (time-out, 42, a refused request, an empty reply) blocks nothing and is logged UNVERIFIED as before",
          lambda: all(r[1] == ["CMS", "MBILUNOSSN"] and r[2] == (False, "") and len(r[3]) == 1 and re.match(unv.replace("%s", r".+").replace("(", r"\(").replace(")", r"\)"), r[3][0]) for r in res), res)
    check("guard: ... and the chart is NOT kept as 'no death on record': no cache entry, no stored answer, the plain 72 never reached record()",
          lambda: all(r[4] is None and not r[5] and [{"code": "72", "description": DESC["72"]}] not in r[6] for r in res), res)
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); OVERRIDE[("CMS", p["number"])] = ("timeout",)
    r = guard_check(pid, iso(ago(2)))
    check("guard: a failed plain check (time-out) blocks nothing, buys nothing else, and the LOG line is word for word as before",
          lambda: r == (False, "") and kinds() == ["CMS"] and DG.LOG == [unv % (pid, iso(ago(2)))] and (cache_json() or {}).get(pid) is None, (r, DG.LOG))
    del SENT[:]; del DG.LOG[:]; r = guard_check(pid, iso(ago(1)))
    check("guard: a second charge of that chart the same day buys nothing ('asked and failed today') and is reported UNVERIFIED again", lambda: r == (False, "") and SENT == [] and len(DG.LOG) == 1)
    OVERRIDE.clear(); store_edit(lambda d: d["charts"][pid]["failed"].update(day=iso(ago(1)))); r = guard_check(pid, iso(ago(1)))
    check("guard: the next day it is asked again", lambda: r == (False, "") and kinds() == ["CMS"] and (cache_json() or {}).get(pid, {}).get("src") == "stedi: no death on record")
    reset(); p = newp(); pid = cid()
    ST._dod_hook(pid, err_answer("72", {"memberId": p["number"]}), plain=True); ST._dod_hook(pid, {"errors": [], "benefitsInformation": []}, plain=True)
    DG.record(pid, {"errors": [], "benefitsInformation": [], "subscriber": {}})
    check("guard: neither the hook nor record() keeps a plain 'not found' or an empty reply as 'no death on record'", lambda: cache_json() is None)
    DG.record(pid, {"dateOfDeath": ymd(ago(9))}, "amd-271"); DG.record(cid(), err_answer("72"))
    check("guard: record() still keeps a date of death from anyone, and a look-up's lone 72 as 'not a Medicare beneficiary' (as before)",
          lambda: cache_json()[pid]["dod"] == iso(ago(9)) and cache_json()[pid]["src"] == "amd-271" and any(v["src"] == "stedi: not a Medicare beneficiary" for v in cache_json().values()))

def t_guard_shared():
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); dos = ago(2)
    guard_check(pid, iso(dos)); n1 = len(SENT); guard_check(pid, iso(ago(1))); n2 = len(SENT)
    j, how, err = askp(p, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=(TODAY - first_of_month(dos)).days)
    check("guard: two helpers asking about one chart on one day make ONE paid call (guard, a second charge, then the pre-claim check)",
          lambda: (n1, n2, len(SENT)) == (1, 1, 1) and how == "plain" and j["stored"]["who"] == "guard", (n1, n2, len(SENT)))
    reset(); q = newp(); pid = chart(cid(), q, plans=[("car6085", "", q["number"])])
    askp(q, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=0); r = guard_check(pid, iso(dos))
    L = log_lines()
    check("guard: ... and the other way round: the pre-claim check's answer serves the guard (no second request); the one line in the usage log names who paid",
          lambda: len(SENT) == 1 and r == (False, "") and cache_json()[pid]["src"] == "stedi: no death on record" and [l[1] for l in L] == ["pre-claim check"], L)
    reset(); q = newp(); pid = chart(cid(), q, plans=[("car6085", "", q["number"])])
    askp(q, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=0); os.remove(DCACHE)     # a machine where the store came along but the guard's cache did not
    store_edit(lambda d: d["charts"][pid]["answers"][0].update(asked=iso(ago(20)))); del SENT[:]
    r = guard_check(pid, iso(dos))
    check("guard: an answer another helper got 20 days ago is used, and the guard's 30 days count from THAT day (cache 'checked' = the day Medicare was asked)",
          lambda: SENT == [] and r == (False, "") and cache_json()[pid]["checked"] == iso(ago(20)), cache_json())
    reset(); q = newp(); pid = chart(cid(), q, plans=[("car6085", "", q["number"])])
    askp(q, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=0); os.remove(DCACHE)
    store_edit(lambda d: d["charts"][pid]["answers"][0].update(asked=iso(ago(31)))); del SENT[:]
    guard_check(pid, iso(dos))
    check("guard: an answer 31 days old is not used by the guard - it asks again", lambda: kinds() == ["CMS"] and cache_json()[pid]["checked"] == iso(TODAY))

def t_guard_number():
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", mdy(ago(400)), WRONG[0]), ("car6085", "", spaced(p["number"])), ("car6404", "", "M" + "5" * 9)])
    guard_check(pid, iso(ago(2)))
    check("guard: it takes the member number of the chart's OPEN Medicare Part B plan (car6085) and asks the plain check; the usage log says 'guard'",
          lambda: kinds() == ["CMS"] and SENT[0][1]["subscriber"]["memberId"] == p["number"] and log_lines()[0][1] == "guard" and log_lines()[0][4] == pid)
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", mdy(ago(100)), p["number"]), ("car6085", mdy(ago(900)), WRONG[1])])
    guard_check(pid, iso(ago(2)))
    check("guard: no open Medicare plan -> the number of the one that ended last", lambda: kinds() == ["CMS"] and SENT[0][1]["subscriber"]["memberId"] == p["number"])
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6404", "", "M" + "6" * 9)])
    r = guard_check(pid, iso(ago(2)), carrier="car6404", proc="99490")
    check("guard: a care-management chart with no Medicare plan keeps the look-up by name, counted as 'guard, no Medicare plan on the chart'",
          lambda: kinds() == ["MBILUNOSSN"] and log_lines()[0][1] == "guard, no Medicare plan on the chart" and r == (False, ""))
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", "")]); guard_check(pid, iso(ago(2)))
    check("guard: a Medicare plan with no number -> the look-up, still counted as 'guard'", lambda: kinds() == ["MBILUNOSSN"] and log_lines()[0][1] == "guard")
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); r = guard_check(pid, iso(ago(2)), carrier="car6404", proc="99213")
    check("guard: a claim that is neither straight Medicare nor care management asks nothing (as before)", lambda: SENT == [] and r == (False, ""))

def t_guard_flag_cache():
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=mdy(ago(30)))
    r = guard_check(pid, iso(ago(5)))
    check("guard: the chart's own deceased flag still comes first - blocked from it, no vendor request", lambda: r[0] is True and SENT == [] and cache_json()[pid]["dod"] == iso(ago(30)))
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="Y"); r = guard_check(pid, iso(ago(5)))
    check("guard: a deceased flag with no date counts the date of service as the date (as before), no vendor request", lambda: r == (False, "") and SENT == [] and cache_json()[pid]["dod"] == iso(ago(5)))
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); other = cid()
    def meanwhile(url, body):
        c = cache_json() or {}; c[other] = {"dod": iso(ago(40)), "checked": iso(TODAY), "src": "another helper"}
        os.makedirs(os.path.dirname(DCACHE), exist_ok=True)
        with open(DCACHE, "w") as fh: json.dump(c, fh)
    ON_SEND.append(meanwhile); guard_check(pid, iso(ago(2))); del ON_SEND[:]
    c = cache_json() or {}
    check("guard: check() reads and writes the ONE cache file it is configured with, and keeps what another helper wrote there meanwhile",
          lambda: c.get(other, {}).get("src") == "another helper" and c.get(pid, {}).get("src") == "stedi: no death on record" and sorted(os.listdir(os.path.dirname(DCACHE))) == ["deceased_cache.json"], c)
    reset(); os.makedirs(os.path.dirname(DCACHE), exist_ok=True)
    with open(DCACHE, "w") as fh: fh.write("{this file holds dates of death but cannot be read")
    p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); r = guard_check(pid, iso(ago(2)))
    check("guard: a cache file that is there but cannot be read is never overwritten (it may hold dates of death)",
          lambda: text_of(DCACHE) == "{this file holds dates of death but cannot be read" and r == (False, "") and DG._put(pid, {"dod": None}) is False)
    reset(); p = newp(death=ago(15)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])])
    os.makedirs(os.path.dirname(DCACHE), exist_ok=True)
    with open(DCACHE, "w") as fh: json.dump({pid: {"dod": "[DOB]", "checked": iso(TODAY), "src": "x"}}, fh)
    r = guard_check(pid, iso(ago(2)))
    check("guard: a scrubbed '[DOB]' in the cache is unknown and asked again (the 10/14 fix holds) - here it finds the death and blocks", lambda: kinds() == ["CMS"] and r[0] is True)
    reset(); nb = newp(beneficiary=False); pid = chart(cid(), nb, plans=[("car6404", "", "M" + "7" * 9)]); r = guard_check(pid, iso(ago(2)), carrier="car6404", proc="99490")
    nb2 = newp(beneficiary=False); pid2 = chart(cid(), nb2, plans=[("car6085", "", nb2["number"])]); r2 = guard_check(pid2, iso(ago(2)))
    check("guard: a LOOK-UP that says 72 ('not a Medicare beneficiary') is still a valid answer, kept 30 days, nothing blocked - also after a plain 72",
          lambda: r == r2 == (False, "") and kinds() == ["MBILUNOSSN", "CMS", "MBILUNOSSN"] and cache_json()[pid]["src"] == cache_json()[pid2]["src"] == "stedi: no death on record" and DG.LOG == [], (kinds(), DG.LOG))

def t_guard_old_client():
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])])
    sys.modules["stedi"] = standin("stedi", mbi=ST.mbi, med_summ=ST.med_summ)
    try: r = guard_check(pid, iso(ago(2)))
    finally: sys.modules["stedi"] = ST
    check("guard: with an older client in the workspace (no medicare()) it falls back to the look-up through the client, as before", lambda: kinds() == ["MBILUNOSSN"] and r == (False, "") and cache_json()[pid]["dod"] is None)

def t_guard_charge():
    reset(); p = newp(death=ago(30)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])])
    RESAVE["555"] = '<r><visit date="%s"/><patient id="pat%s"/><charge id="charge555" proccode="99309"/><insplan sequence="1" carrier="car6085"/></r>' % (mdy(ago(3)), pid)
    err = io.StringIO()
    with contextlib.redirect_stderr(err): r = DG.check_charge("555", 1)
    check("guard: check_charge reads the charge and blocks a straight-Medicare claim after a death learned from the plain check", lambda: r[0] is True and kinds() == ["CMS"], r)

# ==== 5. the nightly pre-claim check (run as a program INSIDE this process, in a throwaway workspace) ===========================
WS_N = [0]
def new_ws():
    WS_N[0] += 1; ws = os.path.join(TMP, "ws%d" % WS_N[0]); os.makedirs(ws)
    with open(os.path.join(ws, "carriers.json"), "w") as fh: json.dump({"car6085": ["FLO02", "MEDICARE PART B (TEST)"], "car6404": ["UNI20", "COMMERCIAL PLAN (TEST)"]}, fh)
    return ws
def unpaid(pid, code, dos, balance=100.0):
    UNPAID.append({"patientid": str(pid), "carriercode": code + " ", "patientname": CHARTS[str(pid)]["name"], "dateofservice": dos.isoformat() + "T00:00:00", "insbalance": balance})
def precheck(ws, *argv):
    return run_main("scripts/helpers/precheck.py", list(argv) or ["--days", "3", "--max", "120"], ws)
def rows(ws):
    with open(os.path.join(ws, "precheck_%s.json" % ymd(TODAY))) as fh: return {str(r["patientid"]): r for r in json.load(fh)}
def t_precheck_args():
    reset(); ws = new_ws(); p = newp(); unpaid(chart(cid(), p, plans=[("car6085", "", p["number"])]), "FLO02", ago(1))
    c1, o1, e1 = precheck(ws, "--help"); n1 = (len(SENT), len(BILLING), len(LOGINS))
    c2, o2, e2 = precheck(ws, "--dayz", "3"); n2 = (len(SENT), len(BILLING), len(LOGINS))
    c3, o3, e3 = precheck(ws, "3"); n3 = (len(SENT), len(BILLING), len(LOGINS))
    check("pre-claim: --help prints the usage and exits, with no call of any kind", lambda: c1 == 0 and "usage: precheck.py" in o1 and "--dry" in o1 and n1 == (0, 0, 0), (c1, o1[:200], n1))
    check("pre-claim: an unknown option or a stray word is an error and nothing is asked (no login, no unpaid list, no vendor call)",
          lambda: c2 == 2 and c3 == 2 and "unrecognized arguments" in e2 and n2 == n3 == (0, 0, 0), (c2, c3, e2[-200:], n3))
    c4, o4, e4 = precheck(ws, "--days", "3", "--dry")
    check("pre-claim: --dry reads the unpaid list and the charts and asks the vendor nothing (as before)", lambda: c4 == 0 and SENT == [] and len(BILLING) >= 2 and rows(ws)[str(UNPAID[0]["patientid"])]["result"] == "DRY")

def t_precheck_words():
    reset(); ws = new_ws(); dos = ago(1); C = {}
    def med(key, p, number):
        C[key] = chart(cid(), p, plans=[("car6085", "", number)]); unpaid(C[key], "FLO02", dos)
    # the hospice note reads '45' anywhere in the summarized other-payer entry (as before this change: the summary keeps no service type codes),
    # so the canned hospice entry here carries an id with 45 in it, and the words are compared with what the helper always printed
    good, ma, dd, wr, nb, hs, to = newp(), newp(advantage=("TEST ADVANTAGE", "H" + str(4521))), newp(death=ago(40)), newp(), newp(beneficiary=False), newp(hospice="HSP" + "45"), newp()
    med("ok", good, spaced(good["number"])); med("ma", ma, ma["number"]); med("dead", dd, dd["number"]); med("wrong", wr, WRONG[0])
    med("notben", nb, ""); med("hosp", hs, hs["number"]); med("timeout", to, to["number"]); OVERRIDE[("CMS", to["number"])] = ("timeout",)
    co = newp(); C["comm"] = chart(cid(), co, plans=[("car6404", "", "M" + "8" * 9)]); unpaid(C["comm"], "UNI20", dos)
    ci = newp(); C["inact"] = chart(cid(), ci, plans=[("car6404", "", "M" + "9" * 9)]); unpaid(C["inact"], "UNI20", dos); OTHER["M" + "9" * 9] = "inactive"
    code, out, err = precheck(ws); R = rows(ws)
    res = {k: R[v]["result"] for k, v in C.items()}
    check("pre-claim: 'OK straight Medicare' from ONE plain check on a good number (written with dashes and a space on the chart)", lambda: res["ok"] == "OK straight Medicare", res)
    check("pre-claim: 'ADVANTAGE PLAN on DOS: ...' word for word as before (entity, id, dates)",
          lambda: res["ma"] == "ADVANTAGE PLAN on DOS: TEST ADVANTAGE H4521 (dates %s)" % json.dumps({"plan": ymd(datetime.date(TODAY.year, 1, 1))}), res["ma"])
    check("pre-claim: 'DATE OF DEATH <date>' as before (from a plain answer)", lambda: res["dead"] == "DATE OF DEATH " + dd["death8"], res["dead"])
    check("pre-claim: 'MBI MISMATCH chart <number> vs CMS <number>' as before - raised from the look-up after Medicare refused the chart's number",
          lambda: res["wrong"] == "MBI MISMATCH chart %s vs CMS %s" % (WRONG[0], wr["number"]), res["wrong"])
    check("pre-claim: 'not found on Medicare: 72 ...' as before (the look-up's answer; no number on the chart)", lambda: res["notben"] == "not found on Medicare: 72 " + DESC["72"], res["notben"])
    check("pre-claim: 'OK straight Medicare (hospice benefit present)' as before", lambda: res["hosp"] == "OK straight Medicare (hospice benefit present)", res["hosp"])
    check("pre-claim: a failed Medicare check is an ERROR row (never OK) and is not cached, as a failed look-up was", lambda: res["timeout"] == "ERROR Medicare check failed (time-out)", res["timeout"])
    check("pre-claim: the other payers' checks and discovery are unchanged ('OK active - ...', 'INACTIVE on DOS (...)' + discovery)",
          lambda: res["comm"].startswith("OK active - TEST PLAN ") and res["inact"] == "INACTIVE on DOS (Inactive)" and R[C["inact"]]["discovery"][0][0] == "TEST MEDICAID", res)
    want_kinds = {"ok": ["CMS"], "ma": ["CMS"], "dead": ["CMS"], "wrong": ["CMS", "MBILUNOSSN"], "notben": ["MBILUNOSSN"], "hosp": ["CMS"], "timeout": ["CMS"]}
    sent = [(b.get("tradingPartnerServiceId"), (b.get("subscriber") or {}).get("lastName")) for _, b in SENT]
    check("pre-claim: Medicare visits cost one plain check each (two calls only for the wrong number, the look-up only with no number); 11 requests for 9 pairs",
          lambda: all([k for k, last in sent if last == CHARTS[C[key]]["name"].split(",")[0]] == v for key, v in want_kinds.items()) and len(SENT) == 11, sent)
    last = [l for l in out.splitlines() if l.startswith("checked ")]
    check("pre-claim: the summary line is unchanged ('checked N patient/payer pairs (N new lookups); N flagged')", lambda: last == ["checked 9 patient/payer pairs (9 new lookups); 6 flagged"], last)
    cache = text_of(os.path.join(ws, "precheck_cache.json")); outf = text_of(os.path.join(ws, "precheck_%s.json" % ymd(TODAY)))
    plain_numbers = [good["number"], ma["number"], dd["number"], hs["number"]]
    check("pre-claim: for a plain answer the Medicare number is written neither into precheck_cache.json nor into precheck_<date>.json",
          lambda: not any(n in cache or n in outf or n.lower() in outf for n in plain_numbers) and "member" not in R[C["ok"]] and "mbi" not in R[C["ok"]], R[C["ok"]])
    check("pre-claim: for a look-up answer today's behaviour stays (the chart's and Medicare's number in its files)",
          lambda: R[C["wrong"]]["member"] == WRONG[0] and R[C["wrong"]]["mbi"] == wr["number"] and wr["number"] in cache, R[C["wrong"]])
    check("pre-claim: the timed-out pair is not in its cache (asked again next night)", lambda: not any(k.startswith(C["timeout"] + "|") for k in json.loads(cache)))
    check("pre-claim: every paid call it made is in the usage log as 'pre-claim check'; its Medicare calls carry the chart id (its other-payer calls pass none, as before)",
          lambda: len(log_lines()) == 11 and {l[1] for l in log_lines()} == {"pre-claim check"} and all((l[4] in C.values()) == (l[2] in ("plain Medicare", "look-up without SSN")) for l in log_lines()), log_lines())
    check("privacy: the store, the usage log and the guard cache hold no Medicare number of any chart asked", lambda: not any(n in text_of(STORE) + text_of(ULOG) + text_of(DCACHE) for n in [p["number"] for p in PEOPLE.values()] + WRONG))
    del SENT[:]; OVERRIDE.clear(); code, out, err = precheck(ws)
    check("pre-claim: run again the same day, its own cache answers the pairs it has and the failed one is NOT bought again ('asked and failed today')",
          lambda: SENT == [] and rows(ws)[C["ok"]].get("cached") is True and rows(ws)[C["timeout"]]["result"] == "ERROR Medicare check failed (time-out)", (kinds(), rows(ws)[C["timeout"]]))
    store_edit(lambda d: d["charts"][C["timeout"]]["failed"].update(day=iso(ago(1)))); code, out, err = precheck(ws)
    check("pre-claim: the next night (same month) the failed pair is asked again - one plain check - and the cached pairs still cost nothing",
          lambda: kinds() == ["CMS"] and rows(ws)[C["timeout"]]["result"] == "OK straight Medicare" and rows(ws)[C["ma"]].get("cached") is True, kinds())

def t_precheck_store():
    reset(); ws = new_ws(); dos = ago(1)
    p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); unpaid(pid, "FLO02", dos)
    guard_check(pid, iso(dos)); n1 = len(SENT)
    code, out, err = precheck(ws)
    check("pre-claim: an answer the guard got today serves the pre-claim check - no request, same words, counted as 0 new lookups",
          lambda: n1 == 1 and len(SENT) == 1 and rows(ws)[pid]["result"] == "OK straight Medicare" and "(0 new lookups)" in out, (n1, len(SENT), out))
    reset(); ws = new_ws(); p = newp(); pid = chart(cid(), p, plans=[("car6085", mdy(ago(300)), WRONG[1]), ("car6085", "", p["number"])]); unpaid(pid, "FLO02", dos)
    precheck(ws)
    check("pre-claim: it sends the number of the chart's OPEN Medicare plan (an ended plan listed first is passed over)", lambda: kinds() == ["CMS"] and SENT[0][1]["subscriber"]["memberId"] == p["number"])
    reset(); ws = new_ws(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); unpaid(pid, "FLO02", dos)
    MS.put(pid, {"active": True, "partA": "A", "partB": "B", "other": [], "errors": []}, "plain", "guard", ymd(prev_month(dos)))
    precheck(ws)
    check("pre-claim: an answer asked about last month is not used for this month's visit (it asks)", lambda: kinds() == ["CMS"])
    reset(); ws = new_ws(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); unpaid(pid, "FLO02", dos)
    MS.put(pid, {"active": True, "partA": "A", "partB": "B", "other": [], "errors": []}, "plain", "guard", ymd(dos))
    store_edit(lambda d: d["charts"][pid]["answers"][0].update(asked=iso(first_of_month(dos) - datetime.timedelta(days=1))))
    precheck(ws)
    check("pre-claim: an answer asked before the first of the visit's month is not used (its age rule is the visit's calendar month)", lambda: kinds() == ["CMS"])
    reset(); ws = new_ws(); p = newp(advantage=("TEST ADVANTAGE", "H" + str(4521))); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); unpaid(pid, "FLO02", dos)
    MS.put(pid, {"active": True, "partA": "A", "partB": "B", "other": [{"code": "U", "type": "HM", "typeName": "x", "plan": "x", "dates": {}, "entity": [["LATER PLAN", "H9"]]}], "errors": []}, "plain", "guard", ymd(next_month(dos)))
    precheck(ws)
    check("pre-claim: an answer about a LATER month is not used for this visit's plan (rule (a) would add that plan and rebill) - it asks for the visit's month",
          lambda: kinds() == ["CMS"] and "LATER PLAN" not in rows(ws)[pid]["result"] and rows(ws)[pid]["result"].startswith("ADVANTAGE PLAN on DOS: TEST ADVANTAGE"), rows(ws)[pid]["result"])
    reset(); ws = new_ws(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", WRONG[2])]); unpaid(pid, "FLO02", dos)
    guard_check(pid, iso(dos)); n1 = kinds(); del SENT[:]
    code, out, err = precheck(ws)
    check("pre-claim: a shared look-up answer that found the chart's number differs -> ONE look-up to read Medicare's number for rule (d): 'MBI MISMATCH chart ... vs CMS ...'",
          lambda: n1 == ["CMS", "MBILUNOSSN"] and kinds() == ["MBILUNOSSN"] and rows(ws)[pid]["result"] == "MBI MISMATCH chart %s vs CMS %s" % (WRONG[2], p["number"]), (n1, kinds(), rows(ws)[pid]))
    check("pre-claim: ... and the store still knows the numbers differ afterwards", lambda: (store_chart(pid).get("answers") or [{}])[-1].get("number_differs") is True, store_chart(pid))
    reset(); ws = new_ws(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", spaced(p["number"]))]); unpaid(pid, "FLO02", dos)
    guard_check(pid, iso(dos)); del SENT[:]; precheck(ws)
    check("pre-claim: a shared plain answer never raises MBI MISMATCH (the chart's number with dashes is not 'different')", lambda: SENT == [] and rows(ws)[pid]["result"] == "OK straight Medicare", rows(ws)[pid])

def t_ten_charts():
    reset(); dos = ago(1); C = []
    for i in range(8):
        p = newp(); C.append((chart(cid(), p, plans=[("car6085", "", p["number"])]), p, p["number"]))
    p = newp(); C.append((chart(cid(), p, plans=[("car6085", "", WRONG[3])]), p, WRONG[3]))
    p = newp(); C.append((chart(cid(), p, plans=[("car6404", "", "M" + "3" * 9)]), p, None))
    for pid, p, number in C: askp(p, number=number, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=(TODAY - first_of_month(dos)).days)
    for pid, p, number in C: guard_check(pid, iso(dos), proc="99490")
    for pid, p, number in C: askp(p, number=number, dos=ymd(dos), pid=pid, who="feed check", max_age_days=0)
    k = kinds()
    check("10 charts (8 good numbers, 1 wrong, 1 none) asked by a pre-claim-style, a guard-style and a feed-style caller: 11 requests (9 plain, 2 look-ups) instead of 30 look-ups",
          lambda: len(k) == 11 and k.count("CMS") == 9 and k.count("MBILUNOSSN") == 2, k)
    check("privacy: after the 10 charts the store, usage log and guard cache hold no Medicare number", lambda: not any(n in text_of(STORE) + text_of(ULOG) + text_of(DCACHE) for _, p, n in C if n) and not any(p["number"] in text_of(STORE) + text_of(ULOG) + text_of(DCACHE) for _, p, n in C))

# ==== 6. the engine's cascade step and the texts ==============================================================================
def t_engine():
    RA = load("tools/button/run_all.py", "run_all_under_test")
    ws = os.path.join(TMP, "engine_ws"); os.makedirs(ws, exist_ok=True)
    for f in ("precheck.py", "void_rules.py", "void_rules.json"):
        with open(os.path.join(ws, f), "w") as fh: fh.write("# stand-in file - the engine test never starts anything\n")
    a = argparse.Namespace(mode="live", stamp="T", ws=ws, out=os.path.join(TMP, "engine_out"), python=None, stedi_proxy=True, profile=None, steps="cascade", packages="", note="", run_url="")
    r = RA.Run(a); started = []
    r.helper = lambda name, argv, timeout=1800, env=None, cwd=None: (started.append(name), (0, "", ""))[1]
    out = io.StringIO()
    with contextlib.redirect_stdout(out): r.cascade()
    s = r.steps[-1]; said = [l for l in out.getvalue().splitlines() if "pre-claim" in l]
    check("engine: the cascade step no longer starts the pre-claim check (with a Stedi key and precheck.py present, only void_rules.py is started)", lambda: started == ["void_rules.py"], started)
    check("engine: it prints ONE line saying the nightly insurance cascade routine runs that check, and the step's report says the same",
          lambda: len(said) == 1 and "the nightly insurance cascade routine runs it once a night" in said[0] and "nightly insurance cascade routine" in s["summary"] and s["status"] == "ok", (said, s))
    src = _read("tools/button/run_all.py")
    check("engine: nothing in run_all.py starts precheck.py any more", lambda: not re.search(r"helper\(\s*['\"]precheck\.py", src))

def t_texts():
    pages = {"tools/button/billing_button_page.html": None, "desktop/ui.html": None}
    for rel in pages:
        m = re.search(r'<label for="s-cascade">(.*?)</label>', _read(rel), re.S); pages[rel] = m.group(1) if m else ""
    check("texts: the Billing Button page and the desktop app say for the cascade step that the nightly insurance cascade routine runs the pre-claim check",
          lambda: all("nightly insurance cascade routine" in t and "over the last 3 days of visits" not in t for t in pages.values()), pages)
    doc = _read("docs/BILLING_BUTTON.md"); expl = _read("tools/button/app_build_page.html")
    check("texts: the engine's documentation and explainer page no longer say the engine runs precheck.py",
          lambda: "| `cascade` |" in doc and "precheck.py --days 3 --max 120` (skipped" not in doc and "not started here" in doc and "pre-check runs once a night in the nightly insurance cascade routine" in expl)
    live = {os.path.basename(f): _read(os.path.relpath(f, ROOT)) for f in sorted(glob.glob(os.path.join(ROOT, "nightly", "live", "*.txt")))}
    starts = sorted(n for n, t in live.items() if re.search(r"python3 precheck\.py --", t))
    check("texts: the six-hourly run's evening start is gone - the nightly cascade routine is the one scheduled start (a Billing Button press may still start it by hand)",
          lambda: starts == ["billing_button.txt", "cascade.txt"] and "the pre-claim check is NOT started here" in live["columns.txt"], starts)

def t_copies():
    names = ("stedi.py", "deceased_guard.py", "precheck.py", "medicare_store.py", "amd.py", "elig_amd.py")
    diff = [n for n in names if _read("scripts/helpers/" + n) != _read("core/" + n)]
    check("copies: core/ holds the same stedi, deceased_guard, precheck, medicare_store, amd and elig_amd as scripts/helpers", lambda: diff == [], diff)

TESTS = [t_prices, t_usage_reader, t_shape, t_plain_good, t_not_found, t_wrong_number, t_suffix, t_no_number, t_down, t_other_refusal, t_ssn, t_med_summ,
         t_usage_log, t_cli, t_store]
GUARD_TESTS = [t_guard_death, t_guard_not_found_failed, t_guard_shared, t_guard_number, t_guard_flag_cache, t_guard_old_client, t_guard_charge,
               t_precheck_args, t_precheck_words, t_precheck_store, t_ten_charts]
LAST = [t_engine, t_texts, t_copies]
_PATH = list(sys.path)
def _run(t):
    try: t()
    except Exception:
        check("%s ran to its end" % t.__name__, False, traceback.format_exc()[-700:])
    finally:
        sys.path[:] = _PATH                                          # the client adds its own folder to sys.path - nothing of the checkout stays importable
        os.environ.update(MEDICARE_STORE=STORE, STEDI_USAGE_LOG=ULOG, DECEASED_CACHE=DCACHE)
for t in TESTS: _run(t)
reset(); DG = load("scripts/helpers/deceased_guard.py", "deceased_guard"); sys.modules["deceased_guard"] = DG     # from here on the client's hook feeds the REAL guard
check("guard: the guard is the real file, it uses the one cache path it is configured with, and its own request and key file are gone",
      lambda: DG.CACHE == DCACHE and DG.MAX_AGE_DAYS == 30 and not hasattr(DG, "KEYF") and not hasattr(DG, "STEDI") and "requests" not in _read("scripts/helpers/deceased_guard.py"))
for t in GUARD_TESTS + LAST: _run(t)
check("nothing was written in the checkout", lambda: _snapshot() == BEFORE, sorted(set(_snapshot().items()) ^ set(BEFORE.items()))[:5])
print("test_lookup_rules: %d checks, %d failed%s" % (COUNT[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:300]))
sys.exit(1 if FAILS else 0)
