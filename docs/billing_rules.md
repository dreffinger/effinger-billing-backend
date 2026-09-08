# Standing billing rules

Practice rules that govern every automated pass. These are decisions made by
the practice owner; they override any generic coding instinct. Dates are when
the rule was set.

---

## Data entry

**No group numbers, ever (8/31).** When entering ANY insurance plan, leave both
`grpnum` and `grpname` empty — group numbers have caused billing problems in
the past. Applies to every carrier even when the card or facesheet shows a
group. If a plan was entered with one, strip it.

**Identity check before attaching insurance.** Compare the chart DOB to the
facesheet DOB. Some facilities send patients with placeholder DOBs
(01/01/1900-style), which spawns a duplicate chart on each admit. On a
mismatch, find the existing correct chart and align DOB + insurance to it —
never attach insurance to a mis-dated duplicate, and never guess. Escalate.

**Never type an SSN anywhere.** Mask on any output:
`sed 's/[0-9]\{3\}-[0-9]\{2\}-[0-9]\{4\}/xxx-xx-xxxx/g'`.

---

## The void trap (learned the hard way, 9/2–9/3 — 30 charges voided)

`getchargedetaildataicd10` returns ONLY the one charge you asked for.

Any `updvisitwithcharges` / `updvisitwithnewcharges` resave (`force="1"`)
**REPLACES the visit's charges with the list you send** — every charge you
omit is VOIDED.

Rules:
- Build every resave from a full visit-charge fetch, never from a single-charge
  detail.
- Never echo a single-charge detail on a multi-charge visit (99487+99489,
  99223+99497, 99306+99497).
- Run a void scan after any resave batch.
- Restoring a wrongly voided charge requires explicit sign-off.

---

## Claim frequency — always original (9/3)

Before ANY rebill, set the charge's extra-insurance info to
`resubmissioncode="1" origrefnum=""`, then rebill.

**Never frequency 7** unless handed the payer's ICN.

---

## Diagnosis rules

**Acute stroke dx in an outpatient setting → swap, don't delete (9/1).**
Any claim in a non-hospital setting (POS != 21: ALF 13, nursing facility 31/32,
home 12, office 11) denied for acute ischemic stroke — "ACUTE ISCHEMIC STROKE
DIAGNOSIS SHOULD NOT BE BILLED IN AN OUTPATIENT SETTING" — gets **I63.9
replaced with I69.30** (unspecified sequelae of cerebral infarction). Resave
with the full echo, rebill, verify `insbilled=0`, complete.
**Hospital POS-21 claims keep I63.9.** This supersedes the earlier
delete-the-dx instruction. Bulk sweeps run off-peak.

**Sequela / external-cause code ordering (Pattern 20389).** Move the
S/T/V/W/X/Y code behind the condition code.

**Z51.11 on a facility visit (Pattern 2776).** Drop it.

**Unspecified laterality (Pattern 11256) is a BILLING issue, not a
documentation one.** Apply a known correction; otherwise delete that one dcode
or bypass the advisory so it does not hold billing. **Always log it and raise
it.** Known corrections: hip/knee OA unspecified -> bilateral; hemiplegia
unspecified (G81.90) -> I69.30; carotid stenosis unspecified (I65.2x) ->
I65.23. (The bilateral and I65.23 dcodes still need a lookup call — bypass +
log until captured.)

---

## CCM / modifier 25 gate — do not skip

- **99487** (complex CCM, first 60 min) NEVER carries modifier 25.
- If a 25 belongs anywhere it is on the add-on **99489**, "if at all."
- **99497** (advance care planning) on the same day as 99223 -> the 99497 gets
  the 25.
- Flag any CCM-needs-25 case for human review rather than bulk-approving it.
  Only bulk-approve a clean batch.

Pattern 35790 (99489 with 99487): put the 25 on the 99489, then bypass.
Patterns 3429 / 7011 / 35777 / 33799 (CCM duplicate/frequency on distinct
monthly dates): bypass.

---

## Claim inspector patterns

**Hospital E&M (9922x/9923x) at a non-hospital location (Pattern 4531):**
hospital codes at a non-hospital location -> set the visit's facility to the
hospital, which auto-sets POS 21, then resave.

**Other advisories** (4426 mod-25, 4311 new-pt in history, 4310
provider-history, 4564/28158 dx-not-typical-for-age): bypass to clear, **but
flag real coding issues** — e.g. a second 99344 on an already-established
patient should be recoded to 99349.

**Timely filing (Pattern 20657, DOS > 12 months):** triage by payer. Since
nearly all are past every 12-month window, bypass + submit — the denials
document the write-off — unless told to void.

**Rebills re-run the inspector** and surface new advisories. Re-check after any
sweep.

---

## Write-offs and timely filing

**The 12-month write-off rule is for PRIMARY claims (9/7).** Over 12 months
from DOS and unpaid = write off to insurance (WOINS) with a dated note.

**A secondary / supplement balance is timely from the PRIMARY'S remit date,
not the DOS (9/7).** Medigap (Aetna Senior Supplemental, AARP, etc.) and
Medicaid crossovers with a recent Medicare posting get **rebilled**, never
written off on age. Write-offs made against this rule have had to be voided.

**A Medicaid crossover that paid $0 on Medicare coinsurance** is a contractual
WOINS — never a patient balance.

**Overpayment credits (9/3).** When a payer overpays a line (wrong-CPT rate),
leave the excess as an UNAPPLIED credit under that carrier on the patient. Do
not apply it to that patient's other unadjudicated claims — the payer nets it
on a later remit or requests a refund.

