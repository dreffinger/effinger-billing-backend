#!/usr/bin/env python3
# PLAIN ENGLISH (complete named Exclusions rows - generic form of excl_complete_1011.py, written 11/2/2026 run 2026-11-02T1840Z)
# Decides: nothing new. The standing rule "complete every exclusion whose visit balance is already $0 or whose visit was re-sent
#   this run" (prompt step 4): once a rejected visit has been corrected and re-sent (frequency 1 / 7 by freq1_visit / freq7_visit),
#   or written to $0, its stale clearinghouse/payer rejection row is COMPLETED with hideexclusions hide=-1 so the column clears.
# Does (only with --live): ONE hideexclusions per claim run carrying exactly the visit/claim ids named on the command line, then
#   re-lists that run (getclaimexclusioncharges) to confirm which visits are left. --dry (default) prints what it would send.
# Never touches: charges, payments, write-offs, claims, plans, any row not named.
#   python3 excl_complete.py --run <claimrunid> --rows <visitid>:<claimid> [<visitid>:<claimid> ...] --why "<what was done>" [--stamp S] [--live]
# Register: registers/excl_complete_<run>_<stamp>[_dry].json (chart/visit ids only, no names).
import amd, json, re, sys, time, datetime
LIVE = "--live" in sys.argv
def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default
RUN = arg("--run"); WHY = arg("--why", ""); STAMP = arg("--stamp", datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ"))
if not RUN or "--rows" not in sys.argv:
    sys.exit("usage: excl_complete.py --run <claimrunid> --rows <visitid>:<claimid> ... [--why ...] [--stamp S] [--live]")
rows = []
for a in sys.argv[sys.argv.index("--rows") + 1:]:
    if a.startswith("--"): break
    vid, claimid = a.split(":", 1); rows.append((re.sub(r"\D", "", vid), claimid))
amd.login_cached()
reg = {"stamp": STAMP, "run": RUN, "live": LIVE, "why": WHY, "rows": rows}
lst = "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in rows)
if not LIVE:
    print("DRY - would hideexclusions run %s for %d rows: %s (%s)" % (RUN, len(rows), [c for _, c in rows], WHY))
else:
    x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120)
    reg["hide_result"] = re.sub(r"\s+", " ", x[:300]); print("hideexclusions ->", reg["hide_result"])
    time.sleep(1)
    y = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RUN, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
    left = re.findall(r'<visit [^>]*\bid="(\d+)"', y); reg["relist_visits"] = left
    print("re-list run %s: %d exclusion visits left: %s" % (RUN, len(left), left))
json.dump(reg, open("registers/excl_complete_%s_%s%s.json" % (RUN, STAMP, "" if LIVE else "_dry"), "w"), indent=1)
print("register written")
