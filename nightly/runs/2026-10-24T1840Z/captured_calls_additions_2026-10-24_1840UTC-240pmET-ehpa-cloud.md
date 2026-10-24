# captured_calls additions - 2026-10-24T1840Z backend billing run (2:40 PM ET 10/24 (fired 18:40Z), ehpa cloud, v7 prompt + v12/v13 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy: columns_scan before/after, insp_bypass_advisories,
unbilled_repair, payreasons --unbilled, excl_dup_complete / excl_crossover_complete on runs 1700294 + 1700319, era_list / era_post
--all-unposted / era_clear, claim_status_sweep --skip-answered, sweep_register), lookuppatient (admit_lookup_1024_1840.py, read-only).
No AdvancedMD write this run.
Behaviour seen: nothing new - the two exclusion rows are the standing carrier-record holds (AET12 PREF0288 + PREF0264 on run 1700294,
chart 24750 v19455937; UNI98 'CH EC MISSING PAYER CITY' + 'L2010BB.N4 missing state code' on run 1700319, chart 17475632 v19433791);
the ERA Center was empty before and after; the UNI20/BCBS pre-5/1 277 pass answered PENDING on all 16 chart-17472874 visits again (pass 165).
Container lesson: the fresh container had no `requests` module (every helper exited 1 in 0 s, engine 'nothing ran', no AMD call made) -
`python3 -m pip install requests` and re-run; pypdf imports fail in this image (cryptography _cffi_backend), pdftotext path unaffected.
