# PLAIN ENGLISH (Medicare ERA check 1053023 / payment 819928855 - contractual correction by the WRITE-OFF RECIPE, prepared by the
#   9 AM ET 10/7/2026 run 2026-10-07T1310Z as the successor of approval card A-2026-10-07T1110Z-A)
# Why a new helper: the approved card's command (era_co45_relink.py 1053023 --live = void the Post-button payment + ERA-linked re-post)
#   needs the remit detail, and GET /api/era/checkdetails for 1053023 now answers only the 4 unposted claims - the 208 posted claims
#   dropped out after the Post button (the same PROCESSED-check condition the cascade session met on the 9/9 remits this morning). The
#   7 AM run's dry register registers/era_co45_relink_1053023_2026-10-07T1129Z_dry.json holds every line (chart, visit, charge, CPT,
#   Post-button payment id, paid, CO, PR, balances before) - it is the line list here; the live chart is re-read before every line.
# Decides: nothing new - the chat session's proven 10/7 recipe (docs/SHARED_LESSONS.md 2026-10-07T1300Z FIX, fix_inflated_wo_1007.py):
#   the live Post-button payment already carries balanced CO45 / CO253 / PR reasons; only the WOINS is missing. Per line:
#     1. manual_post.post(cid, "FLO02", 0, CO, "WOINS", checknumber = 819928855, depositdate = 10/08/2026)   (captured addpayments shape)
#     2. void the $0 code-less payment that addpayments adds beside the write-off (void_tx.void_payment) - the WOINS survives the void
#     3. verify live: a non-void WOINS of the CO amount, no non-void code-less payment, payreasons.balanced() True, insbal + patbal = PR
#   Guards per line (dry and live): the Post-button payment (payid) is live with reasons; no non-void WOINS on the charge yet;
#   fee - paid == CO + PR; the open INSURANCE balance >= CO (manual_post refuses over-apply). Lines whose contractual was parked on the
#   PATIENT side by the Post button (charts with no secondary - insbalance < CO) are LISTED for review, not written: moving the patient
#   balance back and writing off would leave the PR on the insurance side of a chart with nothing to bill it to.
# Writes (only with --live): per line ONE addpayments (WOINS) + ONE void; --first-only stops after the first corrected line; 3 consecutive
#   faults stop the run. Register registers/era_1053023_wo_2026-10-07T1310Z[_dry].json. Never touches: PR amounts, the payments with
#   reasons (never voided), plans, insurance order, the 4 unposted $0-balance claims (v19453207/19453499/19453703/19453717), the line already
#   corrected at 11:35Z (charge 23354307).
# Usage: cd /home/claude/unbilled && python3 era_1053023_wo_1310.py [--live] [--first-only] [--max N]
import amd, payreasons, manual_post, void_tx, txh, json, sys, time
a = sys.argv[1:]; LIVE = "--live" in a; FIRST = "--first-only" in a
MAX = int(a[a.index("--max") + 1]) if "--max" in a else 10**9
S = "2026-10-07T1310Z"; CHECK = "1053023"; PAYNUM = "819928855"; DEPOSIT = "10/08/2026"; SKIP_CIDS = {"23354307"}
SRC = "registers/era_co45_relink_1053023_2026-10-07T1129Z_dry.json"
amd.login_cached()
lines = [l for l in json.load(open(SRC))["lines"] if l.get("result") == "DRY" and str(l["cid"]) not in SKIP_CIDS]
out = {"stamp": S, "check": CHECK, "paymentnumber": PAYNUM, "live": LIVE, "source": SRC, "lines": [], "summary": {}}
def L(m): print(m, flush=True)
roots = {}; faults = 0; done = 0; totals = {"planned": 0, "co": 0.0, "corrected": 0, "co_done": 0.0, "review": 0, "co_review": 0.0, "already": 0, "skip": 0}
def state(pid, vid, fresh=False):
    if fresh or pid not in roots: roots[pid] = txh.fetch(pid)
    return payreasons.visit_state(pid, vid, roots[pid])
