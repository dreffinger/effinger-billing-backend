# PLAIN ENGLISH (read-only Florida Medicaid 271 by chart, 10/5/2026 shape)
# Decides: nothing. Usage: python3 medicaid271_1015_0710.py <pid> <dos YYYYMMDD>
# Reads the chart's name / DOB / gender / SSN from AMD (getdemographic), asks Florida Medicaid (Stedi 77027) with the
# 10/5/2026 shape (firstName, lastName, dateOfBirth, gender, ssn - no memberId), saves the raw answer to patient_db/<pid>/
# and prints a masked summary (Medicaid id masked, SSN never printed). Never touches: AMD writes.
import amd, stedi, json, os, re, sys, requests
pid, dos = sys.argv[1], sys.argv[2]
pid = pid if pid.startswith("pat") else "pat" + pid
amd.login_cached()
r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
pat = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', r).group(0)))
last, first = (pat.get("name", "").split(",") + [""])[:2]; first = first.strip().split(" ")[0]; last = last.strip()
m = re.match(r"(\d{2})/(\d{2})/(\d{4})", pat.get("dob") or ""); dob = "%s%s%s" % (m.group(3), m.group(1), m.group(2)) if m else None
ssn = (pat.get("ssn") or "").replace("-", ""); sex = (pat.get("sex") or "").strip()[:1].upper()
sub = {"firstName": first, "lastName": last, "dateOfBirth": dob}
if sex: sub["gender"] = sex
if ssn: sub["ssn"] = ssn
body = {"tradingPartnerServiceId": "77027", "provider": stedi.PROV, "subscriber": sub, "encounter": {"dateOfService": dos, "serviceTypeCodes": ["30"]}}
rr = requests.post(stedi.API + "/change/medicalnetwork/eligibility/v3", headers=stedi.H, json=body, timeout=130)
j = rr.json() if rr.content else {}
os.makedirs("patient_db/%s" % pid, exist_ok=True)
json.dump(j, open("patient_db/%s/stedi_elig_77027_%s.json" % (pid, dos), "w"))
def mask(s): s = str(s or ""); return "*" * max(0, len(s) - 4) + s[-4:]
b = j.get("benefitsInformation") or []
out = {"pid": pid, "dos": dos, "http": rr.status_code, "shape": "name+dob+gender+ssn" if ssn else "name+dob+gender",
       "errors": ["%s %s" % (e.get("code"), (e.get("description") or "")[:80]) for e in j.get("errors") or []],
       "medicaid_id": mask((j.get("subscriber") or {}).get("memberId")),
       "planDates": j.get("planDateInformation") or {},
       "active": [(x.get("insuranceTypeCode"), x.get("planCoverage"), x.get("benefitsDateInformation"), [e.get("entityName") for e in x.get("benefitsRelatedEntities") or []]) for x in b if x.get("code") == "1"][:6],
       "inactive_n": len([x for x in b if x.get("code") == "6"]),
       "other_text": [x.get("planCoverage") for x in b if x.get("code") not in ("1", "6") and x.get("planCoverage")][:6]}
print(json.dumps(out, default=str))
