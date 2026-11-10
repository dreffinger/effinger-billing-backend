# R2 - How small independent US physician practices are valued and sold

Prepared 2026-11-10 for a valuation model and a "maximize sale value" learning module. Subject profile: one-physician (DO) geriatrics / facility-based primary care practice with one nurse practitioner, Tallahassee, Florida; government-payer heavy; no real estate; some term debt.

**This is education, not an appraisal, fair-market-value opinion, tax advice or legal advice.** No patient data was sought or used.

**How to read the tags.** [V] = figure or wording read on the source page this session. [S] = read on a secondary page that quotes the primary source. [U] = seen only in a search-result extract or commonly quoted; treat as unverified. Bracketed numbers are the URLs in section 10.

**Access note.** The session's page-fetch tool could not resolve any host, so pages were opened with a plain HTTP client through the session proxy. Sites that refuse automated clients were not worked around; they are listed in section 9.

## 1. Valuation approaches and standards of value

| Approach | What it does | When used for physician practices | Sources |
|---|---|---|---|
| Income (discounted cash flow, capitalization of earnings) | Present value of cash flow left after market-level physician pay | Preferred for operating practices, but only if earnings remain after post-sale compensation | Coker 2017 [37]; VMG Health 2024 [18]; ECG 2023 [50] [V] |
| Market (guideline transactions) | Multiple of EBITDA, seller's discretionary earnings (SDE) or revenue from comparable sales | Cross-check; true comparables are scarce; EBITDA is measured after the post-transaction pay structure | Coker 2017 [37]; VMG 2024 [18]; Medical Economics 2024 [80] [V] |
| Asset / cost | Tangible assets plus identifiable intangibles (records, trained workforce, EMR) less liabilities | Default when post-sale pay equals or exceeds historical pay; "not uncommon" for practices | VMG 2024 [18]; Coker 2017 [37]; ECG 2023 [50] [V] |

**Standards of value**

- **Fair market value (FMV).** Under the Stark regulations: "the value in an arm's-length transaction, consistent with the general market value"; for an asset, the price from bona fide bargaining between well-informed parties "not otherwise in a position to generate business for each other" (42 CFR 411.351, eCFR as of 2026-10-01) [42] [V]. Buyer-specific synergies (downstream referrals, hospital rates, cost savings) cannot be counted (Coker 2017 [37]) [V].
- **Investment value.** Value to one particular buyer, including its synergies. Non-health-system buyers "are not required to follow" FMV standards and can outbid (ECG 2023 [50]); the Anti-Kickback Statute is "usually not implicated" in equity-fund deals (Schultz, Medical Economics 2023 [81]) [V].

**Why hospitals are capped at FMV and commercial reasonableness**

- Stark "isolated transactions" exception, 42 CFR 411.357(f): a one-time practice sale must be consistent with FMV, must not reflect the volume or value of referrals, and must be commercially reasonable even if the physician made no referrals [43] [V].
- Anti-Kickback safe harbor, 42 CFR 1001.952(e): a sale to a hospital is protected only if the seller will not be able to refer afterwards and the practice is in a shortage area [64] [V]. The usual "sell and stay" deal is therefore outside the safe harbor and rests on FMV.
- PYA: paying above FMV "could result in penalties or sanctions under the Stark law and/or Anti-Kickback Statute" [91] [V].

**Effect on price.** The hospital must also pay FMV compensation after closing. If that equals historical take-home, the income approach yields nothing and price falls to assets: "the value of the practice will be paid via ongoing compensation" (Coker 2017 [37]); "We didn't buy any goodwill, just tangible assets" (Physicians Practice 2008 [85]); hospitals "are not very competitive on valuations" (Baker, Medical Economics 2026 [79]) [V].

## 2. Normalizing earnings

**Step 1 - replace owner pay with market-rate compensation.**

| Source (report year, data year, statistic) | Geriatrics | Internal medicine | Family medicine | Nurse practitioner | Status |
|---|---|---|---|---|---|
| AMGA 2026, 2025 data, median | NOT FOUND (not in public tables) | $361,426 | $342,411 | $149,178 (primary care) | Primary [29] [V] |
| MGMA 2026, 2025 data, median | NOT FOUND (paywalled) | Primary care physicians as a group: $314,404 (non-production plans) to $345,852 (production plans) | same group | Dollars not public; primary care NP +4.79% in a year | Primary [11] [V] |
| Doximity 2026, 2025 data, average | $304,411 | $339,274 | $325,040 | n/a | Primary [40] [V] |
| Doximity 2025, 2024 data, average | $291,968 | $326,116 | $318,959 | n/a | Primary [39] [V] |
| Medscape 2026, 2025 data, average | not listed | $307,000 | $288,000 | n/a | Secondary: AOA "The DO", July 2026 [14] [S] |
| BLS OEWS, May 2025, median wage | no category | $256,560 (Florida $222,600) | $244,180 (Florida $227,700) | $132,300 (Florida $129,510; Tallahassee metro $117,880) | Primary, BLS data API [97] [V] |

