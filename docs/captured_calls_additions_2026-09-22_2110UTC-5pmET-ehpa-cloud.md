# captured_calls additions - 2026-09-22 21:10 UTC (5pm ET 9/22 slot, ehpa cloud Code Routine, run 2026-09-22T2110Z)

## Run summary (no new call shapes)
- Columns: Charge Review 0 -> 0 | Claim Inspector 11 -> 11 (all pat17472874, April-2026 stay held for the HCA admission date; error ids 394797-394807 unchanged) | Unbilled 1 -> 1 (v19441047 MCAD crossover hold) | Exclusions 0 -> 0 rows on every claim run (82 runs, newest 1700216, AMD clock 9/21 21:09).
- ERA step 5: GET /api/era/checks empty before and after (0 / $0.00); locks release-expired sent; era_post / fallback / era_clear all 0; payreasons --list 0 rows. No new 835, Availity PDF or Check/EFT export on Drive.
- Boards: Working Denials queue 0; Insurance Refresh Board 0 new drops, no row updated after 19:40Z; Pam Gmail nothing newer than the three 9/21 16:46Z readmit records.
- Calls used (all already in the registry): login_cached, getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaiminspectorcharges, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges, POST /api/era/locks/release-expired, GET /api/era/checks.
- Vocabulary: unchanged (54 entries).
