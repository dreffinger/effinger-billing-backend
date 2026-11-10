# R1 - Revenue cycle KPIs for US independent physician practices

Research date 2026-11-10. No patient data was sought or used.

**Reading guide.** Keys in [brackets] resolve to source name, year and URL in the last section. Confidence: **H** = I read the number or text on the source page; **M** = reputable secondary source; **L** = could not confirm. NOT FOUND = searched, nothing citable.

**Caveats on every benchmark**

1. HFMA MAP Keys define metrics but publish no targets [HFMA23]. The numbers often presented as HFMA or MGMA benchmarks (98% clean claims, A/R 30-40 days, A/R>90 under 10%) appear on those sites, as far as I could find, only in a Conifer Health Solutions white paper (mgma.com) and a Conifer-sponsored article (hfma.org) [CON-M][CON-H].
2. The familiar thresholds (A/R <35 / >50 days; denials <5% / >10%; net collection <95% "poor") appear in a 2012 AAPC article that names no data source [AAPC12]; AAFP repeats similar numbers on an undated page [AAFP].
3. MGMA DataDive medians are paywalled; only figures MGMA printed in free reports or articles are used.

## A. KPI table

| # | Metric | Definition (source) | Benchmarks: best / typical or observed / red flag | Traps | Conf |
|---|---|---|---|---|---|
| 1 | Clean claim rate | Claims passing scrubber edits untouched on first scrub ÷ claims accepted into the claims tool (HFMA CL-1) [HFMA23] | No HFMA target. "98%" is sponsored content citing Becker's [CON-H]; PwC hospital 85%+ (2021) [PWC21]; AdvancedMD guarantees 95% first-pass acceptance [AMD]. Observed mean acceptance 93-94% (billing companies, 2024) [HBMA24] | One name, three meanings: passed scrubber, accepted by payer, paid first pass | H; target is convention |
| 2 | First-pass resolution | Claims paid on first submission ÷ claims submitted (HBMA wording; no HFMA key) [HBMA24] | 90%+ target: source NOT FOUND. Observed means 85.7% office-based, 88.3% hospital-based (2024) [HBMA24] | "Not denied" is not "paid in full"; claim vs line level | H observed; L target |
| 3 | Initial denial rate | HFMA AR-5: claims with an actionable denial code ÷ claims remitted (count; excludes patient responsibility, duplicates) [HFMA23]. AAFP: denied dollars ÷ submitted dollars [AAFP]. MGMA: % claims denied on first submission | Best <5%, typical 5-10% [AAFP]; red flag >10% [AAPC12]. Observed: practices 8% (2022) [MGMA-OPS23], 7-8% over four years [MGMA-S26]; other datasets 12-17% (section B); professional claims 14.6%, vendor (2023-25) [TPS26] | Claims vs dollars vs lines; initial vs final; payer mix dominates | H |
| 4 | Final denial (write-off) rate | HFMA AR-6: net dollars written off as denials ÷ average monthly net patient service revenue (NPSR) [HFMA23] | PwC hospital target 1.5% of NPSR or less (2021) [PWC21]. Observed hospital median final denial rate 2.5% (2024), 2.7% (2025) [KOD26]; unreversed MA denials cost providers 7% of MA revenue (2019) [VAB25]. Practice benchmark NOT FOUND | Denials posted as "contractual" vanish from it | H; M Kodiak |
| 5 | Denial overturn / appeal success | No HFMA key. Variants: overturned ÷ appealed; ultimately paid ÷ all initial denials; dollars recovered ÷ dollars denied | PwC hospital target >80% [PWC21]. Observed: 54.3% (2022) and 68.6% (2023) of private-payer denials ultimately paid [PREM24][PREM25]; 57% of MA claim denials overturned (2019) [VAB25]; 42.1% (2025) [KOD26]; 80.7% of appealed MA prior-auth denials overturned, 11.5% appealed (2024) [KFF-MA]; 29% of contested dollars recovered, vendor [TPS26] | Denominator choice moves the answer two-fold | H; M Kodiak |
| 6 | Days in A/R | HFMA FM-1: net A/R ÷ average daily NPSR (3 months) [HFMA23]. MGMA: total A/R ÷ (gross or adjusted charges ÷ 365) [MGMA-G25]. AAFP/AAPC: (A/R minus credits) ÷ average daily gross charges | Best <35 [AAPC12] or 30-40 [AAFP]; typical 35-50 [AAPC12]; mean 42.3 (2024) [HBMA24]; red flag >50 [AAFP][AAPC12]. MGMA medians NOT FOUND | Gross-charge and net-revenue versions are not comparable; write-offs and agency transfers lower it | H |
| 7 | % A/R over 90 / over 120 | HFMA AR-1/AR-3: bucket ÷ total A/R, aged from date of service, debit balances only [HFMA23] | Over 120: best <12%, typical 12-25%, red flag >25% [AAPC12]; MGMA median 13.54%, multispecialty (2021) [MGMA-S21b]. Over 90: <10% [CON-H] vs observed mean 28.6% [HBMA24] | Re-aging when a balance moves to secondary; netting credits; MGMA excludes agency accounts | H |
| 8 | Net (adjusted) collection rate | MGMA: net FFS revenue ÷ adjusted FFS charges [MGMA-G25]. AAFP: payments net of credits ÷ charges net of approved contractual adjustments, 12 months [AAFP] | Best 99%+; typical 95-99%; red flag <95% [AAFP][AAPC12]. Observed means 84.9% office-based, 93.2% hospital-based [HBMA24] | Any write-off coded "contractual" inflates it; cohort vs calendar method; HFMA FM-2 (cash ÷ NPSR) is a different ratio | H |
| 9 | Gross collection rate | Net FFS revenue ÷ gross FFS charges [MGMA-G25] | No valid benchmark (set by fee schedule). Observed means 53.6% office, 64.7% hospital-based [HBMA24] | Trend within one practice only | H |
| 10 | Charge lag | HFMA PB-4: sum of (posting date minus service date) ÷ count of charge codes; CL-2 late charges = posted >3 days after service ÷ total [HFMA23]. MGMA: service date to claim posted for payment [MGMA-G25] | MGMA advice: notes closed in 72 h, charges posted in 2 days; sector 3-7 days [MGMA-S26]. Observed 3.8 days (2019), 7.75 days (2022) [MGMA-OPS23] | Service-to-entry vs service-to-claim | H |
| 11 | Days to payment | Payer receipt to payment (no standard definition found) | Medicare FFS: earliest day 14, due day 30 [CPM1]. MA "typically 30 to 45 days" vs 10-14 traditional Medicare (consultant quote) [MGMA-S24]. UnitedHealthcare: most within 15 days, up to 45 [UHC26]. Florida plans: act within 20 days [FS641]. Medicaid FFS: 90% within 30 days [CFR447] | Submission vs receipt date | H |
| 12 | Point-of-service / patient collection | HFMA PA-7: POS payments ÷ total self-pay cash [HFMA23]. MGMA: % of copays and of patient balances collected at time of service | 2024: 72% of copays, about 27% of other balances collected at time of service [MGMA-S26]; 34.46% of insured-patient balances collected (2024) [KOD25] | Three denominators | H |
| 13 | Bad debt rate | HFMA AR-7: bad-debt provision ÷ gross patient service revenue [HFMA23] | Hospital median 1.1% to 1.3% (2024-25) [KOD26]. Practice benchmark NOT FOUND | Provision vs actual write-offs | H; M Kodiak |
| 14 | Write-offs by reason | No standard. AAFP: separate contractual from non-contractual (timely filing, no authorization) [AAFP] | NOT FOUND | Depends on adjustment-code discipline | L |
| 15 | Cost to collect | HFMA FM-6: revenue cycle cost ÷ patient-service cash collected; excludes capital IT, rent [HFMA23] | PwC hospital 2% or less (2021) [PWC21]. Academic system: billing cost 14.5% of professional revenue, 20.49 USD and 13 minutes per primary care visit (2016-17) [TSE18]. Small-practice benchmark NOT FOUND | Whether physician time and front desk count | H |
| 16 | Clearinghouse rejection rate | Claims rejected before adjudication ÷ claims submitted (no HFMA key) | About 6-7% observed (complement of [HBMA24], my inference); AdvancedMD guarantee implies 5% or less [AMD] | Rejections never reach the remittance and do not prove timely filing [UHC26] | H / inferred |
| 17 | Credit balances / unapplied | HFMA AR-9: credit-balance dollars ÷ average daily NPSR [HFMA23] | PwC hospital 2 days or less [PWC21] | Medicare overpayments must be returned within 60 days of identification [CFR401] | H |
| 18 | Eligibility verification rate | HFMA PA-3: verified encounters ÷ registered encounters [HFMA23] | Vendor 98%+ [CON-M]. Electronic check 2.00 USD and 4 minutes vs manual 8.57 USD and 16 minutes (2023 data) [CAQH24] | "Verified" is locally defined | H |
| 19 | Prior authorization denial rate | HFMA PA-4/5: encounters authorized ÷ encounters requiring authorization [HFMA23]; payer view: requests denied ÷ requests | MA 7.7% denied, 4.2%-12.8% by insurer (2024) [KFF-MA]; 9% of ACA in-network denial reasons were missing authorization or referral (2024) [KFF-ACA] | Request vs claim level | H |
| 20 | Coding accuracy | Records coded correctly ÷ records audited (no standard formula found) | 95% is convention; an AAPC or CMS standard NOT FOUND. CMS improper payment rates FY2025: nursing home visits 12.7%, subsequent hospital visits 13.8%, initial hospital visits 12.0%, established office visits 5.3% [CERT25] | Undercoding counts too: underpayment rate 7.3% for 99231, 2.9% for 99308 [CERT25] | H CERT; L 95% |
| 21 | Billing staff productivity | Claims, accounts or encounters per FTE | Coding staff 41 encounters/day (2022) vs 75 (2019) [MGMA-OPS23]. Claims per billing FTE NOT FOUND | Role definitions differ | H / L |
| 22 | Credentialing turnaround | Application to billable date, per payer | Medicare online (PECOS), clean application: 95% in 15 days, 100% in 50; paper 30 / 65 [FCSO-ENR]. Commercial/MA norm and a Florida statutory deadline NOT FOUND | Clock starts at complete application | H / L |
| 23 | Underpayment / contract variance | Claims paid below contracted allowed ÷ claims paid | 4.9% of professional claims underpaid, on average 27% below allowed, vendor (2023-25) [TPS26]; Medicare FFS underpayment 0.2% of dollars [CERT25] | Florida: underpayment claims due within 12 months of payment [FS627] | H (vendor claim) |
| 24 | Timely-filing write-offs | Timely-filing write-off dollars ÷ net revenue (or ÷ denial dollars) | NOT FOUND. HFMA Q&A (2019): no industry standard known; one respondent "less than 1%" of denial dollars [HFMA-TF] | Target is zero | L |

