---
name: billing-insurances-cleaning-task
description: "Insurances cleaning task (on demand): split the patient-balance A/R into QMB write-off / untimely write-off / cascade / cost-sharing (not a write-off) using ALLOWED>0 as the adjudication test; gated write-off posting; CCM-never-to-Medicaid rule; the 5/31 WOINSBANK lesson."
---

## What it is (William 9/11/2026)
An on-demand scheduled task in the EHPA billing & credentialing project. Prompt: `nightly/insurances_cleaning_task_prompt_v1.txt`; script: `billing/writeoff/insurance_cleaning.py` (workspace copy `/home/claude/unbilled/insurance_cleaning.py`). MODE A classify (always, read-only) -> `Patient_AR_split_<date>.xlsx`; MODE B post write-offs only when William's start message says APPROVED with the codes; MODE C Stedi supplement discovery only when he says SUPPLEMENTS with a budget.

## The test that prevents another WOINSBANK (5/31/2026, 5,166 write-offs reversed)
A charge is ADJUDICATED only when the correct payer set an `allowedamount` > 0 (an ERA posted). "Has a balance", "has a last-payment date" ($0 denial lines set it too) or "looks unpaid" prove nothing — UNI20/BCBS balances were paid-but-unposted when they were bulk written off. Source list: `POST /api/masswriteoff/masswriteoffsearch` with `isinsbalance:false` = every charge carrying a PATIENT balance (patientid, chargedetailid, carriercode, allowedamount, patpayment, lastpaymentdate, dateofservice).

