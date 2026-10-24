# captured_calls additions - 2026-10-24T0640Z backend billing run (3 AM ET 10/24 (fired 06:40Z), ehpa cloud, v7 prompt + v12/v13 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(columns_scan before/after, insp_bypass_advisories, unbilled_repair, payreasons --unbilled, excl_dup_complete / excl_crossover_complete
on runs 1700294 + 1700319, era_list / era_post --all-unposted / era_clear, claim_status_sweep --skip-answered, sweep_register),
lookuppatient (admit_lookup_1024_0640.py, read-only). No AdvancedMD write this run.
Behaviour seen: nothing new - the two exclusion rows are the standing carrier-record holds (AET12 PREF0288 on run 1700294; UNI98
'CH EC MISSING PAYER CITY' + 'L2010BB.N4 missing state code' on run 1700319); the ERA Center was empty before and after; the UNI20
pre-5/1 277 pass answered PENDING on all 16 chart-17472874 visits again (pass 163).
