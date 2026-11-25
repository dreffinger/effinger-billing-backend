# PLAIN ENGLISH (cascade pre-check rule (a), 11/25/2026 button run: two feed visits billed Medicare-first on Medicare Advantage members)
# Decides: nothing new - precheck_<today>.json flagged 'ADVANTAGE PLAN on DOS' for two 11/22/2026 99233 hospital visits whose feed entry
#   put the visit order 2,1 (Medicare first) while each chart's own order is 1 = its Blue Cross Medicare Advantage plan (already on the chart,
#   ACTIVE): chart 17472826 v19462327 (BCBS of Michigan MA) and chart 17473090 v19462326-? (HCSC MA). Rule (a): point the visit at the MA
#   plan and rebill - here ONE visit each, so the standing one-rebill re-route freq1_visit.reroute(vid, cid, "1", 1) (no-rebill full-visit
#   echo of the order, then ONE frequency-1 rebill; the deceased guard inside). Before it, dx_primary_fix.plan on the visit's diagnoses:
#   a never-primary first code stops this helper (the dx cascade is its own step).
# Never touches: other visits, payments, plans. Usage: python3 precheck_ma_1125.py [--live]
import amd, dx_primary_fix, freq1_visit, json, sys
LIVE = "--live" in sys.argv
V = [("17472826", "19462327", "23375392"), ("17473090", None, "23375390")]
amd.login_cached(); out = []
for pid, vid, cid in V:
    vis, pat, allc, m = dx_primary_fix.visit_dx(cid)
    vid = vid or (vis.get("id") or "").replace("visit", "")
    codes = [m.get(d, d) for d in (allc[0].get("diagcodes") or "").split()]
    action, new = dx_primary_fix.plan(codes)
    line = {"pid": pid, "visit": vid, "charge": cid, "insorder_before": vis.get("insorder"), "dx_first": codes[:1], "dx_action": action}
    if action != "ok": line["result"] = "STOP - never-primary first diagnosis, dx cascade first"; print(line); out.append(line); continue
    r = freq1_visit.reroute(vid, cid, "1", 1, dry=not LIVE); line["result"] = str(r)[:220]
    print(line); out.append(line)
json.dump(out, open("registers/precheck_ma_2026-11-25T0435Z%s.json" % ("" if LIVE else "_dry"), "w"), indent=1)
