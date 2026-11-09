# PLAIN ENGLISH (Set a chart's address from a facesheet, 11/9/2026)
# Decides: Nothing. Writes one chart's address through the PATCH shape that AMD actually accepts on a Claimocity-fed
#          chart. Why this script exists: the feed creates new charts with the PLACEHOLDER address 'HCA / HCA,
#          TALLAHASSEE 32308-4486', and a claim with no real subscriber address rejects PN3-0107 at the clearinghouse.
#          patient_patch.family_address (the proven 9/7 'Edit address' shape) answers 500 'Address is required.' on such a
#          chart, and addr_line1_fix only handles a chart whose line 1 is BLANK - a placeholder line 1 is neither case.
#          The shape that saves (9/12 lesson, re-proven here): familyupdate.capturepreviousaddress = true AND newaddress
#          keeps the chart's CURRENT address2 text in the same PATCH; an invalid email on the chart must be blanked first
#          (500 'Email is not a valid format.'). Once line 1 holds the street, a second PATCH clears line 2.
# Rules it uses: Reads the chart back after every step and prints what AMD stored, so a silent refusal cannot pass for success.
# Never touches: Insurance, charges, or any other chart.
# Usage: python3 set_address_1109.py <patientid> "<line1>" "<city>" <state> <zip> [homephone] [--live]
# Register: registers/set_address_1109.json
import copy, json, os, sys
import requests
import amd, patient_patch

args = [a for a in sys.argv[1:] if not a.startswith("--")]
PID, LINE1, CITY, STATE, ZIP = args[0], args[1], args[2], args[3], args[4]
PHONE = args[5] if len(args) > 5 else ""
live = "--live" in sys.argv

web, tok = amd.login_cached()
p = patient_patch.get(PID); orig = patient_patch.flatten(p)
before = {k: orig.get(k) for k in ("address1", "address2", "city", "state", "zipcode", "email", "homephone")}
print("pat%s before: %s" % (PID, before))
print("would set: %s | %s %s %s  phone %s" % (LINE1, CITY, STATE, ZIP, PHONE or "(unchanged)"))
if not live:
    print("DRY"); sys.exit(0)

HDR = {"Authorization": "Bearer " + tok, "Accept": patient_patch.ACC, "Content-Type": "application/json",
       "origin": "https://static-100.advancedmd.com", "referer": "https://static-100.advancedmd.com/"}

def attempt(keep_line2, clear_email):
    """One PATCH. keep_line2: leave the chart's existing address2 in newaddress (the shape AMD accepts)."""
    new = {"address1": LINE1, "address2": (orig.get("address2") or "") if keep_line2 else "",
           "zipcode": ZIP, "city": CITY, "state": STATE, "countrycode": "USA"}
    u = copy.deepcopy(orig); u.update(new); u["updateaccounttype"] = False
    o = copy.deepcopy(orig)
    if clear_email: u["email"] = ""
    for d in (u, o):
        for n in d.get("names", []):
            n.setdefault("prefixSuffix", {"prefix": n.get("prefix") or "", "suffix": n.get("suffix") or ""})
    body = {"updatedpatient": u, "originalpatient": o, "updateaccounttype": False,
            "familyupdate": {"capturepreviousaddress": True, "responsiblepartyid": orig["responsiblepartyfid"],
                             "patientids": [0], "homephone": PHONE or orig.get("homephone") or "", "newaddress": new},
            "deleteappointments": False}
    r = requests.patch(patient_patch.H % PID, json=body, timeout=60, headers=HDR)
    return r.status_code, r.text[:160].replace("\n", " ")

steps = []
for keep_line2 in (True, False):
    for clear_email in (False, True):
        code, txt = attempt(keep_line2, clear_email)
        steps.append("keep_line2=%s clear_email=%s -> %s %s" % (keep_line2, clear_email, code, "" if code < 300 else txt))
        print("   ", steps[-1])
        if code < 300: break
        if "Email" not in txt: break
    else:
        continue
    break

a = (patient_patch.get(PID).get("currentaddress") or {})
after = {k: a.get(k) for k in ("address1", "address2", "city", "state", "zipcode")}
print("address after:", after)
# line 1 now real but line 2 still repeats the placeholder -> clear it with the proven 9/7 shape
if (after.get("address1") or "").strip().upper() == LINE1.strip().upper() and (after.get("address2") or "").strip():
    code, txt, after2 = patient_patch.family_address(PID, LINE1, "", ZIP, CITY, STATE, PHONE)
    print("   clear line 2 ->", code, after2)
    steps.append("clear-line2 %s" % code); after = after2

os.makedirs("registers", exist_ok=True)
reg = json.load(open("registers/set_address_1109.json")) if os.path.exists("registers/set_address_1109.json") else []
reg.append({"pid": PID, "before": before, "after": after, "steps": steps})
json.dump(reg, open("registers/set_address_1109.json", "w"), indent=1)
print("register -> registers/set_address_1109.json")
