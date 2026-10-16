# captured_calls additions - backend billing run 2026-10-16T2110Z (5 PM ET 10/16/2026, ehpa cloud)

No new call shapes this run. Calls used: login (cached), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges, getdemographic, lookuppatient, gettxhistory (visitid=), checkEligibility (free 271, 4 charts), GET /api/era/checks, GET /api/era/checkdetails (1053196 / 1053197 / 1053198), GET /api/era/checks/dismiss?DismissedDateBegin=2026-10-16, Stedi 276 claim status x17, addpayments postingmethod=era (payreasons.post_line, 10 lines, all 200).

Observation (not a new shape): the Billing Button slot at 21:22Z Post-buttoned Humana 203380621261016 and dismissed all three new checks (dismissedat 14:25 AMD clock = 21:25Z) between this run's ERA list read (21:17Z) and its posting pass; the ERA-linked WOCAID2ND posts against the dismissed checks' claim ids still answered 200 and balanced the visits.
