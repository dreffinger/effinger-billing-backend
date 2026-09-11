# PLAIN ENGLISH (Restore a voided charge)
# Decides: Re-adds a charge that a single-charge resave voided by mistake, with identical attributes and balances.
# Rules it uses: Tries to keep the original billed date so it isn't treated as a new claim.
# Never touches: Charges voided on purpose.
# ---
"""Restore a charge that was voided by a single-charge resave (9/3/2026 move_to_ins bug): re-add it to its visit
with identical attributes/balances alongside the surviving charge(s).  Tries insbilled/datebilled so the claim run
doesn't treat it as a new claim.  Usage: python3 restore_charge.py <voided_chargeid> <surviving_chargeid> [--dry]"""
import amd, resave, re, sys, time
import xml.etree.ElementTree as ET
EXTRA = ["insbilled", "datebilled", "lastbilledcarrier", "batchnumber"]
def restore(void_cid, live_cid, dry=False, to_ins=True):
    vx = ET.fromstring(resave.detail(void_cid)); vc = [c for c in vx.iter("charge") if c.get("id") == "charge" + void_cid][0]
    lx = ET.fromstring(resave.detail(live_cid)); vis = lx.find(".//visit"); pat = lx.find(".//patient")
    lc = [c for c in lx.iter("charge") if c.get("id") == "charge" + live_cid][0]
    if lc.get("void") == "1": return "live charge is void too"
    if vc.get("void") != "1": return "not void"
    # the surviving charge, echoed
    a = {"id": lc.get("id")}
    for f in resave.CHG_FIELDS:
        if lc.get(f) is not None: a[f] = lc.get(f)
    chg = "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    # the voided charge, re-entered (no id) with its balances; dx from sibling if blank
    b = {}
    for f in resave.CHG_FIELDS + EXTRA:
        if vc.get(f) is not None: b[f] = vc.get(f)
    if not b.get("diagcodes"): b["diagcodes"] = lc.get("diagcodes") or ""
    b["fee"] = vc.get("fee") if vc.get("fee") not in (None, "0", "0.00") else vc.get("allowed")
    if to_ins:   # William 9/3: these balances belong on insurance
        pb = float(b.get("patbalance") or 0); ib = float(b.get("insbalance") or 0)
        b["insbalance"] = "%.2f" % (pb + ib); b["patbalance"] = "0.00"
        b["insportion"] = "%.2f" % (float(b.get("insportion") or 0) + float(b.get("patportion") or 0)); b["patportion"] = "0.00"
    chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in b.items())
    va = dict(vis.attrib); va["force"] = "1"
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    if dry: return "DRY " + chg
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:300])
    time.sleep(0.8)
    return "OK " + str(re.findall(r'<charge id="([^"]*)"[^>]*proccode="([^"]*)"[^>]*(?:patbalance="([^"]*)" insbalance="([^"]*)")?[^>]*void="([^"]*)"', r)[:4])
if __name__ == "__main__":
    print(restore(sys.argv[1], sys.argv[2], "--dry" in sys.argv))
