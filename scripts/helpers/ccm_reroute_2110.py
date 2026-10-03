# PLAIN ENGLISH (5 PM ET 10/3 slot, run 2026-10-03T2110Z): three 9/20/2026 CCM claims (99487 / 99487+99489) went to Humana as the ONLY payer
#   (visit insorder = the chart's Humana MEDICAID-MMA plan) and Humana answered $0 PI-252 on ERA 201994566261003. Every chart carries Florida
#   Medicare at sequence 2, so Medicaid-first was the wrong order (William 9/3: never Medicaid first; Medicare first, Medicaid/LTC second).
# Decides per visit: move_to_ins.move(cid, "2,<humana seq>", rebill_seq=2) = full-visit echo with the new insorder (nothing on the patient balance
#   to move) + chargerebill to Medicare (204), then freq1_visit.run(vid, cid, 2) = resubmissioncode 1 / origrefnum blank + rebill again (original claim).
#   --dry prints the plan only. Never touches: plans, payments, the Humana $0 lines (they stay as the denial record on the ERA).
import amd, move_to_ins, freq1_visit, resave, json, sys, time
DRY = "--dry" in sys.argv; STAMP = "2026-10-03T2110Z"
amd.login_cached()
PLAN = [("17471793","19455780","23367223","2,4"), ("20407","19455733","23367143","2,3"), ("17469466","19455762","23367201","2,3")]
out = []
for pid, vid, cid, order in PLAN:
    r = {"pid": pid, "vid": vid, "cid": cid, "order": order}
    r["move"] = move_to_ins.move(cid, order, dry=DRY, rebill_seq=2); print("v%s pat%s move -> %s" % (vid, pid, r["move"]), flush=True); time.sleep(0.5)
    if not DRY:
        r["freq1"] = freq1_visit.run(vid, cid, 2); print("   freq1 -> %s" % r["freq1"], flush=True); time.sleep(0.5)
        vis, pat, allc = resave.visit_charges(cid); e = vis.find("extins")
        r["after"] = {"insorder": vis.get("insorder"), "resub": e.get("resubmissioncode") if e is not None else None, "charges": [(c.get("id"), c.get("insbilled"), c.get("insbalance")) for c in allc]}
        print("   after", r["after"], flush=True)
    out.append(r)
json.dump(out, open("registers/ccm_reroute_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
