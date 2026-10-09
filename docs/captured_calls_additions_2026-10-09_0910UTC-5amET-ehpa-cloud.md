# captured_calls additions - 2026-10-09T0910Z (5 AM ET 10/9/2026, ehpa cloud backend billing run)

No new call shapes this run. Calls used (all previously captured): login (one attempt, AMD_PSW env credential), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/getclaiminspectorcharges, getclaimunbillablecharges, getclaimexclusionclaimruns/getclaimexclusioncharges (columns_scan.py before/after), getdemographic x8 (insurance plans of the held charts), gettxhistory (txh.fetch_visit, charts 17475638 + 17477640), GET /api/era/checks + checkdetails (era_list.py), posterapayments dry (era_post.py --dry, 0 posts), lookuppatient x4 (admit_lookup_0910.py), Stedi 276/277 claim status x21 (claim_status_sweep.py pass 33).

Attempted write: era_new_1009_0910.py --live (addpayments postingmethod=era, 6 lines) - refused by the environment's permission classifier (Modify Shared Resources); submitted as Mandatory Approvals A-2026-10-09T0910Z-A/B.

Columns 0/3/11/1 -> 0/3/11/1. ERA 3 checks $317.83 before and after (1052906 held, 1053058 + 1053059 waiting on the approval). Vocabulary entries added: 0.
