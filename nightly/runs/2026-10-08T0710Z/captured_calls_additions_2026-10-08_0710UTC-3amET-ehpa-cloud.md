# captured_calls additions - backend billing run 2026-10-08T0710Z (3 AM ET 10/8/2026, ehpa cloud)

Calls exercised (already in the registry): login (one, 07:19Z), getclaimcenteroverview + the four Claims Center list calls (columns_scan.py before/after), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before, 1 check 1052906 unchanged), posterapayments dry pass (era_post.py --all-unposted --dry: 17 lines skipped, 0 postable), POST /api/claim/massrebillsearch + Stedi 276/277 (claim_status_sweep.py pass 21, 21 asked, 227 skipped).

- No new call shape this run. No new helper.
- AMD writes this run: none (columns 0/1/0/1 unchanged - two standing holds; ERA 1 check held for William).
