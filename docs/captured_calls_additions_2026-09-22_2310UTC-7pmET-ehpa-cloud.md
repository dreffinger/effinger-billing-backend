# captured_calls additions - 2026-09-22 23:10 UTC (7 PM ET 9/22 backend billing run, ehpa cloud)

No new call shapes this run. Every call used is already in the registry: getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/charges, getclaimunbillablecharges, getclaimexclusionclaimruns/charges, getclaimrunstatus, GET /api/era/checks, GET /api/era/checkdetails, POST /api/era/locks/release-expired, posterapayments (era_post --all-unposted), POST /api/era/checks/dismiss (era_clear), gettxhistory (txh.fetch), Stedi MBI lookup / eligibility (precheck --days 3).

Run facts: columns 0/11/1/0 -> 0/11/1/0 (unchanged); ERA 1 check / $83.13 -> 0 / $0.00 (Centene 1051741 trace 0917735332: $83.13 auto-posted on pat17472703 v19454648 with CO45 $76.87 WOMCAD; 8 $0 denial lines - 4 FCC CO-26 held per the 9/22 FCC rule, 2 Sunshine CO-16/M56 joined to the centene-m56 cluster, 2 already at $0; dismissed). Precheck 17 pairs, 0 flagged. No AMD write other than the ERA Center post.
