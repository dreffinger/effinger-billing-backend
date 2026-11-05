#!/usr/bin/env python3
# PLAIN ENGLISH (run 2026-11-05T0040Z): chart 17469446's 16 Humana 'POLICY CANCELED' 277 rejections on claim run 1700349 -
#   the 2025 Medicare-paid residuals William re-routed to Humana Medicaid on 11/2 ("Humana Medicaid"). Humana says the policy
#   was not in force on those 2025 dates, so the Medicaid-family plan of the period cannot be billed; William's own order on
#   this chart (v19409077, 11/2: "'write off' (WOCAID2ND, dual residual)") settles the same kind of line.
# Decides per live charge (payreasons.visit_state - the primary's payment must be on the charge, patient balance 0):
#   contractual = Medicare CO45 + CO253 minus non-void WOINS already posted -> WOINS (capped to the open insurance balance);
#   the rest of the open insurance balance (= the PR2 coinsurance) -> WOCAID2ND. Never over-apply; nothing on the patient.
#   LESSON 11/5: post the WOCAID2ND before the WOINS - a WOINS first moved the PR2 remainder to the PATIENT balance (fixed with move_to_ins + repost).
# Then excl_complete.py completes the 16 rows. --dry prints the plan; --live posts.  Register registers/excl_dual_settle_<stamp>.json
import sys, json, time, payreasons, manual_post
LIVE = "--live" in sys.argv
STAMP = "2026-11-05T0040Z"
pid = "17469446"
vids = ['19402245','19402644','19403418','19403945','19404635','19404697','19405084','19405500','19406109','19407286','19407974','19408949','19413644','19415101','19416084','19417133']
plan = []
for v in vids:
    for ch in payreasons.visit_state(pid, v):
        bal = round(float(ch["insbalance"] or 0), 2)
        if ch.get("patbalance"): print("PATBAL", v, ch["cid"], ch["patbalance"]); 
        if bal <= 0: plan.append({"vid": v, "cid": ch["cid"], "cpt": ch["cpt"], "dos": ch["dos"], "outcome": "already $0"}); continue
        med = [p for p in ch["pays"] if p["void"] == "0" and p["carrier"] == "FLO02"]
        if not med: plan.append({"vid": v, "cid": ch["cid"], "cpt": ch["cpt"], "dos": ch["dos"], "outcome": "HOLD no Medicare payment"}); continue
        contr = sum(a for p in med for code, a in p["reasons"] if code in ("CO45", "CO253", "CO144"))
        pr = sum(a for p in med for code, a in p["reasons"] if code.startswith("PR"))
        wo_done = sum(w["amount"] for w in ch["wos"] if w["void"] == "0" and w["code"].startswith("WOINS"))
        woins = round(min(max(contr - wo_done, 0.0), bal), 2)
        caid = round(bal - woins, 2)
        plan.append({"vid": v, "cid": ch["cid"], "cpt": ch["cpt"], "dos": ch["dos"], "insbal": bal, "pr": round(pr, 2), "woins": woins, "wocaid2nd": caid, "outcome": "plan"})
tot_i = sum(p.get("woins", 0) for p in plan); tot_c = sum(p.get("wocaid2nd", 0) for p in plan)
for p in plan: print(json.dumps(p))
print("PLAN: %d charges, WOINS %.2f, WOCAID2ND %.2f, total %.2f" % (len([p for p in plan if p["outcome"]=="plan"]), tot_i, tot_c, tot_i + tot_c))
if LIVE:
    faults = 0
    for p in plan:
        if p["outcome"] != "plan": continue
        for code, amt, car in (("WOCAID2ND", p["wocaid2nd"], "HUM01"), ("WOINS", p["woins"], "FLO02")):
            if amt <= 0: continue
            try:
                r = manual_post.post(p["cid"], car, 0.0, amt, code, "EXCL1105", None, "run %s: Humana Medicaid 277 'policy canceled' on the 2025 dual residual - %s per William 11/2 (v19409077 precedent)" % (STAMP, code))
                p.setdefault("posted", []).append({"code": code, "amt": amt, "r": str(r)[:160]}); faults = 0
            except Exception as e:
                p.setdefault("errors", []).append("%s %s: %s" % (code, amt, str(e)[:200])); faults += 1
                print("FAULT", p["vid"], code, amt, str(e)[:200])
                if faults >= 3: print("STOP after 3 consecutive faults"); break
            time.sleep(0.4)
        if faults >= 3: break
json.dump(plan, open("registers/excl_dual_settle_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1)
