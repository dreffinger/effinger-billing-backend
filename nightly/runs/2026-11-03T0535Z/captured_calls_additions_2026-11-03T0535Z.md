# captured_calls additions - nightly cascade 2026-11-03T0535Z (Tuesday)

No new AdvancedMD or Stedi call shapes this run. Calls used (all already in the registry / docs/api_vocabulary.json): AMD login (one, precheck.py 05:48Z; .session.json reused by every later helper), massrebillsearch (precheck unpaid list + build_money), getdemographic (precheck DOB/member reads), Stedi payer eligibility v3 (two: UHC 87726, Centene 68069), Stedi payers/search probe (free), GET /api/era/checks (empty), void_rules charge lookup (gettxhistory). Vocabulary entries added: 0.

Observation for the registry (precheck cache): precheck_cache.json is keyed patient|payer|yyyymm, so a chart fix that changes what the 270 sends (DOB, member id) leaves the old rejection cached for the rest of that month - pat17478213's Centene AAA 71 (DOB mismatch) was still reported on 11/3 a day after the facesheet DOB went on the chart. Fix used tonight: delete that patient's keys for the affected month(s) (`jq 'del(."<pid>|<carrier>|<yyyymm>")'`) and re-run precheck; the fresh 271 answered ACTIVE. Any run that edits a chart DOB or subscriber number should evict those keys in the same pass.

Egress to npiregistry.cms.hhs.gov / data.cms.gov / oig.hhs.gov is still blocked from the nightly container (cred_check: 'Max retries exceeded' on all three; the 10/26 NPPES snapshot stands).
