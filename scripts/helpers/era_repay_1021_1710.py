#!/usr/bin/env python3
# PLAIN ENGLISH (ERA re-pay lines the fallback skipped as 'reversal', 1 PM ET 10/21/2026 run 2026-10-21T1710Z).
# Florida Blue check 1053245 (trace 423830695) holds $58.80 the GitHub slot's Post button left unvalidated: three claims where Florida Blue
#   REVERSED an earlier $0 / deductible adjudication and RE-PAID the Medicare coinsurance (OA-23 lines) - v19438715 99497 $13.35 (chart 21411),
#   v19451186 99309 $16.93 (chart 21308), v19453037 99309 $16.93 (chart 17471131) - plus v19456195 $11.59 on a charge already at $0 (residual,
#   disregarded per William's 9/13 rule). era_fallback_0913b.py classed the three as 'reversal' because each visit also carries a reversal
#   claim; the reversed adjudications had paid $0, so nothing is taken back and the re-pay is new money with no payment on the charge yet.
# Decides: posts each line through the ERA-LINKED Payment Entry shape (payreasons.post_line, pay = min(remit paid, open insurance balance),
#   wo = the line's CO adjustments capped so pay + wo <= balance, WOINS) after re-reading the live charge; skips a charge that already carries a
#   non-void payment with this trace number. --dry prints the plan only. Register registers/era_repay_<stamp>.json. Stops after 3 faults.
# Usage: python3 era_repay_1021_1710.py [--dry]
import json, sys, time, re, os
import xml.etree.ElementTree as ET
import amd, payreasons, resave
S = "2026-10-21T1710Z"; CHK = 1053245; TRN = "423830695"; dry = "--dry" in sys.argv
LINES = [  # (checkclaimid, chargedetailid, remit paid)
    (15447308, 23345986, 13.35), (15447320, 23361186, 16.93), (15447312, 23363452, 16.93)]
amd.login_cached(); d = payreasons.details(CHK); out = []; faults = 0
for ccid, cid, paid in LINES:
    v = [x for x in d["eracheckdetails"] if x["checkclaimid"] == ccid][0]
    ch = [c for c in v.get("charges", []) if abs(float(c.get("paymentamount") or 0) - paid) < 0.005][0]
    ch = dict(ch); ch["chargedetailid"] = int(cid)
    rt = ET.fromstring(resave.detail(str(cid))); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + str(cid)][0]
    bal = float(c.get("insbalance") or 0)
    pays = [p for p in c.iter("payment") if p.get("void") != "1" and TRN in (p.get("checknumber") or "")]
    pay, wo, code, resid = payreasons.line_amounts(ch, bal)
    rec = {"checkid": CHK, "checkclaimid": ccid, "visitid": v["visitid"], "pid": v["patientid"], "cid": cid, "cpt": c.get("proccode"), "dos": c.get("dos"), "insbalance": bal, "remit_paid": paid, "pay": pay, "wo": wo, "wocode": code, "residual": resid, "when": S}
    if pays: rec["outcome"] = "already-posted"
    elif pay <= 0: rec["outcome"] = "residual-zero"
    elif dry: rec["outcome"] = "DRY"
    else:
        try:
            chk = payreasons.check_meta(CHK, v)
            ok, payid, msg = payreasons.post_line(v["patientid"], v["visitid"], chk, v, cid, ch, pay=pay, wo=wo, wocode=code)
        except Exception as e: ok, payid, msg = False, "", str(e)
        rec.update(outcome="posted" if ok else "fault", paymentid=payid, msg=msg[:160]); faults = 0 if ok else faults + 1
    print(json.dumps(rec)); out.append(rec); time.sleep(0.4)
    if faults >= 3: print("3 consecutive faults - stop"); break
os.makedirs("registers", exist_ok=True)
json.dump(out, open("registers/era_repay_%s%s.json" % (S, "_dry" if dry else ""), "w"), indent=1)
if not dry:
    R = "registers/era_manual_register.json"; reg = json.load(open(R)) if os.path.exists(R) else []
    reg += [{"checkid": r["checkid"], "checkclaimid": r["checkclaimid"], "visitid": r["visitid"], "chargeid": r["cid"], "outcome": r["outcome"] if r["outcome"] != "residual-zero" else "residual %.2f" % r["residual"], "when": S} for r in out]
    json.dump(reg, open(R, "w"), indent=1)
