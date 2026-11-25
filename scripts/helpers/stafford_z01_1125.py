#!/usr/bin/env python3
# PLAIN ENGLISH (chart 17477572 - after I10 was put first on William's word, the Claim Inspector holds the three visits on Pattern 2776:
#   Z01.818 'may only be used as first-listed' - a first-listed-only code sitting fourth)
# Decides: nothing new - the diagnosis cascade's own rule for a code the inspector refuses in its slot: DELETE it when another acceptable
#   code remains (I10, M17.12, R10.9 stay; a hospital visit keeps three conditions). Full-visit echo (dx_primary_fix.save_visit_dx) with
#   the code list without Z01.818 on charges 23363598 / 23363597 / 23363599; no second rebill (the frequency-1 rebill of this run is
#   queued; the claim leaves once the inspector is clean). --dry prints. Register registers/stafford_z01_<stamp>.json.
# Never touches: other codes, other visits, payments. Usage: python3 stafford_z01_1125.py [--live]
import amd, dx_primary_fix as dpf, json, sys
LIVE = "--live" in sys.argv; S = "2026-11-25T0634Z"; PID = "17477572"; out = {}
amd.login_cached()
for vid, cid in (("19453098", "23363598"), ("19453097", "23363597"), ("19453099", "23363599")):
    vis, pat, allc, m = dpf.visit_dx(cid); inv = {v: k for k, v in m.items()}; inv.setdefault("I10", dpf.I10_DCODE); plans = {}
    for c in allc:
        codes = [m.get(d, d) for d in (c.get("diagcodes") or "").split()]; new = [x for x in codes if x != "Z01.818"]
        if new != codes: plans[c.get("id")] = [inv[x] for x in new]
    if not plans: out[vid] = "Z01.818 not on the charge - nothing to do"; print(vid, out[vid]); continue
    r, det = dpf.save_visit_dx(cid, plans, dry=not LIVE); out[vid] = {"before": codes, "after": new, "save": str(r)[:160], "verified": all(det.get(k, (None, None))[1] == v for k, v in plans.items()) if LIVE else None}
    print(vid, out[vid])
json.dump(out, open("registers/stafford_z01_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
