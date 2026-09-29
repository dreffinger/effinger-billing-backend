# PLAIN ENGLISH (7am ET 9/29/2026 run 2026-09-29T1110Z): the ERA Center Post button posted Medicare ACH 819872046 (ERA 1052872, $2,797.29,
#   32 claims / 39 lines) with the CO-45/CO-253 reasons on each payment but payreasonwoamount 0, so every posted charge still carries the
#   contractual on its insurance balance (or, on the 4 charts with no secondary, on the patient balance) - the 9/23 CO-45 defect, now on Medicare.
#   Correction per line: WOINS = the remit's CO amounts (CO45 + CO253), check number = the ERA trace, deposit date = the check date; the PR-2
#   coinsurance is never written off (it crosses to the secondary or stays as the patient's). Lines whose balance sits on the patient are moved
#   back to insurance first (move_to_ins.move) so the write-off applies to the insurance balance; AMD returns the PR-2 to the patient on its own.
#   PART B: six $0 CO-29 lines on the Medicare NON remit 350011571 (ERA 1052873) are frequency-1 resubmissions (9/22) of visits Medicare had
#   already PAID on 9/9/2026 (checks 815876983 / 815906990 / 816846022) whose CO-45 was never written off either: WOINS = insbal - PR2 with
#   PR2 = 20% of allowed and allowed = paid / 0.784 (80% less the 2% sequestration) - the same numbers the sibling lines carry (33.76 / 43.80).
# Rules: --dry = read only; refuses any line whose live balance does not equal CO + PR (left for review); 3 consecutive addpayments faults stop it.
# Never touches: payments, plans, PR amounts, other charts.
import amd, txh, move_to_ins, manual_post, json, sys, time
DRY = "--dry" in sys.argv; S = "2026-09-29T1110Z"
amd.login_cached()
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"),
                            "wos": [(w.get("amount"), w.get("wocode"), w.get("void"), w.get("date"), w.get("checknumber")) for w in c.iter("writeoff")]}
    return res
def L(m): print(m, flush=True)
out = {"stamp": S, "dry": DRY, "A": [], "B": []}
faults = 0
# ---- PART A: ERA 1052872 lines (from the check details + the live read taken at 11:35Z)
d = json.load(open("era_details/1052872.json"))["eracheckdetails"]
A = []
for v in d:
    for ch in v["charges"]:
        co = round(sum(c["reasonamt"] for c in ch.get("carc", []) if c["payreasongroup"] in ("CO", "OA")), 2)
        pr = round(sum(c["reasonamt"] for c in ch.get("carc", []) if c["payreasongroup"] == "PR"), 2)
        A.append((str(v["patientid"]), str(v["visitid"]), str(ch["chargedetailid"]), co, pr))
CHK = "819872046"; DD = "09/30/2026"
for pid, vid, cid, co, pr in A:
    st = live(pid, vid).get(cid)
    if not st: L("pat%s v%s c%s: not live" % (pid, vid, cid)); out["A"].append({"pid": pid, "vid": vid, "cid": cid, "result": "not live"}); continue
    rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": st["cpt"], "check": CHK, "co": co, "pr": pr, "before": {k: st[k] for k in ("fee", "paid", "patbal", "insbal")}}
    if any(w[1] and w[1].strip() == "WOINS" and w[2] != "1" and (w[4] or "") == CHK for w in st["wos"]):
        rec["result"] = "already corrected"; L("pat%s v%s c%s already corrected" % (pid, vid, cid)); out["A"].append(rec); continue
    bal = st["insbal"] + st["patbal"]
    if abs(bal - co - pr) > 0.02:
        rec["result"] = "balance %.2f != CO %.2f + PR %.2f - left for review" % (bal, co, pr); L("pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); out["A"].append(rec); continue
    need_move = st["patbal"] > 0.005
    L("pat%s v%s c%s %s fee %.2f paid %.2f insbal %.2f patbal %.2f -> %sWOINS %.2f (PR %.2f stays)" % (pid, vid, cid, st["cpt"], st["fee"], st["paid"], st["insbal"], st["patbal"], "move back + " if need_move else "", co, pr))
    rec["wo"] = co; rec["move"] = need_move
    if DRY: rec["result"] = "DRY"; out["A"].append(rec); continue
    if need_move:
        m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120]); time.sleep(0.8)
    ok, msg = manual_post.post(cid, "FLO02", 0.0, co, "WOINS", checknumber=CHK, depositdate=DD, note="ERA 1052872 contractual correction run %s" % S)
    rec["post"] = (ok, str(msg)[:160]); L("   manual_post WOINS %.2f -> %s %s" % (co, ok, str(msg)[:120]))
    faults = 0 if ok else faults + 1
    time.sleep(0.8); after = live(pid, vid).get(cid) or {}; rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "paid")}; L("   after patbal %s insbal %s" % (after.get("patbal"), after.get("insbal")))
    rec["result"] = "posted" if ok else "FAULT"; out["A"].append(rec)
    if faults >= 3: L("3 consecutive addpayments faults - stopping"); break
