# PLAIN ENGLISH (5 AM ET 10/19/2026 run 2026-10-19T0910Z - ehpa cloud copy; stamp copy of era_dual_1018_1110.py with this run's five lines)
# Two new $0-denial sets arrived this slot and the Billing Button engine dismissed both checks before their $0 lines were worked
#   (the 10/16 and 10/18 TRAP): settle them from era_details/ by the standing rules, ERA-linked to the check that answered.
#   Check 1053210 (Humana ACH 203602886261018, HUM01 = the Medicaid MMA SECONDARY on these dual charts):
#     group A  chart 17472397 v19397335 c22470803 (99309 12/09/2024): the primary (AMB03, check 0923844014 9/9/2026) paid 90.57 and its own
#              payment carries CO45 50.43 that was never written off - the live insurance balance IS that contractual. Humana's PI-29 on the
#              residual is moot. Standing rule (William 10/13-10/14: contractual on the payer's own CO45/CO253/CO144 -> WOINS; nothing stays open)
#              -> pay 0.00 + WOINS = the open insurance balance, ERA-linked under this check.
#     group B  chart 17476681 v19455801 c23367254 (99487) + c23367255 (99489) 9/20/2026: Medicare 819970542 paid 63.28 / 34.95 + WOINS, the PR
#              coinsurance 16.14 / 8.92 sits at HUM01; Humana answered OA-23 $0. Standing rule (9/23, 10/14, 10/18 precedents): a Medicaid MMA
#              never pays CCM -> WOCAID2ND ERA-linked.
#   Check 1053209 (Optum VA CCN 3680160141, $0, VACCN = the THIRD plan on a dual chart):
#     group B  chart 17471773 v19417230 c23320853, v19417014 c23320662, v19417163 c23320775 (99233 9/17-9/19/2025): Medicare 817795550 paid
#              89.83 + WOINS 47.25 each, Humana Medicaid MMA (169608144251010) answered 0.04 each, 22.88 Medicare coinsurance left at VACCN,
#              which answered OA-23 + CO-288 $0. The Medicaid-family plan answered short of the PR total -> WOCAID2ND (William 10/13-10/14 rule);
#              VA CCN's CO-288 'referral absent' on a Medicare-coinsurance residual is listed in the report, not appealed.
# Decides, by the standing rules only: group A = WOINS ERA-linked; group B = WOCAID2ND ERA-linked (payreasons.post_line pay 0 + wo = the open
#   insurance balance, capped at the live balance, PR never beyond it).
# Reads first: era_details/<checkid>.json, registers/era_checks_before_2026-10-19T0915Z.json, the charge live (txh.fetch_visit).
# --dry (default) prints the plan; --live writes. Stops after 3 consecutive addpayments faults. A charge already carrying a non-void payment
#   with this check number is 'already-posted'; a charge with nothing open is skipped; a patient-side balance is moved back first (no rebill).
# Register: registers/era_dual_2026-10-19T0910Z[_dry].json + registers/era_manual_register.json (live).
# Never touches: plans, insurance order, claims, rebills, any charge not named, the Post-button money lines of 1053210.
import amd, payreasons, move_to_ins, txh, json, sys, time
a = sys.argv; DRY = "--live" not in a; S = "2026-10-19T0910Z"
def L(m): print(m, flush=True)
amd.login_cached()
_l = json.load(open("registers/era_checks_before_2026-10-19T0915Z.json")); _l = _l.get("checks") if isinstance(_l, dict) else _l
CHK = {str(c["id"]): dict(c) for c in _l}
DET = {cid: {str(v["visitid"]): v for v in json.load(open("era_details/%s.json" % cid))["eracheckdetails"]} for cid in CHK}
# (group, checkid, pid, visitid, [chargeids], wocode)
LINES = [
    ("A", "1053210", "17472397", "19397335", ["22470803"], "WOINS"),
    ("B", "1053210", "17476681", "19455801", ["23367254", "23367255"], "WOCAID2ND"),
    ("B", "1053209", "17471773", "19417230", ["23320853"], "WOCAID2ND"),
    ("B", "1053209", "17471773", "19417014", ["23320662"], "WOCAID2ND"),
    ("B", "1053209", "17471773", "19417163", ["23320775"], "WOCAID2ND"),
]
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"), "fee": c.get("fee"),
            "pays": [((p.get("checknumber") or "").strip(), p.get("void"), p.get("amount"), p.get("carrier")) for p in c.iter("payment")]}
    return res
