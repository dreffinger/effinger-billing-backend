# captured_calls additions - backend billing run 2026-10-08T1710Z (1 PM ET 10/8/2026, ehpa cloud)

Calls exercised (already in the registry): login (one, 17:15Z), getclaimcenteroverview + the four Claims Center list calls (columns_scan.py before/after), GET /api/era/checks x2 (era_list.py before/after; 1052906 details cached), posterapayments dry pass only (era_post.py --all-unposted --dry: 1052906 0 postable / 17 skipped), POST /api/claim/massrebillsearch + Stedi 276/277 x21 (claim_status_sweep.py pass 26), lookuppatient name wildcard x2 ([name]% / BARCELO% - empty), Stedi eligibility v3 x2 (CMS by MBI; Humana 61101 by member) for Pam's new Brynwood admit.

- **No new call shape this run.** No helper changed.
- Columns 0/1/0/1 -> 0/1/0/1 (CCI hold pat20863; UNI20 'Medicare is primary' hold pat17473087). ERA 1 check ($104.19, 1052906 held) before and after. UNI20/BCBS pre-5/1 pass 26 = the same 21 answers as passes 12-25 (20 PENDING, 1 UNKNOWN), 0 candidates, 0 sent.
- Pam admit 17:16Z (Brynwood 10/7/2026): no AMD chart yet; Stedi CMS 271 = Medicare A/B since 2008 with a Humana PPO Medicare Advantage entity (COB 11/1/2013); Stedi Humana 61101 = HumanaChoice ACTIVE since 1/1/2023. Pending-admit record in patient_db/_pending_admits/ (state bundle only); board row on Claude's turn.
- AMD writes this run: none. No classifier refusal.
