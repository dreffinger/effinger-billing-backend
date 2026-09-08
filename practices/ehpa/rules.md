# ehpa — Effinger Health PA: William's standing billing rules

- Medicare first, Medicaid / LTC second. Hospice patients: Medicare with modifier GV. A 9-digit AARP number is UHC Medicare Advantage (UNI20).
- PRIMARY claims more than 12 months from the date of service and unpaid are written off, any carrier — "no chance of it being resubmitted for actual payment" (9/7/2026).
- A SECONDARY / supplement balance is timely from the PRIMARY'S remit date, never the date of service — rebill it, never age it out (9/7/2026).
- Wrong-payer denials never stay on the patient balance. Medicaid crossover paying $0 on Medicare coinsurance = contractual write-off.
- Never rebill UHC (UNI20) or Florida Blue visits older than 5/1/2026 (unposted-ERA backlog). Never send a claim older than 12 months to Medicare.
- Frequency 1 (original claim) before every rebill; frequency 7 only with the payer's ICN from William.
- No group numbers on any insurance plan. No SSNs anywhere.
- Address placeholder when a chart has no street address: line 1 = HCA (hospital), SNF (nursing home), ALF (ALF / home visit); zip 32308-4486; use the pop-up's Edit address.
- Insurance lookup order: patient database -> AMD eligibility (free 271) -> Stedi -> facesheet -> William. If AMD eligibility is down, skip to Stedi.
- Florida Medicaid's 271 names the SMMC plan; a patient in "SMMC MMA Capitated — FLORIDA COMMUNITY CARE" (FLO99) or Humana / Sunshine / Simply MMA is billed to that plan, not Medicaid fee-for-service.
- One AMD login attempt per run. Every call learned from a DevTools paste is written to docs/captured_calls.md the same night; not in the registry = not captured, ask instead of guessing.
- Protected health information travels only to William (SendUserFile, the boards, Gmail to himself) — never into this repository, a skill, or a public page.