## B. Hard external facts

| Fact | Finding | Source | Conf |
|---|---|---|---|
| Medicare FFS timely filing | 1 calendar year (12 months) after date of service | [CFR424]; [CPM1] s. 70 | H |
| Medicare payment floor | Clean electronic claims cannot be paid before the 14th day after receipt (paper: 29th day); pay or deny within 30 days, then interest | [CPM1] s. 80.2.1.1-2, Rev. 13725, April 2026 | H |
| Medicare Advantage | No federal filing window for contracted providers: contract governs. Non-contracted: 95% of clean claims paid in 30 days, the rest in 60. Federal MA standards supersede state law except licensing and solvency, so Florida prompt-pay rules do not reach MA claims (my reading). UnitedHealthcare 2026: 365 days for non-contracted MA providers; otherwise "refer to your Agreement" | [CFR422.520][CFR422.402][UHC26] | H |
| Commercial filing windows | Florida-regulated insurers and HMOs: 6 months from date of service; secondary within 90 days of the primary's determination; not waivable by contract. UnitedHealthcare commercial: at least 90 days participating, up to 180 non-participating | [FS627][FS641][UHC26] | H |
| Florida prompt pay | Electronic claims: acknowledge within 24 h after the next business day begins; pay, deny or contest within 20 days; provider has 35 days to answer information requests; pay or deny within 90 days; no action by 120 days = uncontestable obligation. Paper: 15 / 40 / 120 / 140 days. 12% simple interest on overdue claims. Disputes finalized in 60 days. Overpayment demands on MDs/DOs limited to 12 months | s. 627.6131 [FS627]; s. 641.3155 [FS641] (2026 statutes) | H |
| Florida Medicaid | Managed care plans must comply with s. 641.3155 [FS409.967]. Sunshine Health: 180 days; Medicare crossovers within 90 days of Medicare's determination, at most 3 years [SUN]. Aetna Better Health: 180 days participating, 365 non-participating (2019) [ABH]. FFS: federal rule requires a 12-month limit [CFR447]; state handbook not opened | as cited | H; M for FFS |
| CAQH Index | 2025 Index (2024 data, released Feb 2026): average medical provider cost per transaction 8.03 USD manual vs 2.65 electronic; transaction detail not public [CAQH25]. 2024 Index (2023 data), manual vs electronic: eligibility 8.57 / 2.00; prior authorization 12.88 / 5.38; claim submission 6.33 / 3.05; claim status 13.80 / 3.64; claim payment 4.99 / 3.16; remittance advice 5.67 / 2.95 [CAQH24] | as cited | H |
| Initial denial data | Experian survey (n=204, Aug 2026): 40% of providers report 10%+ of claims denied (41% 2025, 38% 2024, 31% 2022) [EXP26]. KFF, ACA plans 2024: 19% of in-network claims denied, not counting claims paid on resubmission [KFF-ACA]. KFF, MA prior authorization 2024: 7.7% denied [KFF-MA]. Premier (hospitals): about 15% of private-payer claims, 2022 and 2023 [PREM24][PREM25]. Kodiak: 11.81% in 2024 [KOD25]; a later report gives 11.4% for 2024 and 11.6% for 2025 [KOD26]. MGMA: 8% of practice claims (2022) [MGMA-OPS23]; poll, March 2024: 60% of leaders reported rising denials [MGMA-S24]. Peer-reviewed: MA 17% of initial claims (2019) [VAB25]; Medicaid FFS 17.8 points above Medicare FFS (2013-15) [GOT18] | as cited | H; M Kodiak 2025 |
| Cost to rework a denial | "25 USD": AAFP's FPM (2015) cites Graham T., MGMA Connexion 2014;14(2):37-38 for "approximately $25" [FPM15]. That MGMA page now returns 404; a search excerpt shows it credited unnamed "studies". MGMA Stat (2021, with Change Healthcare) says 25.20, uncited [MGMA-S21a]. Weak support. "118 USD": Change Healthcare's 2017 index of hospital claims from 724 hospitals, extrapolated; a vendor estimate of hospital appeal cost [CHC17]. Better documented: Premier hospital surveys 43.84 (2022) and 57.23 (2023) per denied claim [PREM24][PREM25] | as cited | H chain; M for 118 |
| "65% never reworked" | No study found. FPM 2015 says "more than 50 percent", citing the same 2014 article [FPM15]; per a search excerpt that article said "50% to 65%... according to industry sources". Later copies credit MGMA, HFMA, Change Healthcare or AMA interchangeably [TERA]. Measured data conflict with it: 57% of all MA claim denials were overturned [VAB25]; 54-69% of denied hospital claims were eventually paid [PREM24][PREM25]. Reliability: low | as cited | H chain; L original |

