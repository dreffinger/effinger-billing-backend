# Cloud Practice — Effinger Health PA (`ehpa`)

One project for running a medical practice's back office with Claude: the **daily back-end billing run**, the **insurance cascade** (who really covers the patient), **credentialing**, the **Claimocity** hospital charge feed, and the three live boards (Insurance Refresh, Credentialing, Money Ledger). It grew out of cleaning up Effinger Health PA / North Florida Senior Care (Tallahassee, FL) on AdvancedMD, and is laid out so the same scripts can clean up another practice by adding a `practices/<code>/` folder.

Every script starts with a PLAIN ENGLISH header — what it decides, which of William's rules it uses, what it never touches — and this README is generated from those headers. **No credentials and no patient data are in this repository**: tokens come from the login cache, the Stedi key from `secrets/`, logs / results / `patient_db/` stay in the workspace, and the 12 scripts whose data tables hold member numbers are mirrored as header-only stubs (marked *local only* below).

## Layout

| Folder | What lives there |
|---|---|
| `core/` | Shared library: the AMD client (one login, XML + REST), Stedi client, transaction history, the full-echo resave that protects charges, plan add/update, address PATCH, balance moves, frequency-1 rebill, manual posting, voids, 835 and facesheet parsers, AMD eligibility. |
| `billing/claims_center/` | The daily Claims Center columns - Charge Review, Claim Inspector, Unbilled, Exclusions - and the fixes each one needs (admission dates, modifiers, dx edits, releases, completions). |
| `billing/era/` | ERA Center: posting checks the way the Post button does, $0 process-accepted lines, dismiss / restore, the write-off reversal pipeline, manual posts for unvalidated lines. |
| `billing/rebill/` | Re-pointing claims at the right payer and re-sending them as original claims: payer switches, GV hospice, I63 stroke recodes, CO24 restores, and the dated one-off passes (each header says what it decided that night). |
| `billing/writeoff/` | Write-off passes: not-on-file remnants, cascade untimely, and the over-365-day rule (primary claims past a year with any carrier). |
| `billing/scans/` | Read-only scans: payments by carrier, CO24, voids, blank begin dates, full claim-status sweep (Stedi 276/277), AWV due list. |
| `eligibility/` | The insurance cascade: patient database -> AMD eligibility (free 271) -> Stedi eligibility / discovery -> facesheet -> William. Denial cascades ask the payers what coverage really was and sort every denied claim into an action. |
| `credentialing/` | Nightly credentialing check (NPPES, Medicare revalidation, OIG) feeding the Credentialing Board; the board template lives in boards/templates. |
| `claimocity/` | Claimocity hospital charge feed (HL7 drop on Drive, Cloud Run pull every 30 min) compared against AMD insurance. |
| `boards/` | Builders for the Money Ledger, Programming Lab and the board facility lines, plus the HTML templates of the three boards. |
| `nightly/` | The scheduled nightly run: the prompt the task starts from and, in English, what a run does. |
| `practices/ehpa/` | Effinger Health PA: NPIs, office key, carrier and facility ids, Drive folder ids, board ids, and `rules.md` — William's standing billing rules. Add `practices/<code>/` for the next practice. |
| `docs/` | `captured_calls.md` (the call registry), `postman_effinger_amd.json` (Postman mirror), `memory.md` (where everything is remembered). |

Run anything with `source env.sh` from the repo root (it puts every folder on PYTHONPATH; the scripts import each other flat, exactly as they run in the workspace).

## Scripts

### `core/`

Shared library: the AMD client (one login, XML + REST), Stedi client, transaction history, the full-echo resave that protects charges, plan add/update, address PATCH, balance moves, frequency-1 rebill, manual posting, voids, 835 and facesheet parsers, AMD eligibility.

