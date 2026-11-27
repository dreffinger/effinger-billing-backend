# Medicaid credentialing (Florida first, any practice)

How to enroll a practice and its clinicians in Medicaid, fix a returned application, and keep every enrollment current.
Written from Effinger Health PA's 2026 work (one APRN re-enrollment, one physician renewal, one group) so the next
practice starts from the lessons instead of the deficiency letters. Florida specifics are marked **FL**. For another
state, keep the checklist and replace the FL portal, phone numbers and forms.

**This repository is public.** Never put in it: SSNs or individual tax IDs, dates of birth, home addresses, driver's
license or SS-card images, NPDB or discipline details, portal usernames or passwords, or signatures. Each practice keeps
those in its private Drive folder (see `practices/<code>/credentialing_medicaid.md` for the pointer) and passwords in a
password manager the owner controls.

## 1. What Medicaid needs (collect once, keep on file)

### The practice (group)
- Legal name, DBA, EIN, group NPI (NPPES entity type 2 must match the Medicaid record), taxonomy
- Group Medicaid ID(s), one per service location; which old location IDs should be closed
- Service, mailing, pay-to and corporate addresses. Every one must be current: undeliverable mail is how an ID gets
  restricted and then terminated.
- Owners and managing employees with 5% or more ownership or control: name, title, SSN, DOB, home address, ownership
  percent. These go on the Owners panel, and **the title there must be the title printed on the agreement**.
- EFT bank letter or voided check, W-9
- Signed Medicaid Provider Agreement (MPA), **current version only** (FL: Non-Institutional, December 2023)
- Background screening for every owner and operator (FL: Level 2 Livescan through the AHCA Clearinghouse)
- Portal account for the group's Medicaid ID: username, recovery email, who owns it (password in the password manager)
- Agreement end date for each base ID (FL: five years for non-institutional; separate renewal notice per base ID)

### Each clinician (individual, or individual enrolling as a member of the group)
- Legal name exactly as on the license (typos propagate: see lesson 3), NPI, taxonomy, NPPES record current
- State license number with the current prefix (FL: APRN licenses are `APRN#######`; `ARNP#######` is rejected)
- DEA, board certification, malpractice carrier and dates (payers ask; FL Medicaid itself does not use CAQH)
- Individual Medicaid ID, group affiliation(s) and the affiliation effective date
- Tax ID used on the individual file (an individual's own SSN when enrolling as a group member: handwritten on the
  form, never typed into a shared file)
- Background screening result and its retention date (FL: Clearinghouse keeps prints five years)
- **APRN or PA:** the state's collaboration form signed by the clinician and the collaborating physician (FL: form
  0104 "Practitioner Collaborative Agreement" with the ATN or Medicaid ID at the top). A clinical protocol or
  supervision agreement is not the form and is logged as "missing".
- Adverse history to disclose, with documents (license discipline, payment suspensions, prior terminations). Answer
  the history questions the way the agency's own records will read.

## 2. Florida: where things are

| What | Where |
|---|---|
| Secure portal (renewals, demographic changes) | https://www.mymedicaid-florida.com > Secure Web Portal Login |
| Enrollment wizard (new applications, "continue application" with ATN + last name) | Provider Services > Enrollment > Enrollment Application |
| Application status, upload, correct (no login) | https://portal.flmmis.com/FLPublic/Provider_ProviderServices/Provider_Enrollment/Provider_Enrollment_EnrollmentStatus/tabId/57/Default.aspx, or run `fl_medicaid_status.py <ATN> <NAME>` |
| Blank forms (MPA, collaboration form 0104, group membership 0113) | https://portal.flmmis.com/FLPublic/Provider_ProviderServices/Provider_Enrollment/Provider_Enrollment_EnrollmentForms/tabId/58/Default.aspx |
| Renewal rules | https://portal.flmmis.com/FLPublic/Provider_ProviderServices/Provider_Enrollment/Provider_Enrollment_ProviderReEnrollment/tabId/59/Default.aspx |
| Background screening (Clearinghouse) | https://crw.flclearinghouse.com (info: https://info.flclearinghouse.com) |
| Provider Enrollment phone | 1-800-289-7799, option 4 |
| Secure portal login help | 1-800-289-7799, option 7 |
| AHCA Medicaid Program Integrity | answers payment restrictions only; sends enrollment questions back to Gainwell |

