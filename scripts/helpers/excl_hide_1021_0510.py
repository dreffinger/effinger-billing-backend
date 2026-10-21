#!/usr/bin/env python3
# PLAIN ENGLISH (complete one exclusion row, 1 AM ET 10/21/2026 run 2026-10-21T0510Z): hideexclusions for ONE visit/claim on ONE claim run.
# Decides: nothing. The row it completes (chart 48449, v19457091 claim 19457091C, run 1700315, Florida Blue CH FH PREF0283) was
#   re-sent first by freq1_visit.py reroute (visit order 2,1 = Florida Blue first - Medicare's 271 shows Part A only, no Part B,
#   and Medicare answered $0 PR-27 - then ONE frequency-1 original to Florida Blue seq 2). Run --dry first (prints the call),
#   then --live (posts it). Register registers/excl_hide_2026-10-21T0510Z.json. Never touches payments, charges or plans.
# Usage: python3 excl_hide_1021_0510.py <claimrunid> <visitid> <claimid> [--live]
import amd, json, re, sys
LIVE = "--live" in sys.argv; run, vid, cl = [a for a in sys.argv[1:] if not a.startswith("--")][:3]
child = '<visitlist><visit id="%s" claimid="%s"/></visitlist>' % (vid, cl)
reg = {"stamp": "2026-10-21T0510Z", "live": LIVE, "run": run, "visit": vid, "claimid": cl}
if not LIVE: print("DRY hideexclusions run %s hide=-1 %s" % (run, child)); reg["resp"] = "dry"
else:
    amd.login_cached(); r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
    reg["ok"] = "Fault" not in r; reg["resp"] = re.sub(r"\s+", " ", r[:200]); print("hideexclusions run %s -> %s %s" % (run, "OK" if reg["ok"] else "FAULT", reg["resp"][:160]))
json.dump(reg, open("registers/excl_hide_2026-10-21T0510Z.json", "w"), indent=1)
