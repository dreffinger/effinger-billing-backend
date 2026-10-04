# captured_calls additions - 2026-10-04 1310 UTC (9 AM ET 10/4 backend billing run, ehpa cloud)

No new AMD or Stedi call shapes this run. Calls exercised (all already in the registry): login_cached (one login 13:14Z), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/charges, getclaimunbillablecharges, getclaimexclusionclaimruns/getclaimexclusioncharges, GET /api/era/checks, GET /api/era/checkdetails?checkid=1052906. No writes: every column row was a standing hold on William's turn and the only unposted ERA check is the held Florida Blue takeback pair.

Observation (not a new shape): GET /api/era/checks returns the held check with checknumber/carriername/checkamount null and only unpostedamount (104.19) + systemcarriercode BCBS populated - the check header fields come from checkdetails, not the list.
