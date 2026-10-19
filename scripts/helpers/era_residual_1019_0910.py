# PLAIN ENGLISH (5 AM ET 10/19/2026 run 2026-10-19T0910Z - ehpa cloud copy)
# One Medicare-coinsurance residual left by the ERA Center Post button on Humana ACH 203602886261018 (check 1053210):
#   chart 20937 v19425168 c23331134 (99497 11/30/2025, fee 133): Medicare 818255226 paid 48.46 (CO45 71.19 / PR2 12.36 / CO253 0.99,
#   WOINS 72.18 posted 5/28/2026); Humana (the Medicaid MMA secondary) answered CO-185 $0 on 5/30/2026 and again $0 today on this check
#   (era_post's over-apply guard posted the check's 29.81 on the visit's other charge and a 0.00 payment here, no write-off). The 12.36
#   PR-2 is 'coinsurance a Medicaid-family plan answered short of the PR total' -> WOCAID2ND (William 10/13-10/14 rule; 9/23, 10/14,
#   10/18 precedents). The remit line is no longer readable (AMD's checkdetails drops a claim once it is posted), so the write-off goes
#   through manual_post.post as a $0 payment + WOCAID2ND carrying the Humana check number and date - the v13 payment-reason settlement shape.
# Decides: nothing new. --dry (default) re-reads the charge live and prints the plan; --live writes when the live insurance balance is
#   exactly the expected residual (12.36) and the patient balance is 0; anything else is HELD and listed. Stops on the first fault.
# Register: registers/era_residual_2026-10-19T0910Z[_dry].json + registers/era_manual_register.json (live).
# Never touches: payments, plans, claims, rebills, any other charge.
import amd, manual_post, txh, json, sys, time
a = sys.argv; DRY = "--live" not in a; S = "2026-10-19T0910Z"
LINES = [("20937", "19425168", "23331134", 12.36, "HUM01", "203602886261018", "10/17/2026", "WOCAID2ND")]
def L(m): print(m, flush=True)
amd.login_cached()
def live(pid, vid, cid):
    root = txh.fetch_visit(pid, vid)
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("id").replace("charge", "") != cid: continue
        return {"insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "cpt": c.get("proccode"), "fee": c.get("fee"), "carrier": c.get("carrier"),
                "pays": [((p.get("checknumber") or "").strip(), p.get("void"), p.get("amount"), p.get("carrier"), [(r.get("code"), r.get("amount")) for r in p.iter("payreason")]) for p in c.iter("payment")],
                "wos": [(w.get("wocode"), w.get("amount"), w.get("void")) for w in c.iter("writeoff")]}
out = {"stamp": S, "dry": DRY, "lines": []}
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
for pid, vid, cid, expect, carrier, chk, dep, wocode in LINES:
    s = live(pid, vid, cid); r = {"pid": pid, "visitid": vid, "chargedetailid": cid, "expect": expect, "before": s}
    if not s: r["outcome"] = "skip - charge not live"
    elif any(w[0] == wocode and w[2] != "1" for w in s["wos"]): r["outcome"] = "already-posted (a live %s is on the charge)" % wocode
    elif abs(s["insbal"] - expect) > 0.009 or s["patbal"] > 0: r["outcome"] = "HELD - live ins %.2f pat %.2f differs from the expected residual %.2f" % (s["insbal"], s["patbal"], expect)
    elif DRY: r["outcome"] = "DRY would post pay 0.00 + %s %.2f under %s check %s" % (wocode, expect, carrier, chk)
    else:
        res = manual_post.post(cid, carrier, 0.0, expect, wocode, checknumber=chk, depositdate=dep, note="ERA 1053210 dual residual %s" % S)
        time.sleep(0.7); s2 = live(pid, vid, cid) or {}
        r.update(resp=str(res)[:200], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
        r["outcome"] = "posted" if (s2.get("insbal") == 0 and s2.get("patbal") == 0) else "FAULT - after ins %s pat %s" % (s2.get("insbal"), s2.get("patbal"))
    L("v%s c%s %s" % (vid, cid, r["outcome"])); out["lines"].append(r)
json.dump(out, open("registers/era_residual_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r["outcome"].startswith("posted"):
            reg.append({"checkid": "1053210", "checkclaimid": None, "visitid": r["visitid"], "chargedetailid": r["chargedetailid"], "outcome": "posted", "pay": 0.0, "wo": r["expect"], "wocode": "WOCAID2ND", "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