out = {"stamp": S, "dry": DRY, "lines": []}; faults = 0
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
for group, CID, pid, vid, cids, wocode in LINES:
    chk = CHK[CID]; v = DET[CID][vid]; st = live(pid, vid)
    for cid in cids:
        s = st.get(cid); r = {"group": group, "checkid": CID, "checkclaimid": v["checkclaimid"], "pid": pid, "visitid": vid, "chargedetailid": cid, "wocode": wocode, "before": s}
        if not s: r["outcome"] = "skip - charge not live"; out["lines"].append(r); L("v%s c%s not live" % (vid, cid)); continue
        if any(p[0] == chk["paymentnumber"] and p[1] != "1" for p in s["pays"]): r["outcome"] = "already-posted"; out["lines"].append(r); L("v%s c%s already posted" % (vid, cid)); continue
        if s["patbal"] <= 0 and s["insbal"] <= 0: r["outcome"] = "skip - nothing open"; out["lines"].append(r); L("v%s c%s nothing open" % (vid, cid)); continue
        if s["patbal"] > 0:
            if DRY: r["move"] = "DRY would move %.2f patient balance back to insurance (no rebill)" % s["patbal"]; L("%s v%s c%s %s" % (group, vid, cid, r["move"]))
            else:
                mv = move_to_ins.move(cid, rebill=False); r["move"] = mv; L("%s v%s c%s move back: %s" % (group, vid, cid, mv))
                if not str(mv).startswith("moved"): r["outcome"] = "HOLD - move back failed"; out["lines"].append(r); continue
                time.sleep(0.6); st = live(pid, vid); s = st.get(cid); r["after_move"] = {"insbal": s["insbal"], "patbal": s["patbal"]}
        ch = next(c for c in v["charges"] if str(c["chargedetailid"]) == cid)
        bal = s["insbal"] if not DRY else (s["insbal"] + s["patbal"])
        wo = round(bal, 2)
        if DRY: r["outcome"] = "DRY would post pay 0.00 + %s %.2f under %s (live ins %.2f pat %.2f cpt %s fee %s)" % (wocode, wo, chk["systemcarriercode"], s["insbal"], s["patbal"], s["cpt"], s["fee"]); out["lines"].append(r); L("%s v%s c%s %s" % (group, vid, cid, r["outcome"])); continue
        if faults >= 3: r["outcome"] = "not attempted - 3 faults"; out["lines"].append(r); continue
        ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=0.0, wo=wo, wocode=wocode)
        time.sleep(0.7); s2 = live(pid, vid).get(cid) or {}
        r.update(outcome="posted" if ok else "FAULT", pay=0.0, wo=wo, paymentid=payid, resp=resp[:160], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
        faults = 0 if ok else faults + 1
        L("%s v%s c%s %s %.2f ok=%s after ins %s pat %s" % (group, vid, cid, wocode, wo, ok, s2.get("insbal"), s2.get("patbal")))
        out["lines"].append(r); time.sleep(0.4)
json.dump(out, open("registers/era_dual_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r.get("outcome", "").startswith(("posted", "already")):
            reg.append({"checkid": r["checkid"], "checkclaimid": r["checkclaimid"], "visitid": r["visitid"], "chargedetailid": r["chargedetailid"], "outcome": r["outcome"].split()[0], "pay": r.get("pay"), "wo": r.get("wo"), "wocode": r.get("wocode"), "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
L(json.dumps([(r["group"], r["checkid"], r["visitid"], r["chargedetailid"], r["outcome"][:70]) for r in out["lines"]], indent=0))
