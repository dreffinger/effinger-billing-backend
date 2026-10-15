# captured_calls additions - 2026-10-15 0110 UTC (9 PM ET 10/14) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, 01:22Z; AMD_PSW environment credential), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaiminspectorcharges / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before and after), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before/after - 1 check, cached), posterapayments dry evaluation only (era_post.py --all-unposted --dry on 1053116: 0 postable), era_clear.py --dry (HELD), Stedi 276/277 x17 (claim_status_sweep.py pass 98 - read-only). No AdvancedMD write this run.

Behaviors noted:
- Columns 0/5/28/19 and the ERA Center (1 check, $71 held) are identical to the 2310Z run: every row is a standing hold or waits on approval cards A-2026-10-14T1910Z-B / -C.
- The 277 for chart 17472874's 3/4/2026 visit now reads 'Claim has been adjudicated and is awaiting payment cycle' (status P1/20 family) while the other 15 read 'Accepted for processing' - still PENDING under the sweep's rules; an 835 should follow.
- The Drive connector's modifiedTime filter on a Drive-wide search returned files older than the bound (10/14 04:27Z for a > 23:40Z filter); the per-folder parentId queries behaved - use parentId + modifiedTime per watched folder.
