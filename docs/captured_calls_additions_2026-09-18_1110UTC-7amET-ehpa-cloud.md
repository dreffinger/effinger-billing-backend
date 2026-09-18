# captured_calls additions - 2026-09-18T1110Z (7am ET 9/18/2026 slot, ehpa cloud Code Routine)

No new AMD call shapes this run. Behaviours worth keeping:
- getclaimrunstatus still lists 1700202 (AMD clock 2026-09-16 22:16) as the newest claim run at 11:14Z 9/18: two nightly closes (9/17, 9/18) produced no claim run - the same finding as the 6:46am ET 'morning money & posting report' (no EOD-close notice since 9/16). Nothing in the API starts a claim run; William closes the day / checks Automation Center rule status.
- State restore precedence when the newest Drive bundle is OLDER than the last run's GitHub commit: practices/ehpa/registers/ + nightly/runs/ on main win (the bundle carries no patient_db/era_details, only registers + the facesheet list).
