#!/usr/bin/env python3
# PLAIN ENGLISH: William 11/25/2026 06:39Z on card [name]-17477311-pos-0827: "99223 needs to be changed to hca hospital".
# Visit v19462192 (99223 + 99497, DOS 08/27/2026) came through the feed at POS 31 / nursing facility; Claim Inspector Pattern 4531.
# Fix: full-visit echo (every live charge kept) with facility fac29 (HCA Florida Capital Hospital) and pos 21 on every charge;
# admission date (hospitalizationfrom) = the DOS when the visit carries none (a 99223 is the admission). No rebill here - the
# Claim Inspector re-lists the visit and the run releases it. Usage: python3 atkins_pos_1125.py [--live]
import sys, re, time, json
sys.path.insert(0, "/home/claude/unbilled")
import amd, resave, txh
LIVE = "--live" in sys.argv
PID, VID = "17477311", "19462192"
v = txh.fetch_visit(PID, VID)
cids = [c.get("id") for c in v.iter("charge") if c.get("id")]
print("charges from history:", cids)
cid = str(cids[0]).replace("chg", "")
vis, pat, allc = resave.visit_charges(cid)
print("visit", vis.get("id"), "facility", vis.get("facility"), "charges", [(c.get("id"), c.get("proccode"), c.get("pos"), c.get("begindate")) for c in allc])
ex = vis.find("extins"); print("hospfrom", ex.get("hospitalizationfrom") if ex is not None else None)
chg = ""
for c in allc:
    a = {"id": c.get("id")}
    for f in resave.CHG_FIELDS:
        if c.get(f) is not None: a[f] = c.get(f)
    a["pos"] = "21"
    chg += "<charge %s/>" % " ".join('%s="%s"' % (k, x) for k, x in a.items())
va = dict(vis.attrib); va["force"] = "1"; va["facility"] = "fac29"
if not LIVE:
    print("DRY: would resave visit %s facility fac29, pos 21 on %d charges" % (vis.get("id"), len(allc))); sys.exit(0)
r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
    "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, x) for k, x in va.items()), chg)))
print("FAULT" if "Fault" in r else "saved", re.sub(r"\s+", " ", r[:200]) if "Fault" in r else "")
time.sleep(1); v2, p2, c2 = resave.visit_charges(cid)
print("readback facility", v2.get("facility"), [(c.get("id"), c.get("proccode"), c.get("pos")) for c in c2], "live", len(c2), "of", len(allc))
ex2 = v2.find("extins"); hf = ex2.get("hospitalizationfrom") if ex2 is not None else ""
dos = allc[0].get("begindate")
if (hf or "").strip() != dos:  # the 99223 IS the admission (inspector rule: most recent 99223 on/before the DOS)
    print("admission date", hf, "-> writing", dos, resave.restore_admit(v2.get("id").replace("vst", ""), c2, dos))
