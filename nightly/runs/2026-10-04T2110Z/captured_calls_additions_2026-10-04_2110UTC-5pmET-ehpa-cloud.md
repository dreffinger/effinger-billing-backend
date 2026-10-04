# captured_calls additions - 2026-10-04 2110 UTC (5 PM ET 10/4 backend billing run, ehpa cloud)

No new AMD or Stedi call shapes this run. Calls exercised (all already in the registry): login_cached (one login 21:14Z), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/charges (11 batches), getclaimunbillablecharges, getclaimrunstatus/getclaimexclusioncharges (80 runs), getdemographic x4 (plan re-read on the held charts), gettxhistory x1 (99223 anchor search), GET /api/era/checks, GET /api/era/checkdetails?checkid=1052906, posterapayments dry build (era_post --dry). No AMD writes.
Helpers added: columns_scan_1004_2110.py (scan of the four columns, this slot), recheck_2110_1004.py (read-only re-check of the held charts + ERA before picture).
