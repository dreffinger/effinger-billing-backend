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
    if DG is not None: del DG.LOG[:]; DG._ASKED.clear(); getattr(DG, "_LOST_ASKED", set()).clear()      # ... and the charts asked about for a lost day (one question per chart per start)
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
    """guard#1 (the scrubbed copy), gate#1: a death on record whose day cannot be read here was asked about only for Medicare and care-management claims."""
    reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6404", "", "M" + "6" * 9), ("car6085", "", p["number"])])
    put_cache({pid: {"dod": "[DOB]", "checked": iso(TODAY), "src": "stedi-medicare-271"}}); free_death(pid, p, i=2)
    r = guard_check(pid, iso(ago(5)), carrier="car6404", proc="99349")
    check("guard (day lost): a death on record whose day cannot be read here (the scrubbed copy from the repository) is asked about again WHATEVER the payer and the code - AdvancedMD's free check first - and the day it brings blocks the claim",
          lambda: r[0] is True and iso(ago(20)) in r[1] and len(FREE_ASKED) == 1 and SENT == [] and (cache_json() or {}).get(pid, {}).get("dod") == iso(ago(20)), (r, FREE_ASKED, len(SENT)))
    reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6404", "", "M" + "6" * 9), ("car6085", "", p["number"])])
    put_cache({pid: {"dod": "[DOB]", "checked": iso(TODAY), "src": "stedi-medicare-271"}}); FREE[ins(pid, 2)] = ("timeout",); OVERRIDE[("CMS", p["number"])] = ("timeout",); OVERRIDE[("MBILUNOSSN", p["last"])] = ("timeout",)
    lost = _raises(lambda: guard_check(pid, iso(ago(5)), carrier="car6404", proc="99349"), DG.DayLost)
    check("guard (day lost): ... and when neither AdvancedMD nor the vendor answers, the claim is NOT cleared: the guard raises DayLost (amd.rebill_charge then answers 409 and sends nothing; the check before approvals says NOT CHECKED) - the entry and its mark stay as they were",
          lambda: lost and (cache_json() or {}).get(pid, {}).get("dod") == "[DOB]" and issubclass(DG.DayLost, RuntimeError), (lost, cache_json(), DG.LOG))
    check("guard (day lost): ... and NO 'date of death UNVERIFIED' line is logged for such a chart (the independent check of that round, finding 13): that line says 'not a block - the charge went on', and this claim did not - its caller says NOT CHECKED or holds the visit. The feed's count 'date of death UNVERIFIED xN' is of the guard's LOG lines, so it counts only charges that went on",
          lambda: lost and DG.LOG == [] and len(SENT) + len(FREE_ASKED) >= 2, (DG.LOG, len(SENT), len(FREE_ASKED)))
    q = newp(); other = chart(cid(), q, plans=[("car6085", "", q["number"])]); FREE[ins(other)] = ("timeout",); OVERRIDE[("CMS", q["number"])] = ("timeout",); OVERRIDE[("MBILUNOSSN", q["last"])] = ("timeout",)
    went_on = guard_check(other, iso(ago(5)))
    check("guard (day lost): ... while a chart with NO death on record whose look-up fails in the same start is logged as before - one line, and that charge is not blocked", lambda: went_on == (False, "") and DG.LOG == [UNVERIFIED % (other, iso(ago(5)))], (went_on, DG.LOG))
    cache_only = _raises(lambda: DG.check(pid, iso(ago(5)), "car6404", "99349", allow_lookup=False), DG.DayLost)
    check("guard (day lost): ... a question from the cache only (a dry run) is not cleared either; a chart with NO death on record, or with a readable day, is answered from the cache as before",
          lambda: cache_only and (put_cache({pid: {"dod": None, "checked": iso(TODAY), "src": "stedi: no death on record"}}) or DG.check(pid, iso(ago(5)), "car6404", "99349", allow_lookup=False) == (False, "")), cache_only)
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])]); put_cache({pid: {"dod": "[DOB]", "checked": iso(TODAY), "src": "x"}}); free_is(pid, p=p)
    nolog = len(DG.LOG); r = _raises(lambda: guard_check(pid, iso(ago(5))), DG.DayLost); asked = len(FREE_ASKED) + len(SENT)
    check("guard (day lost): ... when Medicare answers and shows NO death the claim is STILL not cleared - only a day is an answer for such a chart (a death the practice learned elsewhere is not in Medicare's answer for weeks; the placeholder stands where a real day stood): DayLost, the entry stays as it was, and no 'unverified' line is logged for an answer that came",
          lambda: r and (cache_json() or {}).get(pid, {}).get("dod") == "[DOB]" and len(DG.LOG) == nolog and asked >= 1, (r, cache_json(), DG.LOG[nolog:]))
    r2 = _raises(lambda: guard_check(pid, iso(ago(4))), DG.DayLost)
    check("guard (day lost): ... and a second question about that chart in the same start asks nobody again (one question per chart per start) - it is not cleared either",
          lambda: r2 and len(FREE_ASKED) + len(SENT) == asked, (r2, len(FREE_ASKED), len(SENT), asked))
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
    check("drive copy: pack keeps every day that can be read - also one a helper wrote in eight digits or as MM/DD/YYYY - as YYYY-MM-DD; a day that cannot be read is in neither list (it is unknown), a chart with no death is in the other",
          lambda: n == (3, 1) and packed["dated"][a][0] == iso(ago(9)) and packed["dated"][b][0] == iso(ago(8)) and packed["dated"][e][0] == iso(ago(7)) and c not in packed["dated"] and c not in packed["nodeath"] and list(packed["nodeath"]) == [d], (n, packed))
    target = os.path.join(TMP, "drive_target.json"); json.dump({a: {"dod": "[DOB]", "checked": iso(ago(5)), "src": None}, e: {"dod": None, "checked": None, "src": None}, d: {"dod": iso(ago(30)), "checked": iso(ago(3)), "src": "stedi-medicare-271"}}, open(target, "w"))
    m = DD.unpack(out, [target]); got = json.load(open(target))
    check("drive copy: unpack raises nothing on an entry whose source or 'checked' is null, a day that can be read replaces a scrubbed one and an entry with none, the free check's own label is kept, and a real day in the cache is never undone by a 'no death' note",
          lambda: got[a]["dod"] == iso(ago(9)) and got[e]["dod"] == iso(ago(7)) and got[b]["dod"] == iso(ago(8)) and got[d]["dod"] == iso(ago(30)) and isinstance(got[a].get("src"), str), (m, got))

