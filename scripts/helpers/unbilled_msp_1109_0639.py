#!/usr/bin/env python3
# PLAIN ENGLISH (Unbilled 'MSP code required' rows, 06:39Z 11/9 run): three 99309 visits from the 11/8 feed carry Medicare first with
#   UHC Dual Complete behind it ('1,4' / '1,3'). AMD's free 271 on each chart: Medicare names CARE IMPROVEMENT PLUS SOUTH CENTRAL
#   (H1889 = UnitedHealthcare Dual Complete) as the primary MA plan; the chart's UHCMA plan (car302853) answers ACTIVE; the Magellan /
#   WellCare / Staywell plans are REJECTED or INACTIVE. A Medicare Advantage member is never billed to Medicare FFS - the visit order
#   becomes the UHCMA plan alone (full-visit echo, void trap), chart 25558's default order (2,3,1,4 - dead plans first) becomes the
#   UHCMA plan, and the visits are released from Unbilled. No rebill (never billed - they go on the next claim run).
# Usage: python3 unbilled_msp_1109_0639.py [--live]    register registers/unbilled_msp_2026-11-09T0639Z[_dry].json
import sys, json, re, time, amd, resave, ins_update
LIVE = "--live" in sys.argv; STAMP = "2026-11-09T0639Z"
ROWS = [("25558", "19460510", "23373216", "4", "ins9521057", True), ("21020", "19460514", "23373220", "3", "ins9506840", False), ("21020", "19460515", "23373221", "3", "ins9506840", False)]
amd.login_cached(); out = {"stamp": STAMP, "live": LIVE, "rows": []}; released = []
for pid, vid, cid, order, insid, fixdefault in ROWS:
    ok, msg = resave.set_insorder(cid, order, dry=not LIVE); print(pid, vid, msg)
    rec = {"pid": pid, "vid": vid, "order": order, "resave": msg[:200], "ok": ok}
    if LIVE and fixdefault:
        r = ins_update.update(pid, insid, sequence=order); rec["patient_order"] = str(r)[:160]; print("  patient default order", order, str(r)[:120])
    if ok: released.append(vid)
    out["rows"].append(rec); time.sleep(0.4)
if LIVE and released:
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in released)))
    out["release"] = "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:200]); print("release", released, out["release"])
json.dump(out, open("registers/unbilled_msp_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1)
