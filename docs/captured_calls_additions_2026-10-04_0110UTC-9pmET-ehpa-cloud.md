# captured_calls additions - run 2026-10-04T0110Z (9 PM ET 10/3, ehpa cloud)

No new call shapes this run. Calls used (all previously captured): getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaiminspectorcharges / getclaimunbillablecharges / getclaimrunstatus / getclaimexclusioncharges (columns_scan.py before + after), lookuppatient x6 (the 9/30 Pam admits still without a chart), getdemographic x11 (the 'Insurance order is missing' charts), gettxhistory typefilter=0 (txh.fetch, admission-anchor read on pat17476868), GET /api/era/checks, GET /api/era/checkdetails?checkid= (1052906 / 1052948 / 1052954 re-cached into era_details/).

No AMD writes this run: every Claim Inspector row (24) and Unbilled row (34) is a standing hold, the Exclusions list is empty, and the three ERA Center checks are unchanged (1052906 held for William; 1052948 / 1052954 $0 dismissals wait on approval A-2026-10-03T2110Z-A1, no reply yet - not re-attempted).
