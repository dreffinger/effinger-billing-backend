# captured_calls additions - 2026-10-12 1310 UTC (9 AM ET 10/12) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), gettxhistory (payreasons.py --list), getdemographic (pat17478013 read - zero insplans), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before/after), POST /api/era/locks/release-expired (era_post.locks on 1053116 - nothing locked), posterapayments dry plan (era_post.py --all-unposted --dry: 0 postable), era_clear.py --dry (HOLD), POST /api/claim/massrebillsearch + Stedi 276/277 x19 (claim_status_sweep.py pass 69), Stedi MBILUNOSSN eligibility x1 (ERR 72) and insurance-discovery x1 (coveragesFound 0).

Behaviors noted:
- Stedi /insurance-discovery/check/v1 answered normally again at 13:21Z (coveragesFound 0 for pat17478013, DOS 20261005) - the 1110Z 502 was transient; 0 found is now the answer of record for that chart.
- No AMD write this slot.
