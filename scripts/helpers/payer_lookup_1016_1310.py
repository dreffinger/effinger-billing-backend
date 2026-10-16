# PLAIN ENGLISH (payer eligibility by name/DOB, 9 AM ET [DOB] run 2026-10-16T1310Z) - READ ONLY (Stedi only).
# Decides: nothing. Asks one Stedi payer (e.g. 87726 UnitedHealthcare) for a patient by first/last/DOB at a date of service
#   WITHOUT a member id (RULE C 10/14: UHC / Humana / FL Medicaid answer by name/DOB) and prints plan status, the member id the
#   payer returns, plan names/dates and any AAA errors; saves the raw answer under patient_db/<pid>/. No AdvancedMD write.
# Usage: python3 payer_lookup_1016_1310.py <pid> <payer> FIRST LAST YYYYMMDD YYYYMMDD
import stedi, json, sys, os
pid, payer, first, last, dob, dos = sys.argv[1:7]
j = stedi._post(stedi.API + "/change/medicalnetwork/eligibility/v3", {"tradingPartnerServiceId": payer, "provider": stedi.PROV,
      "subscriber": {"firstName": first, "lastName": last, "dateOfBirth": dob}, "encounter": {"dateOfService": dos, "serviceTypeCodes": ["30"]}})
os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_%s_%s.json" % (pid, payer, dos), "w"), indent=1)
sub = j.get("subscriber") or {}
print("planStatus", j.get("planStatus")); print("errors", j.get("errors")); print("memberId", sub.get("memberId"), "name", sub.get("firstName"), sub.get("lastName"))
print("planDates", j.get("planDateInformation"))
for b in (j.get("benefitsInformation") or [])[:12]:
    if b.get("code") in ("1", "6") or b.get("planCoverage") or b.get("insuranceType"):
        print("  ", b.get("code"), b.get("name"), b.get("insuranceTypeCode"), b.get("insuranceType"), b.get("planCoverage"), b.get("benefitsDateInformation"), [e.get("entityName") for e in b.get("benefitsRelatedEntities") or []])
