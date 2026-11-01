# captured_calls additions - nightly cascade 2026-11-01T0535Z (Sunday)

No new AdvancedMD or Stedi call shapes this run. Calls used: AMD login (one, precheck.py; .session.json reused by every later helper), massrebillsearch (precheck unpaid list + build_money), gettxhistory (pay_scan over the rebuilt 587-patient universe), getdemographic (claim-status sweep plan reads), Stedi 270 (one UHC 87726 payer eligibility in precheck), Stedi 276/277 claim status (Sunday sweep), ERA checks list (empty), payers/search probe. Vocabulary entries added: 0.

Lessons for the registry:
- Fresh container: `pip` on this image belongs to Python 3.13 while `python3` is 3.11 - `pip install requests` reports success but `import requests` still fails; use `python3 -m pip install requests openpyxl` (tools/nightly_bootstrap.sh's `pip install -q openpyxl` has the same gap).
- pay_scan.py needs patient_universe_0907.json, lost with the September workspace: run `python3 build_money.py` first (writes unpaid_<date>.json), then `python3 build_universe_1025.py` (rebuilds the universe from the unpaid list, claim-status sweeps and era_details present), then `python3 pay_scan.py`. The rebuilt universe is the patients with an OPEN balance (587 tonight), so the ledger's "paid all time" per payer is smaller than the 9/7 scan of 1,102 patients - a known narrowing, not a payment drop.
- cred_check.py: NPPES / data.cms.gov / oig.hhs.gov egress still blocked ('Max retries exceeded'); NPPES verified through the NPI Registry connector instead (all three records unchanged).