## C. Check of the vendor guide (CleanClaimRx "Road to Cash")

| Vendor statement | Verdict | Evidence |
|---|---|---|
| Clean claim rate 95%+ (at risk <90%) | PARTLY | Convention, not measurement. HFMA sets no target; "98%" is sponsored content; PwC used 85%+; billing companies average 93-94% [HFMA23][CON-H][PWC21][HBMA24] |
| Denial rate <5% (at risk >10%) | SUPPORT as convention | Matches AAFP and AAPC [AAFP][AAPC12]. Measured rates are 7-8% in practices and 12-17% elsewhere; 40% of providers exceed 10% [MGMA-S26][KOD25][VAB25][EXP26] |
| Days in A/R <35 (at risk >50) | SUPPORT | Identical to AAPC 2012; AAFP says under 50, ideally 30-40 [AAPC12][AAFP] |
| First-pass resolution 90%+ (at risk <75%) | UNVERIFIABLE | No authoritative benchmark; billing companies average 86-88% [HBMA24]. The 75% floor has no source |
| Net collection rate 98%+ (at risk <95%) | PARTLY | 95% floor supported; AAFP calls 95-99% average and 99% top [AAFP]. Self-reported means are 85-93% [HBMA24] |
| Overturn rate 60%+ (at risk <40%) | PARTLY | Published rates run 42% to 81% depending on denominator [KOD26][PREM24][VAB25][KFF-MA]. Nobody authoritative sets 60% |
| "Patient portals reduce transcription errors by up to 60%" | UNVERIFIABLE | No study found (PubMed and web searches) |
| "Clearinghouse scrubbing catches 80%+ of errors" | UNVERIFIABLE, doubtful | No source. About 6-7% of claims are rejected up front yet 12-14% are not paid first pass [HBMA24]; leading denial causes (eligibility, authorization, non-covered) are not format errors [MGMA-S21a][EXP26] |
| "Automation reduces posting time 70%" | PARTLY (direction only) | Best public measure: remittance advice 9 minutes manual vs 5 electronic, 44% less [CAQH24] |
| "Template-based appeals... increase overturn rates 30-40%" | UNVERIFIABLE | No study found |
| "Run eligibility 72 hours prior" | PARTLY | Common practice, not a standard; MGMA members describe checks 1-2 days ahead [MGMA-16] |
| "Claims billed within 48 hrs" | PARTLY | Aspirational. MGMA: notes in 72 h plus charges in 2 days; measured lag 7.75 days (2022); HFMA's late-charge line is 3 days [MGMA-S26][MGMA-OPS23][HFMA23] |

