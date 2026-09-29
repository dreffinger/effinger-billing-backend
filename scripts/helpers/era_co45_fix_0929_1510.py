# PLAIN ENGLISH (11am ET 9/29/2026 run 2026-09-29T1510Z): the ERA Center Post button posted CAP07 check 4124256 (ERA 1052877, 23 money lines
#   $1,708.46) with the CO-45 / CO-253 reason on each payment but payreasonwoamount 0 (the 9/23-9/25 CHP/UHC/Florida Blue defect), so each
#   posted charge can show patient balance = fee - paid. PR amounts on every money line are 0, so any patient balance left is contractual.
#   For each money line whose live patient balance > 0: move_to_ins.move(cid) (balance back to insurance, no rebill) then manual_post pay 0 +
#   WOINS = the open balance, with the check number 4124256 and deposit date 09/29/2026. The 5 $0 claims (PR-200 x3, CO-A1, CO-29) that
#   era_clear zero-posted: if the zero-post pushed the charge to the patient balance, move it back (move only - the denial handling decides).
# Never touches: lines already at $0 both sides, plans, other charts. --dry = read only. Register registers/era_co45_fix_2026-09-29T1510Z.json
import amd, txh, move_to_ins, manual_post, json, sys, time
DRY = "--dry" in sys.argv; S = "2026-09-29T1510Z"; CK = 1052877; CHKNO = "4124256"; DD = "09/29/2026"
amd.login_cached()
det = json.load(open("era_details/%d.json" % CK))["eracheckdetails"]
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        res[c.get("id")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"),
                            "pays": [(p.get("amount"), p.get("checknumber"), p.get("void")) for p in c.iter("payment")],
                            "wos": [(w.get("amount"), w.get("wocode"), w.get("void")) for w in c.iter("writeoff")]}
    return res
out = {"stamp": S, "dry": DRY, "money": [], "zero": []}
def L(m): print(m, flush=True)
for cl in det:
    pid = str(cl["patientid"]); vid = str(cl["visitid"]); st = live(pid, vid); time.sleep(0.3)
    for ch in cl["charges"]:
        cid = str(ch["chargedetailid"]); s = st.get("charge" + cid) or st.get(cid)
        if not s: L("v%s pat%s c%s NOT LIVE (keys %s)" % (vid, pid, cid, list(st)[:3])); continue
        paid = float(ch["paymentamount"] or 0)
        rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": s["cpt"], "fee": s["fee"], "live_paid": s["paid"], "patbal": s["patbal"], "insbal": s["insbal"], "era_paid": paid, "pays": s["pays"], "wos": s["wos"]}
        if paid > 0:
            if s["patbal"] <= 0.005 and s["insbal"] <= 0.005: rec["result"] = "already $0"; out["money"].append(rec); L("M v%s pat%s c%s %s already $0 (paid %.2f)" % (vid, pid, cid, s["cpt"], s["paid"])); continue
            wo = round(s["patbal"] + s["insbal"], 2)
            L("M v%s pat%s c%s %s fee %.2f paid %.2f patbal %.2f insbal %.2f -> move back + WOINS %.2f" % (vid, pid, cid, s["cpt"], s["fee"], s["paid"], s["patbal"], s["insbal"], wo))
            rec["wo"] = wo
            if DRY: rec["result"] = "DRY"; out["money"].append(rec); continue
            if s["patbal"] > 0.005:
                m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120]); time.sleep(0.6)
            ok, msg = manual_post.post(cid, "CAP07", 0.0, wo, "WOINS", checknumber=CHKNO, depositdate=DD, note="ERA %d contractual correction run %s" % (CK, S)); rec["post"] = (ok, str(msg)[:160]); L("   manual_post WOINS %.2f -> %s %s" % (wo, ok, str(msg)[:120]))
            rec["result"] = "corrected" if ok else "FAULT"; out["money"].append(rec); time.sleep(0.6)
        else:
            L("Z v%s pat%s c%s %s fee %.2f paid %.2f patbal %.2f insbal %.2f pays=%s" % (vid, pid, cid, s["cpt"], s["fee"], s["paid"], s["patbal"], s["insbal"], s["pays"]))
            if s["patbal"] > 0.005 and not DRY:
                m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120]); time.sleep(0.6); rec["result"] = "moved back"
            else: rec["result"] = "DRY" if DRY else "on insurance"
            out["zero"].append(rec)
json.dump(out, open("registers/era_co45_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
L("done: money %d zero %d" % (len(out["money"]), len(out["zero"])))
