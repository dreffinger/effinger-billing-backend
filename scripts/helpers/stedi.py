# PLAIN ENGLISH (Stedi client)
# Decides: Nothing. Asks Stedi questions: payer eligibility, MBI lookup, insurance discovery, payer search, enrollment status.
#   11/10/2026 (look-ups part A, William 11/10: "get a better deal on all the look ups"): it also decides HOW one Medicare answer is
#   asked - medicare() sends a PLAIN Medicare check (payer id CMS, the ordinary eligibility price) with the Medicare number already on
#   the chart, and buys the Medicare-number look-up only when the chart has no number of that shape or Medicare does not know it.
# Rules it uses: Uses secrets/stedi_live.key when present; otherwise sends NO Authorization header and the ehpa cloud environment's API credential (agent proxy) attaches the key. Provider is always Effinger Health PA 1629515325. MBI lookups need a date of service to get the right Advantage plan for that date.
#   11/10/2026: every paid call (every POST) leaves ONE line in the usage log ($STEDI_USAGE_LOG, default patient_db/stedi_usage.log -
#   time, who asked, kind of call, payer id, chart id, first error code or ok, first-tier list price from stedi_prices.py); the two free
#   GET calls are not counted, and writing the line can never stop a call. Medicare answers are shared with every other helper through
#   medicare_store.py (one file under patient_db/, never the Medicare number, a name or a birth date).
# Never touches: AMD. Results are read by a person or another script before anything changes on a chart.
# ---
"""Stedi client (headless, from the container - allowed 9/6 after William allowlisted the domains).
Key: secrets/stedi_live.key when present (Gmail fallback); when absent the request goes out without an Authorization header and
the environment API credential for healthcare.us.stedi.com / enrollments.us.stedi.com supplies it at the proxy (bootstrap_workspace.sh net
prints STEDI_CRED_OK / STEDI_CRED_MISSING).  Usage examples (placeholders - real patient data stays out of git, rules.md):
  python3 stedi.py mbi FIRST LAST YYYYMMDD ST YYYYMMDD              # MBI lookup without SSN (payer MBILUNOSSN)
  python3 stedi.py mbi FIRST LAST YYYYMMDD - YYYYMMDD <ssn>          # with SSN (MBILU)
  python3 stedi.py medicare FIRST LAST YYYYMMDD <medicare number or -> YYYYMMDD [ST]   # ONE Medicare answer: plain check first, look-up only when needed
  python3 stedi.py elig 87726 FIRST LAST YYYYMMDD <member> YYYYMMDD
  python3 stedi.py disc FIRST LAST YYYYMMDD ST YYYYMMDD
  python3 stedi.py payer "capital health plan"
Argument order: name, date of birth, then state or member number, then the date of service.
"""
import requests, json, sys, os, re, datetime, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
_KEYFILE = os.path.join(HERE, "secrets", "stedi_live.key")
KEY = open(_KEYFILE).read().strip() if os.path.isfile(_KEYFILE) else ""
H = {"Content-Type": "application/json"}
if KEY: H["Authorization"] = KEY   # no key file -> the environment API credential adds the header at the proxy
API = "https://healthcare.us.stedi.com/2024-04-01"
ENR = "https://enrollments.us.stedi.com/2024-09-01"
PROV = {"organizationName": "EFFINGER HEALTH PA", "npi": "1629515325"}
# 11/10/2026 USAGE LOG: WHO names the helper on every line - a helper sets stedi.WHO once; by default it is the program's file name.
WHO = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else "stedi.py"
_CALL = {"pid": None, "who": None}     # the chart id and the asker of the call in progress (set by medicare() and the pid= wrappers) - for the log line only
def _kind(url, body):
    """The kind of paid call, as the statement and stedi_prices.py name it."""
    if "insurance-discovery" in url: return "discovery"
    if "claimstatus" in url: return "claim status"
    payer = str((body or {}).get("tradingPartnerServiceId") or "")
    return {"MBILU": "look-up with SSN", "MBILUNOSSN": "look-up without SSN", "CMS": "plain Medicare"}.get(payer, "eligibility")
def _err_word(e):
    """A failed call in one short word: 'http 503', 'time-out', or the kind of error (no text that could carry patient data)."""
    st = getattr(getattr(e, "response", None), "status_code", None)
    if st: return "http %s" % st
    return "time-out" if "timeout" in type(e).__name__.lower() else "error %s" % type(e).__name__
