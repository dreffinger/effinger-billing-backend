# captured_calls additions - 2026-10-22T0640Z (3 AM ET 10/22/2026, backend billing run, ehpa cloud)

No new call shapes this run. Calls used (all already in the registry): getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches,
getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges (columns_scan.py before/after/after2); GET /api/era/checks (era_list.py);
posterapayments path (era_post.py --all-unposted, 0 lines); era_clear.py (0); Stedi 276/277 (claim_status_sweep.py pass 155, 17 asked);
getdemographic (plan_check_1022_0110.py chart 48449); gettxhistory (txh.py chart 48449); updvisitwithcharges full-visit echo with insorder="2"
onhcfa="1" + hideunbillablevisits (visit_order_release.py 48449 anchor charge 23368913 --order 2 --release --live: insorder 2,1 -> 2, success=1).
Vocabulary entries added: 0.
