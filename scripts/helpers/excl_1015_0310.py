# PLAIN ENGLISH (Exclusions column, 11 PM ET 10/14/2026 run 2026-10-15T0310Z): claim run 1700296 carries one UNITED HEALTHCARE
#   (UNI20) payer rejection on chart 17471414 - 'ACK, RETURNED AS UNPROCESSABLE CLAIM / MEMBER PICK REJECT' on v19394861
#   (99306 + 99497, DOS 03/18/2024), the 10/13 patient-balance review's BILL-SECONDARY send (claim 19394861B). Live read this run:
#   the visit already carries the PRIMARY's payment - HUMANA (HUM01, seq 1, a Medicare Advantage plan) paid 150.46 + 62.34 on
#   11/26/2024 with CO-45 / CO-253 contractual; the residual (105.54 + 70.66 = 176.20) is the MA cost-share. The chart's UNI20 plan
#   (seq 3, begin 02/20/2024) answers INACTIVE on AMD's own 271 and UHC says the member does not exist; the Medicare plan's MBI answers
#   AAA 72 (AMD 271 and Stedi MBI lookup alike); Stedi discovery answered 502. No supplement was in force on the DOS behind the MA plan
#   (a Medigap never pays MA cost-share anyway). Rule A refinement (William 10/14): a visit that already carries the primary's payment
#   is NEVER rolled back or rebilled - it is settled; William 10/13 ('nothing stays on the patient balance'): the Medicare/MA
#   cost-share with no supplement in force on the DOS is written off WOCLTREQ (the cards_ab_1014.py code), then hideexclusions for the
#   rejected claim id on run 1700296.
# Never touches: payments, voids, plans, member ids, any other chart or visit; no chargerebill, no plan edit, no resave; writes only
#   through manual_post.post (WOCLTREQ, pay 0.0) and amd.post(hideexclusions).
# Usage: cd /home/claude/unbilled && python3 excl_1015_0310.py            # dry run (reads only)
#        cd /home/claude/unbilled && python3 excl_1015_0310.py --live     # the writes above, register registers/excl_2026-10-15T0310Z.json
import sys, json, time, re
import amd, manual_post, txh
LIVE = "--live" in sys.argv
S = "2026-10-15T0310Z"
REG = "registers/excl_%s%s.json" % (S, "" if LIVE else "_dry")
rec = {"stamp": S, "live": LIVE, "pid": "17471414", "steps": [], "hidden": {}}
def L(m): print(m, flush=True)
amd.login_cached()
PID = "17471414"; VID = "19394861"; CLAIM = "19394861B"; RUN = "1700296"
CHARGES = [("22467665", "99306", 105.54), ("22467666", "99497", 70.66)]
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"cpt": c.get("proccode"), "dos": c.get("dos"), "fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0),
            "insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "carrier": c.get("carrier"), "billdate": c.get("billdate"),
            "pays": [(x.get("date"), x.get("carrier"), x.get("amount"), x.get("checknumber")) for x in c.iter("payment") if x.get("void") != "1"]}
    return res
st = live(PID, VID); rec["before"] = st
L("v%s %s" % (VID, [(k, v["cpt"], v["dos"], v["paid"], v["insbal"], v["patbal"], v["carrier"], v["billdate"], v["pays"]) for k, v in st.items()]))
ok_all = True; settled = 0
for cid, cpt, expect in CHARGES:
    x = st.get(cid); step = {"cid": cid, "cpt": cpt, "expect": expect}
    if not x: step["result"] = "charge not live - skipped"; rec["steps"].append(step); ok_all = False; continue
    hum = [p for p in x["pays"] if p[1] == "HUM01" and abs(float(p[2] or 0)) > 0]
    if not hum: step["result"] = "HOLD - no HUM01 payment on the charge any more"; rec["steps"].append(step); ok_all = False; continue
    if x["cpt"] != cpt or abs(x["insbal"] - expect) > 0.005 or x["patbal"] > 0.005:
        step["result"] = "HOLD - live state differs from the 03:2xZ read (cpt %s insbal %.2f patbal %.2f)" % (x["cpt"], x["insbal"], x["patbal"]); rec["steps"].append(step); ok_all = False; continue
    note = "MA cost-share after HUM01 primary (paid 11/26/2024, CO-45/CO-253); UNI20 'secondary' rejected member not found run %s, plan INACTIVE on 271, Medicare MBI AAA 72 - no supplement in force on the DOS - William 10/13 rule; run %s" % (RUN, S)
    if LIVE:
        ok, msg = manual_post.post(cid, "HUM01", 0.0, x["insbal"], "WOCLTREQ", checknumber="EXCL1015", depositdate=None, note=note)
        step["wocltreq"] = (ok, str(msg)[:200]); L("   manual_post WOCLTREQ %.2f on %s -> %s %s" % (x["insbal"], cid, ok, str(msg)[:140])); time.sleep(0.6)
        if not ok: step["result"] = "FAULT on WOCLTREQ"; rec["steps"].append(step); ok_all = False; continue
    else:
        step["wocltreq"] = "DRY - would WOCLTREQ %.2f under HUM01 check EXCL1015" % x["insbal"]
    step["result"] = "settled (primary paid, cost-share written off)"; rec["steps"].append(step); settled += 1
if LIVE and ok_all and settled == len(CHARGES):
    child = "<visitlist><visit id=\"%s\" claimid=\"%s\"/></visitlist>" % (VID, CLAIM)
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, child))
    ok = "Fault" not in r; rec["hidden"][RUN] = {"n": 1, "ok": ok, "resp": re.sub(r"\s+", " ", r[:160])}
    L("hideexclusions run %s (%s) -> %s" % (RUN, CLAIM, "OK" if ok else re.sub(r"\s+", " ", r[:200])))
    rec["after"] = live(PID, VID); L("after: %s" % json.dumps(rec["after"], default=str)[:600])
elif LIVE:
    L("NOT hiding the exclusion - a charge did not settle (see steps)")
else:
    rec["would"] = {"hide": [(VID, CLAIM)] if ok_all else [], "settled": settled}
    L("DRY would: %s" % rec["would"])
json.dump(rec, open(REG, "w"), indent=1, default=str)
L("DONE live=%s settled=%d/%d hidden=%s" % (LIVE, settled, len(CHARGES), {k: v.get("ok") for k, v in rec["hidden"].items()}))
