# PLAIN ENGLISH (9am ET 10/2/2026 run 2026-10-02T1310Z): the ERA Center Post button posted Centene/WellCare ACH 1008831190 (ERA 1052930,
#   $165.90, 2 claims / 2 lines, 99309 9/24/2026 on pat17476739 + pat12182947) with the CO-45 + PI-253 reasons on each payment but
#   payreasonwoamount 0 - the 9/23 CO-45 defect (Florida Blue / VA CCN / Humana / Medicare / now Centene): the contractual stays on the
#   balance instead of being written off. Correction per line: WOINS = the remit's CO + PI amounts (56.36 + 1.69 = 58.05), check number =
#   the ERA trace, deposit date = the check date; PR amounts (none here) are never written off. A line whose balance sits on the patient is
#   moved back to insurance first (move_to_ins.move). Same shape as era_co45_fix_1110.py (9/29).
# Rules: --dry = read only; refuses any line whose live balance does not equal CO + PI + PR; skips a line already carrying a WOINS with this
#   check number; 3 consecutive addpayments faults stop it.
# Never touches: payments, plans, PR amounts, other charts.
import amd, txh, move_to_ins, manual_post, json, sys, time
DRY = "--dry" in sys.argv; S = "2026-10-02T1310Z"; CHECKID = "1052930"; CAR = "WEL04"; CHK = "1008831190"; DD = "10/01/2026"
amd.login_cached()
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"),
                            "pays": [(p.get("amount"), p.get("checknumber"), p.get("void")) for p in c.iter("payment")],
                            "wos": [(w.get("amount"), w.get("wocode"), w.get("void"), w.get("date"), w.get("checknumber")) for w in c.iter("writeoff")]}
    return res
def L(m): print(m, flush=True)
out = {"stamp": S, "dry": DRY, "checkid": CHECKID, "lines": []}
faults = 0
d = json.load(open("era_details/%s.json" % CHECKID))["eracheckdetails"]
for v in d:
    for ch in v["charges"]:
        pid, vid, cid = str(v["patientid"]), str(v["visitid"]), str(ch["chargedetailid"])
        co = round(sum(c["reasonamt"] for c in ch.get("carc", []) if c["payreasongroup"] in ("CO", "OA", "PI")), 2)
        pr = round(sum(c["reasonamt"] for c in ch.get("carc", []) if c["payreasongroup"] == "PR"), 2)
        st = live(pid, vid).get(cid)
        if not st: L("pat%s v%s c%s: not live" % (pid, vid, cid)); out["lines"].append({"pid": pid, "vid": vid, "cid": cid, "result": "not live"}); continue
        rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": st["cpt"], "check": CHK, "co": co, "pr": pr, "before": {k: st[k] for k in ("fee", "paid", "patbal", "insbal")}, "pays": st["pays"]}
        if not any((p[1] or "") == CHK and p[2] != "1" for p in st["pays"]):
            rec["result"] = "payment with check %s not on the charge yet - left" % CHK; L("pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); out["lines"].append(rec); continue
        if any(w[1] and w[1].strip() == "WOINS" and w[2] != "1" and (w[4] or "") == CHK for w in st["wos"]):
            rec["result"] = "already corrected"; L("pat%s v%s c%s already corrected" % (pid, vid, cid)); out["lines"].append(rec); continue
        bal = st["insbal"] + st["patbal"]
        if abs(bal - co - pr) > 0.02:
            rec["result"] = "balance %.2f != CO/PI %.2f + PR %.2f - left for review" % (bal, co, pr); L("pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); out["lines"].append(rec); continue
        need_move = st["patbal"] > 0.005
        L("pat%s v%s c%s %s fee %.2f paid %.2f insbal %.2f patbal %.2f -> %sWOINS %.2f (PR %.2f stays)" % (pid, vid, cid, st["cpt"], st["fee"], st["paid"], st["insbal"], st["patbal"], "move back + " if need_move else "", co, pr))
        rec["wo"] = co; rec["move"] = need_move
        if DRY: rec["result"] = "DRY"; out["lines"].append(rec); continue
        if need_move:
            m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120]); time.sleep(0.8)
        ok, msg = manual_post.post(cid, CAR, 0.0, co, "WOINS", checknumber=CHK, depositdate=DD, note="ERA %s contractual correction run %s" % (CHECKID, S))
        rec["post"] = (ok, str(msg)[:160]); L("   manual_post WOINS %.2f -> %s %s" % (co, ok, str(msg)[:120]))
        faults = 0 if ok else faults + 1
        time.sleep(0.8); after = live(pid, vid).get(cid) or {}; rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "paid")}; L("   after patbal %s insbal %s" % (after.get("patbal"), after.get("insbal")))
        rec["result"] = "posted" if ok else "FAULT"; out["lines"].append(rec)
        if faults >= 3: L("3 consecutive addpayments faults - stopping"); break
json.dump(out, open("registers/era_co45_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
n = sum(1 for r in out["lines"] if r.get("result") in ("posted", "DRY")); t = sum(r.get("wo", 0) for r in out["lines"] if r.get("result") in ("posted", "DRY"))
L("SUMMARY %s: %d lines WOINS $%.2f; review %d" % ("DRY" if DRY else "LIVE", n, t, sum(1 for r in out["lines"] if "review" in str(r.get("result")) or "left" in str(r.get("result")))))