def _usage_line(url, body, j=None, err=None):
    """ONE line in the usage log for one paid call. Anything that goes wrong here is swallowed: the log never stops or slows a call."""
    try:
        kind = _kind(url, body); errs = j.get("errors") if isinstance(j, dict) else None
        code = _err_word(err) if err is not None else (str(errs[0].get("code")) if errs and isinstance(errs[0], dict) and errs[0].get("code") is not None else "ok")
        try:
            import stedi_prices; price = "%.2f" % stedi_prices.first_tier(kind)
        except Exception: price = ""
        pid = re.sub(r"\D", "", str(_CALL.get("pid") or "")) or "-"
        payer = "-" if kind == "discovery" else str((body or {}).get("tradingPartnerServiceId") or "-")
        line = "\t".join(re.sub(r"[\t\r\n]+", " ", str(x)) for x in (datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), _CALL.get("who") or WHO, kind, payer, pid, code, price))
        p = os.environ.get("STEDI_USAGE_LOG") or os.path.join(HERE, "patient_db", "stedi_usage.log")
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
        with open(p, "a") as fh: fh.write(line + "\n")
    except Exception: pass
@contextlib.contextmanager
def _asking(pid=None, who=None):
    """The chart id / asker of the calls made inside the block (the usage log names them); restored afterwards."""
    saved = dict(_CALL)
    if pid: _CALL["pid"] = pid
    if who: _CALL["who"] = who
    try: yield
    finally: _CALL.clear(); _CALL.update(saved)
def _post(url, body):
    try:
        r = requests.post(url, headers=H, json=body, timeout=130); r.raise_for_status(); j = r.json()
    except Exception as e:
        _usage_line(url, body, err=e); raise
    _usage_line(url, body, j=j); return j
def elig(payer, first, last, dob, member_id, dos, stc=("30",)):
    return _post(API + "/change/medicalnetwork/eligibility/v3", {"tradingPartnerServiceId": payer, "provider": PROV,
        "subscriber": {"firstName": first, "lastName": last, "dateOfBirth": dob, "memberId": member_id}, "encounter": {"dateOfService": dos, "serviceTypeCodes": list(stc)}})
def mbi(first, last, dob, state=None, dos=None, ssn=None):
    sub = {"firstName": first, "lastName": last, "dateOfBirth": dob}
    if ssn: sub["ssn"] = ssn.replace("-", "")
    else: sub["address"] = {"state": state or "FL"}
    enc = {"serviceTypeCodes": ["30"]}
    if dos: enc["dateOfService"] = dos
    return _post(API + "/change/medicalnetwork/eligibility/v3", {"tradingPartnerServiceId": "MBILU" if ssn else "MBILUNOSSN", "provider": PROV, "subscriber": sub, "encounter": enc})
def disc(first, last, dob, state="FL", dos=None):
    body = {"provider": PROV, "subscriber": {"firstName": first, "lastName": last, "dateOfBirth": dob, "address": {"state": state}}}
    if dos: body["encounter"] = {"dateOfService": dos}
    return _post(API + "/insurance-discovery/check/v1", body)
def payers(q):
    r = requests.get(API + "/payers/search", params={"query": q}, headers=H, timeout=60); r.raise_for_status(); return r.json().get("items", [])
def enrollments():
    r = requests.get(ENR + "/enrollments", headers=H, timeout=60); r.raise_for_status(); return r.json().get("items", [])
def med_summ(j):
    """Medicare picture from an MBI-lookup / CMS response."""
    if isinstance(j, dict) and isinstance(j.get("stored"), dict):     # 11/10/2026: an answer read back from medicare_store.py - it keeps no number, name, birth date or address
        return {"mbi": None, "name": None, "dob": None, "death": j.get("death"), "address": None, "errors": list(j.get("errors") or []),
                "partA": j.get("partA"), "partB": j.get("partB"), "other": list(j.get("other") or [])}
    b = j.get("benefitsInformation") or []; pd = j.get("planDateInformation") or {}; s = j.get("subscriber") or {}
    o = {"mbi": s.get("memberId"), "name": "%s, %s" % (s.get("lastName"), s.get("firstName")), "dob": s.get("dateOfBirth"), "death": pd.get("dateOfDeath"),
         "address": s.get("address"), "errors": ["%s %s" % (e.get("code"), e.get("description")) for e in j.get("errors") or []]}
    for code, key in (("MA", "partA"), ("MB", "partB")):
        x = next((x for x in b if x.get("code") == "1" and x.get("insuranceTypeCode") == code), None)
        d = (x or {}).get("benefitsDateInformation") or {}; o[key] = d.get("plan") or d.get("benefit")
    o["other"] = []
    for x in b:
        if x.get("code") in ("R", "U", "X", "Y") or "45" in (x.get("serviceTypeCodes") or []):
            o["other"].append({"code": x.get("code"), "type": x.get("insuranceTypeCode"), "typeName": x.get("insuranceType"), "plan": x.get("planCoverage"),
                               "dates": x.get("benefitsDateInformation"), "entity": [(e.get("entityName"), e.get("entityIdentifierValue")) for e in x.get("benefitsRelatedEntities") or []]})
    return o
