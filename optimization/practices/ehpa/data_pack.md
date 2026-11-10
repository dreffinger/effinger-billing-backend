# EHPA practice data pack (aggregates only, no patient-level data)

Compiled 2026-11-10 from: the practice's Neon Postgres (`ehpa.*` views, read-only), the accountant's cash-basis financial statements in Drive (Lanigan & Associates; "not audited, reviewed, or compiled"), the billing repository (`practices/ehpa/*`, `README.md`), and the credentialing board copy. Dollar figures are as stated in those sources. Every number here is an aggregate; there are no names, dates of birth, member ids or chart-level rows. Treat it as confidential business information of the practice.

## 1. Profile

- Legal entity: Effinger Health, P.A. (files Form 1120-S, i.e. taxed as an S corporation). DBA North Florida Senior Care. Tallahassee, Florida. Group NPI 1629515325.
- Clinicians: William L. Effinger, DO (owner; family medicine, AOBFP board certified through 12/31/2030; NPI 1225327380) and one nurse practitioner (APRN; NPI 1235128869).
- Model: facility-based geriatrics / primary care. Sites seen in the charge feed (Sep 30 - Nov 7, 2026): one hospital (HCA Florida Capital Hospital, POS 21), five skilled nursing / nursing facilities (all billed as POS 31: Brynwood in Monticello, Aspire at Tallahassee, Centre Pointe, Westminster Bertrand, Oakes Southwood), and seven assisted living facilities (POS 13). A small office exists (rent and utilities about $58K a year). Tallahassee Memorial Hospital appears in historical notes but not in the current feed.
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
- By payer (11/9): Medicare fee-for-service $190,203 (55.5%); UnitedHealthcare $30,856; Florida Community Care (Medicaid long-term care plan; paper checks, portal-only eligibility) $26,640; Florida Blue $18,483; UnitedHealthcare Dual Complete $17,284; Humana $11,132; VA Community Care (Optum) $6,024; Sunshine $4,985; Capital Health Plan $4,603; Florida Medicaid $4,409; Cigna $4,364; Railroad Medicare $3,764 (practice is not credentialed; being written off); Tricare For Life $2,479; Tricare East $1,540 (nurse practitioner not credentialed); others small.
- Aging engine verdicts (2026-10-16): wait $205,605 (1,635 visits); correct and resend $65,431 (714 visits); write off $44,700 (876 visits, $31,088 of it over a year old).
- Weekly average of total open receivables: $272K (Oct 5), $301K, $281K, $305K, $323K, $340K (Nov 9): rising about 25% in five weeks while charge volume through the new feed ramped up.

### 3.2 Charges (Claimocity feed, entered into AdvancedMD; Sep 30 - Nov 7, 2026)
- October 2026: 775 entered encounters, $164,832 gross charges, 326 distinct patients, 24 days with service. Nov 1-7: 246 encounters, $44,897.
- By site, share of gross charges in the whole window ($211,062): hospital 37.8% ($79,886), skilled nursing / nursing facilities 42.6% ($89,825 incl. unlabeled), assisted living 19.3% ($40,693). Largest single sites: HCA Capital Hospital 37.8%, Brynwood 17.6%, Aspire 9.4%.
- By clinician: physician-owner 716 encounters / $162,198 (76.8% of charges); nurse practitioner 309 encounters / $48,864 (23.2%).
- October workload: physician 548 billed lines over 18 days (about 255 of them are monthly care-management lines, so roughly 16 face-to-face visits a day); nurse practitioner 227 encounters over 17 days (13.4 a day).
- Lead payer by charges: Medicare fee-for-service 55.5%; no payer recorded 11.2%; UnitedHealthcare 8.0%; Humana 5.6%; Capital Health Plan 5.0%; Florida Blue 3.8%; Florida Community Care 2.8%; Sunshine 2.7%; UHC Dual Complete 2.3%; VA 0.9%; Medicaid 0.8%.
- Charge lag (date of service to entry in AMD, October onward): median 3 days, 90th percentile 5 days for visits.
- Code counts (entered lines, whole window): 99233 x269; 99309 x260; 99487 x257; 99489 x213; 99232 x96; 99223 x70; 99497 x62; 99344 x31; 99306 x19; 99308 x12; 99239 x7; 99316 x3; 99498 x2. No 99231, 99221, 99222, 99304, 99305, 99307, 99310, 99238, 99315, and no established-patient home/residence codes (99347-99350) in this window (99349 does appear on earlier remittances).
- Level distribution inside each family: subsequent hospital care 99233 73.7% / 99232 26.3% / 99231 0%; initial hospital care 99223 100%; subsequent nursing facility care 99309 95.6% / 99308 4.4% / 99307 0% / 99310 0%; initial nursing facility care 99306 100% (19 visits, 10 of them billed under the nurse practitioner at POS 31); discharge day codes 100% the over-30-minute code (99239 x7, 99316 x3); assisted living 99344 (new patient) x31, 25 of them by the nurse practitioner.
- Advance care planning 99497 on 62 encounters (about 8% of face-to-face visits), usually on the same day as an admission or visit.
- Nursing facility visits per resident, October 2026 (charge feed, counted 2026-11-10): 218 visits to 135 residents, 1.61 each; 14 residents were seen four or more times.
- Place of service: every nursing-facility visit in the feed carries POS 31 (skilled nursing facility); POS 32 (nursing facility, long-term) is never used.
- The practice's charge amounts: 99233 $160; 99232 $111; 99223 $310; 99309 $130-141; 99308 $107; 99306 n/a alone; 99487 $206; 99487+99489 $315; 99344 $300; 99239 $163; 99316 $207.