def t_guard_flag_no_day():
    """The independent check of the second round, new finding 10 (D10): a 'deceased' attribute on the AdvancedMD chart that carries NO readable date made the
    claim's own date of service 'the day' - the claim was cleared, and that date was written into the cache as the day, for good. It is a death on record with
    no day: Medicare is asked for the day as for any chart; a day that comes is the day; when none comes the claim is not cleared (DayLost) and the entry says
    'a death on record, its day not known'. An attribute that carries a date works as before."""
    src = "amd: deceased on the chart, no date"; res = []
    for flag in ("Y", "true", "1", "-1", "02/31/" + str(TODAY.year)):      # a mark, a number that is no date, a date that is none
        reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased=flag); dos = iso(ago(5))
        lost = _raises(lambda: guard_check(pid, dos), DG.DayLost); res.append((flag, lost, kinds(), len(FREE_ASKED), dict((cache_json() or {}).get(pid) or {}), list(DG.LOG)))
    check("guard (flag, no day): the chart's own record says deceased and names no day (Y, true, a number, a date that is none) - the claim's own date of service is NOT taken for the day any more: Medicare is asked for the day as for any chart (AdvancedMD's free check, then the vendor's plain check), and when it names none the claim is NOT cleared - the guard raises DayLost",
          lambda: len(res) == 5 and all(r[1] is True and r[2] == ["CMS"] and r[3] == 1 for r in res), [(r[0], r[1], r[2], r[3]) for r in res])
    check("guard (flag, no day): ... the entry is written as a death ON RECORD whose day is not known - a dod that is no day (never the claim's date of service), checked today, the source says where it comes from - and no 'unverified' line is logged for an answer that came",
          lambda: all(r[4] == {"dod": DG.NO_DAY, "checked": iso(TODAY), "src": src} and r[5] == [] for r in res) and DG._day(DG.NO_DAY) is None and DG.NO_DAY != iso(ago(5)), [(r[0], r[4], r[5]) for r in res])
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="Y")
    first = _raises(lambda: guard_check(pid, iso(ago(5))), DG.DayLost); asked = len(SENT) + len(FREE_ASKED)
    second = _raises(lambda: guard_check(pid, iso(ago(4)), carrier="car6404", proc="99349"), DG.DayLost); cache_only = _raises(lambda: DG.check(pid, iso(ago(60)), "car6404", "99349", allow_lookup=False), DG.DayLost)
    DG.record(pid, json.loads(json.dumps(ALIVE_271)))
    check("guard (flag, no day): ... from then on the chart is one whose day is lost: a second question in the same start - another payer, another date - asks nobody again and is not cleared either, a question from the cache only neither, and another helper's 'no death on record' does not undo the entry",
          lambda: first and second and cache_only and len(SENT) + len(FREE_ASKED) == asked and cache_json()[pid]["dod"] == DG.NO_DAY and DG.cache_state()["lost"] == 1, (first, second, cache_only, asked, cache_json()))
    reset(); p = newp(death=ago(20)); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="Y")
    r1 = guard_check(pid, iso(ago(5))); k1 = kinds(); e1 = dict(cache_json()[pid]); r2 = guard_check(pid, iso(ago(25)))
    reset(); p2 = newp(death=ago(20)); pid2 = chart(cid(), p2, plans=[("car6085", "", p2["number"])], deceased="true"); free_death(pid2, p2); r3 = guard_check(pid2, iso(ago(5)))
    check("guard (flag, no day): when Medicare names a day, THAT is the day - a claim after it is blocked, one before it is not, and the entry holds the day with Medicare's source (the vendor's plain check here; AdvancedMD's free check when it answers, and then nothing is bought)",
          lambda: r1[0] is True and iso(ago(20)) in r1[1] and k1 == ["CMS"] and e1["dod"] == iso(ago(20)) and e1["src"] == "stedi-medicare-271" and r2 == (False, "")
          and r3[0] is True and SENT == [] and cache_json()[pid2]["src"] == "amd-medicare-271", (r1, k1, e1, r2, r3))
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="Y"); FREE[ins(pid)] = ("timeout",); OVERRIDE[("CMS", p["number"])] = ("timeout",); OVERRIDE[("MBILUNOSSN", p["last"])] = ("timeout",)
    nobody = _raises(lambda: guard_check(pid, iso(ago(5))), DG.DayLost)
    check("guard (flag, no day): when nobody answers at all the claim is not cleared either - DayLost, the same entry", lambda: nobody and cache_json()[pid] == {"dod": DG.NO_DAY, "checked": iso(TODAY), "src": src}, (nobody, cache_json()))
    reset(); p = newp(); pid = chart(cid(), p, plans=[("car6085", "", p["number"])], deceased="Y"); put_cache({pid: {"dod": "[DOB]", "checked": iso(ago(50)), "src": "x"}})
    both = _raises(lambda: guard_check(pid, iso(ago(5)), carrier="car6404", proc="99309"), DG.DayLost)
    check("guard (flag, no day): the checker's own case - the cache holds the placeholder AND the chart carries such a flag: not cleared (it answered 'not blocked' and wrote the claim's date as the day), and the entry stays as it was",
          lambda: both and cache_json()[pid] == {"dod": "[DOB]", "checked": iso(ago(50)), "src": "x"}, (both, cache_json()))
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
          lambda: n == (2, 0) and packed["dated"][a][0] == packed["dated"][b][0] == iso(D) and DG.check(a, iso(ago(5)), "car6404", "99349", allow_lookup=False)[0] is True and DG.check(b, iso(ago(60)), "car6404", "99349", allow_lookup=False) == (False, ""), (n, packed))
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
    lost_before = _raises(lambda: DG.check(a, iso(ago(5)), "car6404", "99309", allow_lookup=False), DG.DayLost)
    n = DD.unpack(drive, [DCACHE]); got = cache_json()
    check("drive merge (finding 2): a 'no death' note of the Drive copy NEVER replaces an entry whose dod is set - not a placeholder checked before the note, not one checked after it, not a day (whatever the note's date)",
          lambda: got[a] == {"dod": "[DOB]", "checked": iso(ago(30)), "src": "stedi-medicare-271"} and got[b]["dod"] == "[DOB]" and got[c]["dod"] == iso(ago(60)), {k: got.get(k) for k in (a, b, c)})
    check("drive merge: ... so the claim of such a chart is as little cleared after step 0c's merge as before it - the guard still raises DayLost (it answered 'not blocked' after the merge)",
          lambda: lost_before and _raises(lambda: DG.check(a, iso(ago(5)), "car6404", "99309", allow_lookup=False), DG.DayLost) and SENT == [] and FREE_ASKED == [], lost_before)
    check("drive merge (finding 2): of two days for one chart the EARLIER stays, whatever the check dates - the cache's early day is not replaced by Drive's later one (its check date is newer), and Drive's early day replaces the cache's later one (its check date is older); a visit between the two days is blocked either way",
          lambda: got[c]["dod"] == iso(ago(60)) and got[c]["checked"] == iso(ago(30)) and got[d]["dod"] == iso(ago(60)) and DG.check(c, iso(ago(30)), "car6404", "99309", allow_lookup=False)[0] is True
          and DG.check(d, iso(ago(30)), "car6404", "99309", allow_lookup=False)[0] is True, {k: got.get(k) for k in (c, d)})
    check("drive merge: a real day still beats a placeholder (also one checked later than the Drive copy's entry); the same day with a newer check date only moves the check date; what stands under 'dated' but is no day is not taken; a newer note still renews an entry with NO death on record - and the count is the entries written",
          lambda: got[f]["dod"] == iso(ago(50)) and got[h]["dod"] == iso(ago(45)) and got[h]["checked"] == iso(ago(4)) and g not in got and got[e] == {"dod": None, "checked": iso(ago(10)), "src": "stedi: no death on record"} and n == 3,
          (n, {k: got.get(k) for k in (e, f, g, h)}))
    odd = os.path.join(TMP, "drive_merge_list.json"); open(odd, "w").write("[1, 2, 3]"); m = _try(lambda: DD.unpack(drive, [odd]))
    check("drive merge: a cache file that is there but is no table (a JSON list) does not stop the merge - it is replaced by the table the Drive copy gives",
          lambda: m != "raised" and json.load(open(odd))[f]["dod"] == iso(ago(50)) and json.load(open(odd))[a] == {"dod": None, "checked": iso(ago(10)), "src": "stedi: no death on record (drive copy)"}, m)
    put_cache({a: {"dod": iso(ago(9)), "checked": iso(ago(1))}, b: "a line that is no entry", c: ["nor", "this"], d: {"dod": None, "checked": iso(ago(2))}}); out = os.path.join(TMP, "drive_pack_odd.json")
    k = _try(lambda: DD.pack(DCACHE, out))
    check("drive copy: pack passes over a cache line that is no entry (a text, a list) - it does not stop the pack, and the entries beside it are packed", lambda: k == (1, 1) and sorted(json.load(open(out))["dated"]) == [a] and list(json.load(open(out))["nodeath"]) == [d], k)

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
    r = guard_check(k, iso(ago(2)), carrier="car6404", proc="99490")
    check("free first: a care-management claim billed to another payer is checked too - the free check goes to the chart's Medicare plan and its date of death blocks, nothing bought",
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
    e = one(lambda p: [("car6404", "", "M" + "6" * 9)], 0, carrier="car6404", proc="99490")
    check("free first (A1, A11): no Medicare plan on the chart -> NO free check; the look-up by name runs exactly as before, counted 'guard, no Medicare plan on the chart'; COUNTS = 0 asked free, 1 bought",
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
_a1 = {k: _g1.check(k, _dos, "car6404", "99349", allow_lookup=False) for k in ("7001", "7002", "7003", "7004", "7005")}
_c1 = json.load(open(os.path.join(_ws1, "registers", "deceased_cache.json")))
check("guard (one cache): in a workspace that holds three cache files the guard uses the register and knows EVERY day any of them holds - a claim after the day is blocked for the charts only the feed's own file or the hand copy knew, with nobody asked; a chart with no death on record anywhere is not blocked",
      lambda: _g1.CACHE == os.path.join(_ws1, "registers", "deceased_cache.json") and all(_a1[k][0] is True for k in ("7001", "7002", "7004", "7005")) and _a1["7003"] == (False, ""), _a1)
check("guard (one cache): ... the days are carried INTO the cache in use (the file the pack uploads), each as YYYY-MM-DD: a day that can be read replaces the scrubbed one, of two days the EARLIER stays, an entry without a day and a line that is no entry are not carried",
      lambda: _c1["7002"]["dod"] == iso(ago(20)) and _c1["7004"]["dod"] == iso(ago(12)) and _c1["7005"]["dod"] == iso(ago(8)) and _c1["7001"]["dod"] == iso(ago(30)) and "7003" not in _c1 and "not a chart" not in _c1, _c1)
_ws2 = _three_files("named"); _g2 = _guard_at(os.path.join(_ws2, "deceased_guard.py"), env=os.path.join(_ws2, "deceased_cache_local.json"))
_a2 = {k: _g2.check(k, _dos, "car6404", "99349", allow_lookup=False) for k in ("7001", "7002", "7005")}
check("guard (one cache): ... and a helper of before that still names the feed's own file (DECEASED_CACHE) gets the same days carried into THAT file: whichever file a helper names, no day the workspace holds is unknown to it",
      lambda: _g2.CACHE == os.path.join(_ws2, "deceased_cache_local.json") and all(v[0] is True for v in _a2.values()) and json.load(open(_g2.CACHE))["7001"]["dod"] == iso(ago(30)), _a2)
_ws3 = _three_files("unreadable"); open(os.path.join(_ws3, "registers", "deceased_cache.json"), "w").write("{ this register cannot be read"); open(os.path.join(_ws3, "deceased_cache_local.json"), "w").write("[1, 2")
_g3 = _guard_at(os.path.join(_ws3, "deceased_guard.py")); _a3 = _g3.check("7005", _dos, "car6404", "99349", allow_lookup=False)
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
_a4 = {k: (_try(lambda k=k: _g4.check(k, _dos4, "car6404", "99349", allow_lookup=False)), _raises(lambda k=k: _g4.check(k, _dos4, "car6404", "99349", allow_lookup=False), _g4.DayLost)) for k in ("7060", "7061", "7062", "7063", "7064", "7099")}
_c4 = json.load(open(os.path.join(_ws4, "registers", "deceased_cache.json")))
check("guard (carry, finding 8a): a PLACEHOLDER that stands only in another cache file is carried as a death on record when the cache in use holds no dod for the chart - no entry at all, or 'no death on record': the chart is NOT cleared (DayLost) where it read 'clear' with nobody asked; the cache in use keeps its own day and its own placeholder as they were",
      lambda: _a4["7060"][1] and _a4["7061"][1] and _a4["7063"][1] and _a4["7062"][0][0] is True and _a4["7099"][0] == (False, "") and _c4["7060"]["dod"] == "[DOB]" and _c4["7061"]["dod"] == "[DOB]"
      and _c4["7062"]["dod"] == iso(ago(9)) and _c4["7063"] == _own63 and _g4.cache_state()["lost"] == 3, (_a4, _c4))
check("guard (carry): ... the entry's own fields stay when something is carried into it (its name), of two days the EARLIER wins also when it is the OTHER file's (the cache in use held the later one), and an entry under a key that is no chart number is not carried - day or placeholder",
      lambda: _c4["7061"].get("name") == "kept" and _c4["7064"]["dod"] == iso(ago(40)) and _c4["7064"].get("name") == "kept" and _c4["7064"].get("at") == "a field of its own" and _a4["7064"][0][0] is True
      and "somebody" not in _c4 and "nobody" not in _c4, _c4)
reset(); _p4 = newp(death=ago(20)); chart("7060", _p4, plans=[("car6404", "", "M" + "8" * 9)]); _g4._LOST_ASKED.clear(); _r4 = _try(lambda: _g4.check("7060", _dos4, "car6404", "99349")); _k4 = kinds()
check("guard (carry): ... and such a chart is ASKED about whatever its payer, like any chart whose day is lost - here the look-up names the day and the claim after it is blocked",
      lambda: _r4 != "raised" and _r4[0] is True and iso(ago(20)) in _r4[1] and _k4 == ["MBILUNOSSN"], (_r4, _k4))
_ws5 = _cache_files("unreadable_in_use", '{"7070": {"dod": "20', local={"7070": {"dod": iso(ago(40)), "checked": iso(ago(2)), "src": "amd-271"}, "7071": {"dod": "[DOB]", "checked": iso(ago(2)), "src": "x"}, "7072": {"dod": None, "checked": iso(ago(2))}})
_g5 = _guard_at(os.path.join(_ws5, "deceased_guard.py"))
_a5 = (_try(lambda: _g5.check("7070", iso(ago(5)), "car6404", "99349", allow_lookup=False)), _raises(lambda: _g5.check("7071", iso(ago(5)), "car6404", "99349", allow_lookup=False), _g5.DayLost), _try(lambda: _g5.check("7072", iso(ago(5)), "car6404", "99349", allow_lookup=False)))
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
_aD = (_try(lambda: _gD.check("7950", iso(ago(5)), "car6404", "99349", allow_lookup=False)), _raises(lambda: _gD.check("7951", iso(ago(5)), "car6404", "99349", allow_lookup=False), _gD.DayLost))
check("guard (layout): ... so a visit after a day that register holds is blocked there, and a chart whose day is the placeholder is not cleared (both answered 'not blocked'); nothing is written into the stray folder",
      lambda: _aD[0] != "raised" and _aD[0][0] is True and _aD[1] is True and os.listdir(os.path.join(_clD, "scripts", "helpers", "registers")) == [], _aD)
_clE = _tree("clone_stray_file", [_REG, "scripts/helpers/registers/deceased_cache.json", "scripts/helpers/deceased_cache_local.json"], ["core"])
with open(os.path.join(_clE, "scripts", "helpers", "registers", "deceased_cache.json"), "w") as _fh: json.dump({"7952": {"dod": iso(ago(30)), "checked": iso(ago(1)), "src": "x"}}, _fh)
_gE = _guard_at(os.path.join(_clE, "scripts", "helpers", "deceased_guard.py")); _oE = sorted(_gE._others()); _aE = _try(lambda: _gE.check("7952", iso(ago(5)), "car6404", "99349", allow_lookup=False))
check("guard (layout): ... and a cache FILE such a stray folder holds (the guard of that round wrote its answers there) is one of the other files: _others() lists every cache file of the layout except the one in use, and its day is carried into the repository's register",
      lambda: _gE.CACHE == os.path.join(_clE, _REG) and _oE == sorted([os.path.join(_clE, "scripts", "helpers", "registers", "deceased_cache.json"), os.path.join(_clE, "scripts", "helpers", "deceased_cache_local.json")])
      and _aE != "raised" and _aE[0] is True and json.load(open(os.path.join(_clE, _REG)))["7952"]["dod"] == iso(ago(30)), lambda: (_gE.CACHE, _oE, _aE))
_clF = _tree("clone_named", [_REG], ["core", "scripts/helpers"])
with open(os.path.join(_clF, _REG), "w") as _fh: json.dump({"7953": {"dod": iso(ago(30)), "checked": iso(ago(1)), "src": "x"}}, _fh)
_nF = os.path.join(_clF, "scripts", "helpers", "deceased_cache_local.json"); _nC = os.path.join(_clF, "core", "a_cache_of_its_own.json")
_gF = _guard_at(os.path.join(_clF, "scripts", "helpers", "deceased_guard.py"), env=_nF); _oF = _gF._others(); _aF = _try(lambda: _gF.check("7953", iso(ago(5)), "car6404", "99349", allow_lookup=False))
_cF = _try(lambda: json.load(open(_nF))["7953"]["dod"])
_gC = _guard_at(os.path.join(_clF, "core", "deceased_guard.py"), env=_nC); _oC = _gC._others(); _aC = _try(lambda: _gC.check("7953", iso(ago(5)), "car6404", "99349", allow_lookup=False))
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
check("nothing was written in the checkout", lambda: _snapshot() == BEFORE, sorted(set(_snapshot().items()) ^ set(BEFORE.items()))[:5])
print("test_lookup_rules: %d checks, %d failed%s" % (COUNT[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:300]))
sys.exit(1 if FAILS else 0)
