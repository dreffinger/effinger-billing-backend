# Workflows

## The Claims Center pass

Four columns, cleared in order. Run `getclaimcenteroverview` before and after
every pass — but trust the list calls, not the counts (the overview is cached
and lags).

### 1. Charge Review
List with `getreviewcharges`. Apply the CCM / modifier-25 gate
(`docs/billing_rules.md`) — flag anything that needs a 25 rather than
bulk-approving. Approve a clean batch with `approvecharges`.

### 2. Claim Inspector
Re-list first (error ids change on every reinspection). For each error:
fix the data, or bypass if it is an advisory. Never bypass a missing-DATA
error. Then resave with the full charge echo, which re-inspects and approves;
a clean reinspection drops the visit from the list.

### 3. Unbilled
The list is a cached snapshot — fixing data does not remove a row, only the
release does. Error types and their fixes:

| Error text | Fix |
|---|---|
| "Unresolved Claim Inspector errors" | Fix/bypass in the inspector, then release |
| "Insurance order is missing on visit" | No plan on file -> facesheet/eligibility -> `addinsurance` + set visit insorder |
| "Patient address is incomplete" | The address PATCH (placeholder rule applies) |
| "...charges have errors" | Per the inspector |
| "A payment from the prior payor is required before another claim can be submitted" | See below |

That last one means AMD tried to bill the NEXT plan in the visit's insorder
after a payment event (any posting, including a $0 denial posting or a
re-posted old payment) and the first plan has no payment linked to it. Two
cases:

