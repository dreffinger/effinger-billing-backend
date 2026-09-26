# PLAIN ENGLISH (ERA denial lines, Florida Medicaid FFS check 1052850 / 201060564260925, run 2026-09-26T0110Z): the MCAD crossover
#   check carries 94 claims and only 4 money lines; every other line is a $0 Medicaid-secondary answer on a Medicare-paid charge:
#   OA-23 (prior payer adjudication - a dual crossover paying $0 on Medicare coinsurance = contractual write-off WOCAID2ND, rules.md 9/11 + 9/22),
#   CO-185/N767 (rendering provider not enrolled in FL Medicaid - the 9/20 rule: WOINS, the crossover residual never goes to the patient),
#   CO-147 on a 99497 ACP line (no Medicaid fee-schedule line - ACP is never payable by a Medicaid secondary: WOCAID2ND, the 9/23 FCC decode),
#   OA-18 (duplicate - the original adjudication stands; never rebilled, recorded only).
# Decides: for each $0 charge line read the LIVE charge (resave.detail); skip when the insurance balance is already 0 or no prior non-void
#   payment is on the charge (not a secondary residual -> hold); else post the ERA line ERA-linked through payreasons.post_line
#   (pay 0, write-off = min(line adjustment, open insurance balance), reason codes kept). Register registers/mcad_1052850_<stamp>.json. --dry first.
# Never touches: paid lines (Post button / fallback), any other check, patient balances, plans.
import amd, resave, payreasons, json, sys, time
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv; STAMP = "2026-09-26T0110Z"; CID = "1052850"
amd.login_cached()
chk = [c for c in json.load(open("era_checks_before_%s.json" % STAMP)) if str(c["id"]) == CID][0]
det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]
reg = {"stamp": STAMP, "checkid": CID, "lines": []}
def L(m): print(m, flush=True)
faults = 0; done = set()
for v in det:
    pid = str(v["patientid"]); vid = str(v["visitid"])
    for ch in v.get("charges", []):
        if float(ch.get("paymentamount") or 0) > 0: continue
        cid = str(ch["chargedetailid"])
        if int(cid) <= 0: continue
        carcs = ["%s%s" % (r["payreasongroup"], r["reasoncode"]) for r in ch.get("carc", [])]
        rec = {"visitid": vid, "patientid": pid, "chargeid": cid, "checkclaimid": v.get("checkclaimid"), "cpt": ch["chargecode"], "dos": ch["dos"][:10], "carcs": carcs, "adj": ch.get("adjustmentamount")}
        if cid in done: rec["outcome"] = "skip - same charge already handled on this check (repeated claim)"; reg["lines"].append(rec); continue
        rt = ET.fromstring(resave.detail(cid)); cc = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid]
        if not cc: rec["outcome"] = "skip - charge not live"; L("v%s %s not live" % (vid, cid)); reg["lines"].append(rec); continue
        c = cc[0]; bal = float(c.get("insbalance") or 0); pbal = float(c.get("patbalance") or 0)
        prior = [(p.get("id"), p.get("amount"), p.get("checknumber"), p.get("carrierfid")) for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) > 0]
        rec.update({"insbalance": bal, "patbalance": pbal, "prior_payments": prior})
        if bal <= 0: rec["outcome"] = "skip - insurance balance already 0"; L("v%s %s %s bal 0 - skip" % (vid, cid, carcs)); reg["lines"].append(rec); done.add(cid); continue
        if any("OA18" in x for x in carcs): rec["outcome"] = "skip - duplicate (OA-18), original adjudication stands"; L("v%s %s OA18 bal %.2f - skip" % (vid, cid, bal)); reg["lines"].append(rec); done.add(cid); continue
        if not prior: rec["outcome"] = "HOLD - no prior payment on the charge (not a secondary residual)"; L("v%s pat%s %s %s bal %.2f NO PRIOR PAYMENT - hold" % (vid, pid, ch["chargecode"], carcs, bal)); reg["lines"].append(rec); done.add(cid); continue
        if any("CO185" in x for x in carcs): code = "WOINS"; why = "CO-185/N767 Medicaid FFS crossover on a Medicare-paid line - rules.md 9/20 WOINS"
        elif any("OA23" in x for x in carcs): code = "WOCAID2ND"; why = "OA-23 dual crossover $0 on Medicare coinsurance (Medicaid FFS secondary)"
        elif any("CO147" in x for x in carcs) and ch["chargecode"] == "99497": code = "WOCAID2ND"; why = "CO-147 on ACP 99497 - no Medicaid fee-schedule line, never payable by the secondary (9/23 FCC decode)"
        else: rec["outcome"] = "HOLD - unhandled CARC %s" % carcs; L("v%s %s %s HOLD unhandled" % (vid, cid, carcs)); reg["lines"].append(rec); done.add(cid); continue
        wo = round(min(bal, sum(float(r["reasonamt"]) for r in ch.get("carc", []))), 2)
        rec.update({"wocode": code, "wo": wo, "why": why})
        if DRY: rec["outcome"] = "DRY would post $0 + %s %.2f" % (code, wo); L("v%s pat%s %s %s bal %.2f pat %.2f -> DRY %s %.2f" % (vid, pid, ch["chargecode"], carcs, bal, pbal, code, wo)); reg["lines"].append(rec); done.add(cid); continue
        ok, payid, head = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=0.0, wo=wo, wocode=code)
        time.sleep(0.6)
        rt2 = ET.fromstring(resave.detail(cid)); c2 = [x for x in rt2.iter("charge") if x.get("id") == "charge" + cid][0]
        rec.update({"ok": ok, "paymentid": payid, "resp": head[:160], "insbalance_after": float(c2.get("insbalance") or 0), "patbalance_after": float(c2.get("patbalance") or 0)})
        rec["outcome"] = ("posted $0 + %s %.2f" % (code, wo)) if ok else "FAULT"
        faults = 0 if ok else faults + 1
        L("v%s pat%s %s %s bal %.2f -> %s %.2f ok=%s after ins %.2f pat %.2f %s" % (vid, pid, ch["chargecode"], carcs, bal, code, wo, ok, rec["insbalance_after"], rec["patbalance_after"], head[:100]))
        reg["lines"].append(rec); done.add(cid); time.sleep(0.4)
        if faults >= 3: L("3 consecutive addpayments faults - stopping"); break
    if faults >= 3: break
json.dump(reg, open("registers/mcad_1052850_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
L("=== %s: %d lines; %s" % ("DRY" if DRY else "LIVE", len(reg["lines"]), {k: sum(1 for r in reg["lines"] if r.get("outcome","").startswith(k)) for k in ("skip", "HOLD", "DRY", "posted", "FAULT")}))
L("write-off dollars: WOINS %.2f WOCAID2ND %.2f" % (sum(r.get("wo",0) for r in reg["lines"] if r.get("wocode")=="WOINS" and not r.get("outcome","").startswith("HOLD")), sum(r.get("wo",0) for r in reg["lines"] if r.get("wocode")=="WOCAID2ND" and not r.get("outcome","").startswith("HOLD"))))