## D. What changes for a facility-based geriatric practice

Cited rules are verified; KPI consequences are my reasoning. KPI benchmarks specific to post-acute/long-term-care physician practices: NOT FOUND. The PALTmed (formerly AMDA) coding guide is paywalled and was not opened.

| KPI | Why it changes | How to read it |
|---|---|---|
| Eligibility verification | No appointments. Institutionalized beneficiaries may change MA elections at any time [CFR422.62]; dual-eligible beneficiaries have monthly elections since January 2025 [DUALSEP] | Re-verify per admission and every month start: plan, hospice election, QMB status |
| Clean claim, rejection, denial | When an MA enrollee elects hospice, Medicare FFS pays all claims from the election date; professional claims lacking GV or GW are denied [CPM11] s. 30.4, 40.1.3, 40.2. Physician services sit outside SNF consolidated billing [SNFCB] | Track wrong-payer and hospice-modifier denials separately |
| Denial rate target | MA denies 17% of initial claims [VAB25]; Medicaid FFS runs 17.8 points above Medicare FFS [GOT18] | Set targets by payer; blended "<5%" is unrealistic for this mix |
| Point-of-service collection | No front desk. QMB patients cannot be billed Medicare cost sharing [QMB25][FCSO-QMB]. Florida Medicaid pays no coinsurance when Medicare's payment already meets the Medicaid rate (s. 409.908(13)) [FS409.908]; 41 states have such "lesser of" rules for physicians [MACPAC25] | Not applicable; use statement yield on non-QMB balances |
| Net and gross collection, bad debt | Unpayable dual-eligible coinsurance is a legal limit, not a collection failure. NP services pay 85% of the physician fee schedule [CFR414.56] | Post as contractual; report by payer and clinician type |
| Days in A/R, aged A/R | Medicare FFS can pay on day 14 [CPM1]; Florida's 20-day rule binds Medicaid plans, not MA [FS409.967][CFR422.402] | Report by payer; show crossovers separately |
| Charge lag, missed charges | Charges come from census and rounding lists. SNF residents must be seen every 30 days for 90 days, then every 60 [CFR483.30] | Add census-to-charge reconciliation and a required-visit count |
| Coding accuracy | Core codes carry the highest E/M error rates, 12-14% vs 5.3% for office visits; about half is incorrect coding [CERT25] | Lead quality KPI; audit under- and over-coding |
| Timely filing | 12 months Medicare FFS, 180 days Florida Medicaid plans, contract-defined for MA [CPM1][SUN][UHC26]; a late-found plan switch eats the window | Age unbilled and wrong-payer claims weekly |
| Credentialing | Physician and NP each need Medicare, every MA plan and Medicaid (for crossovers) [FCSO-ENR][QMB25] | Days to billable, per payer |