## Buckets (9/11/2026 run: $234,758 / 4,201 charges / 671 patients)
1. QMB / dual — patient has a Medicaid-type plan (MCAD, SUN01, WEL04/07, SIM01, STA03, FLO99) anywhere on file: cannot be balance-billed -> write off with the QMB/patient code (not WOINS, so it is not classified contractual). Pre-check: the Medicaid plan was billed as the crossover; if never billed, bill Medicaid secondary first. ($20,676 adjudicated + $1,369 never-adjudicated)
2. Untimely — never adjudicated, DOS > 12 months, primary claim -> WOINS untimely with a dated note (William's 9/7 rule). ($11,303) 2b: UNI20/BCBS never-adjudicated -> HOLD, check ERA Center / claim status for an unposted remit first, never blind write-off.
3. Timely never-adjudicated -> rebill / insurance cascade. Only $1,652 left — the correct-primary Stedi cascade on PATIENT balances is finished (William 9/11: stop it).
B. $0-denial transfer (touched, allowed=0) -> the PR-transfer bug: `move_to_ins.move(cid)` and find the real payer. Was EMPTY 9/11 (the two-week cleanup cleared it).
4. Adjudicated cost-sharing on non-Medicaid patients — NOT a write-off ($199.6K): 4-Medicare = Medicare 20% coinsurance ($55.8K / 169 pts) -> bill the supplement if on file, else Stedi discovery (~$1.50/pt, MODE C), else patient statement; 4-MA/commercial = MA copays/coins (UNI20 $58.8K, CAP07 $42.9K, HUM01 $19.3K, BCBS $13.3K) -> patient statements + small-balance policy (median patient balance $159; 177 pts < $100 = $8.8K; 37 pts >= $1,000 = $83K). Dual flag only sees Medicaid plans ENTERED in AMD — always run `--verify-dual`; a custodial-LTC patient whose Medicaid was never added looks non-dual.

## Write-off codes (practice master list, William 9/11/2026) — never substitute WOINS
WOCAID2ND = dual, Medicaid secondary after Medicare/MA paid · WOMCAD = residual on a Medicaid-primary charge · WOLATE = never adjudicated, DOS >12 months (late filing) · WONCS = CCM (or any service) Florida Medicaid does not cover, billed Medicaid-primary · WOSMBAL = small balance (needs William's threshold). Also on the list for later collections decisions: WOCOLL, WOENDCOLLA, WOBAD, WOCOUR, WOAPPEAL. WOPD90+PB / WOPD90+AR ("PD transfer" patient/insurance balance) — meaning to confirm with William before use.

## Adjudication test (corrected 9/11/2026)
A payer ACTED on a charge when the open balance (ins + pat) is below the charge amount, or a remit stamped lastpaymentdate. `allowedamount` alone is NOT proof: a freq-1 rebill leaves allowed == fee with nothing paid. This moved $92K on the patient side out of "adjudicated cost-sharing": $45.4K of UNI20/BCBS full-charge patient balances are the unposted-ERA pattern (HOLD, check ERA Center / claim status), $24.3K is timely never-adjudicated (still cascade), $35.3K untimely (WOLATE).

## MODE D — the Medicaid INSURANCE side (masswriteoffsearch isinsbalance:true by Medicaid carrier ids)
9/11/2026: $97.5K held by Medicaid-type carriers (SUN01 $ largest, FLO99, WEL04, SIM01, MCAD only $7.6K): D1 paid stub $41.1K (WOMCAD/WOCAID2ND), D2 CCM never payable $16.8K (WONCS), D3 timely unpaid E/M $39.6K -> rebill on Medicaid's own sequence (the SMMC tail never scanned), D3b untimely -> WOLATE. The earlier $129K "open Medicaid list" was massrebillsearch (visits by LAST-BILLED carrier, settling included) — a different question; masswriteoffsearch is the write-off source because it reflects who currently holds the balance.

## Write-off posting path
move_to_ins.move(cid) (patient -> insurance side) then manual_post.post(cid, carrier, 0, balance, <code>, note=dated) — both captured calls. A native PATIENT-side adjustment call is NOT captured; if William wants that classification, ask for the DevTools paste. Every pass writes Writeoff_register_<date>.xlsx for the Money Ledger.

## Standing rules learned 9/10–9/11/2026
- CCM (99487/99489) is NEVER rebilled to Florida Medicaid: 322 CCM payments in the history are all Medicare (+3 Humana), ZERO from Medicaid. Medicaid-secondary CCM coinsurance -> contractual WOINS; Medicaid-primary CCM -> non-covered write-off. CCM is ~23% of the open-Medicaid residual. Consider not charging CCM on non-dual Medicaid patients at all.
- Rebilling "to Medicaid" must target Medicaid's OWN plan sequence (car6113) from getdemographic — never `insorder.split(",")[0]`, which is often Medicare/UHC.
- ~95% of the open-Medicaid list is already paid; the open balance is an un-written-off contractual stub (median ~$17/charge; insbal == fee - paid - writeoff) -> WOINS to zero, not a rebill.
- A provider-profile change (updvisitwithnewcharges profile=prof13) VOIDS the old charges and recreates them on a NEW visit id; AMD posts NEGATIVE write-off reversals (void-flagged) that net the old write-offs to zero — correct bookkeeping, never "corrected" with offsetting positive adjustments.

## Deceased-patient guard (9/22/2026)
DECEASED GUARD (William 9/22/2026 - hard rule, every task): never submit, rebill or release a claim whose date of service is AFTER the patient's date of death. core/deceased_guard.py enforces it: amd.rebill_charge() refuses (409, nothing sent) and fails closed; before approving/releasing any Charge Review visit (incl. when adding modifier 25) or sending any new claim to straight Medicare (FLO02) or any CCM claim, call deceased_guard.check(pid, dos, carrier, proc) - it reads the date-of-death cache (practices/ehpa/registers/deceased_cache.json), AMD's 'deceased' field, and when needed runs a Stedi Medicare lookup (MBILUNOSSN) whose 271 carries the date of death. Blocked = do not approve/submit; list it in the daily report for William to void (or, for CCM in the month of death, correct the DOS to on/before the death date if the CCM time was met before death). A lookup that FAILS does not block, but is reported as 'date of death unverified'.
