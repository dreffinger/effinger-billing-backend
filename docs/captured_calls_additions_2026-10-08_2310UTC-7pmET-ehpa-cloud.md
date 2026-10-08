# captured_calls additions - 2026-10-08T2310Z (7 PM ET 10/8/2026, ehpa cloud backend billing run)

No new call shapes this run. Calls used (all previously captured): login (one attempt, AMD_PSW env credential), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/getclaiminspectorcharges, getclaimunbillablecharges, getclaimexclusionclaimruns/getclaimexclusioncharges (columns_scan.py before/after), GET /api/era/checks + checkdetails (era_list.py), posterapayments dry (era_post.py --dry, 0 posts), lookuppatient (admit_lookup_2310.py, read-only), getdemographic (read), Stedi 276/277 claim status (claim_status_sweep.py, 21 claims), precheck.py (0 pairs). No AMD write.

Columns 0/3/0/1 -> 0/3/0/1 (standing holds). ERA 1 check $104.19 (1052906 held) before and after. UNI20/BCBS pre-5/1 pass 29: 20 PENDING, 1 UNKNOWN, 0 sent. Vocabulary entries added: 0.
