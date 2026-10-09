# captured_calls additions - 2026-10-09T1110Z (7 AM ET 10/9/2026, ehpa cloud backend billing run)

No new call shapes this run. Calls used (all previously captured): login (one attempt), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/getclaiminspectorcharges, getclaimunbillablecharges, getclaimexclusionclaimruns/getclaimexclusioncharges (columns_scan.py before/after), getdemographic x6 (chart_plans_1110.py - insurance plans of the six held Unbilled charts, all still zero), lookuppatient x2 (admit_lookup_1110.py), GET /api/era/checks + checkdetails (era_list.py before/after), posterapayments dry (era_post.py --dry --all-unposted, 0 posts), Stedi 276/277 claim status x21 (claim_status_sweep.py pass 34).

Attempted writes: none (the two postable Humana lines of 1053058 are covered by the waiting approval cards A-2026-10-09T0910Z-A/B - not re-attempted).

Columns 0/3/11/1 -> 0/3/11/1. ERA 3 checks $317.83 before and after. Vocabulary entries added: 0.
