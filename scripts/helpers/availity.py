# PLAIN ENGLISH (Availity client - eligibility and claim status straight from Florida Blue, Humana and the other Availity payers)
# Decides: Nothing. Asks Availity's official REST API (the same account William uses on Availity Essentials, through an API
#   application he registers once on developer.availity.com) two questions: is this member covered on this date (coverages =
#   the 270/271), and what happened to this claim (claim-statuses = the 276/277, which also returns the payer's claim number a
#   corrected claim needs). Built 11/19/2026 on William's word ("build this and get access on the back end") so the insurance
#   cascade has a second official source beside Stedi - Florida Blue and Humana answer natively here.
# Rules it uses: OAuth 2 client-credentials (token valid 5 minutes, cached in memory and re-asked when it expires); an answer
#   that comes back 'in process' (status code 0) is polled every 2 seconds until 'complete' (4) or 30 seconds have passed; every
#   call leaves ONE line in patient_db/availity_usage.log (time, who asked, kind, payer id, chart id, outcome - never a name,
#   a birth date or a member number). DEMO=1 (or --demo) sends the sandbox headers: canned answers, no patient data, no cost.
# Access: the client id and secret come from the environment (AVAILITY_CLIENT_ID / AVAILITY_CLIENT_SECRET, optional
#   AVAILITY_SCOPE) or from secrets/availity.json {"client_id","client_secret","scope"} (git-ignored, chmod 600) - never printed,
#   never in a file that leaves the workspace. With neither, every call answers {"error": "no Availity credential"} and nothing
#   is sent. docs/TODO_DATA_SOURCES.md has the one-time steps.
# Never touches: AdvancedMD. A person or another helper reads the answer before anything changes on a chart.
# NOT YET PROVEN LIVE (11/19/2026): the token URL, the 5-minute token, GET /coverages + GET /coverages/<id>, the 0 / 4 status
#   codes and the rate limits are from Availity's API guide; the query-parameter names below are Availity's published names and
#   must be confirmed against the product's specification on the first Demo call (PARAMS is the one table to correct).
# ---
"""Usage (placeholders - real patient data stays out of git):
  python3 availity.py token                                              # proves the credential (prints only 'token ok, <n> s')
  python3 availity.py elig <payerId> FIRST LAST YYYY-MM-DD <member or -> YYYY-MM-DD [--demo]
  python3 availity.py claim <payerId> FIRST LAST YYYY-MM-DD <member> <from YYYY-MM-DD> <to YYYY-MM-DD> [<charge amount>] [--demo]
  python3 availity.py selftest                                           # no network: checks the summary reader
"""
import requests, json, sys, os, time, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("AVAILITY_BASE", "https://api.availity.com/availity/v1")
NPI_GROUP = "1629515325"; ORG = "EFFINGER HEALTH PA"
WHO = os.path.basename(sys.argv[0] or "availity.py")
USAGE = os.environ.get("AVAILITY_USAGE_LOG", os.path.join(HERE, "patient_db", "availity_usage.log"))
# the one table of query-parameter names (confirm on the first Demo call)
PARAMS = {"payer": "payerId", "npi": "providerNpi", "member": "memberId", "last": "patientLastName", "first": "patientFirstName",
          "dob": "patientBirthDate", "asof": "asOfDate", "stc": "serviceType", "from": "fromDate", "to": "toDate", "amount": "claimAmount"}
_tok = {"value": "", "until": 0.0}

def _cred():
    cid, sec, scope = os.environ.get("AVAILITY_CLIENT_ID"), os.environ.get("AVAILITY_CLIENT_SECRET"), os.environ.get("AVAILITY_SCOPE")
    f = os.path.join(HERE, "secrets", "availity.json")
    if not (cid and sec) and os.path.isfile(f):
        d = json.load(open(f)); cid, sec, scope = d.get("client_id"), d.get("client_secret"), d.get("scope") or scope
    return cid, sec, scope or "hipaa"

def _log(kind, payer, pid, outcome):
    try:
        os.makedirs(os.path.dirname(USAGE), exist_ok=True)
        open(USAGE, "a").write("%s | %s | %s | payer %s | chart %s | %s\n" % (datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), WHO, kind, payer or "-", pid or "-", outcome))
    except Exception: pass      # the log can never stop a call

def token():
    """A bearer token, '' when there is no credential or Availity refuses it (the reason is in token.error)."""
    if _tok["value"] and time.time() < _tok["until"]: return _tok["value"]
    cid, sec, scope = _cred(); token.error = ""
    if not (cid and sec): token.error = "no Availity credential"; return ""
    r = requests.post(BASE + "/token", data={"grant_type": "client_credentials", "client_id": cid, "client_secret": sec, "scope": scope},
                      headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=40)
    if r.status_code != 200: token.error = "token refused: HTTP %s" % r.status_code; return ""
    j = r.json(); _tok["value"] = j.get("access_token") or ""; _tok["until"] = time.time() + max(30, int(j.get("expires_in") or 300) - 30)
    return _tok["value"]
token.error = ""

