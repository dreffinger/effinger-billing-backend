# captured_calls additions - backend billing run 2026-10-08T0310Z (11 PM ET 10/7/2026, ehpa cloud)

Calls exercised (already in the registry): login (one, 03:14Z), getclaimcenteroverview + the four Claims Center list calls (columns_scan.py before/after), GET /api/era/checks (1 check, unchanged) and GET /api/era/checkdetails?checkid=1052906 (17 lines, through era_list.py), posterapayments dry pass (era_post.py --all-unposted --dry: 17 lines skipped, 0 postable, nothing sent), POST /api/claim/massrebillsearch + Stedi 276/277 (claim_status_sweep.py pass 19, 21 asked, 227 skipped).

- No new call shape this run. No new helper.
- No AdvancedMD write this run (columns 0/1/0/1 = the two standing holds; ERA list = 1052906 only, William's takeback decision).
