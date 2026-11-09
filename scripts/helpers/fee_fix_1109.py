# PLAIN ENGLISH (Fee correction after a procedure recode, 11/9/2026)
# Decides: Nothing on its own. A recode done with recode.swap_proc keeps the OLD code's fee, because the full-visit echo
#          carries fee / allowed / expected / insportion / insbalance unchanged (found 11/9/2026 on Lewis chg23351281:
#          99306 -> 99309 left the charge at the 99306 fee of 256.00 while every real 99309 on the chart is 141.00).
#          This sets one charge's fee to the correct fee-schedule amount and rebills the visit as an original claim, so the
#          claim and the A/R carry the right number.
# Rules it uses: Full-visit echo; refuses a charge that carries a payment or a write-off (the money would no longer balance).
# Never touches: Any other charge on the visit - only the id named on the command line.
# Usage: python3 fee_fix_1109.py <chargeid> <newfee> <rebillseq> [--live]
# Register: registers/fee_fix_1109.json
import json, os, re, sys, time
import xml.etree.ElementTree as ET
import amd, resave, freq1_visit

args = [a for a in sys.argv[1:] if not a.startswith("--")]
CID, NEWFEE, SEQ = args[0], float(args[1]), args[2]
live = "--live" in sys.argv
amd.login_cached()

vis, pat, allc = resave.visit_charges(CID)
target = [c for c in allc if c.get("id") == "charge" + CID]
if not target:
    print("charge%s is not live on the visit" % CID); sys.exit(1)
t = target[0]
root = ET.fromstring(resave.detail(CID))
c0 = [c for c in root.iter("charge") if c.get("id") == "charge" + CID][0]
pays = [p.attrib for p in c0.iter("payment") if float(p.attrib.get("amount") or 0) != 0]
wos = [w.attrib for w in c0.iter("writeoff") if float(w.attrib.get("amount") or 0) != 0]
print("charge%s %s fee %s allowed %s insbalance %s" % (CID, c0.get("proccode"), c0.get("fee"), c0.get("allowed"), c0.get("insbalance")))
if pays or wos:
    print("REFUSED - money is posted on this charge; fix it by hand:", pays, wos); sys.exit(1)
print("would set fee / allowed / expected / insportion / insbalance to %.2f and rebill sequence %s" % (NEWFEE, SEQ))
if not live:
    print("DRY"); sys.exit(0)

chg = ""
for c in allc:
    a = {"id": c.get("id")}
    for f in resave.CHG_FIELDS:
        if c.get(f) is not None: a[f] = c.get(f)
    if c.get("id") == "charge" + CID:
        for k in ("fee", "allowed", "insportion", "insbalance"):
            if k in a: a[k] = "%.2f" % NEWFEE
    chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
va = dict(vis.attrib); va["force"] = "1"
r = amd.post(amd.msg("updvisitwithcharges", "chargeentry",
                     {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                      "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                     "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
time.sleep(0.8)
print("save:", "FAULT " + re.sub(r"\s+", " ", r[:300]) if "Fault" in r else "ok")
vid = re.sub(r"\D", "", vis.get("id"))
print("rebill:", freq1_visit.run(vid, CID, SEQ))

back = ET.fromstring(resave.detail(CID))
cb = [c for c in back.iter("charge") if c.get("id") == "charge" + CID][0]
after = {k: cb.get(k) for k in ("proccode", "fee", "allowed", "expected", "insportion", "insbalance")}
print("AFTER", after)
os.makedirs("registers", exist_ok=True)
reg = json.load(open("registers/fee_fix_1109.json")) if os.path.exists("registers/fee_fix_1109.json") else []
reg.append({"charge": CID, "newfee": NEWFEE, "seq": SEQ, "after": after})
json.dump(reg, open("registers/fee_fix_1109.json", "w"), indent=1)
print("register -> registers/fee_fix_1109.json")
