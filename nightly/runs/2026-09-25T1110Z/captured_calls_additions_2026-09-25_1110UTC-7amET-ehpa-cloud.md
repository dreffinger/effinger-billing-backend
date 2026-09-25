# captured_calls additions - run 2026-09-25T1110Z (7am ET 9/25/2026, ehpa cloud Code Routine)
No new call shape this run. Behaviours confirmed:
- getclaimcenteroverview at 11:2xZ: chargereview 0 / inspector 20 ($3,846) / unbilled 26 ($5,252) / exclusions 8 ($1,268 - the overview count lags; getclaimexclusioncharges per run lists 2) / claimrunstatus 83 runs; newest claim run still 1700236 - the four list calls returned exactly the 0910Z rows.
- GET /api/era/checks answered an empty list before and after (ERA Center empty since the 0910Z run cleared 1052840/1052841); POST /api/era/locks/release-expired accepted on an empty Center.
- payreasons.py --list on an Unbilled list with no 'Payment reason codes' rows prints 0 rows / SUMMARY {} and makes no write.
