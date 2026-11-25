# PLAIN ENGLISH (Capital Health Plan home and assisted-living visits - William's word of 11/25/2026, board card capital-health-plan-home-visits-1125)
# Decides: nothing. William, in chat 11/25/2026: Capital Health Plan (CAP07) pays this practice out of network for FACILITY visits
#   (hospital, nursing facility) and denies the practice's home / assisted-living visits - "you can write those off or void them".
#   The card asks for a WRITE-OFF (WONCS, non-covered service), never a void, so the visit stays on the chart.
# What it does: (1) masswriteoffsearch on carrier car41826 (CAP07), isinsbalance true, bill dates of the last 3 years = every charge whose
#   open INSURANCE balance sits at Capital Health Plan; (2) keeps the home / assisted-living codes only - 99341 99342 99344 99345 99347
#   99348 99349 99350 (hospital, nursing-facility, care-management 99487/99489 and advance-care-planning lines are NOT touched);
#   (3) per kept charge reads the LIVE charge (resave.detail: carrier, insbalance, paid) - a charge with any non-void payment or a $0
#   balance is listed and skipped; (4) --live: manual_post.post(cid, "CAP07", 0.0, <open balance>, "WONCS", "BOARD1125CHP", None, note)
#   per charge, then reads the charge back ($0). The card gets the list (chart, visit, DOS, CPT, dollars).
# --dry (default) lists only. Register registers/chp_home_visits_2026-11-25T0809Z[_dry].json. Never touches any other carrier or code.
# Usage: python3 chp_home_visits_1125.py [--live]
import amd, resave, manual_post, requests, json, sys, time, datetime
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv; S = "2026-11-25T0809Z"
HOME = {"99341", "99342", "99344", "99345", "99347", "99348", "99349", "99350"}
web, tok = amd.login_cached()
end = datetime.date.today(); start = end - datetime.timedelta(days=3 * 365)
body = {"carrierids": [41826], "isinsbalance": True, "billstartdate": start.isoformat(), "billenddate": end.isoformat(),
        "patientids": None, "providerids": None, "facilityids": None, "financialclassids": None, "dateofservicestartdate": None, "dateofserviceenddate": None}
r = requests.post("https://pm-api-103.advancedmd.com/api/masswriteoff/masswriteoffsearch", json=body,
                  headers={"Authorization": "Bearer " + tok, "Accept": "application/json"}, timeout=180)
r.raise_for_status(); d = r.json(); rows = d.get("chargedetails", []) if isinstance(d, dict) else d
print("CAP07 open insurance balances: %d charges" % len(rows))
# 11/25: CHP's $0 denial of a home visit lands the fee on the PATIENT balance (chart 46678, 10/01/2026): the patient-balance side too
body2 = dict(body); body2["isinsbalance"] = False
r2 = requests.post("https://pm-api-103.advancedmd.com/api/masswriteoff/masswriteoffsearch", json=body2,
                   headers={"Authorization": "Bearer " + tok, "Accept": "application/json"}, timeout=180)
r2.raise_for_status(); d2 = r2.json(); rows2 = d2.get("chargedetails", []) if isinstance(d2, dict) else d2
rows2 = [x for x in rows2 if (x.get("carriercode") or "").strip() == "CAP07"]
print("CAP07 patient balances (last carrier CAP07): %d charges" % len(rows2))
seen = {str(x.get("chargedetailid")) for x in rows}
for x in rows2:
    if str(x.get("chargedetailid")) not in seen: x["_from_patient_side"] = True; rows.append(x)
keep = [x for x in rows if (x.get("chargecode") or "").strip() in HOME]
print("home / assisted-living codes among them: %d" % len(keep))
reg = {"stamp": S, "live": LIVE, "cap07_open_charges": len(rows), "home_rows": []}
for x in keep:
    cid = str(x.get("chargedetailid")); pid = str(x.get("patientid")); vid = str(x.get("visitid"))
    rt = ET.fromstring(resave.detail(cid)); c = [e for e in rt.iter("charge") if e.get("id") == "charge" + cid]
    c = c[0] if c else None
    live_bal = float(c.get("insbalance") or 0) if c is not None else None
    pat_bal = float(c.get("patbalance") or 0) if c is not None else None
    paid = c.get("paid") if c is not None else None
    row = {"pid": pid, "visit": vid, "charge": cid, "dos": x.get("dateofservice"), "cpt": (x.get("chargecode") or "").strip(),
           "list_insbalance": x.get("insbalance"), "live_insbalance": live_bal, "live_patbalance": pat_bal, "live_paid": paid, "carrier": x.get("carriercode"), "action": ""}
    pays = [p for p in rt.iter("payment") if p.get("void") not in ("1", "true") and float(p.get("amount") or 0) != 0]
    if c is not None and (not live_bal or live_bal <= 0) and pat_bal and pat_bal > 0 and not pays:
        # the CHP $0 denial moved the fee to the patient: back to insurance first (move_to_ins.move, no seq, no rebill), then the write-off
        if not LIVE: row["action"] = "DRY - patient balance %.2f (CHP $0 denial): would move_to_ins.move then WONCS %.2f" % (pat_bal, pat_bal)
        else:
            import move_to_ins
            mv = move_to_ins.move(cid); time.sleep(0.8)
            rt = ET.fromstring(resave.detail(cid)); c = [e for e in rt.iter("charge") if e.get("id") == "charge" + cid][0]
            live_bal = float(c.get("insbalance") or 0); row["moved_back"] = "%s -> insbalance %.2f" % (str(mv)[:100], live_bal)
    if row["action"]: pass
    elif c is None or not live_bal or live_bal <= 0: row["action"] = "skip - no open insurance balance on the live charge"
    elif pays: row["action"] = "skip - a payment is posted on the charge (%d)" % len(pays)
    elif not LIVE: row["action"] = "DRY - would write off WONCS %.2f" % live_bal
    else:
        ok, msg = manual_post.post(cid, "CAP07", 0.0, live_bal, "WONCS", "BOARD1125CHP", None, "William 11/25/2026: Capital Health Plan denies home/ALF visits - non-covered, written off (card capital-health-plan-home-visits-1125)")
        time.sleep(0.8)
        rt2 = ET.fromstring(resave.detail(cid)); c2 = [e for e in rt2.iter("charge") if e.get("id") == "charge" + cid][0]
        row["action"] = "WONCS %.2f posted ok=%s %s | read back insbalance %s patbalance %s" % (live_bal, ok, str(msg)[:120], c2.get("insbalance"), c2.get("patbalance"))
    print("  pat%s v%s %s %s %s -> %s" % (pid, vid, row["dos"], row["cpt"], live_bal, row["action"]))
    reg["home_rows"].append(row); time.sleep(0.3)
json.dump(reg, open("registers/chp_home_visits_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
print("register written; rows %d" % len(reg["home_rows"]))
