# captured_calls additions - 2026-09-18T1710Z (1pm ET 9/18/2026 slot, ehpa cloud Code Routine)

No new AMD call shapes this run. Behaviours worth keeping:
- getclaimrunstatus still lists 1700202 (AMD clock 2026-09-16 22:16) as the newest claim run at 17:15Z 9/18 (78 runs): fourth consecutive worked slot with no nightly claim run - nothing in the API starts one; claims queued since 9/16 have not transmitted.
- The 11am ET 9/18 slot's container wrote its START marker (15:11Z) and nothing else - a routine container can die before its first AMD call; the next slot's guard treats a START older than 40 minutes with no digest as dead and proceeds.
- A complete Drive state bundle can still be OLDER than GitHub main when the run that followed it pushed registers without bundling; compare the bundle stamp to the newest nightly/runs/<stamp> before choosing the restore source.
