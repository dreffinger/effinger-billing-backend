# captured_calls additions - 2026-10-13 0310 UTC (11 PM ET 10/12) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), gettxhistory (payreasons.py --list x11, unbilled_repair.py dry x11), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before; 1053116, 3 claim rows), posterapayments dry plan (era_post.py --all-unposted --dry on 1053116: 0 postable / 3 skipped), era_clear.py --dry (HOLD 1053116), POST /api/claim/massrebillsearch + Stedi 276/277 x19 (claim_status_sweep.py pass 76).

Behaviors noted:
- No AdvancedMD write this slot: every row on the four columns is a standing hold (11 reason-code rows waiting on UHC / TRICARE 835s not in the ERA Center, 5 rows on one chart with zero plans), the one ERA check is William's takeback decision, and the 277 sweep returned the same 18 PENDING + 1 UNKNOWN as passes 54-75.
- The Billing Button's 0317Z live 'columns' run had not committed when this run fetched main at 03:21Z (latest button commit 2026-10-13T0151Z) - the two-engines overlap WATCH stands.
