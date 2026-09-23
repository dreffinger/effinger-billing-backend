# captured_calls additions - 2026-09-23 1510UTC (11am ET 9/23 slot, ehpa cloud Code Routine)

No new AMD / Stedi call shapes this run (read-only slot: columns 0/16/13/2 all standing holds, ERA Center empty).

## Behaviours confirmed
- getclaimcenteroverview still lags the list calls (exclusioncount 3 / $469 while getclaimexclusioncharges returns 2 rows on run 1700227).
- GET /api/era/checks empty at 15:17Z after POST /api/era/locks/release-expired; era_step_b before/after snapshots, era_post, era_fallback, era_clear all no-ops.

## GitHub inbox
- The 9/23 chat's PACKAGE effinger-billing-backend_2026-09-23_payer-sweep (7 base64 parts + manifest + loose PACKAGE_apply_bundle.py on Drive 'github mirror') and its follow-up payer-sweep-2 (1 part) were applied this run by tools/mirror/apply_bundle.py - see the run digest for the merge/push result.