## 3. Lessons learned (2026)

1. **Agreement title = Owners panel title.** The returned letter said "must be signed by the CEO, president, or all
   persons listed in the owners panel". The rejected copy was signed by the right person but titled "APRN", while the
   Owners panel lists her relationship as OWNER (the most likely reason it was judged incomplete). Print the name and
   title exactly as the Owners panel shows them (the **Title** column, e.g. "SOLE PROPRIETOR", not the Affiliation column,
   e.g. "OWNER"; read it at Providers > Demographic Maintenance > Ownership), and fill every line on
   page 5 (DBA "N/A", NPI, Medicaid ID or "N/A - new applicant, ATN ...", tax ID handwritten).
2. **APRN/PA collaboration is a specific form.** FL wants form 0104. Uploading the practice's ARNP protocol was logged
   as "Practitioner Collaborative Agreement is missing".
3. **A typo on one file spreads.** The physician's own Medicaid file had his first name with an extra letter. The
   wizard copies the collaborator's name from that file into the APRN's application, so the APRN's collaboration
   form "did not match". Fix the name on the physician's file in his renewal (upload a license or ID copy as proof),
   write the correct name plus license and Medicaid ID on form 0104, and add a one-paragraph cover note.
4. **"Screening category LIMITED" still needs fingerprints.** The status page listed Livescan as NOT RECEIVED and the
   letter required the Clearinghouse screening. Start the screening the day the ATN is issued: it is the long pole.
5. **Returned is not denied, and nothing moves until you act.** A deficient application waits ("Awaiting Provider").
   Statuses: Not Submitted, Awaiting Supporting Documentation, In Process (~14 business days), Clearinghouse (<15
   days), QC, State Review, Enrolled, Denied, Closed (inactivity: start over). Check the status page weekly.
6. **Fix in one sitting.** UPLOAD Documentation, then CORRECT Application and Submit. The portal warns the Correct
   Application link can disappear if the session is abandoned.
7. **Group affiliation dates cannot be backdated in the wizard** (earlier dates are rejected). A retroactive effective
   date is a separate ask to Provider Enrollment by phone (option 4), not to Program Integrity.
8. **A terminated ID stops managed-care money too.** SMMC plans check the FFS enrollment. Do not move a non-physician's
   personally performed visits to the physician as rendering: Medicaid has no APRN incident-to. Hold them and rebill
   under the new ID inside the 12-month filing window.
9. **Undeliverable mail is the root cause to prevent.** Keep the service, mail-to and pay-to addresses current on
   every base ID and in NPPES, and remove old locations (an old address line on the file kept appearing on 2026 letters).
10. **Renewal links open only within 90 days of expiry.** Notices go out at 90/60/30 days, one per base ID. The
    agreement's expiry date is the deadline; after it, claims suspend and the ID can be terminated.
11. **Portal passwords expire** (a reminder arrives about 10 days ahead). Reset before working a deadline; login
    help is option 7.

## 4. Keeping it current (put these on the credentialing board)

| Item | Cycle | Reminder |
|---|---|---|
| Medicaid agreement, each base ID (group + each individual) | 5 years (FL non-institutional) | 120 / 90 / 30 days before expiry |
| Background screening retention | 5 years from prints | 90 days before; re-print before any renewal that falls after it |
| State licenses (prefix changes too) | per board | 90 / 30 days |
| NPPES (address, taxonomy, license, group) | on any change; review yearly | nightly diff in `credentialing/cred_check.py` |
| Portal password | per portal policy | when the expiry email arrives |
| Open applications | weekly until Enrolled | `fl_medicaid_status.py` |
| Collaboration agreements (APRN/PA) | when collaborator, license or practice changes | with the license renewal |

## 5. Tools here

- `fl_medicaid_status.py` checks any FL application by ATN and name (no login) and prints document statuses and
  deficiencies. It never changes the application.
- The skill `skills/fl-medicaid-credentialing/SKILL.md` tells a Claude session how to run a fix or a renewal end to end:
  check status, pre-fill the current forms, and hand the signer a short list.
