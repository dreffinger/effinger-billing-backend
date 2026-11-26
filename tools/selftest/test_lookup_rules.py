#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the Medicare-answer rules - look-ups part A, 11/10/2026)
# Decides: nothing. Loads the vendor client (scripts/helpers/stedi.py), the Medicare answer store (medicare_store.py), the deceased-
#   patient guard (deceased_guard.py), the reader of AdvancedMD's free eligibility answer the guard uses (elig_amd.py, since 11/25/2026),
#   the nightly pre-claim check (precheck.py), the price table (stedi_prices.py), the usage reader
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
#     - the core/ copies are the scripts/helpers copies; nothing is written in the checkout;
#     - (11/10/2026 review fixes) the look-up goes with the chart's own last name, suffix and all; after a refusal of our provider number
#       the run sends no more plain checks; an answer asked before the claim's date of service is asked again by the guard; a date of
#       death a plain answer carried during the check blocks that claim; the pre-claim check never caches a failed call; an old-style
#       chart number still 'differs'; the store keeps the Advantage plan line; a temporary file of an atomic write is git-ignored;
#     - (11/10/2026 re-check fixes) a death the answer store already holds blocks the claim with no call when the guard's cache lacks it,
#       and still blocks when the guard's own call fails (also an answer about last month's visit); a failed look-up for a stored
#       'number differs' answer is not kept in the pre-claim check's cache for the month;
#     - (11/10/2026 second re-check, kept as it is) when the guard's own call fails, the death an OLDER kept answer shows blocks even when
#       a newer kept answer shows none, it goes into the guard's cache and the chart's next claim is blocked with no call - and the
#       guard's header says so.
#     - (11/25/2026, William: "do a stedi or advanced md check ... is stedi able to do that for free?") the guard asks AdvancedMD's FREE
#       eligibility check first, on the chart's Medicare plan (the plan whose number the vendor would be asked with), and buys the vendor's
#       answer only when the free check gives no usable answer: a date of death in the free answer blocks in the same words and buys
#       nothing; ACTIVE with Part A or Part B, no rejection and stamps of today keeps 'no death on record' and buys nothing; a rejection,
#       INACTIVE with no date, an unreadable answer, a status other than 200, a time-out, any error, an answer AdvancedMD kept from an
#       earlier day -> the paid call exactly as before, with the same arguments; no Medicare plan -> no free check; the switch
#       DEATH_CHECK_FREE=off; 3 failures in a row switch the free check off for the run; a death in the cache -> no call at all; an answer
#       the answer store already holds is used first, as before; a death the free check found still blocks when the cache file is lost
#       and nothing can be asked; COUNTS; nothing printed, nothing written in the working directory. The stand-in AdvancedMD answers the
#       free check 'Medicare cannot answer now' for every plan a test does not name, so every guard check written before that day runs
#       through the free check too and proves that an unusable free answer changes nothing.
#     - (11/25/2026, the independent review of that change - section 4c) a date-of-death segment whose date cannot be read (empty,
#       missing, null, blanks, a text that is no date) is never 'no death on record', beside ACTIVE lines too: the plain check is bought
#       as before; the note of a free date of death in the answer store leaves the store's 'asked and failed today' mark as it was, so
#       no helper buys the failing chart again that day; an answer that came but cannot be read is not 'down' and does not count toward
#       the 3; and the rules no check pinned before: the store is asked with the guard's 30 days and about the claim's own date of
#       service, only HTTP 200 is an answer, each of the answer's three stamps must be of today, a vendor call that raises is still
#       counted as bought; the marker the mirror holds for the guard is a string the guard carries.
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
os.environ.pop("DEATH_CHECK_FREE", None)          # 11/25/2026: the guard's free check runs as a workspace has it by default (on), whatever this shell says
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
WRONG = [mnum(i) for i in range(895, 900)]       # well-shaped numbers that belong to nobody (a chart holding one has a wrong number)
# (11/10/2026, third fix round) mnum() repeats every 900 and the invented people are numbered 1, 2, 3 ... - numbers 95 to 99 were
# also the 95th to 99th person's own, so one more person earlier in the run made a 'wrong' number that person's own; 895-899 are
# never reached (a check at the end proves no person holds one).
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
        return Resp(200, {"coveragesFound": 1, "items": [{"payer": dict(name="TEST MEDICAID"), "payerId": "77027", "subscriber": {"memberId": "D" + "7" * 7},
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
    p = p or dict(first="NOPLAN", last="ZZNOPLAN", dob8=ymd(datetime.date(1940, 1, 2)))     # dict(): the privacy gate reads a quoted capital word after "last": as a name
    CHARTS[str(pid)] = {"name": nm(last or p["last"], p["first"]), "dob": p["dob8"][4:6] + "/" + p["dob8"][6:] + "/" + p["dob8"][:4], "deceased": deceased, "plans": list(plans)}
    return str(pid)
def _chart_xml(pid):
    c = CHARTS[str(pid)]
    plans = "".join('<insplan id="ins%s" carrier="%s" begindate="%s" enddate="%s" x="" subscribernum="%s" y="" sequence="%d"/>' % (ins(pid, i + 1), car, mdy(datetime.date(2015, 1, 1)), end, num, i + 1)      # 11/25/2026: a plan id of its own per chart and plan (ins(), below) - the free check is asked by plan id
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

# ---- stand-in for AdvancedMD's FREE eligibility check, amd.check_eligibility (11/25/2026) -----------------------------------------
# The guard asks it FIRST. The stand-in answers per insurance-plan id from FREE; a plan no test names gets 'Medicare cannot answer now'
# (a rejection, AAA 42) - an answer that is NOT usable - so every guard check written before 11/25/2026 runs through the free check
# too and proves on its way that an unusable free answer leaves the paid path exactly as it was. An answer has the shape
# elig_amd.summarize reads (docs/captured_calls.md: <PPMDResults><Results ...><Edi271>...; or the same as JSON, attributes as "@name")
# and carries what a real one carries - the name, the Medicare number, the birth date - all invented and put together at run time.
import xml.etree.ElementTree as ET
FREE = {}                       # insurance-plan digits -> ("answer", body) / ("http", status[, body]) / ("timeout",) / ("raise",)
FREE_ASKED = []                 # every free check since the last reset(): (the plan id as the guard passed it, service type, time-out)
FREE_TOTAL = [0]                # every free check of the whole run (never reset)
def ins(pid, i=1):
    """The digits of the insurance-plan id of plan i (1 = the first) of an invented chart: what the free check is asked with."""
    return "%s%d" % (pid, i)
def amd_stamp(days_back=0):
    """A stamp as AdvancedMD writes it on an eligibility answer: its own clock, 7 hours behind UTC, MM/DD/YYYY HH:MMPM."""
    return (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=7, days=days_back)).strftime("%m/%d/%Y %I:%M%p")
def free271(p=None, status="active", parts=("MA", "MB"), death8=None, aaa=(), stamp=0, shape="xml"):
    """One free answer of the stand-in AdvancedMD. status: active (benefit lines with code 1) / inactive (code 6) / rejected or unknown (no
    benefit line); parts: the insurance types of the benefit lines; aaa: rejection codes; stamp: how many days back the answer's three own
    stamps are (a triple = created, changed, response; a word = written as it is; None = no stamp); shape 'json' = as AdvancedMD sometimes sends it.
    death8: the text of the answer's date-of-death segment (qualifier 442); a tuple = one such segment per item, in that order - '' is a segment
    with an empty date, None one with no date in it at all (the attribute left out; null in the JSON shape)."""
    p = p or dict(first="NOPLAN", last="ZZNOPLAN", dob8=ymd(datetime.date(1940, 1, 2)), number="")
    root = ET.Element("PPMDResults")
    res = ET.SubElement(root, "Results", dict(eligibilityid="89" + "2" * 5, eligibilitystatusid="1" if status in ("active", "inactive") else "20",
                                              patientname=nm(p["last"], p["first"]), subscriberid=p.get("number") or ""))
    if stamp is not None:
        for k, d in zip(("eligibilitycreatedat", "eligibilitychangedat", "eligibilityresponsedate"), stamp if isinstance(stamp, tuple) else (stamp,) * 3):
            res.set(k, d if isinstance(d, str) else amd_stamp(d))
    edi = ET.SubElement(res, "Edi271")
    for code in aaa: ET.SubElement(edi, "RequestValidation", dict(AAA01_ValidRequestIndicator="Y", AAA03_RejectReasonCode=code, AAA04_FollowUpActionCode="C"))
    sub = ET.SubElement(edi, "Subscriber")
    ET.SubElement(sub, "Name", dict(NM101_EntityIdentifierCode="IL", NM103_LastOrOrganizationalName=p["last"], NM104_FirstName=p["first"], NM109_IdentificationCode=p.get("number") or ""))
    ET.SubElement(sub, "DemographicInformation", dict(DMG02_DateTimePeriod=p["dob8"], DMG03_GenderCode="F"))
    for d in (death8 if isinstance(death8, tuple) else ((death8,) if death8 else ())):
        seg = dict(DTP01_DateTimeQualifier="442", DTP02_DateTimePeriodFormatQualifier="D8")
        if d is not None or shape != "xml": seg["DTP03_DateTimePeriod"] = d       # None: the segment carries no date (11/25/2026 review, finding 1)
        ET.SubElement(sub, "DTPSegment", seg)
    for typ in (parts if status in ("active", "inactive") else ()):
        w = ET.SubElement(sub, "EligibilityOrBenefitInformation")
        ET.SubElement(w, "EligibilityOrBenefitInformation", dict(EB01_EligibilityOrBenefitInformationCode="1" if status == "active" else "6", EB03_ServiceTypeCode="30", EB04_InsuranceTypeCode=typ))
        ET.SubElement(w, "DTPSegment", dict(DTP01_DateTimeQualifier="291", DTP03_DateTimePeriod=ymd(datetime.date(2015, 1 if typ == "MA" else 2, 1))))
    if shape == "xml": return ET.tostring(root, encoding="unicode")
    def conv(e):                                           # the JSON shape: attributes as "@name", a repeated child as a list
        d = {"@" + k: v for k, v in e.attrib.items()}
        for c in e: d[c.tag] = conv(c) if c.tag not in d else (d[c.tag] if isinstance(d[c.tag], list) else [d[c.tag]]) + [conv(c)]
        return d
    return {root.tag: conv(root)}
def _amd_free(insplan_id, stc="30", timeout=120):
    FREE_ASKED.append((str(insplan_id), stc, timeout)); FREE_TOTAL[0] += 1
    ov = FREE.get(re.sub(r"\D", "", str(insplan_id)))
    if ov is None: return 200, free271(status="rejected", aaa=("42",))      # nothing said about this plan: Medicare cannot answer now - not a usable answer
    if ov[0] == "timeout": raise FakeTimeout("read timed out")
    if ov[0] == "raise": raise RuntimeError("connection reset")
    if ov[0] == "http": return ov[1], (ov[2] if len(ov) > 2 else "<html><body>the stand-in's error page</body></html>")
    return 200, ov[1]
fake_amd.check_eligibility = _amd_free

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
    if hasattr(ST, "_PLAIN_OFF"): del ST._PLAIN_OFF[:]           # a refusal of our provider number holds for one run (one process) - each case is a new run
    if DG is not None: del DG.LOG[:]; DG._ASKED.clear(); getattr(DG, "_LOST_ASKED", set()).clear(); getattr(DG, "_UNSAVED", {}).clear(); getattr(DG, "_NONE_SAID", set()).clear()      # ... and the charts asked about for a lost day (one question per chart per start), and what a start kept in memory because it could not write it
    del FREE_ASKED[:]; FREE.clear(); os.environ.pop("DEATH_CHECK_FREE", None)      # 11/25/2026: the free check - each case is a new run: nothing said about any plan, the switch not set,
    if DG is not None:                                                             # COUNTS at zero and no failure in a row behind it
        for k in getattr(DG, "COUNTS", {}): DG.COUNTS[k] = 0
        if hasattr(DG, "_FREE_FAILS"): DG._FREE_FAILS[0] = 0
        if hasattr(DG, "_FREE"): DG._FREE.clear()
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
    check("client: suffix and still not found -> exactly two plain checks and ONE look-up, sent with the chart's OWN last name (suffix and all, as every caller sent it before)",
          lambda: kinds() == ["CMS", "CMS", "MBILUNOSSN"] and SENT[1][1]["subscriber"]["lastName"] == p["last"] and SENT[2][1]["subscriber"]["lastName"] == p["last"] + " JR"
          and how == "lookup after plain", (kinds(), [b["subscriber"]["lastName"] for _, b in SENT]))
    # review B1: Medicare matches the last name WITH its suffix (rules.md 10/4). A chart named 'X JR' with an outdated number: the plain check
    # and its retry without the suffix both miss; the look-up must go with 'X JR' - stripped, it missed a death the old look-up found.
    reset(); pj = newp(death=ago(9)); pj["last"] = pj["last"] + " JR"; pid = cid()
    j, how, err = askp(pj, number=WRONG[1], dos=ymd(ago(3)), pid=pid)
    check("client: Medicare holds the name WITH its suffix and the chart's number is outdated -> the look-up by the chart's own name finds the record (Medicare's own number, the date of death)",
          lambda: kinds() == ["CMS", "CMS", "MBILUNOSSN"] and how == "lookup after plain" and not j.get("errors") and j["subscriber"]["memberId"] == pj["number"]
          and ST.med_summ(j)["death"] == pj["death8"] and (store_chart(pid).get("answers") or [{}])[0].get("number_differs") is True, (kinds(), how, j.get("errors")))

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
    # review S5: a refusal of OUR provider number (41, 43, 50, 51, 97) holds for every chart - after the first one the run sends no plain check
    res = []
    for code in ("41", "97", "43"):
        reset(); five = [newp() for _ in range(5)]
        for q in five: OVERRIDE[("CMS", q["number"])] = ("answer", err_answer(code, {"memberId": q["number"]}))
        hows = [askp(q, dos=ymd(ago(1)), pid=cid())[1] for q in five]
        res.append((code, kinds(), hows, list(ST.NOTES)))
    check("client: Medicare refuses OUR provider number (41 / 97 / 43) -> ONE plain check in the run, then every chart goes straight to the look-up (1 plain + 5 look-ups, not 5 + 5); one report line says so",
          lambda: all(r[1] == ["CMS"] + ["MBILUNOSSN"] * 5 and r[2] == ["lookup after plain"] + ["lookup"] * 4 and len(r[3]) == 1 and "no plain check" in r[3][0]
                      and "Medicare refused the plain check (%s) - the look-up was bought instead" % r[0] in r[3][0] for r in res), res)
    reset(); p = newp(); q = newp(); OVERRIDE[("CMS", p["number"])] = ("answer", err_answer("61", {"memberId": p["number"]}))
    askp(p, dos=ymd(ago(1)), pid=cid()); j, how, err = askp(q, dos=ymd(ago(1)), pid=cid())
    check("client: a refusal about the patient (61) does not switch the plain check off for the next chart", lambda: kinds() == ["CMS", "MBILUNOSSN", "CMS"] and how == "plain", kinds())

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
    tmps = ["practices/ehpa/registers/.deceased_cache.abc123.tmp", "practices/ehpa/registers/.claim_status_ledger.abc123.tmp", "scripts/helpers/registers/.claim_status_ledger.abc123.tmp"]
    ign = [subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", r], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode for r in tmps]
    check("store: the temporary file an interrupted atomic write leaves (guard cache, claim-status ledger) is git-ignored even inside a tracked folder (ops N2)",
          lambda: ign == [0] * len(tmps), dict(zip(tmps, ign)))
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
    reset(); pid = cid(); many = [{"code": "X", "type": "MA", "typeName": "x", "plan": "x", "dates": {}, "entity": [["TEST FACILITY", "F%02d" % i]]} for i in range(21)]
    plan_line = {"code": "U", "type": "HM", "typeName": "x", "plan": "TEST ADVANTAGE PLAN", "dates": {}, "entity": [["TEST ADVANTAGE", "H" + str(4521)]]}
    MS.put(pid, dict(facts, other=many + [plan_line]), "plain", "x", dos); got = MS.get(pid, 0, dos) or {}
    check("store: more than 20 other-payer lines - the Advantage plan line is still kept (plan lines first, the 20-line cut falls on the others; review S4)",
          lambda: len(got.get("other") or []) == 20 and got["other"][0]["code"] == "U" and got["other"][0]["entity"][0][0] == "TEST ADVANTAGE", [o.get("code") for o in got.get("other") or []])
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
    r = guard_check(pid, iso(ago(25)))                                                          # a claim dated BEFORE that answer was asked (review S1)
    check("guard: an answer another helper got 20 days ago is used, and the guard's 30 days count from THAT day (cache 'checked' = the day Medicare was asked) - for a claim dated on or before that day",
          lambda: SENT == [] and r == (False, "") and cache_json()[pid]["checked"] == iso(ago(20)), cache_json())
    reset(); q = newp(); pid = chart(cid(), q, plans=[("car6085", "", q["number"])])
    askp(q, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=0); os.remove(DCACHE)
    store_edit(lambda d: d["charts"][pid]["answers"][0].update(asked=iso(ago(31)))); del SENT[:]
    guard_check(pid, iso(ago(33)))                                                              # a claim dated before that answer: only the 30 days decide
    check("guard: an answer 31 days old is not used by the guard - it asks again (a claim dated before that answer, so only the 30 days decide)",
          lambda: kinds() == ["CMS"] and cache_json()[pid]["checked"] == iso(TODAY))

def t_guard_review():
    # review S1: an answer (shared, or the guard's own cache entry) asked BEFORE the claim's date of service cannot know of a death since
    res = []
    for where in ("the guard's own cache entry", "a shared answer in the store (the guard's cache lost)"):
        reset(); q = newp(); pid = chart(cid(), q, plans=[("car6085", "", q["number"])])
        askp(q, dos=ymd(ago(5)), pid=pid, who="pre-claim check", max_age_days=0)             # alive when asked: a plain answer, and the hook's cache entry
        if where.startswith("the guard's"):
            c = cache_json(); c[pid]["checked"] = iso(ago(20)); os.remove(STORE)
            with open(DCACHE, "w") as fh: json.dump(c, fh)
        else:
            store_edit(lambda d: d["charts"][pid]["answers"][0].update(asked=iso(ago(20)))); os.remove(DCACHE)
        q["death8"] = ymd(ago(10)); del SENT[:]                                               # the patient died after that answer was asked
        r = guard_check(pid, iso(ago(5))); res.append((where, r, kinds()))
    check("guard: an answer asked BEFORE the claim's date of service (20 days ago, the claim 5 days ago) is not taken as 'no death' - ONE plain check asks again and a death since then blocks the claim (review S1)",
          lambda: all(r[2] == ["CMS"] and r[1][0] is True and "after date of death %s" % iso(ago(10)) in r[1][1] for r in res), res)
    reset(); q = newp(); pid = chart(cid(), q, plans=[("car6085", "", q["number"])]); later = iso(TODAY + datetime.timedelta(days=3))
    r1 = guard_check(pid, later); r2 = guard_check(pid, later)
    check("guard: a claim dated after today is asked about once - today's answer is the newest there can be, so a second check the same day buys nothing",
          lambda: kinds() == ["CMS"] and r1 == r2 == (False, "") and cache_json()[pid]["checked"] == iso(TODAY), kinds())
    # review N1: a plain answer with error 61 carries the date of death; the look-up after it times out - the date already known blocks THIS claim
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])])
    OVERRIDE[("CMS", p["number"])] = ("answer", {"errors": [{"code": "61", "description": DESC["61"]}], "subscriber": {"memberId": p["number"]}, "benefitsInformation": [],
                                                  "planDateInformation": {"dateOfDeath": ymd(ago(10))}})
    OVERRIDE[("MBILUNOSSN", p["last"])] = ("timeout",)
    r = guard_check(pid, iso(ago(5)))
    check("guard: a plain answer with error 61 and a date of death, then a look-up that times out -> THIS claim is blocked by that date, not logged UNVERIFIED (review N1)",
          lambda: kinds() == ["CMS", "MBILUNOSSN"] and r[0] is True and "after date of death %s" % iso(ago(10)) in r[1] and DG.LOG == [], (kinds(), r, DG.LOG))
    # re-check NEW-1: the answer store already holds a death (an answer asked BEFORE the claim's date of service); the guard's own cache
    # lacks it (lost, cut off, or scrubbed to the gate's placeholder); Medicare is down (42, a time-out) or would answer - the death is
    # used as it is: the claim is blocked, no call is bought, no UNVERIFIED line
    res = []
    for cache in ("lost", "cut off", "scrubbed"):
        for now in (("answer", err_answer("42")), ("timeout",), None):
            reset(); p = newp(death=ago(4)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); dos = ago(2)
            askp(p, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=0)                  # a plain answer that shows the death
            store_edit(lambda d: d["charts"][pid]["answers"][0].update(asked=iso(ago(3))))       # asked BEFORE the claim's date of service
            if cache == "lost": os.remove(DCACHE)
            else:
                with open(DCACHE, "w") as fh: fh.write('{"' + pid + '": {"do' if cache == "cut off" else json.dumps({pid: {"dod": "[DOB]", "checked": iso(ago(3)), "src": "stedi-medicare-271"}}))
            if now: OVERRIDE[("CMS", p["number"])] = now; OVERRIDE[("MBILUNOSSN", p["last"])] = now
            del SENT[:]; r = guard_check(pid, iso(dos)); res.append((cache, now and now[0], r, kinds(), list(DG.LOG)))
    check("guard: a death the answer store already holds (asked before the claim's date of service), the guard's cache lost, cut off or scrubbed, Medicare down or not -> blocked by that death, no call bought, no UNVERIFIED line (re-check NEW-1)",
          lambda: len(res) == 9 and all(x[2][0] is True and "after date of death %s" % iso(ago(4)) in x[2][1] and x[3] == [] and x[4] == [] for x in res), [x for x in res if not (x[2][0] is True and x[3] == [])][:3])
    # ... and when the store's month rule hides that answer (it was about last month's visit) and the guard's own call fails, the death
    # any kept answer shows still blocks the claim (medicare_store.death)
    res = []
    for now in (("answer", err_answer("42")), ("timeout",)):
        reset(); last_month = first_of_month(TODAY) - datetime.timedelta(days=5); p = newp(death=last_month - datetime.timedelta(days=5))
        pid = chart(cid(), p, plans=[("car6085", "", p["number"])])
        askp(p, dos=ymd(last_month), pid=pid, who="pre-claim check", max_age_days=0); os.remove(DCACHE)
        OVERRIDE[("CMS", p["number"])] = now; OVERRIDE[("MBILUNOSSN", p["last"])] = now; del SENT[:]
        r = guard_check(pid, iso(first_of_month(TODAY)), proc="99490"); res.append((now[0], r, kinds(), list(DG.LOG), _try(lambda: MS.death(pid))))
    check("guard: a death in a stored answer about LAST month's visit, the guard's cache lost, and its own call for this month's claim fails (42 / time-out) -> still blocked by that death, not UNVERIFIED (re-check NEW-1)",
          lambda: all(x[1][0] is True and "after date of death %s" % iso(last_month - datetime.timedelta(days=5)) in x[1][1] and x[2] == ["CMS"] and x[3] == [] for x in res)
          and res[0][4] == ymd(last_month - datetime.timedelta(days=5)), res)
    # second re-check R2-2 (kept as it is - it errs toward blocking): Medicare's older kept answer showed a death, its newer kept answer
    # shows none (a corrected record); the guard's cache holds the hook's 'no death on record', asked before the claim's date of service;
    # the guard's own call fails (42) -> the EARLIEST death a kept answer shows blocks, goes into the guard's cache, and the chart's next
    # claim is blocked with no call although Medicare would now answer 'no death'. The guard's header says so.
    reset(); p = newp(death=ago(16)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])])
    askp(p, dos=ymd(ago(15)), pid=pid, who="pre-claim check", max_age_days=0)                      # the older answer: it shows the death
    store_edit(lambda d: d["charts"][pid]["answers"][0].update(asked=iso(ago(14))))
    p["death8"] = None                                                                             # a corrected record: no death any more
    askp(p, dos=ymd(ago(7)), pid=pid, who="pre-claim check", max_age_days=0)                       # the newer answer: no death
    store_edit(lambda d: d["charts"][pid]["answers"][-1].update(asked=iso(ago(6))))
    c = cache_json() or {}; hook_kept = (c.get(pid) or {}).get("dod")      # (the independent check of the second round, D4 - written 11/25/2026) the hook no longer writes the newer answer's 'no death on record' over the day the older answer brought - the guard's cache keeps the death ...
    c[pid] = {"dod": None, "checked": iso(ago(6)), "src": "stedi: no death on record"}      # ... so the case this check is about is put there by hand: a cache that says 'no death on record' while the answer store still holds the older answer (a death taken off the record by hand; a cache refilled from elsewhere)
    with open(DCACHE, "w") as fh: json.dump(c, fh)
    kept = [bool(a.get("death")) for a in sorted(store_chart(pid).get("answers") or [], key=lambda a: str(a.get("asked")))]; was = dict(c.get(pid) or {})
    OVERRIDE[("CMS", p["number"])] = ("answer", err_answer("42")); OVERRIDE[("MBILUNOSSN", p["last"])] = ("answer", err_answer("42")); del SENT[:]
    r1 = guard_check(pid, iso(ago(2))); k1 = kinds(); dod1 = ((cache_json() or {}).get(pid) or {}).get("dod")
    OVERRIDE.clear(); del SENT[:]; r2 = guard_check(pid, iso(ago(1))); k2 = kinds()
    head = " ".join(l.lstrip("# ") for l in _read("scripts/helpers/deceased_guard.py").split("\nimport ", 1)[0].splitlines() if l.startswith("#"))
    check("guard: its own call fails (42) - the death an OLDER kept answer shows blocks even though a NEWER kept answer shows none (the earliest death counts), it goes into the guard's cache and the chart's next claim is blocked with no call; the guard's header says it errs toward blocking (second re-check R2-2, kept as it is)",
          lambda: kept == [True, False] and hook_kept == iso(ago(16)) and was.get("dod") is None and r1[0] is True and "after date of death %s" % iso(ago(16)) in r1[1] and k1 == ["CMS"] and dod1 == iso(ago(16))
          and r2[0] is True and k2 == [] and "That fallback takes the EARLIEST date of death any kept answer shows, even when a newer kept answer shows none" in head
          and "it errs toward blocking, as this cache itself keeps a death for good" in head, (kept, hook_kept, was, r1, k1, dod1, r2, k2))

def t_guard_number():
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", mdy(ago(400)), WRONG[0]), ("car6085", "", spaced(p["number"])), ("car6404", "", "M" + "5" * 9)])
    guard_check(pid, iso(ago(2)))
    check("guard: it takes the member number of the chart's OPEN Medicare Part B plan (car6085) and asks the plain check; the usage log says 'guard'",
          lambda: kinds() == ["CMS"] and SENT[0][1]["subscriber"]["memberId"] == p["number"] and log_lines()[0][1] == "guard" and log_lines()[0][4] == pid)
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", mdy(ago(100)), p["number"]), ("car6085", mdy(ago(900)), WRONG[1])])
    guard_check(pid, iso(ago(2)))
    check("guard: no open Medicare plan -> the number of the one that ended last", lambda: kinds() == ["CMS"] and SENT[0][1]["subscriber"]["memberId"] == p["number"])
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6404", "", "M" + "6" * 9)])
    r = guard_check(pid, iso(ago(2)), carrier=None, proc="99490")      # (the sixth round, 11/26/2026: a care-management charge is looked up where the caller does not know the payer - the feed's entry check; billed to another payer it never is)
    check("guard: a care-management chart with no Medicare plan keeps the look-up by name, counted as 'guard, no Medicare plan on the chart' (a care-management charge whose payer the caller does not know - the sixth round)",
          lambda: kinds() == ["MBILUNOSSN"] and log_lines()[0][1] == "guard, no Medicare plan on the chart" and r == (False, ""))
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", "")]); guard_check(pid, iso(ago(2)))
    check("guard: a Medicare plan with no number -> the look-up, still counted as 'guard'", lambda: kinds() == ["MBILUNOSSN"] and log_lines()[0][1] == "guard")
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); r = guard_check(pid, iso(ago(2)), carrier="car6404", proc="99213")
    check("guard: a claim that is neither straight Medicare nor care management asks nothing (as before)", lambda: SENT == [] and r == (False, ""))

def t_guard_flag_cache():
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=mdy(ago(30)))
    r = guard_check(pid, iso(ago(5)))
    check("guard: the chart's own deceased flag still comes first - blocked from it, no vendor request", lambda: r[0] is True and SENT == [] and cache_json()[pid]["dod"] == iso(ago(30)))
    # (11/25/2026, the independent check of the second round: 'a deceased flag with no date counts the date of service as the date' was pinned here until that day -
    #  the claim was cleared by its own date. What such a flag is now: t_guard_flag_no_day, below.)
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
    reset(); nb = newp(beneficiary=False); pid = chart(cid(), nb, plans=[("car6404", "", "M" + "7" * 9)]); r = guard_check(pid, iso(ago(2)), carrier=None, proc="99490")      # (a care-management charge whose payer the caller does not know - the sixth round)
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

# ==== 4a2. the second verification (11/25/2026) of the change that asks AdvancedMD first - each check names its finding ============
def put_cache(entries):
    os.makedirs(os.path.dirname(DCACHE), exist_ok=True)
    with open(DCACHE, "w") as fh: json.dump(entries, fh)
def t_guard_day_shapes():
    """guard#1: a day the cache holds in another shape than YYYY-MM-DD was read as 'unknown', and a claim to another payer passed with no word."""
    reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6404", "", "M" + "5" * 9)])
    put_cache({pid: {"dod": ymd(ago(20)), "src": "a helper that wrote the day as eight digits"}})
    r = guard_check(pid, iso(ago(5)), carrier="car6404", proc="99349")
    check("guard (day shapes): a day the cache holds as EIGHT DIGITS is a day - a claim to any payer dated after it is blocked with no call at all (it used to pass as 'unknown' and was never asked about for a plan that is not Medicare)",
          lambda: r[0] is True and iso(ago(20)) in r[1] and SENT == [] and FREE_ASKED == [], (r, len(SENT), len(FREE_ASKED)))
    put_cache({pid: {"dod": mdy(ago(20)), "checked": None, "src": "x"}}); r2 = guard_check(pid, iso(ago(5)), carrier="car6404", proc="99349"); r3 = guard_check(pid, iso(ago(25)), carrier="car6404", proc="99349")
    check("guard (day shapes): ... the same for a day written MM/DD/YYYY; a date of service BEFORE the day is not blocked; and an entry whose 'checked' is null (the Drive copy writes that) raises nothing",
          lambda: r2[0] is True and r3 == (False, "") and SENT == [], (r2, r3))
    put_cache({pid: {"dod": "%d-02-31" % TODAY.year, "checked": "not a day", "src": "x"}})
    check("guard (day shapes): a 'day' that is no calendar date, and a 'checked' that is no day, raise nothing - the entry is one whose day cannot be read (below)",
          lambda: _raises(lambda: guard_check(pid, iso(ago(5)), carrier="car6404", proc="99349"), DG.DayLost) or True)
def t_guard_day_lost():
    """guard#1 (the scrubbed copy), gate#1: a death on record whose day cannot be read here was asked about only for Medicare and care-management claims.
    The sixth round (11/26/2026, William: "i think only straight medicare is where i really dont want the charges after death to go"; "Medicare decides: bill"): such a
    chart is asked about for a charge billed to straight Medicare or whose payer the caller does not know - never for a charge billed to a payer known not to be straight
    Medicare, which it never holds - and Medicare's answer decides; the one wait left is the one where Medicare cannot be asked."""
    reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6404", "", "M" + "6" * 9), ("car6085", "", p["number"])])
    put_cache({pid: {"dod": "[DOB]", "checked": iso(TODAY), "src": "stedi-medicare-271"}}); free_death(pid, p, i=2)
    r = guard_check(pid, iso(ago(5)))
    check("guard (day lost): a death on record whose day cannot be read here (the scrubbed copy from the repository) is asked about again for a straight-Medicare charge - AdvancedMD's free check first - and the day it brings blocks the claim",
          lambda: r[0] is True and iso(ago(20)) in r[1] and len(FREE_ASKED) == 1 and SENT == [] and (cache_json() or {}).get(pid, {}).get("dod") == iso(ago(20)), (r, FREE_ASKED, len(SENT)))
    reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6404", "", "M" + "6" * 9), ("car6085", "", p["number"])])
    put_cache({pid: {"dod": "[DOB]", "checked": iso(TODAY), "src": "stedi-medicare-271"}}); free_death(pid, p, i=2)
    other = [says(lambda: guard_check(pid, iso(ago(5)), carrier=c_, proc=k_)) for c_, k_ in (("car6404", "99349"), ("car6404", "99490"))] + [says(lambda: DG.check(pid, iso(ago(5)), "car6404", "99349", allow_lookup=False))]
    check("guard (A1, the sixth round - ONLY STRAIGHT MEDICARE): a charge billed to a payer KNOWN not to be straight Medicare - an ordinary code or a care-management code, with a look-up allowed or from the cache only - is never looked up and never held by a death on record whose day cannot be read: not blocked, nobody asked, the entry as it was",
          lambda: other == [(False, "")] * 3 and FREE_ASKED == [] and SENT == [] and BILLING == [] and (cache_json() or {}).get(pid, {}).get("dod") == "[DOB]", (other, len(FREE_ASKED), len(SENT), cache_json()))
    reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6404", "", "M" + "6" * 9), ("car6085", "", p["number"])])
    put_cache({pid: {"dod": "[DOB]", "checked": iso(TODAY), "src": "stedi-medicare-271"}}); FREE[ins(pid, 2)] = ("timeout",); OVERRIDE[("CMS", p["number"])] = ("timeout",); OVERRIDE[("MBILUNOSSN", p["last"])] = ("timeout",)
    lost = _raises(lambda: guard_check(pid, iso(ago(5))), DG.DayLost)
    check("guard (day lost): ... and when neither AdvancedMD nor the vendor answers, the claim is NOT cleared: the guard raises DayLost (amd.rebill_charge then answers 409 and sends nothing; the check before approvals says NOT CHECKED) - the entry and its mark stay as they were",
          lambda: lost and (cache_json() or {}).get(pid, {}).get("dod") == "[DOB]" and issubclass(DG.DayLost, RuntimeError), (lost, cache_json(), DG.LOG))
    check("guard (day lost): ... and NO 'date of death UNVERIFIED' line is logged for such a chart (the independent check of that round, finding 13): that line says 'not a block - the charge went on', and this claim did not - its caller says NOT CHECKED or holds the visit. The feed's count 'date of death UNVERIFIED xN' is of the guard's LOG lines, so it counts only charges that went on",
          lambda: lost and DG.LOG == [] and len(SENT) + len(FREE_ASKED) >= 2, (DG.LOG, len(SENT), len(FREE_ASKED)))
    q = newp(); other = chart(cid(), q, plans=[("car6085", "", q["number"])]); FREE[ins(other)] = ("timeout",); OVERRIDE[("CMS", q["number"])] = ("timeout",); OVERRIDE[("MBILUNOSSN", q["last"])] = ("timeout",)
    went_on = guard_check(other, iso(ago(5)))
    check("guard (day lost): ... while a chart with NO death on record whose look-up fails in the same start is logged as before - one line, and that charge is not blocked", lambda: went_on == (False, "") and DG.LOG == [UNVERIFIED % (other, iso(ago(5)))], (went_on, DG.LOG))
    cache_only = _raises(lambda: DG.check(pid, iso(ago(5)), None, "99349", allow_lookup=False), DG.DayLost)
    check("guard (day lost): ... a question from the cache only (a dry run) about a charge whose payer is not known is not cleared either; a chart with NO death on record, or with a readable day, is answered from the cache as before",
          lambda: cache_only and (put_cache({pid: {"dod": None, "checked": iso(TODAY), "src": "stedi: no death on record"}}) or DG.check(pid, iso(ago(5)), "car6404", "99349", allow_lookup=False) == (False, "")), cache_only)
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); put_cache({pid: {"dod": "[DOB]", "checked": iso(TODAY), "src": "x"}}); free_is(pid, p=p)
    nolog = len(DG.LOG); r = says(lambda: guard_check(pid, iso(ago(5)))); asked = len(FREE_ASKED) + len(SENT)
    check("guard (A2, the sixth round - MEDICARE DECIDES): ... when Medicare answers and shows NO death the straight-Medicare claim is BILLED (William 11/26/2026, 'Medicare decides: bill' - until then it stayed not cleared): not blocked, the entry stays exactly as it was (a later answer may name the day again), and the guard's log gets ONE line 'TOP OF REPORT: pat<chart>: ...' about a recorded death whose day cannot be read - no 'unverified' line for an answer that came",
          lambda: r == (False, "") and (cache_json() or {}).get(pid, {}).get("dod") == "[DOB]" and DG.LOG[nolog:] == ["TOP OF REPORT: pat%s: %s" % (pid, DG.TOP_LOST)] and asked >= 1, (r, cache_json(), DG.LOG[nolog:]))
    r2 = says(lambda: guard_check(pid, iso(ago(4)))); r3 = says(lambda: DG.check(pid, iso(ago(3)), None, None, allow_lookup=False))
    check("guard (A2): ... and a second question about that chart in the same start - another date, and one from the cache only - gives the same answer without asking again and without a second line",
          lambda: r2 == r3 == (False, "") and len(FREE_ASKED) + len(SENT) == asked and DG.LOG[nolog:] == ["TOP OF REPORT: pat%s: %s" % (pid, DG.TOP_LOST)], (r2, r3, len(FREE_ASKED), len(SENT), asked, DG.LOG[nolog:]))
    DG._LOST_ASKED.clear(); took = DG._answered(ALIVE_271); DG.record(pid, ALIVE_271)
    check("guard (day lost): ... the hook that keeps every Medicare answer (record) does not write 'no death on record' over such an entry either - it would clear the chart behind the guard's back in the next start (asked with an answer record() really takes: Part A and Part B lines, no error - the independent check found this check passing with the rule switched off, because its answer was one record() passes over)",
          lambda: took is True and (cache_json() or {}).get(pid, {}).get("dod") == "[DOB]", (took, cache_json()))
