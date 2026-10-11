# captured_calls additions - 2026-10-11 1910 UTC (3 PM ET) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW env), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), GET /api/era/checks (2 unposted), GET /api/era/checkdetails?checkid= (1053096, 1053116 via era_post --dry), payreasons.py --list (11 rows no-era-line), gettxhistory (repost_fix_1011.py dry: the 3 code-less payments still live), Stedi 276/277 claim status x19 (claim_status_sweep.py pass 60).

Behaviors noted:
- The Drive connector's search_files `modifiedTime >` filter compares the DATE only (files modified earlier the same day are returned) - use list_recent_files orderBy lastModified for 'anything new since the last run'.
- Both Mandatory Approvals cards were approved on the page at 17:37Z while practices/ehpa/registers/approvals_pending.json on main still said waiting; the approved command of A-2026-10-11T0710Z-A names tf_wolate_1011.py, which was never committed (the 0710Z run wrote no digest and no commit).
