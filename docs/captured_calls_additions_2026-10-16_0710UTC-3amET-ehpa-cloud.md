# captured_calls additions - 2026-10-16 0710 UTC (3 AM ET 10/16) backend billing run, ehpa cloud (repo attached)

No new AdvancedMD or Stedi call shapes this run (0 vocabulary entries).

## Run notes
- Columns (list calls) 0/0/6/17 -> 0/0/6/1; ERA Center 0 unposted checks before and after.
- Exclusions: 16 of 17 rows settled (excl_1016_0710.py): pat17478013 x8 VA CCN PNM10902 - the approved card A-2026-10-15T0510Z-H had been applied from the PHI-scrubbed repo copy of its helper, so the VA plan's member id was the literal placeholder; ICN from William's board paste written (ins_update subscribernum, wrapped updateinsurance; the field edit blanked insorder, restored to 1), 8 x freq1 seq 1 -> 204, hideexclusions 1700305; pat17475064 x6 AET07 'subscriber not found' on Medicare-paid 1-2/2026 visits (Aetna INACTIVE, deceased [DOB]) -> WOCLTREQ $104.91; pat46253 / pat20804 2023 Medigap coinsurance (Medicare remits 5/2023, 7/2023) -> WOINS $53.52 untimely, dated notes; AET12 pat24750 hold.
- Unbilled 6 = three zero-plan HCA charts (pat17478059 / pat17478063 / pat17478064) on William's turn for the HCA facesheet; re-read live, still 0 plans.
- UNI20/BCBS pre-5/1 pass 112: 17 asked, 16 PENDING + 1 UNKNOWN, 0 sent (--skip-answered built with ls | paste -sd, per the 0310Z trap).
- Pam Gmail: three 10/15 admit emails (Tapestry, Brynwood x2) still have no AMD chart (lookuppatient 07:2xZ, read-only).
- Drive: nothing new in the 835 / Availity / treasury / facesheet / Claimocity folders. Boards: drops 0, Working Denials queue 0; approvals 0 approved / 0 waiting.
- Permission classifier: no refusal this run.
- State bundle: full pack = 519 parts (registers 23 MB) - the PHI-only bundle was uploaded instead; registers ride the repo.