ALIVE_271 = {"benefitsInformation": [{"code": "1", "insuranceTypeCode": "MA"}, {"code": "1", "insuranceTypeCode": "MB"}], "errors": []}      # a Medicare answer that shows no death and that record() really takes (_answered): Part A and Part B lines, no error
def t_guard_record_keeps():
    """The independent check of the second round, new finding 4 (D4): record() still wrote 'no death on record' over a day the cache could READ - the guard
    forgot a death, although its header says it keeps one for good. An answer WITHOUT a day never replaces an entry that holds a dod, readable or not."""
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); day = iso(ago(40)); held = {"dod": day, "checked": iso(ago(9)), "src": "amd-271", "name": "kept as it was"}
    put_cache({pid: dict(held)}); before = guard_check(pid, iso(ago(5)), carrier="car6404", proc="99309")
    r = DG.record(pid, json.loads(json.dumps(ALIVE_271))); after = guard_check(pid, iso(ago(5)), carrier="car6404", proc="99309"); ccm = guard_check(pid, iso(ago(5)), carrier="car6085", proc="99487")
    check("guard (record keeps a death): the cache holds a day it can READ and a claim after it is blocked; another helper's Medicare answer shows NO death and the client's hook hands it to record() - the entry stays exactly as it was, and the same claim and a straight-Medicare care-management claim are STILL blocked, with nobody asked (they both passed before: the guard had forgotten the death)",
          lambda: DG._answered(ALIVE_271) is True and before[0] is True and r is None and after[0] is True and ccm[0] is True and cache_json()[pid] == held and SENT == [] and FREE_ASKED == [], (before, r, after, ccm, cache_json()))
    DG.record(pid, err_answer("72")); DG.record(pid, {"errors": [], "benefitsInformation": [{"code": "1", "insuranceTypeCode": "MB"}], "stored": {"asked": iso(TODAY)}})
    check("guard (record keeps a death): ... neither does a look-up's lone 72 ('not a Medicare beneficiary' - or a look-up that hit another person) nor an answer read back from the answer store undo it",
          lambda: cache_json()[pid] == held, cache_json())
    put_cache({pid: {"dod": "[DOB]", "checked": iso(ago(9)), "src": "x"}}); DG.record(pid, json.loads(json.dumps(ALIVE_271))); DG.record(pid, err_answer("72"))
    check("guard (record keeps a death): ... the same for an entry whose day cannot be read here (the placeholder): it stays, whatever answer without a day comes",
          lambda: cache_json()[pid] == {"dod": "[DOB]", "checked": iso(ago(9)), "src": "x"}, cache_json())
    got = DG.record(pid, {"dateOfDeath": ymd(ago(30))}, "amd-271")
    check("guard (record keeps a death): an answer WITH a day is still taken - it is the day from then on", lambda: got == iso(ago(30)) and cache_json()[pid]["dod"] == iso(ago(30)) and cache_json()[pid]["src"] == "amd-271", (got, cache_json()))
    a, b = cid(), cid(); put_cache({a: {"dod": None, "checked": iso(ago(20)), "src": "stedi: no death on record", "name": "kept too"}})
    DG.record(a, json.loads(json.dumps(ALIVE_271))); DG.record(b, json.loads(json.dumps(ALIVE_271))); c = cache_json()
    check("guard (record keeps a death): and nothing else changed - for a chart with NO death on record, or with no entry at all, 'no death on record' is written as before (checked today, the entry's name kept)",
          lambda: c[a] == {"dod": None, "checked": iso(TODAY), "name": "kept too", "src": "stedi: no death on record"} and c[b]["dod"] is None and c[b]["checked"] == iso(TODAY) and c[b]["src"] == "stedi: no death on record", c)
def t_guard_charge_unreadable():
    """guard#3: check_charge answered 'not blocked' on a charge whose own read showed nothing to compare - amd.rebill_charge then sent the rebill."""
    reset(); p = newp(death=ago(30)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); put_cache({pid: {"dod": iso(ago(30)), "checked": iso(TODAY), "src": "x"}})
    shapes = {"556": "<Fault><detail>the charge could not be read</detail></Fault>", "557": '<r><patient id="pat%s"/><charge id="charge557" proccode="99309"/></r>' % pid,
              "558": '<r><visit date=""/><patient id="pat%s"/><charge id="charge558" proccode="99309"/></r>' % pid, "559": '<r><visit date="%s"/><patient id="pat%s"/><charge id="charge000" proccode="99309"/></r>' % (mdy(ago(3)), pid),
              "560": '<r><visit date="%s"/><charge id="charge560" proccode="99309"/></r>' % mdy(ago(3))}
    RESAVE.update(shapes)
    got = {k: _raises(lambda k=k: DG.check_charge(k, 1), DG.Unreadable) for k in shapes}
    check("guard (charge): a charge whose own read shows nothing to compare - a Fault, no visit, no visit date, no row of that charge, no chart - is NOT cleared: check_charge raises Unreadable in fixed words (amd.rebill_charge answers 409 on it and sends nothing)",
          lambda: all(got.values()) and issubclass(DG.Unreadable, RuntimeError), got)
    RESAVE["561"] = '<r><visit date="%s"/><patient id="pat%s"/><charge id="charge561" proccode="99309"/><insplan sequence="1" carrier="car6085"/></r>' % (mdy(ago(3)), pid)
    RESAVE["562"] = '<r><visit date="%s"/><patient id="pat%s"/><charge id="charge562" proccode="99309"/><insplan sequence="1" carrier="car6085"/></r>' % (mdy(ago(40)), pid)
    check("guard (charge): ... a charge that can be read is answered as before - blocked after the day, not blocked before it", lambda: DG.check_charge("561", 1)[0] is True and DG.check_charge("562", 1) == (False, ""))
    def words(k):
        try: DG.check_charge(k, 1)
        except DG.Unreadable as e: return str(e)
        return ""
    check("guard (charge): ... the words of that error name no chart, no date and no number (their first hundred characters go into the answer a run reads)",
          lambda: all(words(k) and not re.search(r"\d", words(k)) and pid not in words(k) for k in shapes), {k: words(k)[:80] for k in shapes})
def t_guard_cache_state():
    """gate#1: the check before approvals could say only that the cache FILE is missing - not that it is there and knows nothing."""
    reset(); a, b, c, d = cid(), cid(), cid(), cid()
    s0 = DG.cache_state()
    put_cache({a: {"dod": iso(ago(9)), "checked": iso(TODAY)}, b: {"dod": "[DOB]", "checked": iso(TODAY)}, c: {"dod": None, "checked": iso(TODAY)}, d: {"dod": ymd(ago(4))}}); s1 = DG.cache_state()
    with open(DCACHE, "w") as fh: fh.write("{ cut off")
    s2 = DG.cache_state()
    with open(DCACHE, "w") as fh: fh.write("")
    s3 = DG.cache_state()
    check("guard (cache state): cache_state() says in counts only whether the cache file is there, whether it can be read, how many charts it holds, how many with a day and how many with a day that cannot be read - never an entry",
          lambda: s0 == {"file": False, "readable": False, "charts": 0, "days": 0, "lost": 0} and s1 == {"file": True, "readable": True, "charts": 4, "days": 2, "lost": 1}
          and s2 == {"file": True, "readable": False, "charts": 0, "days": 0, "lost": 0} and s3 == {"file": True, "readable": True, "charts": 0, "days": 0, "lost": 0}, (s0, s1, s2, s3))

def t_drive_copy():
    """guard#1 / guard#4 (the second verification): the Drive copy left out a day written in eight digits, and its unpack stumbled over an entry whose source is null."""
    reset(); DD = load("scripts/helpers/dg_drive.py", "dg_drive"); a, b, c, d, e = cid(), cid(), cid(), cid(), cid()
    put_cache({a: {"dod": iso(ago(9)), "checked": iso(ago(1)), "src": "amd-medicare-271"}, b: {"dod": ymd(ago(8)), "src": "a helper that wrote eight digits"}, c: {"dod": "[DOB]", "checked": iso(ago(1))},
               d: {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"}, e: {"dod": mdy(ago(7)), "checked": None, "src": None}})
    out = os.path.join(TMP, "drive_copy.json"); n = DD.pack(DCACHE, out); packed = json.load(open(out))
    check("drive copy: pack keeps every day that can be read - also one a helper wrote in eight digits or as MM/DD/YYYY - as YYYY-MM-DD; a day that cannot be read is in neither of those two lists (since the third round it travels in a list of its own, 'noday', with its check date), a chart with no death is in the other",
          lambda: n == (3, 1, 1) and packed["dated"][a][0] == iso(ago(9)) and packed["dated"][b][0] == iso(ago(8)) and packed["dated"][e][0] == iso(ago(7)) and c not in packed["dated"] and c not in packed["nodeath"] and list(packed["nodeath"]) == [d]
          and packed["noday"] == {c: iso(ago(1))}, (n, packed))
    target = os.path.join(TMP, "drive_target.json"); json.dump({a: {"dod": "[DOB]", "checked": iso(ago(5)), "src": None}, e: {"dod": None, "checked": None, "src": None}, d: {"dod": iso(ago(30)), "checked": iso(ago(3)), "src": "stedi-medicare-271"}}, open(target, "w"))
    m = DD.unpack(out, [target]); got = json.load(open(target))
    check("drive copy: unpack raises nothing on an entry whose source or 'checked' is null, a day that can be read replaces a scrubbed one and an entry with none, the free check's own label is kept, and a real day in the cache is never undone by a 'no death' note",
          lambda: got[a]["dod"] == iso(ago(9)) and got[e]["dod"] == iso(ago(7)) and got[b]["dod"] == iso(ago(8)) and got[d]["dod"] == iso(ago(30)) and isinstance(got[a].get("src"), str), (m, got))

YES_MARKS = ("1", "Y", "y", "Yes", "YES", "true", "True", "TRUE", "t", "T", "d", "D", "deceased", "Deceased", "DECEASED", " y ")      # what the chart's 'deceased' attribute can carry that is KNOWN to mean yes (R2b) - a blank around it changes nothing
NO_MARKS = ("N", "n", "no", "No", "false", "False", "FALSE", "f", "-1", "2", "X", "x", "unknown", "alive", "yes?", "dead?", "dead", "expired", "died", "on", "checked", "123", "1/2")      # ... and what is NOT a mark: every other value that is no date and has fewer than four digits
DATE_MARKS = ("02/31/" + str(TODAY.year), str(TODAY.year), ago(30).strftime("%m-%d-%Y"), ago(30).strftime("%m/%d/%y"), ago(30).strftime("%Y/%m/%d"), ago(30).strftime("%b %d, %Y"), ago(30).strftime("%d %B %Y"), ago(30).strftime("%d.%m.%Y"),
              "00/00/" + "0000", "%d-%d" % (TODAY.year, 13))      # S3 (a) of the fourth round: a value with FOUR OR MORE DIGITS that is no date the guard can read - a date in another shape: a mark
def t_guard_flag_no_day():
    """The independent check of the second round, new finding 10 (D10): a 'deceased' attribute on the AdvancedMD chart that carries NO readable date made the
    claim's own date of service 'the day' - the claim was cleared, and that date was written into the cache as the day, for good. It is a death on record with
    no day: Medicare is asked for the day as for any chart; a day that comes is the day; when none came the claim was not cleared (DayLost) and the entry said
    'a death on record, its day not known'. An attribute that carries a date works as before. The sixth round (11/26/2026, William: "Medicare decides: bill"; "Bill it,
    flag it"): when Medicare answers and names no day the claim is BILLED - Medicare's answer is written as for any chart, no 'day not known' entry - and ONE line for
    the top of the report names the chart; when nobody answers it is billed and flagged (the 'unverified' line and a line about the mark)."""
    src = "amd: deceased on the chart, no date"; res = []; NO_DEATH = lambda: {"dod": None, "checked": iso(TODAY), "src": "stedi: no death on record"}
    for flag in YES_MARKS:      # (the third round, R2b: the marks KNOWN to mean yes, in any letter case - until then every value that was no date counted: -1, a date that is none, N, false)
        reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=flag); dos = iso(ago(5))
        r = says(lambda: guard_check(pid, dos)); res.append((flag, r, kinds(), len(FREE_ASKED), dict((cache_json() or {}).get(pid) or {}), list(DG.LOG), pid))
    check("guard (flag, no day): the chart's own record says deceased and names no day (a mark known to mean yes: 1, y, yes, true, t, d, deceased - in any letter case) - the claim's own date of service is NOT taken for the day: Medicare is asked for the day as for any chart (AdvancedMD's free check, then the vendor's plain check), and when it names none the claim is BILLED (the sixth round - William 11/26/2026, 'Medicare decides: bill'; until then the guard raised DayLost)",
          lambda: len(res) == len(YES_MARKS) >= 12 and all(r[1] == (False, "") and r[2] == ["CMS"] and r[3] == 1 for r in res), [(r[0], r[1], r[2], r[3]) for r in res])
    no = []
    for flag in NO_MARKS:      # R2b (new finding 2 of the second independent check, its part (c)): a mark that does NOT mean yes was read as a death with no day, for good
        reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=flag)
        r = _try(lambda: guard_check(pid, iso(ago(5)))); no.append((flag, r, kinds(), dict((cache_json() or {}).get(pid) or {}).get("dod", "no entry"), _try(lambda: DG.check(pid, iso(ago(4)), "car6404", "99349", allow_lookup=False))))
    check("guard (flag, R2b): the chart's 'deceased' attribute is a MARK only for a value known to mean yes - or (the fourth round) one with four or more digits. Any other value that is no date - N, no, false, 0, -1, a letter nobody knows, a word, a number of fewer than four digits - is NO mark: the chart is asked about as any other, Medicare's 'no death on record' clears the claim, the entry holds no dod, and the chart's next claim is answered from the cache (each of these values made the chart 'a death on record, its day not known', for good)",
          lambda: len(no) == len(NO_MARKS) >= 14 and all(r[1] == (False, "") and r[2] == ["CMS"] and r[3] is None and r[4] == (False, "") for r in no), [r for r in no if not (r[1] == (False, "") and r[3] is None)][:6])
    dm = []
    for flag in DATE_MARKS:      # S3 (a) (the third independent check, finding 5): ten DATES in a shape the guard does not read held the chart before the third round and cleared the claim after it
        reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=flag); r = says(lambda: guard_check(pid, iso(ago(5)))); e = dict((cache_json() or {}).get(pid) or {})
        reset(); q = newp(death=ago(20)); pid2 = chart(cid(), q, plans=[("car6085", "", q["number"])], deceased=flag); r2 = says(lambda: guard_check(pid2, iso(ago(5)))); dm.append((flag, DG._day(flag), r, e, r2, kinds()))
    check("guard (flag, S3 a): a value of the chart's 'deceased' attribute with FOUR OR MORE DIGITS that is no date the guard can read - a date in another shape: MM-DD-YYYY, a two-digit year, YYYY/MM/DD, a month's name, dots, zeros, a year alone, a date that is none - is a MARK: Medicare is asked for the day, and when it names none the claim is billed with Medicare's own 'no death on record' entry (the sixth round - until then DayLost and the entry 'day not known'); when Medicare names a day that is the day",
          lambda: len(dm) == len(DATE_MARKS) >= 10 and all(r[1] is None and r[2] == (False, "") and r[3] == NO_DEATH() and r[4] != "DayLost" and r[4][0] is True and r[5] == ["CMS"] for r in dm),
          [r for r in dm if not (r[1] is None and r[2] == (False, "") and r[4] != "DayLost" and r[4][0] is True)][:5])
    check("guard (A2, the sixth round - MEDICARE DECIDES for a mark with no date): ... Medicare's answer is written as for any chart - 'no death on record', checked today, no 'day not known' entry (never the claim's date of service as the day) - and the guard's log holds exactly ONE line 'TOP OF REPORT: pat<chart>: AdvancedMD marks the chart deceased with no date and Medicare shows none - billed ...' and no 'unverified' line",
          lambda: all(r[4] == NO_DEATH() and r[5] == ["TOP OF REPORT: pat%s: %s" % (r[6], DG.TOP_NODAY)] for r in res) and DG.TOP_NODAY.startswith("AdvancedMD marks the chart deceased with no date and Medicare shows none - billed (William, 11/26/2026)") and DG._day(DG.NO_DAY) is None,
          [(r[0], r[4], r[5]) for r in res if not (r[4] == NO_DEATH() and len(r[5]) == 1)][:4])
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="Y")
    first = says(lambda: guard_check(pid, iso(ago(5)))); asked = len(SENT) + len(FREE_ASKED); log1 = list(DG.LOG)
    second = says(lambda: guard_check(pid, iso(ago(4)), carrier="car6404", proc="99349")); cache_only = says(lambda: DG.check(pid, iso(ago(60)), None, "99349", allow_lookup=False))
    check("guard (A2): ... a second question about that chart in the same start - another payer, another date, one from the cache only - asks nobody again, gives the same answer (billed) and adds no line; the chart is no death on record whose day is lost",
          lambda: first == second == cache_only == (False, "") and len(SENT) + len(FREE_ASKED) == asked and DG.LOG == log1 and len(log1) == 1 and cache_json()[pid] == NO_DEATH() and DG.cache_state()["lost"] == 0, (first, second, cache_only, asked, DG.LOG, cache_json()))
    reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="Y")
    r1 = guard_check(pid, iso(ago(5))); k1 = kinds(); e1 = dict(cache_json()[pid]); r2 = guard_check(pid, iso(ago(25)))
    reset(); p2 = newp(death=ago(20)); pid2 = chart(cid(), p2, plans=[("car6085", "", p2["number"])], deceased="true"); free_death(pid2, p2); r3 = guard_check(pid2, iso(ago(5)))
    check("guard (flag, no day): when Medicare names a day, THAT is the day - a claim after it is blocked, one before it is not, and the entry holds the day with Medicare's source (the vendor's plain check here; AdvancedMD's free check when it answers, and then nothing is bought)",
          lambda: r1[0] is True and iso(ago(20)) in r1[1] and k1 == ["CMS"] and e1["dod"] == iso(ago(20)) and e1["src"] == "stedi-medicare-271" and r2 == (False, "")
          and r3[0] is True and SENT == [] and cache_json()[pid2]["src"] == "amd-medicare-271", (r1, k1, e1, r2, r3))
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="Y"); FREE[ins(pid)] = ("timeout",); OVERRIDE[("CMS", p["number"])] = ("timeout",); OVERRIDE[("MBILUNOSSN", p["last"])] = ("timeout",)
    nobody = says(lambda: guard_check(pid, iso(ago(5))))
    check("guard (A3, the sixth round - NO ANSWER NEVER HOLDS): a mark with no date and nobody answers at all - the claim is BILLED and FLAGGED (William 11/26/2026, 'Bill it, flag it'; until then DayLost): not blocked, no entry is written, and the guard's log holds the 'unverified' line as for any chart and ONE line 'TOP OF REPORT: pat<chart>: ... Medicare could not be asked - billed ...'",
          lambda: nobody == (False, "") and (cache_json() or {}).get(pid) is None and DG.LOG == ["pat%s DOS %s: date of death UNVERIFIED (lookup failed)" % (pid, iso(ago(5))), "TOP OF REPORT: pat%s: %s" % (pid, DG.TOP_NODAY_UNASKED)]
          and "Medicare could not be asked - billed" in DG.TOP_NODAY_UNASKED, (nobody, cache_json(), DG.LOG))
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="Y"); put_cache({pid: {"dod": "[DOB]", "checked": iso(ago(50)), "src": "x"}})
    both = says(lambda: guard_check(pid, iso(ago(5))))
    check("guard (flag, no day): the checker's own case - the cache holds the placeholder AND the chart carries such a flag (a straight-Medicare claim): Medicare shows no death, so it is billed with ONE line about the recorded death whose day cannot be read (the sixth round), the claim's date is never written as the day, and the entry stays as it was",
          lambda: both == (False, "") and cache_json()[pid] == {"dod": "[DOB]", "checked": iso(ago(50)), "src": "x"} and DG.LOG == ["TOP OF REPORT: pat%s: %s" % (pid, DG.TOP_LOST)], (both, cache_json(), DG.LOG))
    res = []
    for flag in (mdy(ago(30)), mdy(ago(30)) + " 12:00:00 AM", iso(ago(30)), ymd(ago(30))):
        reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=flag); res.append((guard_check(pid, iso(ago(5))), guard_check(pid, iso(ago(40))), len(SENT), len(FREE_ASKED), cache_json()[pid]["dod"]))
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="0"); zero = guard_check(pid, iso(ago(5)))
    check("guard (flag, no day): an attribute that carries a DATE works as before - in any shape the guard reads a day in, with a time behind it too: blocked from it with nobody asked; and '0' is no flag (asked as any chart, cleared by Medicare's answer)",
          lambda: all(r[0][0] is True and r[1] == (False, "") and r[2] == 0 and r[3] == 0 and r[4] == iso(ago(30)) for r in res) and zero == (False, "") and kinds() == ["CMS"] and cache_json()[pid]["dod"] is None, (res, zero))
def t_guard_covered():
    """The independent check of the second round, new finding 5 (D5): the check before approvals dropped a 'date of death unverified' line although nobody
    had answered for that charge. It now asks the guard: covered(pid, dos) - True when the cache holds for the chart a day that can be read, or an entry
    that is not stale for that date of service by check()'s own rule. It asks nobody and never raises."""
    reset(); a, b, c, d, e, f, g, h = (cid() for _ in range(8)); soon = TODAY + datetime.timedelta(days=5)
    put_cache({a: {"dod": iso(ago(40)), "checked": iso(ago(200)), "src": "x"}, b: {"dod": "[DOB]", "checked": iso(TODAY), "src": "x"}, c: {"dod": None, "checked": iso(ago(10)), "src": "stedi: no death on record"},
               d: {"dod": None, "checked": iso(ago(31))}, e: {"dod": None, "checked": None}, f: "a line that is no entry", h: {"dod": None, "checked": iso(TODAY)}})
    got = {"day, a claim after it": DG.covered(a, iso(ago(5))), "day, a claim before it": DG.covered(a, iso(ago(100))), "placeholder": DG.covered(b, iso(ago(5))),
           "no death, checked after the date of service": DG.covered(c, iso(ago(12))), "... on it": DG.covered(c, iso(ago(10))), "... before it": DG.covered(c, iso(ago(3))), "... before today, a date to come": DG.covered(c, iso(soon)),
           "checked today, a date to come": DG.covered(h, iso(soon)), "checked more than 30 days ago": DG.covered(d, iso(ago(40))), "no check date": DG.covered(e, iso(ago(40))), "no entry": DG.covered(f, iso(ago(5))),
           "unknown chart": DG.covered(g, iso(ago(5))), "the chart with its prefix, the date as AdvancedMD writes it": DG.covered("pat" + c, mdy(ago(12))), "nothing": DG.covered(None, None)}
    want = dict.fromkeys(got, False); want.update({k: True for k in ("day, a claim after it", "day, a claim before it", "no death, checked after the date of service", "... on it", "checked today, a date to come", "the chart with its prefix, the date as AdvancedMD writes it")})
    check("guard (covered, finding 5): covered(pid, dos) is True when the cache holds a day that can be read (the claim is decided by the day), or 'no death on record' checked within 30 days and not before the date of service (or today, for a date to come); False for a placeholder, an older or undated check, no entry - and it asks nobody",
          lambda: got == want and SENT == [] and FREE_ASKED == [] and BILLING == [], {k: v for k, v in got.items() if v is not want[k]})
    res = []
    for back in (12, 10, 9, 3, 0, -3):      # ONE rule: covered() says exactly when check() would ask nobody for a straight-Medicare claim of that date
        reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); dos = iso(ago(back)); put_cache({pid: {"dod": None, "checked": iso(ago(10)), "src": "stedi: no death on record"}})
        cov = DG.covered(pid, dos); guard_check(pid, dos); res.append((back, cov, not (SENT or FREE_ASKED)))
    check("guard (covered): ... it is check()'s own rule - for every date of service covered() is True exactly when check() asks nobody for a straight-Medicare claim of that chart and date (one rule, held together here)",
          lambda: [r[1] for r in res] == [r[2] for r in res] == [True, True, False, False, False, False], res)
    reset(); os.makedirs(os.path.dirname(DCACHE), exist_ok=True)
    with open(DCACHE, "w") as fh: fh.write("{ cut off")
    check("guard (covered): ... and it never raises - a cache file that cannot be read covers nothing", lambda: DG.covered(a, iso(ago(5))) is False and DG.covered(a, "not a date") is False and DG.covered(["odd"], {"odd": 1}) is False)
def t_one_reading_of_a_day():
    """The independent check of the second round, new finding 12 (D12): three helpers read a cached day, each with its own code, and they disagreed on a day
    with a time behind it - a day to the guard (it blocks by it), no day to the feed's import (the chart counted as one whose day is lost: every visit held,
    also one BEFORE the day) and no day to the Drive copy (pack left the chart out of both lists). The guard's _day is the reference; the other two accept
    exactly what it accepts and return the same."""
    import ast
    def lifted(rel, name):
        """ONE function of a helper, run from its text alone (the import helper cannot be loaded here: it reads its batch files when it is loaded)"""
        node = next(n for n in ast.parse(_read(rel)).body if isinstance(n, ast.FunctionDef) and n.name == name)
        ns = {"re": re, "datetime": datetime}; exec(compile(ast.Module(body=[node], type_ignores=[]), rel, "exec"), ns); return ns[name]
    reset(); guard = DG._day; feed = lifted("scripts/helpers/claimocity_import.py", "death_day"); DD = load("scripts/helpers/dg_drive.py", "dg_drive"); drive = DD.day
    D = ago(40); y = D.year
    days = [iso(D), ymd(D), mdy(D), "%d/%d/%d" % (D.month, D.day, y), "  " + iso(D) + " ", iso(D) + "T00:00:00", iso(D) + " 00:00:00", iso(D) + "T00:00:00Z", mdy(D) + " 12:00:00 AM", mdy(D) + "T00:00:00", int(ymd(D))]
    none = ["[" + "DOB" + "]", DG.NO_DAY, "", "   ", "unknown", "not a day", "Y", "true", "%d-02-31" % y, "%d0231" % y, "02/31/%d" % y, "13/01/%d" % y, "0" * 8, "0000-00-00", "%d-13-01" % y, "%d-1-5" % y, str(y), None, 0, 1, False, True, float(ymd(D)), -int(ymd(D))]
    other = [ymd(D) + "T000000", ymd(D) + " 12:00", iso(D) + "x", mdy(D) + "x", ymd(D) + "0", "x" + iso(D), [iso(D)], (iso(D),), {"a day": iso(D)}, b"bytes", 10 ** 30]      # whatever the guard makes of these, the other two make the same
    got = [(repr(x)[:30], guard(x), feed(x), drive(x)) for x in days + none + other]
    check("one reading of a day (finding 12): the guard's _day, the import's death_day and dg_drive.py's day give the SAME answer for every shape - YYYY-MM-DD, eight digits, MM/DD/YYYY, each with a time behind it, the placeholder, texts, impossible dates, None, numbers, things that are no text",
          lambda: all(g == f == d for _x, g, f, d in got), [r for r in got if not (r[1] == r[2] == r[3])][:6])
    check("one reading of a day: ... and that answer is the day, as YYYY-MM-DD, for every shape a helper has written a day in - with a time behind it too (AdvancedMD stamps its dates with one) - and no day for the placeholder, a text, a date that is none, None and a number that is no date",
          lambda: [guard(x) for x in days] == [iso(D)] * len(days) and [feed(x) for x in days] == [iso(D)] * len(days) and [guard(x) for x in none] == [None] * len(none) and [drive(x) for x in none] == [None] * len(none),
          [(repr(x), guard(x), feed(x), drive(x)) for x in days + none if (guard(x), feed(x), drive(x)) != ((iso(D),) * 3 if x in days else (None,) * 3)][:6])
    a, b = cid(), cid(); put_cache({a: {"dod": iso(D) + "T00:00:00", "checked": iso(ago(3)), "src": "x"}, b: {"dod": mdy(D) + " 12:00:00 AM", "checked": iso(ago(3)), "src": "x"}}); out = os.path.join(TMP, "drive_time.json")
    n = DD.pack(DCACHE, out); packed = json.load(open(out))
    check("one reading of a day: ... so an entry whose day carries a time blocks at the guard AND travels in the Drive copy as its day (pack left such a chart out of both lists - the next run did not know it)",
          lambda: n == (2, 0, 0) and packed["dated"][a][0] == packed["dated"][b][0] == iso(D) and DG.check(a, iso(ago(5)), "car6404", "99349", allow_lookup=False)[0] is True and DG.check(b, iso(ago(60)), "car6404", "99349", allow_lookup=False) == (False, ""), (n, packed))
def t_guard_odd_entry():
    """The independent check of the second round: a one-line change of the guard that passed every check (g20) - a cache entry of another shape than an entry."""
    res = []
    for odd in ("a line that is no entry", ["nor", "is", "this"], 7):
        reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); put_cache({pid: odd})
        quiet = _try(lambda: DG.check(pid, iso(ago(5)), "car6404", "99349", allow_lookup=False)); cov = _try(lambda: DG.covered(pid, iso(ago(5)))); asked = _try(lambda: guard_check(pid, iso(ago(5))))
        res.append((quiet, cov, asked, kinds(), (cache_json() or {}).get(pid, {}).get("dod") if isinstance((cache_json() or {}).get(pid), dict) else None))
    check("guard (odd entry): a cache line of another shape than an entry (a text, a list, a number) is NO entry - a question from the cache only answers 'not blocked', it covers nothing, and a claim that needs Medicare's answer is asked about like a chart the cache does not know (here the day comes back and blocks); nothing raises, and the answer replaces the odd line",
          lambda: all(r[0] == (False, "") and r[1] is False and r[2] != "raised" and r[2][0] is True and r[3] == ["CMS"] and r[4] == iso(ago(20)) for r in res), res)
def t_drive_merge_keeps():
    """The independent check of the second round, new finding 2 (D2): step 0c's own merge undid a death on record - a 'no death' note of the Drive copy replaced
    a placeholder whose check date was older, and a later day replaced an earlier one when the Drive copy's check date was newer. Now: a note never replaces an
    entry whose dod is set (a day OR a placeholder); of two days the EARLIER stays whatever the check dates; a real day still beats a placeholder."""
    reset(); DD = load("scripts/helpers/dg_drive.py", "dg_drive"); a, b, c, d, e, f, g, h = (cid() for _ in range(8)); drive = os.path.join(TMP, "drive_merge_copy.json")
    put_cache({a: {"dod": "[DOB]", "checked": iso(ago(30)), "src": "stedi-medicare-271"},        # a placeholder, checked BEFORE the Drive copy's note
               b: {"dod": "[DOB]", "checked": iso(ago(5)), "src": "x"},                          # a placeholder, checked after it
               c: {"dod": iso(ago(60)), "checked": iso(ago(30)), "src": "stedi-medicare-271"},    # an EARLY day, checked long ago; the Drive copy holds a LATER day with a newer check date
               d: {"dod": iso(ago(20)), "checked": iso(ago(3)), "src": "amd-medicare-271"},       # a LATE day, checked the other day; the Drive copy holds an EARLIER day with an older check date
               e: {"dod": None, "checked": iso(ago(30)), "src": "stedi: no death on record"},     # no death on record, older than the note
               f: {"dod": "[DOB]", "checked": iso(ago(2)), "src": "x"},                          # a placeholder checked the other day; the Drive copy holds the real day, checked earlier
               h: {"dod": iso(ago(45)), "checked": iso(ago(30)), "src": "x"}})                    # a day; the Drive copy holds the same day with a newer check date
    json.dump({"dated": {c: [iso(ago(20)), iso(ago(3))], d: [iso(ago(60)), iso(ago(40))], f: [iso(ago(50)), iso(ago(9))], g: ["[DOB]", iso(ago(3))], h: [ymd(ago(45)), iso(ago(4))]},
               "nodeath": {a: iso(ago(10)), b: iso(ago(10)), e: iso(ago(10)), c: iso(ago(1))}}, open(drive, "w"))
    lost_before = _raises(lambda: DG.check(a, iso(ago(5)), None, "99309", allow_lookup=False), DG.DayLost)      # (the sixth round: a charge whose payer the caller does not know - a known other payer is never held)
    n = DD.unpack(drive, [DCACHE]); got = cache_json()
    check("drive merge (finding 2): a 'no death' note of the Drive copy NEVER replaces an entry whose dod is set - not a placeholder checked before the note, not one checked after it, not a day (whatever the note's date)",
          lambda: got[a] == {"dod": "[DOB]", "checked": iso(ago(30)), "src": "stedi-medicare-271"} and got[b]["dod"] == "[DOB]" and got[c]["dod"] == iso(ago(60)), {k: got.get(k) for k in (a, b, c)})
    check("drive merge: ... so the claim of such a chart is as little cleared after step 0c's merge as before it - the guard still raises DayLost (it answered 'not blocked' after the merge)",
          lambda: lost_before and _raises(lambda: DG.check(a, iso(ago(5)), None, "99309", allow_lookup=False), DG.DayLost) and SENT == [] and FREE_ASKED == [], lost_before)
    check("drive merge (finding 2): of two days for one chart the EARLIER stays, whatever the check dates - the cache's early day is not replaced by Drive's later one (its check date is newer), and Drive's early day replaces the cache's later one (its check date is older); a visit between the two days is blocked either way",
          lambda: got[c]["dod"] == iso(ago(60)) and got[c]["checked"] == iso(ago(30)) and got[d]["dod"] == iso(ago(60)) and DG.check(c, iso(ago(30)), "car6404", "99309", allow_lookup=False)[0] is True
          and DG.check(d, iso(ago(30)), "car6404", "99309", allow_lookup=False)[0] is True, {k: got.get(k) for k in (c, d)})
    check("drive merge: a real day still beats a placeholder (also one checked later than the Drive copy's entry); the same day with a newer check date only moves the check date; what stands under 'dated' but is no day is not taken; a newer note still renews an entry with NO death on record - and the count is the entries written",
          lambda: got[f]["dod"] == iso(ago(50)) and got[h]["dod"] == iso(ago(45)) and got[h]["checked"] == iso(ago(4)) and g not in got and got[e] == {"dod": None, "checked": iso(ago(10)), "src": "stedi: no death on record"} and n == 3,
          (n, {k: got.get(k) for k in (e, f, g, h)}))
    # ('a cache file that is there but is no table (a JSON list) ... is replaced by the table the Drive copy gives' was pinned here until the third round. A file
    #  that cannot be read may hold dates of death: the guard never writes over one, and since the fourth round the merge keeps it under another name beside it and
    #  writes the table in its place - t_drive_unreadable_cache, below.)
    put_cache({a: {"dod": iso(ago(9)), "checked": iso(ago(1))}, b: "a line that is no entry", c: ["nor", "this"], d: {"dod": None, "checked": iso(ago(2))}}); out = os.path.join(TMP, "drive_pack_odd.json")
    k = _try(lambda: DD.pack(DCACHE, out))
    check("drive copy: pack passes over a cache line that is no entry (a text, a list) - it does not stop the pack, and the entries beside it are packed", lambda: k == (1, 1, 0) and sorted(json.load(open(out))["dated"]) == [a] and list(json.load(open(out))["nodeath"]) == [d], k)