for l in lines:
    if done >= MAX: break
    pid, vid, cid, co, pr, paid, payid = str(l["pid"]), str(l["vid"]), str(l["cid"]), round(float(l["co"]), 2), round(float(l["pr"]), 2), round(float(l["paid"]), 2), str(l.get("payid") or "")
    rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": l.get("cpt"), "paid": paid, "co": co, "pr": pr, "payid": payid}
    try:
        st = state(pid, vid); c = [x for x in st if x["cid"] == cid]
        if not c: rec["result"] = "SKIP - charge not live"; totals["skip"] += 1; out["lines"].append(rec); L(rec); continue
        c = c[0]; rec["live"] = {"fee": c["fee"], "paid": c["paid"], "insbalance": c["insbalance"], "patbalance": c["patbalance"]}
        pay = [p for p in c["pays"] if p["void"] != "1" and p["id"] == payid]
        woins = [w for w in c["wos"] if w["void"] != "1" and w["code"].strip() == "WOINS"]
        if woins: rec["result"] = "already corrected - WOINS %s live" % [(w["id"], w["amount"]) for w in woins]; totals["already"] += 1; out["lines"].append(rec); L(rec); continue
        if not pay or not pay[0]["reasons"]: rec["result"] = "SKIP - Post-button payment %s not live with reasons" % payid; totals["skip"] += 1; out["lines"].append(rec); L(rec); continue
        if abs((c["fee"] - c["paid"]) - (co + pr)) > 0.02: rec["result"] = "REVIEW - fee %.2f - paid %.2f != CO %.2f + PR %.2f" % (c["fee"], c["paid"], co, pr); totals["review"] += 1; totals["co_review"] += co; out["lines"].append(rec); L(rec); continue
        if c["insbalance"] + 0.005 < co: rec["result"] = "REVIEW - contractual parked on the PATIENT side (insbalance %.2f < CO %.2f, patbalance %.2f) - no-secondary chart; needs the void + ERA-linked re-post" % (c["insbalance"], co, c["patbalance"]); totals["review"] += 1; totals["co_review"] += co; out["lines"].append(rec); L(rec); continue
        totals["planned"] += 1; totals["co"] += co
        if not LIVE: rec["result"] = "DRY: manual_post WOINS %.2f (check %s, deposit %s) then void the $0 code-less payment; expected after: insbal+patbal = PR %.2f" % (co, PAYNUM, DEPOSIT, pr); out["lines"].append(rec); L(rec); continue
        if faults >= 3: rec["result"] = "STOPPED - 3 consecutive faults"; out["lines"].append(rec); L(rec); continue
        ok, msg = manual_post.post(cid, "FLO02", 0.0, co, "WOINS", checknumber=PAYNUM, depositdate=DEPOSIT, note="ERA %s contractual CO45/CO253 left by the Post button - WOINS per card A-%s (write-off recipe)" % (CHECK, S))
        rec["post"] = [ok, str(msg)[:160]]
        if not ok: rec["result"] = "FAULT post"; faults += 1; out["lines"].append(rec); L(rec); time.sleep(1); continue
        time.sleep(1.0); st2 = state(pid, vid, fresh=True); c2 = [x for x in st2 if x["cid"] == cid][0]
        zero = [p for p in c2["pays"] if p["void"] != "1" and not p["reasons"] and abs(p["amount"]) < 0.005]
        rec["void"] = []
        for p in zero:
            vok, vmsg = void_tx.void_payment(pid, cid, p["id"]); rec["void"].append([p["id"], vok, str(vmsg)[:100]]); time.sleep(0.6)
        st3 = state(pid, vid, fresh=True); c3 = [x for x in st3 if x["cid"] == cid][0]
        w3 = [w for w in c3["wos"] if w["void"] != "1" and w["code"].strip() == "WOINS"]
        z3 = [p for p in c3["pays"] if p["void"] != "1" and not p["reasons"]]
        good = bool(w3) and abs(sum(w["amount"] for w in w3) - co) < 0.011 and not z3 and payreasons.balanced(st3) and abs((c3["insbalance"] + c3["patbalance"]) - pr) < 0.02
        rec["after"] = {"insbalance": c3["insbalance"], "patbalance": c3["patbalance"], "woins": [(w["id"], w["amount"]) for w in w3], "codeless": [p["id"] for p in z3], "balanced": payreasons.balanced(st3)}
        rec["result"] = "corrected" if good else "posted-unverified"
        if good: totals["corrected"] += 1; totals["co_done"] += co; faults = 0; done += 1
        else: faults += 1
        out["lines"].append(rec); L(rec); time.sleep(0.8)
        if FIRST: break
    except Exception as e:
        rec["result"] = "ERROR %s" % e; faults += 1; out["lines"].append(rec); L(rec)
out["summary"] = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in totals.items()}
fn = "registers/era_1053023_wo_%s%s.json" % (S, "" if LIVE else "_dry")
json.dump(out, open(fn, "w"), indent=1)
L("SUMMARY %s check %s: %s -> %s" % ("LIVE" if LIVE else "DRY", CHECK, out["summary"], fn))
