# captured_calls additions - 2026-10-13 1510 UTC (11 AM ET 10/13) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), gettxhistory (unbilled_repair.py dry x11; payreasons.py --list x11), getdemographic (chart 17478013 - zero insplans), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before/after, era_post.py --all-unposted --dry, era_clear.py --dry), POST /api/era/locks/release-expired (era_post.locks(1053116) - nothing locked; the function takes the check id, a bare era_post.locks() raises TypeError), POST /api/claim/massrebillsearch + Stedi 276/277 x17 (claim_status_sweep.py pass 82).

Behaviors noted:
- Columns 0/0/18/0 and ERA 1 check $71.00 unchanged from the 1310Z run; the Billing Button's :17 live 'columns' run overlapped this slot again (two engines, neither wrote).
