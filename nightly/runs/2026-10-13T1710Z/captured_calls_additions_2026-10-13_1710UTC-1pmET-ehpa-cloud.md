# captured_calls additions - 2026-10-13 1710 UTC (1 PM ET 10/13) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), gettxhistory (unbilled_repair.py dry x11; payreasons.py --list x11), getdemographic (chart 17478013 - zero insplans, address line 1 set), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before/after, era_post.py --all-unposted --dry, era_clear.py --dry), POST /api/era/locks/release-expired (era_post.locks(1053116) - nothing locked), POST /api/claim/massrebillsearch + Stedi 276/277 x17 (claim_status_sweep.py pass 83, --skip-answered passes 1-82: 270 skipped).

Behaviors noted:
- Columns 0/0/18/0 and ERA 1 check $71.00 unchanged from the 1510Z run; the Billing Button's :17 live 'columns' run (68802f2 at 15:33Z) overlapped the 1510Z slot again; no button commit had landed on main by 17:25Z for this slot. Two engines, neither wrote.
- The routine was delivered its v7 text again; the v12 rules on main were applied (bootstrap 0a-0i, step 5(b2), the ONE REBILL / TIMELY-FILING WATCH flags).
