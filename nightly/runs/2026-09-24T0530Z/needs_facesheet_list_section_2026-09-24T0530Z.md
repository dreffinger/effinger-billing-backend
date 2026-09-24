
## 1:30 AM ET 9/24 nightly insurance cascade (run 2026-09-24T0530Z, 06:07-06:35 UTC)
- STEP 1 precheck --days 3: 22 patient/payer pairs, 0 exceptions (3 'no plan on chart' flags were a false positive - precheck.py's CARRIERS line now accepts the rich carN->[code,name] carriers.json). Stedi: 6 MBI + 3 eligibility ~$6.90. Thursday - no claim-status sweep.
- STEP 2b void_rules: Hollis Ellery 9/5/2026 rule still open (no matching charge on the chart yet).
- STEP 3 ERA: Medicare check 819843767 (1052828, $11,504.56): $11,225.98 posted by the Center on 114 visits (one refused line made the whole-check reply a fault, but the money landed); TAPSTER 10/25/2025 99489 posted by hand $37.13 + WOINS $62.40; EDGERTON 8/23 CCM $172.83 posted after voiding the 9/10 WOINS $315 (wo_reversal_post). Residual $68.62 (TAPSTER 99487 already paid by 348567230) + $9.47 coinsurance stay on the check - left on the list, not dismissed. $0 check 349992844 (1052829) dismissed: 3 hospice CO-B9 CCM denials -> GV rule (AVERILL 22 visits $2,681, MACKLIN 6 visits $832, DASHWOOD 2 visits $513 re-sent to Medicare); 2 CO-151/CO-16-N382 CCM denials 8/22 (DETTMER open $315 -> William; TAPSTER already written off 9/10).
- Diagnosis rule (g): no primary-position denials tonight; dx_primary_fix.plan clean on every rebilled chart (no I10 fallback used).
- AVERILL: Medicare DOD [DOB] on record, last charge 7/6/2026 - no post-death write-off needed; AMD chart not marked deceased (note on her row).
- Write-offs: none. Reversed: EDGERTON WOINS $315 voided (paid instead).
- STEP 4b cred_check: NPPES 3 records unchanged; OIG LEIE download blocked (oig.hhs.gov unreachable from the container); 7 overdue reminder cards already on William's turn - no cred file.
- Waiting on William: DETTMER 8/22 CCM CO-151/CO-16 decision; the 7 overdue credentialing cards (Cigna secure emails, UHC attestation, Centene Relias, FCC contract check, TRICARE case, Availity sender number, Pam's Medicaid ATN 1127554).
