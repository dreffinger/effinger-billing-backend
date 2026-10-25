# captured_calls additions - 2026-10-25T1240Z backend billing run (9 AM ET 10/25 slot, fired 12:40Z, ehpa cloud, v7 prompt + v12/v13 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy, 12:52-12:56Z: columns_scan before/after,
insp_bypass_advisories, unbilled_repair, payreasons --unbilled, excl_dup_complete / excl_crossover_complete on runs 1700294 + 1700319,
era_list / era_post --all-unposted / era_clear, claim_status_sweep --skip-answered, sweep_register), lookuppatient (admit_lookup_1025_1240.py,
read-only), getclaimcenteroverview.
Behaviour seen: nothing new - columns 0/0/0/2 unchanged (standing holds AET12 run 1700294 chart 24750; UNI98 run 1700319 chart 17475632);
ERA Center 0 checks before/after; UNI20/BCBS pre-5/1 277 pass 162: 16 PENDING chart 17472874, 0 sent. No AMD write this slot.
Container lesson (repeat): fresh container had no python requests - installed before the engine pass.
