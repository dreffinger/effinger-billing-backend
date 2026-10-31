# captured_calls additions - nightly cascade 2026-10-31T0535Z

No new AdvancedMD or Stedi call shapes this run. Calls used: AMD login (one), massrebillsearch (precheck unpaid list), eligibility 271 (elig_amd --all), getdemographic, gettxhistory, updvisitwithnewcharges full-echo resave + updextrainsinfo + chargerebill (freq1_visit reroute), ERA checks list (empty), Stedi 270 (MBILUNOSSN, CMS, Centene 68069, CHP 95112, Humana 61101, BCBSF) and payers/search. Vocabulary entries added: 0.

Lesson for the registry: cred_check.py prints 'NPPES: 3 records, 0 changed' when all three NPPES calls error (egress) - the per-NPI `error` field is the tell; the NPI Registry connector is the working NPPES path from this environment.
