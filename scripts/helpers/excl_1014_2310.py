# PLAIN ENGLISH (Exclusions column, 7 PM ET 10/14/2026 run 2026-10-14T2310Z): claim run 1700297 brought two NEW UNITED HEALTHCARE
#   (UNI20) payer rejections on chart 17471600 - 'ACK, RETURNED AS UNPROCESSABLE CLAIM' on v19451930 (99223 8/17/2026) and v19452051
#   (99232 8/18/2026), the 10/13 BILL-SECONDARY sends. Live read this run: BOTH visits already carry the PRIMARY's payment - MERITAIN
#   HEALTH (MER01, seq 2, AMD 271 ACTIVE since 08/29/2025) paid 230.10 (CO-45 22.37 / PR-2 57.53) and 88.80 (PR-2 22.20) on 10/05/2026,
#   check 415094527. The UNI20 plan (seq 1) answers INACTIVE on AMD's own 271 - a dead plan that the residual was sent to as 'secondary'.
#   Rule A refinement (William 10/14): a visit that already carries the primary's payment is NEVER rolled back or rebilled - it is
#   settled: WOINS for the contractual on the payer's own reason (CO-45 22.37 on the 99223); the PR-2 coinsurance (57.53 + 22.20) is
#   patient responsibility (commercial plan, no live secondary) and is never written off. Wrong-insurance rule (v13): end-date the dead
#   plan the day before the first rejected DOS (08/16/2026; ins_update puts the patient order back through the live plan), set each
#   visit's insurance order to the live plan with the no-rebill full-visit echo (resave.set_insorder - NO rebill, the claim is paid),
#   then hideexclusions for the two rejected claim ids on run 1700297.
# Never touches: payments, voids, member ids, any other chart or plan; no chargerebill of any kind; writes only through manual_post,
#   ins_update, resave.set_insorder and amd.post(hideexclusions).
# Usage: cd /home/claude/unbilled && python3 excl_1014_2310.py            # dry run (reads only)
#        cd /home/claude/unbilled && python3 excl_1014_2310.py --live     # the writes above, register registers/excl_2026-10-14T2310Z.json
import sys, json, time, re
import amd, ins_update, manual_post, resave, txh
LIVE = "--live" in sys.argv
S = "2026-10-14T2310Z"
REG = "registers/excl_%s%s.json" % (S, "" if LIVE else "_dry")
rec = {"stamp": S, "live": LIVE, "pid": "17471600", "steps": [], "hidden": {}}
def L(m): print(m, flush=True)
amd.login_cached()
PID = "17471600"; DEAD = "9510889"; LIVEPLAN = "9519033"; RUN = "1700297"
VISITS = [("19451930", "23362020", "19451930C", 22.37), ("19452051", "23362164", "19452051C", 0.0)]
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"cpt": c.get("proccode"), "dos": c.get("dos"), "fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0),
            "insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "carrier": c.get("carrier"), "billdate": c.get("billdate"),
            "pays": [(x.get("date"), x.get("carrier"), x.get("amount"), x.get("checknumber")) for x in c.iter("payment") if x.get("void") != "1"]}
    return res
_, plans, porder = ins_update._plans(PID)
rec["plans_before"] = [(k, v.get("carrier"), v.get("sequence"), v.get("begindate"), v.get("enddate")) for k, v in plans.items()]; rec["porder_before"] = porder
L("pat%s plans %s patient order %r" % (PID, rec["plans_before"], porder))
dead = plans.get("ins" + DEAD); lv = plans.get("ins" + LIVEPLAN)
if not dead or dead.get("carrier") != "car6404" or not lv or lv.get("carrier") != "car6135":
    L("ABORT - chart plans are not UNI20 ins%s / MER01 ins%s as read at 23:2xZ" % (DEAD, LIVEPLAN)); json.dump(rec, open(REG, "w"), indent=1, default=str); sys.exit(1)
