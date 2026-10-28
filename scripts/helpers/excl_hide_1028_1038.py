#!/usr/bin/env python3
# PLAIN ENGLISH (complete one exclusion row, ehpa Billing Button run 2026-10-28T1038Z): hideexclusions for ONE visit/claim on ONE claim run.
# Decides: nothing. Used for rows whose visit was re-sent this run on William's board order (10/26 02:56Z on row levin-lize-17475632:
#   "PO BOX 809025, DALLAS, TX 75380 set, rebill" - v19433791 re-sent as a frequency-1 original to the UNI98 plan, run 1700319 row completed).
#   Run --dry first, then --live (posts it). Register registers/excl_hide_2026-10-28T1038Z_<run>_<visit>.json. Never touches payments, charges or plans.
# Usage: python3 excl_hide_1028_1038.py <claimrunid> <visitid> <claimid> [--live]
import amd, json, re, sys
LIVE = "--live" in sys.argv; run, vid, cl = [a for a in sys.argv[1:] if not a.startswith("--")][:3]
child = '<visitlist><visit id="%s" claimid="%s"/></visitlist>' % (vid, cl)
reg = {"stamp": "2026-10-28T1038Z", "live": LIVE, "run": run, "visit": vid, "claimid": cl}
if not LIVE: print("DRY hideexclusions run %s hide=-1 %s" % (run, child)); reg["resp"] = "dry"
else:
    amd.login_cached(); r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
    reg["ok"] = "Fault" not in r; reg["resp"] = re.sub(r"\s+", " ", r[:200]); print("hideexclusions run %s -> %s %s" % (run, "OK" if reg["ok"] else "FAULT", reg["resp"][:160]))
json.dump(reg, open("registers/excl_hide_2026-10-28T1038Z_%s_%s%s.json" % (run, vid, "" if LIVE else "_dry"), "w"), indent=1)
