# captured_calls additions - backend billing run 2026-10-18T0110Z (9 PM ET 10/17/2026, ehpa cloud)

No new call shapes this run. Calls used, all already in the registry: login (one attempt, AMD_PSW environment credential), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus + getclaimexclusioncharges (clearinghouse=1 payer=1; columns_scan.py before/after), getdemographic x3 (live insplan re-check of the zero-plan charts pat17478059 / pat17478063 / pat17478064 - still 0 plans), lookuppatient x3 (admit_lookup_1017_1710.py - the three 10/15 admits still have no chart), GET /api/era/checks x2 (era_list.py before/after, 0 checks), massrebillsearch + Stedi 276/277 claim status x17 (claim_status_sweep.py pass 133, --skip-answered with the comma-joined sweep registers: 16 PENDING + 1 UNKNOWN). No AdvancedMD write.

Behaviors noted:
- Drive 'workspace mirror' search by parentId + modifiedTime returns the folder in pages of ~5 with a nextPageToken; a title filter ('workspace_state_', 'manifest.json') still lists only the 2026-09-18 bundle manifests - no newer state bundle exists (standing since 10/10).
- The Insurance Refresh Board items collection answers a where-in query on amdid (4 ids -> 5 rows) in one call; the board's drive_sync 'applied' map still ends 9/20 (page registry not recording), so no inbox file was trashed.
