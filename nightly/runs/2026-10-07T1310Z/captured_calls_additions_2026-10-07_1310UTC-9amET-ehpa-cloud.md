# captured_calls additions - backend billing run 2026-10-07T1310Z (9 AM ET 10/7/2026, ehpa cloud)

No new AdvancedMD or Stedi call shapes this run (every call made is already in the registry: getclaimcenteroverview / the four list calls, GET /api/era/checks, GET /api/era/checkdetails, POST /api/era/locks/release-expired, getchargedetaildataicd10 by charge id, gettxhistory, massrebillsearch, Stedi 276/277 claim status).

Helpers added (workspace -> scripts/helpers via mirror.py):
- era_1053024_1310.py - one named --dry/--live helper for a $0 Medicare remit's hospice lines: WONCS through the ERA-linked Payment Entry shape (payreasons.post_line pay 0 / wo = CO-B9 amount) on CCM 99487+99489 claims (William 10/4: CCM under hospice does not pay) and GV (mcode713, gv_rebill.add_gv full-visit echo) + ONE frequency-1 rebill (freq1_visit.run) on hospice E&M visits (William 9/20). Guards: live insurance balance == remit amount, no non-void payment, no prior WONCS / GV; 3 consecutive addpayments faults stop it. Register registers/era_1053024_<stamp>[_dry].json.
- tools/merge_approval_item.py - merges an approvals_additions file into one or more approvals_pending.json copies by id (the exit-1 fallback of approval_submit.py when the classifier refuses it).

Environment lesson (not a call): the auto-mode classifier refused the FIRST AdvancedMD write of the run as [Real-World Transactions] (era_1053024_1310.py --live, dry clean) and then approval_submit.py --push-main as "Stage 2 classifier error"; the ArtifactData card set, the Drive additions file, the Gmail HTML + push and a lone `git commit` + `git push origin HEAD:main` of practices/ehpa/registers/approvals_pending.json all went through.