def disc_summ(j):
    out = []
    for it in j.get("items") or []:
        b = it.get("benefitsInformation") or []; act = next((x for x in b if x.get("code") == "1"), b[0] if b else {})
        out.append({"payer": (it.get("payer") or {}).get("name"), "payerId": it.get("payerId"), "member": (it.get("subscriber") or {}).get("memberId"),
                    "dates": it.get("planDateInformation"), "status": act.get("name"), "plan": act.get("planCoverage"), "conf": it.get("confidence")})
    return {"found": j.get("coveragesFound"), "items": out, "errors": j.get("errors")}

# 9/22/2026 DECEASED GUARD: every Medicare 271 feeds the date-of-death cache (core/deceased_guard.py) when the caller passes pid=.
# 11/10/2026: a PLAIN Medicare answer (payer id CMS) is passed on only when it is a real answer (no error, and Part A / Part B or a date of
#   death in it) or when it carries a date of death: on a plain check code 72 means 'this number is not valid', never 'no Medicare record',
#   so a plain 'not found' is never remembered as 'no death on record'. No chart id -> nothing to record (the guard is not even loaded).
def _dod_hook(pid, j, plain=False):
    try:
        if not pid or (plain and not (_plain_usable(j) or _death(j))): return
        import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import deceased_guard
        deceased_guard.record(pid, j)
    except Exception: pass
_elig_raw, _mbi_raw = elig, mbi
def elig(payer, first, last, dob, member_id, dos, stc=("30",), pid=None):
    with _asking(pid): j = _elig_raw(payer, first, last, dob, member_id, dos, stc)
    if payer in ("CMS", "MBILU", "MBILUNOSSN"): _dod_hook(pid, j, plain=(payer == "CMS"))
    return j
def mbi(first, last, dob, state=None, dos=None, ssn=None, pid=None):
    with _asking(pid): j = _mbi_raw(first, last, dob, state, dos, ssn)
    _dod_hook(pid, j); return j

# 11/10/2026 ONE MEDICARE ANSWER FOR EVERYBODY (look-ups part A). medicare() is how a helper asks Medicare about a patient:
#   1. the chart's member number is cleaned (spaces and dashes out, upper case); when it has the shape of a Medicare number (11 characters:
#      digit 1-9, letter, letter-or-digit, digit, letter, letter-or-digit, digit, letter, letter, digit, digit; never S, L, O, I, B, Z) a
#      PLAIN eligibility check goes to payer id CMS with it. Anything else on the chart (an old number, a plan's member id) skips it;
#   2. the plain answer is used when it carries no error and shows Part A or Part B or a date of death -> how = "plain";
#   3. Medicare says the number or the name is not found (72, 73, 75, 76, 58) -> a generation suffix (JR, SR, II, III, IV) comes off the
#      last name and the plain check goes ONCE more; still not found -> ONE look-up (the SSN only when the caller passed one - it is never
#      fetched for this) -> how = "lookup after plain"; the look-up's answer is the result. Any other refusal of the plain check (41 the
#      provider is not cleared, 61, an answer with no Part A or Part B) also goes to the look-up, as every caller did before, and says so in
#      NOTES. A plain 'not found' is never the result and never means 'no Medicare record';
#   4. no usable number on the chart -> the look-up, as before -> how = "lookup";
#   5. the vendor or Medicare is down (42, 79, 80, a time-out, an HTTP error) -> no second call of another kind -> how = "failed", and the
#      caller treats it exactly as a failed look-up before;
#   6. always the group provider block and the caller's date of service; the date-of-death hook runs on every answer when pid= is given;
#   7. in a plain answer the member number is only the echo of the number sent: only an answer from a look-up can show that the chart's
#      number differs from Medicare's (LOOKUP_KINDS);
#   8. with pid= and max_age_days= the answer store (medicare_store.py) is read first, with the caller's own age rule; every real answer is
#      written to it, a failed call only as 'asked and failed today' so no other helper buys the same failing chart again that day.
MEDICARE_NOT_FOUND = {"72", "73", "75", "76", "58"}      # the number or the name is not found
MEDICARE_DOWN = {"42", "79", "80"}                        # the vendor or Medicare cannot answer now
LOOKUP_KINDS = ("lookup", "lookup after plain")           # answers that came from a look-up: the only ones whose member number is Medicare's own
NOTES = []                                                 # report lines: a plain check Medicare refused for another reason than 'not found'
_LT = "ACDEFGHJKMNPQRTUVWXY"
_NUMBER = re.compile("[1-9][{0}][{0}0-9][0-9][{0}][{0}0-9][0-9][{0}][{0}][0-9][0-9]".format(_LT))
_SUFFIX = re.compile(r"^(.*?[^\s,.])[\s,.]+(?:JR|SR|II|III|IV)\.?$", re.I)
def medicare_number(x):
    """The chart's member number cleaned (spaces and dashes out, upper case) when it has the shape of a Medicare number, else None."""
    s = re.sub(r"[\s-]+", "", str(x or "")).upper()
    return s if _NUMBER.fullmatch(s) else None
