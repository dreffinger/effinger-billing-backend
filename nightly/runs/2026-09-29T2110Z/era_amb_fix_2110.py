# PLAIN ENGLISH (Ambetter ERA 0934787936 = check 1052884, run 2026-09-29T2110Z): the ERA Center Post button posted the 5 claims / 9 lines
#   ($736.73) with the CO-45 reasons on each payment but payreasonwoamount 0, so every charge now shows the contractual on the PATIENT
#   balance (the 9/23 CO-45 defect, seen on Ambetter too). Correction per line, from the LIVE charge: move the patient balance back to
#   insurance (move_to_ins.move), then WOINS = the remit's CO-45 with the Ambetter trace number and check date (manual_post pay 0);
#   the one PR-2 coinsurance line (24.21, chart has Ambetter only) is left for AMD to return to the patient. A line is touched only when
#   its patient balance equals CO-45 (+ PR-2) exactly; 3 consecutive faults stop the pass.  Then: dismiss the fully posted checks
#   1052883 (AARP/UHC), 1052887 (AARP mapped to FLO99) and 1052884 from the ERA Center and re-read the unposted list.
# Never touches: the Sunshine check 1052885 (left on the list - its hand-posting was declined this slot), payments, plans.
import amd, txh, move_to_ins, manual_post, era_post, requests, json, time, sys
S = "2026-09-29T2110Z"; CHKNO = "0934787936"; DD = "09/29/2026"
amd.login_cached()
det = json.load(open("era_details/1052884.json"))["eracheckdetails"]
out = {"stamp": S, "lines": [], "dismiss": {}}; faults = 0
def L(m): print(m, flush=True)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"cpt": c.get("proccode"), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0),
            "wos": [((w.get("wocode") or "").strip(), (w.get("checknumber") or "").strip(), w.get("void")) for w in c.iter("writeoff")]}
    return res
for v in det:
    pid = str(v["patientid"]); vid = str(v["visitid"])
    for ch in v["charges"]:
        cid = str(ch["chargedetailid"])
        co = round(sum(float(a["reasonamt"]) for a in ch.get("carc", []) if a["payreasongroup"] in ("CO", "OA")), 2)
        pr = round(sum(float(a["reasonamt"]) for a in ch.get("carc", []) if a["payreasongroup"] == "PR"), 2)
        st = live(pid, vid).get(cid); rec = {"pid": pid, "vid": vid, "cid": cid, "co": co, "pr": pr, "before": st}
        if not st: rec["result"] = "not live"; out["lines"].append(rec); continue
        if any(w[0] == "WOINS" and w[1] == CHKNO and w[2] != "1" for w in st["wos"]): rec["result"] = "already corrected"; out["lines"].append(rec); continue
        if abs(st["patbal"] + st["insbal"] - co - pr) > 0.02: rec["result"] = "balance %.2f != CO %.2f + PR %.2f - left" % (st["patbal"] + st["insbal"], co, pr); L("pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); out["lines"].append(rec); continue
        if faults >= 3: rec["result"] = "not attempted (3 faults)"; out["lines"].append(rec); continue
        L("pat%s v%s c%s %s patbal %.2f -> move back + WOINS %.2f (PR %.2f stays)" % (pid, vid, cid, st["cpt"], st["patbal"], co, pr))
        if st["patbal"] > 0.005:
            m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:100]); time.sleep(0.8)
        ok, msg = manual_post.post(cid, "AMB03", 0.0, co, "WOINS", checknumber=CHKNO, depositdate=DD, note="ERA 1052884 contractual correction run %s" % S)
        rec["post"] = (ok, str(msg)[:140]); faults = 0 if ok else faults + 1; L("   WOINS %.2f -> %s %s" % (co, ok, str(msg)[:100]))
        time.sleep(0.8); rec["after"] = live(pid, vid).get(cid); rec["result"] = "corrected" if ok else "FAULT"; L("   after %s" % rec["after"])
        out["lines"].append(rec)
# ---- dismiss the settled checks
for cid in ("1052883", "1052887", "1052884"):
    r = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(cid)), timeout=60)
    out["dismiss"][cid] = (r.status_code, r.text[:120]); L("dismiss %s -> %s %s" % (cid, r.status_code, r.text[:100])); time.sleep(0.5)
after = era_post.checks(); out["era_after"] = [(c["id"], c["systemcarriercode"], c["paymentnumber"], c["paymentamount"], c["unpostedamount"]) for c in after]
L("ERA Center after: %s" % out["era_after"])
json.dump(out, open("registers/era_amb_fix_%s.json" % S, "w"), indent=1, default=str)