Cautions: Doximity and Medscape are self-reported averages; BLS covers employee wages only (no owner profit, no benefits). Survey medians are not automatically FMV (PYA 2025 [90]) [V].

**Step 2 - load the salary.** Employer payroll tax: 6.2% Social Security on wages up to $184,500 (2026) plus 1.45% Medicare with no cap (IRS Topic 751, reviewed November 2026 [75]) [V]. Benefits load: NOT FOUND in an authoritative public source; "20-30% of compensation" is commonly quoted [U]. Model actual plan costs.

**Step 3 - adjustments.**

| Adjustment | Direction | Source |
|---|---|---|
| Owner pay above or below market | Add back excess; deduct shortfall | VMG 2024 [18]; PYA 2026 [89] |
| Above-market rent to a related party; family members on payroll at high pay | Add back excess | PYA 2026 [89] |
| Discretionary personal costs (auto, meals, travel) | Add back if documented | PYA 2026 [89] |
| One-time legal settlement and other non-recurring costs | Add back | PYA 2026 [89]; VMG 2024 [17] |
| Non-recurring revenue (relief funds, one-off or retroactive payments) | Remove | Weaver 2021 [22]; VMG 2024 [17] |
| Cash-to-accrual conversion | Either way | VMG 2024 [17]; Weaver 2021 [22] |
| Pro forma items (new-provider ramp, renegotiated contracts) | Heavily scrutinized | VMG 2024 [17]; Blann and Patel 2023 [77] |

All [V]. Buyers now test add-backs harder than in 2021 [77].

## 3. Observed multiples

SDE multiples apply to earnings before any owner salary. EBITDA multiples apply after a market-rate physician salary. They are not interchangeable.

| Metric | Band | Figure | Source, date | Status |
|---|---|---|---|---|
| EBITDA | Small primary care (revenue under $5M) | 3x-6x | Scope Research, May 2025 [92] | V |
| EBITDA | Mid-sized groups (revenue $5-50M) | 5x-10x | same | V |
| EBITDA | Large, value-based or tech-enabled platforms | 10x-20x | same | V |
| EBITDA | Private-equity purchases generally | 6x-10x (also "six- to 12-times"); aggregated resale 10x-16x | Schultz, Medical Economics, Nov 2023 [81] | V (opinion, no dataset) |
| EBITDA | Primary care platform vs add-on | 8x-12x vs 3x-6x | FOCUS Investment Banking, quoted by Iconic, 2026 [6] | S |
| EBITDA | Under $1M EBITDA | 5x-7x (FOCUS) vs 3x-4x (Acquisition Stars) | search extracts | U; sources disagree |
| EBITDA | All industries, deals of $2-5M / $5-50M | 4.0x / 5.8x | IBBA Market Pulse, Q2 2026 [72] | V (read from chart) |
| SDE | Medical practices sold on BizBuySell, 2021-2025 | Median 2.05x (quartiles 1.46x-2.94x) | BizBuySell, quoted by Iconic [6] | S |
| SDE | One-to-four-provider primary care clinics listed for sale | 1.5x-3.1x | Scope Research, May 2025 [92] | V (asking prices) |
| SDE | All industries, deals under $500K / $500K-1M / $1-2M | 2.0x / 2.8x / 3.1x | IBBA Market Pulse, Q2 2026 [72] | V |
| Revenue | BizBuySell sold medical practices | Median 0.62x (0.42x-0.91x) | quoted by Iconic [6] | S |
| Revenue | Small primary care listings | 0.7x-1.15x (25th-75th percentile) | Scope Research 2025 [92] | V (asking prices) |
| Revenue, EBITDA | Illustrative small pediatric practice | 0.65x revenue; about 2x EBITDA | Venette, Medical Economics, Sept 2024 [80] | V (illustration) |
| Any | DealStats / BVR physician offices | NOT FOUND (subscription; site blocked) | | |

**Value-based, payer-owned and private-equity buyers, 2023-2026**

