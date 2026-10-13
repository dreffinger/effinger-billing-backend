# captured_calls additions - 2026-10-13 0510 UTC (1 AM ET 10/13) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), gettxhistory (payreasons.py --list x11, unbilled_repair.py dry + live), hideunbillablevisits hide=-1 x20 (unbilled_repair.py --live, rule b), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before; 1053116, 3 claim rows), posterapayments dry plan (era_post.py --all-unposted --dry on 1053116: 0 postable / 3 skipped), era_clear.py --dry (HOLD 1053116), POST /api/claim/massrebillsearch + Stedi 276/277 x19 (claim_status_sweep.py pass 77).

Behaviors noted:
- The nightly claim run re-listed 20 'A payment from the prior payor is required' Unbilled rows (the same kind the 10/12 0510Z run released): rule b released them again at 05:21-05:22Z; the 11 reason-code rows and the 7 chart-17478013 rows are the only Unbilled holds left.
- Chart 17478013 grew from 5 to 7 held visits (10/10 and 10/11 99233s arrived) - still zero plans, facesheet on William's turn.
