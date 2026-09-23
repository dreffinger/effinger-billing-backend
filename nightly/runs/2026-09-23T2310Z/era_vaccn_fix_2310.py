# PLAIN ENGLISH (VA CCN ERA follow-up, 7pm ET 9/23/2026 run 2026-09-23T2310Z): the Optum VA CCN 835 check 1052821 (trace 3009447223,
#   $663.00, 8 hospital visits on pat17477706 / pat17477775) was posted by the ERA Center Post button WITH the CO-45 reason code but WITHOUT
#   the contractual write-off (payreasonwoamount 0 on the VACCN carrier ERA setup - the same defect as Florida Blue, corrected 9/18 and 9/23),
#   so each charge shows patient balance = fee - paid (7 x 39.10 + 150.30 = $424.00). A VA CCN veteran owes the community provider nothing.
# Decides, per posted charge (live read first): patient balance > 0 and no PR amount on the remit line -> move_to_ins.move(cid) (balance
#   back to insurance, no rebill) then manual_post pay 0 + WOINS = that balance with the VA check number and deposit date (the 9/18
#   'Contractual correction' recipe, era_fb_fix_1910.py part A). A charge whose patient balance is already 0 is left alone.
# Never touches: the payments themselves, insurance plans, referral plans / auths, hospitalization dates, any other visit.
"""Usage: python3 era_vaccn_fix_2310.py [--dry]"""
import amd, txh, move_to_ins, manual_post, json, time, sys
DRY = "--dry" in sys.argv; S = "2026-09-23T2310Z"; CK = "1052821"
amd.login_cached()
chk = {c["id"]: c for c in json.load(open("era_checks_before_%s.json" % S))}[int(CK)]
chkno = chk["paymentnumber"]; y, m, d = chk["depositdate"][:10].split("-"); dd = "%s/%s/%s" % (m, d, y)
det = json.load(open("era_details/%s.json" % CK))
out = {"stamp": S, "check": CK, "checknumber": chkno, "depositdate": dd, "dry": DRY, "lines": []}
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        res[c.get("id")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "cpt": c.get("proccode"), "dos": c.get("dos"),
                            "wos": [(w.get("id"), w.get("amount"), w.get("wocode"), w.get("void")) for w in c.iter("writeoff")]}
    return res
for c in det["eracheckdetails"]:
    pid, vid = str(c["patientid"]), str(c["visitid"])
    st = live(pid, vid); time.sleep(0.4)
    for l in c["charges"]:
        cid = str(l["chargedetailid"]); s = st.get(cid)
        pr = float(l.get("patientamount") or 0); adj = float(l.get("adjustmentamount") or 0)
        carcs = [x.get("reasoncode") or x.get("carccode") or x.get("code") for x in (l.get("carc") or [])]
        rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": l.get("chargecode"), "dos": c["dos"][:10], "remit_paid": l.get("paymentamount"), "remit_adj": adj, "remit_pr": pr, "carc": carcs, "live": s}
        if not s: rec["result"] = "charge not live"; out["lines"].append(rec); print(rec["result"], rec); continue
        wo = round(s["patbal"] - pr, 2)
        if s["patbal"] <= 0.005 or wo <= 0.005:
            rec["result"] = "patbal %.2f - nothing to correct" % s["patbal"]; out["lines"].append(rec); print("pat%s v%s c%s %s: %s" % (pid, vid, cid, s["cpt"], rec["result"]), flush=True); continue
        if any(w[3] != "1" and (w[2] or "").strip() == "WOINS" and abs(abs(float(w[1] or 0)) - wo) < 0.01 for w in s["wos"]):
            rec["result"] = "WOINS %.2f already on the charge" % wo; out["lines"].append(rec); print(rec["result"]); continue
        print("pat%s v%s c%s %s fee %.2f paid %.2f patbal %.2f insbal %.2f remit CO45 %.2f PR %.2f -> move back + WOINS %.2f (check %s %s)" % (pid, vid, cid, s["cpt"], s["fee"], s["paid"], s["patbal"], s["insbal"], adj, pr, wo, chkno, dd), flush=True)
        rec["wo"] = wo
        if DRY: rec["result"] = "DRY"; out["lines"].append(rec); continue
        mv = move_to_ins.move(cid); rec["move"] = str(mv)[:120]; print("   move_to_ins -> %s" % str(mv)[:120], flush=True); time.sleep(0.6)
        ok, msg = manual_post.post(cid, "VACCN", 0.0, wo, "WOINS", checknumber=chkno, depositdate=dd, note="ERA %s VA CCN CO-45 contractual correction run %s" % (CK, S))
        rec["post"] = (ok, str(msg)[:160]); print("   manual_post WOINS %.2f -> %s %s" % (wo, ok, str(msg)[:120]), flush=True); time.sleep(0.6)
        s2 = live(pid, vid).get(cid); rec["after"] = {k: s2[k] for k in ("patbal", "insbal", "paid")} if s2 else None; print("   after:", rec["after"], flush=True)
        out["lines"].append(rec)
json.dump(out, open("registers/era_vaccn_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
print("DONE", "dry" if DRY else "live", sum(1 for r in out["lines"] if r.get("wo")), "corrections", round(sum(r.get("wo", 0) for r in out["lines"]), 2))
