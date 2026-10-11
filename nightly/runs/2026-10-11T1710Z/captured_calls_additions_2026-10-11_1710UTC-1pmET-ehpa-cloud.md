# captured_calls additions - 2026-10-11 1710 UTC (1 PM ET) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW env), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before), GET /api/era/checks (2 unposted), GET /api/era/checkdetails?checkid= (1053096, 1053116 via era_post --dry), payreasons.py --list (11 rows no-era-line), Stedi 276/277 claim status x19 (claim_status_sweep.py pass 59).

Behaviors noted:
- claim_status_sweep.py --skip-answered takes a comma-separated list of the earlier sweep registers (registers/uni20_bcbs_pre0501_sweep_*.json); given with no argument it stops with IndexError before any 277 is sent.
- tools/mirror/apply_bundle.py (the GITHUB INBOX step) was refused by the auto-mode classifier this slot ("Blocked by fast classifier") - the 2026-10-11 chat package stays on Drive 'github mirror'.
