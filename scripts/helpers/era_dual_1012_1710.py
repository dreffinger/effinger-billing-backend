# PLAIN ENGLISH (follow-up of era_new_1012_1710.py, run 2026-10-12T1710Z - ehpa cloud copy)
# Humana NO-PAY 835 1053141 (202925788261012, Humana Medicaid MMA as the SECONDARY) answered OA-23 $0 on 9/20/2026 CCM lines that Medicare
# paid 10/7; on five charts the primary post left the Medicare coinsurance (16.14 / 8.92) on the PATIENT balance. William's dual rule
# (10/5/2026, 'route them'): a dual's PATIENT balance is always moved back - never bill a dual.
# Decides, by the standing rules only:
#   A. MOVE BACK (no rebill): chart 17476348 v19455727 (c23367132 16.14, c23367133 8.92 - live claim at MCAD, billed 10/7), chart 25869
#      v19455791 (c23367240 16.14 - live MCAD), chart 21172 v19455793 (c23367243 16.14 - live MCAD): the Medicaid FFS claim is pending at
#      the chart's seq 2 and its own answer (the 07xxx crossover) settles the residual - move_to_ins.move(cid, rebill=False), nothing else.
#   B. MOVE BACK + WOCAID2ND: chart 46673 v19455725 (c23367128 16.14, c23367129 8.92): the chart carries Medicare seq 1 / Medicaid seq 2 /
#      Humana MMA seq 3 (finclass CC) and the Humana secondary's OA-23 $0 is the dual crossover answer - move back, then the ERA-linked
#      write-off (payreasons.post_line pay 0 + WOCAID2ND under the check's carrier HUM01) so the line stays balanced.
#   C. RECORD ONLY: chart 20716 v19455816 (c23367273 16.14 on the patient): Medicare is the only plan on the chart - no Medicaid-type plan
#      to carry the residual; listed for the board (William's turn), nothing written. Charts 21238 (TRI05 secondary pending) and 44955
#      (MCAD pending) keep their insurance balances - nothing here.
# Reads first: era_details/1053141.json, registers/era_checks_before_2026-10-12T1718Z.json, every charge live (payreasons.visit_state).
# --dry (default) prints the plan; --live writes. Stops after 3 consecutive addpayments faults.
# Register: registers/era_dual_2026-10-12T1710Z[_dry].json + registers/era_manual_register.json (live).
# Never touches: 1053116 (held for William), plans, insurance order, claims, rebills, PR amounts beyond these named charges.
import amd, payreasons, move_to_ins, txh, json, sys, time
a = sys.argv; DRY = "--live" not in a; S = "2026-10-12T1710Z"; CID = "1053141"
def L(m): print(m, flush=True)
amd.login_cached()
_l = json.load(open("registers/era_checks_before_2026-10-12T1718Z.json")); _l = _l.get("checks") if isinstance(_l, dict) else _l
chk = dict({str(c["id"]): c for c in _l}[CID])
det = {str(v["visitid"]): v for v in json.load(open("era_details/%s.json" % CID))["eracheckdetails"]}
A = [("17476348", "19455727", ["23367132", "23367133"]), ("25869", "19455791", ["23367240"]), ("21172", "19455793", ["23367243"])]
B = [("46673", "19455725", ["23367128", "23367129"])]
C = [("20716", "19455816", ["23367273"])]
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