| Date | Event | Source |
|---|---|---|
| Feb 2023 | More than 35 practice deals at 10x EBITDA or higher in five years (12 primary care, none bought by health systems); non-system buyers "might pay up to $12,000 per Medicare Advantage life" | ECG [50] [V] |
| Apr 2023 | Private multiples down "one to two-plus turns of EBITDA" | Blann (DC Advisory) and Patel, Medical Economics [77] [V] |
| May 2023 | CVS buys Oak Street Health: $39 per share, enterprise value about $10.6B | CVS [38] [V] |
| Feb-Jun 2024 | Cano Health (2021 SPAC at $4.4B) enters Chapter 11; exits with 80 Florida clinics vs 172 centers at end-2022 | MedCity News [7]; Healthcare Dive [68] [V] |
| Mar 2024 | Walgreens records $5.8B VillageMD goodwill impairment; 160 clinic closures planned | Healthcare Dive [70] [V] |
| Nov 2024-Feb 2025 | CareMax (2021 SPAC, $614M) bankrupt; clinics sold for $35M cash plus $65M buyer equity; shareholders get nothing | VMG Health [16]; Healthcare Dive [69] [V] |
| Jan 2025 | Private-equity multiples "not currently at all-time highs" but "still robust" | Foley [61] [V] |
| Sep 2025 | Privia buys Evolent's value-based primary care unit for up to $113M on about $10M adjusted EBITDA (roughly 10x-11x, my arithmetic) | HIT Consultant [4] [V] |
| Oct 2025 | CVS books goodwill impairment of more than $5.7B tied to Oak Street; closures and slower openings | HCI Innovation Group [67] [V] |
| Feb 2026 | Humana's CenterWell completes MaxHealth purchase (82 Florida clinics); price undisclosed, about $1B reported by Bloomberg [U] | Humana [9] [V] |
| Q1 2026 | MUSC buys Palmetto Primary Care Physicians for $111M; valuations described as a "return to normalcy" after 2020-2022 peaks | Bass Berry [32] [V] |
| Q3 2026 | Practice deal activity "modestly declined"; interest rates and state notice laws weigh on valuations | Bass Berry [33] [V] |

Also: new private-equity primary care platforms fell from 12 (2022) to 6 (2024) (Scope [92]) [V]; median healthcare-services multiple 11.5x in 2025 vs 14.5x in 2024 (FOCUS, via Iconic [6]) [S].

Reading: risk-bearing senior clinics commanded peak prices in 2021 to early 2023, cooled sharply in 2024-2025, and trade selectively in 2026. Nothing found shows a return to 2021-2022 pricing.

**What a one-physician practice typically sells for**

- To a hospital: usually tangible assets, with the rest delivered through the employment contract [37][18][85].
- To another physician or internal successor: roughly 1.5x-3x SDE or 0.4x-0.9x revenue on marketplace data [6][92]; partner buyouts are "often small and based on accounts receivable, usually paid over several years" (Medical Economics 2026 [79]) [V].
- Why many sell for little more than assets plus receivables: (1) after a replacement physician is paid a market salary, little EBITDA remains [37][18][50]; (2) goodwill is personal and leaves with the physician [88][86]; (3) hospital buyers cannot pay for referral value [43][64]; (4) receivables normally stay with the seller [10][85].

**Planning range for this profile (analyst synthesis, not an appraisal).** About 2x-4x normalized EBITDA: the lower half of the verified 3x-6x small-practice band, taken down one turn for single-physician concentration, fee-for-service government payers and facility relationships that are not owned. Cross-check at about 1.5x-2.5x SDE (owner-operator successor) and 0.4x-0.9x revenue. Treat 5x-6x as a stretch case needing a strategic post-acute or senior-care buyer, a multi-year physician commitment and documented, transferable relationships. Floor: tangible assets, with receivables collected by the seller. Where owner earnings are well above a market salary, the SDE method gives the higher answer; the gap is the personal-goodwill question that earn-outs exist to bridge.

## 4. Personal vs enterprise goodwill, key-person risk, post-acute practices

- "Two questions drive most conclusions: how much goodwill is personal to individual physicians rather than transferable to a buyer, and how owner compensation is normalized" (PYA 2026 [88]) [V].
- Buyers test revenue by provider, "high dependence on a small number of providers", dependence on few referral sources, and each physician's age and expected work life (PYA checklist [91]) [V].
- A published percentage "key-person discount" for practice sales: NOT FOUND. It appears as a lower multiple, an earn-out or holdback, and a required employment term.
- If the sole physician retires at closing, buyers resist paying goodwill tied to that physician; nurse practitioners who stay carry their own goodwill (Hernandez, Physicians Practice 2021 [86]) [V].
- Tax angle: personal goodwill can be sold by the individual at capital-gain rates only if the owner has no pre-existing non-compete or employment agreement with the practice entity, and then signs with the buyer. It is hard to support if the seller retires immediately (Weaver 2024 [24]; ECG 2023 [51]) [V].

