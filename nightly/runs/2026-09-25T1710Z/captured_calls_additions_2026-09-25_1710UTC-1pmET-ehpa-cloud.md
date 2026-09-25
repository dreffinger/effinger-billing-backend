# captured_calls additions - run 2026-09-25T1710Z (1pm ET 9/25/2026, ehpa cloud Code Routine)
No new call shape this run. Behaviours confirmed:
- getclaimcenteroverview at 17:20Z: chargereview 0 / inspector 20 ($3,846) / unbilled 26 ($5,252) / exclusions 8 ($1,268 - lags; per-run list = 2) / claimrunstatus 83 runs; newest claim run still 1700236 - the four list calls returned exactly the 1510Z rows (same 20 inspector error ids 394797-395161).
- GET /api/era/checks: 0 unposted checks at 17:22Z (the 1510Z run's three checks stayed cleared); POST /api/era/locks/release-expired sent; payreasons --list 0 Unbilled 'Payment reason codes' rows.
- amd.login_cached(): one relogin at 17:20Z from a fresh container (.session.json written, .amd_login_lock cleared on success) - the 1510Z session token was not carried over (state bundle not unpacked), so each fresh container costs exactly one login.
