#!/usr/bin/env python3
# PLAIN ENGLISH (contractual settlement on paid lines, 11 PM ET 10/15/2026 run 2026-10-16T0310Z)
# Decides: for a short list of charges where the PRIMARY payer's own payment is already posted with CO45 / CO253
#   reason codes but the contractual was never written off (the insurance balance equals the payer's own CO amounts),
#   writes off exactly that contractual as WOINS - William's standing rule (10/13-10/14/2026: contractual on the payer's
#   own reasons CO45/CO253/CO144 -> WOINS, nothing stays open; PR amounts are NEVER written off - they stay for the
#   secondary or the patient). Found by the UNI20/BCBS pre-5/1 277 pass 111: chart 17472977 v19429034 (UHC paid 1/21/2026)
#   and chart 21577 v19389388 (Medicare paid, the 99232 lines).
# How: re-reads each visit LIVE (payreasons.visit_state), wo = sum(CO45+CO253+CO144 on non-void payments with amount > 0)
#   minus non-void WOINS already posted, capped at the live insurance balance; posts 0.00 payment + WOINS with
#   manual_post.post (a bare write-off, check number PAYREASON1016). --dry (default) prints; --live writes.
# Never touches: payments, PR amounts, any charge not listed, any charge whose live balance differs from the CO sum by
#   more than a cent (listed as HELD instead). Register registers/co45_settle_2026-10-16T0310Z[_dry].json.
import sys, json, time
import amd, payreasons, manual_post
LIVE = "--live" in sys.argv
STAMP = "2026-10-16T0310Z"
TARGETS = [  # (chart, visit, charge, paying carrier code)
    (17472977, 19429034, "23335546", "UNI20"), (17472977, 19429034, "23335547", "UNI20"),
    (21577, 19389388, "22460602", "FLO02"), (21577, 19389388, "22460606", "FLO02"), (21577, 19389388, "22460607", "FLO02"),
]
amd.login_cached()
REG = {"stamp": STAMP, "live": LIVE, "rows": []}
for pid, vid, cid, car in TARGETS:
    st = payreasons.visit_state(pid, vid)
    ch = [c for c in st if str(c["cid"]) == cid]
    row = {"pid": pid, "vid": vid, "cid": cid, "carrier": car}
    if not ch:
        row["outcome"] = "HELD - charge not found live"; REG["rows"].append(row); print(row); continue
    ch = ch[0]
    co = sum(a for p in ch["pays"] if p["void"] == "0" and p["amount"] > 0 for code, a in p["reasons"] if code in ("CO45", "CO253", "CO144"))
    pr = sum(a for p in ch["pays"] if p["void"] == "0" and p["amount"] > 0 for code, a in p["reasons"] if code.startswith("PR"))
    wo_done = sum(w["amount"] for w in ch["wos"] if w["void"] == "0" and w["code"] == "WOINS")
    wo = round(co - wo_done, 2)
    bal = float(ch["insbalance"])
    row.update({"cpt": ch["cpt"], "dos": ch["dos"], "fee": ch["fee"], "paid": ch["paid"], "insbalance": bal, "co": round(co, 2), "pr": round(pr, 2), "woins_already": wo_done, "wo": wo})
    if wo <= 0.005:
        row["outcome"] = "nothing to write off"
    elif abs((bal - pr) - wo) > 0.01:
        row["outcome"] = "HELD - balance %.2f minus PR %.2f != contractual %.2f" % (bal, pr, wo)
    else:
        ok, msg = manual_post.post(cid, car, 0.0, wo, "WOINS", "PAYREASON1016", None,
                                   "contractual CO45/CO253 on %s's own payment - backend billing run %s" % (car, STAMP), dry=not LIVE)
        row["outcome"] = ("posted" if LIVE else "DRY") if ok else "FAILED"; row["msg"] = msg
    print(json.dumps(row)); REG["rows"].append(row); time.sleep(0.4)
json.dump(REG, open("registers/co45_settle_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1, default=str)
print("TOTAL wo %.2f on %d lines (%s)" % (sum(r.get("wo", 0) for r in REG["rows"] if r.get("outcome") in ("posted", "DRY")), sum(1 for r in REG["rows"] if r.get("outcome") in ("posted", "DRY")), "LIVE" if LIVE else "dry"))
