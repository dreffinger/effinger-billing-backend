# captured_calls additions - 2026-09-18T2110Z (5pm ET 9/18/2026 slot, ehpa cloud Code Routine)

No new AMD call shapes this run. Behaviours worth keeping:
- A Sunshine (SUN01) 835 pair arrives as two ERA Center checks: the money check (1051710, ACH 0917702417) posts cleanly through posterapayments (era_post --all-unposted, 2 visits, HTTP 200) and leaves GET /api/era/checks on its own; the companion $0 check (1051711, X319609686) carries only denial lines with a WOMCAD write-off code - era_clear dismisses it (POST /api/era/checks/dismiss) and the lines go to the Working Denials board, never to a manual post.
- OA23 + CO45 on a Sunshine secondary line = Medicare already adjudicated the visit and Sunshine (QMB/crossover) pays $0 on the coinsurance; the remit-stored insurancebalance equals the Medicare coinsurance (21.80 on a 99232) - contractual per William's 9/7 rule, not a patient balance.
- getclaimrunstatus still lists 1700202 (AMD clock 2026-09-16 22:16) as the newest claim run at 21:17Z 9/18 (78 runs): sixth consecutive worked slot with no nightly claim run - nothing in the API starts one.
