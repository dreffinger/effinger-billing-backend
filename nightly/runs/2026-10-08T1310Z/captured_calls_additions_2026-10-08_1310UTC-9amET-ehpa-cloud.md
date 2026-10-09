# captured_calls additions - backend billing run 2026-10-08T1310Z (9 AM ET 10/8/2026, ehpa cloud)

Calls exercised (already in the registry): login (one, 13:16Z), getclaimcenteroverview + the four Claims Center list calls (columns_scan.py before/after), GET /api/era/checks x2 + GET /api/era/checkdetails?checkid= (era_list.py before/after: 1052906 re-cached), posterapayments dry pass only (era_post.py --all-unposted --dry, 0 postable / 17 skipped), POST /api/claim/massrebillsearch + Stedi 276/277 x21 (claim_status_sweep.py pass 24).

- **No new call shape this run.** No AdvancedMD write of any kind: Charge Review 0, Claim Inspector 1 (CCI hold), Unbilled 0, Exclusions 1 (UNI20 'Medicare is primary' hold), ERA 1 check held (1052906), UNI20/BCBS pre-5/1 pass 24 = the same 21 answers as passes 12-23 (20 PENDING, 1 UNKNOWN), 0 candidates, 0 sent.
- AMD writes this run: none. No classifier refusal.
