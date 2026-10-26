# captured_calls additions - 2026-10-26T0640Z backend billing run (3 AM ET 10/26 slot, fired 06:40Z, ehpa cloud, v7 prompt + v12/v13 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy, 06:57-07:01Z: columns_scan before/after,
insp_bypass_advisories, unbilled_repair, payreasons --unbilled, excl_dup_complete / excl_crossover_complete on runs 1700294 + 1700319,
era_list / era_post --all-unposted / era_clear, claim_status_sweep --skip-answered, sweep_register); then by hand on the one Unbilled row:
getdemographic (plans), gettxhistory (txh.py), freq1_visit.reroute (resave.set_insorder full-visit echo + updextrainsinfo resubmissioncode 1 +
chargerebill seq 2 -> 204), visit_order_release.py --release (hideunbillablevisits hide=-1, success 1), ins_update.update sequence=2 (patient
insorder), lookuppatient (admit_lookup_1026_0640.py, read-only), columns_scan final re-list.
Behaviour seen: the GitHub Billing Button slot 05:30Z had cleared 32 of 33 Unbilled rows; the one it left (chart 17473308 v19442309, CCM
99487+99489 05/17/2026, $315, 'Date of service is outside insurance coverage effective dates') pointed at the chart's Florida Blue plan that
ended 10/24/2025 while Medicare seq 2 (begin 05/01/2025) covers the DOS and carries only $0 Florida Blue denials (check 213403769) - rule A
refinement (10/14): re-route to the covering plan, ONE freq-1 rebill, release; unbilled_repair.py leaves this error on purpose and
unbilled_rules_1014.py is chart-specific (hardcoded PLAN + scan dir), so the generic freq1_visit.reroute + visit_order_release pair is the tool.
Patient insorder was blank on the chart - set to 2 so the next CCM bills Medicare on its own.
Columns 0/0/1/2 -> 0/0/0/2 (standing holds AET12 run 1700294 chart 24750; UNI98 run 1700319 chart 17475632). ERA 0 checks before/after.
UNI20/BCBS pre-5/1 277 pass: 16 PENDING chart 17472874, 0 sent.
Container lesson: amd.py reads .amd_cred.json BEFORE the AMD_PSW environment credential - on this environment (AMD_PSW set) never write the
credential file from the 2023 Gmail thread (its password may be stale and a failed login locks POI0712); the 0040Z run's no-file path is right.
