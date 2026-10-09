# captured_calls additions - backend billing run 2026-10-09T1910Z (3 PM ET 10/9/2026, ehpa cloud)

No new call shape this run. Calls used (all already in the registry): login, getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches /
getclaiminspectorcharges / getclaimunbillablecharges / getclaimrunstatus / getclaimexclusioncharges (columns_scan.py before + after),
GET /api/era/checks (3 checks, all standing holds - nothing new), posterapayments dry pass (era_post.py --all-unposted --dry: 1052906 17 lines
skipped, 1053058 2 postable lines left to card A-2026-10-09T0910Z-A; nothing posted), gettxhistory typefilter=0 (chart 17474046 re-read: the
10/05/2026 99223 visit v19457421 is now on the chart), updextrainsinfo hospitalizationfrom + updvisitwithnewcharges full-visit resave onhcfa=1
(insp_1009_1910.py: v19457421 / v19457309 / v19457308, admission 10/05/2026, 0 faults), getdemographic (chart_plans_1710.py: the six Unbilled
charts still carry zero plans), lookuppatient (admit_lookup_1910.py: two of the four 10/8 Brynwood admits still have no chart), Stedi 276/277
(claim_status_sweep.py pass 38, 21 asked: 20 PENDING, 1 UNKNOWN, 0 sent).
AdvancedMD writes this run: 3 visits of chart pat17474046 (admission date + resave). Helpers this run (stamp copies, PLAIN ENGLISH headers):
insp_1009_1910.py (from insp_1008_1910.py), admit_lookup_1910.py.