# ---- PART B: the six CO-29 lines of ERA 1052873 whose 9/9 Medicare payment never had its CO-45 written off
B = [("17470697", "19392264", "22464223", "815876983", 61.54), ("17470697", "19392365", "22464362", "815876983", 61.54),
     ("17470697", "19392381", "22464390", "815906990", 61.54), ("17470697", "19392525", "22464512", "815906990", 61.54),
     ("17468923", "19404007", "22478145", "816846022", 101.51), ("17470939", "19403870", "22477999", "816846022", 101.51)]
if faults < 3:
    for pid, vid, cid, chk, paid in B:
        st = live(pid, vid).get(cid)
        if not st: L("B pat%s v%s c%s: not live" % (pid, vid, cid)); continue
        allowed = round(paid / 0.784, 2); pr2 = round(allowed * 0.2, 2); wo = round(st["insbal"] - pr2, 2)
        rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": st["cpt"], "check": chk, "allowed": allowed, "pr2": pr2, "before": {k: st[k] for k in ("fee", "paid", "patbal", "insbal")}}
        if any(w[1] and w[1].strip() == "WOINS" and w[2] != "1" for w in st["wos"]) or st["insbal"] <= pr2 + 0.005:
            rec["result"] = "already corrected (insbal %.2f, PR2 %.2f)" % (st["insbal"], pr2); L("B pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); out["B"].append(rec); continue
        if abs(st["paid"] - paid) > 0.01 or abs(st["fee"] - allowed - (st["fee"] - allowed)) > 0.01 or wo <= 0 or abs((st["fee"] - allowed + round(paid * 0.02 / 0.98, 2)) - wo) > 0.05:
            rec["result"] = "paid %.2f / insbal %.2f do not fit the 80%%-less-sequestration formula (wo %.2f) - left for review" % (st["paid"], st["insbal"], wo); L("B pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); out["B"].append(rec); continue
        L("B pat%s v%s c%s %s fee %.2f paid %.2f insbal %.2f -> WOINS %.2f (PR2 %.2f stays) check %s" % (pid, vid, cid, st["cpt"], st["fee"], st["paid"], st["insbal"], wo, pr2, chk))
        rec["wo"] = wo
        if DRY: rec["result"] = "DRY"; out["B"].append(rec); continue
        ok, msg = manual_post.post(cid, "FLO02", 0.0, wo, "WOINS", checknumber=chk, depositdate="09/09/2026", note="ERA %s (9/9/2026 remit) contractual correction run %s; the 9/22 resubmission answered CO-29 on ERA 1052873" % (chk, S))
        rec["post"] = (ok, str(msg)[:160]); L("   manual_post WOINS %.2f -> %s %s" % (wo, ok, str(msg)[:120]))
        faults = 0 if ok else faults + 1
        time.sleep(0.8); after = live(pid, vid).get(cid) or {}; rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "paid")}; L("   after patbal %s insbal %s" % (after.get("patbal"), after.get("insbal")))
        rec["result"] = "posted" if ok else "FAULT"; out["B"].append(rec)
        if faults >= 3: L("3 consecutive addpayments faults - stopping"); break
json.dump(out, open("registers/era_co45_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
n = sum(1 for r in out["A"] + out["B"] if r.get("result") in ("posted", "DRY")); t = sum(r.get("wo", 0) for r in out["A"] + out["B"] if r.get("result") in ("posted", "DRY"))
L("SUMMARY %s: %d lines WOINS $%.2f; review %d" % ("DRY" if DRY else "LIVE", n, t, sum(1 for r in out["A"] + out["B"] if "review" in str(r.get("result")))))
