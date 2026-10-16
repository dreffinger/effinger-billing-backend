# PLAIN ENGLISH (follow-up of era_new_1016_2110.py, run 2026-10-16T2110Z - ehpa cloud copy; stamp copy of era_dual_1012_1710.py with this run's one line)
# Humana ACH 835 1053197 (203380621261016, Humana Medicaid MMA as the SECONDARY on chart 17472784 - AMD 271 21:3xZ: Humana 7418478453 ACTIVE
#   'MC MEDICAID GATE CAP DIR', Medicare INACTIVE, date of death [DOB]) answered OA-18 DUPLICATE on the 99223 of 12/12/2025 (v19426363
#   c23332397): Humana adjudicated this coinsurance earlier and AMD never got that answer; the sister 99497 line on the same claim got OA-23 $0
#   (posted WOCAID2ND 14.54 by era_new_1016_2110.py). William's duplicate rule (9/14): never rebill, settle the ORIGINAL adjudication; the
#   original answer of a Medicaid MMA secondary on a dual's coinsurance is $0 -> WOCAID2ND (9/20, 10/4, 10/6, 10/12 rule).
# Decides, by the standing rules only:
#   B. WOCAID2ND ERA-linked: chart 17472784 v19426363 c23332397 (live insurance balance 33.75 = Medicare PR-2 coinsurance, patient 0.00) -
#      payreasons.post_line pay 0 + WOCAID2ND under the check's carrier HUM01 so the line stays balanced. Groups A and C are empty this run.
# Reads first: era_details/1053197.json, registers/era_checks_before_2026-10-16T2110Z.json, the charge live (txh.fetch_visit).
# --dry (default) prints the plan; --live writes. Stops after 3 consecutive addpayments faults.
# Register: registers/era_dual_2026-10-16T2110Z[_dry].json + registers/era_manual_register.json (live).
# Never touches: 1053116 (held for William), plans, insurance order, claims, rebills, PR amounts beyond this named charge.
import amd, payreasons, move_to_ins, txh, json, sys, time
a = sys.argv; DRY = "--live" not in a; S = "2026-10-16T2110Z"; CID = "1053197"
def L(m): print(m, flush=True)
amd.login_cached()
_l = json.load(open("registers/era_checks_before_2026-10-16T2110Z.json")); _l = _l.get("checks") if isinstance(_l, dict) else _l
chk = dict({str(c["id"]): c for c in _l}[CID])
det = {str(v["visitid"]): v for v in json.load(open("era_details/%s.json" % CID))["eracheckdetails"]}
A = []
B = [("17472784", "19426363", ["23332397"])]
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