**Post-acute / long-term-care ("SNFist") groups.** Published multiples or valuation guidance specific to these practices: NOT FOUND (searched SNFist and post-acute physician-group valuation and M&A; Scope, VMG, Provident). Closest evidence:

- Hospitalist analogy: facility-based practices have almost no tangible assets; the facility contract is the main asset, usually cannot be assigned without the facility's consent, and loyalty runs to the clinicians; such practices "may not have much monetary value" (The Hospitalist, 2008 [94]) [V, dated].
- Each nursing facility "must designate a physician to serve as medical director" (42 CFR 483.70(g) [49]) [V]. The stipend is the facility's arrangement with a physician, not a practice-owned annuity.
- Residents must be seen by a physician every 30 days for 90 days, then every 60 days; later skilled-facility visits may alternate with a nurse practitioner (42 CFR 483.30(c) [48]) [V]. A nurse practitioner alone cannot carry all of this revenue.
- OIG nursing-facility guidance (20 Nov 2024) flags medical-director pay: FMV for documented services, unrelated to referrals (Hall Render 2025 [3]) [S]. Expect buyers to discount stipends without time records.
- Investor interest exists but prices are undisclosed: Curana Health formed in 2022 from three senior-care companies [12]; HCAP Partners backed Puzzle Healthcare (230 facilities, 15 states) in December 2025 [5] [V].

## 5. What raises or lowers the multiple

| Factor | Raises | Lowers | Source |
|---|---|---|---|
| Payer mix | Value-based or capitated revenue; attributed Medicare Advantage panel | "Heavy dependence on fee-for-service Medicare or Medicaid" | Scope 2025 [92] [V] |
| Provider concentration | Several producers; stable physician and NP mix | One physician produces most collections; short remaining work life | PYA [91]; Scope [92] [V] |
| Growth | Demonstrated organic growth, consistent results | Flat volume; "limited growth potential" | Blann and Patel 2023 [77]; Weaver [22] [V] |
| Recurring revenue | Shared savings and capitation seen as "predictable, recurring" | Premium for chronic care management specifically: NOT FOUND | Scope [92] [V] |
| Receivables quality | Clean aging; cash-to-accrual analysis ties out | Balances over 90 days; unresolved credit balances | PYA [91]; VMG [17] [V] |
| Coding and compliance | Independent audit; normal E/M distribution; signed notes | Outlier patterns; price "adjusted to account for the risk"; six-year lookback | Zupko, Physicians Practice 2019 [87]; Foley 2025 [61]; 42 CFR 401.305 [41] [V] |
| Processes, technology, management | Professionalized non-clinical functions; comparable period reporting | Books only good enough to file taxes | Blann and Patel [77]; Baker 2026 [79] [V] |
| Restrictive covenants | Enforceable seller covenant | Owner's own pre-existing non-compete defeats personal-goodwill treatment | Fla. Stat. 542.335 [57]; Weaver [24] [V] |
| Payer contracts | Assignable, or consents obtained early | Anti-assignment and change-of-control clauses; re-credentialing under a new tax ID | Search extract only [U] |

**Non-compete law, November 2026.**

- Federal: the FTC rule was struck down in August 2024; the FTC dropped its appeals on 5 September 2025 (APTA [30]) and removed the rule from the Code of Federal Regulations effective 12 February 2026 (91 FR 6507 [53]) [V]. The FTC now acts case by case and sent warning letters to healthcare employers [30].
- Florida CHOICE Act (effective 1 July 2025; covenants up to four years): a covered employee "does not include a person classified as a health care practitioner" (Fla. Stat. 542.43(3) [59]; Foley [62]) [V]. Physicians and nurse practitioners stay under s. 542.335: seller-of-practice covenants presumed reasonable up to 3 years and unreasonable beyond 7; employee covenants 6 months and 2 years [57] [V].
- Fla. Stat. 542.336 voids physician covenants where one entity employs every physician of a specialty in a county [58] [V].
- A federal bill introduced September 2026 would restrict physician non-competes; passage called doubtful (Bass Berry [33]) [V].

## 6. Deal mechanics

