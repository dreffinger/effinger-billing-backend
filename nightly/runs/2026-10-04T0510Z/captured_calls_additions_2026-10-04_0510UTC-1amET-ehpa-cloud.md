# captured_calls additions - 2026-10-04 05:10 UTC (1 AM ET 10/4) backend billing run, ehpa cloud

No new call shapes this run. Behaviours recorded:
- The routine environment's auto-mode classifier refused every AdvancedMD WRITE helper again ('Real-World Transactions': act_0310_1004.py, act_0510_1004.py) and a second-page board read with out_dir ('PII Data Handling'); reads (getdemographic, gettxhistory, checkEligibility, lookupcarrier, GET /api/era/checks + checkdetails, Stedi), Drive uploads, Gmail send and push all pass. Approval register add/build passed this run (it was refused 'Modify Shared Resources' at 0310Z).
- addreferralplan reminder (from the 9/8 Allen capture, to be re-tested by A-2026-10-04T0510Z-A2 item I): with ismain="0" status="stat1" the call INSERTS a blank plan and returns its rplan id; the bare shape get-or-returns the main plan.
- Patient name storage: a suffix typed into the last-name field ('SCOTT III') makes Medicare's 271 reject AAA 73 (subscriber name); the PATCH /api/demographic/patients/{id} names[] entry has separate lastname / suffix / prefixSuffix fields (patient_patch.patch(pid, {"names": [...]})).
