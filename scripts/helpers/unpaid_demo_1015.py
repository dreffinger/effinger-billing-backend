# PLAIN ENGLISH (unpaid-list chart plans snapshot, chat 10/15/2026 - the aging summary needs to know who has a live secondary)
# Decides: nothing. READ-ONLY. For every patient on the unpaid list, reads getdemographic once and keeps the insurance plans
#   (plan id, carrier id, sequence, begin/end dates, eligibility status id) plus the patient's insorder, deceased flag and
#   DOB year - never a name, SSN or member number. One JSON per patient: patient_db/<pid>/plans_1015.json. Resumable.
# Never touches: AMD writes.
import json, os, re, sys, time
import xml.etree.ElementTree as ET
sys.path.insert(0, "/home/claude/unbilled")
import amd
WS = "/home/claude/unbilled"
rows = json.load(open(os.path.join(WS, "unpaid_raw_1015.json")))
pids = sorted({str(r["patientid"]) for r in rows}, key=int)
LOG = open(os.path.join(WS, "logs", "unpaid_demo_1015.log"), "a")
amd.login_cached()
done = 0
for i, pid in enumerate(pids, 1):
    out = os.path.join(WS, "patient_db", pid, "plans_1015.json")
    if os.path.exists(out): continue
    try:
        x = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}))
        root = ET.fromstring(x.encode("latin-1", "ignore"))
        p = root.find(".//patient"); a = p.attrib if p is not None else {}
        plans = [{k: v for k, v in i_.attrib.items() if k in ("id", "carrier", "sequence", "begindate", "enddate", "coverage", "eligibilitystatusid", "hipaarelationship", "relationship", "finclass")} for i_ in root.iter("insplan")]
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump({"pid": pid, "insorder": a.get("insorder"), "deceased": a.get("deceased"), "dob_year": (a.get("dob") or "")[-4:], "plans": plans}, open(out, "w"))
        done += 1
        LOG.write(json.dumps({"pid": pid, "plans": len(plans), "n": i, "of": len(pids)}) + "\n"); LOG.flush()
    except Exception as e:
        LOG.write(json.dumps({"pid": pid, "err": str(e)[:200], "n": i}) + "\n"); LOG.flush(); time.sleep(2)
    time.sleep(0.2)
LOG.write(json.dumps({"done": done, "patients": len(pids)}) + "\n"); LOG.flush()
print("DONE", done, "of", len(pids))
