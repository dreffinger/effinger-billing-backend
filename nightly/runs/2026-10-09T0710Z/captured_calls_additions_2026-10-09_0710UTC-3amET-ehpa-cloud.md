# captured_calls additions - 2026-10-09T0710Z (3 AM ET 10/9/2026, ehpa cloud backend billing run)

No new call shapes this run. Calls used (all previously captured): login (one attempt, AMD_PSW env credential), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/getclaiminspectorcharges, getclaimunbillablecharges, getclaimexclusionclaimruns/getclaimexclusioncharges (columns_scan.py before/after), gettxhistory (txh.fetch, chart 17474046 + 17472396 reads), GET /api/era/checks + checkdetails (era_list.py), posterapayments dry (era_post.py --dry, 0 posts), bypassclaimedits (insp_bypass_advisories.py --live, 1 visit), Stedi 276/277 claim status x21 (claim_status_sweep.py pass 32).

Columns 0/4/11/1 -> 0/3/11/1. ERA 1 check $104.19 (1052906 held) before and after. Vocabulary entries added: 0.