# ==== 4a3. the third round (11/25/2026): the items of the second independent check - each check names the item (R1 ... R7) it closes ==============
PLACEHOLDER = "[" + "DOB" + "]"      # the privacy gate's placeholder for a scrubbed day, put together here
def answer_61(p, day):
    """Medicare's PLAIN answer for a patient who has passed away: error 61 and the day (the shape the guard's header records as seen)"""
    return {"errors": [{"code": "61", "description": DESC["61"]}], "subscriber": {"memberId": p["number"]}, "benefitsInformation": [], "planDateInformation": {"dateOfDeath": ymd(day)}}
def t_guard_lookup_keeps_day():
    """R1 (new finding 1 of the second independent check): the guard's OWN look-up still made it forget a death. Medicare's plain check answers 61 WITH the
    day; the client's hook keeps it (record) and, as it always does after a 61, buys the look-up by name. When that look-up named nobody (a lone 72) or hit
    another person (Part A / Part B, no day), check() wrote 'no death on record' over the day the hook had just kept, and the claim after it passed. Shown with
    the REAL client (stedi.py) and the REAL answer store (medicare_store.py) over this file's wire stand-in."""
    res = []
    for how in ("a lone 72", "another person"):
        reset(); p = newp(); other = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); day = ago(40)
        OVERRIDE[("CMS", p["number"])] = ("answer", answer_61(p, day))
        OVERRIDE[("MBILUNOSSN", p["last"])] = ("answer", err_answer("72") if how == "a lone 72" else a271(other, other["number"], address={"state": "FL"}))
        r1 = _try(lambda: guard_check(pid, iso(ago(5)))); k1 = kinds(); e1 = dict((cache_json() or {}).get(pid) or {}); del SENT[:]
        r2 = _try(lambda: DG.check(pid, iso(ago(4)), "car6404", "99349", allow_lookup=False)); r3 = _try(lambda: guard_check(pid, iso(ago(60))))
        res.append((how, r1, k1, e1.get("dod") == iso(day), r2, r3, len(SENT), list(DG.LOG)))
    check("guard (R1, the look-up keeps the day): Medicare's PLAIN check answers 61 with the day, the look-up bought after it answers a lone 72 ('not a Medicare beneficiary') - or Part A / Part B of ANOTHER person: the straight-Medicare claim dated after that day is BLOCKED by it (it answered 'not blocked'), with the real client and answer store on the way",
          lambda: len(res) == 2 and all(r[1] != "raised" and r[1][0] is True and iso(ago(40)) in r[1][1] and r[2] == ["CMS", "MBILUNOSSN"] for r in res), [(r[0], r[1], r[2]) for r in res])
    check("guard (R1): ... and the entry KEEPS the day: the chart's next claim is blocked from the cache with nobody asked, a claim dated before the day is not, and no 'unverified' line is logged",
          lambda: all(r[3] is True and r[4] != "raised" and r[4][0] is True and r[5] == (False, "") and r[6] == 0 and r[7] == [] for r in res), [(r[0], r[3], r[4], r[5], r[6], r[7]) for r in res])
    # ... the same rule from the other side: whatever wrote the entry WHILE the look-up was on its way (the hook, another helper), check() reads it again before it writes
    out = []
    for held in (iso(ago(40)), PLACEHOLDER, "day not known"):
        reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); entry = {"dod": held, "checked": iso(TODAY), "src": "another helper, meanwhile"}
        ON_SEND.append(lambda url, body, pid=pid, entry=entry: put_cache({pid: dict(entry)}))
        r = _try(lambda: guard_check(pid, iso(ago(5)))); top = list(DG.LOG); again = says(lambda: DG.check(pid, iso(ago(5)), None, "99349", allow_lookup=False)); del ON_SEND[:]
        out.append((held == iso(ago(40)), r, again, (cache_json() or {}).get(pid) == entry, kinds(), top, pid))
    check("guard (R1): check() never writes an entry WITHOUT a day over one that holds a dod - an entry another helper wrote while Medicare was being asked (Medicare answers 'no death on record'): a day that can be read blocks the claim; a death on record whose day cannot be read is decided by Medicare's answer (the sixth round: billed, ONE line for the top of the report, and a question from the cache only in the same process gives the same answer); and the entry stays exactly as that helper wrote it",
          lambda: len(out) == 3 and out[0][1] != "raised" and out[0][1][0] is True and out[0][3] and all(o[1] == (False, "") and o[2] == (False, "") and o[3] and o[5] == ["TOP OF REPORT: pat%s: %s" % (o[6], DG.TOP_LOST)] for o in out[1:]) and all(o[4] == ["CMS"] for o in out), out)
def lift(rel, *names):
    """Functions and constants of a helper by their names, run from its text alone -> their namespace (the import helper cannot be loaded here: it reads its
    batch files when it is loaded)."""
    import ast
    body = [n for n in ast.parse(_read(rel)).body if (isinstance(n, ast.FunctionDef) and n.name in names) or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
    ns = {"re": re, "datetime": datetime}; exec(compile(ast.Module(body=body, type_ignores=[]), rel, "exec"), ns); return ns
def death_shapes():
    """-> (values that are a death ON RECORD whose day cannot be read, values that are NO dod, values that are a day) - R2a's three kinds, with the fourth
    round's wider reading of the first (S3 b): any text in square or angle brackets in any letter case, a masked date, the words that stand for a death"""
    D = ago(40); y = D.year
    death = [PLACEHOLDER, " " + PLACEHOLDER + " ", PLACEHOLDER + " 00:00:00", PLACEHOLDER + " 12:00 AM", PLACEHOLDER + "Z", "[" + "MBI" + "]", "day not known", "  day not known ",
             "%d-02-31" % y, "%d0231" % y, "02/31/%d" % y, "13/45/%d" % y, str(y), "%d-11" % y, "0000-00-00", "0" * 8, ymd(D) + "T000000", iso(D)[:8] + "x1", "1/1/26", "x" + iso(D), "a 1 b 2 c 3 d 4"] + death_shapes_s3()
    none = [None, "", " ", "   ", "None", "null", "unknown", "0", "n/a", "no", "N", "false", "x1y2z3", "123", "[]", "[ ]", "[12]", "<>", "< >", "<1>", "DOB", "day unknown", "X", "x", "XX", "XXX", "X/X", "x-x.x", "/", "--", "ye", "yess", "yes?", "dead?", "the deceased",
            "x-ray: fax to exton, box 6", "x-ray, fax, exit, box"] + death_nothing() + [
            "not deceased", "deceased?", "true", "t", "d", "1", "on", 0, 1, y, int("%d0231" % y), 1.5, float(ymd(D)), True, False, [], [PLACEHOLDER], (PLACEHOLDER,), {"a": PLACEHOLDER}, b"1234 bytes", b"deceased", ["deceased"]]
    days = [iso(D), ymd(D), mdy(D), iso(D) + "T00:00:00", mdy(D) + " 12:00:00 AM", "  " + iso(D) + " ", int(ymd(D))]
    return death, none, days
def death_nothing():
    """F8 of the fifth round (the fourth independent check, finding 8): a bracketed text that plainly means NOTHING - none, null, n/a, na, unknown, no, empty, in any
    letter case, in square or angle brackets - is NO death on record (each of these held a living patient's chart after the fourth round); a blank inside the
    brackets or around them changes nothing, and neither does a text beside them that is no death by itself"""
    return ["[none]", "[None]", "[NONE]", "<none>", "[null]", "<NULL>", "[n/a]", "[N/A]", "<n/a>", "[na]", "[NA]", "[unknown]", "[UNKNOWN]", "<Unknown>", "[no]", "<NO>", "[empty]", "<EMPTY>", "[ none ]", "< null >", " [none] ", "see [none]",
            "[none] [null]", "[no] <empty>"]
def death_shapes_s3():
    """S3 (b) of the fourth round (the third independent check, finding 5): what ALSO stands for a death with no day in a cache's day place - sixteen such texts
    read 'no dod' after the third round, and another payer's claim passed with nobody asked"""
    return ["[dob]", "[Dob]", "[name]", "[D0B]", "[redacted]", "[REDACTED]", "[DATE OF DEATH]", "[date of death]", "<DOB>", "<dob>", "< redacted >", "see [dob]", "[x] 00:00:00",
            "[unknown date]", "[nobody]", "[nay]", "[none] [dob]", "[dob] [none]", "<null> <redacted>",
            "XX/XX/XXXX", "xx/xx/xxxx", "XXXX-XX-XX", "XXXXXXXX", "XX.XX.XXXX", "XX XX XXXX", "XXXX", " XX/XX/XXXX ", "deceased", "Deceased", "DECEASED", " deceased ", "dead", "Dead", "died", "DIED", "expired", "Expired", "redacted", "REDACTED",
            "y", "Y", "yes", "Yes", "YES", " y "]
def t_death_on_record_shapes():
    """R2a (new finding 2 of the second independent check, its part about values): WHAT COUNTS as 'a death on record whose day cannot be read'. Until the third
    round ANY value in a dod field that was no day counted - 'unknown', the word None, one blank, the text 0 in a stray file held a living patient's chart, for
    good. Now: a dod value that is no day is a death on record only when it is the privacy gate's placeholder (an upper-case word in square brackets), the
    guard's own 'day not known', or a text with at least four digits (a damaged date). Every other value is NO dod: the entry is one without an answer - asked
    about again when the claim needs it - never a death on record. ONE reading for the guard, the import and dg_drive.py, held together here."""
    reset(); DD = load("scripts/helpers/dg_drive.py", "dg_drive"); F = lift("scripts/helpers/claimocity_import.py", "death_day", "death_unread", "DEATH_NO_DAY", "DEATH_WORDS", "DEATH_NOTHING")
    death, none, days = death_shapes(); guard = getattr(DG, "_unread", None); feed = F.get("death_unread"); drive = getattr(DD, "unread", None)
    got = [(repr(x)[:30], _try(lambda: guard(x)), _try(lambda: feed(x)), _try(lambda: drive(x))) for x in death + none + days]
    check("death on record (R2a): the guard's _unread, the import's death_unread and dg_drive.py's unread give the SAME answer for every shape - and the words they know 'day not known' by are one word in three places",
          lambda: all(g is f is d and g in (True, False) for _x, g, f, d in got) and F.get("DEATH_NO_DAY") == getattr(DD, "NO_DAY", None) == DG.NO_DAY and F.get("DEATH_WORDS") == getattr(DD, "DEATH_WORDS", None) == DG.DEATH_WORDS
          == {"deceased", "dead", "died", "expired", "redacted", "y", "yes"}, [r for r in got if not (r[1] is r[2] is r[3])][:6])
    check("death on record (R2a; S3 b of the fourth round): ... it is True for the privacy gate's placeholder (also with a time left behind it), the guard's own 'day not known', a text with at least four digits (a damaged date) - and, since the fourth round, for ANY text in square or angle brackets in any letter case, a masked date (only X and separators, four X or more) and the words deceased, dead, died, expired, redacted, y, yes in any letter case; False for None, '', blanks, the words None / null / unknown, '0', a number, a list, empty brackets, fewer than four X, a word beside those words ('not deceased', 'the deceased', 'true'), and for every value that IS a day. The fifth round (F8; g36): False too for a bracketed text that plainly means nothing ('[none]', '<null>', '[n/a]', '[unknown]', '[no]', '[empty]' - every other bracketed text is still True: '[unknown date]', '[none] [dob]'), and for a text that only STARTS like a masked date ('x-ray: fax to exton, box 6' - the masked date must be the whole value)",
          lambda: [guard(x) for x in death] == [True] * len(death) and [guard(x) for x in none + days] == [False] * len(none + days) and [DG._day(x) for x in death + none] == [None] * len(death + none),
          [(repr(x), _try(lambda: guard(x))) for x in death if _try(lambda: guard(x)) is not True][:5] + [(repr(x), _try(lambda: guard(x))) for x in none + days if _try(lambda: guard(x)) is not False][:5])
    res = []
    for v in ("unknown", "None", "null", " ", "0", "n/a", 0, 7, True, ["x"]):      # NO dod: an entry without an answer
        reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); put_cache({pid: {"dod": v, "checked": iso(TODAY), "src": "x"}})
        quiet = _try(lambda: DG.check(pid, iso(ago(5)), "car6404", "99349", allow_lookup=False)); cov = _try(lambda: DG.covered(pid, iso(ago(5)))); st = _try(lambda: DG.cache_state()["lost"])
        asked = _try(lambda: guard_check(pid, iso(ago(5)))); res.append((repr(v), quiet, cov, st, asked, kinds(), ((cache_json() or {}).get(pid) or {}).get("dod")))
    check("death on record (R2a): an entry whose dod is any OTHER value that is no day ('unknown', the words None / null, a blank, '0', a number, true, a list) is NO death on record - a claim to another payer answers 'not blocked' from the cache (it raised DayLost), the entry covers nothing and is not counted as lost - and it is an entry WITHOUT an answer: a straight-Medicare claim is asked about although the entry says 'checked today'; here Medicare names the day, it blocks, and the answer replaces the odd value",
          lambda: len(res) == 10 and all(r[1] == (False, "") and r[2] is False and r[3] == 0 and r[4] != "raised" and r[4][0] is True and r[5] == ["CMS"] and r[6] == iso(ago(20)) for r in res), res)
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); put_cache({pid: {"dod": "unknown", "checked": iso(TODAY), "src": "x"}})
    r = _try(lambda: guard_check(pid, iso(ago(5)))); e = dict((cache_json() or {}).get(pid) or {})
    b = cid(); put_cache({b: {"dod": "None", "checked": iso(ago(3)), "src": "x", "name": "kept"}}); DG.record(b, json.loads(json.dumps(ALIVE_271))); eb = dict((cache_json() or {}).get(b) or {})
    check("death on record (R2a): ... when Medicare shows NO death for such a chart the claim is cleared and the entry is the ordinary 'no death on record', checked today; and the hook that keeps every Medicare answer (record) writes its 'no death on record' over such a value too - it holds no death",
          lambda: r == (False, "") and kinds() == ["CMS"] and e == {"dod": None, "checked": iso(TODAY), "src": "stedi: no death on record"} and eb == {"dod": None, "checked": iso(TODAY), "name": "kept", "src": "stedi: no death on record"}, (r, e, eb))
    res = []
    for v in ("%d-02-31" % TODAY.year, str(TODAY.year), PLACEHOLDER + " 00:00:00"):      # a damaged date, a placeholder with a time left behind it: a death ON RECORD
        reset(); pid = cid(); entry = {"dod": v, "checked": iso(ago(9)), "src": "x"}; put_cache({pid: dict(entry)})
        lost = _raises(lambda: DG.check(pid, iso(ago(5)), None, "99349", allow_lookup=False), DG.DayLost); DG.record(pid, json.loads(json.dumps(ALIVE_271)))      # (the sixth round: a charge whose payer is not known - a known other payer is never held)
        res.append((v, lost, DG.covered(pid, iso(ago(5))), DG.cache_state()["lost"], cache_json()[pid] == entry))
    check("death on record (R2a): ... while a damaged date (a text with four digits or more that is no calendar date) and a placeholder with a time left behind it ARE a death on record: the claim whose payer is not known is not cleared from the cache only (DayLost), the entry covers nothing, counts as lost, and no answer without a day is written over it",
          lambda: all(r[1] and r[2] is False and r[3] == 1 and r[4] for r in res), res)
    res = []
    for v in ("[dob]", "[redacted]", "<DOB>", "XX/XX/XXXX", "deceased", "Dead", "expired", "REDACTED", "Y", "yes"):      # S3 (b): each of these let another payer's claim through with nobody asked
        reset(); pid = cid(); entry = {"dod": v, "checked": iso(ago(9)), "src": "x"}; put_cache({pid: dict(entry)})
        lost = says(lambda: DG.check(pid, iso(ago(5)), None, "99349", allow_lookup=False)); DG.record(pid, json.loads(json.dumps(ALIVE_271)))      # (the sixth round: a charge whose payer is not known)
        res.append((v, lost, DG.covered(pid, iso(ago(5))), DG.cache_state()["lost"], cache_json()[pid] == entry))
    check("death on record (S3 b): a bracketed text in any letter case, a masked date and the words that stand for a death ARE a death on record with no day: a claim whose payer is not known is not cleared from the cache only (DayLost - each of them answered 'not blocked' with nobody asked), the entry covers nothing, counts as lost, and no answer without a day is written over it",
          lambda: len(res) == 10 and all(r[1] == "DayLost" and r[2] is False and r[3] == 1 and r[4] for r in res), res)
    # dg_drive.py goes by the same reading: an entry without an answer is no 'no death' note, and a 'no death' note or a day from the Drive copy replaces an odd value
    reset(); a, b, c, d, e, f = (cid() for _ in range(6)); drive = os.path.join(TMP, "drive_r2a.json")
    put_cache({a: {"dod": iso(ago(9)), "checked": iso(ago(1))}, b: {"dod": PLACEHOLDER, "checked": iso(ago(1))}, c: {"dod": None, "checked": iso(ago(2))}, d: {"dod": "unknown", "checked": iso(TODAY)}, e: {"dod": 0, "checked": iso(TODAY)},
               f: {"dod": "", "checked": iso(ago(4))}})
    n = _try(lambda: DD.pack(DCACHE, drive)); packed = json.load(open(drive)) if os.path.exists(drive) else {}
    check("death on record (R2a), the Drive copy: pack writes a 'no death' note only for an entry that holds NO value in the day's place (null or an empty text) - an entry with an odd value ('unknown', 0) is one without an answer: it goes into neither list, so its check date does not come back as 'no death on record, checked that day'",
          lambda: sorted(packed.get("dated") or {}) == [a] and sorted(packed.get("nodeath") or {}) == sorted([c, f]) and n != "raised" and n[:2] == (1, 2), (n, packed))
    put_cache({a: {"dod": "unknown", "checked": iso(ago(3)), "src": "x"}, b: {"dod": "None", "checked": iso(ago(3))}, c: {"dod": "%d-02-31" % TODAY.year, "checked": iso(ago(3)), "src": "x"}, d: {"dod": "0", "checked": iso(TODAY), "src": "x"}})
    json.dump({"dated": {b: [iso(ago(30)), iso(ago(2))]}, "nodeath": {a: iso(ago(1)), c: iso(TODAY), d: iso(ago(5))}}, open(drive, "w")); m = _try(lambda: DD.unpack(drive, [DCACHE])); got = cache_json() or {}
    check("death on record (R2a), the merge: a 'no death' note of the Drive copy replaces an odd value when it is the newer of the two (an older note leaves the entry as it is), a day replaces it, and a damaged date is a death on record the note never replaces",
          lambda: m != "raised" and got[a]["dod"] is None and got[a]["checked"] == iso(ago(1)) and got[b]["dod"] == iso(ago(30)) and got[c] == {"dod": "%d-02-31" % TODAY.year, "checked": iso(ago(3)), "src": "x"} and got[d]["dod"] == "0", (m, got))
@contextlib.contextmanager
def no_write(g):
    """While the block runs the guard g cannot WRITE its cache: the temporary file it writes through cannot be made, as in a folder that refuses a new file (a
    read-only checkout). Only that guard's own name for the module is replaced - nothing else in this process loses its temporary files."""
    real = g.tempfile
    def no(*a, **k): raise OSError(30, "Read-only file system")
    g.tempfile = types.SimpleNamespace(mkstemp=no)
    try: yield
    finally: g.tempfile = real
def t_guard_cannot_write():
    """R5 (new finding 6 of the second independent check): a cache in use that cannot be WRITTEN. The second round kept in memory what a cache that cannot be
    READ would have received; when the write itself failed, _put let the error out: check() ended in an OSError for a chart it had the answer for, the carry
    gave up, and the day was neither written nor kept. _put answers False now, and what could not be written is kept in memory for the rest of the process."""
    reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); put_cache({}); before = text_of(DCACHE)
    with no_write(DG):
        put = _try(lambda: DG._put(pid, {"dod": None, "checked": iso(TODAY)})); r1 = _try(lambda: guard_check(pid, iso(ago(5)))); k1 = kinds(); del SENT[:]
        r2 = _try(lambda: DG.check(pid, iso(ago(4)), "car6404", "99349", allow_lookup=False)); r3 = _try(lambda: guard_check(pid, iso(ago(3)))); kept = pid in DG._UNSAVED
    check("guard (R5, a cache that cannot be written): _put answers False instead of raising; check() still answers - the day Medicare names blocks the claim (it ended in an OSError) - and what it could not write is kept in memory: the chart's next claims in the same process are blocked with nobody asked again; the file is as it was and no temporary file is left beside it",
          lambda: put is False and r1 != "raised" and r1[0] is True and k1 == ["CMS"] and r2 != "raised" and r2[0] is True and r3 != "raised" and r3[0] is True and SENT == [] and kept and text_of(DCACHE) == before
          and os.listdir(os.path.dirname(DCACHE)) == ["deceased_cache.json"], (put, r1, k1, r2, r3, kept))
    reset(); a, b = cid(), cid(); put_cache({})
    with no_write(DG):
        got = _try(lambda: DG.record(a, {"dateOfDeath": ymd(ago(30))}, "amd-271")); ra = _try(lambda: DG.check(a, iso(ago(5)), "car6404", "99349", allow_lookup=False))
        p = newp(); pid = chart(b, p, plans=[("car6085", "", p["number"])]); OVERRIDE[("CMS", p["number"])] = ("answer", answer_61(p, ago(40))); OVERRIDE[("MBILUNOSSN", p["last"])] = ("answer", err_answer("72"))
        rb = _try(lambda: guard_check(pid, iso(ago(5))))
    check("guard (R5): ... the hook that keeps every Medicare answer (record) keeps in memory the day it could not write, too - so the day a plain answer carried during a check (61 with the day, then a look-up that names nobody: R1) still blocks that claim when the cache cannot be written",
          lambda: got == iso(ago(30)) and ra != "raised" and ra[0] is True and rb != "raised" and rb[0] is True and iso(ago(40)) in rb[1] and cache_json() == {}, (got, ra, rb, cache_json()))
    later = _try(lambda: DG._put(a, {"dod": iso(ago(31)), "checked": iso(TODAY), "src": "written once the folder takes a file again"})); seen = _try(lambda: DG._load().get(a))
    check("guard (R5): ... and once a write of that chart's entry goes through, the entry kept in memory is gone - the file is the one source again (an entry in memory never hides a newer one in the file)",
          lambda: later is True and a not in DG._UNSAVED and seen["dod"] == iso(ago(31)) and cache_json()[a]["dod"] == iso(ago(31)), (later, seen, sorted(DG._UNSAVED)))
def t_guard_lost_words_and_two_days():
    """R7 (the second round's own left-overs). (a) The words of the DayLost error said 'and Medicare named none' - untrue when nobody was asked (a question from
    the cache only, a second question in the same start). (b) ONE rule for two days everywhere: the carry and the Drive merge kept the EARLIER of two days,
    while record() - the hook that keeps every Medicare answer - wrote a LATER day over an earlier one, and a visit between the two passed."""
    reset(); pid = cid(); put_cache({pid: {"dod": PLACEHOLDER, "checked": iso(ago(9)), "src": "x"}})
    def words(f):
        try: f()
        except DG.DayLost as e: return str(e)
        return ""
    w = words(lambda: DG.check(pid, iso(ago(5)), None, "99349", allow_lookup=False))
    check("guard (R7a, the words of a lost day): the error says what is true also when NOBODY was asked - 'its day cannot be read here, and nobody named it' (it said 'and Medicare named none' for a question from the cache only) - names the two ways on, the cache copy from Drive or a look-up, and (the sixth round, A4) says that the claim waits only while Medicare cannot be asked and the day cannot be read, and that Medicare's own answer decides - no word of taking a record off by hand any more (the owner never overrides Medicare's date of death)",
          lambda: w == DG.LOST_WORDS == "a date of death is on record for this chart but its day cannot be read here, and nobody named it - the claim is not cleared: it waits only while Medicare cannot be asked and the day cannot be read, and Medicare's own answer decides (merge the cache copy from Drive, or look the chart up)"
          and "Medicare named none" not in _read("scripts/helpers/deceased_guard.py").split("\nimport os, re, json")[1], (w, getattr(DG, "LOST_WORDS", None)))
    check("guard (R7a): ... those words name no chart, no date and no number, and their first hundred characters - what amd.rebill_charge puts into its 409 answer - say that a death is on record, that its day cannot be read and that nobody named it",
          lambda: not re.search(r"\d", DG.LOST_WORDS) and pid not in DG.LOST_WORDS and DG.LOST_WORDS[:100].endswith("its day cannot be read here, and nobody named it - t") and ".py" not in DG.LOST_WORDS and "by hand" not in DG.LOST_WORDS and "alive" not in DG.LOST_WORDS, DG.LOST_WORDS[:100])
    reset(); a, b, c = cid(), cid(), cid(); early, late = iso(ago(40)), iso(ago(10)); held = {"dod": early, "checked": iso(ago(30)), "src": "amd-271", "name": "kept as it was"}
    put_cache({a: dict(held), b: {"dod": late, "checked": iso(ago(9)), "src": "x", "name": "kept"}, c: {"dod": ymd(ago(40)), "checked": iso(ago(30)), "src": "x"}})
    ga = DG.record(a, {"dateOfDeath": ymd(ago(10))}); gb = DG.record(b, {"dateOfDeath": ymd(ago(40))}, "amd-271"); gc = DG.record(c, {"dateOfDeath": ymd(ago(40))}, "amd-271"); got = cache_json()
    between = [DG.check(k, iso(ago(20)), "car6404", "99349", allow_lookup=False)[0] for k in (a, b)]
    check("guard (R7b, one rule for two days): record() with a day KEEPS an earlier day the entry already holds - the entry stays exactly as it was and a visit between the two days is still blocked (the later day was written over it, and that visit passed); an EARLIER day than the entry's is taken; the same day only renews the entry",
          lambda: ga == late and got[a] == held and gb == early and got[b]["dod"] == early and got[b]["src"] == "amd-271" and got[b].get("name") == "kept" and between == [True, True]
          and gc == early and got[c]["dod"] == early and got[c]["checked"] == iso(TODAY), (ga, gb, gc, got, between))
    reset(); p = newp(death=ago(10)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])])
    ON_SEND.append(lambda url, body: put_cache({pid: {"dod": iso(ago(30)), "checked": iso(TODAY), "src": "another helper, meanwhile"}}))
    r = _try(lambda: guard_check(pid, iso(ago(20)))); del ON_SEND[:]
    check("guard (R7b): ... the same in check(): of two days - the one the look-up names and an EARLIER one the entry holds by then (another helper wrote it while Medicare was being asked) - the earlier stays and decides: the visit between the two is blocked",
          lambda: r != "raised" and r[0] is True and iso(ago(30)) in r[1] and cache_json()[pid]["dod"] == iso(ago(30)) and cache_json()[pid]["src"] == "another helper, meanwhile", (r, cache_json()))
    reset(); p = newp(death=ago(40)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])])
    ON_SEND.append(lambda url, body: put_cache({pid: {"dod": iso(ago(10)), "checked": iso(TODAY), "src": "another helper, meanwhile"}}))
    r = _try(lambda: guard_check(pid, iso(ago(20)))); del ON_SEND[:]
    check("guard (R7b): ... and the other way round - the look-up names the EARLIER of the two: that day is taken and decides", lambda: r != "raised" and r[0] is True and iso(ago(40)) in r[1] and cache_json()[pid]["dod"] == iso(ago(40)), (r, cache_json()))
def t_guard_asked_once():
    """R6 (a one-line change of check() that passed every check - m19): 'one question per chart per start' for a chart the chart's own record marks deceased
    with no day. The check that was there counted the vendor's requests - and the second look-up made none: the answer store handed the first one's answer
    over. What a second look-up always does is read the chart again; that is counted here."""
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="Y"); reads = lambda: BILLING.count("getdemographic " + pid)
    first = says(lambda: guard_check(pid, iso(ago(5)))); r1 = reads(); second = says(lambda: guard_check(pid, iso(ago(4)))); third = says(lambda: guard_check(pid, iso(ago(3)), carrier=None, proc="99487")); r2 = reads()
    check("guard (R6, m19; the sixth round): a chart marked deceased with no day that Medicare names none for is asked about ONCE per process - billed (William 11/26/2026, 'Medicare decides: bill'), and the second and the third question of the same start (another date, a care-management code whose payer is not known) give the same answer, do not even read the chart again and add no second line",
          lambda: first == second == third == (False, "") and r1 == 1 and r2 == 1 and pid in DG._NONE_SAID and DG.LOG == ["TOP OF REPORT: pat%s: %s" % (pid, DG.TOP_NODAY)], (first, second, third, r1, r2, DG.LOG))
    DG._NONE_SAID.clear(); fourth = says(lambda: guard_check(pid, iso(ago(2))))
    check("guard (R6): ... and a NEW process answers from Medicare's own 'no death on record' the cache keeps for the chart, as for any chart (checked today): nobody is asked and the chart is not read again", lambda: fourth == (False, "") and reads() == 1, (fourth, reads()))
LONG_AGO = "2000-01-" + "01"      # the check date of an entry that must be asked about again (the guard's own LONG_AGO, put together here)
def says(f):
    """What a guard call ends in: its answer - or, when it raises, the KIND of the error (DayLost ...)"""
    try: return f()
    except Exception as e: return type(e).__name__
OLD_FIELDS = ("re" + "ask", "off" + "_record", "approved" + "_by")      # the fields rounds three and four wrote into an entry for the owner's word - put together here: the names are gone from every file of the guard
def old_word_rec(d=None, **more):
    """An entry as the helper of the fourth round left it where the owner had said a patient is alive: no death, a check date long ago, and that round's own fields.
    To this round's guard, to dg_drive.py and to the import it is an entry like any other - the fields mean nothing."""
    d = d or ago(10); e = {"dod": None, "checked": LONG_AGO, "src": "an entry the round before wrote", OLD_FIELDS[0]: iso(d), OLD_FIELDS[2]: "William %d/%d/%d (board)" % (d.month, d.day, d.year)}; e.update(more); return e
def nobody_answers(pid, p):
    """AdvancedMD's free check, the vendor's plain check and its look-up all fail for this chart"""
    FREE[ins(pid)] = ("timeout",); OVERRIDE[("CMS", p["number"])] = ("timeout",); OVERRIDE[("MBILUNOSSN", p["last"])] = ("timeout",)
