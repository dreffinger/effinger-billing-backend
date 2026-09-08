# PLAIN ENGLISH (Demographics PATCH (REST))
# Decides: Nothing. Writes patient demographic fields (DOB, address) through AMD's newer JSON API, echoing the original record for the concurrency check.
# Rules it uses: Captured from your own UI save on 9/2; sends updatedpatient + originalpatient exactly as the screen does.
# Never touches: Insurance plans, charges.
# ---
"""Demographics write — captured from the UI 9/2/2026 (William's PATCH cURL).
PATCH https://pm-api-103.advancedmd.com/api/demographic/patients/{id}
body = {"updatedpatient": {...flat...}, "originalpatient": {...flat...},
        "updateaccounttype": false, "familyupdate": null, "deleteappointments": false}
Flat address fields: address1, address2, zipcode, city, state, countrycode (NOT nested).
Usage: python3 patient_patch.py <patientid> key=value [key=value ...]
  e.g. python3 patient_patch.py 17477607 dob=1938-09-22"""
import amd, requests, json, sys, copy

H = "https://pm-api-103.advancedmd.com/api/demographic/patients/%s"
ACC = "application/vnd.advancedmd.api.v2+json,application/json"

FLAT_KEYS = ["patient_uid","conversionid","chartnumber","additionalmrn","ssn","dob","inactivestatusfid",
 "statusdate","ispatientactive","pronounsfid","address1","address2","zipcode","city","state","countrycode",
 "previousaddress1","previousaddress2","previouscity","previousstate","previouszipcode","previouscountrycode",
 "previousaddressenddate","languagefid","gender","maritalstatus","sexualorientation","genderidentity",
 "financialclassfid","profilefid","referringproviderfid","officephone","officeextension","homephone","other",
 "phonetype","email","preferredcommunicationfid","confidentialcommunicationfid","timezonefid",
 "hipaarelationshipcode","responsiblepartyfid","employerfid","employername","employmentstatus","names",
 "races","ethnicities","communicationnote","updateaccounttype","familyupdate","tribalentityfid",
 "industryfid","occupationfid"]

def get(pid):
    web, tok = amd.login_cached()
    r = requests.get(H % pid, headers={"Authorization": "Bearer " + tok, "Accept": ACC}, timeout=60)
    r.raise_for_status()
    return r.json()

def flatten(p):
    """Map the nested GET body to the flat shape the UI PATCH sends (captured 9/2/2026)."""
    g = lambda d, k, dflt=None: (d or {}).get(k, dflt)
    addr = p.get("currentaddress") or {}
    prev = p.get("previousaddress") or {}
    ct = p.get("contact") or {}
    emp = p.get("employer") or {}
    o = {
        "patient_uid": p.get("id"), "conversionid": p.get("conversionid"),
        "chartnumber": p.get("chartnumber") or "", "additionalmrn": None,
        "statusdate": p.get("statusdate"), "ispatientactive": p.get("ispatientactive", True),
        "inactivestatusfid": g(p.get("status"), "id"), "ssn": p.get("ssn") or None,
        "dob": p.get("dob"),
        "address1": addr.get("address1") or "", "address2": addr.get("address2") or "",
        "zipcode": addr.get("zipcode") or "", "city": addr.get("city") or "",
        "state": addr.get("state") or "", "countrycode": addr.get("countrycode") or "",
        "previousaddress1": prev.get("address1") or "", "previousaddress2": prev.get("address2") or "",
        "previouscity": prev.get("city") or None, "previousstate": prev.get("state") or None,
        "previouszipcode": prev.get("zipcode") or "", "previouscountrycode": prev.get("countrycode") or None,
        "previousaddressenddate": prev.get("enddate"),
        "gender": p.get("gender"), "maritalstatus": p.get("maritalstatus"),
        "sexualorientation": p.get("sexualorientation"), "genderidentity": p.get("genderidentity"),
        "races": [r["id"] if isinstance(r, dict) else r for r in (p.get("races") or [])],
        "ethnicities": [r["id"] if isinstance(r, dict) else r for r in (p.get("ethnicities") or [])],
        "languagefid": g(p.get("language"), "id"),
        "financialclassfid": g(p.get("financialclass"), "id"),
        "profilefid": g(p.get("providerprofile"), "id"),
        "referringproviderfid": g(p.get("referringprovider"), "id"),
        "officephone": ct.get("officephone") or "", "officeextension": ct.get("officeextension") or "",
        "homephone": ct.get("homephone") or "", "other": ct.get("otherphone"),
        "phonetype": ct.get("phonetype") or "", "email": ct.get("email") or "",
        "communicationnote": ct.get("communicationnote") or "",
        "preferredcommunicationfid": ct.get("preferredcommunicationtype"),
        "confidentialcommunicationfid": ct.get("confidentialcommunicationid"),
        "timezonefid": g(p.get("timezone"), "id"),
        "hipaarelationshipcode": g(p.get("hipaarelationship"), "relationshipcode"),
        "responsiblepartyfid": g(p.get("responsibleparty"), "id"),
        "employerfid": emp.get("id"), "employername": emp.get("name") or "",
        "employmentstatus": emp.get("employmentstatus"),
        "names": p.get("names") or [],
        "pronounsfid": g(p.get("pronouns"), "id"),
        "updateaccounttype": None, "familyupdate": None,
        "tribalentityfid": g(p.get("tribalentity"), "id"),
        "occupationfid": g(p.get("occupation"), "id"), "industryfid": g(p.get("industry"), "id"),
    }
    return o

