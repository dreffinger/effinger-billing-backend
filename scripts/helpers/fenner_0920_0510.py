# PLAIN ENGLISH (1am ET 9/20/2026 run, 2026-09-20T0510Z): William's board note 04:52Z on row fenner-maude-20379 - "write these off the humana secondary amounts".
# Decides: (1) posts a WOINS write-off (Payment Entry addpayments via manual_post, pay 0) for every open HUM01 (Humana Medicaid-MMA
#   secondary) residual on chart pat20379 - the Medicare-coinsurance crossover lines Humana denied CO185/N767 (rendering provider not
#   enrolled in FL Medicaid); balances read live, never over-applied. (2) the chart's two new HCA 99233 visits (9/17, 9/18) that sit in
#   Unbilled 'Insurance order is missing': primary-dx gate, admission 09/16/2026 (the 99223 of the same stay), insorder 1 (Medicare, as the
#   9/16 visit), onhcfa 1 full-visit echo, then hideunbillablevisits. Register: registers/fenner_0920_0510.json
# Never touches: any other chart, any charge with a $0 Humana balance.
import amd, resave, manual_post, dx_primary_fix, json, re, time, sys
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
amd.login_cached()
PID = "20379"; NOTE = "Humana Medicaid-MMA crossover residual written off per William 9/20/2026 (CO185/N767 - WOINS) run 2026-09-20T0510Z"
WO = ["23361174", "23361324", "23361618", "23363228", "23362630", "23362631", "23363902"]
reg = {"stamp": "2026-09-20T0510Z", "writeoffs": [], "visits": []}
def L(m): print(m, flush=True)
for cid in WO:
    rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
    bal = float(c.get("insbalance") or 0); car = c.get("carrier") or ""
    rec = {"chargeid": cid, "insbalance_before": bal, "carrier": car}
    if bal <= 0: rec["outcome"] = "skip - balance already 0"; L("%s skip bal 0" % cid); reg["writeoffs"].append(rec); continue
    if DRY: rec["outcome"] = "DRY would WOINS %.2f" % bal; L("%s DRY WOINS %.2f" % (cid, bal)); reg["writeoffs"].append(rec); continue
    ok, msg = manual_post.post(cid, "HUM01", 0.0, bal, "WOINS", checknumber="", depositdate=None, note=NOTE)
    time.sleep(0.6)
    rt2 = ET.fromstring(resave.detail(cid)); c2 = [x for x in rt2.iter("charge") if x.get("id") == "charge" + cid][0]
    rec.update({"ok": ok, "resp": str(msg)[:160], "wo": bal, "insbalance_after": float(c2.get("insbalance") or 0), "patbalance_after": float(c2.get("patbalance") or 0)})
    rec["outcome"] = "posted WOINS %.2f" % bal if ok and rec["insbalance_after"] == 0 else "CHECK"
    L("%s WOINS %.2f -> ok=%s insbal after %.2f %s" % (cid, bal, ok, rec["insbalance_after"], str(msg)[:100]))
    reg["writeoffs"].append(rec); time.sleep(0.5)
L("write-offs total %.2f" % sum(r.get("wo", 0) for r in reg["writeoffs"]))
# (2) the two new Unbilled visits
def set_date(vid, code, admit):
    return amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
        '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
def full_resave(cid, over):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(over)
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    return ("Fault" not in r), "live=%d/%d insorder=%s onhcfa=%s hospfrom=%s" % (len(c2), len(allc), v2.get("insorder"), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None) if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:200])
for vid, cid in (("19455112", "23366251"), ("19455126", "23366265")):
    rec = {"vid": vid, "cid": cid, "steps": []}
    det = resave.detail(cid); dmap = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', det))
    vis, pat, allc = resave.visit_charges(cid); codes = [dmap.get(x, x) for x in (allc[0].get("diagcodes") or "").split()]
    bad = bool(codes) and dx_primary_fix.never_primary(codes[0]); rec["dx"] = codes; rec["steps"].append("dx %s never_primary(first)=%s" % (codes, bad))
    if bad: rec["steps"].append("HOLD - primary dx needs the cascade (not run automatically here)"); L("v%s dx %s HOLD" % (vid, codes)); reg["visits"].append(rec); continue
    if DRY: rec["steps"].append("DRY"); reg["visits"].append(rec); L("v%s DRY dx ok %s" % (vid, codes)); continue
    r = set_date(vid, "99233", "09/16/2026"); rec["steps"].append("admit 09/16/2026 -> %s" % ("ok" if "Fault" not in r else "FAULT " + r[:120]))
    ok, m = full_resave(cid, {"insorder": "1", "onhcfa": "1"}); rec["steps"].append("resave insorder 1 onhcfa 1 -> %s" % m)
    if ok:
        xml = amd.call('action="hideunbillablevisits" class="claimsreports" hide="-1" nocookie="1"', '<visitlist><visit id="%s"/></visitlist>' % vid)
        rel = 'success="1"' in xml or '<Error/>' in xml or '<Error />' in xml
        rec["steps"].append("released=%s %s" % (rel, re.sub(r"\s+", " ", xml)[:120]))
    L("v%s %s" % (vid, " | ".join(rec["steps"]))); reg["visits"].append(rec); time.sleep(0.5)
json.dump(reg, open("registers/fenner_0920_0510.json", "w"), indent=1)
L("=== fenner done")
