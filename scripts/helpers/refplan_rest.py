# PLAIN ENGLISH (Referral plans - read/write through AMD's REST API, captured 10/5/2026)
# Decides: Nothing about billing. Lists a chart's referral plans, reads one, and edits one - which is how a plan's
#   Pre-Auth # (the auth that prints in box 23 on every visit pointing at the plan) is cleared or corrected from the backend.
# Rules it uses: William captured the Referral Plans screen's Save in Chrome DevTools on 10/5/2026 (chart pat17477777,
#   plan rplan18462071): the screen reads GET /api/referral/inboundreferrals?PatientId=<pid>&ShowExpired=true and
#   GET /api/referral/inboundreferrals/<plan id>, and saves with PUT /api/referral/inboundreferrals carrying the WHOLE plan
#   object - the Pre-Auth # lives in authorizations[].authorizationnumber (plus a singular 'authorization' copy of the
#   edited authorization, and carrierid / facilityid at the top level). Dates go out as yyyy-mm-dd. The XML gateway has
#   no update/delete for referral plans (9/20 probes) - this REST path is the only backend edit. Read back after every
#   write: REST (this module) and XML (getdemographic refplanlist preauth=, or resave.detail's <refplan>).
# Never touches: visits (repoint a visit with the full-echo resave refplan= attr), plans' ownership (always confirm
#   plan.patientid == the chart before writing), balances, charges.
# ---
"""Usage:
  python3 refplan_rest.py list <patientid>                 # every referral plan on the chart (expired included)
  python3 refplan_rest.py get <refplanid>                  # one plan, full JSON
  python3 refplan_rest.py clear <refplanid> <patientid>    # blank every authorizationnumber on the plan (the 10/5 Lazenby fix)
  python3 refplan_rest.py set <refplanid> <patientid> <authnumber>   # write / overwrite the Pre-Auth # (first authorization)
Ids are plain numbers (18462071), with or without the rplan/pat prefixes."""
import amd, requests, json, copy, re, sys

API = "https://pm-api-103.advancedmd.com/api/referral"
def _h():
    web, tok = amd.login_cached()
    return {"Authorization": "Bearer " + tok, "Accept": "application/json", "Content-Type": "application/json"}
def _num(x): return re.sub(r"\D", "", str(x))

def list_plans(pid, show_expired=True):
    """{'totalcount': n, 'items': [plan, ...]} - the list rows carry an EMPTY authorizations[] (proven 10/5); read a plan
    with get() to see its Pre-Auth #."""
    r = requests.get(API + "/inboundreferrals", params={"PatientId": _num(pid), "ShowExpired": "true" if show_expired else "false"}, headers=_h(), timeout=60)
    r.raise_for_status(); return r.json()

def get(rplan):
    r = requests.get(API + "/inboundreferrals/%s" % _num(rplan), headers=_h(), timeout=60)
    r.raise_for_status(); return r.json()

def statuscodes():
    r = requests.get(API + "/statuscodes/0", headers=_h(), timeout=60); r.raise_for_status(); return r.json()

def _ui_body(plan):
    """The PUT body exactly as the Referral Plans screen sends it (captured 10/5/2026): the GET object with dates as
    yyyy-mm-dd, every authorization carrying carrierid, nulls where the screen sends nulls, plus the singular
    'authorization' copy and top-level carrierid / facilityid."""
    b = copy.deepcopy(plan)
    for k in ("effectivedate", "expirationdate"):
        if b.get(k): b[k] = b[k][:10]
    for a in b.get("authorizations") or []:
        a.setdefault("carrierid", None)
        for k in ("warnremainingminutes", "warnremainingvisits", "warnremainingdays"):
            if a.get(k) == 0: a[k] = None
    b["authorization"] = copy.deepcopy(b["authorizations"][0]) if b.get("authorizations") else None
    b.setdefault("carrierid", None); b.setdefault("facilityid", None)
    return b

def put(plan):
    """PUT the whole plan object (use _ui_body on a fresh GET). Returns (status, json-or-text)."""
    r = requests.put(API + "/inboundreferrals", headers=_h(), json=plan, timeout=60)
    try: return r.status_code, r.json()
    except Exception: return r.status_code, r.text[:500]

def set_preauth(rplan, pid, number, dry=False):
    """Write `number` as the plan's Pre-Auth # (every authorization on the plan; '' clears). Refuses a plan that is not the chart's."""
    plan = get(rplan)
    if _num(plan.get("patientid")) != _num(pid):
        raise RuntimeError("plan %s belongs to patient %s, not %s - refusing" % (rplan, plan.get("patientid"), pid))
    before = [(a.get("id"), a.get("authorizationnumber")) for a in plan.get("authorizations") or []]
    if not plan.get("authorizations"):
        return {"before": before, "after": before, "note": "plan has no authorization record - nothing to write (the UI creates one when a Pre-Auth # is typed; that POST is not captured yet)"}
    body = _ui_body(plan)
    for a in body["authorizations"]: a["authorizationnumber"] = number
    body["authorization"] = copy.deepcopy(body["authorizations"][0])
    if dry: return {"before": before, "dry_body": body}
    code, resp = put(body)
    after = get(rplan)
    return {"before": before, "http": code, "after": [(a.get("id"), a.get("authorizationnumber")) for a in after.get("authorizations") or []]}

def clear_preauth(rplan, pid, dry=False): return set_preauth(rplan, pid, "", dry)

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit()
    if a[0] == "list": print(json.dumps(list_plans(a[1]), indent=1))
    elif a[0] == "get": print(json.dumps(get(a[1]), indent=1))
    elif a[0] == "clear": print(json.dumps(clear_preauth(a[1], a[2], "--dry" in a), indent=1))
    elif a[0] == "set": print(json.dumps(set_preauth(a[1], a[2], a[3], "--dry" in a), indent=1))
    elif a[0] == "status": print(json.dumps(statuscodes(), indent=1))
    else: print(__doc__)
