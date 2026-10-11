# PLAIN ENGLISH (read-only: does chart 17478031 carry a UnitedHealthcare Medicare Advantage plan? - run 2026-10-11T0510Z)
# Decides: nothing in AMD. AMD's 271 on the new Medicare plan named 'HN ... H2509 UNITEDHEALTHCARE OF FLORIDA, INC.' (an HMO Medicare
#   risk contract) beside the QMB entity; this asks Stedi UHC (87726) and the CMS record (with the MBI from patient_db) for the MA plan,
#   its member id and dates, and saves the raw answers under patient_db/17478031/. Prints plan names, dates and whether a member id came
#   back - never the name or the ids.
import stedi, json, sys, time
pid = "17478031"; dos = "20261007"
d = json.load(open("patient_db/%s/demographics_20261006.json" % pid)); j = json.load(open("patient_db/%s/[name]_[DOB].json" % pid))
mbi = j.get("subscriber", {}).get("memberId"); dob = j.get("subscriber", {}).get("dateOfBirth") or d["dob"]
first, last = d["first"], d["last"]
for b in j.get("benefitsInformation", []):
    if b.get("insuranceType") or b.get("insuranceTypeCode") or b.get("benefitsRelatedEntity"):
        print("CMS entity:", b.get("code"), b.get("insuranceTypeCode"), b.get("insuranceType"), b.get("benefitsDateInformation"), (b.get("benefitsRelatedEntity") or {}).get("entityName"))
for payer in ("87726",):
    try:
        e = stedi.elig(payer, first, last, dob, mbi, dos, pid=pid)
        json.dump(e, open("patient_db/%s/stedi_%s_%s.json" % (pid, payer, dos), "w"), indent=1)
        sub = e.get("subscriber", {}); print("UHC", payer, "errors", e.get("errors"), "planStatus", [(p.get("statusCode"), p.get("status"), p.get("planDetails")) for p in e.get("planStatus", [])][:4], "memberId returned:", bool(sub.get("memberId")), "planDates", e.get("planDateInformation"))
        for b in e.get("benefitsInformation", [])[:6]:
            if b.get("code") in ("1", "6"): print("   ", b.get("code"), b.get("insuranceType"), b.get("planCoverage"), b.get("benefitsDateInformation"))
    except Exception as ex:
        print("UHC", payer, "ERR", str(ex)[:200])
    time.sleep(0.5)
