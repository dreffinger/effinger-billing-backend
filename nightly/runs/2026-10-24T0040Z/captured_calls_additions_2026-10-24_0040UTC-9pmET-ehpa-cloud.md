# captured_calls additions - 2026-10-24T0040Z backend billing run (9 PM ET 10/23 slot, fired 00:40Z 10/24, ehpa cloud, v7 prompt + v12/v13 rules)
Calls learned: NONE - no new AMD or Stedi call shape this run (0 vocabulary entries). Calls used, all in the registry: the engine pass
(tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy, 00:52-00:56Z, plainly in the foreground):
columns_scan before/after (getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimrunstatus,
getclaimexclusioncharges), insp_bypass_advisories (0 to bypass), unbilled_repair --live (0 rows), payreasons --unbilled --live (0 rows),
excl_dup_complete / excl_crossover_complete on runs 1700294 + 1700319 (0 completed), era_list before/after (GET /api/era/checks, 0 checks),
era_post --all-unposted (0 lines), era_clear (0), claim_status_sweep --min-age 176 --max 60 --carriers UNI20,BCBS --skip-answered (Stedi 276/277,
16 asked) + sweep_register; lookuppatient (admit_lookup_1024_0040.py, read-only, three name patterns). ONE login inside the engine pass; no 429,
no lock, no classifier refusal. No AdvancedMD write by this container.
Behaviour seen: nothing new - the two exclusion rows are the standing carrier-record holds (AET12 PREF0288 v19455937 on run 1700294;
UNI98 'CH EC MISSING PAYER CITY' v19433791 on run 1700319); the ERA Center was empty before and after; the UNI20/BCBS pre-5/1 277 pass
(pass 162) answered PENDING on all 16 chart-17472874 visits again; the two chartless Pam admits (BRO* 10/19 Brynwood, HIC* 10/22) still have no AMD chart.
