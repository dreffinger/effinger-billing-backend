#!/usr/bin/env python3
# PLAIN ENGLISH (two demographics corrections from the hospital / nursing sheets William pasted on the board 11/25/2026 07:19-07:26Z)
# Decides: whether the correction William's sheet gives is the one Medicare holds - AdvancedMD's free Medicare check (271) must
#   answer ACTIVE once the chart carries it; anything else and the old value goes back and the card says so.
#   chart 17476479: Medicare answered 71 (birth date does not match) on 11/20; the sheet's subscriber DOB is [DOB]
#     (the chart held another year). Patch dob; on ACTIVE re-route the one Medicare-paid visit the card names (v19452652,
#     08/31/2026 99487+99489, Medicare coinsurance 44.09 still at Medicare) to the Medigap plan UNI01 seq 2 - ONE re-route.
#   chart 17473945: Medicare answered 73 (name does not match); the sheet spells the surname with one letter more than the chart had.
#     Patch the billing name's lastname; on ACTIVE keep it. The coinsurance 17.65 on v19418640 stays where it is - its secondary is
#     AET12 (Aetna Senior Supplemental), whose carrier record still transmits the TIN (standing hold aet12-carrier-cpid).
# Rules it uses: patient_patch.patch = the captured demographics PATCH (read-before-write, originalpatient echoed); elig_amd.run_plan
#   = the free 271; freq1_visit.reroute = no-rebill full-visit echo + ONE frequency-1 reset + ONE chargerebill.
# 07:5xZ addendum: Medicare answered INACTIVE with a DATE OF DEATH once each chart matched (both charts): the match
#   is the proof, the correction is kept and the date goes into the deceased cache; neither chart carries a charge after its date (read first).
# Never touches: other fields, other charts, paid lines, the Aetna plan. Usage: NEW_DOB=<yyyy-mm-ddT00:00:00> NEW_LASTNAME=<name> python3 facesheet_fix_1125d.py [--live]  (the values ran 11/25 from William's sheets; they are not kept in this file)
import amd, patient_patch, elig_amd, freq1_visit, json, sys, copy, os
LIVE = "--live" in sys.argv
STAMP = "2026-11-25T0721Z"
JOBS = [
    {"pid": "17476479", "ins": "ins9517767", "field": "dob", "new": os.environ.get("NEW_DOB", "[DOB]"), "reroute": ("19452652", "23363023", "1,2", 2)},
    {"pid": "17473945", "ins": "ins9515257", "field": "lastname", "new": os.environ.get("NEW_LASTNAME", "[NAME]"), "reroute": None},
]
amd.login_cached(); out = {"stamp": STAMP, "live": LIVE, "jobs": []}
for j in JOBS:
    pid = j["pid"]; rec = {"pid": pid, "field": j["field"]}
    p = patient_patch.get(pid); f = patient_patch.flatten(p)
    if j["field"] == "dob":
        old = f.get("dob"); changes = {"dob": j["new"]}
    else:
        names = copy.deepcopy(f.get("names") or []); old = [n.get("lastname") for n in names]
        for n in names: n["lastname"] = j["new"]
        changes = {"names": names}
    rec["before"] = old; print("pat%s %s before: %s -> would write %s" % (pid, j["field"], old, j["new"]))
    if not LIVE:
        print("  DRY - patch, 271 on %s, keep on ACTIVE else restore; reroute %s" % (j["ins"], j["reroute"])); out["jobs"].append(rec); continue
    code, txt, _ = patient_patch.patch(pid, changes); rec["patch"] = [code, str(txt)[:160]]; print("  PATCH", code, str(txt)[:160])
    f2 = patient_patch.flatten(patient_patch.get(pid))
    rec["after"] = f2.get("dob") if j["field"] == "dob" else [n.get("lastname") for n in (f2.get("names") or [])]; print("  after:", rec["after"])
    s = elig_amd.run_plan(pid, j["ins"], force=True); rec["271"] = elig_amd.one_line(s)[:240]; print("  271:", rec["271"])
    dod = s.get("date_of_death")
    if s.get("status") == "ACTIVE" or dod:
        # 11/25/2026 07:5xZ: Medicare answered INACTIVE with a date of death the moment the chart matched its record - the correction IS
        # right (Medicare identified the person); keep it, record the date of death for the deceased guard, void nothing here (no charge on
        # either chart is dated after the death - read before this run), and say so on the card.
        rec["outcome"] = "kept - Medicare ACTIVE" if not dod else "kept - Medicare identifies the chart; INACTIVE, date of death %s" % dod
        if dod:
            import deceased_guard; deceased_guard._put(pid, {"dod": dod, "src": "AMD 271 %s" % STAMP, "at": STAMP}); rec["dod"] = dod
        if j["reroute"]:
            vid, cid, order, seq = j["reroute"]; r = freq1_visit.reroute(vid, cid, order, seq); rec["reroute"] = str(r)[:300]; print("  reroute v%s ->" % vid, r)
    else:
        if j["field"] == "dob": back = {"dob": old}
        else:
            names = copy.deepcopy(f2.get("names") or []);
            for n, o in zip(names, old): n["lastname"] = o
            back = {"names": names}
        c2, t2, _ = patient_patch.patch(pid, back); rec["outcome"] = "restored - Medicare %s (%s)" % (s.get("status"), rec["271"]); print("  restored", c2, str(t2)[:100])
    print("  OUTCOME:", rec["outcome"]); out["jobs"].append(rec)
json.dump(out, open("registers/facesheet_fix_%s.json" % STAMP, "w"), indent=1)
