## 2026-09-22 05:10 UTC - 1am ET 9/22 columns run (ehpa cloud) - additions

No new call shapes this run. Behaviour learned (registry note, not a new call):
- `updextrainsinfo` (hospitalizationfrom) on its own never re-runs the Claim Inspector - only the full-visit resave (`updvisitwithnewcharges`, every live charge echoed by id, onhcfa=1) does. A referral-plan repoint saved without the extins block (the 9/22 chat referring-provider correction) wipes `hospitalizationfrom` on the visit, which puts already-PAID hospital visits back in the inspector.
- `gettxhistory` pagenumber=1 with typefilter=1 stops short on a 100-charge chart (pat12231996's 12/16/2025 99223 was on the missing part) - anchor searches read `txh.fetch` (typefilter=0, full history).
- Stedi Humana (61101) eligibility answers with the MBI as memberId and returns the Humana member id (pat17477819: PPO 'Alcoa' group Medicare Advantage, H49353396, planBegin 20260101) - the MA member id without a facesheet.
- Stedi FL Medicaid 77027: AAA 42 'Unable to Respond at Current Time' x4 across 90 seconds this slot (payer outage) - the QMB Medicaid number for pat17477818 waits for the next run.
Helpers this run: insp_0922_0510.py / _0510b.py / _0510c.py / _0510d.py (--allow-paid: paid visits whose admission date the repoint wiped), insp_dateonly_0922_0510.py, newcharts_0922_0510.py, excl_1700216_0922_0510.py, unbilled_release_0922_0510.py, era_chain_0922_0510.sh, run_outputs_0922_0510.py.
