# captured_calls additions - run 2026-10-03T1310Z (9 AM ET 10/3, ehpa cloud)

No new AMD call shapes this run (columns_scan.py before/after, reads_1310_1003.py = lookuppatient x6 + getdemographic x11 + GET /api/era/checks + checkdetails, gettxhistory/getdemographic on one chart, era_clear.py --carrier WEL04 = POST /api/era/checks/dismiss). One AMD write: ERA check 1052945 (WellCare, $0.00, one CO-18 exact-duplicate line on pat17477375 v19455316) dismissed after the line was recorded in era_manual_register.json. Lesson recorded:

- A payer can answer the SAME duplicate denial on two ERA checks days apart (1052922 on 10/1, 1052945 on 10/3 - both CO-18 on claim B of the 9/27 resend). The register entry from the first check is the guard: match on visit id + CARC before treating the second as new; the original claim's 277 status (pending) is what decides whether anything is rebilled - never the duplicate line.
