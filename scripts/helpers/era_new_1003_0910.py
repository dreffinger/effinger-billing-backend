# PLAIN ENGLISH (two new Florida Medicare ERA checks, run 2026-10-03T0910Z = 5 AM ET 10/3 slot: 1052942 (819910096, $1,344.70, 17 clean money lines) + 1052943 ($0, 47 denial-only claims - every $0 line HOLDs here and is worked by the denial rules)): Humana 1052939 ($88.28), 1052940 ($1,280.80, 12 HCA 99233/99239
#   lines on one chart) and 1052941 ($320.46, 3 HCA 99233 lines) plus Ambetter 1052938 ($125.21, 2 SNF lines) are clean money lines (paid = allowed,
#   CO-45 + CO-253 sequestration adjustments, one PR-2 coinsurance) on charges open at full fee. The one $0 line (1052939, pat21378 v19444121,
#   two charges) is Humana's MEDICAID-MMA SECONDARY answer on a Medicare-paid HCA stay: CO-45 + PI-B13 "previously paid" (UHC Community Plan had
#   already paid the crossover in July) = the dual crossover owes nothing more on the Medicare coinsurance -> WOCAID2ND, the standing
#   Medicaid-secondary residual code (rules.md 9/11 + 9/22, same family as OA-23); the Humana plan on that chart carries the Medicaid id.
#   The PI-B13 sits at claim level, so both charges of that claim (99223 36.45 + 99232 14.38 open) take the WOCAID2ND.
# Decides, per line, from the LIVE charge (gettxhistory): skip when a non-void payment already carries this check number or the insurance
#   balance is 0; MONEY: pay = min(paid, open insurance balance), write-off = the remit's CO adjustments capped so pay + wo never exceeds the
#   balance, WOINS; $0: write-off = the open balance capped by the remit adjustment (WOCAID2ND / WOINS as above). Every line goes through the
#   ERA-linked Payment Entry shape (payreasons.post_line - reason codes kept, no CO-45 lands on the patient, nothing left to transfer).
#   --dry = read only. 3 consecutive addpayments faults stop the run. Copy of era_new_0110.py (9/30) with the new stamp + the PI-B13 branch.
# Never touches: the Post button, the held Florida Blue check 1052906, plans, patient balances.
import amd, txh, payreasons, json, sys, time
DRY = "--dry" in sys.argv; S = "2026-10-03T0910Z"
amd.login_cached()
chks = {str(c["id"]): c for c in json.load(open("era_checks_before_2026-10-03T0910Z.json"))}
def L(m): print(m, flush=True)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"), "dos": c.get("dos"),
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("carrier"), p.get("void")) for p in c.iter("payment")]}
    return res
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
out = {"stamp": S, "dry": DRY, "lines": []}; faults = 0
for CID in sys.argv[1:]:
    if CID.startswith("--"): continue
    chk = chks[CID]; det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]; done = set()
    L("=== check %s %s %s $%s" % (CID, chk["systemcarriercode"], chk["paymentnumber"], chk["paymentamount"]))
    for v in det:
        pid = str(v["patientid"]); vid = str(v["visitid"]); st = None
        for ch in v.get("charges") or []:
            cid = str(ch["chargedetailid"]); paid = float(ch.get("paymentamount") or 0)
            carcs = ["%s" % a["reasoncode"] for a in ch.get("carc") or []]; rarcs = [r["remarkcode"] for r in ch.get("rarc") or [] if r["remarkcode"] != "#AM"]
            co = sum(float(a["reasonamt"] or 0) for a in ch.get("carc") or [] if a["payreasongroup"] in ("CO", "OA", "PI"))
            r = {"checkid": CID, "checkclaimid": v["checkclaimid"], "visitid": vid, "pid": pid, "chargedetailid": cid, "cpt": ch["chargecode"], "dos": ch["dos"][:10], "paid": paid, "carcs": carcs, "rarcs": rarcs, "when": S}
            if faults >= 3: r["outcome"] = "not attempted - 3 consecutive addpayments faults"; out["lines"].append(r); continue
            if cid in done: r["outcome"] = "skip - charge already handled on this check (repeated claim)"; out["lines"].append(r); continue
            done.add(cid)
            if st is None: st = live(pid, vid); time.sleep(0.3)
            s = st.get(cid)
            if not s: r["outcome"] = "skip - charge not live"; out["lines"].append(r); L("v%s c%s not live" % (vid, cid)); continue
            r["before"] = {k: s[k] for k in ("fee", "paid", "insbal", "patbal", "carrier")}
            if any(p[1] == chk["paymentnumber"] and p[3] != "1" for p in s["pays"]): r["outcome"] = "already-posted"; out["lines"].append(r); L("v%s c%s already posted" % (vid, cid)); continue
            bal = s["insbal"]
            if bal <= 0: r["outcome"] = ("residual %.2f" % paid) if paid > 0 else "skip - insurance balance already 0"; out["lines"].append(r); L("v%s c%s %s bal 0 -> %s" % (vid, cid, ch["chargecode"], r["outcome"])); continue
            if paid > 0:
                pay = min(paid, bal); wo = max(0.0, min(round(co, 2), round(bal - pay, 2))); code = "WOINS"
            else:
                if any(c in ("OA18", "18") for c in carcs): r["outcome"] = "duplicate OA-18 - original adjudication stands, nothing posted"; out["lines"].append(r); continue
                prior = [p for p in s["pays"] if p[3] != "1" and p[0] < 0]
                if not prior: r["outcome"] = "HOLD - $0 answer with no prior payment on the charge (not a secondary residual)"; out["lines"].append(r); L("v%s c%s HOLD no prior" % (vid, cid)); continue
                if any(c in ("CO185", "185") for c in carcs): code = "WOINS"; why = "CO-185/N767 Medicaid-secondary crossover on a Medicare-paid line - 9/20 rule WOINS"
                elif any(c in ("OA23", "23") for c in carcs): code = "WOCAID2ND"; why = "OA-23 dual crossover $0 on Medicare coinsurance"
                elif (any(c in ("PIB13", "B13") for c in carcs) or any(a["reasoncode"] in ("PIB13", "B13") for a in v.get("carc") or [])) and chk["systemcarriercode"] == "HUM01": code = "WOCAID2ND"; why = "PI-B13 previously paid - Humana Medicaid-MMA secondary $0 on a Medicare-paid line (dual crossover residual)"
                else: r["outcome"] = "HOLD - unhandled $0 CARC %s %s" % (carcs, rarcs); out["lines"].append(r); L("v%s c%s HOLD %s" % (vid, cid, carcs)); continue
                pay = 0.0; wo = round(min(bal, co), 2); r["why"] = why
            r.update(pay=round(pay, 2), wo=round(wo, 2), wocode=code, residual=round(paid - pay, 2))
            if DRY: r["outcome"] = "DRY would post pay %.2f + %s %.2f (bal %.2f)" % (pay, code, wo, bal); out["lines"].append(r); L("v%s pat%s c%s %s %s paid %.2f bal %.2f -> %s" % (vid, pid, cid, ch["chargecode"], "+".join(carcs), paid, bal, r["outcome"])); continue
            ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=round(pay, 2), wo=round(wo, 2), wocode=code)
            time.sleep(0.7); st = live(pid, vid); s2 = st.get(cid) or {}
            r.update(outcome="posted" if ok else "FAULT", paymentid=payid, resp=resp[:160], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
            faults = 0 if ok else faults + 1
            L("v%s pat%s c%s %s paid %.2f bal %.2f -> pay %.2f %s %.2f ok=%s after ins %s pat %s" % (vid, pid, cid, ch["chargecode"], paid, bal, pay, code, wo, ok, s2.get("insbal"), s2.get("patbal")))
            out["lines"].append(r); time.sleep(0.4)
json.dump(out, open("registers/era_new_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r.get("outcome", "").startswith(("posted", "already", "residual")):
            reg.append({"checkid": r["checkid"], "checkclaimid": r["checkclaimid"], "visitid": r["visitid"], "chargedetailid": r["chargedetailid"], "cpt": r["cpt"], "outcome": r["outcome"].split()[0], "pay": r.get("pay"), "wo": r.get("wo"), "wocode": r.get("wocode"), "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
from collections import Counter
L(str(Counter(r["outcome"].split(" (")[0][:28] for r in out["lines"])))
L("pay $%.2f  WOINS $%.2f  WOCAID2ND $%.2f" % (sum(r.get("pay", 0) for r in out["lines"] if r["outcome"].startswith(("posted", "DRY"))), sum(r.get("wo", 0) for r in out["lines"] if r.get("wocode") == "WOINS" and r["outcome"].startswith(("posted", "DRY"))), sum(r.get("wo", 0) for r in out["lines"] if r.get("wocode") == "WOCAID2ND" and r["outcome"].startswith(("posted", "DRY")))))
