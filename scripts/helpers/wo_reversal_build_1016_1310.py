# PLAIN ENGLISH (reversal-pipeline record builder, 9 AM ET 10/16/2026 run 2026-10-16T1310Z) - READ ONLY.
# Decides: nothing. For the check id and visit ids given, reads the cached ERA lines (era_details/<check>.json) and the live chart
#   (gettxhistory) and writes wo_reversal_<today>.json in the shape wo_reversal_post.py reads: a visit the payer PAID whose charges were
#   written off to $0 (no non-void money payment on it) - the write-off ids, codes, amounts and dates come from the live chart.
#   Prints what it found. The voids and the re-post are wo_reversal_post.py's (--dry first). No AMD write here.
import json, sys, datetime, txh
cid = sys.argv[1]; vids = sys.argv[2:]
det = json.load(open("era_details/%s.json" % cid))["eracheckdetails"]
recs = []
for v in det:
    if str(v["visitid"]) not in vids: continue
    root = txh.fetch("pat%s" % v["patientid"])
    chs = [ch for ch in root.iter("charge") if ch.get("visit") == str(v["visitid"]) and ch.get("void") != "1"]
    pays = [(p.get("id"), p.get("amount"), p.get("checknumber")) for ch in chs for p in ch.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
    wos = [(ch.get("id"), w.get("id"), w.get("wocode"), w.get("amount"), w.get("date")) for ch in chs for w in ch.iter("writeoff") if w.get("void") != "1"]
    print("visit", v["visitid"], "pid", v["patientid"], "era pay", v["paymentamount"], "money payments", pays, "writeoffs", wos)
    if pays or not wos: print("   -> skipped (has money payment or no write-off)"); continue
    recs.append({"checkid": cid, "check": None, "carrier": "FLO02", "visitid": v["visitid"], "patientid": v["patientid"], "patient": v["patientname"], "dos": v["dos"][:10],
                 "era_pay": v["paymentamount"], "writeoffs": wos, "fee": sum(float(ch.get("fee") or 0) for ch in chs)})
fn = "wo_reversal_%s.json" % datetime.date.today().strftime("%Y%m%d")
json.dump(recs, open(fn, "w"), indent=1); print(len(recs), "records ->", fn)
