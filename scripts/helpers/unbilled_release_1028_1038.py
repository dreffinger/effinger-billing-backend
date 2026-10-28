#!/usr/bin/env python3
# PLAIN ENGLISH (release Unbilled rows whose data was fixed this run - ehpa Billing Button run 2026-10-28T1038Z)
# Decides: nothing. Releases (hideunbillablevisits hide=-1, NUMERIC visit id) the Unbilled rows named on the command line - used only
#   for visits whose cause was repaired first in this run (10/28: two 'MSP Code required' visits re-routed from Medicare to the
#   UHC Dual Complete plan with freq1_visit.py reroute; the UHCMA 271 answered ACTIVE on both charts). Run --dry first, then --live.
# Rules it uses: a release only hides the row - never run it on a visit whose data is still broken.
# Never touches: charges, payments, plans, claims. Register registers/unbilled_release_2026-10-28T1038Z.json.
# Usage: python3 unbilled_release_1028_1038.py <visitid> [<visitid> ...] [--live]
import amd, json, re, sys, datetime
LIVE = "--live" in sys.argv
vids = [re.sub(r"\D", "", a) for a in sys.argv[1:] if not a.startswith("--")]
reg = {"stamp": "2026-10-28T1038Z", "live": LIVE, "at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "rows": []}
if LIVE: amd.login_cached()
for v in vids:
    child = '<visitlist><visit id="%s"/></visitlist>' % v
    if not LIVE:
        print("DRY hideunbillablevisits hide=-1", child); reg["rows"].append({"visit": v, "resp": "dry"}); continue
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, child))
    ok = ('success="1"' in r and "<Fault" not in r)
    print("release", v, "->", "OK" if ok else "FAULT", re.sub(r"\s+", " ", r)[:140])
    reg["rows"].append({"visit": v, "ok": ok, "resp": re.sub(r"\s+", " ", r)[:160]})
json.dump(reg, open("registers/unbilled_release_2026-10-28T1038Z%s.json" % ("" if LIVE else "_dry"), "w"), indent=1)