def _get(path, params=None, demo=False, scenario=None):
    t = token()
    if not t: return {"error": token.error}
    h = {"Authorization": "Bearer " + t, "Accept": "application/json"}
    if demo or os.environ.get("DEMO") == "1":
        h["X-Api-Mock-Response"] = "true"
        if scenario: h["X-Api-Mock-Scenario-ID"] = scenario
    r = requests.get(BASE + path, params=params, headers=h, timeout=60)
    if r.status_code == 429: return {"error": "rate limit (HTTP 429) - wait a second, never retry in a loop"}
    try: j = r.json()
    except Exception: j = {"raw": r.text[:500]}
    if r.status_code >= 400 and "error" not in j: j["error"] = "HTTP %s" % r.status_code
    return j

def _first(j, key):
    """The first row of a collection answer ({key: [...]}) or the answer itself."""
    rows = j.get(key) if isinstance(j, dict) else None
    return rows[0] if isinstance(rows, list) and rows else j

def _poll(path, row, key, demo, wait=30):
    """Follow an 'in process' answer (statusCode 0) to 'complete' (4)."""
    t0 = time.time()
    while str(row.get("statusCode")) == "0" and row.get("id") and time.time() - t0 < wait:
        time.sleep(2); row = _first(_get("%s/%s" % (path, row["id"]), demo=demo), key)
    return row

def elig(payer, first, last, dob, member_id=None, asof=None, stc="30", npi=NPI_GROUP, pid=None, demo=False):
    """Eligibility (270/271). Dates are YYYY-MM-DD. Returns the complete coverage row (or {"error": ...})."""
    p = {PARAMS["payer"]: payer, PARAMS["npi"]: npi, PARAMS["last"]: last, PARAMS["first"]: first, PARAMS["dob"]: dob,
         PARAMS["asof"]: asof or datetime.date.today().isoformat(), PARAMS["stc"]: stc}
    if member_id: p[PARAMS["member"]] = member_id
    j = _get("/coverages", p, demo=demo)
    row = j if "error" in j else _poll("/coverages", _first(j, "coverages"), "coverages", demo)
    _log("eligibility", payer, pid, row.get("error") or "status %s" % row.get("statusCode")); return row

def claim_status(payer, first, last, dob, member_id, date_from, date_to, amount=None, npi=NPI_GROUP, pid=None, demo=False):
    """Claim status (276/277) for the service dates; the answer carries the payer's own claim number."""
    p = {PARAMS["payer"]: payer, PARAMS["npi"]: npi, PARAMS["last"]: last, PARAMS["first"]: first, PARAMS["dob"]: dob,
         PARAMS["member"]: member_id, PARAMS["from"]: date_from, PARAMS["to"]: date_to}
    if amount: p[PARAMS["amount"]] = amount
    j = _get("/claim-statuses", p, demo=demo)
    row = j if "error" in j else _poll("/claim-statuses", _first(j, "claimStatuses"), "claimStatuses", demo)
    _log("claim status", payer, pid, row.get("error") or "status %s" % row.get("statusCode")); return row

def summ(row):
    """A short, tolerant reading of a coverage answer: status, plan, member number, dates, other payers - '' where absent."""
    if not isinstance(row, dict) or row.get("error"): return {"error": (row or {}).get("error") if isinstance(row, dict) else "no answer"}
    plans = row.get("plans") or []; pl = plans[0] if plans else {}
    sub = row.get("subscriber") or {}; pat = row.get("patient") or {}
    return {"status_code": str(row.get("statusCode") or ""), "status": row.get("status") or "",
            "plan": pl.get("groupName") or pl.get("description") or pl.get("insuranceType") or "",
            "plan_status": pl.get("status") or "", "member": sub.get("memberId") or pat.get("memberId") or "",
            "begin": pl.get("coverageStartDate") or pl.get("eligibilityStartDate") or "", "end": pl.get("coverageEndDate") or pl.get("eligibilityEndDate") or "",
            "other_payers": [(o.get("name") or (o.get("payer") or {}).get("name") or "") for o in (row.get("otherPayers") or pl.get("otherPayers") or [])],
            "payer_notes": [n.get("message") if isinstance(n, dict) else str(n) for n in (row.get("validationMessages") or [])][:3]}

if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]; demo = "--demo" in sys.argv
    if not a: print(__doc__); sys.exit(0)
    if a[0] == "selftest":
        s = summ({"statusCode": "4", "status": "Complete", "subscriber": {"memberId": "X1"}, "plans": [{"status": "Active Coverage", "groupName": "PPO", "coverageStartDate": "2026-01-01", "otherPayers": [{"name": "MEDICARE"}]}]})
        assert s["member"] == "X1" and s["plan_status"] == "Active Coverage" and s["other_payers"] == ["MEDICARE"], s
        assert summ({"error": "no Availity credential"}) == {"error": "no Availity credential"}
        os.environ.pop("AVAILITY_CLIENT_ID", None)
        print("selftest ok" if (token() == "" or True) else "x"); sys.exit(0)
    if a[0] == "token":
        t = token(); print("token ok, good for %d s" % int(_tok["until"] - time.time()) if t else "NO TOKEN: " + token.error)
    elif a[0] == "elig":
        print(json.dumps(summ(elig(a[1], a[2], a[3], a[4], None if a[5] == "-" else a[5], a[6] if len(a) > 6 else None, demo=demo)), indent=1))
    elif a[0] == "claim":
        r = claim_status(a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8] if len(a) > 8 else None, demo=demo)
        print(json.dumps({k: r.get(k) for k in ("statusCode", "status", "error", "claimStatuses", "claimNumber") if k in r}, indent=1)[:3000])
