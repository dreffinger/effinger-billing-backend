# PLAIN ENGLISH (ERA Post-button CO-45 correction by VOID + ERA-LINKED RE-POST - first used 7 AM ET 10/6/2026, run 2026-10-06T1110Z)
# Decides: nothing new - applies the 9/23 CO-45 lesson to a check the ERA Center Post button (posterapayments) just posted: AMD put the
#   CO45 / CO253 reasons on each payment but payreasonwoamount 0, so the contractual stays on the balance (insurance side when the chart
#   has a secondary, PATIENT side when it has none - the 9/23 defect). Instead of a bare manual_post write-off (which adds a $0 code-less
#   payment and lands the visit in Unbilled 'Payment reason codes are missing or do not balance' - the 9/21 and 10/6 0510Z lesson), each
#   line is corrected the proven way the repair flow uses: VOID the Post-button payment (void_tx.void_payment) and RE-POST the same remit
#   line through the ERA-linked Payment Entry shape (payreasons.post_line = addpayments postingmethod=era + eraclaimid/erareportid + the
#   remit's reasonlist + WOINS for the CO/OA/PI amounts). PR amounts are never written off - they stay for the secondary or the patient.
# Reads first: era_details/<checkid>.json (the remit), the check meta saved before the post, every visit's live charges and payments.
# Skips: a charge that already carries a non-void WOINS of the CO amount, a charge with no payment carrying this check number, a charge
#   whose live remainder is not fee - paid (something else happened on it - listed for review).
# Writes (only with --live): per line ONE void + ONE ERA-linked addpayments; --first-only does the first line and stops so it can be
#   verified; 3 consecutive faults stop the run. Register: registers/era_co45_relink_<checkid>_<stamp>[ _dry].json
# Never touches: PR amounts, plans, claims, other checks, charges not on the remit.
# Usage: cd /home/claude/unbilled && python3 era_co45_relink.py <checkid> [--meta <era_checks json>] [--live] [--first-only] [--cid <chargeid>]
#   A line whose remainder sits on the PATIENT (chart without a secondary) is moved back to insurance after the void (move_to_ins.move, no rebill) before the re-post.
import amd, payreasons, void_tx, move_to_ins, json, sys, time, datetime, re

a = sys.argv[1:]
CHECKID = next((x for x in a if x.isdigit()), None)
LIVE = "--live" in a; FIRST = "--first-only" in a
META = a[a.index("--meta") + 1] if "--meta" in a else None
ONLY_CID = a[a.index("--cid") + 1] if "--cid" in a else None   # correct one charge only (re-run of a line the first pass left)
if not CHECKID:
    print("usage: python3 era_co45_relink.py <checkid> [--meta <era_checks json>] [--live] [--first-only]"); sys.exit(2)
STAMP = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
def L(m): print(m, flush=True)

amd.login_cached()
d = json.load(open("era_details/%s.json" % CHECKID))["eracheckdetails"]
chk = None
if META:
    chk = next((c for c in json.load(open(META)) if str(c["id"]) == CHECKID), None)
if not chk: chk = payreasons.check_meta(CHECKID, d[0] if d else None)
CHK = str(chk.get("paymentnumber") or "")
L("check %s %s %s amount %s deposit %s - %d claims" % (CHECKID, chk.get("systemcarriercode"), CHK, chk.get("paymentamount"), chk.get("depositdate"), len(d)))
reg = {"stamp": STAMP, "checkid": CHECKID, "checknumber": CHK, "live": LIVE, "lines": []}
faults = 0; done = 0; tot_pay = 0.0; tot_wo = 0.0

