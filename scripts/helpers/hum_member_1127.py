# PLAIN ENGLISH (nightly cascade 2026-11-27T0535Z): ONE Humana (61101) eligibility call for one chart and prints only the
#   member id Humana echoes back, the plan name and dates - so the Humana MA plan can be added with Humana's own number.
# Usage: python3 hum_member_1127.py <patientid> <first> <last> <yyyymmdd dob> <member id sent> <yyyymmdd dos>
import sys, json, stedi
pid, first, last, dob, mid, dos = sys.argv[1:7]
j = stedi.elig("61101", first, last, dob, mid, dos, pid=pid)
s = j.get("subscriber") or {}
print(json.dumps({"memberId": s.get("memberId"), "groupNumber": s.get("groupNumber"),
                  "plan": [x.get("planDetails") for x in j.get("planStatus") or [] if x.get("planDetails")],
                  "dates": j.get("planDateInformation"), "payer": (j.get("payer") or {}).get("name"),
                  "refs": [(r.get("referenceIdentificationQualifier"), r.get("referenceIdentification")) for r in (s.get("additionalIdentification") and [s["additionalIdentification"]] or [])]}, indent=1))