| Topic | High-level treatment | Source |
|---|---|---|
| Asset vs stock | "Most physician practice acquisitions are structured as asset purchases"; buyer gets stepped-up basis and avoids unknown liabilities; sellers prefer stock | PYA [91]; McGuireWoods 2013 [76] [V] |
| C corporation | Asset sale taxed twice (corporation, then shareholder) unless value is personal goodwill | Weaver 2024 [24] [V] |
| S corporation or PA taxed as S | One level of tax; built-in-gains tax if converted from C within 5 years | 26 USC 1374(d)(7) [65] [V] |
| Price allocation | Both sides file Form 8594: receivables Class III, equipment Class V, covenants and workforce Class VI, goodwill Class VII. Goodwill is capital gain to the seller and amortized over 15 years by the buyer | IRS [73]; Physicians Practice 2021 [86] [V] |
| Tax rates | Long-term capital gains 0%, 15% or 20%, plus possible net investment income tax. Cash-basis receivables are generally ordinary income (not verified against a primary source) | IRS Topic 409 [74] [V] |
| Cash and debt | "Most of the time, healthcare transactions occur on a cash-free, debt-free basis": seller keeps cash and repays term debt; debt-like items are deducted | VMG 2024 [17] [V] |
| Receivables and working capital | Small and hospital deals: receivables are "not an acquired asset"; seller collects. Larger deals: working-capital peg with dollar-for-dollar true-up. Cash-basis books omit receivables and payables, so both must be built | AOA [10]; PYA [91]; VMG [17] [V] |
| Earn-outs, seller notes | Bridge key-person risk; must not track referrals | No primary source opened [U] |
| Rollover equity | Price split between cash and equity in the buyer's management company, "up to 40%" in larger deals; settle forfeiture and repurchase terms at letter-of-intent stage | Foley 2025 [61] [V] |
| Compensation reset | Price and post-close pay move inversely; private-equity example of a 30% pay buy-down (75th to about 25th percentile); hospital pay should not be "significantly higher" than historical | VMG 2024 [18], 2018 [20]; PYA 2026 [89] [V] |
| Indemnity | Escrow; representation-and-warranty insurance in larger deals | Foley [61] [V] |
| Billing diligence | Code distribution by provider vs benchmarks; revenue by provider; aged receivables; payer mix; payer claims; credit balances and overpayments (return within 60 days of identification; six-year lookback); enrollment and credentialing files. Denial-rate benchmark: NOT FOUND | PYA [91]; Zupko [87]; 42 CFR 401.305 [41] [V] |
| Medicare enrollment | Billing privileges cannot be sold (42 CFR 424.550(a)). Ownership change reported within 30 days (424.516(d)). A change that also changes the tax ID "requires... a new enrollment application" (424.550(c)). Billing starts on the later of filing date or first service, with a 30-day look-back (424.520(d), 424.521), so file before closing. Reassignments now go on CMS-855I; CMS-855R was discontinued in November 2023 | [47][44][45][46][34] [V] |
| Florida Medicaid | Seller notice and buyer application at least 60 days before a change of ownership, or both are jointly liable for overpayments | Fla. Stat. 409.907(6) [55] [V] |
| Florida ownership | Buyers not wholly owned by licensed practitioners need a health care clinic licence or an exemption | Fla. Stat. 400.9905(4) [54] [V] |

Contractor and payer processing times: NOT FOUND (not checked).

## 7. Pre-sale timeline and plausible buyers

| Months before closing | Work | Basis |
|---|---|---|
| 36-24 | Monthly, accrual-capable financials and KPIs; independent coding audit and refunds; written, FMV-supported medical-director agreements with time records; shift volume to the nurse practitioner or a second clinician | Baker 2026 [79]; Zupko [87]; Hall Render [3] |
| 24-12 | Entity and tax review (built-in gains, personal goodwill; no owner non-compete with own entity); staff agreements; payer-contract and enrollment inventory; clean receivables and credit balances | Weaver [24]; ECG [51] |
| 12-6 | Sell-side quality of earnings; advisers; approach several buyer types; letter of intent | VMG [17]; Foley [61]; Blann and Patel [77] |
| 6-0 | Diligence; Medicaid 60-day notice; Medicare filings; payer consents; facility and patient notices; debt payoff | [55][47][10] |
| After closing (12-36) | Employment or transition term; earn-out; receivables run-off | Weaver [24]; Coker [37] |

Baker frames succession on a three-to-five-year horizon [79] [V]; "two to three years" appears in search extracts [U].

