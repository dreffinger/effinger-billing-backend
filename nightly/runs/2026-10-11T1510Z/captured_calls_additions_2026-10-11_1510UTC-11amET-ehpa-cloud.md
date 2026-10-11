# captured_calls additions - 2026-10-11 1510 UTC (11 AM ET) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW env), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), payreasons.py --list (gettxhistory on the 11 reason-code rows), GET /api/era/checks (2 unposted), POST /api/era/locks/release-expired x2, GET /api/era/checkdetails?checkid= (1053096, 1053116 - 0 claims each, the posted remainder), POST /api/claim/massrebillsearch + Stedi 276/277 claim status x19 (claim_status_sweep.py pass 58).

Behaviors noted:
- GET /api/era/checkdetails on a check whose remaining lines are hand-posted (1053096) or settled (1053116) answers an empty claim list while GET /api/era/checks still lists the check with its full paymentamount (1,783.61 / 168.59) - the unposted-dollar figure of the report comes from registers/era_manual_register.json, not from the checks list.
