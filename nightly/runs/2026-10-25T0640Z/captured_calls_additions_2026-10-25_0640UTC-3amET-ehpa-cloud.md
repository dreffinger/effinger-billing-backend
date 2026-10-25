# captured_calls additions - 2026-10-25T0640Z backend billing run (3 AM ET 10/25 slot, fired 06:39Z, ehpa cloud, v7 prompt + v12/v13 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy, 06:55-06:59Z: columns_scan before/after,
insp_bypass_advisories, unbilled_repair, payreasons --unbilled, excl_dup_complete / excl_crossover_complete on runs 1700294 + 1700319 +
1700323, era_list / era_post --all-unposted / era_clear, claim_status_sweep --skip-answered, sweep_register), excl_crossover_complete.py
(gettxhistory read + hideexclusions hide=-1 on run 1700323, re-list getclaimexclusioncharges), lookuppatient (admit_lookup_1024_1840.py,
read-only), getclaimcenteroverview.
Behaviour seen: excl_crossover_complete.py left the Florida Blue PREF0283 row of v19456319 (chart 17477516) because the 99497 charge's
live carrier still read FLO02 after Medicare paid it (the 99349 had flipped to BCBS) - gate widened 10/25 to accept a Medicare-flagged
charge that Medicare paid with only its PR coinsurance open; dry then live -> hideexclusions success, re-list 0. getclaimcenteroverview
still showed exclusioncount=3 right after (counts lag - trust the list calls).
Columns 0/0/0/3 -> 0/0/0/2 (standing holds AET12 run 1700294 chart 24750; UNI98 run 1700319 chart 17475632). ERA 0 checks before/after.
UNI20/BCBS pre-5/1 277 pass 167: 16 PENDING chart 17472874, 0 sent.
Container lesson: fresh container had no python requests - installed before the engine pass (no lost pass).
