## 2026-10-07 11 AM ET run (2026-10-07T1510Z, ehpa cloud) - additions

No new call shapes this run. Calls used (all previously captured): login (one attempt, AMD_PSW env credential), getclaimcenteroverview + the four list calls (columns_scan.py before/after), GET /api/era/checks, GET /api/era/checkdetails (4 checks cached), POST /api/claim/massrebillsearch + Stedi claimstatus/v2 (claim_status_sweep.py, 21 x 277), gettxhistory visitid= (txh.fetch_visit), POST /api/era/checks/dismiss (check 1053025).

NEW HELPER: era_dismiss_zero.py <checkid> [--live] [--stamp] - dismisses ONE $0 ERA check whose every claim line is $0 paid, validated, and whose every named charge is at $0 insurance balance on the LIVE chart (gettxhistory visitid=); otherwise HOLD, nothing written. Register registers/era_dismiss_<stamp>[_dry].json. Fills the gap era_clear.py leaves on purpose ('denial with write-off (cascade handles)' holds a $0 check even after the cascade is done with it). Proven 10/7 1510Z on check 1053025 (WellCare 1003569030): HTTP 200 {"issuccess":true,"id":1053025,"actionname":1}, check gone from GET /api/era/checks.

claim_status_sweep.py --skip-answered takes a comma-separated list of the earlier sweep registers (registers/uni20_bcbs_pre0501_sweep_*.json, shape {about, stamp, rows}); the bare flag without a file list fails with IndexError (seen this run, re-run with the list).
