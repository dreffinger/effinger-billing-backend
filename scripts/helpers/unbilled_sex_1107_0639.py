# PLAIN ENGLISH (1:39 AM ET 11/7 slot, run 2026-11-07T0639Z - ehpa cloud): applies the standing Unbilled rule for
#   'Subscriber sex is invalid for insurance coverage' (10/5/2026 precedent act_1005_0510.py W1): the chart's sex is set from an
#   authoritative record - here Medicare's own eligibility answer through Stedi (subscriber.gender) - with the captured demographics
#   PATCH, read back, and only then the held visits are released from Unbilled (hideunbillevisits). Writes registers/unbilled_sex_<stamp>.json
#   (chart id, visit ids, before/after - no names). Never touches charges, plans or the responsible party title.
import amd, patient_patch, payreasons, stedi, json, time, sys
STAMP = "2026-11-07T0639Z"; amd.login_cached()
pid, visits, dob = "46439", ["19460324", "19460338"], "19590108"
reg = {"stamp": STAMP, "pid": pid, "steps": []}
def log(*a): print(*a, flush=True); reg["steps"].append(" ".join(str(x) for x in a))
j = stedi.mbi("CHERILYN", "HARCOURT", dob, state="FL", dos="20261105", pid=pid)
sub = j.get("subscriber") or {}; g = sub.get("gender")
summ = stedi.med_summ(j)
log("stedi medicare record gender", g, "| MA entities:", [o for o in (summ.get("other") or []) if o], "| death", summ.get("death"))
if g not in ("F", "M"): log("no gender on the Medicare record - stop"); json.dump(reg, open("registers/unbilled_sex_%s.json" % STAMP, "w"), indent=1); sys.exit(0)
code, txt, before = patient_patch.patch(pid, {"gender": g})
after = patient_patch.flatten(patient_patch.get(pid))
log("gender PATCH", code, txt[:100], "before", before.get("gender"), "after", after.get("gender"))
if after.get("gender") == g:
    time.sleep(0.5)
    for v in visits:
        ok, msg = payreasons.release_visit(v); log("release", v, ok, str(msg)[:120]); time.sleep(0.3)
json.dump(reg, open("registers/unbilled_sex_%s.json" % STAMP, "w"), indent=1)
