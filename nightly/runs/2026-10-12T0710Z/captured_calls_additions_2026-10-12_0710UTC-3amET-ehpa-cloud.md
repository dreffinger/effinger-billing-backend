# captured_calls additions - 2026-10-12 0710 UTC (3 AM ET 10/12) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), checkEligibility (elig_amd.py pat17478013: still zero plans), gettxhistory (unbilled_repair.py dry: 11 reason-code rows, all code-less-with-money / no-era-line), GET /api/era/checks + GET /api/era/checkdetails (era_list.py) + posterapayments validate pass (era_post.py --all-unposted --dry: 1 check, 0 postable, 3 skipped), POST /api/claim/massrebillsearch + Stedi 276/277 x19 (claim_status_sweep.py pass 66).

Behaviors noted:
- era_post.locks(checkid) takes a check id (POST /api/era/locks/release-expired per check) - a bare era_post.locks() raises TypeError; nothing was locked this run, nothing to release.
- unbilled_repair.py dry: 11 reason-code rows held (code-less payment carries money), 0 prior-payor rows, 5 'Insurance order is missing' rows left alone - no live run needed.
- No classifier refusal this run; no AMD write.
