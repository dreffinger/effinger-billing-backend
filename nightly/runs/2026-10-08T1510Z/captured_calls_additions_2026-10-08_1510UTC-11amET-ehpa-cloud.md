# captured_calls additions - backend billing run 2026-10-08T1510Z (11 AM ET 10/8/2026, ehpa cloud)

Calls exercised (already in the registry): login (one, 15:15Z), getclaimcenteroverview + the four Claims Center list calls (columns_scan.py before/after), GET /api/era/checks x2 + GET /api/era/checkdetails?checkid= (era_list.py before/after: 1053052 cached), posterapayments dry pass only (era_post.py --all-unposted --dry: 1052906 0 postable / 17 skipped; 1053052 1 postable, Post button not used), addpayments postingmethod=era x2 (payreasons.post_line via era_new_1008_1510.py - check 1053052 TRICARE East, chart 17477946 v19456584: pay $174.18 + WOINS $156.76, PR-2 $58.06 to the patient, 0 faults), getdemographic x3 (read-only re-checks of charts 17473087 / 20863 / 17477946), POST /api/claim/massrebillsearch + Stedi 276/277 x21 (claim_status_sweep.py pass 25).

- **No new call shape this run.** The ERA-linked posting helper era_new_1008_1510.py is a stamp/check-id copy of era_new_1008_1110.py (no code change).
- Columns 0/1/0/1 -> 0/1/0/1 (CCI hold chart 20863; UNI20 'Medicare is primary' hold chart 17473087). ERA 2 checks ($104.19 + $174.18 unposted) -> 1 check ($104.19 held). UNI20/BCBS pre-5/1 pass 25 = the same 21 answers as passes 12-24 (20 PENDING, 1 UNKNOWN), 0 candidates, 0 sent.
- AMD writes this run: 2 ERA-linked addpayments. No classifier refusal.
