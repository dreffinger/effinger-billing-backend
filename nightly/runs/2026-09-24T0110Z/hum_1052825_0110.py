# PLAIN ENGLISH (ERA denial lines, Humana check 1052825 / 200815298260923, run 2026-09-24T0110Z): every $0 line on the check is a Humana
#   SECONDARY answer on a Medicare-paid nursing-home line: CO-185/N767 (rendering provider not enrolled in FL Medicaid - William 9/20:
#   WOINS the Humana secondary amounts), OA-23 (prior payer adjudication - a dual crossover paying $0 on Medicare coinsurance = contractual
#   write-off, WOCAID2ND when the Humana plan is the Medicaid MMA line of business, WOINS when it is Humana MA), OA-18 (duplicate, already $0).
# Decides: for each $0 charge line read the LIVE charge (resave.detail); skip when the insurance balance is already 0 or no prior non-void
#   payment is on the charge; else post the ERA line ERA-linked through payreasons.post_line (pay 0, write-off = min(adjustment, open balance),
#   reason codes kept). Register registers/hum_1052825_2026-09-24T0110Z.json. --dry first.
# Never touches: paid lines, any other check, patient balances.
import amd, resave, payreasons, elig_amd, json, re, sys, time
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv; STAMP = "2026-09-24T0110Z"; CID = "1052825"
amd.login_cached()
chk = [c for c in json.load(open("era_checks_before_%s.json" % STAMP)) if str(c["id"]) == CID][0]
det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]
reg = {"stamp": STAMP, "checkid": CID, "lines": []}
plancache = {}
def hum_kind(pid):
    if pid not in plancache:
        a, pl = elig_amd.plans(pid)
        hum = [p for p in pl if p.get("carrier") in ("car6285", "car302851")]
        ids = [p.get("subscribernum", "") for p in hum]
        plancache[pid] = ("MMA" if any(re.fullmatch(r"\d{10}", x or "") for x in ids) else "MA", ids)
    return plancache[pid]
def L(m): print(m, flush=True)
for v in det:
    pid = str(v["patientid"]); vid = str(v["visitid"])
    for ch in v.get("charges", []):
        if float(ch.get("paymentamount") or 0) > 0: continue
        cid = str(ch["chargedetailid"]); carcs = ["%s%s" % (r["payreasongroup"], r["reasoncode"]) for r in ch.get("carc", [])]
        rec = {"visitid": vid, "patientid": pid, "chargeid": cid, "cpt": ch["chargecode"], "dos": ch["dos"][:10], "carcs": carcs, "adj": ch.get("adjustmentamount")}
        rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
        bal = float(c.get("insbalance") or 0); pbal = float(c.get("patbalance") or 0)
        prior = [(p.get("id"), p.get("amount"), p.get("checknumber"), p.get("carrierfid")) for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) > 0]
        rec.update({"insbalance": bal, "patbalance": pbal, "prior_payments": prior})
        if bal <= 0: rec["outcome"] = "skip - insurance balance already 0"; L("v%s %s %s bal 0 - skip" % (vid, cid, carcs)); reg["lines"].append(rec); continue
        if any("OA18" in x for x in carcs): rec["outcome"] = "skip - duplicate (OA-18), original adjudication stands"; L("v%s %s OA18 bal %.2f - skip" % (vid, cid, bal)); reg["lines"].append(rec); continue
        if not prior: rec["outcome"] = "HOLD - no prior payment on the charge (not a secondary residual)"; L("v%s %s %s bal %.2f NO PRIOR PAYMENT - hold" % (vid, cid, carcs, bal)); reg["lines"].append(rec); continue
        kind, ids = hum_kind(pid)
        if any("CO185" in x for x in carcs): code = "WOINS"; why = "CO-185/N767 Humana Medicaid secondary - William 9/20 WOINS"
        elif any("OA23" in x for x in carcs): code = "WOCAID2ND" if kind == "MMA" else "WOINS"; why = "OA-23 dual crossover $0 on Medicare coinsurance (Humana %s)" % kind
        else: rec["outcome"] = "HOLD - unhandled CARC %s" % carcs; L("v%s %s %s HOLD unhandled" % (vid, cid, carcs)); reg["lines"].append(rec); continue
        wo = round(min(bal, sum(float(r["reasonamt"]) for r in ch.get("carc", []))), 2)
        rec.update({"wocode": code, "wo": wo, "why": why, "humana_ids": ids})
        if DRY: rec["outcome"] = "DRY would post $0 + %s %.2f" % (code, wo); L("v%s pat%s %s %s bal %.2f -> DRY %s %.2f (%s)" % (vid, pid, ch["chargecode"], carcs, bal, code, wo, why)); reg["lines"].append(rec); continue
        ok, payid, head = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=0.0, wo=wo, wocode=code)
        time.sleep(0.6)
        rt2 = ET.fromstring(resave.detail(cid)); c2 = [x for x in rt2.iter("charge") if x.get("id") == "charge" + cid][0]
        rec.update({"ok": ok, "paymentid": payid, "resp": head[:160], "insbalance_after": float(c2.get("insbalance") or 0), "patbalance_after": float(c2.get("patbalance") or 0)})
        rec["outcome"] = ("posted $0 + %s %.2f" % (code, wo)) if ok else "FAULT"
        L("v%s pat%s %s %s bal %.2f -> %s %.2f ok=%s after ins %.2f pat %.2f %s" % (vid, pid, ch["chargecode"], carcs, bal, code, wo, ok, rec["insbalance_after"], rec["patbalance_after"], head[:100]))
        reg["lines"].append(rec); time.sleep(0.4)
json.dump(reg, open("registers/hum_1052825_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
L("=== %s: %d lines; %s" % ("DRY" if DRY else "LIVE", len(reg["lines"]), {k: sum(1 for r in reg["lines"] if r.get("outcome","").startswith(k)) for k in ("skip", "HOLD", "DRY", "posted", "FAULT")}))
L("write-off dollars: WOINS %.2f WOCAID2ND %.2f" % (sum(r.get("wo",0) for r in reg["lines"] if r.get("wocode")=="WOINS" and not r.get("outcome","").startswith("HOLD")), sum(r.get("wo",0) for r in reg["lines"] if r.get("wocode")=="WOCAID2ND")))
