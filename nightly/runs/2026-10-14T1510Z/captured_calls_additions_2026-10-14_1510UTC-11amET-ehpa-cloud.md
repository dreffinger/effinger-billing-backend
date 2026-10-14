# captured_calls additions - 2026-10-14 1510 UTC (11 AM ET 10/14) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt; AMD_PSW environment credential), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaiminspectorcharges / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before/after, era_post.details), posterapayments dry (era_post.py --all-unposted --dry), era_clear.py --dry x2, addpayments postingmethod=era (payreasons.post_line x4 inside era_new_1014_1510.py - the ERA-linked Payment Entry shape), gettxhistory visitid= (txh.fetch_visit: 4 live reads before/after each post + 34 NOT-ON-FILE billdate reads in sweep_eval_1014_1510.py), POST /api/claim/massrebillsearch + Stedi 276/277 x60 (claim_status_sweep.py pass 94).

Behaviors noted:
- A check whose every line is posted ERA-linked (payreasons.post_line, 4 x CAP07 lines of 1053160) leaves GET /api/era/checks on its own - no dismiss call needed (era_clear --dry afterwards listed only 1053116). Same as 1053151 on 10/13 and 1053153 on 10/14 1110Z.
- CAP07 primary lines carry CO-45 + CO-253 only (no PR) on 99223 / 99232 - pay + WOINS = fee exactly, both balances 0.00 after the post.
- claim_status_sweep.py --skip-answered with the 86 pass registers skipped 485 visits; the 34 NOT-ON-FILE rows all carry billdate 10/13/2026 (the 10/13 BILL-SECONDARY sends) - not yet on file, 0 candidates.
