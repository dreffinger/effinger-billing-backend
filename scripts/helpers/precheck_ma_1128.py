# PLAIN ENGLISH (nightly cascade 2026-11-28T0536Z, pre-check rule (a)): three feed visits billed Medicare-first (order 2,1) on
#   Medicare Advantage members whose chart order 1 is their Blue Cross MA plan (already on the chart): chart 17472826 v19462796 11/26 +
#   v19462819 11/25 (BCBS of Michigan MA) and chart 17473090 v19462817 11/25 (HCSC MA). Same as precheck_ma_1125.py: dx_primary_fix.plan
#   first (a never-primary first code stops it), then freq1_visit.reroute(vid, cid, "1", 1) - full-visit echo of the order, ONE
#   frequency-1 rebill, deceased guard inside.
# Never touches: other visits, payments, plans. Usage: python3 precheck_ma_1128.py [--live]
import amd, dx_primary_fix, freq1_visit, json, sys
LIVE = "--live" in sys.argv
V = [("17472826", "19462796", "23376147"), ("17472826", "19462819", "23376170"), ("17473090", "19462817", "23376168")]
amd.login_cached(); out = []
for pid, vid, cid in V:
    vis, pat, allc, m = dx_primary_fix.visit_dx(cid)
    codes = [m.get(d, d) for d in (allc[0].get("diagcodes") or "").split()]
    action, new = dx_primary_fix.plan(codes)
    line = {"pid": pid, "visit": vid, "charge": cid, "insorder_before": vis.get("insorder"), "dx_first": codes[:1], "dx_action": action}
    if action != "ok": line["result"] = "STOP - never-primary first diagnosis, dx cascade first"; print(line); out.append(line); continue
    r = freq1_visit.reroute(vid, cid, "1", 1, dry=not LIVE); line["result"] = str(r)[:220]
    print(line); out.append(line)
json.dump(out, open("registers/precheck_ma_2026-11-28T0536Z%s.json" % ("" if LIVE else "_dry"), "w"), indent=1)