def _codes(j):
    return [str(e.get("code")) for e in (j.get("errors") or []) if isinstance(e, dict)] if isinstance(j, dict) else []
def _death(j):
    """The earliest date of death anywhere in a Medicare answer (dateOfDeath, or DTP*442 in the raw X12) as YYYYMMDD, else None."""
    s = json.dumps(j); hits = re.findall(r'"[A-Za-z]*[Dd]eath[A-Za-z]*"\s*:\s*"(\d{8})"', s) + re.findall(r"DTP\*442\*D8\*(\d{8})", s)
    return sorted(set(hits))[0] if hits else None
def _parts(j):
    """The Part A and Part B lines of an answer (insurance type MA or MB)."""
    return [x for x in ((j or {}).get("benefitsInformation") or []) if isinstance(x, dict) and x.get("insuranceTypeCode") in ("MA", "MB")] if isinstance(j, dict) else []
def _plain_usable(j):
    return isinstance(j, dict) and not j.get("errors") and bool(_parts(j) or _death(j))
def _real(j, how):
    """A real answer, kept in the store: one with no error that shows Part A / Part B or a date of death (plain or look-up), a look-up with
    72 alone (not a Medicare beneficiary - the guard has always kept that), any date of death. An empty reply with no error is NOT an
    answer: it is kept only as 'asked and failed today' and never as 'no death on record'."""
    if how == "failed": return False
    return how == "plain" or _plain_usable(j) or _codes(j) == ["72"] or bool(_death(j))
def _hospice_line(x):
    """11/10/2026 (look-ups part A, step 3): a hospice election in a Medicare answer is a Health Care Facility line (code X) for service type
    45 - the hospice provider's line with its dates. The Part A lines (active coverage, deductible) list 45 among the many services they
    cover for EVERY beneficiary (the vendor's own look-up example; both plain answers of 10/8/2026), so 45 on such a line is not hospice."""
    return isinstance(x, dict) and x.get("code") == "X" and "45" in [str(s) for s in (x.get("serviceTypeCodes") or [])]
def medicare_facts(j, how, number=None):
    """What medicare_store.py keeps of one answer: the facts every reader needs - never the Medicare number, a name, a birth date or an address."""
    m = med_summ(j)
    if how == "failed": return {"errors": m["errors"], "reason": (j or {}).get("failed") or (m["errors"][0] if m["errors"] else "failed")}
    differs = None
    if how in LOOKUP_KINDS and number and m["mbi"]: differs = (medicare_number(m["mbi"]) or str(m["mbi"]).strip().upper()) != number
    return {"active": any(x.get("code") == "1" for x in _parts(j)), "partA": m["partA"], "partB": m["partB"], "other": m["other"],
            "hospice": any(_hospice_line(x) for x in ((j or {}).get("benefitsInformation") or [])),   # a code-X line for service type 45 (not the Part A line)
            "death": _death(j), "errors": m["errors"], "number_differs": differs}
def _store():
    """The answer store module, or None when this workspace lacks it (a missing store is an empty store: the caller simply asks)."""
    try:
        if HERE not in sys.path: sys.path.append(HERE)
        import medicare_store; return medicare_store
    except Exception: return None
def _note(pid, msg):
    line = "pat%s: %s" % (re.sub(r"\D", "", str(pid or "")) or "?", msg); NOTES.append(line)
    try: print("stedi.medicare: " + line, file=sys.stderr)
    except Exception: pass
