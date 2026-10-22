# captured_calls additions - 2026-10-22T1840Z (2:40 PM ET 10/22/2026, backend billing run, ehpa cloud)

No new call shapes this run. Calls used (all already in the registry): getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches,
getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges (columns_scan.py before/after inside the engine pass 18:47-18:51Z);
GET /api/era/checks (era_list.py before/after, 0 checks); posterapayments path (era_post.py --all-unposted, 0 lines); era_clear.py (0);
Stedi 276/277 (claim_status_sweep.py pass 157, 17 asked); getdemographic (plan_check_1022_1840.py charts 17478059 / 17478063 / 17478064 /
17470713 / 17478013); lookuppatient (admit_lookup_1022_1840.py, six name patterns incl. today's Pam admit). No AdvancedMD write by this container.
Vocabulary entries added: 0.
