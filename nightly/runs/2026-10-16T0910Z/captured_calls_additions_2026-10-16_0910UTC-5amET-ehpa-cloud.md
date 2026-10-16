# captured_calls additions - 2026-10-16 0910 UTC (5 AM ET 10/16) backend billing run, ehpa cloud (repo attached)

No new AdvancedMD or Stedi call shapes this run (0 vocabulary entries).

## Run notes
- Columns (list calls) 0/0/6/1 -> 0/0/6/1 (overview still shows exclusions 2 / $625 - the list call returns 1); ERA Center 0 unposted checks before and after.
- Charge Review 0. Claim Inspector 0. Unbilled 6 = 'Insurance order is missing' on the three zero-plan HCA charts pat17478059 / pat17478063 / pat17478064 (getdemographic re-read 09:3xZ - still 0 plans; board rows on William's turn since 10/16 02:49Z for the CHP member ids / the HCA facesheet). Exclusions 1 = AET12 pat24750 PREF0288 carrier CPID hold. No new claim run since 1700305.
- UNI20/BCBS pre-5/1 sweep pass 113 (--min-age 168 --max 60 --carriers UNI20,BCBS --skip-answered 101 registers comma-joined, 585 skipped): 17 asked - 16 PENDING (pat17472874 $2,563; the 3/4/2026 visit 'adjudicated, awaiting payment cycle'), 1 UNKNOWN (pat17475632 v19433791 $310); 0 candidates, 0 sent.
- Pam Gmail: the three 10/15 admit emails (Tapestry x1, Brynwood x2) still have no AMD chart (lookuppatient 09:3xZ, read-only, admit_lookup_1016_0910.py) - listed, not turned into charts.
- Drive: nothing new in the 835 / Availity / treasury / facesheet / Claimocity folders since the 10/15 2310Z run's own report CSV. Boards: drops 0, Working Denials queue 0, 0 items rows changed since 05:00Z; Mandatory Approvals 0 approved / 0 waiting (register all 89 done). GitHub inbox: no new PACKAGE manifest (the 10-11 / 10-12 parts still fail their sha256 - left).
- State restore: Drive 'workspace mirror' lists no workspace_state bundle newer than 2026-09-18 (connector search by title and by manifest) - patient_db/ and era_details/ started empty; registers, needs list and laterality log came from main (468961e) and the Drive deceased_cache.json (07:40Z) was merged into both caches (72 dated entries).
- Permission classifier: no refusal this run (no AMD write attempted).
- Calls: no new call shape (login, columns scan, lookuppatient, getdemographic, GET /api/era/checks, 276/277 via Stedi). Helpers added: admit_lookup_1016_0910.py, zeroplan_1016_0910.py, sweep_eval_1016_0910.py (stamp copies).
