# PLAIN ENGLISH (Exclusions column, 1:39 PM ET 11/16/2026 run 2026-11-16T1840Z): claim run 1700382 carries two SUNSHINE (SUN01)
#   payer rejections on chart 17472874 - 'ACK/RETURNED AS UNPROCESSABLE CLAIM ... 02 - INVALID MBR' on v19455319 (99308 12/05/2025)
#   and v19455320 (99308 12/15/2025), claims 19455319D / 19455320D = the secondary claims after William's 11/2 'end WellCare 12/4/2025,
#   re-send Medicare first' answer. Live read this run: Medicare (FLO02) paid 55.97 + 36.75 contractual on each charge (check 820183876,
#   11/14/2026); the residual 14.28 per charge is Medicare cost-share. The chart's SUN01 plan carries 30722106 = the WellCare member id;
#   AMD's own 271 on it answers AAA 78 (not in plan); the CMS 271 names no Medicaid / QMB (only a WellCare stand-alone Part D); Stedi
#   discovery at DOS 12/05/2025 finds Medicare only; Stedi FL Medicaid by name/DOB answers 72 (needs an id). No supplement was in force
#   on the DOS -> William 10/13 rule (rules.md): the cost-share with no insurance to bill is written off WOCLTREQ, then hideexclusions.
# Never touches: payments, voids, plans, member ids, any other chart or visit; no chargerebill, no plan edit, no resave; writes only
#   through manual_post.post (WOCLTREQ, pay 0.0) and amd.post(hideexclusions).
# Usage: cd /home/claude/unbilled && python3 excl_1116_1840.py            # dry run (reads only)
#        cd /home/claude/unbilled && python3 excl_1116_1840.py --live     # the writes above, register registers/excl_2026-11-16T1840Z.json
import sys, json, time, re
import amd, manual_post, txh
LIVE = "--live" in sys.argv
S = "2026-11-16T1840Z"
REG = "registers/excl_%s%s.json" % (S, "" if LIVE else "_dry")
rec = {"stamp": S, "live": LIVE, "pid": "17472874", "visits": []}
def L(m): print(m, flush=True)
amd.login_cached()
PID = "17472874"; RUN = "1700382"
VISITS = [("19455319", "19455319D", "23366560", 14.28), ("19455320", "19455320D", "23366562", 14.28)]
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"cpt": c.get("proccode"), "dos": c.get("dos"), "fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0),
            "insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "carrier": c.get("carrier"), "billdate": c.get("billdate"),
            "pays": [(x.get("date"), x.get("carrier"), x.get("amount"), x.get("checknumber")) for x in c.iter("payment") if x.get("void") != "1"]}
    return res
to_hide = []
for vid, claim, cid, expect in VISITS:
    v = {"visit": vid, "claim": claim, "cid": cid}
    st = live(PID, vid); x = st.get(cid); v["before"] = x
    L("v%s %s" % (vid, json.dumps(x, default=str)[:400]))
    if not x: v["result"] = "HOLD - charge not live"; rec["visits"].append(v); continue
    med = [p for p in x["pays"] if p[3] == "820183876" and abs(float(p[2] or 0)) > 0]
    if not med: v["result"] = "HOLD - Medicare payment 820183876 not on the charge"; rec["visits"].append(v); continue
    if abs(x["insbal"] - expect) > 0.005 or x["patbal"] > 0.005:
        v["result"] = "HOLD - live balance differs (insbal %.2f patbal %.2f)" % (x["insbal"], x["patbal"]); rec["visits"].append(v); continue
    note = "Medicare cost-share after FLO02 primary (check 820183876, 11/14/2026); SUN01 secondary rejected 02 INVALID MBR run %s (plan carries the WellCare id, AMD 271 AAA 78; CMS 271 no Medicaid/QMB; Stedi discovery at DOS Medicare only) - no supplement in force on the DOS - William 10/13 rule; run %s" % (RUN, S)
    if LIVE:
        ok, msg = manual_post.post(cid, "FLO02", 0.0, x["insbal"], "WOCLTREQ", checknumber="EXCL1116", depositdate=None, note=note)
        v["wocltreq"] = (ok, str(msg)[:200]); L("   manual_post WOCLTREQ %.2f on %s -> %s %s" % (x["insbal"], cid, ok, str(msg)[:140])); time.sleep(0.6)
        if not ok: v["result"] = "FAULT on WOCLTREQ"; rec["visits"].append(v); continue
        to_hide.append((vid, claim))
    else:
        v["wocltreq"] = "DRY - would WOCLTREQ %.2f under FLO02 check EXCL1116" % x["insbal"]
    v["result"] = "settled (primary paid, cost-share written off)"; rec["visits"].append(v)
if LIVE and to_hide:
    child = "<visitlist>" + "".join("<visit id=\"%s\" claimid=\"%s\"/>" % p for p in to_hide) + "</visitlist>"
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, child))
    ok = "Fault" not in r; rec["hidden"] = {"run": RUN, "n": len(to_hide), "ok": ok, "resp": re.sub(r"\s+", " ", r[:160])}
    L("hideexclusions run %s %s -> %s" % (RUN, to_hide, "OK" if ok else re.sub(r"\s+", " ", r[:200])))
    rec["after"] = {vid: live(PID, vid) for vid, _ in to_hide}; L("after: %s" % json.dumps(rec["after"], default=str)[:600])
json.dump(rec, open(REG, "w"), indent=1, default=str); L("register " + REG)
