#!/usr/bin/env python3
# PLAIN ENGLISH (chart 17477648 - the SurgeryPlus plan William entered as a carrier, and the three September hospital visits, 11/25/2026)
# Decides: nothing. William on card prescot-marisa-17477648 (11/25 08:19Z): 'i entered it as a payer and put bill paper'. The carrier is on
#   AdvancedMD's list now: car307813, code SUR99, name SURGERYPLUS (no clearinghouse payer id - paper). His hospital sheet on the card gives
#   the policy number [member id], effective 08/25/2026, no authorization required. This adds that plan to the chart (no group number - the
#   standing rule), makes it the chart's insurance order (the UMR plan stays on the chart, unordered - UMR answered 'entity not eligible'
#   and its subscriber is another person), then re-routes the three visits with the one-rebill re-route (visit insorder by the no-rebill
#   full-visit echo, ONE frequency-1 reset + ONE chargerebill to the new plan). Refuses to add a second SurgeryPlus plan when one is there.
# Never touches: payments, write-offs, other charts. Usage: python3 prescot_surgeryplus_1018.py [--live]   (dry by default)
# Register: registers/prescot_surgeryplus_<stamp>.json
import amd, add_ins, ins_update, freq1_visit, txh, re, json, sys, os, time, datetime
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv
PID = "17477648"; CAR = "car307813"; POLICY = "2797898050"; BEGIN = "08/25/2026"
VISITS = [("19453782", "23364678"), ("19453773", "23364668"), ("19453753", "23364646")]
stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ"); os.makedirs("registers", exist_ok=True)
rec = {"stamp": stamp, "live": LIVE, "pid": PID, "carrier": CAR, "steps": []}
amd.login_cached()
def plans():
    d = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"})))
    p = d.find(".//patient")
    return p.get("insorder"), [(i.get("id"), i.get("sequence"), i.get("carrier"), i.get("enddate")) for i in d.iter("insplan")]
order, pl = plans(); print("chart order", order, "plans", pl); rec["before"] = {"order": order, "plans": pl}
have = [x for x in pl if x[2] == CAR and not x[3]]
root = txh.fetch(PID)
for vid, cid in VISITS:
    c = next((x.attrib for x in root.iter("charge") if x.get("id") == cid), None)
    pays = [p.attrib for p in next(x for x in root.iter("charge") if x.get("id") == cid).iter("payment") if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0]
    print("visit", vid, "charge", cid, c.get("dos"), c.get("proccode"), "carrier", c.get("carrier"), "billdate", c.get("billdate"), "insbal", c.get("insbal"), "paid", pays)
    if pays: print("REFUSED - a payment sits on the charge"); sys.exit(2)
if have:
    insid, seq = have[0][0], have[0][1]; print("SurgeryPlus plan already on the chart:", have[0]); rec["steps"].append({"plan": "already", "ins": insid, "seq": seq})
elif not LIVE:
    print("DRY: would add %s policy ***%s begin %s (no group), set the chart order to the new plan, re-route %d visits to it" % (CAR, POLICY[-4:], BEGIN, len(VISITS)))
    json.dump(rec, open("registers/prescot_surgeryplus_%s.json" % stamp, "w"), indent=1); sys.exit(0)
else:
    insid, seq = add_ins.add(PID, CAR, POLICY, BEGIN, "1", "CC")
    print("add_ins ->", insid, seq); rec["steps"].append({"plan": "added", "ins": insid, "seq": seq})
    if not insid or not str(seq).isdigit(): print("STOP - the plan was not added"); json.dump(rec, open("registers/prescot_surgeryplus_%s.json" % stamp, "w"), indent=1); sys.exit(2)
    time.sleep(1)
if LIVE:
    r = ins_update.update(PID, insid, sequence=str(seq)); print("chart order ->", r); rec["steps"].append({"order": str(r)})
    order2, pl2 = plans(); print("chart order now", order2); rec["after_order"] = order2
    if str(order2).split(",")[0] != str(seq): print("WARNING - the chart order did not take; stop before the visits"); json.dump(rec, open("registers/prescot_surgeryplus_%s.json" % stamp, "w"), indent=1); sys.exit(2)
for vid, cid in VISITS:
    r = freq1_visit.reroute(vid, cid, str(seq), str(seq), dry=not LIVE); print("visit", vid, "->", r); rec["steps"].append({"visit": vid, "charge": cid, "reroute": str(r)[:300]})
    time.sleep(0.5)
if LIVE:
    root = txh.fetch(PID)
    rec["readback"] = [{"charge": x.get("id"), "carrier": x.get("carrier"), "billdate": x.get("billdate"), "insbal": x.get("insbal")} for x in root.iter("charge") if x.get("id") in {c for _, c in VISITS}]
    print("read back:", rec["readback"])
json.dump(rec, open("registers/prescot_surgeryplus_%s.json" % stamp, "w"), indent=1); print("register: registers/prescot_surgeryplus_%s.json" % stamp)