### 3.3 Complex chronic care management (99487 / 99489)
- October 2026: 257 patients billed 99487, 213 of them also 99489 (83%). All under the physician-owner. Service date is batched (213 of 257 on one day; the practice's standing rule is that the claim is a monthly total dated at month end).
- Place of service on those lines: POS 31 x152, POS 13 x103, POS 21 x2.
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
- Nightly insurance cascade (9 nights to 11/9): $8,447 re-sent after coverage corrections. Insurance Refresh Board: 493 patient coverage cards, 342 still in work.

### 3.5 Treasury (bank deposits vs remittances, Aug 13 - Sep 11, 2026)
- $66,065 of payer deposits in 65 deposits plus $8,769 through the card terminal (12% of receipts; part of that is payer virtual cards, which carry about 3% processing cost), $884 in bank and processor fees.
- Findings logged: Medicare deposits with no matching electronic remittance ($12,902); UnitedHealthcare / Optum remittances arriving with no money landing (flagged critical); eight remittances failing auto-post (188 lines); six payers with zero deposits in the month; Florida Community Care pays by paper check.

### 3.6 Credentialing and enrollment (board copy, 42 items)
- Cigna terminated the practice effective 8/31/2026 after a missed recredentialing; later contact suggested the physician is still listed as participating, unresolved.
- Railroad Medicare: not enrolled; claims written off. Tricare East: nurse practitioner not credentialed and an EDI enrollment rejection. VA Community Care: portal registration pending and claims need authorization numbers. UnitedHealthcare directory attestation overdue. Sunshine/Centene required training overdue. Aetna ERA/EFT enrollment cancelled/rejected. Florida Medicaid: the physician's provider agreement renewal is due 2026-12-01 and the nurse practitioner's revalidation was returned incomplete. The nurse practitioner's NPPES record is stale and carries the wrong taxonomy. Hospital privileges reappointment has open items. Monthly OIG exclusion check is being run.

## 4. Things this pack cannot answer yet (data gaps)
- Net collection rate, contractual adjustments, and true first-pass denial rate by cohort: need AdvancedMD transaction history rolled up by month of service (payments, adjustments, write-offs by reason).
- Collections by payer and by service line for a full year (the Money Ledger payment totals were empty in the latest snapshot).
- How much of 2026 collections is one-time recovery of old receivables.
- Which nursing-facility residents are in a Medicare Part A skilled stay versus long-term residents (drives place of service 31 vs 32, care-management eligibility and visit rules).
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
| Initial nursing facility care | 99304 12.4% / 99305 39.1% / 99306 48.5% | 99306 100% (19; 10 under the nurse practitioner at POS 31). CMS data: the nurse practitioner billed 99306 at the facility rate 37 times in 2023 and 129 times in 2024 |
| Subsequent nursing facility care | 99307 5.1% / 99308 38.7% / 99309 48.8% / 99310 7.3% | 99307 0% / 99308 4.4% / 99309 95.6% / 99310 0% (Oct-Nov 2026 feed); CMS data for the nurse practitioner 2024: 99307 8.2% / 99308 57.9% / 99309 32.0% / 99310 1.9% |
| Nursing facility discharge day | 99315 27.8% / 99316 72.2% | 99316 100% (3) |
| Home or residence visit, established patient | 99347 7.0% / 99348 25.1% / 99349 50.1% / 99350 17.8% | none in the Oct-Nov 2026 feed; 99349 only in 2023-2024 CMS data |
| Home or residence visit, new patient | 99341 9.2% / 99342 24.7% / 99344 38.8% / 99345 27.3% | 99344 100% (31) |

Care management, national 2024: 99490 (non-complex, clinical staff) 6,919,114 services; 99491 (non-complex, clinician time) 283,868; 99487 (complex) 634,385. Complex care management is 8.1% of those three base codes nationally. This practice bills only the complex code: 257 patients in October 2026, and 1,717 (2019), 2,050 (2020), 1,793 (2021), 1,331 (2022) and 539 (2023) services of 99487 under the physician in the CMS data, then none in 2024. At 257 a month the practice would bill about 0.5% of all complex care management paid by Medicare fee-for-service nationally in 2024.

National average Medicare allowed amount in 2024, facility rate versus non-facility rate: 99487 $83.05 vs $126.28; 99489 $46.90 vs $67.71; 99490 $46.06 vs $59.99; 99439 $32.01 vs $46.33; 99309 $97.66 vs $95.24; 99308 $69.40 vs $67.97; 99306 $174.15 vs $171.79; 99497 $70.87 vs $75.69. For care-management codes the place of service on the claim changes the allowed amount by about a third; for nursing-facility visit codes it barely matters in 2024 data.

