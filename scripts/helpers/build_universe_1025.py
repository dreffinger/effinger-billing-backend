# PLAIN ENGLISH (Rebuild the pay_scan patient universe, nightly cascade 2026-10-25)
# Decides: Nothing. The 9/7 patient_universe_0907.json was lost with the September workspace; this rebuilds the
# patient list pay_scan.py walks from tonight's unpaid list (unpaid_<date>.json from build_money.py) plus any
# claim-status sweep and ERA-detail files present, so the Sunday payment scan can run on a fresh container.
# Never touches: AMD writes.
import json, glob, sys
pids = []
seen = set()
def add(p):
    p = str(p or "").strip()
    if p and p not in seen: seen.add(p); pids.append(p)
for f in sorted(glob.glob("unpaid_2026*.json")):
    for v in json.load(open(f)): add(v.get("patientid"))
for f in sorted(glob.glob("claimstatus_2026*.json")):
    for r in json.load(open(f)): add(r.get("patientid") or r.get("pid"))
for f in glob.glob("era_details/*.json"):
    try:
        for c in json.load(open(f)).get("claims", []) or []: add(c.get("patientid"))
    except Exception: pass
json.dump(pids, open("patient_universe_0907.json", "w"))
print("patient universe rebuilt: %d patients from %d sources" % (len(pids), len(glob.glob("unpaid_2026*.json")) + len(glob.glob("claimstatus_2026*.json"))))
