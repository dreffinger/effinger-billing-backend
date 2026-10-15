# captured_calls additions - 2026-10-13 2310 UTC (7 PM ET 10/13) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt; AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), gettxhistory (unbilled_repair.py dry x11), getdemographic (chart 17478013 read-only, still zero insplans), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before/after), posterapayments dry (era_post.py --all-unposted --dry: 1053116 0 postable / 3 skipped), POST /api/claim/massrebillsearch + Stedi 276/277 x17 (claim_status_sweep.py pass 86), Stedi 271 x10 (precheck.py --days 3).

Behaviors noted:
- No AdvancedMD write this slot: every Unbilled row is a standing hold (11 reason-code rows whose UHC / TRICARE 835s are still not in the ERA Center; 7 rows of a chart with zero plans), the ERA Center holds only the UHC W0020208 takeback pair, and the UNI20/BCBS pre-5/1 pool is fully answered (16 pending, 1 unknown).
