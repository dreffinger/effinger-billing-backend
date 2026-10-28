# captured_calls additions - 2026-10-28T0040Z backend billing run (9 PM ET 10/27 slot, fired 00:40Z 10/28, ehpa cloud, v7 prompt + v12/v13 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy, 00:46-00:50Z: columns_scan before/after,
insp_bypass_advisories, unbilled_repair, payreasons --unbilled, excl_dup_complete / excl_crossover_complete on runs 1700294 + 1700319,
era_list / era_post --all-unposted / era_clear, claim_status_sweep --skip-answered, sweep_register); lookuppatient (admit_lookup_1028_0040.py, read-only, three patterns).
Behaviour seen: columns 0/0/0/2 -> 0/0/0/2 (standing holds AET12 run 1700294 pat24750; UNI98 run 1700319 pat17475632); ERA 0 checks before/after;
UNI20/BCBS pre-5/1 sweep pass 165: 15 PENDING pat17472874, 0 sent. Three Pam admits (10/19, 10/22, 10/23) still without an AMD chart. No AMD write this run.
Container lesson: a separate `git worktree add /home/claude/effinger-billing-backend origin/main -b main` from the session clone keeps main checked out
regardless of a modified reports/button/latest.json in the session branch - the 10/27 1840Z checkout trap does not arise.