- **(a)** Primary paid long ago, the leftover is a secondary balance whose
  secondary window has passed (measured from the **primary's remit date**) ->
  write off and release.
- **(b)** Primary claim recently sent and unanswered -> nothing to bill yet;
  release. It reappears on its own if the secondary still cannot bill after
  the primary posts.

Release with `hideunbillablevisits`. **Never release a visit whose data is
still broken** — that just hides it.

### 4. Exclusions
Clearinghouse and payer rejections, grouped per claim run. Both the
`clearinghouse="1"` and `payer="1"` flags are required on the list call or it
returns empty.

Triage by rejection type — duplicates complete straight off, auth-missing
rejections need the facesheet, carrier-setup rejections (PREF0288) are the
carrier record and not the claim. See `docs/billing_rules.md`.

Complete with `hideexclusions`.

---

## Run alerts

`getclaimrunstatus` — read it every run.

| Alert | Meaning | Standing action |
|---|---|---|
| 1 | No clearinghouse report in 4+ days | EDI pipeline may be down; check with support/clearinghouse same day |
| 2 / 3 / 6 | No insurance payment in 45+ days (run / carrier-in-run / carrier) | Identify the silent carrier. Known-broken ERA route -> backlog, watch. Working route -> chase the payer |
| 4 | >=5% claims excluded | Same-day pull of that run's exclusion rows; classify duplicates / data errors / systematic payer-id gaps |
| 5 | >=7% dropped to paper | Payer electronic-routing or enrollment gap -> feeds credentialing |

Aged-run backlog is the recovery scoreboard — report the weekly delta as ERA
fixes and payer portals land.

---

## Insurance lookup cascade

Run **before** escalating a patient for human review. Record every step, and
keep the raw result for the copy-paste trail.

1. **Chart** — plans + open charges (`gettxhistory`, `getdemographic`).
2. **Remits already in AMD** — CO24 = an Advantage plan is responsible ·
   COB9 = hospice · PR27 = coverage terminated · CO16/N382 = bad ID ·
   "entity not found" = wrong payer.
3. **Medicare MBI lookup** at the denied date of service. Returns the whole
   Medicare picture for that DOS: Part A/B dates, MA plan (codes U/R with
   entity name and COB dates -> bill that MA payer), Part D (R/OT = drug plan
   only, so original Medicare), QMB/Medicaid, SNF stays (X), hospice (service
   type 45), and date of death. Error 72 = not a Medicare beneficiary, so take
   the commercial/Medicaid path.
4. **Payer eligibility** on every plan number held, with the real DOS. UHC
   often answers "Inactive" for terminated members regardless of DOS — trust
   the MBI-lookup MA dates over it.
5. **Insurance discovery** when nothing above names a payer (billable per
   check). "Not enrolled with DISCOVERY" means the enrollment is still
   provisioning; retry later.
6. **Only then escalate**, saying exactly what a human should look up and
   where.

Then fix the chart: add/correct plans (no group numbers), end-date dead plans
the day before the first denied DOS, set the new plan's begin date from the
eligibility dates, and rebill **filtered by DOS and carrier** so an unrelated
backlog never goes back out.

Date of death on the Medicare record -> write off any DOS after it and flag
for confirmation.

---

## Facesheets

Facesheets arrive through several channels; check all of them on every pass.
Sources are Google Drive folders (hospital print-to-PDF exports, SNF/ALF
exports from the facility EHR, and a charge feed), plus admit emails from the
facility NP, plus files attached directly in chat.

Filenames are `first last.pdf`. Match to the chart by **name AND DOB** —
spelling drifts between systems. New files sometimes land one level up in the
parent folder; search there too.

### Reading
- Facility EHR exports: `pdftotext -layout` works directly.
- Hospital print-to-PDFs and phone photos are images: `pdftoppm -r 220 -png`
  then `tesseract`. If OCR returns nothing, view the image directly — phone
  photos read fine visually.
- **Mask SSNs on any output. Never print or store one.**

Pull: name, DOB, address, phone, every insurance line **with its label** and
policy number, and the authorization line.

Then apply the Medicare label rule and the authorization rules in
`docs/billing_rules.md`.

Anything blocked on a missing number goes on the needs-facesheet list with the
patient, payer, DOS, exactly what is needed, and the expected source.

---

## Regular reporting

Metrics come from the AMD Report Center. The metric catalog is maintained in
the project workbook — read it first and honor the Keep? column.

Current keeps: collections rate by carrier (90-day lag, monthly) · denial rate
and top denial reasons by carrier (weekly) · AR aging trend by bucket per
carrier week-over-week · days in A/R (weekly) · write-off analysis by reason
(monthly, adjustments-only Transaction Detail) · unpaid-claims delta by
carrier (daily — already backend-native via `massrebillsearch`, no Report
Center needed) · ERA posting throughput (weekly).

Proposed: charge lag · payer mix · clean-claim rate.

### Driving the Report Center
Filters accept typed MM/DD/YYYY dates. The carrier multi-select supports
type-ahead (click the list, type prefix letters, Down / shift+Down to select a
range). **Always narrow carriers** — an all-carrier Transaction Detail ran
over 10 minutes and never finished.

Results render inside an iframe, not the page shell. "Report is being
generated" means still running — poll.

### Output
First run of any metric is a baseline; every later run reports the **delta**
plus threshold flags — an aged bucket up >10% week-over-week, or any carrier
at $0 payments for 30 days. That second pattern is how a dead payer route went
unnoticed once.

Cross-check one number per run against a backend source before presenting.

---

## Open items

- **EDI Reports column** — the last Claims Center column, holding 999/277 and
  payer EOB reports. No API action name found by probing. Unlock by clicking
  the column in Chrome while capturing network requests. High value: those
  reports carry payer claim numbers (ICNs), which unlock payer-portal
  registrations without waiting for paper EOBs, plus denial detail for the
  run-alert exclusions.
- **Mass Rebill button POST** — not captured. Rebill list-wise meanwhile.
- **Report Center run payload** — not captured. Needs an XHR interceptor on
  both the parent window and the iframe before Run Report is clicked.
- **Stuck ERAs** — many ERAs fail auto-posting and sit needing manual number
  adjustments. Plan: parse the nightly ERA automation notification emails
  (they list per-payment-code rule results including failures), learn the
  manual adjustment pattern from a few walked-through examples, then find and
  automate the ERA-module calls.
- **Container egress** — `healthcare.us.stedi.com` and `www.stedi.com` are
  blocked (403). Until allowlisted, Stedi calls run from the browser.
- **Bilateral / I65.23 dcode ids** — still need a lookup call.
