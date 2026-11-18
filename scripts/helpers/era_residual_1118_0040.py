# PLAIN ENGLISH (7:39 PM ET 11/17/2026 evening run 2026-11-18T0040Z - ehpa cloud copy)
# Sunshine (SUN01, the Medicaid SMMC secondary) ACH 0918140025 (ERA check 1053555, deposit 11/17/2026) paid 10.21 on 18 dual-eligible
#   99309 lines after Medicare had paid 121.08 (fee 141.00, total paid 131.29). The Post button left the 9.71 difference open - on the
#   PATIENT balance on 17 lines, on the insurance balance on 1 - and era_co45_relink left all 18 'for review' (its remainder test
#   expects fee - paid). The 9.71 is coinsurance a Medicaid-family secondary answered short of -> WOCAID2ND (William 10/13-10/14 rule;
#   precedents era_residual_1019_0910.py, 10/6 / 10/11 Sunshine checks). A dual's patient balance is never billed: move it back to
#   insurance first (move_to_ins.move, rebill=False), then a $0 payment + WOCAID2ND 9.71 carrying the Sunshine check number and date.
# Decides: nothing new. --dry (default) re-reads each charge live and prints the plan; --live writes only when the live open balance
#   (insurance + patient) is exactly 9.71 and no live WOCAID2ND is on the charge; anything else is HELD and listed. Stops after 3 faults.
# Register: registers/era_residual_2026-11-18T0040Z[_dry].json + registers/era_manual_register.json (live).
# Never touches: payments, plans, claims, rebills, any other charge.
import amd, manual_post, move_to_ins, txh, json, sys, time
a = sys.argv; DRY = "--live" not in a; S = "2026-11-18T0040Z"
CHK, CHECKID, DEP, CAR, EXPECT, WOC = "0918140025", "1053555", "11/17/2026", "SUN01", 9.71, "WOCAID2ND"
LINES = [("17472791", "19459162", "23371570"), ("17472791", "19458960", "23371248"), ("17472791", "19458777", "23370997"),
         ("12179706", "19458771", "23370991"), ("17470875", "19458770", "23370990"), ("25266", "19458750", "23370970"),
         ("17471131", "19458861", "23371090"), ("17472429", "19458759", "23370979"), ("17472286", "19458867", "23371099"),
         ("20670", "19458763", "23370983"), ("17473346", "19458857", "23371084"), ("20729", "19459269", "23371696"),
         ("20729", "19459298", "23371743"), ("20729", "19459272", "23371699"), ("20729", "19458737", "23370957"),
         ("20729", "19459275", "23371702"), ("17472286", "19458847", "23371072"), ("17472286", "19458891", "23371128")]
def L(m): print(m, flush=True)
amd.login_cached()
def live(pid, vid, cid):
    root = txh.fetch_visit(pid, vid)
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("id").replace("charge", "") != cid: continue
        return {"insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "cpt": c.get("proccode"), "carrier": c.get("carrier"),
                "wos": [(w.get("wocode"), w.get("amount"), w.get("void")) for w in c.iter("writeoff")]}
out = {"stamp": S, "dry": DRY, "lines": []}; faults = 0
REGF = "registers/era_manual_register.json"
try: reg = json.load(open(REGF))
except Exception: reg = []
for pid, vid, cid in LINES:
    if faults >= 3: L("stopped after 3 faults"); break
    s = live(pid, vid, cid); r = {"pid": pid, "visitid": vid, "chargedetailid": cid, "before": s}
    if not s: r["outcome"] = "skip - charge not live"
    elif any(w[0] == WOC and w[2] != "1" for w in s["wos"]): r["outcome"] = "already-posted (a live %s is on the charge)" % WOC
    elif abs(s["insbal"] + s["patbal"] - EXPECT) > 0.009: r["outcome"] = "HELD - live ins %.2f pat %.2f differs from the expected residual %.2f" % (s["insbal"], s["patbal"], EXPECT)
    elif DRY: r["outcome"] = "DRY would %spost pay 0.00 + %s %.2f under %s check %s" % ("move %.2f back to insurance, then " % s["patbal"] if s["patbal"] > 0 else "", WOC, EXPECT, CAR, CHK)
    else:
        if s["patbal"] > 0:
            r["move"] = str(move_to_ins.move(cid, rebill=False))[:200]; time.sleep(0.7)
            s1 = live(pid, vid, cid) or {}
            if abs((s1.get("insbal") or 0) - EXPECT) > 0.009 or (s1.get("patbal") or 0) > 0:
                r["outcome"] = "FAULT - move back left ins %s pat %s" % (s1.get("insbal"), s1.get("patbal")); faults += 1
                L("v%s c%s %s" % (vid, cid, r["outcome"])); out["lines"].append(r); continue
        res = manual_post.post(cid, CAR, 0.0, EXPECT, WOC, checknumber=CHK, depositdate=DEP, note="ERA %s dual residual %s" % (CHECKID, S))
        time.sleep(0.7); s2 = live(pid, vid, cid) or {}
        r.update(resp=str(res)[:200], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
        if s2.get("insbal") == 0 and s2.get("patbal") == 0: r["outcome"] = "posted"
        else: r["outcome"] = "FAULT - after ins %s pat %s" % (s2.get("insbal"), s2.get("patbal")); faults += 1
    L("v%s c%s %s" % (vid, cid, r["outcome"])); out["lines"].append(r)
json.dump(out, open("registers/era_residual_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r["outcome"] == "posted":
            reg.append({"checkid": CHECKID, "checkclaimid": None, "visitid": r["visitid"], "chargedetailid": r["chargedetailid"], "outcome": "posted", "pay": 0.0, "wo": EXPECT, "wocode": WOC, "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
L("done: %s" % {k: sum(1 for r in out["lines"] if r["outcome"].startswith(k)) for k in ("posted", "DRY", "HELD", "already", "FAULT", "skip")})
