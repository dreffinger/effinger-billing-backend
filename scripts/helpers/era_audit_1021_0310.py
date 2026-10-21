# PLAIN ENGLISH (post-Post-button audit of UHC check 1053235 / 00148736497 that GitHub slot #120 posted at 03:32Z 10/21/2026, run 2026-10-21T0310Z - READ ONLY)
# Decides: nothing. The slot's Post button posted the check before any routine cached its claim lines (GET /api/era/checkdetails answers
#   0 rows now). The touched visits were found by diffing the Working Denials snapshots the slots wrote (reports/button/working_denials_latest.json
#   at cce3b7b vs ef37f08): 40 visits' open balances went to 0 on four charts. This helper reads those charts live (txh.fetch) and prints every
#   charge that carries a payment with this check number: fee, paid, insurance / patient balance, the payment's reasons and the write-offs -
#   so the CO-45-on-the-patient defect is visible. Output registers/era_audit_2026-10-21T0310Z.json (chart / visit / charge ids and dollars only). No AMD write.
import json, sys, time, txh, amd
S = "2026-10-21T0310Z"; CHK = "00148736497"; CHARTS = sys.argv[1:] or ["17470940", "17476917", "17471388", "17472732"]
amd.login_cached(); out = []; tot = 0.0; patflag = []
for pid in CHARTS:
    root = txh.fetch(pid)
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        pays = [p for p in c.iter("payment") if CHK in (p.get("checknumber") or "") and p.get("void") != "1"]
        if not pays: continue
        row = {"pid": pid, "vid": c.get("visit"), "cid": c.get("id"), "cpt": c.get("proccode"), "dos": c.get("dos"), "fee": c.get("fee"), "paid": c.get("paid"), "insbal": c.get("insbal"), "patbal": c.get("patbal"), "carrier": c.get("carrier"),
               "pays": [{"amt": p.get("amount"), "car": p.get("carrier"), "date": p.get("date"), "reasons": [(r.get("code") or r.get("reasoncode"), r.get("amount")) for r in p.iter() if r.tag.lower().startswith("payreason") and r is not p]} for p in pays],
               "allpays": [(p.get("amount"), (p.get("checknumber") or "").strip()[:14], p.get("carrier")) for p in c.iter("payment") if p.get("void") != "1"],
               "wos": [(w.get("amount"), (w.get("wocode") or w.get("code") or "").strip(), w.get("date")) for w in c.iter("writeoff") if w.get("void") != "1"]}
        tot += sum(float(p["amt"] or 0) for p in row["pays"])
        if float(row["patbal"] or 0) > 0.004: patflag.append(row)
        out.append(row); print(json.dumps(row))
    time.sleep(0.4)
json.dump({"stamp": S, "check": 1053235, "checknumber": CHK, "rows": out}, open("registers/era_audit_%s.json" % S, "w"), indent=1)
print("lines", len(out), "paid total %.2f" % tot, "| patient balance > 0 on", len(patflag), "lines:", [(r["vid"], r["patbal"]) for r in patflag])
