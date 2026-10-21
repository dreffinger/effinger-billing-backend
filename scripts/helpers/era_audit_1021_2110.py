#!/usr/bin/env python3
# PLAIN ENGLISH (post-Post-button audit, 5 PM ET 10/21/2026 run 2026-10-21T2110Z - READ ONLY)
# Decides: nothing. Two Humana checks were in the ERA Center at 21:21Z (both cached in era_details/ before any Post button ran):
#   1053250 (money: two 99232 lines on chart 17477899, v19456969 / v19457079, paid 70.46 each + CO-45 39.10 / CO-253 1.44)
#   1053249 ($0 NO-PAY: 34 claims / 41 OA-B11 lines on charts 12183413 and 21021 - Medicare-secondary residuals Humana forwarded).
# After GitHub slot #130 / this run's engine pass this helper reads the charts live (txh.fetch) and prints, for every charge named in
#   the cached remit lines, the live payments (amount, check number, carrier, reasons), write-offs, and the insurance / patient
#   balance - so a CO-45-on-the-patient defect or an unposted line is visible. Output registers/era_audit_2026-10-21T2110Z.json
#   (chart / visit / charge ids and dollars only). No AMD write of any kind.
# Usage: python3 era_audit_1021_2110.py
import json, time, txh, amd
S = "2026-10-21T2110Z"; amd.login_cached(); out = []; flags = []
want = {}
for cid in ("1053250", "1053249", "1053247", "1053248"):
    d = json.load(open("era_details/%s.json" % cid)); rows = d.get("eracheckdetails") or d
    for r in rows:
        for c in r.get("charges") or []:
            want[str(c.get("chargedetailid"))] = {"check": cid, "pid": str(r["patientid"]), "vid": str(r["visitid"]), "remit_paid": float(c.get("paymentamount") or 0), "remit_insbal": float(r.get("insurancebalance") or 0),
                                                  "carc": ["%s %.2f" % (x["reasoncode"], x["reasonamt"]) for x in (c.get("carc") or [])]}
for pid in sorted({w["pid"] for w in want.values()}):
    root = txh.fetch(pid)
    for c in root.iter("charge"):
        if c.get("id") not in want or c.get("void") == "1": continue
        w = want[c.get("id")]
        row = {"check": w["check"], "pid": pid, "vid": c.get("visit"), "cid": c.get("id"), "cpt": c.get("proccode"), "dos": c.get("dos"), "fee": c.get("fee"), "paid": c.get("paid"), "insbal": c.get("insbal"), "patbal": c.get("patbal"), "carrier": c.get("carrier"), "billdate": c.get("billdate"),
               "remit_paid": w["remit_paid"], "remit_insbal": w["remit_insbal"], "remit_carc": w["carc"],
               "pays": [{"amt": p.get("amount"), "chk": (p.get("checknumber") or "").strip()[:22], "car": p.get("carrier"), "date": p.get("date"), "reasons": [(r.get("code") or r.get("reasoncode"), r.get("amount")) for r in p.iter() if r.tag.lower().startswith("payreason") and r is not p]} for p in c.iter("payment") if p.get("void") != "1"],
               "wos": [(x.get("amount"), (x.get("wocode") or x.get("code") or "").strip(), x.get("date")) for x in c.iter("writeoff") if x.get("void") != "1"]}
        if float(row["patbal"] or 0) > 0.004: flags.append((row["vid"], row["patbal"], "patient balance"))
        if w["remit_paid"] > 0 and not any(abs(float(p["amt"] or 0)) >= w["remit_paid"] - 0.01 and p["date"] and p["date"].endswith("2026") and p["date"][:5] == "10/21" for p in row["pays"]): flags.append((row["vid"], w["remit_paid"], "money line not yet on the charge with today's date"))
        out.append(row); print(json.dumps(row))
    time.sleep(0.4)
json.dump({"stamp": S, "checks": ["1053250", "1053249", "1053247", "1053248"], "rows": out, "flags": flags}, open("registers/era_audit_%s.json" % S, "w"), indent=1)
print("charges audited", len(out), "of", len(want), "| flags:", flags)
