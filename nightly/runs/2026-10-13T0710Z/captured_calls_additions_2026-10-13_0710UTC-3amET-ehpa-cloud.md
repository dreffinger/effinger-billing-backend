# captured_calls additions - 2026-10-13 0710 UTC (3 AM ET 10/13) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), gettxhistory (unbilled_repair.py dry x11), GET /api/era/checks + GET /api/era/checkdetails (era_post.py --all-unposted --dry on 1053116: 0 postable / 3 skipped), POST /api/claim/massrebillsearch + Stedi 276/277 x19 (claim_status_sweep.py pass 78).

Behaviors noted:
- Columns 0/0/18/0 unchanged from the 0510Z run: the 11 reason-code rows (no-era-line, charts 21020 / 24208 / 47124) and the 7 chart-17478013 rows (zero plans) are the only Unbilled holds; no prior-payor rows re-listed this slot.
- No AdvancedMD write this run.