def t_no_way_out():
    """D1 (the fifth round, 11/26/2026): THE TOOL FOR A DEATH THAT IS ON RECORD WRONGLY IS OUT AGAIN, WHOLE. Rounds three and four had each built a way out on the
    owner's word - an entry that outweighed every day reported up to the date of his word, then an entry that made the guard put a new question to Medicare for any
    claim. The independent check of each round found it wanting. So nothing a run starts takes a death off: the guard keeps a death for good, and nobody
    overrides Medicare's date of death - William never would (the sixth round, his word in chat that day). Shown here: no name
    of either way out is left in the guard, the Drive copy helper, the import, the retry, the digest or the tables that keep helpers current; the helper and its
    self-test are gone; the two look-ups take no argument for a new question; and an entry that still carries those rounds' fields is an entry like any other."""
    import inspect
    R = OLD_FIELDS[0]
    names = ["_" + R, "_af" + "ter", R.upper() + "_SRC", R.upper() + "_KEYS", R.upper() + "_UNDATED", "_" + R.upper() + "ED", "Not" + "Answered", "RES" + "ET_WORDS", "_o" + "ff", "_be" + "ats", "OFF" + "_SRC", "OFF" + "_KEYS", "OFF" + "_AGAIN_SRC"]
    words = [R, "RE-" + "ASK", "Not" + "Answered", "death_off" + "_record", OLD_FIELDS[1], "DEATH_RES" + "ET_WHY", "DEATH RECORD " + "RESET", "_dc_res" + "et", "_dr_" + "held", "death_res" + "et", "RES" + "ET_WORDS"]
    files = ["scripts/helpers/deceased_guard.py", "core/deceased_guard.py", "scripts/helpers/dg_drive.py", "scripts/helpers/claimocity_import.py", "scripts/helpers/claimocity_retry_dx.py", "scripts/helpers/claimocity_report.py",
             "scripts/helpers/death_check_review.py", "scripts/helpers/claimocity_void_deceased.py", "scripts/helpers/claimocity_helpers_current.py", "tools/mirror/mirror.py", "tools/bootstrap/bootstrap_workspace.sh"]
    left = [(f, w) for f in files for w in words if w.lower() in _read(f).lower()]
    still = [f for f in ("scripts/helpers/death_off" + "_record.py", "core/death_off" + "_record.py", "tools/selftest/test_death_off" + "_record.py") if os.path.exists(os.path.join(ROOT, f))]
    check("no way out (D1 of the fifth round): nothing of rounds three and four's way out for a wrongly recorded death is left - no function, class or constant of it in the guard, none of its words in the guard (both copies), the Drive copy helper, the import, the retry, the digest, the check before approvals, the void helper, the two tables that keep helpers current or the bootstrap's list; and the helper and its self-test are not in the tree",
          lambda: not any(hasattr(DG, n) for n in names) and left == [] and still == [], ([n for n in names if hasattr(DG, n)], left, still))
    sig = [list(inspect.signature(f).parameters) for f in (DG.stedi_lookup, DG.free_lookup, DG.check, DG.check_charge, DG.record, DG.covered)]
    errors = sorted(n for n, v in vars(DG).items() if isinstance(v, type) and issubclass(v, BaseException))
    check("no way out (D1): ... the two look-ups take no argument for a 'new' question any more (the chart and the date of service; the chart and its plan), the guard has its two errors and no third - DayLost and Unreadable - and DayLost has no kind of its own beneath it",
          lambda: sig == [["pid", "dos_iso"], ["pid", "plan"], ["pid", "dos", "carrier", "proc", "allow_lookup"], ["chargeid", "sequencenumber", "allow_lookup"], ["pid", "j", "src"], ["pid", "dos"]]
          and errors == ["DayLost", "Unreadable"] and DG.DayLost.__subclasses__() == [] and DG.LONG_AGO == LONG_AGO, (sig, errors))
    reset(); a, b, c, d = (cid() for _ in range(4))
    put_cache({a: old_word_rec(name="kept"), b: old_word_rec(checked=iso(TODAY)), c: old_word_rec(dod=iso(ago(40))), d: {"dod": None, "checked": iso(TODAY), "src": "x", OLD_FIELDS[1]: iso(ago(1)), OLD_FIELDS[2]: "the owner"}})
    quiet = {k: says(lambda k=k: DG.check(k, iso(ago(2)), "car6404", "99349", allow_lookup=False)) for k in (a, b, c, d)}
    cov = [DG.covered(k, iso(ago(2))) for k in (a, b, c, d)]; st = DG.cache_state()
    check("no way out (D1): an entry that still carries the fields rounds three and four wrote for the owner's word is an entry LIKE ANY OTHER - the fields mean nothing. With no death in it a claim to another payer is answered 'not blocked' from the cache (the fourth round raised an error of its own there and held the chart), it covers a claim by its check date alone, and with a day in it the day blocks; nobody is asked and nothing is written",
          lambda: quiet[a] == quiet[b] == quiet[d] == (False, "") and quiet[c] not in ("DayLost", "raised") and quiet[c][0] is True and cov == [False, True, True, True] and st["days"] == 1 and st["lost"] == 0
          and SENT == [] and FREE_ASKED == [] and BILLING == [] and cache_json()[a] == old_word_rec(name="kept"), (quiet, cov, st))
    reset(); p = newp(death=ago(40)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); askp(p, dos=ymd(ago(1)), pid=pid, who="pre-claim check", max_age_days=0)      # the answer a wrong day would have come from, kept in the answer store
    store_edit(lambda s: s["charts"][pid]["answers"][0].update(asked=iso(ago(5)))); kept = _try(lambda: MS.death(pid)); p["death8"] = None      # ... five days ago; asked TODAY, Medicare would name no death
    put_cache({pid: old_word_rec()}); del SENT[:]; del FREE_ASKED[:]
    r = says(lambda: guard_check(pid, iso(ago(1)))); k = kinds(); fa = len(FREE_ASKED); e = dict(cache_json()[pid])
    check("no way out (D1): ... and a straight-Medicare claim of such a chart is asked about by the ORDINARY rules: the answer the store keeps - bought five days ago, it shows the day - is used as it is, with no call, free or paid, and its day blocks. A death is never undone, and no question goes round the answer store (the fourth round asked on the wire here and cleared the chart when Medicare named none)",
          lambda: kept == ymd(ago(40)) and r not in ("DayLost", "raised") and r[0] is True and iso(ago(40)) in r[1] and k == [] and fa == 0 and e.get("dod") == iso(ago(40)), (kept, r, k, fa, e))
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); put_cache({pid: old_word_rec()}); nobody_answers(pid, p)
    r1 = says(lambda: guard_check(pid, iso(ago(1)))); log1 = list(DG.LOG); n1 = len(SENT); r2 = says(lambda: guard_check(pid, iso(ago(1)), carrier="car6404", proc="99349")); n2 = len(SENT)
    check("no way out (D1): ... when nobody answers, that claim goes on as 'unverified' like any chart's - one line in the guard's log: a failed check blocks nothing, only a day does - and a claim to another payer is not asked about at all; the entry stays as it was. No error of its own is left for such a chart",
          lambda: r1 == (False, "") and len(log1) == 1 and "UNVERIFIED" in log1[0] and n1 >= 1 and r2 == (False, "") and n2 == n1 and cache_json()[pid] == old_word_rec(), (r1, log1, n1, r2, n2))
