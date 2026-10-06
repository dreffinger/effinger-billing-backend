# captured_calls additions - 2026-10-06 1310 UTC (9 AM ET) backend billing run, ehpa cloud

## 2026-10-06T1310Z - no new call shapes
- Columns 0/1/0/1 unchanged (two standing holds), ERA 1052906 held; no AMD column write.
- UNI20/BCBS pre-5/1 pass 3: `claim_status_sweep.py --skip-answered` fed with a converted list ({visitid, action}) built from the two sweep registers; the helper now reads the register shape ({rows:[{vid, action}]}) directly. 4 D0 'not on file' visits sent once with `freq1_visit.py reroute <vid> <cid> <order> [<seq>]` (dry, then live; 204 x4) after claiming them in practices/ehpa/registers/tf_writeoff_watch.json and pushing main.
- Stedi: `stedi.mbi(first, last, dob, state, dos)` at the 2025 DOS answered the MA entity for both candidate charts (pat20336: Care Improvement Plus South Central = UHC MA PPO 4/1/2024-4/30/2026, date of death [DOB]; pat17474258: UnitedHealthcare of Florida HMO Medicare Risk since 1/1/2025). `stedi.elig("87726", ...)` at DOS 10/8/2025 for pat17474258 answered Inactive and echoed a different member id than the chart (board row for William; the CMS 271 decides the payer). JSON saved under patient_db/<pid>/ by hand (stedi.mbi does not save it).
- A 277 statusCategoryCode A4 ('claim/encounter cannot be found') is not in the v12 candidate set (D0 / A3 / A6 / A7 / A8) - listed, re-asked next run.
