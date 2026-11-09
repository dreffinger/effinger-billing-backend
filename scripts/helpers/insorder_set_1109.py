# PLAIN ENGLISH (Point never-billed visits at a newly added plan, 11/9/2026)
# Decides: Nothing on its own. For each charge id named on the command line it sets that visit's insurance order to the
#          sequence given (full-visit echo, resave.set_insorder) so AMD builds the claim to that plan on the next claim run.
#          Used after a facesheet gives a chart its first insurance plan.
# Rules it uses: resave.set_insorder's own guard - it echoes every live charge, refuses on a Fault and reports when the
#          re-read does not show the new order. No rebill here: these charges have never been billed, so they are originals
#          already and one frequency-1 rebill per visit is freq1_visit's job, not this script's.
# Never touches: A visit that already carries the order (skipped), or any charge not named.
# Usage: python3 insorder_set_1109.py <order> <chargeid> [<chargeid> ...] [--live]
# Register: registers/insorder_set_1109.json
import json, os, sys
import xml.etree.ElementTree as ET
import amd, resave

args = [a for a in sys.argv[1:] if not a.startswith("--")]
ORDER, CIDS = args[0], args[1:]
live = "--live" in sys.argv
amd.login_cached()

out = []
for cid in CIDS:
    root = ET.fromstring(resave.detail(cid))
    c = [x for x in root.iter("charge") if x.get("id") == "charge" + cid]
    v = root.find(".//visit")
    pre = {"proccode": c[0].get("proccode") if c else None, "fee": c[0].get("fee") if c else None,
           "insorder": v.get("insorder"), "visit": v.get("id"), "billdate": c[0].get("datebilled") if c else None}
    ok, msg = resave.set_insorder(cid, ORDER, dry=not live)
    print("chg%s %s vst%s insorder %s -> %s : %s | %s" % (cid, pre["proccode"], pre["visit"], pre["insorder"], ORDER, ok, msg))
    after = None
    if live:
        back = ET.fromstring(resave.detail(cid))
        after = back.find(".//visit").get("insorder")
        print("        re-read insorder:", after)
    out.append({"charge": cid, "before": pre, "ok": ok, "msg": msg, "after": after, "order": ORDER})

if live:
    os.makedirs("registers", exist_ok=True)
    reg = json.load(open("registers/insorder_set_1109.json")) if os.path.exists("registers/insorder_set_1109.json") else []
    reg.extend(out)
    json.dump(reg, open("registers/insorder_set_1109.json", "w"), indent=1)
    print("register -> registers/insorder_set_1109.json")
