# PLAIN ENGLISH (Address line-1 fix for Claimocity-fed charts, captured by probing 9/12/2026 5am ET run)
# Decides: Nothing. Moves the street from address line 2 into line 1 on charts the Claimocity HCA feed created with
#   line 1 BLANK (claims bounce PN3-0107 at the clearinghouse). The 9/7 'Edit address' PATCH answers 500 'Address is
#   required.' on such charts; the shape that saves is: familyupdate.capturepreviousaddress=true, newaddress keeps the
#   line-2 text in address2 as well, and any invalid email on the chart must be blanked first (500 'Email is not a valid
#   format.'). The old email value is printed so it can be kept on the board row (Draycott 9/11: it held a phone number).
# Never touches: insurance, charges. Usage: python3 addr_line1_fix.py <pid> "<street>" <city> <state> <zip> [--dry]
import amd, patient_patch, requests, copy, sys, json
def fix(pid, a1, city, st, z, dry=False):
    web, tok = amd.login_cached()
    p = patient_patch.get(pid); orig = patient_patch.flatten(p)
    cur = {k: orig[k] for k in ("address1", "address2", "city", "state", "zipcode", "email")}
    if (orig.get("address1") or "").strip():
        return "line 1 already set: %s" % orig["address1"], cur
    if dry: return "DRY", cur
    hdr = {"Authorization": "Bearer " + tok, "Accept": patient_patch.ACC, "Content-Type": "application/json",
           "origin": "https://static-100.advancedmd.com", "referer": "https://static-100.advancedmd.com/"}
    # step 1 keeps line 2 exactly as it was (blanking it in the same PATCH answers 'Address is required.'); step 2 clears line 2
    new = {"address1": a1, "address2": orig["address2"], "zipcode": z, "city": city, "state": st, "countrycode": "USA"}
    def body(email_clear):
        u = copy.deepcopy(orig); u.update(new); u["updateaccounttype"] = False
        o = copy.deepcopy(orig)
        if email_clear: u["email"] = ""
        for d in (u, o):
            for n in d.get("names", []): n.setdefault("prefixSuffix", {"prefix": n.get("prefix") or "", "suffix": n.get("suffix") or ""})
        return {"updatedpatient": u, "originalpatient": o, "updateaccounttype": False,
                "familyupdate": {"capturepreviousaddress": True, "responsiblepartyid": orig["responsiblepartyfid"], "patientids": [0], "homephone": orig.get("homephone") or "", "newaddress": new},
                "deleteappointments": False}
    out = []
    for ec in (False, True):
        r = requests.patch(patient_patch.H % pid, json=body(ec), timeout=60, headers=hdr)
        out.append("%s%s" % (r.status_code, "" if r.status_code < 300 else " " + r.text[:80].replace("\n", " ")))
        if r.status_code < 300: break
        if "Email" not in r.text: break
    a = (patient_patch.get(pid).get("currentaddress") or {})
    if (a.get("address1") or "").strip() and (a.get("address2") or "").strip().upper() == a1.strip().upper():
        code, txt, after = patient_patch.family_address(pid, a1, "", z, city, st)   # proven 9/7 shape now that line 1 is filled
        out.append("clear-line2 %s" % code); a = after
    return " | ".join(out), {"before": cur, "after": {k: a.get(k) for k in ("address1", "address2", "city", "state", "zipcode")}}
if __name__ == "__main__":
    a = sys.argv[1:]; print(fix(a[0], a[1], a[2], a[3], a[4], "--dry" in a))
