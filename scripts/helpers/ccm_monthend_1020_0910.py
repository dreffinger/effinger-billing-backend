# PLAIN ENGLISH (CCM month-end re-date for ONE claim - 5 AM ET 10/20/2026 backend billing run 2026-10-20T0910Z)
# Decides: nothing new. Applies William's CCM rule of 10/4/2026 (board row medicare-co151-ccm-frequency-1003: "these are a monthly
#   total charge for CCM - rebill them on the last day of the month; if they are duplicates delete the duplicates") to the one CCM
#   claim Medicare denied CO-151 (99487 $206.00) + CO-234 (99489 $109.00) on ERA 1053219 (claim 15447154): chart 17473343,
#   visit 19455721, DOS 09/20/2026. The live chart carries no OTHER CCM visit in September 2026 (the 8/31 one is August), so there is
#   no duplicate to void: the visit is re-dated to 09/30/2026 (visit date + begin/end date on both charges, FULL-visit echo of every
#   live charge via resave.visit_charges - never a single-charge echo) and sent to the chart's Medicare sequence (seq 2) as an original
#   claim: ONE frequency-1 reset + ONE chargerebill (freq1_visit.run; deceased guard inside amd.rebill_charge).
#   chat_1004_ccm_monthend.py could not be reused: its import chat_1004_board_act.py no longer compiles on main (line 256, a comment
#   the PHI gate wrote into the middle of a call) - that trap is in the run's shared lessons.
# Refuses: a charge that carries a payment, a visit whose live charge count changes, a September sibling CCM visit.
# Never touches: other visits, plans, payments. --dry (default) reads and prints; --live writes.
# Register: registers/ccm_monthend_2026-10-20T0910Z[_dry].json
import sys, json, re, time, datetime, amd, resave, freq1_visit, payreasons, txh
DRY = "--live" not in sys.argv; S = "2026-10-20T0910Z"
PID, VID, CID, SEQ, NEWDATE = "17473343", "19455721", "23367120", 2, "09/30/2026"
CCM = {"99487", "99489", "99490", "99491"}
amd.login_cached()
root = txh.fetch(PID)
sept = {}
for c in root.iter("charge"):
    if c.get("void") == "1": continue
    if c.get("proccode") in CCM and c.get("dos", "").startswith("09/") and c.get("dos", "").endswith("/2026"):
        sept.setdefault(re.sub(r"\D", "", c.get("visit") or ""), []).append((c.get("id"), c.get("proccode"), c.get("dos"), c.get("paid"), c.get("insbal")))
print("September 2026 CCM visits on the chart:", sept)
reg = {"stamp": S, "dry": DRY, "pid": PID, "vid": VID, "newdate": NEWDATE, "sept": sept}
out = "registers/ccm_monthend_%s%s.json" % (S, "_dry" if DRY else "")
if set(sept) - {VID}:
    print("REFUSED: another September CCM visit exists - duplicate decision needed"); reg["result"] = "refused sibling"
    json.dump(reg, open(out, "w"), indent=1); sys.exit(0)
state = payreasons.visit_state(PID, VID, root)
if any(p for ch in state for p in ch["pays"] if p["void"] != "1" and p["amount"] > 0):
    print("REFUSED: a payment is on the visit"); reg["result"] = "refused payment"; json.dump(reg, open(out, "w"), indent=1); sys.exit(0)
vis, pat, allc = resave.visit_charges(CID)
chg = ""
for c in allc:
    a = {"id": c.get("id")}
    for f in resave.CHG_FIELDS:
        if c.get(f) is not None: a[f] = c.get(f)
    a["begindate"] = NEWDATE; a["enddate"] = NEWDATE
    chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
va = dict(vis.attrib); va["force"] = "1"; va["date"] = NEWDATE
print("visit", vis.get("id"), "date", vis.get("date"), "->", NEWDATE, "insorder", vis.get("insorder"), "charges", [(c.get("id"), c.get("proccode"), c.get("begindate")) for c in allc])
reg["before"] = [(c.get("id"), c.get("proccode"), c.get("begindate")) for c in allc]
if DRY:
    print("DRY: would resave the visit dated %s with %d charges and freq-1 rebill to seq %s" % (NEWDATE, len(allc), SEQ))
else:
    import era_post
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(era_post.batch()), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8)
    if "Fault" in r:
        print("FAULT", re.sub(r"\s+", " ", r[:240])); reg["result"] = "FAULT " + re.sub(r"\s+", " ", r[:240])
    else:
        v2, p2, c2 = resave.visit_charges(CID)
        after = [(c.get("id"), c.get("proccode"), c.get("begindate")) for c in c2]
        print("saved: visit date", v2.get("date"), "live", len(c2), "of", len(allc), after); reg["after"] = after; reg["visitdate"] = v2.get("date")
        if len(c2) == len(allc):
            r1 = freq1_visit.run(VID, CID, SEQ); print("freq1:", r1); reg["freq1"] = str(r1)
        else:
            print("CHARGE COUNT CHANGED - no rebill"); reg["result"] = "charge count changed"
json.dump(reg, open(out, "w"), indent=1)
