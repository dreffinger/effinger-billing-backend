# captured_calls additions - backend billing run 2026-10-08T0110Z (9 PM ET 10/7/2026, ehpa cloud)

Calls exercised (already in the registry): login (one, 01:18Z), getclaimcenteroverview + the four Claims Center list calls (columns_scan.py before/after), GET /api/era/checks (1 check, unchanged) and GET /api/era/checkdetails?checkid=1052906 (17 lines, cached through the new read-only helper era_list.py), posterapayments dry pass (era_post.py --all-unposted --dry: 17 lines skipped - $0 / 'multiple adjustment amounts' / held), POST /api/claim/massrebillsearch + Stedi 276/277 (claim_status_sweep.py pass 18, 21 asked).

- No new call shape this run. New READ-ONLY helper era_list.py (`python3 era_list.py <tag> <stamp>`): GET /api/era/checks counted and totalled into registers/era_checks_<tag>_<stamp>.json, checkdetails cached for every check not yet in era_details/ - the standing before/after read of step 5(b), no inline heredoc needed.
- No AdvancedMD write this run (columns 0/1/0/1 = the two standing holds; ERA list = 1052906 only, William's takeback decision).
