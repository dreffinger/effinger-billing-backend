# captured_calls additions - backend billing run 2026-10-09T1510Z (11 AM ET 10/9/2026, ehpa cloud)

No new call shape this run. Calls used (all already in the registry): login, getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches /
getclaiminspectorcharges / getclaimunbillablecharges / getclaimrunstatus / getclaimexclusioncharges (columns_scan.py before + after),
GET /api/era/checks + GET /api/era/checkdetails?checkid= (3 new checks cached), gettxhistory visitid= (live balances before each post),
addpayments postingmethod="era" with eraclaimid / erareportid + the remit reasonlist (payreasons.post_line, 34 lines, 0 faults - checks 1053067
AARP 00148303698 and 1053069 UHC W1039352 left GET /api/era/checks by themselves once every line carried its payment),
POST /api/era/checks/dismiss {"1053071"} (the CHP check: 14 money lines posted, 4 $0 CO-243 / CO-227 lines recorded for the board),
Stedi 276/277 (claim_status_sweep.py pass 36, 21 asked), lookuppatient (admit_lookup_1510.py), getdemographic (chart_plans_1510.py + the two held charts' plans).
Lesson: an AARP Medigap 835 (secondary, claimstatus 2) posts cleanly through the era_new_* stamp copy - pay = the coinsurance, WOINS = Medicare's
contractual still sitting on the insurance balance (the primary post left it there), balances $0 on all 14 lines.
Helpers this run (stamp copies, PLAIN ENGLISH headers): era_new_1009_1510.py, era_dismiss_settled_1510.py, chart_plans_1510.py, admit_lookup_1510.py.
