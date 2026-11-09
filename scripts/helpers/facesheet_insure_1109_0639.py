#!/usr/bin/env python3
# PLAIN ENGLISH (HCA facesheet drop -> chart 17478346 made claim-ready, 1:39 AM ET 11/9 columns run, fired 06:39Z)
# Decides: nothing new. William dropped the HCA (MedCity) Visit Detail for this chart in Drive 'bht hca facesheets' at 05:43Z:
#   financial class MANAGED CARE MEDICARE, primary insurance AETNA MCR (Aetna Medicare Advantage) policy effective 10/01/2026,
#   group 'State of New Jersey' (no group numbers, ever), hospital authorization <auth>/27447 (the value before the slash), and the
#   patient's DOB [DOB] (age 77) - the feed had created the chart 11/8 with DOB [DOB]. Both 11/6 (99223) and 11/7 (99232)
#   HCA visits sat in Unbilled 'Insurance order is missing' (feed hold 'no active plan: discovery found nothing').
# Does, in order: DOB -> [DOB] (patient_patch PATCH, read-back); add_ins AET07 car6047 with the policy number (begin 10/01/2026,
#   no group); patient default order = the new plan; each visit resaved with the FULL charge echo (void trap) carrying insorder,
#   preauth, onhcfa=1 and hospitalizationfrom 11/06/2026 (the stay's 99223); AMD 271 on the new plan; the two visits released from
#   Unbilled (hideunbillablevisits) ONLY when the 271 answers ACTIVE - otherwise they stay and the report says why.
# Rules it uses: one AMD login (amd.login_cached); member id / auth read from secrets/run_0639_ids.json, never printed; no rebill
#   (the claims have not left yet - they go on the next claim run). Never touches: payments, write-offs, other charts.
# Usage: python3 facesheet_insure_1109_0639.py [--live]   register: registers/facesheet_insure_2026-11-09T0639Z[_dry].json
import sys, re, json, time, amd, add_ins, ins_update, resave, era_post, patient_patch
LIVE = "--live" in sys.argv; STAMP = "2026-11-09T0639Z"
PID = "17478346"; CAR = "car6047"; HOSP = "11/06/2026"
VIS = [("19460523", "23373229"), ("19460531", "23373237")]
ids = json.load(open("secrets/run_0639_ids.json"))
out = {"stamp": STAMP, "pid": PID, "live": LIVE, "steps": []}
def step(k, v): out["steps"].append({k: v}); print(k, "->", (str(v)[:300]))
amd.login_cached()
cur = patient_patch.get(PID)
step("dob_before", cur.get("dob"))
if LIVE and str(cur.get("dob") or "")[:10] != ids["dob"]:
    code, txt, _ = patient_patch.patch(PID, {"dob": ids["dob"]})
    step("dob_patch", "HTTP %s %s" % (code, re.sub(r"\s+", " ", txt)[:120]))
    step("dob_after", patient_patch.get(PID).get("dob"))
plans = re.findall(r'<insplan [^>]*/?>', amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + PID, "nocookie": "1"})))
step("plans_before", len(plans))
if not LIVE:
    step("plan", "DRY: add_ins %s begin %s; patient order = new seq; resave 2 visits insorder/preauth/onhcfa/hospfrom %s; 271; release" % (CAR, ids["begindate"], HOSP))
    for vid, cid in VIS:
        v, p, allc = resave.visit_charges(cid)
        step("visit_%s" % vid, "insorder=%s preauth=%s refplan=%s live_charges=%d" % (v.get("insorder"), v.get("preauth"), v.get("refplan"), len(allc)))
else:
    insid, seq = add_ins.add(PID, CAR, ids["member"], begindate=ids["begindate"])
    step("add_ins", "ins %s seq %s" % (insid, seq))
    r = ins_update.update(PID, insid, sequence=str(seq)); step("patient_order", str(r)[:160]); time.sleep(0.5)
    batch = era_post.batch()
    for vid, cid in VIS:
        v, p, allc = resave.visit_charges(cid)
        chg = ""
        for c in allc:
            a = {"id": c.get("id")}
            for f in resave.CHG_FIELDS:
                if c.get(f) is not None: a[f] = c.get(f)
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, val) for k, val in a.items())
        va = dict(v.attrib); va.update({"force": "1", "insorder": str(seq), "preauth": ids["auth"], "onhcfa": "1"})
        vs = " ".join('%s="%s"' % (k, val) for k, val in va.items())
        r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry",
            {"patientid": p.get("id"), "episodeid": v.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch),
             "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
            "<visit %s><chargelist>%s</chargelist>%s</visit>" % (vs, chg, resave._extins_xml(v, HOSP))))
        if "Fault" in r: step("visit_%s" % vid, "FAULT " + re.sub(r"\s+", " ", r[:300])); continue
        time.sleep(0.8)
        v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
        ok = len(c2) == len(allc) and v2.get("preauth") == ids["auth"] and (v2.get("insorder") or "") == str(seq)
        step("visit_%s" % vid, "saved live=%d/%d insorder=%s preauth_ok=%s onhcfa=%s hospfrom=%s %s" % (len(c2), len(allc), v2.get("insorder"), v2.get("preauth") == ids["auth"], v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None, "OK" if ok else "VERIFY FAILED"))
        out.setdefault("visits_ok", []).append(vid) if ok else None
    try:
        e = amd.check_eligibility(insid); s = json.dumps(e) if not isinstance(e, str) else e
        up = s.upper(); st = "INACTIVE" if "INACTIVE" in up else ("ACTIVE" if "ACTIVE" in up else "see raw")
        aaa = re.findall(r'AAA\*[^*]*\*[^*]*\*(\d+)', s)[:3]; plan = re.findall(r'(?:HMO|PPO|MEDICARE ADVANTAGE|ADVANTAGE)[^"<*~]{0,40}', up)[:2]
        step("amd271", "%s aaa=%s %s" % (st, aaa, plan)); out["elig"] = st
        open("registers/elig271_%s_%s.txt" % (PID, STAMP), "w").write(s)
    except Exception as ex2:
        step("amd271_error", str(ex2)[:200]); out["elig"] = "error"
    if out.get("elig") == "ACTIVE" and len(out.get("visits_ok", [])) == 2:
        r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v, _ in VIS)))
        step("release", "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:200]))
    else:
        step("release", "HELD - 271 %s / visits ok %s" % (out.get("elig"), out.get("visits_ok")))
json.dump(out, open("registers/facesheet_insure_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1)