def t_drive_copy_v2():
    """The Drive copy as it stands after the fifth round - what the third and the fourth round's checks left (their finding 5 among it; d08 and d15 are one-line
    changes the checks made that no test had noticed). The copy is 'deceased_cache_drive v2' with THREE lists - dated, nodeath, noday - chart ids and dates only.
    The third round's copy carried a fourth list for the owner's words, with his approval text; the fourth round took the list out and gave the merge a rule for an
    entry of its own; the fifth round took that rule out too: pack and unpack know a day, a 'no death' note and a death with no day - nothing else."""
    reset(); DD = load("scripts/helpers/dg_drive.py", "dg_drive"); D = ago(10); a, b, c, d, e, f, g = (cid() for _ in range(7)); out = os.path.join(TMP, "drive_v2.json")
    put_cache({a: {"dod": iso(ago(40)), "checked": iso(ago(30)), "src": "x", "name": "kept"}, b: {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"}, c: {"dod": PLACEHOLDER, "checked": iso(ago(50))},
               d: {"dod": "day not known", "checked": iso(ago(3)), "src": "amd: deceased on the chart, no date"}, e: old_word_rec(D, name="kept"), f: {"dod": "unknown", "checked": iso(TODAY)}, g: "a line that is no entry"})
    n = _try(lambda: DD.pack(DCACHE, out)); pk = json.load(open(out)) if os.path.exists(out) else {}; flat = json.dumps(pk)
    check("drive copy: pack writes THREE lists - the days, the 'no death' notes and 'noday' = {chart: its check date} for a death on record with no day that can be read - and no list of the owner's words; an entry that still carries the fields of the rounds before is a 'no death' note like any other, by its own check date; the format line says v2 and names the three lists",
          lambda: sorted(k for k in pk if k != "format") == ["dated", "noday", "nodeath"] and pk["noday"] == {c: iso(ago(50)), d: iso(ago(3))} and sorted(pk["dated"]) == [a] and pk["nodeath"] == {b: iso(ago(2)), e: LONG_AGO}
          and str(pk.get("format", "")).startswith("deceased_cache_drive v2") and all(w in pk["format"] for w in ("dated", "nodeath", "noday")) and n == (1, 2, 2) and f not in flat, (n, pk))
    check("drive copy: ... the copy holds chart ids and dates only - no approval text, no name and nothing else of an entry travels in it (the third round's copy carried 'William M/D/YYYY (board)' for every chart his word was given for)",
          lambda: "William" not in flat and "kept" not in flat and "approved" not in flat and OLD_FIELDS[0] not in flat and "word" not in pk.get("format", "")
          and all(isinstance(v, list) and len(v) == 2 and all(x is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(x)) for x in v) for v in pk["dated"].values())
          and all(v is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)) for k in ("nodeath", "noday") for v in pk[k].values()), flat[:400])
    # unpack: what each note of a Drive copy does to the entries of a cache
    L = {k: cid() for k in ("old fields, a day checked long before", "old fields, a mark checked long before", "old fields, a newer no-death note", "old fields, nothing in the copy",
                            "mark on nothing", "mark on old no death", "mark on new no death", "mark on same-day no death", "mark on a day", "mark on a placeholder")}
    OF = old_word_rec(D, name="kept"); local = {L[k]: dict(OF) for k in list(L)[:4]}
    local.update({L["mark on old no death"]: {"dod": None, "checked": iso(ago(20)), "src": "stedi: no death on record"}, L["mark on new no death"]: {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"},
                  L["mark on same-day no death"]: {"dod": None, "checked": iso(ago(7)), "src": "stedi: no death on record"}, L["mark on a day"]: {"dod": iso(ago(40)), "checked": iso(ago(30))}, L["mark on a placeholder"]: {"dod": PLACEHOLDER, "checked": iso(ago(50))}})
    notes = {"format": "deceased_cache_drive v2", "dated": {L["old fields, a day checked long before"]: [iso(ago(40)), iso(ago(30))]}, "nodeath": {L["old fields, a newer no-death note"]: iso(ago(1))},
             "noday": {L["old fields, a mark checked long before"]: iso(ago(15)), L["mark on nothing"]: iso(ago(7)), L["mark on old no death"]: iso(ago(7)), L["mark on new no death"]: iso(ago(7)), L["mark on same-day no death"]: iso(ago(7)),
                       L["mark on a day"]: iso(ago(7)), L["mark on a placeholder"]: iso(ago(7))}}
    put_cache(local); drive = os.path.join(TMP, "drive_v2_notes.json"); json.dump(notes, open(drive, "w")); m = _try(lambda: DD.unpack(drive, [DCACHE])); got = cache_json() or {}; G_ = lambda k: got.get(L[k]) or {}
    check("drive merge (D1 of the fifth round): an entry that still carries the fields of the rounds before is merged like any 'no death on record' entry of its check date - a day of the copy is brought into it whatever the day's own check date (the fourth round kept a day checked before the entry's date OUT of it), a 'noday' note too, a newer 'no death' note brings its check date up to date, and with nothing in the copy it stays as it is; the entry's name stays as any entry's does",
          lambda: m != "raised" and G_("old fields, a day checked long before").get("dod") == iso(ago(40)) and G_("old fields, a day checked long before").get("checked") == iso(ago(30)) and G_("old fields, a day checked long before").get("name") == "kept"
          and G_("old fields, a mark checked long before").get("dod") == DD.NO_DAY and G_("old fields, a mark checked long before").get("checked") == iso(ago(15))
          and G_("old fields, a newer no-death note").get("dod", "x") is None and G_("old fields, a newer no-death note").get("checked") == iso(ago(1)) and G_("old fields, nothing in the copy") == OF, (m, {k: G_(k) for k in list(L)[:4]}))
    asked = {k: says(lambda k=k: DG.check(L[k], iso(ago(1)), None, "99349", allow_lookup=False)) for k in list(L)[:4]}
    check("drive merge (D1): ... and the guard reads that merged cache as any cache: the day blocks, the 'noday' note leaves the chart not cleared (DayLost), and the two entries with no death in them answer 'not blocked' from the cache",
          lambda: asked["old fields, a day checked long before"] not in ("DayLost", "raised") and asked["old fields, a day checked long before"][0] is True and asked["old fields, a mark checked long before"] == "DayLost"
          and asked["old fields, a newer no-death note"] == asked["old fields, nothing in the copy"] == (False, ""), asked)
    check("drive merge (finding 5 of the second check, d08): a 'noday' note makes a chart the cache holds NO death for - no entry, or 'no death on record' checked BEFORE the note - a death on record with no day ('day not known', the note's check date); a 'no death on record' checked on the SAME day as the note or after it, a day and a placeholder of the cache's own stay as they are",
          lambda: G_("mark on nothing") == {"dod": DD.NO_DAY, "checked": iso(ago(7)), "src": "a death on record, its day not known (drive copy)"} and DD.NO_DAY == DG.NO_DAY and G_("mark on old no death").get("dod") == DD.NO_DAY
          and G_("mark on new no death") == local[L["mark on new no death"]] and G_("mark on same-day no death") == local[L["mark on same-day no death"]] and G_("mark on a day") == local[L["mark on a day"]]
          and G_("mark on a placeholder") == local[L["mark on a placeholder"]], {k: G_(k) for k in ("mark on nothing", "mark on old no death", "mark on new no death", "mark on same-day no death", "mark on a day", "mark on a placeholder")})
    # a note whose date is no date (d15), in every list - and a copy of the third round that still carries the list of his words
    reset(); x, z, u, v, w, s, t = (cid() for _ in range(7)); odd = os.path.join(TMP, "drive_v2_odd.json"); gone = OLD_FIELDS[1]
    start = {x: {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"}, z: {"dod": iso(ago(40)), "checked": iso(ago(30)), "src": "x"}, u: {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"},
             s: {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"}, t: {"dod": PLACEHOLDER, "checked": iso(ago(9))}}
    json.dump({"format": "deceased_cache_drive v2", "dated": {}, "nodeath": {x: 20261101, w: ["a", "list"]}, "noday": {x: 7, s: {"no": "date"}, v: None},
               gone: {z: [iso(TODAY), "William said so"], u: [iso(TODAY), "William said so"], t: "not even a pair", cid(): [None, None]}}, open(odd, "w"))
    put_cache(json.loads(json.dumps(start))); m2 = _try(lambda: DD.unpack(odd, [DCACHE])); got2 = cache_json() or {}
    check("drive merge (d15): a note whose date is no date - a number, a list, a table, nothing - never ends the merge on an error: a 'no death' note without a date changes no entry that has a check date, and a 'noday' note without a date is taken only where the cache has NO entry for the chart",
          lambda: m2 != "raised" and got2[x] == start[x] and got2[s] == start[s] and got2[v] == {"dod": DD.NO_DAY, "checked": None, "src": "a death on record, its day not known (drive copy)"}
          and got2[w].get("dod") is None and sorted(got2) == sorted([x, z, u, s, t, v, w]), (m2, got2))
    check("drive merge: a copy that still carries the third round's list of his words: the list is IGNORED - a day and a placeholder the cache holds stay on record (that list took them off), a chart with no death stays as it is, no entry is made for a chart only that list names, nothing of its text reaches the cache, and nothing raises",
          lambda: m2 != "raised" and got2[z] == start[z] and got2[t] == start[t] and got2[u] == start[u] and "William said so" not in json.dumps(got2) and gone not in json.dumps(got2), (m2, got2.get(z), got2.get(t), got2.get(u)))
CHART_SRC = "amd: deceased on the chart"      # the source of a day taken from the chart's own 'deceased' field (the guard's own CHART_SRC, put together here)
def t_round5_small():
    """D3 of the fifth round - two small things the fourth independent check found (its findings 6 and 8), each shown before it was changed.
    F6: a day taken from the chart's OWN 'deceased' field was written with the source 'stedi-medicare-271' - Medicare had not been asked at all - and whatever source
    an entry carried, the next step 0c wrote it back as '... (drive copy)' whenever the Drive copy's check date was the same or the newer one. Now the guard writes
    'amd: deceased on the chart', and dg_drive.py unpack keeps an entry's own source whenever the day does not change.
    F8: 'any text in square or angle brackets' made '[none]', '[unknown]', '<null>' and '[n/a]' in a cache's day place a death on record - a living patient's chart
    was held, for good. A bracketed text that plainly means NOTHING - none, null, n/a, na, unknown, no, empty, in any letter case - is no death on record; every other
    bracketed text still is."""
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=mdy(ago(30)))
    r = guard_check(pid, iso(ago(5))); e = dict((cache_json() or {}).get(pid) or {}); n = (len(SENT), len(FREE_ASKED))
    check("small things (F6): a day taken from the chart's OWN 'deceased' field is written with a source of its own - 'amd: deceased on the chart' - and the block names it; nobody was asked, so the entry no longer reads 'stedi-medicare-271' (it did: the entry said Medicare had named the day)",
          lambda: r[0] is True and ("after date of death %s (%s)" % (iso(ago(30)), CHART_SRC)) in r[1] and e == {"dod": iso(ago(30)), "checked": iso(TODAY), "src": CHART_SRC} and n == (0, 0)
          and getattr(DG, "CHART_SRC", None) == CHART_SRC and DG.NO_DAY_SRC == CHART_SRC + ", no date", (r, e, n, getattr(DG, "CHART_SRC", None)))
    r2 = guard_check(pid, iso(ago(4)), carrier="car6404", proc="99349"); e2 = dict(cache_json()[pid])
    q = newp(); pid2 = chart(cid(), q, plans=[("car6085", "", q["number"])], deceased=mdy(ago(30))); put_cache({pid: e2, pid2: {"dod": None, "checked": iso(ago(40)), "src": "stedi: no death on record"}})
    r3 = guard_check(pid2, iso(ago(5))); e3 = dict(cache_json()[pid2])
    check("small things (F6): ... the chart's next claim is blocked from the cache and the entry stays as it is; and a chart whose entry was an old 'no death on record' gets the day and that source written over it",
          lambda: r2[0] is True and e2 == e and r3[0] is True and e3 == {"dod": iso(ago(30)), "checked": iso(TODAY), "src": CHART_SRC}, (r2, e2, r3, e3))
    reset(); p = newp(death=ago(12)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=mdy(ago(30))); r4 = guard_check(pid, iso(ago(5)))      # the chart's field names a day - and then the field is emptied, the entry lost, and Medicare names another
    CHARTS[pid]["deceased"] = ""; os.remove(DCACHE); r5 = guard_check(pid, iso(ago(5))); e5 = dict(cache_json()[pid])
    q = newp(death=ago(12)); pid3 = chart(cid(), q, plans=[("car6085", "", q["number"])]); r6 = guard_check(pid3, iso(ago(5))); e6 = dict(cache_json()[pid3])
    check("small things (F6): ... that source is the chart's field's alone: once the field is empty and Medicare names the day, the entry says 'stedi-medicare-271' again (nothing is remembered from the look-up before), and a chart that never had the field filled reads as before",
          lambda: r4[0] is True and r5[0] is True and e5.get("dod") == iso(ago(12)) and e5.get("src") == "stedi-medicare-271" and r6[0] is True and e6.get("src") == "stedi-medicare-271" and kinds() == ["CMS", "CMS"], (r4, r5, e5, r6, e6, kinds()))
    reset(); p = newp(death=ago(12)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=mdy(ago(30))); real_post = fake_amd.post; theirs = {"dod": iso(ago(30)), "checked": iso(ago(1)), "src": "amd-271"}
    def post_while_another_helper_writes(body, timeout=0):      # while the guard reads the chart, another helper writes that very day into the cache (the insurance check's hook does so)
        t_ = real_post(body, timeout); put_cache({pid: dict(theirs)}); return t_
    fake_amd.post = post_while_another_helper_writes
    try: r7 = guard_check(pid, iso(ago(5)))
    finally: fake_amd.post = real_post
    e7 = dict(cache_json()[pid]); CHARTS[pid]["deceased"] = ""; os.remove(DCACHE); free_death(pid, p); r8 = guard_check(pid, iso(ago(5))); e8 = dict(cache_json()[pid])      # later in the same start: the field is empty, the cache another one, and AdvancedMD's free check names the day
    check("small things (F6): ... and the same when the entry already HELD the chart's day by the time the look-up came back (another helper had written it meanwhile: that entry stays exactly as it is, its own source with it) - at the chart's next look-up, the field empty by then and AdvancedMD's free check naming the day, the source is that answer's ('amd-medicare-271'), not the chart's field's: every look-up starts by taking the mark of the one before off",
          lambda: r7[0] is True and e7 == theirs and r8[0] is True and e8 == {"dod": iso(ago(12)), "checked": iso(TODAY), "src": "amd-medicare-271"} and SENT == [], (r7, e7, r8, e8, kinds()))
    # ... and the merge of the Drive copy keeps an entry's own source whenever the day does not change
    reset(); DD = load("scripts/helpers/dg_drive.py", "dg_drive"); D = ago(30); ids = [cid() for _ in range(9)]; c1, c2, c3, c4, c5, c6, c7, c8, c9 = ids
    mine = {c1: {"dod": iso(D), "checked": iso(ago(3)), "src": CHART_SRC, "name": "kept"}, c2: {"dod": iso(D), "checked": iso(ago(3)), "src": "amd-271"}, c3: {"dod": ymd(D), "checked": iso(ago(3)), "src": "carried from another cache file of this workspace"},
            c4: {"dod": iso(D), "checked": iso(ago(3))}, c5: {"dod": iso(D), "checked": iso(ago(3)), "src": ""}, c6: {"dod": iso(D), "checked": iso(ago(3)), "src": CHART_SRC},
            c7: {"dod": PLACEHOLDER, "checked": iso(ago(3)), "src": "the register's own"}, c8: {"dod": None, "checked": iso(ago(3)), "src": "stedi: no death on record"}, c9: {"dod": iso(D), "checked": iso(ago(3)), "src": "stedi-medicare-271"}}
    put_cache(json.loads(json.dumps(mine))); copy = os.path.join(TMP, "drive_f6.json")
    json.dump({"format": "deceased_cache_drive v2", "dated": {c1: [iso(D), iso(ago(1))], c2: [iso(D), iso(ago(3))], c3: [iso(D), iso(TODAY)], c4: [iso(D), iso(ago(1))], c5: [iso(D), iso(ago(1))], c6: [iso(ago(31)), iso(ago(1))],
                                                           c7: [iso(D), iso(ago(1))], c8: [iso(D), iso(ago(1))], c9: [iso(ago(31)), iso(ago(1))]}, "nodeath": {}, "noday": {}}, open(copy, "w"))
    m = _try(lambda: DD.unpack(copy, [DCACHE])); got = cache_json() or {}
    check("small things (F6, the merge): the Drive copy names the SAME day an entry already holds, with the same or a newer check date - the entry keeps its OWN source, whatever it is (the chart's field, a plan's eligibility answer, the carry's), and takes the copy's check date; its name stays (each of them read 'stedi-medicare-271 (drive copy)' after the next step 0c)",
          lambda: m != "raised" and got[c1] == {"dod": iso(D), "checked": iso(ago(1)), "src": CHART_SRC, "name": "kept"} and got[c2] == {"dod": iso(D), "checked": iso(ago(3)), "src": "amd-271"}
          and got[c3] == {"dod": iso(D), "checked": iso(TODAY), "src": "carried from another cache file of this workspace"}, (m, got.get(c1), got.get(c2), got.get(c3)))
    check("small things (F6, the merge): ... an entry that names NO source gets the Drive copy's, as before; and where the day CHANGES - an earlier day of the copy, a day over a placeholder or over 'no death on record' - the source is the copy's as before, unless the entry's own names one of the two Medicare answers",
          lambda: got[c4].get("src") == got[c5].get("src") == "stedi-medicare-271 (drive copy)" and got[c6] == {"dod": iso(ago(31)), "checked": iso(ago(1)), "src": "stedi-medicare-271 (drive copy)"}
          and got[c7].get("dod") == iso(D) and got[c7].get("src") == "stedi-medicare-271 (drive copy)" and got[c8].get("dod") == iso(D) and got[c8].get("src") == "stedi-medicare-271 (drive copy)"
          and got[c9] == {"dod": iso(ago(31)), "checked": iso(ago(1)), "src": "stedi-medicare-271"}, {k: got.get(k) for k in (c4, c5, c6, c7, c8, c9)})
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=mdy(D)); guard_check(pid, iso(ago(5))); first = dict(cache_json()[pid]); road = os.path.join(TMP, "drive_f6_road.json")
    c_p, o_p, e_p = drive_tool("pack", DCACHE, road); c_u, o_u, e_u = drive_tool("unpack", road, DCACHE); again = dict(cache_json()[pid])
    check("small things (F6): the road of one such day - the guard writes it from the chart's field, the run packs the cache for Drive, the next step 0c merges that copy back: the entry reads exactly as the guard wrote it, source and all",
          lambda: (c_p, e_p, c_u, e_u) == (0, "", 0, "") and first == again == {"dod": iso(D), "checked": iso(TODAY), "src": CHART_SRC}, (c_p, c_u, first, again))
    # F8: a bracketed text that plainly means 'nothing' is no death on record
    F = lift("scripts/helpers/claimocity_import.py", "death_day", "death_unread", "death_read", "DEATH_NO_DAY", "DEATH_WORDS", "DEATH_NOTHING"); res = []
    for v in ("[none]", "[NONE]", "<null>", "[n/a]", "[NA]", "[unknown]", "<Unknown>", "[no]", "[empty]", "[ none ]"):      # each of these held every claim of the chart (DayLost) after the fourth round
        reset(); pid = cid(); entry = {"dod": v, "checked": iso(ago(9)), "src": "x"}; put_cache({pid: dict(entry)})
        quiet = says(lambda: DG.check(pid, iso(ago(5)), "car6404", "99349", allow_lookup=False)); lost = DG.cache_state()["lost"]; cov = DG.covered(pid, iso(ago(5)))
        feed = _try(lambda: F["death_read"]([{pid: dict(entry)}])); out = os.path.join(TMP, "drive_f8.json"); pk = _try(lambda: DD.pack(DCACHE, out))
        res.append((v, quiet, lost, cov, feed, pk))
    check("small things (F8): a cache entry whose day place holds a bracketed text that plainly means NOTHING - none, null, n/a, na, unknown, no, empty, in any letter case, in square or angle brackets - is NO death on record: another payer's claim is answered 'not blocked' from the cache (each of them raised DayLost and held a living patient's chart), the entry is not counted as lost and covers nothing (it is one without an answer), the import holds no visit for it, and it goes into no list of the Drive copy",
          lambda: len(res) == 10 and all(r[1] == (False, "") and r[2] == 0 and r[3] is False and r[4] == ({}, set()) and r[5] == (0, 0, 0) for r in res), res)
    res = []
    for v in ("[dob]", "[unknown date]", "[no day]", "[none] [dob]", "<null> <redacted>", "[nobody]"):      # every OTHER bracketed text still stands for a death with no day
        reset(); pid = cid(); entry = {"dod": v, "checked": iso(ago(9)), "src": "x"}; put_cache({pid: dict(entry)})
        res.append((v, says(lambda: DG.check(pid, iso(ago(5)), None, "99349", allow_lookup=False)), DG.cache_state()["lost"], _try(lambda: F["death_read"]([{pid: dict(entry)}])) == ({}, {pid})))
    check("small things (F8): ... while every OTHER bracketed text is still a death on record with no day - the placeholder, a text that says the DATE is unknown or missing, a value with one bracketed text that means nothing and one that does not: the claim is not cleared (DayLost), the entry counts as lost and the import holds the chart's visits",
          lambda: len(res) == 6 and all(r[1] == "DayLost" and r[2] == 1 and r[3] is True for r in res), res)
    nothing = {"none", "null", "n/a", "na", "unknown", "no", "empty"}
    check("small things (F8): the words that mean 'nothing' are ONE set in three places - the guard's NOTHING_WORDS, the import's DEATH_NOTHING and dg_drive.py's NOTHING_WORDS - and none of them is one of the words that stand for a death",
          lambda: getattr(DG, "NOTHING_WORDS", None) == F.get("DEATH_NOTHING") == getattr(DD, "NOTHING_WORDS", None) == nothing and not (nothing & DG.DEATH_WORDS), (getattr(DG, "NOTHING_WORDS", None), F.get("DEATH_NOTHING"), getattr(DD, "NOTHING_WORDS", None)))
def t_round5_markers():
    """D4 of the fifth round: the markers the mirror (tools/mirror/mirror.py PROTECTED) and the feed's helper check (claimocity_helpers_current.py VERSION_LINES) know
    this round's helpers by. A marker is a line ONLY this round's file has: a workspace copy from before must never come back over the repository's. The guard's
    was the line that defined the fourth round's error - gone with it; dg_drive.py's ('deceased_cache_drive v2') stood in the third round's file too; and the void
    helper of the feed had none at all - an older copy in a workspace reads the feed's old cache file, and the mirror would have put it back over the repository's."""
    mir = _read("tools/mirror/mirror.py"); hcur = _read("scripts/helpers/claimocity_helpers_current.py"); gsrc = _read("scripts/helpers/deceased_guard.py"); dsrc = _read("scripts/helpers/dg_drive.py"); vsrc = _read("scripts/helpers/claimocity_void_deceased.py")
    def marker(table, name):
        m = re.search(r'"%s":\s*(\'[^\'\n]*\'|"[^"\n]*")' % re.escape(name), table); return m.group(1)[1:-1] if m else None
    G = 'DEATH_GUARD_RULE = "2026-11-26.2"'; DR = 'DG_DRIVE_RULE = "2026-11-26.1"'      # (the guard's sixth round, 11/26/2026: .2)
    check("markers (D4): the guard's marker - in the mirror's table and in the feed helpers' own list - is the line of ITS round, 'DEATH_GUARD_RULE = \"2026-11-26.2\"' (the sixth round): it stands exactly once in each copy of the guard, as a line of its own, the guard reads it as its constant, and the marker of the round before is in neither table",
          lambda: marker(mir, "deceased_guard.py") == marker(hcur, "deceased_guard.py") == G and gsrc.count(G) == 1 and _read("core/deceased_guard.py").count(G) == 1 and len(re.findall(r"(?m)^" + re.escape(G), gsrc)) == 1
          and getattr(DG, "DEATH_GUARD_RULE", None) == "2026-11-26.2" and ("class Not" + "Answered") not in mir + hcur, (marker(mir, "deceased_guard.py"), marker(hcur, "deceased_guard.py"), gsrc.count(G)))
    DD = load("scripts/helpers/dg_drive.py", "dg_drive")
    check("markers (D4): dg_drive.py's marker is a line only this round's file has, 'DG_DRIVE_RULE = \"2026-11-26.1\"' (the words 'deceased_cache_drive v2' stand in the third round's file too: the mirror took such a copy for current) - once in the file, as a line of its own; the FORMAT line of the Drive copy itself stays v2 with its three lists",
          lambda: marker(mir, "dg_drive.py") == DR and dsrc.count(DR) == 1 and len(re.findall(r"(?m)^" + re.escape(DR), dsrc)) == 1 and getattr(DD, "DG_DRIVE_RULE", None) == "2026-11-26.1"
          and DD.FORMAT.startswith("deceased_cache_drive v2: dated = ") and all(w in DD.FORMAT for w in ("nodeath", "noday")) and '"dg_drive.py": "deceased_cache_drive v2"' not in mir, (marker(mir, "dg_drive.py"), dsrc.count(DR)))
    V = marker(mir, "claimocity_void_deceased.py"); hlines = [l for l in vsrc.split("\nimport os as _os")[0].splitlines() if l.startswith("#")]
    HC5 = types.ModuleType("claimocity_helpers_current_r5"); exec(compile(hcur, "claimocity_helpers_current.py", "exec"), HC5.__dict__)
    check("markers (D3, the void helper): claimocity_void_deceased.py - the helper that VOIDS a visit dated after the day on record - has a marker now: ONE sentence in its header that only this version has. The mirror's table and the feed helpers' list hold that very sentence, and the helper is on the list of helpers the feed's driver makes the repository's before anything runs (FEED_HELPERS): an older copy in a workspace - it read the feed's own cache file of before - is replaced, and never comes back over the repository's",
          lambda: bool(V) and len(V) > 40 and V == HC5.VERSION_LINES.get("claimocity_void_deceased.py") and vsrc.count(V) == 1 and sum(1 for l in hlines if V in l) == 1 and "claimocity_void_deceased.py" in HC5.FEED_HELPERS
          and "deceased_guard.py" in HC5.FEED_HELPERS and len(HC5.FEED_HELPERS) == len(set(HC5.FEED_HELPERS)) == 18, (V, HC5.VERSION_LINES.get("claimocity_void_deceased.py"), len(HC5.FEED_HELPERS)))
    check("markers (D3, the void helper): ... and nothing else of that helper changed: below its header it reads the guard's ONE cache through the guard, as before (deceased_guard._load) - never a cache file of its own",
          lambda: "cache = deceased_guard._load()" in vsrc and "deceased_cache_local" not in vsrc and 'void_tx.void_charge(num, c.get("id"))' in vsrc and "DECEASED_CACHE" not in vsrc, vsrc[:300])
def drive_tool(*argv):
    """dg_drive.py started as the prompts start it (a program, inside this process) -> (its exit code, what it printed, its error output)"""
    return run_main("scripts/helpers/dg_drive.py", [str(x) for x in argv], TMP)
KEEP_NAME = "deceased_cache_unreadable"      # the folder dg_drive.py keeps an unreadable cache file in, under the system's temporary folder
REPLACED_LINE = ("DECEASED CACHE REPLACED: %s could not be read - kept as %s; the Drive copy's table stands in its place - the kept file holds days of death: upload it to Drive \"workspace mirror\" under its own name"
                 " in this run and never copy it into registers/ or the repository - TOP OF THE REPORT")
@contextlib.contextmanager
def kept_in(folder=None, system_tmp=None):
    """While the block runs: DG_UNREADABLE_DIR names `folder` (None = the environment names none) and the system's temporary folder is `system_tmp` (None = as it
    is). dg_drive.py reads both at the moment it keeps a file."""
    old_env, old_tmp = os.environ.pop("DG_UNREADABLE_DIR", None), tempfile.tempdir
    try:
        if folder is not None: os.environ["DG_UNREADABLE_DIR"] = folder
        if system_tmp is not None: tempfile.tempdir = system_tmp
        yield
    finally:
        os.environ.pop("DG_UNREADABLE_DIR", None); tempfile.tempdir = old_tmp
        if old_env is not None: os.environ["DG_UNREADABLE_DIR"] = old_env
def files_under(root):
    """every file under a folder, as paths relative to it (a folder that is not there holds none)"""
    return sorted(os.path.relpath(os.path.join(d_, f_), root) for d_, _s, fs_ in os.walk(root) for f_ in fs_)
def t_drive_unreadable_cache():
    """S2 (the fourth round - the third independent check, finding 3) as D2 of the fifth round changed it (the fourth check's finding 1, HIGH). Until the third round
    step 0c's merge wrote over a cache file it could not read; the third round passed such a file over and it was never repaired; the fourth round kept it under
    another name IN ITS OWN FOLDER and wrote the merged table in its place - and from registers/ the run's own mirror step copied the kept file into the clone, where
    the privacy gate passed it over for its ending and `git add -A` staged it: real days of death beside chart numbers, bound for a public repository. Now the kept
    file NEVER lies in a registers folder and NEVER inside a git checkout: it goes to <the system's temporary folder>/deceased_cache_unreadable/ (DG_UNREADABLE_DIR
    names another folder; one inside a checkout or under a registers folder is refused). The bytes are COPIED there and checked before the new table takes the
    file's place - so it works across devices, and the file never leaves its path unless it is kept. ONE line 'DECEASED CACHE REPLACED: ...' names the kept file by
    its full path and says what a run does with it; exit 0 when every path was merged. What cannot be kept anywhere is left as it is: 'DECEASED CACHE NOT MERGED:
    ...', exit 1. And pack on a cache that cannot be read ends with one plain line and exit 2 - never a traceback."""
    reset(); a, b = cid(), cid(); d = os.path.join(TMP, "s2"); os.makedirs(os.path.join(d, "there")); drive = os.path.join(d, "drive.json"); keep = os.path.join(TMP, "s2_kept")
    json.dump({"dated": {a: [iso(ago(50)), iso(ago(9))]}, "nodeath": {b: iso(ago(3))}}, open(drive, "w"))
    cut, lst, good, new, empty, nodir = (os.path.join(d, n) for n in ("cut_off.json", "a_list.json", "good.json", os.path.join("there", "not_yet.json"), "empty.json", os.path.join("no_such_folder", "x.json")))
    texts = {cut: '{"%s": {"dod": "20' % a, lst: "[1, 2, 3]", good: json.dumps({a: {"dod": PLACEHOLDER, "checked": iso(ago(30)), "src": "x"}}), empty: "  \n"}
    for p, t in texts.items(): open(p, "w").write(t)
    with kept_in(keep): code, out, err = drive_tool("unpack", drive, cut, good, lst, new, empty)
    lines = out.splitlines(); said = [l for l in lines if l.startswith("DECEASED CACHE REPLACED: ")]
    aside = {p: sorted(n for n in (os.listdir(keep) if os.path.isdir(keep) else []) if n.startswith(os.path.basename(p) + ".unreadable-")) for p in (cut, lst)}
    merged = {p: _try(lambda p=p: json.load(open(p))) for p in (cut, lst, good, new, empty)}
    check("drive merge (S2, D2): a cache file that is there but cannot be read - cut off in the middle, or no table at all (a JSON list) - is KEPT byte for byte under its own name + '.unreadable-<UTC stamp>' in the folder for such files, and NOT in its own folder any more: nothing it may hold is lost, and nothing with a day in it lies beside the cache",
          lambda: all(len(v) == 1 and re.fullmatch(re.escape(os.path.basename(p)) + r"\.unreadable-\d{8}T\d{6}Z", v[0]) for p, v in aside.items()) and text_of(os.path.join(keep, aside[cut][0])) == texts[cut] and text_of(os.path.join(keep, aside[lst][0])) == texts[lst] and err == ""
          and not any(".unreadable-" in n for n in files_under(d)) and sorted(os.listdir(keep)) == sorted(aside[cut] + aside[lst]), (aside, files_under(d), err[-300:]))
    check("drive merge (S2): ... and the merged table - what the Drive copy gives - is written in its place, so the run knows the days again (the third round left the file as it was: every later run started with a guard that knew nothing of it); the other paths are merged as always - a file that holds a table, a file that is not there yet, an empty file",
          lambda: all(m != "raised" and m[a]["dod"] == iso(ago(50)) and m[b]["dod"] is None for m in merged.values()) and any(l.startswith("dated entries merged: 5") for l in lines), (merged, lines))
    check("drive merge (S2, D2): ... each such path is said in ONE line for the top of the report that names the kept file by its FULL path and says what a run does with it - upload it to Drive under its own name in this run, never copy it into registers/ or the repository - and names no chart; the command ends 0: every path was merged",
          lambda: code == 0 and said == [REPLACED_LINE % (p, os.path.join(keep, aside[p][0])) for p in (cut, lst)]
          and not any(l.startswith("DECEASED CACHE NOT MERGED") for l in lines) and not any(a in l or b in l for l in lines), (code, lines))
    with kept_in(keep): code2, out2, err2 = drive_tool("unpack", drive, good, new)
    check("drive merge (S2): ... with every path readable the command ends 0 and says no such line, as before", lambda: code2 == 0 and "DECEASED CACHE" not in out2 and err2 == "" and out2.strip().startswith("dated entries merged: "), (code2, out2, err2[-200:]))
    before = text_of(good)
    with kept_in(keep): code3, out3, err3 = drive_tool("unpack", drive, nodir, good)
    said3 = [l for l in out3.splitlines() if l.startswith("DECEASED CACHE NOT MERGED: ")]
    check("drive merge (S2): a path that cannot be WRITTEN (its folder is not there) keeps the line 'DECEASED CACHE NOT MERGED: ...' and ends the command 1 - the path behind it is still merged; no half-written file and no temporary file is left anywhere",
          lambda: code3 == 1 and len(said3) == 1 and nodir in said3[0] and said3[0].endswith(" - TOP OF THE REPORT") and err3 == "" and json.load(open(good))[a]["dod"] == iso(ago(50)) and not os.path.exists(os.path.dirname(nodir))
          and sorted(os.listdir(d)) == ["a_list.json", "cut_off.json", "drive.json", "empty.json", "good.json", "there"] and os.listdir(os.path.join(d, "there")) == ["not_yet.json"]
          and not any(".tmp" in n for n in os.listdir(d)), (code3, out3, err3[-300:], sorted(os.listdir(d))))
    # ---- D2: WHERE the kept file lies. Days of death are real patient data: never in a registers folder (the mirror step copies that folder into the clone), never inside a git checkout
    sys_tmp = os.path.join(TMP, "s2_system_tmp"); os.makedirs(sys_tmp); ws = os.path.join(TMP, "s2_ws", "home", "claude", "unbilled"); os.makedirs(os.path.join(ws, "registers"))
    clone = os.path.join(TMP, "s2_ws", "home", "claude", "clone"); os.makedirs(os.path.join(clone, ".git")); os.makedirs(os.path.join(clone, "practices", "ehpa", "registers"))
    wsc = os.path.join(ws, "registers", "deceased_cache.json"); clc = os.path.join(clone, "practices", "ehpa", "registers", "deceased_cache.json"); open(wsc, "w").write(texts[cut]); open(clc, "w").write(texts[cut] + " ")
    with kept_in(None, sys_tmp): code4, out4, err4 = drive_tool("unpack", drive, wsc, clc)
    kd = os.path.join(sys_tmp, KEEP_NAME); kept4 = sorted(os.listdir(kd)) if os.path.isdir(kd) else []; said4 = [l for l in out4.splitlines() if l.startswith("DECEASED CACHE REPLACED: ")]
    check("drive merge (D2, the place): the workspace's cut-off cache in registers/ and the clone's cut-off register inside a git checkout, merged by ONE command as step 0c does, with no folder named in the environment - BOTH are kept under <the system's temporary folder>/deceased_cache_unreadable/, each under a name of its own with its own bytes, and each line names its own kept file",
          lambda: code4 == 0 and err4 == "" and len(kept4) == 2 and sorted(text_of(os.path.join(kd, n)) for n in kept4) == sorted([texts[cut], texts[cut] + " "]) and len(said4) == 2
          and all(any(l == REPLACED_LINE % (p, os.path.join(kd, n)) and text_of(os.path.join(kd, n)) == t for n in kept4) for p, t, l in ((wsc, texts[cut], said4[0]), (clc, texts[cut] + " ", said4[1]))), (code4, out4, err4[-300:], kept4))
    check("drive merge (D2, the place): ... NOTHING is left in the workspace's registers folder but the cache itself, and nothing new anywhere inside the checkout - the kept file never lies where the mirror step, the state bundle or `git add -A` picks it up; both caches hold the merged table",
          lambda: os.listdir(os.path.join(ws, "registers")) == ["deceased_cache.json"] and files_under(clone) == [os.path.join("practices", "ehpa", "registers", "deceased_cache.json")]
          and json.load(open(wsc))[a]["dod"] == json.load(open(clc))[a]["dod"] == iso(ago(50)), (files_under(os.path.dirname(ws)), files_under(clone)))
    res = {}
    for name, folder in (("a folder inside a git checkout", os.path.join(clone, "kept_here")), ("the checkout's own top folder", clone), ("a folder named registers", os.path.join(TMP, "s2_other", "registers")),
                         ("a folder under a registers folder", os.path.join(ws, "registers", "kept")), ("a folder named REGISTERS", os.path.join(TMP, "s2_other", "REGISTERS")), ("a good folder", os.path.join(TMP, "s2_good_place"))):
        stmp = os.path.join(TMP, "s2_tmp_" + str(len(res))); os.makedirs(stmp); one = os.path.join(TMP, "s2_case_%d.json" % len(res)); open(one, "w").write(texts[cut])
        with kept_in(folder, stmp): c_, o_, e_ = drive_tool("unpack", drive, one)
        res[name] = (c_, e_, files_under(os.path.join(stmp, KEEP_NAME)), [n for n in files_under(folder) if ".unreadable-" in n] if os.path.isdir(folder) else [], _try(lambda: json.load(open(one))[a]["dod"]), [l for l in o_.splitlines() if l.startswith("DECEASED CACHE")])
    refused = ("a folder inside a git checkout", "the checkout's own top folder", "a folder named registers", "a folder under a registers folder", "a folder named REGISTERS")
    check("drive merge (D2, the place): DG_UNREADABLE_DIR names the folder - but a folder that lies inside a git checkout, or is a registers folder or lies under one (in any letter case), is REFUSED: the system's temporary folder is used instead and nothing is written into the refused folder; a good folder is used as named, and nothing goes to the temporary folder then",
          lambda: all(res[k][0] == 0 and res[k][1] == "" and len(res[k][2]) == 1 and res[k][3] == [] and res[k][4] == iso(ago(50)) and len(res[k][5]) == 1 and res[k][5][0].startswith("DECEASED CACHE REPLACED: ") for k in refused)
          and res["a good folder"][0] == 0 and res["a good folder"][2] == [] and len(res["a good folder"][3]) == 1 and res["a good folder"][4] == iso(ago(50)), res)
    # ... a move across devices: every step that would RENAME a file from one folder into another is refused, as between two file systems (the fourth round moved the file with one such step)
    DD = load("scripts/helpers/dg_drive.py", "dg_drive"); far = os.path.join(d, "far_away"); os.makedirs(far); x1 = os.path.join(far, "x.json"); open(x1, "w").write(texts[cut]); keep_far = os.path.join(TMP, "s2_kept_far")
    def other_device(s_, t_, real):
        if os.path.dirname(os.path.abspath(s_)) != os.path.dirname(os.path.abspath(t_)): raise OSError(18, "Invalid cross-device link (stand-in)")
        return real(s_, t_)
    DD.os = types.SimpleNamespace(**{k: getattr(os, k) for k in dir(os) if not k.startswith("__")}); DD.os.replace = lambda s_, t_: other_device(s_, t_, os.replace); DD.os.rename = lambda s_, t_: other_device(s_, t_, os.rename)
    DD.shutil = types.SimpleNamespace(move=lambda s_, t_, *a_, **k_: other_device(s_, t_, shutil.move))
    bad = []; buf = io.StringIO()
    with kept_in(keep_far), contextlib.redirect_stdout(buf): n9 = _try(lambda: DD.unpack(drive, [x1], bad))
    k9 = sorted(os.listdir(keep_far)) if os.path.isdir(keep_far) else []
    check("drive merge (D2, across devices): the folder for kept files lies on another file system - no file can be renamed from one folder into the other: the unreadable file is kept all the same, byte for byte (its bytes are copied and read back before anything takes its place), the merged table stands at its path, one REPLACED line, nothing counted as not merged",
          lambda: n9 != "raised" and bad == [] and len(k9) == 1 and text_of(os.path.join(keep_far, k9[0])) == texts[cut] and json.load(open(x1))[a]["dod"] == iso(ago(50)) and os.listdir(far) == ["x.json"]
          and [l for l in buf.getvalue().splitlines() if l.startswith("DECEASED CACHE")] == [REPLACED_LINE % (x1, os.path.join(keep_far, k9[0]))], (n9, bad, k9, buf.getvalue()[-400:]))
    # ... a folder for kept files that cannot be written
    wall = os.path.join(TMP, "s2_a_file_in_the_way"); open(wall, "w").write("a file where a folder would have to be"); x2, x3 = os.path.join(d, "kept_elsewhere.json"), os.path.join(d, "nowhere_to_keep.json")
    open(x2, "w").write(texts[cut]); open(x3, "w").write(texts[cut]); stmp2 = os.path.join(TMP, "s2_tmp_second"); os.makedirs(stmp2)
    with kept_in(os.path.join(wall, "kept"), stmp2): c10, o10, e10 = drive_tool("unpack", drive, x2)
    k10 = files_under(os.path.join(stmp2, KEEP_NAME))
    with kept_in(os.path.join(wall, "kept"), os.path.join(wall, "tmp")): c11, o11, e11 = drive_tool("unpack", drive, x3, good)
    said11 = [l for l in o11.splitlines() if l.startswith("DECEASED CACHE")]
    check("drive merge (D2, a folder that cannot be written): the folder the environment names cannot be made - the system's temporary folder takes the file instead (kept, replaced, exit 0). And when NO folder can take it, the merged table is NOT written: the file is left EXACTLY as it is - it may hold a day only it knows - with the line 'DECEASED CACHE NOT MERGED: ...', exit 1, no temporary file, and the path behind it is still merged",
          lambda: c10 == 0 and e10 == "" and len(k10) == 1 and text_of(os.path.join(stmp2, KEEP_NAME, k10[0])) == texts[cut] and json.load(open(x2))[a]["dod"] == iso(ago(50))
          and c11 == 1 and e11 == "" and text_of(x3) == texts[cut] and len(said11) == 1 and said11[0].startswith("DECEASED CACHE NOT MERGED: " + x3) and said11[0].endswith(" - TOP OF THE REPORT")
          and "its bytes could be kept in no folder outside the registers folders and the git checkouts - it was left exactly as it is, never written over" in said11[0]      # (the line says WHY: nothing took the file's bytes - not 'could not be written')
          and "nowhere_to_keep.json.unreadable" not in " ".join(files_under(TMP)) and not any(".tmp" in n for n in os.listdir(d)) and text_of(wall) == "a file where a folder would have to be", (c10, k10, c11, o11[-500:], e11[-300:]))
    x4 = os.path.join(d, "tmp_in_a_checkout.json"); open(x4, "w").write(texts[cut]); in_tree = os.path.join(clone, "tmp")
    with kept_in(None, in_tree): c12, o12, e12 = drive_tool("unpack", drive, x4)
    check("drive merge (D2): ... and when the system's temporary folder ITSELF lies inside a git checkout and the environment names no other, there is no place for the file that is safe: it is left exactly as it is, NOT MERGED, exit 1 - never kept inside the checkout",
          lambda: c12 == 1 and e12 == "" and text_of(x4) == texts[cut] and not os.path.exists(in_tree) and files_under(clone) == [os.path.join("practices", "ehpa", "registers", "deceased_cache.json")]
          and [l.startswith("DECEASED CACHE NOT MERGED: " + x4) for l in o12.splitlines() if l.startswith("DECEASED CACHE")] == [True], (c12, o12[-400:], e12[-200:], files_under(clone)))
    # an unreadable file in a folder that takes no new file: the new table cannot be written beside it - left as it is, said, exit 1, and no copy of it is kept anywhere (shown with the tool's own two file steps refused for that folder)
    DD = load("scripts/helpers/dg_drive.py", "dg_drive"); ro = os.path.join(d, "read_only"); os.makedirs(ro); stuck = os.path.join(ro, "stuck.json"); open(stuck, "w").write(texts[cut]); real = (DD.os.replace, DD.tempfile.mkstemp); keep_ro = os.path.join(TMP, "s2_kept_ro")
    def no_file(*a_, **k_): raise PermissionError(13, "the stand-in folder takes no new file")
    DD.os = types.SimpleNamespace(**{k: getattr(os, k) for k in dir(os) if not k.startswith("__")}); DD.os.replace = lambda s_, t_: no_file() if os.path.dirname(os.path.abspath(t_)) == ro else real[0](s_, t_)
    DD.tempfile = types.SimpleNamespace(mkstemp=lambda *a_, **k_: no_file() if os.path.abspath(k_.get("dir") or "") == ro else real[1](*a_, **k_), gettempdir=tempfile.gettempdir)
    bad = []; buf = io.StringIO()
    with kept_in(keep_ro), contextlib.redirect_stdout(buf): n4 = _try(lambda: DD.unpack(drive, [stuck, good], bad))
    said4 = [l for l in buf.getvalue().splitlines() if l.startswith("DECEASED CACHE")]
    check("drive merge (S2): ... and an unreadable file whose own folder takes no new file - the new table cannot be written there - is left EXACTLY as it is and said 'NOT MERGED': never half replaced, never lost, and no copy of it is left in the folder for kept files (nothing was replaced, so nothing is kept); the path counts as not merged (exit 1) and the path behind it is merged",
          lambda: n4 != "raised" and bad == [stuck] and text_of(stuck) == texts[cut] and os.listdir(ro) == ["stuck.json"] and len(said4) == 1 and said4[0].startswith("DECEASED CACHE NOT MERGED: " + stuck) and said4[0].endswith(" - TOP OF THE REPORT")
          and files_under(keep_ro) == [], (n4, bad, said4, os.listdir(ro), files_under(keep_ro)))
    DD = load("scripts/helpers/dg_drive.py", "dg_drive"); half = os.path.join(d, "half_way"); os.makedirs(half); stuck2 = os.path.join(half, "stuck.json"); open(stuck2, "w").write(texts[cut]); keep_half = os.path.join(TMP, "s2_kept_half")
    DD.os = types.SimpleNamespace(**{k: getattr(os, k) for k in dir(os) if not k.startswith("__")})      # the LAST step fails: the new table cannot be put in the file's place (its bytes are kept by then)
    DD.os.replace = lambda s_, t_: no_file() if os.path.basename(s_).startswith(".deceased_cache.") and os.path.abspath(t_) == stuck2 else os.replace(s_, t_)
    bad2 = []; buf2 = io.StringIO()
    with kept_in(keep_half), contextlib.redirect_stdout(buf2): n5 = _try(lambda: DD.unpack(drive, [stuck2], bad2))
    said5 = [l for l in buf2.getvalue().splitlines() if l.startswith("DECEASED CACHE")]
    check("drive merge (S2, D2): ... and when the LAST step fails - the file's bytes are kept already and the new table cannot be put in its place - the file still stands at its path exactly as it was (it never left it), and the copy that was kept is taken away again: the file is either kept AND replaced, or left exactly as it is; no second copy with days in it and no temporary file stays behind",
          lambda: n5 != "raised" and bad2 == [stuck2] and text_of(stuck2) == texts[cut] and os.listdir(half) == ["stuck.json"] and len(said5) == 1 and said5[0].startswith("DECEASED CACHE NOT MERGED: " + stuck2)
          and files_under(keep_half) == [], (n5, bad2, said5, os.listdir(half), files_under(keep_half)))
    folder = os.path.join(d, "a_folder.json"); os.makedirs(folder)
    with kept_in(keep): code7, out7, err7 = drive_tool("unpack", drive, folder, good)
    said7 = [l for l in out7.splitlines() if l.startswith("DECEASED CACHE")]
    check("drive merge (S2): ... a path that is no file at all (a folder of that name) is not kept anywhere: left as it is, said 'NOT MERGED', the command ends 1 and the path behind it is merged",
          lambda: code7 == 1 and err7 == "" and os.path.isdir(folder) and os.listdir(folder) == [] and len(said7) == 1 and said7[0].startswith("DECEASED CACHE NOT MERGED: " + folder) and not any(n.startswith("a_folder.json.unreadable-") for n in os.listdir(keep)), (code7, out7, err7[-200:]))
    twice = os.path.join(d, "twice.json"); open(twice, "w").write(texts[cut]); now_ = datetime.datetime.now(datetime.timezone.utc); keep2 = os.path.join(TMP, "s2_kept_twice"); os.makedirs(keep2)
    taken = [os.path.join(keep2, "twice.json.unreadable-" + (now_ + datetime.timedelta(seconds=s_)).strftime("%Y%m%dT%H%M%SZ")) for s_ in range(5)]      # the names the tool would choose in these seconds are TAKEN: files an earlier merge kept
    for n_ in taken: open(n_, "w").write("kept by an earlier merge")
    with kept_in(keep2): code8, out8, err8 = drive_tool("unpack", drive, twice)
    kept8 = sorted(os.path.join(keep2, n_) for n_ in os.listdir(keep2) if n_.startswith("twice.json.unreadable-")); new8 = [n_ for n_ in kept8 if n_ not in taken]
    check("drive merge (S2): ... and a name that is taken already - a file an earlier merge kept in the same second - is never used again: the unreadable file gets a name of its own, and the file kept before stays byte for byte",
          lambda: code8 == 0 and err8 == "" and all(text_of(n_) == "kept by an earlier merge" for n_ in taken) and len(new8) == 1 and text_of(new8[0]) == texts[cut] and ("kept as %s;" % new8[0]) in out8
          and _try(lambda: json.load(open(twice))[a]["dod"]) == iso(ago(50)), (code8, out8, err8[-200:], [os.path.basename(n_) for n_ in kept8]))
    DD = load("scripts/helpers/dg_drive.py", "dg_drive"); full = os.path.join(d, "disk_full"); os.makedirs(full); stuck3 = os.path.join(full, "stuck.json"); open(stuck3, "w").write(texts[cut]); keep_full = os.path.join(TMP, "s2_kept_full")
    def no_room(*a_, **k_): raise OSError(28, "No space left on device (stand-in)")
    DD.json = types.SimpleNamespace(load=json.load, loads=json.loads, dumps=json.dumps, dump=no_room)      # the new table cannot be written to its temporary file
    bad3 = []; buf3 = io.StringIO()
    with kept_in(keep_full), contextlib.redirect_stdout(buf3): n6 = _try(lambda: DD.unpack(drive, [stuck3], bad3))
    said6 = [l for l in buf3.getvalue().splitlines() if l.startswith("DECEASED CACHE")]
    check("drive merge (S2): ... the unreadable file's bytes are kept only when the new table is safely written beside it: when that table cannot be written (the disk is full) nothing is kept anywhere - the file stands at its path exactly as it was, said 'NOT MERGED', and no temporary file is left",
          lambda: n6 != "raised" and bad3 == [stuck3] and text_of(stuck3) == texts[cut] and os.listdir(full) == ["stuck.json"] and len(said6) == 1 and said6[0].startswith("DECEASED CACHE NOT MERGED: " + stuck3) and files_under(keep_full) == [], (n6, bad3, said6, os.listdir(full)))
    # ---- what the fifth round's own mutation pass let through at first (each now with its check): a link, a copy nobody read back, who may read the kept file
    link_c, link_r = os.path.join(TMP, "s2_link_into_the_checkout"), os.path.join(TMP, "s2_link_to_a_registers_folder"); os.makedirs(os.path.join(clone, "by_link")); os.symlink(os.path.join(clone, "by_link"), link_c); os.symlink(os.path.join(ws, "registers"), link_r)
    lres = {}
    for name, folder in (("a link into a git checkout", link_c), ("a link to a registers folder", link_r)):
        stmp = os.path.join(TMP, "s2_tmp_link_%d" % len(lres)); os.makedirs(stmp); one = os.path.join(TMP, "s2_link_case_%d.json" % len(lres)); open(one, "w").write(texts[cut])
        with kept_in(folder, stmp): c_, o_, e_ = drive_tool("unpack", drive, one)
        lres[name] = (c_, e_, files_under(os.path.join(stmp, KEEP_NAME)), [n for n in files_under(os.path.realpath(folder)) if ".unreadable-" in n], _try(lambda: json.load(open(one))[a]["dod"]))
    check("drive merge (D2, the place): a LINK is judged by where it LEADS - DG_UNREADABLE_DIR names a link whose own path looks harmless and that points into a git checkout, or at a registers folder: it is refused as the folder itself is, the system's temporary folder takes the file and nothing is written through the link",
          lambda: all(v[0] == 0 and v[1] == "" and len(v[2]) == 1 and v[3] == [] and v[4] == iso(ago(50)) for v in lres.values()), lres)
    DD = load("scripts/helpers/dg_drive.py", "dg_drive"); x5 = os.path.join(d, "short_copy.json"); open(x5, "w").write(texts[cut]); keep_sw, tmp_sw = os.path.join(TMP, "s2_kept_short"), os.path.join(TMP, "s2_tmp_short"); os.makedirs(tmp_sw)
    class Short:      # a file that takes fewer bytes than it is given and says nothing (a full disk on some file systems, a mount that drops out)
        def __init__(self, fh): self.fh = fh
        def write(self, data): return self.fh.write(data[:len(data) // 2])
        def __enter__(self): return self
        def __exit__(self, *a_): self.fh.close()
    DD.os = types.SimpleNamespace(**{k: getattr(os, k) for k in dir(os) if not k.startswith("__")}); DD.os.fdopen = lambda fd_, mode_="r", *a_, **k_: Short(os.fdopen(fd_, mode_, *a_, **k_)) if "b" in mode_ else os.fdopen(fd_, mode_, *a_, **k_)
    bad7 = []; buf7 = io.StringIO()
    with kept_in(keep_sw, tmp_sw), contextlib.redirect_stdout(buf7): n7 = _try(lambda: DD.unpack(drive, [x5], bad7))
    said8 = [l for l in buf7.getvalue().splitlines() if l.startswith("DECEASED CACHE")]
    check("drive merge (D2): the kept copy is READ BACK and compared before anything takes the file's place - a copy that came out short (the folder took fewer bytes than it was given and said nothing) is no copy: it is taken away again in every folder that was tried, and the file is left exactly as it is, NOT MERGED - never replaced on the strength of a copy nobody checked",
          lambda: n7 != "raised" and bad7 == [x5] and text_of(x5) == texts[cut] and files_under(keep_sw) == [] and files_under(os.path.join(tmp_sw, KEEP_NAME)) == [] and len(said8) == 1
          and said8[0].startswith("DECEASED CACHE NOT MERGED: " + x5) and "its bytes could be kept in no folder outside the registers folders and the git checkouts" in said8[0] and not any(".tmp" in n for n in os.listdir(d)),
          (n7, bad7, said8, files_under(keep_sw), files_under(tmp_sw)))
    m_file, m_dir = os.stat(os.path.join(keep, aside[cut][0])).st_mode & 0o777, os.stat(keep).st_mode & 0o777
    check("drive merge (D2): the kept file holds days of death - only the user the run works as can read it (mode 600), and the folder the tool made for it is that user's alone (mode 700)", lambda: m_file == 0o600 and m_dir == 0o700, (oct(m_file), oct(m_dir)))
    # pack on a cache that cannot be read: one plain line, exit 2, never a traceback - and nothing is written for Drive
    outp = os.path.join(d, "for_drive.json"); res = []; pcut, plst = os.path.join(d, "pack_cut_off.json"), os.path.join(d, "pack_a_list.json"); open(pcut, "w").write(texts[cut]); open(plst, "w").write(texts[lst])
    for src in (pcut, plst, os.path.join(d, "no_such_cache.json")):
        c5, o5, e5 = _try(lambda: drive_tool("pack", src, outp), ("raised", "", "")); res.append((c5, [l for l in o5.splitlines() if l.strip()], e5, os.path.exists(outp)))
    check("drive copy (S2): pack on a cache that cannot be read - cut off, no table, not there - ends with ONE plain line for the top of the report and exit 2: never a traceback (the run's last step ended on a Python error), and no file for Drive is written",
          lambda: all(r[0] == 2 and len(r[1]) == 1 and r[1][0].startswith("DECEASED CACHE NOT PACKED: ") and r[1][0].endswith(" - TOP OF THE REPORT") and r[2] == "" and r[3] is False for r in res) and "Traceback" not in json.dumps(res), res)
    c6, o6, e6 = drive_tool("pack", good, outp)
    check("drive copy (S2): ... and a cache that can be read is packed as always: exit 0, the counts of the three lists in one line", lambda: c6 == 0 and e6 == "" and o6.strip().startswith("packed dated/nodeath/noday: (") and os.path.exists(outp), (c6, o6, e6))
    reset(); DD = load("scripts/helpers/dg_drive.py", "dg_drive"); same = cid(); odd = os.path.join(TMP, "drive_odd.json")
    mine = {same: {"dod": iso(ago(45)), "checked": iso(ago(20)), "src": "stedi-medicare-271"}}; put_cache(json.loads(json.dumps(mine)))
    json.dump({"dated": {a: iso(ago(50)), b: [iso(ago(40)), 20261101], same: [iso(ago(45)), 20261101], cid(): [iso(ago(30))], "x": None}, "nodeath": {cid(): 7, cid(): None}}, open(odd, "w"))
    n = _try(lambda: DD.unpack(odd, [DCACHE])); got = cache_json() or {}
    check("drive merge: a hand-made Drive copy whose entries are not in the tool's own shape - a bare day where [day, checked] belongs, a check date that is a number, a list of one - does not end the merge on an error (it did): what can be read is taken, the rest is passed over",
          lambda: n != "raised" and got.get(b, {}).get("dod") == iso(ago(40)) and all(isinstance(v, dict) for v in got.values()), (n, got))
    check("drive merge (d15, the 'dated' list): ... a day whose check date is no text - a number, a table - is a day with NO check date: written so for a chart the cache does not know, and compared as such with an entry that holds the same day (that entry stays as it is - the merge ended on an error there)",
          lambda: n != "raised" and got.get(b) == {"dod": iso(ago(40)), "checked": None, "src": "stedi-medicare-271 (drive copy)"} and got.get(same) == mine[same], (n, got.get(b), got.get(same)))
    # d17 (a one-line change the fourth check made that no check noticed): a hand-made copy whose LISTS are not tables
    res = []
    for name, copy in (("'dated' is a list", {"dated": [a, iso(ago(50))], "nodeath": {b: iso(ago(3))}, "noday": {}}), ("'nodeath' is a list", {"dated": {a: [iso(ago(50)), iso(ago(9))]}, "nodeath": [b], "noday": {}}),
                       ("'noday' is a text", {"dated": {a: [iso(ago(50)), iso(ago(9))]}, "nodeath": {b: iso(ago(3))}, "noday": "none"}), ("'dated' is a number", {"dated": 7, "nodeath": {b: iso(ago(3))}}),
                       ("the copy is a list", [1, 2, 3]), ("the copy is a text", "nothing")):
        f17 = os.path.join(TMP, "drive_d17_%d.json" % len(res)); json.dump(copy, open(f17, "w")); c17 = os.path.join(TMP, "cache_d17_%d.json" % len(res)); json.dump({same: mine[same]}, open(c17, "w"))
        cc, oo, ee = _try(lambda: drive_tool("unpack", f17, c17), ("raised", "", "")); res.append((name, cc, ee[-200:], "Traceback" in oo + ee, _try(lambda: json.load(open(c17)))))
    by = {r[0]: r for r in res}
    check("drive merge (d17): a hand-made Drive copy whose 'dated', 'nodeath' or 'noday' is no table - a list, a number, a text - or that is no table itself merges with exit 0 and never ends on a traceback: such a list counts as an empty one, the lists that ARE tables are still merged, and what the cache held stays",
          lambda: all(r[1] == 0 and r[2] == "" and r[3] is False and r[4] != "raised" and r[4].get(same) == mine[same] for r in res)
          and by["'dated' is a list"][4].get(b, {}).get("dod", "x") is None and a not in by["'dated' is a list"][4] and by["'nodeath' is a list"][4].get(a, {}).get("dod") == iso(ago(50)) and b not in by["'nodeath' is a list"][4]
          and by["'noday' is a text"][4].get(a, {}).get("dod") == iso(ago(50)) and by["'dated' is a number"][4].get(b, {}).get("dod", "x") is None and sorted(by["the copy is a list"][4]) == sorted(by["the copy is a text"][4]) == [same], res)
# ==== 4b. the guard asks AdvancedMD's FREE check first (William 11/25/2026 - rules A1 to A11 of his order) ======================
BLOCK = "pat%s DOS %s is after date of death %s (%s) - claim must not be submitted; void the charge"
UNVERIFIED = "pat%s DOS %s: date of death UNVERIFIED (lookup failed)"
def counts():
    """The guard's COUNTS as (asked free, answered free, bought); None on a guard that keeps none."""
    c = getattr(DG, "COUNTS", None)
    return tuple(c.get(k) for k in ("free asked", "free answered", "paid asked")) if isinstance(c, dict) else None
def free_is(pid, i=1, **kw): FREE[ins(pid, i)] = ("answer", free271(**kw))
def free_death(pid, p, **kw): free_is(pid, p=p, death8=p["death8"], **dict(dict(status="inactive"), **kw))      # Medicare answers INACTIVE after a death, and gives the date
def guard_said(pid, dos, carrier="car6085", proc="99309"):
    """The guard's answer and everything it printed, on both streams."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out): r = DG.check(pid, dos, carrier, proc)
    return r, out.getvalue()
def src_of(pid): return ((cache_json() or {}).get(pid) or {}).get("src")
def mchart(p, number="same"):
    """A new invented chart with ONE open Medicare plan that holds the person's own number (or the number given)."""
    return chart(cid(), p, plans=[("car6085", "", p["number"] if number == "same" else number)])
def cache_checked(pid, day):
    """Write another 'checked' day into the chart's cache entry (an entry made some days ago)."""
    c = cache_json(); c[pid]["checked"] = iso(day)
    with open(DCACHE, "w") as fh: json.dump(c, fh)
def plain_body(p, dos):
    """The plain Medicare check the guard buys for this person - the vendor call exactly as it was before the free check."""
    return {"tradingPartnerServiceId": "CMS", "provider": ST.PROV, "subscriber": {"firstName": p["first"], "lastName": p["last"], "dateOfBirth": p["dob8"], "memberId": p["number"]},
            "encounter": {"serviceTypeCodes": ["30"], "dateOfService": ymd(dos)}}

def t_free_was_on():
    n = FREE_TOTAL[0]
    check("free first: every guard check above ran with the free check ON and asked first - the stand-in AdvancedMD was asked some 34 times and answered 'Medicare cannot answer now' each time - so each of them also proves that an unusable free answer leaves the paid path exactly as it was (A2)",
          lambda: n >= 30 and FREE == {}, n)

def t_free_death():
    reset(); dead = newp(death=ago(20)); dos = ago(5); pid = mchart(dead); free_death(pid, dead)
    r, said = guard_said(pid, iso(dos)); c = (cache_json() or {}).get(pid)
    check("free first (A2 i, A3): a date of death in AdvancedMD's free answer blocks the claim in the same words, source amd-medicare-271 - and NOTHING is bought",
          lambda: r == (True, BLOCK % (pid, iso(dos), iso(ago(20)), "amd-medicare-271")) and SENT == [] and log_lines() == [], (r, kinds()))
    check("free first (A1, A6): ONE free check - on the chart's Medicare plan, by the digits of its insurance-plan id, service type 30, with a 60-second time-out",
          lambda: FREE_ASKED == [(ins(pid), "30", 60)], FREE_ASKED)
    check("free first (A3): the cache keeps that date with src 'amd-medicare-271', checked today", lambda: c == {"dod": iso(ago(20)), "checked": iso(TODAY), "src": "amd-medicare-271"}, c)
    check("free first (A7): COUNTS = 1 asked free, 1 answered free, 0 bought; the guard printed nothing and logged nothing", lambda: counts() == (1, 1, 0) and said == "" and DG.LOG == [], (counts(), said, DG.LOG))
    del FREE_ASKED[:]; r2 = guard_check(pid, iso(ago(1)))
    check("free first (A11): a death in the cache -> the chart's next claim is blocked with no call at all, free or paid", lambda: r2[0] is True and FREE_ASKED == [] and SENT == [] and counts() == (1, 1, 0), (r2, FREE_ASKED, kinds(), counts()))
    _try(lambda: cache_checked(pid, ago(45))); free_is(pid, p=dict(dead, death8=None)); r3 = guard_check(pid, iso(ago(1))); c3 = (cache_json() or {}).get(pid)
    check("free first (A3, A11): a death is never undone - the entry 45 days old (older than the 30 days) and AdvancedMD now ready to answer 'no death': the claim is still blocked from the cache, nothing is asked, free or paid, and the entry stays as it was",
          lambda: r3 == (True, BLOCK % (pid, iso(ago(1)), iso(ago(20)), "amd-medicare-271")) and FREE_ASKED == [] and SENT == [] and c3 == {"dod": iso(ago(20)), "checked": iso(ago(45)), "src": "amd-medicare-271"} and counts() == (1, 1, 0), (r3, FREE_ASKED, kinds(), c3))
    res = []
    for name, kw in (("beside INACTIVE", dict(status="inactive")), ("beside a rejection (AAA 72)", dict(status="rejected", aaa=("72",))), ("beside ACTIVE lines (an ended plan answers so)", dict(status="active")),
                     ("in the JSON shape", dict(status="inactive", shape="json")), ("in an answer AdvancedMD kept from 3 days ago", dict(status="inactive", stamp=3)), ("in an answer with no stamp", dict(status="inactive", stamp=None))):
        reset(); d = newp(death=ago(12)); pid = mchart(d); free_death(pid, d, **kw)
        r = guard_check(pid, iso(ago(3))); res.append((name, r == (True, BLOCK % (pid, iso(ago(3)), iso(ago(12)), "amd-medicare-271")), kinds(), counts(), src_of(pid)))
    check("free first (A2 i): a date of death is taken whatever else the free answer says - beside INACTIVE, beside a rejection, beside ACTIVE lines, in the JSON shape, in an answer kept from an earlier day or with no stamp (a death is never undone): blocked, nothing bought",
          lambda: len(res) == 6 and all(x[1] and x[2] == [] and x[3] == (1, 1, 0) and x[4] == "amd-medicare-271" for x in res), res)
    reset(); d2 = newp(death=first_of_month(TODAY)); h = mchart(d2); free_death(h, d2)
    rc = guard_check(h, iso(first_of_month(TODAY) + datetime.timedelta(days=1)), proc="99490"); ro = guard_check(h, iso(first_of_month(TODAY)), proc="99490")
    check("free first (A3): the care-management wording in the month of death is the same from a free answer, and a date of service on the date of death is not blocked",
          lambda: rc[0] is True and "(amd-medicare-271)" in rc[1] and rc[1].endswith("; CCM in the month of death needs a DOS on/before the death date, else void") and ro == (False, "") and SENT == [], (rc, ro))
    reset(); d3 = newp(death=ago(9)); k = chart(cid(), d3, plans=[("car6404", "", "M" + "4" * 9), ("car6085", "", d3["number"])]); free_death(k, d3, i=2)
    r = guard_check(k, iso(ago(2)), carrier=None, proc="99490")
    check("free first: a care-management claim whose payer the caller does not know (the feed's entry check) is checked too - the free check goes to the chart's Medicare plan and its date of death blocks, nothing bought (the sixth round: billed to another payer it is never looked up - t_guard_day_lost)",
          lambda: r[0] is True and FREE_ASKED == [(ins(k, 2), "30", 60)] and SENT == [], (r, FREE_ASKED, kinds()))
    reset(); d4 = newp(death=ago(9)); m = mchart(d4); free_death(m, d4); r = guard_check(m, mdy(ago(2)), carrier="FLO02", proc="99309")
    check("free first: a straight-Medicare claim named by its carrier code (FLO02), its date of service written MM/DD/YYYY as the insurance check passes it, is checked the same way - blocked from the free answer, nothing bought",
          lambda: r == (True, BLOCK % (m, iso(ago(2)), iso(ago(9)), "amd-medicare-271")) and FREE_ASKED == [(ins(m), "30", 60)] and SENT == [], (r, FREE_ASKED, kinds()))
    d8 = ymd(ago(12)); res = []
    for bad in (d8[:7], d8 + "-" + d8, d8[:4] + "1340", "0" * 8, "D8" + d8[2:]):
        reset(); q = newp(); pid = mchart(q); FREE[ins(pid)] = ("answer", free271(q, status="inactive", death8=bad))
        r = guard_check(pid, iso(ago(3))); res.append((bad, r, kinds(), counts(), src_of(pid)))
    check("free first (A2): a date of death that is not 8 digits (7 digits, a range, letters) or is no calendar date is NOT an answer - nothing is taken from it and the plain check is bought as before",
          lambda: len(res) == 5 and all(x[1] == (False, "") and x[2] == ["CMS"] and x[3] == (1, 0, 1) and x[4] == "stedi: no death on record" for x in res), res)

def t_free_alive():
    reset(); p = newp(); pid = mchart(p); free_is(pid, p=p)
    r, said = guard_said(pid, iso(ago(2))); c = (cache_json() or {}).get(pid)
    check("free first (A2 ii, A3): a free answer with no rejection, ACTIVE, Part A and Part B, stamped today and with no date of death is kept as 'amd: no death on record', checked today - nothing blocked, nothing bought",
          lambda: r == (False, "") and SENT == [] and log_lines() == [] and c == {"dod": None, "checked": iso(TODAY), "src": "amd: no death on record"} and FREE_ASKED == [(ins(pid), "30", 60)], (r, kinds(), c, FREE_ASKED))
    check("free first (A7, A9): for that answer the guard prints nothing and logs nothing; COUNTS = 1 asked free, 1 answered free, 0 bought", lambda: said == "" and DG.LOG == [] and counts() == (1, 1, 0), (said, DG.LOG, counts()))
    check("free first: an answer that shows no death is not put into the Medicare answer store - the guard's own cache is what it reads (the store file is not even made)", lambda: FREE_ASKED != [] and store_json() is None, store_json())
    del FREE_ASKED[:]; r2 = guard_check(pid, iso(ago(1)))
    check("free first: a second claim of that chart the same day asks nothing, free or paid (the cache entry is today's)", lambda: r2 == (False, "") and FREE_ASKED == [] and SENT == [] and counts() == (1, 1, 0), (r2, FREE_ASKED, kinds(), counts()))
    def variants(rows, make):
        res = []
        for name, value, usable in rows:
            reset(); q = newp(); pid = mchart(q); free_is(pid, p=q, **make(value)); r = guard_check(pid, iso(ago(2)))
            res.append((name, r == (False, "") and kinds() == ([] if usable else ["CMS"]) and counts() == ((1, 1, 0) if usable else (1, 0, 1)) and src_of(pid) == ("amd" if usable else "stedi") + ": no death on record", kinds(), counts(), src_of(pid)))
        return res
    res = variants((("Part B alone", ("MB",), True), ("Part A alone", ("MA",), True), ("ACTIVE lines but neither Part A nor Part B", ("HM",), False)), lambda v: dict(parts=v))
    rj = variants((("the JSON shape", "json", True),), lambda v: dict(shape=v))
    check("free first (A2 ii): Part A or Part B must be shown - Part B alone, Part A alone and the JSON shape are answers (nothing bought); ACTIVE lines with neither are not (the plain check is bought as before)",
          lambda: len(res) == 3 and all(x[1] for x in res + rj), res + rj)
    res = variants((("its three stamps are of today on AdvancedMD's clock, 7 hours behind UTC", 0, True), ("kept from 2 days ago", 2, False), ("created 3 days ago, the response stamped today", (3, 0, 0), False),
                    ("no stamp at all", None, False), ("a stamp that is no date", "soon", False)), lambda v: dict(stamp=v))
    check("free first (A2): the free answer carries its own stamps (created, changed, response) - 'no death on record' is taken only when all of them are of today; an answer AdvancedMD kept from an earlier day, one with an older stamp among the three, one with no stamp or an unreadable one is not an answer (the plain check is bought as before)",
          lambda: len(res) == 5 and all(x[1] for x in res), res)
    res = variants((("created today, CHANGED 3 days ago, the response today", (0, 3, 0), False), ("created and changed today, the RESPONSE 3 days ago", (0, 0, 3), False),
                    ("created today, changed and response 3 days ago", (0, 3, 3), False), ("the three stamps written out one by one, all of today", (0, 0, 0), True)), lambda v: dict(stamp=v))
    names = _try(lambda: tuple(DG.FREE_STAMPS))
    check("free first (A2, review finding 6e and 6f): EACH of the answer's three stamps counts - created today but changed 3 days ago, or the response 3 days old, is an answer AdvancedMD kept, not one of today (the plain check is bought as before); the three names are the ones a captured answer carries",
          lambda: len(res) == 4 and all(x[1] for x in res) and names == ("eligibilitycreatedat", "eligibilitychangedat", "eligibilityresponsedate"), (res, names))
    def at(utc, machine=0):
        """A stand-in datetime module pinned to one moment: now() in UTC is `utc`; this machine's own clock runs `machine` hours off it."""
        class _DT(datetime.datetime):
            @classmethod
            def now(cls, tz=None): return utc.replace(tzinfo=datetime.timezone.utc) if tz else utc + datetime.timedelta(hours=machine)
        class _D(datetime.date):
            @classmethod
            def today(cls): return (utc + datetime.timedelta(hours=machine)).date()
        return types.SimpleNamespace(datetime=_DT, date=_D, timedelta=datetime.timedelta, timezone=datetime.timezone)
    def of_today(stamp, utc, machine=0):
        real = DG.datetime; DG.datetime = at(utc, machine)
        try: return DG._free_today({"amd": {k: stamp for k in DG.FREE_STAMPS}})
        finally: DG.datetime = real
    eve = "%02d/%02d/%d 10:23PM" % (9, 24, 2026); U = datetime.datetime
    clock = _try(lambda: [of_today(eve, U(2026, 9, 25, 5, 30)), of_today(eve, U(2026, 9, 25, 7, 30)), of_today("%02d/%02d/%d 11:35PM" % (11, 24, 2026), U(2026, 11, 25, 6, 35), machine=-5),
                          of_today(eve, U(2026, 9, 25, 9, 0)), of_today(eve, U(2026, 9, 26, 5, 30))])
    check("free first (A2): 'today' is read on AdvancedMD's own clock, 7 hours behind UTC - a captured answer, asked at 05:30 UTC on the 25th, is stamped 10:23PM of the 24th and IS of today (so is one read half an hour after AdvancedMD's midnight, and one read at 1:35 AM on a machine on Eastern time); the same stamp two hours into AdvancedMD's next day, or a day later, is not",
          lambda: clock == [True, True, True, False, False], clock)
    reset(); p = newp(); pid = mchart(p); free_is(pid, p=p); guard_check(pid, iso(ago(40))); n = []
    for day, dos in ((ago(30), ago(40)), (ago(31), ago(40)), (ago(10), ago(5))):
        _try(lambda: cache_checked(pid, day)); del FREE_ASKED[:]; guard_check(pid, iso(dos)); n.append(len(FREE_ASKED))
    check("free first (A3): the staleness rule is unchanged for a free 'no death' entry - 30 days old it is used with no call; 31 days old, or checked before the claim's date of service, the free check is asked again (and answers: still nothing bought)",
          lambda: n == [0, 1, 1] and SENT == [] and cache_json()[pid] == {"dod": None, "checked": iso(TODAY), "src": "amd: no death on record"}, (n, kinds()))
    ws = os.path.join(TMP, "free_cwd"); os.makedirs(ws, exist_ok=True); here = os.getcwd(); reset(); p = newp(); pid = mchart(p); free_is(pid, p=p)
    os.chdir(ws)
    try: r = guard_check(pid, iso(ago(2)))
    finally: os.chdir(here)
    check("free first (A8): the guard asks amd.check_eligibility itself and reads the answer with elig_amd.summarize - nothing is written in the working directory (no patient_db/ folder, no copy of the answer)",
          lambda: r == (False, "") and FREE_ASKED == [(ins(pid), "30", 60)] and os.listdir(ws) == [], (FREE_ASKED, os.listdir(ws)))

def t_free_unusable():
    real = ST.medicare; calls = []
    def spy(*a, **k): calls.append((a, dict(k))); return real(*a, **k)
    cases = (("a rejection (AAA 72: the number is not valid)", lambda p: ("answer", free271(p, status="rejected", aaa=("72",)))),
             ("a rejection beside ACTIVE lines (AAA 42)", lambda p: ("answer", free271(p, aaa=("42",)))),
             ("INACTIVE with no date of death", lambda p: ("answer", free271(p, status="inactive"))),
             ("UNKNOWN (no benefit line and no rejection)", lambda p: ("answer", free271(p, status="unknown"))),
             ("a JSON body that is no eligibility answer", lambda p: ("answer", {"message": "try again"})),
             ("a body that cannot be read (PARSE ERROR)", lambda p: ("answer", "<PPMDResults><Results")),
             ("an empty body", lambda p: ("answer", "")),
             ("HTTP 500 with an error page", lambda p: ("http", 500)),
             ("HTTP 401 with a complete ACTIVE answer in its body", lambda p: ("http", 401, free271(p))),
             ("a time-out", lambda p: ("timeout",)),
             ("an error on the way", lambda p: ("raise",)))
    ST.medicare = spy; res = []
    try:
        for name, make in cases:
            reset(); del calls[:]; p = newp(); dos = ago(2); pid = mchart(p); FREE[ins(pid)] = make(p)
            r = guard_check(pid, iso(dos))
            res.append({"case": name, "r": r, "free": list(FREE_ASKED) == [(ins(pid), "30", 60)], "sent": [b for _, b in SENT] == [plain_body(p, dos)], "src": src_of(pid), "counts": counts(), "log": list(DG.LOG),
                        "call": calls == [((p["first"], p["last"], p["dob8"]), dict(member_id=p["number"], dos=ymd(dos), state="FL", pid=pid, who="guard", max_age_days=30))],
                        "usage": [(l[1], l[2], l[4]) for l in log_lines()] == [("guard", "plain Medicare", pid)]})
    finally: ST.medicare = real
    asked = lambda x: x["free"] and x["counts"] == (1, 0, 1)
    check("free first (A2): a rejection (72; 42 beside ACTIVE lines), INACTIVE with no date, UNKNOWN, a body that is no answer or cannot be read, an HTTP status other than 200 (even with a complete answer in its body), a time-out, an error on the way - none is an answer: the free check was asked once and nothing was taken from it",
          lambda: len(res) == len(cases) and all(asked(x) for x in res), [(x["case"], x["free"], x["counts"]) for x in res if not asked(x)][:4])
    same = lambda x: x["r"] == (False, "") and x["call"] and x["sent"] and x["src"] == "stedi: no death on record" and x["usage"] and x["log"] == []
    check("free first (A2, A11): ... and after each of them the paid call is made exactly as before, with the same arguments - stedi.medicare(first, last, birth date, the plan's number, the date of service, FL, the chart, 'guard', 30 days) - ONE plain check to the vendor, kept as 'stedi: no death on record', the usage line as before, no LOG line",
          lambda: len(res) == len(cases) and all(asked(x) and same(x) for x in res), [(x["case"], x["r"], x["call"], x["sent"], x["src"], x["usage"], x["log"]) for x in res if not same(x)][:3])
    reset(); d = newp(death=ago(9)); pid = mchart(d); FREE[ins(pid)] = ("answer", free271(d, status="unknown")); r = guard_check(pid, iso(ago(2)))
    check("free first (A2): after an unusable free answer a death the vendor's answer shows blocks as before, source stedi-medicare-271",
          lambda: r == (True, BLOCK % (pid, iso(ago(2)), iso(ago(9)), "stedi-medicare-271")) and kinds() == ["CMS"] and counts() == (1, 0, 1), (r, kinds(), counts()))
    reset(); p = newp(); pid = mchart(p); FREE[ins(pid)] = ("timeout",); OVERRIDE[("CMS", p["number"])] = ("timeout",); r = guard_check(pid, iso(ago(2)))
    check("free first (A2, A7): no usable free answer and the vendor's call fails too -> nothing is blocked, nothing is kept, and the LOG line is word for word as before",
          lambda: r == (False, "") and kinds() == ["CMS"] and DG.LOG == [UNVERIFIED % (pid, iso(ago(2)))] and (cache_json() or {}).get(pid) is None and counts() == (1, 0, 1), (r, DG.LOG, counts()))

def t_free_plan():
    def one(plans, want, dos=ago(2), carrier="car6085", proc="99309"):
        """-> (the free check went to plan `want` and to no other, the number the vendor was asked with, the number on that plan, the vendor calls, COUNTS, who the usage log names)"""
        reset(); p = newp(); mine = plans(p); pid = chart(cid(), p, plans=mine); guard_check(pid, iso(dos), carrier, proc)
        sub = SENT[0][1].get("subscriber", {}) if SENT else {}
        return ([x[0] for x in FREE_ASKED] == ([ins(pid, want)] if want else []), sub.get("memberId"), ST.medicare_number(mine[want - 1][2]) if want else None, kinds(), counts(), log_lines()[0][1] if log_lines() else None)
    a = one(lambda p: [("car6085", mdy(ago(400)), WRONG[0]), ("car6085", "", spaced(p["number"])), ("car6404", "", "M" + "5" * 9)], 2)
    check("free first (A1): the free check goes to the chart's OPEN Medicare plan - an ended one listed before it and a plan of another payer are passed over - and when it gives no answer the vendor is asked with that same plan's number",
          lambda: a[0] and a[1] == a[2] is not None and a[3] == ["CMS"] and a[4] == (1, 0, 1), a)
    b = one(lambda p: [("car6085", mdy(ago(100)), p["number"]), ("car6085", mdy(ago(900)), WRONG[1])], 1)
    c = one(lambda p: [("car6085", mdy(ago(900)), WRONG[1]), ("car6085", mdy(ago(100)), p["number"])], 2)
    d = one(lambda p: [("car6085", mdy(ago(3)), p["number"]), ("car6085", mdy(ago(1)), WRONG[2])], 1, dos=ago(5))
    check("free first (A1): no open Medicare plan -> the one that ended last, whichever is listed first; a plan that ended on or after the date of service is open for that claim (the first such plan) - each time the plan whose number the vendor is asked with: the very choice made for the number",
          lambda: all(x[0] and x[1] == x[2] is not None and x[3] == ["CMS"] for x in (b, c, d)), (b, c, d))
    on = one(lambda p: [("car6085", mdy(ago(5)), p["number"]), ("car6085", mdy(ago(1)), WRONG[2])], 1, dos=ago(5))
    check("free first (A1): a plan that ended ON the date of service itself is still open for that claim - it is the plan asked about, free and paid", lambda: on[0] and on[1] == on[2] is not None and on[3] == ["CMS"], on)
    e = one(lambda p: [("car6404", "", "M" + "6" * 9)], 0, carrier=None, proc="99490")      # (the sixth round: a care-management charge whose payer the caller does not know)
    check("free first (A1, A11): no Medicare plan on the chart -> NO free check; the look-up by name runs exactly as before, counted 'guard, no Medicare plan on the chart'; COUNTS = 0 asked free, 1 bought (a care-management charge whose payer is not known)",
          lambda: e[0] and e[3] == ["MBILUNOSSN"] and e[5] == "guard, no Medicare plan on the chart" and e[4] == (0, 0, 1), e)
    f = one(lambda p: [("car6085", "", "")], 1)
    check("free first (A1): a Medicare plan with no number on it is still the chart's Medicare plan - the free check is asked about it, and when it gives no answer the look-up is bought as before, counted 'guard'",
          lambda: f[0] and f[3] == ["MBILUNOSSN"] and f[5] == "guard" and f[4] == (1, 0, 1), f)
    reset(); p = newp(); pid = mchart(p); free_is(pid, p=p); real_post = fake_amd.post
    fake_amd.post = lambda body, timeout=0: real_post(body, timeout).replace(' id="ins%s"' % ins(pid), "")
    try: r = guard_check(pid, iso(ago(2)))
    finally: fake_amd.post = real_post
    check("free first (A1): a Medicare plan the chart answer shows with no plan id cannot be asked about - no free check, the plain check as before",
          lambda: r == (False, "") and FREE_ASKED == [] and kinds() == ["CMS"] and counts() == (0, 0, 1), (FREE_ASKED, kinds(), counts()))

def t_free_order():
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=mdy(ago(30))); free_is(pid, p=p)
    r = guard_check(pid, iso(ago(5)))
    check("free first: the chart's own deceased field still comes first - blocked from it, and neither the free check nor the vendor is asked",
          lambda: r[0] is True and FREE_ASKED == [] and SENT == [] and counts() == (0, 0, 0) and cache_json()[pid]["dod"] == iso(ago(30)), (r, FREE_ASKED, counts()))
    reset(); p = newp(); pid = mchart(p); free_is(pid, p=p)
    r1 = guard_check(pid, iso(ago(2)), carrier="car6404", proc="99213"); n1 = (len(FREE_ASKED), len(SENT), len(BILLING))
    err = io.StringIO()
    with contextlib.redirect_stderr(err): r2 = DG.check(pid, iso(ago(2)), "car6085", "99490", allow_lookup=False)
    n2 = (len(FREE_ASKED), len(SENT), len(BILLING))
    check("free first: WHEN an answer is needed is unchanged - a claim that is neither straight Medicare nor care management asks nothing, and a caller that passes allow_lookup=False asks nothing, free or paid (not even the chart is read)",
          lambda: r1 == r2 == (False, "") and n1 == n2 == (0, 0, 0) and counts() == (0, 0, 0), (r1, r2, n1, n2, counts()))
    reset(); q = newp(); pid = mchart(q); dos = ago(2); free_is(pid, p=q)
    askp(q, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=0); os.remove(DCACHE)         # another helper bought today's answer; the guard's cache did not come along
    r = guard_check(pid, iso(dos))
    check("free first: an answer another helper bought is in the answer store - the guard uses it as before and asks nothing, free or paid (one paid call in all; COUNTS all zero)",
          lambda: len(SENT) == 1 and FREE_ASKED == [] and r == (False, "") and src_of(pid) == "stedi: no death on record" and counts() == (0, 0, 0), (kinds(), FREE_ASKED, src_of(pid), counts()))
    res = []
    for died in (False, True):
        reset(); q = newp(); pid = mchart(q)
        askp(q, dos=ymd(ago(5)), pid=pid, who="pre-claim check", max_age_days=0)                    # alive when asked
        store_edit(lambda d: d["charts"][pid]["answers"][0].update(asked=iso(ago(20)))); os.remove(DCACHE)
        if died: q["death8"] = ymd(ago(10)); free_death(pid, q)                                       # the patient died after that answer was asked
        else: free_is(pid, p=q)
        del SENT[:]; r = guard_check(pid, iso(ago(5))); res.append((r, kinds(), list(FREE_ASKED) == [(ins(pid), "30", 60)], src_of(pid), counts()))
    check("free first: an answer in the store that was asked BEFORE the claim's date of service cannot know of a death since - where one plain check was bought, the FREE check is now asked and answers: 'no death' is kept with nothing bought, and a death since then blocks the claim with nothing bought",
          lambda: res[0] == ((False, ""), [], True, "amd: no death on record", (1, 1, 0)) and res[1][0][0] is True and "after date of death %s (amd-medicare-271)" % iso(ago(10)) in res[1][0][1] and res[1][1:] == ([], True, "amd-medicare-271", (1, 1, 0)), res)
    reset(); d = newp(death=ago(4)); pid = mchart(d); dos = ago(2)
    askp(d, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=0)                              # a bought answer that shows the death
    store_edit(lambda x: x["charts"][pid]["answers"][0].update(asked=iso(ago(3)))); os.remove(DCACHE)
    free_is(pid, p=dict(d, death8=None))                                                               # the free check would now answer 'no death'
    del SENT[:]; r = guard_check(pid, iso(dos))
    check("free first: a death an answer in the store already shows is used as it is, as before - the claim is blocked with no call at all, free or paid, even when the free check would answer 'no death' (a death is never undone; the free check never makes the guard weaker)",
          lambda: r[0] is True and "after date of death %s (stedi-medicare-271)" % iso(ago(4)) in r[1] and FREE_ASKED == [] and SENT == [] and counts() == (0, 0, 0), (r, FREE_ASKED, kinds(), counts()))
    res = []
    for usable in (True, False):
        reset(); p = newp(); pid = mchart(p); OVERRIDE[("CMS", p["number"])] = ("timeout",)
        askp(p, dos=ymd(ago(2)), pid=pid, who="pre-claim check", max_age_days=0); OVERRIDE.clear(); del SENT[:]      # another helper's paid call failed today
        if usable: free_is(pid, p=p)
        r = guard_check(pid, iso(ago(2))); res.append((r, kinds(), len(FREE_ASKED), src_of(pid), list(DG.LOG), counts()))
    check("free first: a chart whose paid call failed earlier today is not bought again today, as before - but the free check costs nothing and is asked: its answer is kept; when it gives none the chart stays UNVERIFIED, exactly as before",
          lambda: res[0] == ((False, ""), [], 1, "amd: no death on record", [], (1, 1, 0)) and res[1][:4] == ((False, ""), [], 1, None) and len(res[1][4]) == 1 and "UNVERIFIED" in res[1][4][0] and res[1][5] == (1, 0, 0), res)

def t_free_switch():
    res = []
    for word in ("off", "OFF", " Off ", "0", "no", "false"):
        reset(); d = newp(death=ago(9)); pid = mchart(d); free_death(pid, d); os.environ["DEATH_CHECK_FREE"] = word
        try: r = guard_check(pid, iso(ago(2)))
        finally: os.environ.pop("DEATH_CHECK_FREE", None)
        res.append((word, r == (True, BLOCK % (pid, iso(ago(2)), iso(ago(9)), "stedi-medicare-271")), list(FREE_ASKED), kinds(), src_of(pid), counts()))
    check("free first (A5): DEATH_CHECK_FREE=off (any case; also 0 / no / false) -> the free check is never tried: the paid check is made as before (here it finds the death), COUNTS = 0 asked free, 1 bought",
          lambda: len(res) == 6 and all(x[1] and x[2] == [] and x[3] == ["CMS"] and x[4] == "stedi-medicare-271" and x[5] == (0, 0, 1) for x in res), res)
    res = []
    for word in (None, "on", "1", ""):
        reset(); d = newp(death=ago(9)); pid = mchart(d); free_death(pid, d)
        if word is not None: os.environ["DEATH_CHECK_FREE"] = word
        try: r = guard_check(pid, iso(ago(2)))
        finally: os.environ.pop("DEATH_CHECK_FREE", None)
        res.append((word, r[0], list(FREE_ASKED) == [(ins(pid), "30", 60)], kinds(), src_of(pid)))
    check("free first (A5): by default - the variable not set - and with any other word the free check is ON", lambda: len(res) == 4 and all(x[1] is True and x[2] and x[3] == [] and x[4] == "amd-medicare-271" for x in res), res)

def t_free_down():
    def run(plan):
        """A new run with one chart per letter: T a time-out, H HTTP 503, X an error on the way, P a body that cannot be read, E an empty body, C a complete answer cut off in the middle,
        A a rejection, U a usable answer, - what the stand-in says by default.
        -> (free checks asked per chart, every chart answered 'no death' from the right source, COUNTS, the guard's free_down())"""
        reset(); asked = []; right = []
        for k in plan:
            p = newp(); pid = mchart(p)
            if k != "-": FREE[ins(pid)] = {"T": ("timeout",), "H": ("http", 503), "X": ("raise",), "P": ("answer", "<PPMDResults><Results"), "E": ("answer", ""), "C": ("answer", free271(p)[:len(free271(p)) // 2]),
                                           "A": ("answer", free271(p, status="rejected", aaa=("72",))), "U": ("answer", free271(p))}[k]
            n = len(FREE_ASKED); r = guard_check(pid, iso(ago(2))); asked.append(len(FREE_ASKED) - n)
            right.append(r == (False, "") and src_of(pid) == ("amd" if k == "U" else "stedi") + ": no death on record")
        return asked, all(right), counts(), _try(lambda: DG.free_down())
    a = run("TTT--"); ka = kinds(); ta = [x[2] for x in FREE_ASKED]
    check("free first (A4): after 3 free checks in a row that end in a time-out the free check is not tried again in this process - the 4th and 5th chart go straight to the paid check; every chart is still answered as before",
          lambda: a == ([1, 1, 1, 0, 0], True, (3, 0, 5), True) and ka == ["CMS"] * 5, (a, ka))
    check("free first (A6): every free check is asked with a 60-second time-out", lambda: ta == [60, 60, 60], ta)
    b = run("THX-")
    check("free first (A4): a time-out, an HTTP error and an error on the way count alike - 3 in a row and the free check is off",
          lambda: b == ([1, 1, 1, 0], True, (3, 0, 4), True), b)
    c = run("PPP-"); c2 = run("PECUU"); c3 = run("TTPT-")
    check("free first (A4, review finding 4): an answer that came but cannot be read is an unusable answer, not 'down' - it does not count toward the 3 and does not start the count again: three unreadable bodies in a row (cut short, empty, cut off in the middle) leave the free check ON, so the usable answers after them are taken free and not bought; fail, fail, unreadable, fail -> off from the 5th chart",
          lambda: c == ([1, 1, 1, 1], True, (4, 0, 4), False) and c2 == ([1, 1, 1, 1, 1], True, (5, 2, 3), False) and c3 == ([1, 1, 1, 1, 0], True, (4, 0, 5), True), (c, c2, c3))
    d = run("TTAT-"); e = run("AAAA-")
    check("free first (A4): a rejection is not 'down' - it does not count toward the 3 and does not start the count again: fail, fail, rejection, fail -> off from the 5th chart; four rejections in a row switch nothing off",
          lambda: d == ([1, 1, 1, 1, 0], True, (4, 0, 5), True) and e == ([1, 1, 1, 1, 1], True, (5, 0, 5), False), (d, e))
    f = run("TTUTT-"); g = run("TTUTT-T-")
    check("free first (A4): a usable answer starts the count again - fail, fail, usable, fail, fail leaves the free check on (the 6th chart is asked); one more failure and it is off",
          lambda: f == ([1, 1, 1, 1, 1, 1], True, (6, 1, 5), False) and g == ([1, 1, 1, 1, 1, 1, 1, 0], True, (7, 1, 7), True), (f, g))
    h = run("-")
    check("free first (A4): 'in this process' only - the next run starts with the free check on again", lambda: h == ([1], True, (1, 0, 1), False), h)
    new = _try(lambda: load("scripts/helpers/deceased_guard.py", "deceased_guard_new_process"))              # the guard as a new process loads it (the runs above start from reset(), which sets these itself)
    check("free first (A4, A7): a new process starts with nothing behind it - no failure counted, the free check on, COUNTS all at zero",
          lambda: new._FREE_FAILS == [0] and new.free_down() is False and new.COUNTS == {"free asked": 0, "free answered": 0, "paid asked": 0} and new._FREE == {} and new.FREE_DOWN_AFTER == 3)

def t_free_counts():
    check("free first (A7): COUNTS is a dict with exactly the keys 'free asked', 'free answered', 'paid asked', all whole numbers", lambda: list(DG.COUNTS) == ["free asked", "free answered", "paid asked"] and all(type(v) is int for v in DG.COUNTS.values()))
    reset(); a, b, c, d, e = newp(), newp(death=ago(8)), newp(), newp(), newp()
    pa, pb, pc, pd, pe = (mchart(x) for x in (a, b, c, d, e))
    free_is(pa, p=a); free_death(pb, b); FREE[ins(pc)] = ("timeout",)                                                   # d: what the stand-in says by default (not usable)
    askp(e, dos=ymd(ago(2)), pid=pe, who="pre-claim check", max_age_days=0); os.remove(DCACHE); n0 = len(SENT)          # e: another helper bought today's answer
    said = "".join(guard_said(x, iso(ago(2)))[1] for x in (pa, pb, pc, pd, pe))
    guard_check(pa, iso(ago(1))); guard_check(pb, iso(ago(1)))                                                          # second claims: the cache answers
    check("free first (A7): five charts - a free 'no death', a free date of death, a free time-out, an unusable free answer, an answer another helper had bought - give COUNTS = 4 asked free, 2 answered free, 2 bought: an answer read back from the store is neither asked nor bought, second claims count nothing, and the guard printed nothing",
          lambda: counts() == (4, 2, 2) and len(SENT) - n0 == 2 and len(FREE_ASKED) == 4 and said == "", (counts(), kinds(), FREE_ASKED, said))

def t_free_store():
    reset(); d = newp(death=ago(9)); pid = mchart(d); dos = ago(2); free_death(pid, d)
    r = guard_check(pid, iso(dos)); st = store_chart(pid).get("answers") or []
    check("free first: a date of death the free check shows is also noted in the Medicare answer store - nothing was bought, yet the store holds ONE death-only entry (medicare_store.death shows it), with no number, name or birth date in the file",
          lambda: r[0] is True and SENT == [] and _try(lambda: MS.death(pid)) == d["death8"] and len(st) == 1 and st[0]["death"] == d["death8"] and st[0]["who"] == "guard" and st[0]["active"] is None
          and not any(x in text_of(STORE) for x in (d["number"], d["last"], d["dob8"])), (kinds(), st))
    got = [_try(lambda: MS.get(pid, 30, ymd(dos))), _try(lambda: MS.get(pid, 0, ymd(TODAY))), _try(lambda: MS.get(pid, 60, ymd(prev_month(dos)))), _try(lambda: MS.get(pid, 60, None))]
    j, how, err = askp(d, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=(TODAY - first_of_month(dos)).days)
    check("free first: ... and the store serves that entry to NO reader as a Medicare answer - the guard's 30 days, a same-day reader, a reader of last month's visit and one with no date all get nothing, and the pre-claim check buys its own answer exactly as before",
          lambda: len(st) == 1 and got == [None] * 4 and how == "plain" and "stored" not in j and kinds() == ["CMS"], (got, how, kinds()))
    res = []
    for now in (("answer", err_answer("42")), ("timeout",)):
        for free_now in (("timeout",), ("answer", free271(status="rejected", aaa=("42",))), "switched off"):
            reset(); d = newp(death=ago(9)); pid = mchart(d); free_death(pid, d); r0 = guard_check(pid, iso(ago(2))), kinds()   # the free check finds the death (nothing bought)
            os.remove(DCACHE)                                                                          # a machine where the answer store came along and the guard's cache did not
            if free_now == "switched off": os.environ["DEATH_CHECK_FREE"] = "off"
            else: FREE[ins(pid)] = free_now
            OVERRIDE[("CMS", d["number"])] = now; OVERRIDE[("MBILUNOSSN", d["last"])] = now; del SENT[:]; del DG.LOG[:]
            try: r = guard_check(pid, iso(ago(1)))
            finally: os.environ.pop("DEATH_CHECK_FREE", None)
            res.append((now[0], free_now if isinstance(free_now, str) else free_now[0], r0[0][0] is True and r0[1] == [], r, kinds(), list(DG.LOG), ((cache_json() or {}).get(pid) or {}).get("dod")))
    check("free first: a death the FREE check found (nothing bought) still blocks when the guard's cache file is lost and neither the free check (a time-out, a rejection, switched off) nor the vendor (42, a time-out) can answer - blocked by the death noted in the answer store, not UNVERIFIED, and the date is back in the cache",
          lambda: len(res) == 6 and all(x[2] is True and x[3][0] is True and "after date of death %s" % iso(ago(9)) in x[3][1] and x[5] == [] and x[6] == iso(ago(9)) for x in res), res)
    reset(); d = newp(death=ago(9)); pid = mchart(d); free_death(pid, d); guard_check(pid, iso(ago(2))); os.remove(DCACHE); del FREE_ASKED[:]
    r = guard_check(pid, iso(ago(1)))
    check("free first: the cache file lost and AdvancedMD answering - the free check is asked again, shows the death again and blocks; nothing is bought",
          lambda: r == (True, BLOCK % (pid, iso(ago(1)), iso(ago(9)), "amd-medicare-271")) and FREE_ASKED == [(ins(pid), "30", 60)] and SENT == [], (r, FREE_ASKED, kinds()))

def t_free_charge():
    reset(); d = newp(death=ago(30)); pid = mchart(d); free_death(pid, d); dos = ago(3)
    RESAVE["556"] = '<r><visit date="%s"/><patient id="pat%s"/><charge id="charge556" proccode="99490"/><insplan sequence="1" carrier="car6085"/></r>' % (mdy(dos), pid)
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out): r = _try(lambda: DG.check_charge("556", 1))
    tail = "; CCM in the month of death needs a DOS on/before the death date, else void" if iso(dos)[:7] == iso(ago(30))[:7] else "; void the charge"
    check("free first: check_charge - what amd.rebill_charge asks before every rebill - blocks a care-management charge to straight Medicare from the free answer, in the same words, buys nothing and prints nothing",
          lambda: r == (True, "pat%s DOS %s is after date of death %s (amd-medicare-271) - claim must not be submitted" % (pid, iso(dos), iso(ago(30))) + tail) and SENT == [] and out.getvalue() == "" and counts() == (1, 1, 0), (r, kinds(), out.getvalue()))

def t_free_missing():
    reset(); p = newp(); pid = mchart(p); free_is(pid, p=p); real = fake_amd.check_eligibility; del fake_amd.check_eligibility
    try: r = guard_check(pid, iso(ago(2)))
    finally: fake_amd.check_eligibility = real
    a = (r, kinds(), src_of(pid), counts(), list(DG.LOG))
    reset(); p = newp(); pid = mchart(p); free_is(pid, p=p); ea = sys.modules.pop("elig_amd", None)
    try: r = guard_check(pid, iso(ago(2)))
    finally:
        if ea is not None: sys.modules["elig_amd"] = ea
    b = (r, kinds(), src_of(pid), counts(), list(DG.LOG)); n = len(FREE_ASKED)
    check("free first: a workspace whose amd.py has no check_eligibility, or one without elig_amd.py -> no free check and no error: the paid check as before, COUNTS = 0 asked free, 1 bought",
          lambda: a == b == ((False, ""), ["CMS"], "stedi: no death on record", (0, 0, 1), []) and n == 0 and ea is not None, (a, b, n))

def t_free_privacy():
    reset(); d = newp(death=ago(9)); pid = mchart(d); free_death(pid, d); r, said = guard_said(pid, iso(ago(2)))
    q = newp(); pq = mchart(q); FREE[ins(pq)] = ("timeout",); OVERRIDE[("CMS", q["number"])] = ("timeout",); r2, said2 = guard_said(pq, iso(ago(2)))
    w = newp(); pw = mchart(w); free_is(pw, p=w); r3, said3 = guard_said(pw, iso(ago(2)))
    secret = [x[k] for x in (d, q, w) for k in ("number", "last", "dob8")]
    check("privacy (A9): the guard prints nothing for a free answer; the one line it logs, for the chart it could not verify, holds the chart id and the date of service only - no name, birth date, Medicare number or date of death in what it prints or logs",
          lambda: r[0] is True and FREE_ASKED != [] and said + said3 == "" and DG.LOG == [UNVERIFIED % (pq, iso(ago(2)))] and not any(s in said + said2 + said3 + " ".join(DG.LOG) for s in secret + [d["death8"], iso(ago(9))]), (said, said2, said3, DG.LOG))
    check("privacy (A9): the cache keeps the date of death as before (the date, the day checked, the source - nothing else); no name, birth date or Medicare number is in the cache, the usage log or the answer store, although the free answers carried all three",
          lambda: cache_json()[pid] == {"dod": iso(ago(9)), "checked": iso(TODAY), "src": "amd-medicare-271"} and cache_json()[pw] == {"dod": None, "checked": iso(TODAY), "src": "amd: no death on record"}
          and all(s in json.dumps(FREE[ins(pid)]) + json.dumps(FREE[ins(pw)]) for s in (d["number"], d["last"], d["dob8"], w["number"])) and not any(s in text_of(DCACHE) + text_of(ULOG) + text_of(STORE) for s in secret), cache_json())

# ---- 4c. after the independent review of the free-first change (11/25/2026) - each check names the review finding it closes ------
def t_free_death_unreadable():
    def run(death8, died=True, plans=None, **kw):
        """One chart whose free answer is complete - no rejection, ACTIVE, Part A and Part B, stamps of today - but for its date-of-death segment(s) `death8`. The vendor's
        answer (Medicare's own record) shows a death 9 days ago, or none. -> (the guard's answer for a care-management claim dated 2 days ago, the vendor calls, COUNTS,
        the source in the guard's cache, how many free checks, the chart)"""
        reset(); d = newp(death=ago(9) if died else None); pid = chart(cid(), d, plans=plans(d) if plans else [("car6085", "", d["number"])])
        FREE[ins(pid)] = ("answer", free271(d, death8=death8, **kw))
        return guard_check(pid, iso(ago(2)), proc="99490"), kinds(), counts(), src_of(pid), len(FREE_ASKED), pid
    d8 = ymd(ago(9))
    from_paid = lambda x: x[0][0] is True and "after date of death %s (stedi-medicare-271)" % iso(ago(9)) in x[0][1] and x[1:5] == (["CMS"], (1, 0, 1), "stedi-medicare-271", 1)
    from_free = lambda x: x[0][0] is True and "after date of death %s (amd-medicare-271)" % iso(ago(9)) in x[0][1] and x[1:5] == ([], (1, 1, 0), "amd-medicare-271", 1)
    shapes = (("an empty date", ("",), {}), ("no date in the segment at all", (None,), {}), ("null, in the JSON shape", (None,), dict(shape="json")), ("an empty date, in the JSON shape", ("",), dict(shape="json")),
              ("blanks only", ("   ",), {}), ("the real date, then a second segment with an empty date (the reader keeps the last one)", (d8, ""), {}),
              ("an empty date on a chart whose only Medicare plan has ended (such a plan answers with ACTIVE lines)", ("",), dict(plans=lambda p: [("car6085", mdy(ago(30)), p["number"])])))
    res = [(name, run(v, **kw)) for name, v, kw in shapes]
    check("free first (A2, review finding 1): a date-of-death segment whose date cannot be read - empty, missing, null, blanks, or an empty one after the real one - beside ACTIVE lines with Part A and Part B stamped today is NOT 'no death on record': the plain check is bought as before, and the death it shows blocks the claim",
          lambda: len(res) == 7 and all(from_paid(x) for _, x in res), [(n, x[:4]) for n, x in res if not from_paid(x)][:3])
    x = run(("",)); pid = x[5]; del SENT[:]; del FREE_ASKED[:]; r2 = guard_check(pid, iso(ago(1)))
    check("free first (review finding 1): ... and that death is in the guard's cache, so the chart's next claim is blocked with no call at all - the misread answer had been kept as 'amd: no death on record' and let every claim of the chart through for 30 days",
          lambda: from_paid(x) and r2[0] is True and SENT == [] and FREE_ASKED == [] and cache_json()[pid]["dod"] == iso(ago(9)), (x[:4], r2, kinds(), FREE_ASKED))
    res = [(name, run(v, died=False, **kw)[:5]) for name, v, kw in shapes[:5]]
    check("free first (A2, review finding 1): for a patient Medicare's record shows alive such an answer is no answer either - one plain check is bought and kept as 'stedi: no death on record'; a free 'no death on record' is taken only from an answer with NO date-of-death segment in it",
          lambda: len(res) == 5 and all(x == ((False, ""), ["CMS"], (1, 0, 1), "stedi: no death on record", 1) for _, x in res), res)
    a = run(("", d8)); b = run((" %s " % d8,)); c = run(("",), status="inactive")
    check("free first (A2 i): an empty segment followed by the real date, and a date with blanks around it, are read as that date - blocked from the free answer, nothing bought; INACTIVE beside an empty date goes to the paid check, as before",
          lambda: from_free(a) and from_free(b) and from_paid(c), (a[:4], b[:4], c[:4]))
    res = [(bad, run(bad)) for bad in (d8[:7], d8 + "-" + d8, d8[:4] + "1340", "0" * 8, "D8" + d8[2:])]
    check("free first (A2, review finding 6a): a date-of-death text that is no date - 7 digits, a range, no calendar date, eight zeros, letters - beside an otherwise complete ACTIVE answer is no answer either (the check further up tries these texts beside INACTIVE lines only): the plain check is bought and the death it shows blocks",
          lambda: len(res) == 5 and all(from_paid(x) for _, x in res), [(n, x[:4]) for n, x in res if not from_paid(x)][:3])

def t_free_failed_mark():
    reset(); d = newp(death=ago(9)); pid = mchart(d); dos = ago(2); free_death(pid, d); age = (TODAY - first_of_month(dos)).days
    OVERRIDE[("CMS", d["number"])] = ("answer", err_answer("42"))                                                                    # Medicare cannot answer now: the mark then carries the code and its words
    j1, how1, e1 = askp(d, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=age); m1 = store_chart(pid).get("failed")     # the pre-claim check's paid call fails: 'asked and failed today'
    r = guard_check(pid, iso(dos), proc="99490"); m2 = store_chart(pid).get("failed"); n2 = len(SENT); c2 = counts()                   # the guard: nothing bought, the free check shows the death
    j3, how3, e3 = askp(d, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=age)                                              # the pre-claim check asks again the same day
    check("free first (review finding 3): a chart whose paid call failed earlier today, then a free answer with a date of death - the claim is blocked and the death is noted in the answer store, and the store's 'asked and failed today' mark is still there exactly as it was, so the pre-claim check asking again that day buys nothing (ONE vendor request in all)",
          lambda: how1 == "failed" and isinstance(m1, dict) and m1.get("who") == "pre-claim check" and m1.get("dos") == ymd(dos) and m1.get("errors") and "42" in str(m1.get("reason")) and m2 == m1
          and r[0] is True and "(amd-medicare-271)" in r[1] and (n2, c2) == (1, (1, 1, 0))
          and how3 == "failed" and j3["stored"]["how"] == "failed" and len(SENT) == 1 and _try(lambda: MS.death(pid)) == d["death8"], (how1, m1, m2, r, n2, c2, how3, kinds()))
    _try(lambda: store_edit(lambda x: x["charts"][pid]["failed"].update(day=iso(ago(1))))); OVERRIDE.clear(); j4, how4, e4 = askp(d, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=age)
    check("free first (review finding 3): ... the mark stays the day's only - the next day the chart is asked again, as before", lambda: how4 == "plain" and kinds() == ["CMS", "CMS"], (how4, kinds()))
    reset(); d = newp(death=ago(9)); pid = mchart(d); nxt = next_month(TODAY) + datetime.timedelta(days=1); free_death(pid, d)
    askp(d, dos=ymd(TODAY), pid=pid, who="pre-claim check", max_age_days=0)                                                            # today's answer about THIS month's visit: it stays in the store
    OVERRIDE[("CMS", d["number"])] = ("timeout",); askp(d, dos=ymd(nxt), pid=pid, who="pre-claim check", max_age_days=0)                # a call about a date in NEXT month fails today: the mark, beside that answer
    os.remove(DCACHE); m1 = store_chart(pid).get("failed"); n1 = len(SENT); r = guard_check(pid, iso(nxt)); m2 = store_chart(pid).get("failed")
    check("free first (review finding 3): the mark is found and put back also when the store holds an answer of today beside it (a claim dated next month: that answer is about this month's visit and serves nobody asking about the later date)",
          lambda: isinstance(m1, dict) and m1.get("dos") == ymd(nxt) and m2 == m1 and r[0] is True and "(amd-medicare-271)" in r[1] and len(SENT) == n1 == 2 and len(store_chart(pid).get("answers") or []) == 2, (m1, m2, r, kinds(), store_chart(pid).get("answers")))
    reset(); ws = new_ws(); d = newp(death=ago(9)); dos = ago(1); pid = mchart(d); unpaid(pid, "FLO02", dos); free_death(pid, d)
    OVERRIDE[("CMS", d["number"])] = ("timeout",)
    c1, o1, e1 = precheck(ws); row1 = _try(lambda: rows(ws)[pid]["result"]); n1 = len(SENT)
    r = guard_check(pid, iso(dos), proc="99490")
    c3, o3, e3 = precheck(ws); row3 = _try(lambda: rows(ws)[pid]["result"]); said = [l for l in o3.splitlines() if l.startswith("checked ")]
    check("free first (review finding 3): the same with the real pre-claim check run as a program before and after the guard - its second start that day reports the failed check again, says '(0 new lookups)' and sends nothing",
          lambda: row1 == row3 == "ERROR Medicare check failed (time-out)" and n1 == 1 and r[0] is True and len(SENT) == 1 and len(said) == 1 and "(0 new lookups)" in said[0], (row1, row3, r, kinds(), said))
    res = []
    def boom(*a, **k): raise OSError("the answer store cannot be reached (stand-in)")
    for broken in ("written", "read", "read or written"):
        reset(); d = newp(death=ago(9)); pid = mchart(d); free_death(pid, d); real = (MS.put, MS.get)
        if "written" in broken: MS.put = boom
        if "read" in broken: MS.get = boom
        try: r = _try(lambda: guard_check(pid, iso(ago(2))))
        finally: MS.put, MS.get = real
        res.append((broken, r, kinds(), src_of(pid), counts(), _try(lambda: MS.death(pid))))
    check("free first: the note in the answer store never stops the guard - with a store that cannot be written, cannot be read, or neither, the free answer's date of death still blocks and is kept in the guard's cache, and nothing is bought; a store that only cannot be read still gets the note",
          lambda: len(res) == 3 and all(x[1] != "raised" and x[1][0] is True and x[2] == [] and x[3] == "amd-medicare-271" and x[4] == (1, 1, 0) for x in res) and res[1][5] == ymd(ago(9)), res)

def t_free_pins():
    # review finding 6: rules of the free-first code that no check pinned (the guard was right on each of them - a later edit could have lost them with no check failing)
    res = []
    for old in (40, 30):
        reset(); p = newp(); pid = mchart(p); dos = ago(45); free_is(pid, p=p)
        askp(p, dos=ymd(dos), pid=pid, who="pre-claim check", max_age_days=0); os.remove(DCACHE)             # another helper's answer about that visit; the guard's cache did not come along
        store_edit(lambda x: x["charts"][pid]["answers"][0].update(asked=iso(ago(old)))); del SENT[:]
        r = guard_check(pid, iso(dos)); res.append((old, r, kinds(), len(FREE_ASKED), src_of(pid), counts()))
    check("free first (review finding 6b): the answer store is asked with the guard's own 30 days - an answer 40 days old is none the client hands over, so the free check is asked and answers and nothing is bought; one 30 days old is used with no call at all, as before",
          lambda: res == [(40, (False, ""), [], 1, "amd: no death on record", (1, 1, 0)), (30, (False, ""), [], 0, "stedi: no death on record", (0, 0, 0))], res)
    last = first_of_month(TODAY) - datetime.timedelta(days=5)                                                # a visit near the end of LAST month - never this month's, whatever day today is
    reset(); d = newp(death=last - datetime.timedelta(days=6)); pid = mchart(d)
    askp(d, dos=ymd(last), pid=pid, who="pre-claim check", max_age_days=0); os.remove(DCACHE)                # another helper bought the answer about that visit: it shows the death
    store_edit(lambda x: x["charts"][pid]["answers"][0].update(asked=iso(max(last, ago(20)))))
    free_is(pid, p=dict(d, death8=None)); del SENT[:]                                                        # the free check would now answer 'no death'
    r = guard_check(pid, iso(last)); c1 = (r[0], "after date of death %s (stedi-medicare-271)" % iso(last - datetime.timedelta(days=6)) in r[1], list(FREE_ASKED), kinds(), counts())
    reset(); p = newp(); pid = mchart(p); nxt = next_month(TODAY) + datetime.timedelta(days=1); free_is(pid, p=p)
    askp(p, dos=ymd(TODAY), pid=pid, who="pre-claim check", max_age_days=0); os.remove(DCACHE); del SENT[:]  # today's answer, about THIS month's visit
    r = guard_check(pid, iso(nxt)); c2 = (r, kinds(), len(FREE_ASKED), src_of(pid), counts())
    check("free first (review finding 6c): the answer store is asked about the CLAIM's own date of service, not about today - a death an answer about LAST month's visit shows is used as it is (blocked, nothing asked, free or paid, although the free check would answer 'no death'); and today's answer about this month's visit is no answer for a claim dated next month (the free check is asked and answers, nothing is bought)",
          lambda: c1 == (True, True, [], [], (0, 0, 0)) and c2 == ((False, ""), [], 1, "amd: no death on record", (1, 1, 0)), (c1, c2))
    res = []
    for st in (201, 204, 206, 299):
        reset(); d = newp(death=ago(12)); pid = mchart(d); FREE[ins(pid)] = ("http", st, free271(d)); r = guard_check(pid, iso(ago(3)))
        res.append((st, r[0], "(stedi-medicare-271)" in r[1], kinds(), counts(), src_of(pid)))
    check("free first (A2, review finding 6d): only HTTP 200 is an answer - 201, 204, 206 or 299 with a complete ACTIVE answer in the body is not taken: the plain check is bought as before, and the death it shows blocks",
          lambda: len(res) == 4 and all(x[1:] == (True, True, ["CMS"], (1, 0, 1), "stedi-medicare-271") for x in res), res)
    def boom(*a, **k): raise RuntimeError("connection reset")
    reset(); p = newp(); pid = mchart(p); sys.modules["stedi"] = standin("stedi", mbi=boom, med_summ=ST.med_summ)      # an older client (no medicare()) whose look-up raises
    try: r = guard_check(pid, iso(ago(2)))
    finally: sys.modules["stedi"] = ST
    g1 = (r, kinds(), counts(), list(DG.LOG) == [UNVERIFIED % (pid, iso(ago(2)))], src_of(pid))
    reset(); p = newp(); pid = mchart(p); real = ST.medicare; ST.medicare = boom                                       # today's client, and medicare() itself raises
    try: r = guard_check(pid, iso(ago(2)))
    finally: ST.medicare = real
    g2 = (r, kinds(), counts(), list(DG.LOG) == [UNVERIFIED % (pid, iso(ago(2)))], src_of(pid))
    check("free first (A7, review finding 6g): a vendor call that RAISES is still counted as bought - with an older client whose look-up raises and with today's client: COUNTS = 1 asked free, 0 answered free, 1 bought; nothing is blocked and the chart is logged UNVERIFIED, as before",
          lambda: g1 == g2 == ((False, ""), [], (1, 0, 1), True, None), (g1, g2))

def t_free_texts():
    src = _read("scripts/helpers/deceased_guard.py")
    head = " ".join(l.lstrip("# ") for l in src.split("\nimport ", 1)[0].splitlines() if l.startswith("#"))
    said = {x: x in head for x in ("11/25/2026 (William:", "is stedi able to do that for free?", "the vendor is never free", "FIRST asks AdvancedMD's free check", "buys the vendor's answer only when the free check gives no usable answer",
                                   "'amd-medicare-271'", "'amd: no death on record'", "can never make the guard weaker", "After 3 free checks in a row", "DEATH_CHECK_FREE=off", "COUNTS", "nothing of them is printed, logged or kept")}
    check("texts: the guard's header says what it does since 11/25/2026 - William's words, AdvancedMD's free check first and the vendor only when it gives no usable answer, the two new sources, the 3-in-a-row rule, the switch, COUNTS, privacy",
          lambda: all(said.values()), [x for x, ok in said.items() if not ok])
    check("texts: the guard still never names a vendor call of its own, the sentence the look-up texts test reads is still there, and the free check does not go through elig_amd.run_plan (which writes the answer into the working directory)",
          lambda: "requests" not in src and "refuses the plain check for another reason" in head and "stedi.medicare(" in src and "FREE_TIMEOUT = 60" in src and "run_plan(" not in src and "amd.check_eligibility" in src and "elig_amd.summarize(" in src)
    said = {x: x in head for x in ("no date-of-death segment in the answer at all", "a date-of-death segment whose date is empty or is no date", "an answer that came but cannot be read",
                                   "is not 'down'", "leaves the store's 'asked and failed today' mark as it was")}
    check("texts: the guard's header says what the review of that day changed - a 'no death' answer has no date-of-death segment at all and one whose date cannot be read is no answer; an unreadable answer is not 'down'; the death note leaves the store's failed mark as it was",
          lambda: all(said.values()), [x for x, ok in said.items() if not ok])
    line = 'COUNTS = {"free asked": 0, "free answered": 0, "paid asked": 0}'
    mk = re.search(r'"deceased_guard\.py":\s*(\'[^\'\n]*\'|"[^"\n]*")', _read("tools/mirror/mirror.py")); marker = mk.group(1)[1:-1] if mk else None
    check("texts (review finding 2): whatever marker the mirror's table of protected helpers holds for deceased_guard.py is a string BOTH copies of the guard carry - the mirror never refuses the repository's own guard as stale; and the line only the free-first guard has, the one that table can tell an older workspace copy by, stands in each copy exactly once",
          lambda: bool(marker) and marker in src and marker in _read("core/deceased_guard.py") and src.count(line) == 1 and _read("core/deceased_guard.py").count(line) == 1, marker)
    hk = re.search(r'"deceased_guard\.py":\s*(\'[^\'\n]*\'|"[^"\n]*")', _read("scripts/helpers/claimocity_helpers_current.py")); helper_marker = hk.group(1)[1:-1] if hk else None
    check("texts: ... and the feed helpers' own list (claimocity_helpers_current.py) holds that very marker for the guard - one line, once in each copy (which line it is: t_round5_markers)",
          lambda: bool(marker) and marker == helper_marker and src.count(marker) == 1 and _read("core/deceased_guard.py").count(marker) == 1, (marker, helper_marker))
    GATE = load("tools/mirror/phi_gate.py", "phi_gate_under_test")                  # the gate's text transform only: pure, no file, no network
    moved = [n for n in ("scripts/helpers/deceased_guard.py", "core/deceased_guard.py") if GATE.redact(_read(n), {}, code=True) != _read(n)]
    check("texts: the privacy gate's tree rules (what mirror.py runs on changed files) leave the guard exactly as it is - no date in its header sits where the gate would take it for a date of birth or of death", lambda: moved == [], moved)

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
    # review S3: a chart number NOT of the Medicare shape (an old-style number) - the guard's look-up answer is shared; it must still say 'differs'
    reset(); ws = new_ws(); p = newp(); old_style = "".join(str(i) for i in range(1, 10)) + "A"
    pid = chart(cid(), p, plans=[("car6085", "", old_style)]); unpaid(pid, "FLO02", dos)
    guard_check(pid, iso(dos)); n1 = kinds(); del SENT[:]; precheck(ws)
    check("pre-claim: a shared look-up answer on a chart number NOT of the Medicare shape still says the numbers differ -> ONE look-up -> 'MBI MISMATCH chart ... vs CMS ...' (review S3)",
          lambda: n1 == ["MBILUNOSSN"] and kinds() == ["MBILUNOSSN"] and rows(ws)[pid]["result"] == "MBI MISMATCH chart %s vs CMS %s" % (old_style, p["number"])
          and (store_chart(pid).get("answers") or [{}])[0].get("number_differs") is True, (n1, kinds(), rows(ws)[pid].get("result")))
    # review S2: another helper's failed call earlier the same day (42) gives the same words, but is never kept for the month
    reset(); ws = new_ws(); p = newp(advantage=("TEST ADVANTAGE", "H" + str(4521))); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); unpaid(pid, "FLO02", dos)
    OVERRIDE[("CMS", p["number"])] = ("answer", err_answer("42", {"memberId": p["number"]}))
    guard_check(pid, iso(dos)); OVERRIDE.clear(); del SENT[:]
    precheck(ws); r1 = rows(ws)[pid]; n1 = len(SENT); cache1 = json.loads(text_of(os.path.join(ws, "precheck_cache.json")) or "{}")
    store_edit(lambda d: d["charts"][pid]["failed"].update(day=iso(ago(1)))); precheck(ws); r2 = rows(ws)[pid]
    check("pre-claim: another helper's failed Medicare call earlier the same day (42) prints the same words but is NOT kept in its cache for the month - the next night asks and finds the Advantage plan (review S2)",
          lambda: n1 == 0 and r1["result"] == "not found on Medicare: 42 " + DESC["42"] and not any(k.startswith(pid + "|") for k in cache1)
          and kinds() == ["CMS"] and r2["result"].startswith("ADVANTAGE PLAN on DOS: TEST ADVANTAGE") and not r2.get("cached"), (n1, r1.get("result"), sorted(cache1), kinds(), r2.get("result")))
    # re-check NEW-3: the ONE look-up bought for a stored 'number differs' answer (an old-style number, an outdated Medicare-shaped one)
    # comes back 42 - the same words, but NOT kept in its cache for the month: the next run asks again and raises MBI MISMATCH
    res = []
    for number in (old_style, WRONG[3]):
        reset(); ws = new_ws(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", number)]); unpaid(pid, "FLO02", dos)
        guard_check(pid, iso(dos)); del SENT[:]; OVERRIDE[("MBILUNOSSN", p["last"])] = ("answer", err_answer("42"))
        precheck(ws); r1 = rows(ws)[pid]; k1 = kinds(); cache1 = json.loads(text_of(os.path.join(ws, "precheck_cache.json")) or "{}")
        OVERRIDE.clear(); del SENT[:]; precheck(ws); r2 = rows(ws)[pid]
        res.append((k1, r1.get("result"), any(k.startswith(pid + "|") for k in cache1), kinds(), r2.get("result"), "MBI MISMATCH chart %s vs CMS %s" % (number, p["number"])))
    check("pre-claim: the ONE look-up bought for a stored 'number differs' answer comes back 42 -> 'not found on Medicare: 42 ...' as before, NOT kept for the month; the next run asks again and raises MBI MISMATCH (re-check NEW-3)",
          lambda: all(x[0] == ["MBILUNOSSN"] and x[1] == "not found on Medicare: 42 " + DESC["42"] and x[2] is False and x[3] == ["MBILUNOSSN"] and x[4] == x[5] for x in res), [x[:5] for x in res])

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
    core = _read("core/deceased_guard.py")
    check("copies: core/deceased_guard.py carries the free-first rule of 11/25/2026 too (COUNTS with its three keys, the switch, the two new sources)",
          lambda: all(x in core for x in ('COUNTS = {"free asked": 0, "free answered": 0, "paid asked": 0}', "DEATH_CHECK_FREE", '"amd-medicare-271"', '"amd: no death on record"')))

TESTS = [t_prices, t_usage_reader, t_shape, t_plain_good, t_not_found, t_wrong_number, t_suffix, t_no_number, t_down, t_other_refusal, t_ssn, t_med_summ,
         t_usage_log, t_cli, t_store]
GUARD_TESTS = [t_guard_death, t_guard_not_found_failed, t_guard_shared, t_guard_review, t_guard_number, t_guard_flag_cache, t_guard_old_client, t_guard_charge,
               t_guard_day_shapes, t_guard_day_lost, t_guard_charge_unreadable, t_guard_cache_state, t_drive_copy,      # the second verification's findings (section 4a2)
               t_guard_record_keeps, t_drive_merge_keeps, t_guard_flag_no_day, t_guard_covered, t_one_reading_of_a_day, t_guard_odd_entry,      # the independent check of the second round (11/25/2026): its findings, each named in its check
               t_guard_lookup_keeps_day, t_death_on_record_shapes, t_guard_cannot_write, t_guard_lost_words_and_two_days, t_drive_unreadable_cache, t_guard_asked_once,      # the third round (11/25/2026, the second independent check - section 4a3)
               t_no_way_out, t_drive_copy_v2, t_round5_small, t_round5_markers,      # the fifth round (11/26/2026): the tool for a wrongly recorded death is out again; the kept cache file; the small things; the markers
               t_precheck_args, t_precheck_words, t_precheck_store, t_ten_charts]
FREE_TESTS = [t_free_was_on, t_free_death, t_free_alive, t_free_unusable, t_free_plan, t_free_order, t_free_switch, t_free_down, t_free_counts, t_free_store, t_free_charge,
              t_free_missing, t_free_privacy, t_free_death_unreadable, t_free_failed_mark, t_free_pins, t_free_texts]      # 11/25/2026: AdvancedMD's free check first (section 4b) and its review the same day (4c)
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
EA = load("scripts/helpers/elig_amd.py", "elig_amd"); sys.modules["elig_amd"] = EA                                # 11/25/2026: the REAL reader of AdvancedMD's free answer (summarize) - its amd is the stand-in; nothing here starts its run_plan
reset(); DG = load("scripts/helpers/deceased_guard.py", "deceased_guard"); sys.modules["deceased_guard"] = DG     # from here on the client's hook feeds the REAL guard
DG._CARRIED[0] = True      # this guard's file stands in the CHECKOUT, so the other cache files of its layout are the checkout's own (the repository's register among them): nothing of the checkout is carried into this self-test's throwaway cache. The carry itself is shown with guards whose file stands in a sandbox folder (_guard_at, at the end)
check("guard: the guard is the real file, it uses the one cache path it is configured with, and its own request and key file are gone",
      lambda: DG.CACHE == DCACHE and DG.MAX_AGE_DAYS == 30 and not hasattr(DG, "KEYF") and not hasattr(DG, "STEDI") and "requests" not in _read("scripts/helpers/deceased_guard.py"))
for t in GUARD_TESTS + FREE_TESTS + LAST: _run(t)
check("fixtures: the well-shaped 'wrong' numbers belong to no invented person of this run (so a chart holding one really has a wrong number)",
      lambda: 0 < len(PEOPLE) < 895 and not any(q["number"] in WRONG for q in PEOPLE.values()), len(PEOPLE))
# ---- the guard's cache when nobody names one (11/25/2026, the integration) ------------------------------------------------------------------
# Until then the guard looked in ONE place - <its folder>/../practices/ehpa/registers/ - which is right for the clone's core/ copy only. In
# the flat workspace of a run (the helpers side by side, the registers folder beside them) no step fills that path: the guard started EMPTY,
# a death the practice already held was unknown to it, and a look-up that failed let the charge through (the runs' own lessons of that day).
def _cache_of(guard_file, env=None):
    """the cache path the guard chooses when its file stands at guard_file (the file need not be there) and DECEASED_CACHE is env (None = not set)"""
    old = os.environ.pop("DECEASED_CACHE", None)
    try:
        if env is not None: os.environ["DECEASED_CACHE"] = env
        m = types.ModuleType("deceased_guard_probe"); m.__file__ = guard_file; m.UNDER_TEST = True
        exec(compile(_read("scripts/helpers/deceased_guard.py"), guard_file, "exec"), m.__dict__)
        return m.CACHE
    finally:
        os.environ.pop("DECEASED_CACHE", None)
        if old is not None: os.environ["DECEASED_CACHE"] = old
def _tree(name, files=(), dirs=()):
    root = os.path.join(TMP, "cachewhere", name)
    for d in dirs: os.makedirs(os.path.join(root, d), exist_ok=True)
    for f in files:
        os.makedirs(os.path.dirname(os.path.join(root, f)), exist_ok=True); open(os.path.join(root, f), "w").write("{}")
    return root
_REG = os.path.join("practices", "ehpa", "registers", "deceased_cache.json")
_wsA = _tree("flat", ["home/ws/registers/deceased_cache.json"]); _wsB = _tree("flat_prepared", ["home/ws/registers/deceased_cache.json", "home/" + _REG])
_clC = _tree("clone", [_REG], ["core", "scripts/helpers"]); _wsE = _tree("flat_new", [], ["home/ws/registers"]); _wsF = _tree("bare", [], ["home/ws"])
check("guard: with no cache named, the guard of a run's FLAT workspace (the helpers side by side, registers/ beside them) reads the workspace's own registers/deceased_cache.json - it no longer starts empty beside the cache the practice holds",
      lambda: _cache_of(os.path.join(_wsA, "home", "ws", "deceased_guard.py")) == os.path.join(_wsA, "home", "ws", "registers", "deceased_cache.json"), lambda: _cache_of(os.path.join(_wsA, "home", "ws", "deceased_guard.py")))
check("guard: ... the workspace's own register wins also where a run has put a copy at the path the guard used to read (<folder>/../practices/ehpa/registers/ - what the guard learned there missed the pack); in the clone the core/ copy reads the repository's register as before, and the scripts/helpers/ copy reads the same file",
      lambda: _cache_of(os.path.join(_wsB, "home", "ws", "deceased_guard.py")) == os.path.join(_wsB, "home", "ws", "registers", "deceased_cache.json") and _cache_of(os.path.join(_clC, "core", "deceased_guard.py")) == os.path.join(_clC, _REG)
      and _cache_of(os.path.join(_clC, "scripts", "helpers", "deceased_guard.py")) == os.path.join(_clC, _REG),
      lambda: (_cache_of(os.path.join(_wsB, "home", "ws", "deceased_guard.py")), _cache_of(os.path.join(_clC, "core", "deceased_guard.py")), _cache_of(os.path.join(_clC, "scripts", "helpers", "deceased_guard.py"))))
# ONE cache (the second verification): the feed helpers kept a file of their own, the check before approvals read the register, a run's hand copy lay at the
# old path - three files that never met. The guard carries every DAY the other files hold into the cache it uses, once, before its first answer.
def _guard_at(guard_file, env=None):
    """the real guard loaded as if its file stood at guard_file, with DECEASED_CACHE as env (None = not set) - a fresh module each time, like a new process"""
    old = os.environ.pop("DECEASED_CACHE", None)
    try:
        if env is not None: os.environ["DECEASED_CACHE"] = env
        m = types.ModuleType("deceased_guard_probe"); m.__file__ = guard_file; m.UNDER_TEST = True
        exec(compile(_read("scripts/helpers/deceased_guard.py"), guard_file, "exec"), m.__dict__)
        return m
    finally:
        os.environ.pop("DECEASED_CACHE", None)
        if old is not None: os.environ["DECEASED_CACHE"] = old
def _three_files(name):
    """a flat workspace that holds three cache files: the register (chart A's day; chart D scrubbed), the feed helpers' file of before (chart B's day in eight digits; C with none; D's real day), a hand copy at the old path (chart E's day; A's day LATER than the register's; a line that is no entry)"""
    root = os.path.join(TMP, "onecache", name); ws = os.path.join(root, "home", "ws"); old_path = os.path.join(root, "home", "practices", "ehpa", "registers")
    os.makedirs(os.path.join(ws, "registers")); os.makedirs(old_path)
    json.dump({"7001": {"dod": iso(ago(30)), "checked": iso(ago(3)), "src": "stedi-medicare-271"}, "7004": {"dod": "[DOB]", "checked": iso(ago(3)), "src": "stedi-medicare-271"}}, open(os.path.join(ws, "registers", "deceased_cache.json"), "w"))
    json.dump({"7002": {"dod": ymd(ago(20)), "src": "amd-medicare-271"}, "7003": {"dod": None, "checked": iso(ago(1)), "src": "amd: no death on record"}, "7004": {"dod": iso(ago(12)), "checked": iso(ago(2)), "src": "amd-medicare-271"}}, open(os.path.join(ws, "deceased_cache_local.json"), "w"))
    json.dump({"7005": {"dod": iso(ago(8)), "checked": iso(ago(1)), "src": "x"}, "7001": {"dod": iso(ago(25)), "checked": iso(ago(1)), "src": "x"}, "not a chart": "text"}, open(os.path.join(old_path, "deceased_cache.json"), "w"))
    return ws
_ws1 = _three_files("default"); _g1 = _guard_at(os.path.join(_ws1, "deceased_guard.py")); _dos = iso(ago(2))
_a1 = {k: _g1.check(k, _dos, None, "99349", allow_lookup=False) for k in ("7001", "7002", "7003", "7004", "7005")}
_c1 = json.load(open(os.path.join(_ws1, "registers", "deceased_cache.json")))
check("guard (one cache): in a workspace that holds three cache files the guard uses the register and knows EVERY day any of them holds - a claim after the day is blocked for the charts only the feed's own file or the hand copy knew, with nobody asked; a chart with no death on record anywhere is not blocked",
      lambda: _g1.CACHE == os.path.join(_ws1, "registers", "deceased_cache.json") and all(_a1[k][0] is True for k in ("7001", "7002", "7004", "7005")) and _a1["7003"] == (False, ""), _a1)
check("guard (one cache): ... the days are carried INTO the cache in use (the file the pack uploads), each as YYYY-MM-DD: a day that can be read replaces the scrubbed one, of two days the EARLIER stays, an entry without a day and a line that is no entry are not carried",
      lambda: _c1["7002"]["dod"] == iso(ago(20)) and _c1["7004"]["dod"] == iso(ago(12)) and _c1["7005"]["dod"] == iso(ago(8)) and _c1["7001"]["dod"] == iso(ago(30)) and "7003" not in _c1 and "not a chart" not in _c1, _c1)
_ws2 = _three_files("named"); _g2 = _guard_at(os.path.join(_ws2, "deceased_guard.py"), env=os.path.join(_ws2, "deceased_cache_local.json"))
_a2 = {k: _g2.check(k, _dos, None, "99349", allow_lookup=False) for k in ("7001", "7002", "7005")}
check("guard (one cache): ... and a helper of before that still names the feed's own file (DECEASED_CACHE) gets the same days carried into THAT file: whichever file a helper names, no day the workspace holds is unknown to it",
      lambda: _g2.CACHE == os.path.join(_ws2, "deceased_cache_local.json") and all(v[0] is True for v in _a2.values()) and json.load(open(_g2.CACHE))["7001"]["dod"] == iso(ago(30)), _a2)
_ws3 = _three_files("unreadable"); open(os.path.join(_ws3, "registers", "deceased_cache.json"), "w").write("{ this register cannot be read"); open(os.path.join(_ws3, "deceased_cache_local.json"), "w").write("[1, 2")
_g3 = _guard_at(os.path.join(_ws3, "deceased_guard.py")); _a3 = _g3.check("7005", _dos, None, "99349", allow_lookup=False)
check("guard (one cache): ... a cache in use that cannot be read is never written over, a file that cannot be read is passed over, and nothing raises - and (the independent check of that round, finding 8) the day the hand copy holds is NOT lost for that: it is kept in memory for the rest of the process and blocks the claim (it answered 'not blocked')",
      lambda: _a3[0] is True and iso(ago(8)) in _a3[1] and open(os.path.join(_ws3, "registers", "deceased_cache.json")).read() == "{ this register cannot be read" and os.listdir(os.path.join(_ws3, "registers")) == ["deceased_cache.json"], _a3)
# The independent check of the second round, new finding 8 (D8): what the guard did NOT take from the other cache files. (a) A placeholder - a death on record
# whose day cannot be read - that stood ONLY in another file was not carried: the chart read 'clear', nobody was asked, while the feed's import held the same
# chart. (b) With a cache in use that cannot be read the carry gave up: a day another file held was unknown, the charge clear. And three rules of the carry that
# no check held (the checker's changes g06, g16, g21 passed every test): of two days the EARLIER wins also when it is the other file's; the entry's own fields
# stay when a day is carried into it; an entry under a key that is no chart number is not carried.
def _cache_files(name, register, local=None, old=None):
    """a flat workspace: its register (a table, or a text written as it is), the feed helpers' file of before, a hand copy at the old path"""
    root = os.path.join(TMP, "onecache", name); ws = os.path.join(root, "home", "ws"); os.makedirs(os.path.join(ws, "registers"))
    for path, what in ((os.path.join(ws, "registers", "deceased_cache.json"), register), (os.path.join(ws, "deceased_cache_local.json"), local), (os.path.join(root, "home", _REG), old)):
        if what is None: continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh: fh.write(what if isinstance(what, str) else json.dumps(what))
    return ws
_own63 = {"dod": "[DOB]", "checked": iso(ago(7)), "src": "the register's own"}
_ws4 = _cache_files("placeholder_elsewhere",
                    {"7061": {"dod": None, "checked": iso(ago(1)), "src": "stedi: no death on record", "name": "kept"}, "7062": {"dod": iso(ago(9)), "checked": iso(ago(1)), "src": "x"}, "7063": dict(_own63),
                     "7064": {"dod": iso(ago(10)), "checked": iso(ago(1)), "src": "stedi-medicare-271", "name": "kept", "at": "a field of its own"}, "7099": {"dod": None, "checked": iso(ago(2)), "src": "stedi: no death on record"}},
                    old={"7060": {"dod": "[DOB]", "checked": iso(ago(20)), "src": "stedi-medicare-271"}, "7061": {"dod": "[DOB]"}, "7062": {"dod": "[DOB]"}, "7063": {"dod": "[DOB]", "checked": iso(ago(1)), "src": "the other file's"},
                         "7064": {"dod": iso(ago(40)), "checked": iso(ago(30)), "src": "y"}, "somebody": {"dod": "[DOB]"}, "nobody": {"dod": iso(ago(5))}})
_g4 = _guard_at(os.path.join(_ws4, "deceased_guard.py")); _dos4 = iso(ago(3))
_a4 = {k: (_try(lambda k=k: _g4.check(k, _dos4, None, "99349", allow_lookup=False)), _raises(lambda k=k: _g4.check(k, _dos4, None, "99349", allow_lookup=False), _g4.DayLost)) for k in ("7060", "7061", "7062", "7063", "7064", "7099")}
_c4 = json.load(open(os.path.join(_ws4, "registers", "deceased_cache.json")))
check("guard (carry, finding 8a): a PLACEHOLDER that stands only in another cache file is carried as a death on record when the cache in use holds no dod for the chart - no entry at all, or 'no death on record': the chart is NOT cleared (DayLost) where it read 'clear' with nobody asked; the cache in use keeps its own day and its own placeholder as they were",
      lambda: _a4["7060"][1] and _a4["7061"][1] and _a4["7063"][1] and _a4["7062"][0][0] is True and _a4["7099"][0] == (False, "") and _c4["7060"]["dod"] == "[DOB]" and _c4["7061"]["dod"] == "[DOB]"
      and _c4["7062"]["dod"] == iso(ago(9)) and _c4["7063"] == _own63 and _g4.cache_state()["lost"] == 3, (_a4, _c4))
check("guard (carry): ... the entry's own fields stay when something is carried into it (its name), of two days the EARLIER wins also when it is the OTHER file's (the cache in use held the later one), and an entry under a key that is no chart number is not carried - day or placeholder",
      lambda: _c4["7061"].get("name") == "kept" and _c4["7064"]["dod"] == iso(ago(40)) and _c4["7064"].get("name") == "kept" and _c4["7064"].get("at") == "a field of its own" and _a4["7064"][0][0] is True
      and "somebody" not in _c4 and "nobody" not in _c4, _c4)
reset(); _p4 = newp(death=ago(20)); chart("7060", _p4, plans=[("car6404", "", "M" + "8" * 9)]); _g4._LOST_ASKED.clear(); _r4 = _try(lambda: _g4.check("7060", _dos4, None, "99349")); _k4 = kinds()
check("guard (carry): ... and such a chart is ASKED about for a charge whose payer the caller does not know (or billed to straight Medicare - the sixth round), like any chart whose day is lost - here the look-up names the day and the claim after it is blocked",
      lambda: _r4 != "raised" and _r4[0] is True and iso(ago(20)) in _r4[1] and _k4 == ["MBILUNOSSN"], (_r4, _k4))
_ws5 = _cache_files("unreadable_in_use", '{"7070": {"dod": "20', local={"7070": {"dod": iso(ago(40)), "checked": iso(ago(2)), "src": "amd-271"}, "7071": {"dod": "[DOB]", "checked": iso(ago(2)), "src": "x"}, "7072": {"dod": None, "checked": iso(ago(2))}})
_g5 = _guard_at(os.path.join(_ws5, "deceased_guard.py"))
_a5 = (_try(lambda: _g5.check("7070", iso(ago(5)), None, "99349", allow_lookup=False)), _raises(lambda: _g5.check("7071", iso(ago(5)), None, "99349", allow_lookup=False), _g5.DayLost), _try(lambda: _g5.check("7072", iso(ago(5)), None, "99349", allow_lookup=False)))
check("guard (carry, finding 8b): the cache in use is cut off and cannot be read - what the other files hold is kept in MEMORY for the rest of the process: the day blocks the claim, the placeholder is not cleared (both read 'clear'), a chart with no death anywhere is clear; nothing is written over the unreadable file, and no other file appears beside it",
      lambda: _a5[0] != "raised" and _a5[0][0] is True and _a5[1] is True and _a5[2] == (False, "") and open(os.path.join(_ws5, "registers", "deceased_cache.json")).read() == '{"7070": {"dod": "20'
      and os.listdir(os.path.join(_ws5, "registers")) == ["deceased_cache.json"] and sorted(_g5._UNSAVED) == ["7070", "7071"], (_a5, sorted(_g5._UNSAVED)))
check("guard: ... with no cache file anywhere yet, a workspace that has a registers folder gets its cache THERE (the folder a run packs), any other place the path of before; and a cache the environment names wins everywhere - an empty name is no name",
      lambda: _cache_of(os.path.join(_wsE, "home", "ws", "deceased_guard.py")) == os.path.join(_wsE, "home", "ws", "registers", "deceased_cache.json")
      and _cache_of(os.path.join(_wsF, "home", "ws", "deceased_guard.py")) == os.path.join(_wsF, "home", _REG)
      and all(_cache_of(os.path.join(r_, "home", "ws", "deceased_guard.py"), "/x/named.json") == "/x/named.json" for r_ in (_wsA, _wsB, _wsE, _wsF)) and _cache_of(os.path.join(_clC, "core", "deceased_guard.py"), "/x/named.json") == "/x/named.json"
      and _cache_of(os.path.join(_wsA, "home", "ws", "deceased_guard.py"), "") == os.path.join(_wsA, "home", "ws", "registers", "deceased_cache.json"),
      lambda: (_cache_of(os.path.join(_wsE, "home", "ws", "deceased_guard.py")), _cache_of(os.path.join(_wsF, "home", "ws", "deceased_guard.py")), _cache_of(os.path.join(_wsA, "home", "ws", "deceased_guard.py"), "")))
# The independent check of the second round, new finding 11 (D11): cache_state() looked at the file BEFORE the guard had carried the other cache files in, so a
# caller's line about the cache could be untrue - 'the file is missing' two lines before a BLOCKED answer from that very file, '2 charts whose day cannot be read'
# although both days had been carried in. It carries first now.
_ws6 = _cache_files("state_carries_first", None, local={"7080": {"dod": iso(ago(40)), "checked": iso(ago(2)), "src": "amd-271"}})
_g6 = _guard_at(os.path.join(_ws6, "deceased_guard.py")); _s6 = _g6.cache_state()
_ws7 = _cache_files("state_carries_first_2", {"7081": {"dod": "[DOB]", "checked": iso(ago(50))}, "7082": {"dod": "[DOB]", "checked": iso(ago(50))}, "7083": {"dod": "[DOB]", "checked": iso(ago(50))}},
                    local={"7081": {"dod": iso(ago(40)), "checked": iso(ago(2)), "src": "amd-271"}, "7082": {"dod": ymd(ago(41))}})
_g7 = _guard_at(os.path.join(_ws7, "deceased_guard.py")); _s7 = _g7.cache_state()
_ws8 = _cache_files("state_nothing_to_carry", None); _g8 = _guard_at(os.path.join(_ws8, "deceased_guard.py")); _s8 = _g8.cache_state()
check("guard (cache state, finding 11): cache_state() carries the other cache files in FIRST - no register file but a day in the feed's old file: the file is there afterwards and holds that day (it said 'no file'); three placeholders of which the old file holds two days: two days and ONE lost (it said 3 lost); and with nothing to carry a missing file is still a missing file",
      lambda: _s6 == {"file": True, "readable": True, "charts": 1, "days": 1, "lost": 0} and _s7 == {"file": True, "readable": True, "charts": 3, "days": 2, "lost": 1}
      and _s8 == {"file": False, "readable": False, "charts": 0, "days": 0, "lost": 0} and not os.path.exists(os.path.join(_ws8, "registers", "deceased_cache.json")), (_s6, _s7, _s8))
# The independent check of the second round, new finding 9 (D9 - a regression of that round): the guard took <its folder>/registers/deceased_cache.json as soon as
# the FOLDER was there. In the repository's own layout any helper started from scripts/helpers leaves such a folder (death_check_review.py writes its register under
# the folder it is started in) - from then on the guard there read a file that is not there, the repository's register was not even among the files it carries
# from, and a visit after a day that register holds answered 'not blocked'. The layout is now decided by where the file stands.
_clD = _tree("clone_stray", [_REG], ["core", "core/registers", "scripts/helpers", "scripts/helpers/registers"])
with open(os.path.join(_clD, _REG), "w") as _fh: json.dump({"7950": {"dod": iso(ago(40)), "checked": iso(ago(3))}, "7951": {"dod": "[DOB]", "checked": iso(ago(3))}}, _fh)
check("guard (layout): in the REPOSITORY layout a stray empty registers folder beside the helpers changes nothing - the guard in scripts/helpers and the guard in core both read the repository's register (the one in scripts/helpers read a file that was not there)",
      lambda: _cache_of(os.path.join(_clD, "scripts", "helpers", "deceased_guard.py")) == os.path.join(_clD, _REG) and _cache_of(os.path.join(_clD, "core", "deceased_guard.py")) == os.path.join(_clD, _REG),
      lambda: (_cache_of(os.path.join(_clD, "scripts", "helpers", "deceased_guard.py")), _cache_of(os.path.join(_clD, "core", "deceased_guard.py"))))
_gD = _guard_at(os.path.join(_clD, "scripts", "helpers", "deceased_guard.py"))
_aD = (_try(lambda: _gD.check("7950", iso(ago(5)), None, "99349", allow_lookup=False)), _raises(lambda: _gD.check("7951", iso(ago(5)), None, "99349", allow_lookup=False), _gD.DayLost))
check("guard (layout): ... so a visit after a day that register holds is blocked there, and a chart whose day is the placeholder is not cleared (both answered 'not blocked'); nothing is written into the stray folder",
      lambda: _aD[0] != "raised" and _aD[0][0] is True and _aD[1] is True and os.listdir(os.path.join(_clD, "scripts", "helpers", "registers")) == [], _aD)
_clE = _tree("clone_stray_file", [_REG, "scripts/helpers/registers/deceased_cache.json", "scripts/helpers/deceased_cache_local.json"], ["core"])
with open(os.path.join(_clE, "scripts", "helpers", "registers", "deceased_cache.json"), "w") as _fh: json.dump({"7952": {"dod": iso(ago(30)), "checked": iso(ago(1)), "src": "x"}}, _fh)
_gE = _guard_at(os.path.join(_clE, "scripts", "helpers", "deceased_guard.py")); _oE = sorted(_gE._others()); _aE = _try(lambda: _gE.check("7952", iso(ago(5)), None, "99349", allow_lookup=False))
check("guard (layout): ... and a cache FILE such a stray folder holds (the guard of that round wrote its answers there) is one of the other files: _others() lists every cache file of the layout except the one in use, and its day is carried into the repository's register",
      lambda: _gE.CACHE == os.path.join(_clE, _REG) and _oE == sorted([os.path.join(_clE, "scripts", "helpers", "registers", "deceased_cache.json"), os.path.join(_clE, "scripts", "helpers", "deceased_cache_local.json")])
      and _aE != "raised" and _aE[0] is True and json.load(open(os.path.join(_clE, _REG)))["7952"]["dod"] == iso(ago(30)), lambda: (_gE.CACHE, _oE, _aE))
_clF = _tree("clone_named", [_REG], ["core", "scripts/helpers"])
with open(os.path.join(_clF, _REG), "w") as _fh: json.dump({"7953": {"dod": iso(ago(30)), "checked": iso(ago(1)), "src": "x"}}, _fh)
_nF = os.path.join(_clF, "scripts", "helpers", "deceased_cache_local.json"); _nC = os.path.join(_clF, "core", "a_cache_of_its_own.json")
_gF = _guard_at(os.path.join(_clF, "scripts", "helpers", "deceased_guard.py"), env=_nF); _oF = _gF._others(); _aF = _try(lambda: _gF.check("7953", iso(ago(5)), None, "99349", allow_lookup=False))
_cF = _try(lambda: json.load(open(_nF))["7953"]["dod"])
_gC = _guard_at(os.path.join(_clF, "core", "deceased_guard.py"), env=_nC); _oC = _gC._others(); _aC = _try(lambda: _gC.check("7953", iso(ago(5)), None, "99349", allow_lookup=False))
check("guard (layout): ... and where a helper NAMES another cache file (DECEASED_CACHE), the repository's register is one of the other files from both folders - two up from scripts/helpers, one up from core: its day is carried into the named file and blocks the visit after it, with nobody asked",
      lambda: _gF.CACHE == _nF and _oF == [os.path.join(_clF, _REG)] and _aF != "raised" and _aF[0] is True and _cF == iso(ago(30))
      and _gC.CACHE == _nC and _oC == [os.path.join(_clF, _REG)] and _aC != "raised" and _aC[0] is True, lambda: (_oF, _aF, _cF, _oC, _aC))
_gB = _guard_at(os.path.join(_wsB, "home", "ws", "deceased_guard.py"))
_laF = _tree("helpers_not_scripts", ["practices/ehpa/registers/deceased_cache.json"], ["tools/helpers/registers"]); _laG = _tree("core_no_register", [], ["home/core/registers"])
_laH = _tree("two_up", ["practices/ehpa/registers/deceased_cache.json"], ["a/b"]); _laI = _tree("scripts_helpers_no_register", [], ["scripts/helpers/registers"])
check("guard (layout): the FLAT workspace is as it was - its own registers folder wins over a copy at the old path (file there or not), and that copy is one of the other files; a folder that only LOOKS like the repository's (helpers not under scripts; core or scripts/helpers with no repository register) is a flat workspace when it has a registers folder; with no registers folder the first repository path that exists counts",
      lambda: _gB.CACHE == os.path.join(_wsB, "home", "ws", "registers", "deceased_cache.json") and _gB._others() == [os.path.join(_wsB, "home", _REG)]
      and _cache_of(os.path.join(_laF, "tools", "helpers", "deceased_guard.py")) == os.path.join(_laF, "tools", "helpers", "registers", "deceased_cache.json")
      and _cache_of(os.path.join(_laG, "home", "core", "deceased_guard.py")) == os.path.join(_laG, "home", "core", "registers", "deceased_cache.json")
      and _cache_of(os.path.join(_laI, "scripts", "helpers", "deceased_guard.py")) == os.path.join(_laI, "scripts", "helpers", "registers", "deceased_cache.json")
      and _cache_of(os.path.join(_laH, "a", "b", "deceased_guard.py")) == os.path.join(_laH, "practices", "ehpa", "registers", "deceased_cache.json"),
      lambda: (_gB.CACHE, _gB._others(), _cache_of(os.path.join(_laF, "tools", "helpers", "deceased_guard.py")), _cache_of(os.path.join(_laG, "home", "core", "deceased_guard.py")), _cache_of(os.path.join(_laI, "scripts", "helpers", "deceased_guard.py")), _cache_of(os.path.join(_laH, "a", "b", "deceased_guard.py"))))
# ---- the third round (11/25/2026, the second independent check): the carry, shown with guards whose file stands in a sandbox folder -------------------------------
# R2a (its new finding 2, the checker's own case): ANY text in the dod field of ANOTHER cache file held a living patient's chart - 'unknown', the word None, one
# blank, the text 0 were carried in as 'a death on record whose day cannot be read', over yesterday's 'no death on record', for good. Only the privacy gate's
# placeholder, the guard's own 'day not known' and a damaged date are that; every other value is no dod and is not carried.
_R2A_NONE = ["unknown", "None", "null", " ", "", "0", 0, False, True, [], ["x"], None]; _R2A_DEATH = [PLACEHOLDER, "day not known", "%d-02-30" % TODAY.year, str(TODAY.year)]
_ws9 = _cache_files("r2a_other_file", {str(7200 + i): {"dod": None, "checked": iso(ago(1)), "src": "stedi: no death on record"} for i in range(0, len(_R2A_NONE + _R2A_DEATH), 2)},      # every second chart is known to the cache in use: 'no death on record', yesterday
                    local={str(7200 + i): {"dod": v, "checked": iso(ago(20)), "src": "x"} for i, v in enumerate(_R2A_NONE + _R2A_DEATH)})
_g9 = _guard_at(os.path.join(_ws9, "deceased_guard.py")); _dos9 = iso(ago(3))
_a9 = [(_try(lambda i=i: _g9.check(str(7200 + i), _dos9, None, "99349", allow_lookup=False)), _raises(lambda i=i: _g9.check(str(7200 + i), _dos9, None, "99349", allow_lookup=False), _g9.DayLost)) for i in range(len(_R2A_NONE + _R2A_DEATH))]
_c9 = json.load(open(os.path.join(_ws9, "registers", "deceased_cache.json")))
check("guard (carry, R2a): a value in ANOTHER cache file's dod field that is no day and no death on record - 'unknown', the words None / null, a blank, '0', 0, false, true, a list - holds NO chart: the claim is 'not blocked' from the cache as before the carry (each of them raised DayLost, for good), and nothing of it is carried into the cache in use",
      lambda: all(a == ((False, ""), False) for a in _a9[:len(_R2A_NONE)]) and all(_c9.get(str(7200 + i), {}).get("dod") is None for i in range(len(_R2A_NONE))) and len(_c9) == (len(_R2A_NONE + _R2A_DEATH) + 1) // 2 + len(_R2A_DEATH) // 2,
      (_a9[:len(_R2A_NONE)], sorted(_c9)))
check("guard (carry, R2a): ... while the placeholder, the guard's own 'day not known' and a damaged date in another file ARE carried as a death on record - over 'no death on record' and where the cache in use has no entry: the chart is not cleared (DayLost)",
      lambda: all(a[1] is True for a in _a9[len(_R2A_NONE):]) and [_c9[str(7200 + len(_R2A_NONE) + i)]["dod"] for i in range(len(_R2A_DEATH))] == _R2A_DEATH and _g9.cache_state()["lost"] == len(_R2A_DEATH), (_a9[len(_R2A_NONE):], _c9))
_ws10 = _cache_files("r2a_cache_in_use", {"7230": {"dod": "unknown", "checked": iso(TODAY), "src": "x", "name": "kept"}, "7231": {"dod": " ", "checked": iso(TODAY)}}, local={"7230": {"dod": PLACEHOLDER, "checked": iso(ago(20)), "src": "the other file's"}, "7231": {"dod": iso(ago(40)), "checked": iso(ago(20)), "src": "y"}})
_g10 = _guard_at(os.path.join(_ws10, "deceased_guard.py")); _a10 = (_raises(lambda: _g10.check("7230", iso(ago(3)), None, "99349", allow_lookup=False), _g10.DayLost), _try(lambda: _g10.check("7231", iso(ago(3)), None, "99349", allow_lookup=False)))
_c10 = json.load(open(os.path.join(_ws10, "registers", "deceased_cache.json")))
check("guard (carry, R2a): ... and an odd value in the cache IN USE is 'no dod' for the carry too: a placeholder and a day another file holds for that chart come in over it (the entry's other fields stay)",
      lambda: _a10[0] is True and _a10[1] != "raised" and _a10[1][0] is True and _c10["7230"]["dod"] == PLACEHOLDER and _c10["7230"].get("name") == "kept" and _c10["7231"]["dod"] == iso(ago(40)), (_a10, _c10))
# R5 (its new finding 6): the cache in use can be read but not WRITTEN (its folder refuses a new file). The carry gave up without a word - the day another file held
# was neither written nor kept, and the visit after it answered 'not blocked'. What the carry cannot write is kept in memory now, as for a cache that cannot be read.
_ws11 = _cache_files("r5_cannot_write", {"7250": {"dod": None, "checked": iso(ago(1)), "src": "stedi: no death on record"}}, local={"7250": {"dod": iso(ago(40)), "checked": iso(ago(2)), "src": "feed"}, "7251": {"dod": PLACEHOLDER, "checked": iso(ago(2))}})
_g11 = _guard_at(os.path.join(_ws11, "deceased_guard.py")); _t11 = open(os.path.join(_ws11, "registers", "deceased_cache.json")).read()
with no_write(_g11):
    _a11 = (_try(lambda: _g11.check("7250", iso(ago(5)), None, "99349", allow_lookup=False)), _raises(lambda: _g11.check("7251", iso(ago(5)), None, "99349", allow_lookup=False), _g11.DayLost),
            _try(lambda: _g11.check("7250", iso(ago(60)), None, "99349", allow_lookup=False)))
check("guard (carry, R5): the cache in use can be read but not WRITTEN - what the carry could not write is kept in memory for the rest of the process: the other file's day blocks the claim (it answered 'not blocked'), its placeholder is not cleared, a visit before the day passes; the file is as it was and nothing is left beside it",
      lambda: _a11[0] != "raised" and _a11[0][0] is True and iso(ago(40)) in _a11[0][1] and _a11[1] is True and _a11[2] == (False, "") and sorted(_g11._UNSAVED) == ["7250", "7251"]
      and open(os.path.join(_ws11, "registers", "deceased_cache.json")).read() == _t11 and os.listdir(os.path.join(_ws11, "registers")) == ["deceased_cache.json"], (_a11, sorted(_g11._UNSAVED)))
# D1 of the fifth round (11/26/2026): the carry knows a day and a death on record with no day - NOTHING of the owner's word. Rounds three and four had each given
# it a part (c): an entry that kept another file's older record out. An entry that still carries those rounds' fields is an entry like any other: what another
# cache file holds for the chart is carried into it by the two rules the carry has.
_D12 = ago(10); _of12 = old_word_rec(_D12, name="kept")
_k12 = ("the old day, checked long before", "a day with no check date", "a day whose check date is no date", "a day checked lately", "no day, checked long before", "no day, no check date", "the guard's own 'day not known'", "no death", "an odd value")
_o12 = [{"dod": iso(ago(40)), "checked": iso(ago(30)), "src": "x"}, {"dod": iso(ago(40))}, {"dod": iso(ago(40)), "checked": "not a day"}, {"dod": mdy(ago(5)), "checked": iso(ago(4)) + "T08:00:00", "src": "stedi-medicare-271"},
        {"dod": PLACEHOLDER, "checked": iso(ago(20)), "src": "x"}, {"dod": PLACEHOLDER}, {"dod": "day not known", "checked": iso(ago(3)), "src": "amd: deceased on the chart, no date"},
        {"dod": None, "checked": iso(TODAY), "src": "stedi: no death on record"}, {"dod": "unknown", "checked": iso(TODAY)}]
_ws12 = _cache_files("r5_carry_old_fields", {str(7300 + i): dict(_of12) for i in range(len(_o12))}, local={str(7300 + i): e for i, e in enumerate(_o12)}); _g12 = _guard_at(os.path.join(_ws12, "deceased_guard.py"))
_a12 = [says(lambda i=i: _g12.check(str(7300 + i), iso(ago(1)), None, "99349", allow_lookup=False)) for i in range(len(_o12))]
_c12 = json.load(open(os.path.join(_ws12, "registers", "deceased_cache.json")))
check("guard (carry, D1 of the fifth round): the cache in use holds, for a chart, an entry that still carries the fields rounds three and four wrote for the owner's word. A day ANOTHER cache file holds is carried into it whatever that file's check date - checked long before, with no check date, with one that is no date, or lately - and blocks the claim after it (the fourth round kept every one of the first three OUT, and the claim was held or passed by other rules); the entry's name stays",
      lambda: all(_a12[i] not in ("DayLost", "raised") and _a12[i][0] is True and _c12[str(7300 + i)].get("name") == "kept" for i in (0, 1, 2, 3)) and [_c12[str(7300 + i)]["dod"] for i in (0, 1, 2, 3)] == [iso(ago(40))] * 3 + [iso(ago(5))]
      and _c12["7300"]["checked"] == iso(ago(30)) and _c12["7300"]["src"] == "x" and _c12["7303"]["src"] == "stedi-medicare-271", [(_k12[i], _a12[i], _c12[str(7300 + i)]) for i in (0, 1, 2, 3)])
check("guard (carry, D1): ... a death with no day another file holds is carried too - the placeholder with a check date or with none, the guard's own 'day not known' - and the chart is not cleared (DayLost); another file's 'no death' and an odd value change nothing: the entry stays as it was and the claim is answered 'not blocked' from the cache, as for any chart with no death on record",
      lambda: [_a12[i] for i in (4, 5, 6)] == ["DayLost"] * 3 and [_c12[str(7300 + i)]["dod"] for i in (4, 5, 6)] == [PLACEHOLDER, PLACEHOLDER, "day not known"] and _a12[7] == _a12[8] == (False, "") and _c12["7307"] == _c12["7308"] == _of12,
      [(_k12[i], _a12[i], _c12[str(7300 + i)]) for i in (4, 5, 6, 7, 8)])
# ONE reading for the guard and the import. The import reads the cache files itself (it asks the guard only about care-management charts and charts whose day is
# lost) - its death_read and the guard after its carry must come to the SAME answer for every set of entries the files can hold for one chart: blocked by which
# day, held for a lost day, or clear. An entry with the fields of the rounds before is among the kinds: it must read as 'no death' everywhere.
_F14 = lift("scripts/helpers/claimocity_import.py", "death_day", "death_unread", "death_read", "DEATH_NO_DAY", "DEATH_WORDS", "DEATH_NOTHING")
_e14 = {"no entry": None, "no death": {"dod": None, "checked": iso(ago(1)), "src": "stedi: no death on record"}, "old day": {"dod": iso(ago(40)), "checked": iso(ago(30))}, "a day in another shape": {"dod": mdy(ago(12)), "checked": iso(_D12)},
        "a later day": {"dod": iso(ago(5)), "checked": iso(ago(4))}, "no day, the placeholder": {"dod": PLACEHOLDER, "checked": iso(ago(20))}, "no day, the guard's own": {"dod": "day not known", "checked": iso(ago(3))},
        "old fields": old_word_rec(_D12), "odd": {"dod": "unknown", "checked": iso(TODAY)}, "nothing in brackets": {"dod": "[none]", "checked": iso(ago(2))}}
def _says14(g, chart):
    try: r = g.check(chart, iso(TODAY), None, "99349", allow_lookup=False)
    except g.DayLost: return "lost"
    return ("blocked " + re.search(r"after date of death (\S+)", r[1]).group(1)) if r[0] else "clear"
def _reads14(tables, chart):
    try: d = _F14["death_read"](json.loads(json.dumps(tables))); return "death_read gave %d values" % len(d) if len(d) != 2 else ("blocked " + d[0][chart]["dod"]) if chart in d[0] else "lost" if chart in d[1] else "clear"
    except Exception as e: return "death_read raised " + type(e).__name__
_p14 = [(x, y) for x in _e14 for y in _e14]; _n14 = {p: str(7400 + i) for i, p in enumerate(_p14)}
_t14 = ({_n14[p]: _e14[p[0]] for p in _p14 if _e14[p[0]] is not None}, {_n14[p]: _e14[p[1]] for p in _p14 if _e14[p[1]] is not None})
_ws14 = _cache_files("r5_one_reading", json.loads(json.dumps(_t14[0])), local=json.loads(json.dumps(_t14[1]))); _g14 = _guard_at(os.path.join(_ws14, "deceased_guard.py"))
_r14 = [(p, _try(lambda p=p: _says14(_g14, _n14[p])), _reads14(_t14, _n14[p])) for p in _p14]
check("ONE reading: for every pair of entries the cache in use and another cache file can hold for one chart - no entry, 'no death', an old day, a day in another shape, a later day, a death with no day (the placeholder, the guard's own word), an entry with the fields of the rounds before, an odd value, a bracketed text that means nothing: %d pairs - the guard (after its carry) and the import's death_read give the SAME answer: blocked by the same day, held for a lost day, or clear; death_read gives two values, no third" % len(_p14),
      lambda: len(_r14) == 100 and all(g == f for _p, g, f in _r14) and {f.split()[0] for _p, g, f in _r14} == {"blocked", "lost", "clear"}, [r for r in _r14 if r[1] != r[2]][:8])
check("ONE reading: ... and that answer is the two rules': of the days the two files hold the EARLIEST blocks, whichever file holds it; a death with no day holds the chart unless a file names a day; and an entry with the fields of the rounds before, an odd value and a bracketed 'nothing' are no death - whatever the other file holds decides",
      lambda: all(dict(((x, y), g) for (x, y), g, f in _r14)[k] == v for k, v in {("old day", "a later day"): "blocked " + iso(ago(40)), ("a later day", "old day"): "blocked " + iso(ago(40)), ("a later day", "a day in another shape"): "blocked " + iso(ago(12)),
              ("no day, the placeholder", "old day"): "blocked " + iso(ago(40)), ("old day", "no day, the guard's own"): "blocked " + iso(ago(40)), ("no entry", "no day, the placeholder"): "lost", ("no death", "no day, the guard's own"): "lost",
              ("no day, the placeholder", "no death"): "lost", ("old fields", "old day"): "blocked " + iso(ago(40)), ("old fields", "a later day"): "blocked " + iso(ago(5)), ("old fields", "no day, the placeholder"): "lost",
              ("old fields", "no death"): "clear", ("old fields", "no entry"): "clear", ("old fields", "old fields"): "clear", ("old day", "old fields"): "blocked " + iso(ago(40)), ("no day, the placeholder", "old fields"): "lost",
              ("no entry", "old fields"): "clear", ("odd", "no death"): "clear", ("nothing in brackets", "no death"): "clear", ("nothing in brackets", "old day"): "blocked " + iso(ago(40)), ("no entry", "nothing in brackets"): "clear",
              ("no entry", "no entry"): "clear"}.items()),
      [r for r in _r14 if r[0][0] in ("old fields", "nothing in brackets") or r[0][1] in ("old fields", "nothing in brackets")][:12])
# THREE files (finding 4 of the third check: the third round's carry read them in a fixed order and its answer could depend on it; the grid above holds pairs
# only). Every triple of seven kinds of entry - the cache in use, the feed helpers' file of before (read first), the copy at the old path (read second): the
# guard's answer must not depend on the order of the two other files, and it must be the import's.
_e15 = {k: _e14[k] for k in ("no entry", "no death", "old day", "a later day", "no day, the guard's own", "old fields")}; _e15["another later day"] = {"dod": iso(ago(8)), "checked": iso(ago(2))}
_p15 = [(x, y, z) for x in _e15 for y in _e15 for z in _e15]; _n15 = {p: str(10000 + i) for i, p in enumerate(_p15)}
_t15 = tuple({_n15[p]: _e15[p[j]] for p in _p15 if _e15[p[j]] is not None} for j in range(3))
_ws15 = _cache_files("r5_three_files", json.loads(json.dumps(_t15[0])), local=json.loads(json.dumps(_t15[1])), old=json.loads(json.dumps(_t15[2]))); _g15 = _guard_at(os.path.join(_ws15, "deceased_guard.py"))
_r15 = {p: (_try(lambda p=p: _says14(_g15, _n15[p])), _reads14(_t15, _n15[p])) for p in _p15}
check("THREE files (finding 4 of the third check): for every triple of entries the cache in use and TWO other cache files can hold for one chart (%d triples) the guard after its carry and the import's death_read give the same answer - and neither depends on the order of the three files: every way of laying the same three entries into the three files ends in the same answer" % len(_p15),
      lambda: len(_r15) == 343 and len(_g15._others()) == 2 and all(g == f for g, f in _r15.values()) and all(len({_r15[q][0] for q in ((x, y, z), (x, z, y), (y, x, z), (y, z, x), (z, x, y), (z, y, x))}) == 1 for x, y, z in _p15),
      [(p, r) for p, r in _r15.items() if r[0] != r[1]][:5] + [(p, _r15[p][0], _r15[(p[0], p[2], p[1])][0]) for p in _p15 if _r15[p][0] != _r15[(p[0], p[2], p[1])][0]][:5])
check("THREE files: ... and it is the two rules': the earliest of the days the three files hold blocks, wherever it stands; with no day in any of them a death with no day in one holds the chart; an entry with the fields of the rounds before keeps nothing out, wherever it stands - an old day in another file blocks behind it, in both orders",
      lambda: _r15[("a later day", "another later day", "old day")][0] == _r15[("old day", "a later day", "another later day")][0] == "blocked " + iso(ago(40)) and _r15[("no entry", "a later day", "another later day")][0] == "blocked " + iso(ago(8))
      and _r15[("no death", "no day, the guard's own", "no entry")][0] == _r15[("no entry", "no death", "no day, the guard's own")][0] == "lost" and _r15[("no day, the guard's own", "no death", "a later day")][0] == "blocked " + iso(ago(5))
      and _r15[("old fields", "a later day", "old day")][0] == _r15[("old fields", "old day", "a later day")][0] == "blocked " + iso(ago(40)) and _r15[("old fields", "old day", "no death")][0] == "blocked " + iso(ago(40))
      and _r15[("old fields", "no death", "no entry")][0] == "clear" and _r15[("no entry", "old fields", "old day")][0] == "blocked " + iso(ago(40)) and _r15[("no entry", "old fields", "no death")][0] == "clear",
      {p: _r15[p] for p in (("old fields", "a later day", "old day"), ("old fields", "old day", "a later day"), ("old day", "a later day", "old fields"), ("no entry", "old fields", "old day"))})
check("nothing was written in the checkout", lambda: _snapshot() == BEFORE, sorted(set(_snapshot().items()) ^ set(BEFORE.items()))[:5])
print("test_lookup_rules: %d checks, %d failed%s" % (COUNT[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:300]))
sys.exit(1 if FAILS else 0)