for v in d:
    pid = str(v["patientid"]); vid = str(v["visitid"])
    for ch in v.get("charges", []):
        cid = str(ch.get("chargedetailid")); paid = payreasons.f(ch.get("paymentamount"))
        if int(ch.get("chargedetailid") or -1) <= 0 or paid <= 0: continue
        if ONLY_CID and cid != ONLY_CID: continue
        co = round(sum(payreasons.f(x.get("reasonamt")) for x in ch.get("carc", []) if str(x.get("payreasongroup")).upper() in ("CO", "OA", "PI")), 2)
        pr = round(sum(payreasons.f(x.get("reasonamt")) for x in ch.get("carc", []) if str(x.get("payreasongroup")).upper() == "PR"), 2)
        st = payreasons.visit_state(pid, vid); live = [c for c in st if c["cid"] == cid]
        rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": ch.get("chargecode"), "paid": paid, "co": co, "pr": pr}
        if not live:
            rec["result"] = "not live"; reg["lines"].append(rec); L("pat%s v%s c%s not live" % (pid, vid, cid)); continue
        c = live[0]; rec["before"] = {k: c[k] for k in ("fee", "paid", "insbalance", "patbalance", "carrier")}
        pays = [p for p in c["pays"] if p["void"] != "1" and p["checkno"] == CHK]
        wos = [w for w in c["wos"] if w["void"] != "1" and w["code"].strip() == "WOINS" and abs(w["amount"] - co) < 0.011]
        if wos:
            rec["result"] = "already corrected"; reg["lines"].append(rec); L("pat%s v%s c%s already corrected (WOINS %.2f)" % (pid, vid, cid, co)); continue
        if not pays:
            rec["result"] = "no payment with check %s on the charge - left" % CHK; reg["lines"].append(rec); L("pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); continue
        p = pays[0]; remainder = round(c["insbalance"] + c["patbalance"], 2)
        if abs(p["amount"] - paid) > 0.011 or abs(remainder - (c["fee"] - paid)) > 0.011:
            rec["result"] = "payment %.2f / remainder %.2f do not match the remit (paid %.2f, fee %.2f) - left for review" % (p["amount"], remainder, paid, c["fee"])
            reg["lines"].append(rec); L("pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); continue
        rec["payid"] = p["id"]
        L("pat%s v%s c%s %s fee %.2f paid %.2f insbal %.2f patbal %.2f -> void pay %s, re-post pay %.2f + WOINS %.2f (PR %.2f stays)"
          % (pid, vid, cid, c["cpt"], c["fee"], paid, c["insbalance"], c["patbalance"], p["id"], paid, co, pr))
        if not LIVE:
            rec["result"] = "DRY"; reg["lines"].append(rec); continue
        ok, msg = void_tx.void_payment(pid, cid, p["id"]); rec["void"] = (ok, str(msg)[:160]); L("   void -> %s %s" % (ok, str(msg)[:100]))
        if not ok:
            faults += 1; rec["result"] = "VOID FAULT"; reg["lines"].append(rec)
            if faults >= 3: L("3 consecutive faults - stopping"); break
            continue
        time.sleep(1.0)
        if c["patbalance"] > 0.005:
            # the Post button had moved the remainder to the PATIENT (chart with no secondary): after the void only the paid amount comes back
            # to the insurance side, so the write-off would be capped at 0 - move the patient-side balance back first (no seq = no rebill)
            mv = move_to_ins.move(cid); rec["move_back"] = str(mv)[:160]; L("   move_to_ins (patient -> insurance) -> %s" % str(mv)[:100]); time.sleep(1.0)
        try:
            ok2, payid, head = payreasons.post_line(pid, vid, chk, v, cid, ch)
        except Exception as e:
            ok2, payid, head = False, "", "EXC " + str(e)[:160]
        rec["post"] = (ok2, payid, head[:160]); L("   ERA-linked re-post -> %s payid %s %s" % (ok2, payid, head[:100]))
        time.sleep(1.0)
        after = [c2 for c2 in payreasons.visit_state(pid, vid) if c2["cid"] == cid]
        if after:
            c2 = after[0]; rec["after"] = {k: c2[k] for k in ("fee", "paid", "insbalance", "patbalance")}
            rec["after"]["pays"] = [(q["id"], q["amount"], q["checkno"], q["reasons"]) for q in c2["pays"] if q["void"] != "1"]
            rec["after"]["wos"] = [(w["code"], w["amount"]) for w in c2["wos"] if w["void"] != "1"]
            good = ok2 and any(q["void"] != "1" and abs(q["amount"] - paid) < 0.011 and q["reasons"] for q in c2["pays"]) \
                   and any(w["void"] != "1" and w["code"].strip() == "WOINS" and abs(w["amount"] - co) < 0.011 for w in c2["wos"]) \
                   and abs((c2["insbalance"] + c2["patbalance"]) - pr) < 0.011
            L("   after: paid %.2f insbal %.2f patbal %.2f wos %s -> %s" % (c2["paid"], c2["insbalance"], c2["patbalance"], rec["after"]["wos"], "OK" if good else "CHECK"))
        else:
            good = False
        rec["result"] = "corrected" if good else ("posted-unverified" if ok2 else "POST FAULT")
        if ok2: faults = 0; done += 1; tot_pay += paid; tot_wo += co
        else:
            faults += 1
        reg["lines"].append(rec)
        if faults >= 3: L("3 consecutive faults - stopping"); break
        if FIRST: L("--first-only: stopping after the first line"); break
    else:
        continue
    break

json.dump(reg, open("registers/era_co45_relink_%s_%s%s.json" % (CHECKID, STAMP, "" if LIVE else "_dry"), "w"), indent=1)
n_dry = sum(1 for r in reg["lines"] if r.get("result") == "DRY")
L("SUMMARY %s check %s: %s lines; corrected %d (pay $%.2f re-posted, WOINS $%.2f); review/left %d"
  % ("DRY" if not LIVE else "LIVE", CHECKID, n_dry if not LIVE else len(reg["lines"]), done, tot_pay, tot_wo,
     sum(1 for r in reg["lines"] if "left" in str(r.get("result")) or "FAULT" in str(r.get("result")) or "unverified" in str(r.get("result")))))
