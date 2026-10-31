# captured_calls additions - backend billing run 2026-10-30T1240Z (9 AM ET 10/30 slot, ehpa cloud)

No new call shapes this run. Calls used (all registered): login (one), getclaimcenteroverview / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus / getclaimexclusioncharges (columns_scan before + after), GET /api/era/checks (era_list before + after, 0 checks), massrebillsearch + Stedi 277 (claim_status_sweep pass 172), checkEligibility (AMD free 271, chart pat17472874, 3 plans), Stedi 270/271 CMS + 87726 at DOS 2026-04-07 (pat17472874), gettxhistory (pat17472874 two visits). No AMD write.

Lesson: claim_status_sweep.py has no --help flag - any unknown argument starts a default pass (--min-age 45 --max 100); read the docstring (head -12) instead of probing.
