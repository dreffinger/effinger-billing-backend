# PLAIN ENGLISH (Claim Inspector 'send' on William's word - 10/11/2026 03:30Z board note on chart 20863: "send")
# Decides: nothing new. Re-lists inspector batch 127783 (error ids change on every re-inspection), finds visit 19455936
#   (99306 + 99497 9/17/2026, $389) and, when EVERY error on it is the Medicare CCI Pattern 24078 hold William said to send
#   through (his First Coast reopening of the paid 99233 -> 99239 is his side), bypasses exactly those fresh error ids with
#   bypassclaimedits so the claim goes to Medicare on the next claim run. Any other error on the visit = held, nothing written.
# Never touches: diagnosis codes, modifiers, dates, plans, payments, any other visit.
#   python3 insp_send_1011.py          # dry
#   python3 insp_send_1011.py --live   # register registers/insp_send_2026-10-11T0510Z.json
import amd, json, re, sys, time
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv; S = "2026-10-11T0510Z"; BATCH = "127783"; VID = "19455936"; PATTERN = "24078"
amd.login_cached()
t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": BATCH, "nocookie": "1"}), timeout=120)
rec = {"stamp": S, "live": LIVE, "batch": BATCH, "vid": VID, "pattern": PATTERN, "found": False}
for v in ET.fromstring(t).iter("visit"):
    if v.get("id") != VID: continue
    rec["found"] = True; rec["pid"] = v.get("patientid")
    errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:200]) for e in v.iter("error")]
    rec["errs"] = errs
    only = bool(errs) and all(("Pattern " + PATTERN) in e[1] for e in errs)
    rec["only_pattern"] = only
    if not only: rec["bypassed"] = "held - another error on the visit"
    elif not LIVE: rec["bypassed"] = "dry"
    else:
        r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (VID, "".join('<claimedit id="%s"/>' % e[0] for e in errs))))
        rec["bypassed"] = "Fault" not in r; rec["resp"] = re.sub(r"\s+", " ", r[:200])
        time.sleep(0.8)
        t2 = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": BATCH, "nocookie": "1"}), timeout=120)
        rec["still_listed"] = any(v2.get("id") == VID for v2 in ET.fromstring(t2).iter("visit"))
print(json.dumps(rec))
json.dump(rec, open("registers/insp_send_%s.json" % S, "w"), indent=1)
