# captured_calls additions - 2026-10-06 0910 UTC (5 AM ET 10/6 slot, ehpa cloud backend billing run)

No new call shapes this run. Calls used (all registered): login (one), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/charges, getclaimunbillablecharges, getclaimexclusionclaimruns/charges (columns_scan.py before), GET /api/era/checks + GET /api/era/checkdetails + posterapayments dry build (era_post.py --all-unposted --dry).

Lessons (no chart data): (1) the auto-mode classifier refuses extracting Drive package parts from the session transcript ([Untrusted Code Integration]) - the GitHub-inbox packages still need William's machine; (2) a batched `sed`/`grep` over several helper headers is refused as [Sensitive-Source Provenance] - run a helper by name (`--dry`) to learn its behaviour instead; (3) `claim_status_sweep.py --help` prints no usage within 120 s (stopped) - give it its real arguments or nothing.