to_hide = []
for vid, cid, cl, wo in VISITS:
    st = live(PID, vid); x = st.get(cid); step = {"vid": vid, "cid": cid, "claimid": cl, "before": st}
    L("v%s %s" % (vid, [(k, v["cpt"], v["dos"], v["paid"], v["insbal"], v["patbal"], v["carrier"], v["pays"]) for k, v in st.items()]))
    if not x: step["result"] = "charge not live - skipped"; rec["steps"].append(step); continue
    mer = [p for p in x["pays"] if p[1] == "MER01" and p[3] == "415094527"]
    if not mer: step["result"] = "HOLD - the MER01 payment 415094527 is not on the charge any more"; rec["steps"].append(step); continue
    if wo > 0 and x["insbal"] >= wo - 0.005:
        note = "MER01 remit 415094527 (10/05/2026) CO-45 contractual never adjusted; UNI20 secondary rejected (dead plan) run %s; run %s" % (RUN, S)
        if LIVE:
            ok, msg = manual_post.post(cid, "MER01", 0.0, wo, "WOINS", checknumber="415094527", depositdate="10/05/2026", note=note)
            step["woins"] = (ok, str(msg)[:200]); L("   manual_post WOINS %.2f -> %s %s" % (wo, ok, str(msg)[:140])); time.sleep(0.6)
            if not ok: step["result"] = "FAULT on WOINS - nothing else done for this visit"; rec["steps"].append(step); continue
        else: step["woins"] = "DRY - would WOINS %.2f under MER01 check 415094527" % wo
    elif wo > 0: step["woins"] = "skipped - insbal %.2f below the CO-45 %.2f (already adjusted?)" % (x["insbal"], wo)
    to_hide.append((vid, cl)); step["result"] = "settled (primary paid) - hide"; rec["steps"].append(step)
if LIVE:
    ok, msg = ins_update.update(PID, DEAD, enddate="08/16/2026"); rec["enddate"] = (ok, str(msg)[:400]); L("end-date UNI20 ins%s 08/16/2026 -> %s %s" % (DEAD, ok, str(msg)[:300])); time.sleep(0.6)
    _, plans2, porder2 = ins_update._plans(PID); rec["porder_after_enddate"] = porder2
    if porder2 != "2":
        ok2, msg2 = ins_update.update(PID, LIVEPLAN, sequence="2"); rec["order"] = (ok2, str(msg2)[:300]); L("patient order -> 2: %s %s" % (ok2, str(msg2)[:200])); time.sleep(0.6)
    for vid, cid, cl, wo in VISITS:
        try: ok3, msg3 = resave.set_insorder(cid, "2")
        except Exception as e: ok3, msg3 = False, "EXC %s" % e
        rec.setdefault("insorder", {})[vid] = (ok3, str(msg3)[:300]); L("visit %s insorder 2 (no rebill) -> %s %s" % (vid, ok3, str(msg3)[:200])); time.sleep(0.6)
    if to_hide:
        child = "<visitlist>" + "".join('<visit id="%s" claimid="%s"/>' % (vv, cl) for vv, cl in to_hide) + "</visitlist>"
        r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, child))
        ok = "Fault" not in r; rec["hidden"][RUN] = {"n": len(to_hide), "ok": ok, "resp": re.sub(r"\s+", " ", r[:160])}
        L("hideexclusions run %s (%d visits) -> %s" % (RUN, len(to_hide), "OK" if ok else re.sub(r"\s+", " ", r[:200])))
    rec["after"] = {vid: live(PID, vid) for vid, cid, cl, wo in VISITS}
    L("after: %s" % json.dumps(rec["after"], default=str)[:600])
else:
    rec["would"] = {"enddate": "UNI20 ins%s enddate 08/16/2026, patient order -> 2" % DEAD, "insorder": "both visits insorder 2 (no rebill)", "hide": to_hide}
    L("DRY would: %s" % rec["would"])
json.dump(rec, open(REG, "w"), indent=1, default=str)
L("DONE live=%s steps=%d hidden=%s" % (LIVE, len(rec["steps"]), {k: v.get("ok") for k, v in rec["hidden"].items()}))
