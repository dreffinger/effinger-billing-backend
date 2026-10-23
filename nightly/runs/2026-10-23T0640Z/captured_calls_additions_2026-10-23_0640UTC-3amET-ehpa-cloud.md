# captured_calls additions - 2026-10-23T0640Z backend billing run (3 AM ET 10/23 (fired 06:39Z), ehpa cloud, v7 prompt + v12 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(columns_scan before/after, insp_bypass_advisories, unbilled_repair, payreasons --unbilled, excl_dup_complete / excl_crossover_complete
on runs 1700294 + 1700319, era_list / era_post --all-unposted / era_clear, claim_status_sweep --skip-answered, sweep_register),
getclaimexclusioncharges (re-list of run 1700319 before the write), getdemographic, gettxhistory (visit_read), getchargedetaildataicd10
(resave.detail), hideexclusions run 1700319 (excl_hide_1023_0640.py), move_to_ins.py --no-rebill (the $0-balance move shape),
lookuppatient (admit_lookup_1023_0640.py).
Behaviour seen: (1) a Florida Blue Medigap SECONDARY whose Medicare payment was re-posted by the payreason repair (no Medicare ICN on the
payment) rejects CH FH PREF0283 'MISSING PAYER DOC CONTROL NUM' even as a frequency-1 original (resubmissioncode 1, origrefnum blank) -
the edit is about the PRIMARY payer's claim control number in the COB loop, not the claim frequency; complete the exclusion and route the
coinsurance to William (Availity secondary / write-off). (2) A carrier added in Master Files without a payer address (UNI98 car307804)
rejects 'CH EC MISSING PAYER CITY' + 'CH G2 L2010BB.N4..2.0.1:missing state code' on the first claim run - the address is a Master Files
field (no API), William's turn.