def patch(pid, changes):
    web, tok = amd.login_cached()
    p = get(pid)
    orig = flatten(p)
    upd = copy.deepcopy(orig)
    upd.update(changes)
    upd["updateaccounttype"] = False
    for n in upd.get("names", []):
        n.setdefault("prefixSuffix", {"prefix": n.get("prefix") or "", "suffix": n.get("suffix") or ""})
    body = {"updatedpatient": upd, "originalpatient": orig,
            "updateaccounttype": False, "familyupdate": None, "deleteappointments": False}
    r = requests.patch(H % pid, json=body, timeout=60,
        headers={"Authorization": "Bearer " + tok, "Accept": ACC, "Content-Type": "application/json"})
    return r.status_code, r.text[:800], p

if __name__ == "__main__":
    pid = sys.argv[1]
    if len(sys.argv) == 2:
        print(json.dumps(get(pid), indent=1)[:4000]); sys.exit()
    ch = {}
    for kv in sys.argv[2:]:
        k, v = kv.split("=", 1); ch[k] = v
    code, txt, before = patch(pid, ch)
    print("PATCH", code, txt)
    after = get(pid)
    for k in ch:
        print(k, "before:", before.get(k), "after:", after.get(k))

def family_address(pid, address1, address2="", zipcode="32308-4486", city="TALLAHASSEE", state="FL", homephone=""):
    """The 'Edit address' button (captured from William's PATCH on MacDonald 9/7/2026): the same PATCH as patch(), but
    familyupdate carries the new address for the responsible party (patientids [0] = this patient), which is what the
    plain PATCH with familyupdate=null was missing ('Address is required')."""
    web, tok = amd.login_cached()
    p = get(pid); orig = flatten(p); upd = copy.deepcopy(orig)
    new = {"address1": address1, "address2": address2, "zipcode": zipcode, "city": city, "state": state, "countrycode": "USA"}
    upd.update(new); upd["updateaccounttype"] = False
    for n in upd.get("names", []):
        n.setdefault("prefixSuffix", {"prefix": n.get("prefix") or "", "suffix": n.get("suffix") or ""})
    body = {"updatedpatient": upd, "originalpatient": orig, "updateaccounttype": False,
            "familyupdate": {"capturepreviousaddress": False, "responsiblepartyid": orig["responsiblepartyfid"], "patientids": [0], "homephone": homephone or orig.get("homephone") or "", "newaddress": new},
            "deleteappointments": False}
    r = requests.patch(H % pid, json=body, timeout=60, headers={"Authorization": "Bearer " + tok, "Accept": ACC, "Content-Type": "application/json", "origin": "https://static-100.advancedmd.com", "referer": "https://static-100.advancedmd.com/"})
    a = (get(pid).get("currentaddress") or {})
    return r.status_code, r.text[:300], {k: a.get(k) for k in ("address1", "address2", "city", "state", "zipcode")}
