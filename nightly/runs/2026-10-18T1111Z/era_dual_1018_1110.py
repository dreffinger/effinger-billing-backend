# PLAIN ENGLISH (7 AM ET 10/18/2026 run 2026-10-18T1111Z - ehpa cloud copy; stamp copy of era_dual_1016_2110.py with this run's two lines)
# Sunshine Health ACH 835 1053207 (0917934406, AMD maps it to FLO02; Sunshine = the Medicaid MMA SECONDARY on these dual charts) answered
#   CO-96/N448 'not in the fee schedule' $0 on two CCM 99487 Medicare-coinsurance residuals: chart 20670 v19455778 c23367220 and chart 17472429
#   v19455765 c23367205 (live 11:2xZ: Medicare 819960772 paid 63.28 + WOINS 126.58 each, PR-2 16.14 open on insurance at SUN01, patient 0.00).
#   Standing rule (9/23, 10/14 precedent on chart 25266): a Medicaid MMA never pays CCM/AWV -> WOCAID2ND, ERA-linked under the check's carrier.
# Decides, by the standing rules only: group B = WOCAID2ND ERA-linked (payreasons.post_line pay 0 + WOCAID2ND = the open insurance balance).
# Reads first: era_details/1053207.json, registers/era_checks_before_2026-10-18T1111Z.json, the charge live (txh.fetch_visit).
# --dry (default) prints the plan; --live writes. Stops after 3 consecutive addpayments faults.
# Register: registers/era_dual_2026-10-18T1111Z[_dry].json + registers/era_manual_register.json (live).
# Never touches: plans, insurance order, claims, rebills, PR amounts beyond the two named charges, the M56 / CO-18 $0 lines on the same check.
import amd, payreasons, move_to_ins, txh, json, sys, time
a = sys.argv; DRY = "--live" not in a; S = "2026-10-18T1111Z"; CID = "1053207"
def L(m): print(m, flush=True)
amd.login_cached()
_l = json.load(open("registers/era_checks_before_2026-10-18T1111Z.json")); _l = _l.get("checks") if isinstance(_l, dict) else _l
chk = dict({str(c["id"]): c for c in _l}[CID])
det = {str(v["visitid"]): v for v in json.load(open("era_details/%s.json" % CID))["eracheckdetails"]}
A = []
B = [("20670", "19455778", ["23367220"]), ("17472429", "19455765", ["23367205"])]
C = []
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"),
            "pays": [((p.get("checknumber") or "").strip(), p.get("void")) for p in c.iter("payment")]}
    return res
out = {"stamp": S, "dry": DRY, "lines": []}; faults = 0
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
for group, items in (("A", A), ("B", B), ("C", C)):
    for pid, vid, cids in items:
        st = live(pid, vid); v = det[vid]
        for cid in cids:
            s = st.get(cid); r = {"group": group, "checkid": CID, "checkclaimid": v["checkclaimid"], "pid": pid, "visitid": vid, "chargedetailid": cid, "before": s}
            if not s: r["outcome"] = "skip - charge not live"; out["lines"].append(r); continue
            if group == "C":
                r["outcome"] = "record only - %.2f on the patient balance, no Medicaid-type plan on the chart (board row, William's turn)" % s["patbal"]; out["lines"].append(r); L("%s v%s c%s %s" % (group, vid, cid, r["outcome"])); continue
            if any(p[0] == chk["paymentnumber"] and p[1] != "1" for p in s["pays"]): r["outcome"] = "already-posted"; out["lines"].append(r); L("v%s c%s already posted" % (vid, cid)); continue
            if s["patbal"] <= 0 and s["insbal"] <= 0: r["outcome"] = "skip - nothing open"; out["lines"].append(r); continue
            if s["patbal"] > 0:
                if DRY: r["move"] = "DRY would move %.2f patient balance back to insurance (no rebill)" % s["patbal"]; L("%s v%s c%s %s" % (group, vid, cid, r["move"]))
                else:
                    mv = move_to_ins.move(cid, rebill=False); r["move"] = mv; L("%s v%s c%s move back: %s" % (group, vid, cid, mv))
                    if not str(mv).startswith("moved"): r["outcome"] = "HOLD - move back failed"; out["lines"].append(r); continue
                    time.sleep(0.6); st = live(pid, vid); s = st.get(cid); r["after_move"] = {"insbal": s["insbal"], "patbal": s["patbal"]}
            if group == "A": r["outcome"] = "moved back - Medicaid FFS claim pending at %s settles it" % s["carrier"] if not DRY else "DRY move back only"; out["lines"].append(r); continue
            ch = next(c for c in v["charges"] if str(c["chargedetailid"]) == cid)
            bal = s["insbal"] if not DRY else (s["insbal"] + s["patbal"])
            wo = round(bal, 2)
            if DRY: r["outcome"] = "DRY would post pay 0.00 + WOCAID2ND %.2f under %s" % (wo, chk["systemcarriercode"]); out["lines"].append(r); L("%s v%s c%s %s" % (group, vid, cid, r["outcome"])); continue
            if faults >= 3: r["outcome"] = "not attempted - 3 faults"; out["lines"].append(r); continue
            ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=0.0, wo=wo, wocode="WOCAID2ND")
            time.sleep(0.7); s2 = live(pid, vid).get(cid) or {}
            r.update(outcome="posted" if ok else "FAULT", pay=0.0, wo=wo, wocode="WOCAID2ND", paymentid=payid, resp=resp[:160], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
            faults = 0 if ok else faults + 1
            L("%s v%s c%s WOCAID2ND %.2f ok=%s after ins %s pat %s" % (group, vid, cid, wo, ok, s2.get("insbal"), s2.get("patbal")))
            out["lines"].append(r); time.sleep(0.4)
json.dump(out, open("registers/era_dual_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r.get("outcome", "").startswith(("posted", "already")):
            reg.append({"checkid": CID, "checkclaimid": r["checkclaimid"], "visitid": r["visitid"], "chargedetailid": r["chargedetailid"], "outcome": r["outcome"].split()[0], "pay": r.get("pay"), "wo": r.get("wo"), "wocode": r.get("wocode"), "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
L(json.dumps([(r["group"], r["visitid"], r["chargedetailid"], r["outcome"][:60]) for r in out["lines"]], indent=0))
