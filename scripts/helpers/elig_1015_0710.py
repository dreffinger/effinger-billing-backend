# PLAIN ENGLISH (read-only payer eligibility checks for the 2026-10-15T0710Z run)
# Decides: nothing. Two Stedi 271 reads for the two new HCA charts whose insurance discovery answered this run:
#   chart 17478061 - discovery named a Humana Medicare PPO (active since 02/01/2024): ask Humana (61101) with the
#     discovery member id read from patient_db/ at run time (never on the command line, never printed).
#   chart 17478063 - discovery found no medical coverage (a MetLife row with placeholder dates): ask Florida Medicaid
#     (77027) with the 10/5/2026 shape - firstName, lastName, dateOfBirth, gender, ssn from the AMD chart, no memberId.
# Raw answers go to patient_db/<pid>/; the printed summary masks every id. Never touches: AMD writes.
import amd, stedi, json, os, re, sys, time, requests
amd.login_cached()

def demo(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    pat = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', r).group(0)))
    return pat

def ymd(mdy):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", mdy or ""); return "%s%s%s" % (m.group(3), m.group(1), m.group(2)) if m else None

def mask(s): s = str(s or ""); return "*" * max(0, len(s) - 4) + s[-4:]

def summ(j):
    b = j.get("benefitsInformation") or []
    act = [x for x in b if x.get("code") == "1"]; inact = [x for x in b if x.get("code") == "6"]
    return {"errors": ["%s %s" % (e.get("code"), (e.get("description") or "")[:80]) for e in j.get("errors") or []],
            "active_n": len(act), "inactive_n": len(inact),
            "planDates": j.get("planDateInformation") or {},
            "active_plans": [(x.get("insuranceTypeCode"), x.get("insuranceType"), x.get("planCoverage"), x.get("benefitsDateInformation")) for x in act][:4],
            "entities": sorted({e.get("entityName") for x in b for e in (x.get("benefitsRelatedEntities") or []) if e.get("entityName")})[:6],
            "subscriber_member": mask((j.get("subscriber") or {}).get("memberId"))}

out = {}
# ---- chart 17478061: Humana 61101 with the discovery member id
pid = "pat17478061"; dos = "20261012"
try:
    pat = demo(pid); last, first = (pat.get("name", "").split(",") + [""])[:2]; first = first.strip().split(" ")[0]; last = last.strip()
    d = json.load(open("patient_db/%s/stedi_disc_%s.json" % (pid, dos)))
    member = next(((it.get("subscriber") or {}).get("memberId") for it in d.get("items") or [] if "HUMANA" in ((it.get("payer") or {}).get("name") or "").upper()), None)
    hic = next(((it.get("planInformation") or {}).get("hicNumber") for it in d.get("items") or [] if (it.get("planInformation") or {}).get("hicNumber")), None)
    r = stedi.elig("61101", first, last, ymd(pat.get("dob")), member, dos, pid=pid)
    json.dump(r, open("patient_db/%s/stedi_elig_61101_%s.json" % (pid, dos), "w"))
    out[pid] = {"humana_61101": summ(r), "discovery_member": mask(member), "discovery_mbi": mask(hic)}
except Exception as e:
    out[pid] = {"error": str(e)[:300]}
time.sleep(0.5)
# ---- chart 17478063: Florida Medicaid 77027, 10/5 shape (name, DOB, gender, SSN; no memberId)
pid = "pat17478063"
try:
    pat = demo(pid); last, first = (pat.get("name", "").split(",") + [""])[:2]; first = first.strip().split(" ")[0]; last = last.strip()
    ssn = (pat.get("ssn") or "").replace("-", ""); sex = (pat.get("sex") or "").strip()[:1].upper()
    sub = {"firstName": first, "lastName": last, "dateOfBirth": ymd(pat.get("dob"))}
    if sex: sub["gender"] = sex
    if ssn: sub["ssn"] = ssn
    body = {"tradingPartnerServiceId": "77027", "provider": stedi.PROV, "subscriber": sub, "encounter": {"dateOfService": dos, "serviceTypeCodes": ["30"]}}
    rr = requests.post(stedi.API + "/change/medicalnetwork/eligibility/v3", headers=stedi.H, json=body, timeout=130)
    j = rr.json() if rr.content else {}
    json.dump(j, open("patient_db/%s/stedi_elig_77027_%s.json" % (pid, dos), "w"))
    out[pid] = {"medicaid_77027": summ(j), "http": rr.status_code, "shape": "name+dob+gender+ssn" if ssn else "name+dob+gender (chart has no SSN)"}
except Exception as e:
    out[pid] = {"error": str(e)[:300]}
json.dump(out, open("registers/elig_1015_0710.json", "w"), indent=1, default=str)
print(json.dumps(out, default=str))
