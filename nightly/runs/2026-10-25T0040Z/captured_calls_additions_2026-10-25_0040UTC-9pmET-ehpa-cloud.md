# captured_calls additions - 2026-10-25T0040Z backend billing run (9 PM ET 10/24 slot, fired 00:40Z 10/25, ehpa cloud, v7 prompt + v12/v13 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy: columns_scan before/after, insp_bypass_advisories,
unbilled_repair, payreasons --unbilled, excl_dup_complete / excl_crossover_complete on runs 1700294 + 1700319, era_list / era_post
--all-unposted / era_clear, claim_status_sweep --skip-answered, sweep_register), era_co45_relink.py (void_tx.void_payment +
move_to_ins.move + payreasons.post_line ERA-linked re-post), payreasons.visit_state (live read), elig_amd.py (AMD free 271, read),
lookuppatient (admit_lookup_1024_1840.py, read-only).
Behaviour seen: Humana check 1053282 (2 claims, chart 17478012) posted by the Post button with CO45/CO253 on the payment but
payreasonwoamount 0 - the 9/23 Humana/Florida Blue defect again: the contractual (151.90 + 39.82) landed on the PATIENT balance of both
visits (v19457320, v19457271). era_co45_relink.py 1053282 --meta <list json> --live corrected both (void, move back, ERA-linked re-post +
WOINS); PR2 stays on the patient (no secondary on the chart). The relink's --meta needs the plain LIST (era_list.py writes {checks:[..]} -
the 10/24 FIX): registers/era_checks_before_<stamp>_list.json dumped first.
Columns 0/0/0/2 -> 0/0/0/2 (standing holds AET12 run 1700294 chart 24750; UNI98 run 1700319 chart 17475632). UNI20/BCBS pre-5/1 277
pass 166: 16 PENDING chart 17472874, 0 sent.
Container lesson (again): fresh container had no python requests - installed before the engine pass this time (no lost engine pass).
