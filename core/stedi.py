# PLAIN ENGLISH (Stedi client)
# Decides: Nothing. Asks Stedi questions: payer eligibility, MBI lookup, insurance discovery, payer search, enrollment status.
# Rules it uses: Uses secrets/stedi_live.key when present; otherwise sends NO Authorization header and the ehpa cloud environment's API credential (agent proxy) attaches the key. Provider is always Effinger Health PA 1629515325. MBI lookups need a date of service to get the right Advantage plan for that date.
# Never touches: AMD. Results are read by a person or another script before anything changes on a chart.
# ---
"""Stedi client (headless, from the container - allowed 9/6 after William allowlisted the domains).
Key: secrets/stedi_live.key when present (Gmail fallback); when absent the request goes out without an Authorization header and
the environment API credential for healthcare.us.stedi.com / enrollments.us.stedi.com supplies it at the proxy (bootstrap_workspace.sh net
prints STEDI_CRED_OK / STEDI_CRED_MISSING).  Usage examples (placeholders - real patient data stays out of git, rules.md):
  python3 stedi.py mbi FIRST LAST YYYYMMDD ST YYYYMMDD              # MBI lookup without SSN (payer MBILUNOSSN)
  python3 stedi.py mbi FIRST LAST YYYYMMDD - YYYYMMDD <ssn>          # with SSN (MBILU)
  python3 stedi.py elig 87726 FIRST LAST YYYYMMDD <member> YYYYMMDD
  python3 stedi.py disc FIRST LAST YYYYMMDD ST YYYYMMDD
  python3 stedi.py payer "capital health plan"
Argument order: name, date of birth, then state or member number, then the date of service.
"""
import requests, json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
_KEYFILE = os.path.join(HERE, "secrets", "stedi_live.key")
KEY = open(_KEYFILE).read().strip() if os.path.isfile(_KEYFILE) else ""
H = {"Content-Type": "application/json"}
if KEY: H["Authorization"] = KEY   # no key file -> the environment API credential adds the header at the proxy
API = "https://healthcare.us.stedi.com/2024-04-01"
ENR = "https://enrollments.us.stedi.com/2024-09-01"
PROV = {"organizationName": "EFFINGER HEALTH PA", "npi": "1629515325"}
def _post(url, body):
    r = requests.post(url, headers=H, json=body, timeout=130); r.raise_for_status(); return r.json()
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
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "mbi": print(json.dumps(med_summ(mbi(a[1], a[2], a[3], None if a[4] == "-" else a[4], a[5] if len(a) > 5 else None, a[6] if len(a) > 6 else None)), indent=1))
    elif a[0] == "elig": j = elig(a[1], a[2], a[3], a[4], a[5], a[6]); print(json.dumps({"planStatus": j.get("planStatus"), "dates": j.get("planDateInformation"), "errors": j.get("errors"), "plans": [x.get("planCoverage") for x in j.get("benefitsInformation") or [] if x.get("planCoverage")][:3]}, indent=1))
    elif a[0] == "disc": print(json.dumps(disc_summ(disc(a[1], a[2], a[3], a[4], a[5] if len(a) > 5 else None)), indent=1))
    elif a[0] == "payer": print([(p["payer"]["displayName"], p["payer"]["primaryPayerId"], p["payer"]["transactionSupport"]["eligibilityCheck"]) for p in payers(a[1])[:6]])
    elif a[0] == "enr": print([(e["payer"].get("name"), e["status"]) for e in enrollments()])

# 9/22/2026 DECEASED GUARD: every Medicare 271 feeds the date-of-death cache (core/deceased_guard.py) when the caller passes pid=.
def _dod_hook(pid, j):
    try:
        import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import deceased_guard
        if pid: deceased_guard.record(pid, j)
    except Exception: pass
_elig_raw, _mbi_raw = elig, mbi
def elig(payer, first, last, dob, member_id, dos, stc=("30",), pid=None):
    j = _elig_raw(payer, first, last, dob, member_id, dos, stc)
    if payer in ("CMS", "MBILU", "MBILUNOSSN"): _dod_hook(pid, j)
    return j
def mbi(first, last, dob, state=None, dos=None, ssn=None, pid=None):
    j = _mbi_raw(first, last, dob, state, dos, ssn); _dod_hook(pid, j); return j