def _plain_raw(first, last, dob, number, dos):
    enc = {"serviceTypeCodes": ["30"]}
    if dos: enc["dateOfService"] = dos
    return _post(API + "/change/medicalnetwork/eligibility/v3", {"tradingPartnerServiceId": "CMS", "provider": PROV,
        "subscriber": {"firstName": first, "lastName": last, "dateOfBirth": dob, "memberId": number}, "encounter": enc})
def _ask_medicare(first, last, dob, number, dos, state, ssn, pid):
    how = "lookup"
    if number:
        how = "lookup after plain"
        for n in (1, 2):
            try: j = _plain_raw(first, last, dob, number, dos)
            except Exception as e: return {"errors": [], "failed": _err_word(e)}, "failed"
            _dod_hook(pid, j, plain=True)
            if _plain_usable(j): return j, "plain"
            c = set(_codes(j))
            if c & MEDICARE_DOWN: return j, "failed"
            if n == 1 and c & MEDICARE_NOT_FOUND and _SUFFIX.match(str(last or "").strip()):
                last = _SUFFIX.match(str(last).strip()).group(1); continue          # the suffix off, the plain check ONCE more
            if not c & MEDICARE_NOT_FOUND: _note(pid, "Medicare refused the plain check (%s) - the look-up was bought instead" % (", ".join(sorted(c)) or "no Part A or Part B in the answer"))
            break
    try: j = _mbi_raw(first, last, dob, state, dos, ssn)
    except Exception as e: return {"errors": [], "failed": _err_word(e)}, "failed"
    _dod_hook(pid, j)
    if set(_codes(j)) & MEDICARE_DOWN: return j, "failed"
    return j, how
def medicare(first, last, dob, member_id=None, dos=None, state="FL", ssn=None, pid=None, who="", max_age_days=None):
    """ONE Medicare answer -> (answer, how); how is 'plain', 'lookup after plain', 'lookup' or 'failed' (see the note above).
    An answer read back from the store carries "stored": {asked, dos, how, who} and the stored facts; med_summ() reads it like a 271."""
    who = who or WHO; dos = re.sub(r"\D", "", str(dos or ""))[:8] or None; number = medicare_number(member_id); store = _store() if pid else None
    if store and max_age_days is not None:
        try: hit = store.get(pid, max_age_days, dos)
        except Exception: hit = None
        if hit and hit.get("failed"):
            return {"stored": {"asked": hit.get("day"), "dos": hit.get("dos"), "how": "failed", "who": hit.get("who")}, "failed": hit.get("reason") or "failed", "errors": list(hit.get("errors") or [])}, "failed"
        if hit:
            ans = {k: hit.get(k) for k in ("active", "partA", "partB", "other", "hospice", "death", "errors", "number_differs")}
            ans["stored"] = {k: hit.get(k) for k in ("asked", "dos", "how", "who")}
            return ans, hit.get("how")
    with _asking(pid, who): j, how = _ask_medicare(first, last, dob, number, dos, state, ssn, pid)
    if store:
        kind = how if _real(j, how) else "failed"
        try: store.put(pid, medicare_facts(j, kind, number), kind, who, dos)
        except Exception: pass
    return j, how

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "mbi": print(json.dumps(med_summ(mbi(a[1], a[2], a[3], None if a[4] == "-" else a[4], a[5] if len(a) > 5 else None, a[6] if len(a) > 6 else None)), indent=1))
    elif a[0] == "medicare": j, how = medicare(a[1], a[2], a[3], None if a[4] == "-" else a[4], a[5] if len(a) > 5 else None, a[6] if len(a) > 6 else "FL"); print(json.dumps(dict(med_summ(j), how=how), indent=1))
    elif a[0] == "elig": j = elig(a[1], a[2], a[3], a[4], a[5], a[6]); print(json.dumps({"planStatus": j.get("planStatus"), "dates": j.get("planDateInformation"), "errors": j.get("errors"), "plans": [x.get("planCoverage") for x in j.get("benefitsInformation") or [] if x.get("planCoverage")][:3]}, indent=1))
    elif a[0] == "disc": print(json.dumps(disc_summ(disc(a[1], a[2], a[3], a[4], a[5] if len(a) > 5 else None)), indent=1))
    elif a[0] == "payer": print([(p["payer"]["displayName"], p["payer"]["primaryPayerId"], p["payer"]["transactionSupport"]["eligibilityCheck"]) for p in payers(a[1])[:6]])
    elif a[0] == "enr": print([(e["payer"].get("name"), e["status"]) for e in enrollments()])