| Buyer type (examples; none confirmed as an active acquirer in Tallahassee) | Valuation logic | Likely form of value |
|---|---|---|
| Health system or hospital-employed group, e.g. TMH Physician Partners (50+ clinics, 500+ providers in northwest Florida [96] [V]); HCA Florida Capital Hospital [U] | FMV only; cost approach unless pay is reduced | Asset price plus employment contract |
| Local independent group or successor physician | SDE or revenue multiple, limited by loan coverage; receivables-based buy-ins | Modest cash, seller note, transition employment |
| The nurse practitioner | Same logic. Florida permits autonomous practice only in primary care after 3,000 supervised hours (Fla. Stat. 464.0123 [56] [V]); nursing-facility rules still require a physician [48] | Seller-financed, phased |
| Post-acute and senior-living physician groups, e.g. TeamHealth [93], Sound Physicians [13], Curana Health [2], Theoria Medical [95], Bluestone (lists Florida [1]) | Buy clinician capacity and facility census; EBITDA after their pay model; retention is the asset | Small upfront amount, retention or earn-out, employment |
| Value-based senior-care groups (Humana CenterWell and others; Tallahassee presence not verified) | Attributed Medicare Advantage lives and risk margin; facility-based fee-for-service panels may not fit | Lives-based price or employment |
| Private-equity add-on through a platform | 3x-6x add-on band [92][6]; rollover; pay reduction | Cash plus rollover; minimum size thresholds likely [U] |

If a buyer owns or manages facilities to which the physician admits, kickback risk rises and FMV discipline applies again (analyst inference from [64][3]).

## 8. Worked template (placeholders only)

Symbols: R revenue; S earnings before owner compensation, accrual-adjusted; A add-backs; N non-recurring revenue; C market-rate physician compensation; t employer payroll tax; b benefits; m EBITDA multiple; s SDE multiple; r revenue multiple; K cash; D debt and debt-like items; W closing working capital; Wp agreed peg.

1. Normalized owner earnings: S' = S + A - N
2. Replacement cost of the owner: C' = C + t + b
3. Normalized EBITDA: E = S' - C'
4. Enterprise value: EV = E x m
5. Cross-checks: EV_s = S' x s and EV_r = R x r
6. Equity value: EQ = EV + K - D + (W - Wp)
7. Asset sale with receivables retained: seller proceeds before tax = EV - D + collected receivables - run-off payables
8. Key-person structure: price = P0 (cash at close) + P1 (earn-out, weighted by probability and discounted) + rollover equity
9. Sensitivity: each 1 unit change in C' moves EV by m units, so the compensation assumption is the largest lever [18].

## 9. Not found or not verified

- MGMA and AMGA geriatrics medians (paywalled); only Doximity's geriatrics average was verified.
- Benefits load as a percentage of physician pay. BLS employer-cost data not retrieved (API daily limit). BLS wage figures came from the BLS data API; "May 2025" is the standard reference period for that series.
- DealStats / BVR multiples; BizBuySell's own page (blocked; figures via Iconic and a search extract).
- FOCUS Investment Banking, Physician Growth Partners, BRG, Becker's, FTC.gov and BLS.gov pages (refused automated access). HealthCare Appraisers, Pinnacle and Provident: no usable figures found.
- OIG primary documents, including the 1992 OIG letter on paying for goodwill (oig.hhs.gov failed TLS verification; not bypassed).
- Multiples for SNFist or post-acute physician practices; a percentage key-person discount; a premium for chronic-care-management revenue; denial-rate benchmarks.
- MaxHealth price; buyer presence in Tallahassee beyond TMH; payer assignment terms; enrollment processing times; earn-out norms; tax character of receivables.

## 10. URLs opened this session

