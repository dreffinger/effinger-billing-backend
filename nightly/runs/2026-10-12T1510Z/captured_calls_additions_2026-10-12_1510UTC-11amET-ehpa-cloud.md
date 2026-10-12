# captured_calls additions - 2026-10-12 1510 UTC (11 AM ET 10/12) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), gettxhistory (payreasons.py --list x11), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before/after), POST /api/era/locks/release-expired (era_post.locks(1053116) - nothing locked), posterapayments dry plan (era_post.py --all-unposted --dry: 0 postable, 3 skipped), era_clear.py --dry (HOLD), POST /api/claim/massrebillsearch + Stedi 276/277 x19 (claim_status_sweep.py pass 70).

Behaviors noted:
- era_post.locks takes the check id (era_post.locks(checkid)); the reply lists featurelocks AutoERAProcessingBOT and ERA_ReportID_<checkid>, both locked=false on 1053116.
- No AMD write this slot. Stedi insurance lookups not re-asked for chart 17478013 (the 13:21Z answers of record stand: MBI ERR 72, discovery 0 found).
