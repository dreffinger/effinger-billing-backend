---
name: fl-medicaid-credentialing
description: "Florida Medicaid enrollment, returned-application fixes and renewals for any practice: check status by ATN, pre-fill the current forms, give the signer a short list, keep every base ID current."
---

# Florida Medicaid credentialing

Read `credentialing/medicaid/README.md` first: the checklist of inputs, the FL links and phone numbers, and the eleven
lessons from 2026. The practice-specific profile (IDs, open items, account inventory) lives in the practice's private
Drive folder; `practices/<code>/credentialing_medicaid.md` points to it. This repository is public: no SSNs, DOBs, home
addresses, discipline details, usernames, passwords or signatures in it, ever.

## Where documents go
Every document is filed in the practice's Drive Credentialing Vault and indexed in Neon (`credentialing/README.md`, intake rule). Identity, SSN-bearing and discipline documents go only into the restricted folders and are indexed with `--restricted` (no bytes in Neon). For a new practice send `credentialing/medicaid/practice_kit.md` (List A: documents to send; List B: what only they can do).

When giving William steps: exact links and click paths (button and panel names from the portal's own guides), no phone numbers unless he asks.

## Fix a returned (deficient) application
1. `python3 credentialing/medicaid/fl_medicaid_status.py <ATN> <LAST-OR-BUSINESS-NAME>` gives the live document statuses
   and the deficiency text. No login needed. Closed or Denied means a new application.
2. Download the blank forms from the portal's Enrollment Forms page (only current versions are accepted) and pre-fill
   every non-signature field:
   - MPA page 5: printed name and title **exactly as the Owners panel shows them**, Provider's Name, DBA ("N/A" if
     none), NPI, Medicaid ID (or "N/A - new applicant, ATN ..."). Leave the individual's tax ID blank for the signer to
     handwrite. Never type an SSN.
   - APRN/PA: form 0104 with the ATN or Medicaid ID, the applicant's license (current prefix), the collaborating
     physician's name, license and Medicaid ID as they appear on his file. If his file has a typo, write the correct
     name and add a cover note.
3. Hand the signer one list: what to sign, the Clearinghouse step (Livescan), and the upload path (status page >
   UPLOAD Documentation > CORRECT Application > Submit, in one sitting). Email the PDFs and put copies in the
   practice's Drive credentialing folder.
4. Update the board row with read > merge > `update` pinned to `if_version`. Re-run the status check weekly until it
   reads Enrolled.

## Renew an agreement (each base ID: group and each individual)
1. Expiry date from the AHCA notice (90/60/30 days) or the portal. The renewal Quick Link opens only within 90 days.
2. Pre-fill the MPA as above, with the Medicaid ID filled in. For a group, a president or CEO may sign for all
   principals.
3. Signer's list: reset the portal password if needed (option 7), get the Clearinghouse Eligible printout, Quick Links
   > Renewal Application, correct name and address lines (upload proof for a name change), upload the screening proof
   and the signed MPA, Submit, save the Renewal Status page.

## Never
- Sign, attest, create accounts or set passwords for anyone. The owner does those; Claude prepares.
- Read, store or send password values. Keep an account inventory (site, username, owner, help line) in the private
  Drive profile only, and let the owner's password manager autofill.
- Lift a signature from an ID document. Use a saved signature only under `skills/add-signature/SKILL.md`.
- Ask Program Integrity enrollment questions. Gainwell Provider Enrollment (option 4) owns enrollment.
