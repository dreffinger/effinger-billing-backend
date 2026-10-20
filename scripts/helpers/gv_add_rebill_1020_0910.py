# PLAIN ENGLISH (hospice GV on ONE visit - 5 AM ET 10/20/2026 backend billing run 2026-10-20T0910Z)
# Decides: nothing new. Applies William's standing hospice rule (hospice -> straight Medicare + GV; the chart's 9/20/2026 CCM already
#   carries GV and was paid) to the one visit Medicare denied CO-B9 'patient is enrolled in a hospice' on ERA 1053219 (claim 15447152,
#   chart 17471496, visit 19456918, 99349 10/02/2026, $198.00). The $0 denial line was never posted (the check left the ERA Center
#   unposted), so gv_rebill.py's void step has nothing to undo: this adds GV (mcode713) to every live charge of the visit with the
#   full-visit echo (gv_rebill.add_gv -> resave.visit_charges, never a single-charge echo) and then sends ONE frequency-1 rebill to the
#   chart's Medicare sequence (freq1_visit.run = frequency 1, blank original ref, chargerebill; the deceased guard inside amd.rebill_charge).
# Never touches: other visits, plans, payments. --dry (default) reads the visit and prints what it would do; --live writes.
# Register: registers/gv_add_rebill_2026-10-20T0910Z[_dry].json
import sys, json, datetime, amd, resave, gv_rebill, freq1_visit
DRY = "--live" not in sys.argv; S = "2026-10-20T0910Z"
PID, VID, CID, SEQ = "17471496", "19456918", "23368626", 2
amd.login_cached()
vis, pat, allc = resave.visit_charges(CID)
rows = [{"cid": c.get("id"), "proc": c.get("proccode"), "dos": c.get("begindate") or c.get("dos"), "mods": c.get("modcodes"), "insorder": vis.get("insorder")} for c in allc]
print("visit", VID, "patient", pat.get("id"), "insorder", vis.get("insorder"), "live charges", rows)
reg = {"stamp": S, "dry": DRY, "pid": PID, "vid": VID, "cid": CID, "seq": SEQ, "before": rows}
if DRY:
    print("DRY: would add GV (mcode713) to %d charge(s) and freq-1 rebill visit %s to seq %s" % (len(allc), VID, SEQ))
else:
    g = gv_rebill.add_gv(CID); print("add_gv:", g); reg["add_gv"] = g
    if not str(g).startswith("FAULT"):
        r = freq1_visit.run(VID, CID, SEQ); print("freq1:", r); reg["freq1"] = str(r)
json.dump(reg, open("registers/gv_add_rebill_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