| Script | What it is | What it decides |
|---|---|---|
| `add_ins.py` | Add an insurance plan | Nothing on its own. Adds one plan (carrier + member number + begin date) to a chart and returns its sequence number. |
| `amd.py` | AdvancedMD client | Nothing about billing. It logs in to AMD once, keeps the token in .session.json, and sends every XML message the other scripts build. |
| `build_repo.py` | Build the GitHub mirror of the Cloud Practice project from the workspace, William 9/7-9/8/2026 | Nothing about billing. Rebuilds /home/claude/effinger-billing-backend from /home/claude/unbilled: every script goes into the folder for the part of the practice it serves (core / billing / eligibility / credentialing / c… |
| `elig_amd.py` | AMD's own eligibility check - the free one, William's capture re-pasted 9/7/2026 | Nothing. Runs AMD's real-time eligibility (EligibilityDetailsLegacy/checkEligibility) on one insurance plan and turns the 271 into a short answer: active or not on the chart plan, plan dates, Medicare Part A/B dates, any… |
| `facesheet_auth.py` | Facesheet authorization OCR | Which number on a hospital facesheet is the authorization, using OCR on the PDF. |
| `freq1_visit.py` | Frequency-1 reset + rebill | Nothing. Resets one visit to an original claim (frequency 1, no payer reference number), strips 1900 dates, rebills one plan sequence. |
| `freq7_visit.py` | Corrected-claim resend with the payer's original claim number | Nothing on its own. Re-sends one visit to one insurance sequence as a CORRECTED claim (frequency 7) carrying the payer's original claim number (ICN), which is what a payer needs to link the resend to the claim it already… |
| `ins_update.py` | Update one plan | Nothing on its own. Changes fields on an existing plan - end date, begin date, member number, even the carrier - with AMD's original-value echo. |
| `manual_post.py` | Manual payment / write-off on one charge | Nothing on its own: posts a payment and/or write-off to one charge with a note. |
| `mark_done.py` | Mark audit row done | Marks a patient done/checked in the audit workbook. |
| `move_to_ins.py` | Move balance to insurance + rebill | Moves a visit's patient-responsibility balance back to insurance, sets the plan order on the visit, and rebills it. |
| `parse835.py` | Parse 835 files | Nothing. Turns raw X12 835 remit files into a readable inventory (check, payer, amount, claims). |
| `patient_patch.py` | Demographics PATCH (REST) | Nothing. Writes patient demographic fields (DOB, address) through AMD's newer JSON API, echoing the original record for the concurrency check. |
| `pcc_parse.py` | Parse PCC facesheets | Nothing. Extracts name, DOB, facility, MBI, Medicaid number and payer block from a PointClickCare Admission Record PDF. |
| `precheck.py` | Nightly pre-claim eligibility check | For every recent unpaid visit, whether the plan it is billed to was really active on that date of service (Stedi), and proposes the right payer when it was not. |
| `recode.py` | Swap a diagnosis or procedure | Nothing on its own: replaces one diagnosis or procedure code on every live charge of a visit, resets frequency, rebills. |
| `resave.py` | Full-visit resave | How to save a visit back to AMD safely: fetch the whole visit, echo every charge, then reinspect and approve. |
| `restore_charge.py` | Restore a voided charge | Re-adds a charge that a single-charge resave voided by mistake, with identical attributes and balances. |
| `scripts_manifest.py` *(local only)* |  | Plain-English manifest for every script in /home/claude/unbilled.  Used by build_learning_app.py to (1) stamp a PLAIN ENGLISH header on each .py and (2) build the Effinger Programming Lab artifact. st |
| `stedi.py` | Stedi client | Nothing. Asks Stedi questions: payer eligibility, MBI lookup, insurance discovery, payer search, enrollment status. |
| `txh.py` | Transaction history dump | Nothing. Reads a patient's charges, payments, write-offs and balances (gettxhistory) so other scripts can decide. |
| `void_rules.py` | Void-on-arrival rules | Whether any charge that has landed in AMD matches a rule William gave in advance ("that 9/5 visit is an error - void it when it comes through"), and voids it. |
| `void_tx.py` | Void a payment or write-off | Nothing by itself. Voids one payment or write-off on one charge, the way Payment Entry's Void button does. |

### `billing/claims_center/`

The daily Claims Center columns - Charge Review, Claim Inspector, Unbilled, Exclusions - and the fixes each one needs (admission dates, modifiers, dx edits, releases, completions).

| Script | What it is | What it decides |
|---|---|---|
| `apply_inspector_fix.py` | Claim Inspector hospitalization fix | Clears inspector errors about hospitalization dates by setting the admission date and flipping the Box 18 flag. |
| `clean_1900.py` | Clear 01/01/1900 dates | Finds claim fields set to 01/01/1900 on visits touched today and clears them. |
| `complete_admit_exclusions.py` | Complete fixed admission exclusions | Marks 'missing admission date' exclusions completed once fix_admit_dates has repaired the visit. |
| `excl_act_0907.py` *(local only)* | 9/7 Exclusions column pass - 197 rejected claims on 10 claim runs | (1) Rejections over 12 months old with an open balance are written off as untimely (William 9/7: "write those off if no chance of being paid") - UHC "member not valid at DOS" remnants after Medicare paid, Oswin Patient216's A… |
| `fix_admit_dates.py` | Restore hospital admission dates | For hospital (POS 21) visits whose admission date was lost in the frequency reset, puts it back and rebills. |
| `fix_freq7_exclusions.py` | Clear frequency-7 exclusions | Which excluded claims are failing only because of the corrected-claim flag, fixes the flag, rebills, completes the exclusion. |
| `fix_tricare_exclusions.py` | TRICARE referral numbers | Puts the TRICARE referral/auth from the facesheet on each excluded visit, resaves, rebills, completes the exclusion. |
| `inspector_0906.py` | 9/6 Claim Inspector pass | Clears tonight's 37 inspector holds by rule: hospital admission date = most recent 99223 on/before the visit; Garrity F02.818 -> F03.90; Alderton 99497 gets modifier 25 next to 99223; Eastman second new-patient 99344 -> 99349… |
| `inspector_0907.py` | 9/7 Claim Inspector pass | Clears the 50 inspector holds by William's standing rules: hospital admission date = the most recent 99223 within 45 days on/before the visit (written to Extra Info, claim forced to CMS-1500); CCM pairs get modifier 25 o… |
| `resolve_admits.py` | Work out admission dates | Nothing - builds the mapping of subsequent-care visits to their admitting 99223 date. |
| `scan_alf_codes.py` | ALF visits using SNF codes | Nothing - lists unpaid 2025+ charges with 9930x codes at place of service 13 (ALF). |
| `unbilled_0906.py` *(local only)* | 9/6 Unbilled column pass | Which of tonight's 47 unbilled visits can be released: adds the plan Stedi found (Tolliver UHC, Marchetti + Hendricks Medicare, Purcell UMR), points visits with plans already on file at the right sequence (Rothwell, Whitfield, Jackso… |
| `unbilled_0907.py` | 9/7 Unbilled column pass - 160 visits | (1) 135 "payment from the prior payor is required" rows: these appeared because the 9/6 ERA clearing posted the old payer's $0 denials / re-posted 2023-24 payments, and AMD then tried to bill the NEXT plan. The 2023-2024… |
| `unbilled_0907_scan.py` |  | PLAIN ENGLISH (9/7 Unbilled scan) - reads only. For each unbilled visit: DOS, fee, balance, insorder, last claim sent (carrier/date), payments on the visit. Writes unbilled_0907_scan.json. |

### `billing/era/`

ERA Center: posting checks the way the Post button does, $0 process-accepted lines, dismiss / restore, the write-off reversal pipeline, manual posts for unvalidated lines.

| Script | What it is | What it decides |
|---|---|---|
| `era_alloc_post.py` | ERA payment-only post | For secondary/supplement remits whose 'allowed' doesn't match AMD, allocates the paid amount across the charges with no write-offs. |
| `era_clear.py` | Clear the ERA Center unposted list the way William does by hand | For every check still on the ERA Center list: (1) post any line that still carries real money onto a visit with an open balance (era_post.post_check - the Post button); (2) post the leftover $0-payment / $0-adjustment li… |
| `era_fix_0907.py` | Fix the 21 checks left in ERA Center, 9/7/2026 late | On 9/6 the manual-post pass took the $0 DENIAL line of several 2024 UHC checks instead of the PAYMENT line, so McKenna, Farraday, Norwood and Winslow Justine show a $0 payment and a full write-off where UHC actually paid ($1,850… |
| `era_manual_post.py` | Manual post of an ERA line | Posts an ERA line ERA Center refuses (procedure codes don't match), replicating your 9/3 Pinckney entry. |
| `era_post.py` | Post ERA payments | Which ERA checks and visits in ERA Center can be posted automatically, and posts them the way the Post button does. |
| `era_upload.py` | Upload 835 files to ERA Center | Which downloaded 835 files are not already in ERA Center, and uploads those. |
| `era_zero.py` | Clear the ERA Center list - post the $0 lines the way the 'Process Accepted' button does | For every check still on the ERA Center unposted list, posts the remaining validated lines that carry $0 payment AND $0 adjustment (denial / duplicate / info-only lines) - exactly what William's 'Process Accepted ($0.00)… |
| `wo_direct.py` | Direct write-offs | Writes off approved visits whose ERA lines are unmatched or gone. |
| `wo_post.py` | ERA-linked $0 + write-off | Posts approved write-offs on ERA lines (Medicaid non-covered CCM/AWV) with the CARC reason. |
| `wo_reversal_post.py` | Reverse write-offs and post the payer's money | For every visit in wo_reversal_<date>.json - a remit that PAID a visit whose charges were instead written off (the 5/31/2026 WOINSBANK bulk write-off and similar) - voids the write-offs so the balance returns to insuranc… |
| `wo_reversal_scan.py` | Remit vs write-off scan | Nothing - finds ERA Center remits with money for visits whose charges were written off (no payment ever posted), so the write-off can be reversed and the payer's money posted instead. |

### `billing/rebill/`

Re-pointing claims at the right payer and re-sending them as original claims: payer switches, GV hospice, I63 stroke recodes, CO24 restores, and the dated one-off passes (each header says what it decided that night).

| Script | What it is | What it decides |
|---|---|---|
| `add_modifier_rebill.py` | Add a modifier and rebill | Adds one modifier (e.g. GV) to every charge on a visit and rebills. |
| `aet12_rebill_0907.py` | Aetna Senior Supplemental (AET12) secondaries - rebill after William fixed the carrier payer id to 62118, 9/7/2026 | (1) Voids today's four "untimely" write-offs on Oswin Patient216 - wrong call: a Medigap secondary's clock runs from Medicare's remit (posted 9/6/2026), not the date of service. (2) Every charge with an open AET12 insurance b… |
| `audit_pr_transfer.py` | Patient-balance audit | Nothing - finds charges pushed to patient balance by denials that really mean 'wrong payer'. |
| `batch_refresh.py` *(local only)* | 9/4 PCC facesheet refresh | For each patient on the 9/4 list: add Medicare if missing, add the Medicaid/MMA plan if missing, end the denying plan, move balances to insurance and rebill. |
| `build_pr_audit_wb.py` *(local only)* | Audit workbook | Builds the PR-transfer audit Excel: patients, facilities, live balances, refresh status. |
| `bramwell_rebill.py` | Bramwell hospice-period rebill | Bramwell's 5/31-8/4/26 visits to FCC with GV. |
| `co24_restore.py` | Undo a CO24 posting and rebill the MA plan | For Medicare $0 CO24 postings: void the $0 payment and its write-off, then bill the visit to the Advantage plan. |
| `elig_fix.py` | Hospital eligibility refresh | From a pasted TMH 'Active Insurance' block: make Medicare primary with the MBI, the listed plan secondary, end the old denying plan, re-point and rebill the audit visits. |
| `fairbank_gv.py` | Fairbank GV pass | Fairbank's hospice rebill done separately after the date filter was added. |
| `fcc_rebill_0907.py` | Florida Community Care re-point + rebill, William 9/7/2026: "yes FCC is FLO99 - rebill them all there and anything else that is Florida Community Care going back a year" | (1) Every open visit inside 12 months already on FLO99 (car42008, Florida Community Care) is re-sent as an original claim. (2) Every patient on the unpaid list with a Medicaid-side balance inside 12 months (MCAD, SUN01, … |
| `gv_rebill.py` | Hospice GV rebill | For a patient's visits Medicare denied as hospice (COB9): undo the $0 posting, add GV, re-send to Medicare. |
| `i63_apply.py` | Apply I63.9 to I69.30 | For every outpatient charge carrying acute stroke I63.9, swaps to sequela I69.30 and rebills the denied ones. |
| `i63_scan2.py` | I63.9 scanner (resumable) | Nothing - finds outpatient I63.9 charges and checkpoints. |
| `i63_scan_par.py` | I63.9 scanner (parallel) | Nothing - same scan, five workers. |
| `i63_sweep.py` | I63.9 sweep (scan + apply) | Same rule as i63_apply, run as one off-peak sweep over open claims. |
| `move_audit_to_ins.py` | 9/3 balances back to insurance | Every audit charge sitting on a patient balance after a wrong-payer denial goes back to insurance; flags it for rebill once the new plan is on file. |
| `pr27_b.py` *(local only)* | Calloway MBI typo + Haverthwaite to Humana | Fixes Calloway' MBI (4F76 to <id>, per CMS) and re-sends Haverthwaite's UHC denials to her Humana MA plan. |
| `pr27_medicare.py` | UHC 'coverage terminated' group to Medicare | For the patients UHC dropped (PR27), end UHC on the chart and re-send every open UHC-billed visit Medicare-first with the chart's Medicaid/LTC plan second. |
| `rebill_driver.py` | Fix order, rebill, complete | For rejected claims: set the correct insurance order, rebill, then mark the rejection completed - verifying each step. |
| `rebill_patient_year.py` | Rebill a patient's last 12 months | Which of a patient's visits in the last N days are unpaid with a balance, and re-sends each under a given plan order. |
| `rebill_to_seq.py` | Bill a visit to another plan | Nothing on its own: re-points one visit at plan sequence N (optionally with a pre-auth) and rebills. |
| `rebill_under_effinger.py` | Rebill Garland-G denials under Dr. Effinger | Which Garland-G-rendered denials (N290/N767) to re-send with you as rendering provider, and does it without voiding the originals. |
| `refresh3.py` *(local only)* | 9/5 refresh batch 3 | The chart fixes and rebills for a specific set of names from the 9/5 TMH pastes (per-patient lines you approved in chat). |
| `refresh4.py` *(local only)* | 9/5 refresh batch 4 | Sedgwick, Ivens, Jessop Patient850, Kendal, Ambleside, Wexford chart fixes and rebills from the 9/5 facesheets. |
| `resend_notonfile.py` | Resend claims the payer never received | Which visits from the full status sweep the payer says are NOT ON FILE and are still inside the 12-month window, and re-sends each one as an ORIGINAL claim (frequency 1) to the plan it is already assigned to. |
| `reset_freq_rebill.py` | 9/3 frequency-1 sweep | Every unpaid visit still carrying the 6/9 'corrected claim' flag with no payer ICN gets reset to frequency 1 and rebilled. |
| `restore_rest.py` | Restore batch (9/3) | Runs restore_charge over the list of charges the 9/3 bug voided. |
| `ridgeway_fix.py` | Ridgeway to UHC Advantage | End Humana 6/30/25, add UHC MA <id> from 7/1/25, undo the two Medicare CO24 postings, re-send the three visits. |
| `run_gv.py` | GV run list | Which patients gv_rebill runs for on a given night. |
| `stanhope_sterling.py` *(local only)* | Stanhope Patient864 to Medicare; Sterling post-death write-off | Adds Stanhope's MBI and re-sends her two visits; writes off Sterling's CCM lines dated after his 11/8/25 date of death. |
| `wexford_fix.py` | Wexford Feb-May 2026 to Medicare | UHC was inactive Feb-May 2026 (Stedi), so those visits go Medicare first, FCC second; UHC start set to 6/1/26. |
| `work_0906.py` *(local only)* | 9/6 board work (Sterling, Lydgate, Ludlow) | Sterling to Medicare + Sunshine (Aetna ended, two untimely lines written off); Lydgate Patient960's patient balances back to Humana; Ludlow to CHP + Simply (BCBS ended). |
| `wrongpayer_rebill.py` | Rebill after a refresh | After a chart's insurance is corrected, which other unpaid visits are still pointed at the ended plan, and re-sends them under the new order. |

### `billing/writeoff/`

Write-off passes: not-on-file remnants, cascade untimely, and the over-365-day rule (primary claims past a year with any carrier).

| Script | What it is | What it decides |
|---|---|---|
| `writeoff_0905.py` | 9/5 approved write-offs | Carrow, Chadwick, Cormack, Barlowe (2024) lines older than 12 months, plus Lockridge 8/22 CCM (no Railroad credentialing). |
| `writeoff_old.py` | 9/4 pre-2025 write-offs | Every pre-2025 audit line, past all timely-filing windows. |
| `writeoff_old_notonfile.py` | Write off the 'never received' claims that are past every payer's filing limit | Every claim the full status sweep marked NOT ON FILE whose date of service is more than 12 months old gets its open insurance balance written off as untimely (William, 9/7/2026: "we could probably just write those off if… |
| `writeoff_over365_0907.py` | Write off every open claim more than a year old - all carriers, William 9/7/2026 | William's call tonight: "write off every claim past one year with any carrier - no chance of it being resubmitted for actual payment." Every visit on the unpaid list with a date of service more than 365 days old gets its… |

### `billing/scans/`

Read-only scans: payments by carrier, CO24, voids, blank begin dates, full claim-status sweep (Stedi 276/277), AWV due list.

| Script | What it is | What it decides |
|---|---|---|
| `awv_due.py` | Annual wellness visit due list | For every active patient, when the next AWV is billable. |
| `blank_begindate_scan.py` | Blank insurance effective-date scan | Which active insurance plans on recently-seen patients have NO effective (begin) date - the Southwick oversight William spotted 9/6. Plans without a begin date can be sent as primary when they should not be, and eligibili… |
| `claim_status_sweep.py` | Weekly claim-status sweep | For unpaid claims older than N days, what the payer says happened to them (paid / denied / pending / never received) via a Stedi 276/277 check, and sorts them into actions. |
| `mcad_pay_scan.py` | Medicaid payment scan | Nothing - lists what Medicaid paid vs denied. |
| `pay_scan.py` | Posted-payment scan for the Money Ledger | Nothing. Reads every known patient's transaction history and totals what each carrier has actually PAID (posted payments, by month) and what was written off, so the ledger can show "paid last 12 months / paid all time" p… |
| `scan_co24.py` | Medicare $0 denial scan | Nothing - finds every 2025+ Medicare $0 denial that means 'bill someone else' (CO24, COB9, CO109, CO16, CO22). |
| `sweep_full.py` | Full claim-status sweep - every open insurance balance | For every unpaid visit older than 30 days on a payer Stedi can reach, what the payer says happened to the claim (paid / denied / pending / never received), one Stedi 276/277 check per visit. |
| `void_scan.py` | Find voided charges | Nothing - lists charges voided on given dates and whether the void looked intended. |

### `eligibility/`

The insurance cascade: patient database -> AMD eligibility (free 271) -> Stedi eligibility / discovery -> facesheet -> William. Denial cascades ask the payers what coverage really was and sort every denied claim into an action.

| Script | What it is | What it decides |
|---|---|---|
| `denial_act2.py` | 9/6 commercial/Medicaid denial cascade - actions | Applies the clear-cut verdicts from denial_cascade2: (A) Medicaid says the patient has Medicare -> add Medicare, bill Medicare first then Medicaid; (B) Medicaid says the patient is in an SMMC plan -> add that plan (with … |
| `denial_act3.py` *(local only)* | 9/7 second-pass actions from stedi_pass2 - the clear-cut ones | Applies the second Stedi pass verdicts that need no human judgment: add the Advantage plan / Medicare the payers confirmed, fix a member number the payer corrected, and point the denied (or never-received Medicaid) in-wi… |
| `denial_act_0906.py` *(local only)* | 9/6 denial cascade - actions | Applies tonight's Stedi findings to the Medicare $0-denial patients: bills the Advantage plan Medicare named (LaRosa, Sinclair, Jarvis Lorna, Lansing, Galloway, O'Donnell), and corrects Ellsworth' MBI to the one CMS holds, t… |
| `denial_cascade.py` | Medicare $0-denial cascade | For every patient in the Medicare $0-denial scan (CO24 / COB9 / CO16 / CO22 / CO109), what Medicare's own record says for the denied date of service - Advantage plan, hospice, MBI mismatch, other payer, death - and what … |
| `denial_cascade2.py` | Commercial / Medicaid denial cascade - from the claim-status sweep | For every patient whose non-Medicare claims came back DENIED or FINALIZED-$0 in the full status sweep, what the coverage actually was on those dates - asked of the payers themselves (Stedi eligibility on the billed plan,… |
| `disc_run.py` | Stedi Insurance Discovery over the held board cards | Nothing on its own. First checks whether the DISCOVERY enrollment is LIVE (one cheap test call). If it is, runs discovery (name + DOB + state, $1.50 each) for every Insurance Refresh Board card that is holding for it and… |
| `held_elig_0908.py` | AMD eligibility over the 87 board cards that were waiting for Stedi discovery | Nothing yet - it looks. For every Insurance Refresh Board card still 'Holding for Stedi Insurance Discovery', runs AMD's free eligibility on every plan on the chart (elig_amd) and writes held_elig_0908.json: per patient,… |
| `stedi_pass2.py` | Second Stedi pass on the board candidates - before anything goes to William | For the denial-cascade patients that were parked for William, asks Stedi everything that is live today: (MA) eligibility at the Advantage payer Medicare named, using the MBI as the member id - most MA payers hand back th… |

### `credentialing/`

Nightly credentialing check (NPPES, Medicare revalidation, OIG) feeding the Credentialing Board; the board template lives in boards/templates.

| Script | What it is | What it decides |
|---|---|---|
| `cred_check.py` | Nightly credentialing check | Whether anything on the Credentialing Board changed at the source - the three NPPES records (address, taxonomy, license, group), the Medicare revalidation list (a due date appearing), and the OIG exclusion list (a match)… |

### `claimocity/`

Claimocity hospital charge feed (HL7 drop on Drive, Cloud Run pull every 30 min) compared against AMD insurance. `claimocity/README.md` is the feed runbook (two paths, the 9/10–9/17 outage and its fix, Cloud Shell one-liners); `claimocity/cloud_run/` is the deployed copy-job code.

| Script | What it is | What it decides |
|---|---|---|
| `claimocity_in1.py` | Claimocity feed vs AMD | For each hospital patient in the Claimocity HL7 drop, whether the hospital's insurance (IN1) matches what AMD has. |
| `cloud_run/main.py` | Claimocity SFTP -> Drive copy job | Nothing — copies every new SFTP file into the "Claimocity drop" Drive folder as the job's service account (deployed 9/18/2026). |

### `boards/`

Builders for the Money Ledger, Programming Lab and the board facility lines, plus the HTML templates of the three boards.

| Script | What it is | What it decides |
|---|---|---|
| `board_facilities.py` | Facilities line for the Insurance Refresh Board | Nothing. For every board card with an AMD patient id, reads the chart's transaction history and writes a one-line list of the facilities the patient was seen at (name + month range, newest first; '(Pam)' when only Pam sa… |
| `board_identity.py` | Identity block for the Insurance Refresh Board - DOB, insurance ID, last facility | Nothing. For every board card with an AMD patient id, reads the chart and the transaction history and writes the DOB, the insurance ID of the plan that bills first (with carrier), every plan in billing order, the last facility + last DOS and the facilities line into board_identity.json and ONE board_updates_<stamp>.json for the Drive 'board inbox' (the board applies it itself). |
| `build_learning_app.py` |  |  |
| `build_money.py` | Money Ledger builder | Nothing. Pulls the unpaid list, ERA Center checks, claim runs, tonight's exclusions and the write-off registers into money_data.json and renders money_ledger.html for the Effinger Money Ledger artifact. |

## History

- 2026-09-07 — first mirror (104 scripts) as `effinger-billing-backend`.
- 2026-09-08 — reorganized as the Cloud Practice project: folders by function, `practices/ehpa`, PHI-bearing scripts reduced to stubs, README generated from headers.
