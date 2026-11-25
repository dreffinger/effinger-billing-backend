# PLAIN ENGLISH (feed-cascade holds of the 11/25/2026 09:00Z batch - two care-management visits whose Medicare record names a Medicare
#   Advantage plan the chart does not carry with a member number)
# Decides: nothing. The batch's insurance check (claimocity_verify) HELD these charts: Medicare's own 271 names an MA plan as primary -
#   chart 17478219: CAPITAL HEALTH PLAN (coordination of benefits since 02/01/2026; her 10/22/2026 CCM visit v19459226 already waits with
#   an empty insurance order for the CHP member number - card kestrel-k-shelley-17478219 on William's turn); chart 17478224: HUMANA
#   INSURANCE COMPANY H5216-070 since 01/01/2018 - Stedi insurance discovery (11/25) returned Medicare alone, no Humana member id.
#   A held visit still goes out to the chart's insurance order (Medicare) at the next claim run and comes back CO-24 (covered by a
#   capitation / MA plan). This helper JARRELL each visit the way the 10/22 Kestrel-K visit is parked - the visit's insurance order set to
#   EMPTY by the full-visit echo (resave.set_insorder, every live charge echoed - the void trap) - so AdvancedMD makes no claim for it
#   until the MA member number is on the chart; feed_order_sweep.py (round 7) lists every parked feed visit on every run and the card
#   on William's turn asks for the number. Reads each visit back (insorder + charge count).
# Rules it uses: full-visit echo (resave.set_insorder), never a single-charge resave; no rebill (nothing has been billed); no plan is
#   invented (William: never invent a plan). Never touches: other visits, balances, plans, the chart's default order.
# --dry (default) reads and lists. Register registers/feed_holds_2026-11-25T0900Z[_dry].json.
# 11/25 10:5xZ correction: the twin card [name]-17478224 carries William's word of 11/19 ("Medicare is right" - the Humana record
#   on Medicare's 271 read as her drug plan, the 10/22 CCM sent to Medicare on his word). His word stands: `--restore 17478224` puts that
#   visit's insurance order back to 1 (Medicare) the same way; only the Kestrel-K visit stays parked.
# Usage: python3 feed_holds_1125_0900.py [--live] [--restore <pid>]
import amd, resave, json, sys, time
LIVE = "--live" in sys.argv; S = "2026-11-25T0900Z"
RESTORE = sys.argv[sys.argv.index("--restore") + 1] if "--restore" in sys.argv else None
VISITS = [("17478219", "19462480", "23375622", "CAPITAL HEALTH PLAN (CMS 271 11/25: HMO since 02/01/2026) - no CHP member number on the chart"),
          ("17478224", "19462482", "23375625", "HUMANA INSURANCE COMPANY H5216-070 (CMS 271 11/25: since 01/01/2018) - no Humana member id; discovery found Medicare only")]
amd.login_cached(); reg = {"stamp": S, "live": LIVE, "visits": []}
for pid, vid, cid, why in VISITS:
    if RESTORE and pid != RESTORE: continue
    target = "1" if RESTORE else ""
    vis, pat, allc = resave.visit_charges(cid)
    row = {"pid": pid, "visit": vid, "charge": cid, "why": why, "before": {"insorder": vis.get("insorder"), "list": resave.order_list(vis), "charges": len(allc),
           "dos": [c.get("begindate") for c in allc], "cpt": [c.get("proccode") for c in allc], "insbalance": [c.get("insbalance") for c in allc]}}
    print("pat%s v%s: insorder=%r list=[%s] charges=%d %s" % (pid, vid, vis.get("insorder"), row["before"]["list"], len(allc), row["before"]["cpt"]))
    if not LIVE:
        row["action"] = "DRY - would set the visit's insurance order EMPTY (full-visit echo) so no claim goes to Medicare"; print("  ", row["action"])
    else:
        ok, msg = resave.set_insorder(cid, target); time.sleep(0.8)
        v2, _, allc2 = resave.visit_charges(cid)
        row["action"] = "set_insorder %r ok=%s %s" % (target, ok, str(msg)[:200]); row["after"] = {"insorder": v2.get("insorder"), "list": resave.order_list(v2), "charges": len(allc2)}
        print("  ", row["action"], "| after", row["after"])
    reg["visits"].append(row)
json.dump(reg, open("registers/feed_holds_%s%s%s.json" % (S, "_restore" if RESTORE else "", "" if LIVE else "_dry"), "w"), indent=1); print("register written")
