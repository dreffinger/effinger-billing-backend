# PLAIN ENGLISH (9 AM ET 10/19/2026 run 2026-10-19T1310Z - ehpa cloud copy)
# Five Medicare-contractual residuals left on chart 17477350 after the ERA Center Post button posted AARP Medigap ACH 00148578843
#   (check 1053212) this run: the five HCA 99233s of 9/2-9/6/2026 (v19453714 c23364597, v19453777 c23364672, v19453761 c23364654,
#   v19453857 c23364776, v19453838 c23364756; fee 160 each). Medicare 819814877 (check 1051715, posted 9/19) paid 85.46 on each with
#   CO45 51.00 / CO253 1.74 / PR2 21.80 on the payment but NO write-off (the FLO02 Post-button CO-45 defect, 10/17 TRAP), so the
#   charge sat at 74.54 insurance balance; AARP then paid the PR-2 21.80 (era_post over-apply guard: 'posting payment only') and
#   AMD flipped the remaining 52.74 = Medicare's never-adjusted contractual onto the PATIENT balance. Nothing is owed by anyone:
#   the 52.74 is CO45 + CO253 -> WOINS, carried on the Medicare check number (the 9/23 rule: move_to_ins + manual_post pay 0 / WOINS
#   with the trace number; the remit line of 1051715 is no longer readable - AMD's checkdetails drops a claim once it is posted,
#   so era_co45_relink.py cannot re-post it ERA-linked).
# Decides: nothing new. --dry (default) re-reads each charge live and prints the plan; --live, per line: (1) move_to_ins.move(cid,
#   rebill=False) - the full-visit echo that moves the patient balance back to insurance, no rebill; (2) manual_post.post(cid, FLO02,
#   0.00, 52.74, WOINS, checknumber 819814877, deposit date = the Medicare payment's date on the charge) - only when the live charge
#   shows exactly pat 52.74 / ins 0.00, no live WOINS, and the AARP payment of this check already on it; anything else is HELD and
#   listed. Stops on the first fault. Register: registers/era_residual_2026-10-19T1310Z[_dry].json + registers/era_manual_register.json.
# Never touches: payments, plans, claims, rebills, any other charge or chart.
import amd, manual_post, move_to_ins, txh, json, sys, time
a = sys.argv; DRY = "--live" not in a; S = "2026-10-19T1310Z"
PID = "17477350"; EXPECT = 52.74; MCHK = "819814877"; ACHK = "00148578843"
LINES = [("19453714", "23364597"), ("19453777", "23364672"), ("19453761", "23364654"), ("19453857", "23364776"), ("19453838", "23364756")]
def L(m): print(m, flush=True)
amd.login_cached()
def live(vid, cid):
    root = txh.fetch_visit(PID, vid)
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("id").replace("charge", "") != cid: continue
        pays = []
        for p in c.iter("payment"):
            if p.get("void") == "1": continue
            pays.append({"chk": (p.get("checknumber") or "").strip(), "amt": p.get("amount"), "carrier": p.get("carrier"), "attrs": dict(p.attrib),
                         "reasons": [(r.get("code"), r.get("amount")) for r in p.iter("payreason")]})
        return {"insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "cpt": c.get("proccode"), "fee": c.get("fee"), "carrier": c.get("carrier"),
                "pays": pays, "wos": [(w.get("wocode"), w.get("amount"), w.get("void")) for w in c.iter("writeoff")]}
def depdate(s):
    for p in s["pays"]:
        if p["carrier"] == "FLO02" and MCHK in p["chk"]:
            for k in ("depositdate", "date", "paymentdate", "postdate", "entrydate"):
                if p["attrs"].get(k): return p["attrs"][k][:10]
    return None
out = {"stamp": S, "dry": DRY, "lines": []}
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF)); faults = 0
for vid, cid in LINES:
    s = live(vid, cid); r = {"pid": PID, "visitid": vid, "chargedetailid": cid, "expect": EXPECT, "before": {k: s[k] for k in s if k != "pays"} if s else None}
    if s: r["before"]["pays"] = [(p["chk"][-6:], p["amt"], p["carrier"], p["reasons"]) for p in s["pays"]]
    dep = depdate(s) if s else None; r["depositdate"] = dep
    has_aarp = s and any(p["chk"].endswith(ACHK[-6:]) and abs(float(p["amt"] or 0)) > 0 for p in s["pays"])
    if not s: r["outcome"] = "skip - charge not live"
    elif any(w[0] == "WOINS" and w[2] != "1" for w in s["wos"]): r["outcome"] = "already-posted (a live WOINS is on the charge)"
    elif not has_aarp: r["outcome"] = "HELD - no AARP %s payment on the charge" % ACHK
    elif abs(s["patbal"] - EXPECT) > 0.009 or s["insbal"] > 0.009: r["outcome"] = "HELD - live pat %.2f ins %.2f differs from the expected residual pat %.2f / ins 0" % (s["patbal"], s["insbal"], EXPECT)
    elif not dep: r["outcome"] = "HELD - Medicare payment date not readable (attrs %s)" % [p["attrs"] for p in s["pays"] if p["carrier"] == "FLO02"]
    elif DRY: r["outcome"] = "DRY would move pat %.2f -> insurance (no rebill), then post pay 0.00 + WOINS %.2f under FLO02 check %s dep %s" % (EXPECT, EXPECT, MCHK, dep)
    else:
        mv = move_to_ins.move(cid, None, False, rebill=False); r["move"] = str(mv)[:200]
        if not str(mv).startswith("moved"):
            r["outcome"] = "FAULT - move: %s" % str(mv)[:160]; faults += 1; L("v%s c%s %s" % (vid, cid, r["outcome"])); out["lines"].append(r); break
        time.sleep(0.8)
        res = manual_post.post(cid, "FLO02", 0.0, EXPECT, "WOINS", checknumber=MCHK, depositdate=dep, note="ERA 1051715 Post-button CO45/CO253 residual after AARP 1053212 %s" % S)
        time.sleep(0.8); s2 = live(vid, cid) or {}
        r.update(resp=str(res)[:200], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
        if s2.get("insbal") == 0 and s2.get("patbal") == 0: r["outcome"] = "posted"
        else:
            r["outcome"] = "FAULT - after ins %s pat %s" % (s2.get("insbal"), s2.get("patbal")); faults += 1
    L("v%s c%s %s" % (vid, cid, r["outcome"])); out["lines"].append(r)
    if faults: break
json.dump(out, open("registers/era_residual_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r["outcome"] == "posted":
            reg.append({"checkid": "1051715", "checkclaimid": None, "visitid": r["visitid"], "chargedetailid": r["chargedetailid"], "pid": PID, "outcome": "posted",
                        "pay": 0.0, "wo": EXPECT, "wocode": "WOINS", "checkno": MCHK, "note": "CO45/CO253 residual after AARP 1053212", "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
L("done: %s" % {o: sum(1 for r in out["lines"] if r["outcome"].split(" ")[0] == o) for o in set(r["outcome"].split(" ")[0] for r in out["lines"])})
