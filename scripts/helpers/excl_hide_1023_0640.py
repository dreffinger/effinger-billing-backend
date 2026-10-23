#!/usr/bin/env python3
# PLAIN ENGLISH (complete one exclusion row, 3 AM ET 10/23/2026 run 2026-10-23T0640Z): hideexclusions for ONE visit/claim on ONE claim run.
# Decides: nothing. The row it completes (chart 17473245, v19452629 claim 19452629F, run 1700319, Florida Blue CH FH PREF0283 on a Medigap
#   secondary) was already re-sent as a frequency-1 original on 10/22 (resubmissioncode 1, origrefnum blank) after the 10/21 Medicare payreason repair and
#   rejected again - a second identical send is a duplicate (one rebill per visit); the balance is listed for William. Run --dry first,
#   then --live (posts it). Register registers/excl_hide_2026-10-23T0640Z.json. Never touches payments, charges or plans.
# Usage: python3 excl_hide_1023_0640.py <claimrunid> <visitid> <claimid> [--live]
import amd, json, re, sys
LIVE = "--live" in sys.argv; run, vid, cl = [a for a in sys.argv[1:] if not a.startswith("--")][:3]
child = '<visitlist><visit id="%s" claimid="%s"/></visitlist>' % (vid, cl)
reg = {"stamp": "2026-10-23T0640Z", "live": LIVE, "run": run, "visit": vid, "claimid": cl}
if not LIVE: print("DRY hideexclusions run %s hide=-1 %s" % (run, child)); reg["resp"] = "dry"
else:
    amd.login_cached(); r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
    reg["ok"] = "Fault" not in r; reg["resp"] = re.sub(r"\s+", " ", r[:200]); print("hideexclusions run %s -> %s %s" % (run, "OK" if reg["ok"] else "FAULT", reg["resp"][:160]))
json.dump(reg, open("registers/excl_hide_2026-10-23T0640Z.json", "w"), indent=1)
