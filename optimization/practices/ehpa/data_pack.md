# EHPA practice data pack (aggregates only, no patient-level data)

Compiled 2026-11-10 from: the practice's Neon Postgres (`ehpa.*` views, read-only), the accountant's cash-basis financial statements in Drive (Lanigan & Associates; "not audited, reviewed, or compiled"), the billing repository (`practices/ehpa/*`, `README.md`), and the credentialing board copy. Dollar figures are as stated in those sources. Every number here is an aggregate; there are no names, dates of birth, member ids or chart-level rows. Treat it as confidential business information of the practice.

Updated November 10, 2026 (evening) with that day's facts: the place-of-service rule and its first live batch, the clinician on feed visits, initial nursing-facility visits, the never-billed feed visits, the coverage refresh and the look-up vendor, the Medicare quality program, the full AdvancedMD history in the practice database, and credentialing corrections. They are in section 6; lines above that the day changed say so and point there. An independent check of this update returned 33 findings; they were applied on November 11, 2026 (UTC). Brought forward on November 11, 2026 (UTC) with that day's facts: the never-billed fix went live, the history pull finished, and the Medicaid renewal is to be filed by November 13. Where a figure changed, the line says so.

## 1. Profile

- Legal entity: Effinger Health, P.A. (files Form 1120-S, i.e. taxed as an S corporation). DBA North Florida Senior Care. Tallahassee, Florida. Group NPI 1629515325.
- Clinicians: William L. Effinger, DO (owner; family medicine, AOBFP board certified through 12/31/2030; NPI 1225327380) and one nurse practitioner (APRN; NPI 1235128869).
- Model: facility-based geriatrics / primary care. Sites seen in the charge feed (Sep 30 - Nov 7, 2026): one hospital (HCA Florida Capital Hospital, POS 21), five skilled nursing / nursing facilities (all billed as POS 31 until 2026-11-10; since then the import sets 31 or 32 by the owner's rule, see 6.1: Brynwood in Monticello, Aspire at Tallahassee, Centre Pointe, Westminster Bertrand, Oakes Southwood), and seven assisted living facilities (POS 13). A small office exists (rent and utilities about $58K a year). Tallahassee Memorial Hospital appears in historical notes but not in the current feed.
- Medical director stipends: two in 2026 ($12,000 each for nine months), down from five or more in 2023.
- Systems: AdvancedMD (practice management), Claimocity (hospital/facility census and charge capture, feeding AMD), Stedi (eligibility, claim status), Availity and payer portals, Square (card terminal and paper-check deposits), QuickBooks (connector needs re-authorization), Neon Postgres (HIPAA project) as the permanent store, Claude agents run billing in-house on a schedule (every 2-6 hours) under a BAA.
- Staff: staff salaries were $154,534 for the nine months to 9/30/2026 (about $206K annualized) and include the nurse practitioner. Staff payroll fell from $522K (2023) to $370K (2024) to $272K (2025).
- Medicare contractor: First Coast Service Options (Florida Part B).

## 2. Financial statements (cash basis, unaudited)

| | 2023 | 2024 | 2025 | 9 months to 9/30/2025 | 9 months to 9/30/2026 | Q3 2026 alone |
|---|---|---|---|---|---|---|
| Professional fees (collections) | 1,530,282 | 1,152,238 | 828,415 | 597,268 | 779,006 | 307,949 |
| Medical director stipends | 185,300 | 54,000 | 96,500 | 72,500 | 24,000 | 9,000 |
| Net revenue | 1,727,834 | 1,206,210 | 924,915 | 669,768 | 803,006 | 316,949 |
| Total operating expenses | 976,299 | 702,782 | 524,514 | 418,420 | 367,002 | 138,497 |
| of which staff salaries and fringe | 590,701 | 433,277 | 322,113 | 261,665 | 186,353 | 62,478 |
| of which billing services / software | 107,330 | 92,932 | 69,499 | 54,698 | 48,772 | 26,790 |
| of which legal and accounting | 69,716 | 77,834 | 28,086 | 21,986 | 17,257 | n/a |
| of which rent and utilities | 49,006 | 45,684 | 45,238 | 35,356 | 43,456 | 16,270 |
| Interest expense | 195,050 | 65,372 | 34,601 | 26,540 | 21,738 | 6,833 |
| Depreciation + amortization | 13,002 | 11,723 | 6,322 | 4,741 | 6,044 | 3,488 |
| Interest income (shareholder loan accrual) | 25,531 | 13,842 | 8,339 | 6,379 | 4,560 | 1,642 |
| Net operating income (before doctor pay) | 652,263 | 440,175 | 367,817 | 226,445 | 412,782 | 169,773 |
| Doctor salary + payroll tax + health | 72,850 | 149,603 | 184,121 | 129,684 | 162,858 | 54,556 |
| Net income | 579,413 | 290,572 | 183,696 | 96,761 | 249,924 | 115,217 |

Derived:
- EBITDA before any owner compensation = net revenue - operating expenses: 2023 $751,535 (2023 also had $72,669 of one-time Employee Retention Credit income and a $10,400 asset gain in other income), 2024 $503,428, 2025 $400,401, nine months 2026 $436,004.
- Trailing twelve months to 9/30/2026 (Q4 2025 + nine months 2026): net revenue $1,058,153; operating expenses $473,096; EBITDA before owner compensation $585,057; interest expense $29,799; doctor compensation recorded $217,296; net income $336,858.
- Revenue trend: -30% (2024 vs 2023), -23% (2025 vs 2024), +19.9% (nine months 2026 vs nine months 2025); Q3 2026 net revenue +38% vs Q3 2025. Q3 2026 annualizes to $1.27M; the first half of 2026 annualized to $0.97M. Part of Q3 2026 collections is recovery of old receivables from the AI-run cleanup that began in September 2026 (not yet separated from recurring collections).
- Operating expense ratio (operating expenses / net revenue): 56.5% (2023), 58.3% (2024), 56.7% (2025), 45.7% (nine months 2026).
- Billing cost as a share of professional fees: 7.0% (2023), 8.1% (2024), 8.4% (2025), 6.3% (nine months 2026); Q3 2026 alone 8.7% (billing services and software $26,790 on $307,949).
- Owner cash in the nine months 2026: salary $135,000 plus $176,241 of distributions.

Balance sheet at 9/30/2026 (cash basis, so no receivables or payables are on it):
- Cash $94,431 (two Regions accounts). Net property and equipment $22,497. Capitalized loan fees, net $13,005.
- Shareholder loan receivable $162,121 (money the owner owes the corporation; it was $288,420 at end of 2023; interest accrues as income).
- Debt $212,206: Bankers Healthcare Group note $187,206 (current portion $48,053; the owner's board lists the rate as 13.99%) and a family trust loan $25,000. Merchant-cash-advance style notes (Square Capital, Spartan Capital) were paid off during 2024; interest expense fell from $195K (2023) to about $29K a year now.
- Stockholder's equity $79,847.
- Outside the corporation, the owner's finance board notes a personal tax balance on a monthly installment plan (amount not recorded here).

## 3. Revenue cycle (Neon `ehpa.*`, aggregates)

### 3.1 Receivables
- Open insurance receivables at billed charges (Money Ledger, as of 2026-11-09): $342,620 on 2,695 visits and 489 patients' charts. By days since date of service: 0-30 $155,619 (45.4%); 31-60 $46,954 (13.7%); 61-90 $18,644 (5.4%); 91-180 $34,727 (10.1%); 181-365 $61,713 (18.0%); over 365 $24,964 (7.3%). So 35.4% is older than 90 days and 25.3% older than 180 days.
- Earlier snapshot (2026-10-11, $272,171): 46.1% older than 120 days. On 2026-11-02 the routine wrote off $40,686 of balances over a year old under the owner's standing rule.
- Approximate days in receivables on gross charges: $342,620 / (October 2026 gross charges $164,832 / 31 days) = about 64 days. This is gross-on-gross from one month of charges, so treat it as an estimate.
- By payer (11/9): Medicare fee-for-service $190,203 (55.5%); UnitedHealthcare $30,856; Florida Community Care (Medicaid long-term care plan; paper checks, portal-only eligibility) $26,640; Florida Blue $18,483; UnitedHealthcare Dual Complete $17,284; Humana $11,132; VA Community Care (Optum) $6,024; Sunshine $4,985; Capital Health Plan $4,603; Florida Medicaid $4,409; Cigna $4,364; Railroad Medicare $3,764 (it paid $718.76 in 2026, so "not credentialed" looks wrong for the group and the physician; the nurse practitioner's status is not known; its claims were being written off - corrected 2026-11-10, see 6.8); Tricare For Life $2,479 (electronic enrollment rejected); Tricare East $1,540 (electronic claims approved October 2026; nurse practitioner not credentialed); others small.
- Aging engine verdicts (2026-10-16): wait $205,605 (1,635 visits); correct and resend $65,431 (714 visits); write off $44,700 (876 visits, $31,088 of it over a year old).
- Weekly average of total open receivables: $272K (Oct 5), $301K, $281K, $305K, $323K, $340K (Nov 9): rising about 25% in five weeks while charge volume through the new feed ramped up.

### 3.2 Charges (Claimocity feed, entered into AdvancedMD; Sep 30 - Nov 7, 2026)
- October 2026: 775 entered encounters, $164,832 gross charges, 326 distinct patients, 24 days with service. Nov 1-7: 246 encounters, $44,897.
- By site, share of gross charges in the whole window ($211,062): hospital 37.8% ($79,886), skilled nursing / nursing facilities 42.6% ($89,825 incl. unlabeled), assisted living 19.3% ($40,693). Largest single sites: HCA Capital Hospital 37.8%, Brynwood 17.6%, Aspire 9.4%.
- By clinician: physician-owner 716 encounters / $162,198 (76.8% of charges); nurse practitioner 309 encounters / $48,864 (23.2%).
- October workload: physician 548 billed lines over 18 days (about 255 of them are monthly care-management lines, so roughly 16 face-to-face visits a day); nurse practitioner 227 encounters over 17 days (13.4 a day).
- Lead payer by charges: Medicare fee-for-service 55.5%; no payer recorded 11.2% (checked 2026-11-10: this is the share of feed dollars on charts the insurance check held (counted after the check ran), $23,534 of $211,062, not charges that arrived with no payer; see 6.4); UnitedHealthcare 8.0%; Humana 5.6%; Capital Health Plan 5.0%; Florida Blue 3.8%; Florida Community Care 2.8%; Sunshine 2.7%; UHC Dual Complete 2.3%; VA 0.9%; Medicaid 0.8%.
- Charge lag (date of service to entry in AMD, October onward): median 3 days, 90th percentile 5 days for visits.
- Code counts (entered lines, whole window): 99233 x269; 99309 x260; 99487 x257; 99489 x213; 99232 x96; 99223 x70; 99497 x62; 99344 x31; 99306 x19; 99308 x12; 99239 x7; 99316 x3; 99498 x2. No 99231, 99221, 99222, 99304, 99305, 99307, 99310, 99238, 99315, and no established-patient home/residence codes (99347-99350) in this window (99349 does appear on earlier remittances).
- Level distribution inside each family: subsequent hospital care 99233 73.7% / 99232 26.3% / 99231 0%; initial hospital care 99223 100%; subsequent nursing facility care 99309 95.6% / 99308 4.4% / 99307 0% / 99310 0%; initial nursing facility care 99306 100% (19 visits at POS 31; the feed names the nurse practitioner on 10 and the physician on 9, and the import entered 6 under her and 13 under the physician - corrected 2026-11-10, see 6.3); discharge day codes 100% the over-30-minute code (99239 x7, 99316 x3); assisted living 99344 (new patient) x31, 25 of them by the nurse practitioner.
- Advance care planning 99497 on 62 encounters (about 8% of face-to-face visits), usually on the same day as an admission or visit.
- Nursing facility visits per resident, October 2026 (charge feed, counted 2026-11-10): 218 visits to 135 residents, 1.61 each; 14 residents were seen four or more times.
- Place of service: every nursing-facility visit in the feed carries POS 31 (skilled nursing facility); POS 32 (nursing facility, long-term) is never used. (True for this window. From 2026-11-10 the import sets 31 or 32 by the owner's rule; see 6.1.)
- The practice's charge amounts: 99233 $160; 99232 $111; 99223 $310; 99309 $130-141; 99308 $107; 99306 n/a alone; 99487 $206; 99487+99489 $315; 99344 $300; 99239 $163; 99316 $207.

### 3.3 Complex chronic care management (99487 / 99489)
- October 2026: 257 patients billed 99487, 213 of them also 99489 (83%). All under the physician-owner. Service date is batched (213 of 257 on one day; the practice's standing rule is that the claim is a monthly total dated at month end).
- Place of service on those lines: POS 31 x152, POS 13 x103, POS 21 x2. From 2026-11-10 the import enters care management in the five nursing buildings as POS 32, except in a month the chart looks skilled (see 6.1).
- Implied documented clinical-staff time: 257 x 60 minutes + 213 x 30 minutes = 21,810 minutes, about 364 hours in the month.
- Remittance experience, dates of service since 2026-06-01: 99487 137 lines, 58 paid (42%), 79 paid zero; 99489 80 lines, 40 paid, 40 zero. Reasons on the zero-paid lines: CO-170 with remark N95 from Medicare (38 lines on 99487, 18 on 99489), CO-96 non-covered (14 and 6), CO-151 frequency (6), CO-234 not paid separately (6 on 99489), OA-18 duplicate, CO-B9 hospice (3).
- When paid as primary, 99487 paid $63 on 32 lines (allowed about $79, the facility rate), $112 on 12 lines (allowed about $140, the non-facility rate), $69 on 10 lines. 99489 median paid $35.
- Standing practice rules: care management is never billed to Florida Medicaid (never pays; written off as non-covered); not billable for hospice patients (written off); a frequency denial is re-dated to month end and resent; duplicates in a month are voided.

### 3.4 Payments and denials
- Remittance lines processed by the engine 9/30-10/16/2026: 956 lines, $26,832 paid, 53% of lines paid zero (inflated by the rebilling of old claims). For dates of service on or after 2026-08-01: 311 primary lines, 93 paid zero (29.9%). Zero-pay reasons on those recent lines: CO-170 (63), OA-23 (39), CO-256 (32), CO-96 (21), CO-45 (20), CO-16 (18), OA-18 (18).
- CO-256 ("not payable per managed care contract") hit 21 lines of 99233 plus 99223 and 99306 lines: a Medicare Advantage or HMO plan refusing hospital and admission visits.
- Days from date of service to remittance, paid lines with service on or after 2026-08-01: median 18 days, 90th percentile 46 days. All paid lines (including old rebills): median 28, 75th percentile 158, 90th percentile 298.
- Median paid per code as primary (2026 service dates): 99223 $125.20; 99233 $85.46; 99232 $56.37; 99306 $110.29; 99309 $66.36; 99308 $45.44; 99239 $84.62; 99316 $79.42; 99487 $63.28; 99489 $34.95; 99497 $52.33.
- Working Denials register (1,356 denied visits, service dates 2022-2026, $100,226 open): by first reason code: 16 missing information x163; 27 coverage terminated x154; 29 timely filing x100; 18 duplicate x100; 23 prior payer x100; 45 contractual x100; 96 non-covered x90; 1 deductible x90; 24 covered by a capitated/advantage plan x68; 185 rendering provider not eligible x61; 200 lapse in coverage x55; 22 coordination of benefits x42; 242 not network/PCP x36; 256 managed care contract x34; B9 hospice x31. Status: resolved 575 visits; written off 351 visits ($82,665 of billed charges); resubmitted 184 ($42,557 open); open 246 ($50,126 open). Disposition tags: fix 227 ($30,977 open); coordination of benefits 119; credentialing 108; timely 100; patient responsibility 90.
- Latest billing run (2026-11-10 01:24 UTC): Claims Center columns after the run: charge review 0, claim inspector 2, unbilled 0, exclusions 2; unposted remittances $0; 74 actionable denials worth $13,463.
- Claim runs since 2026-07-11: 13,385 claims, $2,574,765 submitted across 125 runs (this includes mass re-sends of old claims, so it is not a clean volume measure).
- Nightly insurance cascade (9 nights to 11/9): $8,447 re-sent after coverage corrections. Insurance Refresh Board: 503 cards, 349 open on 2026-11-10; 136 with nothing left to bill or collect were closed that day (see 6.4).

### 3.5 Treasury (bank deposits vs remittances, Aug 13 - Sep 11, 2026)
- $66,065 of payer deposits in 65 deposits plus $8,769 through the card terminal (12% of receipts; part of that is payer virtual cards, which carry about 3% processing cost), $884 in bank and processor fees.
- Findings logged: Medicare deposits with no matching electronic remittance ($12,902); UnitedHealthcare / Optum remittances arriving with no money landing (flagged critical); eight remittances failing auto-post (188 lines); six payers with zero deposits in the month; Florida Community Care pays by paper check.

### 3.6 Credentialing and enrollment (board copy, 42 items)
- Cigna terminated the practice effective 8/31/2026 after a missed recredentialing; later contact suggested the physician is still listed as participating, unresolved.
- Corrected 2026-11-10 from the reminders check of the board, the compliance sheet and the mail (see 6.8): Railroad Medicare is paying ($718.76 in 2026, $3,764 open); the earlier "not enrolled" looks wrong for the group and the physician (whether the nurse practitioner has a Railroad Medicare number is not known), but its claims were being written off. Tricare East: electronic claims approved 2026-10-09 and remittances 2026-10-05; the nurse practitioner is not credentialed. Tricare For Life: claims agreement denied 2026-09-30 and remittance agreement 2026-10-21 (invalid trading partner ID). VA Community Care: portal registration pending and claims need authorization numbers. UnitedHealthcare directory attestation: done 2026-08-28, next about 2026-11-26 (not overdue); a network removal notice with missing first pages is open. Sunshine/Centene required training: two of eight courses left. Aetna ERA/EFT enrollment cancelled/rejected. Florida Medicaid: the physician's provider agreement expires 2026-12-27 (file by 2026-11-13; 2026-12-01 is the last call); the nurse practitioner's Medicaid enrollment is a new application, not a revalidation, returned with three faults. Cigna: its three secure messages can be read until 7:30 AM Eastern on 2026-12-08, so the last day is 2026-12-07. The nurse practitioner's NPPES record is stale and carries the wrong taxonomy. Hospital privileges reappointment has open items. Monthly OIG exclusion check is being run.

## 4. Things this pack cannot answer yet (data gaps)
- Net collection rate, contractual adjustments, and true first-pass denial rate by cohort: need AdvancedMD transaction history rolled up by month of service (payments, adjustments, write-offs by reason). Since 2026-11-10 that history is in the practice database (6.7); the rates are not computed yet, and posted payments for 2022-2025 are a floor.
- Collections by payer and by service line for a full year (the Money Ledger payment totals were empty in the latest snapshot).
- How much of 2026 collections is one-time recovery of old receivables.
- Which nursing-facility residents are in a Medicare Part A skilled stay versus long-term residents (drives place of service 31 vs 32, care-management eligibility and visit rules). The 2026-11-10 rule reads the visit pattern instead; each facility's Part A list is still wanted as the proof.
- Time logs, consent and care plans behind complex care management claims (documentation lives in the clinical record, not in this data).
- Payer contract terms and fee schedules; the practice's charge master versus contracted rates.
- QuickBooks detail (connector must be re-authorized); monthly profit and loss; payroll by person.

## 5. Public Medicare fee-for-service history (CMS open data, by rendering NPI)

Source: CMS "Medicare Physician & Other Practitioners" public use files on data.cms.gov, calendar years 2019-2024 (2024 released May 2026). This is public data that any auditor, payer or buyer can pull. It covers Medicare fee-for-service only (no Medicare Advantage, Medicaid or commercial), is grouped by the clinician who rendered the service, and suppresses any code with fewer than 11 beneficiaries, so totals understate slightly. Place of service: F = facility rate (hospital, skilled nursing facility POS 31), O = non-facility rate (office, nursing facility POS 32, assisted living, home).

### 5.1 Totals by year (CMS provider summary file)

| Clinician | Year | Beneficiaries | Services | Medicare allowed | Medicare paid | Dual-eligible share | Average risk score |
|---|---|---|---|---|---|---|---|
| Physician-owner | 2022 | 685 | 4278 | $448,410 | $341,236 | 47% | 2.1519 |
| Physician-owner | 2023 | 512 | 4079 | $445,219 | $330,399 | 47% | 2.1453 |
| Physician-owner | 2024 | 308 | 2859 | $265,381 | $207,807 | 32% | 2.1018 |
| Nurse practitioner | 2022 | 390 | 2868 | $159,170 | $118,134 | 52% | 2.102 |
| Nurse practitioner | 2023 | 276 | 2163 | $164,385 | $124,600 | 58% | 2.2743 |
| Nurse practitioner | 2024 | 306 | 2564 | $193,669 | $141,983 | 50% | 2.2661 |

Sum of the code-level rows, 2019-2021 (no summary file pulled for those years): physician Medicare allowed $469,732 (2019), $402,795 (2020), $346,363 (2021); nurse practitioner $89,571, $169,086, $162,769.

### 5.2 Services by code and year (services / average Medicare allowed), rows with 11+ beneficiaries

**Physician-owner**

| Code | POS | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|
| 99487 | O | 1,717 @ $80 | 2,050 @ $81 | 1,793 @ $90 | 1,331 @ $131 | 539 @ $130 |  |
| 99232 | F |  |  |  | 127 @ $71 | 575 @ $79 | 1,978 @ $77 |
| 99233 | F |  |  |  | 339 @ $102 | 1,045 @ $119 | 27 @ $116 |
| 99223 | F |  |  |  | 108 @ $197 | 353 @ $173 | 400 @ $169 |
| 99497 | F | 343 @ $79 | 211 @ $80 | 231 @ $79 | 336 @ $78 | 398 @ $75 | 268 @ $73 |
| 99497 | O | 389 @ $85 | 472 @ $86 | 394 @ $86 | 200 @ $85 | 56 @ $82 |  |
| 99306 | F | 249 @ $167 | 97 @ $169 | 130 @ $168 | 144 @ $163 | 116 @ $180 | 28 @ $177 |
| 99305 | O | 311 @ $130 | 241 @ $131 | 211 @ $130 | 77 @ $128 |  |  |
| 99489 | O | 19 @ $45 |  |  | 719 @ $65 | 536 @ $65 |  |
| 99316 | O | 106 @ $106 | 295 @ $106 | 240 @ $106 | 89 @ $103 |  |  |
| 99305 | F | 171 @ $130 | 146 @ $131 | 114 @ $130 | 125 @ $127 | 18 @ $132 |  |
| 99306 | O | 75 @ $167 | 174 @ $169 | 126 @ $168 | 50 @ $164 |  |  |
| 99239 | F |  |  |  | 70 @ $104 | 196 @ $114 | 71 @ $111 |
| 99307 | F | 590 @ $44 | 153 @ $44 | 41 @ $44 | 62 @ $43 |  |  |
| 99307 | O | 632 @ $44 | 37 @ $44 |  |  |  |  |
| 99316 | F | 42 @ $106 | 46 @ $106 | 71 @ $106 | 67 @ $102 | 40 @ $130 |  |
| 99309 | F | 151 @ $91 | 45 @ $92 | 12 @ $91 | 18 @ $89 | 21 @ $105 | 15 @ $105 |
| G0438 | F | 118 @ $169 | 16 @ $168 |  |  |  |  |
| 99308 | F | 129 @ $69 | 46 @ $70 |  | 75 @ $68 |  | 18 @ $72 |
| 99310 | F |  |  |  |  | 72 @ $152 | 41 @ $149 |
| 99327 | O | 30 @ $188 | 22 @ $188 | 23 @ $187 | 16 @ $182 |  |  |
| G0439 | F | 12 @ $114 | 48 @ $114 | 17 @ $133 | 36 @ $131 |  |  |
| 99337 | O | 47 @ $194 | 19 @ $196 |  |  |  |  |
| 99490 | O | 24 @ $41 |  |  | 166 @ $63 |  |  |
| 99336 | O | 42 @ $136 | 22 @ $136 |  |  |  |  |
| G0438 | O | 24 @ $169 | 20 @ $168 |  |  |  |  |
| G0439 | O |  | 16 @ $113 |  | 15 @ $131 | 22 @ $127 |  |
| 99326 | O | 11 @ $140 |  | 22 @ $139 | 14 @ $135 |  |  |
| 99308 | O | 75 @ $69 |  |  | 16 @ $68 |  |  |
| 99315 | F |  | 14 @ $75 | 30 @ $73 | 13 @ $72 |  |  |
| 99309 | O | 41 @ $91 |  |  |  |  |  |
| 99498 | O | 22 @ $75 |  |  |  | 28 @ $71 |  |
| 99213 | O |  | 44 @ $75 |  |  |  |  |
| 99487 | F | 55 @ $53 |  |  |  |  |  |
| 99344 | O |  |  |  |  | 17 @ $143 |  |
| 99214 | O |  | 19 @ $109 |  |  |  |  |
| 99498 | F | 11 @ $75 |  |  |  | 11 @ $71 |  |
| 99318 | O |  |  |  | 13 @ $94 |  |  |

**Nurse practitioner**

| Code | POS | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|
| 99307 | F | 1,323 @ $37 | 1,618 @ $38 | 1,680 @ $37 | 1,535 @ $37 | 359 @ $33 | 130 @ $33 |
| 99308 | F | 146 @ $58 | 728 @ $59 | 596 @ $59 | 651 @ $58 | 567 @ $63 | 921 @ $61 |
| 99309 | F | 289 @ $78 | 471 @ $78 | 292 @ $77 | 208 @ $76 | 468 @ $89 | 510 @ $89 |
| 99336 | O | 42 @ $115 | 105 @ $116 | 213 @ $115 | 172 @ $113 |  |  |
| 99497 | F | 12 @ $67 | 18 @ $68 |  | 72 @ $66 | 216 @ $64 | 442 @ $62 |
| 99349 | O |  |  |  |  | 212 @ $108 | 190 @ $106 |
| 99337 | O | 22 @ $165 | 36 @ $167 | 45 @ $165 | 67 @ $162 |  |  |
| 99497 | O |  |  | 23 @ $73 | 76 @ $72 | 118 @ $70 | 168 @ $68 |
| 99306 | F |  |  |  |  | 37 @ $153 | 129 @ $151 |
| 99310 | F |  |  |  |  | 136 @ $129 | 31 @ $127 |
| 99307 | O |  | 171 @ $38 | 165 @ $37 |  |  |  |
| 99308 | O |  | 36 @ $60 | 46 @ $59 |  |  |  |
| 99344 | O |  |  |  |  | 15 @ $121 | 20 @ $118 |
| 99350 | O |  |  |  |  | 25 @ $157 |  |
| G0439 | F |  |  |  | 27 @ $109 |  |  |
| 99316 | F |  |  |  |  |  | 18 @ $108 |

Charge amounts on file in those years (average submitted charge): complex care management 99487 $110-112 (2019-2020) and $135 (2021-2023) against an allowed amount of $130 in 2022-2023; 99489 $65.70 against $65 allowed; 99490 $62.93 against $62.51 allowed. The charge was set at or within a few dollars of the Medicare allowed amount, which caps any payer that would have paid more. The charge in the October 2026 feed is $206 for 99487.

### 5.3 National distribution of visit levels, Medicare fee-for-service 2024, all specialties (CMS geography-and-service file) versus this practice

| Code family | National mix 2024 | This practice |
|---|---|---|
| Subsequent hospital care | 99231 6.6% / 99232 56.2% / 99233 37.2% | 99231 0% / 99232 26.3% / 99233 73.7% (Oct-Nov 2026 feed); CMS data for the physician: 99233 share 64.5% in 2023, 1.3% in 2024 |
| Initial hospital care | 99221 5.1% / 99222 35.4% / 99223 59.5% | 99223 100% (70 visits) |
| Hospital discharge day | 99238 23.3% / 99239 76.7% | 99239 100% (7) |
| Initial nursing facility care | 99304 12.4% / 99305 39.1% / 99306 48.5% | 99306 100% (19 at POS 31; the feed names the nurse practitioner on 10, see 6.3). CMS data: the nurse practitioner billed 99306 at the facility rate 37 times in 2023 and 129 times in 2024 |
| Subsequent nursing facility care | 99307 5.1% / 99308 38.7% / 99309 48.8% / 99310 7.3% | 99307 0% / 99308 4.4% / 99309 95.6% / 99310 0% (Oct-Nov 2026 feed); CMS data for the nurse practitioner 2024: 99307 8.2% / 99308 57.9% / 99309 32.0% / 99310 1.9% |
| Nursing facility discharge day | 99315 27.8% / 99316 72.2% | 99316 100% (3) |
| Home or residence visit, established patient | 99347 7.0% / 99348 25.1% / 99349 50.1% / 99350 17.8% | none in the Oct-Nov 2026 feed; 99349 only in 2023-2024 CMS data |
| Home or residence visit, new patient | 99341 9.2% / 99342 24.7% / 99344 38.8% / 99345 27.3% | 99344 100% (31) |

Care management, national 2024: 99490 (non-complex, clinical staff) 6,919,114 services; 99491 (non-complex, clinician time) 283,868; 99487 (complex) 634,385. Complex care management is 8.1% of those three base codes nationally. This practice bills only the complex code: 257 patients in October 2026, and 1,717 (2019), 2,050 (2020), 1,793 (2021), 1,331 (2022) and 539 (2023) services of 99487 under the physician in the CMS data, then none in 2024. At 257 a month the practice would bill about 0.5% of all complex care management paid by Medicare fee-for-service nationally in 2024.

National average Medicare allowed amount in 2024, facility rate versus non-facility rate: 99487 $83.05 vs $126.28; 99489 $46.90 vs $67.71; 99490 $46.06 vs $59.99; 99439 $32.01 vs $46.33; 99309 $97.66 vs $95.24; 99308 $69.40 vs $67.97; 99306 $174.15 vs $171.79; 99497 $70.87 vs $75.69. For care-management codes the place of service on the claim changes the allowed amount by about a third; for nursing-facility visit codes it barely matters in 2024 data.

## 6. November 10 and 11, 2026 (aggregates; from those days' facts files and handoff notes)

### 6.1 Place of service in the nursing buildings
- The owner's rule (November 10, 2026): care management done in the nursing facilities is on long-term residents who are not being actively skilled, so it is billed POS 32, not 31, although the Claimocity feed sends 31; residents billed a monthly face-to-face visit are POS 32; residents seen once or twice a week in a skilled stay are POS 31; assisted living / home stays 13. Going forward only: claims already submitted are not changed and nothing is reopened ("seems like a red flag for an audit"). Care management is not flagged for review or held (standing).
- Live: rule version 2026-11-10.4 reached the live billing branch at 11:14 UTC; version 2026-11-10.6 (live 22:46 UTC) added the reviewers' follow-ups. In the five buildings (Brynwood, Aspire, Centre Pointe, Westminster Oaks-Bertrand, Oakes Southwood): care management 99487 / 99489 goes in as 32, except 31 when the chart shows, in the same calendar month, a hospital visit of the practice, a home or assisted living visit of the practice, a nursing visit the rule reads as weekly, an admission, a discharge or a new stay, or when the resident's nursing visits are in another building (those lines are listed for the owner, not held; list corrected after the check to the live rule). Visits 99304-99310, 99315, 99316 go in as 32 only for the monthly visit (previous nursing visit 21 to 92 days earlier, same building, not a discharge, no hospital or home visit of the practice in between, no admission visit the same day or within two weeks after); weekly or twice-weekly visits, admissions, discharges, the first visit of a chart or a stay, and anything unclear stay 31. 99497 / 99498 follow the visit line of the same date. Hospital, assisted living / home and unknown buildings are entered as before. It is a rule read from the visit pattern, not a check of each facility's Part A list.
- First live batch (12:39 UTC): 60 visits, 66 lines, $10,368, 0 failed; Brynwood 24 visits at 32 and 6 at 31; Aspire 1 at 31; HCA Capital Hospital 28 at 21; Azalea Gardens 1 at 13; both initial nursing-facility visits at 31 and entered under the physician; physician 31 visits, nurse practitioner 29; insurance check 55 RELEASE, 5 HOLD (Medicare names an Advantage plan that is not on the chart). Whether AdvancedMD kept every 32 is not read yet (the import register had not reached the live branch by 14:32 UTC).
- Medicare rates, Florida locality 99 (CMS RVU25D, RVU26D and the CY 2027 final rule): 99487 $129.48 at 32 vs $87.52 at 31 (2025), $142.98 vs $80.71 (2026), $139.13 vs $77.04 (2027). 99489 gap $21.89 (2025), $32.89 (2026), $32.95 (2027); 2026 $77.47 vs $44.58. Visits differ only in 2026: 99309 $114.90 vs $99.58 (+$15.32), 99307 +$4.79, 99308 +$10.54, 99310 +$22.04, 99306 +$28.42; equal in 2025 and again from 2027-01-01 (91 FR 70992). 99497 gap $6.69 (2025), $20.12 (2026), $17.43 (2027). Medicare pays 78.4% of the allowed amount; a nurse practitioner's service is paid at 85%. The practice's own 2026 payments in the nursing buildings: $63.28 per 99487 line and $34.95 per 99489 line, the facility rate.
- Past year, from the complete history (service months 2025-11 to 2026-10, five buildings): care management 3,505 lines; 1,667 paid by Medicare, $85,175.97; 372 open at Medicare. At the non-facility rate: $76,549.31 more allowed, Medicare's share $60,014.66, patient / secondary $15,310 ($76,492.74 allowed only if the nurse practitioner's 7 lines are put at 85%). Nursing visits 99306-99310, January-October 2026: 2,852 lines, 1,530 paid by Medicare; upper bound if every one had been a long-term resident: $20,896.64 allowed, Medicare's share $16,382.96 (corrected from $24,029.58 / $18,839.19; most paid lines are the nurse practitioner's, at 85%). The owner decided not to ask Medicare to reopen any of it.
- Going forward (estimate): at February-September 2026 volumes (about 86 first-hour and 71 add-on Medicare-paid lines a month), POS 32 adds about $6,000 a month of Medicare payment, about $72,000 a year at 2026 and 2027 rates; a fair planning range is $50,000 to $70,000 a year. The patient's 20% share on care management rises by about $19 a month per resident at 32.
- Visits, going forward (estimate, worked out after the check): the gain exists only for 2026 dates of service. The upper bound above is $10.71 of Medicare payment a paid visit line ($16,382.96 on 1,530 lines), and Medicare paid 131 to 213 visit lines a month from February to September 2026 (about 178 on average). For November 10 to December 31, 2026 that is about $3,200 if every visit went out at 32, about $2,500 at the first live batch's share (24 of 31 nursing facility visits at 32) and about $1,100 at the third expected before go-live: about $1,000 to $3,000. The plan's earlier $2,000 to $8,000 was above this ceiling.

### 6.2 Clinician on feed visits
- From 10/28/2026 the import kept one clinician per feed patient per batch. Result: 149 visits / 167 charge lines, all October 2026 dates of service (all but one visit in the 10/28 backlog batch): 165 lines on 148 visits the feed names the nurse practitioner on were entered under the physician (137 x 99309, 17 x 99497, 4 x 99306, 4 x 99344, 3 x 99308), and 2 care-management lines on 1 visit the other way. Fees on the 167 lines: $24,438 (corrected after the check: the earlier "about $21,900" was the import registers' visit totals, in which 18 of the visits show a fee of zero). State on 11/10: 133 lines billed and not yet paid (120 of them with Medicare Part B, on 107 visits), 15 not billed, 19 paid ($1,711, commercial plans and TRICARE; none by Medicare). By visit, of the 148 entered under the physician: 120 billed and not yet paid, 16 paid, 12 never billed. Only 3 lines are with a Medicaid plan. The same check found 18 visits whose code does not fit the building they were entered in (corrected after the check: it is not a comparison with each message's own building, which the registers do not keep): 3 with nursing facility codes at the hospital, 2 with hospital codes at an assisted living building, 2 care-management visits at the hospital and 11 with nursing facility codes and no building. The building side cannot be sized exactly.
- Fixed for new batches by rule version 2026-11-10.4 (11:14 UTC): each visit takes its clinician, building and admission date from its own feed message. Nothing already entered has been corrected.
- The 15 unbilled lines are 12 of the 84 never-billed visits (6.4). The owner decided on 11/10: the 10 that are not initial visits move to the nurse practitioner before they are sent; the 2 initial visits stay under the physician ("i saw those patients", 15:18 UTC). The 133 billed and 19 paid lines are open; the owner has not said to correct them.

### 6.3 Initial nursing-facility visits
- The owner's rule (November 10, 2026): "going forward the 99306 should always be billed under [the physician's] npi and group npi as i am the one who is doing the initial hps 99306 and 99497". Rule version 2026-11-10.6 (live 22:46 UTC) enters every 99306 and the 99497 billed with it under the physician and the group from the next feed import. Past claims are not reopened and not listed as work: the owner did not ask for corrections ("it looks like the initial 99306 billing under arnpo has been fixed mostly for 2026"). The monthly clinician check counts, and does not list, initial visits entered under the physician by this rule; the feed report names each one.
- History: 982 live initial visits under the nurse practitioner's code (946 x 99306, 36 x 99305): 2022 48 (from July), 2023 143, 2024 522, 2025 224, 2026 45. The pattern starts in July 2023; April 2024-May 2025, 610 of 663 initial visits (92%) are under her code; June 2025-November 9, 2026, 422 are under the physician's code and 99 under hers. Charged $249,340; insurance payments posted $88,061 (Medicare Part B $29,641). Medicare, Capital Health Plan, Humana and WellCare allowed her 85% of the physician amount. A billing line shows the code a visit was entered under; only the visit note shows who saw the patient.
- Feed since 10/28: 19 initial visits; the feed names the nurse practitioner on 10 and the physician on 9. Under the rule they go out under the physician's number, which is right only if he personally did them; the best fix is at the source (who logs the visit in Claimocity).

### 6.4 Coverage, the insurance check and the never-billed feed visits
- The plan's "one charge in nine" (11.2%) is the share of feed dollars on charts the insurance check held (counted after the check ran; $23,534 of $211,062), not a share of all visits. Of the 73 holds, the look-up ran and found nothing usable on 38 ($15,737), was switched off on 17, returned an error on 7, and 11 were held for another reason before that step. Visits that arrived with no open plan on the chart: 138 of 1,037 in the first 13 feed batches (13.3% of visits; $29,286, 13.7% of dollars).
- Feed visits with no claim on 11/10: 122 ($26,373): 86 with a payer on the chart that were never sent ($19,405; 84 of them the never-billed visits below), 21 with no plan ($4,358), 15 moved to the patient balance ($2,610). These are unbilled charges, not a forecast of collections.
- Never billed, proven by two independent read-only reviews: 84 feed visits, 102 lines, $18,802, 39 charts, service dates 10/12-11/07. They were entered while the chart had no plan, so AdvancedMD kept an empty insurance-order list; the insurance check later skipped the save because the visit's order attribute already read "1", and logged success. 0 of 84 appeared in the Unbilled column across 458 scans; 0 of 5,228 billed visits have an empty list. 69 ($15,616) were released after the look-up added the chart's first plan; 15 ($3,186) were held and their plan came later. The fix (rule version 2026-11-10.7) passed three reviews, a fix round and a re-check ("deliver"); it went live on the billing branch at 01:20 UTC on November 11 (the ten billing self-tests run before delivery passed on the delivered version; an eleventh, not run then, failed on it because its own stand-in for the billing system was out of date - repaired, extended from 51 to 100 checks, independently checked, and all eleven pass on the live branch since 03:05 UTC on November 11; no fault was found in the fix for the cases the practice meets); it has not yet been seen on a live batch. The independent check named three weak spots in the visit-save helper: two older than the fix (a save sent when the visit's charges could not all be read; the admission date after the frequency reset) and one in the read-back the fix added (a false 'admission date lost' on a visit with no hospital code, which errs on the safe side). None is known to have caused harm: of 341 rebilled hospital visits with a second code in 2025-2026, 339 still carry their admission date. A guard for the first is being built and reviewed before the 84 visits are sent.
- The owner's answers (11/10, 15:15 UTC "yes to all your recommendations"; 15:18 UTC "i saw those patients"): the 71 visits whose payer only the look-up found go out after a coverage check dated to each service date; the chart with two plans by that check; the 13 face-sheet / feed-block / by-hand visits are sent; the nurse practitioner's visits entered under the physician are moved to her first (10); the two initial visits stay under the physician; a standing word lets a routine re-save such a visit once its plan lands, after clinician, admission-date and insurance-order read-backs, never on a billed visit. None is billed yet; version .7 is live since 01:20 UTC on November 11, and a billing session with write access to the billing system sends them, one pilot visit first.
- HOLD is a label in the insurance check's report, not an AdvancedMD state: 56 held visits on charts with a plan were billed anyway.
- Plans added by discovery alone: 56 in 13 batches without a person; one dental plan added by mistake. The owner (11/10): they may keep being added, only medical plans active on the date of service (that check came with version .7, live since November 11).
- Insurance Refresh Board: the coverage refresh stopped mid-September (passes by hand 9/5-9/8 and 9/23-9/24). 349 of 503 cards open; no routine works them; 147 cards on 138 charts had nothing left to bill or collect; 145 charts with money waiting hold $153,124 (101 seen in the last 30 days, $125,260). Cleanup 11/10 16:21 UTC on the owner's word: 136 cards closed, 7 moved to the owner's turn (6 where his own October note had no reply, 1 with a patient who has no chart number), 3 left open (money still owed on another chart of the card), 1 left open (a chart with no charges yet).
- Monthly coverage run: approved CHECK-ONLY (11/10): it changes no chart. About 40-70 paid checks a month, $10-$40 (cap 150 checks or $75 a run; discovery at most 25); a one-time catch-up at most about 450 checks, about $260 (estimates). Medicare does not allow checks not tied to real claims, so Medicare is checked only for patients being billed that month. Its build started on November 11 after version .7 went live (version .6 and the look-up savings went live on November 10).

### 6.5 The look-up vendor (Stedi)
- Usage billed at public prices (checked to the cent): September 5-30 $1,879.97; October $2,029.25. October: claim status 6,770 checks $889.50 (44%); Medicare-number look-ups 1,064 $783.50 (39%); insurance discovery 187 $237.00; eligibility checks 505 $113.25.
- October is a poor baseline: a one-time claim-status sweep (3,826 checks, 2,948 of them on 21 claims asked 31-164 times) ended November 2. Without it October is about $1,372-$1,619 at public prices. After the practice's own changes (plain Medicare checks with the number on the chart; one shared Medicare answer per patient per month; one claim-status check per claim per week) an October-size month is about $450-$975 (estimates). A $1,300 monthly commitment could cost more than paying as you go.
- The vendor's offer (October 30): "from almost $2k to just above $1.3k" a month on a custom plan; no rates, minimum, term or payment method stated. A reply went 11/10 12:30 UTC asking for per-transaction prices, any minimum and term, what happens to unused amounts, payment method, start date and the plain Medicare price; it states the expected volumes and asks for a new Slack invitation. Follow-up check 11/11.
- The practice's Medicare eligibility enrollment at the vendor is live for the group number, so Medicare can be checked with the number on the chart at $0.15 instead of $0.40-$1.00 for a look-up. The look-up savings (plain Medicare checks first, one shared answer, claim status by need with caps of 150 / $25 a run and 400 / $100 a month) passed three reviews and three fix rounds and went live on the billing branch at 23:44 UTC on November 10. Still open: the owner replaces his installed copy of the look-up skill with the new file billing sent him (a push does not change it); the first nightly run and the usage log are watched.
- Three effects of the claim-status change to put to the owner: a claim more than a year old gets no status check (kept, in line with his write-off rule of November 2); claims that stop being asked go to a hand-off list that needs a person, about 129 claims in an October-size month (estimate); claim status is switched off for TRICARE (80 unpaid visits, $4,226) until the vendor says whether an enrollment fixes it.

### 6.6 Medicare quality program (MIPS)
- 2025 performance year (payments in 2027), from the owner's CMS feedback download: physician scored as facility-based, final score 65.8053, adjustment -1.1034%; nurse practitioner 16.3057, -9%. Cost in 2027: about $4,800-$5,700 (physician) + $11,700-$12,200 (nurse practitioner) = about $16,500-$18,000.
- 2026 performance year (payments in 2028): the physician is not facility-based. Hospital share of his Medicare lines by October-September period: 74.5% (2022-23), 95.4%, 64.1%, 41.7% (2025-26); CMS's own flags: facility-based 2024 no, 2025 yes, 2026 no. With nothing submitted both are scored on cost alone: about -9% each, about $47,000-$54,000 on the 2026 projection of $567,280 (range $522,000-$597,000). The 9% is an estimate: it is 9% if each cost score is 62.5 or lower (the nurse practitioner's was 54.35 in 2025) and about 6.3% at a median cost score. The 10-point bonus for complex patients is the 2025 figure; the 2026 amount is not known.
- Registered 11/10: the group and both clinicians for the neurological option M0004 (the group was first registered for Value in Primary Care, M0005, and changed the same day). M0004 is in AdvancedMD's code list ("QUAL CARE NEUROLOGIC CND MVP"); 1124F is not. Estimate on that route: 66 + 3 x cost points (at least 69; 95 if cost is not scored), against at most 66 on the ordinary route with the one claims measure.
- Billing, rule version 2026-11-10.6 (live 22:46 UTC), from the next feed import: 1123F pilot (up to 3 no-charge lines, Medicare patients 65 and older, never hospital visits), then M0004 once per clinician after proof; a held visit's no-charge 1123F line is taken off automatically (the owner: "doesnt appear to have any significance whiever way to just deal with it"). The first import under the rule, at 00:40 UTC on November 11, 2026, created no visit, because all 60 of its visits were already in the billing system, so no line has been entered yet.
- What 1123F states: an advance care plan or a named decision-maker is documented in the patient's record. Asked on 11/10 whether that holds for every patient the practice follows, the owner answered "yes for all", so the statement on each claim is his, and CMS can ask for the record of any coded patient. Not checked against charts. A patient who declined needs 1124F (not in AdvancedMD's code list) and one with whom it was never discussed needs 1123F with modifier 8P: a person enters both, and the owner names those patients.
- The rule adds 1123F only to visits dated in 2026. From January 1, 2027 it adds none until the owner renews it, and in January the feed report says so at the top. His to settle for 2027: whether hospital visits are coded, whether charts where Medicare is the second payer are coded, and once per patient or once for each clinician. The code can switch itself off (for example when AdvancedMD keeps leaving the line off the claim, or a held visit's line cannot be taken off) and then stays off until the owner restarts it; from December 1 the feed report puts at its top any clinician with no M0004 line billed or waiting.
- For the 2026 score the number of 1123F lines does not matter: what matters is at least one counted line and M0004 once for each clinician, on claims processed by March 1, 2027. Attestation January 4-March 31, 2027, 8 pm Eastern: six entries (group and each clinician, under the option and under the ordinary route); the activity must have been running by October 3, 2026 (90 days in a row). Registration can be edited until November 30, 2026, 8 pm Eastern; 2027 registration April 1-November 30, 2027. The CMS sign-in password must be changed every 60 days.
- Reminders done 11/10 13:05 UTC: 34 calendar entries (20 timed, 14 all-day), 22 rows in the compliance sheet, 3 new Credentialing Board rows for the quality program (and 4 older board rows corrected at 13:10 UTC), one task email. Key date: Monday January 4, 2027 9:00 AM, attest the activity at qpp.cms.gov. Cigna follow-up moved to 12/07/2026. A 35th calendar entry was added at 00:19 UTC on November 11: Monday December 21, 2026, 9:00 AM, decide the 2027 quality-code rules. The compliance sheet is rebuilt by a weekly routine whose November 9 run did not finish: check on Monday November 16 that it kept the 22 rows and doubled nothing. The 2027 dates on the sheet are marked expected until CMS publishes them (the 2027 registration window, April 1 to November 30, is set by regulation).

### 6.7 AdvancedMD history in the practice database
- Schema `amd` (production branch): charts, charges, payments, payment_reasons, writeoffs, plus analysis views. History on file: 11,050 charts; 84,617 charge lines (68,727 live), 91,094 payment lines, 108,768 write-off lines; dates of service 2022 to November 2026; checked as an exact copy of the pull. Held out on purpose: patient names, full birth dates, street addresses, phone numbers, insurance member ids, Social Security numbers. The tables are pseudonymous, not anonymous: chart numbers can be tied to names through the practice's other data.
- Definitions corrected and applied 11/10 13:33 UTC (reviewed migration; 31 + 14 checks pass): "paid" renamed "settled" (payments plus write-offs, $10,042,860.47 across the history); 1,415 reason codes split; 5,534 placeholder 1900-01-01 dates made empty; unapplied payments now their own table (310 lines, 149 with money, $9,266.19); nursing-facility setting = the five named buildings. The old objects are kept as *_before_1110 until the owner says to remove them.
- Privacy leftovers for the owner: the preview copy of the database still holds 6 chart documents with ZIP code, city and marital status (a person decides whether to replace them); earlier versions of the chart-facts layer, which held ZIP code, city and marital status, may still be restorable from the database's own history for a while; the workbook of billed and paid lines given to the owner has rows that describe one patient, so it must be thinned before it leaves the practice; the pre-claim check's memory keeps Medicare numbers on Drive and in GitHub's cache.
- Pull state: complete. Transaction history, chart facts and charge detail are loaded for all 11,050 charts. The charge-detail pull stopped at 228 charts at the two-hour background limit, continued in two-hour pieces on the owner's word (11/10) and finished at 01:08 UTC on November 11, when the database refresh was run: 68,727 charge-detail rows on the 5,416 charts that have charges, and 168,630 billing-event rows.
- Caveats: posted payments for 2022-2025 (all payers) are a floor: 12,821 charge lines with $1,910,279.88 of fees were closed in May 2026 as "paid, not posted" with no payment line, so up to about $1.0 million (27%) more may have been received than the postings show (posted $284,326 / $1,088,727 / $840,272 / $770,108 by year of service 2022-2025; 2022 is a part year). Collections by year must come from the bank or the books, or be labelled "posted payments". Read money by year of service: the payment date in AdvancedMD is the day of entry (all payers 2025 by payment date = $2,812.68).
- Medicare Part B posted, by year of service: physician 2024 $202,965, 2025 $285,518, 2026 to date $322,961.05; nurse practitioner 2024 $133,178, 2025 $104,925, 2026 to date $104,072.51. The 2024 and 2025 totals may be understated: 959 Medicare charges were closed in May 2026 as "paid, not posted" (up to +3.5% / +4.0% physician, +17.8% / +17.8% nurse practitioner). 2026 full-year projection for both together $567,280 (range $522k-$597k; the method missed by up to 9% on earlier years): $437,204 / $130,076 as entered, or $428,057 / $140,097 if the 165 October lines the feed gives to the nurse practitioner are counted under her. Twelve months November 2025-October 2026: $508,701.26 posted (physician $383,252.92, nurse practitioner $125,448.34), about $540k-$550k once October is paid. Railroad Medicare paid $718.76 in 2026 ($3,764 open).
- The valuation takes revenue and collections from the accountant's books (twelve months to September 30, 2026), not from AdvancedMD postings, so the floor caveat does not change it.

### 6.8 Credentialing corrections (checked by the reminders challenger, 11/10)
- The physician's Florida Medicaid provider agreement expires December 27, 2026; file by November 13 (the plan's work item carries that date, and the board row was set to it on 11/10); December 1 is the last-call reminder on the calendar. (The facts sheet calls this "the group's" renewal; the agency letter quoted on the board, the sheet and the 10/5 task email is for the physician's individual Medicaid ID. The group's own agreement date is not on file.)
- The nurse practitioner's Florida Medicaid enrollment is a NEW application, not a renewal; it was returned with three faults.
- The UnitedHealthcare directory attestation is not overdue (done August 28, next about November 26).
- TRICARE East is approved (electronic claims October 9, remittances October 5); TRICARE For Life is the one still rejected.
- Railroad Medicare is paying ($718.76 in 2026, $3,764 open): the plan's earlier "not enrolled" looks wrong for the group and the physician. Whether the nurse practitioner has a Railroad Medicare number is not known; the question for Palmetto GBA is on the compliance sheet.
- Nearer dated duties than the Medicaid expiry (they are duties, not expirations): the Veterans Affairs payment portal account lapses about November 22 unless someone signs in (estimated); the UnitedHealthcare directory attestation is next due about November 26; the physician's board-certification yearly assessment is due November 30, 2026, and it is not known whether it is done.

