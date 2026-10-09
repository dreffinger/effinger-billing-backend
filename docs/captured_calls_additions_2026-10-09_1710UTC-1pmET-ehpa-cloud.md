# captured_calls additions - backend billing run 2026-10-09T1710Z (1 PM ET 10/9/2026, ehpa cloud)

No new call shape this run. Calls used (all already in the registry): login, getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches /
getclaiminspectorcharges / getclaimunbillablecharges / getclaimrunstatus / getclaimexclusioncharges (columns_scan.py before + after),
GET /api/era/checks (3 checks, all standing holds - nothing new), posterapayments dry pass (era_post.py --all-unposted --dry: 1052906 17 lines
skipped, 1053058 2 postable lines left to card A-2026-10-09T0910Z-A; nothing posted), gettxhistory visitid= (chart 17474046 re-read: 99233 only, no
99223 anchor), getdemographic (chart_plans_1710.py: the six Unbilled charts still carry zero plans), lookuppatient (admit_lookup_1710.py: two of
the four 10/8 Brynwood admits still have no chart), Stedi 276/277 (claim_status_sweep.py pass 37, 21 asked: 20 PENDING, 1 UNKNOWN, 0 sent).
No AdvancedMD write this run. Helpers this run (stamp copies, PLAIN ENGLISH headers): chart_plans_1710.py, admit_lookup_1710.py.
