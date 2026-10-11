# PLAIN ENGLISH (hospice-period visits to Medicare with GV - William's board word 10/11/2026 03:21Z on chart 17472396:
#   "bill medicare with the gv code for the attending-physician visits of the election period, if that denys write them off")
# Decides: for each named visit of chart 17472396 (the five Humana rejected as duplicates on 10/6 + the 10/6/2026 99309 sitting in
#   Unbilled 'MSP code required'): refuse when any live charge carries a non-void payment > 0 (never rebill a paid visit);
#   add the GV modifier (mcode713) through gv_rebill.add_gv (full-visit echo) only when a charge lacks it; then ONE re-route
#   freq1_visit.reroute(vid, cid, "1,2", 1) = visit order Medicare first / Humana second (no-rebill echo) + one frequency-1 reset
#   + one chargerebill to the Medicare sequence; then release the visit's Unbilled row (hideunbillablevisits hide=-1).
#   A Medicare denial that comes back on these is William's write-off order (next run, on the ERA line).
# Never touches: payments, write-offs, the chart's plan list, any other chart.
#   python3 hospice_medicare_1011.py          # dry: shows the plan per visit
#   python3 hospice_medicare_1011.py --live   # register registers/hospice_medicare_2026-10-11T0510Z.json
import amd, resave, gv_rebill, freq1_visit, txh, payreasons, json, re, sys, time
LIVE = "--live" in sys.argv; S = "2026-10-11T0510Z"; PID = "17472396"
VISITS = [("19441616", "23349530"), ("19442523", "23350697"), ("19444342", "23353047"), ("19446223", "23355217"), ("19447320", "23356503"), ("19457336", "23369193")]
UNBILLED = {"19441616", "19444342", "19446223", "19447320", "19457336"}
amd.login_cached()
reg = {"stamp": S, "live": LIVE, "pid": PID, "visits": []}
rel = []
for vid, cid in VISITS:
    st = payreasons.visit_state(PID, vid, root=txh.fetch_visit(PID, vid))
    paid = [(c["cid"], p["carrier"], p["amount"]) for c in st for p in c["pays"] if p["void"] != "1" and p["amount"] > 0]
    rec = {"vid": vid, "cid": cid, "live_pays": paid, "open_ins": round(sum(c["insbalance"] for c in st), 2)}
    if paid:
        rec["action"] = "SKIP - non-void payment on the visit (never rebill a paid visit)"; reg["visits"].append(rec); print(json.dumps(rec)); continue
    vis, pat, allc = resave.visit_charges(cid)
    missing = [c.get("id") for c in allc if "mcode713" not in (c.get("modcodes") or "").split()]
    rec["gv_missing"] = missing; rec["visit_insorder"] = vis.get("insorder")
    if not LIVE:
        rec["action"] = "DRY: %sreroute 1,2 seq 1%s" % ("add GV + " if missing else "", " + release" if vid in UNBILLED else "")
    else:
        if missing:
            rec["add_gv"] = gv_rebill.add_gv(cid); time.sleep(0.6)
        rec["reroute"] = freq1_visit.reroute(vid, cid, "1,2", 1)
        if vid in UNBILLED: rel.append(vid)
        rec["action"] = "done"
    reg["visits"].append(rec); print(json.dumps(rec)); time.sleep(0.5)
if LIVE and rel:
    xml = amd.call('action="hideunbillablevisits" class="claimsreports" hide="-1" nocookie="1"', "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in rel))
    reg["release"] = {"vids": rel, "ok": 'success="1"' in xml or '<Error/>' in xml or '<Error />' in xml, "resp": re.sub(r"\s+", " ", xml)[:160]}
    print("release", json.dumps(reg["release"]))
json.dump(reg, open("registers/hospice_medicare_%s.json" % S, "w"), indent=1)
print("saved registers/hospice_medicare_%s.json" % S)
