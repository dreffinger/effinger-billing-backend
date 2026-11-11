# CCM documentation hub (started 2026-11-11)

William 11/11/2026: "new artifact called ccm documentation hub, this will be a fax archive and additional practice notes for CCM
supporting the ccm charges"; "a note or folder for each ccm charge that will contain a minimum of a statement note that the time was
spent and at a maximum any unlimited number of supporting documents and orders"; "do patient level data on the neon database but also
have an artifact pull from that and have patient data on it which is ok".

## The record
There is one record per patient per calendar month - the unit chronic care management is billed in. A record holds:
- the month's CCM charge lines (date, code, AdvancedMD visit and charge numbers, facility, provider);
- William's late-entry statement for that month - the least a record holds;
- any number of supporting items of that same month - the most.

## The statement (his words; codes confirmed by him 11/11/2026)
- 99487 alone: "greater than 60 minutes spent during <month> performing chart review, reviewing medication lists, faxes, labs, orders,
  referrals, phone conversations with nurses, the ARNP, the treatment team and family if needed, and on developing treatment plans for
  this patient."
- 99487 with 99489: the same sentence with "greater than 90 minutes".
- Any other set of CCM codes (99489 without 99487, 99490, 99491, 99439, 99437, G0506) has no ready-made statement: the record is flagged
  and William writes that note himself.

## The note
`scripts/helpers/ccm_notes.py` lays the note out like his sample encounter note: the practice's letterhead, the patient, the location,
the provider, the charge date and codes, a section headed LATE ENTRY, the month's supporting items, and his signed stamp down the side.
- The top of the note is the practice's name, North Florida Senior Care. The late entry reads "LATE ENTRY for the charge dated <date>,
  for the month of <month>" and then the day it was written (William 11/11/2026; he and his attorney approved the wording that day).
- It is a late entry: dated the day it is written, never dated an earlier day, and it cannot be signed before it was written.
- The helper never signs for him. The stamp appears only when a signing (who, when) was recorded for that note; until then the note says
  DRAFT - NOT SIGNED. Whether the statement is true of that patient and month is his to review before he signs.
- A signed note is final (the database refuses a change): a correction is a new late entry.
- A month with no supporting item says so on the note and is flagged for him, and so is a month with no ready-made statement.

## Supporting items
Each item has a kind, a date inside the record's month, a source and one line of summary. Kinds: `fax_lab`, `fax_order`,
`fax_hhc_plan_of_care`, `fax_other`, `phone_call`, `call_transcript`, `referral`, `prescription`, `email`, `pcc_record`, `other`.
Where they come from: the practice's RingCentral account (faxes received, and calls and their transcripts on the main number),
referrals and prescriptions sent, home health plans of care signed, e-mail, and later PointClickCare. An item from another month is
refused: a month is supported by that month's own records.

## Where it lives
Neon is the primary store (`tools/db/ccm_schema.sql`: `ccm.patient_month`, `ccm.note`, `ccm.evidence`, `ccm.fax`). The hub artifact is
filled from Neon and may show patient data - it is William's private page, shared as carefully as the Insurance Refresh Board. Nothing
of a patient is written into this repository.

## Not built yet
- The list of every CCM charge ever billed (an AdvancedMD read by a session with billing access).
- The RingCentral search (faxes, calls): it needs the practice's RingCentral app key; `scripts/helpers/ringcentral_fax.py` is on the
  census-inputs pull request.
- Applying `tools/db/ccm_schema.sql` to the practice's database, the loader, the hub artifact page, and his signing step.

Offline proof: `python3 tools/selftest/test_ccm_notes.py` (no AdvancedMD, no RingCentral, no Neon, no network).
