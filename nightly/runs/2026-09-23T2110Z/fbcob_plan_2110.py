# PLAIN ENGLISH (Florida Blue secondary COB - plan, 5pm ET 9/23/2026 run 2026-09-23T2110Z): for the 2026 lines of the CO-252 / MA04 group
#   whose Medicare payment (check 819814877, 9/19/2026) carries reason codes, read: the charge's LAST-BILLED carrier + bill date (gettxhistory),
#   the visit's insorder / extins (getchargedetaildataicd10) and the chart's plans (getdemographic) to find the Florida Blue sequence.
#   Prints a per-visit plan: RESEND (freq-1 on the Florida Blue sequence) when the secondary was last billed BEFORE the Medicare posting
#   or never billed to Florida Blue; HOLD-REPORT when it was billed after the posting (the adjudication was already on the claim).
# Never touches: AMD writes (dry / plan only).
import amd, txh, resave, json, time, re, sys
import xml.etree.ElementTree as ET
STAMP = "2026-09-23T2110Z"
V = {"17473086": ["19420894", "19417565"], "17476090": ["19438064"],
     "17472195": ["19433890", "19433413", "19430677", "19427221", "19421063", "19442312", "19420521"],
     "17469028": ["19423587", "19427201", "19442293"]}
plan = []
for pid, vids in V.items():
    root = txh.fetch(pid); time.sleep(0.3)
    dem = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": str(pid), "nocookie": "1"}))); time.sleep(0.3)
    plans = [(ip.get("sequence"), ip.get("carrier"), ip.get("carriercode") or ip.get("carriername") or "", ip.get("enddate") or "", ip.get("id")) for ip in dem.iter("insplan")]
    print("pat%s plans %s" % (pid, plans))
    for vid in vids:
        chs = [c for c in root.iter("charge") if c.get("void") != "1" and str(c.get("visit")).replace("vst", "") == vid]
        cid = chs[0].get("id").replace("chg", "") if chs else None
        d = ET.fromstring(resave.detail(cid)) if cid else None; time.sleep(0.3)
        vis = d.find(".//visit") if d is not None else None
        insorder = vis.get("insorder") if vis is not None else None
        ext = d.find(".//extins") if d is not None else None
        row = {"pid": pid, "vid": vid, "cid": cid, "charges": [(c.get("id"), c.get("proccode"), c.get("carrier"), c.get("billdate"), c.get("insbal")) for c in chs],
               "insorder": insorder, "resub": ext.get("resubmissioncode") if ext is not None else None, "origref": ext.get("origrefnum") if ext is not None else None}
        print("  v%s cid %s charges %s insorder %s resub %s origref %s" % (vid, cid, row["charges"], insorder, row["resub"], row["origref"]))
        plan.append(row)
json.dump(plan, open("registers/fbcob_plan_%s.json" % STAMP, "w"), indent=1)
