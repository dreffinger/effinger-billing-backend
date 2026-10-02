# captured_calls additions - 2026-10-02 1711 UTC (1 PM ET 10/2) - backend billing run, ehpa cloud

No new call shapes this run. Calls used (all previously captured): login (one attempt, AMD_PSW environment credential), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches / getclaiminspectorcharges, getclaimunbillablecharges, getclaimrunstatus / getclaimexclusioncharges (columns_scan.py before/after), lookuppatient x4 + getdemographic x11 (unbilled_reads.py, read-only), GET /api/era/checks + GET /api/era/checkdetails (era_post.py --all-unposted --dry). No AMD writes.