1. https://bluestonemd.com/
2. https://curanahealth.com/
3. https://hallrender.com/2025/03/04/post-acute-compliance-program-update-oig-recommendations-on-medical-director-agreements-and-roles/
4. https://hitconsultant.net/2025/09/26/evolent-health-sells-primary-care-business-to-privia-health-for-113m/
5. https://hitconsultant.net/2025/12/19/hcap-partners-invests-in-puzzle-healthcare-to-scale-post-acute-care-platform/
6. https://iconic.co/blog/medical-practice-valuation-multiples/
7. https://medcitynews.com/2024/02/bankruptcy-healthcare-primary-care-medicare-advantage/
8. https://midcapadvisors.com/insights/article-6-the-top-5-financial-metrics-that-determine-your-practices-value/
9. https://news.humana.com/press-room/press-releases/2026/centerwell-completes-acquisition-of-maxhealth-from-arsenal
10. https://osteopathic.org/practicing-medicine/business-of-medicine/selling-a-practice/
11. https://pages.mgma.com/rs/144-AMJ-639/images/2606-N36956D-2026%20Provider%20Compensation%20and%20Productivity%20Data%20Report%20MW%202.pdf?version=0
12. https://skillednursingnews.com/2022/05/allyalign-partnership-launches-curana-health-to-grow-value-based-care-in-skilled-nursing/
13. https://soundphysicians.com/
14. https://thedo.osteopathic.org/2026/07/what-physicians-are-getting-paid-in-2026/
15. https://vmghealth.com/articles/5-fundamentals-for-a-physician-practice-valuation
16. https://vmghealth.com/insights/blog/caremax-caught-in-stewards-storm-caremaxs-bankruptcy-reorganization/
17. https://vmghealth.com/insights/blog/five-key-analyses-for-healthcare-financial-due-diligence/
18. https://vmghealth.com/insights/blog/how-post-transaction-physician-compensation-structure-affects-fair-market-value-of-physician-practices/
19. https://vmghealth.com/insights/blog/physician-practice-strategy-the-private-equity-play/
20. https://vmghealth.com/insights/blog/valuing-a-practice-in-a-physician-practice-management-context-its-all-about-salary-sustainability-and-succession/
21. https://vmghealth.com/insights/industry-report/2026-healthcare-ma-report
22. https://weaver.com/resources/considerations-selling-physician-practices/
23. https://weaver.com/resources/lower-physician-practice-transaction-volume-may-impact-valuation/
24. https://weaver.com/resources/personal-goodwill-in-health-care-ma-transactions-unlocking-tax-benefits/
25. https://www.aboutamazon.com/news/company-news/one-medical-joins-amazon-to-make-it-easier-for-people-to-get-and-stay-healthier
26. https://www.aha.org/node/683812
27. https://www.amga.org/about-amga/newsroom/press-releases/2025/june/new-amga-survey-notes-significant-gains-in-physician-compensation
28. https://www.amga.org/about-amga/newsroom/press-releases/2026/june/provider-compensation-grows-as-health-systems-navigate-widening-gap-between-pay-and-reimbursement
29. https://www.amga.org/getmedia/6b7fc588-0aa3-4d42-a80c-5919fb7cbbbb/2026-comp-survey-charts-doc-final.pdf
30. https://www.apta.org/article/2025/10/08/ftc-drops-legal-appeals-abandons-noncompete-rule
31. https://www.bain.com/insights/new-models-of-value-creation-for-physician-groups-global-healthcare-private-equity-report-2026/
32. https://www.bassberry.com/news/healthcare-trends-transactions-q1-2026/
33. https://www.bassberry.com/news/healthcare-trends-transactions-q3-2026/
34. https://www.cms.gov/files/document/consolidated-cms-8551-bulletin.pdf
35. https://www.cms.gov/medicare/regulations-guidance/physician-self-referral
36. https://www.cokergroup.com/insights/the-private-equity-model-for-medical-group-transactions
37. https://www.cokergroup.com/insights/wheres-the-value-in-physician-practice-valuations
38. https://www.cvshealth.com/news/company-news/cvs-health-completes-acquisition-of-oak-street-health.html
39. https://www.doximity.com/reports/physician-compensation-report/2025
40. https://www.doximity.com/reports/physician-compensation-report/2026
41. https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=401&section=401.305
42. https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=411&section=411.351
43. https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=411&section=411.357
44. https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=424&section=424.516
45. https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=424&section=424.520
46. https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=424&section=424.521
47. https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=424&section=424.550
48. https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=483&section=483.30
49. https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=483&section=483.70
50. https://www.ecgmc.com/insights/article/2596/determining-the-true-value-of-primary-care-practices
51. https://www.ecgmc.com/insights/article/3016/unlocking-value-the-role-of-personal-goodwill-in-physician-practice-deals
52. https://www.federalregister.gov/api/v1/documents.json?conditions%5Bterm%5D=%22Non-Compete+Clause+Rule%22&conditions%5Bagencies%5D%5B%5D=federal-trade-commission&order=newest&per_page=10
53. https://www.federalregister.gov/api/v1/documents/2026-02866.json (document page: https://www.federalregister.gov/documents/2026/02/12/2026-02866/revision-of-the-negative-option-rule-withdrawal-of-the-cars-rule-removal-of-the-non-compete-rule-to)
54. https://www.flsenate.gov/Laws/Statutes/2025/400.9905
55. https://www.flsenate.gov/Laws/Statutes/2025/409.907
56. https://www.flsenate.gov/Laws/Statutes/2025/464.0123
57. https://www.flsenate.gov/Laws/Statutes/2025/542.335
58. https://www.flsenate.gov/Laws/Statutes/2025/542.336
59. https://www.flsenate.gov/Laws/Statutes/2025/542.43
60. https://www.flsenate.gov/Laws/Statutes/2025/542.45
61. https://www.foley.com/insights/publications/2025/01/physician-practice-private-equity-transactions-refresher/
62. https://www.foley.com/insights/publications/2025/07/florida-bucks-trend-enacts-new-employer-friendly-noncompete-statute/
63. https://www.govinfo.gov/content/pkg/CFR-2025-title42-vol2/xml/CFR-2025-title42-vol2-sec411-351.xml
64. https://www.govinfo.gov/content/pkg/CFR-2025-title42-vol5/xml/CFR-2025-title42-vol5-sec1001-952.xml
65. https://www.govinfo.gov/content/pkg/USCODE-2023-title26/html/USCODE-2023-title26-subtitleA-chap1-subchapS-partIII-sec1374.htm
66. https://www.harriswilliams.com/our-insights/hcls-value-based-healthcare-m&a-trends-demand-for-integrated-care
67. https://www.hcinnovationgroup.com/population-health-management/news/55327220/cvs-takes-57b-charge-on-lowered-healthcare-services-projections
68. https://www.healthcaredive.com/news/cano-health-emerges-bankruptcy-restructuring/720326/
69. https://www.healthcaredive.com/news/caremax-could-lay-off-530-people/735078/
70. https://www.healthcaredive.com/news/walgreens-villagemd-impairment-charge-second-quarter/711598/
71. https://www.ibba.org/wp-content/uploads/2026/02/market-pulse-highlights-q4-2025.pdf
72. https://www.ibba.org/wp-content/uploads/2026/08/mp-highlights-q2-2026.pdf
73. https://www.irs.gov/instructions/i8594
74. https://www.irs.gov/taxtopics/tc409
75. https://www.irs.gov/taxtopics/tc751
76. https://www.mcguirewoods.com/client-resources/alerts/2013/8/physician-practice-acquisitions-business-and-legal-considerations-structuring-for-tax-advantage
77. https://www.medicaleconomics.com/view/2023-robust-valuations-for-physician-practices-continue-despite-turbulent-market-conditions
78. https://www.medicaleconomics.com/view/how-far-in-advance-should-you-prepare-for-a-practice-sale
79. https://www.medicaleconomics.com/view/selling-a-medical-practice-planning-tips-for-physicians
80. https://www.medicaleconomics.com/view/valuing-your-medical-practice-key-approaches-and-considerations-for-ownership-transitions
81. https://www.medicaleconomics.com/view/why-do-medical-practices-sell-to-equity-funds-
82. https://www.mgma.com/2025-provider-compensation
83. https://www.mgma.com/2026-provider-compensation
84. https://www.mgma.com/press/physician-pay-and-productivity-are-moving-in-opposite-directions
85. https://www.physicianspractice.com/view/appraisals-whats-your-practice-worth
86. https://www.physicianspractice.com/view/goodwill-how-it-factors-into-a-medical-practice-sale
87. https://www.physicianspractice.com/view/selling-your-practice-clean-coding-first
88. https://www.pyapc.com/healthcare-physician-practices/
89. https://www.pyapc.com/insights/fmv-and-cr-considerations-for-hospitals-employing-physician-practice-owners/
90. https://www.pyapc.com/insights/physician-compensation-challenges-5-common-fair-market-value-mistakes-and-potential-solutions/
91. https://www.pyapc.com/wp-content/uploads/2021/03/Buyers-Side-Due-Diligence-Checklist-%E2%80%93-Hospital-Acquisitions-of-Physician-Practices.pdf
92. https://www.scoperesearch.co/post/primary-care-physician-practice-valuation-multiples-and-m-a-trends-2025
93. https://www.teamhealth.com/what-we-do/post-acute-care/
94. https://www.the-hospitalist.org/hospitalist/article/123659/value-your-practice/2/
95. https://www.theoriamedical.com/
96. https://www.tmh.org/tmh-physician-partners/about-tmh-physician-partners
97. https://api.bls.gov/publicAPI/v2/timeseries/data/ (BLS public data API; OEWS series OEUN000000000000029117113, OEUN000000000000029121513, OEUN000000000000029121613, OEUS120000000000029117113, OEUS120000000000029121513, OEUS120000000000029121613, OEUM004522000000029117113)

**Attempted, not opened (refused, missing or failed security check):** focusbankers.com; beckersasc.com; bls.gov; bizbuysell.com; bvresources.com; physiciangrowthpartners.com; thinkbrg.com; ftc.gov; ssa.gov; oig.hhs.gov; kevinmd.com; soferadvisors.com; mondaq.com; businesswire.com; sidley.com; benefitspro.com; healthcarefinancenews.com; eventuswh.com; two ebglaw.com pages, one schneiderdowns.com page, one aafp.org page and one sullivancotter.com PDF (not found).
