# captured_calls additions - 2026-10-11 2110 UTC (5 PM ET) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW env), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), GET /api/era/checks (2 unposted), GET /api/era/checkdetails?checkid= (1053096, 1053116 via era_post --dry), payreasons.py --list (11 rows no-era-line), POST /api/claim/massrebillsearch + Stedi 276/277 claim status x19 (claim_status_sweep.py pass 61).

Behaviors noted:
- AMD's providerapi answered slowly this slot: the first columns_scan.py pass and a massrebillsearch read both hit the helpers' 120 s read timeout (ReadTimeout) at 21:1xZ; the same reads completed on a second attempt a few minutes later. Nothing was retried against a login - the cached token stayed valid.
- claim_status_sweep.py and columns_scan.py do not parse --help: `--help` runs the default pass (the sweep with min-age 45 / max 100 / all ten carriers, the scan into scan_<date>/*_--help.xml). Read-only, but a sweep started that way spends Stedi 277 calls on claims outside the UNI20/BCBS pre-5/1 pool.
