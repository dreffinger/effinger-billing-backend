# captured_calls additions - 2026-10-12 0510 UTC (1 AM ET 10/12) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), checkEligibility (elig_amd.py pat17478013: still zero plans), gettxhistory (payreasons.py --list: 11 reason-code rows, all no-era-line), hideunbillablevisits hide=-1 x22 (unbilled_repair.py --live, rule b), GET /api/era/checks + posterapayments validate pass (era_post.py --all-unposted --dry: 1 check, 0 postable, 3 skipped), POST /api/claim/massrebillsearch + Stedi 276/277 x19 (claim_status_sweep.py pass 65).

Behaviors noted:
- claim_status_sweep.py: `--skip-answered` with no file argument raises IndexError (list index out of range) - the flag needs the comma-joined list of earlier sweep registers; usage branch still missing (10/11 TRAP stands).
- unbilled_repair.py dry + live wrote registers/unbilled_repair_2026-10-12T0517Z.json (dry) and _0518Z.json (live); 22 prior-payor rows released, 11 reason-code rows held (code-less payment carries money), 5 'Insurance order is missing' rows left alone.
- No classifier refusal this run.