## Not found or blocked

- Blocked here: businesswire.com, kodiaksolutions.io (used a syndicated copy and TechTarget), web.archive.org (2014 MGMA Connexion article), Becker's, Fierce Healthcare, humana.com; Florida Medicaid CMS-1500 handbook not located.
- Items with no citable source are marked NOT FOUND in the tables.

## Sources opened (key - name, year - URL)

Every URL below was opened and read in this session unless marked otherwise.

- [HFMA23] HFMA MAP Keys, 2023 edition - https://www.hfma.org/wp-content/uploads/2023/10/2023-Edition-MAP-Keys.pdf
- [CON-H] "7 KPIs providers should be tracking", sponsored by Conifer, hfma.org, 2023 (updated 2024) - https://www.hfma.org/revenue-cycle/kpis/7-kpis-providers-should-be-tracking/
- [CON-M] Conifer Health Solutions white paper hosted by MGMA, 2023 - https://www.mgma.com/getkaiasset/64027d0a-cff9-43c6-8b43-17d6588d2413/PRCM-KPIWhitePaper-Final-19April23.pdf
- [PWC21] PwC presentation to an HFMA chapter, Nov 2021 - https://www.hfma.org/wp-content/uploads/2023/07/Revenue-Cycle-Management-2021-mari.pdf
- [HFMA-TF] HFMA Ask the Experts, timely filing, 2019 (updated 2022) - https://www.hfma.org/revenue-cycle/kpis/ask-the-experts-timely-filing-measurement/
- [MGMA-G25] MGMA DataDive Definitions Glossary, 2025 - https://www.mgma.com/getkaiasset/8dd9987a-755a-4943-a5bc-98a5690ff99e/2505-D33056D-2025%20MGMA%20DataDive%20Definitions%20Glossary-Letter-V3-NM.pdf
- [MGMA-OPS23] MGMA Practice Operations data report, Aug 2023 (2022 data) - https://www.mgma.com/getkaiasset/ef6e357a-412b-41de-848f-a1b506b4261b/MGMA-PracticeOperations-DataReport-August2023-FINAL.pdf
- [MGMA-S26] MGMA Stat, 30 Jul 2026 - https://www.mgma.com/mgma-stat/days-in-a/r-holds-steady-for-most-practices-but-payer-pressure-persists-in-2026
- [MGMA-S24] MGMA Stat, 6 Mar 2024 - https://www.mgma.com/mgma-stat/strategic-improvements-in-your-rcm-to-reduce-your-practices-claim-denials
- [MGMA-S21a] MGMA Stat, 18 Mar 2021 - https://www.mgma.com/mgma-stats/6-keys-to-addressing-denials-in-your-medical-practice-s-revenue-cycle
- [MGMA-S21b] MGMA Stat, 11 Nov 2021 - https://www.mgma.com/mgma-stats/not-so-graceful-aging-half-of-practices-saw-days-in-a-r-increase-in-2021
- [MGMA-16] MGMA member-community excerpt, 2016 - https://www.mgma.com/articles/pre-verifying-eligibility-and-benefits
- MGMA author page confirming the 2014 article exists (article itself returns 404) - https://www.mgma.com/authors/tina-graham ; https://www.mgma.com/resources/revenue-cycle/you-might-be-losing-thousands-of-dollars-per-month
- MGMA pages opened, no figures used - https://www.mgma.com/2025-financials-and-operations ; https://www.mgma.com/articles/foundational-benchmarks-and-kpis-for-medical-practice-operations-in-2023 ; https://www.mgma.com/resources/operations-management/data-mine-the-secret-of-staffing-success
- [AAFP] AAFP "Managing practice finances", undated, read Nov 2026 - https://www.aafp.org/family-physician/practice-and-career/managing-your-practice/practice-finances.html
- [FPM15] "The Cure for Claims Denials", FPM 2015;22(2):7-10 - https://www.aafp.org/pubs/fpm/issues/2015/0300/p7.html
- [AAPC12] AAPC "Manage Four Key Revenue Cycle Metrics", 1 Dec 2012 - https://www.aapc.com/blog/24475-manage-four-key-revenue-cycle-metrics/
- [HBMA24] HBMA RCM Advisor, Q1 2024 survey - https://hbma.org/rcmadvisor/quarter-1-2024-volume-29-issue-1/data-science-committee-survey-results
- [CAQH24] 2024 CAQH Index (2023 data) - https://www.caqh.org/hubfs/Index/2024%20Index%20Report/CAQH_IndexReport_2024_FINAL.pdf
- [CAQH25] 2025 CAQH Index Executive Report and release note, Feb 2026 - https://index.caqh.org/hubfs/Index/CAQH_IndexReport_2025_Executive%20Report_v6.pdf ; https://www.caqh.org/blog/2025-caqh-index-shows-u.s.-healthcare-avoided-258-billion-and-accelerated-automation-interoperability-and-ai-adoption
- [EXP26] Experian Health State of Claims 2026, 28 Oct 2026 - https://www.experianplc.com/newsroom/press-releases/2026/experian-health-s-annual-state-of-claims-survey-finds-denials-re ; https://www.experian.com/blogs/healthcare/state-of-claims-2026-why-denials-remain-an-uphill-climb/ ; https://www.experian.com/blogs/healthcare/healthcare-claim-denials-statistics-state-of-claims-report
- [KFF-MA] KFF, 28 Jan 2026 (2024 data) - https://www.kff.org/medicare/medicare-advantage-insurers-made-nearly-53-million-prior-authorization-determinations-in-2024/
- [KFF-ACA] KFF, 24 Mar 2026 (2024 data) - https://www.kff.org/private-insurance/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/
- [PREM24] Premier, 21 Mar 2024 (2022 claims) - https://premierinc.com/newsroom/blog/trend-alert-private-payers-retain-profits-by-refusing-or-delaying-legitimate-medical-claims
- [PREM25] Premier, 24 Feb 2025 (2023 claims) - https://premierinc.com/newsroom/blog/claims-adjudication-costs-providers-25-7-billion
- [KOD25] Kodiak Solutions release, 21 May 2025, syndicated copy - https://markets.financialcontent.com/winslow/article/bizwire-2025-5-21-rate-of-initial-denials-of-medical-insurance-claims-continued-to-rise-in-2024-kodiak-solutions-proprietary-data-show
- [KOD26] TechTarget on Kodiak's 2026 report, 2 Apr 2026 (secondary) - https://www.techtarget.com/revcyclemanagement/news/366641065/Hospitals-lost-over-48B-from-claims-denials-uncollected-bills
- [TPS26] TriZetto Provider Solutions (Cognizant) 2026 report card, vendor - https://www.trizettoprovider.com/c/healthcare-payments-report-card ; https://www.trizettoprovider.com/resource-library/a-clean-claim-isnt-a-fully-paid-claim
- [CHC17] Healthcare Innovation on Change Healthcare's index, 26 Jun 2017 (secondary) - https://www.hcinnovationgroup.com/finance-revenue-cycle/news/13028823/an-estimated-262b-in-medical-claims-initially-denied-in-2016-analysis-shows
- [VAB25] Vabson, Hicks, Chernew, Health Affairs 2025;44(6):702-706; read as PubMed abstract, PMID 40456040 - https://doi.org/10.1377/hlthaff.2024.01485
- [GOT18] Gottlieb, Shapiro, Dunn, Health Affairs 2018;37(4):619-626; read as PubMed abstract, PMID 29608348 - https://doi.org/10.1377/hlthaff.2017.1325
- [TSE18] Tseng et al., JAMA 2018;319(7):691-697; read as PubMed abstract, PMID 29466590 - https://doi.org/10.1001/jama.2017.19148
- [CERT25] CMS 2025 Medicare FFS Supplemental Improper Payment Data (claims July 2023 - June 2024) - https://www.cms.gov/files/document/nov-2025-medicare-ffs-supplemental-improper-payment-data-2025922.pdf
- [CPM1] Medicare Claims Processing Manual ch. 1, Rev. 13725, Apr 2026 - https://www.cms.gov/regulations-and-guidance/guidance/manuals/downloads/clm104c01.pdf
- [CPM11] Medicare Claims Processing Manual ch. 11, Rev. 13190, Apr 2025 - https://www.cms.gov/regulations-and-guidance/guidance/manuals/downloads/clm104c11.pdf
- [QMB25] CMS MLN7936176, Sept 2025 - https://www.cms.gov/files/document/mln7936176-prohibition-billing-qualified-medicare-beneficiaries.pdf
- [SNFCB] CMS SNF consolidated billing page, read Nov 2026 - https://www.cms.gov/medicare/coding-billing/skilled-nursing-facility-snf-consolidated-billing
- [DUALSEP] CMS job aid, dual/LIS enrollment periods, Oct 2024 - https://www.cms.gov/files/document/duals-lissepsjobaid01012025.pdf
- CMS HETS page opened, nothing used - https://www.cms.gov/data-research/cms-information-technology/hipaa-eligibility-transaction-system
- [CFR424] 42 CFR 424.44, eCFR current text, read Nov 2026 - https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-42?part=424&section=424.44
- [CFR422.520] 42 CFR 422.520, eCFR current text, read Nov 2026 - https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-42?part=422&section=422.520
- [CFR422.402] 42 CFR 422.402, eCFR current text, read Nov 2026 - https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-42?part=422&section=422.402
- [CFR422.62] 42 CFR 422.62, eCFR current text, read Nov 2026 - https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-42?part=422&section=422.62
- [CFR414.56] 42 CFR 414.56, eCFR current text, read Nov 2026 - https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-42?part=414&section=414.56
- [CFR401] 42 CFR 401.305, eCFR current text, read Nov 2026 - https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-42?part=401&section=401.305
- [CFR447] 42 CFR 447.45, eCFR current text, read Nov 2026 - https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-42?part=447&section=447.45
- [CFR483.30] 42 CFR 483.30, eCFR current text, read Nov 2026 - https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-42?part=483&section=483.30
- [FS627] Florida Statutes 2026, s. 627.6131 - https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0600-0699/0627/Sections/0627.6131.html
- [FS641] s. 641.3155 - https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0600-0699/0641/Sections/0641.3155.html
- [FS409.967] s. 409.967 - https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0400-0499/0409/Sections/0409.967.html
- [FS409.908] s. 409.908 - https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0400-0499/0409/Sections/0409.908.html
- [MACPAC25] MACPAC Policy in Brief, Aug 2025 - https://www.macpac.gov/wp-content/uploads/2025/08/2025.08-Policy-in-Brief-State-Medicaid-Payment-Policies-for-Medicare-Cost-Sharing.pdf
- [UHC26] UnitedHealthcare 2026 Care Provider Administrative Guide - https://www.uhcprovider.com/content/dam/provider/docs/public/admin-guides/2026-UHC-Administrative-Guide.pdf (found via https://www.uhcprovider.com/en/admin-guides.html and https://www.uhcprovider.com/en/resource-library/news/2026/admin-guide-2026.html)
- [SUN] Sunshine Health LTC claims page, read Nov 2026 - https://www.sunshinehealth.com/providers/resources/electronic-transactions/ltc-claims-submission.html
- [ABH] Aetna Better Health of Florida timely filing sheet, 2019 - https://www.aetnabetterhealth.com/content/dam/aetna/medicaid/florida/provider/pdf/Appeals_and_Grievances%20Timely%20Filing%20_Website_Doc08.2019_2.pdf
- [FCSO-ENR] First Coast CMS-855 processing timeframes, 18 Feb 2026 - https://medicare.fcso.com/enrollment/cms-855-enrollment-application-processing-timeframes
- [FCSO-QMB] First Coast QMB billing prohibition, read Nov 2026 - https://medicare.fcso.com/billing/prohibition-billing-dually-eligible-individuals-enrolled-qualified-medicare-beneficiary-qmb
- [AMD] AdvancedMD claims scrubbing page, read Nov 2026 - https://www.advancedmd.com/medical-billing/software/claims-management/claims-scrubbing/
- [TERA] Teragonia blog tracing the 65% claim, 19 Aug 2026 (secondary) - https://teragonia.com/insights/four-claims-that-are-universally-cited-but-your-healthcare-model-cant-defend/
- Merits blog on the 25-118 USD range, Jul 2026 (secondary, used only as a cross-check) - https://meritsappeals.com/research/what-one-denial-costs
- Opened, not relied on: Physicians Practice staffing article, Mar 2026 - https://www.physicianspractice.com/view/how-many-staff-members-does-my-practice-actually-need- ; Humana documents for other states - https://assets.humana.com/is/content/humana/HMO%20D-SNP%20Provider%20Billing%20Guidepdf ; https://assets.humana.com/is/content/humana/2026%20Claims%20Quick%20Reference%20Guidepdf
- Opened but unusable (script-only page, 403/404 or connection refused): https://www.kodiaksolutions.io/internal/benchmarking_reports/march_2026_benchmarking_intelligence_report ; https://www.humana.com/provider/support/claims/addresses ; https://provider.humana.com/coverage-claims/claims-submissions ; https://www.beckershospitalreview.com/finance/denial-rework-costs-providers-roughly-118-per-claim-4-takeaways.html ; https://www.fiercehealthcare.com/finance/despite-better-cash-flow-providers-missed-out-more-revenue-2025-due-increased-payer-denials ; https://www.mgma.com/data-tools/accounts-receivable-dashboard ; https://www.mgma.com/articles/you-might-be-losing-thousands-of-dollars-per-month-in-unclean-claims ; https://www.molinahealthcare.com/-/media/Molina/PublicWebsite/PDF/Providers/fl/medicaid/Crossover-Claims-FINAL-111221 ; https://web.archive.org/web/20201128052711/https://www.mgma.com/resources/revenue-cycle/you-might-be-losing-thousands-of-dollars-per-month
