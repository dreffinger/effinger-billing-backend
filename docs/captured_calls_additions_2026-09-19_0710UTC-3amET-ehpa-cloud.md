# captured_calls additions - 2026-09-19 0710 UTC (3am ET 9/19 backend billing run, ehpa cloud)

No new AMD call shapes and no new behaviours. Read-only observations (chart ids only):
- getclaimrunstatus at 07:2xZ 9/19 still lists 1700202 (2026-09-16 22:16) as the newest claim run (78 runs): eleventh consecutive worked slot with no nightly claim run.
- getclaimunbillablecharges snapshot: 14 rows / $3,030.26 (the 0510Z hideunbillablevisits release of v19455048 has left the snapshot; the 11 'Payment reason codes' rows, pat17471007's MV line and pat17477798's two 'Insurance order is missing' rows remain).
- ERA Center empty (0 checks) at 07:25Z 9/19 - era_post / fallback / era_clear all no-ops.
