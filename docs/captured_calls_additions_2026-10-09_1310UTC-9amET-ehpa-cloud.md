# captured_calls additions - backend billing run 2026-10-09T1310Z (9 AM ET 10/9/2026, ehpa cloud)

No new call shape this run. Calls used (all already in the registry): login, getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches /
getclaiminspectorcharges / getclaimunbillablecharges / getclaimrunstatus / getclaimexclusioncharges (columns_scan.py before + after),
GET /api/era/checks + GET /api/era/checkdetails?checkid= (6 checks cached), gettxhistory visitid= (live balances before each post),
addpayments postingmethod="era" with eraclaimid / erareportid + the remit reasonlist (payreasons.post_line, 77 lines, 0 faults - checks 1053061
Medicare 819948282 and 1053063 WellCare 1008839854 left GET /api/era/checks by themselves once every line carried its payment),
POST /api/era/checks/dismiss {"1053064"} (the $0 Medicare CO-29 check, every line recorded), Stedi 276/277 (claim_status_sweep.py pass 35,
21 asked), lookuppatient (admit_lookup_1310.py), getdemographic (chart_plans_1310.py).
Helpers this run (stamp copies, PLAIN ENGLISH headers): era_new_1009_1310.py, era_dismiss_settled_1310.py, chart_plans_1310.py, admit_lookup_1310.py.
