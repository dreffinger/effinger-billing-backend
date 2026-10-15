# captured_calls additions - 2026-10-12 0310 UTC (11 PM ET 10/11) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), checkEligibility (elig_amd.py pat17478013: still zero plans), payreasons.py --list (gettxhistory on the 11 reason-code rows: no-era-line x11), GET /api/era/checks (1 unposted) + posterapayments validate pass (era_post.py --all-unposted --dry: 0 postable, 3 skipped), POST /api/claim/massrebillsearch + Stedi 276/277 x19 (claim_status_sweep.py pass 64).

Behaviors noted:
- payreasons.py --list (read-only mode) still writes registers/payreason_repair_<stamp>.json (empty repair register) - harmless, but the register name suggests a repair ran.
- Drive 'github mirror' package PACKAGE_effinger-billing-backend_2026-10-11 unchanged since 23:29Z 10/11 (manifest 23:04Z, part01 23:29Z): same sha256 mismatch the 0110Z run recorded; left for the chat to re-upload a manifest matching part01.
- No AMD write this run; nothing refused.
