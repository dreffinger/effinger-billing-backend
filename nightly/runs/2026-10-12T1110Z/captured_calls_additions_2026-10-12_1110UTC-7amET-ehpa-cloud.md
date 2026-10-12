# captured_calls additions - 2026-10-12 1110 UTC (7 AM ET 10/12) backend billing run, ehpa cloud

No new call shape this run. Calls used (all already in the registry): login (one attempt, AMD_PSW environment credential, no credential file), getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (columns_scan.py before/after), gettxhistory (payreasons.py --list, unbilled_repair.py dry), getdemographic (pat17478013 read - zero insplans), GET /api/era/checks + GET /api/era/checkdetails (era_list.py before/after), posterapayments dry plan (era_post.py --all-unposted --dry: 0 postable), era_clear.py --dry (HOLD), POST /api/claim/massrebillsearch + Stedi 276/277 x19 (claim_status_sweep.py pass 68), Stedi MBILUNOSSN eligibility x1 (ERR 72) and insurance-discovery x1 (HTTP 502).

Behaviors noted:
- stedi.mbi / stedi.disc take COMPACT dates (dateOfBirth "[DOB]", dateOfService "20261005") exactly as precheck.py passes them; ISO "1949-09-02" draws HTTP 400 Bad Request from /change/medicalnetwork/eligibility/v3.
- Stedi insurance-discovery /insurance-discovery/check/v1 answered 502 Bad Gateway at 11:38Z (payer-side outage) - retry next run, not an answer.
- No AMD write this slot; the Drive package PACKAGE_effinger-billing-backend_2026-10-12_weekly-metrics decodes to the manifest's byte counts (15,275 chars / 11,306 bytes) but neither sha256 matches, so apply_bundle.py was not run (left on Drive); the two helpers it carries were taken byte-exact from 'workspace mirror' instead.