---

## Wrong-payer denials never sit on the patient statement (9/3)

A PR-group denial that really means "wrong payer" — **PR27** coverage
terminated, **PR26/PR200** outside coverage, **PR22/PR24** COB/capitation,
**PR31** not identified, **PI/PR109** not this payer, **PR49/PR96/PR204**
non-covered under that plan — is auto-transferred to the patient by the ERA
poster. **That is a mistake.**

Fix: move the whole visit's balance back to insurance -> find the real payer ->
add the plan (no group numbers) -> end-date the old plan the day before the
first denied DOS -> set insorder to the new sequence -> rebill.

Every patient whose balance was moved back to insurance goes on the
**insurance refresh list**, which appears in every daily update email with
facility, dollar amount, and what is needed.

---

## Payer order

**Medicare first, Medicaid second — never Medicaid first (9/3).**

A facility census showing Medicaid or an LTC Medicaid plan (Humana LTC,
Florida Community Care, Sunshine LTC, "MCD ...") as the payer means
**custodial long-term care only — that is not the physician payer.**

- "Medicare A" on a census = traditional Medicare (skilled stay).
- "MCR LEVEL-<plan>" = a Medicare Advantage plan is primary.
- Medicaid-only patients whose plan is an LTC carrier: physician visits go to
  Medicaid fee-for-service when eligibility shows Full Medicaid active with no
  MMA plan.

Hospice -> Medicare + GV. A 9-digit AARP number = UHC Medicare Advantage.

**Watch for charges dated after a STOP BILLING / expired date** (auto-generated
CCM/AWV charges after a date of death) — flag for void, do not rebill.

---

## The Medicare label rule (facesheets)

**The LABEL decides the payer.** Facilities always print the Medicare number
("good to have"), so its presence means nothing on its own.

- "Medicare Managed" / "Primary Payer: Managed Care" / another insurer listed
  alongside the Medicare number -> **Medicare Advantage with that insurer is
  the ONLY plan, primary**, using the MA policy number (not the MBI), no
  Part D.
- "Medicare Part A / Part B" or plain Medicare -> **traditional Medicare
  primary** (MBI); any other insurer is a supplement/secondary.

Confirm against eligibility whenever possible.

---

## Authorizations

**VA / Optum VA CCN claims REQUIRE the VA authorization number (8/29)** or they
reject. Source: the facesheet insurance block. Format: `VA` / `UC` prefix plus
exactly 12 bytes. Where the field reads `Authorization Auth VA.../...`, the VA
number is the part **before** the slash.

**TRICARE East claims REQUIRE a referral/auth number** — the clearinghouse
rejects `PREF0201 MISSING ORIGINAL REF NUMBER` without it. Source: the hospital
admission facesheet. Send it **exactly as the hospital recorded it**; TRICARE
validates on the next run. Strip a prefix only if it bounces on format.

**"Track" / B-prefixed numbers are TRACKING numbers (HSRM), not billable
auths.** Never bill one. When only a tracking number exists, get the real
number from the payer's portal or by phone.

VA also wants the veteran's ICN (or SSN) as the member id — take the ICN from
the facesheet.

**No auth anywhere -> do NOT bill.** Add it to the needs-facesheet list with
exactly what is needed and the expected source. **Never invent a value.**

Apply the auth to EVERY visit of the stay, with the admission date and
insorder, via `preauth` on the visit resave. It lands on the refplan and prints
as the claim auth — verify it in the detail readback.

---

## Exclusions handling

**Duplicate-claim rejections: complete straight off the rejected list, no
rebill.** The original claim is already in play; rebilling duplicates it again.
This is the authorized exception to "never complete without rebill."

**Primary rejections over 12 months old with an open balance** (member not
valid at DOS, policy canceled, VA "submit with SSN/ICN") -> write off untimely,
complete.

**"Member not valid at DOS" inside 12 months** -> run eligibility with the
chart ids first; if Medicaid FFS is active, add that carrier and send an
original claim; otherwise escalate and complete.

**Carrier-setup rejections (PREF0288 invalid payer id/CPID) are the carrier
record, not the claim.** No API call reads carrier master files — fix in the
AMD UI.

**A facesheet can reveal the claim is on the WRONG payer entirely** -> add the
real plan, bill it, and complete the wrong-payer exclusion.

---

## Payer-specific: United (UNI20) and BCBS ERA backlog (8/29)

United and BCBS remittances were not posting into AMD for a long stretch, so
most UNI20/BCBS charges on the unpaid list **were paid but unposted**.

**Routine passes must NOT auto-rebill them** — they would only deny as
duplicates. Correct the diagnosis if needed, but do not rebill.

Track the UNI20/BCBS unpaid totals as a daily delta; shrinking = ERAs draining.
Entries that persist ~2 weeks with no movement -> gap-period ERA retrieval from
the clearinghouse, or fix-and-resubmit once the payer confirms no payment.

**A charge with `paymentcount > 0` or partial posting is settling — exclude it
from every rebill list.**

---

## Verification (every pass)

Re-run the list calls and `getclaimcenteroverview`. Report:

- cleared counts
- remaining rows with patient + error text
- **everything skipped, with why** (payment-posted, needs-facesheet, DOB
  mismatch, CCM-needs-25)

Append blocked items to the needs-facesheet list. Cross-check one number per
run against a backend source before presenting.
